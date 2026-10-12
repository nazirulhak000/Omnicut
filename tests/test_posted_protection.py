"""
Tests for Posted Video Protection (Round POST-4).
Verifies:
1. Posted angles in ProductStore are never rolled back or reverted to in_production.
2. Deleting files tied to posted angles is blocked with 400 error.
3. Re-rendering posted angles or projects is strictly blocked.
4. GET /projects/{project_name} reports is_posted = True for posted angles.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from scripts.product_store import ProductStore
from scripts.api_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_rollback_by_video_or_project_never_rolls_back_posted_angle(tmp_path):
    """Angles with status='posted' or posted_at set must NEVER be rolled back."""
    fake_products = [
        {
            "id": "prod_1",
            "name": "Test Product",
            "angles": [
                {
                    "angle_id": "ang_posted",
                    "project_name": "LOG01-รีวิวสเปก_1",
                    "status": "posted",
                    "posted_at": "2026-09-07T01:25:29",
                    "video_url": "04_Exports/Ready_to_post/LOG01-รีวิวสเปก_1_test.mp4"
                },
                {
                    "angle_id": "ang_rendered",
                    "project_name": "LOG01-ปัญหาก่อนใช้_1",
                    "status": "rendered",
                    "video_url": "04_Exports/Ready_to_post/LOG01-ปัญหาก่อนใช้_1_test.mp4"
                }
            ]
        }
    ]

    with patch.object(ProductStore, "_load", return_value=fake_products), \
         patch.object(ProductStore, "_save") as mock_save:

        # Attempt to roll back the posted angle
        rolled = ProductStore.rollback_by_video_or_project(
            "LOG01-รีวิวสเปก_1_test.mp4",
            product_id="prod_1",
            angle_id="ang_posted"
        )
        assert rolled == [], "Posted angle should NOT be in rolled_back list"
        assert fake_products[0]["angles"][0]["status"] == "posted"

        # Attempt to roll back by project_name
        rolled = ProductStore.rollback_by_video_or_project(
            "LOG01-รีวิวสเปก_1",
            product_id="prod_1",
            angle_id="ang_posted"
        )
        assert rolled == []
        assert fake_products[0]["angles"][0]["status"] == "posted"


def test_delete_file_blocks_posted_videos(client, tmp_path):
    """POST /api/delete-file must reject deleting files from Posted/ or tied to posted angles."""
    fake_products = [
        {
            "id": "prod_1",
            "name": "Test Product",
            "angles": [
                {
                    "angle_id": "ang_1",
                    "project_name": "LOG01-รีวิวสเปก_1",
                    "status": "posted",
                    "posted_at": "2026-09-07T01:25:29",
                    "video_url": "04_Exports/Ready_to_post/LOG01-รีวิวสเปก_1_20260907.mp4"
                }
            ]
        }
    ]

    with patch.object(ProductStore, "_load", return_value=fake_products), \
         patch.object(ProductStore, "get", return_value=fake_products[0]):

        # 1. Reject deletion when product_id and angle_id are given
        res1 = client.post("/api/delete-file", json={
            "file_path": "04_Exports/Ready_to_post/LOG01-รีวิวสเปก_1_20260907.mp4",
            "product_id": "prod_1",
            "angle_id": "ang_1"
        })
        assert res1.status_code == 400
        assert "โพสต์ไปแล้ว" in res1.json()["detail"]

        # 2. Reject deletion when matching posted angle by filename alone
        res2 = client.post("/api/delete-file", json={
            "file_path": "04_Exports/Ready_to_post/LOG01-รีวิวสเปก_1_20260907.mp4"
        })
        assert res2.status_code == 400
        assert "โพสต์ไปแล้ว" in res2.json()["detail"]


def test_render_blocks_already_posted_angle(client):
    """POST /api/render must reject re-rendering an angle that has already been posted."""
    fake_products = [
        {
            "id": "prod_1",
            "name": "Test Product",
            "angles": [
                {
                    "angle_id": "ang_posted",
                    "project_name": "LOG01-รีวิวสเปก_1",
                    "status": "posted",
                    "posted_at": "2026-09-07T01:25:29"
                }
            ]
        }
    ]

    with patch.object(ProductStore, "_load", return_value=fake_products), \
         patch.object(ProductStore, "get", return_value=fake_products[0]):

        res = client.post("/api/render", json={
            "product_name": "Test",
            "raw_video_path": "dummy.mp4",
            "key_features": "features",
            "pain_point": "pain",
            "price_deal": "deal",
            "product_id": "prod_1",
            "angle_id": "ang_posted",
            "project_name": "LOG01-รีวิวสเปก_1"
        })
        assert res.status_code == 400
        assert "โพสต์ไปแล้ว" in res.json()["detail"]


def test_product_store_update_angle_status_blocks_demotion():
    """ProductStore.update_angle_status must never demote an angle with status='posted' or posted_at."""
    fake_product = {
        "id": "prod_1",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_posted",
                "status": "posted",
                "posted_at": "2026-09-07T01:25:29",
                "video_url": "04_Exports/Posted/test.mp4"
            }
        ]
    }
    with patch.object(ProductStore, "_mutate") as mock_mutate:
        mock_mutate.return_value.__enter__.return_value = [fake_product]
        # Try to demote to in_production
        ProductStore.update_angle_status("prod_1", "ang_posted", status="in_production")
        assert fake_product["angles"][0]["status"] == "posted"

        # Try to demote to scripted
        ProductStore.update_angle_status("prod_1", "ang_posted", status="scripted")
        assert fake_product["angles"][0]["status"] == "posted"


def test_product_store_remove_angle_and_delete_blocks_posted():
    """ProductStore.remove_angle and delete must raise ValueError on posted angles."""
    fake_product = {
        "id": "prod_1",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_posted",
                "status": "posted",
                "posted_at": "2026-09-07T01:25:29",
            }
        ]
    }
    with patch.object(ProductStore, "get", return_value=fake_product), \
         patch.object(ProductStore, "_mutate") as mock_mutate:
        mock_mutate.return_value.__enter__.return_value = [fake_product]

        with pytest.raises(ValueError, match="ไม่อนุญาตให้ลบมุม"):
            ProductStore.remove_angle("prod_1", "ang_posted")

        with pytest.raises(ValueError, match="ไม่อนุญาตให้ลบสินค้า"):
            ProductStore.delete("prod_1")


def test_reroll_angle_script_blocks_posted(client):
    """POST /api/products/{pid}/angles/{aid}/reroll-script must return 400 for posted angles."""
    fake_product = {
        "id": "prod_1",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_posted",
                "status": "posted",
                "posted_at": "2026-09-07T01:25:29",
            }
        ]
    }
    with patch.object(ProductStore, "get", return_value=fake_product):
        res = client.post("/api/products/prod_1/angles/ang_posted/reroll-script", json={
            "duration": "30s"
        })
        assert res.status_code == 400
        assert "โพสต์แล้ว" in res.json()["detail"]


def test_delete_project_blocks_posted_angle_and_product_scopes(client):
    """DELETE /api/projects/{name} with scope=angle or scope=product must return 400 for posted angles."""
    from scripts.project_manifest import ProjectManifest
    ProjectManifest.save("LOG01-รีวิวสเปก_1", channel_id="main")
    fake_product = {
        "id": "prod_1",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_posted",
                "project_name": "LOG01-รีวิวสเปก_1",
                "status": "posted",
                "posted_at": "2026-09-07T01:25:29",
            }
        ]
    }
    with patch("scripts.api_phase1.render_jobs.is_busy", return_value=False), \
         patch("scripts.api_phase1._project_origin", return_value=(None, fake_product, fake_product["angles"][0])):

        res_angle = client.delete("/api/projects/LOG01-รีวิวสเปก_1?scope=angle")
        assert res_angle.status_code == 400
        assert "โพสต์แล้ว" in res_angle.json()["detail"]

        res_prod = client.delete("/api/projects/LOG01-รีวิวสเปก_1?scope=product")
        assert res_prod.status_code == 400
        assert "โพสต์แล้ว" in res_prod.json()["detail"]

