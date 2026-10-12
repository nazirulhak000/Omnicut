"""Canonical HyperFrames business manifests; runtime compositions live separately.

All IO is scoped to an explicit workspace root. No global store is constructed.
The manifest is compatible with ProjectManifest discovery without pretending to
contain an NLE timeline. External executors never choose owner or parent IDs.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from scripts.channel_identity import resolve_channel_identity
from scripts.channel_store import is_valid_channel_id
from scripts.project_manifest import project_revision


class HyperFramesProjectError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code, self.status_code = code, status_code


def _now():
    return datetime.now(timezone.utc).isoformat()


class HyperFramesProjects:
    MUTABLE = frozenset({"inputs", "status", "composition_revisions", "accepted_revision",
                         "authoring_job_id", "render_job_id", "render_artifact",
                         "publish_package", "publish_package_refs", "readiness", "overlay_contract"})
    STATUSES = frozenset({"draft", "blocked", "authoring", "preview_ready", "render_queued",
                          "rendering", "render_failed", "rendered", "exported", "cancelled"})

    def __init__(self, root: Path, *, product_store=None, sources=None):
        self.root = Path(root).resolve()
        self.projects_dir = self.root / "03_Projects"
        self.product_store = product_store
        from scripts.hyperframes_sources import HyperFramesSources
        self.sources = sources or HyperFramesSources(self.root)
        if Path(self.sources.root).resolve() != self.root:
            raise HyperFramesProjectError("source_root_conflict", "Source adapter must share the project root")

    def _path(self, project_id, channel_id):
        if not is_valid_channel_id(channel_id):
            raise HyperFramesProjectError("channel_invalid", "Invalid channel ID")
        if not isinstance(project_id, str) or not re.fullmatch(r"[0-9a-f]{32}", project_id):
            raise HyperFramesProjectError("project_id_invalid", "Invalid HyperFrames project ID")
        path = self.projects_dir / channel_id / f"HF_{project_id}" / "project.json"
        if self.root not in path.resolve().parents:
            raise HyperFramesProjectError("project_path_invalid", "Project escapes workspace")
        for parent in (self.projects_dir, path.parent.parent, path.parent, path):
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise HyperFramesProjectError("project_path_invalid", "Managed project cannot use symlinks or junctions")
        return path

    def directory(self, project_id, channel_id):
        return self._path(project_id, channel_id).parent

    def _validate_source(self, binding, channel_id, allow_standalone=False):
        if not isinstance(binding, dict):
            raise HyperFramesProjectError("source_binding_invalid", "Source binding must be an object")
        kind = binding.get("type")
        if kind == "gadget_project":
            return self.sources.validate(channel_id, binding)
        if kind == "standalone":
            if not allow_standalone or set(binding) != {"type"}:
                raise HyperFramesProjectError("standalone_disabled", "Standalone is not enabled for this operation")
            return deepcopy(binding)
        if kind != "product_angle" or set(binding) != {"type", "product_id", "angle_id"}:
            raise HyperFramesProjectError("source_binding_invalid", "MVP requires a product_angle source")
        if not all(isinstance(binding[k], str) and binding[k].strip() for k in ("product_id", "angle_id")):
            raise HyperFramesProjectError("source_binding_invalid", "Parent IDs are required")
        store = self.product_store
        if store is None:
            from scripts.config import BASE_DIR
            if self.root != Path(BASE_DIR).resolve():
                raise HyperFramesProjectError("source_store_required", "A scoped source store is required outside the configured workspace")
            from scripts.product_store import ProductStore
            # ProductStore.get() reconciles and can write. This read path must not.
            rows = ProductStore._scoped_load(ProductStore._scope(channel_id, False))
            product = next((row for row in rows if row.get("id") == binding["product_id"]), None)
        else:
            product = store.get(binding["product_id"], channel_id=channel_id)
        if not product or product.get("channel_id") != channel_id:
            raise HyperFramesProjectError("source_not_found", "Product is not owned by this channel", 404)
        if sum((angle.get("angle_id") or angle.get("id")) == binding["angle_id"] for angle in product.get("angles", [])) != 1:
            raise HyperFramesProjectError("source_not_found", "Angle does not belong to the product", 404)
        return deepcopy(binding)

    @staticmethod
    def _inputs(value):
        if not isinstance(value, dict):
            raise HyperFramesProjectError("inputs_invalid", "Inputs must be an object")
        value = deepcopy(value)
        for field, limit in (("title", 200), ("description", 8000), ("caption", 4000), ("tiktok_product_id", 200)):
            if field in value and (not isinstance(value[field], str) or len(value[field]) > limit):
                raise HyperFramesProjectError("inputs_invalid", f"{field} must be text with at most {limit} characters")
        if "hashtags" in value and (not isinstance(value["hashtags"], list) or len(value["hashtags"]) > 100
                or not all(isinstance(item, str) and len(item) <= 100 for item in value["hashtags"])):
            raise HyperFramesProjectError("inputs_invalid", "Hashtags must be a bounded list of text")
        value.setdefault("audio_mode", "narration")
        if value["audio_mode"] not in {"narration", "music_only", "silent"}:
            raise HyperFramesProjectError("audio_mode_invalid", "Unsupported audio mode")
        for field in ("duration_seconds", "total_duration"):
            if field in value and (isinstance(value[field], bool) or not isinstance(value[field], (int, float))
                                   or not 0 < value[field] < 3600):
                raise HyperFramesProjectError("duration_invalid", "Duration must be positive and finite")
        return value

    @contextmanager
    def _lock(self, path):
        for parent in (path.parent, *path.parent.parents):
            if parent == self.root:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise HyperFramesProjectError("project_path_invalid", "Managed locks cannot use path aliases")
        path.parent.mkdir(parents=True, exist_ok=True)
        with (path.parent / ".hyperframes.lock").open("a+b") as handle:
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _write(self, path, manifest):
        from scripts.maintenance_lock import is_blocked
        if is_blocked(self.root):
            raise HyperFramesProjectError("maintenance_locked", "Workspace is in maintenance", 503)
        manifest["project_revision"] = project_revision({k: v for k, v in manifest.items() if k != "project_revision"})
        temporary = path.with_name(f".project-{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return deepcopy(manifest)

    def create(self, channel_id, source_binding, channel_identity, inputs=None, *, allow_standalone=False):
        project_id = uuid.uuid4().hex
        path = self._path(project_id, channel_id)
        binding = self._validate_source(source_binding, channel_id, allow_standalone)
        identity = resolve_channel_identity(channel_identity, channel_id=channel_id)
        manifest = {"version": 1, "schema_version": 1, "engine": "hyperframes",
                    "project_id": project_id, "project_name": f"{channel_id}/HF_{project_id}",
                    "channel_id": channel_id, "channel_identity": identity, "source_binding": binding,
                    "revision": 1, "brief_revision": 1, "inputs": self._inputs(inputs or {}),
                    "status": "draft", "composition_revisions": [], "accepted_revision": None,
                    "publish_package": None, "publish_package_refs": [], "artifacts": {},
                    "created_at": _now(), "updated_at": _now()}
        with self._lock(path):
            return self._write(path, manifest)

    def get(self, project_id, channel_id):
        path = self._path(project_id, channel_id)
        if not path.is_file():
            raise HyperFramesProjectError("project_not_found", "HyperFrames project not found", 404)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (manifest.get("engine") != "hyperframes" or manifest.get("schema_version") != 1
                or manifest.get("channel_id") != channel_id or manifest.get("project_id") != project_id
                or manifest.get("project_name") != f"{channel_id}/HF_{project_id}"):
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest identity or schema mismatch")
        identity = manifest.get("channel_identity")
        if not isinstance(identity, dict) or identity.get("channel_id") != channel_id:
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest identity snapshot mismatch")
        resolve_channel_identity(identity, channel_id=channel_id)
        if (isinstance(manifest.get("revision"), bool) or not isinstance(manifest.get("revision"), int)
                or manifest["revision"] < 1 or not isinstance(manifest.get("brief_revision"), int)
                or manifest["brief_revision"] < 1):
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest revision is invalid")
        binding = manifest.get("source_binding")
        if not isinstance(binding, dict) or binding.get("type") not in {"product_angle", "standalone", "gadget_project"}:
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest source discriminator is invalid")
        if binding["type"] == "product_angle" and (set(binding) != {"type", "product_id", "angle_id"}
                or not all(isinstance(binding[k], str) and binding[k].strip() for k in ("product_id", "angle_id"))):
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest source binding is invalid")
        if binding["type"] == "standalone" and set(binding) != {"type"}:
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest standalone source is invalid")
        if binding["type"] == "gadget_project" and (set(binding) - {"type", "project_id", "campaign_id", "slot_id"}
                or not isinstance(binding.get("project_id"), str) or not binding["project_id"]
                or bool(binding.get("campaign_id")) != bool(binding.get("slot_id"))):
            raise HyperFramesProjectError("project_manifest_invalid", "Manifest Gadget source is invalid")
        return manifest

    def list(self, channel_id):
        # Validate scope even if directory is absent.
        self._path("0" * 32, channel_id)
        folder = self.projects_dir / channel_id
        return [self.get(path.parent.name[3:], channel_id) for path in sorted(folder.glob("HF_*/project.json"))]

    def update(self, project_id, channel_id, expected_revision, changes):
        if not isinstance(changes, dict) or set(changes) - self.MUTABLE:
            raise HyperFramesProjectError("project_fields_immutable", "Only managed mutable fields can change")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise HyperFramesProjectError("revision_required", "Expected revision is required", 409)
        path = self._path(project_id, channel_id)
        if not path.is_file():
            raise HyperFramesProjectError("project_not_found", "HyperFrames project not found", 404)
        with self._lock(path):
            manifest = self.get(project_id, channel_id)
            if manifest["revision"] != expected_revision:
                raise HyperFramesProjectError("revision_conflict", "Project revision changed", 409)
            changes = deepcopy(changes)
            if "inputs" in changes:
                if manifest.get("overlay_contract"):
                    raise HyperFramesProjectError("overlay_inputs_immutable", "Create a new overlay project to change approved-master inputs", 409)
                if changes.get("accepted_revision") is not None or changes.get("status", "draft") != "draft":
                    raise HyperFramesProjectError("revision_conflict", "New inputs must be accepted in a separate operation", 409)
                changes["inputs"] = self._inputs(changes["inputs"])
                manifest["brief_revision"] += 1
                # Old approval remains in revision history, but cannot approve new inputs.
                manifest["accepted_revision"] = None
                manifest["status"] = "draft"
            if "status" in changes and changes["status"] not in self.STATUSES:
                raise HyperFramesProjectError("status_invalid", "Unsupported project status")
            for field in ("composition_revisions", "publish_package_refs"):
                if field in changes and not isinstance(changes[field], list):
                    raise HyperFramesProjectError("project_fields_invalid", f"{field} must be a list")
            manifest.update(changes)
            manifest["revision"] += 1
            manifest["updated_at"] = _now()
            return self._write(path, manifest)
