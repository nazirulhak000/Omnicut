"""
Central deterministic compliance lint for every text that can reach a clip.

TikTok Shop clips must never say or show a price / discount / price guess, and
must not carry fabricated or exaggerated claims (AGENTS.md + owner memory).
Until this module existed the only guard was the prompt itself, so a model
slip (or a hand-written fallback template) went straight to TTS and ASS.

Everything here is pure and offline: plain regex/keyword checks, no AI, no
I/O. Callers decide what to do with a hit (regenerate once, strip the line,
or reject) -- this module only finds and reports, plus a couple of small
deterministic sanitizers that never invent new wording.

Rollback: set ``COMPLIANCE_LINT_ENABLED = False`` (module-level, kept out of
the shared ``scripts/config.py`` on purpose) and every ``lint_*`` helper
returns no violations, so callers fall back to today's behavior.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------
COMPLIANCE_LINT_ENABLED = True

# ---------------------------------------------------------------------------
# Rule codes
# ---------------------------------------------------------------------------
RULE_NO_PRICE = "NO_PRICE"
RULE_NO_EXAGGERATED_CLAIM = "NO_EXAGGERATED_CLAIM"
RULE_NO_FILLER_OPENER = "NO_FILLER_OPENER"
RULE_NO_CTA_FIRST_LINE = "NO_CTA_FIRST_LINE"
RULE_NO_ELLIPSIS = "NO_ELLIPSIS"
RULE_NO_EMOJI = "NO_EMOJI"

# Structure (M3) warning codes -- warnings only, never a hard fail.
STRUCT_NO_OPEN_LOOP = "STRUCT_NO_OPEN_LOOP"
STRUCT_FILLER_ENDING = "STRUCT_FILLER_ENDING"
STRUCT_NO_COMMENT_QUESTION = "STRUCT_NO_COMMENT_QUESTION"
STRUCT_LENGTH_OFF_TARGET = "STRUCT_LENGTH_OFF_TARGET"

# ---------------------------------------------------------------------------
# Couple Paper Chat price lint (moved verbatim from script_rules.py so the
# couple behavior -- and its parity with frontend/src/lib/scriptRules.js --
# stays byte-for-byte identical).
# ---------------------------------------------------------------------------
COUPLE_PRICE_KEYWORDS = (
    "บาท",
    "฿",
    "ราคา",
    "โปรโมชั่น",
    "ลดเหลือ",
    "คูปอง",
    "ส่วนลด",
    "ถูกมาก",
)
COUPLE_PRICE_SHORT_BAHT_RE = re.compile(r"\d+\s*บ\.")


def find_couple_price_term(text: str) -> Optional[str]:
    """Return the first couple-lint price term in `text`, or None (legacy rule)."""
    if not text:
        return None
    for kw in COUPLE_PRICE_KEYWORDS:
        if kw in text:
            return kw
    if COUPLE_PRICE_SHORT_BAHT_RE.search(text):
        return "บ."
    return None


# ---------------------------------------------------------------------------
# General price / discount / price-guess detection
# ---------------------------------------------------------------------------
# Deliberately NOT matched (spec/feature words that share a prefix):
#   "ลดเสียงรบกวน", "ลดความร้อน" (bare "ลด" is never a hit),
#   "โปรเซสเซอร์", "โปรไฟล์", English "Pro" model names (bare "โปร" is
#   only a hit when it stands alone or in an explicit promo phrase).
_PRICE_PATTERNS: Sequence[tuple] = (
    (re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:บาท|฿|บ\.|\.-)"), "ตัวเลขราคา"),
    (re.compile(r"฿\s*\d"), "ตัวเลขราคา"),
    (re.compile(r"บาท"), "บาท"),
    (re.compile(r"฿"), "฿"),
    (re.compile(r"\bTHB\b|\bbaht\b", re.IGNORECASE), "THB"),
    (re.compile(r"ราคา"), "ราคา"),
    (re.compile(r"ส่วนลด"), "ส่วนลด"),
    (re.compile(r"ลด(?:ราคา|เหลือ|แรง|พิเศษ|กระหน่ำ|ล้าง|สูงสุด)"), "ลดราคา"),
    (re.compile(r"ลด\s*\d+\s*%"), "ลดเปอร์เซ็นต์"),
    (re.compile(r"ถูกกว่า"), "ถูกกว่า"),
    (re.compile(r"ถูกกับแพง|ถูกหรือแพง"), "ถูกกับแพง"),
    (re.compile(r"ไม่แพง|แพงกว่า"), "แพง"),
    (re.compile(r"ถูกมาก"), "ถูกมาก"),
    (re.compile(r"ไม่กี่บาท|กี่บาท"), "ไม่กี่บาท"),
    (re.compile(r"หลักร้อย|หลักพัน|หลักหมื่น"), "เดาราคา"),
    (re.compile(r"ทายราคา|เดาราคา|ทายสิว่า"), "ทายราคา"),
    (re.compile(r"สตางค์"), "สตางค์"),
    (re.compile(r"คุ้มค่าเงิน"), "คุ้มค่าเงิน"),
    (re.compile(r"คูปอง"), "คูปอง"),
    (re.compile(r"โปรโมชั่น|โปรโมชัน"), "โปรโมชั่น"),
    (re.compile(r"(?:จัด|ติด|มี)โปร(?![ก-๙])|โปร(?:แรง|พิเศษ|เด็ด|หมด|นี้)|โปร(?=\s|$|[!?.,])"), "โปร"),
    (re.compile(r"flash\s*sale", re.IGNORECASE), "Flash Sale"),
    (re.compile(r"ส่งฟรี"), "ส่งฟรี"),
)

# ---------------------------------------------------------------------------
# Exaggerated / fabricated claims -- a small explicit list + a few patterns.
# ---------------------------------------------------------------------------
_CLAIM_PATTERNS: Sequence[tuple] = (
    (re.compile(r"ถล่มทลาย"), "ถล่มทลาย"),
    (re.compile(r"ที่สุดใน(?:โลก|ไทย|ประเทศ|จักรวาล|ตลาด)"), "ดีที่สุดในโลก"),
    (re.compile(r"อันดับ\s*(?:1|หนึ่ง)(?!\d)"), "อันดับ 1"),
    (re.compile(r"เบอร์\s*(?:1|หนึ่ง)(?!\d)"), "เบอร์ 1"),
    (re.compile(r"100\s*%\s*ไม่"), "100% ไม่"),
    (re.compile(r"ไม่มีวันพัง|ไม่พังแน่นอน|ไม่พังแน่ๆ"), "ไม่มีวันพัง"),
    (re.compile(r"การันตี\s*100"), "การันตี 100%"),
    (re.compile(r"รักษา(?:โรค|หาย)"), "รักษาโรค"),
    (re.compile(r"ใช้(?:งาน)?(?:จริง)?มา(?:แล้ว)?\s*\d+\s*(?:วัน|สัปดาห์|อาทิตย์|เดือน|ปี)"), "ใช้จริงมา N เดือน"),
    (re.compile(r"\d+\s*(?:เดือน|ปี)เต็ม"), "N เดือนเต็ม"),
    (re.compile(r"ขาย(?:ไป)?(?:แล้ว)?(?:กว่า)?\s*\d[\d,]*\s*(?:ชิ้น|ออเดอร์|ตัว|เครื่อง)"), "ยอดขายอ้างตัวเลข"),
    (re.compile(r"ยอดขายทะลุ|ขายดีที่สุด"), "ยอดขายเกินจริง"),
)

# ---------------------------------------------------------------------------
# Filler openers + CTA in the first line (Q3)
# ---------------------------------------------------------------------------
_FILLER_OPENER_PATTERNS: Sequence[tuple] = (
    (re.compile(r"อย่า(?:เพิ่ง)?เลื่อน"), "อย่าเพิ่งเลื่อนผ่าน"),
    (re.compile(r"หยุด(?:ดู|ก่อน|เลื่อน|นิ้ว)"), "หยุดดูก่อน"),
    (re.compile(r"ดู(?:คลิปนี้)?ให้จบ"), "ดูให้จบ"),
    (re.compile(r"ดูคลิปนี้"), "ดูคลิปนี้"),
    (re.compile(r"^\s*ทุกคน\s*(?:!|ดูนี่|ฟังทางนี้)"), "ทุกคน!"),
)

# "ก่อนกดซื้อ" / "ก่อนสั่งซื้อ" are not a CTA ("before you buy"), so they are
# excluded with a fixed-width look-behind.
_CTA_PATTERNS: Sequence[tuple] = (
    (re.compile(r"ตะกร้า"), "ตะกร้า"),
    (re.compile(r"(?<!ก่อน)กด(?:ซื้อ|สั่ง|ลิงก์|ลิงค์)"), "กดซื้อ"),
    (re.compile(r"(?<!ก่อน)สั่ง(?:ซื้อ|เลย)"), "สั่งเลย"),
    (re.compile(r"รีบกด|จิ้มเลย"), "รีบกด"),
)

ELLIPSIS_RE = re.compile(r"(\.{2,}|…)")

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
    "\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def _first_hit(patterns: Iterable[tuple], text: str) -> Optional[str]:
    for pattern, label in patterns:
        if pattern.search(text):
            return label
    return None


def find_price_term(text: str) -> Optional[str]:
    """Return a label for the first price/discount/price-guess hit, or None."""
    if not text:
        return None
    return _first_hit(_PRICE_PATTERNS, str(text))


def find_claim_term(text: str) -> Optional[str]:
    """Return a label for the first exaggerated/fabricated claim hit, or None."""
    if not text:
        return None
    return _first_hit(_CLAIM_PATTERNS, str(text))


def find_filler_opener(text: str) -> Optional[str]:
    """Return a label if `text` (a first line) asks the viewer to stop/watch."""
    if not text:
        return None
    return _first_hit(_FILLER_OPENER_PATTERNS, str(text))


def find_cta(text: str) -> Optional[str]:
    """Return a label if `text` contains a basket/buy CTA."""
    if not text:
        return None
    return _first_hit(_CTA_PATTERNS, str(text))


def _violation(code: str, message: str, field: str, index: int = -1) -> Dict[str, Any]:
    return {"code": code, "message": message, "field": field, "index": index}


def lint_text(text: Any, field: str = "text", index: int = -1) -> List[Dict[str, Any]]:
    """Run the hard compliance rules (price + claim) on one string.

    Returns a list of violations (empty when clean or when the lint is off).
    """
    if not COMPLIANCE_LINT_ENABLED or not text:
        return []
    s = str(text)
    out: List[Dict[str, Any]] = []
    price = find_price_term(s)
    if price:
        out.append(_violation(
            RULE_NO_PRICE,
            f"ห้ามพูด/แสดงราคา ส่วนลด หรือการทายราคา ('{price}') — ผิดกฎ TikTok",
            field, index,
        ))
    claim = find_claim_term(s)
    if claim:
        out.append(_violation(
            RULE_NO_EXAGGERATED_CLAIM,
            f"ห้ามเคลมเกินจริง/แต่งข้อมูลที่พิสูจน์ไม่ได้ ('{claim}')",
            field, index,
        ))
    return out


def lint_opening_line(text: Any, field: str = "lines[0].text") -> List[Dict[str, Any]]:
    """Q3: the first spoken line must not be a filler opener nor carry a CTA."""
    if not COMPLIANCE_LINT_ENABLED or not text:
        return []
    s = str(text)
    out: List[Dict[str, Any]] = []
    filler = find_filler_opener(s)
    if filler:
        out.append(_violation(
            RULE_NO_FILLER_OPENER,
            f"ประโยคแรกห้ามเป็นคำขอให้หยุดดู ('{filler}') ให้เปิดด้วยผลลัพธ์/ภาพ/คำถามเฉพาะสินค้า",
            field, 0,
        ))
    cta = find_cta(s)
    if cta:
        out.append(_violation(
            RULE_NO_CTA_FIRST_LINE,
            f"ห้ามมี CTA ในประโยคแรก ('{cta}') ให้เก็บไว้ท้ายคลิป",
            field, 0,
        ))
    return out


# ---------------------------------------------------------------------------
# Small deterministic sanitizers (never invent wording)
# ---------------------------------------------------------------------------
def strip_ellipsis(text: Any) -> str:
    """Replace '...'/'…' with a space and collapse whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", ELLIPSIS_RE.sub(" ", str(text))).strip()


def strip_emoji(text: Any) -> str:
    """Remove emoji (incl. variation selectors / ZWJ) and collapse whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", EMOJI_RE.sub("", str(text))).strip()


# ---------------------------------------------------------------------------
# Script-level lint (AI "script" task output)
# ---------------------------------------------------------------------------
SCRIPT_HOOK_FIELDS = ("hook_title", "hook_brand", "hook_model", "hook_label")


def lint_script(data: Any) -> List[Dict[str, Any]]:
    """Lint a script dict (`{"lines": [{"text", "on_screen", ...}], "hook_title", ...}`).

    Hard rules on every line `text` + `on_screen` + hook banner fields, plus
    the Q3 opener rule on line 1. Returns violations with `field`/`index`.
    """
    if not COMPLIANCE_LINT_ENABLED or not isinstance(data, dict):
        return []
    out: List[Dict[str, Any]] = []
    for key in SCRIPT_HOOK_FIELDS:
        out.extend(lint_text(data.get(key), field=key))
    lines = data.get("lines")
    if isinstance(lines, list):
        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            out.extend(lint_text(line.get("text"), field="text", index=i))
            out.extend(lint_text(line.get("on_screen"), field="on_screen", index=i))
        if lines and isinstance(lines[0], dict):
            for v in lint_opening_line(lines[0].get("text")):
                v["field"] = "text"
                out.append(v)
    return out


def enforce_script_compliance(data: Dict[str, Any]) -> tuple:
    """Remove every offending piece from a script dict in place.

    - line `text` with a price/claim hit -> the whole line is dropped
    - `on_screen` with a hit -> cleared
    - hook banner field with a hit -> cleared
    - first line that is a filler opener / CTA -> dropped (only if other
      lines remain, so we never return an empty script for that reason)

    Returns `(data, removed)` where `removed` lists the violations acted on.
    The caller must log `removed` (Thai) -- this never passes silently.
    """
    if not COMPLIANCE_LINT_ENABLED or not isinstance(data, dict):
        return data, []
    removed: List[Dict[str, Any]] = []
    for key in SCRIPT_HOOK_FIELDS:
        hits = lint_text(data.get(key), field=key)
        if hits:
            removed.extend(hits)
            data[key] = ""
    lines = data.get("lines")
    if isinstance(lines, list):
        kept: List[Any] = []
        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                kept.append(line)
                continue
            if line.get("on_screen"):
                line["on_screen"] = strip_ellipsis(line.get("on_screen"))
                hits = lint_text(line.get("on_screen"), field="on_screen", index=i)
                if hits:
                    removed.extend(hits)
                    line["on_screen"] = ""
            hits = lint_text(line.get("text"), field="text", index=i)
            if hits:
                removed.extend(hits)
                continue
            kept.append(line)
        if len(kept) > 1 and isinstance(kept[0], dict):
            opener_hits = lint_opening_line(kept[0].get("text"))
            if opener_hits:
                removed.extend(opener_hits)
                kept = kept[1:]
        data["lines"] = kept
    return data, removed


def lint_hook_variant(variant: Any) -> List[Dict[str, Any]]:
    """Lint one hook variant (hook_title/label/opening_line + opener rule)."""
    if not COMPLIANCE_LINT_ENABLED or not isinstance(variant, dict):
        return []
    out: List[Dict[str, Any]] = []
    for key in ("hook_title", "hook_label", "hook_brand", "hook_model", "opening_line"):
        out.extend(lint_text(variant.get(key), field=key))
    out.extend(lint_opening_line(variant.get("opening_line"), field="opening_line"))
    return out


def format_violations_th(violations: Sequence[Dict[str, Any]], limit: int = 6) -> str:
    """Compact Thai summary for logs / regeneration feedback."""
    parts = []
    for v in list(violations)[:limit]:
        where = v.get("field", "")
        if isinstance(v.get("index"), int) and v["index"] >= 0:
            where = f"บรรทัดที่ {v['index'] + 1} ({where})"
        parts.append(f"- {where}: {v.get('message', '')}")
    if len(violations) > limit:
        parts.append(f"- และอีก {len(violations) - limit} จุด")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# M3: deterministic script structure checker (warnings only)
# ---------------------------------------------------------------------------
# Roughly what the existing prompt already implies: 35–45 s ≈ 500–650 chars,
# 20–25 s ≈ 300–380 chars -> ~14.5 non-space characters per second of VO.
CHARS_PER_SECOND = 14.5
LENGTH_TOLERANCE = 0.15

_OPEN_LOOP_PATTERNS = (
    re.compile(r"เดี๋ยว|รอดู|ท้ายคลิป|ตอนท้าย|ข้อสุดท้าย|เก็บไว้ท้าย|เฉลย|จะบอก|บอกให้"),
    re.compile(r"ความลับ|ไม่มีใครบอก|ไม่ค่อยมีใครรู้|เพิ่งรู้|ต่างกันตรงไหน"),
    re.compile(r"\d+\s*(?:จุด|ข้อ|เหตุผล|สเต็ป|วิธี|อย่าง)"),
    re.compile(r"[?？]|ไหม|มั้ย|หรือเปล่า|รึเปล่า|ทำไม|ยังไง|อะไร|แค่ไหน"),
)

_FILLER_ENDING_PATTERNS = (
    re.compile(r"ตอบโจทย์ชีวิต|จบครบในตัวเดียว|ของมันต้องมี|ไม่ผิดหวัง|บอกเลยว่า"),
    re.compile(r"สุดๆ\s*(?:ครับ|ค่ะ)?\s*$"),
)

_COMMENT_QUESTION_RE = re.compile(r"คอมเมนต์|เมนต์|[?？]|ไหม|มั้ย|หรือเปล่า|อะไร|แบบไหน|ยังไง")


def count_script_chars(lines: Sequence[Any]) -> int:
    """Non-whitespace character count of all spoken line texts."""
    total = 0
    for line in lines or []:
        text = line.get("text", "") if isinstance(line, dict) else str(line or "")
        total += len(re.sub(r"\s+", "", str(text)))
    return total


def target_char_count(target_duration: Optional[float]) -> Optional[int]:
    if not target_duration or target_duration <= 0:
        return None
    return int(round(float(target_duration) * CHARS_PER_SECOND))


def check_script_structure(
    lines: Sequence[Any],
    target_duration: Optional[float] = None,
) -> Dict[str, Any]:
    """Check retention beats on a generated script. Never raises.

    - an open-loop / promise line within the first 2 lines
    - the last content line (before a trailing CTA line) is not generic filler
    - an open-ended comment question somewhere after line 1
    - total characters within target ±15% when `target_duration` is given

    Returns `{"ok": bool, "warnings": [{"code", "message"}], "char_count": int,
    "target_chars": int|None}`.
    """
    texts = [
        str(line.get("text", "") if isinstance(line, dict) else (line or "")).strip()
        for line in (lines or [])
    ]
    texts = [t for t in texts if t]
    warnings: List[Dict[str, str]] = []

    if texts:
        head = texts[:2]
        if not any(p.search(t) for t in head for p in _OPEN_LOOP_PATTERNS):
            warnings.append({
                "code": STRUCT_NO_OPEN_LOOP,
                "message": "ไม่พบ open loop/คำสัญญาใน 2 บรรทัดแรก (ควรบอกว่าเดี๋ยวจะได้เห็นอะไร)",
            })

        content = list(texts)
        if len(content) > 1 and find_cta(content[-1]):
            content = content[:-1]
        last = content[-1] if content else ""
        if last and (
            len(re.sub(r"\s+", "", last)) < 8
            or find_cta(last)
            or any(p.search(last) for p in _FILLER_ENDING_PATTERNS)
        ):
            warnings.append({
                "code": STRUCT_FILLER_ENDING,
                "message": f"บรรทัดเนื้อหาสุดท้ายเป็นคำลอยๆ ไม่ใช่ payoff ที่ผูกกับ hook: '{last[:40]}'",
            })

        if not any(_COMMENT_QUESTION_RE.search(t) for t in texts[1:]):
            warnings.append({
                "code": STRUCT_NO_COMMENT_QUESTION,
                "message": "ไม่พบคำถามปลายเปิดชวนคอมเมนต์ก่อน CTA (ห้ามเป็นคำถามทายราคา)",
            })

    char_count = count_script_chars(texts)
    target = target_char_count(target_duration)
    if target:
        lo = int(target * (1 - LENGTH_TOLERANCE))
        hi = int(round(target * (1 + LENGTH_TOLERANCE)))
        if not (lo <= char_count <= hi):
            warnings.append({
                "code": STRUCT_LENGTH_OFF_TARGET,
                "message": (
                    f"ความยาวสคริปต์ {char_count} ตัวอักษร ไม่อยู่ในเป้า {lo}–{hi} "
                    f"(คลิป {target_duration} วินาที ±15%)"
                ),
            })

    return {
        "ok": not warnings,
        "warnings": warnings,
        "char_count": char_count,
        "target_chars": target,
    }


__all__ = [
    "COMPLIANCE_LINT_ENABLED",
    "COUPLE_PRICE_KEYWORDS",
    "COUPLE_PRICE_SHORT_BAHT_RE",
    "RULE_NO_PRICE",
    "RULE_NO_EXAGGERATED_CLAIM",
    "RULE_NO_FILLER_OPENER",
    "RULE_NO_CTA_FIRST_LINE",
    "check_script_structure",
    "count_script_chars",
    "enforce_script_compliance",
    "find_claim_term",
    "find_couple_price_term",
    "find_cta",
    "find_filler_opener",
    "find_price_term",
    "format_violations_th",
    "lint_hook_variant",
    "lint_opening_line",
    "lint_script",
    "lint_text",
    "strip_ellipsis",
    "strip_emoji",
    "target_char_count",
]
