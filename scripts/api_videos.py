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

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    SFX_DIR, MUSIC_DIR, STICKERS_DIR, CAPCUT_DRAFT_DIR
)
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import DEFAULT_BGM
from scripts.product_store import ProductStore
from scripts.media_service import (
    scan_video_files, get_file_info, stream_media_file
)
from scripts.api_schemas import (
    RenameVideoPayload, ReassignVideoPayload, BatchDeleteVideosPayload,
    DeleteFileRequest, OpenFolderRequest
)

router = APIRouter(tags=["Videos & Assets"])


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

            prod_dir = RAW_DIR / product_id
            prod_dir_paths = {p.resolve() for p in scan_video_files(prod_dir)} if prod_dir.exists() else set()

            for v in all_videos:
                v_path = Path(v["path"]).resolve()
                if v["path"] in assigned_paths or v["rel_path"] in assigned_paths or v_path in prod_dir_paths:
                    product_videos.append(v)
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
        v_path.rename(target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เปลี่ยนชื่อไฟล์บนดิสก์ไม่สำเร็จ: {e}")

    new_file_info = get_file_info(target_path)

    try:
        products = ProductStore._load()
        updated_any = False
        old_rel = str(v_path.relative_to(BASE_DIR)).replace("\\", "/")
        old_abs = str(v_path)
        for p in products:
            if payload.product_id and p.get("id") != payload.product_id:
                continue
            v_list = p.get("videos", [])
            for v in v_list:
                if v.get("path") == old_abs or v.get("rel_path") == old_rel or v.get("name") == v_path.name:
                    v["path"] = new_file_info["path"]
                    v["rel_path"] = new_file_info["rel_path"]
                    v["name"] = new_file_info["name"]
                    updated_any = True
        if updated_any:
            ProductStore._save(products)
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
        dest_dir = RAW_DIR / product_id
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
    """Returns rich metadata of all raw footage grouped by products and unassigned clips."""
    products = ProductStore._load()
    raw_file_paths = scan_video_files(RAW_DIR, INBOX_DIR)
    all_raw_files = [get_file_info(p) for p in raw_file_paths]

    product_groups = []
    assigned_file_paths = set()

    for p in products:
        pid = p["id"]
        p_title = p.get("title", pid)
        p_cover = p.get("image_url") or p.get("cover_image") or None
        prod_dir = (RAW_DIR / pid).resolve()

        prod_videos = []
        assigned_in_store = {v.get("path") for v in p.get("videos", []) if v.get("path")}
        assigned_rel_in_store = {v.get("rel_path") for v in p.get("videos", []) if v.get("rel_path")}

        for v in all_raw_files:
            v_abs = Path(v["path"]).resolve()
            is_in_dir = False
            try:
                is_in_dir = v_abs.is_relative_to(prod_dir)
            except Exception:
                pass

            if is_in_dir or v["path"] in assigned_in_store or v["rel_path"] in assigned_rel_in_store or v["rel_path"] in assigned_in_store:
                v_copy = dict(v)
                v_copy["product_id"] = pid
                v_copy["product_title"] = p_title
                prod_videos.append(v_copy)
                assigned_file_paths.add(v_abs)

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
        target_dir = RAW_DIR / target_pid
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

                products = ProductStore._load()
                updated_any = False
                for p in products:
                    v_list = p.get("videos", [])
                    new_v_list = [v for v in v_list if v.get("path") != str(v_path) and v.get("name") != v_path.name]
                    if len(new_v_list) != len(v_list):
                        p["videos"] = new_v_list
                        updated_any = True
                if updated_any:
                    ProductStore._save(products)
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
    """Lists available sound effects from 02_Assets/SFX."""
    sfx_files = sorted(list(SFX_DIR.glob("*.wav")) + list(SFX_DIR.glob("*.mp3")))
    results = []
    for sf in sfx_files:
        info = get_file_info(sf)
        info["audio_url"] = f"/api/media/{info['rel_path']}"
        results.append(info)
    return {"sfx": results}


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
        "counts": {
            "sfx": len(registry["sfx"]),
            "music": len(registry["bgm"]),
            "fonts": len(font_list),
            "stickers": len(registry["stickers"]),
            "luts": len(registry["luts"])
        }
    }


@router.post("/api/assets/rescan")
def rescan_assets():
    """Force a fresh scan of 02_Assets/*."""
    registry = AssetRegistry.rebuild()
    return {"success": True, "counts": registry["counts"]}


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
    dest_dir = type_map.get(asset_type.lower(), SFX_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    save_path = dest_dir / file.filename
    with open(save_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    AssetRegistry.rebuild()

    return {
        "message": f"เพิ่มทรัพยากร {file.filename} เข้าสู่ {asset_type.upper()} เรียบร้อยแล้ว",
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
    target_path = folder_map.get(req.target, Path(req.target))

    if os.name == 'nt':
        try:
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target_path))
            return {"success": True, "path": str(target_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"success": False, "message": "Not on Windows"}


@router.post("/api/delete-file")
def delete_file(req: DeleteFileRequest):
    """Safely deletes a file from 00_Inbox, 01_Raw, 04_Exports, or 02_Assets with Windows file-lock handling."""
    target = Path(req.file_path)
    if not target.is_absolute():
        target = BASE_DIR / req.file_path

    target = target.resolve()

    allowed_roots = [
        (BASE_DIR / "00_Inbox").resolve(),
        (BASE_DIR / "01_Raw").resolve(),
        (BASE_DIR / "04_Exports").resolve(),
        (BASE_DIR / "02_Assets").resolve(),
        (BASE_DIR / "03_Projects").resolve(),
        (BASE_DIR / "06_Archive").resolve()
    ]

    is_safe = any(str(target).startswith(str(root)) for root in allowed_roots)
    if not is_safe:
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้ลบไฟล์นอกพื้นที่โปรเจกต์")

    if not target.exists():
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

    def _on_deleted_success():
        try:
            ProductStore.rollback_by_video_or_project(target.name)
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
    if not (str(target).startswith(str(BASE_DIR)) or str(target).startswith(str(CAPCUT_DRAFT_DIR))):
        raise HTTPException(status_code=403, detail="Access denied")

    return stream_media_file(target, request)
