"""
Unit and integration tests for Batch Render Queue and API endpoints.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.batch_render import BatchRenderManager, BATCH_REGISTRY
import scripts.batch_queue_store as batch_queue_store
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_tasks_and_batches(tmp_path, monkeypatch):
    """Ensure clean state before each test."""
    monkeypatch.setattr(batch_queue_store, "BATCH_QUEUE_PATH", tmp_path / "batch_render_queue.json")
    monkeypatch.setattr(TaskManager, "create_task", lambda **kwargs: kwargs)
    monkeypatch.setattr(TaskManager, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(TaskManager, "complete_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(TaskManager, "fail_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(TaskManager, "cancel_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)
    BATCH_REGISTRY.clear()
    yield
    BATCH_REGISTRY.clear()


def test_batch_checkpoint_survives_memory_reset(tmp_path, monkeypatch):
    """A queued batch must remain queryable after the in-memory cache is lost."""
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")
    product = {
        "id": "durable-product",
        "title": "Durable",
        "angles": [{"angle_id": "a1", "angle_name": "A1", "selected_video": str(clip)}],
    }
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)
    with patch.object(ProductStore, "get", return_value=product):
        created = BatchRenderManager.create_batch("durable-product")

    BATCH_REGISTRY.clear()
    restored = BatchRenderManager.get_batch(created["batch_id"])
    assert restored is not None
    assert restored["status"] == "queued"
    assert restored["items"][0]["angle_id"] == "a1"


def test_restart_requeues_only_interrupted_item(monkeypatch):
    """Recovery must preserve completed work and requeue only the interrupted item."""
    batch = {
        "batch_id": "restart-batch",
        "status": "processing",
        "cancelled": False,
        "items": [
            {"angle_id": "done", "status": "rendered"},
            {"angle_id": "retry", "status": "in_production", "error": None},
        ],
    }
    monkeypatch.setattr(batch_queue_store.BatchQueueStore, "load", lambda: [batch])
    persisted = []
    monkeypatch.setattr(BatchRenderManager, "_persist_batch", lambda item: persisted.append(item["batch_id"]))
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)

    assert BatchRenderManager.recover_pending_batches() == 1
    assert batch["status"] == "queued"
    assert batch["items"][0]["status"] == "rendered"
    assert batch["items"][1]["status"] == "queued"
    assert persisted == ["restart-batch"]


def test_batch_render_no_product():
    """Requesting batch render for non-existent product raises ValueError."""
    with pytest.raises(ValueError, match="ไม่พบข้อมูลสินค้า"):
        BatchRenderManager.create_batch(product_id="non_existent_9999")


def test_batch_render_create_and_query(tmp_path):
    """Test creating a batch with mocked product and querying its status."""
    fake_product_id = f"test_prod_{uuid.uuid4().hex[:6]}"
    fake_angle_1 = {
        "angle_id": "ang_1",
        "angle_name": "รีวิวการใช้งานจริง",
        "status": "scripted",
        "selected_video": str(tmp_path / "clip1.mp4"),
        "script_lines": ["สวัสดีครับ", "วันนี้จะมารีวิว"]
    }
    fake_angle_2 = {
        "angle_id": "ang_2",
        "angle_name": "เทียบความคุ้มค่า",
        "status": "scripted",
        "selected_video": str(tmp_path / "clip2.mp4"),
        "script_lines": ["เทียบกับรุ่นอื่น", "ตัวนี้คุ้มสุด"]
    }
    fake_product = {
        "id": fake_product_id,
        "title": "หูฟังไร้สาย Pro",
        "angles": [fake_angle_1, fake_angle_2]
    }

    # Create dummy video files
    (tmp_path / "clip1.mp4").write_text("fake video")
    (tmp_path / "clip2.mp4").write_text("fake video")

    with patch.object(ProductStore, "get", return_value=fake_product):
        res = BatchRenderManager.create_batch(
            product_id=fake_product_id,
            angle_ids=["ang_1", "ang_2"]
        )

        assert res["batch_id"] is not None
        assert res["total_items"] == 2
        assert res["status"] == "queued"
        assert len(res["items"]) == 2

        # Query batch
        batch_status = BatchRenderManager.get_batch(res["batch_id"])
        assert batch_status is not None
        assert batch_status["product_title"] == "หูฟังไร้สาย Pro"

        # Cancel batch
        cancel_res = BatchRenderManager.cancel_batch(res["batch_id"])
        assert cancel_res is True
        assert BatchRenderManager.get_batch(res["batch_id"])["status"] == "cancelled"


def test_batch_worker_execution(tmp_path):
    """Test batch worker execution updates angle status to rendered on success."""
    fake_product_id = f"test_prod_{uuid.uuid4().hex[:6]}"
    clip_file = tmp_path / "footage.mp4"
    clip_file.write_text("dummy mp4")

    fake_angle = {
        "angle_id": "ang_single",
        "angle_name": "จุดเด่นหลัก",
        "status": "scripted",
        "selected_video": str(clip_file),
        "script_lines": ["ประโยคแรก", "ประโยคสอง"]
    }
    fake_product = {
        "id": fake_product_id,
        "title": "คีย์บอร์ดไร้สาย",
        "angles": [fake_angle]
    }

    with patch.object(ProductStore, "get", return_value=fake_product), \
         patch.object(ProductStore, "update_angle_status") as mock_update_status, \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run") as mock_pipeline_run:

        mock_pipeline_run.return_value = {
            "mp4": "04_Exports/keyboard_v1.mp4",
            "project_name": "keyboard_proj",
            "export_id": "exp_123"
        }

        res = BatchRenderManager.create_batch(
            product_id=fake_product_id,
            angle_ids=["ang_single"]
        )
        batch_id = res["batch_id"]

        # Run worker synchronously for test verification
        BatchRenderManager._run_batch_worker(batch_id)

        batch_state = BatchRenderManager.get_batch(batch_id)
        assert batch_state["status"] == "completed"
        assert batch_state["completed_items"] == 1
        assert batch_state["failed_items"] == 0
        assert batch_state["items"][0]["status"] == "rendered"
        assert mock_update_status.called


def test_api_batch_render_flow(tmp_path):
    """Test full FastAPI endpoint flow for /api/render/batch."""
    # 1. Non-existent product -> 400
    with patch.object(ProductStore, "get", return_value=None):
        resp = client.post("/api/render/batch", json={"product_id": "none_123"})
        assert resp.status_code == 400

    # 2. Valid product -> 200 Queued
    clip_file = tmp_path / "raw.mp4"
    clip_file.write_text("clip")

    fake_prod = {
        "id": "prod_api_test",
        "title": "เมาส์ไร้สาย RGB",
        "angles": [
            {
                "angle_id": "ang_mouse",
                "angle_name": "รีวิวความเร็ว",
                "status": "scripted",
                "selected_video": str(clip_file)
            }
        ]
    }

    with patch.object(ProductStore, "get", return_value=fake_prod):
        create_resp = client.post("/api/render/batch", json={
            "product_id": "prod_api_test",
            "angle_ids": ["ang_mouse"],
            "voice_gender": "female"
        })
        assert create_resp.status_code == 200
        data = create_resp.json()
        assert "batch_id" in data
        batch_id = data["batch_id"]
        assert data["total_items"] == 1

        # 3. Status endpoint
        status_resp = client.get(f"/api/render/batch/{batch_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["batch_id"] == batch_id

        # 4. Cancel endpoint
        cancel_resp = client.post(f"/api/render/batch/{batch_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"


def test_batch_draft_api(tmp_path):
    """Test creating a batch draft with export_mp4=False."""
    clip_file = tmp_path / "raw.mp4"
    clip_file.write_text("clip")

    fake_prod = {
        "id": "prod_draft_test",
        "title": "สินค้าทดสอบดราฟต์",
        "angles": [
            {
                "angle_id": "ang_draft",
                "angle_name": "มุมดราฟต์เร็ว",
                "status": "scripted",
                "selected_video": str(clip_file)
            }
        ]
    }

    with patch.object(ProductStore, "get", return_value=fake_prod):
        create_resp = client.post("/api/render/batch", json={
            "product_id": "prod_draft_test",
            "angle_ids": ["ang_draft"],
            "export_mp4": False,
        })
        assert create_resp.status_code == 200
        data = create_resp.json()
        assert "batch_id" in data
        batch_id = data["batch_id"]

        status_resp = client.get(f"/api/render/batch/{batch_id}")
        assert status_resp.status_code == 200
        batch_info = status_resp.json()
        assert batch_info["options"].get("export_mp4") is False


def test_batch_worker_resolves_angle_style_and_completes_task_with_project_name(tmp_path):
    """Test that batch worker maps angle_id to editorial style preset and sends project_name in TaskManager completion."""
    clip_file = tmp_path / "raw.mp4"
    clip_file.write_text("clip")

    fake_prod = {
        "id": "prod_style_test",
        "title": "สายรัดข้อมืออัจฉริยะ",
        "angles": [
            {
                "angle_id": "stop_scroll",
                "angle_name": "เตือนภัยเชิงลบ",
                "status": "scripted",
                "selected_video": str(clip_file),
                "script_lines": ["หยุดก่อน!"]
            },
            {
                "angle_id": "pain_point",
                "angle_name": "ปัญหาก่อนใช้",
                "status": "scripted",
                "selected_video": str(clip_file),
                "script_lines": ["เคยเจอปัญหานี้ไหม"]
            }
        ]
    }

    captured_styles = []
    captured_hook_styles = []
    completed_tasks = []

    def mock_run(**kwargs):
        captured_styles.append(kwargs.get("style_preset"))
        captured_hook_styles.append(kwargs.get("hook_style"))
        return {
            "mp4": "",
            "project_name": f"proj_{kwargs.get('angle_id')}",
            "export_id": ""
        }

    with patch.object(ProductStore, "get", return_value=fake_prod), \
         patch.object(ProductStore, "update_angle_status"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=mock_run), \
         patch.object(TaskManager, "complete_task", side_effect=lambda task_id, **kwargs: completed_tasks.append(kwargs)):

        res = BatchRenderManager.create_batch(
            product_id="prod_style_test",
            angle_ids=["stop_scroll", "pain_point"],
            options={"export_mp4": False}
        )
        batch_id = res["batch_id"]
        BatchRenderManager._run_batch_worker(batch_id)

    # 1. Verify angle style mapping
    assert captured_styles == ["viral_punch", "pain_punch"]
    assert captured_hook_styles == [{"template": "b1_viral_red"}, {"template": "b1_pain_pink"}]

    # 2. Verify TaskManager.complete_task received project_name
    assert len(completed_tasks) == 1
    result_payload = completed_tasks[0].get("result", {})
    assert result_payload.get("project_name") == "proj_stop_scroll"
    assert result_payload.get("completed") == 2


def test_synthesize_project_name_with_product_code():
    from scripts.batch_render import synthesize_project_name
    name = synthesize_project_name(
        product_code="BCD01",
        product_title="BCD Loop Smartband สายรัดข้อมืออัจฉริยะ",
        angle_id="spec_review",
        existing_dirs=[]
    )
    assert name == "BCD01-รีวิวสเปก_1"

    # Collision test: when _1 exists, it should increment to _2
    name2 = synthesize_project_name(
        product_code="BCD01",
        product_title="BCD Loop Smartband สายรัดข้อมืออัจฉริยะ",
        angle_id="spec_review",
        existing_dirs=["BCD01-รีวิวสเปก_1"]
    )
    assert name2 == "BCD01-รีวิวสเปก_2"


def test_synthesize_project_name_without_product_code():
    from scripts.batch_render import synthesize_project_name
    name = synthesize_project_name(
        product_code="",
        product_title="BCD Loop Smartband สายรัดข้อมืออัจฉริยะ",
        angle_id="unboxing",
        existing_dirs=[]
    )
    assert name.startswith("bcd_loop_smartband_แกะกล่องว้าว_1")


def test_synthesize_project_name_with_batch_and_angle_slug_suffix():
    from scripts.batch_render import synthesize_project_name
    # Batch 2 angle with pain_point_b2 should strip _b2, find ปัญหาก่อนใช้, and start at version 2
    name = synthesize_project_name(
        product_code="BCD01",
        product_title="BCD Loop Smartband",
        angle_id="pain_point_b2",
        batch=2,
        existing_dirs=[]
    )
    assert name == "BCD01-ปัญหาก่อนใช้_2"

    # If _2 already exists in existing_dirs, it should increment to _3
    name_bump = synthesize_project_name(
        product_code="BCD01",
        product_title="BCD Loop Smartband",
        angle_id="pain_point_b2",
        batch=2,
        existing_dirs=["BCD01-ปัญหาก่อนใช้_2"]
    )
    assert name_bump == "BCD01-ปัญหาก่อนใช้_3"


def test_batch_render_uses_standard_project_name_convention(tmp_path):
    """Batch worker must synthesize project_name adhering to {product_code}-{angle_name}_{variant} when not provided."""
    dummy_video = tmp_path / "vid.mp4"
    dummy_video.write_bytes(b"dummy")

    fake_prod = {
        "id": "prod_name_test",
        "product_code": "BCD01",
        "title": "BCD Loop Smartband",
        "angles": [
            {
                "angle_id": "spec_review",
                "angle_name": "รีวิวสเปกเจาะลึก",
                "selected_video": str(dummy_video),
                "script_lines": ["Line 1"]
            }
        ]
    }

    captured_proj_name = []

    def mock_run(*args, **kwargs):
        captured_proj_name.append(kwargs.get("project_name"))
        return {
            "output_video": "",
            "project_name": kwargs.get("project_name"),
            "export_id": ""
        }

    with patch.object(ProductStore, "get", return_value=fake_prod), \
         patch.object(ProductStore, "update_angle_status"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=mock_run), \
         patch.object(TaskManager, "complete_task"):

        res = BatchRenderManager.create_batch(
            product_id="prod_name_test",
            angle_ids=["spec_review"],
            options={"export_mp4": False}
        )
        batch_id = res["batch_id"]
        BatchRenderManager._run_batch_worker(batch_id)

    assert len(captured_proj_name) == 1
    assert captured_proj_name[0].startswith("BCD01-รีวิวสเปก_")


