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
import json
import subprocess
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.config import (
    BASE_DIR,
    CAPCUT_DRAFT_DIR,
    COVERS_DIR,
    FONTS_DIR,
    STICKERS_DIR,
    PROJECTS_DIR,
    RAW_DIR,
)
from scripts.asset_registry import AssetRegistry
from scripts.hook_styles import resolve_hook_style, TIER_KEYS

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
) -> Path:
    """Frame grab + optional tier stamp, written into 05_Covers_Thumbnails/."""
    video_path = _resolve_media(video_rel_path)
    out_path = COVERS_DIR / f"{video_path.stem}_cover.jpg"
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
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
                    mp4_path = data.get("artifacts", {}).get("mp4_video", {}).get("path", "")
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
            rel = f.relative_to(BASE_DIR)
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
            "category": "คุ้มราคา / โปรเด็ด",
            "text": f"ราคาหลักร้อย\nได้ขนาดนี้จริงดิ?!",
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


def render_pro_cover(
    video_path_str: Optional[str] = None,
    at_seconds: float = 1.0,
    custom_image_str: Optional[str] = None,
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

    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = COVERS_DIR / ".cache"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Obtain base image
    base_img = None
    stem_name = export_stem or "cover"

    if custom_image_str:
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

    # 4. Prepare Lines (if enable_hook_text is True)
    if enable_hook_text:
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
    tmpl = (template or "neon").lower()

    if all_lines:
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
        badge_path = STICKERS_DIR / badge
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
    out_path_9x16 = COVERS_DIR / f"{base_clean}_cover.jpg"
    out_path_3x4 = COVERS_DIR / f"{base_clean}_cover_3x4.jpg"

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


class GenerateHooksRequest(BaseModel):
    product_name: str
    angle_title: Optional[str] = ""
    script_content: Optional[str] = ""


class RenderProCoverRequest(BaseModel):
    video_path: Optional[str] = None
    at_seconds: float = 1.0
    custom_image_path: Optional[str] = None
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


@router.get("/badges")
def get_badges_endpoint():
    """Lists available 3D badges in 02_Assets/Stickers_Memes."""
    return {"badges": get_badges_catalog()}


@router.post("/highlights")
def get_highlights_endpoint(req: HighlightsRequest):
    """Extracts candidate highlight frames across the video for quick selection."""
    v_path = _resolve_media(req.video_path)
    res = extract_highlight_candidates(v_path)
    return res


@router.post("/raw-sources")
def get_raw_sources_endpoint(req: RawSourcesRequest):
    """Lists available unburned raw footage clips for clean frame capture."""
    v_path = _resolve_media(req.video_path)
    sources = find_raw_sources_for_video(v_path)
    return {"raw_sources": sources}


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
def render_pro_cover_endpoint(req: RenderProCoverRequest):
    """Renders high-converting cover images (9:16, 3:4, or both) with chosen template, position, and badge."""
    primary_path, path_3x4 = render_pro_cover(
        video_path_str=req.video_path,
        at_seconds=req.at_seconds,
        custom_image_str=req.custom_image_path,
        raw_video_path_str=req.raw_video_path,
        pan_y_pct=req.pan_y_pct,
        pan_x_pct=req.pan_x_pct,
        zoom_scale=req.zoom_scale,
        aspect_ratio=req.aspect_ratio,
        enable_hook_text=req.enable_hook_text,
        enable_badge=req.enable_badge,
        template=req.template,
        hook_text=req.hook_text,
        sub_text=req.sub_text,
        hook_position=req.hook_position,
        badge=req.badge,
        badge_position=req.badge_position,
        export_stem=req.export_filename,
    )
    rel = primary_path.relative_to(BASE_DIR)
    media_url = f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}"
    res = {
        "success": True,
        "cover_path": str(rel).replace("\\", "/"),
        "media_url": media_url,
    }
    if path_3x4 and path_3x4.exists():
        rel_3x4 = path_3x4.relative_to(BASE_DIR)
        res["cover_3x4_path"] = str(rel_3x4).replace("\\", "/")
        res["media_url_3x4"] = f"/api/media/{urllib.parse.quote(str(rel_3x4).replace(chr(92), '/'))}"
    return res


@router.post("/generate")
def generate_cover_endpoint(req: GenerateCoverRequest):
    out_path = generate_cover(
        req.video_path, req.at_seconds, req.brand, req.model, req.label, req.template,
    )
    rel = out_path.relative_to(BASE_DIR)
    return {
        "success": True,
        "cover_path": str(rel),
        "media_url": f"/api/media/{urllib.parse.quote(str(rel).replace(chr(92), '/'))}",
    }

