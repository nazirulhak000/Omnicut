"""
API Router for Video Rendering pipeline and system status.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    STICKERS_DIR, CAPCUT_DRAFT_DIR
)
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager
from scripts import render_jobs
from scripts.render_jobs import RenderCancelled
from scripts.media_service import scan_video_files, get_local_ip
from scripts.api_schemas import RenderRequest

router = APIRouter(tags=["Render & System"])


def execute_render_job(job_id: str, req_data: RenderRequest):
    """Background worker function executing the full video pipeline."""
    base_progress = render_jobs.progress_reporter(job_id)

    def on_progress(msg: str, progress: float):
        base_progress(msg, progress)
        TaskManager.update_progress(job_id, progress, step_label=msg)

    try:
        raw_video = Path(req_data.raw_video_path)
        if not raw_video.is_absolute():
            raw_video = BASE_DIR / req_data.raw_video_path

        human_voice_path = req_data.human_voice_audio
        if req_data.voice_mode == "video":
            human_voice_path = str(raw_video)
        elif req_data.voice_mode == "human" and human_voice_path:
            h_path = Path(human_voice_path)
            if not h_path.is_absolute():
                human_voice_path = str(BASE_DIR / human_voice_path)

        voice_engine_type = "gemini_tts" if req_data.voice_mode == "gemini_tts" else "edge_tts"

        sticker_file_path = None
        if req_data.sticker_badge:
            candidate = STICKERS_DIR / req_data.sticker_badge
            if candidate.exists():
                sticker_file_path = str(candidate)
            elif (BASE_DIR / req_data.sticker_badge).exists():
                sticker_file_path = str(BASE_DIR / req_data.sticker_badge)

        # Block re-rendering if this angle or project has already been posted!
        # Posted videos must remain permanent proof and cannot be overwritten.
        is_already_posted = False
        if req_data.product_id and req_data.angle_id:
            try:
                prod = ProductStore.get(req_data.product_id)
                if prod:
                    for a in prod.get("angles", []):
                        if (a.get("angle_id") or a.get("id")) == req_data.angle_id:
                            if a.get("status") == "posted" or a.get("posted_at"):
                                is_already_posted = True
                                break
            except Exception:
                pass
        elif req_data.project_name:
            try:
                for prod in ProductStore._load():
                    for a in prod.get("angles", []):
                        if a.get("project_name") == req_data.project_name:
                            if a.get("status") == "posted" or a.get("posted_at"):
                                is_already_posted = True
                                break
            except Exception:
                pass

        if is_already_posted:
            raise HTTPException(
                status_code=400,
                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
            )

        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(
                    req_data.product_id,
                    req_data.angle_id,
                    "in_production",
                    project_name=req_data.project_name
                )
            except Exception:
                pass

        with render_jobs.render_slot(job_id):
            result = TikTokAutoCutterPipeline.run(
                cancel_event=render_jobs.get_cancel_event(job_id),
                product_name=req_data.product_name,
                raw_video_path=str(raw_video),
                project_name=req_data.project_name,
                key_features=req_data.key_features,
                pain_point=req_data.pain_point,
                price_deal=req_data.price_deal,
                custom_script=req_data.custom_script,
                script_overlays=req_data.script_overlays,
                voice=req_data.voice_gender,
                voice_rate=req_data.voice_rate,
                voice_engine_type=voice_engine_type,
                voice_preset=req_data.voice_preset,
                ad_tone=req_data.ad_tone or "commercial_premium",
                human_voice_audio_path=human_voice_path,
                overlays=req_data.overlays,
                hook_brand=req_data.hook_brand,
                hook_model=req_data.hook_model,
                hook_label=req_data.hook_label,
                hook_motion=req_data.hook_motion,
                hook_colors=req_data.hook_colors,
                hook_style=req_data.hook_style,
                font_name=req_data.font_name,
                bilingual_subtitles=req_data.bilingual_subtitles,
                use_ai_vision=req_data.use_ai_vision,
                sticker_path=sticker_file_path,
                bgm_name=req_data.bgm_name,
                bgm_volume=req_data.bgm_volume,
                bgm_ducking=req_data.bgm_ducking,
                audio_mutes=req_data.audio_mutes,
                lut_name=req_data.lut_name,
                clip_list=req_data.clip_list,
                transitions=req_data.transitions,
                export_mp4=req_data.export_mp4,
                caption_position=req_data.caption_position or "bottom",
                caption_color=req_data.caption_color,
                caption_scale=req_data.caption_scale or 1.0,
                sticker_position=req_data.sticker_position or "top_right",
                sticker_scale=req_data.sticker_scale or 1.0,
                sticker_start_time=req_data.sticker_start_time,
                sticker_end_time=req_data.sticker_end_time,
                sticker_norm_x=req_data.sticker_norm_x,
                sticker_norm_y=req_data.sticker_norm_y,
                stickers=req_data.stickers,
                text_overlays=req_data.text_overlays,
                product_id=req_data.product_id,
                angle_id=req_data.angle_id,
                progress_callback=on_progress
            )

        if req_data.product_id and result.get("project_name"):
            try:
                ProductStore.attach_project(req_data.product_id, result["project_name"])
            except Exception as link_err:
                print(f"Warning: could not link project to product: {link_err}")

        if req_data.product_id and req_data.angle_id:
            try:
                mp4_val = result.get("mp4") or result.get("mp4_video") or result.get("output_video") or result.get("video_path") or ""
                is_rendered = bool(req_data.export_mp4 and mp4_val)
                ProductStore.update_angle_status(
                    req_data.product_id,
                    req_data.angle_id,
                    "rendered" if is_rendered else "in_production",
                    video_url=str(mp4_val) if is_rendered else None,
                    project_name=result.get("project_name"),
                    export_id=result.get("export_id") if is_rendered else None,
                )
            except Exception as angle_err:
                print(f"Warning: could not update angle status: {angle_err}")

        render_jobs.complete_job(job_id, result)
        is_exported = bool(req_data.export_mp4 and (result.get("mp4") or result.get("mp4_video") or result.get("output_video") or result.get("video_path")))
        TaskManager.complete_task(
            job_id,
            result=result,
            step_label="🎉 เรนเดอร์วิดีโอเสร็จสมบูรณ์ 100%!" if is_exported else "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!",
            target_id=result.get("project_name")
        )

    except RenderCancelled:
        # A cancel is not a failure: revert the angle exactly as a fresh
        # render's failure path already does (there is no earlier "rendered"
        # state a fresh render could be reverting *from* -- unlike a reroll,
        # which restores its pre-action snapshot instead, see _execute_reroll
        # in api_phase1.py), then bring all three systems to the same
        # terminal "cancelled" state instead of "failed".
        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(req_data.product_id, req_data.angle_id, "scripted")
            except Exception as angle_err:
                print(f"Warning: Could not revert angle status after cancel: {angle_err}")

        render_jobs.cancel_job(job_id)
        TaskManager.cancel_task(job_id)

    except Exception as e:
        from scripts.error_handler import classify_exception

        # The pipeline stamps the name it resolved onto the exception, which
        # is the only way to learn it when the caller sent none and a stage
        # failed before run() could return.
        failed_project = getattr(e, "pipeline_project_name", None) or req_data.project_name
        app_err = classify_exception(e, project_name=failed_project, job_id=job_id)
        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(req_data.product_id, req_data.angle_id, "scripted")
            except Exception as angle_err:
                print(f"Warning: Could not revert angle status: {angle_err}")

        render_jobs.fail_job(job_id, app_err)
        fail_msg = f"{app_err.message_th}"
        TaskManager.fail_task(
            job_id,
            app_err.message_th,
            step_label=fail_msg
        )


@router.post("/api/render")
def trigger_render(req: RenderRequest, background_tasks: BackgroundTasks):
    """Triggers the video creation pipeline in the background."""
    # Guard: Block re-rendering if this angle or project has already been posted!
    if req.product_id and req.angle_id:
        try:
            prod = ProductStore.get(req.product_id)
            if prod:
                for a in prod.get("angles", []):
                    if (a.get("angle_id") or a.get("id")) == req.angle_id:
                        if a.get("status") == "posted" or a.get("posted_at"):
                            raise HTTPException(
                                status_code=400,
                                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
                            )
        except HTTPException:
            raise
        except Exception:
            pass
    elif req.project_name:
        try:
            for prod in ProductStore._load():
                for a in prod.get("angles", []):
                    if a.get("project_name") == req.project_name:
                        if a.get("status") == "posted" or a.get("posted_at"):
                            raise HTTPException(
                                status_code=400,
                                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
                            )
        except HTTPException:
            raise
        except Exception:
            pass

    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id)

    p_name = req.product_name or req.project_name or "วิดีโอใหม่"
    is_render_task = bool(req.export_mp4)
    TaskManager.create_task(
        task_type="render_video" if is_render_task else "edit_project",
        title=f"{'เรนเดอร์วิดีโอ' if is_render_task else 'ตัดต่อวิดีโอ'}: {p_name}",
        payload={"project_name": req.project_name, "product_name": req.product_name, "export_mp4": is_render_task},
        target_tab="gallery" if is_render_task else "editor",
        target_id=req.project_name,
        task_id=job_id
    )

    background_tasks.add_task(execute_render_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}


@router.get("/api/render/status/{job_id}")
def get_render_status(job_id: str):
    """Returns current status and progress of a render job."""
    job = render_jobs.get_job(job_id)
    if job is not None:
        # cancel_event is a threading.Event living on the in-memory job dict
        # for request_cancel()/is_cancel_requested() to use -- it is not
        # JSON-serializable and was never part of this response's contract,
        # so it must never reach FastAPI's jsonable_encoder. Every other key
        # ("cancelling"/"cancelled" statuses included) already round-trips
        # through the same shape "completed"/"failed" use.
        return {k: v for k, v in job.items() if k != "cancel_event"}

    task = TaskManager.get_task(job_id)
    if task:
        return {
            "id": job_id,
            "status": task.get("status", "completed"),
            "progress": task.get("progress", 1.0),
            "message": task.get("step_label", "เสร็จสิ้น"),
            "result": task.get("result") or {},
            "error": task.get("error"),
            "error_category": task.get("error_category"),
            "error_code": task.get("error_code"),
            "suggestion_th": task.get("suggestion_th"),
        }
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/api/status")
def get_system_status(refresh_ip: bool = False):
    """Returns general health and system stats with fast single-pass scanning."""
    raw_files = scan_video_files(RAW_DIR, INBOX_DIR)
    export_files = list(EXPORTS_DIR.glob("*.mp4"))
    local_ip = get_local_ip(force=refresh_ip)

    return {
        "status": "online",
        "ffmpeg_ready": True,
        "capcut_draft_path": str(CAPCUT_DRAFT_DIR),
        "capcut_synced": CAPCUT_DRAFT_DIR.exists(),
        "total_raw_videos": len(raw_files),
        "total_exports": len(export_files),
        "local_ip": local_ip,
        "mobile_url": f"http://{local_ip}:5173",
        "directories": {
            "base": str(BASE_DIR),
            "inbox": str(INBOX_DIR),
            "raw": str(RAW_DIR),
            "exports": str(EXPORTS_DIR),
            "assets": str(ASSETS_DIR),
            "capcut": str(CAPCUT_DRAFT_DIR)
        }
    }
