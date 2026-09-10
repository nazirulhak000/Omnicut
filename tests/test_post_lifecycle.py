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


def test_mark_posted_persists_angle_status_after_moving_export(monkeypatch, tmp_path):
    """The real endpoint must update the angle, not only move the file.

    This deliberately does not stub ProductStore.update_angle_status.  The
    endpoint moves the export before writing the product record, so the
    regression catches a path-validation mismatch between the moved Posted
    path and the registry snapshot that still points at Ready_to_post.
    """
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    source.write_bytes(b"same export")
    record = export_registry.ExportRegistry.ensure(
        source, product_id="product-1", angle_id="review", status="rendered",
    )
    products_path = tmp_path / "_Docs" / "products.json"
    products_path.parent.mkdir(parents=True, exist_ok=True)
    products_path.write_text(json.dumps([{
        "id": "product-1",
        "name": "Demo Product",
        "angles": [{
            "angle_id": "review",
            "status": "rendered",
            "video_url": f"04_Exports/Ready_to_post/{source.name}",
            "export_id": record["id"],
        }],
    }]), encoding="utf-8")
    monkeypatch.setattr(api_exports, "_mark_scheduled_queue_item_posted", lambda *args: None)

    response = TestClient(app).post("/api/exports/mark-posted", json={
        "file_path": f"04_Exports/Ready_to_post/{source.name}",
        "export_id": record["id"],
        "product_id": "product-1",
        "angle_id": "review",
    })

    assert response.status_code == 200, response.text
    assert response.json().get("status_warning") is None, response.text
    saved = ProductStore._load()
    angle = saved[0]["angles"][0]
    assert angle["status"] == "posted"
    assert angle["video_url"] == f"04_Exports/Posted/{source.name}"
    assert angle["export_id"] == record["id"]
    assert angle.get("posted_at")
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


def test_move_or_reuse_posted_treats_a_concurrent_winner_as_success(monkeypatch, tmp_path):
    """Regression for a rapid-double-click 500 on the extension's mark-posted button.

    api_exports.mark_posted's handlers are sync `def`, so FastAPI genuinely
    runs two overlapping requests for the same clip on separate threads --
    not just in theory, this is what a fast double-click on the side panel's
    "mark posted" button produces in practice. Whichever request's
    shutil.move() runs second finds `source` already gone (the other request
    moved it) and used to raise a bare FileNotFoundError -- an unhandled
    exception FastAPI turns into a 500, while the file itself was already
    correctly posted by the winner. This reproduces that exact race
    deterministically: shutil.move is stubbed to simulate a concurrent
    winner completing the same move first, instead of relying on real OS
    thread timing (which would make this test flaky).
    """
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    source.write_bytes(b"same export")
    destination = posted / source.name

    def fake_move(src, dst):
        # Simulate a concurrent request's shutil.move() having already
        # completed this exact move by the time this thread's own call runs.
        source.unlink(missing_ok=True)
        raise FileNotFoundError(src)

    monkeypatch.setattr(api_exports.shutil, "move", fake_move)
    destination.write_bytes(b"same export")  # what the "winning" request left behind

    api_exports._move_or_reuse_posted(source, destination)  # must not raise

    assert destination.read_bytes() == b"same export"


def test_move_or_reuse_posted_still_errors_when_source_vanishes_for_another_reason(monkeypatch, tmp_path):
    """The FileNotFoundError recovery above must not swallow a genuine problem.

    If `source` disappears and `destination` was NEVER created by anyone,
    that is not the "a concurrent request already finished this" case --
    something else removed the file, and that should still surface as a
    clear error instead of being silently treated as success.
    """
    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    source.write_bytes(b"same export")
    destination = posted / source.name

    def fake_move(src, dst):
        source.unlink(missing_ok=True)
        raise FileNotFoundError(src)

    monkeypatch.setattr(api_exports.shutil, "move", fake_move)

    try:
        api_exports._move_or_reuse_posted(source, destination)
        assert False, "expected an HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    assert not destination.exists()


def test_mark_posted_concurrent_double_click_never_500s(monkeypatch, tmp_path):
    """End-to-end version of the race above, through the real HTTP endpoint.

    Fires two /api/exports/mark-posted requests for the same clip from two
    threads with a barrier so they overlap as tightly as the GIL allows.
    Whichever one loses the race must still resolve cleanly (200, treating
    the other's completed move as success) -- never a 500 -- and the clip
    must end up posted exactly once, not duplicated or left half-moved.
    """
    import threading

    ready, posted = _patch_export_roots(monkeypatch, tmp_path)
    source = ready / "DEMO01-review_1_20260908_120000.mp4"
    source.write_bytes(b"same export")
    record = export_registry.ExportRegistry.ensure(source, product_id="product-1", angle_id="review")
    monkeypatch.setattr(api_exports.ProductStore, "update_angle_status", lambda **kwargs: {"id": "product-1"})
    monkeypatch.setattr(api_exports, "_mark_scheduled_queue_item_posted", lambda *args: None)

    client = TestClient(app)
    payload = {
        "file_path": f"04_Exports/Ready_to_post/{source.name}",
        "export_id": record["id"],
        "product_id": "product-1",
        "angle_id": "review",
    }
    barrier = threading.Barrier(2)
    responses = [None, None]

    def fire(i):
        barrier.wait(timeout=5)
        responses[i] = client.post("/api/exports/mark-posted", json=payload)

    threads = [threading.Thread(target=fire, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    for res in responses:
        assert res is not None, "a request thread did not complete"
        assert res.status_code != 500, res.text

    moved = export_registry.ExportRegistry.get(record["id"])
    assert moved["status"] == "posted"
    assert (posted / source.name).exists()
    assert not source.exists()
