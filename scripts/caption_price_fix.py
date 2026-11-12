"""Rewrite a caption the posting guard refuses for price/discount wording (``price_in_caption``).

Owner decision 2026-11-13: an AI rewrite that keeps the caption's meaning and tone ("AI เขียนใหม่"), applied
automatically when a clip enters the queue and on demand for rows already queued ("แก้อัตโนมัติแล้วบอก").

Every result is checked again with the SAME guard the extension and /prepare use (``content_guard.content_reason``).
When the AI is unavailable or its answer still carries price wording, the caption becomes the neutral sentence the
product store already uses (``product_scraper.scrub_angle_price_text``), so a fix never fails open.

Results are cached on disk by (caption, hashtags, product name): the auto-fill preview and the save that follows it
produce exactly the same text, and re-opening a preview never spends another AI call.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from scripts import config
from scripts.content_guard import PRICE_RE, content_reason

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ELLIPSIS_RE = re.compile(r"\.{3,}|…")
MAX_WORKERS = 4


def _cache_path() -> Path:
    return Path(config.BASE_DIR) / "03_Projects" / ".cache" / "caption_price_fix.json"


def _load_cache() -> Dict[str, Any]:
    path = _cache_path()
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        logger.warning("caption_price_fix: เขียน cache ไม่สำเร็จ (%s)", exc)


def _key(caption: str, hashtags: str, product_name: str) -> str:
    raw = json.dumps([caption, hashtags, product_name], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def needs_fix(caption: Any, hashtags: Any = "") -> bool:
    return content_reason(caption or "", hashtags or "") == "price_in_caption"


def _ai_rewrite(caption: str, product_name: str, found: List[str]) -> Optional[str]:
    from scripts.ai_bridge import AIBridge
    result = AIBridge.generate(
        "caption_fix",
        {"caption": caption, "product_name": product_name or "สินค้า", "forbidden_found": found},
        prefer_antigravity=False,
    )
    text = str((result or {}).get("caption") or "").strip()
    return text or None


def _acceptable(candidate: Optional[str], hashtags: str, original: str) -> bool:
    if not candidate:
        return False
    if _ELLIPSIS_RE.search(candidate) or "#" in candidate:
        return False
    if len(candidate) > max(len(original) + 80, 300):
        return False
    return content_reason(candidate, hashtags) == ""


def fix_caption(
    caption: Any,
    hashtags: Any = "",
    product_name: Any = "",
    *,
    rewrite: Optional[Callable[[str, str, List[str]], Optional[str]]] = None,
) -> Dict[str, Any]:
    """Return ``{caption, hashtags, changed, method, found}``; ``method`` is ``ai`` / ``neutral`` / ``None``."""
    caption = str(caption or "")
    hashtags = str(hashtags or "")
    product_name = str(product_name or "")
    if not needs_fix(caption, hashtags):
        return {"caption": caption, "hashtags": hashtags, "changed": False, "method": None, "found": []}
    key = _key(caption, hashtags, product_name)
    with _LOCK:
        cached = _load_cache().get(key)
    if cached:
        return {**cached, "changed": True}

    from scripts.product_scraper import _scrub_hashtags, _short_name
    new_hashtags = _scrub_hashtags(hashtags) if PRICE_RE.search(hashtags) else hashtags
    found = sorted({m.group(0) for m in PRICE_RE.finditer(caption)})
    new_caption, method = caption, None
    if found:
        candidate = None
        for attempt in range(2):
            try:
                candidate = (rewrite or _ai_rewrite)(caption, product_name, found)
            except Exception as exc:  # AI down / quota / manual mode: fall back, never block the queue
                logger.warning("caption_price_fix: AI เขียน caption ใหม่ไม่สำเร็จ (%s) ใช้ประโยคกลางแทน", type(exc).__name__)
                candidate = None
                break
            if _acceptable(candidate, new_hashtags, caption):
                break
            candidate = None
        if candidate:
            new_caption, method = candidate, "ai"
        else:
            new_caption, method = f"{_short_name(product_name)} ดูรายละเอียดในตะกร้าเลยครับ 👇", "neutral"
    else:
        method = "hashtags"
    result = {"caption": new_caption, "hashtags": new_hashtags, "method": method, "found": found}
    if content_reason(new_caption, new_hashtags):
        # should not happen (both branches are checked): never hand back text the guard still refuses
        raise ValueError("caption_price_fix: ผลลัพธ์ยังไม่ผ่านตัวกันเนื้อหา")
    with _LOCK:
        cache = _load_cache()
        cache[key] = result
        _save_cache(cache)
    return {**result, "changed": True}


def fix_many(rows: Iterable[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """``fix_caption`` for several {caption, hashtags, product_name} rows, at most 4 AI calls at once."""
    rows = list(rows)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(lambda r: fix_caption(r.get("caption"), r.get("hashtags"), r.get("product_name"), **kwargs), rows))
