"""Caption/hashtag content guard for TikTok posting -- Python twin of ``OmniPostGuard.contentReason``.

Both implementations are tested against the same cases in ``tests/fixtures/content_guard_cases.json``;
change a rule in one place and the parity test fails until the other follows.

Reasons: ``''`` (ok) | ``empty_caption`` | ``placeholder_in_caption`` | ``price_in_caption`` |
``caption_too_long`` | ``too_many_hashtags``.
"""
from __future__ import annotations

import re
import unicodedata

MAX_TEXT_CHARS = 4000
MAX_HASHTAGS = 30

_INVISIBLE = re.compile("[­​-‏‪-‮⁠-⁤﻿]")
_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 3) | {0x066A: "%", 0xFF05: "%"}

# Price / discount wording. ฟรี, โปร and ถูก on their own are NOT price text; a number with a currency,
# a percentage, a discount word or the word ราคา is.
PRICE_RE = re.compile(
    r"฿|[$€£¥]\s*\d|\d\s*[$€£¥]"
    r"|\b(?:thb|usd|baht)\b"
    r"|\d[\d,.]*\s*(?:บาท|บ\.|baht|฿|k\s*บาท)"
    r"|\d+\.-"
    r"|ราคา|ลดราคา|ส่วนลด|ร้อยละ"
    r"|ลด\s*\d+\s*(?:%|บาท|฿|\.-)|ลดเหลือ|ลด\s*\d+\s*เหลือ"
    r"|\d+\s*%"
    r"|\d+\s*%?\s*off\b|\boff\s*\d"
    r"|(?:เหลือ|เพียง|เริ่มต้น|เริ่มที่|แค่)\s*\d+\s*(?:บาท|฿|\.-)?(?=\s|$|[^\d%a-z])",
    re.I | re.A,
)

PLACEHOLDER_RE = re.compile(
    r"\{[a-z][a-z0-9_]*\}|\{\{[^}]*\}\}|\$\{[^}]*\}|\[[a-z]+_[a-z_]+\]|<[a-z]+_[a-z_]+>|%[sd]\b"
    r"|\b(?:undefined|null|nan)\b|\btodo\b|\blorem ipsum\b",
    re.I | re.A,
)

_HASHTAG_RE = re.compile(r"#[^\s#]+")


def normalize_text(text: object) -> str:
    """NFKC, no zero-width/format characters, Thai digits -> ASCII, single spaces, lower case."""
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = _INVISIBLE.sub("", value).translate(_THAI_DIGITS)
    return re.sub(r"\s+", " ", value).strip().lower()


def content_reason(caption: object, hashtags: object = "", *, allow_price: bool = False) -> str:
    raw = f"{caption or ''}\n\n{hashtags or ''}"
    text = normalize_text(raw)
    if not text:
        return "empty_caption"
    if PLACEHOLDER_RE.search(text):
        return "placeholder_in_caption"
    if not allow_price and PRICE_RE.search(text):
        return "price_in_caption"
    if len(raw) > MAX_TEXT_CHARS:
        return "caption_too_long"
    if len(_HASHTAG_RE.findall(raw)) > MAX_HASHTAGS:
        return "too_many_hashtags"
    return ""
