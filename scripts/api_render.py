"""
API Router for Video Rendering pipeline and system status.
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from scripts.channel_scope import ChannelScope, require_active_for_new_work, require_final_ready
from scripts.channel_workflows import get_workflow_scope, capture_job_scope, require_record_owner, require_project_owner
from scripts.pipeline_context import channel_project_name
from scripts.project_manifest import ProjectManifest

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

MIN_FREE_DISK_GB = 3.0
MIN_FREE_DISK_BYTES = int(MIN_FREE_DISK_GB * 1024 * 1024 * 1024)


def check_disk_space(path: Optional[Path] = None, min_bytes: int = MIN_FREE_DISK_BYTES) -> Dict[str, Any]:
    """Checks free disk space where video rendering and exports take place."""
    target = path or EXPORTS_DIR or BASE_DIR
    try:
        target = Path(target)
        while not target.exists() and target != target.parent:
            target = target.parent
        usage = shutil.disk_usage(str(target))
        free_gb = round(usage.free / (1024 ** 3), 2)
        total_gb = round(usage.total / (1024 ** 3), 2)
        min_required_gb = round(min_bytes / (1024 ** 3), 1)
        return {
            "free_bytes": usage.free,
            "total_bytes": usage.total,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "min_required_gb": min_required_gb,
            "is_sufficient": usage.free >= min_bytes
        }
    except Exception as e:
        return {
            "free_bytes": None,
            "total_bytes": None,
            "free_gb": None,
            "total_gb": None,
            "min_required_gb": round(min_bytes / (1024 ** 3), 1),
            # An unknown free-space value cannot authorize a heavy render.
            "is_sufficient": False,
            "error": str(e)
        }


@router.get("/api/render/disk-check")
def get_render_disk_check():
    """Returns disk space status for render storage and exports."""
    return check_disk_space()



def execute_render_job(job_id: str, req_data: RenderRequest, job_scope: Optional[Dict[str, Any]] = None):
    """Background worker function executing the full video pipeline."""
    pinned = render_jobs.pin_job_scope(job_scope=job_scope)
    channel_kwargs = {"channel_id": pinned["channel_id"]} if pinned.get("channel_id") else {}
    base_progress = render_jobs.progress_reporter(job_id, **channel_kwargs)

    def on_progress(msg: str, progress: float):
        base_progress(msg, progress)
        TaskManager.update_progress(job_id, progress, step_label=msg, **channel_kwargs)

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

        voice_engine_type = "edge_tts" if req_data.voice_mode == "edge_tts" else "gemini_tts"

        sticker_file_path = None
        if req_data.sticker_badge:
            # req_data.sticker_badge is client-controlled -- strip to just the
            # filename (drops any "../" traversal or absolute-path component)
            # and resolve+verify containment within STICKERS_DIR before ever
            # treating it as a real path, otherwise a caller could read any
            # file the process has access to (e.g. "../../../../Users/x/private.png").
            badge_name = Path(req_data.sticker_badge).name
            if badge_name:
                candidate = (STICKERS_DIR / badge_name).resolve()
                try:
                    candidate.relative_to(STICKERS_DIR.resolve())
                    if candidate.exists():
                        sticker_file_path = str(candidate)
                except ValueError:
                    pass

        # Block re-rendering if this angle or project has already been posted!
        # Posted videos must remain permanent proof and cannot be overwritten.
        is_already_posted = False
        if req_data.product_id and req_data.angle_id:
            try:
                prod = ProductStore.get(req_data.product_id, **channel_kwargs)
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
                if ProductStore.has_posted_angle_for_project(req_data.project_name, **channel_kwargs):
                    is_already_posted = True
            except Exception:
                pass

        if is_already_posted:
            raise HTTPException(
                status_code=400,
                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
            )

        # Guard: Re-verify disk space at execution time before heavy processing
        disk = check_disk_space(EXPORTS_DIR)
        if not disk.get("is_sufficient", True):
            if disk.get("error"):
                raise RuntimeError(
                    f"ตรวจสอบพื้นที่ว่างก่อน Render ไม่สำเร็จ ({disk['error']}) จึงหยุดเพื่อป้องกันไฟล์เสียหาย"
                )
            free_gb = disk.get("free_gb", 0)
            min_gb = disk.get("min_required_gb", 3.0)
            raise RuntimeError(
                f"พื้นที่ว่างบนดิสก์เหลือน้อยเกินไป ({free_gb} GB เหลืออยู่, ต้องการขั้นต่ำ {min_gb} GB) ระงับการเรนเดอร์เพื่อป้องกันคลิปเสียหาย"
            )

        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(
                    req_data.product_id,
                    req_data.angle_id,
                    "in_production",
                    project_name=req_data.project_name,
                    **channel_kwargs,
                )
            except Exception:
                pass

        with render_jobs.render_slot(job_id, **channel_kwargs):
            result = TikTokAutoCutterPipeline.run(
                cancel_event=render_jobs.get_cancel_event(job_id, **channel_kwargs),
                **channel_kwargs,
                job_scope=pinned or None,
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
                voice_preset=req_data.voice_preset or "gemini_fenrir_male_strong",
                ad_tone=req_data.ad_tone or "commercial_hype",
                style_preset=req_data.style_preset,
                human_voice_audio_path=human_voice_path,
                overlays=req_data.overlays,
                hook_brand=req_data.hook_brand,
                hook_model=req_data.hook_model,
                hook_label=req_data.hook_label,
                hook_motion=req_data.hook_motion,
                hook_colors=req_data.hook_colors,
                hook_style=req_data.hook_style,
                target_duration=req_data.target_duration,
                story_format=req_data.story_format,
                font_name=req_data.font_name,
                bilingual_subtitles=req_data.bilingual_subtitles,
                show_watermark=req_data.show_watermark,
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
                effects=req_data.effects,
                text_overlays=req_data.text_overlays,
                product_id=req_data.product_id,
                angle_id=req_data.angle_id,
                color_theme=req_data.color_theme,
                spotlight=req_data.spotlight,
                background_isolation=req_data.background_isolation,
                shot_list_id=req_data.shot_list_id,
                manual_shot_map=req_data.manual_shot_map or [],
                progress_callback=on_progress
            )


        if req_data.product_id and result.get("project_name"):
            try:
                ProductStore.attach_project(req_data.product_id, result["project_name"], **channel_kwargs)
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
                    **channel_kwargs,
                )
            except Exception as angle_err:
                print(f"Warning: could not update angle status: {angle_err}")

        render_jobs.complete_job(job_id, result, **channel_kwargs)
        is_exported = bool(req_data.export_mp4 and (result.get("mp4") or result.get("mp4_video") or result.get("output_video") or result.get("video_path")))
        TaskManager.complete_task(
            job_id,
            result=result,
            step_label="🎉 เรนเดอร์วิดีโอเสร็จสมบูรณ์ 100%!" if is_exported else "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!",
            target_id=result.get("project_name"),
            **channel_kwargs,
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
                # project_name="" clears the stale pointer to the abandoned,
                # manifest-less folder this attempt was writing into -- left
                # set, it makes ProductToClip's `isInProduction` heuristic
                # (status !== 'in_production' but project_name truthy) show
                # "กำลังตัดต่อ" forever on an angle that is actually free to
                # regenerate, and GET /api/projects/<name> 404s if anything
                # tries to open it (there is nothing to resume: this function
                # only ever runs a from-scratch render, never a reroll).
                ProductStore.update_angle_status(req_data.product_id, req_data.angle_id, "scripted", project_name="", **channel_kwargs)
            except Exception as angle_err:
                print(f"Warning: Could not revert angle status after cancel: {angle_err}")

        render_jobs.cancel_job(job_id, **channel_kwargs)
        TaskManager.cancel_task(job_id, **channel_kwargs)

    except Exception as e:
        from scripts.error_handler import classify_exception

        # The pipeline stamps the name it resolved onto the exception, which
        # is the only way to learn it when the caller sent none and a stage
        # failed before run() could return.
        failed_project = getattr(e, "pipeline_project_name", None) or req_data.project_name
        app_err = classify_exception(e, project_name=failed_project, job_id=job_id)
        if req_data.product_id and req_data.angle_id:
            try:
                # Same project_name clear as the RenderCancelled branch above.
                ProductStore.update_angle_status(req_data.product_id, req_data.angle_id, "scripted", project_name="", **channel_kwargs)
            except Exception as angle_err:
                print(f"Warning: Could not revert angle status: {angle_err}")

        render_jobs.fail_job(job_id, app_err, **channel_kwargs)
        fail_msg = f"{app_err.message_th}"
        if getattr(app_err, "suggestion_th", None):
            fail_msg = f"{app_err.message_th} — {app_err.suggestion_th}"
        TaskManager.fail_task(
            job_id,
            fail_msg,
            step_label=fail_msg,
            **channel_kwargs,
        )


@router.post("/api/render")
def trigger_render(req: RenderRequest, background_tasks: BackgroundTasks, scope: ChannelScope = Depends(get_workflow_scope)):
    """Triggers the video creation pipeline in the background."""
    scoped = isinstance(scope, ChannelScope)
    channel_kwargs = {"channel_id": scope.channel_id} if scoped else {}
    if scoped:
        require_active_for_new_work(scope)
        if req.export_mp4 and not (scope.is_implicit_default and not scope.strict):
            require_final_ready(scope)
        if req.product_id:
            require_record_owner(scope, ProductStore.get(req.product_id, **channel_kwargs), resource_label="สินค้า")
        project_name = channel_project_name(req.project_name, scope.channel_id)
        req = req.model_copy(deep=True, update={"project_name": project_name})
        if project_name and ProjectManifest.load(project_name) is not None:
            require_project_owner(scope, project_name, writable=True)
    # Guard: Block re-rendering if this angle or project has already been posted!
    if req.product_id and req.angle_id:
        try:
            prod = ProductStore.get(req.product_id, **channel_kwargs)
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
        except Exception as guard_err:
            # The guard's own HTTPException (a genuine "already posted" match)
            # must keep surfacing as-is. But an unrelated failure here
            # (ProductStore read error, etc.) must NOT be treated as "no
            # posted match" -- that would silently let a re-render proceed
            # over what might be a posted, proof-of-record export. Fail
            # closed instead of falling through to the render.
            raise HTTPException(
                status_code=500,
                detail=f"ตรวจสอบสถานะโพสต์ก่อนเรนเดอร์ไม่สำเร็จ จึงหยุดการเรนเดอร์เพื่อความปลอดภัย: {guard_err}",
            )
    elif req.project_name:
        try:
            if ProductStore.has_posted_angle_for_project(req.project_name, **channel_kwargs):
                raise HTTPException(
                    status_code=400,
                    detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
                )
        except HTTPException:
            raise
        except Exception as guard_err:
            # Same fail-closed reasoning as the product_id/angle_id branch above.
            raise HTTPException(
                status_code=500,
                detail=f"ตรวจสอบสถานะโพสต์ก่อนเรนเดอร์ไม่สำเร็จ จึงหยุดการเรนเดอร์เพื่อความปลอดภัย: {guard_err}",
            )

    # Guard: Disk space check before queuing heavy render (minimum 3.0 GB required)
    disk = check_disk_space(EXPORTS_DIR)
    if not disk.get("is_sufficient", True):
        if disk.get("error"):
            raise HTTPException(
                status_code=507,
                detail="ตรวจสอบพื้นที่ว่างก่อน Render ไม่สำเร็จ จึงหยุดเพื่อป้องกันไฟล์เสียหาย",
            )
        free_gb = disk.get("free_gb", 0)
        min_gb = disk.get("min_required_gb", 3.0)
        raise HTTPException(
            status_code=507,
            detail=f"พื้นที่ว่างบนดิสก์เหลือน้อยเกินไป ({free_gb} GB เหลืออยู่, ต้องการขั้นต่ำ {min_gb} GB) กรุณาเคลียร์พื้นที่จัดเก็บก่อนเริ่มเรนเดอร์เพื่อป้องกันคลิปเสียหาย"
        )

    job_id = str(uuid.uuid4())
    pinned = capture_job_scope(scope) if scoped else None
    render_jobs.create_job(job_id, job_scope=pinned, **channel_kwargs)

    p_name = req.product_name or req.project_name or "วิดีโอใหม่"
    is_render_task = bool(req.export_mp4)
    TaskManager.create_task(
        task_type="render_video" if is_render_task else "edit_project",
        title=f"{'เรนเดอร์วิดีโอ' if is_render_task else 'ตัดต่อวิดีโอ'}: {p_name}",
        payload={"project_name": req.project_name, "product_name": req.product_name, "product_id": req.product_id, "angle_id": req.angle_id, "export_mp4": is_render_task},
        target_tab="gallery" if is_render_task else "editor",
        target_id=req.project_name,
        task_id=job_id,
        job_scope=pinned,
        **channel_kwargs,
    )

    background_tasks.add_task(execute_render_job, job_id, req, pinned)
    return {"job_id": job_id, "status": "queued"}


@router.get("/api/render/status/{job_id}")
def get_render_status(job_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """Returns current status and progress of a render job."""
    channel_kwargs = {"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}
    job = render_jobs.get_job(job_id, **channel_kwargs)
    if job is not None:
        # cancel_event is a threading.Event living on the in-memory job dict
        # for request_cancel()/is_cancel_requested() to use -- it is not
        # JSON-serializable and was never part of this response's contract,
        # so it must never reach FastAPI's jsonable_encoder. Every other key
        # ("cancelling"/"cancelled" statuses included) already round-trips
        # through the same shape "completed"/"failed" use.
        return {k: v for k, v in job.items() if k != "cancel_event"}

    task = TaskManager.get_task(job_id, **channel_kwargs)
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


_LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "[::1]", "0.0.0.0"}


def _public_mobile_url(request: Optional[Request], local_ip: str) -> str:
    """Base URL a PHONE can open for mobile / quick-post links.

    Order: ``OMNICUT_PUBLIC_URL`` (e.g. the Colab tunnel
    ``https://studio.nazirulhak.com``) -> the URL this request actually came
    in on (honouring ``x-forwarded-proto`` / ``x-forwarded-host`` from the
    tunnel/proxy) unless that is localhost -> the LAN dev server as a last
    resort. A LAN ``https://<ip>:5173`` link is dead for a phone outside the
    office network, so it must never win over a real public origin.
    """
    env_url = (os.environ.get("OMNICUT_PUBLIC_URL") or "").strip().rstrip("/")
    if env_url:
        return env_url
    if request is not None:
        headers = request.headers
        host = (headers.get("x-forwarded-host") or headers.get("host") or "").split(",")[0].strip()
        proto = (headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
        hostname = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
        if host and hostname.lower() not in _LOCAL_HOSTNAMES:
            return f"{proto}://{host}"
    # https, not http: MobileFilmingPage.jsx's getUserMedia() is only exposed
    # by phone browsers in a secure context (https:// or localhost) --
    # frontend/vite.config.js's basicSsl() plugin serves the dev server over
    # self-signed https to match.
    return f"https://{local_ip}:5173"


@router.get("/api/status")
def get_system_status(request: Request, refresh_ip: bool = False):
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
        "mobile_url": _public_mobile_url(request, local_ip),
        "directories": {
            "base": str(BASE_DIR),
            "inbox": str(INBOX_DIR),
            "raw": str(RAW_DIR),
            "exports": str(EXPORTS_DIR),
            "assets": str(ASSETS_DIR),
            "capcut": str(CAPCUT_DRAFT_DIR)
        }
    }
