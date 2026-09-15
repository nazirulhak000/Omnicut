"""
Phase 1 API router — AI bridge, angle catalog, and the post log.

Kept in its own router so it can be mounted with a single include_router() call
and reviewed without touching the existing endpoints.
"""

import re
import json
import uuid
import html
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from scripts.ai_bridge import AIBridge, ManualModeRequired
from scripts.quota import is_quota_error
from scripts.hook_motion_presets import hook_motion_catalog
from scripts.it_angles import ANGLES_BY_KEY, catalog_for_prompt, fallback_angles
from scripts.subtitle_engine import DEFAULT_HOOK_MOTION
from scripts.post_log import METRIC_FIELDS, PostLog
from scripts.product_store import STATUSES, ProductStore
from scripts.product_scraper import _build_safe_image_opener, _validate_public_http_url
from scripts.config import BASE_DIR, COVERS_DIR, STICKERS_DIR
from scripts.project_manifest import REROLL_STAGE, ProjectManifest
from scripts import render_jobs
from scripts.render_jobs import RenderCancelled
from scripts.task_manager import TaskManager
from scripts.api_products import _with_product_source_fallback

router = APIRouter(prefix="/api", tags=["phase1"])

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


# ----------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------
class AIPromptRequest(BaseModel):
    task: str
    context: Dict[str, Any]


class AIParseRequest(BaseModel):
    task: str
    raw_text: str


class PostCreateRequest(BaseModel):
    product_name: str
    clip_file: str
    platform: str = "tiktok"
    product_url: str = ""
    angle_key: str = ""
    angle_title: str = ""
    hook: str = ""
    caption: str = ""
    hashtags: List[str] = []


class MetricsRequest(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    cart_clicks: Optional[int] = None
    orders: Optional[int] = None
    commission_thb: Optional[float] = None


# ----------------------------------------------------------------------
# AI bridge
# ----------------------------------------------------------------------
@router.post("/ai/prompt")
def ai_prompt(req: AIPromptRequest):
    """
    Run an AI task. Returns finished data when a key is configured, otherwise
    the prompt for the user to paste into their own chat.
    """
    try:
        data = AIBridge.generate(req.task, req.context)
        return {"mode": "auto", "task": req.task, "data": data}
    except ManualModeRequired as manual:
        return {"mode": "manual", "task": req.task, "prompt": manual.prompt}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:  # SDK/network failures must not kill the panel
        # A quota hit is the user's own daily cap stopping the call, not a
        # provider failure -- surface it as a real error instead of silently
        # degrading to manual mode (which would hide why the AI call was
        # skipped). Any other AppError category (and every non-AppError
        # exception) keeps falling back to manual mode exactly as before.
        if is_quota_error(err):
            raise HTTPException(status_code=429, detail=err.suggestion_th)
        try:
            prompt = AIBridge.build_prompt(req.task, req.context)
        except ValueError as build_err:
            raise HTTPException(status_code=400, detail=str(build_err))
        return {
            "mode": "manual",
            "task": req.task,
            "prompt": prompt,
            "warning": f"เรียก AI อัตโนมัติไม่สำเร็จ ใช้โหมดวางเองแทน ({err})",
        }


@router.post("/ai/parse")
def ai_parse(req: AIParseRequest):
    """Turn a pasted answer into validated data."""
    try:
        return {"task": req.task, "data": AIBridge.parse_response(req.task, req.raw_text)}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("/ai/status")
def ai_status():
    return {
        "mode": "auto" if AIBridge.is_available() else "manual",
        "provider": (
            "antigravity_pro"
            if AIBridge.has_antigravity_cli()
            else ("gemini_api" if AIBridge.has_api_key() else "manual")
        ),
        "model": (
            "gemini-3.8-flash-high (Antigravity Pro)"
            if AIBridge.has_antigravity_cli()
            else ("gemini-2.5-flash" if AIBridge.has_api_key() else None)
        ),
        "tasks": {key: spec["label"] for key, spec in AIBridge.TASKS.items()},
    }


# ----------------------------------------------------------------------
# Angle catalog
# ----------------------------------------------------------------------
@router.get("/angles")
def get_angles(seller_assets_only: bool = False, product_name: str = ""):
    """Angle catalog for IT products, plus no-LLM fallback angles."""
    return {
        "catalog": catalog_for_prompt(seller_assets_only=seller_assets_only),
        "fallback": fallback_angles(product_name or "สินค้านี้", seller_assets_only=seller_assets_only),
        "total": len(ANGLES_BY_KEY),
    }


@router.get("/hook-motion-presets")
def get_hook_motion_presets():
    """
    The four hook-banner motion pickers (In / Loop / Out / Accent). The
    editor renders whatever this returns rather than keeping its own copy of
    the list, so a preset added in hook_motion_presets.py + a builder in
    subtitle_engine.py shows up in the UI without a frontend change.
    """
    return {"catalog": hook_motion_catalog(), "default": DEFAULT_HOOK_MOTION}


# ----------------------------------------------------------------------
# Post log
# ----------------------------------------------------------------------
@router.get("/posts")
def get_posts():
    return {
        "posts": PostLog.list_posts(),
        "summary": PostLog.summary(),
        "pending_metrics": PostLog.pending_metrics(),
        "metric_fields": list(METRIC_FIELDS),
    }


@router.post("/posts")
def create_post(req: PostCreateRequest):
    """Record that a clip went live."""
    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="ต้องระบุชื่อสินค้า")
    if not req.clip_file.strip():
        raise HTTPException(status_code=400, detail="ต้องระบุไฟล์คลิปที่โพสต์")

    post = PostLog.add_post(
        product_name=req.product_name,
        clip_file=req.clip_file,
        platform=req.platform,
        product_url=req.product_url,
        angle_key=req.angle_key,
        angle_title=req.angle_title,
        hook=req.hook,
        caption=req.caption,
        hashtags=req.hashtags,
    )
    return {"success": True, "post": post, "summary": PostLog.summary()}


@router.post("/posts/{post_id}/metrics")
def set_metrics(post_id: str, req: MetricsRequest):
    """Fill in the 48-hour numbers."""
    try:
        post = PostLog.update_metrics(post_id, req.model_dump(exclude_none=True))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {"success": True, "post": post, "summary": PostLog.summary()}


@router.get("/posts/performance")
def get_performance():
    """Which angles actually earn — empty until metrics have been filled in."""
    return {"by_angle": PostLog.angle_performance(), "summary": PostLog.summary()}


# ----------------------------------------------------------------------
# Product queue
# ----------------------------------------------------------------------
def _cover_stem(value: object) -> str:
    """Return the filename stem used by the cover renderer."""
    text = str(value or "").strip().replace("\\", "/")
    text = text.rsplit("/", 1)[-1]
    if not text:
        return ""
    stem = Path(text).stem
    return re.sub(r"_cover(?:_3x4)?$", "", stem, flags=re.IGNORECASE)


def _cover_url(relative_path: Optional[str]) -> str:
    if not relative_path:
        return ""
    return f"/api/media/{urllib.parse.quote(str(relative_path).replace(chr(92), '/'), safe='/')}"


def _hydrate_product_covers(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach persisted or discoverable cover variants to product angles.

    Older cover renders predate the angle association API. For those records,
    look up the renderer's canonical ``<stem>_cover*.jpg`` siblings using the
    angle project/video identity. New renders already carry paths and simply
    receive their media URLs here.
    """
    covers_root = COVERS_DIR.resolve()
    for product in products:
        angles = product.get("angles") or []
        for angle in angles:
            cover_path = angle.get("cover_path") or ""
            cover_3x4_path = angle.get("cover_3x4_path") or ""
            cover_9x16_path = angle.get("cover_9x16_path") or ""

            if cover_path:
                if cover_path.casefold().endswith("_cover_3x4.jpg"):
                    cover_3x4_path = cover_3x4_path or cover_path
                else:
                    cover_9x16_path = cover_9x16_path or cover_path

            # Product name is a safe fallback only for a single-angle product;
            # otherwise one legacy file could appear on every angle.
            if not (cover_path or cover_3x4_path or cover_9x16_path):
                stems = [angle.get("project_name"), Path(str(angle.get("video_url") or "")).stem]
                if len(angles) == 1:
                    stems.append(product.get("name"))
                for raw_stem in stems:
                    stem = _cover_stem(raw_stem)
                    if not stem:
                        continue
                    candidate_9x16 = covers_root / f"{stem}_cover.jpg"
                    candidate_3x4 = covers_root / f"{stem}_cover_3x4.jpg"
                    if candidate_9x16.is_file() or candidate_3x4.is_file():
                        if candidate_9x16.is_file():
                            cover_9x16_path = str(candidate_9x16.relative_to(BASE_DIR.resolve())).replace("\\", "/")
                        if candidate_3x4.is_file():
                            cover_3x4_path = str(candidate_3x4.relative_to(BASE_DIR.resolve())).replace("\\", "/")
                        break

            if cover_9x16_path:
                angle["cover_9x16_path"] = cover_9x16_path
            if cover_3x4_path:
                angle["cover_3x4_path"] = cover_3x4_path
            if not cover_path:
                cover_path = cover_9x16_path or cover_3x4_path
            if cover_path:
                angle["cover_path"] = cover_path

            url_9x16 = _cover_url(cover_9x16_path)
            url_3x4 = _cover_url(cover_3x4_path)
            if url_9x16:
                angle["cover_9x16_url"] = url_9x16
                angle["cover_url"] = url_9x16
                angle["media_url"] = url_9x16
            elif url_3x4:
                angle["cover_url"] = url_3x4
                angle["media_url"] = url_3x4
            if url_3x4:
                angle["cover_3x4_url"] = url_3x4
                angle["media_url_3x4"] = url_3x4
    return products


class ProductFetchRequest(BaseModel):
    url: str


class ProductCreateRequest(BaseModel):
    name: str
    url: str = ""
    platform: str = ""
    category: str = ""
    specs: List[Dict[str, str]] = []
    pain_points: List[str] = []
    selling_points: List[str] = []
    price_note: str = ""
    target_buyer: str = ""
    thumbnail: str = ""
    product_code: Optional[str] = None
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    specs: Optional[List[Any]] = None
    pain_points: Optional[List[str]] = None
    selling_points: Optional[List[str]] = None
    price_note: Optional[str] = None
    target_buyer: Optional[str] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None
    metadata_source: Optional[str] = None
    source_warning: Optional[str] = None
    status: Optional[str] = None
    angles: Optional[List[Dict[str, Any]]] = None
    tiktok_product_id: Optional[str] = None
    product_code: Optional[str] = None
    # Product images can be either scraped URL strings or local upload
    # records. Keep this permissive so attaching images later does not reject
    # products created by older scraper versions.
    images: Optional[List[Any]] = None
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    apply_to_angles: Optional[bool] = None


def _meta_tag(html_text: str, prop: str) -> str:
    """Pull one og:/twitter: meta value, with attributes in either order."""
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\'](.*?)["\']',
        rf'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


@router.post("/product/fetch")
def fetch_product(req: ProductFetchRequest):
    """
    Read what a product page publishes about itself — og: tags, or TikTok's
    oEmbed endpoint. Deliberately shallow: no login, no headless browser, no
    scraping past what the page hands out, so it stays within each site's terms.

    A blocked page is not an error. It returns `blocked: true` and the UI asks
    the user to type the details instead.
    """
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="ต้องเป็นลิงก์ที่ขึ้นต้นด้วย http:// หรือ https://")

    # This endpoint fetches whatever URL the caller sends and reflects up to
    # ~400KB of the response back as title/raw_text -- with no auth and CORS
    # wide open, that's a full SSRF primitive (cloud metadata endpoints,
    # 127.0.0.1, the internal network) unless the target is checked first.
    # Same guard product_scraper.py already uses for /api/products/scrape,
    # just without its Shopee/TikTok domain allowlist -- this endpoint is
    # meant to accept any product page host (Lazada and others included),
    # so only the public-IP check applies here.
    try:
        _validate_public_http_url(url, require_allowed_domain=False)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    platform = ProductStore.detect_platform(url)

    try:
        if platform == "tiktok":
            oembed = f"https://www.tiktok.com/oembed?url={urllib.parse.quote(url, safe='')}"
            request = urllib.request.Request(oembed, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8", errors="ignore"))
            return {
                "blocked": False,
                "platform": platform,
                "url": url,
                "title": data.get("title", ""),
                "thumbnail": data.get("thumbnail_url", ""),
                "description": data.get("author_name", ""),
                "raw_text": data.get("title", ""),
            }

        # _build_safe_image_opener() re-validates every redirect hop (still
        # public-IP-only, no domain allowlist) before following it -- urllib
        # follows redirects automatically and, unguarded, would fetch
        # whatever a 3xx on an otherwise-legit URL points at next.
        request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept-Language": "th,en"})
        with _build_safe_image_opener().open(request, timeout=12) as response:
            page = response.read(400_000).decode("utf-8", errors="ignore")

        title = _meta_tag(page, "og:title") or _meta_tag(page, "twitter:title")
        if not title:
            match = re.search(r"<title[^>]*>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
            title = html.unescape(match.group(1)).strip() if match else ""

        description = _meta_tag(page, "og:description") or _meta_tag(page, "twitter:description")
        thumbnail = _meta_tag(page, "og:image") or _meta_tag(page, "twitter:image")
        price = _meta_tag(page, "product:price:amount") or _meta_tag(page, "og:price:amount")

        return {
            "blocked": not (title or description),
            "platform": platform,
            "url": url,
            "title": title,
            "description": description,
            "thumbnail": thumbnail,
            "price_note": price,
            "raw_text": f"{title}\n{description}".strip(),
        }

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as err:
        # Shopee in particular blocks plain requests. Say so plainly rather
        # than pretending the product does not exist.
        return {
            "blocked": True,
            "platform": platform,
            "url": url,
            "title": "",
            "raw_text": "",
            "warning": f"ดึงข้อมูลจากหน้านี้ไม่ได้ ({err}) — กรอกชื่อและสเปคเองได้เลย",
        }


@router.get("/products")
def list_products(status: Optional[str] = None):
    if status and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"status ต้องเป็นหนึ่งใน {', '.join(STATUSES)}")
    products = [_with_product_source_fallback(product) for product in ProductStore.list(status)]
    products = _hydrate_product_covers(products)
    return {"products": products, "summary": ProductStore.summary()}


@router.post("/products")
def create_product(req: ProductCreateRequest):
    try:
        product = ProductStore.add(**req.model_dump())
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {"success": True, "product": product}


@router.patch("/products/{product_id}")
def update_product(product_id: str, req: ProductUpdateRequest):
    if req.url:
        parsed_url = urllib.parse.urlparse(req.url.strip())
        hostname = (parsed_url.hostname or "").lower().rstrip(".")
        allowed_domains = ("tiktok.com", "shopee.co.th", "shp.ee")
        if parsed_url.scheme not in ("http", "https") or not hostname or not any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in allowed_domains
        ):
            raise HTTPException(status_code=400, detail="URL สินค้าต้องเป็นลิงก์ http(s) จาก TikTok หรือ Shopee")
    try:
        product = ProductStore.update(product_id, **req.model_dump(exclude_none=True))
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    return {"success": True, "product": product}


@router.delete("/products/{product_id}")
def delete_product(product_id: str):
    try:
        ProductStore.delete(product_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    return {"success": True}


# ----------------------------------------------------------------------
# Projects and partial re-rolls
# ----------------------------------------------------------------------
class RerollRequest(BaseModel):
    project_name: str
    part: str  # hook | subtitles | voice | script | video
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    hook_duration: Optional[float] = None
    hook_motion: Optional[Dict[str, Any]] = None
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, Any]] = None
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    font_name: Optional[str] = None
    bilingual_subtitles: Optional[bool] = None
    show_watermark: Optional[bool] = None
    voice_gender: Optional[str] = None
    voice_rate: Optional[str] = None
    voice_preset: Optional[str] = None
    ad_tone: Optional[str] = None
    style_preset: Optional[str] = None
    sticker_path: Optional[str] = None
    # The editor picks a badge by file name (same shape as RenderRequest);
    # "" means "no badge" and must clear whatever the manifest already has.
    sticker_badge: Optional[str] = None
    bgm_name: Optional[str] = None
    lut_name: Optional[str] = None
    lut_intensity: Optional[float] = None
    bgm_volume: Optional[float] = None
    bgm_ducking: Optional[bool] = None
    export_preset: Optional[str] = None
    caption_position: Optional[str] = None
    caption_color: Optional[str] = None
    caption_scale: Optional[float] = None
    sticker_position: Optional[str] = None
    sticker_scale: Optional[float] = None
    clip_list: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Any]] = None
    text_overlays: Optional[List[Dict[str, Any]]] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    # Both plural arrays were previously missing from this model entirely --
    # FastAPI/Pydantic silently drops any field the frontend sends that isn't
    # declared here, so the multi-sticker editor UI's "Apply"/reroll path
    # never actually reached the renderer (only the singular legacy
    # sticker_badge/_position/_scale fields above did). Declaring them here
    # is what makes both the sticker array AND the new effects array actually
    # take effect on reroll, not just on a from-scratch /api/render.
    stickers: Optional[List[Dict[str, Any]]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    spotlight: Optional[Dict[str, Any]] = None
    background_isolation: Optional[Dict[str, Any]] = None


# What each button costs, so the UI can warn before a slow one.
REROLL_COST = {
    "hook": "เร็ว (~30 วิ) — ใช้เสียงเดิม",
    "subtitles": "เร็ว (~40 วิ) — ใช้เสียงเดิม",
    "video": "ปานกลาง — ตัดวิดีโอใหม่ ใช้เสียงและซับเดิม",
    "voice": "ช้า (2-4 นาที) — พากย์ใหม่ทั้งคลิป",
    "bgm": "ปานกลาง — มิกซ์เสียงใหม่แล้วตัดวิดีโอใหม่ ใช้เสียงพากย์เดิม",
    "script": "ช้าที่สุด (2-4 นาที) — เขียนบทใหม่แล้วพากย์ใหม่",
}


@router.get("/projects")
def list_projects():
    return {"projects": ProjectManifest.list_projects()}


def _project_origin(project_name: str):
    """The product and angle a project was rendered from, if they still exist."""
    manifest = ProjectManifest.load(project_name)
    params = (manifest or {}).get("render_params") or {}
    # Prefer the stable ids the render pipeline stamps into render_params
    # (see video_assembly_stage.py) -- matching by product_name/hook_title
    # text risks grabbing the WRONG product/angle when two happen to share
    # a name, which is disastrous here since this feeds project deletion.
    product_id = params.get("product_id") or ((manifest or {}).get("product") or {}).get("id") or ""
    angle_id = params.get("angle_id") or ((manifest or {}).get("angle") or {}).get("angle_id") or ((manifest or {}).get("angle") or {}).get("id") or ""
    product, angle = ProductStore.find_by_project(
        project_name,
        product_id=product_id,
        angle_id=angle_id,
    )
    return manifest, product, angle


@router.get("/projects/{project_name}/origin")
def project_origin(project_name: str):
    """
    What else deleting this project could take with it, so the UI can name it
    instead of guessing. A project rendered before the product link was
    recorded can usually still be traced by product name, but its exact angle
    often cannot -- say so rather than removing the wrong script.
    """
    manifest, product, angle = _project_origin(project_name)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")
    return {
        "project_name": project_name,
        "product": None if not product else {
            "id": product["id"],
            "name": product.get("name") or product.get("title") or "",
            "angle_count": len(product.get("angles") or []),
        },
        "angle": None if not angle else {
            "angle_id": angle.get("angle_id"),
            "angle_name": angle.get("angle_name") or "",
            "hook_title": angle.get("hook_title") or "",
            "status": angle.get("status") or "",
            "posted_at": angle.get("posted_at"),
            "is_posted": angle.get("status") == "posted" or bool(angle.get("posted_at")),
        },
    }


@router.delete("/projects/{project_name}")
def delete_project(project_name: str, scope: str = "project"):
    """
    Delete a project folder for good.

    Refuses while a render is running: the pipeline writes into this folder and
    pulling it out from under a job leaves half-written files and a job that
    fails with a confusing error. Exported mp4s live in 04_Exports and are
    untouched -- deleting the project you edited must not remove the video you
    already posted.
    """
    if render_jobs.is_busy():
        raise HTTPException(
            status_code=409,
            detail="กำลังเรนเดอร์อยู่ — รอให้เสร็จก่อนแล้วค่อยลบโปรเจกต์",
        )
    if scope not in ("project", "angle", "product"):
        raise HTTPException(status_code=400, detail=f"scope '{scope}' ไม่ถูกต้อง")

    # Read the origin before the folder goes: the manifest is what points at it.
    # Also used (regardless of scope) to scope the rollback below to the
    # specific product/angle this project belongs to -- rolling back by
    # filename/project_name alone risks touching an unrelated angle that
    # happens to share the same stem.
    extra: Dict[str, Any] = {}
    _, origin_product, origin_angle = _project_origin(project_name)
    if scope in ("angle", "product"):
        product, angle = origin_product, origin_angle
        if not product:
            raise HTTPException(
                status_code=409,
                detail="หาสินค้าที่ผูกกับโปรเจกต์นี้ไม่เจอ — ลบเฉพาะโปรเจกต์ได้อย่างเดียว",
            )
        if scope == "angle":
            if not angle:
                raise HTTPException(
                    status_code=409,
                    detail="หามุม/สคริปต์ที่ตรงกับโปรเจกต์นี้ไม่เจอ — เลือกลบทั้งสินค้าหรือลบเฉพาะโปรเจกต์แทน",
                )
            if angle.get("status") == "posted" or angle.get("posted_at"):
                raise HTTPException(
                    status_code=400,
                    detail="ไม่อนุญาตให้ลบมุมที่โพสต์แล้ว เนื่องจากต้องเก็บไว้เป็นหลักฐาน (สามารถเลือกลบเฉพาะโปรเจกต์ตัดต่อเพื่อคืนพื้นที่ดิสก์ได้)",
                )
            extra = ProductStore.remove_angle(product["id"], angle["angle_id"])
        else:
            posted_angles = [a for a in product.get("angles", []) if a.get("status") == "posted" or a.get("posted_at")]
            if posted_angles:
                raise HTTPException(
                    status_code=400,
                    detail=f"ไม่อนุญาตให้ลบสินค้า '{product.get('name')}' เนื่องจากมีคลิปที่โพสต์แล้ว {len(posted_angles)} มุม (ต้องเก็บไว้เป็นหลักฐาน)",
                )
            ProductStore.delete(product["id"])
            extra = {"product_removed": product["id"], "angles_removed": len(product.get("angles") or [])}

    try:
        ProductStore.rollback_by_video_or_project(
            project_name,
            product_id=(origin_product or {}).get("id") or "",
            angle_id=(origin_angle or {}).get("angle_id") or "",
        )
        return {"success": True, "scope": scope, **ProjectManifest.delete(project_name), **extra}
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except OSError as err:
        # WinError 32 here almost always means this very server still has the
        # project's audio open for an editor <audio> element. Say so, because
        # "[WinError 32] used by another process" sends people hunting for a
        # media player that was never involved.
        if getattr(err, "winerror", None) == 32:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"ลบไม่ได้เพราะไฟล์ยังถูกเปิดค้างอยู่: {getattr(err, 'filename', '') or err}. "
                    "ปิดแท็บ Editor ของโปรเจกต์นี้ (หรือเปลี่ยนไปโปรเจกต์อื่น) แล้วลองใหม่"
                ),
            )
        raise HTTPException(status_code=500, detail=f"ลบไม่สำเร็จ: {err}")


@router.post("/projects/{project_name}/archive")
def archive_project(project_name: str):
    """
    Move a project folder from 03_Projects/ to 06_Archive/Projects/.
    Keeps exported videos in 04_Exports/ intact.
    """
    if render_jobs.is_busy():
        raise HTTPException(
            status_code=409,
            detail="กำลังเรนเดอร์งานอยู่ ไม่สามารถย้ายโปรเจกต์เข้าคลังประวัติได้ในขณะนี้",
        )
    try:
        res = ProjectManifest.archive(project_name)
        return {"success": True, **res}
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการย้ายเข้าคลัง: {err}")


@router.get("/projects/{project_name}")
def get_project(project_name: str):
    manifest = ProjectManifest.load(project_name)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")
    try:
        _, product, angle = _project_origin(project_name)
        if angle:
            manifest["angle_status"] = angle.get("status")
            manifest["posted_at"] = angle.get("posted_at")
            manifest["is_posted"] = angle.get("status") == "posted" or bool(angle.get("posted_at"))
    except Exception:
        pass
    return manifest


@router.get("/projects/{project_name}/snapshots")
def list_project_snapshots(project_name: str):
    """Returns list of rolling snapshots (.bak1, .bak2, .bak3) available for this project."""
    try:
        snapshots = ProjectManifest.get_snapshots(project_name)
        return {"project_name": project_name, "snapshots": snapshots}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/projects/{project_name}/snapshots/{snapshot_id}/restore")
def restore_project_snapshot(project_name: str, snapshot_id: str):
    """Restores the project manifest from a rolling backup snapshot."""
    try:
        restored = ProjectManifest.restore_snapshot(project_name, snapshot_id)
        return {"success": True, "project_name": project_name, "snapshot_id": snapshot_id, "manifest": restored}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))



class UpdateCuesRequest(BaseModel):
    cues: Optional[List[Dict[str, Any]]] = None
    micro_cues: Optional[List[Dict[str, Any]]] = None


@router.patch("/projects/{project_name}/cues")
def update_project_cues(project_name: str, req: UpdateCuesRequest):
    """
    Manual Editor caption edits: persist edited cue text/timing into the
    manifest only -- no re-render here. `SubtitleEngine.generate_ass()`
    already reads whatever cues are in the manifest, so the caller follows
    this up with `POST /api/reroll` (`part: "subtitles"` or `"video"`) to
    actually regenerate the .ass / final MP4 from the edited cues.
    """
    if req.cues is None and req.micro_cues is None:
        raise HTTPException(status_code=400, detail="ต้องส่ง cues หรือ micro_cues มาอย่างน้อยหนึ่งอย่าง")

    # Existence check and field computation both happen inside save_merge's
    # mutator (under ProjectManifest._SAVE_LOCK) rather than from an earlier,
    # separate load() -- see update_project_state below for why that matters.
    def _mutate(current: Dict[str, Any]) -> Dict[str, Any]:
        if not current:
            raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")
        fields: Dict[str, Any] = {}
        if req.cues is not None:
            fields["cues"] = req.cues
        if req.micro_cues is not None:
            fields["micro_cues"] = req.micro_cues
        return fields

    updated = ProjectManifest.save_merge(project_name, _mutate)
    return {"success": True, "cues": updated.get("cues"), "micro_cues": updated.get("micro_cues")}


class UpdateClipsRequest(BaseModel):
    clip_list: List[Dict[str, Any]]
    transitions: Optional[List[Any]] = None


@router.patch("/projects/{project_name}/clips")
def update_project_clips(project_name: str, req: UpdateClipsRequest):
    """
    Manual Editor clip/trim edits: persist edited clip_list into manifest.
    """
    # render_params is read-modify-written as a whole field below, so the
    # read has to happen under the same lock as the write (save_merge) --
    # see update_project_state's docstring note for the race this avoids.
    def _mutate(current: Dict[str, Any]) -> Dict[str, Any]:
        if not current:
            raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")

        fields: Dict[str, Any] = {
            "clip_list": req.clip_list,
        }
        render_params = dict(current.get("render_params") or {})
        render_params["clip_list"] = req.clip_list
        if req.transitions is not None:
            fields["transitions"] = req.transitions
            render_params["transitions"] = req.transitions
        fields["render_params"] = render_params
        return fields

    updated = ProjectManifest.save_merge(project_name, _mutate)
    return {"success": True, "clip_list": updated.get("clip_list")}


class UpdateProjectStateRequest(BaseModel):
    cues: Optional[List[Dict[str, Any]]] = None
    micro_cues: Optional[List[Dict[str, Any]]] = None
    clip_list: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Any]] = None
    style_preset: Optional[str] = None
    style: Optional[Dict[str, Any]] = None
    # EditorShell.jsx's autosave and manual-save both send these on every
    # edit -- omitted here before, Pydantic silently drops unknown fields
    # (no error, no warning), so the hook banner's edits in the Editor never
    # actually reached the manifest.
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    hook_duration: Optional[float] = None
    hook_motion: Optional[Dict[str, Any]] = None
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, Any]] = None
    text_overlays: Optional[List[Dict[str, Any]]] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    spotlight: Optional[Dict[str, Any]] = None
    background_isolation: Optional[Dict[str, Any]] = None
    track_mix: Optional[Dict[str, Any]] = None
    audio_mutes: Optional[Dict[str, bool]] = None


@router.patch("/projects/{project_name}/state")
def update_project_state(project_name: str, req: UpdateProjectStateRequest):
    """
    Unified atomic save for manual Editor state (captions, clips, transitions, style).
    Saves everything in a single atomic manifest transaction.

    Uses ProjectManifest.save_merge() rather than load()-then-save(): this
    handler fires on every autosave tick, and it decides its new
    render_params by reading the CURRENT manifest and patching a few keys
    into a copy of it. If that read happens before save()'s own lock (as a
    plain load()+save() would), a render pipeline finishing concurrently and
    writing its own fresh render_params in between would get silently
    reverted by this call's save() -- a real request X reads old
    render_params, a render elsewhere saves new render_params from output it
    just produced, then request X's save() (atomic by itself) overwrites that
    with values computed from its own stale read. save_merge() runs the read
    and the write under the same lock so nothing else can land in between.
    """
    def _mutate(current: Dict[str, Any]) -> Dict[str, Any]:
        if not current:
            raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")

        fields: Dict[str, Any] = {}
        render_params = dict(current.get("render_params") or {})

        if req.track_mix is not None:
            fields["track_mix"] = req.track_mix
            render_params["track_mix"] = req.track_mix
        if req.audio_mutes is not None:
            fields["audio_mutes"] = req.audio_mutes
            render_params["audio_mutes"] = req.audio_mutes

        if req.cues is not None:
            fields["cues"] = req.cues
        if req.micro_cues is not None:
            fields["micro_cues"] = req.micro_cues
        if req.clip_list is not None:
            fields["clip_list"] = req.clip_list
            render_params["clip_list"] = req.clip_list
        if req.transitions is not None:
            fields["transitions"] = req.transitions
            render_params["transitions"] = req.transitions
        if req.style_preset is not None:
            fields["style_preset"] = req.style_preset
            render_params["style_preset"] = req.style_preset
        if req.style is not None:
            fields["style"] = dict(req.style)
            for k, v in req.style.items():
                fields[k] = v
                render_params[k] = v
        # Top-level AND render_params, matching EditorShell.jsx's load priority
        # (data.hook_brand first, data.render_params?.hook_brand as fallback) --
        # writing only one of the two would leave the other stale.
        if req.hook_brand is not None:
            fields["hook_brand"] = req.hook_brand
            render_params["hook_brand"] = req.hook_brand
        if req.hook_model is not None:
            fields["hook_model"] = req.hook_model
            render_params["hook_model"] = req.hook_model
        if req.hook_label is not None:
            fields["hook_label"] = req.hook_label
            render_params["hook_label"] = req.hook_label
        if req.hook_duration is not None:
            fields["hook_duration"] = req.hook_duration
            render_params["hook_duration"] = req.hook_duration
        if req.hook_motion is not None:
            fields["hook_motion"] = req.hook_motion
            render_params["hook_motion"] = req.hook_motion
        if req.hook_colors is not None:
            fields["hook_colors"] = req.hook_colors
            render_params["hook_colors"] = req.hook_colors
        if req.hook_style is not None:
            fields["hook_style"] = req.hook_style
            render_params["hook_style"] = req.hook_style
        if req.text_overlays is not None:
            fields["text_overlays"] = req.text_overlays
            render_params["text_overlays"] = req.text_overlays
        if req.overlays is not None:
            # Written at both levels because the editor reads the top level first
            # and the pipeline reads render_params; writing one left them
            # disagreeing until the next save.
            fields["overlays"] = req.overlays
            render_params["overlays"] = req.overlays
        if req.stickers is not None:
            fields["stickers"] = req.stickers
            render_params["stickers"] = req.stickers
        if req.effects is not None:
            fields["effects"] = req.effects
            render_params["effects"] = req.effects
        if req.spotlight is not None:
            fields["spotlight"] = req.spotlight
            render_params["spotlight"] = req.spotlight
        if req.background_isolation is not None:
            fields["background_isolation"] = req.background_isolation
            render_params["background_isolation"] = req.background_isolation

        fields["render_params"] = render_params
        return fields

    updated = ProjectManifest.save_merge(project_name, _mutate)
    return {
        "success": True,
        "cues": updated.get("cues"),
        "micro_cues": updated.get("micro_cues"),
        "clip_list": updated.get("clip_list"),
        "overlays": updated.get("overlays"),
        "updated_at": updated.get("updated_at"),
    }


def _execute_reroll(job_id: str, project_name: str, stage: str, overrides: Dict[str, Any]) -> None:
    from scripts.pipeline import TikTokAutoCutterPipeline

    try:
        manifest = ProjectManifest.require(project_name)
        params = dict(manifest.get("render_params") or {})
        # Fallback to root manifest keys if render_params wasn't populated
        for k in [
            "raw_video_path", "product_name", "key_features", "pain_point", "price_deal",
            "custom_script", "script_overlays", "voice", "voice_rate", "voice_engine_type",
            "voice_preset", "ad_tone", "human_voice_audio_path",
            "style_preset",
            "hook_brand", "hook_model", "hook_label", "hook_duration", "hook_motion", "hook_colors", "hook_style",
            "overlays",
            "font_name", "bilingual_subtitles", "show_watermark", "sticker_path", "bgm_name", "bgm_volume",
            "bgm_ducking", "lut_name", "lut_intensity", "caption_position", "caption_color",
            "audio_mutes",
            "caption_scale", "sticker_position", "sticker_scale", "clip_list", "transitions",
            "text_overlays", "stickers", "effects"
        ]:
            if k not in params and k in manifest and manifest[k] is not None:
                params[k] = manifest[k]
        params.update({k: v for k, v in overrides.items() if v is not None})

        # Ensure raw_video_path is resolved
        raw_video = params.get("raw_video_path")
        if not raw_video and manifest.get("clip_list"):
            raw_video = manifest["clip_list"][0].get("source_path")
        if not raw_video:
            raw_video = str(BASE_DIR / "01_Raw")

        # Resolve product_id and angle_id for accurate lifecycle synchronization
        product_id = params.get("product_id") or (manifest.get("product") or {}).get("id")
        angle_id = params.get("angle_id") or (manifest.get("angle") or {}).get("id") or (manifest.get("angle") or {}).get("angle_id")
        if not (product_id and angle_id):
            prod, ang = ProductStore.find_by_project(
                project_name,
                product_id=product_id or "",
                angle_id=angle_id or ""
            )
            if prod and not product_id:
                product_id = prod.get("id")
            if ang and not angle_id:
                angle_id = ang.get("angle_id") or ang.get("id")

        # Snapshot the angle's pre-reroll status/video so a failed reroll can
        # restore exactly what was there before this attempt started (e.g. a
        # "rendered" angle with a good prior video must not get stuck on
        # "in_production" just because this reroll attempt failed).
        prev_status = None
        prev_video_url = None
        prev_export_id = None
        if product_id and angle_id:
            try:
                existing_product = ProductStore.get(product_id)
                existing_angle = next(
                    (
                        a for a in (existing_product or {}).get("angles", [])
                        if (a.get("angle_id") or a.get("id")) == angle_id
                    ),
                    None,
                )
                if existing_angle:
                    prev_status = existing_angle.get("status")
                    prev_video_url = existing_angle.get("video_url")
                    prev_export_id = existing_angle.get("export_id")
                    if prev_status == "posted" or existing_angle.get("posted_at"):
                        raise HTTPException(
                            status_code=400,
                            detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
                        )
            except HTTPException:
                raise
            except Exception as snapshot_err:
                print(f"Warning: could not snapshot pre-reroll angle state: {snapshot_err}")
        elif project_name:
            for prod in ProductStore._load():
                for a in prod.get("angles", []):
                    if a.get("project_name") == project_name:
                        if a.get("status") == "posted" or a.get("posted_at"):
                            raise HTTPException(
                                status_code=400,
                                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้เรนเดอร์ซ้ำ เพื่อรักษาหลักฐานเดิม"
                            )

        if product_id and angle_id:
            try:
                ProductStore.update_angle_status(
                    product_id,
                    angle_id,
                    "in_production",
                    project_name=project_name
                )
            except Exception:
                pass

        def _restore_pre_reroll_snapshot() -> None:
            """
            Put the angle back exactly where it was before this reroll
            attempt started. Shared by the cancel path and the generic
            failure path below -- both mean "this attempt never happened",
            so both restore the same snapshot rather than one of them
            hardcoding "in_production" independently.
            """
            if not (product_id and angle_id):
                return
            try:
                if prev_status is not None:
                    ProductStore.update_angle_status(
                        product_id,
                        angle_id,
                        prev_status,
                        video_url=prev_video_url,
                        project_name=project_name,
                        export_id=prev_export_id,
                    )
                else:
                    # Snapshot was never taken (product/angle missing at
                    # snapshot time, e.g. deleted mid-reroll) -- fall back to
                    # the old hardcoded behavior rather than guessing.
                    print(
                        f"Warning: no pre-reroll snapshot for angle '{angle_id}' "
                        f"(product '{product_id}') -- falling back to 'in_production'"
                    )
                    ProductStore.update_angle_status(
                        product_id,
                        angle_id,
                        "in_production",
                        project_name=project_name
                    )
            except Exception:
                pass

        base_progress = render_jobs.progress_reporter(job_id)

        def on_progress(msg: str, progress: float):
            base_progress(msg, progress)
            TaskManager.update_progress(job_id, progress, step_label=msg)

        with render_jobs.render_slot(job_id):
            result = TikTokAutoCutterPipeline.run(
                cancel_event=render_jobs.get_cancel_event(job_id),
                product_name=params.get("product_name", project_name),
                raw_video_path=raw_video,
                project_name=project_name,
                key_features=params.get("key_features", ""),
                pain_point=params.get("pain_point", ""),
                price_deal=params.get("price_deal", ""),
                custom_script=params.get("custom_script"),
                script_overlays=params.get("script_overlays"),
                voice=params.get("voice", "male"),
                voice_rate=params.get("voice_rate", "+15%"),
                voice_engine_type=params.get("voice_engine_type", "gemini_tts"),
                voice_preset=params.get("voice_preset", "gemini_puck_male_hype"),
                ad_tone=params.get("ad_tone", "commercial_hype"),
                style_preset=params.get("style_preset", "clean_tech_review"),
                human_voice_audio_path=params.get("human_voice_audio_path"),
                overlays=params.get("overlays"),
                hook_brand=params.get("hook_brand"),
                hook_model=params.get("hook_model"),
                hook_label=params.get("hook_label"),
                hook_duration=float(params.get("hook_duration", 5.0) or 5.0),
                hook_motion=params.get("hook_motion"),
                hook_colors=params.get("hook_colors"),
                hook_style=params.get("hook_style"),
                font_name=params.get("font_name", "IBMPlex"),
                bilingual_subtitles=params.get("bilingual_subtitles", True),
                show_watermark=params.get("show_watermark", True),
                sticker_path=params.get("sticker_path"),
                bgm_name=params.get("bgm_name"),
                bgm_volume=params.get("bgm_volume"),
                bgm_ducking=bool(params.get("bgm_ducking")),
                audio_mutes=params.get("audio_mutes"),
                lut_name=params.get("lut_name"),
                lut_intensity=params.get("lut_intensity", 1.0),
                # never sticky: a draft is a one-off, the project keeps its
                # post-quality setting for the next render
                export_preset=overrides.get("export_preset", "post"),
                product_id=product_id,
                angle_id=angle_id,
                caption_position=params.get("caption_position", "bottom"),
                caption_color=params.get("caption_color"),
                caption_scale=params.get("caption_scale", 1.0),
                sticker_position=params.get("sticker_position", "top_right"),
                sticker_scale=params.get("sticker_scale", 1.0),
                clip_list=params.get("clip_list"),
                transitions=params.get("transitions"),
                text_overlays=params.get("text_overlays"),
                stickers=params.get("stickers"),
                effects=params.get("effects"),
                spotlight=params.get("spotlight"),
                background_isolation=params.get("background_isolation"),
                export_mp4=True,
                resume_from=stage,
                progress_callback=on_progress,
            )

        # Round: the pipeline's own result_paths key is "mp4_video"
        # (video_assembly_stage.py) -- "mp4"/"output_video"/"video_path" were
        # never keys it sets, so this always read "" here and every reroll
        # left the angle stuck on "in_production" no matter how the render
        # actually finished. api_render.py's initial-render path already
        # checked "mp4_video" correctly; this path just never matched it.
        mp4_val = result.get("mp4_video") or result.get("mp4") or result.get("output_video") or result.get("video_path") or ""
        if product_id and angle_id:
            try:
                ProductStore.update_angle_status(
                    product_id,
                    angle_id,
                    "rendered" if mp4_val else "in_production",
                    video_url=str(mp4_val) if mp4_val else None,
                    project_name=project_name,
                    export_id=result.get("export_id") if mp4_val else None,
                )
            except Exception as update_err:
                print(f"Warning: could not update angle status after reroll: {update_err}")

        if product_id:
            try:
                ProductStore.attach_project(product_id, project_name)
            except Exception:
                pass

        render_jobs.complete_job(job_id, result, message="🎉 เรนเดอร์เสร็จสมบูรณ์!")
        TaskManager.complete_task(
            job_id,
            result=result,
            step_label="🎉 เรนเดอร์วิดีโอเสร็จสมบูรณ์ 100%!",
            target_id=project_name,
        )

    except RenderCancelled:
        # Same "this attempt never happened" outcome as a failure, but the
        # user asked for it -- restore the pre-reroll snapshot exactly as the
        # generic failure path does (reused via _restore_pre_reroll_snapshot
        # rather than duplicated), then bring all three systems to the real
        # terminal "cancelled" state instead of "failed".
        _restore_pre_reroll_snapshot()
        render_jobs.cancel_job(job_id)
        TaskManager.cancel_task(job_id)

    except Exception as err:
        # Restore whatever the angle actually was before this reroll attempt
        # started, instead of hardcoding "in_production" -- an angle that was
        # "rendered" (with a perfectly good prior video) must land back on
        # "rendered" with that same video_url, not get stuck requiring manual
        # intervention.
        _restore_pre_reroll_snapshot()
        render_jobs.fail_job(job_id, err)
        TaskManager.fail_task(job_id, str(err), step_label="เรนเดอร์วิดีโอล้มเหลว")


@router.post("/reroll")
def trigger_reroll(req: RerollRequest, background_tasks: BackgroundTasks):
    """
    Rebuild one part of an existing clip, reusing everything earlier in the
    chain. Returns the same job shape as /api/render so the frontend can watch
    it with the polling loop it already has.
    """
    stage = REROLL_STAGE.get(req.part)
    if not stage:
        raise HTTPException(
            status_code=400,
            detail=f"part '{req.part}' ไม่ถูกต้อง — ต้องเป็นหนึ่งใน {', '.join(REROLL_STAGE)}",
        )

    manifest = ProjectManifest.load(req.project_name)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=f"ไม่พบ manifest ของ '{req.project_name}' — ต้อง render เต็มรอบก่อนอย่างน้อย 1 ครั้ง",
        )

    overrides = req.model_dump(exclude={"project_name", "part"}, exclude_none=True)
    if "voice_gender" in overrides:
        overrides["voice"] = overrides.pop("voice_gender")

    # A badge name resolves to a path the same way /api/render does. "Clear the
    # badge" is written as "" rather than None on purpose: _execute_reroll
    # merges with `if v is not None`, so a None would be dropped and the badge
    # already in the manifest would survive. "" survives the merge and reads as
    # falsy where the renderer checks it.
    if "sticker_badge" in overrides:
        badge = overrides.pop("sticker_badge")
        resolved = ""
        if badge:
            candidate = STICKERS_DIR / badge
            if candidate.exists():
                resolved = str(candidate)
            elif (BASE_DIR / badge).exists():
                resolved = str(BASE_DIR / badge)
        overrides["sticker_path"] = resolved

    job_id = str(uuid.uuid4())
    part_label = "เรนเดอร์วิดีโอ" if req.part in ("subtitles", "bgm", "video") else f"สุ่มใหม่: {req.part}"
    render_jobs.create_job(job_id, message=f"กำลัง{part_label}...")

    # Register in global TaskManager so Activity Center tracks it in real-time
    TaskManager.create_task(
        task_type="render_video",
        title=f"{part_label}: {req.project_name}",
        payload={"project_name": req.project_name, "part": req.part},
        target_tab="editor",
        target_id=req.project_name,
        task_id=job_id,
    )

    background_tasks.add_task(_execute_reroll, job_id, req.project_name, stage, overrides)

    return {"job_id": job_id, "status": "queued", "part": req.part, "cost": REROLL_COST.get(req.part, "")}
