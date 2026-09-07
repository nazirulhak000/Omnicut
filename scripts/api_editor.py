"""
Manual Editor API router -- endpoints the CapCut-style editor needs that the
render pipeline itself does not.

Kept in its own router (mounted with one include_router line) so editor work
never has to edit the busy api_server.py surface.
"""

import sys
import time
import hashlib
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import BASE_DIR, CAPCUT_DRAFT_DIR
from scripts.video_editor import VideoEditor
from scripts.api_schemas import OverlayLayoutRequest

router = APIRouter(prefix="/api/editor", tags=["editor"])

# Filmstrips are derived, disposable art -- they live beside the other
# generated cover/thumbnail output rather than in 02_Assets (which is the
# hand-curated library AssetRegistry scans).
FILMSTRIP_DIR = BASE_DIR / "05_Covers_Thumbnails" / ".filmstrips"

FRAME_WIDTH = 160       # per tile; height follows the source aspect
MIN_FRAMES = 2
MAX_FRAMES = 40         # a 40-tile strip is already ~6400px wide


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
    """Same absolute-or-BASE_DIR-relative rule (and guard) as stream_media()."""
    target = Path(urllib.parse.unquote(raw_path))
    if not target.is_absolute():
        target = BASE_DIR / target
    target = target.resolve()

    if not (_is_contained(target, BASE_DIR.resolve()) or _is_contained(target, CAPCUT_DRAFT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")
    return target


def build_filmstrip(source: Path, count: int) -> Path:
    """
    Render (or reuse) one horizontal sprite of `count` frames sampled evenly
    across `source`. Cache key includes the file's mtime+size so replacing a
    clip with a different file of the same name can't serve a stale strip.
    """
    FILMSTRIP_DIR.mkdir(parents=True, exist_ok=True)

    stat = source.stat()
    key = f"{source}|{stat.st_mtime_ns}|{stat.st_size}|{count}|{FRAME_WIDTH}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    out_path = FILMSTRIP_DIR / f"{digest}.jpg"
    if out_path.exists():
        return out_path

    duration = VideoEditor.get_media_info(str(source)).get("duration") or 0.0
    if duration <= 0:
        raise HTTPException(status_code=422, detail="อ่านความยาววิดีโอไม่ได้")

    # One ffmpeg pass with a `fps=` filter has to decode the whole file to
    # sample N frames -- measured 13.6s on the 115MB HEVC test clip. Input
    # seeking (`-ss` before `-i`) jumps per frame instead, so cost scales
    # with N rather than with clip length.
    tmp_dir = FILMSTRIP_DIR / f".tmp_{digest}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    try:
        for i in range(count):
            # Sample mid-slice of each of `count` equal spans, never the very
            # last frame (often black on phone recordings).
            t = duration * (i + 0.5) / count
            frame_path = tmp_dir / f"{i:03d}.jpg"
            grab = subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(source),
                 "-frames:v", "1", "-vf", f"scale={FRAME_WIDTH}:-2",
                 "-q:v", "4", str(frame_path)],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
            )
            if grab.returncode == 0 and frame_path.exists():
                frames.append(frame_path)

        if not frames:
            raise HTTPException(status_code=500, detail="ดึงเฟรมจากวิดีโอไม่ได้เลย")

        stack_cmd = ["ffmpeg", "-y"]
        for f in frames:
            stack_cmd += ["-i", str(f)]
        if len(frames) == 1:
            stack_cmd += ["-q:v", "4", str(out_path)]
        else:
            stack_cmd += ["-filter_complex", f"hstack=inputs={len(frames)}",
                          "-q:v", "4", str(out_path)]

        res = subprocess.run(stack_cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="ignore")
        if res.returncode != 0 or not out_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"สร้าง filmstrip ไม่สำเร็จ: {(res.stderr or '')[-200:]}",
            )
    finally:
        for f in tmp_dir.glob("*.jpg"):
            f.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass

    return out_path


@router.get("/filmstrip")
def get_filmstrip(path: str, count: int = 10):
    """
    Horizontal sprite of evenly-spaced frames for a timeline clip.

    Deliberately outside render_jobs.render_slot(): this is a sub-second
    single-frame tile job, and blocking it behind a full 9:16 render (minutes,
    CPU-only here) would leave the timeline grey the whole time.
    """
    count = max(MIN_FRAMES, min(MAX_FRAMES, count))
    source = _resolve_media(path)
    sprite = build_filmstrip(source, count)
    return FileResponse(
        sprite,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/overlay/layout")
def get_overlay_layout(req: OverlayLayoutRequest):
    """
    Computes static per-word positions (x, y, w) in normalized coordinates.
    Mirrors libass dialogue layout calculations for zero-drift preview parity.
    """
    from scripts.subtitle.word_layout import layout_overlay
    return layout_overlay(
        text=req.text,
        font_name=req.font_name,
        font_size_px=req.font_size_px,
        norm_x=req.norm_x,
        norm_y=req.norm_y,
        video_w=req.video_w,
        video_h=req.video_h,
    )


class SaveCustomHookTemplateRequest(BaseModel):
    id: Optional[str] = None
    label_th: Optional[str] = None
    name: Optional[str] = None
    font: Optional[str] = None
    tiers: Optional[Dict[str, Any]] = None
    motion: Optional[Dict[str, Any]] = None


@router.get("/hook-templates")
def list_hook_templates():
    """Returns built-in templates and user custom templates."""
    from scripts.hook_styles import HOOK_TEMPLATES, load_custom_hook_templates
    custom = load_custom_hook_templates()
    return {
        "status": "success",
        "builtin": HOOK_TEMPLATES,
        "custom": custom,
        "all": {**HOOK_TEMPLATES, **custom},
    }


@router.post("/hook-templates")
def create_or_update_hook_template(req: SaveCustomHookTemplateRequest):
    """Saves or updates a custom hook template in 02_Assets/Templates/custom_hook_templates.json."""
    from scripts.hook_styles import save_custom_hook_template, load_custom_hook_templates
    tid = req.id or f"custom_{int(time.time())}"
    data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    saved = save_custom_hook_template(tid, data)
    all_custom = load_custom_hook_templates()
    return {"status": "success", "template_id": tid, "template": saved, "templates": all_custom}


@router.delete("/hook-templates/{template_id}")
def remove_custom_hook_template(template_id: str):
    """Deletes a custom hook template. Built-in templates cannot be deleted."""
    from scripts.hook_styles import delete_custom_hook_template, load_custom_hook_templates, HOOK_TEMPLATES
    if template_id in HOOK_TEMPLATES:
        raise HTTPException(status_code=400, detail="ไม่สามารถลบแม่แบบมาตรฐานได้")
    success = delete_custom_hook_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบแม่แบบที่ต้องการลบ")
    all_custom = load_custom_hook_templates()
    return {"status": "success", "deleted_id": template_id, "templates": all_custom}
