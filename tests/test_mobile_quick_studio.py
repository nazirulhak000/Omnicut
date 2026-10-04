"""Mobile integration contracts with temporary stores and an offline pipeline."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import mobile_quick_studio as mobile, product_store, recording_sessions, shot_lists_store, task_manager, render_jobs, path_utils, project_manifest
from scripts.api_mobile_studio import router
from scripts.pipeline_context import PipelineContext
from scripts.product_store import ProductStore
from scripts.recording_sessions import RecordingSessionStore
from scripts.shot_lists_store import ShotListsStore
from scripts.task_manager import TaskManager

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_mobile(tmp_path, monkeypatch):
    for module in (mobile, product_store, recording_sessions, render_jobs, path_utils):
        if hasattr(module, "BASE_DIR"):
            monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    for name in ("RAW_DIR", "EXPORTS_DIR", "INBOX_DIR"):
        folder = tmp_path / name.lower()
        folder.mkdir()
        monkeypatch.setattr(mobile, name, folder)
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "docs/products.json")
    monkeypatch.setattr(recording_sessions, "STORE_PATH", tmp_path / "docs/recording_sessions.json")
    monkeypatch.setattr(shot_lists_store, "STORE_PATH", tmp_path / "docs/shot_lists.json")
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(task_manager, "TASKS_FILE", tmp_path / "tasks.json")
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    # No daemon threads can escape the fixture's cleanup / monkeypatch lifetime.
    monkeypatch.setattr(TaskManager, "run_in_background", lambda fn: fn())
    raw = mobile.RAW_DIR / "fresh.mp4"
    raw.write_bytes(b"test-owned raw bytes")
    product = {
        "id": "prod", "name": "Test Gadget", "category": "Gadget",
        "specs": [{"label": "Weight", "value": "100g"}], "price_note": "1000",
        "angles": [{"angle_id": "angle", "angle_name": "Review", "hook_title": "Official Hook",
                    "script_lines": ["Official first line", "Official second line"],
                    "selected_videos": [raw.relative_to(tmp_path).as_posix()], "status": "draft"}],
    }
    product_store._TABLE.save([product])
    return {"root": tmp_path, "raw": raw, "product": product}


def shot_plan(batch=1):
    return ShotListsStore.upsert({
        "product_id": "prod", "angle_id": "angle", "batch": batch,
        "shot_list": [{"beat_index": 0, "role": "hook", "start": 0, "end": 1, "planned_duration": 1}],
    }, batch=batch)


def install_pipeline(monkeypatch, *, result=None, create_output=True):
    captured = {}
    def run(**kwargs):
        assert render_jobs.is_busy(), "Mobile must share the desktop render semaphore"
        captured.update(kwargs)
        PipelineContext(product_name="Test", raw_video_path="", progress_callback=kwargs["progress_callback"]).notify("halfway", 0.5)
        if result is not None:
            return result
        output = mobile.EXPORTS_DIR / "video with spaces.mp4"
        if create_output:
            output.write_bytes(b"offline-render-result")
        return {"mp4_video": str(output), "mix_degraded": True, "mix_degraded_reason": "mock mix fallback"}
    monkeypatch.setattr(mobile.TikTokAutoCutterPipeline, "run", run)
    return captured


def test_catalog_real_product_shape_and_latest_session(isolated_mobile):
    shot_plan()
    session = RecordingSessionStore.create("prod", "angle")
    data = client.get("/api/mobile-studio/catalog").json()
    assert data["total"] == 1
    item = data["catalog"][0]
    assert item["price"] == "1000"
    angle = item["angles"][0]
    assert angle["id"] == "angle"
    assert angle["script_full"] == "Official first line\nOfficial second line"
    assert angle["attached_raw"] == "raw_dir/fresh.mp4"
    assert angle["has_session"] and angle["session_id"] == session["id"]


def test_cached_batch_one_session_resumes_without_tts(isolated_mobile, monkeypatch):
    shot_plan()
    monkeypatch.setattr(mobile, "generate_shot_list_for_angle", lambda *args: pytest.fail("cached plan billed twice"))
    first = client.post("/api/mobile-studio/session", json={"product_id": "prod", "angle_id": "angle"})
    second = client.post("/api/mobile-studio/session", json={"product_id": "prod", "angle_id": "angle"})
    assert first.status_code == second.status_code == 200
    assert first.json()["session"]["id"] == second.json()["session"]["id"]


def test_fresh_session_uses_existing_real_timing_builder(isolated_mobile, monkeypatch):
    calls = []
    def generate(product_id, angle_id):
        calls.append((product_id, angle_id))
        shot_plan()
    monkeypatch.setattr(mobile, "generate_shot_list_for_angle", generate)
    response = client.post("/api/mobile-studio/session", json={"product_id": "prod", "angle_id": "angle"})
    assert response.status_code == 200
    assert calls == [("prod", "angle")]
    assert response.json()["session"]["segments"][0]["planned_duration"] == 1


def test_batch_two_is_never_substituted_for_default_plan(isolated_mobile):
    shot_plan(batch=2)
    assert ShotListsStore.get("prod", "angle") is None
    assert ShotListsStore.get("prod", "angle", batch=2)["batch"] == 2
    shot_plan(batch=1)
    assert ShotListsStore.get("prod", "angle")["batch"] == 1
    assert ShotListsStore.get("prod", "angle", batch=2)["batch"] == 2


def test_legacy_shot_list_takes_priority(isolated_mobile):
    shot_plan()
    legacy = {"id": "prod:angle", "product_id": "prod", "angle_id": "angle", "shot_list": [{"legacy": True}]}
    ShotListsStore.upsert(legacy)
    assert ShotListsStore.get("prod", "angle")["shot_list"] == [{"legacy": True}]


@pytest.mark.parametrize("endpoint,payload", [
    ("session", {"product_id": "unknown", "angle_id": "angle"}),
    ("session", {"product_id": "prod", "angle_id": "unknown"}),
    ("assemble", {"product_id": "unknown", "angle_id": "angle"}),
    ("assemble", {"product_id": "prod", "angle_id": "unknown"}),
])
def test_invalid_ids_are_client_errors(isolated_mobile, endpoint, payload):
    assert client.post(f"/api/mobile-studio/{endpoint}", json=payload).status_code == 400
    assert not TaskManager._tasks


def test_assemble_real_output_progress_metadata_and_storage(isolated_mobile, monkeypatch):
    kwargs = install_pipeline(monkeypatch)
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert response.status_code == 200
    task = client.get(f"/api/mobile-studio/task/{response.json()['task_id']}").json()
    assert task["is_completed"] and not task["is_failed"]
    assert task["result"]["video_url"] == "/api/media/exports_dir/video%20with%20spaces.mp4"
    assert Path(task["result"]["video_path"]).is_file()
    assert task["result"]["mix_degraded"]
    assert any(log["msg"] == "halfway" and log["progress"] == 53 for log in task["task"]["logs"])
    assert kwargs["custom_script"] == "Official first line\nOfficial second line"
    assert kwargs["raw_video_path"] == str(isolated_mobile["raw"])
    assert kwargs["key_features"] == "Weight: 100g"
    assert kwargs["product_meta"]["id"] == "prod" and kwargs["angle_meta"]["angle_id"] == "angle"
    assert kwargs["cancel_event"] is not None
    assert ProductStore.get("prod")["angles"][0]["status"] == "rendered"


@pytest.mark.parametrize("mode", ["no_path", "missing_file", "empty_file", "outside_export"])
def test_false_render_success_is_rejected(isolated_mobile, monkeypatch, mode):
    path = mobile.EXPORTS_DIR / "bad.mp4"
    if mode == "empty_file":
        path.touch()
    if mode == "outside_export":
        path = isolated_mobile["raw"]
    result = {} if mode == "no_path" else {"mp4_video": str(path)}
    install_pipeline(monkeypatch, result=result)
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    task = client.get(f"/api/mobile-studio/task/{response.json()['task_id']}").json()
    assert task["is_failed"] and not task["is_completed"]
    assert ProductStore.get("prod")["angles"][0]["status"] == "draft"


def test_completed_recording_uses_fresh_clip_over_stale_attachment(isolated_mobile, monkeypatch):
    shot_plan()
    session = RecordingSessionStore.create("prod", "angle")
    fresh = mobile.RAW_DIR / "recorded.mp4"
    fresh.write_bytes(b"fresh")
    with recording_sessions._TABLE.mutate() as sessions:
        sessions[0].update(status="completed", raw_video_path=str(fresh))
    kwargs = install_pipeline(monkeypatch)
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle", "session_id": session["id"]})
    assert response.status_code == 200
    assert kwargs["raw_video_path"] == str(fresh)


def test_uploaded_session_finalizes_with_actual_raw_video_key(isolated_mobile, monkeypatch):
    shot_plan()
    session = RecordingSessionStore.create("prod", "angle")
    RecordingSessionStore.upload_segment(session["id"], 0, str(isolated_mobile["raw"]), 1)
    finalized = []
    def finalize(session_id):
        finalized.append(session_id)
        return {"raw_video_path": str(isolated_mobile["raw"])}
    monkeypatch.setattr(RecordingSessionStore, "finalize", finalize)
    kwargs = install_pipeline(monkeypatch)
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle", "session_id": session["id"]})
    assert response.status_code == 200
    assert finalized == [session["id"]]
    assert kwargs["raw_video_path"] == str(isolated_mobile["raw"])


def test_session_cannot_cross_product_or_angle(isolated_mobile):
    shot_plan()
    session = RecordingSessionStore.create("prod", "angle")
    with recording_sessions._TABLE.mutate() as sessions:
        sessions[0]["angle_id"] = "other-angle"
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle", "session_id": session["id"]})
    assert response.status_code == 400
    assert not TaskManager._tasks


@pytest.mark.parametrize("source", ["outside", "directory", "missing"])
def test_raw_source_is_validated_before_task(isolated_mobile, source):
    path = isolated_mobile["root"] / "secret.txt"
    if source == "outside":
        path.write_text("private", encoding="utf-8")
    elif source == "directory":
        path = mobile.RAW_DIR
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle", "custom_raw_video": str(path)})
    assert response.status_code == 400
    assert not TaskManager._tasks


def test_task_missing_and_cancelled_are_reported(isolated_mobile):
    assert client.get("/api/mobile-studio/task/unknown").status_code == 404
    task = TaskManager.create_task("mobile", "test")
    TaskManager.cancel_task(task["id"])
    data = client.get(f"/api/mobile-studio/task/{task['id']}").json()
    assert data["is_cancelled"] and not data["is_completed"]


def test_queued_cancellation_skips_pipeline(isolated_mobile, monkeypatch):
    def cancel_then_run(fn):
        task_id = next(iter(TaskManager._tasks))
        TaskManager.cancel_task(task_id)
        render_jobs.request_cancel(task_id)
        fn()
    monkeypatch.setattr(TaskManager, "run_in_background", cancel_then_run)
    monkeypatch.setattr(mobile.TikTokAutoCutterPipeline, "run", lambda **kwargs: pytest.fail("cancelled task rendered"))
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "prod", "angle_id": "angle"})
    assert TaskManager.get_task(response.json()["task_id"])["status"] == "cancelled"
    assert ProductStore.get("prod")["angles"][0]["status"] == "draft"


def test_empty_angles_product_allows_quick_angle_and_session(isolated_mobile):
    """When a product has no angles, quick-take creates a fallback angle and session without error."""
    # Create a product with empty angles
    p = ProductStore.add(name="No Angles Device", category="Gadget", angles=[])
    assert len(p.get("angles", [])) == 0

    # 1. Test /api/mobile-studio/quick-angle
    res = client.post("/api/mobile-studio/quick-angle", json={
        "product_id": p["id"],
        "title": "⚡ รีวิวสเปกแบบเรียลๆ",
        "script": "นี่คือคลิปรีวิวแบบเรียลๆ ครับ กดสั่งในตะกร้าได้เลย"
    })
    assert res.status_code == 200
    angle_data = res.json()["angle"]
    assert "quick_take" in angle_data["angle_id"]
    assert angle_data["hook_title"] == "⚡ รีวิวสเปกแบบเรียลๆ"

    # 2. Test /api/mobile-studio/session with quick_take
    session_res = client.post("/api/mobile-studio/session", json={
        "product_id": p["id"],
        "angle_id": "quick_take"
    })
    assert session_res.status_code == 200
    assert session_res.json()["success"] is True
    assert session_res.json()["session"]["product_id"] == p["id"]


def test_upload_mobile_video_endpoint(isolated_mobile):
    """Tests direct upload of camera roll video from mobile."""
    # Upload video to prod and angle
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + b"A" * 100
    files = {"file": ("my_phone_take.mp4", video_bytes, "video/mp4")}
    data = {"product_id": "prod", "angle_id": "angle"}
    res = client.post("/api/mobile-studio/upload-video", data=data, files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "01_Raw/prod/" in body["video_path"]

    # Verify attached to angle
    updated = ProductStore.get("prod")
    assert any("mobile_take_" in v for v in updated["angles"][0].get("selected_videos", []))


def test_quick_add_product_endpoint(isolated_mobile):
    """Tests creating product directly from mobile."""
    res = client.post("/api/mobile-studio/products/quick-add", json={
        "name_or_url": "เมาส์ไร้สายบลูทูธ AI"
    })
    assert res.status_code == 200
    prod = res.json()["product"]
    assert prod["name"] == "เมาส์ไร้สายบลูทูธ AI"
    # Should have 1 ready-to-record quick angle
    assert len(prod["angles"]) >= 1
    assert "quick_take" in prod["angles"][0]["angle_id"]


def test_catalog_enrichment_badges_and_footage_status(isolated_mobile):
    """Ensures /api/mobile-studio/catalog returns product counts and angle footage/render fields."""
    res = client.get("/api/mobile-studio/catalog")
    assert res.status_code == 200
    cat = res.json()["catalog"]
    assert len(cat) >= 1
    p = cat[0]
    assert "total_angles" in p
    assert "rendered_count" in p
    assert "footage_count" in p
    assert "product_status" in p
    assert p["product_status"] in ("completed", "in_progress", "not_started")

    ang = p["angles"][0]
    assert "is_rendered" in ang
    assert "has_footage" in ang
    assert "attached_raw_name" in ang
    assert "render_status" in ang
    assert ang["render_status"] in ("rendered", "ready_to_cut", "draft")
