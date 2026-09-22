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

STORE_PATH = BASE_DIR / "_Docs" / "shot_lists.json"


def _store_db_path() -> Path:
    return STORE_PATH.parent / "store.db"


def _store_json_path() -> Path:
    return STORE_PATH


_TABLE = DocumentTable("shot_lists", _store_db_path, _store_json_path)


class ShotListsStore:
    """Keyed by `f"{product_id}:{angle_id}"` -- generating a shot list again
    for the same angle overwrites the previous one (matches how a script
    reroll already overwrites in place, no version history kept)."""

    @staticmethod
    def _now() -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    @classmethod
    def get(cls, product_id: str, angle_id: str, batch: Optional[int] = None) -> Optional[Dict[str, Any]]:
        # If batch is provided or extractable from compound angle_id (_bN), look ONLY for batch-specific rows.
        effective_batch = batch
        if effective_batch is None:
            import re
            m = re.search(r"_b(\d+)$", str(angle_id))
            if m:
                effective_batch = int(m.group(1))

        if effective_batch is not None:
            batch_row_id = f"{product_id}:{angle_id}:b{effective_batch}"
            for record in _TABLE.load():
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
        for record in _TABLE.load():
            if record.get("id") == row_id:
                return record
        return None


    @classmethod
    def upsert(cls, record: Dict[str, Any], batch: Optional[int] = None) -> Dict[str, Any]:
        record = dict(record)
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

        with _TABLE.mutate() as records:
            for i, existing in enumerate(records):
                if existing.get("id") == record["id"]:
                    records[i] = record
                    break
            else:
                records.append(record)
        return record

    @classmethod
    def delete(cls, product_id: str, angle_id: str, batch: Optional[int] = None) -> bool:
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
        with _TABLE.mutate() as records:
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
    def is_stale(cls, product_id: str, angle_id: str, current_script: str, batch: Optional[int] = None) -> bool:
        """Checks whether the cached shot list matches the angle's current script."""
        record = cls.get(product_id, angle_id, batch=batch)
        if not record:
            return False
        cached_script = record.get("custom_script", "").strip()
        return cached_script != current_script.strip()
