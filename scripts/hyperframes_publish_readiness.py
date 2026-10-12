"""Readiness is resolved from the real source domain, never a stale manifest flag."""
import json
from scripts.channel_store import ChannelError
from scripts.export_cover_bindings import ExportCoverBindingStore
from scripts.hyperframes_sources import source_review_status


def export_readiness(root, channel, record):
    name = record.get("project_name")
    if not name:
        return {"ready": True, "required": False}
    paths = ExportCoverBindingStore(root)
    manifest = paths._path(f"03_Projects/{name}/project.json")
    if not manifest.is_file():
        if name.split("/")[-1].startswith("HF_"):
            raise ChannelError(409, "hyperframes_publish_package_missing", "HyperFrames export manifest is missing")
        return {"ready": True, "required": False}
    try:
        project = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ChannelError(409, "hyperframes_publish_package_invalid", "Repair the export manifest before preparing") from error
    if project.get("engine") != "hyperframes":
        return {"ready": True, "required": False}
    if project.get("channel_id") != channel:
        raise ChannelError(404, "resource_not_found", "Export project is outside this channel")
    packages = [p for p in project.get("publish_package_refs", []) if p.get("export_id") == record.get("id")]
    if len(packages) != 1:
        raise ChannelError(409, "hyperframes_publish_package_missing", "Exact export package is missing or ambiguous")
    package = packages[0]
    binding = package.get("source_binding") or project.get("source_binding") or {}
    if binding.get("type") not in {"product_angle", "standalone", "gadget_project"}:
        raise ChannelError(409, "hyperframes_source_invalid", "Export source is missing")
    if package.get("channel_id") not in (None, channel) or (project.get("source_binding") and project["source_binding"] != binding):
        raise ChannelError(409, "hyperframes_publish_package_invalid", "Export source identity changed")
    if package.get("video_sha256"):
        video = paths._path(record.get("path") or package.get("video_path"))
        if not video.is_file() or paths._digest(video) != package["video_sha256"]:
            raise ChannelError(409, "hyperframes_export_changed", "Export bytes differ from the reviewed revision")
    elif binding["type"] != "product_angle":
        raise ChannelError(409, "hyperframes_publish_package_invalid", "Reviewed export hash is missing")
    return {**source_review_status(root, channel, binding, record["id"]), "engine": "hyperframes",
            "source_binding": binding, "source_artifact_id": package.get("source_artifact_id"), "video_sha256": package.get("video_sha256")}


def require_export_ready(root, channel, record):
    result = export_readiness(root, channel, record)
    if not result["ready"]:
        raise ChannelError(409, "hyperframes_source_review_required", "Approve this exact candidate in Gadget Review before scheduling or preparing it", project_id=result.get("project_id"), artifact_id=result.get("artifact_id"))
    return result
