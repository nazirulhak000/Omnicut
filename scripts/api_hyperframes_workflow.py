"""Channel-scoped HyperFrames workflow; generated code never owns store writes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict

from scripts import config
from scripts.channel_store import ChannelError
from scripts.channel_scope import require_active_for_new_work, require_final_ready, require_writable
from scripts.channel_workflows import get_workflow_scope, capture_job_scope, require_media_owner
from scripts.hyperframes_project import HyperFramesProjects, HyperFramesProjectError
from scripts.hyperframes_authoring import CreativeJobStore, AuthoringError, validate_inputs, verify_snapshot, managed_work_path
from scripts.hyperframes_render import HyperFramesRenderJobs
from scripts.hyperframes_finalize import HyperFramesFinalizer
from scripts.product_store import ProductStore

router = APIRouter(prefix="/api/hyperframes", tags=["HyperFrames workflow"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProject(Payload):
    source_binding: dict
    inputs: dict


class EditProject(Payload):
    expected_revision: int = Field(ge=1)
    inputs: dict


class RevisionRequest(Payload):
    expected_revision: int = Field(ge=1)


class AcceptRevision(RevisionRequest):
    authoring_job_id: str


class RenderRequest(RevisionRequest):
    idempotency_key: str = Field(min_length=1, max_length=200)


class FinalizeRequest(RevisionRequest):
    artifact_hash: str = Field(min_length=64, max_length=64)
    publish_package: dict


class Claim(Payload):
    executor_id: str = Field(min_length=1, max_length=200)
    expected_generation: int = Field(ge=0)


class Fence(Payload):
    executor_id: str
    generation: int
    fence: str


class Checkpoint(Fence):
    checkpoint: dict


class Submit(Fence):
    entrypoint: str = "index.html"


def _guard(operation):
    try:
        return operation()
    except HyperFramesProjectError as error:
        raise ChannelError(error.status_code, error.code, str(error)) from error
    except AuthoringError as error:
        status = 404 if error.code == "job_not_found" else 409 if any(word in error.code for word in ("stale", "lease", "fence", "conflict")) else 422
        raise ChannelError(status, error.code, str(error)) from error


class Workflow:
    def __init__(self, root, *, products=None, projects=None, creative=None, renders=None, finalizer=None, sources=None):
        self.root = Path(root).resolve()
        self.products = products or (ProductStore if self.root == Path(config.BASE_DIR).resolve() else None)
        from scripts.hyperframes_sources import HyperFramesSources
        self.sources = sources or HyperFramesSources(self.root)
        if Path(self.sources.root).resolve() != self.root:
            raise ChannelError(422, "hyperframes_source_root_conflict", "Source adapter must share the workflow root")
        self.projects = projects or HyperFramesProjects(self.root, product_store=self.products, sources=self.sources)
        self.creative = creative or CreativeJobStore(self.root)
        self.renders = renders or HyperFramesRenderJobs(self.root)
        self.finalizer = finalizer or HyperFramesFinalizer(self.root, jobs=self.renders, projects=self.projects, product_store=self.products, sources=self.sources)
        if any(Path(service.root).resolve() != self.root for service in (self.projects, self.creative, self.renders, self.finalizer)):
            raise ChannelError(422, "hyperframes_store_root_conflict", "Workflow services must share the same explicit root")

    def angle(self, channel, project):
        binding = project["source_binding"]
        if binding["type"] != "product_angle":
            return self.sources.packet(channel, project)["angle"]
        if hasattr(self.products, "_scoped_load"):
            products = self.products._scoped_load(self.products._scope(channel, False))
            product = next((p for p in products if p.get("id") == binding["product_id"]), None)
        else:
            product = self.products.get(binding["product_id"], channel_id=channel)
        if not product or product.get("channel_id") != channel:
            raise ChannelError(404, "hyperframes_source_not_found", "Product is outside this channel")
        matches = [a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == binding["angle_id"]]
        if len(matches) != 1:
            raise ChannelError(409, "hyperframes_angle_ambiguous", "Source angle is missing or ambiguous")
        return deepcopy(matches[0])

    def source_revision(self, channel, project):
        return hashlib.sha256(json.dumps(self.source_packet(channel, project), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def source_packet(self, channel, project):
        binding = project["source_binding"]
        if binding["type"] != "product_angle":
            return self.sources.packet(channel, project)
        if self.products is None:
            raise ChannelError(422, "hyperframes_store_required", "Custom product sources require a scoped product adapter")
        if hasattr(self.products, "_scoped_load"):
            rows = self.products._scoped_load(self.products._scope(channel, False))
            product = next((p for p in rows if p.get("id") == binding["product_id"]), None)
        else:
            product = self.products.get(binding["product_id"], channel_id=channel)
        if not product or product.get("channel_id") != channel:
            raise ChannelError(404, "hyperframes_source_not_found", "Product is outside this channel")
        matches = [a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == binding["angle_id"]]
        if len(matches) != 1:
            raise ChannelError(409, "hyperframes_angle_ambiguous", "Source angle is missing or ambiguous")
        angle = deepcopy(matches[0])
        fields = ("id", "name", "product_code", "canonical_product_key", "description", "url", "specs", "pain_points", "selling_points", "price_note", "target_buyer", "metadata_source", "source_warning")
        return {"product": {key: deepcopy(product[key]) for key in fields if key in product}, "angle": angle}

    def snapshot(self, reference):
        snapshot = deepcopy(reference)
        directory = (self.root / snapshot["revision_relative_path"]).resolve()
        revisions = (self.root / "03_Projects/_HyperFrames_Studio/revisions").resolve()
        if not directory.is_relative_to(revisions):
            raise ChannelError(422, "hyperframes_snapshot_path", "Snapshot is outside the revision store")
        snapshot.update(revision_dir=str(directory), snapshot_path=str(directory / "snapshot.json"), entry_path=str(directory / snapshot["entrypoint"]))
        verify_snapshot(snapshot)
        return snapshot

    def validated_inputs(self, scope, inputs):
        for key in ("voiceover_path", "music_path"):
            if inputs.get(key):
                require_media_owner(scope, inputs[key], base_dir=self.root)
        for reference in inputs.get("media_refs", []) if isinstance(inputs.get("media_refs", []), list) else []:
            if isinstance(reference, dict) and reference.get("path"):
                require_media_owner(scope, reference["path"], base_dir=self.root)
        return validate_inputs(self.root, inputs)["inputs"]


def get_workflow():
    # Construct lazily: importing the router must not create tables or projects.
    return Workflow(config.BASE_DIR)


@router.get("/projects")
def list_projects(scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    return _guard(lambda: {"projects": service.projects.list(scope.channel_id)})


@router.post("/projects", status_code=201)
def create_project(body: CreateProject, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    return _guard(lambda: {"project": service.projects.create(scope.channel_id, body.source_binding, capture_job_scope(scope)["channel_identity_snapshot"], service.validated_inputs(scope, body.inputs), allow_standalone=True)})


@router.get("/projects/{project_id}")
def get_project(project_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    return _guard(lambda: {"project": service.projects.get(project_id, scope.channel_id),
                           "authoring_jobs": [j for j in service.creative.list(scope.channel_id) if j["project_id"] == project_id],
                           "render_jobs": service.renders.list(scope.channel_id, project_id=project_id)})


@router.patch("/projects/{project_id}")
def edit_project(project_id: str, body: EditProject, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    return _guard(lambda: {"project": service.projects.update(project_id, scope.channel_id, body.expected_revision, {"inputs": service.validated_inputs(scope, body.inputs)})})


@router.post("/projects/{project_id}/authoring-jobs", status_code=201)
def create_authoring(project_id: str, body: RevisionRequest, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    def operation():
        project = service.projects.get(project_id, scope.channel_id)
        if project["revision"] != body.expected_revision:
            raise ChannelError(409, "hyperframes_revision_conflict", "Project changed")
        service.validated_inputs(scope, project["inputs"])
        packet = validate_inputs(service.root, project["inputs"])
        packet.update(source_binding=project["source_binding"], channel_identity=project["channel_identity"], source_snapshot=service.source_packet(scope.channel_id, project))
        source_revision = hashlib.sha256(json.dumps(packet["source_snapshot"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        job = service.creative.create(scope.channel_id, project_id, body.expected_revision, packet, expected_source_revision=source_revision)
        # Working files are the executor's only write boundary, never a store.
        managed_work_path(service.root, job["work_path"]).mkdir(parents=True, exist_ok=True)
        return {"job": job}
    return _guard(operation)


@router.get("/authoring-jobs/{job_id}")
def get_authoring(job_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    return _guard(lambda: {"job": service.creative.get(job_id, scope.channel_id)})


@router.get("/authoring-jobs/{job_id}/handoff")
def handoff(job_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    def operation():
        packet = service.creative.handoff_packet(job_id, scope.channel_id)
        packet["executor_client"] = {"path": "tools/hyperframes_workflow.py", "actions": ["status", "handoff", "claim", "heartbeat", "checkpoint", "submit"],
                                     "claim_generation": packet["generation"], "entrypoint": "index.html"}
        return {"handoff": packet}
    return _guard(operation)


@router.post("/authoring-jobs/{job_id}/claim")
def claim(job_id: str, body: Claim, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    return _guard(lambda: {"job": service.creative.claim(job_id, scope.channel_id, body.executor_id, body.expected_generation)})


@router.post("/authoring-jobs/{job_id}/heartbeat")
def heartbeat(job_id: str, body: Fence, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    return _guard(lambda: {"job": service.creative.heartbeat(job_id, scope.channel_id, **body.model_dump())})


@router.post("/authoring-jobs/{job_id}/checkpoint")
def checkpoint(job_id: str, body: Checkpoint, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    return _guard(lambda: {"job": service.creative.checkpoint(job_id, scope.channel_id, **body.model_dump())})


@router.post("/authoring-jobs/{job_id}/submit")
def submit(job_id: str, body: Submit, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    def operation():
        job = service.creative.get(job_id, scope.channel_id)
        project = service.projects.get(job["project_id"], scope.channel_id)
        if body.entrypoint != "index.html":
            raise ChannelError(422, "hyperframes_entrypoint_unsupported", "Use root index.html so CLI check validates the rendered entry")
        packet = validate_inputs(service.root, project["inputs"])
        if packet["asset_hashes"] != job["input_packet"].get("asset_hashes"):
            raise ChannelError(409, "hyperframes_input_asset_changed", "Saved audio changed during authoring")
        def prepare(source):
            entry = source / "index.html"
            if not entry.is_file() or entry.is_symlink():
                raise ChannelError(422, "hyperframes_entry_missing", "Author index.html inside the claimed work directory")
            hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in source.rglob("*") if path.is_file() and not path.is_symlink()}
            if not set(packet["asset_hashes"].values()).issubset(hashes):
                raise ChannelError(409, "hyperframes_audio_not_frozen", "Composition must vendor the exact saved audio before submission")
            content = entry.read_text(encoding="utf-8")
            if not re.search(r"<head\b[^>]*>", content, re.I):
                raise ChannelError(422, "hyperframes_head_required", "Composition needs an HTML head")
            if project.get("overlay_contract") is not None:
                overlay = project["overlay_contract"].get("approved_master_overlay") or {}
                master = source / "master.mp4"
                master_hash = None
                if master.is_file() and not master.is_symlink():
                    with master.open("rb") as stream:
                        master_hash = hashlib.file_digest(stream, "sha256").hexdigest()
                if (hashlib.sha256(entry.read_bytes()).hexdigest() != overlay.get("composition_sha256")
                        or not master.is_file() or master.is_symlink()
                        or master_hash != overlay.get("master_sha256")):
                    raise ChannelError(409, "hyperframes_overlay_revision_changed", "Overlay differs from the server-approved composition")
                # This server-built composition is sealed exactly, including its
                # HTML. Scope/identity stay in the immutable project/job/master;
                # injecting ordinary authoring metadata would invalidate its hash.
                return
            # This runs only after the lease fence and base revision pass.
            for node_id in ("omnicut-channel-identity", "omnicut-composition-metadata"):
                content = re.sub(r'<script\b[^>]*\bid=[\'\"]' + node_id + r'[\'\"][^>]*>.*?</script\s*>', '', content, flags=re.I | re.S)
            blocks = ""
            for node_id, value in (("omnicut-channel-identity", project["channel_identity"]), ("omnicut-composition-metadata", {"channel_id": scope.channel_id, "project_id": project["project_id"], "source_binding": project["source_binding"]})):
                encoded = json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
                blocks += f'<script type="application/json" id="{node_id}">{encoded}</script>'
            content = re.sub(r"(<head\b[^>]*>)", lambda match: match.group(1) + blocks, content, count=1, flags=re.I)
            entry.write_text(content, encoding="utf-8")
        result = service.creative.submit(job_id, scope.channel_id, **body.model_dump(), current_revision=project["revision"], current_source_revision=service.source_revision(scope.channel_id, project), source_dir=service.root / job["work_path"], prepare_source=prepare)
        return {"job": result}
    return _guard(operation)


@router.post("/projects/{project_id}/accept-revision")
def accept_revision(project_id: str, body: AcceptRevision, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    def operation():
        project = service.projects.get(project_id, scope.channel_id)
        job = service.creative.get(body.authoring_job_id, scope.channel_id)
        if job["project_id"] != project_id or job["status"] != "submitted" or job["base_revision"] != body.expected_revision or job["source_revision"] != service.source_revision(scope.channel_id, project):
            raise ChannelError(409, "hyperframes_accept_stale", "Submission is not the saved project/source revision")
        reference = deepcopy(job["submitted_revision"])
        service.snapshot(reference)
        reference["source_revision"] = job["source_revision"]
        reference["validated_input_hash"] = job["input_packet"]["input_hash"]
        reference["asset_hashes"] = deepcopy(job["input_packet"]["asset_hashes"])
        overlay_contract = project.get("overlay_contract")
        if overlay_contract is not None:
            overlay = overlay_contract.get("approved_master_overlay") or {}
            files = {item["path"]: item["sha256"] for item in reference["files"]}
            if (not overlay or files.get(reference["entrypoint"]) != overlay.get("composition_sha256")
                    or files.get(overlay.get("master_path")) != overlay.get("master_sha256")):
                raise ChannelError(409, "hyperframes_overlay_revision_changed", "Overlay revision differs from the server-approved master composition")
            reference["asset_contract"] = deepcopy(overlay_contract)
        for key in ("revision_dir", "snapshot_path", "entry_path"):
            reference.pop(key, None)
        return {"project": service.projects.update(project_id, scope.channel_id, body.expected_revision, {"accepted_revision": reference, "composition_revisions": project["composition_revisions"] + [reference], "status": "preview_ready"})}
    return _guard(operation)


@router.post("/projects/{project_id}/render-jobs", status_code=202)
def render(project_id: str, body: RenderRequest, background: BackgroundTasks, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    def operation():
        project = service.projects.get(project_id, scope.channel_id)
        if project["revision"] != body.expected_revision or not project.get("accepted_revision"):
            raise ChannelError(409, "hyperframes_render_unapproved", "Accept the current composition before rendering")
        accepted = project["accepted_revision"]
        source = service.source_packet(scope.channel_id, project)
        source_revision = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if accepted.get("source_revision") != source_revision:
            raise ChannelError(409, "hyperframes_source_changed", "Source Angle changed after acceptance; author a new revision")
        if accepted.get("validated_input_hash") != validate_inputs(service.root, project["inputs"])["input_hash"]:
            raise ChannelError(409, "hyperframes_input_asset_changed", "Saved input assets changed after acceptance")
        snapshot = service.snapshot(project["accepted_revision"])
        job = service.renders.create(scope.channel_id, project, snapshot, idempotency_key=body.idempotency_key,
                                     source_angle_snapshot=source["angle"], source_product_snapshot=source["product"],
                                     asset_contract=deepcopy(accepted.get("asset_contract")))
        if job["status"] == "queued":
            background.add_task(service.renders.execute, scope.channel_id, job["id"])
        return {"job": job}
    return _guard(operation)


@router.get("/render-jobs/{job_id}")
def get_render(job_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    return {"job": service.renders.get(scope.channel_id, job_id)}


@router.post("/render-jobs/{job_id}/cancel")
def cancel_render(job_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    return {"job": service.renders.cancel(scope.channel_id, job_id)}


@router.post("/render-jobs/{job_id}/retry", status_code=202)
def retry_render(job_id: str, background: BackgroundTasks, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    job = service.renders.get(scope.channel_id, job_id)
    if job["status"] not in {"failed", "interrupted"}:
        raise ChannelError(409, "hyperframes_retry_invalid", "Only failed or interrupted renders can retry")
    job = service.renders.queue_retry(scope.channel_id, job_id)
    background.add_task(service.renders.execute, scope.channel_id, job_id)
    return {"job": job}


@router.post("/render-jobs/{job_id}/finalize")
def finalize(job_id: str, body: FinalizeRequest, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_final_ready(scope)
    return _guard(lambda: {"job": service.finalizer.finalize(scope.channel_id, job_id, body.expected_revision, body.artifact_hash, body.publish_package)})


@router.post("/render-jobs/{job_id}/repair")
def repair(job_id: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_writable(scope)
    return _guard(lambda: {"job": service.finalizer.repair(scope.channel_id, job_id)})


@router.get("/render-jobs/{job_id}/artifact/{kind}")
def artifact(job_id: str, kind: str, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    job = service.renders.get(scope.channel_id, job_id)
    if kind not in {"video", "thumbnail"} or job["status"] not in {"qc_ready", "finalizing", "finalized", "recovery_required"}:
        raise ChannelError(404, "hyperframes_artifact_unavailable", "Artifact is not ready")
    record = job.get("artifact") or {}
    field = "path" if kind == "video" else "thumbnail_path"
    digest = record.get("sha256" if kind == "video" else "thumbnail_sha256")
    intent = job.get("finalize_intent") or {}
    promoted = intent.get("video_path" if kind == "video" else "thumbnail_path")
    candidates = [promoted] if job["status"] == "finalized" else [record.get(field), promoted]
    for value in candidates:
        if not value or not digest:
            continue
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        candidate = service.root / relative
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (candidate, *candidate.parents) if p != service.root and p.is_relative_to(service.root)):
            continue
        path = candidate.resolve()
        if not path.is_relative_to(service.root) or not path.is_file():
            continue
        actual = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual.update(chunk)
        if actual.hexdigest() == digest:
            return FileResponse(path, media_type="video/mp4" if kind == "video" else "image/webp", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
    raise ChannelError(404, "hyperframes_artifact_unavailable", "Reviewed artifact is missing or changed")
