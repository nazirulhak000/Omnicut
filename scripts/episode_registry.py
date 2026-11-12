"""Episode numbers (EP) -- a permanent, human-readable id per clip lineage.

Rules (decided with the operator, 2026-11-10):
* One number per *lineage*: product + angle (a re-render of the same angle is a new export but the same episode). A clip without
  product/angle falls back to its own export id.
* The number is issued ONCE, when the clip first enters the queue or is prepared for posting. It is permanent: never reused, never
  re-issued, not even when the draft is deleted or the slot is re-arranged. Nothing is ever guessed back from TikTok.
* Per channel, atomic (one transaction), starting at 1 (configurable). The counter can be raised but never
  lowered to a number that was already issued.
* The caption carries the number as a hashtag ``#EP1731`` (see :func:`compose_hashtags`); the content guard accepts that form.
"""
from __future__ import annotations

import datetime as dt
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts import config
from scripts.channel_store import ChannelError
from scripts.db import DocumentTable

DEFAULT_FIRST_NUMBER = 1
TAG_RE = re.compile(r"#EP0*(\d{1,9})(?!\d)", re.IGNORECASE)


def lineage_key(product_id: Optional[str], angle_id: Optional[str], export_id: Optional[str]) -> str:
    if product_id and angle_id:
        return f"angle:{product_id}:{angle_id}"
    if export_id:
        return f"export:{export_id}"
    raise ChannelError(422, "episode_lineage_missing", "ออกเลข EP ไม่ได้: ไม่มีทั้งสินค้า/มุม และ export id")


def episode_tag(episode_no: int) -> str:
    return f"#EP{int(episode_no)}"


def tag_numbers(text: Any) -> List[int]:
    """Every EP number written as a hashtag in ``text``."""
    return [int(m) for m in TAG_RE.findall(str(text or ""))]


def compose_hashtags(hashtags: Any, episode_no: Optional[int]) -> str:
    """Hashtags with the episode tag appended -- idempotent (already there = unchanged), and a DIFFERENT EP tag is refused
    (a caption must never carry another clip's number)."""
    base = str(hashtags or "").strip()
    if episode_no is None:
        return base
    present = tag_numbers(base)
    if present and any(n != int(episode_no) for n in present):
        raise ChannelError(409, "episode_tag_conflict", f"แฮชแท็กมีเลข EP อื่น ({present}) ที่ไม่ใช่ของคลิปนี้ (EP{int(episode_no)})")
    if int(episode_no) in present:
        return base
    return f"{base} {episode_tag(episode_no)}".strip()


class EpisodeRegistry:
    def __init__(self, root: Path | None = None, *, clock=lambda: dt.datetime.now().isoformat(timespec="seconds")):
        self.root = Path(root) if root is not None else None
        self.clock = clock
        self.table = DocumentTable("episodes", lambda: self.path.parent / "store.db", lambda: self.path)

    @property
    def path(self) -> Path:
        return (self.root or config.BASE_DIR) / "_Docs" / "episodes.json"

    # ---- helpers (always inside one scoped transaction) ----
    @staticmethod
    def _counter_id(channel_id: str) -> str:
        return f"{channel_id}:counter"

    def _counter(self, rows, channel_id: str) -> Dict[str, Any]:
        row = next((r for r in rows if r["id"] == self._counter_id(channel_id)), None)
        if row is None:
            top = max((r["episode_no"] for r in self._episodes(rows)), default=0)
            row = {"id": self._counter_id(channel_id), "channel_id": channel_id, "kind": "counter", "next": max(DEFAULT_FIRST_NUMBER, top + 1)}
            rows.append(row)
        return row

    @staticmethod
    def _episodes(rows) -> List[Dict[str, Any]]:
        return [r for r in rows if r.get("kind") == "episode"]

    # ---- reads ----
    def next_number(self, channel_id: str) -> int:
        rows = self.table.scoped_load(channel_id)
        counter = next((r for r in rows if r["id"] == self._counter_id(channel_id)), None)
        top = max((r["episode_no"] for r in self._episodes(rows)), default=0)
        cur = int(counter["next"]) if counter else DEFAULT_FIRST_NUMBER
        return max(cur, top + 1)

    def list(self, channel_id: str) -> List[Dict[str, Any]]:
        return sorted((deepcopy(r) for r in self._episodes(self.table.scoped_load(channel_id))), key=lambda r: r["episode_no"])

    def by_export(self, channel_id: str) -> Dict[str, int]:
        """export id -> episode number, for read-only joins (queue / export listings)."""
        out: Dict[str, int] = {}
        for row in self._episodes(self.table.scoped_load(channel_id)):
            for export_id in row.get("export_ids", []):
                out[export_id] = row["episode_no"]
        return out

    def get(self, channel_id: str, *, product_id=None, angle_id=None, export_id=None) -> Optional[Dict[str, Any]]:
        key = lineage_key(product_id, angle_id, export_id)
        for row in self._episodes(self.table.scoped_load(channel_id)):
            if row["lineage_key"] == key or (export_id and export_id in row.get("export_ids", [])):
                return deepcopy(row)
        return None

    # ---- writes ----
    def ensure(self, channel_id: str, *, product_id=None, angle_id=None, export_id=None, source: str = "new",
               number: Optional[int] = None) -> Dict[str, Any]:
        """The episode of this clip's lineage, issuing a number the first time. Idempotent; the export id is remembered so later
        read-only joins find it. ``number`` is only for backfill (an explicit, unused number)."""
        key = lineage_key(product_id, angle_id, export_id)
        with self.table.scoped_mutate(channel_id) as rows:
            episodes = self._episodes(rows)
            found = next((r for r in episodes if r["lineage_key"] == key or (export_id and export_id in r.get("export_ids", []))), None)
            if found is not None:
                if export_id and export_id not in found.setdefault("export_ids", []):
                    found["export_ids"].append(export_id)
                return deepcopy(found)
            counter = self._counter(rows, channel_id)
            top = max((r["episode_no"] for r in episodes), default=0)
            if number is None:
                number = max(int(counter["next"]), top + 1)
                counter["next"] = number + 1
            else:
                number = int(number)
                if any(r["episode_no"] == number for r in episodes):
                    raise ChannelError(409, "episode_number_taken", f"เลข EP{number} ถูกใช้แล้ว")
                counter["next"] = max(int(counter["next"]), number + 1, top + 1)
            row = {"id": f"{channel_id}:ep:{number}", "channel_id": channel_id, "kind": "episode", "episode_no": number,
                   "lineage_key": key, "product_id": product_id, "angle_id": angle_id,
                   "export_ids": [export_id] if export_id else [], "source": source, "assigned_at": self.clock()}
            rows.append(row)
            return deepcopy(row)

    def set_next(self, channel_id: str, next_number: int) -> int:
        """Move the counter. Never to a number that was already issued (permanent numbers are never re-issued)."""
        if int(next_number) < 1:
            raise ChannelError(422, "episode_next_invalid", "เลข EP ต้องเป็นจำนวนเต็มบวก")
        with self.table.scoped_mutate(channel_id) as rows:
            top = max((r["episode_no"] for r in self._episodes(rows)), default=0)
            if int(next_number) <= top:
                raise ChannelError(409, "episode_next_taken", f"เลขถัดไปต้องมากกว่าเลขที่ออกไปแล้ว (สูงสุดตอนนี้ EP{top})")
            counter = self._counter(rows, channel_id)
            counter["next"] = int(next_number)
            return int(counter["next"])
