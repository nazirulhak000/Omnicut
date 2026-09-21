"""FastAPI routes for the Gadget Media Product Video Studio."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from scripts import render_jobs
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
    voice_preset: str = Field(default="gemini_puck_male_hype", max_length=120)
    ad_tone: str = Field(default="commercial_expert", max_length=120)
    speed: float = Field(default=1.15, ge=0.75, le=1.5)


class CreateFromSlotRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=160)
    category: str = "Gadget"
    variant: str = ""
    presentation_mode: str = "gemini_tts"


def _repo() -> GadgetMediaRepository:
    return PROJECT_REPOSITORY


def _project_or_404(project_id: str):
    try:
        return _repo().get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ Product Video Project") from exc
    except (ProductVideoValidationError, GadgetMediaPathError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _resolved_workspace_file(raw_path: str) -> Path:
    candidate = Path(str(raw_path or ""))
    target = candidate.resolve(strict=False) if candidate.is_absolute() else (BASE_DIR / candidate).resolve(strict=False)
    base = BASE_DIR.resolve(strict=False)
    if target != base and base not in target.parents:
        raise ProductVideoValidationError("source file must be inside the workspace")
    if not target.is_file():
        raise ProductVideoValidationError("source file does not exist")
    return target


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
def list_projects():
    projects = _repo().list()
    return {"projects": [_repo()._summary(project) for project in projects]}


@router.post("/projects", status_code=201)
def create_project(payload: CreateProjectRequest):
    try:
        project = _repo().create(
            {
                "brand": payload.brand,
                "model": payload.model,
                "category": payload.category,
                "variant": payload.variant,
            },
            audience=payload.audience,
            editorial_promise=payload.editorial_promise,
            presentation={"mode": payload.presentation_mode, "voice": payload.voice},
            project_id=payload.project_id,
        )
        return project.to_dict()
    except (ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 400, detail=str(exc)) from exc


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return _project_or_404(project_id).to_dict()


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, payload: ProjectPatchRequest):
    _project_or_404(project_id)
    try:
        return _repo().patch(project_id, payload.model_dump(exclude_none=True)).to_dict()
    except (ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/sources/probe")
def probe_project_source(project_id: str, payload: SourceProbeRequest):
    project = _project_or_404(project_id)
    try:
        path = _resolved_workspace_file(payload.local_path)
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
        saved = _repo().patch(project_id, {"source_assets": sources})
        return {"source": source, "project": saved.to_dict()}
    except (ProductVideoValidationError, GadgetMediaPathError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/timeline/build")
def build_project_timeline(project_id: str):
    project = _project_or_404(project_id)
    try:
        timeline = GadgetMediaTimelineAdapter.build(project)
        saved = _repo().save_timeline(project_id, timeline)
        return {"timeline": timeline, "project": saved.to_dict()}
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/timeline")
def get_project_timeline(project_id: str):
    _project_or_404(project_id)
    try:
        return _repo().load_timeline(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ยังไม่ได้สร้าง Timeline") from exc


@router.put("/projects/{project_id}/timeline")
def save_project_timeline(project_id: str, payload: TimelineSaveRequest):
    _project_or_404(project_id)
    try:
        timeline = GadgetMediaTimelineAdapter.normalize_saved(project_id, payload.timeline)
        project = _repo().save_timeline(project_id, timeline)
        return {"timeline": timeline, "project": project.to_dict()}
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/quality/validate")
def validate_project_quality(project_id: str):
    project = _project_or_404(project_id)
    try:
        timeline = _repo().load_timeline(project_id)
    except KeyError:
        timeline = None
    report = validate_product_video(
        project,
        timeline,
        project_root=_repo().roots.project_dir(project_id),
    )
    saved = _repo().save_quality_report(project_id, report)
    return {"report": report, "project": saved.to_dict()}


@router.post("/projects/{project_id}/audio/generate", status_code=202)
def generate_project_narration(
    project_id: str,
    payload: NarrationRequest,
    background_tasks: BackgroundTasks,
):
    project = _project_or_404(project_id)
    if project.presentation.get("mode") != "gemini_tts":
        raise HTTPException(status_code=409, detail="Project ต้องเลือกโหมด Gemini TTS ก่อนสร้างเสียง")
    if not payload.script_text.strip() and not any(
        str(block.get("text") or "").strip() for block in (project.story.get("blocks") or [])
    ):
        raise HTTPException(status_code=409, detail="Story ต้องมีบทพูดก่อนสร้าง Gemini TTS")
    if not GeminiFlashTTSEngine.is_available():
        raise HTTPException(status_code=503, detail="ยังไม่ได้ตั้ง GEMINI_API_KEY สำหรับสร้างเสียง")

    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id, message="รอคิวสร้าง Gemini TTS สำหรับ Gadget Media")
    background_tasks.add_task(
        execute_gadget_media_narration,
        job_id,
        project_id,
        _repo(),
        script_text=payload.script_text,
        voice_preset=payload.voice_preset,
        ad_tone=payload.ad_tone,
        speed=payload.speed,
    )
    return {"job_id": job_id, "status": "queued", "project_id": project_id}


@router.post("/projects/{project_id}/renders", status_code=202)
def start_project_render(project_id: str, payload: RenderRequest, background_tasks: BackgroundTasks):
    project = _project_or_404(project_id)
    try:
        timeline = _repo().load_timeline(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="Project ต้องมี Timeline ก่อน Render") from exc
    report = validate_product_video(
        project,
        timeline,
        project_root=_repo().roots.project_dir(project_id),
    )
    project = _repo().save_quality_report(project_id, report)
    if not project.quality_report.get("passed") or project.status != "ready_to_render":
        raise HTTPException(status_code=409, detail="Project ต้องผ่าน Quality Gate และอยู่สถานะ ready_to_render ก่อน Render")
    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id, message="รอคิว Render Gadget Media")
    background_tasks.add_task(
        execute_gadget_media_render,
        job_id,
        project_id,
        _repo(),
        export_preset=payload.export_preset,
    )
    return {"job_id": job_id, "status": "queued", "project_id": project_id}


@router.post("/projects/{project_id}/renders/{artifact_id}/approve")
def approve_project_render(project_id: str, artifact_id: str):
    _project_or_404(project_id)
    try:
        return _repo().approve_render(project_id, artifact_id).to_dict()
    except ProductVideoValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/slots/{slot_id}/project", status_code=201)
def create_project_from_slot(campaign_id: str, slot_id: str, payload: CreateFromSlotRequest):
    store = CampaignStore(CAMPAIGNS_FILE)
    try:
        campaign = store.get(campaign_id)
        slot = next((item for item in campaign.slots if item.slot_id == slot_id), None)
        if not slot:
            raise KeyError(slot_id)
        if slot.product_project_id:
            return _repo().get(slot.product_project_id).to_dict()
        project = _repo().create(
            {"brand": payload.brand, "model": payload.model, "category": payload.category, "variant": payload.variant},
            audience=slot.target_audience,
            editorial_promise=slot.hook,
            presentation={"mode": payload.presentation_mode, "voice": ""},
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
        _repo().save(project)
        store.update_slot(campaign_id, slot_id, {"product_project_id": project.project_id})
        return project.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ Campaign Slot หรือ Product Project") from exc
    except (CampaignValidationError, ProductVideoValidationError, GadgetMediaPathError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
