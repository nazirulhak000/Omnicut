"""
API Endpoints for Hook Variation & A/B Testing Generator
Provides:
- POST /api/hooks/generate: Generate 5 marketing hook variations
- POST /api/hooks/apply-angle: Apply a chosen hook variant to a product angle
- POST /api/hooks/apply-project: Apply a hook variant to an active project manifest with optional instant reroll
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from scripts.hook_generator import HookVariationEngine, HOOK_STYLES
from scripts.product_store import ProductStore
from scripts.project_manifest import ProjectManifest
from scripts.tts_sanitizer import TTSSanitizer

router = APIRouter(prefix="/api/hooks", tags=["hooks"])


class HookGenerateRequest(BaseModel):
    product_name: str
    brand: Optional[str] = ""
    model: Optional[str] = ""
    description: Optional[str] = ""
    pain_point: Optional[str] = ""
    price_deal: Optional[str] = ""
    angle_name: Optional[str] = ""


class ApplyAngleHookRequest(BaseModel):
    product_id: str
    angle_id: str
    hook_variant: Dict[str, Any]
    update_script_first_line: Optional[bool] = False


class ApplyProjectHookRequest(BaseModel):
    project_name: str
    hook_variant: Dict[str, Any]
    auto_reroll: Optional[bool] = False


@router.get("/styles")
def get_hook_styles():
    """Return the 5 standard marketing hook styles."""
    return {"styles": HOOK_STYLES}


@router.post("/generate")
def generate_hooks(req: HookGenerateRequest):
    """Generate 5 tailored hook variations across standard marketing styles."""
    name = (req.product_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อสินค้า")

    variations = HookVariationEngine.generate_variations(
        product_name=name,
        brand=req.brand or "",
        model=req.model or "",
        description=req.description or "",
        pain_point=req.pain_point or "",
        price_deal=req.price_deal or "",
        angle_name=req.angle_name or "",
    )

    return {
        "product_name": name,
        "variations": variations,
    }


@router.post("/apply-angle")
def apply_hook_to_angle(req: ApplyAngleHookRequest):
    """Apply a selected hook variant to a specific product angle in store."""
    product = ProductStore.get(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า ID '{req.product_id}'")

    angles = product.get("angles", [])
    matched_idx = -1
    for idx, ang in enumerate(angles):
        if str(ang.get("angle_id")) == str(req.angle_id):
            matched_idx = idx
            break

    if matched_idx == -1:
        raise HTTPException(status_code=404, detail=f"ไม่พบมุม ID '{req.angle_id}' ในสินค้า")

    variant = req.hook_variant
    target_angle = dict(angles[matched_idx])

    # Update hook banner fields
    target_angle["hook_title"] = variant.get("hook_title") or target_angle.get("hook_title", "")
    target_angle["hook_brand"] = variant.get("hook_brand") or target_angle.get("hook_brand", "")
    target_angle["hook_model"] = variant.get("hook_model") or target_angle.get("hook_model", "")
    target_angle["hook_label"] = variant.get("hook_label") or target_angle.get("hook_label", "")
    target_angle["tts_hook_title"] = TTSSanitizer.clean(target_angle["hook_title"])

    # Optionally update the first spoken line
    if req.update_script_first_line and variant.get("opening_line"):
        clean_opening = variant["opening_line"].strip()
        script_lines = list(target_angle.get("script_lines") or [])
        if script_lines:
            script_lines[0] = clean_opening
        else:
            script_lines = [clean_opening]
        target_angle["script_lines"] = script_lines
        target_angle["script_text"] = "\n".join(script_lines)
        target_angle["tts_lines"] = script_lines

    angles[matched_idx] = target_angle
    updated_product = ProductStore.update(req.product_id, {"angles": angles})

    return {
        "status": "success",
        "product_id": req.product_id,
        "angle_id": req.angle_id,
        "angle": target_angle,
        "product": updated_product,
    }


@router.post("/apply-project")
def apply_hook_to_project(req: ApplyProjectHookRequest, background_tasks: BackgroundTasks):
    """Apply a hook variant to an active project's manifest with optional instant reroll."""
    project_name = req.project_name.strip()
    try:
        manifest = ProjectManifest.load(project_name)
    except Exception as err:
        raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}': {err}")

    variant = req.hook_variant
    manifest["hook_title"] = variant.get("hook_title") or manifest.get("hook_title", "")
    manifest["hook_brand"] = variant.get("hook_brand") or manifest.get("hook_brand", "")
    manifest["hook_model"] = variant.get("hook_model") or manifest.get("hook_model", "")
    manifest["hook_label"] = variant.get("hook_label") or manifest.get("hook_label", "")

    # Update overlays if present
    overlays = manifest.get("overlays") or []
    for ov in overlays:
        if ov.get("kind") == "hook":
            ov["brand"] = manifest["hook_brand"]
            ov["model"] = manifest["hook_model"]
            ov["label"] = manifest["hook_label"]
    manifest["overlays"] = overlays

    ProjectManifest.save(project_name, manifest)

    reroll_job_id = None
    if req.auto_reroll:
        from scripts.api_phase1 import _execute_reroll
        reroll_job_id = str(uuid.uuid4())
        overrides = {
            "hook_brand": manifest["hook_brand"],
            "hook_model": manifest["hook_model"],
            "hook_label": manifest["hook_label"],
        }
        background_tasks.add_task(_execute_reroll, reroll_job_id, project_name, "subtitles", overrides)

    return {
        "status": "success",
        "project_name": project_name,
        "hook_brand": manifest["hook_brand"],
        "hook_model": manifest["hook_model"],
        "hook_label": manifest["hook_label"],
        "reroll_job_id": reroll_job_id,
    }
