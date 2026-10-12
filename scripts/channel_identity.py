"""Frozen visual identity shared by Canvas, ASS and HyperFrames.

Capture from the registry once at job creation. Renderers consume this JSON
snapshot and never look up a live channel profile. Layout stays owned by each
renderer; this module changes content only.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts import config
from scripts.channel_store import ChannelError, MAIN_SEED, avatar_identity, is_valid_channel_id, normalize_text_field, normalize_avatar_path, normalize_handle

VISUAL_FIELDS = ("display_name", "handle", "watermark_text", "follow_title", "avatar_asset_path")
SNAPSHOT_VERSION = 1
DEFAULT_MAIN_PROFILE = MAIN_SEED


def project_channel_identity(channel: dict, channel_id: str | None = None) -> dict:
    """Project a registry row into a JSON snapshot, including pinned avatar hash."""
    if not isinstance(channel, dict):
        raise ChannelError(422, "channel_identity_invalid", "identity ของช่องไม่ถูกต้อง")
    owner = channel_id or channel.get("channel_id") or channel.get("id")
    if not is_valid_channel_id(owner):
        raise ChannelError(422, "channel_identity_invalid", "ช่องของ identity ไม่ถูกต้อง")
    for key in ("id", "channel_id"):
        if channel.get(key) is not None and channel[key] != owner:
            raise ChannelError(422, "channel_scope_conflict", "identity ไม่ตรงกับช่องของงาน")
    result = {"schema_version": SNAPSHOT_VERSION, "id": owner, "channel_id": owner,
              "revision": int(channel.get("channel_revision", channel.get("revision", 0))),
              "channel_revision": int(channel.get("channel_revision", channel.get("revision", 0)))}
    for field in VISUAL_FIELDS:
        value = channel.get(field) or ""
        if not isinstance(value, str):
            raise ChannelError(422, "channel_identity_invalid", "ข้อความ identity ไม่ถูกต้อง")
        if field == "avatar_asset_path":
            canonical = normalize_avatar_path(value, project_root=config.BASE_DIR)
        elif field == "handle":
            canonical = normalize_handle(value) if value else ""
        else:
            canonical = normalize_text_field(field, value)
        if canonical != value:
            raise ChannelError(422, "channel_identity_invalid", "snapshot ต้องใช้ identity ที่ผ่านการ validate แล้ว")
        result[field] = value
    result["avatar_sha256"] = channel.get("avatar_sha256") if "avatar_sha256" in channel else avatar_identity(result["avatar_asset_path"], project_root=config.BASE_DIR)["sha256"]
    result["identity_hash"] = channel.get("identity_hash") or identity_fingerprint(result)
    if "presentation" in channel:
        result["presentation"] = deepcopy(channel["presentation"])
    return deepcopy(result)


def resolve_channel_identity(snapshot: dict | None, *, channel_id: str | None = None) -> dict:
    """Read old full snapshots; only an ownerless main clip gets legacy defaults."""
    if snapshot is not None and not isinstance(snapshot, dict):
        raise ChannelError(422, "channel_identity_invalid", "identity snapshot ไม่ถูกต้อง")
    owner = channel_id or (snapshot or {}).get("channel_id") or (snapshot or {}).get("id") or "main"
    if snapshot is None:
        if owner != "main":
            raise ChannelError(422, "channel_identity_missing", "งานช่องรองต้องมี identity snapshot")
        snapshot = DEFAULT_MAIN_PROFILE
    return project_channel_identity(snapshot, owner)


def identity_fingerprint(snapshot: dict | None) -> str:
    """Only visible content/owner invalidates caches; lifecycle edits do not."""
    snapshot = snapshot or DEFAULT_MAIN_PROFILE
    payload = {field: snapshot.get(field) or "" for field in VISUAL_FIELDS}
    payload.update(channel_id=snapshot.get("channel_id") or snapshot.get("id") or "main",
                   avatar_sha256=snapshot.get("avatar_sha256"))
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def require_identity_avatar(snapshot: dict, *, allow_legacy_missing: bool = False) -> Path | None:
    """A changed/missing avatar cannot silently change a frozen clip's identity."""
    value = snapshot.get("avatar_asset_path") or ""
    actual = avatar_identity(value, project_root=config.BASE_DIR)
    expected = snapshot.get("avatar_sha256")
    if expected and actual["sha256"] != expected:
        raise ChannelError(409, "channel_identity_asset_changed", "รูปโปรไฟล์ของ snapshot เปลี่ยนหรือหายไป")
    if not actual["sha256"]:
        if allow_legacy_missing and snapshot.get("channel_id", snapshot.get("id")) == "main":
            return None
        raise ChannelError(422, "channel_identity_avatar_missing", "ไม่พบรูปโปรไฟล์ของ snapshot")
    return config.BASE_DIR / actual["path"]
