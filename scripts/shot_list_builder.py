"""
Shot-list builder for the guided-take filming feature.

Generates a per-beat filming plan for one product angle, tied to the exact
TTS voice timing (not a text-length estimate), so the user can film to it
without relying on AI vision to guess which part of the raw footage matches
which script line. See C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md
(Phase A) for the full design.

Deliberately runs only ScriptStage + VoiceStage against a scratch
PipelineContext -- no raw video exists yet at this point, and this only
needs `PipelineContext.beat_cues` (one real-timed cue per script line), not
the subtitle-burst-level `micro_cues` SubtitleStage would additionally
produce.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scripts.config import PROJECTS_DIR, DEFAULT_VOICE, DEFAULT_VOICE_RATE
from scripts.pipeline_context import PipelineContext
from scripts.stages.script_stage import ScriptStage
from scripts.stages.voice_stage import VoiceStage
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore

_VOICE_OVERRIDE_KEYS = ("voice", "voice_rate", "voice_engine_type", "voice_preset", "ad_tone")


def assign_beat_role(index: int, total: int) -> str:
    """Position-based role assignment -- mirrors the exact convention
    scripts/script_generator.py already uses for SFX pool assignment
    (idx==0 opener, idx==last closer, else accent), so a beat's role here
    always agrees with the SFX/tone treatment that beat already gets
    elsewhere in the pipeline."""
    if total <= 1:
        return "hook"
    if index == 0:
        return "hook"
    if index == total - 1:
        return "cta"
    return "feature"


def camera_direction_for_beat(
    role: str,
    index: int,
    beat_text: str,
    on_screen: str,
    product_name: str,
) -> str:
    """Deterministic templated Thai filming direction -- no AI call, so
    generating a shot list never costs AI quota or depends on network
    availability, matching the whole feature's premise of removing AI
    dependency from the footage-matching step."""
    if role == "hook":
        return (
            f"ตั้งกล้อง/มือถือมุมเดียว ระยะ Medium shot ระดับอก ห้ามขยับกล้องตลอดคลิป — "
            f"ถือหรือวาง {product_name} ให้เห็นชัดกลางเฟรม พูดพร้อมแอคชั่นแนะนำตัวสินค้า"
        )
    if role == "cta":
        base = (
            "ชี้/แตะราคาหรือตะกร้าสินค้าให้เห็นชัดในเฟรม — "
            "อาจถ่ายแยกเป็นคลิปโคลสอัพต่างหากจากเทกหลักได้ (กล้องขยับเข้าใกล้ได้เฉพาะช็อตนี้)"
        )
        return base
    if on_screen:
        return f"ทำแอคชั่นตามบทพูด พร้อมโชว์ '{on_screen}' ให้เห็นในเฟรม — กล้องมุมเดิมไม่ขยับ"
    return "ทำแอคชั่นมือกับสินค้าให้ตรงกับบทพูดช่วงนี้ — กล้องมุมเดิมไม่ขยับ"


def build_shot_list(beat_cues: List[Dict[str, Any]], product_name: str) -> List[Dict[str, Any]]:
    total = len(beat_cues)
    shot_list: List[Dict[str, Any]] = []
    for index, cue in enumerate(beat_cues):
        role = assign_beat_role(index, total)
        start = float(cue.get("start", 0.0))
        end = float(cue.get("end", 0.0))
        shot_list.append({
            "beat_index": index,
            "role": role,
            "text": cue.get("text", ""),
            "start": round(start, 3),
            "end": round(end, 3),
            "planned_duration": round(max(0.0, end - start), 3),
            "camera_direction": camera_direction_for_beat(
                role, index, cue.get("text", ""), cue.get("on_screen", ""), product_name
            ),
            "on_screen": cue.get("on_screen", ""),
            "is_separate_clip": index == total - 1 and total > 1,
        })
    return shot_list


def _find_angle(product: Dict[str, Any], angle_id: str) -> Optional[Dict[str, Any]]:
    return next(
        (a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id),
        None,
    )


def generate_shot_list_for_angle(
    product_id: str,
    angle_id: str,
    voice_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Orchestrates: look up the angle's script -> run ScriptStage+VoiceStage
    on a scratch context (no raw video, no SubtitleStage) -> build the shot
    list from the resulting `beat_cues` -> persist it. Returns
    `{shot_list, voice_audio_path, total_duration}`.
    """
    voice_overrides = voice_overrides or {}

    product = ProductStore.get(product_id)
    if not product:
        raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
    angle = _find_angle(product, angle_id)
    if not angle:
        raise ValueError(f"ไม่พบมุม '{angle_id}' ในสินค้านี้")

    lines = angle.get("tts_lines") or angle.get("script_lines") or []
    lines = [str(line).strip() for line in lines if str(line).strip()]
    if not lines:
        raise ValueError(f"มุม '{angle_id}' ยังไม่มีสคริปต์ให้สร้างแผนถ่าย")
    custom_script = "\n".join(lines)

    product_name = product.get("name") or product_id
    project_dir = PROJECTS_DIR / "_ShotLists" / f"{product_id}_{angle_id}"
    project_dir.mkdir(parents=True, exist_ok=True)

    ctx = PipelineContext(
        product_name=product_name,
        raw_video_path="",
        project_name=f"_ShotLists_{product_id}_{angle_id}",
        custom_script=custom_script,
        script_overlays=None,
        voice=voice_overrides.get("voice") or DEFAULT_VOICE,
        voice_rate=voice_overrides.get("voice_rate") or DEFAULT_VOICE_RATE,
        voice_engine_type=voice_overrides.get("voice_engine_type") or "edge_tts",
        voice_preset=voice_overrides.get("voice_preset"),
        ad_tone=voice_overrides.get("ad_tone") or "commercial_premium",
        angle_meta=angle,
        product_meta=product,
        product_id=product_id,
        angle_id=angle_id,
        resume_from=None,
    )
    ctx.project_dir = project_dir

    ScriptStage.run(ctx)
    VoiceStage.run(ctx)

    if not ctx.beat_cues:
        raise ValueError("สร้างเสียงพากย์สำเร็จ แต่ไม่พบ beat_cues -- กรุณาลองใหม่")

    shot_list = build_shot_list(ctx.beat_cues, product_name)

    record = {
        "id": f"{product_id}:{angle_id}",
        "product_id": product_id,
        "angle_id": angle_id,
        "product_name": product_name,
        "shot_list": shot_list,
        "voice_audio_path": str(ctx.voice_audio_path),
        "beat_cues": ctx.beat_cues,
        "custom_script": custom_script,
        "voice_params": {key: getattr(ctx, key) for key in _VOICE_OVERRIDE_KEYS},
        "total_duration": ctx.total_duration,
    }
    ShotListsStore.upsert(record)

    return {
        "shot_list": shot_list,
        "voice_audio_path": str(ctx.voice_audio_path),
        "total_duration": ctx.total_duration,
    }
