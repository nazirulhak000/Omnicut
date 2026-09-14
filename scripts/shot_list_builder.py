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
    category: str = "",
) -> str:
    """Smart templated Thai filming direction aware of product category, product name,
    and semantic context of the specific beat line.
    Deterministic with zero AI calls or quota costs."""
    combined_context = f"{category} {product_name}".lower()
    text_lower = f"{beat_text} {on_screen}".lower()

    # Category detection (from category field OR product name)
    is_mouse = any(k in combined_context for k in ("mouse", "เมาส์", "lift", "mx master", "trackball"))
    is_keyboard = any(k in combined_context for k in ("keyboard", "คีย์บอร์ด", "keys", "mechanical"))
    is_desk_tech = is_mouse or is_keyboard or any(k in combined_context for k in ("คอมพิวเตอร์", "ไอที", "it", "gadget", "โต๊ะ", "desk", "monitor", "stand"))
    is_cable = any(k in combined_context for k in ("cable", "charger", "สายชาร์จ", "ชาร์จ", "หัวชาร์จ", "essager", "ugreen", "baseus", "anker"))
    is_beauty = any(k in combined_context for k in ("beauty", "skincare", "ลิป", "ครีม", "เซรั่ม", "สำอาง", "ผิว", "โลชั่น", "กันแดด"))

    if role == "hook":
        if is_mouse:
            return (
                f"ตั้งกล้องมุมเฉียง 45° ส่องบนโต๊ะทำงาน — "
                f"วาง {product_name} บนแผ่นรองเมาส์ มือจับเข้าท่าทรงสรีรศาสตร์ 57° หรือเลื่อนเมาส์เข้าเฟรมเพื่อเปิดคลิป"
            )
        if is_desk_tech:
            return (
                f"ตั้งกล้องมุมเฉียง 45° หรือ Top-Down ส่องบนโต๊ะทำงาน — "
                f"วาง {product_name} กลางโต๊ะ มือจับหรือเริ่มใช้งานให้เห็นสรีระ/ฟังก์ชันชัดเจน"
            )
        if is_cable:
            return (
                f"ตั้งกล้องมุม Close-up ระดับอกหรือบนโต๊ะ — "
                f"ถือ {product_name} โชว์การม้วนเก็บ/ดูดของแม่เหล็ก หรือดึงสายให้เห็นความทนทานชัดๆ"
            )
        if is_beauty:
            return (
                f"ตั้งกล้องระยะ Medium Close-up สว่างชัดเจน — "
                f"ถือ {product_name} ใกล้ใบหน้าหรือท่อนบน ยิ้มพร้อมโชว์บรรจุภัณฑ์หน้ากล้อง"
            )
        return (
            f"ตั้งกล้อง/มือถือมุมเดียว ระยะ Medium shot ระดับอก ห้ามขยับกล้องตลอดคลิป — "
            f"ถือหรือวาง {product_name} ให้เห็นชัดกลางเฟรม พูดพร้อมแอคชั่นแนะนำตัวสินค้า"
        )

    if role == "cta":
        if is_mouse or is_desk_tech:
            return (
                "ชี้/แตะราคาหรือพิกัดตะกร้าสินค้าในเฟรม — "
                "อาจขยับกล้องเข้าใกล้ (Close-up) เพื่อโชว์เมาส์คู่กับหน้าจอคอมหรือวางมือผ่อนคลายข้างสินค้า"
            )
        return (
            "ชี้/แตะราคาหรือตะกร้าสินค้าให้เห็นชัดในเฟรม — "
            "อาจถ่ายแยกเป็นคลิปโคลสอัพต่างหากจากเทกหลักได้ (กล้องขยับเข้าใกล้ได้เฉพาะช็อตนี้)"
        )

    # ── Feature / Body beats: Semantic Context Analysis ──
    # Note: Structure as 'มุมกล้อง — แอคชั่นการถ่าย' so the UI separates them cleanly
    angle_base = "กล้องมุมเดิมบนขาตั้ง (ไม่ขยับกล้อง)"

    # 1. Clicking / Buttons / Wheel / Sound / Smoothness
    if any(k in text_lower for k in ("คลิก", "ปุ่ม", "เสียง", "เงียบ", "ลื่น", "สมูท", "wheel", "click", "silent")):
        if is_mouse:
            return f"{angle_base} — ใช้นิ้วชี้-กลางกดคลิกปุ่มซ้ายขวา และหมุน SmartWheel ให้เห็นความนุ่มลื่นเงียบกริบ"
        if is_keyboard:
            return f"{angle_base} — พิมพ์นิ้วรัวๆ ลงบนปุ่มคีย์บอร์ด โชว์สัมผัสการกดที่นุ่มและเสียงพิมพ์ที่ฟินมือ"
        return f"{angle_base} — กดปุ่มหรือขยับฟังก์ชันเด่นของ {product_name} ให้เห็นการทำงานที่ลื่นไหล"

    # 2. Daily cost comparison / Savings / Math value (e.g. ตกวันละกี่บาท vs ยาแก้ปวด)
    if any(k in text_lower for k in ("วันละ", "สตางค์", "บาท", "ยาแก้ปวด", "ถูกกว่า", "ประหยัด")):
        if is_mouse or is_desk_tech:
            return f"{angle_base} — ยก {product_name} ขึ้นมาถือเทียบกับมือ หรือหมุนช้าๆ 360° โชว์ความพรีเมียมและวัสดุที่คุ้มค่าน่าใช้"
        return f"{angle_base} — ยก {product_name} ขึ้นมาถือหรือหมุนช้าๆ 360° โชว์ความพรีเมียมและวัสดุที่คุ้มค่าน่าใช้"

    # 3. Ergonomics / Wrist pain / Health / Comfort / Posture / Investment for body
    if any(k in text_lower for k in ("สุขภาพ", "สรีระ", "ปวด", "เมื่อย", "ข้อ", "มือ", "สบาย", "ถนอม", "เอียง", "องศา", "ธรรมชาติ", "ergo", "ลงทุนครั้งเดียว")):
        if is_mouse:
            return f"{angle_base} — วางมือทาบลงบนเมาส์ ยกให้เห็นมุมเอียง 57° ที่กระชับพอดีฝ่ามือ ไม่เกร็งข้อมือ"
        if is_desk_tech:
            return f"{angle_base} — จัดท่าทางการนั่งหรือวางมือคู่กับ {product_name} ให้เห็นความสบายตามหลักสรีรศาสตร์"
        return f"{angle_base} — ถือหรือสัมผัส {product_name} ในท่าที่ผ่อนคลายและใช้งานสบายที่สุด"

    # 4. Value / General Cost / Durability
    if any(k in text_lower for k in ("คุ้ม", "ราคา", "ลงทุน", "ทน", "ปี", "ยาวนาน")):
        return f"{angle_base} — จับถือ {product_name} พลิกโชว์งานประกอบเนี๊ยบๆ เน้นความทนทานใช้งานได้หลายปี"

    # 5. Connection / Bluetooth / Wireless / Battery / Multi-device
    if any(k in text_lower for k in ("บลูทูธ", "bluetooth", "ไร้สาย", "wireless", "ต่อ", "เชื่อม", "สลับ", "เครื่อง", "แบต", "ถ่าน", "ชาร์จ")):
        if is_mouse:
            return f"{angle_base} — พลิกด้านใต้เมาส์ให้เห็นสวิตช์เปิด-ปิด หรือปุ่มสลับเครื่อง Easy-Switch / ฝาปิดถ่าน"
        return f"{angle_base} — โชว์พอร์ตเชื่อมต่อหรืออุปกรณ์ที่ทำงานร่วมกับ {product_name}"

    # 6. Cable specific
    if is_cable:
        if any(k in text_lower for k in ("ม้วน", "เก็บ", "แม่เหล็ก", "พัน")):
            return f"{angle_base} — ม้วนสายเข้าหากัน โชว์แม่เหล็กดูดติดเก็บเป็นระเบียบใน 1 วินาที"
        if any(k in text_lower for k in ("เหนียว", "ขาด", "ทน", "ดึง", "หัก")):
            return f"{angle_base} — จับปลายสายทั้งสองข้างดึงยืด หรืองอข้อต่อโชว์ความทนทานไม่หักงอง่าย"
        if on_screen:
            return f"{angle_base} — ทำแอคชั่นม้วน/เสียบชาร์จจริง พร้อมเน้น '{on_screen}' ให้เห็นในเฟรม"
        return f"{angle_base} — เสียบชาร์จใช้งานกับมือถือหรืออุปกรณ์จริงให้เห็นสถานะไฟเข้า"

    # 7. Beauty specific
    if is_beauty:
        if any(k in text_lower for k in ("ทา", "เนื้อ", "สัมผัส", "ซึม", "เกลี่ย", "ปาก", "ชุ่ม", "ฉ่ำ")):
            return f"{angle_base} — ปาด/แตะเนื้อผลิตภัณฑ์ลงบนหลังมือหรือริมฝีปาก โชว์ความฉ่ำวาวและความเนียนนุ่ม"
        if on_screen:
            return f"{angle_base} — แตะ/ทาเนื้อสัมผัส หรือโชว์ '{on_screen}' กับผิวให้เห็นความเรียบเนียน"
        return f"{angle_base} — เปิดฝา ปั๊มเนื้อครีม หรือถือคู่กับใบหน้ายิ้มอย่างมั่นใจ"

    # Fallback with on_screen or index-based varied action
    if on_screen:
        return f"{angle_base} — ทำแอคชั่นใช้งานจริง พร้อมชี้หรือโชว์ '{on_screen}' ให้เห็นชัดในเฟรม"

    # Alternating natural actions so consecutive beats never repeat identical text
    default_actions = [
        f"{angle_base} — จับถือ {product_name} หมุนโชว์ดีไซน์รอบตัวเครื่องอย่างเป็นธรรมชาติ",
        f"{angle_base} — ใช้งาน {product_name} จริงบนโต๊ะให้สอดคล้องกับจังหวะเสียงพากย์",
        f"{angle_base} — วางมือทาบหรือขยับ {product_name} เพื่อเน้นจุดเด่นตามบทพูด",
    ]
    return default_actions[index % len(default_actions)]


def build_shot_list(beat_cues: List[Dict[str, Any]], product_name: str, category: str = "") -> List[Dict[str, Any]]:
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
                role, index, cue.get("text", ""), cue.get("on_screen", ""), product_name, category
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

    voice_engine_type = voice_overrides.get("voice_engine_type") or angle.get("voice_engine_type") or "gemini_tts"
    voice_preset = voice_overrides.get("voice_preset") or angle.get("voice_preset") or "gemini_puck_male_hype"
    voice_rate = voice_overrides.get("voice_rate") or angle.get("voice_rate") or "+15%"
    ad_tone = voice_overrides.get("ad_tone") or angle.get("ad_tone") or "commercial_hype"

    ctx = PipelineContext(
        product_name=product_name,
        raw_video_path="",
        project_name=f"_ShotLists_{product_id}_{angle_id}",
        custom_script=custom_script,
        script_overlays=None,
        voice=voice_overrides.get("voice") or DEFAULT_VOICE,
        voice_rate=voice_rate,
        voice_engine_type=voice_engine_type,
        voice_preset=voice_preset,
        ad_tone=ad_tone,
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

    category = product.get("category") or product.get("product_category") or ""
    shot_list = build_shot_list(ctx.beat_cues, product_name, category=category)

    record = {
        "id": f"{product_id}:{angle_id}",
        "product_id": product_id,
        "angle_id": angle_id,
        "product_name": product_name,
        "shot_list": shot_list,
        "voice_audio_path": str(ctx.voice_audio_path),
        "cues": ctx.cues,
        "beat_cues": ctx.beat_cues,
        "custom_script": custom_script,
        "voice_params": {key: getattr(ctx, key) for key in _VOICE_OVERRIDE_KEYS},
        "total_duration": ctx.total_duration,
    }
    ShotListsStore.upsert(record)

    try:
        ProductStore.update_angle_voice(
            product_id,
            angle_id,
            voice_preset=voice_preset,
            voice_engine_type=voice_engine_type,
            ad_tone=ad_tone,
        )
    except Exception as update_err:
        print(f"[ShotList] Note: Could not update angle with voice settings: {update_err}")

    return {
        "shot_list": shot_list,
        "voice_audio_path": str(ctx.voice_audio_path),
        "total_duration": ctx.total_duration,
    }
