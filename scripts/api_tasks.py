"""
API Router for global task and activity management.
"""

from fastapi import APIRouter, HTTPException, Depends
from scripts.channel_scope import ChannelScope, require_writable
from scripts.channel_workflows import get_workflow_scope
from scripts.task_manager import TaskManager
from scripts import render_jobs
from scripts import config
from scripts.hyperframes_activity import hyperframes_activity_tasks
from scripts.hyperframes_render import HyperFramesRenderJobs
from scripts.api_background_isolation import request_background_isolation_cancel

router = APIRouter(tags=["Tasks"])


@router.get("/api/tasks/active")
def get_active_tasks(scope: ChannelScope = Depends(get_workflow_scope)):
    """Returns all running/queued tasks and recent history for global tracking."""
    tasks = TaskManager.get_active_tasks(**({"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}))
    if isinstance(scope, ChannelScope):
        tasks = [*tasks, *hyperframes_activity_tasks(config.BASE_DIR, scope.channel_id)]
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/api/tasks/{task_id}")
def get_task_by_id(task_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """Returns a specific task status."""
    if isinstance(scope, ChannelScope) and task_id.startswith(("hfr_", "creative_")):
        task = next((t for t in hyperframes_activity_tasks(config.BASE_DIR, scope.channel_id) if t["id"] == task_id), None)
    else:
        task = TaskManager.get_task(task_id, **({"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """
    Cancels a pending/running task.

    task_id and render job_id are the same uuid4 for every render/reroll task
    (see api_render.py's trigger_render and api_phase1.py's trigger_reroll,
    both of which mint one uuid4 and pass it as both render_jobs.create_job's
    job_id and TaskManager.create_task's task_id) -- so this also asks the
    render-job side to stop the actual background work, not just flip
    TaskManager's own bookkeeping. request_cancel() is a no-op (returns
    False) for a task_id that never had a matching render job -- e.g. a
    non-render task type -- so this is safe to call unconditionally.
    """
    if isinstance(scope, ChannelScope):
        require_writable(scope)
        if task_id.startswith("hfr_"):
            HyperFramesRenderJobs(config.BASE_DIR).cancel(scope.channel_id, task_id)
            return {"success": True, "task": get_task_by_id(task_id, scope)}
        if task_id.startswith("creative_"):
            raise HTTPException(status_code=409, detail="งาน AI ต้องจัดการ lease และ revision ผ่าน HyperFrames")
    kwargs = {"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}
    task = TaskManager.cancel_task(task_id, **kwargs)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    render_jobs.request_cancel(task_id, **kwargs)
    request_background_isolation_cancel(task_id)
    return {"success": True, "task": task}


@router.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """Removes a task from registry."""
    if isinstance(scope, ChannelScope):
        require_writable(scope)
        if task_id.startswith(("hfr_", "creative_")):
            raise HTTPException(status_code=409, detail="ประวัติ HyperFrames เก็บไว้สำหรับกู้คืนงาน เปิดจัดการใน HyperFrames")
    ok = TaskManager.delete_task(task_id, **({"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}))
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


@router.post("/api/tasks/clear-completed")
def clear_completed_tasks(scope: ChannelScope = Depends(get_workflow_scope)):
    """Clears all completed, failed, or cancelled tasks."""
    if isinstance(scope, ChannelScope):
        require_writable(scope)
    cleared = TaskManager.clear_completed(**({"channel_id": scope.channel_id} if isinstance(scope, ChannelScope) else {}))
    return {"success": True, "cleared_count": cleared}
