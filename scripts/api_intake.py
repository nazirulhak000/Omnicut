"""
Mobile Product Intake & Couple Script Review API (`scripts/api_intake.py`).

Mounted by `scripts/api_server.py` (or directly in unit tests):
- `POST /api/intake/parse`
- `POST /api/intake/preview`
- `POST /api/intake/commit`
- `POST /api/scripts/lint`
- `POST /api/scripts/generate-couple-20`
- `POST /api/scripts/{product_id}/angles/review`
- `PATCH /api/scripts/{product_id}/angles/{angle_id}`
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scripts.channel_scope import ChannelScope, get_channel_scope
from scripts.couple_script_generator import (
    generate_couple_20_scripts,
    generate_single_couple_angle,
)
from scripts.product_store import ProductStore
from scripts.script_rules import lint_couple_script, sanitize_text_for_rules

router = APIRouter(tags=["MobileIntake"])

# Matches TikTok shortlinks, full TikTok URLs, or general HTTP(S) URLs embedded in shared text
_TIKTOK_URL_RE = re.compile(
    r"(https?://(?:vt\.tiktok\.com|vm\.tiktok\.com|(?:www\.|m\.|shop\.)?tiktok\.com)/[^\s\"'<>]+)",
    flags=re.IGNORECASE,
)
_ANY_URL_RE = re.compile(r"(https?://[^\s\"'<>]+)", flags=re.IGNORECASE)
_PRODUCT_ID_IN_URL_RE = re.compile(
    r"(?:/(?:product|item|pdp)/(\d{10,})|[?&](?:item_id|itemId|product_id)=(\d{10,}))"
)
_STANDALONE_PRODUCT_ID_RE = re.compile(r"\b(\d{15,22})\b")


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def extract_clean_url_and_product_id(raw_text: str) -> Dict[str, Optional[str]]:
    """Extract a clean URL and optional TikTok product ID from messy share text."""
    text = (raw_text or "").strip()
    if not text:
        return {"url": None, "tiktok_product_id": None}

    clean_url: Optional[str] = None
    m_tt = _TIKTOK_URL_RE.search(text)
    if m_tt:
        clean_url = m_tt.group(1)
    else:
        m_any = _ANY_URL_RE.search(text)
        if m_any:
            clean_url = m_any.group(1)

    if clean_url:
        clean_url = clean_url.rstrip(".,;:!?)>]}'\"")

    product_id: Optional[str] = None
    search_target = clean_url or text
    m_pid = _PRODUCT_ID_IN_URL_RE.search(search_target)
    if m_pid:
        product_id = m_pid.group(1) or m_pid.group(2)
    else:
        m_num = _STANDALONE_PRODUCT_ID_RE.search(text)
        if m_num:
            product_id = m_num.group(1)

    return {"url": clean_url, "tiktok_product_id": product_id}


def _find_duplicate_product(
    url: Optional[str],
    tiktok_product_id: Optional[str],
    channel_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find an existing product in the channel scope by tiktok_product_id or URL."""
    products = ProductStore.snapshot(channel_id=channel_id)
    norm_url = (url or "").strip().rstrip("/")
    norm_pid = (tiktok_product_id or "").strip()

    for prod in products:
        existing_pid = str(prod.get("tiktok_product_id") or "").strip()
        if norm_pid and existing_pid and existing_pid == norm_pid:
            return prod
        existing_url = str(prod.get("url") or "").strip().rstrip("/")
        if norm_url and existing_url and existing_url == norm_url:
            return prod
    return None


def _looks_like_waf_challenge(info: Dict[str, Any]) -> bool:
    """Return True if scraper response indicates a WAF/CAPTCHA challenge or empty scrape."""
    if not isinstance(info, dict):
        return True
    if info.get("needs_manual") or info.get("challenge"):
        return True
    warning = str(info.get("warning") or info.get("source_warning") or "").lower()
    challenge_markers = (
        "security check",
        "captcha",
        "verify",
        "challenge",
        "waf",
        "เข้าถึงไม่ได้",
        "อ่านรายละเอียดหน้าเว็บไม่ได้",
        "ยังไม่ได้ติดตั้ง playwright",
    )
    if any(m in warning for m in challenge_markers):
        return True
    name = str(info.get("name") or info.get("title") or "").strip()
    if not name or name.lower() in ("tiktok", "tiktok shop", "verify to continue"):
        return True
    return False


def _safe_scrape_preview(url: str) -> Dict[str, Any]:
    """Attempt safe, headless-only metadata preview without launching a headed desktop browser."""
    try:
        from scripts.product_scraper import ProductScraper

        # Ensure we only call fast/non-interactive scrape if available; catch any failure cleanly
        info = ProductScraper.scrape_url(url)
        if isinstance(info, dict):
            return info
    except Exception as exc:
        return {"warning": f"ไม่สามารถดึงข้อมูลอัตโนมัติได้: {exc}", "needs_manual": True}
    return {"warning": "ไม่พบข้อมูลสินค้าจากลิงก์นี้", "needs_manual": True}


class IntakeParseRequest(BaseModel):
    text: str = Field(default="", description="Messy shared text or direct URL from TikTok")
    url: Optional[str] = Field(default=None, description="Optional explicit URL")


class IntakePreviewRequest(BaseModel):
    url: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    specs: Optional[List[Any]] = Field(default=None)
    photos: Optional[List[Any]] = Field(default=None)
    simulate_waf: bool = Field(default=False)


class IntakeCommitRequest(BaseModel):
    url: str = Field(default="")
    name: str
    code: Optional[str] = Field(default=None)
    tiktok_product_id: Optional[str] = Field(default=None)
    category: str = Field(default="")
    specs: List[Any] = Field(default_factory=list)
    selling_points: List[str] = Field(default_factory=list)
    photos: List[Any] = Field(default_factory=list)
    description: str = Field(default="")
    raw_text: str = Field(default="")


class ScriptLintRequest(BaseModel):
    script: Optional[Dict[str, Any]] = Field(default=None)
    turns: Optional[List[Any]] = Field(default=None)
    scripts: Optional[List[Any]] = Field(default=None)


class GenerateCouple20Request(BaseModel):
    product_id: Optional[str] = Field(default=None)
    product: Optional[Dict[str, Any]] = Field(default=None)
    force: bool = Field(default=False)


class AngleReviewRequest(BaseModel):
    angle_id: Optional[str] = Field(default=None)
    angle_ids: Optional[List[str]] = Field(default=None)
    state: str = Field(default="approved")
    note: str = Field(default="")
    approve_all_valid: bool = Field(default=False)


class AnglePatchRequest(BaseModel):
    turns: Optional[List[Dict[str, Any]]] = Field(default=None)
    title: Optional[str] = Field(default=None)
    hook_title: Optional[str] = Field(default=None)
    note: Optional[str] = Field(default=None)
    regenerate: bool = Field(default=False)
    reason: str = Field(default="")
    base_revision: Optional[int] = Field(default=None)


@router.post("/api/intake/parse")
def parse_intake_input(
    payload: IntakeParseRequest,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    combined = f"{payload.url or ''} {payload.text or ''}".strip()
    extracted = extract_clean_url_and_product_id(combined)
    clean_url = extracted["url"]
    tiktok_pid = extracted["tiktok_product_id"]

    if not clean_url and not tiktok_pid:
        raise HTTPException(status_code=422, detail="ไม่พบลิงก์สินค้าหรือรหัสสินค้าในข้อความที่วาง")

    existing = _find_duplicate_product(clean_url, tiktok_pid, channel_id=scope.channel_id)
    return {
        "url": clean_url,
        "tiktok_product_id": tiktok_pid or (existing.get("tiktok_product_id") if existing else None),
        "duplicate": existing is not None,
        "existing_product": existing,
    }


@router.post("/api/intake/preview")
def preview_intake_product(
    payload: IntakePreviewRequest,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    combined = f"{payload.url or ''} {payload.text or ''}".strip()
    extracted = extract_clean_url_and_product_id(combined)
    clean_url = extracted["url"] or (payload.url or "").strip()
    tiktok_pid = extracted["tiktok_product_id"]

    existing = _find_duplicate_product(clean_url, tiktok_pid, channel_id=scope.channel_id)

    if payload.simulate_waf:
        return {
            "url": clean_url,
            "name": (payload.name or "").strip(),
            "code": None,
            "tiktok_product_id": tiktok_pid,
            "specs": payload.specs or [],
            "photos": payload.photos or [],
            "needs_manual": True,
            "duplicate": existing is not None,
            "existing_product_id": existing.get("id") if existing else None,
            "warning": "TikTok ขอ Security Check กรุณาระบุชื่อสินค้าและจุดเด่นด้วยตนเอง",
        }

    # If user already provided manual name & specs, return clean preview immediately
    if payload.name and payload.name.strip():
        clean_name = sanitize_text_for_rules(payload.name.strip(), speaker="bao")
        return {
            "url": clean_url,
            "name": clean_name,
            "code": existing.get("product_code") if existing else None,
            "tiktok_product_id": tiktok_pid or (existing.get("tiktok_product_id") if existing else None),
            "specs": payload.specs or (existing.get("specs") if existing else []),
            "photos": payload.photos or (existing.get("images") if existing else []),
            "needs_manual": False,
            "duplicate": existing is not None,
            "existing_product_id": existing.get("id") if existing else None,
            "warning": "",
        }

    if existing:
        return {
            "url": clean_url or existing.get("url", ""),
            "name": existing.get("name", ""),
            "code": existing.get("product_code"),
            "tiktok_product_id": tiktok_pid or existing.get("tiktok_product_id"),
            "specs": existing.get("specs") or [],
            "photos": existing.get("images") or [],
            "needs_manual": False,
            "duplicate": True,
            "existing_product_id": existing.get("id"),
            "warning": "",
        }

    scraped = _safe_scrape_preview(clean_url) if clean_url else {"needs_manual": True}
    if _looks_like_waf_challenge(scraped):
        return {
            "url": clean_url,
            "name": "",
            "code": None,
            "tiktok_product_id": tiktok_pid or scraped.get("tiktok_product_id"),
            "specs": [],
            "photos": [],
            "needs_manual": True,
            "duplicate": False,
            "existing_product_id": None,
            "warning": scraped.get("warning")
            or "เว็บไซต์ติดระบบป้องกัน (WAF/Challenge) กรุณากรอกสเปกหรือจุดเด่นสินค้าด้วยตนเอง",
        }

    raw_photos = scraped.get("images") or scraped.get("photos") or []
    photos: List[Dict[str, Any]] = []
    for idx, p in enumerate(raw_photos):
        if isinstance(p, str) and p.strip():
            photos.append({"url": p.strip(), "name": f"photo_{idx + 1}", "starred": idx == 0})
        elif isinstance(p, dict):
            photos.append({**p, "starred": bool(p.get("starred", idx == 0))})

    clean_name = sanitize_text_for_rules(str(scraped.get("name") or scraped.get("title") or ""), speaker="bao")
    return {
        "url": clean_url,
        "name": clean_name,
        "code": scraped.get("product_code"),
        "tiktok_product_id": tiktok_pid or scraped.get("tiktok_product_id"),
        "specs": scraped.get("specs") or [],
        "photos": photos,
        "needs_manual": False,
        "duplicate": False,
        "existing_product_id": None,
        "warning": "",
    }


def _normalize_photos(photos: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(photos or []):
        if isinstance(item, str) and item.strip():
            normalized.append({
                "name": f"hero_{idx + 1}",
                "url": item.strip(),
                "starred": idx == 0,
            })
        elif isinstance(item, dict):
            url_or_path = item.get("url") or item.get("rel_path") or item.get("path") or ""
            if url_or_path:
                normalized.append({
                    "name": item.get("name") or f"hero_{idx + 1}",
                    "url": str(url_or_path),
                    "rel_path": item.get("rel_path"),
                    "path": item.get("path"),
                    "starred": bool(item.get("starred") or item.get("is_hero")),
                })
    if normalized and not any(p.get("starred") for p in normalized):
        normalized[0]["starred"] = True
    return normalized


def _normalize_specs(specs: List[Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in specs or []:
        if isinstance(item, dict):
            k = sanitize_text_for_rules(str(item.get("label") or item.get("key") or "จุดเด่น"), speaker="bao")
            v = sanitize_text_for_rules(str(item.get("value") or item.get("val") or ""), speaker="bao")
            if v:
                out.append({"label": k, "value": v})
        elif isinstance(item, str) and item.strip():
            clean_val = sanitize_text_for_rules(item.strip(), speaker="bao")
            if clean_val:
                out.append({"label": "จุดเด่น", "value": clean_val})
    return out


def _merge_angles_preserving_approved(
    existing_angles: List[Dict[str, Any]],
    new_angles: List[Dict[str, Any]],
    *,
    force: bool = False,
) -> List[Dict[str, Any]]:
    """Merge new angles into existing angles without overwriting approved/rendered angles."""
    if force or not existing_angles:
        return new_angles

    by_batch: Dict[int, Dict[str, Any]] = {}
    by_id: Dict[str, Dict[str, Any]] = {}
    for ang in existing_angles:
        if not isinstance(ang, dict):
            continue
        b = ang.get("batch")
        aid = str(ang.get("angle_id") or ang.get("id") or "")
        if isinstance(b, int):
            by_batch[b] = ang
        if aid:
            by_id[aid] = ang

    merged: List[Dict[str, Any]] = []
    for idx, new_ang in enumerate(new_angles):
        batch_num = new_ang.get("batch") or (idx + 1)
        aid = str(new_ang.get("angle_id") or new_ang.get("id") or "")
        prev = by_id.get(aid) or by_batch.get(batch_num)
        if prev:
            review_state = (prev.get("script_review") or {}).get("state")
            status = prev.get("status")
            if review_state == "approved" or status in ("in_production", "rendered", "posted"):
                merged.append(prev)
                continue
        merged.append(new_ang)
    return merged


@router.post("/api/intake/commit")
def commit_intake_product(
    payload: IntakeCommitRequest,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    clean_name = sanitize_text_for_rules((payload.name or "").strip(), speaker="bao")
    if not clean_name:
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อสินค้า")

    extracted = extract_clean_url_and_product_id(payload.url or "")
    clean_url = extracted["url"] or (payload.url or "").strip()
    tiktok_pid = (payload.tiktok_product_id or extracted["tiktok_product_id"] or "").strip() or None

    photos = _normalize_photos(payload.photos)
    specs = _normalize_specs(payload.specs)
    selling_points = [
        sanitize_text_for_rules(s, speaker="bao")
        for s in (payload.selling_points or [])
        if isinstance(s, str) and s.strip()
    ]
    if not selling_points and specs:
        selling_points = [s["value"] for s in specs if s.get("value")]

    existing = _find_duplicate_product(clean_url, tiktok_pid, channel_id=scope.channel_id)
    if existing:
        update_fields: Dict[str, Any] = {
            "name": clean_name,
            "specs": specs or existing.get("specs") or [],
            "selling_points": selling_points or existing.get("selling_points") or [],
            "images": photos or existing.get("images") or [],
        }
        if clean_url:
            update_fields["url"] = clean_url
        if tiktok_pid:
            update_fields["tiktok_product_id"] = tiktok_pid
        if payload.description:
            update_fields["description"] = sanitize_text_for_rules(payload.description, speaker="bao")
        if payload.raw_text:
            update_fields["raw_text"] = sanitize_text_for_rules(payload.raw_text, speaker="bao")
        # Never overwrite existing approved angles on commit
        updated = ProductStore.update(
            existing["id"],
            channel_id=scope.channel_id,
            **update_fields,
        )
        return {"product": updated, "merged": True}

    hero_thumb = next((p["url"] for p in photos if p.get("starred")), photos[0]["url"] if photos else "")
    created = ProductStore.add(
        name=clean_name,
        url=clean_url,
        category=payload.category,
        specs=specs,
        selling_points=selling_points,
        price_note="",  # Strict Zero-Price Rule
        thumbnail=hero_thumb,
        images=photos,
        tiktok_product_id=tiktok_pid,
        product_code=payload.code,
        description=sanitize_text_for_rules(payload.description, speaker="bao"),
        raw_text=sanitize_text_for_rules(payload.raw_text, speaker="bao"),
        channel_id=scope.channel_id,
    )
    return {"product": created, "merged": False}


@router.post("/api/scripts/lint")
def lint_scripts_endpoint(payload: ScriptLintRequest) -> Dict[str, Any]:
    if payload.scripts is not None:
        results = [lint_couple_script(item) for item in payload.scripts]
        all_violations = []
        for idx, res in enumerate(results):
            for v in res["violations"]:
                all_violations.append({**v, "script_index": idx})
        return {
            "valid": all(r["valid"] for r in results),
            "violations": all_violations,
            "results": results,
        }

    target = payload.script if payload.script is not None else {"turns": payload.turns or []}
    res = lint_couple_script(target)
    return {
        "valid": res["valid"],
        "violations": res["violations"],
        "results": [res],
    }


@router.post("/api/scripts/generate-couple-20")
def generate_couple_20_endpoint(
    payload: GenerateCouple20Request,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    product: Optional[Dict[str, Any]] = None
    if payload.product_id:
        product = ProductStore.find(payload.product_id, channel_id=scope.channel_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{payload.product_id}'")
    elif payload.product:
        product = dict(payload.product)
    else:
        raise HTTPException(status_code=422, detail="ต้องระบุ product_id หรือข้อมูล product")

    generated_angles = generate_couple_20_scripts(product)

    if payload.product_id and product.get("id"):
        merged_angles = _merge_angles_preserving_approved(
            product.get("angles") or [],
            generated_angles,
            force=payload.force,
        )
        updated = ProductStore.update(
            product["id"],
            channel_id=scope.channel_id,
            angles=merged_angles,
            status="scripted",
        )
        final_angles = updated.get("angles") or merged_angles
    else:
        final_angles = generated_angles

    valid_count = sum(1 for a in final_angles if lint_couple_script(a)["valid"])
    return {
        "product_id": product.get("id"),
        "total": len(final_angles),
        "valid_count": valid_count,
        "angles": final_angles,
    }


@router.post("/api/scripts/{product_id}/angles/review")
def review_product_angles(
    product_id: str,
    payload: AngleReviewRequest,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    if payload.state not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=422, detail="state ต้องเป็น approved, rejected หรือ pending")

    product = ProductStore.find(product_id, channel_id=scope.channel_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")

    angles = list(product.get("angles") or [])
    if not angles:
        raise HTTPException(status_code=422, detail="สินค้านี้ยังไม่มีสคริปต์")

    target_ids = set(payload.angle_ids or [])
    if payload.angle_id:
        target_ids.add(payload.angle_id)

    now = _now_iso()
    updated_ids: List[str] = []
    skipped_invalid_ids: List[str] = []

    for ang in angles:
        aid = str(ang.get("angle_id") or ang.get("id") or "")
        should_apply = payload.approve_all_valid or (aid in target_ids)
        if not should_apply:
            continue

        lint_res = lint_couple_script(ang)
        ang["lint"] = lint_res

        target_state = "approved" if payload.approve_all_valid else payload.state
        if target_state == "approved" and not lint_res["valid"]:
            if not payload.approve_all_valid and len(target_ids) == 1:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "ไม่สามารถอนุมัติบทที่ยังไม่ผ่านกฎได้",
                        "violations": lint_res["violations"],
                    },
                )
            skipped_invalid_ids.append(aid)
            continue

        ang["script_review"] = {
            "state": target_state,
            "at": now,
            "note": payload.note,
        }
        ang["revision"] = int(ang.get("revision") or 1) + 1
        updated_ids.append(aid)

    updated_product = ProductStore.update(
        product_id,
        channel_id=scope.channel_id,
        angles=angles,
    )
    return {
        "product_id": product_id,
        "updated_angle_ids": updated_ids,
        "skipped_invalid_ids": skipped_invalid_ids,
        "angles": updated_product.get("angles") or [],
    }


@router.patch("/api/scripts/{product_id}/angles/{angle_id}")
def patch_product_angle(
    product_id: str,
    angle_id: str,
    payload: AnglePatchRequest,
    scope: ChannelScope = Depends(get_channel_scope),
) -> Dict[str, Any]:
    product = ProductStore.find(product_id, channel_id=scope.channel_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")

    angles = list(product.get("angles") or [])
    target_idx: Optional[int] = None
    for idx, ang in enumerate(angles):
        aid = str(ang.get("angle_id") or ang.get("id") or "")
        if aid == angle_id:
            target_idx = idx
            break

    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"ไม่พบบทสคริปต์ '{angle_id}'")

    current_angle = dict(angles[target_idx])
    current_revision = int(current_angle.get("revision") or 1)

    if payload.base_revision is not None and payload.base_revision != current_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "revision_conflict",
                "message": f"บทนี้ถูกแก้ไขจากอีกหน้าจอแล้ว (revision ปัจจุบันคือ {current_revision})",
                "current_revision": current_revision,
                "current_angle": current_angle,
            },
        )

    if payload.regenerate:
        regenerated = generate_single_couple_angle(
            product,
            target_idx,
            reason=payload.reason or payload.note or "",
        )
        current_angle["turns"] = regenerated["turns"]
        current_angle["title"] = regenerated["title"]
        current_angle["hook_title"] = regenerated["hook_title"]
        current_angle["script_review"] = {
            "state": "pending",
            "at": _now_iso(),
            "note": payload.reason or payload.note or "",
        }
    else:
        if payload.turns is not None:
            normalized_turns: List[Dict[str, Any]] = []
            for t in payload.turns:
                disp = str(t.get("display") or "")
                spok = str(t.get("spoken") or disp)
                spk = str(t.get("speaker") or "nui")
                normalized_turns.append({
                    "speaker": spk,
                    "display": disp,
                    "spoken": spok,
                    "phrases": [{"display": disp, "spoken": spok}],
                    "photo": t.get("photo"),
                })
            current_angle["turns"] = normalized_turns
        if payload.title is not None:
            current_angle["title"] = payload.title
        if payload.hook_title is not None:
            current_angle["hook_title"] = payload.hook_title
        if payload.note is not None:
            review = dict(current_angle.get("script_review") or {"state": "pending", "at": _now_iso()})
            review["note"] = payload.note
            review["at"] = _now_iso()
            current_angle["script_review"] = review

    lint_res = lint_couple_script(current_angle)
    current_angle["lint"] = lint_res
    if not lint_res["valid"]:
        # If edited script now violates a rule, downgrade approved -> pending
        review = dict(current_angle.get("script_review") or {})
        if review.get("state") == "approved":
            review["state"] = "pending"
            review["at"] = _now_iso()
            current_angle["script_review"] = review

    current_angle["revision"] = current_revision + 1
    angles[target_idx] = current_angle

    ProductStore.update(
        product_id,
        channel_id=scope.channel_id,
        angles=angles,
    )
    return {
        "product_id": product_id,
        "angle": current_angle,
        "revision": current_angle["revision"],
        "lint": lint_res,
    }
