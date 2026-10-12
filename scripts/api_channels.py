"""Channel registry API (multi-channel P1).

All routes are ``global`` with ``ignore_scope_header`` in
``scripts/channel_route_policy.json``: the registry must stay reachable even
when a client holds a stale/unknown channel id.  There is deliberately no
delete endpoint (archive instead).  Errors use the project shape
``{"detail": <Thai message>, "code": <machine code>, ...}``.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body

from scripts import config
from scripts.channel_store import ChannelError, get_default_store

router = APIRouter(prefix="/api/channels", tags=["channels"])


def _require_object(payload: Any, *, allow_none: bool = False) -> dict[str, Any]:
    if payload is None and allow_none:
        return {}
    if not isinstance(payload, dict):
        raise ChannelError(422, "payload_invalid", "ข้อมูลที่ส่งมาต้องเป็น JSON object")
    return payload


def _only_expected_revision(payload: dict[str, Any]) -> Any:
    extra = set(payload) - {"expected_revision"}
    if extra:
        name = sorted(extra)[0]
        raise ChannelError(422, "field_not_editable", f"คำสั่งนี้ไม่รับฟิลด์ {name}", field=name)
    return payload.get("expected_revision")


@router.get("")
def list_channels(include_archived: bool = True) -> dict[str, Any]:
    store = get_default_store()
    doc = store.load()
    channels = [c for c in doc["channels"] if include_archived or c.get("status") != "archived"]
    return {
        "channels": channels,
        "revision": doc["revision"],
        "schema_version": doc["schema_version"],
        "default_channel_id": config.DEFAULT_CHANNEL_ID,
        "strict_mode": config.is_multi_channel_strict(),
        "registry_exists": store.exists(),
    }


@router.get("/{channel_id}")
def get_channel(channel_id: str) -> dict[str, Any]:
    store = get_default_store()
    return {"channel": store.get(channel_id), "registry_revision": store.revision()}


@router.post("", status_code=201)
def create_channel(payload: Any = Body(...)) -> dict[str, Any]:
    data = dict(_require_object(payload))
    expected = data.pop("expected_registry_revision", None)
    channel = get_default_store().create(data, expected_registry_revision=expected)
    return {"channel": channel}


@router.patch("/{channel_id}")
def update_channel(channel_id: str, payload: Any = Body(...)) -> dict[str, Any]:
    data = dict(_require_object(payload))
    expected = data.pop("expected_revision", None)
    channel = get_default_store().update(channel_id, data, expected_revision=expected)
    return {"channel": channel}


@router.post("/{channel_id}/activate")
def activate_channel(channel_id: str, payload: Optional[Any] = Body(None)) -> dict[str, Any]:
    expected = _only_expected_revision(_require_object(payload, allow_none=True))
    return {"channel": get_default_store().activate(channel_id, expected_revision=expected)}


@router.post("/{channel_id}/archive")
def archive_channel(channel_id: str, payload: Optional[Any] = Body(None)) -> dict[str, Any]:
    expected = _only_expected_revision(_require_object(payload, allow_none=True))
    return {"channel": get_default_store().archive(channel_id, expected_revision=expected)}


@router.get("/{channel_id}/readiness")
def get_channel_readiness(channel_id: str) -> dict[str, Any]:
    store = get_default_store()
    channel = store.get(channel_id)
    issues = store.readiness(channel_id)
    posting = store.posting_issues(channel_id)
    return {
        "channel_id": channel["id"],
        "status": channel["status"],
        "revision": channel["revision"],
        "identity_hash": channel["identity_hash"],
        "ready": not issues,
        "issues": [issue.to_dict() for issue in issues],
        "posting_ready": not posting,
        "posting_issues": [issue.to_dict() for issue in posting],
    }
