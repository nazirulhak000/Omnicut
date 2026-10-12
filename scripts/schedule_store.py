"""Durable queue records for the multi-day TikTok publishing agenda.

Channel ownership (multi-channel P2.2, ADR §12/§13)
---------------------------------------------------
Every queue row and every template carries a top-level ``channel_id``; rows
without it are legacy (``main`` in compat mode only, invisible in strict
mode until the migration tool assigns an owner).  The record-level service
below is the ONLY public way to read/write them:

* every method takes keyword ``channel_id`` / ``all_channels`` exactly like
  ``ProductStore``: ``"a"`` = channel ``a`` (+ legacy when ``a`` is main and
  strict is off); ``None`` = compat-only unscoped (strict -> 422);
  ``all_channels=True`` = maintenance bypass (allowlisted modules only);
* items are always addressed by ``(channel_id, item_id)`` -- an id of another
  channel is "not found" and is never read or written;
* occupied/blocked slot times are computed per channel, so the same time in
  channel A and B is allowed;
* template ids are ``<channel_id>:default`` and ``<channel_id>:week:<YYYY-MM-DD>``.
  Legacy ids ``default`` / ``week:<date>`` (no ``channel_id``) are read as
  ``main``'s templates in compat mode only and are edited in place (they
  stay legacy -- renaming them is the migration tool's job, P2.3).

``_load()/_save()/_mutate()`` stay the INTERNAL full-table access (all
channels) and remain the patch points existing tests use; unscoped calls
run through them.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from scripts import config
from scripts.config import BASE_DIR
from scripts.channel_ownership import OWNER_KEY, StoreScope, owner_for_new_record, resolve_store_scope
from scripts.db import DocumentTable

SCHEDULE_QUEUE_PATH = BASE_DIR / "_Docs" / "schedule_queue.json"
SCHEDULE_TEMPLATE_PATH = BASE_DIR / "_Docs" / "schedule_templates.json"

LEGACY_DEFAULT_TEMPLATE_ID = "default"


def _db_path() -> Path:
    return SCHEDULE_QUEUE_PATH.parent / "store.db"


def _json_path() -> Path:
    return SCHEDULE_QUEUE_PATH


def _template_db_path() -> Path:
    return SCHEDULE_TEMPLATE_PATH.parent / "store.db"


def _template_json_path() -> Path:
    return SCHEDULE_TEMPLATE_PATH


_TABLE = DocumentTable("schedule_queue", _db_path, _json_path)
_TEMPLATE_TABLE = DocumentTable("schedule_templates", _template_db_path, _template_json_path)


def _scope(channel_id: Optional[str] = None, all_channels: bool = False) -> StoreScope:
    return resolve_store_scope(channel_id, all_channels=all_channels)


def _visible(rows: Iterable[Dict[str, Any]], scope: StoreScope) -> List[Dict[str, Any]]:
    rows = list(rows)
    if scope.unscoped:
        return rows
    return [row for row in rows if scope.owns(row)]


class ScheduleQueueStore:
    # ------------------------------------------------------------------
    # internal full-table access (all channels)
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _save(cls, records: List[Dict[str, Any]]) -> None:
        _TABLE.save(records)

    @classmethod
    def _mutate(cls):
        return _TABLE.mutate()

    @classmethod
    @contextmanager
    def _scoped_mutate(cls, scope: StoreScope):
        if scope.unscoped:
            with cls._mutate() as records:
                yield records
            return
        with _TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy) as records:
            yield records

    # ------------------------------------------------------------------
    # public, channel-scoped service
    # ------------------------------------------------------------------
    @classmethod
    def transaction(cls, *, channel_id: Optional[str] = None, all_channels: bool = False):
        """Context manager: the rows of ONE channel inside one write transaction.

        For multi-row operations (bulk create, auto-fill commit) that must
        validate and write all-or-nothing.  Only that channel's rows are
        exposed; rows appended must carry ``channel_id`` = the scope owner
        (use :meth:`new_owner`) -- the db layer re-verifies at commit.
        Never call another store's writer inside the block (same connection).
        """
        return cls._scoped_mutate(_scope(channel_id, all_channels))

    @staticmethod
    def new_owner(*, channel_id: Optional[str] = None, all_channels: bool = False) -> str:
        """Owner to stamp on a new queue row (compat ``None`` -> main; all_channels -> ValueError)."""
        return owner_for_new_record(_scope(channel_id, all_channels))

    @classmethod
    def list_items(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        return _visible(cls._load(), _scope(channel_id, all_channels))

    @classmethod
    def get_item(
        cls, item_id: str, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Optional[Dict[str, Any]]:
        return next(
            (row for row in cls.list_items(channel_id=channel_id, all_channels=all_channels) if row.get("id") == item_id),
            None,
        )

    @classmethod
    def owner_of(cls, item_id: str) -> tuple[bool, Optional[str]]:
        """``(exists, channel_id)`` across ALL channels (system read for 404 guards)."""
        for row in cls._load():
            if row.get("id") == item_id:
                return True, row.get(OWNER_KEY)
        return False, None

    @classmethod
    def occupied_times(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> set:
        """Every ``scheduled_at`` already used by this channel (posted rows included)."""
        return {str(row.get("scheduled_at")) for row in cls.list_items(channel_id=channel_id, all_channels=all_channels)}

    @classmethod
    def update_item(
        cls,
        item_id: str,
        fn: Callable[[Dict[str, Any], List[Dict[str, Any]]], Any],
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Edit one row of the channel in one transaction.

        ``fn(row, channel_rows)`` edits ``row`` in place (``channel_rows`` = the
        channel's rows, read-only, for per-channel collision checks) and may
        raise to abort with nothing written.  Returns a copy of the row, or
        ``None`` when the id does not exist in this channel.
        """
        with cls._scoped_mutate(_scope(channel_id, all_channels)) as records:
            row = next((item for item in records if item.get("id") == item_id), None)
            if row is None:
                return None
            owner_before = (OWNER_KEY in row, row.get(OWNER_KEY))
            fn(row, records)
            if (OWNER_KEY in row, row.get(OWNER_KEY)) != owner_before:
                raise ValueError("ห้ามเปลี่ยน channel_id ของรายการในคิว")
            return dict(row)

    @classmethod
    def remove_item(
        cls,
        item_id: str,
        guard: Optional[Callable[[Dict[str, Any]], Any]] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Remove one row of the channel (``guard(row)`` may raise to refuse).
        Returns the removed row, or ``None`` when the id is not in this channel."""
        with cls._scoped_mutate(_scope(channel_id, all_channels)) as records:
            row = next((item for item in records if item.get("id") == item_id), None)
            if row is None:
                return None
            if guard is not None:
                guard(row)
            records.remove(row)
            return dict(row)


class ScheduleTemplateStore:
    """Durable weekly schedule templates, kept separate from queue rows (per channel)."""

    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TEMPLATE_TABLE.load()

    @classmethod
    def _save(cls, records: List[Dict[str, Any]]) -> None:
        _TEMPLATE_TABLE.save(records)

    @classmethod
    def _mutate(cls):
        return _TEMPLATE_TABLE.mutate()

    @classmethod
    @contextmanager
    def _scoped_mutate(cls, scope: StoreScope):
        if scope.unscoped:
            with cls._mutate() as records:
                yield records
            return
        with _TEMPLATE_TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy) as records:
            yield records

    # -- ids ------------------------------------------------------------
    @staticmethod
    def template_id(channel_id: str, week_key: Optional[str] = None) -> str:
        """``<channel>:default`` / ``<channel>:week:<YYYY-MM-DD>``."""
        return f"{channel_id}:week:{week_key}" if week_key else f"{channel_id}:default"

    @staticmethod
    def legacy_template_id(week_key: Optional[str] = None) -> str:
        return f"week:{week_key}" if week_key else LEGACY_DEFAULT_TEMPLATE_ID

    @staticmethod
    def _template_channel(scope: StoreScope) -> str:
        """The channel whose templates a call addresses.  Compat ``None`` means
        ``main`` (the old single global template set); ``all_channels`` has
        no single template set and is refused."""
        if scope.channel_id is not None:
            return scope.channel_id
        if scope.all_channels:
            raise ValueError("เทมเพลตตารางโพสต์ต้องระบุช่อง (all_channels ใช้ไม่ได้)")
        return config.DEFAULT_CHANNEL_ID

    @classmethod
    def _pick(cls, rows: List[Dict[str, Any]], channel: str, week_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """Channel-scoped id first; legacy id (no owner) only for main.

        ``rows`` is already filtered to the scope, so a legacy row is only
        present when legacy rows belong to this channel (main, compat)."""
        wanted = cls.template_id(channel, week_key)
        legacy = cls.legacy_template_id(week_key)
        scoped = next((row for row in rows if row.get("id") == wanted and row.get(OWNER_KEY) == channel), None)
        if scoped is not None:
            return scoped
        if channel != config.DEFAULT_CHANNEL_ID:
            return None
        return next((row for row in rows if row.get("id") == legacy and row.get(OWNER_KEY) is None), None)

    # -- reads ------------------------------------------------------------
    @classmethod
    def list_templates(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        scope = _scope(channel_id, all_channels)
        rows = _visible(cls._load(), scope)
        if scope.unscoped and not scope.all_channels:
            # compat None = main's template set (old global behaviour)
            main = config.DEFAULT_CHANNEL_ID
            rows = [row for row in rows if row.get(OWNER_KEY) in (None, main)]
        return rows

    @classmethod
    def find_template(
        cls, week_key: Optional[str] = None, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Optional[Dict[str, Any]]:
        """The stored default (``week_key=None``) or week override of ONE channel."""
        scope = _scope(channel_id, all_channels)
        channel = cls._template_channel(scope)
        return cls._pick(cls.list_templates(channel_id=channel_id, all_channels=all_channels), channel, week_key)

    # -- writes -----------------------------------------------------------
    @classmethod
    def upsert_template(
        cls,
        week_key: Optional[str],
        days: Dict[str, Any],
        *,
        timezone: str = "Asia/Bangkok",
        updated_at: str,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Save the default/week template of ONE channel; returns the stored row.

        An existing row (channel id, or main's legacy id) is updated in place
        (it keeps its id/owner); otherwise a new ``<channel>:...`` row stamped
        with ``channel_id`` is created.
        """
        scope = _scope(channel_id, all_channels)
        channel = cls._template_channel(scope)
        with cls._scoped_mutate(scope) as records:
            visible = records if not scope.unscoped else [
                row for row in records if row.get(OWNER_KEY) in (None, config.DEFAULT_CHANNEL_ID)
            ]
            row = cls._pick(list(visible), channel, week_key)
            if row is None:
                row = {
                    "id": cls.template_id(channel, week_key),
                    OWNER_KEY: owner_for_new_record(scope),
                    "week_start": week_key,
                    "timezone": timezone,
                    "days": days,
                    "updated_at": updated_at,
                }
                records.append(row)
            else:
                row["week_start"] = week_key
                row["timezone"] = timezone
                row["days"] = days
                row["updated_at"] = updated_at
            return dict(row)

    @classmethod
    def delete_template(
        cls, week_key: Optional[str], *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> int:
        """Remove ONE channel's week override (channel id + main's legacy id).
        Returns how many rows were removed."""
        scope = _scope(channel_id, all_channels)
        channel = cls._template_channel(scope)
        removed = 0
        with cls._scoped_mutate(scope) as records:
            while True:
                visible = records if not scope.unscoped else [
                    row for row in records if row.get(OWNER_KEY) in (None, config.DEFAULT_CHANNEL_ID)
                ]
                row = cls._pick(list(visible), channel, week_key)
                if row is None:
                    break
                records.remove(row)
                removed += 1
        return removed


def schedule_state_revision(
    queue_rows: Iterable[Dict[str, Any]],
    template_rows: Iterable[Dict[str, Any]],
    post_rows: Iterable[Dict[str, Any]],
) -> str:
    """Revision token of ONE channel's auto-fill inputs (AC04 preview -> commit).

    Hash of the channel's queue rows, template rows and the post-log fields
    the daily rules/analytics read.  Any change between preview and commit
    yields a different token, so a stale preview can never commit silently.
    """
    post_fields = ("id", "posted_at", "product_id", "product_name", "style_preset", "hook_color",
                   "clip_file", "metrics", "metrics_history")

    def canonical(rows: Iterable[Dict[str, Any]]) -> List[str]:
        return sorted(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)

    payload = {
        "queue": canonical(queue_rows),
        "templates": canonical(template_rows),
        "posts": canonical({key: post.get(key) for key in post_fields} for post in post_rows),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"sq1:{digest}"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex
