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
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from scripts.ai_bridge import AIBridge, ManualModeRequired
from scripts.it_angles import ANGLES_BY_KEY, catalog_for_prompt, fallback_angles
from scripts.post_log import METRIC_FIELDS, PostLog
from scripts.product_store import STATUSES, ProductStore
from scripts.project_manifest import REROLL_STAGE, ProjectManifest
from scripts import render_jobs

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
        "mode": "auto" if AIBridge.has_api_key() else "manual",
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


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    specs: Optional[List[Dict[str, str]]] = None
    pain_points: Optional[List[str]] = None
    selling_points: Optional[List[str]] = None
    price_note: Optional[str] = None
    target_buyer: Optional[str] = None
    status: Optional[str] = None
    angles: Optional[List[Dict[str, Any]]] = None


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

        request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept-Language": "th,en"})
        with urllib.request.urlopen(request, timeout=12) as response:
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
    return {"products": ProductStore.list(status), "summary": ProductStore.summary()}


@router.post("/products")
def create_product(req: ProductCreateRequest):
    try:
        product = ProductStore.add(**req.model_dump())
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {"success": True, "product": product}


@router.patch("/products/{product_id}")
def update_product(product_id: str, req: ProductUpdateRequest):
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
    hook_title: Optional[str] = None
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    font_name: Optional[str] = None
    bilingual_subtitles: Optional[bool] = None
    voice_gender: Optional[str] = None
    voice_rate: Optional[str] = None
    voice_preset: Optional[str] = None
    ad_tone: Optional[str] = None
    sticker_path: Optional[str] = None


# What each button costs, so the UI can warn before a slow one.
REROLL_COST = {
    "hook": "เร็ว (~30 วิ) — ใช้เสียงเดิม",
    "subtitles": "เร็ว (~40 วิ) — ใช้เสียงเดิม",
    "video": "ปานกลาง — ตัดวิดีโอใหม่ ใช้เสียงและซับเดิม",
    "voice": "ช้า (2-4 นาที) — พากย์ใหม่ทั้งคลิป",
    "script": "ช้าที่สุด (2-4 นาที) — เขียนบทใหม่แล้วพากย์ใหม่",
}


@router.get("/projects")
def list_projects():
    return {"projects": ProjectManifest.list_projects()}


@router.get("/projects/{project_name}")
def get_project(project_name: str):
    manifest = ProjectManifest.load(project_name)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"ไม่พบโปรเจกต์ '{project_name}'")
    return manifest


def _execute_reroll(job_id: str, project_name: str, stage: str, overrides: Dict[str, Any]) -> None:
    from scripts.pipeline import TikTokAutoCutterPipeline

    try:
        manifest = ProjectManifest.require(project_name)
        params = dict(manifest.get("render_params") or {})
        params.update({k: v for k, v in overrides.items() if v is not None})

        with render_jobs.render_slot(job_id):
            result = TikTokAutoCutterPipeline.run(
                product_name=params.get("product_name", project_name),
                raw_video_path=params["raw_video_path"],
                project_name=project_name,
                key_features=params.get("key_features", ""),
                pain_point=params.get("pain_point", ""),
                price_deal=params.get("price_deal", ""),
                custom_script=params.get("custom_script"),
                script_overlays=params.get("script_overlays"),
                voice=params.get("voice", "male"),
                voice_rate=params.get("voice_rate", "+15%"),
                voice_engine_type=params.get("voice_engine_type", "edge_tts"),
                voice_preset=params.get("voice_preset"),
                ad_tone=params.get("ad_tone", "commercial_premium"),
                human_voice_audio_path=params.get("human_voice_audio_path"),
                hook_title=params.get("hook_title"),
                font_name=params.get("font_name", "IBMPlex"),
                bilingual_subtitles=params.get("bilingual_subtitles", True),
                sticker_path=params.get("sticker_path"),
                export_mp4=True,
                resume_from=stage,
                progress_callback=render_jobs.progress_reporter(job_id),
            )
        render_jobs.complete_job(job_id, result, message="🎉 สุ่มใหม่เสร็จแล้ว!")

    except Exception as err:
        render_jobs.fail_job(job_id, err)


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

    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id, message=f"กำลังสุ่มใหม่: {req.part}...")
    background_tasks.add_task(_execute_reroll, job_id, req.project_name, stage, overrides)

    return {"job_id": job_id, "status": "queued", "part": req.part, "cost": REROLL_COST.get(req.part, "")}
