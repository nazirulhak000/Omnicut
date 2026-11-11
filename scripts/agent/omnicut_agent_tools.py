"""OmniCut Pro Studio - NLE Timeline Manipulation & Action Tools for AI Agent.

Provides structured tools that allow the AI Agent to inspect projects,
propose non-destructive NLE timeline edits, and execute approved action proposals.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("omnicut.agent.tools")

PROJECTS_DIR = Path("03_Projects")


def _resolve_project_path(project_name: str) -> Path:
    proj_dir = PROJECTS_DIR / project_name
    if not proj_dir.is_dir():
        raise FileNotFoundError(f"Project directory '{project_name}' not found in 03_Projects")
    proj_json = proj_dir / "project.json"
    if not proj_json.is_file():
        raise FileNotFoundError(f"project.json missing for project '{project_name}'")
    return proj_json


def load_project_manifest(project_name: str) -> Dict[str, Any]:
    proj_json = _resolve_project_path(project_name)
    with open(proj_json, "r", encoding="utf-8") as f:
        return json.load(f)


def save_project_manifest(project_name: str, data: Dict[str, Any]) -> None:
    proj_json = _resolve_project_path(project_name)
    # Create safety backup before saving
    bak_path = proj_json.with_suffix(".json.bak")
    try:
        shutil.copy2(proj_json, bak_path)
    except Exception as e:
        logger.warning(f"Could not create backup for {project_name}: {e}")

    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(proj_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_timeline_summary(project_name: str) -> Dict[str, Any]:
    """Inspects the project and returns a clean, structured summary for the AI."""
    manifest = load_project_manifest(project_name)
    clips = manifest.get("clip_list", [])
    cues = manifest.get("cues", [])
    total_dur = manifest.get("total_duration", 0.0)

    clip_summaries = []
    accum_time = 0.0
    for idx, c in enumerate(clips):
        dur = float(c.get("duration", 0.0) or (c.get("target_end", 0.0) - c.get("target_start", 0.0)) or 0.0)
        clip_summaries.append({
            "index": idx,
            "file": Path(c.get("file_path", "")).name if c.get("file_path") else f"Clip #{idx+1}",
            "start": round(accum_time, 2),
            "end": round(accum_time + dur, 2),
            "duration": round(dur, 2),
        })
        accum_time += dur

    return {
        "project_name": project_name,
        "total_duration": round(total_dur or accum_time, 2),
        "clip_count": len(clips),
        "clips": clip_summaries,
        "subtitle_count": len(cues),
        "audio_levels": {
            "voice_volume": manifest.get("voice_volume", 1.0),
            "sfx_volume": manifest.get("sfx_volume", 0.28),
            "bgm_volume": manifest.get("bgm_volume", 0.12),
        },
        "style": {
            "font_name": manifest.get("font_name", "Mali-Bold"),
            "caption_scale": manifest.get("caption_scale", 1.0),
            "caption_color": manifest.get("caption_color", "#FFFFFF"),
        },
    }


def propose_split_clip(project_name: str, split_time: float) -> Dict[str, Any]:
    """Proposes splitting a video clip at the given timestamp (seconds)."""
    manifest = load_project_manifest(project_name)
    clips = manifest.get("clip_list", [])

    accum_time = 0.0
    target_idx = -1
    offset_in_clip = 0.0

    for idx, c in enumerate(clips):
        dur = float(c.get("duration", 0.0) or (c.get("target_end", 0.0) - c.get("target_start", 0.0)) or 0.0)
        if accum_time <= split_time <= accum_time + dur:
            target_idx = idx
            offset_in_clip = split_time - accum_time
            break
        accum_time += dur

    if target_idx == -1:
        return {
            "error": f"Split time {split_time:.2f}s is outside project timeline bounds (0 to {accum_time:.2f}s)"
        }

    return {
        "action_id": f"act_split_{int(time.time()*1000)}",
        "action_type": "split_clip",
        "title": f"ตัดแยกคลิป #{target_idx+1} ที่เวลา {split_time:.2f}วิ",
        "description": f"แยกคลิป #{target_idx+1} ออกเป็น 2 คลิปย่อย ณ ตำแหน่ง {split_time:.2f}s",
        "payload": {
            "project_name": project_name,
            "clip_index": target_idx,
            "split_time": round(split_time, 3),
            "offset_in_clip": round(offset_in_clip, 3),
        },
    }


def propose_audio_mix(
    project_name: str,
    voice_volume: Optional[float] = None,
    sfx_volume: Optional[float] = None,
    bgm_volume: Optional[float] = None,
) -> Dict[str, Any]:
    """Proposes adjusting audio bus volumes (voice, sfx, bgm)."""
    manifest = load_project_manifest(project_name)
    current_v = manifest.get("voice_volume", 1.0)
    current_s = manifest.get("sfx_volume", 0.28)
    current_b = manifest.get("bgm_volume", 0.12)

    new_v = round(voice_volume if voice_volume is not None else current_v, 2)
    new_s = round(sfx_volume if sfx_volume is not None else current_s, 2)
    new_b = round(bgm_volume if bgm_volume is not None else current_b, 2)

    return {
        "action_id": f"act_mix_{int(time.time()*1000)}",
        "action_type": "audio_mix",
        "title": "ปรับระดับเสียง 4 บัส (Audio Mix)",
        "description": f"ปรับระดับเสียง Voice: {new_v} | SFX: {new_s} | BGM: {new_b}",
        "payload": {
            "project_name": project_name,
            "voice_volume": new_v,
            "sfx_volume": new_s,
            "bgm_volume": new_b,
        },
    }


def propose_subtitles_style(
    project_name: str,
    font_name: Optional[str] = None,
    caption_scale: Optional[float] = None,
    caption_color: Optional[str] = None,
) -> Dict[str, Any]:
    """Proposes updating subtitle typography or colors."""
    manifest = load_project_manifest(project_name)
    cur_f = manifest.get("font_name", "Mali-Bold")
    cur_s = manifest.get("caption_scale", 1.0)
    cur_c = manifest.get("caption_color", "#FFFFFF")

    new_f = font_name or cur_f
    new_s = caption_scale if caption_scale is not None else cur_s
    new_c = caption_color or cur_c

    return {
        "action_id": f"act_sub_{int(time.time()*1000)}",
        "action_type": "subtitle_style",
        "title": f"เปลี่ยนสไตล์ซับไตเติลเป็น {new_f}",
        "description": f"ฟอนต์: {new_f}, ขนาด: {new_s}x, สีตัวอักษร: {new_c}",
        "payload": {
            "project_name": project_name,
            "font_name": new_f,
            "caption_scale": new_s,
            "caption_color": new_c,
        },
    }


def apply_smart_camera_9_16(
    project_name: str,
    clip_index: int = 0,
    preset: str = "slow_push",
    easing: str = "hero_in",
) -> Dict[str, Any]:
    """Proposes applying CapCut 7.1 9:16 Smart Camera Motion & Cubic-Bezier Easing (W3.6)."""
    from scripts.keyframe_engine import generate_smart_camera_keyframes

    manifest = load_project_manifest(project_name)
    clips = manifest.get("clip_list", [])
    dur = 3.0
    if 0 <= clip_index < len(clips):
        c = clips[clip_index]
        dur = float(c.get("duration") or ((c.get("trim_end") or 3.0) - (c.get("trim_start") or 0.0)) or 3.0)
    kfs = generate_smart_camera_keyframes(duration=max(0.5, dur), preset=preset)
    for kf in kfs:
        if isinstance(kf, dict) and float(kf.get("time", 0.0)) > 0:
            kf["easing"] = easing
    return {
        "action_id": f"act_cam_{int(time.time()*1000)}",
        "action_type": "apply_smart_camera_9_16",
        "title": f"ตั้งกล้องอัจฉริยะ 9:16 ({preset} / {easing}) คลิป #{clip_index + 1}",
        "description": f"ซูมฐาน 1.25x กันขอบดำ + โค้งความเร็ว Cubic-Bezier ({easing})",
        "payload": {
            "project_name": project_name,
            "clip_index": clip_index,
            "preset": preset,
            "easing": easing,
            "keyframes": kfs,
        },
    }


def apply_pro_color_grade(
    project_name: str,
    clip_index: int = 0,
    shadows: float = 0.25,
    highlights: float = -0.15,
    vibrance: float = 0.35,
    vignette: float = 0.20,
    temperature: float = 0.05,
    gamma: float = 1.05,
    brightness: float = 1.0,
    contrast: float = 1.0,
) -> Dict[str, Any]:
    """Proposes applying In-App Pro Studio Color Grade (Shadows/Highlights/Vibrance/Vignette) (M6)."""
    return {
        "action_id": f"act_color_{int(time.time()*1000)}",
        "action_type": "apply_pro_color_grade",
        "title": f"เกรดสีระดับโปรครบวงจร คลิป #{clip_index + 1}",
        "description": (
            f"Shadows: {shadows:+.2f} | Highlights: {highlights:+.2f} | "
            f"Vibrance: {vibrance:+.2f} | Vignette: {vignette:+.2f}"
        ),
        "payload": {
            "project_name": project_name,
            "clip_index": clip_index,
            "shadows": round(float(shadows), 3),
            "highlights": round(float(highlights), 3),
            "vibrance": round(float(vibrance), 3),
            "vignette": round(float(vignette), 3),
            "temperature": round(float(temperature), 3),
            "gamma": round(float(gamma), 3),
            "brightness": round(float(brightness), 3),
            "contrast": round(float(contrast), 3),
        },
    }


def apply_capcut_color_grade(
    project_name: str,
    clip_index: int = 0,
    shadows: float = 0.25,
    highlights: float = -0.15,
    vibrance: float = 0.35,
    vignette: float = 0.20,
    temperature: float = 0.05,
    gamma: float = 1.05,
) -> Dict[str, Any]:
    """Backward-compatible alias for apply_pro_color_grade."""
    return apply_pro_color_grade(
        project_name=project_name,
        clip_index=clip_index,
        shadows=shadows,
        highlights=highlights,
        vibrance=vibrance,
        vignette=vignette,
        temperature=temperature,
        gamma=gamma,
    )


def apply_viral_transitions(
    project_name: str,
    transition_name: str = "whip_pan",
    duration: float = 0.4,
) -> Dict[str, Any]:
    """Proposes applying viral high-speed transitions across clips in the project timeline (M6)."""
    valid_transitions = {"whip_pan", "zoom_in_punch", "flash_white", "glitch_shake"}
    clean_trans = transition_name if transition_name in valid_transitions else "whip_pan"
    return {
        "action_id": f"act_trans_{int(time.time()*1000)}",
        "action_type": "apply_viral_transitions",
        "title": f"ใส่ทรานซิชันไวรัล {clean_trans} ข้ามทุกช็อต",
        "description": f"รูปแบบ: {clean_trans} | ความยาว: {duration:.2f}s | อัปเดตรอยต่อระหว่างคลิปอัตโนมัติ",
        "payload": {
            "project_name": project_name,
            "transition_name": clean_trans,
            "duration": round(float(duration), 2),
        },
    }


def normalize_project_audio_lufs(
    project_name: str,
    target_lufs: float = -14.0,
    voice_clarity: bool = True,
) -> Dict[str, Any]:
    """Proposes normalizing project audio to -14 LUFS + enabling RNNoise/SAMI Voice Clarity (W3.6)."""
    return {
        "action_id": f"act_lufs_{int(time.time()*1000)}",
        "action_type": "normalize_project_audio_lufs",
        "title": f"ปรับเสียงมาตรฐาน {target_lufs:.1f} LUFS + เปิดเสียงใสตัดนอยส์",
        "description": (
            f"ปรับสมดุล 4 บัส (Voice 1.0, SFX 0.28, BGM 0.12) เป้าหมาย {target_lufs:.1f} LUFS "
            f"พร้อม RNNoise + SAMI Voice Clarity ({'เปิด' if voice_clarity else 'ปิด'})"
        ),
        "payload": {
            "project_name": project_name,
            "target_lufs": round(float(target_lufs), 2),
            "voice_clarity": bool(voice_clarity),
            "voice_volume": 1.0,
            "sfx_volume": 0.28,
            "bgm_volume": 0.12,
        },
    }


def export_or_import_capcut_draft(
    project_name: str,
    mode: str = "export",
) -> Dict[str, Any]:
    """Proposes exporting or importing a CapCut Desktop v7.1.0 draft (version 360000 / 144.0.0) (W3.6)."""
    clean_mode = "import" if str(mode).lower() == "import" else "export"
    label = "นำเข้าดราฟต์ CapCut 7.1 เข้าไทม์ไลน์" if clean_mode == "import" else "ส่งออกดราฟต์ CapCut 7.1 (Schema 360000)"
    return {
        "action_id": f"act_ccdraft_{int(time.time()*1000)}",
        "action_type": "export_or_import_capcut_draft",
        "title": label,
        "description": f"โหมด: {clean_mode.upper()} | โปรเจกต์: {project_name} (CapCut v7.1.0 / 144.0.0)",
        "payload": {
            "project_name": project_name,
            "mode": clean_mode,
        },
    }


def apply_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a previously proposed action proposal upon user approval."""
    action_type = action.get("action_type")
    payload = action.get("payload", {})
    project_name = payload.get("project_name")

    if not project_name:
        raise ValueError("Missing project_name in action payload")

    manifest = load_project_manifest(project_name)

    if action_type == "audio_mix":
        if "voice_volume" in payload:
            manifest["voice_volume"] = payload["voice_volume"]
        if "sfx_volume" in payload:
            manifest["sfx_volume"] = payload["sfx_volume"]
        if "bgm_volume" in payload:
            manifest["bgm_volume"] = payload["bgm_volume"]
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"ปรับระดับเสียงโปรเจกต์ {project_name} เรียบร้อยแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "subtitle_style":
        if "font_name" in payload:
            manifest["font_name"] = payload["font_name"]
        if "caption_scale" in payload:
            manifest["caption_scale"] = payload["caption_scale"]
        if "caption_color" in payload:
            manifest["caption_color"] = payload["caption_color"]
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"เปลี่ยนสไตล์ซับไตเติลโปรเจกต์ {project_name} เรียบร้อยแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "split_clip":
        clip_idx = payload.get("clip_index")
        offset = payload.get("offset_in_clip", 0.0)
        clips = manifest.get("clip_list", [])

        if clip_idx is None or clip_idx >= len(clips):
            raise ValueError(f"Invalid clip index {clip_idx}")

        original = clips[clip_idx]
        old_dur = float(original.get("duration", 0.0) or 0.0)

        # Clone and split
        clip1 = dict(original)
        clip2 = dict(original)

        clip1["duration"] = round(offset, 3)
        clip1["target_end"] = round(float(original.get("target_start", 0.0)) + offset, 3)

        clip2["duration"] = round(old_dur - offset, 3)
        clip2["target_start"] = round(float(original.get("target_start", 0.0)) + offset, 3)

        # Replace 1 clip with 2 clips
        new_clips = clips[:clip_idx] + [clip1, clip2] + clips[clip_idx + 1 :]
        manifest["clip_list"] = new_clips
        save_project_manifest(project_name, manifest)

        return {
            "success": True,
            "message": f"ตัดแยกคลิป #{clip_idx+1} สำเร็จแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "apply_smart_camera_9_16":
        clip_idx = int(payload.get("clip_index", 0))
        clips = list(manifest.get("clip_list") or [])
        if not clips:
            clips = [{"file_path": "video.mp4", "duration": 5.0, "target_start": 0.0, "target_end": 5.0}]
        target_i = min(max(0, clip_idx), len(clips) - 1)
        clip_obj = dict(clips[target_i])
        clip_obj["smart_camera_preset"] = payload.get("preset", "slow_push")
        clip_obj["keyframe_easing"] = payload.get("easing", "hero_in")
        clip_obj["zoom"] = 1.25
        if payload.get("keyframes"):
            clip_obj["keyframes"] = payload["keyframes"]
        clips[target_i] = clip_obj
        manifest["clip_list"] = clips
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"ตั้งกล้องอัจฉริยะ 9:16 ({clip_obj['smart_camera_preset']}) ให้คลิป #{target_i + 1} สำเร็จแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type in ("apply_pro_color_grade", "apply_capcut_color_grade"):
        clip_idx = int(payload.get("clip_index", 0))
        clips = list(manifest.get("clip_list") or [])
        if not clips:
            clips = [{"file_path": "video.mp4", "duration": 5.0, "target_start": 0.0, "target_end": 5.0}]
        target_i = min(max(0, clip_idx), len(clips) - 1)
        clip_obj = dict(clips[target_i])
        for k in ("shadows", "highlights", "vibrance", "vignette", "temperature", "gamma", "brightness", "contrast"):
            if k in payload:
                clip_obj[k] = payload[k]
        clips[target_i] = clip_obj
        manifest["clip_list"] = clips
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"เกรดสีระดับโปรครบวงจรให้คลิป #{target_i + 1} สำเร็จแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "apply_viral_transitions":
        trans_name = str(payload.get("transition_name", "whip_pan"))
        dur = float(payload.get("duration", 0.4))
        clips = list(manifest.get("clip_list") or [])
        if not clips:
            clips = [{"file_path": "video.mp4", "duration": 5.0, "target_start": 0.0, "target_end": 5.0}]
        applied_count = 0
        for i in range(1, len(clips)):
            c = dict(clips[i])
            c["transition_in"] = trans_name
            c["transition_duration"] = dur
            clips[i] = c
            applied_count += 1
        manifest["clip_list"] = clips
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"ใส่ทรานซิชันไวรัล {trans_name} ({dur}s) ให้ {applied_count} รอยต่อเรียบร้อยแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "normalize_project_audio_lufs":
        manifest["voice_volume"] = float(payload.get("voice_volume", 1.0))
        manifest["sfx_volume"] = float(payload.get("sfx_volume", 0.28))
        manifest["bgm_volume"] = float(payload.get("bgm_volume", 0.12))
        manifest["target_lufs"] = float(payload.get("target_lufs", -14.0))
        manifest["voice_clarity"] = bool(payload.get("voice_clarity", True))
        rp = dict(manifest.get("render_params") or {})
        rp["voice_clarity"] = manifest["voice_clarity"]
        rp["target_lufs"] = manifest["target_lufs"]
        manifest["render_params"] = rp
        save_project_manifest(project_name, manifest)
        return {
            "success": True,
            "message": f"ปรับระดับเสียงมาตรฐาน {manifest['target_lufs']} LUFS และเปิดเสียงใสตัดนอยส์เรียบร้อยแล้ว",
            "manifest": get_timeline_summary(project_name),
        }

    elif action_type == "export_or_import_capcut_draft":
        from scripts.capcut_builder import CapCutBuilder, import_capcut_draft_to_manifest

        mode = str(payload.get("mode", "export")).lower()
        proj_dir = _resolve_project_path(project_name).parent
        draft_dir = proj_dir / "capcut_draft_7_1"
        draft_dir.mkdir(parents=True, exist_ok=True)
        content_file = draft_dir / "draft_content.json"

        builder = CapCutBuilder(project_name=project_name, draft_root=proj_dir)
        cues = manifest.get("cues") or manifest.get("micro_cues") or []
        clips = manifest.get("clip_list") or []
        stickers = manifest.get("stickers") or []
        duration = float(manifest.get("audio_duration") or manifest.get("total_duration") or 15.0)

        if mode == "import" and content_file.is_file():
            draft_data = json.loads(content_file.read_text(encoding="utf-8"))
            updated = import_capcut_draft_to_manifest(draft_data, base_manifest=manifest)
            save_project_manifest(project_name, updated)
            return {
                "success": True,
                "message": f"นำเข้าดราฟต์ CapCut 7.1 กลับเข้าโปรเจกต์ {project_name} สำเร็จแล้ว",
                "draft_content_path": str(content_file),
                "manifest": get_timeline_summary(project_name),
            }
        else:
            draft_data = builder._create_draft_content(
                video_path=Path("video.mp4"),
                audio_path=Path("voiceover.wav"),
                cues=cues,
                total_dur_us=int(max(1.0, duration) * 1_000_000),
                clips=clips,
                stickers=stickers,
            )
            if content_file.is_file():
                # AGENTS.md rule 3: never overwrite a CapCut draft without a backup.
                backup_file = content_file.with_name(
                    f"{content_file.name}.{time.strftime('%Y%m%d_%H%M%S')}.bak"
                )
                shutil.copy2(content_file, backup_file)
            content_file.write_text(json.dumps(draft_data, ensure_ascii=False, indent=2), encoding="utf-8")
            if mode == "import":
                updated = import_capcut_draft_to_manifest(draft_data, base_manifest=manifest)
                save_project_manifest(project_name, updated)
            return {
                "success": True,
                "message": f"ส่งออกดราฟต์ CapCut 7.1 สำหรับ {project_name} สำเร็จแล้ว",
                "draft_content_path": str(content_file),
                "manifest": get_timeline_summary(project_name),
            }

    else:
        raise ValueError(f"Unsupported action type: {action_type}")
