"""
Storage for guided-take shot lists (scripts/shot_list_builder.py's output).

One row per product+angle, same SQLite `DocumentTable` pattern as
scripts/product_store.py (see scripts/db.py) sharing the same _Docs/store.db
file -- see C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase A).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.config import BASE_DIR
from scripts.db import DocumentTable
from scripts.channel_ownership import resolve_store_scope, owner_for_new_record
from scripts.channel_store import ChannelError

STORE_PATH = BASE_DIR / "_Docs" / "shot_lists.json"


def _store_db_path() -> Path:
    return STORE_PATH.parent / "store.db"


def _store_json_path() -> Path:
    return STORE_PATH


_TABLE = DocumentTable("shot_lists", _store_db_path, _store_json_path)


def _channel_kwargs(channel_id):
    return {"channel_id": channel_id} if channel_id is not None else {}


def _load(channel_id):
    scope = resolve_store_scope(channel_id)
    return _TABLE.load() if scope.unscoped else _TABLE.scoped_load(scope.channel_id, include_legacy=scope.include_legacy)


def _mutate(channel_id):
    scope = resolve_store_scope(channel_id)
    return _TABLE.mutate() if scope.unscoped else _TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy)


def _guard_parent(product_id, channel_id):
    if channel_id is not None:
        from scripts.product_store import ProductStore
        if not ProductStore.get(product_id, channel_id=channel_id):
            raise ChannelError(404, "resource_not_found", "ไม่พบสินค้าที่ร้องขอ")


class ShotListsStore:
    """Keyed by `f"{product_id}:{angle_id}"` -- generating a shot list again
    for the same angle overwrites the previous one (matches how a script
    reroll already overwrites in place, no version history kept)."""

    @staticmethod
    def _now() -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    @classmethod
    def get(cls, product_id: str, angle_id: str, batch: Optional[int] = None, *, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # If batch is provided or extractable from compound angle_id (_bN), look ONLY for batch-specific rows.
        effective_batch = batch
        if effective_batch is None:
            import re
            m = re.search(r"_b(\d+)$", str(angle_id))
            if m:
                effective_batch = int(m.group(1))

        if effective_batch is not None:
            batch_row_id = f"{product_id}:{angle_id}:b{effective_batch}"
            for record in _load(channel_id):
                if record.get("id") == batch_row_id:
                    return record
                if (
                    record.get("product_id") == product_id
                    and record.get("angle_id") == angle_id
                    and record.get("batch") == effective_batch
                ):
                    return record
            # batch specified but no matching row found → no shot list for this batch
            return None
        # No batch specified: return the legacy (no-batch) row if it exists
        row_id = f"{product_id}:{angle_id}"
        records = _load(channel_id)
        for record in records:
            if record.get("id") == row_id:
                return record
        # The real voice-timed builder writes explicit batch 1 even for an
        # unsuffixed default angle. Legacy rows still take priority; another
        # batch must never be substituted into a default filming session.
        for record in records:
            if (
                record.get("product_id") == product_id
                and record.get("angle_id") == angle_id
                and record.get("batch") == 1
            ):
                return record
        return None


    @classmethod
    def upsert(cls, record: Dict[str, Any], batch: Optional[int] = None, *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        record = dict(record)
        _guard_parent(record.get("product_id"), channel_id)
        owner = owner_for_new_record(resolve_store_scope(channel_id), record.get("channel_id"))
        b = batch if batch is not None else record.get("batch")
        if b is None and record.get("angle_id"):
            import re
            m = re.search(r"_b(\d+)$", str(record.get("angle_id")))
            if m:
                b = int(m.group(1))
        if b is not None:
            record["batch"] = b
            record["id"] = f"{record['product_id']}:{record['angle_id']}:b{b}"
        else:
            record.setdefault("id", f"{record['product_id']}:{record['angle_id']}")
        now = cls._now()
        record.setdefault("created_at", now)
        record["updated_at"] = now

        with _mutate(channel_id) as records:
            for i, existing in enumerate(records):
                if existing.get("id") == record["id"]:
                    if "channel_id" in existing:
                        record["channel_id"] = existing["channel_id"]
                    else:
                        record.pop("channel_id", None)
                    records[i] = record
                    break
            else:
                record["channel_id"] = owner
                records.append(record)
        return record

    @classmethod
    def delete(cls, product_id: str, angle_id: str, batch: Optional[int] = None, *, channel_id: Optional[str] = None) -> bool:
        """Deletes shot list record for a product angle."""
        effective_batch = batch
        if effective_batch is None:
            import re
            m = re.search(r"_b(\d+)$", str(angle_id))
            if m:
                effective_batch = int(m.group(1))

        row_id = f"{product_id}:{angle_id}"
        batch_row_id = f"{product_id}:{angle_id}:b{effective_batch}" if effective_batch is not None else None
        found = False
        with _mutate(channel_id) as records:
            if effective_batch is not None:
                filtered = [
                    r for r in records
                    if r.get("id") != batch_row_id
                    and not (r.get("product_id") == product_id and r.get("angle_id") == angle_id and r.get("batch") == effective_batch)
                ]
            else:
                filtered = [
                    r for r in records
                    if r.get("id") != row_id
                    and not (r.get("product_id") == product_id and r.get("angle_id") == angle_id and r.get("batch") is None)
                ]
            if len(filtered) != len(records):
                found = True
                records.clear()
                records.extend(filtered)
        return found

    @classmethod
    def is_stale(cls, product_id: str, angle_id: str, current_script: str, batch: Optional[int] = None, *, channel_id: Optional[str] = None) -> bool:
        """Checks whether the cached shot list matches the angle's current script."""
        record = cls.get(product_id, angle_id, batch=batch, **_channel_kwargs(channel_id))
        if not record:
            return False
        cached_script = record.get("custom_script", "").strip()
        return cached_script != current_script.strip()
