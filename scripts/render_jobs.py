"""
Shared render-job registry.

Full renders and partial re-rolls both run in the background and both are
watched by the same frontend polling loop, so they have to land in one
registry — otherwise /api/render/status/{job_id} would not find a re-roll.

Jobs live in memory only: a server restart forgets them, which is fine because
the artifacts themselves are on disk and recorded in the project manifest.
"""

import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from scripts.config import BASE_DIR

ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}


def create_job(job_id: str, message: str = "กำลังเริ่มต้นกระบวนการ...") -> Dict[str, Any]:
    """Register a queued job and return it."""
    ACTIVE_JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": message,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": [],
        "result": None,
        "error": None,
    }
    return ACTIVE_JOBS[job_id]


def progress_reporter(job_id: str) -> Callable[[str, float], None]:
    """A `progress_callback` for the pipeline that writes into the job."""
    def on_progress(msg: str, progress: float) -> None:
        job = ACTIVE_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "processing"
        job["progress"] = min(1.0, max(0.0, progress))
        job["message"] = msg
        job["logs"].append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
            "progress": int(progress * 100),
        })

    return on_progress


def media_url(file_path: Optional[str]) -> Optional[str]:
    """Turn an absolute artifact path into a /api/media URL the browser can load."""
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists():
        return None
    try:
        relative = path.relative_to(BASE_DIR)
    except ValueError:
        return None
    return f"/api/media/{relative}".replace("\\", "/")


def complete_job(job_id: str, result: Dict[str, Any], message: str = "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!") -> None:
    """Mark a job finished, shaping the pipeline result for the frontend."""
    job = ACTIVE_JOBS.get(job_id)
    if not job:
        return
    job["status"] = "completed"
    job["progress"] = 1.0
    job["message"] = message
    job["result"] = {
        "project_name": result.get("project_name"),
        "mp4_video": result.get("mp4_video"),
        "mp4_url": media_url(result.get("mp4_video")),
        "capcut_draft": result.get("capcut_draft"),
        "duration": result.get("duration", 0),
        "script": result.get("script"),
        "manifest": result.get("manifest"),
    }


def fail_job(job_id: str, error: Exception) -> None:
    job = ACTIVE_JOBS.get(job_id)
    if not job:
        return
    job["status"] = "failed"
    job["error"] = str(error)
    job["message"] = f"❌ เกิดข้อผิดพลาด: {error}"
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": f"Error: {error}",
        "progress": 0,
    })
