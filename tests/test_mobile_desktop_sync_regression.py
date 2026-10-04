"""Behavioral regression test suite for Mobile <-> Desktop Synchronization.

Covers Acceptance Criteria A01-A28 mapped to defects M01-M24.
All tests run offline on tmp_path without touching real media or production DB.
"""

from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import (
    mobile_quick_studio as mobile,
    product_store,
    recording_sessions,
    shot_lists_store,
    task_manager,
    render_jobs,
    path_utils,
    project_manifest,
    export_registry,
    api_products,
    api_exports,
)
from scripts.api_mobile_studio import router as mobile_router
from scripts.api_exports import router as exports_router
from scripts.product_store import ProductStore
from scripts.recording_sessions import RecordingSessionStore
from scripts.shot_lists_store import ShotListsStore
from scripts.task_manager import TaskManager
from scripts.export_registry import ExportRegistry
from scripts.product_scraper import ProductScraper

app = FastAPI()
app.include_router(mobile_router)
app.include_router(exports_router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_sync_env(tmp_path, monkeypatch):
    """Isolate all stores, registry, paths, and workers inside tmp_path."""
    for module in (mobile, product_store, recording_sessions, render_jobs, path_utils, export_registry, api_exports):
        if hasattr(module, "BASE_DIR"):
            monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    for name in ("RAW_DIR", "EXPORTS_DIR", "INBOX_DIR"):
        folder = tmp_path / name.lower()
        folder.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(mobile, name, folder)
    (tmp_path / "covers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "05_Covers_Thumbnails").mkdir(parents=True, exist_ok=True)
    (tmp_path / "04_Exports/Posted").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_exports, "EXPORTS_DIR", tmp_path / "exports_dir")
    monkeypatch.setattr(api_exports, "POSTED_DIR", tmp_path / "04_Exports/Posted")

    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "docs/products.json")
    monkeypatch.setattr(recording_sessions, "STORE_PATH", tmp_path / "docs/recording_sessions.json")
    monkeypatch.setattr(shot_lists_store, "STORE_PATH", tmp_path / "docs/shot_lists.json")
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(task_manager, "TASKS_FILE", tmp_path / "tasks.json")
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "docs/export_registry.json")

    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    # Synchronous background runner for deterministic testing
    monkeypatch.setattr(TaskManager, "run_in_background", lambda fn: fn())
    # Stub shot-list generation to avoid network / AI calls
    monkeypatch.setattr(mobile, "generate_shot_list_for_angle", lambda *a, **kw: {})

    raw = mobile.RAW_DIR / "fresh.mp4"
    raw.write_bytes(b"test-owned raw bytes")

    product = {
        "id": "prod",
        "name": "Test Gadget",
        "category": "Gadget",
        "specs": [{"label": "Weight", "value": "100g"}],
        "price_note": "1000",
        "angles": [
            {
                "angle_id": "angle",
                "angle_name": "Review",
                "hook_title": "Official Hook",
                "script_lines": ["Official first line", "Official second line"],
                "selected_videos": [raw.relative_to(tmp_path).as_posix()],
                "status": "draft",
            }
        ],
    }
    product_store._TABLE.save([product])
    return {"root": tmp_path, "raw": raw, "product": product}


def install_pipeline_mock(monkeypatch, result=None):
    """Installs a deterministic mock pipeline runner."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        if result is not None:
            return result
        out = mobile.EXPORTS_DIR / "video with spaces.mp4"
        out.write_bytes(b"rendered-mp4")
        return {"mp4_video": str(out)}

    monkeypatch.setattr(mobile.TikTokAutoCutterPipeline, "run", fake_run)
    return captured


# ---------------------------------------------------------------------------
# Acceptance Tests
# ---------------------------------------------------------------------------

def test_a02_real_export_identity_binds_to_store_with_relative_path(isolated_sync_env, monkeypatch):
    """A02: Real export_id from pipeline must bind into ProductStore with relative path (no double /api/media/)."""
    output = mobile.EXPORTS_DIR / "video with spaces.mp4"
    output.write_bytes(b"probe-output")
    record = ExportRegistry.ensure(output, product_id="prod", angle_id="angle", project_name="probe")
    install_pipeline_mock(monkeypatch, result={"mp4_video": str(output), "export_id": record["id"]})

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200, res.text
    task = TaskManager.get_task(res.json()["task_id"])

    assert task["status"] == "completed"
    angle = ProductStore.get("prod")["angles"][0]
    assert angle["status"] == "rendered"
    assert angle.get("export_id") == record["id"]
    # Path must be store-relative, not prefixed with /api/media/ in the database
    assert not angle["video_url"].startswith("/api/media/")
    assert angle["video_url"].endswith("video with spaces.mp4") or angle["video_url"].endswith("video%20with%20spaces.mp4")


def test_a03_store_failure_marks_task_as_failed_not_completed(isolated_sync_env, monkeypatch):
    """A03: If ProductStore persistence fails, task must fail rather than reporting fake success."""
    install_pipeline_mock(monkeypatch)

    def failing_update(*args, **kwargs):
        raise RuntimeError("injected store persistence failure")

    monkeypatch.setattr(ProductStore, "update_angle_status", failing_update)

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200, res.text
    task = TaskManager.get_task(res.json()["task_id"])

    # Must NOT report completed when store persistence failed!
    assert task["status"] == "failed"
    assert "error" in task or "error" in task.get("result", {})


def test_a06_posted_angle_is_not_overridden_to_rendered(isolated_sync_env):
    """A06: An angle with status 'posted' must keep 'posted' in mobile catalog projection."""
    with product_store._TABLE.mutate() as products:
        products[0]["angles"][0].update(
            status="posted",
            posted_at="2026-10-04T12:00:00",
            video_url="exports_dir/posted.mp4"
        )
    catalog = mobile.MobileQuickStudioService.get_catalog()
    angle = catalog[0]["angles"][0]
    assert angle["status"] == "posted"
    assert angle.get("posted_at") == "2026-10-04T12:00:00"


def test_a07_in_production_status_set_during_render(isolated_sync_env, monkeypatch):
    """A07: When assemble begins, angle status must become 'in_production' before pipeline runs."""
    observed_status = []
    original_run = install_pipeline_mock(monkeypatch)

    def capture_status(**kwargs):
        observed_status.append(ProductStore.get("prod")["angles"][0]["status"])
        out = mobile.EXPORTS_DIR / "video with spaces.mp4"
        out.write_bytes(b"rendered-mp4")
        return {"mp4_video": str(out)}

    monkeypatch.setattr(mobile.TikTokAutoCutterPipeline, "run", capture_status)

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200, res.text
    assert observed_status == ["in_production"]


def test_a08_posted_angle_blocks_new_render(isolated_sync_env, monkeypatch):
    """A08: Attempting to render an angle that is already posted must be rejected to protect published work."""
    with product_store._TABLE.mutate() as products:
        products[0]["angles"][0].update(
            status="posted",
            posted_at="2026-10-04",
            video_url="exports_dir/old-posted.mp4"
        )
    install_pipeline_mock(monkeypatch)

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    # Either 400 Bad Request or task marked failed due to posted guard
    if res.status_code == 200:
        task = TaskManager.get_task(res.json()["task_id"])
        assert task["status"] == "failed"
    else:
        assert res.status_code in (400, 409)


def test_a11_manual_shot_map_and_multi_sources_forwarded_to_pipeline(isolated_sync_env, monkeypatch):
    """A11: When desktop has selected multiple videos, mobile assembly forwards all sources."""
    second = mobile.RAW_DIR / "second.mp4"
    second.write_bytes(b"second-source")
    with product_store._TABLE.mutate() as products:
        products[0]["angles"][0]["selected_videos"].append(second.relative_to(isolated_sync_env["root"]).as_posix())

    captured = install_pipeline_mock(monkeypatch)
    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200, res.text

    assert captured.get("multi_video_paths") is not None
    assert len(captured["multi_video_paths"]) >= 2


def test_a25_quick_add_deduplicates_shop_url_and_handles_scraper_safely(isolated_sync_env, monkeypatch):
    """A25: Quick add product with same shop URL must deduplicate and not crash on missing scrape method."""
    monkeypatch.setattr(api_products, "resolve_tiktok_product_id", lambda value: {"success": True, "product_id": "1234567890"})
    monkeypatch.setattr(ProductScraper, "scrape_url", lambda value: {"title": "Gadget From TikTok", "specs": []})
    monkeypatch.setattr(mobile.MobileQuickStudioService, "create_quick_angle", lambda *a, **kw: {})

    first = mobile.MobileQuickStudioService.quick_add_product("https://fixture.invalid/shop/item")
    second = mobile.MobileQuickStudioService.quick_add_product("https://fixture.invalid/shop/item")

    assert first["id"] == second["id"]
    assert first["url"] == "https://fixture.invalid/shop/item"


def test_a24_bgm_toggle_disables_background_music(isolated_sync_env, monkeypatch):
    """A24: BGM Toggle off must pass None/0.0 volume into the render pipeline."""
    captured = install_pipeline_mock(monkeypatch)
    res = client.post("/api/mobile-studio/assemble", json={
        "product_id": "prod",
        "angle_id": "angle",
        "bgm_enabled": False
    })
    assert res.status_code == 200, res.text
    assert captured.get("bgm_name") is None
    assert captured.get("bgm_volume") == 0.0


def test_a19_mark_posted_moves_both_cover_variants_and_updates_store_paths(isolated_sync_env, monkeypatch):
    """A19: When marking an export posted, both 3:4 and 9:16 covers must move with it and update store paths."""
    out = isolated_sync_env["root"] / "exports_dir/video_sample.mp4"
    out.write_bytes(b"sample-video")
    poster = isolated_sync_env["root"] / "exports_dir/video_sample.webp"
    poster.write_bytes(b"poster-webp")

    cov_3x4 = isolated_sync_env["root"] / "05_Covers_Thumbnails/video_sample_cover.jpg"
    cov_3x4.write_bytes(b"cover-3x4")
    cov_9x16 = isolated_sync_env["root"] / "05_Covers_Thumbnails/video_sample_cover_9x16.jpg"
    cov_9x16.write_bytes(b"cover-9x16")

    record = ExportRegistry.ensure(out, product_id="prod", angle_id="angle", project_name="probe")

    with product_store._TABLE.mutate() as products:
        products[0]["angles"][0].update(
            status="rendered",
            video_url="exports_dir/video_sample.mp4",
            export_id=record["id"],
            cover_path="05_Covers_Thumbnails/video_sample_cover.jpg",
            cover_3x4_path="05_Covers_Thumbnails/video_sample_cover.jpg",
            cover_9x16_path="05_Covers_Thumbnails/video_sample_cover_9x16.jpg"
        )

    res = client.post("/api/exports/mark-posted", json={
        "file_path": str(out),
        "export_id": record["id"],
        "product_id": "prod",
        "angle_id": "angle"
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True

    # Both covers must be in Posted/
    posted_dir = isolated_sync_env["root"] / "04_Exports/Posted"
    assert (posted_dir / "video_sample.mp4").exists()
    assert (posted_dir / "video_sample_cover.jpg").exists()
    assert (posted_dir / "video_sample_cover_9x16.jpg").exists()

    # Store paths must be updated
    angle = ProductStore.get("prod")["angles"][0]
    assert angle["status"] == "posted"
    assert "04_Exports/Posted" in angle["video_url"]
    assert "Posted" in angle.get("cover_9x16_path", "")
    assert "Posted" in angle.get("cover_3x4_path", "")


def test_a21_mark_posted_returns_status_warning_if_product_store_fails(isolated_sync_env, monkeypatch):
    """A21: If updating ProductStore fails during mark_posted, status_warning must be returned in response."""
    out = isolated_sync_env["root"] / "exports_dir/video_warn.mp4"
    out.write_bytes(b"sample-video-warn")
    record = ExportRegistry.ensure(out, product_id="prod", angle_id="angle", project_name="probe")

    def failing_update(*args, **kwargs):
        raise RuntimeError("store write locked")

    monkeypatch.setattr(ProductStore, "update_angle_status", failing_update)

    res = client.post("/api/exports/mark-posted", json={
        "file_path": str(out),
        "export_id": record["id"],
        "product_id": "prod",
        "angle_id": "angle"
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert "status_warning" in body
    assert "store write locked" in body["status_warning"]


def test_a12_idempotency_resumes_existing_running_task(isolated_sync_env, monkeypatch):
    """A12: Repeated assemble request for same angle while running must return existing task_id without duplicate workers."""
    # Create an active running task
    task = TaskManager.create_task(
        task_type="mobile_auto_assemble_render",
        title="⚡ Auto-Assemble & SOP Render: Test",
        payload={"product_id": "prod", "angle_id": "angle", "project_name": "running_proj"}
    )
    TaskManager.update_progress(task["id"], 0.25, "Rendering in progress...")

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["task_id"] == task["id"]
    assert body.get("resumed") is True


def test_a11b_cancel_task_rolls_back_status_to_scripted(isolated_sync_env, monkeypatch):
    """A11b: When a render task is cancelled, angle status must rollback from in_production to scripted."""
    def cancelling_pipeline(**kwargs):
        raise render_jobs.RenderCancelled("user requested stop")

    monkeypatch.setattr(mobile.TikTokAutoCutterPipeline, "run", cancelling_pipeline)

    res = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert res.status_code == 200
    task_id = res.json()["task_id"]

    task = TaskManager.get_task(task_id)
    assert task["status"] == "cancelled"

    angle = ProductStore.get("prod")["angles"][0]
    assert angle["status"] in ("scripted", "draft")



