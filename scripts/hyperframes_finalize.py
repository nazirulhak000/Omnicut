"""Recoverable HyperFrames publication-package commit, without publishing.

One durable render-job intent names one output and one registry identity.
Recovery repeats verified effects, never re-renders or changes a queued export.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import uuid

from PIL import Image

from scripts.channel_store import ChannelError
from scripts.hyperframes_project import HyperFramesProjects, HyperFramesProjectError
from scripts.hyperframes_render import HyperFramesRenderJobs


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def hyperframes_style_metadata(angle=None, inputs=None, duration=None):
    """Export style metadata for a HyperFrames clip from data already in hand.

    HyperFrames clips have no OmniCut project manifest, so this feeds the
    registry's ``style_metadata_from_manifest`` a manifest-shaped view of the
    source angle / render inputs: ``style_preset``, ``hook_style_id``,
    ``story_format`` (default ``classic``), the rendered ``duration`` and the
    hook line. Never raises; missing data simply yields fewer fields.
    """
    try:
        from scripts.export_registry import style_metadata_from_manifest
        angle = angle if isinstance(angle, dict) else {}
        inputs = inputs if isinstance(inputs, dict) else {}

        def pick(*keys):
            for source in (inputs, angle):
                for key in keys:
                    value = source.get(key)
                    if isinstance(value, str) and value.strip():
                        return value
            return None

        return style_metadata_from_manifest({
            "style_preset": pick("style_preset"),
            "hook_style_id": pick("hook_style_id"),
            "story_format": pick("story_format"),
            "total_duration": duration,
            "hook_text": pick("hook_text", "hook_headline", "hook"),
        })
    except Exception:
        return {}


class HyperFramesFinalizer:
    def __init__(self, root, *, jobs=None, projects=None, registry=None, product_store=None,
                 artifact_register=None, fault_hook=None, sources=None):
        self.root = Path(root).resolve()
        self.jobs = jobs or HyperFramesRenderJobs(self.root)
        self.projects = projects or HyperFramesProjects(self.root, product_store=product_store)
        self.registry = registry
        self.products = product_store
        from scripts.hyperframes_sources import HyperFramesSources
        self.sources = sources or HyperFramesSources(self.root)
        if Path(self.sources.root).resolve() != self.root:
            raise ChannelError(422, "hyperframes_source_root_conflict", "Source adapter must share the finalize root")
        self.artifact_register = artifact_register
        self.fault_hook = fault_hook or (lambda phase: None)

    def _path(self, value):
        if not isinstance(value, str) or not value:
            raise ChannelError(422, "hyperframes_path_invalid", "Artifact path is required")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ChannelError(422, "hyperframes_path_invalid", "Artifact path must be workspace relative")
        candidate = self.root / relative
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (candidate, *candidate.parents) if p != self.root and p.is_relative_to(self.root)):
            raise ChannelError(422, "hyperframes_path_invalid", "Artifact filesystem aliases are forbidden")
        path = candidate.resolve()
        if not path.is_relative_to(self.root):
            raise ChannelError(422, "hyperframes_path_invalid", "Artifact escapes workspace")
        return path

    def _defaults(self):
        from scripts.config import BASE_DIR
        if self.root != Path(BASE_DIR).resolve() and self.registry is None:
            raise ChannelError(422, "hyperframes_store_required", "Scoped adapters are required outside the configured workspace")
        if self.registry is None:
            from scripts.export_registry import ExportRegistry
            self.registry = ExportRegistry
        if self.products is None and self.root == Path(BASE_DIR).resolve():
            from scripts.product_store import ProductStore
            self.products = ProductStore
        if self.artifact_register is None and self.root == Path(BASE_DIR).resolve():
            from scripts.channel_artifacts import register
            self.artifact_register = register

    def _product_angle(self, channel, binding):
        if binding.get("type") != "product_angle":
            raise ChannelError(422, "hyperframes_source_unsupported", "Product lookup requires a product_angle source")
        if self.products is None:
            raise ChannelError(422, "hyperframes_store_required", "A scoped product adapter is required")
        if hasattr(self.products, "_scoped_load"):
            rows = self.products._scoped_load(self.products._scope(channel, False))
            product = next((p for p in rows if p.get("id") == binding["product_id"]), None)
        else:
            product = self.products.get(binding["product_id"], channel_id=channel)
        if not product or product.get("channel_id") != channel:
            raise ChannelError(404, "hyperframes_source_not_found", "Product is outside this channel")
        matches = [a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == binding["angle_id"]]
        if len(matches) != 1:
            raise ChannelError(409, "hyperframes_angle_ambiguous", "Angle is missing or ambiguous")
        return deepcopy(matches[0])

    @staticmethod
    def _product_facts(product):
        fields = ("id", "name", "product_code", "canonical_product_key", "description", "url", "specs", "pain_points", "selling_points", "price_note", "target_buyer", "metadata_source", "source_warning")
        return {key: deepcopy(product[key]) for key in fields if key in product}

    def _verify_product(self, channel, job, product=None):
        if job["source_binding"].get("type") != "product_angle":
            return
        baseline = job.get("source_product_snapshot")
        if baseline is None:  # Compatibility for jobs created before this contract.
            return
        if product is None:
            binding = job["source_binding"]
            if hasattr(self.products, "_scoped_load"):
                rows = self.products._scoped_load(self.products._scope(channel, False))
                product = next((p for p in rows if p.get("id") == binding["product_id"]), None)
            else:
                product = self.products.get(binding["product_id"], channel_id=channel)
        if not product or _fingerprint(baseline) != _fingerprint(self._product_facts(product)):
            raise ChannelError(409, "hyperframes_product_changed", "Product facts changed after render creation")

    def _package(self, project, supplied):
        if not isinstance(supplied, dict):
            raise ChannelError(422, "hyperframes_package_invalid", "Publish package is required")
        allowed = {"caption", "hashtags", "tiktok_product_id", "cover_path", "cover_sha256", "cover_format"}
        if set(supplied) - allowed:
            raise ChannelError(422, "hyperframes_package_invalid", "Unknown or client-owned package field")
        inputs = project.get("inputs") or {}
        caption = supplied.get("caption", inputs.get("caption", ""))
        hashtags = supplied.get("hashtags", inputs.get("hashtags", []))
        product_id = supplied.get("tiktok_product_id", inputs.get("tiktok_product_id", ""))
        if not isinstance(caption, str) or len(caption) > 4000 or not isinstance(hashtags, list) or not all(isinstance(v, str) for v in hashtags):
            raise ChannelError(422, "hyperframes_package_invalid", "Caption or hashtags are invalid")
        if not isinstance(product_id, str):
            raise ChannelError(422, "hyperframes_package_invalid", "TikTok product ID must be text")
        # The basket is a saved business input, not a creative executor decision.
        if product_id != (inputs.get("tiktok_product_id") or ""):
            raise ChannelError(409, "hyperframes_basket_changed", "Save the basket in project inputs before finalization")
        result = {"caption": caption, "hashtags": deepcopy(hashtags), "tiktok_product_id": product_id}
        if supplied.get("cover_path"):
            cover = self._path(supplied["cover_path"])
            relative = cover.relative_to(self.root).parts
            if not (relative[0] == "02_Assets" or (len(relative) > 2 and relative[0] in {"03_Projects", "05_Covers_Thumbnails"}
                    and relative[1] == project["channel_id"])):
                raise ChannelError(404, "hyperframes_cover_scope", "Cover is outside the channel or shared assets")
            self._image(cover)
            digest = _hash(cover)
            if supplied.get("cover_sha256") and supplied["cover_sha256"] != digest:
                raise ChannelError(409, "hyperframes_cover_changed", "Cover hash changed")
            result.update(cover_path=cover.relative_to(self.root).as_posix(), cover_sha256=digest,
                          cover_format=supplied.get("cover_format") or "9x16")
        return result

    @staticmethod
    def _image(path):
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, ValueError) as error:
            raise ChannelError(422, "hyperframes_thumbnail_invalid", "A real image artifact is required") from error

    def _verify_artifact(self, job, expected_hash, intent=None):
        artifact = job.get("artifact") or {}
        video = self._path(artifact.get("path"))
        if intent and not video.is_file():
            video = self._path(intent["video_path"])
        if not video.is_file() or _hash(video) != expected_hash or artifact.get("sha256") != expected_hash:
            raise ChannelError(409, "hyperframes_artifact_changed", "Reviewed video hash no longer matches")
        thumb = self._path(artifact.get("thumbnail_path"))
        if intent and not thumb.is_file():
            thumb = self._path(intent["thumbnail_path"])
        self._image(thumb)
        if not artifact.get("thumbnail_sha256") or _hash(thumb) != artifact["thumbnail_sha256"]:
            raise ChannelError(409, "hyperframes_thumbnail_changed", "Rendered thumbnail hash changed")
        return artifact

    def finalize(self, channel, job_id, expected_revision, artifact_hash, publish_package):
        self._defaults()
        job = self.jobs.get(channel, job_id)
        if job.get("finalize_intent"):
            intent = job["finalize_intent"]
            if artifact_hash != intent["artifact_hash"] or _fingerprint(publish_package) != intent["request_hash"]:
                raise ChannelError(409, "hyperframes_finalize_conflict", "Finalize request differs from the recorded approval")
            return self.resume(channel, job_id)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision != job["revision"] or job["status"] != "qc_ready":
            raise ChannelError(409, "hyperframes_review_stale", "Review the current QC-ready render before finalizing")
        artifact = self._verify_artifact(job, artifact_hash)
        project = self.projects.get(job["project_id"], channel)
        if project["revision"] != job["project_revision"]:
            raise ChannelError(409, "hyperframes_project_changed", "Project changed after the render input was frozen")
        package = self._package(project, publish_package)
        self._verify_product(channel, job)
        binding = job["source_binding"]
        angle = (self._product_angle(channel, binding) if binding["type"] == "product_angle"
                 else self.sources.packet(channel, project)["angle"])
        baseline = job.get("source_angle_snapshot")
        if baseline is None or _fingerprint(baseline) != _fingerprint(angle):
            raise ChannelError(409, "hyperframes_parent_changed", "Source Angle changed after render creation")
        if angle.get("project_name") not in (None, "", project["project_name"]):
            raise ChannelError(409, "hyperframes_parent_changed", "Angle now points to another project")
        suffix = uuid.uuid4().hex
        facts = job.get("source_product_snapshot") or {}
        product_label = str(facts.get("product_code") or facts.get("name") or binding.get("product_id") or binding.get("project_id") or "standalone")
        product_label = re.sub(r"[^\w-]+", "-", product_label, flags=re.UNICODE).strip("-_")[:60] or "product"
        hook_label = str(angle.get("hook_headline") or angle.get("title") or angle.get("angle_id") or angle.get("id") or "hf")
        hook_label = re.sub(r"[^\w-]+", "-", hook_label, flags=re.UNICODE).strip("-_")[:50] or "hf"
        basename = f"{datetime.now(timezone.utc):%Y%m%d}_{product_label}_{hook_label}-{suffix[:12]}_v{project['revision']}"
        intent = {"id": "hff_" + suffix, "phase": "prepared", "artifact_hash": artifact_hash,
                  "request_hash": _fingerprint(publish_package), "project_revision": project["revision"],
                  "angle_fingerprint": _fingerprint(angle), "package": package, "export_id": None,
                  "video_path": f"04_Exports/Ready_to_post/{channel}/{basename}.mp4",
                  "thumbnail_path": f"04_Exports/Ready_to_post/{channel}/{basename}{Path(artifact['thumbnail_path']).suffix.lower()}",
                  "approved_at": datetime.now(timezone.utc).isoformat()}
        if package.get("cover_path"):
            intent["cover_source"] = package["cover_path"]
            intent["cover_path"] = f"05_Covers_Thumbnails/{channel}/HF_{suffix}{Path(package['cover_path']).suffix.lower()}"
        def begin(row):
            if row["revision"] != expected_revision or row["status"] != "qc_ready" or row.get("finalize_intent"):
                raise ChannelError(409, "hyperframes_review_stale", "Render changed before the finalize intent was saved")
            row.update(finalize_intent=deepcopy(intent), status="finalizing", phase="finalizing")
        self.jobs._change(channel, job_id, begin)
        self.fault_hook("intent")
        return self.resume(channel, job_id)

    def _promote(self, source, target, digest):
        if target.exists():
            if _hash(target) != digest:
                raise ChannelError(409, "hyperframes_output_conflict", "Final path contains different content")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}-{uuid.uuid4().hex}.tmp")
        try:
            shutil.copyfile(source, temporary)
            if _hash(temporary) != digest:
                raise ChannelError(409, "hyperframes_artifact_changed", "Artifact changed during promotion")
            with temporary.open("r+b") as stream:
                os.fsync(stream.fileno())
            # Atomic exclusive promotion: a crash cannot leave a partial final
            # file and a concurrently created export is never overwritten.
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _phase(self, channel, job_id, phase, **fields):
        def change(row):
            row["finalize_intent"].update(phase=phase, **fields)
            row.update(status="finalizing", phase=phase, error=None)
        return self.jobs._change(channel, job_id, change)

    def _attach_angle(self, channel, job, intent):
        binding = job["source_binding"]
        if binding["type"] != "product_angle":
            return self.sources.attach(channel, job, intent)
        fields = {"project_name": job["project_name"], "video_url": intent["video_path"],
                  "export_id": intent["export_id"], "status": "rendered", "qc_reviewed": True,
                  "cover_path": intent["package"].get("cover_path"),
                  "tiktok_caption": intent["package"]["caption"],
                  "tiktok_hashtags": " ".join(intent["package"]["hashtags"]),
                  "tiktok_product_id": intent["package"]["tiktok_product_id"]}
        if not hasattr(self.products, "_scoped_mutate") and hasattr(self.products, "compare_and_set_angle"):
            self._verify_product(channel, job)
            return self.products.compare_and_set_angle(channel, binding["product_id"], binding["angle_id"],
                                                       intent["angle_fingerprint"], fields)
        with self.products._scoped_mutate(self.products._scope(channel, False)) as rows:
            product = next((row for row in rows if row.get("id") == binding["product_id"] and row.get("channel_id") == channel), None)
            matches = [] if not product else [a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == binding["angle_id"]]
            if len(matches) != 1:
                return False
            self._verify_product(channel, job, product)
            angle = matches[0]
            if angle.get("export_id") == intent["export_id"] and angle.get("project_name") == job["project_name"]:
                return True
            if _fingerprint(angle) != intent["angle_fingerprint"]:
                return False
            angle.update(fields)
            product["updated_at"] = datetime.now(timezone.utc).isoformat()
            return True

    def resume(self, channel, job_id):
        self._defaults()
        job = self.jobs.get(channel, job_id)
        if job["status"] == "finalized":
            return job
        if not job.get("finalize_intent"):
            raise ChannelError(409, "hyperframes_intent_missing", "No approved finalize intent exists")
        # Serialize retries across processes. This lock is separate from the
        # business manifest lock, which projects.update acquires itself.
        lock_path = self.root / ".tmp/hyperframes/finalize" / job_id / "intent.json"
        with self.projects._lock(lock_path):
            return self._resume_locked(channel, job_id)

    repair = resume

    def _resume_locked(self, channel, job_id):
        from scripts.maintenance_lock import is_blocked
        if is_blocked(self.root):
            raise ChannelError(503, "maintenance_locked", "Workspace is in maintenance")
        job = self.jobs.get(channel, job_id)
        if job["status"] == "finalized":
            return job
        intent = deepcopy(job["finalize_intent"])
        try:
            artifact = self._verify_artifact(job, intent["artifact_hash"], intent)
            video, thumbnail = self._path(intent["video_path"]), self._path(intent["thumbnail_path"])
            self._promote(self._path(artifact["path"]), video, intent["artifact_hash"])
            self._promote(self._path(artifact["thumbnail_path"]), thumbnail, artifact["thumbnail_sha256"])
            if intent.get("cover_source"):
                self._promote(self._path(intent["cover_source"]), self._path(intent["cover_path"]), intent["package"]["cover_sha256"])
                intent["package"]["cover_path"] = intent["cover_path"]
            self.fault_hook("promotion")
            self._phase(channel, job_id, "promoted")
            binding = job["source_binding"]
            entry = {"path": intent["video_path"], "product_id": binding.get("product_id"),
                     "angle_id": binding.get("angle_id"), "project_name": job["project_name"], "status": "rendered"}
            snapshot = job.get("channel_identity_snapshot") or {}
            scope = {"channel_id": channel, "channel_revision": snapshot.get("channel_revision", 0),
                     "channel_identity_hash": snapshot.get("identity_hash"), "channel_identity_snapshot": snapshot}
            export = self.registry.find_by_path(intent["video_path"], channel_id=channel)
            if export is None:
                style = hyperframes_style_metadata(
                    job.get("source_angle_snapshot"), job.get("inputs"),
                    ((job.get("artifact") or {}).get("specs") or {}).get("duration"),
                )
                export = self.registry.ensure_many([{**entry, "style_metadata": style}],
                                                   channel_id=channel, job_scope=scope)[0]
            if any(export.get(key) != entry[key] for key in ("product_id", "angle_id", "project_name")):
                raise ChannelError(409, "hyperframes_export_conflict", "Registry parent binding changed")
            if export.get("channel_id") != channel or (intent["export_id"] and intent["export_id"] != export["id"]):
                raise ChannelError(409, "hyperframes_export_conflict", "Registry identity changed")
            intent["export_id"] = export["id"]
            self.fault_hook("registration")
            self._phase(channel, job_id, "registered", export_id=export["id"])
            for path in (thumbnail, self._path(intent["package"]["cover_path"]) if intent["package"].get("cover_path") else thumbnail):
                if self.artifact_register:
                    self.artifact_register(path.relative_to(self.root).as_posix(), channel)
            package = {**intent["package"], "export_id": export["id"], "channel_id": channel,
                       "project_id": job["project_id"], "project_name": job["project_name"],
                       "source_binding": binding, "video_path": intent["video_path"], "video_sha256": intent["artifact_hash"],
                       "thumbnail_path": intent["thumbnail_path"], "thumbnail_sha256": artifact["thumbnail_sha256"],
                       "composition_revision": job["snapshot"]["id"], "approved_at": intent["approved_at"],
                       "finalize_intent_id": intent["id"]}
            if binding["type"] != "product_angle":
                facts = job.get("source_product_snapshot") or {}
                angle = job.get("source_angle_snapshot") or {}
                package.update(source_title=facts.get("name") or "standalone",
                               source_hook=angle.get("title") or "")
            if binding["type"] == "gadget_project":
                package.update(source_review_required=True, source_artifact_id=intent["id"])
            project = self.projects.get(job["project_id"], channel)
            own_commit = any(ref.get("finalize_intent_id") == intent["id"] for ref in project.get("publish_package_refs", []))
            if own_commit and project["revision"] != intent["project_revision"] + 1:
                raise ChannelError(409, "hyperframes_project_changed", "Project changed after partial finalize; retained export requires review")
            if not own_commit:
                if project["revision"] != intent["project_revision"]:
                    raise ChannelError(409, "hyperframes_project_changed", "Project changed; retained export requires review")
                self.projects.update(job["project_id"], channel, project["revision"],
                                     {"status": "exported", "render_artifact": package, "publish_package": package,
                                      "publish_package_refs": [*project.get("publish_package_refs", []), package]})
            self.fault_hook("manifest")
            self._phase(channel, job_id, "manifest_committed")
            if not self._attach_angle(channel, job, intent):
                raise ChannelError(409, "hyperframes_parent_changed", "Angle changed; export retained, current Angle was not overwritten")
            self.fault_hook("parent")
            def done(row):
                row.update(status="finalized", phase="finalized", export_id=export["id"], error=None)
                row["finalize_intent"].update(phase="finalized", export_id=export["id"], publish_package=package)
            return self.jobs._change(channel, job_id, done)
        except (Exception,) as error:
            def failed(row):
                row.update(status="recovery_required", phase="recovery_required",
                           error={"code": getattr(error, "code", "hyperframes_finalize_failed"), "message": str(error),
                                  "next_action": "Inspect retained export and source; resume this intent after resolving the conflict"})
            self.jobs._change(channel, job_id, failed)
            raise
