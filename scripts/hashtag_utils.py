"""
Hashtag Utilities for TikTok Video Production and Publishing (OmniCut Pro Studio).

Enforces:
1. Strict Max 5 Hashtags (TikTok Best Practice / Anti-Tag Stuffing Guard)
2. Safe Price Scrubbing (No price, promo, discount terms in tags)
3. Golden 5-Hashtag Formula for TikTok Shop Affiliate:
   - #Brand/Product (Niche Tag)
   - #Category/Feature (Target Tag)
   - #TikTokป้ายยา (Mega Traffic Shop Booster)
   - #ของดีบอกต่อ (General Trend & Social Proof)
   - #พิกัดในตะกร้า (Call-To-Action Cart Booster)
"""

import re
from typing import Any, List, Optional

MAX_TIKTOK_HASHTAGS = 5
MIN_TIKTOK_HASHTAGS = 3

DEFAULT_BOOSTER_TAGS = [
    "#TikTokป้ายยา",
    "#ของดีบอกต่อ",
    "#พิกัดในตะกร้า",
]

def _is_price_tag(tag: str) -> bool:
    """Check if tag contains price/discount terminology via product_scraper.has_price_text."""
    from scripts.product_scraper import has_price_text
    return bool(has_price_text(tag, caption=True))


def clean_single_tag(raw: str) -> str:
    """Clean a single tag string, ensuring leading # and stripping illegal characters."""
    t = str(raw).strip()
    if not t:
        return ""
    # Strip leading hashes or punctuation
    t = re.sub(r"^[#\s]+", "", t)
    # Remove emoji, symbols that break hashtags (keep alphanumeric, thai, underscore)
    t = re.sub(r"[^\w\u0E00-\u0E7F]+", "", t)
    if not t:
        return ""
    return f"#{t}"


def extract_hashtag_list(hashtags: Any) -> List[str]:
    """Parse hashtags input (string or list) into a list of normalized tag strings."""
    if not hashtags:
        return []
    if isinstance(hashtags, list):
        items = hashtags
    elif isinstance(hashtags, str):
        # Match either #tag or space-delimited words
        if "#" in hashtags:
            items = re.findall(r"#[\w\u0E00-\u0E7F]+", hashtags)
            if not items:
                items = hashtags.split()
        else:
            items = hashtags.split()
    else:
        items = str(hashtags).split()

    tags = []
    seen = set()
    for item in items:
        cleaned = clean_single_tag(item)
        if not cleaned:
            continue
        lower_key = cleaned.lower()
        if lower_key in seen:
            continue
        seen.add(lower_key)
        tags.append(cleaned)
    return tags


def normalize_tiktok_hashtags(
    hashtags: Any,
    product_name: Optional[str] = None,
    max_count: int = MAX_TIKTOK_HASHTAGS,
) -> str:
    """
    Standardize hashtags string for TikTok:
    - Removes price words
    - Deduplicates case-insensitively
    - Fills booster tags (#TikTokป้ายยา, #ของดีบอกต่อ, #พิกัดในตะกร้า) if < 3 tags
    - Caps to max_count (default 5) with smart retention of niche & booster tags
    Returns a single space-separated string.
    """
    raw_list = extract_hashtag_list(hashtags)

    # 1. Filter out price terms
    valid_tags: List[str] = [t for t in raw_list if not _is_price_tag(t)]

    # 2. If empty and product_name provided, generate a clean product tag
    if not valid_tags and product_name:
        clean_name = re.sub(r"[^\w\u0E00-\u0E7F]+", "", str(product_name).strip())
        if clean_name:
            prod_tag = f"#{clean_name[:20]}"
            if not _is_price_tag(prod_tag):
                valid_tags.append(prod_tag)

    # 3. Add booster tags if fewer than MIN_TIKTOK_HASHTAGS
    seen_lower = {t.lower() for t in valid_tags}
    if len(valid_tags) < MIN_TIKTOK_HASHTAGS:
        for booster in DEFAULT_BOOSTER_TAGS:
            if len(valid_tags) >= max_count:
                break
            if booster.lower() not in seen_lower:
                valid_tags.append(booster)
                seen_lower.add(booster.lower())

    # 4. Smart Cap at max_count (strict limit 5)
    if len(valid_tags) > max_count:
        # Separate high-conversion boosters vs product/content tags
        essential_boosters = [b for b in DEFAULT_BOOSTER_TAGS if any(b.lower() == t.lower() for t in valid_tags)]
        content_tags = [t for t in valid_tags if not any(b.lower() == t.lower() for b in DEFAULT_BOOSTER_TAGS)]

        needed_booster_slots = min(len(essential_boosters), max_count - 1)
        allowed_content_slots = max_count - needed_booster_slots

        final_tags = content_tags[:allowed_content_slots] + essential_boosters[:needed_booster_slots]
    else:
        final_tags = valid_tags

    return " ".join(final_tags)
