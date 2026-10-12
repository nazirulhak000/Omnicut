"""Pending TikTok Studio rows that auto-matching could not place.

Rows the extension scraped but neither an existing post nor a clip
candidate matched go here instead of vanishing when the side panel
closes. The Performance tab lists them so the user can attach each row
to the right library clip by hand (see api_tiktok_stats.attach).

Same storage contract as PostLog: SQLite document table in store.db,
mirrored to a plain JSON file next to post_log.json.
"""

from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts.db import DocumentTable
from scripts.channel_ownership import resolve_store_scope, owner_for_new_record

PENDING_PATH = BASE_DIR / "_Docs" / "tiktok_pending.json"
IGNORED_PATH = BASE_DIR / "_Docs" / "tiktok_ignored.json"


def _pending_db_path():
    return BASE_DIR / "_Docs" / "store.db"


def _pending_json_path():
    return PENDING_PATH


def _ignored_db_path():
    return BASE_DIR / "_Docs" / "store.db"


def _ignored_json_path():
    return IGNORED_PATH


_TABLE = DocumentTable("tiktok_pending", _pending_db_path, _pending_json_path)
_IGNORED_TABLE = DocumentTable("tiktok_ignored", _ignored_db_path, _ignored_json_path)


def _identity(row: Dict[str, Any]) -> str:
    vid = str(row.get("video_id") or "").strip()
    if vid:
        return f"vid:{vid}"
    return f"title:{str(row.get('title') or '').strip().lower()[:120]}"


def _load(table, channel_id):
    scope = resolve_store_scope(channel_id)
    return table.load() if scope.unscoped else table.scoped_load(scope.channel_id, include_legacy=scope.include_legacy)


def _mutate(table, channel_id):
    scope = resolve_store_scope(channel_id)
    return table.mutate() if scope.unscoped else table.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy)


def _owner(channel_id):
    return owner_for_new_record(resolve_store_scope(channel_id))


class TikTokIgnored:
    """Clips the user explicitly skipped/ignored -- never re-appear in pending rows on future syncs."""

    @classmethod
    def add(cls, row: Dict[str, Any], *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        import uuid
        from datetime import datetime

        key = _identity(row)
        with _mutate(_IGNORED_TABLE, channel_id) as rows:
            for r in rows:
                if r.get("identity") == key or _identity(r) == key:
                    return r
            entry = {
                "id": uuid.uuid4().hex,
                "channel_id": _owner(channel_id),
                "identity": key,
                "ignored_at": datetime.now().isoformat(timespec="seconds"),
                "title": str(row.get("title") or "")[:200],
                "posted_text": str(row.get("posted_text") or ""),
                "video_id": row.get("video_id"),
                "video_url": row.get("video_url"),
                "views": row.get("views"),
                "likes": row.get("likes"),
                "comments": row.get("comments"),
                "shares": row.get("shares"),
                "account_unverified": row.get("account_unverified", False),
                "source_account": row.get("source_account"),
            }
            rows.append(entry)
            return entry

    @classmethod
    def is_ignored(cls, row: Dict[str, Any], *, channel_id: Optional[str] = None) -> bool:
        key = _identity(row)
        vid = str(row.get("video_id") or "").strip()
        for r in _load(_IGNORED_TABLE, channel_id):
            if r.get("identity") == key or _identity(r) == key:
                return True
            if vid and str(r.get("video_id") or "").strip() == vid:
                return True
        return False

    @classmethod
    def list_rows(cls, *, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return _load(_IGNORED_TABLE, channel_id)

    @classmethod
    def get(cls, ignored_id: str, *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        for row in _load(_IGNORED_TABLE, channel_id):
            if row.get("id") == ignored_id:
                return row
        raise ValueError(f"ไม่พบรายการที่ข้าม id '{ignored_id}'")

    @classmethod
    def remove(cls, ignored_id: str, *, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        removed = None
        with _mutate(_IGNORED_TABLE, channel_id) as rows:
            for i, r in enumerate(rows):
                if r.get("id") == ignored_id:
                    removed = rows.pop(i)
                    break
        return removed

    @classmethod
    def clear(cls, *, channel_id: Optional[str] = None) -> None:
        with _mutate(_IGNORED_TABLE, channel_id) as rows:
            rows.clear()


class TikTokPending:
    """Tiny CRUD over the pending table -- one row per unplaced Studio post."""

    @classmethod
    def replace_from_sync(cls, unmatched_rows: List[Dict[str, Any]], synced_at: str, *, channel_id: Optional[str] = None) -> int:
        """Sync results are authoritative: rows matched this run disappear,
        remaining/new unmatched rows replace the stored set (deduped).
        Rows previously ignored by the user are permanently excluded."""
        import uuid

        seen: Dict[str, Dict[str, Any]] = {}
        ignored = {_identity(row) for row in TikTokIgnored.list_rows(channel_id=channel_id)}
        with _mutate(_TABLE, channel_id) as rows:
            for row in unmatched_rows:
                # Exclude any row that was explicitly skipped/ignored by the user
                if _identity(row) in ignored:
                    continue
                key = _identity(row)
                seen[key] = row
            rows.clear()
            for row in seen.values():
                rows.append({
                    "id": uuid.uuid4().hex,
                "channel_id": _owner(channel_id),
                    "saved_at": synced_at,
                    "title": str(row.get("title") or "")[:200],
                    "posted_text": str(row.get("posted_text") or ""),
                    "video_id": row.get("video_id"),
                    "video_url": row.get("video_url"),
                    "views": row.get("views"),
                    "likes": row.get("likes"),
                    "comments": row.get("comments"),
                    "shares": row.get("shares"),
                    "account_unverified": row.get("account_unverified", False),
                    "source_account": row.get("source_account"),
                })
            return len(rows)

    @classmethod
    def list_rows(cls, *, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return _load(_TABLE, channel_id)

    @classmethod
    def get(cls, row_id: str, *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        for row in _load(_TABLE, channel_id):
            if row.get("id") == row_id:
                return row
        raise ValueError(f"ไม่พบแถวค้าง id '{row_id}'")

    @classmethod
    def remove(cls, row_id: str, *, channel_id: Optional[str] = None) -> None:
        with _mutate(_TABLE, channel_id) as rows:
            rows[:] = [r for r in rows if r.get("id") != row_id]

    @classmethod
    def remove_video_ids(cls, video_ids: List[str], *, channel_id: Optional[str] = None) -> None:
        """Rows the sync just matched successfully must not linger."""
        vids = {str(v) for v in video_ids if v}
        if not vids:
            return
        with _mutate(_TABLE, channel_id) as rows:
            rows[:] = [r for r in rows if str(r.get("video_id") or "") not in vids]

    @classmethod
    def ignore(cls, row_id: str, *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """Record the pending row into TikTokIgnored and remove from TikTokPending."""
        row = cls.get(row_id, channel_id=channel_id)
        ignored_entry = TikTokIgnored.add(row, channel_id=channel_id)
        cls.remove(row_id, channel_id=channel_id)
        return ignored_entry

    @classmethod
    def ignore_all(cls, *, channel_id: Optional[str] = None) -> int:
        """Ignore all currently pending rows in one batch."""
        count = 0
        current_rows = cls.list_rows(channel_id=channel_id)
        for r in current_rows:
            TikTokIgnored.add(r, channel_id=channel_id)
            count += 1
        moved_ids = {row.get("id") for row in current_rows}
        with _mutate(_TABLE, channel_id) as rows:
            rows[:] = [row for row in rows if row.get("id") not in moved_ids]
        return count

    @classmethod
    def restore(cls, ignored_id: str, *, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """Restore a previously ignored item back into TikTokPending."""
        import uuid
        from datetime import datetime

        ignored_row = TikTokIgnored.get(ignored_id, channel_id=channel_id)
        if not ignored_row:
            raise ValueError(f"ไม่พบรายการที่ข้าม id '{ignored_id}'")
        with _mutate(_TABLE, channel_id) as rows:
            key = _identity(ignored_row)
            for r in rows:
                if _identity(r) == key:
                    restored = r
                    break
            else:
                restored = None
            if restored is None:
                entry = {
                    "id": uuid.uuid4().hex,
                    "channel_id": _owner(channel_id),
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "title": str(ignored_row.get("title") or "")[:200],
                    "posted_text": str(ignored_row.get("posted_text") or ""),
                    "video_id": ignored_row.get("video_id"),
                    "video_url": ignored_row.get("video_url"),
                    "views": ignored_row.get("views"),
                    "likes": ignored_row.get("likes"),
                    "comments": ignored_row.get("comments"),
                    "shares": ignored_row.get("shares"),
                    "account_unverified": ignored_row.get("account_unverified", False),
                    "source_account": ignored_row.get("source_account"),
                }
                rows.append(entry)
            else:
                entry = restored
        TikTokIgnored.remove(ignored_id, channel_id=channel_id)
        return entry

