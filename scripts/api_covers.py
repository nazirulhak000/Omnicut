"""
Cover image generation for desktop TikTok posting.

TikTok's uploader rejects the .webp gallery poster (VideoEditor.generate_poster_thumbnail
in video_editor.py) -- that format was chosen for instant 0.05s gallery load,
never for upload. Until this module, the only workaround was TikTok's own
"pick a frame from the video" step, which the user has been living with even
though the frames it offers are rarely the flattering one.

This grabs a real JPG frame at whatever timestamp the user picks, optionally
stamps the hook's three tiers over it using the SAME HOOK_TEMPLATES the
in-video banner uses, and writes the result into 05_Covers_Thumbnails/ -- the
folder README.md and AGENTS.md have named since before this existed, that
nothing ever wrote to.

Deliberately does NOT reuse SequencePlayer.jsx / drawOneOverlay: those are
built around a time axis (in/loop/out envelopes, stagger); a cover is one
static frame with none of that. Pillow draws it directly from the same
resolved look (resolve_hook_style, AssetRegistry's font paths) so the choice
of font/size/colour/outline per tier is the SAME data the video's banner
uses -- just rendered once instead of animated -- without depending on any of
the motion machinery in scripts/subtitle/.
"""
import os
import time
import uuid
import json
import base64
import hashlib
import subprocess
import urllib.parse
import urllib.request
import io
import warnings
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFilter

from scripts.config import (
    BASE_DIR,
    CAPCUT_DRAFT_DIR,
    COVERS_DIR,
    FONTS_DIR,
    STICKERS_DIR,
    PROJECTS_DIR,
    RAW_DIR,
    asset_relative_path,
)
from scripts.asset_registry import AssetRegistry
from scripts.channel_workflows import get_workflow_scope, get_writable_workflow_scope, require_media_owner
from scripts.channel_artifacts import register as register_companion
from scripts.export_cover_bindings import ExportCoverBindingStore
from scripts.cover_scene import CoverSceneValidationError, normalize_scene
from scripts.hook_styles import resolve_hook_style, TIER_KEYS

def _get_genai_client(api_key: str):
    """Helper to instantiate Google GenAI client (can be patched in tests)."""
    from google import genai
    return genai.Client(api_key=api_key)

# TikTok's own upload cover requirement: 1080x1920, 9:16.
COVER_W, COVER_H = 1080, 1920
# TikTok Profile Grid requirement: 1080x1440, 3:4.
PROFILE_W, PROFILE_H = 1080, 1440
# A cover is read at a glance in a feed thumbnail, not paused mid-video --
# noticeably larger than the in-video banner's 0.065 of frame width.
COVER_BASE_FS_RATIO = 0.09


def _is_contained(path: Path, root: Path) -> bool:
    """
    True if `path` is `root` or lives underneath it. Uses `Path.relative_to`
    rather than a `str.startswith()` prefix check -- a prefix check treats
    `D:\\...\\Capcut_evil\\` as "under" `D:\\...\\Capcut` because the string
    happens to start with the same characters, which is not real path
    containment. Both `path` and `root` are expected to already be resolved.
    """
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_media(raw_path: str) -> Path:
    """Same absolute-or-BASE_DIR-relative rule as stream_media()/build_filmstrip()."""
    target = Path(urllib.parse.unquote(raw_path))
    if not target.is_absolute():
        target = BASE_DIR / target
    target = target.resolve()
    if not (_is_contained(target, BASE_DIR.resolve()) or _is_contained(target, CAPCUT_DRAFT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")
    return target


def grab_frame(video_path: Path, at_seconds: float, out_path: Path) -> Path:
    """
    One JPG frame at `at_seconds`, cropped to cover resolution. Input-seek
    (`-ss` before `-i`) like build_filmstrip() in api_editor.py -- cost is
    independent of clip length, not a full decode pass.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{max(0.0, at_seconds):.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", (
            f"scale={COVER_W}:{COVER_H}:force_original_aspect_ratio=increase,"
            f"crop={COVER_W}:{COVER_H}"
        ),
        "-q:v", "2",
        str(out_path),
    ]
    res = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=20,
    )
    if res.returncode != 0 or not out_path.exists():
        raise HTTPException(
            status_code=500, detail=f"ดึงเฟรมจากวิดีโอไม่สำเร็จ: {(res.stderr or '')[-300:]}",
        )
    return out_path


_font_path_cache: dict = {}


def _font_path_for_family(family: str) -> Optional[str]:
    """AssetRegistry font family -> the .ttf/.otf Pillow needs to open."""
    if not _font_path_cache:
        for f in AssetRegistry.fonts():
            _font_path_cache[f["family"]] = f["path"]
    return _font_path_cache.get(family)


def _ass_hex_to_rgb(value: Optional[str]) -> Tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b). Anything else (None, the "accent" sentinel
    from an unresolved model-tier colour) falls back to white -- a cover has
    no caption colour to inherit, unlike the in-video banner."""
    if not value or not value.startswith("#") or len(value) != 7:
        return (255, 255, 255)
    try:
        v = value.lstrip("#")
        return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except ValueError:
        return (255, 255, 255)


def stamp_hook_tiers(
    image_path: Path,
    brand: str = "", model: str = "", label: str = "",
    template: Optional[str] = None,
) -> Path:
    """
    Draws the same 3-tier stack the in-video banner uses -- brand/model/label,
    each at its template's size/colour/outline -- centred near the top of the
    frame. The static equivalent of drawHookHeader; a cover has no time axis
    to animate, so this is one Pillow pass instead of per-frame canvas work.
    """
    texts = [brand or "", model or "", label or ""]
    if not any(t.strip() for t in texts):
        return image_path

    from PIL import Image, ImageDraw, ImageFont

    resolved = resolve_hook_style(template, None, None)
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    base_fs = round(img.width * COVER_BASE_FS_RATIO)
    font_path = _font_path_for_family(resolved["font"])

    y = round(img.height * 0.09)
    for i, key in enumerate(TIER_KEYS):
        text = texts[i].strip()
        if not text:
            continue
        tier = resolved["tiers"][key]
        if tier.get("upper"):
            text = text.upper()

        size_px = max(10, round(base_fs * tier["size_pct"] / 100))
        font = ImageFont.truetype(font_path, size_px) if font_path else ImageFont.load_default()
        outline_px = round(float(tier.get("outline_px") or 0))
        fill = _ass_hex_to_rgb(tier.get("color"))
        outline_fill = _ass_hex_to_rgb(tier.get("outline_color"))

        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=outline_px)
        x = (img.width - (bbox[2] - bbox[0])) / 2 - bbox[0]
        draw.text(
            (x, y), text, font=font, fill=fill,
            stroke_width=outline_px, stroke_fill=outline_fill,
        )
        y += size_px + round(size_px * 0.25)

    img.save(image_path, format="JPEG", quality=92)
    return image_path


def generate_cover(
    video_rel_path: str,
    at_seconds: float,
    brand: str = "", model: str = "", label: str = "",
    template: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Frame grab + optional tier stamp, written into 05_Covers_Thumbnails/."""
    video_path = _resolve_media(video_rel_path)
    out_path = (output_dir or COVERS_DIR) / f"{video_path.stem}_cover.jpg"
    grab_frame(video_path, at_seconds, out_path)
    stamp_hook_tiers(out_path, brand, model, label, template)
    return out_path


def probe_video_duration(video_path: Path) -> float:
    """Uses ffprobe to obtain duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return max(0.5, float(res.stdout.strip()))
    except Exception:
        pass
    return 10.0


def extract_highlight_candidates(video_path: Path) -> Dict[str, Any]:
    """
    Extracts 4-5 key candidate frames across the video to suggest highlight shots.
    Caches small 270x480 preview images in 05_Covers_Thumbnails/.cache/.
    """
    dur = probe_video_duration(video_path)
    cache_dir = COVERS_DIR / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 5 strategic highlight points
    points = [
        {"ts": 0.5, "label": "ต้นคลิป (Hook ช็อตแรก)"},
        {"ts": round(min(1.8, dur * 0.20), 2), "label": "เปิดตัวสินค้า"},
        {"ts": round(min(3.5, dur * 0.40), 2), "label": "จุดเด่นสินค้า"},
        {"ts": round(min(6.0, dur * 0.65), 2), "label": "การใช้งานจริง"},
        {"ts": round(min(dur - 0.5, dur * 0.85), 2), "label": "ท้ายคลิป / สรุป"},
    ]
    # Filter points to be strictly within duration and unique
    unique_points = []
    seen_ts = set()
    for p in points:
        ts = min(dur - 0.1, max(0.1, p["ts"]))
        ts = round(ts, 1)
        if ts not in seen_ts:
            seen_ts.add(ts)
            unique_points.append({"ts": ts, "label": p["label"]})

    candidates = []
    # Full HD 1080x1920 preview frames with -q:v 2 so preview is razor sharp even when zoomed 1.5x - 2.5x
    frame_w, frame_h = COVER_W, COVER_H
    for idx, pt in enumerate(unique_points):
        ts = pt["ts"]
        cand_name = f"{video_path.stem}_hd_{idx}_{int(ts*10):04d}.jpg"
        cand_path = cache_dir / cand_name
        if not cand_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", f"scale={frame_w}:{frame_h}:force_original_aspect_ratio=increase,crop={frame_w}:{frame_h}",
                "-q:v", "2",
                str(cand_path)
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=15)
            except Exception:
                pass

        if cand_path.exists():
            rel = cand_path.relative_to(BASE_DIR)
            media_url = f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}"
            candidates.append({
                "index": idx,
                "timestamp": ts,
                "label": pt["label"],
                "thumb_url": media_url,
            })

    return {
        "duration": dur,
        "candidates": candidates
    }


def find_raw_sources_for_video(video_path: Path) -> List[Dict[str, Any]]:
    """
    Finds original raw footage clips associated with an export video:
    1. Looks inside 03_Projects/ for matching project.json and reads clip_list
    2. Looks inside 01_Raw/ for footage files
    Allows users to capture 100% clean frames before hardcoded subtitles were burned.
    """
    sources: List[Dict[str, Any]] = []
    seen = set()
    v_stem = video_path.stem.lower()

    # 1. Check projects directory
    if PROJECTS_DIR.exists():
        best_matches = []
        fallback_matches = []
        for p in PROJECTS_DIR.iterdir():
            pj = p / "project.json"
            if p.is_dir() and pj.exists():
                try:
                    data = json.loads(pj.read_text(encoding="utf-8"))
                    p_name = data.get("project_name", p.name).lower()
                    mp4_entry = (data.get("artifacts") or {}).get("mp4_video")
                    mp4_path = mp4_entry.get("path", "") if isinstance(mp4_entry, dict) else ""
                    if (mp4_path and Path(mp4_path).name.lower() == video_path.name.lower()) or v_stem.startswith(p_name) or p_name in v_stem:
                        best_matches.append(data)
                    elif any(len(w) > 4 and w in v_stem for w in p_name.split("_") if w not in ("ปัญหาก่อนใช้", "รีวิวสเปก")):
                        fallback_matches.append(data)
                except Exception:
                    continue

        target_projects = best_matches if best_matches else fallback_matches
        for data in target_projects:
            for clip in data.get("clip_list", []):
                sp = clip.get("source_path")
                if sp and sp not in seen:
                    src_file = Path(sp)
                    if src_file.exists():
                        seen.add(sp)
                        try:
                            rel = src_file.relative_to(BASE_DIR)
                            rel_str = str(rel).replace("\\", "/")
                        except ValueError:
                            rel_str = str(src_file)
                        sources.append({
                            "name": f"{src_file.name} (ต้นฉบับ Raw ไร้ซับ)",
                            "path": rel_str,
                            "source_type": "project_clip",
                        })

    # 2. Check 01_Raw
    if RAW_DIR.exists():
        for ext in ("*.mp4", "*.mov", "*.m4v"):
            for rf in RAW_DIR.rglob(ext):
                sp_str = str(rf)
                if sp_str not in seen:
                    rf_name = rf.name.lower()
                    if any(kw in rf_name for kw in v_stem.split("_") if len(kw) > 3 and kw not in ("ปัญหาก่อนใช้", "รีวิวสเปก", "ready", "post")):
                        seen.add(sp_str)
                        try:
                            rel = rf.relative_to(BASE_DIR)
                            rel_str = str(rel).replace("\\", "/")
                        except ValueError:
                            rel_str = str(rf)
                        sources.append({
                            "name": f"{rf.name} (จาก 01_Raw)",
                            "path": rel_str,
                            "source_type": "raw_dir",
                        })

    return sources


def find_product_ref_images(
    video_path: Optional[str] = None,
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    *, channel_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Finds high-resolution product reference images (scraped from TikTok Shop / web / uploaded)
    for a given product or video export.
    """
    from scripts.product_store import ProductStore
    matched_product = None
    if product_id:
        matched_product = ProductStore.get(product_id, channel_id=channel_id)

    if not matched_product and product_name:
        p_clean = product_name.strip().lower()
        for p in ProductStore.list(channel_id=channel_id):
            p_name = (p.get("name") or "").strip().lower()
            if p_name and (p_name == p_clean or p_clean in p_name or p_name in p_clean):
                matched_product = p
                break

    if not matched_product and video_path:
        v_name = Path(video_path).name.lower()
        v_stem = Path(video_path).stem.lower()
        for p in ProductStore.list(channel_id=channel_id):
            for a in p.get("angles", []):
                v_url = str(a.get("video_url") or "").lower()
                pj_name = str(a.get("project_name") or "").lower()
                sel_v = str(a.get("selected_video") or "").lower()
                if (v_name and (v_name in v_url or v_name in sel_v)) or (pj_name and pj_name in v_stem):
                    matched_product = p
                    break
            if matched_product:
                break

    ref_images = []
    if matched_product:
        images = matched_product.get("images") or []
        for idx, item in enumerate(images):
            if isinstance(item, str):
                ref_images.append({
                    "name": f"รูปสินค้า {idx + 1}",
                    "url": item,
                    "local_path": item if not item.startswith(("http://", "https://")) else None,
                    "source": "url",
                })
            elif isinstance(item, dict):
                url = item.get("url") or item.get("previewUrl") or ""
                path = item.get("path") or item.get("local_path") or item.get("rel_path")
                if not url and path:
                    url = f"/api/media/{path}" if not path.startswith("/") else f"/api/media{path}"
                ref_images.append({
                    "name": item.get("name") or f"รูปสินค้า {idx + 1}",
                    "url": url,
                    "local_path": path,
                    "source": item.get("source") or "tiktok_scraped",
                })
    return ref_images


def get_badges_catalog() -> List[Dict[str, str]]:
    """Returns available 3D Badges in 02_Assets/Stickers_Memes with friendly Thai titles."""
    badge_titles = {
        "plate_banner_yellow_3d.png": "แผ่นป้าย 3D สีเหลืองนีออน",
        "plate_banner_cyan_3d.png": "แผ่นป้าย 3D สีฟ้านีออน",
        "plate_banner_coral_3d.png": "แผ่นป้าย 3D สีส้มคอรัล",
        "frame_tech_callout_3d.png": "กรอบข้อความ 3D Tech HUD",
        "frame_tech_callout_hollow_3d.png": "กรอบโปร่ง 3D Tech HUD",
        "arrow_pointer_yellow_3d.png": "ลูกศรชี้ 3D สีเหลือง",
        "arrow_pointer_cyan_3d.png": "ลูกศรชี้ 3D สีฟ้า",
        "accent_sparkle_star_3d.png": "ดาวประกาย 3D Pop Star",
        "badge_exclamation_alert_3d.png": "ป้ายเตือน 3D ห้ามพลาด Alert",
        "icon_fire_hot_deal_3d.png": "ไอคอนไฟ 3D ดีลร้อนแรง",
    }
    badges = []
    if STICKERS_DIR.exists():
        for f in sorted(STICKERS_DIR.glob("*.png")):
            fname = f.name
            title = badge_titles.get(fname, fname.replace(".png", "").replace("_", " "))
            rel = asset_relative_path(f)
            badges.append({
                "id": fname,
                "title": title,
                "url": f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}",
            })
    return badges


def generate_hook_ideas(
    product_name: str,
    angle_title: str = "",
    script_content: str = ""
) -> List[Dict[str, str]]:
    """
    Generates 4 high-converting cover hooks across 4 key marketing psychological angles:
    1. Curiosity / เตือนภัย
    2. Value / ความคุ้มค่า
    3. Problem / ทางแก้ปัญหาเร่งด่วน
    4. Review / การันตีของดี
    Strictly preserves English brand names and avoids punctuation dots.
    """
    p_clean = product_name.strip() if product_name else "ตัวนี้"

    hooks = [
        {
            "style": "curiosity",
            "category": "อยากรู้ / เตือนภัย",
            "text": f"อย่าเพิ่งซื้อ {p_clean}\nถ้ายังไม่รู้สิ่งนี้!",
        },
        {
            "style": "value",
            "category": "คุ้มค่าการใช้งาน",
            "text": f"ใช้จริงทุกวัน\nดีขนาดนี้จริงดิ?!",
        },
        {
            "style": "problem",
            "category": "แก้ปัญหา / เร่งด่วน",
            "text": f"แก้ปัญหาได้ใน 3 วิ!\nตัวจบที่ตามหา",
        },
        {
            "style": "rating",
            "category": "การันตี / รีวิวเด็ด",
            "text": f"ให้ 10/10 ตัวจบจริง!\nสมคำร่ำลือ",
        },
    ]

    # If angle_title is provided, offer an angle-tailored hook as well
    if angle_title and angle_title.strip():
        at_clean = angle_title.strip()
        hooks.insert(0, {
            "style": "angle",
            "category": "ตรงประเด็นคลิป",
            "text": at_clean if len(at_clean) < 30 else f"{at_clean[:25]}...",
        })

    return hooks


def _clean_cover_text(text: str) -> str:
    """Removes emoji and unsupported glyphs that cause tofu boxes in standard TTF fonts."""
    import re
    if not text:
        return ""
    # Strip emojis and non-BMP symbols
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[\u2600-\u27BF\uE000-\uF8FF]', '', cleaned)
    return cleaned.strip()


def _wrap_thai_text(text: str, max_chars_per_line: int = 16) -> List[str]:
    """Splits or wraps text cleanly for 9:16 cover titles."""
    text = _clean_cover_text(text)
    if not text:
        return []
    if "\n" in text:
        return [_clean_cover_text(l) for l in text.split("\n") if _clean_cover_text(l)]
    if len(text) <= max_chars_per_line:
        return [text]

    try:
        import pythainlp
        words = pythainlp.word_tokenize(text, keep_whitespace=False)
    except Exception:
        words = text.split(" ")

    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) <= max_chars_per_line:
            cur += w
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _cover_scene_requested(scene: Optional[Dict[str, Any]], layers: Optional[List[Dict[str, Any]]], template: Optional[str]) -> bool:
    return scene is not None or layers is not None or (template or "").strip().lower() == "product_front_text_under"


def _normalise_requested_cover_scene(
    *, scene: Optional[Dict[str, Any]], layers: Optional[List[Dict[str, Any]]], aspect_ratio: str,
    template: Optional[str], hook_text: str, sub_text: Optional[str], hook_position: str,
    custom_image_path: Optional[str], video_path: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Build the opt-in scene without changing the legacy render path."""
    if not _cover_scene_requested(scene, layers, template):
        return None
    raw: Dict[str, Any] = dict(scene or {})
    if layers is not None:
        raw["layers"] = layers
    raw.setdefault("aspect_ratio", aspect_ratio)
    if scene is None and layers is None:
        raw.update({
            "hook_text": hook_text, "sub_text": sub_text, "hook_position": hook_position,
            "custom_image_path": custom_image_path, "video_path": video_path,
        })
    return normalize_scene(raw)


def _scene_layer_bounds(layer: Dict[str, Any], width: int, height: int) -> Tuple[int, int, int, int]:
    bounds = layer["bounds"]
    left = round(float(bounds["x"]) * width)
    top = round(float(bounds["y"]) * height)
    right = round((float(bounds["x"]) + float(bounds["width"])) * width)
    bottom = round((float(bounds["y"]) + float(bounds["height"])) * height)
    return left, top, max(left + 1, right), max(top + 1, bottom)


def _scene_colour(layer: Dict[str, Any], theme: Dict[str, Any]) -> Tuple[int, int, int]:
    role = layer.get("color_role") or "neutral"
    value = theme.get(role) or {
        "primary": "#FFE600", "secondary": "#35E6FF", "neutral": "#FFFFFF", "ink": "#111111",
    }.get(role, "#FFFFFF")
    return _ass_hex_to_rgb(value)


def _scene_source_path(layer: Dict[str, Any]) -> Optional[str]:
    source = layer.get("source")
    if isinstance(source, dict):
        value = source.get("asset_path") or source.get("path")
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = layer.get("asset_path")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _fit_scene_image(image: Any, box_w: int, box_h: int, fit: str) -> Any:
    from PIL import Image
    if fit == "stretch":
        return image.resize((box_w, box_h), Image.Resampling.LANCZOS)
    scale = max(box_w / image.width, box_h / image.height) if fit == "cover" else min(box_w / image.width, box_h / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    if fit == "cover":
        x = max(0, (resized.width - box_w) // 2)
        y = max(0, (resized.height - box_h) // 2)
        return resized.crop((x, y, x + box_w, y + box_h))
    return resized


def _render_cover_scene(canvas: Any, scene: Dict[str, Any], font_path: Optional[str]) -> Any:
    """Render canonical layers bottom-to-top onto a detached cover canvas."""
    from PIL import Image, ImageDraw, ImageFont
    work = canvas.convert("RGBA")
    base_snapshot = work.copy()
    width, height = work.size
    theme = scene.get("theme") or {}

    for layer in scene["layers"]:
        if not layer.get("visible", True):
            continue
        layer_type = layer["type"]
        left, top, right, bottom = _scene_layer_bounds(layer, width, height)
        box_w, box_h = right - left, bottom - top
        opacity = max(0.0, min(1.0, float(layer.get("opacity", 1.0))))

        if layer_type in {"product", "image", "product_image", "badge"}:
            source = layer.get("source") if isinstance(layer.get("source"), dict) else {}
            source_path = _scene_source_path(layer)
            if source_path:
                source_img = Image.open(_resolve_media(source_path)).convert("RGBA")
            elif source.get("kind") == "base_frame":
                source_img = base_snapshot.copy()
            else:
                # A product without a source reserves layout only; never
                # duplicate or modify an original image asset implicitly.
                continue
            fitted = _fit_scene_image(source_img, box_w, box_h, str(layer.get("fit") or "contain").lower())
            if opacity < 1.0:
                fitted.putalpha(fitted.getchannel("A").point(lambda value: round(value * opacity)))
            paste_x = left + max(0, (box_w - fitted.width) // 2)
            paste_y = top + max(0, (box_h - fitted.height) // 2)
            work.alpha_composite(fitted, (paste_x, paste_y))
            continue

        overlay = Image.new("RGBA", work.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        colour = _scene_colour(layer, theme)
        alpha = round(opacity * 255)
        if layer_type == "shape":
            draw.rounded_rectangle(
                (left, top, right, bottom), radius=max(0, round(min(box_w, box_h) * 0.12)),
                fill=(*colour, alpha),
            )
        elif layer_type in {"text", "callout"}:
            text = layer.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            role = layer.get("role") or ""
            default_size = 46 if role in {"feature", "proof", "price", "cta"} else 76
            font_size = max(20, min(default_size, round(box_h * 0.72)))
            try:
                font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            max_chars = max(1, round(box_w / max(1, font_size * 0.58)))
            lines = _wrap_thai_text(text, max_chars_per_line=max_chars)
            line_height = max(font_size, round(font_size * 1.12))
            y = top + max(0, (box_h - len(lines) * line_height) // 2)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font, stroke_width=5)
                text_w = bbox[2] - bbox[0]
                x = left + max(0, (box_w - text_w) // 2) - bbox[0]
                draw.text(
                    (x, y - bbox[1]), line, font=font, fill=(*colour, alpha),
                    stroke_width=5, stroke_fill=(0, 0, 0, round(alpha * 0.9)),
                )
                y += line_height
        work.alpha_composite(overlay)
    return work.convert("RGB")


def render_pro_cover(
    video_path_str: Optional[str] = None,
    at_seconds: float = 1.0,
    custom_image_str: Optional[str] = None,
    custom_image_data_str: Optional[str] = None,
    raw_video_path_str: Optional[str] = None,
    pan_y_pct: float = 50.0,
    pan_x_pct: float = 50.0,
    zoom_scale: float = 1.0,
    aspect_ratio: str = "9:16",  # "9:16" | "3:4" | "both"
    enable_hook_text: bool = False,
    enable_badge: bool = False,
    template: str = "neon",
    hook_text: str = "",
    sub_text: Optional[str] = None,
    hook_position: str = "top",
    badge: Optional[str] = None,
    badge_position: str = "top_left",
    export_stem: Optional[str] = None,
    scene: Optional[Dict[str, Any]] = None,
    layers: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
) -> Tuple[Path, Optional[Path]]:
    """
    Renders official TikTok cover JPG(s) (9:16 1080x1920 and/or 3:4 1080x1440):
    - Background from video frame, unburned raw footage, or uploaded photo
    - Vertical & horizontal pan cropping and zoom (1.0x - 3.0x) to avoid burned subtitles
    - Optional high-converting TikTok hook templates (default off for clean frame)
    - Optional 3D badge overlay (default off)
    - Writes into 05_Covers_Thumbnails/{export_stem}_cover.jpg and/or _cover_3x4.jpg
    """
    from PIL import Image, ImageDraw, ImageFont

    cover_root = output_dir or COVERS_DIR
    cover_root.mkdir(parents=True, exist_ok=True)
    temp_dir = cover_root / ".cache"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # export_stem is client-controlled (RenderProCoverRequest.export_filename)
    # and flows straight through to COVERS_DIR / f"{base_clean}_cover.jpg"
    # below. The substring stripping there only removes known suffixes, not
    # path separators -- a value like "../../evil" would still escape
    # COVERS_DIR. Strip to just the filename component here, at the point
    # export_stem is derived, so every use of it below is already safe.
    if export_stem:
        export_stem = Path(export_stem).name or None

    # 1. Obtain base image
    base_img = None
    stem_name = export_stem or "cover"

    if custom_image_data_str:
        if not custom_image_data_str.startswith("data:image/") or "," not in custom_image_data_str:
            raise HTTPException(status_code=400, detail="ภาพจาก Timeline ต้องเป็น data URL ของรูปภาพ")
        try:
            header, encoded = custom_image_data_str.split(",", 1)
            if ";base64" not in header:
                raise ValueError("not base64")
            image_bytes = base64.b64decode(encoded, validate=True)
            if len(image_bytes) > 8 * 1024 * 1024:
                raise ValueError("image too large")
            from PIL import ImageFile
            parser = ImageFile.Parser()
            parser.feed(image_bytes)
            parsed = parser.close()
            base_img = parsed.convert("RGB")
        except Exception as exc:
            raise HTTPException(status_code=400, detail="อ่านภาพจาก Timeline ไม่สำเร็จ") from exc
    elif custom_image_str:
        img_path = _resolve_media(custom_image_str)
        stem_name = export_stem or img_path.stem
        base_img = Image.open(img_path).convert("RGB")
    elif raw_video_path_str:
        rv_path = _resolve_media(raw_video_path_str)
        stem_name = export_stem or rv_path.stem
        raw_frame_path = temp_dir / f"{rv_path.stem}_raw_{int(at_seconds*100):05d}.jpg"
        grab_frame(rv_path, at_seconds, raw_frame_path)
        base_img = Image.open(raw_frame_path).convert("RGB")
    elif video_path_str:
        v_path = _resolve_media(video_path_str)
        stem_name = export_stem or v_path.stem
        raw_frame_path = temp_dir / f"{v_path.stem}_frame_{int(at_seconds*100):05d}.jpg"
        grab_frame(v_path, at_seconds, raw_frame_path)
        base_img = Image.open(raw_frame_path).convert("RGB")
    else:
        # Fallback dark background
        base_img = Image.new("RGB", (COVER_W, COVER_H), (18, 18, 22))

    # 2. Scale & Zoom (1.0x - 3.0x) & Crop with 2D Pan
    orig_w, orig_h = base_img.size
    base_scale = max(COVER_W / orig_w, COVER_H / orig_h)
    clamped_zoom = max(1.0, min(3.0, float(zoom_scale)))
    effective_scale = base_scale * clamped_zoom
    new_w = round(orig_w * effective_scale)
    new_h = round(orig_h * effective_scale)
    scaled_img = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Crop with pan X and pan Y
    extra_x = max(0, new_w - COVER_W)
    extra_y = max(0, new_h - COVER_H)
    clamped_pan_x = max(0.0, min(100.0, float(pan_x_pct)))
    clamped_pan_y = max(0.0, min(100.0, float(pan_y_pct)))
    crop_x = round(extra_x * (clamped_pan_x / 100.0))
    crop_y = round(extra_y * (clamped_pan_y / 100.0))

    canvas = scaled_img.crop((crop_x, crop_y, crop_x + COVER_W, crop_y + COVER_H))
    draw = ImageDraw.Draw(canvas)

    # 3. Load Fonts
    font_path = str(FONTS_DIR / "Kanit-Black.ttf")
    if not Path(font_path).exists():
        font_path = str(FONTS_DIR / "Prompt-Black.ttf")
    if not Path(font_path).exists():
        font_path = None

    main_font_size = 76
    sub_font_size = 46

    try:
        font_main = ImageFont.truetype(font_path, main_font_size) if font_path else ImageFont.load_default()
        font_sub = ImageFont.truetype(font_path, sub_font_size) if font_path else ImageFont.load_default()
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    template_name = (template or "neon").lower()
    scene_model = _normalise_requested_cover_scene(
        scene=scene,
        layers=layers,
        aspect_ratio=aspect_ratio,
        template=template_name,
        hook_text=hook_text,
        sub_text=sub_text,
        hook_position=hook_position,
        custom_image_path=custom_image_str,
        video_path=video_path_str,
    )
    if scene_model is not None:
        canvas = _render_cover_scene(canvas, scene_model, font_path)
        draw = ImageDraw.Draw(canvas)

    # 4. Prepare Lines (if enable_hook_text is True)
    if enable_hook_text and scene_model is None:
        hook_lines = _wrap_thai_text(hook_text, max_chars_per_line=15) if hook_text else []
        sub_clean = _clean_cover_text(sub_text) if sub_text else ""
        sub_lines = [sub_clean] if sub_clean else []
    else:
        hook_lines = []
        sub_lines = []

    # 5. Determine Y Center based on zone
    if hook_position == "center":
        y_anchor = round(COVER_H * 0.48)
    elif hook_position == "bottom":
        y_anchor = round(COVER_H * 0.68)
    else:  # "top" (default)
        y_anchor = round(COVER_H * 0.25)

    line_spacing = 18
    all_lines = hook_lines + sub_lines
    total_height = len(hook_lines) * (main_font_size + line_spacing) + len(sub_lines) * (sub_font_size + line_spacing)
    start_y = max(120, round(y_anchor - total_height / 2.0))

    # 6. Render selected template if text is enabled and present
    tmpl = template_name

    if all_lines and scene_model is None:
        if tmpl == "yellow_bar":
            cur_y = start_y
            for line in hook_lines:
                bbox = draw.textbbox((0, 0), line, font=font_main)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = (COVER_W - tw) // 2
                pad_x, pad_y = 32, 14
                bar_box = [tx - pad_x, cur_y - pad_y, tx + tw + pad_x, cur_y + th + pad_y]
                draw.rounded_rectangle(bar_box, radius=18, fill=(255, 230, 0))
                draw.text((tx - bbox[0], cur_y - bbox[1]), line, font=font_main, fill=(0, 0, 0))
                cur_y += main_font_size + line_spacing + 16

            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = (COVER_W - tw) // 2
                pad_x, pad_y = 24, 10
                bar_box = [tx - pad_x, cur_y - pad_y, tx + tw + pad_x, cur_y + th + pad_y]
                draw.rounded_rectangle(bar_box, radius=14, fill=(20, 20, 20))
                draw.text((tx - bbox[0], cur_y - bbox[1]), sline, font=font_sub, fill=(255, 255, 255))
                cur_y += sub_font_size + line_spacing

        elif tmpl == "modern_box":
            cur_y = start_y
            max_w = 0
            for line in hook_lines:
                bbox = draw.textbbox((0, 0), line, font=font_main)
                max_w = max(max_w, bbox[2] - bbox[0])
            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub)
                max_w = max(max_w, bbox[2] - bbox[0])

            box_w = min(COVER_W - 80, max_w + 80)
            box_h = total_height + 40
            box_x = (COVER_W - box_w) // 2
            box_y = start_y - 20

            box_overlay = Image.new("RGBA", (box_w, box_h), (15, 23, 42, 220))
            box_draw = ImageDraw.Draw(box_overlay)
            box_draw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=24, outline=(37, 244, 238, 255), width=3)
            canvas.paste(box_overlay, (box_x, box_y), box_overlay)

            cur_y = start_y
            for line in hook_lines:
                bbox = draw.textbbox((0, 0), line, font=font_main)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), line, font=font_main,
                    fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0)
                )
                cur_y += main_font_size + line_spacing

            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), sline, font=font_sub,
                    fill=(255, 230, 0), stroke_width=3, stroke_fill=(0, 0, 0)
                )
                cur_y += sub_font_size + line_spacing

        elif tmpl == "minimal_bold":
            cur_y = start_y
            for line in hook_lines:
                bbox = draw.textbbox((0, 0), line, font=font_main, stroke_width=16)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), line, font=font_main,
                    fill=(255, 255, 255), stroke_width=16, stroke_fill=(0, 0, 0)
                )
                cur_y += main_font_size + line_spacing

            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub, stroke_width=10)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), sline, font=font_sub,
                    fill=(255, 230, 0), stroke_width=10, stroke_fill=(0, 0, 0)
                )
                cur_y += sub_font_size + line_spacing

        elif tmpl in ("tech_neon", "tech_reviewer"):
            cur_y = start_y
            for idx, line in enumerate(hook_lines):
                bbox = draw.textbbox((0, 0), line, font=font_main, stroke_width=18)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0] + 6, cur_y - bbox[1] + 8), line, font=font_main,
                    fill=(0, 0, 0), stroke_width=18, stroke_fill=(0, 0, 0)
                )
                color = (255, 255, 255) if idx == 0 else (57, 255, 20)
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), line, font=font_main,
                    fill=color, stroke_width=16, stroke_fill=(0, 0, 0)
                )
                cur_y += main_font_size + line_spacing + 6

            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = (COVER_W - tw) // 2
                pad_x, pad_y = 28, 8
                pill_box = [tx - pad_x, cur_y - pad_y, tx + tw + pad_x, cur_y + th + pad_y]
                draw.rounded_rectangle(pill_box, radius=16, fill=(10, 15, 22), outline=(57, 255, 20), width=2)
                draw.text((tx - bbox[0], cur_y - bbox[1]), sline, font=font_sub, fill=(255, 255, 255))
                cur_y += sub_font_size + line_spacing + 8

        else:
            # Default: "neon"
            cur_y = start_y
            for line in hook_lines:
                bbox = draw.textbbox((0, 0), line, font=font_main, stroke_width=14)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2

                draw.text(
                    (tx - bbox[0] + 6, cur_y - bbox[1] + 8), line, font=font_main,
                    fill=(0, 0, 0), stroke_width=14, stroke_fill=(0, 0, 0)
                )
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), line, font=font_main,
                    fill=(255, 230, 0), stroke_width=14, stroke_fill=(0, 0, 0)
                )
                cur_y += main_font_size + line_spacing

            for sline in sub_lines:
                bbox = draw.textbbox((0, 0), sline, font=font_sub, stroke_width=10)
                tw = bbox[2] - bbox[0]
                tx = (COVER_W - tw) // 2
                draw.text(
                    (tx - bbox[0], cur_y - bbox[1]), sline, font=font_sub,
                    fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0)
                )
                cur_y += sub_font_size + line_spacing

    # 7. Stamp 3D Badge (if selected and enable_badge is True)
    if enable_badge and badge and badge != "none" and badge_position != "none":
        # badge is client-controlled (RenderProCoverRequest.badge) and was
        # joined straight into STICKERS_DIR / badge -- a value like
        # "../../evil.png" would escape STICKERS_DIR. Strip to just the
        # filename component and verify the resolved path still lives
        # inside STICKERS_DIR before ever treating it as a real path (same
        # pattern as the sticker_badge handling in api_render.py).
        badge_name = Path(badge).name
        badge_path = STICKERS_DIR / badge_name
        try:
            badge_path.resolve().relative_to(STICKERS_DIR.resolve())
        except ValueError:
            badge_path = STICKERS_DIR / "__unsafe_badge_path__"
        if not badge_path.exists():
            for bf in STICKERS_DIR.glob("*.png"):
                if badge.lower() in bf.name.lower():
                    badge_path = bf
                    break

        if badge_path.exists():
            try:
                badge_img = Image.open(badge_path).convert("RGBA")
                target_bw = 240
                target_bh = round(badge_img.height * (target_bw / badge_img.width))
                badge_resized = badge_img.resize((target_bw, target_bh), Image.Resampling.LANCZOS)

                if badge_position == "top_right":
                    bx = COVER_W - target_bw - 50
                    by = 130
                else:  # "top_left" (default)
                    bx = 50
                    by = 130

                canvas.paste(badge_resized, (bx, by), badge_resized)
            except Exception:
                pass

    # 8. Save Cover Images (9:16 and/or 3:4)
    base_clean = stem_name.replace("_cover_3x4.jpg", "").replace("_cover.jpg", "").replace("_cover", "").replace(".jpg", "")
    out_path_9x16 = cover_root / f"{base_clean}_cover.jpg"
    out_path_3x4 = cover_root / f"{base_clean}_cover_3x4.jpg"

    # Compute 3:4 profile grid crop (1080 x 1440)
    # Pan moves crop window vertically: 0 is top (cuts bottom 480px subtitles), 100 is bottom
    crop_3x4_y = round((COVER_H - PROFILE_H) * (clamped_pan_y / 100.0))
    canvas_3x4 = canvas.crop((0, crop_3x4_y, PROFILE_W, crop_3x4_y + PROFILE_H))

    if aspect_ratio == "3:4":
        canvas_3x4.save(out_path_3x4, format="JPEG", quality=95)
        return out_path_3x4, None
    elif aspect_ratio == "both":
        canvas.save(out_path_9x16, format="JPEG", quality=95)
        canvas_3x4.save(out_path_3x4, format="JPEG", quality=95)
        return out_path_9x16, out_path_3x4
    else:  # default "9:16"
        canvas.save(out_path_9x16, format="JPEG", quality=95)
        return out_path_9x16, None


# ---------------- API Router & Endpoints ----------------

router = APIRouter(prefix="/api/covers", tags=["covers"])


class GenerateCoverRequest(BaseModel):
    video_path: str
    at_seconds: float = 1.0
    brand: str = ""
    model: str = ""
    label: str = ""
    template: Optional[str] = None


class HighlightsRequest(BaseModel):
    video_path: str


class RawSourcesRequest(BaseModel):
    video_path: str


class ProductRefImagesRequest(BaseModel):
    video_path: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None


class GenerateHooksRequest(BaseModel):
    product_name: str
    angle_title: Optional[str] = ""
    script_content: Optional[str] = ""


class RenderProCoverRequest(BaseModel):
    video_path: Optional[str] = None
    export_id: Optional[str] = None
    at_seconds: float = 1.0
    custom_image_path: Optional[str] = None
    custom_image_data: Optional[str] = None
    raw_video_path: Optional[str] = None
    pan_y_pct: float = 50.0
    pan_x_pct: float = 50.0
    zoom_scale: float = 1.0
    aspect_ratio: str = "9:16"  # "9:16" | "3:4" | "both"
    enable_hook_text: bool = False
    enable_badge: bool = False
    template: str = "neon"  # "neon" | "yellow_bar" | "modern_box" | "minimal_bold"
    hook_text: str = ""
    sub_text: Optional[str] = ""
    hook_position: str = "top"  # "top" | "center" | "bottom"
    badge: Optional[str] = None
    badge_position: str = "top_left"  # "top_left" | "top_right" | "none"
    export_filename: Optional[str] = None
    scene: Optional[Dict[str, Any]] = None
    layers: Optional[List[Dict[str, Any]]] = None


@router.get("/badges")
def get_badges_endpoint():
    """Lists available 3D badges in 02_Assets/Stickers_Memes."""
    return {"badges": get_badges_catalog()}


@router.post("/highlights")
def get_highlights_endpoint(req: HighlightsRequest, channel_scope=Depends(get_workflow_scope)):
    """Extracts candidate highlight frames across the video for quick selection."""
    v_path = _resolve_media(req.video_path)
    require_media_owner(channel_scope, v_path, base_dir=BASE_DIR)
    res = extract_highlight_candidates(v_path)
    return res


@router.post("/raw-sources")
def get_raw_sources_endpoint(req: RawSourcesRequest, channel_scope=Depends(get_workflow_scope)):
    """Lists available unburned raw footage clips for clean frame capture."""
    v_path = _resolve_media(req.video_path)
    require_media_owner(channel_scope, v_path, base_dir=BASE_DIR)
    sources = find_raw_sources_for_video(v_path)
    return {"raw_sources": sources}


@router.post("/product-ref-images")
def get_product_ref_images_endpoint(req: ProductRefImagesRequest, channel_scope=Depends(get_workflow_scope)):
    """Lists high-res product reference images scraped from TikTok Shop / catalog."""
    if req.video_path:
        require_media_owner(channel_scope, req.video_path, base_dir=BASE_DIR)
    if req.product_id:
        from scripts.product_store import ProductStore
        from scripts.channel_workflows import require_record_owner
        require_record_owner(channel_scope, ProductStore.get(req.product_id, channel_id=channel_scope.channel_id))
    images = find_product_ref_images(
        video_path=req.video_path,
        product_id=req.product_id,
        product_name=req.product_name,
        channel_id=channel_scope.channel_id,
    )
    return {"ref_images": images}


@router.post("/generate-hooks")
def generate_hooks_endpoint(req: GenerateHooksRequest):
    """Generates high CTR TikTok cover hooks tailored for Thai e-commerce."""
    hooks = generate_hook_ideas(
        req.product_name,
        req.angle_title or "",
        req.script_content or ""
    )
    return {"hooks": hooks}


@router.post("/render-pro")
def render_pro_cover_endpoint(req: RenderProCoverRequest, channel_scope=Depends(get_writable_workflow_scope)):
    """Renders high-converting cover images (9:16, 3:4, or both) with chosen template, position, and badge."""
    binding_store = ExportCoverBindingStore(BASE_DIR) if req.export_id else None
    binding_revision = None
    if binding_store:
        binding_store.validate_export(channel_scope.channel_id, req.export_id, req.video_path)
        binding_revision = binding_store.revision(channel_scope.channel_id, req.export_id)
    for source in (req.video_path, req.custom_image_path, req.raw_video_path):
        if source:
            require_media_owner(channel_scope, source, base_dir=BASE_DIR)
    # Unique companion revisions prevent an old cover from being overwritten
    # by another job using the same video basename.
    cover_root = COVERS_DIR / channel_scope.channel_id / uuid.uuid4().hex
    try:
        scene_model = _normalise_requested_cover_scene(
            scene=req.scene,
            layers=req.layers,
            aspect_ratio=req.aspect_ratio,
            template=req.template,
            hook_text=req.hook_text,
            sub_text=req.sub_text,
            hook_position=req.hook_position,
            custom_image_path=req.custom_image_path,
            video_path=req.video_path,
        )
    except CoverSceneValidationError as exc:
        raise HTTPException(status_code=422, detail={"scene_errors": list(exc.errors)}) from exc

    for layer in (scene_model or {}).get("layers", []):
        source = _scene_source_path(layer)
        if source:
            require_media_owner(channel_scope, source, base_dir=BASE_DIR)

    primary_path, path_3x4 = render_pro_cover(
        video_path_str=req.video_path, at_seconds=req.at_seconds,
        custom_image_str=req.custom_image_path, custom_image_data_str=req.custom_image_data,
        raw_video_path_str=req.raw_video_path,
        pan_y_pct=req.pan_y_pct, pan_x_pct=req.pan_x_pct, zoom_scale=req.zoom_scale,
        aspect_ratio=req.aspect_ratio, enable_hook_text=req.enable_hook_text,
        enable_badge=req.enable_badge, template=req.template, hook_text=req.hook_text,
        sub_text=req.sub_text, hook_position=req.hook_position, badge=req.badge,
        badge_position=req.badge_position, export_stem=req.export_filename,
        scene=scene_model, layers=None,
        output_dir=cover_root,
    )
    rel = primary_path.relative_to(BASE_DIR)
    register_companion(rel, channel_scope.channel_id)
    media_url = f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}?channel={channel_scope.channel_id}"
    res = {
        "success": True,
        "cover_path": str(rel).replace("\\", "/"),
        "media_url": media_url,
    }
    if path_3x4 and path_3x4.exists():
        rel_3x4 = path_3x4.relative_to(BASE_DIR)
        register_companion(rel_3x4, channel_scope.channel_id)
        res["cover_3x4_path"] = str(rel_3x4).replace("\\", "/")
        res["media_url_3x4"] = f"/api/media/{urllib.parse.quote(str(rel_3x4).replace(chr(92), '/'))}?channel={channel_scope.channel_id}"
    if scene_model is not None:
        res["scene"] = scene_model
    if binding_store:
        selections = {"3:4" if req.aspect_ratio == "3:4" else "9:16": res["cover_path"]}
        if res.get("cover_3x4_path"):
            selections["3:4"] = res["cover_3x4_path"]
        saved = binding_store.save(channel_scope.channel_id, req.export_id, req.video_path,
                                   selections, expected_revision=binding_revision)
        res.update(export_id=req.export_id, cover_binding_revision=saved["revision"])
    return res


@router.post("/generate")
def generate_cover_endpoint(req: GenerateCoverRequest, channel_scope=Depends(get_writable_workflow_scope)):
    require_media_owner(channel_scope, req.video_path, base_dir=BASE_DIR)
    out_path = generate_cover(
        req.video_path, req.at_seconds, req.brand, req.model, req.label, req.template,
        output_dir=COVERS_DIR / channel_scope.channel_id / uuid.uuid4().hex,
    )
    rel = out_path.relative_to(BASE_DIR)
    register_companion(rel, channel_scope.channel_id)
    return {
        "success": True,
        "cover_path": str(rel),
        "media_url": f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}?channel={channel_scope.channel_id}",
    }


class GrabFrameRequest(BaseModel):
    video_path: str
    at_seconds: float = 0.0


@router.post("/grab-frame")
def grab_frame_endpoint(req: GrabFrameRequest, channel_scope=Depends(get_writable_workflow_scope)):
    """
    Grabs a single high-quality JPG frame from video at the specified timestamp in seconds.
    Cached on disk for instant re-scrubbing.
    """
    if not req.video_path:
        raise HTTPException(status_code=400, detail="video_path is required")
    v_path = _resolve_media(req.video_path)
    require_media_owner(channel_scope, v_path, base_dir=BASE_DIR)
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    sec_str = f"{round(req.at_seconds, 2):.2f}".replace(".", "_")
    vid_stem = v_path.stem[:24]
    cache_name = f"frame_{vid_stem}_{sec_str}.jpg"
    source_hash = hashlib.sha256(str(v_path).encode()).hexdigest()[:16]
    out_file = COVERS_DIR / channel_scope.channel_id / f"{source_hash}_{cache_name}"

    if not out_file.exists():
        grab_frame(v_path, max(0.0, req.at_seconds), out_file)

    if not out_file.exists():
        raise HTTPException(status_code=500, detail="Failed to grab frame from video")

    rel = out_file.relative_to(BASE_DIR)
    register_companion(rel, channel_scope.channel_id)
    media_url = f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}?channel={channel_scope.channel_id}"
    return {
        "success": True,
        "frame_path": str(out_file),
        "media_url": media_url,
        "seconds": req.at_seconds,
    }


class AiGenerateCoverImageRequest(BaseModel):
    product_name: str = "สินค้า"
    hook_title: Optional[str] = ""
    style_prompt: Optional[str] = ""
    video_path: Optional[str] = None
    at_seconds: Optional[float] = None
    source_image_path: Optional[str] = None


def _clean_backdrop_prompt(raw_prompt: Optional[str]) -> str:
    """Sanitize prompt to generate an empty luxury commercial product stage or handheld hero shot."""
    if not raw_prompt:
        raw_prompt = ""
    is_handheld = any(kw in raw_prompt.lower() for kw in ["hand holding", "holding", "มือถือสินค้า", "handheld"])
    clean = "".join(ch for ch in raw_prompt if ord(ch) < 128)
    if is_handheld:
        for bad in ["portrait", "woman", "girl", "face", "model face"]:
            clean = clean.replace(bad, "")
        clean = " ".join(clean.split())
        return f"{clean}, professional product demonstration, sharp focus on product, high contrast rim lighting, 9:16 vertical ratio"

    for bad in ["product photography of", "commercial photography of", "portrait", "woman", "girl", "person", "human", "face"]:
        clean = clean.replace(bad, "")
    clean = " ".join(clean.split())
    if len(clean) < 10:
        clean = "Luxury commercial product display podium on dark marble floor, dramatic soft studio rim lighting, clean modern aesthetic"
    return (
        f"{clean}, empty product showcase stage, minimalist pedestal, high-end commercial studio lighting, "
        f"completely empty center for product placement, no people, no humans, no woman, no girl, no man, "
        f"no face, no model, 9:16 vertical ratio"
    )


def _get_genai_client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def _generate_cover_via_antigravity_cli(
    prompt_text: str, prod_name: str, ts: int, uid: str, ref_image_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Directly execute Antigravity CLI's built-in generate_image tool.
    Produces astonishing 8K commercial product hero covers without third-party API costs.
    """
    try:
        if os.environ.get("DISABLE_ANTIGRAVITY", "").lower() in ("1", "true", "yes"):
            return None
        from scripts.ai_bridge import get_agy_path
        agy_exe = get_agy_path()
        if not agy_exe or not agy_exe.exists():
            return None

        cli_brain = Path.home() / ".gemini" / "antigravity-cli" / "brain"
        t_before = time.time() - 2.0
        prod_label = prod_name or "สินค้าพรีเมียม"
        ref_clause = ""
        if ref_image_path and ref_image_path.exists():
            ref_path_str = str(ref_image_path.resolve()).replace("\\", "/")
            ref_clause = f" ImagePaths=['{ref_path_str}']"

        cmd_prompt = (
            f"Use generate_image tool with AspectRatio 9:16 named cover_{uid}{ref_clause}: "
            f"High-end commercial hero product shot of {prod_label}, cinematic studio lighting, 8k resolution, 9:16 vertical ratio: {prompt_text}"
        )
        cmd = [
            str(agy_exe),
            "-p",
            cmd_prompt,
            "--model",
            "gemini-3.8-flash-high",
            "--dangerously-skip-permissions",
            "--output-format",
            "text",
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        if proc.returncode == 0 and cli_brain.exists():
            candidates = []
            for p in cli_brain.glob("**/*.jpg"):
                try:
                    m = p.stat().st_mtime
                    if m >= t_before:
                        candidates.append((m, p))
                except OSError:
                    pass
            candidates.sort(key=lambda x: x[0], reverse=True)
            if candidates:
                src_f = candidates[0][1]
                out_f = COVERS_DIR / f"ai_cover_{ts}_{uid}.jpg"
                out_f.write_bytes(src_f.read_bytes())
                return out_f
    except Exception as agy_ex:
        print(f"[CoverStudioAI] Antigravity CLI note: {agy_ex}")
    return None


@router.post("/ai-generate-image")
def ai_generate_cover_image_endpoint(req: AiGenerateCoverImageRequest, channel_scope=Depends(get_writable_workflow_scope)):
    """
    Generates a 9:16 vertical commercial cover image.
    Priority 1: Antigravity Pro CLI in-machine Image Generator (Ultra 8K)
    Priority 2: Google GenAI Imagen 3 (Enterprise mode)
    Priority 3: Free AI Image Generator (Pollinations / Flux) with strict negative prompt
    Priority 4: Offline 3D Studio Podium Backdrop
    """
    for source in (req.video_path, req.source_image_path):
        if source and not source.startswith(("http://", "https://")):
            require_media_owner(channel_scope, source, base_dir=BASE_DIR)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    safe_uid = uuid.uuid4().hex[:6]
    product_name = (req.product_name or "สินค้า").strip()
    full_prompt = _clean_backdrop_prompt(req.style_prompt)

    # Download or resolve reference image if provided (from TikTok Shop / Catalog)
    cached_ref_path = None
    if req.source_image_path:
        src = req.source_image_path.strip()
        if src.startswith(("http://", "https://")):
            try:
                cached_ref_path = COVERS_DIR / f"ref_cache_{safe_uid}.jpg"
                req_obj = urllib.request.Request(
                    src,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req_obj, timeout=12) as resp:
                    cached_ref_path.write_bytes(resp.read())
            except Exception as dl_err:
                print(f"[CoverStudioAI] Download ref image error: {dl_err}")
                cached_ref_path = None
        else:
            try:
                cached_ref_path = _resolve_media(src)
            except Exception:
                p = Path(src)
                if p.exists():
                    cached_ref_path = p

    generated_file = None
    method_used = "studio_auto"

    # 1. Primary: In-machine Antigravity Pro CLI Image Generator
    try:
        agy_out = _generate_cover_via_antigravity_cli(
            full_prompt, product_name, ts, safe_uid, ref_image_path=cached_ref_path
        )
        if agy_out and agy_out.exists():
            generated_file = agy_out
            method_used = "antigravity_pro"
    except Exception as agy_err:
        print(f"[CoverStudioAI] Antigravity generator error: {agy_err}")

    # 2. Secondary: Try Google GenAI Imagen 3 if configured
    if not generated_file:
        try:
            from scripts.ai_bridge import AIBridge
            api_keys = AIBridge.get_api_keys()
        except Exception:
            api_keys = []
        if not api_keys:
            fallback_k = os.environ.get("GEMINI_API_KEY", "").strip()
            if fallback_k:
                api_keys = [fallback_k]

        if api_keys:
            try:
                from google import genai
                from google.genai import types

                for key in api_keys:
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            client = _get_genai_client(key)
                            resp = client.models.generate_images(
                                model="imagen-3.0-generate-002",
                                prompt=full_prompt,
                                config=types.GenerateImagesConfig(
                                    number_of_images=1,
                                    aspect_ratio="9:16",
                                    output_mime_type="image/jpeg",
                                ),
                            )
                            if resp and resp.generated_images:
                                img_bytes = resp.generated_images[0].image.image_bytes
                                out_path = COVERS_DIR / f"ai_cover_{ts}_{safe_uid}.jpg"
                                out_path.write_bytes(img_bytes)
                                generated_file = out_path
                                method_used = "imagen_3"
                                break
                    except Exception:
                        continue
            except Exception:
                pass

    # 3. Tertiary: Free AI Image Generator (Pollinations / Flux)
    if not generated_file:
        try:
            encoded_p = urllib.parse.quote(full_prompt)
            is_handheld_prompt = any(kw in (req.style_prompt or "").lower() for kw in ["hand holding", "holding", "มือถือสินค้า", "handheld"])
            if is_handheld_prompt:
                neg_str = "face,eyes,head,portrait,anime,character,distorted,bad anatomy,extra fingers,blurry,deformed"
            else:
                neg_str = "person,people,human,woman,girl,model,face,man,character,clothing,portrait,anime,eyes"
            negative = urllib.parse.quote(neg_str)
            gen_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width=1080&height=1920&nologo=true&seed={safe_uid}&negative={negative}"
            req_ai = urllib.request.Request(gen_url, headers={"User-Agent": "OmniCutProStudio/1.0"})
            with urllib.request.urlopen(req_ai, timeout=12) as ai_resp:
                if ai_resp.status == 200:
                    ai_bytes = ai_resp.read()
                    if len(ai_bytes) > 5000:
                        out_path = COVERS_DIR / f"ai_cover_{ts}_{safe_uid}.jpg"
                        ai_img = Image.open(io.BytesIO(ai_bytes)).convert("RGB")
                        if ai_img.size != (COVER_W, COVER_H):
                            ai_img = ai_img.resize((COVER_W, COVER_H), Image.Resampling.LANCZOS)
                        ai_img.save(out_path, format="JPEG", quality=95)
                        generated_file = out_path
                        method_used = "ai_free"
        except Exception as free_err:
            print(f"[CoverStudioAI] Free AI Generator note: {free_err}")

    # 4. Quaternary: Elegant Offline 3D Studio Podium Backdrop
    if not generated_file:
        out_path = COVERS_DIR / f"studio_cover_{ts}_{safe_uid}.jpg"
        backdrop = Image.new("RGBA", (COVER_W, COVER_H), (14, 18, 28, 255))
        b_draw = ImageDraw.Draw(backdrop)
        for y in range(COVER_H):
            ratio = y / float(COVER_H)
            r = int(14 + ratio * 20)
            g = int(18 + ratio * 28)
            b = int(28 + ratio * 48)
            b_draw.line([(0, y), (COVER_W, y)], fill=(r, g, b, 255))

        spot = Image.new("RGBA", (COVER_W, COVER_H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(spot)
        s_draw.ellipse([180, 480, 900, 1380], fill=(60, 130, 245, 80))
        spot = spot.filter(ImageFilter.GaussianBlur(140))
        backdrop.alpha_composite(spot)

        podium = Image.new("RGBA", (COVER_W, COVER_H), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(podium)
        p_draw.ellipse([240, 1240, 840, 1420], fill=(24, 32, 48, 240), outline=(60, 140, 255, 160), width=2)
        p_draw.rectangle([240, 1330, 840, 1450], fill=(18, 24, 36, 250))
        p_draw.ellipse([240, 1360, 840, 1540], fill=(14, 18, 28, 255))
        backdrop.alpha_composite(podium)

        backdrop.convert("RGB").save(out_path, format="JPEG", quality=95)
        generated_file = out_path
        method_used = "studio_auto"

    scoped_copy = COVERS_DIR / channel_scope.channel_id / f"{safe_uid}_{generated_file.name}"
    scoped_copy.parent.mkdir(parents=True, exist_ok=True)
    generated_file.replace(scoped_copy)
    generated_file = scoped_copy
    register_companion(generated_file.relative_to(BASE_DIR), channel_scope.channel_id)
    try:
        rel = generated_file.relative_to(BASE_DIR)
        rel_str = str(rel).replace("\\", "/")
        media_url = f"/api/media/{urllib.parse.quote(rel_str)}?channel={channel_scope.channel_id}"
    except ValueError:
        rel_str = str(generated_file).replace("\\", "/")
        media_url = f"/api/media/{urllib.parse.quote(rel_str)}"

    return {
        "success": True,
        "image_path": str(generated_file),
        "rel_path": rel_str,
        "media_url": media_url,
        "method": method_used,
        "prompt_used": full_prompt,
        "message": (
            "สร้างรูปหน้าปกสินค้า 8K ด้วย Antigravity สำเร็จแล้ว!"
            if "antigravity_pro" in method_used
            else "สร้างรูปหน้าปกสินค้าด้วย AI Studio สำเร็จแล้ว!"
            if "ai_free" in method_used
            else "สร้างภาพพื้นหลังสตูดิโอ 9:16 เรียบร้อยแล้ว!"
        ),
    }


