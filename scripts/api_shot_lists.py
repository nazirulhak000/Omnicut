"""
API Router for guided-take shot lists: generates a per-beat filming plan for
an angle from its real TTS voice timing, so the render pipeline can later map
footage onto script beats exactly instead of via AI vision matching.
See C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase A).
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from scripts.task_manager import TaskManager
from scripts.shot_list_builder import generate_shot_list_for_angle
from scripts.shot_lists_store import ShotListsStore
from scripts.gemini_tts_engine import GeminiTTSError
from scripts.quota import is_quota_error

from scripts.product_store import ProductStore
from scripts import path_utils

router = APIRouter(tags=["Shot Lists"])

_VOICE_OVERRIDE_KEYS = ("voice", "voice_rate", "voice_engine_type", "voice_preset", "ad_tone")


def _execute_generate_shot_list_worker(
    task_id: str, product_id: str, angle_id: str, voice_overrides: Dict[str, Any],
) -> None:
    try:
        TaskManager.update_progress(task_id, 0.20, "กำลังเตรียมสคริปต์และสังเคราะห์เสียงพากย์จริง")
        result = generate_shot_list_for_angle(product_id, angle_id, voice_overrides)
        TaskManager.update_progress(task_id, 0.90, "กำลังบันทึกแผนถ่าย")
        TaskManager.complete_task(
            task_id,
            result=result,
            step_label="🎬 สร้างแผนถ่ายสำเร็จ!",
            target_id=product_id,
        )
    except Exception as e:
        import traceback
        print(f"[API] Shot list generation error: {type(e).__name__}: {e}")
        traceback.print_exc()
        if hasattr(e, "message_th") and hasattr(e, "suggestion_th") and e.suggestion_th:
            err_msg = f"{e.message_th} — {e.suggestion_th}"
        elif hasattr(e, "message_th"):
            err_msg = e.message_th
        else:
            err_msg = str(e)

        if is_quota_error(e):
            TaskManager.fail_task(task_id, err_msg, step_label="เกินโควต้า AI ต่อวันแล้ว")
        else:
            TaskManager.fail_task(task_id, err_msg, step_label="สร้างแผนถ่ายไม่สำเร็จ")


@router.post("/api/products/{product_id}/angles/{angle_id}/shot-list")
def create_shot_list(
    product_id: str, angle_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks
):
    """Kicks off shot-list generation as a background task (same pattern as
    reroll-script, scripts/api_products.py's reroll_angle_script)."""
    voice_overrides = {
        key: payload.get(key) for key in _VOICE_OVERRIDE_KEYS if payload.get(key) is not None
    }

    task = TaskManager.create_task(
        task_type="generate_shot_list",
        title=f"สร้างแผนถ่าย: {angle_id}",
        payload={"product_id": product_id, "angle_id": angle_id, **voice_overrides},
        target_tab="flow",
        target_id=product_id,
    )

    background_tasks.add_task(
        _execute_generate_shot_list_worker,
        task["id"], product_id, angle_id, voice_overrides,
    )

    return {"success": True, "task_id": task["id"], "task": task}


@router.get("/api/products/{product_id}/angles/{angle_id}/shot-list")
def get_shot_list(product_id: str, angle_id: str):
    record = ShotListsStore.get(product_id, angle_id)
    if not record:
        raise HTTPException(status_code=404, detail="ยังไม่มีแผนถ่ายสำหรับมุมนี้")

    # Check if script has changed since this shot list was created
    is_stale = False
    product = ProductStore.get(product_id)
    if product:
        angle = next(
            (a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id),
            None,
        )
        if angle:
            lines = angle.get("tts_lines") or angle.get("script_lines") or []
            current_script = "\n".join(str(l).strip() for l in lines if str(l).strip())
            cached_script = str(record.get("custom_script") or "").strip()
            if current_script and cached_script and current_script != cached_script:
                is_stale = True

    res = dict(record)
    res["is_stale"] = is_stale
    return res


@router.get("/api/products/{product_id}/shot-list-status")
def get_shot_list_status(product_id: str):
    """Returns a map of angle_id → {has_shot_list, is_stale} for all angles
    of a product, so the sidebar can show badges in a single request instead
    of N+1 per-angle calls."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    result = {}
    for angle in product.get("angles", []):
        angle_id = angle.get("angle_id") or angle.get("id")
        if not angle_id:
            continue
        record = ShotListsStore.get(product_id, angle_id)
        if record:
            lines = angle.get("tts_lines") or angle.get("script_lines") or []
            current_script = "\n".join(str(l).strip() for l in lines if str(l).strip())
            cached_script = str(record.get("custom_script") or "").strip()
            is_stale = bool(current_script and cached_script and current_script != cached_script)
            vp = record.get("voice_params") or {}
            engine = vp.get("voice_engine_type") or ("gemini_tts" if vp.get("voice_preset") else "edge_tts")
            preset = vp.get("voice_preset")
            is_edge = (engine == "edge_tts" or not preset)
            result[angle_id] = {
                "has_shot_list": True,
                "is_stale": is_stale,
                "voice_engine_type": engine,
                "voice_preset": preset,
                "is_edge_tts": is_edge,
            }
        else:
            result[angle_id] = {
                "has_shot_list": False,
                "is_stale": False,
                "voice_engine_type": None,
                "voice_preset": None,
                "is_edge_tts": False,
            }

    return {"product_id": product_id, "status": result}


def _execute_batch_generate_audio_worker(
    task_id: str,
    product_id: str,
    payload: Dict[str, Any],
) -> None:
    """Worker for batch generating TTS audio and shot lists across all angles of a product,
    with smart skipping of existing audio and automatic cooldown on HTTP 429 Rate Limits."""
    import time
    try:
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        voice_preset = payload.get("voice_preset") or "gemini_puck_male_hype"
        ad_tone = payload.get("ad_tone") or "commercial_hype"
        batch_index = payload.get("batch_index")
        force_regenerate = payload.get("force_regenerate", False)

        angles = product.get("angles", [])
        if batch_index is not None:
            angles = [a for a in angles if a.get("batch") == batch_index]

        # Filter angles that have script lines AND are not already rendered/posted (unless force_regenerate)
        valid_angles = []
        for a in angles:
            if not force_regenerate and (a.get("status") in ("rendered", "posted") or a.get("posted_at")):
                continue
            lines = a.get("tts_lines") or a.get("script_lines") or []
            if any(str(l).strip() for l in lines):
                valid_angles.append(a)

        if not valid_angles:
            TaskManager.complete_task(
                task_id,
                result={"total": 0, "generated": 0, "skipped": 0},
                step_label="ไม่มีสคริปต์ที่ต้องสร้างเสียงพากย์ (คลิปตัดเสร็จ/โพสต์แล้วทั้งหมด)",
                target_id=product_id,
            )
            return

        total_angles = len(valid_angles)
        generated_count = 0
        skipped_count = 0

        voice_overrides = {
            "voice_engine_type": "gemini_tts",
            "voice_preset": voice_preset,
            "voice_rate": "+15%",
            "ad_tone": ad_tone,
        }

        TaskManager.update_progress(
            task_id, 0.05, f"กำลังเตรียมคิวเสียงพากย์ {total_angles} มุม..."
        )

        for idx, angle in enumerate(valid_angles, 1):
            angle_id = angle.get("angle_id") or angle.get("id")
            angle_title = angle.get("hook_title") or angle.get("angle_name") or f"มุมที่ {idx}"
            short_title = angle_title[:32] + "..." if len(angle_title) > 32 else angle_title

            # Skip rendered or posted angles
            if not force_regenerate and (angle.get("status") in ("rendered", "posted") or angle.get("posted_at")):
                skipped_count += 1
                pct = (idx / total_angles) * 0.95
                TaskManager.update_progress(
                    task_id, pct, f"⏭️ ({idx}/{total_angles}) ข้ามคลิปที่เสร็จ/โพสต์แล้ว: {short_title}"
                )
                continue

            # Check if voice audio is already cached and valid
            if not force_regenerate:
                rec = ShotListsStore.get(product_id, angle_id)
                if rec and rec.get("voice_audio_path"):
                    audio_p = Path(rec["voice_audio_path"])
                    if audio_p.exists() and audio_p.stat().st_size > 0:
                        lines = angle.get("tts_lines") or angle.get("script_lines") or []
                        current_script = "\n".join(str(l).strip() for l in lines if str(l).strip())
                        cached_script = str(rec.get("custom_script") or "").strip()
                        rec_params = rec.get("voice_params") or {}
                        rec_preset = rec_params.get("voice_preset")
                        rec_engine = rec_params.get("voice_engine_type") or ("gemini_tts" if rec_preset else "edge_tts")
                        is_valid_gemini = (rec_engine != "edge_tts" and bool(rec_preset))
                        if is_valid_gemini and current_script == cached_script and rec_preset == voice_preset:
                            skipped_count += 1
                            pct = (idx / total_angles) * 0.95
                            TaskManager.update_progress(
                                task_id, pct, f"⏭️ ({idx}/{total_angles}) มีเสียงพากย์ Gemini แล้ว: {short_title}"
                            )
                            continue

            # Generate with auto 429 rate-limit cooldown
            max_angle_retries = 6
            angle_success = False

            for attempt in range(max_angle_retries):
                pct = ((idx - 1) / total_angles) * 0.95 + 0.02
                TaskManager.update_progress(
                    task_id, pct, f"🎙️ ({idx}/{total_angles}) กำลังสังเคราะห์เสียง: {short_title}"
                )
                try:
                    generate_shot_list_for_angle(product_id, angle_id, voice_overrides)
                    angle_success = True
                    generated_count += 1
                    break
                except Exception as e:
                    delay_seconds = getattr(e, "retry_delay_seconds", None)
                    is_rate_limit = (
                        isinstance(e, GeminiTTSError) and e.code == "GEMINI_TTS_RATE_LIMITED"
                    ) or "429" in str(e) or "rate" in str(e).lower()

                    if is_rate_limit and attempt < max_angle_retries - 1:
                        # Auto-sleep cooldown with live countdown in task progress
                        wait_sec = int(delay_seconds) if (delay_seconds and delay_seconds > 0) else 20
                        wait_sec = max(10, min(wait_sec, 60))
                        for rem in range(wait_sec, 0, -1):
                            TaskManager.update_progress(
                                task_id,
                                pct,
                                f"⏳ ติด Rate Limit (429) — พักรออีก {rem} วินาที แล้วจะทำมุม ({idx}/{total_angles}) ต่ออัตโนมัติ...",
                            )
                            time.sleep(1)
                        continue
                    else:
                        print(f"[BatchAudio] Angle {angle_id} failed after {attempt + 1} attempts: {e}")
                        break

        TaskManager.complete_task(
            task_id,
            result={
                "product_id": product_id,
                "total": total_angles,
                "generated": generated_count,
                "skipped": skipped_count,
                "voice_preset": voice_preset,
            },
            step_label=f"🎉 สังเคราะห์เสียงพากย์เสร็จสิ้น: สร้างใหม่ {generated_count} มุม (ข้าม {skipped_count} มุม)",
            target_id=product_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_msg = getattr(e, "message_th", str(e))
        TaskManager.fail_task(task_id, err_msg, step_label="สร้างเสียงพากย์แบบ Batch ไม่สำเร็จ")


@router.post("/api/products/{product_id}/batch-generate-audio")
def batch_generate_audio(
    product_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
):
    """Kicks off batch TTS pre-generation for all angles of a product as a background task.
    Skips angles that already have valid audio, and automatically cools down on 429 rate limits."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    batch_idx = payload.get("batch_index")
    batch_label = f"ล็อตที่ {batch_idx}" if batch_idx is not None else "ทุกล็อต"
    preset_name = payload.get("voice_preset", "gemini_puck_male_hype")
    force_regenerate = payload.get("force_regenerate", False)

    angles = product.get("angles", [])
    if batch_idx is not None:
        angles = [a for a in angles if a.get("batch") == batch_idx]

    if not force_regenerate:
        active_angles = [
            a for a in angles
            if a.get("status") not in ("rendered", "posted") and not a.get("posted_at")
        ]
    else:
        active_angles = angles

    task = TaskManager.create_task(
        task_type="batch_generate_audio",
        title=f"เตรียมเสียงพากย์: {product.get('name', product_id)} ({batch_label})",
        payload={"product_id": product_id, "voice_preset": preset_name, **payload},
        target_tab="flow",
        target_id=product_id,
    )

    background_tasks.add_task(
        _execute_batch_generate_audio_worker,
        task["id"],
        product_id,
        payload,
    )

    return {"success": True, "task_id": task["id"], "task": task, "angle_count": len(active_angles)}


# ─── Manual Storyboard Mapper endpoints ───────────────────────────────────────

@router.patch("/api/products/{product_id}/angles/{angle_id}/manual-shot-map")
def save_manual_shot_map(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Persists the user's curated shot-map for an angle.

    Body: { "shot_map": [ { "beat_index": 0, "video_path": "...", "trim_start": 1.2, "trim_end": 3.8 }, ... ] }
    Entries with beat_index but no video_path are treated as "let AI decide" (will be ignored by pipeline).
    Returns the updated angle record.
    """
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    shot_map = payload.get("shot_map")
    if shot_map is None:
        raise HTTPException(status_code=422, detail="ต้องระบุ shot_map")
    if not isinstance(shot_map, list):
        raise HTTPException(status_code=422, detail="shot_map ต้องเป็น list")

    # Validate each entry minimally (beat_index required; video_path may be absent for AI-auto slots)
    validated = []
    for entry in shot_map:
        if not isinstance(entry, dict):
            continue
        beat_idx = entry.get("beat_index")
        if beat_idx is None:
            continue
        v_raw = entry.get("video_path")
        clean_v = None
        if v_raw:
            from scripts import path_utils
            rel_v = path_utils.to_relative(v_raw)
            clean_v = str(rel_v).replace("\\", "/") if rel_v else str(v_raw).replace("\\", "/")
        validated.append({
            "beat_index": int(beat_idx),
            "video_path": clean_v,
            "trim_start": float(entry.get("trim_start") or 0.0),
            "trim_end": float(entry.get("trim_end") or 0.0),
        })

    try:
        ProductStore.update_angle_manual_shot_map(product_id, angle_id, validated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"success": True, "product_id": product_id, "angle_id": angle_id, "pinned_count": len(validated)}


@router.get("/api/products/{product_id}/angles/{angle_id}/manual-shot-map")
def get_manual_shot_map(product_id: str, angle_id: str):
    """Returns the saved manual shot-map for an angle, together with the beat_cues timing
    (so the frontend can render the storyboard UI from a single request).

    Returns:
        {
          "manual_shot_map": [...],   # currently pinned assignments (may be empty)
          "beat_cues": [...],         # TTS-timed beat cues from the shot list
          "total_duration": float,
          "has_shot_list": bool,
          "scene_catalogs": {video_path: catalog},  # indexed catalogs for selected videos
        }
    """
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    angle = next(
        (a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id),
        None,
    )
    if not angle:
        raise HTTPException(status_code=404, detail=f"ไม่พบมุม '{angle_id}'")

    # Pull existing shot list (beat_cues, total_duration) from ShotListsStore
    shot_list_record = ShotListsStore.get(product_id, angle_id)
    beat_cues = []
    total_duration = 0.0
    has_shot_list = False
    if shot_list_record:
        beat_cues = shot_list_record.get("beat_cues") or []
        total_duration = float(shot_list_record.get("total_duration") or 0.0)
        has_shot_list = True

    # Collect scene catalogs for all candidate videos of this angle and product
    try:
        from scripts.gemini_vision_matcher import GeminiVisionMatcher
        from scripts.config import BASE_DIR
        from scripts import path_utils
        scene_catalogs = {}
        all_candidate_videos = list(angle.get("selected_videos") or [])
        if angle.get("selected_video") and angle["selected_video"] not in all_candidate_videos:
            all_candidate_videos.append(angle["selected_video"])
        for v_item in product.get("videos") or []:
            v_p = v_item.get("rel_path") or v_item.get("path")
            if v_p and v_p not in all_candidate_videos:
                all_candidate_videos.append(v_p)

        for v_raw in all_candidate_videos:
            if not v_raw:
                continue
            from pathlib import Path as _Path
            v_full = _Path(v_raw)
            if not v_full.is_absolute():
                v_full = BASE_DIR / v_raw
            catalog = GeminiVisionMatcher.get_cached_catalog(str(v_full))
            if catalog:
                rel_p = path_utils.to_relative(v_full)
                rel_key = str(rel_p).replace("\\", "/") if rel_p else str(v_raw).replace("\\", "/")
                cat_dict = {
                    "is_indexed": True,
                    "scenes_count": len(catalog.get("scenes", [])),
                    "is_spin_footage": catalog.get("is_spin_footage", False),
                    "summary": catalog.get("summary", ""),
                    "scenes": catalog.get("scenes", []),
                }
                # Index under all variants so frontend can always find it
                scene_catalogs[rel_key] = cat_dict
                scene_catalogs[str(v_raw)] = cat_dict
                scene_catalogs[str(v_raw).replace("\\", "/")] = cat_dict
                scene_catalogs[str(v_full)] = cat_dict
                scene_catalogs[str(v_full).replace("\\", "/")] = cat_dict
                scene_catalogs[v_full.name] = cat_dict
    except Exception:
        scene_catalogs = {}

    # Resolve manual_shot_map video_path entries to normalized relative paths for the frontend
    raw_map = angle.get("manual_shot_map") or []
    resolved_map = []
    for entry in raw_map:
        e = dict(entry)
        if e.get("video_path"):
            rel_p = path_utils.to_relative(e["video_path"])
            e["video_path"] = str(rel_p).replace("\\", "/") if rel_p else str(e["video_path"]).replace("\\", "/")
        resolved_map.append(e)

    return {
        "product_id": product_id,
        "angle_id": angle_id,
        "manual_shot_map": resolved_map,
        "beat_cues": beat_cues,
        "total_duration": total_duration,
        "has_shot_list": has_shot_list,
        "scene_catalogs": scene_catalogs,
    }
