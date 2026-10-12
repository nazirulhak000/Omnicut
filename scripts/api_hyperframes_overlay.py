"""Create a sealed overlay revision from an explicitly approved Gadget master."""
from copy import deepcopy
import logging
import shutil
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from scripts.api_hyperframes_workflow import get_workflow, create_authoring, submit, RevisionRequest, Submit, _guard
from scripts.channel_workflows import get_workflow_scope, capture_job_scope
from scripts.channel_scope import require_active_for_new_work
from scripts.channel_store import ChannelError
from scripts.hyperframes_sources import HyperFramesSources
from scripts.hyperframes_overlay import HyperFramesOverlay, _sha
from scripts.hyperframes_authoring import managed_work_path, AuthoringError
from scripts.hyperframes_project import HyperFramesProjectError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hyperframes/overlay", tags=["HyperFrames overlay"])


class Inspect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_binding: dict


class Create(Inspect):
    approval: dict
    inputs: dict
    layers: list[dict] = Field(min_length=1, max_length=24)


def overlay_for(service):
    sources = HyperFramesSources(service.root)
    return HyperFramesOverlay(service.root, resolver=sources.approved_master)


def record_failed_overlay(service, scope, project, job, claimed, error):
    """Retain immutable evidence and fence only this operation's owned job."""
    if isinstance(error, ChannelError):
        status, code, message = error.status_code, error.code, error.message
    elif isinstance(error, HyperFramesProjectError):
        status, code, message = error.status_code, error.code, str(error)
    elif isinstance(error, AuthoringError):
        status = 409 if any(word in error.code for word in ("stale", "lease", "fence", "conflict")) else 422
        code, message = error.code, str(error)
    elif isinstance(error, FileExistsError):
        status, code, message = 409, "overlay_work_conflict", "Managed overlay work already contains a file; create a new approved overlay project"
    else:
        status, code, message = 500, "overlay_creation_failed", "Could not finish the overlay project; its approved input and recovery evidence were retained"
    recovery = {"project_id": project["project_id"], "error_code": code,
                "next_action": "Inspect the retained approved-master input and create a new explicitly approved overlay project"}
    if job:
        recovery["authoring_job_id"] = job["id"]
        try:
            with service.creative.table.scoped_mutate(scope.channel_id) as rows:
                row = next((item for item in rows if item["id"] == job["id"] and item.get("project_id") == project["project_id"]), None)
                owned_queued = row and claimed is None and row["status"] == "queued" and row["generation"] == job["generation"]
                owned_claimed = row and claimed and row["status"] == "authoring" and all(row.get(key) == claimed.get(key) for key in ("generation", "executor_id", "fence"))
                if owned_queued or owned_claimed:
                    row.update(status="cancelled", generation=row["generation"] + 1, executor_id=None, fence=None,
                               lease_expires_at=0, updated_at=service.creative.clock(), error=code,
                               checkpoint={"next_action": recovery["next_action"]})
        except Exception:
            recovery["job_recovery_recorded"] = False
            logger.exception("Could not record failed overlay creative job %s", job["id"])
    try:
        current = service.projects.get(project["project_id"], scope.channel_id)
        service.projects.update(project["project_id"], scope.channel_id, current["revision"],
                                {"status": "blocked", "readiness": {"ready": False, "errors": [code], "overlay_recovery": recovery}})
        recovery["recovery_status"] = "blocked"
    except Exception:
        recovery["recovery_status"] = "recording_failed"
        logger.exception("Could not record failed overlay project %s", project["project_id"])
    return ChannelError(status, code, message, **recovery)


@router.post("/inspect")
def inspect(body: Inspect, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    return {"master": overlay_for(service).inspect(scope.channel_id, body.source_binding)}


@router.post("/projects", status_code=201)
def create(body: Create, scope=Depends(get_workflow_scope), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    def operation():
        overlay = overlay_for(service)
        master = overlay.inspect(scope.channel_id, body.source_binding)
        if body.approval.get("approved") is not True or body.approval.get("master_digest") != master["master_digest"]:
            raise ChannelError(409, "overlay_approval_required", "Confirm the exact approved master before creating a new output")
        layers = overlay.validate_layers(scope.channel_id, master["specs"]["duration"], body.layers)
        inputs = deepcopy(body.inputs)
        inputs.update(duration_seconds=master["specs"]["duration"], audio_mode="music_only" if master["specs"].get("audio") else "silent")
        inputs.pop("voiceover_path", None)
        inputs.pop("music_path", None)
        if master["specs"].get("audio"):
            inputs["music_path"] = master["path"]
        inputs = service.validated_inputs(scope, inputs)
        identity = capture_job_scope(scope)["channel_identity_snapshot"]
        project = service.projects.create(scope.channel_id, body.source_binding, identity, inputs)
        job, claimed = None, None
        try:
            directory = service.projects.directory(project["project_id"], scope.channel_id).relative_to(service.root).as_posix()
            frozen = overlay.freeze(scope.channel_id, directory, body.source_binding, approval=body.approval)
            built = overlay.compose(frozen, f"{directory}/overlay_compositions/{uuid.uuid4().hex}", layers)
            inputs.update(built["inputs"])
            project = service.projects.update(project["project_id"], scope.channel_id, project["revision"], {"inputs": service.validated_inputs(scope, inputs)})
            project = service.projects.update(project["project_id"], scope.channel_id, project["revision"], {"overlay_contract": built["asset_contract"]})
            job = create_authoring(project["project_id"], RevisionRequest(expected_revision=project["revision"]), scope, service)["job"]
            owner = f"approved_overlay_{uuid.uuid4().hex}"
            claimed = service.creative.claim(job["id"], scope.channel_id, owner, job["generation"])
            work = managed_work_path(service.root, job["work_path"])
            source = service.root / built["source_dir"]
            for file in built["files"]:
                original = overlay._path((source / file["path"]).relative_to(service.root).as_posix())
                target = work / file["path"]
                if _sha(original) != file["sha256"]:
                    raise ChannelError(409, "overlay_composition_changed", "Sealed overlay source changed before submission")
                with target.open("xb") as output, original.open("rb") as input_file:
                    shutil.copyfileobj(input_file, output)
                if _sha(target) != file["sha256"]:
                    raise ChannelError(409, "overlay_composition_changed", "Sealed overlay changed while copying")
            fence = Submit(executor_id=owner, generation=claimed["generation"], fence=claimed["fence"])
            result = submit(job["id"], fence, scope, service)
            return {"project": service.projects.get(project["project_id"], scope.channel_id), "job": result["job"], "master": frozen}
        except Exception as error:
            raise record_failed_overlay(service, scope, project, job, claimed, error) from error
    return _guard(operation)
