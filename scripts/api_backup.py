"""API Router for One-Click System Backups in OmniCut Pro Studio."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Any, Dict

from scripts.backup_engine import BackupEngine

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("/create")
def create_backup() -> Dict[str, Any]:
    """Creates a full timestamped zip archive of system projects and databases."""
    try:
        result = BackupEngine.create_backup()
        return {"status": "ok", "backup": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")


@router.get("/list")
def list_backups() -> Dict[str, Any]:
    """Lists all available system backup archives."""
    try:
        backups = BackupEngine.list_backups()
        return {"status": "ok", "backups": backups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.get("/download/{filename}")
def download_backup(filename: str):
    """Downloads a specific backup archive by filename."""
    try:
        safe_path = BackupEngine.resolve_safe_path(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail=f"Backup archive '{filename}' not found")

    return FileResponse(
        path=safe_path,
        filename=filename,
        media_type="application/zip",
    )


@router.get("/verify/{filename}")
def verify_backup(filename: str) -> Dict[str, Any]:
    """Verifies the integrity and reads manifest of a backup archive."""
    try:
        res = BackupEngine.verify_backup(filename)
        return {"status": "ok", "verification": res}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backup archive '{filename}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.delete("/{filename}")
def delete_backup(filename: str) -> Dict[str, Any]:
    """Deletes a specific backup archive."""
    try:
        deleted = BackupEngine.delete_backup(filename)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Backup archive '{filename}' not found")
        return {"status": "ok", "message": f"Backup '{filename}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
