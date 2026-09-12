"""Pending TikTok Studio rows that auto-matching could not place.

Rows the extension scraped but neither an existing post nor a clip
candidate matched go here instead of vanishing when the side panel
closes. The Performance tab lists them so the user can attach each row
to the right library clip by hand (see api_tiktok_stats.attach).

Same storage contract as PostLog: SQLite document table in store.db,
mirrored to a plain JSON file next to post_log.json.
"""

from typing import Any, Dict, List

from scripts.config import BASE_DIR
from scripts.db import DocumentTable

PENDING_PATH = BASE_DIR / "_Docs" / "tiktok_pending.json"


def _pending_db_path():
    return BASE_DIR / "_Docs" / "store.db"


def _pending_json_path():
    return PENDING_PATH


_TABLE = DocumentTable("tiktok_pending", _pending_db_path, _pending_json_path)


def _identity(row: Dict[str, Any]) -> str:
    vid = str(row.get("video_id") or "").strip()
    if vid:
        return f"vid:{vid}"
    return f"title:{str(row.get('title') or '').strip().lower()[:120]}"


class TikTokPending:
    """Tiny CRUD over the pending table -- one row per unplaced Studio post."""

    @classmethod
    def replace_from_sync(cls, unmatched_rows: List[Dict[str, Any]], synced_at: str) -> int:
        """Sync results are authoritative: rows matched this run disappear,
        remaining/new unmatched rows replace the stored set (deduped)."""
        import uuid

        seen: Dict[str, Dict[str, Any]] = {}
        with _TABLE.mutate() as rows:
            for row in unmatched_rows:
                key = _identity(row)
                seen[key] = row
            # keep rows from other sources? No -- each sync re-scrapes the
            # whole visible table, so the new unmatched set IS the full set.
            rows.clear()
            for row in seen.values():
                rows.append({
                    "id": uuid.uuid4().hex,
                    "saved_at": synced_at,
                    "title": str(row.get("title") or "")[:200],
                    "posted_text": str(row.get("posted_text") or ""),
                    "video_id": row.get("video_id"),
                    "video_url": row.get("video_url"),
                    "views": row.get("views"),
                    "likes": row.get("likes"),
                    "comments": row.get("comments"),
                    "shares": row.get("shares"),
                })
            return len(rows)

    @classmethod
    def list_rows(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def get(cls, row_id: str) -> Dict[str, Any]:
        for row in _TABLE.load():
            if row.get("id") == row_id:
                return row
        raise ValueError(f"ไม่พบแถวค้าง id '{row_id}'")

    @classmethod
    def remove(cls, row_id: str) -> None:
        with _TABLE.mutate() as rows:
            rows[:] = [r for r in rows if r.get("id") != row_id]

    @classmethod
    def remove_video_ids(cls, video_ids: List[str]) -> None:
        """Rows the sync just matched successfully must not linger."""
        vids = {str(v) for v in video_ids if v}
        if not vids:
            return
        with _TABLE.mutate() as rows:
            rows[:] = [r for r in rows if str(r.get("video_id") or "") not in vids]
