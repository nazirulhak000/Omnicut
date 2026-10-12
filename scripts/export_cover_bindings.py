"""Explicit cover selections belong to one immutable export identity."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts.channel_scope import ChannelError
from scripts.db import DocumentTable


class ExportCoverBindingStore:
    def __init__(self, root, *, clock=time.time):
        self.root = Path(root).resolve()
        self.clock = clock
        self.table = DocumentTable("export_cover_bindings", lambda: self.root / "_Docs/store.db",
                                   lambda: self.root / "_Docs/export_cover_bindings.json")

    def _rows(self, name):
        """Read without creating a DB, table, mirror or importing legacy state."""
        database = self.root / "_Docs/store.db"
        if database.exists():
            from scripts.channel_migration import ro_connect
            with ro_connect(database) as connection:
                exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
                if exists:
                    return [json.loads(row[0]) for row in connection.execute(f"SELECT data FROM {name}")]
        mirror = self.root / f"_Docs/{name}.json"
        rows = json.loads(mirror.read_text(encoding="utf-8-sig")) if mirror.exists() else []
        if not isinstance(rows, list):
            raise ChannelError(409, "export_cover_records_invalid", "Cover records must be a list")
        return rows

    def _path(self, raw):
        if not isinstance(raw, (str, Path)) or not str(raw):
            raise ChannelError(422, "export_cover_path_invalid", "An exact managed path is required")
        candidate = Path(raw)
        candidate = candidate if candidate.is_absolute() else self.root / candidate
        if ".." in candidate.parts or not candidate.is_relative_to(self.root):
            raise ChannelError(422, "export_cover_path_invalid", "Path is outside this workspace")
        for part in (candidate, *candidate.parents):
            if part == self.root:
                break
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise ChannelError(422, "export_cover_path_invalid", "Filesystem aliases are not allowed")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise ChannelError(422, "export_cover_path_invalid", "Path is outside this workspace")
        return resolved

    def validate_export(self, channel_id, export_id, video_path, *, registry=None):
        if not channel_id or not export_id:
            raise ChannelError(422, "export_cover_identity_missing", "Channel and export identity are required")
        row = registry.lookup(export_id=export_id, channel_id=channel_id) if registry else next(
            (r for r in self._rows("export_registry") if r.get("id") == export_id and r.get("channel_id") == channel_id), None)
        if not row or row.get("channel_id") != channel_id:
            raise ChannelError(404, "resource_not_found", "Export is not in this channel")
        actual = self._path(video_path)
        if actual != self._path(row.get("path")) or not actual.is_file():
            raise ChannelError(409, "export_cover_export_mismatch", "Selected video does not match the exact export")
        return deepcopy(row)

    def _binding(self, channel_id, export_id):
        matches = [r for r in self._rows("export_cover_bindings") if r.get("channel_id") == channel_id and r.get("export_id") == export_id]
        if len(matches) > 1:
            raise ChannelError(409, "export_cover_identity_conflict", "Cover selection is ambiguous")
        return matches[0] if matches else None

    def revision(self, channel_id, export_id):
        row = self._binding(channel_id, export_id)
        return row.get("revision", 0) if row else 0

    @staticmethod
    def _digest(path):
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _selection(self, channel_id, format, raw):
        if format not in {"9:16", "3:4"}:
            raise ChannelError(422, "export_cover_format_invalid", "Unsupported cover format")
        path = self._path(raw)
        relative = path.relative_to(self.root)
        if relative.parts[:2] != ("05_Covers_Thumbnails", channel_id) or len(relative.parts) < 3 or not path.is_file():
            raise ChannelError(422, "export_cover_path_invalid", "Cover must be a real file in this channel's cover directory")
        return {"path": relative.as_posix(), "sha256": self._digest(path), "format": format}

    def get(self, channel_id, export_id, *, format="9:16"):
        row = self._binding(channel_id, export_id)
        if row is None:
            return None
        selections = row.get("selections")
        if not isinstance(selections, dict):
            raise ChannelError(409, "export_cover_selection_invalid", "Explicit cover selection record is malformed")
        if format not in selections:
            return None
        selection = selections[format]
        if not isinstance(row.get("revision"), int) or isinstance(row["revision"], bool) or row["revision"] < 1:
            raise ChannelError(409, "export_cover_selection_invalid", "Explicit cover selection revision is malformed")
        try:
            verified = self._selection(channel_id, format, selection["path"])
        except (ChannelError, OSError, KeyError, TypeError) as error:
            raise ChannelError(409, "export_cover_selection_invalid", "Explicit selected cover is missing or unmanaged; choose and save a new cover") from error
        if verified != selection:
            raise ChannelError(409, "export_cover_selection_changed", "Explicit selected cover bytes changed; choose and save a new cover")
        return {**verified, "export_id": export_id, "channel_id": channel_id, "revision": row["revision"]}

    def save(self, channel_id, export_id, video_path, selections, *, expected_revision=None):
        export = self.validate_export(channel_id, export_id, video_path)
        if not isinstance(selections, dict) or not selections:
            raise ChannelError(422, "export_cover_selection_missing", "Rendered cover selection is required")
        verified = {format: self._selection(channel_id, format, raw) for format, raw in selections.items()}
        with self.table.scoped_mutate(channel_id) as rows:
            matches = [r for r in rows if r.get("export_id") == export_id]
            if len(matches) > 1:
                raise ChannelError(409, "export_cover_identity_conflict", "Cover selection is ambiguous")
            current = matches[0] if matches else None
            merged = {**((current or {}).get("selections") or {}), **verified}
            if current and current.get("selections") == merged:
                return deepcopy(current)
            revision = current.get("revision", 0) if current else 0
            if expected_revision is not None and revision != expected_revision:
                raise ChannelError(409, "export_cover_revision_conflict", "A newer explicit cover selection was saved; reload before saving")
            result = {"id": "cover_" + sha256(f"{channel_id}\0{export_id}".encode()).hexdigest(),
                      "channel_id": channel_id, "export_id": export_id, "video_path": export["path"],
                      "selections": merged, "revision": revision + 1, "updated_at": self.clock()}
            if current:
                current.clear()
                current.update(result)
            else:
                rows.append(result)
            return deepcopy(result)
