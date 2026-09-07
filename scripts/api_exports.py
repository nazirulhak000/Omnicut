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

from scripts.config import BASE_DIR, EXPORTS_DIR, COVERS_DIR
from scripts.product_store import ProductStore
from scripts.media_service import get_file_info
from scripts.api_schemas import LinkAngleRequest
from scripts.video_editor import VideoEditor


def _is_contained(path: Path, root: Path) -> bool:
    """True when `path` sits inside `root`.

    `str.startswith` would also accept a sibling whose name merely extends
    the root's (``Capcut_evil`` against ``Capcut``), so compare path
    components instead.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

router = APIRouter(tags=["Exports"])

# "Ready_to_post" was a permanent lie the moment the first clip got posted --
# nothing ever moved the file out, so list_exports() (scanning ONLY this dir)
# kept showing a posted clip as still-to-post forever. Posted/ is scanned
# alongside it below so a moved clip stays findable, tagged `is_posted`.
POSTED_DIR = EXPORTS_DIR.parent / "Posted"


def _find_cover_by_stem(stem: str) -> Optional[Path]:
    """Find a generated 9:16 cover by its canonical stem."""
    name = str(stem or "").strip()
    if not name or not COVERS_DIR.exists():
        return None
    for suffix in ("_cover.jpg", "_cover_3x4.jpg"):
        expected = f"{name}{suffix}"
        direct = COVERS_DIR / expected
        if direct.is_file():
            return direct
        expected_folded = expected.casefold()
        for candidate in COVERS_DIR.iterdir():
            if candidate.is_file() and candidate.name.casefold() == expected_folded:
                return candidate
    return None


def _find_cover_sibling(cover: Path, suffix: str) -> Optional[Path]:
    """Find the other generated crop next to ``cover`` (case-insensitive)."""
    name = cover.name
    folded = name.casefold()
    if folded.endswith("_cover_3x4.jpg"):
        base = name[:-len("_cover_3x4.jpg")]
    elif folded.endswith("_cover.jpg"):
        base = name[:-len("_cover.jpg")]
    else:
        return None
    expected = f"{base}{suffix}"
    direct = cover.parent / expected
    if direct.is_file():
        return direct
    if cover.parent.exists():
        expected_folded = expected.casefold()
        for candidate in cover.parent.iterdir():
            if candidate.is_file() and candidate.name.casefold() == expected_folded:
                return candidate
    return None


def _promote_tiktok_cover_variant(info: Dict[str, Any]) -> None:
    """Expose both crops and make 3:4 the generic cover for TikTok flows."""
    raw = info.get("cover_path")
    if not raw:
        return
    selected = Path(raw)
    if not selected.is_absolute():
        selected = BASE_DIR / selected
    if not selected.is_file():
        return

    cover_3x4 = selected if selected.name.casefold().endswith("_cover_3x4.jpg") else _find_cover_sibling(selected, "_cover_3x4.jpg")
    cover_9x16 = selected if selected.name.casefold().endswith("_cover.jpg") else _find_cover_sibling(selected, "_cover.jpg")

    def add_variant(key: str, path: Optional[Path]) -> None:
        if not path or not path.is_file():
            return
        rel = str(path.relative_to(BASE_DIR)).replace("\\", "/")
        info[key] = rel
        info[key.replace("_path", "_url")] = f"/api/media/{rel}"

    add_variant("cover_3x4_path", cover_3x4)
    add_variant("cover_9x16_path", cover_9x16)
    if cover_3x4 and cover_3x4.is_file():
        rel = str(cover_3x4.relative_to(BASE_DIR)).replace("\\", "/")
        info["cover_path"] = rel
        info["cover_url"] = f"/api/media/{rel}"


def _find_project_cover(project_name: str) -> Optional[Path]:
    """Find a cover saved with the canonical project name."""
    return _find_cover_by_stem(project_name)


def _find_product_cover(product_name: str) -> Optional[Path]:
    """Find a legacy cover saved with the product name."""
    return _find_cover_by_stem(product_name)


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
    # Check 1 below used to be a nested "for every product: for every angle"
    # scan per export file (O(files x products x angles)). It is replaced by
    # two O(1) dict lookups (by video_url stem, by video_url name) built once
    # here. The old loop broke on the FIRST product/angle (in all_products /
    # angles iteration order) whose video_url stem OR name matched a given
    # file -- a plain dict keyed by stem/name would instead let a LATER angle
    # that happens to share a stem/name silently overwrite an earlier one.
    # Each entry below is (insertion_seq, product, angle) so the lookup at
    # match time can pick whichever of the stem/name hits has the smaller
    # seq, reproducing the original first-match-wins priority exactly.
    video_stem_map: Dict[str, tuple] = {}
    video_name_map: Dict[str, tuple] = {}
    # Check 3's exact-equality case (fstem_low == pid), first-match-wins.
    product_id_map: Dict[str, dict] = {}
    _angle_seq = 0
    for p in all_products:
        pid_key = (p.get("id") or "").lower()
        if pid_key and pid_key not in product_id_map:
            product_id_map[pid_key] = p
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

                stem_key = Path(vid_url).stem.lower()
                name_key = Path(vid_url).name.lower()
                if stem_key not in video_stem_map:
                    video_stem_map[stem_key] = (_angle_seq, p, a)
                if name_key not in video_name_map:
                    video_name_map[name_key] = (_angle_seq, p, a)
                _angle_seq += 1

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

        # 1. Exact angle video_url match (O(1) via the maps built above,
        # instead of scanning every product's every angle for every file)
        name_hit = video_name_map.get(fname_low)
        stem_hit = video_stem_map.get(fstem_low)
        if name_hit and stem_hit:
            winner = name_hit if name_hit[0] <= stem_hit[0] else stem_hit
        else:
            winner = name_hit or stem_hit
        if winner:
            _, p, a = winner
            matched_prod, matched_angle = p, a
            matched_proj_name = a.get("project_name")

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

        # 3. Product ID match (exact token match). The exact-equality case
        # (by far the common one -- pass 1/2 already caught most files, so
        # this is only reached for files with no angle/project match at
        # all) is an O(1) dict lookup via product_id_map built once above.
        # The prefix ("{pid}_...") and infix ("..._{pid}_...") cases can't be
        # turned into a plain dict lookup (pid is a variable-length,
        # arbitrary-content token -- there is no fixed key to index on
        # without risking a different match than the original substring
        # scan), so they still walk all_products, but ONLY for files that
        # reach this fallback, not for every file.
        if not matched_prod:
            exact_hit = product_id_map.get(fstem_low)
            if exact_hit:
                matched_prod = exact_hit
            else:
                for p in all_products:
                    pid = p.get("id", "").lower()
                    if pid and (fstem_low.startswith(f"{pid}_") or f"_{pid}_" in fstem_low):
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
        if not info.get("cover_path"):
            project_name = (matched_angle or {}).get("project_name") or matched_proj_name
            project_cover = _find_project_cover(project_name)
            if project_cover:
                rel_cover = str(project_cover.relative_to(BASE_DIR)).replace("\\", "/")
                info["cover_path"] = rel_cover
                info["cover_url"] = f"/api/media/{rel_cover}"
        if not info.get("cover_path") and matched_prod:
            product_cover = _find_product_cover(matched_prod.get("name", ""))
            if product_cover:
                rel_cover = str(product_cover.relative_to(BASE_DIR)).replace("\\", "/")
                info["cover_path"] = rel_cover
                info["cover_url"] = f"/api/media/{rel_cover}"
        _promote_tiktok_cover_variant(info)

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


def _mark_scheduled_queue_item_posted(source: Path, destination: Path) -> None:
    """Close the durable queue row when the extension moves this export.

    Queue identity is filename-based across Ready_to_post/Posted, so moving
    the file must update its lifecycle while keeping the same one-clip guard.
    A queue update is best-effort here: the export move remains authoritative
    even if an old installation has no schedule table yet.
    """
    try:
        from scripts.api_schedule_queue import video_key
        from scripts.schedule_store import ScheduleQueueStore, now_iso
        key = video_key(source)
        with ScheduleQueueStore._mutate() as records:
            for row in records:
                if row.get("video_key") == key or Path(str(row.get("video_path", ""))).name.casefold() == source.name.casefold():
                    row["video_path"] = str(destination.relative_to(BASE_DIR)).replace("\\", "/")
                    row["status"] = "posted"
                    row["posted_at"] = now_iso()
                    row["updated_at"] = now_iso()
    except Exception:
        # Never turn a successful file move into a failed post because the
        # optional queue mirror is unavailable.
        return


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

    if not _is_contained(src, EXPORTS_DIR.resolve()):
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

    _mark_scheduled_queue_item_posted(src, dest)

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
        _is_contained(target, EXPORTS_DIR.resolve())
        or _is_contained(target, POSTED_DIR.resolve())
    ):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ export ที่อนุญาต")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")

    return VideoEditor.get_media_info(str(target))
