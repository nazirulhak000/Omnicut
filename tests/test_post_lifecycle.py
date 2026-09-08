"""Regression contracts for export version and posting lifecycle behavior."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts import api_exports, api_videos, export_registry, media_service
from scripts.product_store import ProductStore
from scripts import product_store as product_store_module


def _patch_export_roots(monkeypatch, tmp_path):
    ready = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    ready.mkdir(parents=True)
    posted.mkdir(parents=True)
    covers.mkdir(parents=True)
    monkeypatch.setattr(api_exports, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_exports, "EXPORTS_DIR", ready)
    monkeypatch.setattr(api_exports, "POSTED_DIR", posted)
    monkeypatch.setattr(api_exports, "COVERS_DIR", covers)
    monkeypatch.setattr(media_service, "BASE_DIR", tmp_path)
    monkeypatch.setattr(media_service, "COVERS_DIR", covers)
    monkeypatch.setattr(api_videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(product_store_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(product_store_module, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")
    return ready, posted


def test_old_export_version_is_deletable_when_another_version_was_posted(monkeypatch, tmp_path):
    """Posting one version must not lock a different MP4 of the same angle."""
    ready, _ = _patch_export_roots(monkeypatch, tmp_path)
    old_file = ready / "DEMO01-review_1_20260908_110000.mp4"
    old_file.write_bytes(b"old version")
    monkeypatch.setattr(ProductStore, "_load", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": "04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4",
        }],
    }])
    monkeypatch.setattr(ProductStore, "rollback_by_video_or_project", lambda *args, **kwargs: [])

    response = TestClient(app).post("/api/delete-file", json={
        "file_path": "04_Exports/Ready_to_post/DEMO01-review_1_20260908_110000.mp4",
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 200, response.text
    assert not old_file.exists()


def test_exact_posted_export_version_remains_undeletable(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    posted_file = posted / "DEMO01-review_1_20260908_120000.mp4"
    posted_file.write_bytes(b"posted version")
    monkeypatch.setattr(ProductStore, "_load", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": "04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4",
        }],
    }])

    response = TestClient(app).post("/api/delete-file", json={
        "file_path": "04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4",
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 400
    assert "โพสต์ไปแล้ว" in response.json()["detail"]
    assert not ready.joinpath("DEMO01-review_1_20260908_120000.mp4").exists()


def test_ready_duplicate_of_posted_filename_is_deletable(monkeypatch, tmp_path):
    """A stale Ready copy of the posted filename is the old removable copy."""
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    filename = "DEMO01-review_1_20260908_120000.mp4"
    ready.joinpath(filename).write_bytes(b"duplicate ready copy")
    posted.joinpath(filename).write_bytes(b"duplicate ready copy")
    monkeypatch.setattr(ProductStore, "_load", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": f"04_Exports/Ready_to_post/{filename}",
        }],
    }])
    monkeypatch.setattr(ProductStore, "rollback_by_video_or_project", lambda *args, **kwargs: [])

    response = TestClient(app).post("/api/delete-file", json={
        "file_path": f"04_Exports/Ready_to_post/{filename}",
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 200, response.text
    assert not ready.joinpath(filename).exists()
    assert posted.joinpath(filename).exists()


def test_export_posted_flag_applies_only_to_the_physical_posted_version(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    old_file = ready / "DEMO01-review_1_20260908_110000.mp4"
    posted_file = posted / "DEMO01-review_1_20260908_120000.mp4"
    old_file.write_bytes(b"old version")
    posted_file.write_bytes(b"posted version")
    monkeypatch.setattr(ProductStore, "get_all", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": "04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4",
        }],
    }])

    result = api_exports.list_exports()["exports"]
    by_path = {item["rel_path"]: item for item in result}

    assert by_path["04_Exports/Ready_to_post/DEMO01-review_1_20260908_110000.mp4"]["is_posted"] is False
    assert by_path["04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4"]["is_posted"] is True


def test_export_ready_duplicate_is_not_marked_as_posted(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    filename = "DEMO01-review_1_20260908_120000.mp4"
    ready.joinpath(filename).write_bytes(b"duplicate ready copy")
    posted.joinpath(filename).write_bytes(b"duplicate ready copy")
    monkeypatch.setattr(ProductStore, "get_all", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": f"04_Exports/Ready_to_post/{filename}",
        }],
    }])

    result = api_exports.list_exports()["exports"]
    by_path = {item["rel_path"]: item for item in result}

    assert by_path[f"04_Exports/Ready_to_post/{filename}"]["is_posted"] is False
    assert by_path[f"04_Exports/Posted/{filename}"]["is_posted"] is True
    assert by_path[f"04_Exports/Ready_to_post/{filename}"]["is_latest"] is False
    assert by_path[f"04_Exports/Ready_to_post/{filename}"]["is_duplicate_copy"] is True
    assert by_path[f"04_Exports/Posted/{filename}"]["is_latest"] is True


def test_mark_posted_is_idempotent_when_posted_destination_already_exists(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    destination = posted / source.name
    source.write_bytes(b"same export")
    destination.write_bytes(b"same export")
    monkeypatch.setattr(api_exports.ProductStore, "update_angle_status", lambda **kwargs: {"id": "product-1"})
    monkeypatch.setattr(api_exports, "_mark_scheduled_queue_item_posted", lambda *args: None)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/exports/mark-posted", json={
        "file_path": "04_Exports/Ready_to_post/DEMO01-review_1_20260908_120000.mp4",
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 200, response.text
    assert destination.read_bytes() == b"same export"
    assert not source.exists()


def test_same_angle_versions_get_distinct_export_ids(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    old_file = ready / "DEMO01-review_1_20260908_110000.mp4"
    posted_file = posted / "DEMO01-review_1_20260908_120000.mp4"
    old_file.write_bytes(b"old version")
    posted_file.write_bytes(b"posted version")
    monkeypatch.setattr(ProductStore, "get_all", lambda: [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "posted",
            "posted_at": "2026-09-08T12:00:00",
            "video_url": "04_Exports/Posted/DEMO01-review_1_20260908_120000.mp4",
        }],
    }])

    result = api_exports.list_exports()["exports"]
    ids = {item["export_id"] for item in result}

    assert len(ids) == 2
    assert all(item["export_id"] for item in result)


def test_registry_ids_are_authoritative_over_filename_matching(monkeypatch, tmp_path):
    ready, _ = _patch_export_roots(monkeypatch, tmp_path)
    shared = ready / "shared_render.mp4"
    shared.write_bytes(b"render")
    monkeypatch.setattr(ProductStore, "get_all", lambda: [
        {
            "id": "product-name-match",
            "angles": [{
                "angle_id": "review",
                "project_name": "shared_render",
                "video_url": "04_Exports/Ready_to_post/shared_render.mp4",
                "status": "rendered",
            }],
        },
        {
            "id": "product-registry-match",
            "angles": [{
                "angle_id": "unboxing",
                "project_name": "other_project",
                "status": "rendered",
            }],
        },
    ])
    record = export_registry.ExportRegistry.ensure(
        shared,
        product_id="product-registry-match",
        angle_id="unboxing",
        project_name="other_project",
    )

    result = api_exports.list_exports()["exports"]

    assert result[0]["export_id"] == record["id"]
    assert result[0]["product_id"] == "product-registry-match"
    assert result[0]["angle_id"] == "unboxing"


def test_export_id_cannot_be_used_against_a_different_path(monkeypatch, tmp_path):
    ready, _ = _patch_export_roots(monkeypatch, tmp_path)
    first = ready / "DEMO01-review_1_20260908_110000.mp4"
    second = ready / "DEMO01-review_1_20260908_120000.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    record = export_registry.ExportRegistry.ensure(first, product_id="product-1", angle_id="review")
    monkeypatch.setattr(ProductStore, "rollback_by_video_or_project", lambda *args, **kwargs: [])

    response = TestClient(app).post("/api/delete-file", json={
        "file_path": f"04_Exports/Ready_to_post/{second.name}",
        "export_id": record["id"],
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 409
    assert second.exists()


def test_mark_posted_updates_the_same_export_id(monkeypatch, tmp_path):
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    source.write_bytes(b"same export")
    record = export_registry.ExportRegistry.ensure(source, product_id="product-1", angle_id="review")
    monkeypatch.setattr(api_exports.ProductStore, "update_angle_status", lambda **kwargs: {"id": "product-1"})
    monkeypatch.setattr(api_exports, "_mark_scheduled_queue_item_posted", lambda *args: None)

    response = TestClient(app).post("/api/exports/mark-posted", json={
        "file_path": f"04_Exports/Ready_to_post/{source.name}",
        "export_id": record["id"],
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 200, response.text
    moved = export_registry.ExportRegistry.get(record["id"])
    assert moved["id"] == record["id"]
    assert moved["status"] == "posted"
    assert moved["path"] == f"04_Exports/Posted/{source.name}"
    assert (posted / source.name).exists()


def test_reconcile_binds_posted_copy_and_id_when_ready_copy_is_stale(monkeypatch, tmp_path):
    """A legacy Ready/Posted duplicate must resolve to the Posted proof."""
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    projects = tmp_path / "03_Projects" / "DEMO01-review_1"
    projects.mkdir(parents=True)
    filename = "DEMO01-review_1_20260908_120000.mp4"
    ready_file = ready / filename
    posted_file = posted / filename
    ready_file.write_bytes(b"same export")
    posted_file.write_bytes(b"same export")
    (projects / "project.json").write_text(json.dumps({
        "project_name": "DEMO01-review_1",
        "render_params": {"product_id": "product-1", "angle_id": "review"},
        "artifacts": {"mp4_video": {"path": f"04_Exports/Ready_to_post/{filename}"}},
    }), encoding="utf-8")
    ready_record = export_registry.ExportRegistry.ensure(
        ready_file, product_id="product-1", angle_id="review", status="rendered",
    )
    posted_record = export_registry.ExportRegistry.ensure(
        posted_file, product_id="product-1", angle_id="review", status="posted",
    )
    products = [{
        "id": "product-1",
        "angles": [{
            "angle_id": "review",
            "project_name": "DEMO01-review_1",
            "status": "rendered",
            "video_url": f"04_Exports/Ready_to_post/{filename}",
        }],
    }]

    assert ProductStore._reconcile_into(
        products,
        tmp_path / "03_Projects",
        ready,
        posted,
    ) is True
    angle = products[0]["angles"][0]
    assert angle["video_url"] == f"04_Exports/Posted/{filename}"
    assert angle["export_id"] == posted_record["id"]
    assert angle["export_id"] != ready_record["id"]
