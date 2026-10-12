"""Explicit paid-provider actions share the existing fenced authoring jobs."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from scripts.api_hyperframes_workflow import get_workflow
from scripts.channel_workflows import get_workflow_scope
from scripts.channel_scope import require_active_for_new_work, require_writable
from scripts.channel_store import ChannelError
from scripts.hyperframes_authoring import AuthoringError
from scripts.hyperframes_ai_provider import HyperframesAIProvider, DEFAULT_MODEL
from threading import Lock

router = APIRouter(prefix="/api/hyperframes", tags=["HyperFrames AI"])
_providers = {}
_provider_lock = Lock()


class Generate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_generation: int = Field(ge=0, strict=True)
    model: str = DEFAULT_MODEL
    timeout_seconds: int = Field(default=120, ge=10, le=300, strict=True)
    max_output_tokens: int = Field(default=8192, ge=1024, le=16384, strict=True)


def get_provider(service=Depends(get_workflow)):
    key = str(service.root.resolve())
    with _provider_lock:
        if key not in _providers:
            def current_source(job, channel):
                project = service.projects.get(job["project_id"], channel)
                return project["revision"], service.source_revision(channel, project)
            _providers[key] = HyperframesAIProvider(service.root, jobs=service.creative, source_state=current_source)
        return _providers[key]


@router.get("/ai/capabilities")
def capabilities(scope=Depends(get_workflow_scope), provider=Depends(get_provider)):
    return provider.capabilities()


@router.post("/authoring-jobs/{job_id}/generate")
async def generate(job_id: str, body: Generate, scope=Depends(get_workflow_scope), provider=Depends(get_provider), service=Depends(get_workflow)):
    require_active_for_new_work(scope)
    try:
        current = provider.jobs.get(job_id, scope.channel_id)
        project = service.projects.get(current["project_id"], scope.channel_id)
        if project.get("overlay_contract"):
            raise ChannelError(409, "overlay_composition_locked", "Approved-master overlays use the sealed builder; create a new overlay to change graphics")
        job = await provider.start(job_id, scope.channel_id, body.expected_generation,
            model=body.model, timeout_seconds=body.timeout_seconds, max_output_tokens=body.max_output_tokens)
        return {"job": job}
    except AuthoringError as error:
        raise ChannelError(getattr(error, "status_code", 409), error.code, str(error)) from error


@router.post("/authoring-jobs/{job_id}/generate/cancel")
async def cancel(job_id: str, scope=Depends(get_workflow_scope), provider=Depends(get_provider)):
    require_writable(scope)
    try:
        return {"job": await provider.cancel(job_id, scope.channel_id)}
    except AuthoringError as error:
        raise ChannelError(getattr(error, "status_code", 409), error.code, str(error)) from error
