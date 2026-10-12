"""Real source adapters for HyperFrames; business identities remain in their domain.

Standalone metadata lives in the canonical HF manifest. Gadget facts and review
artifacts live in GadgetMediaRepository, never masquerading as ProductStore rows.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts.channel_store import ChannelError
from scripts.gadget_media_paths import GadgetMediaRoots, validate_project_id
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gadget_media_campaign import CampaignStore


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def slot_fingerprint(slot):
    """Content identity survives the edited->published projection and metrics."""
    return fingerprint({key: deepcopy(slot.get(key)) for key in
                        ("slot_id", "series", "hook", "target_audience", "script", "product_project_id", "source_refs")})


class HyperFramesSources:
    def __init__(self, root, *, gadget_repository=None):
        self.root = Path(root).resolve()
        self.gadgets = gadget_repository or GadgetMediaRepository(GadgetMediaRoots.under(self.root))
        if any(not Path(getattr(self.gadgets.roots, name)).absolute().is_relative_to(self.root)
               for name in ("raw", "assets", "projects", "exports", "covers", "archive", "docs")):
            raise ChannelError(422, "hyperframes_source_root_conflict", "Gadget source repository must share the workspace root")
        for name in ("raw", "assets", "projects", "exports", "covers", "archive", "docs"):
            self._safe(getattr(self.gadgets.roots, name))

    def _repo(self, channel):
        return self.gadgets.for_channel(channel)

    def gadget(self, channel, binding):
        try:
            project_id = validate_project_id(binding.get("project_id"))
            if project_id != binding.get("project_id"):
                raise ValueError("Non-canonical project ID")
            path = self.gadgets.roots.project_dir(project_id) / "project.json"
            self._safe(path)
            project = self._repo(channel).get(project_id)
        except (KeyError, ValueError) as exc:
            raise ChannelError(404, "hyperframes_source_not_found", "Gadget project is unavailable in this channel") from exc
        if project.channel_id != channel:
            raise ChannelError(404, "hyperframes_source_not_found", "Gadget project belongs to another channel")
        return project

    def _safe(self, path):
        path = Path(path)
        if ".." in path.parts or not path.is_relative_to(self.root) or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                for p in (path, *path.parents) if p != self.root and p.is_relative_to(self.root)):
            raise ChannelError(422, "hyperframes_source_path_invalid", "Source aliases and external paths are forbidden")
        if not path.resolve().is_relative_to(self.root):
            raise ChannelError(422, "hyperframes_source_path_invalid", "Source escapes workspace")
        return path

    def validate(self, channel, binding):
        if not isinstance(binding, dict):
            raise ChannelError(422, "hyperframes_source_invalid", "Source binding must be an object")
        if binding.get("type") == "standalone" and set(binding) == {"type"}:
            return deepcopy(binding)
        allowed = {"type", "project_id", "campaign_id", "slot_id"}
        if binding.get("type") != "gadget_project" or set(binding) - allowed or not binding.get("project_id"):
            raise ChannelError(422, "hyperframes_source_invalid", "Invalid Gadget source binding")
        if not all(isinstance(value, str) and 0 < len(value) <= 200 for key, value in binding.items() if key != "type"):
            raise ChannelError(422, "hyperframes_source_invalid", "Source IDs must be bounded text")
        if bool(binding.get("campaign_id")) != bool(binding.get("slot_id")):
            raise ChannelError(422, "hyperframes_source_invalid", "Campaign and slot must be specified together")
        project = self.gadget(channel, binding)
        self._slot(channel, binding, project)
        return deepcopy(binding)

    def _slot(self, channel, binding, project):
        if not binding.get("campaign_id"):
            return None
        link = {"campaign_id": binding["campaign_id"], "slot_id": binding["slot_id"]}
        if link not in project.campaign_links:
            raise ChannelError(404, "hyperframes_slot_not_found", "Slot is not linked to this Gadget project")
        path = self._safe(self.root / "_Docs/gadget_media_campaigns.json")
        try:
            campaign = CampaignStore(path, channel_id=channel).get(binding["campaign_id"])
            slot = next(item for item in campaign.slots if item.slot_id == binding["slot_id"])
        except (KeyError, StopIteration) as exc:
            raise ChannelError(404, "hyperframes_slot_not_found", "Campaign slot is unavailable") from exc
        if campaign.channel_id != channel or slot.product_project_id != project.project_id:
            raise ChannelError(409, "hyperframes_slot_changed", "Slot now belongs to another project")
        return {**slot.to_dict(), "publish_readiness_errors": slot.publish_readiness_errors()}

    def packet(self, channel, project):
        binding = project["source_binding"]
        if binding["type"] == "standalone":
            inputs = project.get("inputs") or {}
            metadata = {key: deepcopy(inputs[key]) for key in
                        ("title", "description", "caption", "hashtags", "tiktok_product_id") if key in inputs}
            return {"product": {"name": metadata.get("title") or "standalone", "metadata": metadata},
                    "angle": {"title": metadata.get("title") or "standalone", "metadata": metadata,
                              "source_type": "standalone"}}
        gadget = self.gadget(channel, binding)
        data = gadget.to_dict()
        fields = ("project_id", "product_identity", "audience", "editorial_promise", "source_assets",
                  "facts", "story", "presentation", "edit", "quality_report", "campaign_links", "approved_master_id")
        facts = {key: deepcopy(data[key]) for key in fields}
        slot = self._slot(channel, binding, gadget)
        if slot is not None:
            facts["slot"] = slot
        name = " ".join(str(data["product_identity"].get(k) or "") for k in ("brand", "model")).strip()
        return {"product": {"name": name, "gadget": facts},
                "angle": {"title": data["editorial_promise"] or name, "source_type": "gadget_project",
                          "gadget": facts}}

    def attach(self, channel, job, intent):
        if job["source_binding"]["type"] == "standalone":
            current = self.packet(channel, {"source_binding": job["source_binding"], "inputs": job.get("inputs") or {}})
            return fingerprint(current["angle"]) == intent["angle_fingerprint"]
        repo = self._repo(channel)
        # Use the same lock as all real Gadget repository writers, not a second store.
        with repo._lock:
            gadget = self.gadget(channel, job["source_binding"])
            for path in repo.roots.project_layout(gadget.project_id).values():
                self._safe(path)
            self._safe(repo.roots.docs)
            artifact_id = intent["id"]
            existing = next((a for a in gadget.artifacts if a.get("artifact_id") == artifact_id), None)
            if existing:
                return (existing.get("export_id") == intent["export_id"]
                        and existing.get("path") == intent["video_path"]
                        and existing.get("sha256") == intent["artifact_hash"])
            packet = self.packet(channel, {"source_binding": job["source_binding"]})
            if fingerprint(packet["angle"]) != intent["angle_fingerprint"]:
                return False
            artifact = {"artifact_id": artifact_id, "kind": "render", "engine": "hyperframes",
                        "path": intent["video_path"], "sha256": intent["artifact_hash"],
                        "thumbnail_path": intent["thumbnail_path"], "export_id": intent["export_id"],
                        "hyperframes_project_id": job["project_id"], "composition_revision": job["snapshot"]["id"],
                        "duration": (job.get("inputs") or {}).get("total_duration") or (job.get("inputs") or {}).get("duration_seconds"),
                        "approved": False, "review_required": True, "created_at": intent["approved_at"]}
            if job["source_binding"].get("slot_id"):
                frozen_slot = ((job.get("source_angle_snapshot") or {}).get("gadget") or {}).get("slot")
                if not isinstance(frozen_slot, dict):
                    raise ChannelError(409, "hyperframes_slot_snapshot_missing", "The exact render's campaign slot snapshot is missing")
                artifact["source_slot_fingerprint"] = slot_fingerprint(frozen_slot)
            gadget.artifacts.append(artifact)
            # A candidate enters Review; an existing approved master remains intact.
            if gadget.status not in {"approved", "published"}:
                gadget.status = "rendered"
            repo.save(gadget)
            return True

    def review_status(self, channel, binding, export_id):
        if binding.get("type") != "gadget_project":
            return {"ready": True, "required": False}
        gadget = self.gadget(channel, binding)
        slot = self._slot(channel, binding, gadget)
        matches = [a for a in gadget.artifacts if a.get("kind") == "render" and a.get("export_id") == export_id]
        master_ready = len(matches) == 1 and gadget.approved_master_id == matches[0]["artifact_id"] and matches[0].get("approved") is True
        if master_ready:
            self.approved_master(channel, binding, artifact_id=matches[0]["artifact_id"])
        slot_ready = slot is None or slot["ready_to_publish"] is True
        errors = [] if slot is None else deepcopy(slot["publish_readiness_errors"])
        if slot is not None and len(matches) == 1 and matches[0].get("source_slot_fingerprint") != slot_fingerprint(slot):
            slot_ready = False
            errors.append("Campaign slot content changed after the render snapshot; review a new source revision")
        return {"ready": master_ready and slot_ready, "required": True,
                "artifact_id": matches[0]["artifact_id"] if len(matches) == 1 else None,
                "approved_master_id": gadget.approved_master_id, "project_id": gadget.project_id,
                "master_ready": master_ready, "slot_ready": slot_ready,
                "slot_id": binding.get("slot_id"), "slot_errors": errors,
                "slot_fingerprint": None if slot is None else slot_fingerprint(slot)}

    def approved_master(self, channel, binding, *, artifact_id=None):
        gadget = self.gadget(channel, binding)
        matches = [a for a in gadget.artifacts if a.get("artifact_id") == gadget.approved_master_id and a.get("kind") == "render"]
        if len(matches) != 1 or (artifact_id and gadget.approved_master_id != artifact_id) or not matches[0].get("approved"):
            raise ChannelError(409, "hyperframes_master_unapproved", "Select the exact approved Gadget master")
        artifact = deepcopy(matches[0])
        reference = artifact.get("path") or artifact.get("video_path")
        path = Path(str(reference or ""))
        path = path if path.is_absolute() else self.root / path
        path = self._safe(path)
        if not path.is_file() or path.relative_to(self.root).parts[0] not in {"03_Projects", "04_Exports"}:
            raise ChannelError(404, "hyperframes_master_missing", "Approved master media is unavailable")
        relative = path.relative_to(self.root).parts
        domain_owned = (path.is_relative_to(self.gadgets.roots.export_dir(gadget.project_id))
                        or path.is_relative_to(self.gadgets.roots.project_dir(gadget.project_id))
                        or (len(relative) > 3 and relative[:3] in
                            {( "04_Exports", "Ready_to_post", channel), ("04_Exports", "Posted", channel)})
                        or (len(relative) > 2 and relative[:2] == ("03_Projects", channel)))
        # Production Gadget roots use 04_Exports/GadgetMedia, whereas isolated
        # helpers use Ready_to_post/GadgetMedia; both still require the exact ID.
        domain_owned = domain_owned or path.is_relative_to(self.root / "04_Exports/GadgetMedia" / gadget.project_id)
        if not domain_owned:
            raise ChannelError(404, "hyperframes_master_scope", "Master media is outside this Gadget project or channel")
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        digest = checksum.hexdigest()
        if artifact.get("sha256") and artifact["sha256"] != digest:
            raise ChannelError(409, "hyperframes_master_changed", "Approved master bytes changed")
        return {"project_id": gadget.project_id, "artifact_id": artifact["artifact_id"],
                "path": path.relative_to(self.root).as_posix(), "sha256": digest, "artifact": artifact,
                "approved": True, "channel_id": channel, "revision": fingerprint(gadget.to_dict()),
                **({"slot_id": binding["slot_id"]} if binding.get("slot_id") else {})}


def source_review_status(root, channel, binding, export_id):
    return HyperFramesSources(root).review_status(channel, binding, export_id)
