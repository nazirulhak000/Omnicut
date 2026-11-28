"""Background hybrid auto-post scheduler and per-channel automation settings."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo

from scripts import config
from scripts.channel_scope import ChannelScope, resolve_scope
from scripts.channel_route_policy import UNLISTED_ROUTE_POLICY
from scripts.channel_store import STATUS_ACTIVE, ChannelError, get_default_store
from scripts.db import DocumentTable
from scripts.posting_jobs import PostingJobStore
from scripts.schedule_store import ScheduleQueueStore, now_iso

logger = logging.getLogger(__name__)

PROJECT_TZ = ZoneInfo("Asia/Bangkok")
DEFAULT_AUTOMATION_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "mode": "hybrid",
    "poll_interval_sec": 60,
    "due_window_before_min": 5,
    "due_window_after_min": 30,
}
VALID_MODES = {"hybrid", "schedule", "due_now"}
SCHEDULE_MIN_LEAD = dt.timedelta(minutes=15)
SCHEDULE_MAX_LEAD = dt.timedelta(days=10)
TIKTOK_SCHEDULE_QUOTA = 30

_conductor_proc: Optional[subprocess.Popen] = None


def _settings_json_path(root: Optional[Path] = None) -> Path:
    return (root or config.BASE_DIR) / "_Docs" / "autopost_automation_settings.json"


class AutomationSettingsStore:
    """Per-channel automation settings persisted in SQLite + JSON mirror."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else None
        self.table = DocumentTable(
            "autopost_automation_settings",
            lambda: self.path.parent / "store.db",
            lambda: self.path,
        )

    @property
    def path(self) -> Path:
        return _settings_json_path(self.root)

    @staticmethod
    def defaults(channel_id: str) -> Dict[str, Any]:
        return {
            "id": channel_id,
            "channel_id": channel_id,
            **DEFAULT_AUTOMATION_SETTINGS,
            "updated_at": None,
        }

    def get(self, channel_id: str) -> Dict[str, Any]:
        rows = self.table.load()
        row = next((r for r in rows if r.get("channel_id") == channel_id or r.get("id") == channel_id), None)
        base = self.defaults(channel_id)
        if row:
            base.update({k: v for k, v in row.items() if v is not None or k == "updated_at"})
        base["id"] = channel_id
        base["channel_id"] = channel_id
        return base

    def put(self, channel_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        with self.table.mutate() as rows:
            idx = next(
                (i for i, r in enumerate(rows) if r.get("channel_id") == channel_id or r.get("id") == channel_id),
                None,
            )
            current = self.defaults(channel_id)
            if idx is not None:
                current.update(rows[idx])
            for key in ("enabled", "mode", "poll_interval_sec", "due_window_before_min", "due_window_after_min"):
                if key in patch and patch[key] is not None:
                    current[key] = patch[key]
            current["id"] = channel_id
            current["channel_id"] = channel_id
            current["updated_at"] = now_iso()
            if idx is not None:
                rows[idx] = current
            else:
                rows.append(current)
            return dict(current)


def get_automation_settings_store() -> AutomationSettingsStore:
    return AutomationSettingsStore(config.BASE_DIR)


def conductor_state_path(root: Optional[Path] = None) -> Path:
    return (root or config.BASE_DIR) / "tools" / "autopost_conductor" / "state.json"


def conductor_script_path(root: Optional[Path] = None) -> Path:
    return (root or config.BASE_DIR) / "tools" / "autopost_conductor" / "run.js"


def read_conductor_state(root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = conductor_state_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def is_conductor_running(root: Optional[Path] = None) -> tuple[bool, Optional[int]]:
    global _conductor_proc
    if _conductor_proc is not None:
        if _conductor_proc.poll() is None:
            return True, _conductor_proc.pid
        _conductor_proc = None
    state = read_conductor_state(root)
    if state and state.get("running"):
        pid = state.get("pid")
        if _pid_alive(pid):
            return True, pid
    return False, None


def spawn_conductor(
    *,
    mode: str = "hybrid",
    channel_id: Optional[str] = "main",
    limit: int = 5,
    all_channels: bool = False,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Spawn `node tools/autopost_conductor/run.js` in background if not already running."""
    global _conductor_proc
    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported conductor mode: {mode}")
    running, existing_pid = is_conductor_running(root)
    if running:
        return {"started": False, "reason": "already_running", "pid": existing_pid}

    base = Path(root) if root is not None else config.BASE_DIR
    script = conductor_script_path(base)
    cmd: List[str] = ["node", str(script), "--mode", mode, "--limit", str(int(limit))]
    if all_channels:
        cmd.append("--all-channels")
    else:
        cmd.extend(["--channel", channel_id or "main"])

    proc = subprocess.Popen(
        cmd,
        cwd=str(base),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _conductor_proc = proc
    return {"started": True, "reason": "started", "pid": proc.pid}


def parse_queue_datetime(raw: Any) -> Optional[dt.datetime]:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PROJECT_TZ)
    return parsed.astimezone(PROJECT_TZ)


def is_due_now(
    item: Dict[str, Any],
    *,
    now: Optional[dt.datetime] = None,
    before_min: int = 5,
    after_min: int = 30,
) -> bool:
    if item.get("status") not in {"planned", "ready_for_extension"}:
        return False
    when = parse_queue_datetime(item.get("scheduled_at"))
    if when is None:
        return False
    current = (now or dt.datetime.now(PROJECT_TZ)).astimezone(PROJECT_TZ)
    lower = current - dt.timedelta(minutes=max(0, int(before_min)))
    upper = current + dt.timedelta(minutes=max(0, int(after_min)))
    return lower <= when <= upper


def is_in_schedule_window(
    item: Dict[str, Any],
    *,
    now: Optional[dt.datetime] = None,
) -> bool:
    if item.get("status") != "planned":
        return False
    when = parse_queue_datetime(item.get("scheduled_at"))
    if when is None:
        return False
    current = (now or dt.datetime.now(PROJECT_TZ)).astimezone(PROJECT_TZ)
    return (current + SCHEDULE_MIN_LEAD) <= when <= (current + SCHEDULE_MAX_LEAD)


def active_channel_ids() -> List[str]:
    try:
        channels = get_default_store().list_channels(include_archived=False)
        ids = [str(c["id"]) for c in channels if c.get("status") == STATUS_ACTIVE and c.get("id")]
        return ids or ["main"]
    except Exception:
        return ["main"]


def _scope_for_channel(channel_id: str) -> ChannelScope:
    return resolve_scope(
        header_values=[channel_id],
        query_values=[],
        policy=UNLISTED_ROUTE_POLICY,
        strict=config.is_multi_channel_strict(),
    )


def _ensure_due_item_prepared_post_now(item: Dict[str, Any], channel_id: str) -> None:
    """Ensure a due queue item has a prepared `post_now` job ready for the conductor."""
    from scripts.api_tiktok_autopost import PrepareRequest, prepare

    jobs = PostingJobStore(config.BASE_DIR)
    existing_job_id = item.get("posting_job_id")
    if item.get("status") == "ready_for_extension" and existing_job_id:
        try:
            existing_job = jobs.get(channel_id, existing_job_id)
            if existing_job.get("intent") == "post_now" and existing_job.get("status") in {"prepared", "claimed"}:
                return
            if existing_job.get("status") == "prepared":
                jobs.cancel(channel_id, existing_job_id)
        except ChannelError:
            pass

    scope = _scope_for_channel(channel_id)
    prepare(
        PrepareRequest(
            video_path=item["video_path"],
            cover_path=item.get("cover_path"),
            caption=item.get("caption") or "",
            hashtags=item.get("hashtags") or "",
            product_id=item.get("product_id"),
            angle_id=item.get("angle_id"),
            export_id=item.get("export_id"),
            queue_id=item["id"],
            idempotency_key=f"queue:{item['id']}:{item.get('updated_at', '')}:post_now",
            tiktok_product_id=item.get("tiktok_product_id"),
            product_name=item.get("product_name"),
            intent="post_now",
        ),
        scope=scope,
    )


class AutopostScheduler:
    """Lightweight async background loop for hybrid auto-posting across channels."""

    def __init__(
        self,
        *,
        settings_store_factory: Callable[[], AutomationSettingsStore] = get_automation_settings_store,
        spawner: Callable[..., Dict[str, Any]] = spawn_conductor,
        channel_lister: Callable[[], List[str]] = active_channel_ids,
        prepare_due_item: Callable[[Dict[str, Any], str], None] = _ensure_due_item_prepared_post_now,
    ) -> None:
        self._settings_store_factory = settings_store_factory
        self._spawner = spawner
        self._channel_lister = channel_lister
        self._prepare_due_item = prepare_due_item
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="autopost-scheduler")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _next_poll_seconds(self) -> float:
        try:
            store = self._settings_store_factory()
            intervals = [
                int(store.get(ch).get("poll_interval_sec") or 60)
                for ch in self._channel_lister()
                if store.get(ch).get("enabled")
            ]
            if intervals:
                return float(max(10, min(intervals)))
        except Exception:
            pass
        return 60.0

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[AutopostScheduler] tick failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._next_poll_seconds())
            except asyncio.TimeoutError:
                continue

    async def run_once(self, *, now: Optional[dt.datetime] = None, allow_in_pytest: bool = False) -> List[Dict[str, Any]]:
        if os.environ.get("PYTEST_CURRENT_TEST") and not allow_in_pytest:
            return []
        async with self._lock:
            actions: List[Dict[str, Any]] = []
            store = self._settings_store_factory()
            current = (now or dt.datetime.now(PROJECT_TZ)).astimezone(PROJECT_TZ)

            for channel_id in self._channel_lister():
                try:
                    settings = store.get(channel_id)
                    if not settings.get("enabled"):
                        continue

                    mode = settings.get("mode", "hybrid")
                    before_min = int(settings.get("due_window_before_min", 5))
                    after_min = int(settings.get("due_window_after_min", 30))

                    items = ScheduleQueueStore.list_items(channel_id=channel_id)
                    due_items = [
                        item for item in items
                        if is_due_now(item, now=current, before_min=before_min, after_min=after_min)
                    ]

                    if mode in {"hybrid", "due_now"} and due_items:
                        due_items.sort(key=lambda r: str(r.get("scheduled_at") or ""))
                        for due in due_items:
                            try:
                                self._prepare_due_item(due, channel_id)
                            except Exception as exc:
                                logger.warning("[AutopostScheduler] prepare due item %s failed: %s", due.get("id"), exc)
                        result = self._spawner(mode="due_now", channel_id=channel_id, limit=1)
                        actions.append({"channel_id": channel_id, "mode": "due_now", **result})
                        if result.get("started"):
                            break
                        continue

                    if mode in {"hybrid", "schedule"}:
                        scheduled_count = sum(1 for item in items if item.get("status") == "scheduled_on_platform")
                        has_schedulable = any(is_in_schedule_window(item, now=current) for item in items)
                        if scheduled_count < TIKTOK_SCHEDULE_QUOTA and has_schedulable:
                            running, _ = is_conductor_running()
                            if not running:
                                result = self._spawner(mode="schedule", channel_id=channel_id, limit=3)
                                actions.append({"channel_id": channel_id, "mode": "schedule", **result})
                                if result.get("started"):
                                    break
                except Exception as exc:
                    logger.warning("[AutopostScheduler] channel %s error: %s", channel_id, exc)
            return actions


_default_scheduler: Optional[AutopostScheduler] = None


def get_autopost_scheduler() -> AutopostScheduler:
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = AutopostScheduler()
    return _default_scheduler
