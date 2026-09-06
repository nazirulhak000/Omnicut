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
import subprocess
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.config import BASE_DIR, CAPCUT_DRAFT_DIR
from scripts.asset_registry import AssetRegistry
from scripts.hook_styles import resolve_hook_style, TIER_KEYS

COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"
# TikTok's own upload cover requirement: 1080x1920, 9:16.
COVER_W, COVER_H = 1080, 1920
# A cover is read at a glance in a feed thumbnail, not paused mid-video --
# noticeably larger than the in-video banner's 0.065 of frame width.
COVER_BASE_FS_RATIO = 0.09


def _resolve_media(raw_path: str) -> Path:
    """Same absolute-or-BASE_DIR-relative rule as stream_media()/build_filmstrip()."""
    target = Path(urllib.parse.unquote(raw_path))
    if not target.is_absolute():
        target = BASE_DIR / target
    target = target.resolve()
    if not (str(target).startswith(str(BASE_DIR)) or str(target).startswith(str(CAPCUT_DRAFT_DIR))):
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


router = APIRouter(prefix="/api/covers", tags=["covers"])


class GenerateCoverRequest(BaseModel):
    video_path: str
    at_seconds: float = 1.0
    brand: str = ""
    model: str = ""
    label: str = ""
    template: Optional[str] = None


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
