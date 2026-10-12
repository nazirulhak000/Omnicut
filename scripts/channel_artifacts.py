"""Ownership index for generated companions that are not video exports."""
from pathlib import Path
import hashlib

from scripts import config
from scripts.db import DocumentTable
from scripts.channel_store import ChannelError


def _table():
    return DocumentTable("channel_artifacts", lambda: config.BASE_DIR / "_Docs/store.db",
                         lambda: config.BASE_DIR / "_Docs/channel_artifacts.json")


def _key(value):
    root = config.BASE_DIR.resolve()
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อ") from None
    if relative.split("/")[0] not in {"03_Projects", "04_Exports", "05_Covers_Thumbnails"}:
        raise ChannelError(422, "channel_artifact_path_invalid", "ไฟล์นี้ไม่ใช่สื่อที่สร้างขึ้น")
    return relative.casefold(), relative


def owners(value):
    key, _ = _key(value)
    return [row["channel_id"] for row in _table().load() if row.get("path_key") == key]


def register(value, channel_id):
    key, relative = _key(value)
    with _table().mutate() as records:
        for row in records:
            if row.get("path_key") == key:
                if row["channel_id"] != channel_id:
                    raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อของช่อง")
                return dict(row)
        row = {"id": hashlib.sha256(key.encode()).hexdigest(), "channel_id": channel_id,
               "path_key": key, "path": relative}
        records.append(row)
        return dict(row)
