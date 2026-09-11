"""
API Router for guided-take shot lists: generates a per-beat filming plan for
an angle from its real TTS voice timing, so the render pipeline can later map
footage onto script beats exactly instead of via AI vision matching.
See C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase A).
"""

from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from scripts.task_manager import TaskManager
from scripts.shot_list_builder import generate_shot_list_for_angle
from scripts.shot_lists_store import ShotListsStore
from scripts.quota import is_quota_error

router = APIRouter(tags=["Shot Lists"])

_VOICE_OVERRIDE_KEYS = ("voice", "voice_rate", "voice_engine_type", "voice_preset", "ad_tone")


def _execute_generate_shot_list_worker(
    task_id: str, product_id: str, angle_id: str, voice_overrides: Dict[str, Any],
) -> None:
    try:
        TaskManager.update_progress(task_id, 0.20, "กำลังเตรียมสคริปต์และสังเคราะห์เสียงพากย์จริง")
        result = generate_shot_list_for_angle(product_id, angle_id, voice_overrides)
        TaskManager.update_progress(task_id, 0.90, "กำลังบันทึกแผนถ่าย")
        TaskManager.complete_task(
            task_id,
            result=result,
            step_label="🎬 สร้างแผนถ่ายสำเร็จ!",
            target_id=product_id,
        )
    except Exception as e:
        import traceback
        print(f"[API] Shot list generation error: {type(e).__name__}: {e}")
        traceback.print_exc()
        if is_quota_error(e):
            TaskManager.fail_task(task_id, str(e), step_label="เกินโควต้า AI ต่อวันแล้ว")
        else:
            TaskManager.fail_task(task_id, str(e), step_label="สร้างแผนถ่ายไม่สำเร็จ")


@router.post("/api/products/{product_id}/angles/{angle_id}/shot-list")
def create_shot_list(
    product_id: str, angle_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks
):
    """Kicks off shot-list generation as a background task (same pattern as
    reroll-script, scripts/api_products.py's reroll_angle_script)."""
    voice_overrides = {
        key: payload.get(key) for key in _VOICE_OVERRIDE_KEYS if payload.get(key) is not None
    }

    task = TaskManager.create_task(
        task_type="generate_shot_list",
        title=f"สร้างแผนถ่าย: {angle_id}",
        payload={"product_id": product_id, "angle_id": angle_id, **voice_overrides},
        target_tab="flow",
        target_id=product_id,
    )

    background_tasks.add_task(
        _execute_generate_shot_list_worker,
        task["id"], product_id, angle_id, voice_overrides,
    )

    return {"success": True, "task_id": task["id"], "task": task}


@router.get("/api/products/{product_id}/angles/{angle_id}/shot-list")
def get_shot_list(product_id: str, angle_id: str):
    record = ShotListsStore.get(product_id, angle_id)
    if not record:
        raise HTTPException(status_code=404, detail="ยังไม่มีแผนถ่ายสำหรับมุมนี้")
    return record
