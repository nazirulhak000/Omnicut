"""
Couple Paper Chat 20-Script Generator (`scripts/couple_script_generator.py`).

Generates 20 Couple Paper Chat scripts across 5 marketing categories (4 angles each):
1. Pain Point
2. Feature Shock
3. Real-Life Drama
4. Comparison/Safety
5. Daily Convenience

Enforces:
- Nui persona: sassy, vibrant southern girl (`น้องนุ้ย`) — NEVER applies male particles (`ครับ`, `พี่บ่าวพูดเอง`) to Nui.
- Bao persona: playful, earnest southern guy (`พี่บ่าว`) — never serious/academic/formal.
- Self-repair loop against `scripts.script_rules.lint_couple_script` until 100% of scripts pass.
- Offline deterministic generation when LLM is unavailable or mocked.
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Callable, Dict, List, Optional

from scripts.script_rules import (
    lint_couple_script,
    normalize_speaker,
    sanitize_text_for_rules,
)

COUPLE_CATEGORIES: List[Dict[str, Any]] = [
    {
        "key": "Pain Point",
        "label": "หมวดที่ 1: Pain Point — ปัญหาชวนหงุดหงิดก่อนใช้",
        "scenarios": [
            ("ของเดิมพังหงุดหงิดกลางทาง", "น้องนุ้ยบ่นของเก่าใช้งานไม่ได้ดั่งใจ พี่บ่าวรีบส่งตัวช่วยแก้ปัญหาทันที"),
            ("พกพายุ่งยากเกะกะกระเป๋า", "น้องนุ้ยรื้อกระเป๋าแล้วเจอของรุงรัง พี่บ่าวโชว์ดีไซน์คลีนจบในชิ้นเดียว"),
            ("เสียเวลารอนานจนอารมณ์เสีย", "น้องนุ้ยรีบออกจากบ้านแต่ของเดิมช้าไม่ทันใจ พี่บ่าวจัดตัวจบรวดเร็วทันใจ"),
            ("ใช้งานจริงแล้วสะดุดทุกที", "น้องนุ้ยโวยวายเพราะของเดิมงอแงตอนสำคัญ พี่บ่าวเอาตัวใหม่มาช่วยชีวิต"),
        ],
    },
    {
        "key": "Feature Shock",
        "label": "หมวดที่ 2: Feature Shock — ฟีเจอร์เด็ดเห็นแล้วอึ้ง",
        "scenarios": [
            ("สเปกจัดเต็มเกินตัวจนต้องร้องว้าว", "พี่บ่าวโชว์ฟีเจอร์เด่นให้ดูจะๆ จนคนขี้บ่นอย่างน้องนุ้ยยังต้องยอมรับ"),
            ("ดีไซน์ฉลาดคิดเผื่อมาให้ครบ", "น้องนุ้ยสงสัยว่าทำไมใช้งานง่ายขนาดนี้ พี่บ่าวอธิบายจุดเด่นแบบเข้าใจง่าย"),
            ("หน้าจอและฟังก์ชันทำงานแม่นยำ", "พี่บ่าวสาธิตการทำงานสุดล้ำให้น้องนุ้ยดูแบบชัดๆ ไม่มีกั๊ก"),
            ("วัสดุพรีเมียมแข็งแรงทนทาน", "น้องนุ้ยจับดูวัสดุจริงแล้วติดใจ พี่บ่าวภูมิใจนำเสนอความคุ้มค่า"),
        ],
    },
    {
        "key": "Real-Life Drama",
        "label": "หมวดที่ 3: Real-Life Drama — เหตุการณ์จริงคู่รักปะทะคารม",
        "scenarios": [
            ("น้องนุ้ยแอบยึดของพี่บ่าวไปใช้เอง", "พี่บ่าวซื้อมาใช้เองแท้ๆ แต่น้องนุ้ยลองครั้งเดียวแล้วประกาศยึดทันที"),
            ("เถียงกันเรื่องของใช้ในบ้านจนจบด้วยตัวนี้", "น้องนุ้ยตั้งแง่ก่อนใช้ แต่พอลองจริงกลับชมไม่หยุดปาก"),
            ("ทริปเที่ยวเกือบกร่อยเพราะลืมเตรียมของ", "ออกทริปด้วยกันแล้วเจอปัญหาหน้างาน ดีที่พี่บ่าวพกตัวนี้ติดกระเป๋ามา"),
            ("น้องนุ้ยท้าพิสูจน์ว่าดีจริงเหมือนที่คุยไหม", "น้องนุ้ยไม่เชื่อคำคุยของพี่บ่าว เลยจับทดสอบจริงแล้วผ่านฉลุย"),
        ],
    },
    {
        "key": "Comparison/Safety",
        "label": "หมวดที่ 4: Comparison/Safety — เทียบชัดมาตรฐานความปลอดภัย",
        "scenarios": [
            ("ระบบเซฟตี้จัดเต็มใช้ได้สบายใจ", "น้องนุ้ยกลัวของไม่ได้มาตรฐาน พี่บ่าวกางสเปกความปลอดภัยให้ดูชัดๆ"),
            ("เทียบของทั่วไปกับรุ่นมาตรฐานครบ", "พี่บ่าวชี้ให้เห็นความต่างระหว่างของทั่วไปกับรุ่นที่ออกแบบมาอย่างดี"),
            ("ใช้งานต่อเนื่องยาวนานไม่ร้อนไม่งอแง", "น้องนุ้ยถามเรื่องความทนทาน พี่บ่าวยืนยันระบบป้องกันครบถ้วน"),
            ("ผ่านมาตรฐานพกเดินทางได้ไร้กังวล", "น้องนุ้ยจะพกเดินทางไกล พี่บ่าวคอนเฟิร์มว่าผ่านมาตรฐานพกพาสะดวก"),
        ],
    },
    {
        "key": "Daily Convenience",
        "label": "หมวดที่ 5: Daily Convenience — ความสะดวกในชีวิตประจำวัน",
        "scenarios": [
            ("หยิบใช้มือเดียวคล่องตัวทุกสถานการณ์", "น้องนุ้ยถือของพะรุงพะรัง พี่บ่าวโชว์ความคล่องตัวหยิบใช้ง่ายสุดๆ"),
            ("ตัวเดียวจบครบไม่ต้องพกหลายชิ้น", "ลดของในกระเป๋าน้องนุ้ยให้เหลือแค่ชิ้นเดียวแต่ตอบโจทย์ครบ"),
            ("ใช้ได้ทุกที่ทั้งที่ทำงานและตอนเดินทาง", "น้องนุ้ยพกไปใช้ที่ออฟฟิศจนเพื่อนร่วมงานทักถามพิกัด"),
            ("ไอเทมคู่ใจที่ต้องมีติดกระเป๋าทุกวัน", "สรุปความประทับใจหลังใช้งานจริงทุกวันจนกลายเป็นของขาดไม่ได้"),
        ],
    },
]


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def enforce_speaker_persona(text: str, speaker: str) -> str:
    """Ensure speaker persona rules (never apply male particles to Nui; keep Bao playful)."""
    norm = normalize_speaker(speaker) or "nui"
    cleaned = sanitize_text_for_rules(text, speaker=norm)
    if norm == "nui":
        # Strictly strip male particles from Nui
        cleaned = re.sub(r"นะครับ|นะคับ|ครับผม|ครับ|คับ", "นะพี่บ่าว", cleaned)
        cleaned = cleaned.replace("พี่บ่าวพูดเอง", "น้องนุ้ยบอกเลย")
        cleaned = cleaned.replace("พี่บ่าวรับรอง", "น้องนุ้ยคอนเฟิร์ม")
    else:
        # Ensure Bao never uses stiff/academic markers
        cleaned = cleaned.replace("ในเชิงวิชาการ", "บอกเลยว่า")
        cleaned = cleaned.replace("ตามหลักทฤษฎี", "ใช้งานจริงคือ")
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _extract_clean_features(product: Dict[str, Any]) -> List[str]:
    """Extract clean feature strings from product specs/selling_points/description."""
    raw_items: List[str] = []

    for sp in product.get("selling_points") or []:
        if isinstance(sp, str) and sp.strip():
            raw_items.append(sp.strip())

    for spec in product.get("specs") or []:
        if isinstance(spec, dict):
            label = (spec.get("label") or spec.get("key") or spec.get("name") or "").strip()
            val = (spec.get("value") or spec.get("val") or "").strip()
            if label and val:
                raw_items.append(f"{label} {val}")
            elif val:
                raw_items.append(val)
        elif isinstance(spec, str) and spec.strip():
            raw_items.append(spec.strip())

    cleaned_features: List[str] = []
    for item in raw_items:
        s = sanitize_text_for_rules(item, speaker="bao")
        if s and len(s) >= 4:
            cleaned_features.append(s)

    defaults = [
        "ดีไซน์กะทัดรัดพกพาสะดวกทุกวัน",
        "วัสดุแข็งแรงทนทานได้มาตรฐาน",
        "รองรับการใช้งานต่อเนื่องได้สบายใจ",
        "เชื่อมต่อและใช้งานง่ายไม่ต้องตั้งค่าซับซ้อน",
        "ระบบป้องกันความปลอดภัยครบถ้วน",
    ]
    for d in defaults:
        if len(cleaned_features) < 6:
            cleaned_features.append(d)

    return cleaned_features


def _pick_hero_photos(product: Dict[str, Any]) -> List[str]:
    images = product.get("images") or product.get("photos") or []
    starred: List[str] = []
    others: List[str] = []
    for img in images:
        if isinstance(img, dict):
            ref = img.get("rel_path") or img.get("path") or img.get("url") or ""
            if ref:
                if img.get("starred") or img.get("is_hero"):
                    starred.append(str(ref))
                else:
                    others.append(str(ref))
        elif isinstance(img, str) and img.strip():
            others.append(img.strip())
    return starred + others


def _build_deterministic_turns(
    product_name: str,
    category_key: str,
    angle_idx: int,
    scenario_title: str,
    features: List[str],
    photos: List[str],
    reason_note: str = "",
) -> List[Dict[str, Any]]:
    """Build an 8-turn Couple Paper Chat conversation guaranteed to obey persona & lint rules."""
    clean_name = sanitize_text_for_rules(product_name or "ไอเทมตัวจบ", speaker="bao")
    if len(clean_name) > 36:
        clean_name = clean_name[:36].strip()

    f1 = features[(angle_idx * 2) % len(features)]
    f2 = features[(angle_idx * 2 + 1) % len(features)]
    f3 = features[(angle_idx * 2 + 2) % len(features)]
    photo_1 = photos[angle_idx % len(photos)] if photos else None
    photo_2 = photos[(angle_idx + 1) % len(photos)] if photos else None

    raw_turns = [
        (
            "nui",
            f"พี่บ่าว! เรื่อง{scenario_title}ทำน้องหงุดหงิดแล้วนะ!",
            f"พี่บ่าว! วันนี้เรื่อง{scenario_title}ทำน้องนุ้ยหงุดหงิดอารมณ์เสียไปหมดแล้วนะ!",
            None,
        ),
        (
            "nui",
            "ของเดิมไม่ไหวเลย มีตัวช่วยดีๆ ไหมเนี่ย!",
            "ของเดิมที่ใช้อยู่ไม่ไหวจะเคลียร์แล้ว พี่บ่าวมีตัวช่วยดีๆ มาให้น้องไหมเนี่ย!",
            None,
        ),
        (
            "bao",
            f"ใจเย็นครับคนสวย เอา {clean_name} ไปใช้เลย!",
            f"ใจเย็นๆ ก่อนครับน้องนุ้ยคนสวย พี่บ่าวจัด {clean_name} ตัวนี้มาให้แล้วครับ!",
            photo_1,
        ),
        (
            "bao",
            f"ตัวนี้เด่นมาก {f1}!",
            f"บอกเลยว่าตัวนี้เด็ดจริงเพราะเขามี {f1} ใช้งานลื่นไหลสุดๆ ครับ!",
            None,
        ),
        (
            "nui",
            "จริงเหรอพี่บ่าว แล้วใช้ยากไหมเนี่ย!",
            "จริงเหรอพี่บ่าว ขอดูหน่อยซิว่าใช้งานจริงจะง่ายเหมือนที่พี่บ่าวคุยไว้ไหม!",
            None,
        ),
        (
            "bao",
            f"ง่ายสุดๆ แถมมี {f2} ด้วยครับ!",
            f"ใช้ง่ายมากครับน้องนุ้ย แถมยังมี {f2} และ {f3} ครบในตัวเดียวเลยครับ!",
            photo_2,
        ),
        (
            "nui",
            "เออเริ่ดจริง! งั้นน้องนุ้ยขอยึดไว้ใช้เองเลยนะ!",
            "เอออันนี้เริ่ดจริงยอมรับเลย งั้นน้องนุ้ยขอยึดตัวนี้ไว้ใช้เองตั้งแต่วันนี้เลยนะพี่บ่าว!",
            None,
        ),
        (
            "bao",
            "จัดไปครับ ใครอยากได้กดที่ตะกร้าเหลืองได้เลย!",
            "จัดไปเลยครับน้องนุ้ย ใครอยากได้ตัวช่วยดีๆ แบบนี้กดดูที่ตะกร้าเหลืองด้านล่างได้เลยครับ!",
            None,
        ),
    ]

    if reason_note:
        clean_reason = enforce_speaker_persona(reason_note, "nui")
        if clean_reason:
            raw_turns[4] = (
                "nui",
                f"ไหนขอดูจุดนี้หน่อย {clean_reason[:28]}!",
                f"ไหนพี่บ่าวลองบอกเพิ่มซิ เรื่อง{clean_reason[:40]}เป็นยังไงบ้าง!",
                None,
            )

    turns: List[Dict[str, Any]] = []
    for spk, disp, spok, photo in raw_turns:
        safe_disp = enforce_speaker_persona(disp, spk)
        safe_spok = enforce_speaker_persona(spok, spk)
        turns.append({
            "speaker": spk,
            "display": safe_disp,
            "spoken": safe_spok,
            "phrases": [{"display": safe_disp, "spoken": safe_spok}],
            "photo": photo,
        })
    return turns


def repair_couple_script_turns(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministically repair turns so they pass `lint_couple_script`."""
    repaired: List[Dict[str, Any]] = []
    for idx, turn in enumerate(turns or []):
        spk = normalize_speaker(turn.get("speaker") if isinstance(turn, dict) else None)
        if not spk:
            spk = "nui" if idx % 2 == 0 else "bao"

        raw_disp = ""
        raw_spok = ""
        photo = None
        if isinstance(turn, dict):
            photo = turn.get("photo")
            phrases = turn.get("phrases")
            if isinstance(phrases, list) and phrases:
                first = phrases[0]
                if isinstance(first, dict):
                    raw_disp = str(first.get("display") or "")
                    raw_spok = str(first.get("spoken") or "")
            if not raw_disp:
                raw_disp = str(turn.get("display") or turn.get("text") or "")
            if not raw_spok:
                raw_spok = str(turn.get("spoken") or turn.get("text") or raw_disp)

        safe_disp = enforce_speaker_persona(raw_disp, spk)
        safe_spok = enforce_speaker_persona(raw_spok, spk)
        if not safe_disp:
            safe_disp = "น้องนุ้ยถูกใจสิ่งนี้เลย!" if spk == "nui" else "พี่บ่าวจัดให้ครบจบเลยครับ!"
        if not safe_spok:
            safe_spok = safe_disp

        repaired.append({
            "speaker": spk,
            "display": safe_disp,
            "spoken": safe_spok,
            "phrases": [{"display": safe_disp, "spoken": safe_spok}],
            "photo": photo,
        })

    # Ensure turn count is within 8..14
    while len(repaired) < 8:
        next_spk = "nui" if len(repaired) % 2 == 0 else "bao"
        fallback_line = (
            "ใช้งานสะดวกถูกใจน้องนุ้ยมากเลย!"
            if next_spk == "nui"
            else "ใครสนใจกดที่ตะกร้าเหลืองด้านล่างได้เลยครับ!"
        )
        repaired.append({
            "speaker": next_spk,
            "display": fallback_line,
            "spoken": fallback_line,
            "phrases": [{"display": fallback_line, "spoken": fallback_line}],
            "photo": None,
        })
    if len(repaired) > 14:
        repaired = repaired[:14]

    return repaired


def generate_single_couple_angle(
    product: Dict[str, Any],
    angle_index: int,
    *,
    reason: str = "",
    llm_fn: Optional[Callable[[Dict[str, Any], int, str], List[Dict[str, Any]]]] = None,
    max_repair_attempts: int = 3,
) -> Dict[str, Any]:
    """Generate and self-repair one Couple Paper Chat angle (0-based index 0..19)."""
    cat_idx = (angle_index // 4) % len(COUPLE_CATEGORIES)
    sub_idx = angle_index % 4
    cat_info = COUPLE_CATEGORIES[cat_idx]
    scenario_title, scenario_desc = cat_info["scenarios"][sub_idx]

    product_name = (product.get("name") or "สินค้าแนะนำ").strip()
    product_code = (product.get("product_code") or product.get("code") or "CPL01").strip().lower()
    features = _extract_clean_features(product)
    photos = _pick_hero_photos(product)

    turns: Optional[List[Dict[str, Any]]] = None
    if callable(llm_fn):
        try:
            candidate = llm_fn(product, angle_index, reason)
            if isinstance(candidate, list) and candidate:
                turns = candidate
        except Exception:
            turns = None

    if not turns:
        turns = _build_deterministic_turns(
            product_name=product_name,
            category_key=cat_info["key"],
            angle_idx=angle_index,
            scenario_title=scenario_title,
            features=features,
            photos=photos,
            reason_note=reason,
        )

    lint_result = lint_couple_script({"turns": turns})
    attempt = 0
    while not lint_result["valid"] and attempt < max_repair_attempts:
        attempt += 1
        turns = repair_couple_script_turns(turns)
        lint_result = lint_couple_script({"turns": turns})

    if not lint_result["valid"]:
        # Final guaranteed deterministic fallback
        turns = repair_couple_script_turns(
            _build_deterministic_turns(
                product_name=product_name,
                category_key=cat_info["key"],
                angle_idx=angle_index,
                scenario_title=scenario_title,
                features=features,
                photos=photos,
                reason_note="",
            )
        )
        lint_result = lint_couple_script({"turns": turns})

    num = angle_index + 1
    angle_id = f"ang_{product_code}_{num:02d}"
    clean_title = sanitize_text_for_rules(f"{scenario_title} ({product_name})", speaker="bao")
    now = _now_iso()

    return {
        "id": angle_id,
        "angle_id": angle_id,
        "batch": num,
        "format": "couple_v1",
        "category": cat_info["label"],
        "category_key": cat_info["key"],
        "title": clean_title,
        "hook_title": sanitize_text_for_rules(f"POV: {scenario_title}", speaker="nui"),
        "scenario": sanitize_text_for_rules(scenario_desc, speaker="bao"),
        "turns": turns,
        "script_review": {
            "state": "pending",
            "at": now,
            "note": reason.strip() if reason else "",
        },
        "revision": 1,
        "lint": lint_result,
    }


def generate_couple_20_scripts(
    product: Dict[str, Any],
    *,
    llm_fn: Optional[Callable[[Dict[str, Any], int, str], List[Dict[str, Any]]]] = None,
    max_repair_attempts: int = 3,
    progress_cb: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """Generate 20 Couple Paper Chat scripts across 5 categories (4 angles each)."""
    angles: List[Dict[str, Any]] = []
    total = 20
    for idx in range(total):
        angle = generate_single_couple_angle(
            product,
            idx,
            llm_fn=llm_fn,
            max_repair_attempts=max_repair_attempts,
        )
        angles.append(angle)
        if callable(progress_cb):
            progress_cb(idx + 1, total, angle)
    return angles
