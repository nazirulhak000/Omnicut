"""FastAPI routes for the Gadget Media Product Video Studio."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field

from scripts import render_jobs
from scripts.channel_scope import ChannelScope, require_writable, require_active_for_new_work, require_final_ready
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope, capture_job_scope, require_media_owner
from scripts.config import BASE_DIR
from scripts.gadget_media_campaign import CAMPAIGNS_FILE, CampaignStore, CampaignValidationError
from scripts.gadget_media_narration import execute_gadget_media_narration
from scripts.gadget_media_paths import GadgetMediaPathError
from scripts.gadget_media_project import ProductVideoValidationError, new_id
from scripts.gadget_media_quality import validate_product_video
from scripts.gadget_media_renderer import execute_gadget_media_render
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gadget_media_timeline_adapter import GadgetMediaTimelineAdapter
from scripts.gemini_tts_engine import GeminiFlashTTSEngine


router = APIRouter(prefix="/api/gadget-media", tags=["Gadget Media Product Studio"])
PROJECT_REPOSITORY = GadgetMediaRepository()


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = None
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    category: str = Field(default="Gadget", max_length=120)
    variant: str = Field(default="", max_length=160)
    audience: str = Field(default="", max_length=500)
    editorial_promise: str = Field(default="", max_length=500)
    presentation_mode: str = "gemini_tts"
    voice: str = ""


class ProjectPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_identity: Optional[Dict[str, Any]] = None
    audience: Optional[str] = None
    editorial_promise: Optional[str] = None
    status: Optional[str] = None
    source_assets: Optional[List[Dict[str, Any]]] = None
    facts: Optional[List[Dict[str, Any]]] = None
    story: Optional[Dict[str, Any]] = None
    presentation: Optional[Dict[str, Any]] = None
    edit: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    campaign_links: Optional[List[Dict[str, str]]] = None


class SourceProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Optional[str] = None
    local_path: str
    source_url: str = ""
    creator_or_brand: str = ""
    published_date: str = ""
    rights_basis: str = "licensed_press_kit"
    rights_reviewed: bool = False
    usage_note: str = ""
    product_key: str = ""
    checksum: str = ""


class TimelineSaveRequest(BaseModel):
    timeline: Dict[str, Any]


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    export_preset: str = "post"


class NarrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_text: str = Field(default="", max_length=12000)
    voice_preset: str = Field(default="gemini_fenrir_male_strong", max_length=120)
    ad_tone: str = Field(default="commercial_expert", max_length=120)
    speed: float = Field(default=1.15, ge=0.75, le=1.5)


class CreateFromSlotRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    category: str = "Gadget"
    variant: str = ""
    presentation_mode: str = "gemini_tts"


def _guard_write(scope, new_work=False):
    if isinstance(scope, ChannelScope):
        (require_active_for_new_work if new_work else require_writable)(scope)


def _guard_references(scope, value):
    if not isinstance(scope, ChannelScope):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"local_path", "audio_path", "video_path", "source_path", "image_path", "path"} and isinstance(item, str) and item:
                require_media_owner(scope, item, base_dir=BASE_DIR)
            else:
                _guard_references(scope, item)
    elif isinstance(value, list):
        for item in value:
            _guard_references(scope, item)


def _repo(scope=None) -> GadgetMediaRepository:
    return PROJECT_REPOSITORY.for_channel(scope.channel_id) if isinstance(scope, ChannelScope) else PROJECT_REPOSITORY


def _timeline_identity(project, timeline):
    """Preview uses persisted draft/render identity, never a live profile."""
    snapshots = [artifact.get("channel_identity_snapshot") for artifact in project.artifacts
                 if artifact.get("kind") == "render" and artifact.get("channel_identity_snapshot")]
    identity = snapshots[-1] if snapshots else project.presentation.get("channel_identity_snapshot")
    return {**timeline, "channel_id": project.channel_id or "main",
            "channel_identity_snapshot": identity}


def _project_or_404(project_id: str, scope=None):
    try:
        return _repo(scope).get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ Product Video Project") from exc
    except (ProductVideoValidationError, GadgetMediaPathError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _resolved_workspace_file(raw_path: str, scope=None) -> Path:
    candidate = Path(str(raw_path or ""))
    target = candidate.resolve(strict=False) if candidate.is_absolute() else (BASE_DIR / candidate).resolve(strict=False)
    base = BASE_DIR.resolve(strict=False)
    if target != base and base not in target.parents:
        raise ProductVideoValidationError("source file must be inside the workspace")
    if not target.is_file():
        raise ProductVideoValidationError("source file does not exist")
    return require_media_owner(scope, target, base_dir=BASE_DIR) if isinstance(scope, ChannelScope) else target


def _probe_video(path: Path) -> Dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=30,
    )
    if result.returncode != 0:
        raise ProductVideoValidationError(f"ffprobe ตรวจ Source ไม่สำเร็จ: {(result.stderr or '')[-300:]}")
    data = json.loads(result.stdout or "{}")
    video = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), None)
    if not video:
        raise ProductVideoValidationError("Source ไม่มี video stream")
    rate = str(video.get("r_frame_rate") or "0/1").split("/")
    fps = float(rate[0]) / max(1.0, float(rate[1])) if rate else 0.0
    return {
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": round(fps, 3),
        "duration": round(float((data.get("format") or {}).get("duration") or 0), 3),
        "codec": str(video.get("codec_name") or ""),
        "has_audio": any(item.get("codec_type") == "audio" for item in data.get("streams", [])),
    }


@router.get("/projects")
def list_projects( scope: ChannelScope = Depends(get_workflow_scope)):
    projects = _repo(scope).list()
    return {"projects": [_repo(scope)._summary(project) for project in projects]}


@router.post("/projects", status_code=201)
def create_project(payload: CreateProjectRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    try:
        project = _repo(scope).create(
            {
                "brand": payload.brand,
                "model": payload.model,
                "category": payload.category,
                "variant": payload.variant,
            },
            audience=payload.audience,
            editorial_promise=payload.editorial_promise,
            presentation={"mode": payload.presentation_mode, "voice": payload.voice,
                          **({"channel_identity_snapshot": capture_job_scope(scope)["channel_identity_snapshot"]}
                             if isinstance(scope, ChannelScope) else {})},
            project_id=payload.project_id,
        )
        return project.to_dict()
    except (ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 400, detail=str(exc)) from exc


@router.get("/projects/{project_id}")
def get_project(project_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    return _project_or_404(project_id, scope).to_dict()


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, payload: ProjectPatchRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    project = _project_or_404(project_id, scope)
    changes = payload.model_dump(exclude_none=True)
    if "presentation" in changes:
        previous_identity = project.presentation.get("channel_identity_snapshot")
        incoming_identity = changes["presentation"].get("channel_identity_snapshot")
        if incoming_identity is not None and incoming_identity != previous_identity:
            raise ChannelError(422, "channel_identity_immutable", "เปลี่ยนตัวตนช่องที่บันทึกไว้ผ่าน Presentation ไม่ได้")
        if previous_identity is not None:
            changes["presentation"]["channel_identity_snapshot"] = previous_identity
    _guard_references(scope, changes)
    for link in changes.get("campaign_links", []):
        if link.get("campaign_id"):
            try:
                CampaignStore(CAMPAIGNS_FILE, channel_id=scope.channel_id).get(link["campaign_id"])
            except KeyError as exc:
                raise HTTPException(404, "Campaign not found") from exc
    try:
        return _repo(scope).patch(project_id, changes).to_dict()
    except (ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/sources/probe")
def probe_project_source(project_id: str, payload: SourceProbeRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    project = _project_or_404(project_id, scope)
    try:
        path = _resolved_workspace_file(payload.local_path, scope)
        probe = _probe_video(path)
        source_id = payload.source_id or new_id("source")
        source = {
            "source_id": source_id,
            "local_path": str(path),
            "source_url": payload.source_url,
            "creator_or_brand": payload.creator_or_brand,
            "published_date": payload.published_date,
            "rights_basis": payload.rights_basis,
            "rights_reviewed": payload.rights_reviewed,
            "usage_note": payload.usage_note,
            "product_key": payload.product_key,
            "checksum": payload.checksum,
            "upscaled": False,
            **probe,
        }
        sources = [item for item in project.source_assets if item.get("source_id") != source_id]
        sources.append(source)
        saved = _repo(scope).patch(project_id, {"source_assets": sources})
        return {"source": source, "project": saved.to_dict()}
    except (ProductVideoValidationError, GadgetMediaPathError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/timeline/build")
def build_project_timeline(project_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    project = _project_or_404(project_id, scope)
    _guard_references(scope, project.to_dict())
    try:
        timeline = GadgetMediaTimelineAdapter.build(project)
        saved = _repo(scope).save_timeline(project_id, timeline)
        return {"timeline": _timeline_identity(saved, timeline), "project": saved.to_dict()}
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/timeline")
def get_project_timeline(project_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    project = _project_or_404(project_id, scope)
    try:
        return _timeline_identity(project, _repo(scope).load_timeline(project_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ยังไม่ได้สร้าง Timeline") from exc


@router.put("/projects/{project_id}/timeline")
def save_project_timeline(project_id: str, payload: TimelineSaveRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    _project_or_404(project_id, scope)
    try:
        _guard_references(scope, payload.timeline)
        timeline = GadgetMediaTimelineAdapter.normalize_saved(project_id, payload.timeline)
        project = _repo(scope).save_timeline(project_id, timeline)
        return {"timeline": _timeline_identity(project, timeline), "project": project.to_dict()}
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/quality/validate")
def validate_project_quality(project_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    project = _project_or_404(project_id, scope)
    _guard_references(scope, project.to_dict())
    try:
        timeline = _repo(scope).load_timeline(project_id)
    except KeyError:
        timeline = None
    report = validate_product_video(
        project,
        timeline,
        project_root=_repo(scope).roots.project_dir(project_id),
    )
    saved = _repo(scope).save_quality_report(project_id, report)
    return {"report": report, "project": saved.to_dict()}


@router.post("/projects/{project_id}/audio/generate", status_code=202)
def generate_project_narration(
    project_id: str,
    payload: NarrationRequest,
    background_tasks: BackgroundTasks, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    project = _project_or_404(project_id, scope)
    if project.presentation.get("mode") != "gemini_tts":
        raise HTTPException(status_code=409, detail="Project ต้องเลือกโหมด Gemini TTS ก่อนสร้างเสียง")
    if not payload.script_text.strip() and not any(
        str(block.get("text") or "").strip() for block in (project.story.get("blocks") or [])
    ):
        raise HTTPException(status_code=409, detail="Story ต้องมีบทพูดก่อนสร้าง Gemini TTS")
    if not GeminiFlashTTSEngine.is_available():
        raise HTTPException(status_code=503, detail="ยังไม่ได้ตั้ง GEMINI_API_KEY สำหรับสร้างเสียง")

    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id, message="รอคิวสร้าง Gemini TTS สำหรับ Gadget Media", channel_id=scope.channel_id if isinstance(scope, ChannelScope) else None, job_scope=capture_job_scope(scope) if isinstance(scope, ChannelScope) else None)
    background_tasks.add_task(
        execute_gadget_media_narration,
        job_id,
        project_id,
        _repo(scope),
        script_text=payload.script_text,
        voice_preset=payload.voice_preset,
        ad_tone=payload.ad_tone,
        speed=payload.speed,
    )
    return {"job_id": job_id, "status": "queued", "project_id": project_id}


@router.post("/projects/{project_id}/renders", status_code=202)
def start_project_render(project_id: str, payload: RenderRequest, background_tasks: BackgroundTasks, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    if isinstance(scope, ChannelScope) and (not scope.is_implicit_default or scope.strict):
        require_final_ready(scope)
    project = _project_or_404(project_id, scope)
    _guard_references(scope, project.to_dict())
    try:
        timeline = _repo(scope).load_timeline(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="Project ต้องมี Timeline ก่อน Render") from exc
    report = validate_product_video(
        project,
        timeline,
        project_root=_repo(scope).roots.project_dir(project_id),
    )
    project = _repo(scope).save_quality_report(project_id, report)
    if not project.quality_report.get("passed") or project.status != "ready_to_render":
        raise HTTPException(status_code=409, detail="Project ต้องผ่าน Quality Gate และอยู่สถานะ ready_to_render ก่อน Render")
    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id, message="รอคิว Render Gadget Media", channel_id=scope.channel_id if isinstance(scope, ChannelScope) else None, job_scope=capture_job_scope(scope) if isinstance(scope, ChannelScope) else None)
    background_tasks.add_task(
        execute_gadget_media_render,
        job_id,
        project_id,
        _repo(scope),
        export_preset=payload.export_preset,
    )
    return {"job_id": job_id, "status": "queued", "project_id": project_id}


@router.post("/projects/{project_id}/renders/{artifact_id}/approve")
def approve_project_render(project_id: str, artifact_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    _project_or_404(project_id, scope)
    try:
        return _repo(scope).approve_render(project_id, artifact_id).to_dict()
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/slots/{slot_id}/project", status_code=201)
def create_project_from_slot(campaign_id: str, slot_id: str, payload: CreateFromSlotRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    store = CampaignStore(CAMPAIGNS_FILE, channel_id=scope.channel_id if isinstance(scope, ChannelScope) else None)
    try:
        campaign = store.get(campaign_id)
        slot = next((item for item in campaign.slots if item.slot_id == slot_id), None)
        if not slot:
            raise KeyError(slot_id)
        if slot.product_project_id:
            return _repo(scope).get(slot.product_project_id).to_dict()
        project = _repo(scope).create(
            {"brand": payload.brand, "model": payload.model, "category": payload.category, "variant": payload.variant},
            audience=slot.target_audience,
            editorial_promise=slot.hook,
            presentation={"mode": payload.presentation_mode, "voice": "",
                          **({"channel_identity_snapshot": capture_job_scope(scope)["channel_identity_snapshot"]}
                             if isinstance(scope, ChannelScope) else {})},
        )
        project.campaign_links = [{"campaign_id": campaign_id, "slot_id": slot_id}]
        if slot.script:
            project.story["source_script"] = slot.script
        project.source_assets = [
            {
                "source_id": str(item.source_id),
                "source_url": item.source_url,
                "creator_or_brand": item.creator_or_brand,
                "rights_basis": item.rights_basis,
                "rights_reviewed": item.rights_reviewed,
                "usage_note": item.usage_note,
                "local_path": "",
            }
            for item in slot.source_refs
        ]
        _repo(scope).save(project)
        store.update_slot(campaign_id, slot_id, {"product_project_id": project.project_id})
        return project.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ Campaign Slot หรือ Product Project") from exc
    except (CampaignValidationError, ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
