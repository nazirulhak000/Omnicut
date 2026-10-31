"""
Shared deterministic linting rules for Couple Paper Chat scripts.

Maintains 100% parity with `frontend/src/lib/scriptRules.js`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from scripts.compliance_lint import (
    COUPLE_PRICE_KEYWORDS,
    COUPLE_PRICE_SHORT_BAHT_RE,
    find_couple_price_term,
)

RULE_NO_ELLIPSIS = "NO_ELLIPSIS"
RULE_NO_PRICE = "NO_PRICE"
RULE_NO_EMOJI = "NO_EMOJI"
RULE_NO_THAI_TECH_TRANSLITERATION = "NO_THAI_TECH_TRANSLITERATION"
RULE_TURN_STRUCTURE = "TURN_STRUCTURE"

VALID_SPEAKERS = {
    "nui",
    "bao",
    "น้องนุ้ย",
    "พี่บ่าว",
    "f",
    "m",
    "female",
    "male",
}

NUI_SPEAKERS = {"nui", "น้องนุ้ย", "f", "female"}
BAO_SPEAKERS = {"bao", "พี่บ่าว", "m", "male"}

DEFAULT_MIN_TURNS = 8
DEFAULT_MAX_TURNS = 14

# Rule 3.7: Forbidden ellipsis patterns ("..." or "…")
ELLIPSIS_RE = re.compile(r"(\.{2,}|\u2026)")

# Zero-Price Rule: Forbidden price/discount/currency keywords & patterns.
# The list now lives in the central compliance lint (scripts/compliance_lint.py)
# and is re-exported here unchanged, so couple behavior -- and parity with
# frontend/src/lib/scriptRules.js -- stays identical.
PRICE_KEYWORDS = COUPLE_PRICE_KEYWORDS
PRICE_SHORT_BAHT_RE = COUPLE_PRICE_SHORT_BAHT_RE

# Style 3B Zero-Emoji Policy: Unicode emoji ranges
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)

# Rule 3.9: Forbidden Thai transliterations of English tech terms
THAI_TECH_REPLACEMENTS: Dict[str, str] = {
    "บลูทูธ": "Bluetooth",
    "ไทป์ซี": "Type-C",
    "ฟาสต์ชาร์จ": "Fast Charge",
    "ไวร์เลส": "Wireless",
    "ยูเอสบี": "USB",
    "พีดี": "PD",
}

NUI_FORBIDDEN_MALE_PARTICLES = (
    "ครับ",
    "คับ",
    "พี่บ่าวพูดเอง",
    "ผมว่า",
)


def normalize_speaker(speaker: Any) -> Optional[str]:
    """Normalize speaker identifier to 'nui' or 'bao', or None if invalid."""
    if not isinstance(speaker, str):
        return None
    cleaned = speaker.strip().lower()
    if cleaned in NUI_SPEAKERS or speaker.strip() in NUI_SPEAKERS:
        return "nui"
    if cleaned in BAO_SPEAKERS or speaker.strip() in BAO_SPEAKERS:
        return "bao"
    return None


def extract_turn_phrases(turn: Any) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """Extract `(speaker_raw, [{"display": ..., "spoken": ...}, ...])` from any supported turn format.

    Supported formats:
    1. Canonical tuple/list: `["F", [["display", "spoken"], ...], photo]`
    2. Object with phrases: `{"speaker": "nui", "phrases": [{"display": "...", "spoken": "..."}]}`
    3. Flat object: `{"speaker": "nui", "display": "...", "spoken": "..."}`
    """
    if isinstance(turn, (list, tuple)):
        if len(turn) < 2:
            return None, []
        speaker_raw = str(turn[0]) if turn[0] is not None else None
        raw_phrases = turn[1]
        phrases: List[Dict[str, str]] = []
        if isinstance(raw_phrases, (list, tuple)):
            for item in raw_phrases:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    phrases.append({
                        "display": "" if item[0] is None else str(item[0]),
                        "spoken": "" if item[1] is None else str(item[1]),
                    })
                elif isinstance(item, dict):
                    phrases.append({
                        "display": "" if item.get("display") is None else str(item.get("display")),
                        "spoken": "" if item.get("spoken") is None else str(item.get("spoken")),
                    })
        return speaker_raw, phrases

    if isinstance(turn, dict):
        speaker_raw = turn.get("speaker") or turn.get("role")
        if speaker_raw is not None:
            speaker_raw = str(speaker_raw)

        if isinstance(turn.get("phrases"), list):
            phrases = []
            for item in turn["phrases"]:
                if isinstance(item, dict):
                    phrases.append({
                        "display": "" if item.get("display") is None else str(item.get("display")),
                        "spoken": "" if item.get("spoken") is None else str(item.get("spoken")),
                    })
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    phrases.append({
                        "display": "" if item[0] is None else str(item[0]),
                        "spoken": "" if item[1] is None else str(item[1]),
                    })
            return speaker_raw, phrases

        if "display" in turn or "spoken" in turn or "text" in turn:
            disp = turn.get("display") if "display" in turn else turn.get("text", "")
            spok = turn.get("spoken") if "spoken" in turn else turn.get("text", "")
            return speaker_raw, [
                {
                    "display": "" if disp is None else str(disp),
                    "spoken": "" if spok is None else str(spok),
                }
            ]

    return None, []


def lint_text_field(
    text: str,
    turn_index: int,
    field_name: str,
) -> List[Dict[str, Any]]:
    """Run text-level rules on a single string field (`display` or `spoken`)."""
    violations: List[Dict[str, Any]] = []
    if not text:
        return violations

    if ELLIPSIS_RE.search(text):
        violations.append({
            "code": RULE_NO_ELLIPSIS,
            "message": "ห้ามใช้ '...' หรือ '…' ในบทพูดหรือข้อความซับ (กฎข้อ 3.7)",
            "turn_index": turn_index,
            "field": field_name,
        })

    matched_price: Optional[str] = find_couple_price_term(text)

    if matched_price:
        violations.append({
            "code": RULE_NO_PRICE,
            "message": f"ห้ามระบุราคาหรือคำโปรโมชั่น ('{matched_price}') ในสคริปต์",
            "turn_index": turn_index,
            "field": field_name,
        })

    if EMOJI_RE.search(text):
        violations.append({
            "code": RULE_NO_EMOJI,
            "message": "ห้ามใช้อีโมจิในบทสคริปต์ (Style 3B Zero-Emoji Policy)",
            "turn_index": turn_index,
            "field": field_name,
        })

    for bad_thai, eng_term in THAI_TECH_REPLACEMENTS.items():
        if bad_thai in text:
            violations.append({
                "code": RULE_NO_THAI_TECH_TRANSLITERATION,
                "message": f"ห้ามทับศัพท์คำเทคนิค '{bad_thai}' ให้ใช้ '{eng_term}' แทน (กฎข้อ 3.9)",
                "turn_index": turn_index,
                "field": field_name,
            })
            break

    return violations


def lint_couple_script(
    script_or_turns: Any,
    *,
    min_turns: int = DEFAULT_MIN_TURNS,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> Dict[str, Any]:
    """Deterministically validate a Couple Paper Chat script or turns list.

    Returns:
        `{"valid": bool, "violations": [{"code", "message", "turn_index", "field"}, ...]}`
    """
    violations: List[Dict[str, Any]] = []

    if isinstance(script_or_turns, dict):
        turns = script_or_turns.get("turns")
    else:
        turns = script_or_turns

    if not isinstance(turns, list) or len(turns) == 0:
        violations.append({
            "code": RULE_TURN_STRUCTURE,
            "message": "ต้องมีรายการบทสนทนา (turns) อย่างน้อย 1 เทิร์น",
            "turn_index": -1,
            "field": "turns",
        })
        return {"valid": False, "violations": violations}

    if len(turns) < min_turns or len(turns) > max_turns:
        violations.append({
            "code": RULE_TURN_STRUCTURE,
            "message": f"จำนวนเทิร์นต้องอยู่ระหว่าง {min_turns}–{max_turns} เทิร์น (ปัจจุบัน {len(turns)} เทิร์น)",
            "turn_index": -1,
            "field": "turns",
        })

    for idx, turn in enumerate(turns):
        speaker_raw, phrases = extract_turn_phrases(turn)
        normalized_speaker = normalize_speaker(speaker_raw)
        if not normalized_speaker:
            violations.append({
                "code": RULE_TURN_STRUCTURE,
                "message": f"ผู้พูดในเทิร์นที่ {idx + 1} ไม่ถูกต้อง (ต้องเป็น nui/bao หรือ น้องนุ้ย/พี่บ่าว)",
                "turn_index": idx,
                "field": "speaker",
            })

        if not phrases:
            violations.append({
                "code": RULE_TURN_STRUCTURE,
                "message": f"เทิร์นที่ {idx + 1} ต้องมีข้อความ display และ spoken ที่ไม่ว่าง",
                "turn_index": idx,
                "field": "phrases",
            })
            continue

        for phrase in phrases:
            disp = (phrase.get("display") or "").strip()
            spok = (phrase.get("spoken") or "").strip()
            if not disp:
                violations.append({
                    "code": RULE_TURN_STRUCTURE,
                    "message": f"ข้อความแสดงผล (display) ในเทิร์นที่ {idx + 1} ห้ามว่าง",
                    "turn_index": idx,
                    "field": "display",
                })
            if not spok:
                violations.append({
                    "code": RULE_TURN_STRUCTURE,
                    "message": f"บทพูด (spoken) ในเทิร์นที่ {idx + 1} ห้ามว่าง",
                    "turn_index": idx,
                    "field": "spoken",
                })

            violations.extend(lint_text_field(disp, idx, "display"))
            violations.extend(lint_text_field(spok, idx, "spoken"))

    return {
        "valid": len(violations) == 0,
        "violations": violations,
    }


def sanitize_text_for_rules(text: str, speaker: Optional[str] = None) -> str:
    """Repair common rule violations in a single text string."""
    if not text:
        return ""
    out = str(text)
    # 1. Remove ellipsis
    out = ELLIPSIS_RE.sub(" ", out)
    # 2. Remove emojis
    out = EMOJI_RE.sub("", out)
    # 3. Replace Thai tech transliterations with English terms
    for bad_thai, eng_term in THAI_TECH_REPLACEMENTS.items():
        out = out.replace(bad_thai, eng_term)
    # 4. Strip price patterns and keywords
    out = PRICE_SHORT_BAHT_RE.sub("คุ้มมาก", out)
    price_fallbacks = {
        "โปรโมชั่น": "ของดี",
        "ลดเหลือ": "จัดมา",
        "ส่วนลด": "ความคุ้ม",
        "คูปอง": "สิทธิ์พิเศษ",
        "ถูกมาก": "คุ้มมาก",
        "ราคา": "ความคุ้ม",
        "บาท": "",
        "฿": "",
    }
    for kw, replacement in price_fallbacks.items():
        out = out.replace(kw, replacement)

    # 5. Persona guard: Nui must never speak male particles
    if normalize_speaker(speaker) == "nui":
        out = out.replace("พี่บ่าวพูดเอง", "น้องนุ้ยบอกเลย")
        out = re.sub(r"นะครับ|นะคับ|ครับผม|ครับ|คับ", "นะพี่บ่าว", out)

    out = re.sub(r"\s{2,}", " ", out).strip()
    return out
