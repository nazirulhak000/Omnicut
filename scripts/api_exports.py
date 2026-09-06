"""
API Router for Exported Videos and Versioning.
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.product_store import ProductStore
from scripts.media_service import get_file_info
from scripts.api_schemas import LinkAngleRequest
from scripts.video_editor import VideoEditor

router = APIRouter(tags=["Exports"])

# "Ready_to_post" was a permanent lie the moment the first clip got posted --
# nothing ever moved the file out, so list_exports() (scanning ONLY this dir)
# kept showing a posted clip as still-to-post forever. Posted/ is scanned
# alongside it below so a moved clip stays findable, tagged `is_posted`.
POSTED_DIR = EXPORTS_DIR.parent / "Posted"


@router.get("/api/exports")
def list_exports():
    """Lists all rendered videos in 04_Exports/Ready_to_post enriched with product & script metadata.
    Distinguishes latest active export vs previous superseded versions vs external unlinked files.
    """
    files = sorted(
        list(EXPORTS_DIR.glob("*.mp4")) + list(POSTED_DIR.glob("*.mp4")),
        key=os.path.getmtime, reverse=True,
    )
    all_products = ProductStore.get_all()

    # 1. Build lookup tables
    project_angle_map: Dict[str, tuple] = {}
    for p in all_products:
        for proj_name in p.get("projects", []):
            if proj_name:
                project_angle_map[proj_name.lower()] = (p, None)
        for a in p.get("angles", []):
            proj = a.get("project_name", "")
            if proj:
                project_angle_map[proj.lower()] = (p, a)
            vid_url = a.get("video_url", "")
            if vid_url:
                project_angle_map[Path(vid_url).stem.lower()] = (p, a)
                project_angle_map[Path(vid_url).name.lower()] = (p, a)

    # Check 03_Projects/ folders to get script_data if available
    project_disk_info: Dict[str, dict] = {}
    projects_dir = BASE_DIR / "03_Projects"
    if projects_dir.exists():
        for pdir in projects_dir.iterdir():
            if pdir.is_dir():
                pjson = pdir / "project.json"
                if pjson.exists():
                    try:
                        with open(pjson, "r", encoding="utf-8") as pf:
                            project_disk_info[pdir.name.lower()] = json.load(pf)
                    except Exception:
                        pass

    # Pass 1: Identify match for each file
    raw_matches = []
    for f in files:
        fname_low = f.name.lower()
        fstem_low = f.stem.lower()

        matched_prod = None
        matched_angle = None
        matched_proj_name = None

        # 1. Exact angle video_url match
        for p in all_products:
            for a in p.get("angles", []):
                vid_url = a.get("video_url", "")
                if vid_url:
                    vid_p = Path(vid_url)
                    if fname_low == vid_p.name.lower() or fstem_low == vid_p.stem.lower():
                        matched_prod, matched_angle = p, a
                        matched_proj_name = a.get("project_name")
                        break
            if matched_prod:
                break

        # 2. Exact project name match (stripping timestamp suffix like _YYYYMMDD_HHMMSS)
        if not matched_prod:
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_angle_map:
                p, a = project_angle_map[base_proj_name]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else base_proj_name
            elif fstem_low in project_angle_map:
                p, a = project_angle_map[fstem_low]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else fstem_low

        # 2.5 Check project_disk_info if still not matched
        if not matched_proj_name:
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_disk_info:
                matched_proj_name = base_proj_name
            elif fstem_low in project_disk_info:
                matched_proj_name = fstem_low

        # 3. Product ID match (exact token match)
        if not matched_prod:
            for p in all_products:
                pid = p.get("id", "").lower()
                if pid and (fstem_low == pid or fstem_low.startswith(f"{pid}_") or f"_{pid}_" in fstem_low):
                    matched_prod = p
                    break

        disk_proj = project_disk_info.get(matched_proj_name.lower()) if matched_proj_name else None

        raw_matches.append({
            "file": f,
            "product": matched_prod,
            "angle": matched_angle,
            "proj_name": matched_proj_name,
            "disk_proj": disk_proj
        })

    # Pass 2: Determine versioning per group
    latest_file_per_group: Dict[str, Any] = {}
    for item in raw_matches:
        p = item["product"]
        a = item["angle"]
        proj = item["proj_name"]
        group_key = None
        if p and a:
            group_key = f"{p.get('id')}:{a.get('angle_id')}"
        elif proj:
            group_key = f"proj:{proj}"
        elif p:
            group_key = f"prod:{p.get('id')}"

        if group_key and group_key not in latest_file_per_group:
            latest_file_per_group[group_key] = item["file"]

    results = []
    for item in raw_matches:
        f = item["file"]
        matched_prod = item["product"]
        matched_angle = item["angle"]
        matched_proj_name = item["proj_name"]
        disk_proj = item["disk_proj"]

        info = get_file_info(f)
        info["is_posted"] = f.parent.resolve() == POSTED_DIR.resolve()

        group_key = None
        if matched_prod and matched_angle:
            group_key = f"{matched_prod.get('id')}:{matched_angle.get('angle_id')}"
        elif matched_proj_name:
            group_key = f"proj:{matched_proj_name}"
        elif matched_prod:
            group_key = f"prod:{matched_prod.get('id')}"

        latest_f = latest_file_per_group.get(group_key) if group_key else None

        # Product metadata
        if matched_prod:
            info["product_id"] = matched_prod.get("id")
            info["product_name"] = matched_prod.get("name")
            info["price_deal"] = matched_prod.get("price_note")
            info["tiktok_product_id"] = (
                matched_prod.get("tiktok_product_id")
                or matched_prod.get("name", "")
            )

        # Script/Angle metadata
        if matched_angle:
            info["angle_id"] = matched_angle.get("angle_id")
            info["angle_name"] = matched_angle.get("angle_name")
            info["hook_title"] = matched_angle.get("hook_title")
            info["script_lines"] = matched_angle.get("script_lines")
            info["tiktok_caption"] = matched_angle.get("tiktok_caption")
            info["tiktok_hashtags"] = matched_angle.get("tiktok_hashtags")
            info["ad_tone"] = matched_angle.get("ad_tone")
            info["angle_status"] = matched_angle.get("status")
            info["qc_note"] = matched_angle.get("qc_note")
            info["project_name"] = matched_angle.get("project_name") or matched_proj_name
        elif disk_proj:
            s_data = disk_proj.get("script_data", {})
            info["hook_title"] = s_data.get("hook")
            info["script_lines"] = [l.get("text", "") if isinstance(l, dict) else str(l) for l in s_data.get("lines", [])]
            info["tiktok_caption"] = s_data.get("hook", "") + " พิกัดในตะกร้าเลย 👇" if s_data.get("hook") else ""
            info["tiktok_hashtags"] = f"#{matched_prod.get('name', '').replace(' ', '')} #รีวิวของดี #พิกัดในตะกร้า" if (matched_prod and matched_prod.get("name")) else "#รีวิวของดี #พิกัดในตะกร้า"
            info["project_name"] = disk_proj.get("project_name") or matched_proj_name

        # Determine version status
        has_script = bool(matched_angle or (disk_proj and disk_proj.get("script_data", {}).get("hook")))

        if has_script:
            info["is_unlinked"] = False
            if latest_f and latest_f == f:
                info["is_latest"] = True
                info["is_previous_version"] = False
            else:
                info["is_latest"] = False
                info["is_previous_version"] = True
                if latest_f:
                    info["latest_video_name"] = latest_f.name
                    info["latest_video_path"] = str(latest_f)
                    # Derived from the file's real parent, not hardcoded to
                    # Ready_to_post -- the "latest version" of a group can now
                    # be one that already moved to Posted/.
                    info["latest_video_rel"] = str(latest_f.relative_to(BASE_DIR)).replace("\\", "/")

            angle_vid = (matched_angle.get("video_url") or "").lower() if matched_angle else ""
            angle_qc_note = matched_angle.get("qc_note") if matched_angle else None
            is_this_file_rejected = False
            if angle_qc_note and angle_vid:
                is_this_file_rejected = (fname_low in angle_vid or str(f).lower() in angle_vid or Path(angle_vid).name.lower() == fname_low)
            elif angle_qc_note and matched_angle:
                is_this_file_rejected = (latest_f and latest_f == f)

            info["is_qc_rejected"] = is_this_file_rejected
            if not is_this_file_rejected:
                info["qc_note"] = None
        else:
            info["is_unlinked"] = True
            info["is_latest"] = False
            info["is_previous_version"] = False
            info["is_qc_rejected"] = False

        results.append(info)

    return {"exports": results}


@router.post("/api/exports/link-angle")
def link_export_to_angle(req: LinkAngleRequest):
    """Links an exported video to a product angle."""
    try:
        updated = ProductStore.update_angle_status(
            product_id=req.product_id,
            angle_id=req.angle_id,
            status="rendered",
            video_url=req.video_path
        )
        return {"status": "success", "product": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class MarkPostedRequest(BaseModel):
    file_path: str
    product_id: Optional[str] = None
    angle_id: Optional[str] = None


def _posted_companions(mp4_path: Path) -> List[Path]:
    """Every file that travels with an export when it moves: the gallery
    poster (webp) and, since Round POST-1, the TikTok cover (jpg)."""
    stem = mp4_path.stem
    found = [mp4_path.with_suffix(".webp")]
    cover = BASE_DIR / "05_Covers_Thumbnails" / f"{stem}_cover.jpg"
    if cover.exists():
        found.append(cover)
    return found


@router.post("/api/exports/mark-posted")
def mark_posted(req: MarkPostedRequest):
    """
    Moves a clip (+ its poster/cover) from Ready_to_post/ into Posted/, and
    when the angle is known, sets its status to 'posted' with the new path.

    ProductStore.reconcile() preserves 'posted'/'mobile_ready' status
    regardless of where the manifest's video_url points (product_store.py's
    "Preserve advanced lifecycle status" branch), so moving the file here
    does not fight the background reconciler.
    """
    src = Path(req.file_path)
    if not src.is_absolute():
        src = BASE_DIR / req.file_path
    src = src.resolve()

    if not str(src).startswith(str(EXPORTS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ใน Ready_to_post")
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {src.name}")

    companions = _posted_companions(src)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

    dest = POSTED_DIR / src.name
    shutil.move(str(src), str(dest))
    moved = [str(dest.relative_to(BASE_DIR)).replace("\\", "/")]
    for companion in companions:
        if companion.exists():
            companion_dest = POSTED_DIR / companion.name
            shutil.move(str(companion), str(companion_dest))
            moved.append(str(companion_dest.relative_to(BASE_DIR)).replace("\\", "/"))

    if req.product_id and req.angle_id:
        try:
            updated = ProductStore.update_angle_status(
                product_id=req.product_id,
                angle_id=req.angle_id,
                status="posted",
                video_url=str(dest.relative_to(BASE_DIR)).replace("\\", "/"),
            )
            return {"success": True, "moved": moved, "product": updated}
        except Exception as e:
            # The file already moved -- report the status-update failure
            # rather than rolling the move back; "it's in Posted/" stays true
            # either way, and the angle can be re-linked by hand afterward.
            return {"success": True, "moved": moved, "status_warning": str(e)}

    return {"success": True, "moved": moved}


@router.get("/api/exports/media-info")
def get_export_media_info(path: str):
    """
    Real per-file ffprobe data for the Post Studio spec tiles, fetched
    on-demand for whichever single clip is on screen -- NOT folded into
    list_exports() itself, since ffprobing every export on every gallery
    refresh would add real latency that grows with the export count for a
    property only ever looked at one clip at a time.

    Exists because the spec tiles used to hardcode "1080x1920 (9:16 FHD)" /
    "30 FPS - H.264 MP4" for every clip, which quietly lied for a `_draft`
    720p export.
    """
    target = Path(path)
    if not target.is_absolute():
        target = BASE_DIR / path
    target = target.resolve()

    if not (
        str(target).startswith(str(EXPORTS_DIR.resolve()))
        or str(target).startswith(str(POSTED_DIR.resolve()))
    ):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ export ที่อนุญาต")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")

    return VideoEditor.get_media_info(str(target))
