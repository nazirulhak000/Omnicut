"""Production chain: the steps of one product run back to back by the server.

Three chains:

* ``draft``  -- prepare the voice of every angle that has no draft yet, scan
  the attached footage that has no Scene Catalog, then build the drafts, and
  stop so the owner can review them in the Editor.
* ``render`` -- render every reviewed draft from the state the Editor saved
  (the same function the Editor's own Render button ends in), a few at a time.
* ``full``   -- ``draft`` then ``render`` in one task, without the review stop.
  It renders only the drafts it built itself; drafts left from earlier runs
  are the ``render`` chain's job.

None of them touches the posting queue: the owner schedules finished clips
later, from the schedule page.

Each chain is one ``production_chain`` task in TaskManager. It runs on its own
thread, so it keeps going when the page is closed, and it only calls workers
that already exist: a step that was done before is skipped by that worker, so
pressing the button again after a restart continues where the work stopped.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Mapping
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from scripts import render_jobs
from scripts.channel_scope import ChannelScope, require_active_for_new_work, require_final_ready
from scripts.channel_workflows import capture_job_scope, get_workflow_scope, require_record_owner
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager

router = APIRouter(tags=["Production chain"])

TASK_TYPE = "production_chain"
KINDS = ("draft", "render", "full")
KIND_LABEL = {"draft": "ผลิตถึงดราฟต์", "render": "เรนเดอร์ดราฟต์", "full": "ผลิตจนเรนเดอร์เสร็จ"}

# Seconds between looks at a child task, a draft batch or the cancel flag.
POLL_SECONDS = 1.0

# The Editor resumes from the mix stage when the audio settings changed and
# from subtitles otherwise. A chain cannot know which, so it always redoes the
# mix: slower by one stage, never stale.
RENDER_PART = "bgm"

_ACTIVE: Dict[tuple, str] = {}
_ACTIVE_LOCK = threading.Lock()

# task id -> (low, high): the share of the bar a stage of the full chain owns.
_WINDOWS: Dict[str, tuple] = {}


class ChainBusy(Exception):
    """A chain of this product is still running."""

    def __init__(self, task_id: str):
        super().__init__(task_id)
        self.task_id = task_id


# ─── Angle helpers ────────────────────────────────────────────────────────────

def _angle_id(angle: Dict[str, Any]) -> str:
    return str(angle.get("angle_id") or angle.get("id") or "")


def _angle_batch(angle: Dict[str, Any]) -> int:
    return angle.get("batch") or 1


def _angle_key(angle: Dict[str, Any]) -> str:
    """Same key /shot-list-status uses; angle ids repeat across batches."""
    return f"{_angle_id(angle)}_b{_angle_batch(angle)}"


def _angle_name(angle: Dict[str, Any]) -> str:
    return str(angle.get("hook_title") or angle.get("angle_name") or _angle_id(angle))


def _angle_ref(angle: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    return {"angle_id": _angle_id(angle), "batch": _angle_batch(angle), "name": _angle_name(angle), **extra}


def _is_finished(angle: Dict[str, Any]) -> bool:
    return angle.get("status") in ("rendered", "posted") or bool(angle.get("posted_at"))


def _has_draft(angle: Dict[str, Any]) -> bool:
    return angle.get("status") in ("in_production", "rendered", "posted") and bool(angle.get("project_name"))


def _has_script(angle: Dict[str, Any]) -> bool:
    lines = angle.get("script_lines") or angle.get("tts_lines") or []
    return any(str(line).strip() for line in lines)


def _angles_in_scope(product: Dict[str, Any], batch_index: Optional[int]) -> List[Dict[str, Any]]:
    angles = [a for a in product.get("angles", []) or [] if _angle_id(a)]
    if batch_index is None:
        return angles
    return [a for a in angles if _angle_batch(a) == batch_index]


def _channel_kwargs(channel_id: Optional[str]) -> Dict[str, str]:
    return {"channel_id": channel_id} if channel_id else {}


def _voice_ready(product_id: str, angle: Dict[str, Any], channel_id: Optional[str]) -> bool:
    from scripts.api_shot_lists import shot_list_voice_engine
    from scripts.shot_lists_store import ShotListsStore

    kwargs = _channel_kwargs(channel_id)
    batch = _angle_batch(angle)
    record = ShotListsStore.get(product_id, _angle_id(angle), batch=batch, **kwargs)
    if not record and batch == 1:
        record = ShotListsStore.get(product_id, _angle_id(angle), **kwargs)
    return bool(record) and not shot_list_voice_engine(record)[2]


# ─── Task helpers ─────────────────────────────────────────────────────────────

def _task_status(task_id: str) -> str:
    return str((TaskManager.get_task(task_id) or {}).get("status") or "")


def _cancelled(task_id: str) -> bool:
    return _task_status(task_id) == "cancelled"


def _progress(task_id: str, value: float, label: str) -> None:
    """Report progress; a poll that found nothing new adds no log line."""
    low, high = _WINDOWS.get(task_id, (0.0, 1.0))
    value = low + (high - low) * value
    task = TaskManager.get_task(task_id) or {}
    if task.get("step_label") == label and abs(float(task.get("progress") or 0.0) - value) < 0.005:
        return
    TaskManager.update_progress(task_id, value, step_label=label)


@contextmanager
def _progress_window(task_id: str, low: float, high: float) -> Iterator[None]:
    """Map the 0..1 progress of one stage of the full chain onto low..high."""
    _WINDOWS[task_id] = (low, high)
    try:
        yield
    finally:
        _WINDOWS.pop(task_id, None)


@contextmanager
def _mirror_child(chain_id: str, child_id: str, label: str, low: float, high: float) -> Iterator[None]:
    """Show a child task's progress on the chain task while the child runs."""
    stop = threading.Event()

    def _loop() -> None:
        while not stop.wait(POLL_SECONDS):
            child = TaskManager.get_task(child_id) or {}
            share = max(0.0, min(1.0, float(child.get("progress") or 0.0)))
            detail = str(child.get("step_label") or "").strip()
            _progress(chain_id, low + (high - low) * share, f"{label} · {detail}" if detail else label)

    watcher = threading.Thread(target=_loop, name=f"chain-mirror-{chain_id[:8]}", daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join(timeout=POLL_SECONDS + 1.0)


# ─── Chain: draft ─────────────────────────────────────────────────────────────

def _voice_step(task_id: str, product: Dict[str, Any], targets: List[Dict[str, Any]],
                voice_preset: Optional[str], channel_id: Optional[str],
                job_scope: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    from scripts.api_shot_lists import _execute_batch_generate_audio_worker

    label = f"ขั้น 1/3 เตรียมเสียงพากย์ {len(targets)} มุม"
    _progress(task_id, 0.03, label)
    payload: Dict[str, Any] = {"angle_keys": [_angle_key(a) for a in targets], "force_regenerate": False}
    if voice_preset:
        payload["voice_preset"] = voice_preset
    child = TaskManager.create_task(
        task_type="batch_generate_audio",
        title=f"เตรียมเสียงพากย์: {product.get('name', product['id'])} (ผลิตถึงดราฟต์)",
        payload={"product_id": product["id"], "chain_task_id": task_id, **payload},
        target_tab="flow",
        target_id=product["id"],
        **_channel_kwargs(channel_id),
        job_scope=job_scope or None,
    )
    with _mirror_child(task_id, child["id"], label, 0.03, 0.40):
        _execute_batch_generate_audio_worker(child["id"], product["id"], payload, channel_id, job_scope or {})
    done = TaskManager.get_task(child["id"]) or {}
    result = done.get("result") or {}
    return {
        "ok": done.get("status") == "completed",
        "error": str(done.get("error") or ""),
        "generated": int(result.get("generated") or 0),
        "skipped": int(result.get("skipped") or 0),
    }


def _scan_step(task_id: str, product: Dict[str, Any], channel_id: Optional[str],
               job_scope: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    from scripts import api_products
    from scripts.gemini_vision_matcher import GeminiVisionMatcher

    videos = api_products.collect_canonical_videos(product)
    pending: List[str] = []
    missing_files = 0
    for video in videos:
        full = Path(video)
        if not full.is_absolute():
            full = api_products.BASE_DIR / video
        if not full.exists():
            missing_files += 1
        elif not GeminiVisionMatcher.get_cached_catalog(str(full)):
            pending.append(video)

    report = {"ok": True, "videos": len(videos), "scanned": 0, "missing_files": missing_files,
              "not_analyzed": {}, "error": ""}
    if not pending:
        return report

    label = f"ขั้น 2/3 สแกนฉาก {len(pending)} คลิป"
    _progress(task_id, 0.42, label)
    child = TaskManager.create_task(
        task_type="scene_indexing",
        title=f"สแกนสารบัญฉาก {len(pending)} คลิป ({product.get('name', product['id'])})",
        payload={"product_id": product["id"], "videos_to_index": pending, "force": False,
                 "chain_task_id": task_id},
        target_tab="flow",
        target_id=product["id"],
        **_channel_kwargs(channel_id),
        job_scope=job_scope or None,
    )
    with _mirror_child(task_id, child["id"], label, 0.42, 0.62):
        outcome = api_products.run_scene_scan(child["id"], pending, force=False)
    report["scanned"] = len(outcome.get("indexed") or {})
    report["not_analyzed"] = dict(outcome.get("not_analyzed") or {})
    report["error"] = str(outcome.get("error") or "")
    # Owner's rule: a draft cut without the catalog is not what was asked for,
    # so one clip the AI could not look at stops the chain.
    report["ok"] = bool(outcome.get("ok")) and not report["not_analyzed"]
    if not report["ok"] and not report["error"]:
        reason = next(iter(report["not_analyzed"].values()), "")
        report["error"] = f"AI ไม่ได้วิเคราะห์ภาพ {len(report['not_analyzed'])} คลิป: {reason}".rstrip(": ")
    return report


def _draft_step(task_id: str, product_id: str, ready: List[Dict[str, Any]], voice_preset: Optional[str],
                channel_id: Optional[str], job_scope: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    from scripts.api_batch_render import BatchRenderRequest, batch_render_options
    from scripts.batch_render import BatchRenderManager

    kwargs = _channel_kwargs(channel_id)
    created: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    total = len(ready)
    label = f"ขั้น 3/3 สร้างดราฟต์ {total} มุม"
    _progress(task_id, 0.64, label)

    # One batch per lot: an angle id is only unique inside its lot.
    lots: Dict[int, List[Dict[str, Any]]] = {}
    for angle in ready:
        lots.setdefault(_angle_batch(angle), []).append(angle)

    finished = 0
    cancelled = False
    for lot, angles in sorted(lots.items()):
        if cancelled or _cancelled(task_id):
            cancelled = True
            break
        request = BatchRenderRequest(
            product_id=product_id,
            angle_ids=[_angle_id(a) for a in angles],
            batch_index=lot,
            export_mp4=False,
            **({"voice_preset": voice_preset} if voice_preset else {}),
        )
        try:
            batch = BatchRenderManager.create_batch(
                product_id=product_id,
                angle_ids=request.angle_ids,
                options=batch_render_options(request),
                **kwargs,
                job_scope=job_scope or None,
            )
        except (ValueError, RuntimeError) as err:
            failed.extend(_angle_ref(a, error=str(err)) for a in angles)
            finished += len(angles)
            continue

        batch_id = batch["batch_id"]
        names = {_angle_id(a): _angle_name(a) for a in angles}
        state: Dict[str, Any] = batch
        while True:
            state = BatchRenderManager.get_batch(batch_id, **kwargs) or {}
            if not state or state.get("status") in ("completed", "failed", "cancelled"):
                break
            if _cancelled(task_id):
                BatchRenderManager.cancel_batch(batch_id, **kwargs)
                cancelled = True
                break
            done_now = sum(1 for it in state.get("items", [])
                           if it.get("status") in ("draft_ready", "rendered", "failed", "skipped", "cancelled"))
            _progress(task_id, 0.64 + 0.34 * ((finished + done_now) / max(1, total)),
                      f"{label} · เสร็จ {finished + done_now}/{total}")
            time.sleep(POLL_SECONDS)

        for item in state.get("items", []) or []:
            ref = {"angle_id": item.get("angle_id"), "batch": item.get("batch") or lot,
                   "name": names.get(str(item.get("angle_id")), item.get("angle_name") or "")}
            if item.get("status") in ("draft_ready", "rendered"):
                created.append({**ref, "project_name": item.get("project_name") or ""})
            elif not cancelled:
                failed.append({**ref, "error": str(item.get("error") or f"สถานะ {item.get('status')}")})
        if not state:
            failed.extend(_angle_ref(a, error="ไม่พบคิวดราฟต์ชุดนี้แล้ว") for a in angles)
        finished += len(angles)

    return {"created": created, "failed": failed, "cancelled": cancelled}


def run_draft_chain(task_id: str, product_id: str, *, batch_index: Optional[int] = None,
                    voice_preset: Optional[str] = None, channel_id: Optional[str] = None,
                    job_scope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Voice -> scene scan -> drafts, for the angles that have no draft yet."""
    kwargs = _channel_kwargs(channel_id)
    summary: Dict[str, Any] = {"kind": "draft", "ok": False, "stopped_at": None, "message": "",
                               "voice": None, "scan": None, "drafts": None}

    product = ProductStore.get(product_id, **kwargs)
    if not product:
        summary.update(stopped_at="product", message="ไม่พบสินค้า")
        return summary

    targets = [a for a in _angles_in_scope(product, batch_index)
               if not _is_finished(a) and not _has_draft(a) and _has_script(a)]
    if not targets:
        summary.update(ok=True, message="ไม่มีมุมที่ต้องผลิต — ทุกมุมมีดราฟต์แล้วหรือยังไม่มีสคริปต์",
                       drafts={"created": [], "failed": []})
        return summary

    voice = _voice_step(task_id, product, targets, voice_preset, channel_id, job_scope)
    product = ProductStore.get(product_id, **kwargs) or product
    wanted = {_angle_key(a) for a in targets}
    targets = [a for a in _angles_in_scope(product, batch_index)
               if _angle_key(a) in wanted and not _is_finished(a) and not _has_draft(a)]
    ready = [a for a in targets if _voice_ready(product_id, a, channel_id)]
    missing = [_angle_ref(a) for a in targets if a not in ready]
    summary["voice"] = {"targets": len(wanted), "generated": voice["generated"], "skipped": voice["skipped"],
                        "missing": missing}
    if _cancelled(task_id):
        summary.update(stopped_at="cancelled", message="ยกเลิกหลังขั้นเสียงพากย์")
        return summary
    if not ready:
        reason = voice["error"] or "ไม่มีมุมใดได้เสียงพากย์"
        summary.update(stopped_at="voice", message=f"หยุดที่ขั้นเสียงพากย์: {reason}")
        return summary

    scan = _scan_step(task_id, product, channel_id, job_scope)
    summary["scan"] = scan
    if _cancelled(task_id):
        summary.update(stopped_at="cancelled", message="ยกเลิกหลังขั้นสแกนฉาก")
        return summary
    if not scan["ok"]:
        summary.update(stopped_at="scan",
                       message=f"หยุดที่ขั้นสแกนฉาก ยังไม่ได้สร้างดราฟต์: {scan['error']}")
        return summary

    drafts = _draft_step(task_id, product_id, ready, voice_preset, channel_id, job_scope)
    summary["drafts"] = {"created": drafts["created"], "failed": drafts["failed"]}
    if drafts["cancelled"]:
        summary.update(stopped_at="cancelled", message="ยกเลิกระหว่างสร้างดราฟต์")
        return summary

    made, broken = len(drafts["created"]), len(drafts["failed"])
    parts = [f"สร้างดราฟต์ {made} มุม"]
    if broken:
        parts.append(f"ล้มเหลว {broken} มุม")
    if missing:
        parts.append(f"ไม่มีเสียงพากย์ {len(missing)} มุม")
    if scan["missing_files"]:
        parts.append(f"ไม่พบไฟล์คลิป {scan['missing_files']} ไฟล์")
    summary.update(ok=made > 0, message=" · ".join(parts))
    if not made:
        summary["stopped_at"] = "draft"
        first = drafts["failed"][0]["error"] if drafts["failed"] else ""
        summary["message"] = f"สร้างดราฟต์ไม่สำเร็จ {broken} มุม: {first}".rstrip(": ")
    return summary


# ─── Chain: render ────────────────────────────────────────────────────────────

def _scoped_cutout(manifest: Dict[str, Any]) -> bool:
    """Cutout limited to text windows needs clip ids only the open Editor has
    (video_editor refuses the render without them)."""
    params = manifest.get("render_params") or {}
    isolation = params["background_isolation"] if "background_isolation" in params \
        else manifest.get("background_isolation")
    return (isinstance(isolation, Mapping) and isolation.get("enabled") is True
            and isolation.get("scope_mode") == "behind_text_windows")


def _render_overrides(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """The one thing the Editor resolves at render time rather than on save:
    the badge is stored by name and the renderer reads a path."""
    from scripts.api_phase1 import resolve_sticker_badge_path

    params = manifest.get("render_params") or {}
    if "sticker_badge" not in params:
        return {}
    return {"sticker_path": resolve_sticker_badge_path(params.get("sticker_badge"))}


def _projects_rendering_now() -> set:
    busy = set()
    for task in TaskManager.get_active_tasks(limit=200):
        if task.get("type") == "render_video" and task.get("status") in ("queued", "processing"):
            busy.add(str(task.get("target_id") or ""))
    return busy


def plan_render(product: Dict[str, Any], batch_index: Optional[int],
                only: Optional[set] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Drafts waiting for their render, and the ones this chain must leave alone.

    ``only`` limits the plan to these angle keys (``_angle_key``).
    """
    from scripts.project_manifest import ProjectManifest

    ready: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    busy = _projects_rendering_now()
    for angle in _angles_in_scope(product, batch_index):
        if only is not None and _angle_key(angle) not in only:
            continue
        project = str(angle.get("project_name") or "")
        if _is_finished(angle) or angle.get("status") != "in_production" or not project:
            continue
        ref = _angle_ref(angle, project_name=project)
        if project in busy:
            skipped.append({**ref, "reason": "กำลังเรนเดอร์อยู่แล้ว"})
            continue
        try:
            manifest = ProjectManifest.load(project)
        except ValueError:
            manifest = None
        if not manifest:
            skipped.append({**ref, "reason": "ไม่พบโปรเจกต์ดราฟต์"})
            continue
        if _scoped_cutout(manifest):
            skipped.append({**ref, "reason": "ใช้ Cutout เฉพาะช่วงข้อความ — เรนเดอร์จาก Editor"})
            continue
        ready.append({**ref, "overrides": _render_overrides(manifest)})
    return {"ready": ready, "skipped": skipped}


def _render_one(item: Dict[str, Any], channel_id: Optional[str],
                job_scope: Optional[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
    """One draft through the Editor's render path; returns how it ended."""
    from scripts.api_phase1 import REROLL_STAGE, _execute_reroll

    project = item["project_name"]
    kwargs = _channel_kwargs(channel_id)
    pinned = job_scope or None
    render_jobs.create_job(job_id, message="กำลังเรนเดอร์วิดีโอ...", **kwargs, job_scope=pinned)
    TaskManager.create_task(
        task_type="render_video",
        title=f"เรนเดอร์วิดีโอ: {project}",
        payload={"project_name": project, "part": RENDER_PART, **(job_scope or {})},
        target_tab="editor",
        target_id=project,
        task_id=job_id,
        **kwargs,
        job_scope=pinned,
    )
    _execute_reroll(job_id, project, REROLL_STAGE[RENDER_PART], dict(item.get("overrides") or {}), pinned)

    job = render_jobs.get_job(job_id) or {}
    result = job.get("result") or {}
    status = str(job.get("status") or "")
    if status == "completed" and (result.get("mp4_video") or result.get("video_url")):
        return {"outcome": "rendered"}
    if status in ("cancelled", "cancelling"):
        return {"outcome": "cancelled"}
    if status == "completed":
        return {"outcome": "failed", "error": "เรนเดอร์จบแต่ไม่ได้ไฟล์ MP4"}
    return {"outcome": "failed", "error": str(job.get("error") or "เรนเดอร์ไม่สำเร็จ")}


def run_render_chain(task_id: str, product_id: str, *, batch_index: Optional[int] = None,
                     channel_id: Optional[str] = None,
                     job_scope: Optional[Dict[str, Any]] = None,
                     only: Optional[set] = None) -> Dict[str, Any]:
    """Render every reviewed draft (or the ``only`` angle keys) from its saved Editor state."""
    summary: Dict[str, Any] = {"kind": "render", "ok": False, "stopped_at": None, "message": "",
                               "rendered": [], "failed": [], "skipped": []}
    product = ProductStore.get(product_id, **_channel_kwargs(channel_id))
    if not product:
        summary.update(stopped_at="product", message="ไม่พบสินค้า")
        return summary

    plan = plan_render(product, batch_index, only)
    ready, summary["skipped"] = plan["ready"], plan["skipped"]
    total = len(ready)
    if not total:
        reason = summary["skipped"][0]["reason"] if summary["skipped"] else ""
        summary.update(ok=not summary["skipped"],
                       message=(f"ไม่ได้เรนเดอร์ — ข้าม {len(summary['skipped'])} มุม: {reason}"
                                if summary["skipped"] else "ไม่มีดราฟต์ที่รอเรนเดอร์"))
        return summary

    label = f"เรนเดอร์ {total} คลิป"
    _progress(task_id, 0.03, label)

    gate = threading.Lock()
    in_flight: Dict[str, str] = {}  # job id -> project name
    stop = threading.Event()

    def _admit(job_id: str, project: str) -> bool:
        """Start only when the shared render queue has room for this job.

        render_slot() refuses a caller once MAX_QUEUED_RENDERS are waiting, and
        inside the render function that refusal is a failed clip. A job of
        this chain that has not reported progress yet may still be about to
        join the queue, so it counts as waiting.
        """
        while not stop.is_set():
            with gate:
                unsettled = sum(1 for jid in in_flight
                                if (render_jobs.get_job(jid) or {}).get("status") == "queued")
                if unsettled + render_jobs.queued_count() < render_jobs.MAX_QUEUED_RENDERS:
                    in_flight[job_id] = project
                    return True
            time.sleep(min(POLL_SECONDS, 0.5))
        return False

    def _work(item: Dict[str, Any]) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        if not _admit(job_id, item["project_name"]):
            return {"outcome": "cancelled"}
        try:
            return _render_one(item, channel_id, job_scope, job_id)
        except Exception as err:  # a refusal before the render function starts
            return {"outcome": "failed", "error": str(getattr(err, "detail", None) or err)}
        finally:
            with gate:
                in_flight.pop(job_id, None)

    workers = max(1, min(render_jobs.render_concurrency(), total))
    done_count = 0
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="chain-render") as pool:
        futures = {pool.submit(_work, item): item for item in ready}
        waiting = set(futures)
        while waiting:
            finished, waiting = wait(waiting, timeout=POLL_SECONDS, return_when=FIRST_COMPLETED)
            if not stop.is_set() and _cancelled(task_id):
                stop.set()
                with gate:
                    running = list(in_flight)
                for job_id in running:
                    render_jobs.request_cancel(job_id)
            for future in finished:
                item = futures[future]
                ref = {k: item[k] for k in ("angle_id", "batch", "name", "project_name")}
                ended = future.result()
                if ended["outcome"] == "rendered":
                    summary["rendered"].append(ref)
                elif ended["outcome"] == "failed":
                    summary["failed"].append({**ref, "error": ended.get("error") or ""})
                done_count += 1
                _progress(task_id, 0.03 + 0.95 * (done_count / total), f"{label} · เสร็จ {done_count}/{total}")

    if stop.is_set():
        summary.update(stopped_at="cancelled", message="ยกเลิกระหว่างเรนเดอร์")
        return summary

    made, broken, left = len(summary["rendered"]), len(summary["failed"]), len(summary["skipped"])
    parts = [f"เรนเดอร์เสร็จ {made} คลิป"]
    if broken:
        parts.append(f"ล้มเหลว {broken} คลิป")
    if left:
        parts.append(f"ข้าม {left} มุม")
    summary.update(ok=made > 0, message=" · ".join(parts))
    if not made:
        summary["stopped_at"] = "render"
        first = summary["failed"][0]["error"] if summary["failed"] else ""
        summary["message"] = f"เรนเดอร์ไม่สำเร็จ {broken} คลิป: {first}".rstrip(": ")
    return summary


# ─── Chain: full ──────────────────────────────────────────────────────────────

def run_full_chain(task_id: str, product_id: str, *, batch_index: Optional[int] = None,
                   voice_preset: Optional[str] = None, channel_id: Optional[str] = None,
                   job_scope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The draft chain, then the render chain for the drafts it built.

    The draft chain's own stop rules hold (a failed scene scan builds no
    draft). Drafts that failed are reported; the ones that were built are
    rendered.
    """
    summary: Dict[str, Any] = {"kind": "full", "ok": False, "stopped_at": None, "message": "",
                               "draft": None, "render": None}
    with _progress_window(task_id, 0.0, 0.5):
        draft = run_draft_chain(task_id, product_id, batch_index=batch_index, voice_preset=voice_preset,
                                channel_id=channel_id, job_scope=job_scope)
    summary["draft"] = draft
    created = (draft.get("drafts") or {}).get("created") or []
    if draft.get("stopped_at") == "cancelled" or _cancelled(task_id):
        summary.update(stopped_at="cancelled", message=draft.get("message") or "ยกเลิกก่อนเรนเดอร์")
        return summary
    if not created:
        summary.update(ok=bool(draft.get("ok")), stopped_at=draft.get("stopped_at"),
                       message=draft.get("message") or "")
        return summary

    keys = {_angle_key(item) for item in created}
    with _progress_window(task_id, 0.5, 1.0):
        render = run_render_chain(task_id, product_id, batch_index=batch_index, channel_id=channel_id,
                                  job_scope=job_scope, only=keys)
    summary["render"] = render
    parts = [draft.get("message") or "", render.get("message") or ""]
    if len(render.get("rendered") or []) < len(created):
        parts.append("ดราฟต์ที่ยังไม่ได้เรนเดอร์ใช้ปุ่ม เรนเดอร์ดราฟต์")
    summary.update(ok=bool(render.get("ok")), stopped_at=render.get("stopped_at"),
                   message=" · ".join(part for part in parts if part))
    return summary


# ─── Start / run ──────────────────────────────────────────────────────────────

def _run_chain(task_id: str, product_id: str, kind: str, batch_index: Optional[int],
               voice_preset: Optional[str], channel_id: Optional[str],
               job_scope: Optional[Dict[str, Any]]) -> None:
    key = (channel_id or "", product_id)
    try:
        _progress(task_id, 0.01, f"เริ่ม{KIND_LABEL[kind]}")
        if kind == "draft":
            summary = run_draft_chain(task_id, product_id, batch_index=batch_index, voice_preset=voice_preset,
                                      channel_id=channel_id, job_scope=job_scope)
        elif kind == "full":
            summary = run_full_chain(task_id, product_id, batch_index=batch_index, voice_preset=voice_preset,
                                     channel_id=channel_id, job_scope=job_scope)
        else:
            summary = run_render_chain(task_id, product_id, batch_index=batch_index,
                                       channel_id=channel_id, job_scope=job_scope)
        # A cancelled task is already terminal; both calls below leave it alone.
        if summary["ok"]:
            TaskManager.complete_task(task_id, result=summary, step_label=summary["message"], target_id=product_id)
        else:
            TaskManager.fail_task(task_id, summary["message"], step_label=f"{KIND_LABEL[kind]}ไม่จบ")
    except Exception as err:
        import traceback
        traceback.print_exc()
        TaskManager.fail_task(task_id, str(getattr(err, "message_th", None) or err),
                              step_label=f"{KIND_LABEL[kind]}ล้มเหลว")
    finally:
        with _ACTIVE_LOCK:
            if _ACTIVE.get(key) == task_id:
                _ACTIVE.pop(key, None)


def start_chain(product_id: str, kind: str, *, batch_index: Optional[int] = None,
                voice_preset: Optional[str] = None, channel_id: Optional[str] = None,
                job_scope: Optional[Dict[str, Any]] = None, background: bool = True) -> Dict[str, Any]:
    """Create the chain task and run it; one chain per product at a time."""
    if kind not in KINDS:
        raise ValueError(f"ไม่รู้จักชนิดงาน '{kind}'")
    product = ProductStore.get(product_id, **_channel_kwargs(channel_id))
    if not product:
        raise LookupError("ไม่พบสินค้า")

    key = (channel_id or "", product_id)
    with _ACTIVE_LOCK:
        running = _ACTIVE.get(key)
        if running and _task_status(running) in ("queued", "processing"):
            raise ChainBusy(running)
        lot = f"ล็อตที่ {batch_index}" if batch_index is not None else "ทุกล็อต"
        task = TaskManager.create_task(
            task_type=TASK_TYPE,
            title=f"{KIND_LABEL[kind]}: {product.get('name', product_id)} ({lot})",
            payload={"product_id": product_id, "kind": kind, "batch_index": batch_index,
                     "voice_preset": voice_preset},
            target_tab="flow",
            target_id=product_id,
            **_channel_kwargs(channel_id),
            job_scope=job_scope or None,
        )
        _ACTIVE[key] = task["id"]

    args = (task["id"], product_id, kind, batch_index, voice_preset, channel_id, job_scope)
    if background:
        threading.Thread(target=_run_chain, args=args, daemon=True,
                         name=f"production-chain-{task['id'][:8]}").start()
    else:
        _run_chain(*args)
    return task


# ─── Route ────────────────────────────────────────────────────────────────────

class ProductionChainRequest(BaseModel):
    kind: str
    batch_index: Optional[int] = None
    voice_preset: Optional[str] = None


@router.post("/api/products/{product_id}/production-chain")
def start_production_chain(product_id: str, req: ProductionChainRequest,
                           scope: ChannelScope = Depends(get_workflow_scope)) -> Dict[str, Any]:
    """Starts one of the chains of a product as a background task."""
    if req.kind not in KINDS:
        raise HTTPException(status_code=400, detail="kind ต้องเป็น draft, render หรือ full")
    require_active_for_new_work(scope)
    if req.kind in ("render", "full") and not (scope.is_implicit_default and not scope.strict):
        require_final_ready(scope)
    require_record_owner(scope, ProductStore.get(product_id, channel_id=scope.channel_id), resource_label="สินค้า")
    try:
        task = start_chain(product_id, req.kind, batch_index=req.batch_index, voice_preset=req.voice_preset,
                           channel_id=scope.channel_id, job_scope=capture_job_scope(scope))
    except ChainBusy as busy:
        raise HTTPException(status_code=409, detail={
            "message": "สินค้านี้มีงานผลิตต่อเนื่องทำอยู่แล้ว รอให้จบหรือยกเลิกก่อน",
            "task_id": busy.task_id,
        })
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err))
    return {"success": True, "task_id": task["id"], "task": task}
