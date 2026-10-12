"""Explicit workflow ownership boundaries shared by API handlers and jobs.

These helpers never infer ownership from the currently selected browser channel.
Store APIs may keep unscoped compatibility calls for maintenance; HTTP workflows
always pass the effective request channel, including implicit main.
"""
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import Depends, Request

from scripts import config
from scripts.channel_scope import ChannelScope, ensure_same_channel, get_channel_scope, require_writable
from scripts.channel_ownership import reject_foreign_body_channel
from scripts.channel_store import ChannelError


def api_store_kwargs(scope: ChannelScope) -> dict[str, str]:
    return {"channel_id": scope.channel_id}


async def get_workflow_scope(request: Request) -> ChannelScope:
    """Reject conflicting raw JSON owners even when a Pydantic model ignores extras."""
    scope = get_channel_scope(request)
    if "application/json" in request.headers.get("content-type", "").lower():
        try:
            payload = await request.json()
        except ValueError:
            payload = None  # FastAPI validates malformed JSON itself.
        reject_foreign_body_channel(payload, scope.channel_id)
    return scope


def get_writable_workflow_scope(scope: ChannelScope = Depends(get_workflow_scope)) -> ChannelScope:
    return require_writable(scope)


def require_record_owner(scope: ChannelScope, record: dict[str, Any] | None,
                         *, resource_label: str = "ข้อมูล") -> dict[str, Any]:
    if record is None:
        raise ChannelError(404, "channel_resource_not_found", f"ไม่พบ{resource_label}")
    ensure_same_channel(scope, record.get("channel_id"), resource_label=resource_label,
                        allow_legacy_main=not scope.strict)
    return record


def require_project_owner(scope: ChannelScope, project_name: str,
                          *, writable: bool = False) -> dict[str, Any]:
    """Guard before any project load/save/artifact operation, including compat.

    Parent products, when present, must belong to the same scope too. A manifest
    without an owner is only a legacy-main resource with strict mode disabled.
    """
    from scripts.project_manifest import ProjectManifest
    from scripts.product_store import ProductStore

    if writable:
        require_writable(scope)
    try:
        manifest = ProjectManifest.load(project_name)
    except ValueError:
        raise ChannelError(404, "channel_resource_not_found", "ไม่พบโปรเจกต์") from None
    require_record_owner(scope, manifest, resource_label="โปรเจกต์")
    product_id = (manifest.get("product_id") or (manifest.get("product") or {}).get("id")
                  or (manifest.get("render_params") or {}).get("product_id"))
    if product_id:
        parent = ProductStore.get(product_id, **api_store_kwargs(scope))
        require_record_owner(scope, parent, resource_label="สินค้าเจ้าของโปรเจกต์")
    return manifest


def capture_job_scope(scope: ChannelScope) -> dict[str, Any]:
    """Capture JSON-safe provenance once; workers persist this copy, never re-read UI.

    Returning a deep copy prevents registry or caller data changes from altering
    an already-created job. Jobs must preserve these fields on status updates.
    """
    from scripts.channel_identity import project_channel_identity
    channel = deepcopy(scope.channel)
    identity = project_channel_identity(channel, scope.channel_id)
    return {
        "channel_id": scope.channel_id,
        "channel_scope_source": scope.source,
        "channel_scope_strict": scope.strict,
        "channel_status": channel.get("status"),
        "channel_revision": int(channel.get("revision", 0)),
        "channel_identity_hash": channel.get("identity_hash", ""),
        "channel_identity_snapshot": identity,
    }


def owner_path_component(scope: ChannelScope) -> str:
    """Legacy main stays flat; new channel artifacts use their own directory."""
    return "" if scope.channel_id == config.DEFAULT_CHANNEL_ID else scope.channel_id


def require_media_owner(scope: ChannelScope, value: str | Path, *, allow_shared: bool = True,
                        base_dir: Path | None = None, legacy_roots: tuple[Path, ...] = ()) -> Path:
    """Guard generated artifacts before serving, processing, renaming or deleting.

    Raw/source bytes and reusable assets are shared; their attachment/work-item
    metadata still has its own ownership checks. Unregistered generated files
    remain usable only by legacy main with strict mode disabled.
    """
    from scripts.export_registry import ExportRegistry
    from scripts.project_manifest import ProjectManifest

    root = (base_dir or config.BASE_DIR).resolve()
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    packaged_assets = (config.SOURCE_ROOT / "02_Assets").resolve()
    if allow_shared and packaged_assets in path.parents:
        return path
    # CapCut's configured draft directory can live outside the workspace. It
    # is a legacy-main source, never a shared escape for another channel.
    if any(Path(folder).resolve() in path.parents for folder in legacy_roots):
        known_owners = [owner for _, owner in ExportRegistry.path_owners(path)]
        if known_owners:
            for owner in known_owners:
                ensure_same_channel(scope, owner, resource_label="ไฟล์สื่อ", allow_legacy_main=not scope.strict)
            return path
        if scope.channel_id == config.DEFAULT_CHANNEL_ID and not scope.strict:
            return path
        raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อของช่อง")
    if root not in path.parents:
        raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อ")
    relative = path.relative_to(root)
    family = relative.parts[0]
    if family in {"00_Inbox", "01_Raw", "02_Assets", "assets"}:
        if allow_shared:
            return path
        raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อของช่อง")
    if family in {"03_Projects", "04_Exports", "05_Covers_Thumbnails"}:
        from scripts.channel_artifacts import owners as artifact_owners
        indexed_owners = artifact_owners(relative)
        if indexed_owners:
            for owner in indexed_owners:
                ensure_same_channel(scope, owner, resource_label="ไฟล์สื่อ", allow_legacy_main=False)
            return path
    if family == "03_Projects":
        for parent in (path.parent, *path.parents):
            if parent == root / "03_Projects":
                break
            if (parent / "project.json").is_file():
                project_name = parent.relative_to(root / "03_Projects").as_posix()
                require_project_owner(scope, project_name)
                return path
    owners = ExportRegistry.path_owners(path)
    if owners:
        for _, owner in owners:
            ensure_same_channel(scope, owner, resource_label="ไฟล์สื่อ", allow_legacy_main=not scope.strict)
        return path
    if family == "05_Covers_Thumbnails":
        from scripts.product_store import ProductStore
        # Internal ownership oracle, like ExportRegistry.path_owners: metadata
        # is used only to refuse a foreign flat legacy path, never returned.
        cover_owners = []
        for product in ProductStore._load():
            for angle in product.get("angles") or []:
                for key in ("cover_path", "cover_9x16_path", "cover_3x4_path"):
                    candidate = angle.get(key)
                    if candidate and (root / candidate).resolve() == path:
                        cover_owners.append(angle.get("channel_id", product.get("channel_id")))
        if cover_owners:
            for owner in cover_owners:
                ensure_same_channel(scope, owner, resource_label="ปกคลิป", allow_legacy_main=not scope.strict)
            return path
    legacy_posted = relative.parts[:2] == ("06_Archive", "Posted")
    if family in {"03_Projects", "04_Exports", "05_Covers_Thumbnails"} or legacy_posted:
        if scope.channel_id == config.DEFAULT_CHANNEL_ID and not scope.strict:
            # A nested directory for a different channel is never legacy main.
            from scripts.channel_store import get_default_store
            for directory in relative.parts[1:-1]:
                if directory in {"Ready_to_post", "Posted", config.DEFAULT_CHANNEL_ID}:
                    continue
                if get_default_store().find(directory) is not None:
                    raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อ")
            return path
    raise ChannelError(404, "channel_resource_not_found", "ไม่พบไฟล์สื่อของช่อง")
