"""API Router for iPhone Direct Ingest over USB in OmniCut Pro Studio."""
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.config import BASE_DIR, INBOX_DIR, RAW_DIR
from scripts.product_store import ProductStore

router = APIRouter(prefix="/api/iphone", tags=["iphone-direct"])

IPHONE_INBOX_DIR = INBOX_DIR / "iPhone_Clips"
IPHONE_INBOX_DIR.mkdir(parents=True, exist_ok=True)

SCAN_PS_SCRIPT = """
$shell = New-Object -ComObject Shell.Application
$computer = $shell.Namespace(17)
$iphone = $computer.Items() | Where-Object { $_.Name -like '*iPhone*' -or $_.Name -like '*Apple*' }

if (-not $iphone) {
    @{ connected = $false; accessible = $false; error = "ไม่พบอุปกรณ์ iPhone กรุณาเสียบสาย USB" } | ConvertTo-Json
    exit 0
}

$devFolder = $iphone.GetFolder
$storage = $devFolder.Items() | Where-Object { $_.Name -eq 'Internal Storage' }
if (-not $storage) {
    @{ connected = $true; accessible = $false; error = "ไม่สามารถเข้าถึงพื้นที่จัดเก็บได้ กรุณาปลดล็อกหน้าจอ iPhone (Passcode/FaceID)" } | ConvertTo-Json
    exit 0
}

$storageFolder = $storage.GetFolder
$folders = @($storageFolder.Items()) | Sort-Object Name -Descending
$newest = $folders | Where-Object { $_.Name -match '^\\d{6}_[a-z]' } | Select-Object -First 1

if (-not $newest) {
    @{ connected = $true; accessible = $false; error = "ไม่พบโฟลเดอร์ภาพ DCIM ใน iPhone" } | ConvertTo-Json
    exit 0
}

$f = $newest.GetFolder
$items = @($f.Items())
$vids = @()
foreach ($it in $items) {
    $type = $f.GetDetailsOf($it, 1)
    if ($type -like '*MOV*' -or $type -like '*video*' -or $type -like '*movie*' -or $type -like '*mp4*') {
        $name = $f.GetDetailsOf($it, 0)
        $size = $f.GetDetailsOf($it, 2)
        $date = $f.GetDetailsOf($it, 3)
        $vids += @{
            name = $name
            file_name = "$name.MOV"
            size = $size
            date = $date
        }
    }
}

$recent = $vids | Sort-Object { $_.name } -Descending | Select-Object -First 60
@{
    connected = $true
    accessible = $true
    device_name = $iphone.Name
    folder = $newest.Name
    total_videos = $vids.Count
    clips = $recent
} | ConvertTo-Json -Depth 3
"""

class PullRequest(BaseModel):
    clip_names: List[str] = Field(..., description="List of clip names without extension, e.g. ['IMG_8212', 'IMG_8213']")
    target_type: str = Field(default="inbox", description="'inbox' or 'product'")
    product_id: Optional[str] = Field(default=None, description="Target product UUID when target_type is 'product'")

def _get_local_media_index() -> Dict[str, str]:
    """Builds a map of lowercase filename -> relative path in 00_Inbox or 01_Raw."""
    index: Dict[str, str] = {}
    for search_dir in [INBOX_DIR, RAW_DIR]:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in [".mov", ".mp4", ".m4v"]:
                try:
                    rel = str(f.relative_to(BASE_DIR)).replace("\\", "/")
                    index[f.name.lower()] = rel
                    index[f.stem.lower()] = rel
                except ValueError:
                    pass
    return index

@router.get("/status")
def get_iphone_status():
    """Checks whether an iPhone is connected via USB and whether its storage is accessible."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", SCAN_PS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=8
        )
        if res.returncode != 0 or not res.stdout.strip():
            return {
                "connected": False,
                "accessible": False,
                "device_name": None,
                "error": "เกิดข้อผิดพลาดในการตรวจสอบอุปกรณ์ผ่านระบบ WPD"
            }
        data = json.loads(res.stdout.strip())
        return {
            "connected": bool(data.get("connected")),
            "accessible": bool(data.get("accessible")),
            "device_name": data.get("device_name"),
            "folder": data.get("folder"),
            "total_videos": data.get("total_videos", 0),
            "error": data.get("error")
        }
    except subprocess.TimeoutExpired:
        return {
            "connected": True,
            "accessible": False,
            "device_name": "Apple iPhone",
            "error": "การเชื่อมต่อใช้เวลานานผิดปกติ กรุณาปลดล็อกหน้าจอ iPhone (FaceID/Passcode)"
        }
    except Exception as e:
        return {
            "connected": False,
            "accessible": False,
            "error": str(e)
        }

@router.get("/clips")
def list_iphone_clips(limit: int = 50):
    """Scans and returns recent clips from connected iPhone, cross-referenced with local library."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", SCAN_PS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode != 0 or not res.stdout.strip():
            raise HTTPException(status_code=500, detail="ไม่สามารถอ่านข้อมูลจาก iPhone ได้")
        
        data = json.loads(res.stdout.strip())
        if not data.get("connected"):
            raise HTTPException(status_code=404, detail=data.get("error", "ไม่พบ iPhone"))
        if not data.get("accessible"):
            raise HTTPException(status_code=403, detail=data.get("error", "หน้าจอล็อกอยู่"))

        local_index = _get_local_media_index()
        raw_clips = data.get("clips", [])
        if isinstance(raw_clips, dict):
            raw_clips = [raw_clips]
        
        clips = []
        for c in raw_clips[:limit]:
            name = c.get("name")
            fname = c.get("file_name") or f"{name}.MOV"
            local_match = local_index.get(fname.lower()) or local_index.get(name.lower())
            
            clips.append({
                "name": name,
                "file_name": fname,
                "size": c.get("size", "0 MB"),
                "date": c.get("date", ""),
                "already_imported": bool(local_match),
                "imported_path": local_match
            })
            
        return {
            "connected": True,
            "accessible": True,
            "device_name": data.get("device_name"),
            "folder": data.get("folder"),
            "total_count": len(clips),
            "clips": clips
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="หมดเวลาเชื่อมต่อกับ iPhone กรุณาปลดล็อกหน้าจอและลองใหม่อีกครั้ง"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {e}")

@router.post("/pull")
def pull_iphone_clips(req: PullRequest):
    """Directly copies selected video clips from iPhone to destination folder."""
    if not req.clip_names:
        raise HTTPException(status_code=400, detail="กรุณาเลือกอย่างน้อย 1 คลิป")

    # Determine destination folder
    if req.target_type == "product" and req.product_id:
        target_dir = RAW_DIR / req.product_id
        target_dir.mkdir(parents=True, exist_ok=True)
        # Update product raw_folder if not set
        prod = ProductStore.find(req.product_id)
        if prod and not prod.get("raw_folder"):
            prod["raw_folder"] = f"01_Raw/{req.product_id}"
            ProductStore.update(req.product_id, prod)
    else:
        target_dir = IPHONE_INBOX_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

    dest_str = str(target_dir.resolve())
    clean_clips_json = json.dumps(req.clip_names)

    # Use a separate ps1 template with -replace or plain string to avoid f-string escaping issues
    script_parts = [
        f'$destDir = "{dest_str}"',
        f"$clipNames = ConvertFrom-Json '{clean_clips_json}'",
        """
        $shell = New-Object -ComObject Shell.Application
        $computer = $shell.Namespace(17)
        $iphone = $computer.Items() | Where-Object { $_.Name -like '*iPhone*' -or $_.Name -like '*Apple*' }

        if (-not $iphone) {
            @{ success = $false; error = "iPhone not found" } | ConvertTo-Json
            exit 0
        }

        $devFolder = $iphone.GetFolder
        $storage = $devFolder.Items() | Where-Object { $_.Name -eq 'Internal Storage' }
        if (-not $storage) {
            @{ success = $false; error = "Screen locked" } | ConvertTo-Json
            exit 0
        }

        $storageFolder = $storage.GetFolder
        $folders = @($storageFolder.Items()) | Sort-Object Name -Descending
        $newest = $folders | Where-Object { $_.Name -match '^\\d{6}_[a-z]' } | Select-Object -First 1

        $f = $newest.GetFolder
        $destFolderObj = $shell.Namespace($destDir)

        $copied = @()
        $skipped = @()

        foreach ($it in $f.Items()) {
            $name = $f.GetDetailsOf($it, 0)
            if ($clipNames -contains $name) {
                $targetFile = Join-Path $destDir "$name.MOV"
                if (Test-Path $targetFile) {
                    $skipped += $name
                } else {
                    $destFolderObj.CopyHere($it, 16 + 4)
                    $copied += $name
                }
            }
        }

        @{
            success = $true
            copied = $copied
            skipped = $skipped
        } | ConvertTo-Json
        """
    ]
    copy_ps_script = "\n".join(script_parts)

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", copy_ps_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.returncode != 0 or not res.stdout.strip():
            raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดในการคัดลอกไฟล์จาก iPhone")
            
        data = json.loads(res.stdout.strip())
        if not data.get("success"):
            raise HTTPException(status_code=400, detail=data.get("error", "ไม่สามารถดึงคลิปได้"))

        return {
            "status": "ok",
            "copied_count": len(data.get("copied", [])),
            "copied": data.get("copied", []),
            "skipped_count": len(data.get("skipped", [])),
            "skipped": data.get("skipped", []),
            "target_folder": str(target_dir.relative_to(BASE_DIR)).replace("\\", "/")
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="หมดเวลาในการส่งไฟล์ (ไฟล์อาจมีขนาดใหญ่มาก)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {e}")
