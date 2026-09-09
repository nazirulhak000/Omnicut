"""
API Router for Video library, Raw Footage Vault, Assets management, Uploads, and File operations.
"""

import os
import gc
import time
import uuid
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    SFX_DIR, MUSIC_DIR, STICKERS_DIR, CAPCUT_DRAFT_DIR
)
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import DEFAULT_BGM
from scripts.product_store import ProductStore
from scripts.export_registry import ExportRegistry
from scripts.media_service import (
    scan_video_files, get_file_info, stream_media_file
)
from scripts.api_schemas import (
    RenameVideoPayload, ReassignVideoPayload, BatchDeleteVideosPayload,
    DeleteFileRequest, OpenFolderRequest
)

router = APIRouter(tags=["Videos & Assets"])


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


def _safe_product_dir(base_dir: Path, product_id: str) -> Path:
    """
    Resolves `base_dir / product_id` and enforces the result stays contained
    within `base_dir`. `product_id` is client-controlled (query param / form
    field / JSON body) and otherwise flows straight into a Path join with no
    validation -- a relative traversal (`..\\..\\Windows\\Temp`) or an
    absolute path (`C:\\Users\\Public`, which makes `Path.__truediv__` discard
    `base_dir` entirely) would let a caller read/write/move files anywhere the
    process has access to. Legitimate ids are timestamp-based
    (`YYYYmmddHHMMSS_n`), so containment is airtight for real usage.
    Raises HTTPException(400) on any id that would escape base_dir.
    """
    resolved_base = base_dir.resolve()
    candidate = (base_dir / product_id).resolve()
    if not _is_contained(candidate, resolved_base):
        raise HTTPException(status_code=400, detail="product_id ไม่ถูกต้อง")
    return candidate


_RENAME_RETRY_ATTEMPTS = 8
_RENAME_RETRY_DELAY_SECONDS = 0.2


def _is_file_lock_error(error: OSError) -> bool:
    """Return True for the transient Windows error raised by open media files."""
    return getattr(error, "winerror", None) == 32


def _rename_with_retry(source: Path, target: Path) -> None:
    """Rename a media file, allowing a player a moment to release its handle."""
    for attempt in range(_RENAME_RETRY_ATTEMPTS):
        try:
            source.rename(target)
            return
        except OSError as error:
            if not _is_file_lock_error(error) or attempt == _RENAME_RETRY_ATTEMPTS - 1:
                raise
            gc.collect()
            time.sleep(_RENAME_RETRY_DELAY_SECONDS)


@router.get("/api/videos")
def list_raw_videos(product_id: Optional[str] = None):
    """Lists all available raw video candidates with fast single-pass scanning."""
    candidates = scan_video_files(RAW_DIR, INBOX_DIR)
    unique_paths = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    all_videos = [get_file_info(p) for p in unique_paths]

    product_videos = []
    if product_id:
        try:
            prod_assigned = ProductStore.get_product_videos(product_id)
            assigned_paths = {v.get("path") or v.get("rel_path") for v in prod_assigned}

            prod_dir = _safe_product_dir(RAW_DIR, product_id)
            prod_dir_paths = {p.resolve() for p in scan_video_files(prod_dir)} if prod_dir.exists() else set()

            for v in all_videos:
                v_path = Path(v["path"]).resolve()
                if v["path"] in assigned_paths or v["rel_path"] in assigned_paths or v_path in prod_dir_paths:
                    product_videos.append(v)
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error fetching product videos: {e}")
            product_videos = []

    return {
        "videos": all_videos,
        "product_videos": product_videos if product_id else all_videos,
        "product_id": product_id,
        "total_count": len(all_videos),
        "product_count": len(product_videos) if product_id else len(all_videos)
    }


@router.post("/api/videos/rename")
def rename_video_file(payload: RenameVideoPayload):
    """Safely renames a video file on disk and updates any ProductStore references."""
    video_path = payload.video_path
    new_name = payload.new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อคลิปใหม่")

    cleaned_path = video_path.replace("\\", "/").lstrip("/")
    v_path = Path(cleaned_path)
    if not v_path.is_absolute():
        v_path = (BASE_DIR / cleaned_path).resolve()

    if not v_path.exists() or not v_path.is_file():
        raw_check = (RAW_DIR / cleaned_path).resolve()
        if raw_check.exists() and raw_check.is_file():
            v_path = raw_check
        else:
            raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์คลิปต้นฉบับ: {Path(video_path).name}")

    try:
        v_path.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เปลี่ยนชื่อไฟล์ภายนอกโปรเจกต์")

    orig_suffix = v_path.suffix
    clean_new_name = "".join(c for c in new_name if c.isalnum() or c in "._- \u0E00-\u0E7F").strip()
    if not clean_new_name:
        raise HTTPException(status_code=400, detail="ชื่อใหม่มีตัวอักษรที่ไม่ถูกต้อง")

    if not clean_new_name.lower().endswith(orig_suffix.lower()):
        clean_new_name = f"{clean_new_name}{orig_suffix}"

    target_path = v_path.parent / clean_new_name
    if target_path.exists() and target_path.resolve() != v_path.resolve():
        target_path = v_path.parent / f"{target_path.stem}_{int(time.time())}{orig_suffix}"

    try:
        _rename_with_retry(v_path, target_path)
    except OSError as error:
        if _is_file_lock_error(error):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"ระบบยังเปิดคลิป '{v_path.name}' อยู่ ปิดพรีวิวหรือโปรแกรมที่เปิดไฟล์นี้ "
                    "แล้วลองบันทึกชื่อใหม่อีกครั้ง"
                ),
            )
        raise HTTPException(status_code=500, detail=f"เปลี่ยนชื่อไฟล์บนดิสก์ไม่สำเร็จ: {error}")
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"เปลี่ยนชื่อไฟล์บนดิสก์ไม่สำเร็จ: {error}")

    new_file_info = get_file_info(target_path)

    # A rename must not manufacture a second export identity for the same
    # rendered file. Keep the original export_id attached to the new path.
    try:
        export_record = ExportRegistry.find_by_path(v_path)
        if export_record:
            ExportRegistry.update_path(export_record.get("id"), target_path)
    except Exception as e:
        print(f"Notice: Failed to update export registry on rename: {e}")

    try:
        old_rel = str(v_path.relative_to(BASE_DIR)).replace("\\", "/")
        old_abs = str(v_path)
        # Read-modify-write inside one SQLite transaction (ProductStore._mutate())
        # instead of _load()/_save() -- the old pattern read+wrote outside any
        # lock and could silently clobber a concurrent writer's changes to the
        # same products table (e.g. a render finishing and calling
        # update_angle_status while this rename was in flight).
        with ProductStore._mutate() as products:
            for p in products:
                if payload.product_id and p.get("id") != payload.product_id:
                    continue
                v_list = p.get("videos", [])
                for v in v_list:
                    if v.get("path") == old_abs or v.get("rel_path") == old_rel or v.get("name") == v_path.name:
                        v["path"] = new_file_info["path"]
                        v["rel_path"] = new_file_info["rel_path"]
                        v["name"] = new_file_info["name"]
    except Exception as e:
        print(f"Notice: Failed to update ProductStore on rename: {e}")

    return {
        "success": True,
        "message": f"เปลี่ยนชื่อเป็น {target_path.name} เรียบร้อยแล้ว",
        "file": new_file_info
    }


@router.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    target_dir: str = Form("inbox"),
    product_id: Optional[str] = Form(None),
    custom_name: Optional[str] = Form(None)
):
    """Uploads a video or audio file to 00_Inbox or 01_Raw, and links to product if product_id is provided."""
    dest_dir = INBOX_DIR if target_dir == "inbox" else RAW_DIR
    if product_id:
        dest_dir = _safe_product_dir(RAW_DIR, product_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

    orig_filename = Path(file.filename or f"iphone_video_{int(time.time())}.mp4").name
    orig_suffix = Path(orig_filename).suffix or ".mp4"

    if custom_name and custom_name.strip():
        clean_custom = "".join(c for c in custom_name.strip() if c.isalnum() or c in "._- \u0E00-\u0E7F").strip()
        safe_filename = f"{clean_custom}{orig_suffix}" if clean_custom else f"video_{int(time.time())}{orig_suffix}"
    else:
        safe_filename = "".join(c for c in orig_filename if c.isalnum() or c in "._- \u0E00-\u0E7F")
        if not safe_filename:
            safe_filename = f"video_{int(time.time())}{orig_suffix}"

    save_path = dest_dir / safe_filename
    if save_path.exists():
        stem = Path(safe_filename).stem
        save_path = dest_dir / f"{stem}_{int(time.time())}{orig_suffix}"

    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    if orig_suffix.lower() in [".heic", ".heif"]:
        jpg_save_path = save_path.with_suffix(".jpg")
        try:
            conv_cmd = ["ffmpeg", "-y", "-i", str(save_path), "-q:v", "2", str(jpg_save_path)]
            subprocess.run(conv_cmd, check=True, capture_output=True)
            if jpg_save_path.exists():
                try:
                    save_path.unlink()
                except Exception:
                    pass
                save_path = jpg_save_path
        except Exception as conv_err:
            print(f"Warning: HEIC conversion failed: {conv_err}")

    file_info = get_file_info(save_path)

    if product_id:
        try:
            ProductStore.add_video_to_product(product_id, file_info)
        except Exception as e:
            print(f"Warning: Failed to attach video to product {product_id}: {e}")

    return {
        "message": "Upload successful",
        "file": file_info
    }


@router.get("/api/raw-vault")
def get_raw_vault():
    """Returns rich metadata of all raw footage grouped by products and unassigned clips.

    Was O(products x raw_files): every raw file got compared against every
    product's video list PLUS a directory-containment check, per product. At
    SaaS-ish scale (thousands of products/files) that is millions of
    comparisons per request. Rebuilt below as O(products + raw_files):
    - `dir_owner_by_pid` resolves the RAW_DIR-relative directory ownership in
      O(1) per file instead of `is_relative_to()` against every product's
      dir. This is safe because product ids never contain a path separator
      (they are opaque, e.g. timestamp-based), so `RAW_DIR/pid` directories
      are always siblings, never nested in one another -- a file can be
      "inside" at most one product's dir.
    - `path_owners`/`rel_owners` map a raw file's path/rel_path to the list
      of products whose stored `videos[]` reference it, replacing the
      per-product set-membership scan.
    A file can still match more than one product (dir-membership match plus
    a *different* product's stale videos[] reference, for example) exactly
    as before -- the old code had no `break` and appended the same file into
    every matching product's list, so that multi-match behavior is
    preserved here rather than "fixed".
    """
    products = ProductStore._load()
    raw_file_paths = scan_video_files(RAW_DIR, INBOX_DIR)
    all_raw_files = [get_file_info(p) for p in raw_file_paths]
    raw_dir_resolved = RAW_DIR.resolve()

    # Build all lookups ONCE, O(products + raw_files) total.
    dir_owner_by_pid: Dict[str, dict] = {}          # pid -> product, only for products with a RAW_DIR/pid folder
    path_owners: Dict[str, List[dict]] = {}          # v["path"] value -> [products that reference it]
    rel_owners: Dict[str, List[dict]] = {}           # v["rel_path"] value -> [products that reference it]

    for p in products:
        pid = p["id"]
        dir_owner_by_pid[pid] = p
        for v in p.get("videos", []):
            vp = v.get("path")
            if vp:
                path_owners.setdefault(vp, []).append(p)
            vrp = v.get("rel_path")
            if vrp:
                rel_owners.setdefault(vrp, []).append(p)

    prod_videos_by_pid: Dict[str, list] = {p["id"]: [] for p in products}
    assigned_file_paths = set()

    for v in all_raw_files:
        v_abs = Path(v["path"]).resolve()

        candidates: List[dict] = []

        # 1. Directory containment: is this file under RAW_DIR/<some pid>?
        #    (mirrors the old per-product `v_abs.is_relative_to(prod_dir)`)
        try:
            rel_to_raw = v_abs.relative_to(raw_dir_resolved)
            first_part = rel_to_raw.parts[0] if rel_to_raw.parts else None
            if first_part and first_part in dir_owner_by_pid:
                candidates.append(dir_owner_by_pid[first_part])
        except ValueError:
            pass  # not under RAW_DIR at all (e.g. came from INBOX_DIR)

        # 2/3/4. Same three set-membership checks the old code did, just via
        # a dict lookup instead of scanning every product's set.
        candidates.extend(path_owners.get(v["path"], []))
        candidates.extend(rel_owners.get(v["rel_path"], []))
        # old code also checked `v["rel_path"] in assigned_in_store` (the
        # PATH set) -- mirror that with rel_path looked up in path_owners too.
        candidates.extend(path_owners.get(v["rel_path"], []))

        matched_products: List[dict] = []
        seen_pids = set()
        for prod in candidates:
            if prod["id"] not in seen_pids:
                seen_pids.add(prod["id"])
                matched_products.append(prod)

        if matched_products:
            assigned_file_paths.add(v_abs)
        for prod in matched_products:
            v_copy = dict(v)
            v_copy["product_id"] = prod["id"]
            v_copy["product_title"] = prod.get("title", prod["id"])
            prod_videos_by_pid[prod["id"]].append(v_copy)

    product_groups = []
    for p in products:
        pid = p["id"]
        p_title = p.get("title", pid)
        p_cover = p.get("image_url") or p.get("cover_image") or None
        prod_videos = prod_videos_by_pid[pid]

        total_mb = sum(v.get("size_mb", 0) for v in prod_videos)
        product_groups.append({
            "product_id": pid,
            "product_title": p_title,
            "product_cover": p_cover,
            "category": p.get("category", "ทั่วไป"),
            "video_count": len(prod_videos),
            "total_size_mb": round(total_mb, 2),
            "videos": prod_videos
        })

    unassigned_videos = []
    for v in all_raw_files:
        v_abs = Path(v["path"]).resolve()
        if v_abs not in assigned_file_paths:
            v_copy = dict(v)
            v_copy["product_id"] = None
            v_copy["product_title"] = None
            unassigned_videos.append(v_copy)

    total_all_clips = len(all_raw_files)
    total_all_size_mb = round(sum(v.get("size_mb", 0) for v in all_raw_files), 2)

    return {
        "products": product_groups,
        "unassigned": unassigned_videos,
        "total_clips": total_all_clips,
        "total_size_mb": total_all_size_mb
    }


@router.post("/api/raw-vault/reassign")
def reassign_raw_video(payload: ReassignVideoPayload):
    """Reassigns or moves a raw video file to a new product, or unbinds it to general pool."""
    video_path = payload.video_path
    target_pid = payload.target_product_id
    source_pid = payload.source_product_id

    cleaned_path = video_path.replace("\\", "/").lstrip("/")
    v_path = Path(cleaned_path)
    if not v_path.is_absolute():
        v_path = (BASE_DIR / cleaned_path).resolve()

    if not v_path.exists():
        raw_check = (RAW_DIR / cleaned_path).resolve()
        if raw_check.exists():
            v_path = raw_check
        else:
            raise HTTPException(status_code=404, detail="ไม่พบไฟล์วิดีโอนี้")

    try:
        v_path.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")

    if source_pid:
        try:
            ProductStore.remove_video_from_product(source_pid, str(v_path))
        except Exception as e:
            print(f"Notice on remove from source product: {e}")

    if target_pid:
        target_dir = _safe_product_dir(RAW_DIR, target_pid)
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / v_path.name
        if dest_path.resolve() != v_path.resolve():
            if dest_path.exists():
                dest_path = target_dir / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
            shutil.move(str(v_path), str(dest_path))
            v_path = dest_path

        file_info = get_file_info(v_path)
        ProductStore.add_video_to_product(target_pid, file_info)
        return {
            "success": True,
            "message": "ผูกคลิปเข้ากับสินค้าเรียบร้อยแล้ว",
            "file": file_info
        }
    else:
        if v_path.parent != RAW_DIR.resolve():
            dest_path = RAW_DIR / v_path.name
            if dest_path.exists():
                dest_path = RAW_DIR / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
            shutil.move(str(v_path), str(dest_path))
            v_path = dest_path

        file_info = get_file_info(v_path)
        return {
            "success": True,
            "message": "ปลดคลิปออกเป็นคลิปอิสระ (Unassigned) เรียบร้อยแล้ว",
            "file": file_info
        }


@router.post("/api/raw-vault/batch-delete")
def batch_delete_raw_videos(payload: BatchDeleteVideosPayload):
    """Deletes multiple video files safely from disk and removes references."""
    deleted_count = 0
    errors = []

    for v_str in payload.video_paths:
        try:
            cleaned_path = v_str.replace("\\", "/").lstrip("/")
            v_path = Path(cleaned_path)
            if not v_path.is_absolute():
                v_path = (BASE_DIR / cleaned_path).resolve()

            if not v_path.exists():
                raw_check = (RAW_DIR / cleaned_path).resolve()
                if raw_check.exists():
                    v_path = raw_check

            if v_path.exists() and v_path.is_file():
                v_path.resolve().relative_to(BASE_DIR.resolve())
                for attempt in range(3):
                    try:
                        v_path.unlink()
                        deleted_count += 1
                        break
                    except PermissionError:
                        if attempt < 2:
                            gc.collect()
                            time.sleep(0.2)
                        else:
                            raise

                # Read-modify-write inside one SQLite transaction (ProductStore._mutate())
                # instead of _load()/_save() -- see rename handler above for why the
                # old outside-any-lock pattern was unsafe under concurrent writers.
                with ProductStore._mutate() as products:
                    for p in products:
                        v_list = p.get("videos", [])
                        new_v_list = [v for v in v_list if v.get("path") != str(v_path) and v.get("name") != v_path.name]
                        if len(new_v_list) != len(v_list):
                            p["videos"] = new_v_list
        except PermissionError:
            errors.append(f"{v_str}: ไฟล์กำลังถูกเปิดใช้งานหรือเล่นอยู่ กรุณาปิดโปรแกรมที่เปิดไฟล์ก่อน")
        except Exception as e:
            errors.append(f"{v_str}: {str(e)}")

    return {
        "success": True,
        "deleted_count": deleted_count,
        "errors": errors
    }


@router.get("/api/sfx")
def list_sfx():
    """Lists available sound effects from 02_Assets/SFX (including all subfolders)."""
    return {"sfx": AssetRegistry.sfx()}


@router.get("/api/assets/all")
def list_all_assets():
    """Lists all categorized assets (SFX, Music, Fonts, Stickers, LUTs)."""
    registry = AssetRegistry.load()
    font_list = [{**f, "font_family": f["family"]} for f in registry["fonts"]]

    return {
        "sfx": registry["sfx"],
        "music": registry["bgm"],
        "default_bgm": DEFAULT_BGM,
        "fonts": font_list,
        "stickers": registry["stickers"],
        "luts": registry["luts"],
        "effects": registry["effects"],
        "counts": {
            "sfx": len(registry["sfx"]),
            "music": len(registry["bgm"]),
            "fonts": len(font_list),
            "stickers": len(registry["stickers"]),
            "luts": len(registry["luts"]),
            "effects": len(registry["effects"])
        }
    }


@router.post("/api/assets/rescan")
def rescan_assets():
    """Force a fresh scan of 02_Assets/*."""
    registry = AssetRegistry.rebuild()
    return {"success": True, "counts": registry["counts"]}


class StarAssetRequest(BaseModel):
    id: str
    starred: bool


@router.post("/api/assets/star")
def star_asset(req: StarAssetRequest):
    """Marks/unmarks an asset (SFX/BGM) as starred so it surfaces as usable-in-editing."""
    AssetRegistry.set_starred(req.id, req.starred)
    return {"success": True, "id": req.id, "starred": req.starred}


_ASSET_UPLOAD_EXTS = {
    "sfx": {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"},
    "music": {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"},
    "fonts": {".ttf", ".otf", ".woff", ".woff2"},
    "stickers": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
    "luts": {".cube", ".3dl"},
    "branding": {".png", ".jpg", ".jpeg", ".webp", ".svg"},
}


@router.post("/api/assets/upload")
async def upload_asset(file: UploadFile = File(...), asset_type: str = Form("sfx")):
    """Uploads an asset to the appropriate 02_Assets subfolder."""
    type_map = {
        "sfx": SFX_DIR,
        "music": MUSIC_DIR,
        "fonts": ASSETS_DIR / "Fonts",
        "stickers": ASSETS_DIR / "Stickers_Memes",
        "luts": ASSETS_DIR / "LUTs_ColorPresets",
        "branding": ASSETS_DIR / "Branding"
    }
    asset_key = asset_type.lower()
    dest_dir = type_map.get(asset_key, SFX_DIR)

    # `file.filename` is client-controlled and must never be joined into a
    # path raw -- ".name" drops any directory components (relative traversal
    # like "../../scripts/config.py", or an absolute path that would make
    # pathlib discard dest_dir entirely), same as the /api/upload handler
    # above. An extension allowlist per asset type additionally stops an
    # upload from dropping an unexpected file type (e.g. a script) into
    # 02_Assets even once it can no longer escape dest_dir.
    orig_filename = Path(file.filename or "asset").name
    orig_suffix = Path(orig_filename).suffix.lower()
    allowed_exts = _ASSET_UPLOAD_EXTS.get(asset_key, _ASSET_UPLOAD_EXTS["sfx"])
    if orig_suffix not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"ไม่รองรับไฟล์นามสกุล '{orig_suffix or '(ไม่ระบุ)'}' สำหรับหมวด {asset_type}",
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = "".join(c for c in orig_filename if c.isalnum() or c in "._- ฀-๿")
    if not safe_filename or not safe_filename.lower().endswith(orig_suffix):
        safe_filename = f"asset_{int(time.time())}{orig_suffix}"

    save_path = dest_dir / safe_filename
    if save_path.exists():
        stem = Path(safe_filename).stem
        save_path = dest_dir / f"{stem}_{int(time.time())}{orig_suffix}"

    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    AssetRegistry.rebuild()

    return {
        "message": f"เพิ่มทรัพยากร {save_path.name} เข้าสู่ {asset_type.upper()} เรียบร้อยแล้ว",
        "file": get_file_info(save_path)
    }


@router.post("/api/open-folder")
def open_folder(req: OpenFolderRequest):
    """Opens a target directory in Windows Explorer."""
    folder_map = {
        "exports": EXPORTS_DIR,
        "inbox": INBOX_DIR,
        "raw": RAW_DIR,
        "assets": ASSETS_DIR,
        "sfx": SFX_DIR,
        "music": MUSIC_DIR,
        "fonts": ASSETS_DIR / "Fonts",
        "stickers": ASSETS_DIR / "Stickers_Memes",
        "luts": ASSETS_DIR / "LUTs_ColorPresets",
        "capcut": CAPCUT_DRAFT_DIR,
        "root": BASE_DIR
    }
    # Unknown keys used to fall through to Path(req.target) with no BASE_DIR
    # containment check at all -- every real caller passes a literal key
    # ('exports', etc.), so there is nothing that needs the escape hatch.
    target_path = folder_map.get(req.target)
    if target_path is None:
        raise HTTPException(status_code=400, detail=f"ไม่รู้จักปลายทาง: {req.target}")

    if os.name == 'nt':
        try:
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target_path))
            return {"success": True, "path": str(target_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"success": False, "message": "Not on Windows"}


class RevealFileRequest(BaseModel):
    file_path: str


@router.post("/api/reveal-file")
def reveal_file(req: RevealFileRequest):
    """
    Opens Explorer with one file pre-selected -- `explorer /select,<path>` --
    instead of just the containing folder. Before this, "เปิดโฟลเดอร์" put the
    user in a directory of 8+ mp4s with timestamped Thai filenames and left
    them to find the right one by eye; this highlights it for them directly.
    """
    target = Path(req.file_path)
    if not target.is_absolute():
        target = BASE_DIR / req.file_path
    target = target.resolve()

    allowed_roots = [
        (BASE_DIR / "04_Exports").resolve(),
        (BASE_DIR / "05_Covers_Thumbnails").resolve(),
    ]
    if not any(_is_contained(target, root) for root in allowed_roots):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เปิดไฟล์นอกพื้นที่โปรเจกต์")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")

    if os.name != 'nt':
        return {"success": False, "message": "Not on Windows"}
    try:
        # explorer.exe's own argument parser wants "/select,<path>" as ONE
        # token (comma glued to the path, no space) -- not standard argv
        # quoting. Fire-and-forget: explorer.exe is well known to exit
        # non-zero even on success, so its return code is not a signal to
        # check (os.startfile above reports nothing back either).
        subprocess.Popen(['explorer', f'/select,{target}'])
        return {"success": True, "path": str(target)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/delete-file")
def delete_file(req: DeleteFileRequest):
    """Safely deletes a file from 00_Inbox, 01_Raw, 04_Exports, or 02_Assets with Windows file-lock handling."""
    target = Path(req.file_path)
    if not target.is_absolute():
        target = BASE_DIR / req.file_path

    target = target.resolve()

    export_record = ExportRegistry.get(req.export_id) if req.export_id else ExportRegistry.find_by_path(target)
    if export_record is not None:
        registered = Path(str(export_record.get("path") or ""))
        if not registered.is_absolute():
            registered = (BASE_DIR / registered).resolve()
        else:
            registered = registered.resolve()
        if registered != target:
            raise HTTPException(
                status_code=409,
                detail="export_id ไม่ตรงกับไฟล์ที่เลือก จึงหยุดการลบเพื่อป้องกันการลบผิดเวอร์ชัน",
            )
        if export_record.get("status") == "posted":
            raise HTTPException(
                status_code=400,
                detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้ลบเพื่อเก็บไว้เป็นหลักฐาน",
            )

    allowed_roots = [
        (BASE_DIR / "00_Inbox").resolve(),
        (BASE_DIR / "01_Raw").resolve(),
        (BASE_DIR / "04_Exports").resolve(),
        (BASE_DIR / "02_Assets").resolve(),
        (BASE_DIR / "03_Projects").resolve(),
        (BASE_DIR / "06_Archive").resolve()
    ]

    is_safe = any(_is_contained(target, root) for root in allowed_roots)
    if not is_safe:
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้ลบไฟล์นอกพื้นที่โปรเจกต์")

    # Guard: Posted videos must be preserved as proof/archive and CANNOT be deleted.
    posted_dir = (BASE_DIR / "04_Exports" / "Posted").resolve()
    if _is_contained(target, posted_dir):
        raise HTTPException(status_code=400, detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้ลบเพื่อเก็บไว้เป็นหลักฐาน")

    try:
        from scripts.product_store import ProductStore
        for p in ProductStore._load():
            for a in p.get("angles", []):
                if a.get("status") == "posted" or a.get("posted_at"):
                    v_url = a.get("video_url")
                    if not v_url:
                        continue
                    stored = Path(v_url)
                    if not stored.is_absolute():
                        stored = (BASE_DIR / stored).resolve()
                    else:
                        stored = stored.resolve()

                    # Protect only the exact posted export. A product/angle
                    # can have several rendered versions; the identifier pair
                    # alone is intentionally NOT enough to block an older MP4.
                    exact_posted_file = stored == target
                    ready_duplicate = (
                        target.parent == (BASE_DIR / "04_Exports" / "Ready_to_post").resolve()
                        and (posted_dir / target.name).is_file()
                        and stored == target
                    )
                    if exact_posted_file and not ready_duplicate:
                        raise HTTPException(
                            status_code=400,
                            detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่อนุญาตให้ลบเพื่อเก็บไว้เป็นหลักฐาน"
                        )
    except HTTPException:
        raise
    except Exception as guard_err:
        # The guard above deliberately raises HTTPException when it finds a
        # posted export -- that must keep surfacing as-is. But an unrelated
        # failure here (ProductStore read error, bad path, etc.) must NOT be
        # treated as "no posted match found": that would silently let a
        # destructive delete proceed as if the guard had passed. Fail closed
        # instead -- refuse the delete rather than risk destroying proof of
        # a posted export.
        raise HTTPException(
            status_code=500,
            detail=f"ตรวจสอบสถานะโพสต์ก่อนลบไฟล์ไม่สำเร็จ จึงหยุดการลบเพื่อความปลอดภัย: {guard_err}",
        )

    if not target.exists():
        # A missing file must not leave its old ID attached to a future file
        # that happens to reuse the same path.
        if export_record:
            try:
                ExportRegistry.remove(export_record.get("id"))
            except Exception:
                pass
        return {"success": True, "message": "ไฟล์ถูกลบไปแล้ว", "filename": target.name}

    stem = target.stem
    parent = target.parent
    companions = [
        parent / f"{stem}-sub.srt",
        parent / f"{stem}-sub.vtt",
        parent / f"{stem}.srt",
        parent / f"{stem}.vtt",
        target.with_suffix(".webp")
    ]
    for sub_file in companions:
        if sub_file.exists():
            try:
                sub_file.unlink()
            except Exception:
                pass

    gc.collect()

    def _should_rollback_deleted_export():
        if not export_record or not req.product_id or not req.angle_id:
            return True
        product = next((p for p in ProductStore._load() if p.get("id") == req.product_id), None)
        angle = next(
            (
                a for a in (product or {}).get("angles", [])
                if (a.get("angle_id") or a.get("id")) == req.angle_id
            ),
            None,
        )
        if not angle:
            return True
        if angle.get("export_id") and angle.get("export_id") != export_record.get("id"):
            return False
        current_path = angle.get("video_url")
        if not current_path:
            return True
        current = Path(str(current_path))
        if not current.is_absolute():
            current = (BASE_DIR / current).resolve()
        else:
            current = current.resolve()
        return current == target

    def _on_deleted_success():
        try:
            if _should_rollback_deleted_export():
                ProductStore.rollback_by_video_or_project(
                    target.name,
                    product_id=req.product_id or "",
                    angle_id=req.angle_id or "",
                )
        except Exception:
            pass
        if export_record:
            try:
                ExportRegistry.remove(export_record.get("id"))
            except Exception:
                pass
        return {"success": True, "message": f"ลบไฟล์ {target.name} เรียบร้อยแล้ว", "filename": target.name}

    for attempt in range(3):
        try:
            target.unlink()
            return _on_deleted_success()
        except PermissionError:
            gc.collect()
            time.sleep(0.2)
        except Exception:
            break

    try:
        trash_dir = BASE_DIR / "06_Archive" / ".trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        trash_target = trash_dir / f"{uuid.uuid4().hex}_{target.name}"
        shutil.move(str(target), str(trash_target))
        try:
            trash_target.unlink()
        except Exception:
            pass
        return _on_deleted_success()
    except Exception:
        pass

    try:
        subprocess.run(["cmd", "/c", "del", "/f", "/q", str(target)], capture_output=True)
        if not target.exists():
            return _on_deleted_success()
    except Exception:
        pass

    raise HTTPException(status_code=500, detail="ไฟล์กำลังถูกเปิดใช้งานโดยเครื่องเล่นวิดีโอหรือ CapCut กรุณาหยุดเล่นวิดีโอหรือกดรีเฟรชหน้าเว็บ 1 ครั้งแล้วลองลบใหม่อีกครั้งครับ")


@router.get("/api/media/{file_path:path}")
def stream_media(file_path: str, request: Request):
    """Streams video or audio file by absolute or relative path."""
    decoded_path = urllib.parse.unquote(file_path)
    target = Path(decoded_path)
    if not target.is_absolute():
        target = BASE_DIR / decoded_path

    target = target.resolve()
    if not (_is_contained(target, BASE_DIR.resolve()) or _is_contained(target, CAPCUT_DRAFT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    return stream_media_file(target, request)
