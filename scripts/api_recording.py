"""
API Router for guided-take recording sessions: pairs a QR-scanned mobile
filming page with a product/angle, accepts one uploaded video segment per
script beat (strict order, retake-last-only), and finalizes them into one
raw video the render pipeline can map onto script beats exactly.
See C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase B).
"""

import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from scripts.config import PROJECTS_DIR
from scripts.recording_sessions import RecordingSessionStore
from scripts.task_manager import TaskManager
from scripts.video_editor import VideoEditor

from fastapi import Depends
from scripts.channel_scope import ChannelScope, require_writable, require_active_for_new_work
from scripts.channel_store import ChannelError
from scripts.channel_ownership import reject_foreign_body_channel
from scripts.channel_workflows import api_store_kwargs, capture_job_scope, get_workflow_scope
from scripts.product_store import ProductStore

router = APIRouter(tags=["Recording Sessions"])

def _scope_kwargs(scope):
    if isinstance(scope, ChannelScope):
        return api_store_kwargs(scope)
    return {"channel_id": scope} if isinstance(scope, str) else {}


def _job_snapshot(scope):
    return capture_job_scope(scope) if isinstance(scope, ChannelScope) else {}


def _guard_product(product_id, scope):
    if isinstance(scope, ChannelScope) and not ProductStore.get(product_id, **_scope_kwargs(scope)):
        raise ChannelError(404, "resource_not_found", "Product not found")


def _guard_write(scope, new_work=False):
    if isinstance(scope, ChannelScope):
        (require_active_for_new_work if new_work else require_writable)(scope)


# Deliberately NOT under RAW_DIR: scripts/media_service.py's scan_video_files
# recursively globs RAW_DIR for the raw-footage vault / media picker, so raw
# per-beat segments living there showed up as separate selectable clips next
# to the real (already-concatenated) guided-take video. These are working
# files, never meant to be picked individually -- see finalize()'s cleanup
# in scripts/recording_sessions.py, which also removes this directory once
# they're consumed into the final video.
_SEGMENTS_DIR = PROJECTS_DIR / "_RecordingSegments"


@router.post("/api/recording-sessions")
def create_recording_session(payload: Dict[str, Any], scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    if isinstance(scope, ChannelScope):
        reject_foreign_body_channel(payload, scope.channel_id)
    product_id = payload.get("product_id")
    angle_id = payload.get("angle_id")
    if not product_id or not angle_id:
        raise HTTPException(status_code=400, detail="ต้องระบุ product_id และ angle_id")
    try:
        session = RecordingSessionStore.create(product_id, angle_id, **_scope_kwargs(scope))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"session_id": session["id"], "session": session}


@router.get("/api/recording-sessions/{session_id}")
def get_recording_session(session_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    session = RecordingSessionStore.get(session_id, **_scope_kwargs(scope))
    if not session:
        raise HTTPException(status_code=404, detail="ไม่พบเซสชันถ่ายทำ")
    return session


@router.post("/api/recording-sessions/{session_id}/segments")
async def upload_recording_segment(
    session_id: str,
    beat_index: int = Form(...),
    file: UploadFile = File(...), scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    session = RecordingSessionStore.get(session_id, **_scope_kwargs(scope))
    if not session:
        raise HTTPException(status_code=404, detail="ไม่พบเซสชันถ่ายทำ")

    dest_dir = _SEGMENTS_DIR / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    orig_suffix = Path(file.filename or "segment.webm").suffix or ".webm"
    dest_path = dest_dir / f"seg_{beat_index:03d}_raw_{int(time.time())}{orig_suffix}"

    with open(dest_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    try:
        info = VideoEditor.get_media_info(str(dest_path))
        probed_duration = float(info.get("duration") or 0.0)
        if probed_duration <= 0:
            raise ValueError("ไฟล์วิดีโอที่อัปโหลดเสียหายหรือตรวจสอบความยาวไม่สำเร็จ")
        updated = RecordingSessionStore.upload_segment(session_id, beat_index, str(dest_path), probed_duration, **_scope_kwargs(scope))
    except ValueError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    return {"success": True, "session": updated}


@router.delete("/api/recording-sessions/{session_id}/segments/{beat_index}")
def delete_recording_segment(session_id: str, beat_index: int, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=False)
    if not RecordingSessionStore.get(session_id, **_scope_kwargs(scope)):
        raise HTTPException(404, "Recording session not found")
    try:
        session, removed_path = RecordingSessionStore.delete_segment(session_id, beat_index, **_scope_kwargs(scope))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if removed_path:
        removed = Path(removed_path).resolve()
        expected = (_SEGMENTS_DIR / session_id).resolve()
        if expected.parent == _SEGMENTS_DIR.resolve() and removed.parent == expected:
            removed.unlink(missing_ok=True)
    return {"success": True, "session": session}


def _execute_finalize_worker(task_id: str, session_id: str, scope=None) -> None:
    try:
        TaskManager.update_progress(task_id, 0.20, "กำลังแปลงไฟล์วิดีโอแต่ละช็อตให้เป็นฟอร์แมตเดียวกัน", **_scope_kwargs(scope))
        result = RecordingSessionStore.finalize(session_id, **_scope_kwargs(scope))
        TaskManager.update_progress(task_id, 0.90, "กำลังบันทึกวิดีโอเข้าโปรเจกต์", **_scope_kwargs(scope))
        TaskManager.complete_task(
            task_id,
            result=result,
            step_label="🎬 รวมคลิปถ่ายทำสำเร็จ!",
         **_scope_kwargs(scope))
    except Exception as e:
        import traceback
        print(f"[API] Recording session finalize error: {type(e).__name__}: {e}")
        traceback.print_exc()
        TaskManager.fail_task(task_id, str(e), step_label="รวมคลิปไม่สำเร็จ", **_scope_kwargs(scope))


@router.post("/api/recording-sessions/{session_id}/finalize")
def finalize_recording_session(session_id: str, background_tasks: BackgroundTasks, scope: ChannelScope = Depends(get_workflow_scope)):
    _guard_write(scope, new_work=True)
    session = RecordingSessionStore.get(session_id, **_scope_kwargs(scope))
    if not session:
        raise HTTPException(status_code=404, detail="ไม่พบเซสชันถ่ายทำ")

    task = TaskManager.create_task(
        task_type="finalize_recording_session",
        title="รวมคลิปถ่ายทำ (Guided Take)",
        payload={
            "session_id": session_id,
            "product_id": session.get("product_id"),
            "angle_id": session.get("angle_id"),
        },
        target_tab="flow",
        target_id=session.get("product_id"),
     **_scope_kwargs(scope), job_scope=_job_snapshot(scope))
    background_tasks.add_task(_execute_finalize_worker, task["id"], session_id, scope.channel_id if isinstance(scope, ChannelScope) else None)
    return {"success": True, "task_id": task["id"], "task": task}
