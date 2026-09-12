"""
Unit and integration tests for Batch Render Queue and API endpoints.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.batch_render import BatchRenderManager, BATCH_REGISTRY
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_tasks_and_batches():
    """Ensure clean state before each test."""
    BATCH_REGISTRY.clear()
    yield
    BATCH_REGISTRY.clear()


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
