"""
API Router for global task and activity management.
"""

from fastapi import APIRouter, HTTPException
from scripts.task_manager import TaskManager

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
    """Cancels a pending/running task."""
    task = TaskManager.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
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
