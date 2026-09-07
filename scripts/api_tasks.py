"""
API Router for global task and activity management.
"""

from fastapi import APIRouter, HTTPException
from scripts.task_manager import TaskManager
from scripts import render_jobs

router = APIRouter(tags=["Tasks"])


@router.get("/api/tasks/active")
def get_active_tasks():
    """Returns all running/queued tasks and recent history for global tracking."""
    tasks = TaskManager.get_active_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/api/tasks/{task_id}")
def get_task_by_id(task_id: str):
    """Returns a specific task status."""
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
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
    task = TaskManager.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    render_jobs.request_cancel(task_id)
    return {"success": True, "task": task}


@router.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Removes a task from registry."""
    ok = TaskManager.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


@router.post("/api/tasks/clear-completed")
def clear_completed_tasks():
    """Clears all completed, failed, or cancelled tasks."""
    cleared = TaskManager.clear_completed()
    return {"success": True, "cleared_count": cleared}
