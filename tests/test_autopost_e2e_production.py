# -*- coding: utf-8 -*-
"""Round CLAUDE-AUTOPOST-E2E-FIXES-20261113, production/render findings.

C1  an angle reads "rendered" only after the sharpness pass and its cover
C2  the sharpness pass runs inside the render slot (editor render)
C3  replacing a file that is held open is retried; a final failure is
    recorded on the export and shown by the gallery listing
C4  a draft batch still queued after a restart is not queued a second time
C5  a chain that made some clips and failed others is flagged partial
C21 angle lookups stay inside one lot (batch)

Offline: temp storage (``isolated_storage``), no ffmpeg, no real render.
"""
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from scripts import api_phase1
from scripts import auto_sharpen
from scripts import batch_render
from scripts import production_chain
from scripts import product_store as ps
from scripts import render_jobs
from scripts import tiktok_enhancer
from scripts.export_registry import TIKTOK_SHARP_ERROR_FIELD, ExportRegistry
from tests.test_auto_sharpen import EXPORT_ID, CHANNEL, studio  # noqa: F401  (fixture)
from tests.test_auto_cover import _editor_render


# --- C3: retry, record, show -------------------------------------------------

def test_replace_retries_while_the_file_is_held_open(tmp_path, monkeypatch):
    src, dst = tmp_path / "a.partial.mp4", tmp_path / "a.mp4"
    src.write_bytes(b"new")
    dst.write_bytes(b"old")
    real_replace = tiktok_enhancer.os.replace
    calls = {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError("in use")
        return real_replace(a, b)

    monkeypatch.setattr(tiktok_enhancer.os, "replace", flaky)
    waits = []
    tiktok_enhancer.replace_with_retry(src, dst, delays=(0.5, 1.0, 1.5), sleep=waits.append)

    assert dst.read_bytes() == b"new"
    assert waits == [0.5, 1.0]


def test_replace_gives_up_after_the_last_retry(tmp_path, monkeypatch):
    src, dst = tmp_path / "a.partial.mp4", tmp_path / "a.mp4"
    src.write_bytes(b"new")
    monkeypatch.setattr(tiktok_enhancer.os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError("in use")))
    waits = []
    with pytest.raises(PermissionError):
        tiktok_enhancer.replace_with_retry(src, dst, delays=(0.5, 1.0), sleep=waits.append)
    assert waits == [0.5, 1.0]


def test_failed_sharpen_is_recorded_and_cleared_by_a_later_success(studio, monkeypatch):  # noqa: F811
    def locked(input_path, output_path=None, **kwargs):
        raise PermissionError("file in use")

    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok", locked)
    outcome = studio.run()
    assert outcome["status"] == "failed"
    error = studio.record()[TIKTOK_SHARP_ERROR_FIELD]
    assert "เปิดค้าง" in error["reason"] and error["at"]

    def ok(input_path, output_path=None, **kwargs):
        output_path.write_bytes(b"sharp:" + input_path.read_bytes())
        return output_path

    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok", ok)
    assert studio.run()["status"] == "sharpened"
    assert TIKTOK_SHARP_ERROR_FIELD not in studio.record()


def test_gallery_listing_says_why_a_clip_is_not_sharp(isolated_storage, monkeypatch):
    from scripts import api_exports

    monkeypatch.delenv(auto_sharpen.ENV_SWITCH, raising=False)
    exports_dir = api_exports.EXPORTS_DIR
    assert isolated_storage in exports_dir.parents  # never the real exports folder
    exports_dir.mkdir(parents=True, exist_ok=True)
    name = "20261113_locked_hook_v1.mp4"
    clip = exports_dir / name
    clip.write_bytes(b"rendered")
    export_id = ExportRegistry.ensure(str(clip), status="rendered", channel_id=CHANNEL)["id"]

    def listed():
        return next(item for item in api_exports.list_exports()["exports"] if item["name"] == name)

    assert "tiktok_sharpen_error" not in listed()
    ExportRegistry.set_tiktok_sharpen_error(
        export_id, {"reason": "ไฟล์ถูกเปิดค้างอยู่", "at": "2026-11-13T10:00:00+07:00"}, channel_id=CHANNEL)
    row = listed()
    assert row["tiktok_enhanced"] is False
    assert row["tiktok_sharpen_error"] == "ไฟล์ถูกเปิดค้างอยู่"


# --- C1 / C2: order of the render tail ---------------------------------------

@pytest.fixture
def render_events(monkeypatch):
    events = []

    def sharpen(export_id, **kwargs):
        events.append("sharpen")
        return {"status": "sharpened"}

    def cover(export_id, **kwargs):
        events.append(("cover", kwargs.get("batch")))
        return {"status": "created"}

    real_status = ps.ProductStore.update_angle_status

    def status(product_id, angle_id, value, *args, **kwargs):
        events.append(("status", value, kwargs.get("batch")))
        return real_status(product_id, angle_id, value, *args, **kwargs)

    real_slot = render_jobs.render_slot

    @contextmanager
    def slot(job_id, *args, **kwargs):
        with real_slot(job_id, *args, **kwargs):
            events.append("slot_in")
            yield
            events.append("slot_out")

    for module in (api_phase1, batch_render):
        monkeypatch.setattr(module, "ensure_tiktok_sharp", sharpen)
        monkeypatch.setattr(module, "ensure_default_cover", cover)
    monkeypatch.setattr(ps.ProductStore, "update_angle_status", staticmethod(status))
    monkeypatch.setattr(render_jobs, "render_slot", slot)
    return events


def test_editor_render_sharpens_inside_the_slot_and_reads_rendered_last(studio, render_events, monkeypatch):  # noqa: F811
    job = _editor_render(monkeypatch, studio, mp4=studio.video.relative_to(studio.root).as_posix())
    assert job["status"] == "completed"

    tail = [e for e in render_events if e in ("slot_in", "sharpen", "slot_out")
            or (isinstance(e, tuple) and e[0] == "cover")
            or (isinstance(e, tuple) and e[0] == "status" and e[1] == "rendered")]
    assert [e if isinstance(e, str) else e[0] for e in tail] == ["slot_in", "sharpen", "slot_out", "cover", "status"]


def test_batch_render_reads_rendered_only_after_sharpen_and_cover(studio, render_events, monkeypatch, tmp_path):  # noqa: F811
    seen = []
    real = batch_render.ensure_tiktok_sharp

    def sharpen(export_id, **kwargs):
        seen.append("sharpen")
        return real(export_id, **kwargs)

    monkeypatch.setattr(batch_render, "ensure_tiktok_sharp", sharpen)
    with patch.object(ps.ProductStore, "update_angle_status",
                      side_effect=lambda *a, **k: seen.append(("status", a[2]))):
        _batch_render_without_status_patch(monkeypatch, studio, tmp_path)
    rendered_at = seen.index(("status", "rendered"))
    assert seen.index("sharpen") < rendered_at
    assert any(isinstance(e, tuple) and e[0] == "cover" for e in render_events)


def _batch_render_without_status_patch(monkeypatch, studio, tmp_path):  # noqa: F811
    """``_batch_render`` patches update_angle_status itself; run the same
    batch with the caller's patch in place instead."""
    from scripts import batch_queue_store
    from scripts.task_manager import TaskManager

    monkeypatch.setattr(batch_queue_store, "BATCH_QUEUE_PATH", tmp_path / "batch_render_queue.json")
    for name in ("update_progress", "complete_task", "fail_task", "cancel_task"):
        monkeypatch.setattr(TaskManager, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(TaskManager, "create_task", lambda **kwargs: kwargs)
    monkeypatch.setattr(batch_render.BatchRenderManager, "_ensure_dispatcher", lambda: None)
    batch_render.BATCH_REGISTRY.clear()
    clip = tmp_path / "raw.mp4"
    clip.write_text("clip")
    product = {"id": "prod_auto_cover", "title": "Auto Cover Product", "angles": [{
        "angle_id": "a1", "angle_name": "รีวิวสเปก", "status": "scripted",
        "selected_video": str(clip), "script_lines": ["a"]}]}
    result = {"mp4": studio.video.relative_to(studio.root).as_posix(),
              "project_name": "clip_project", "export_id": EXPORT_ID}
    try:
        with patch.object(ps.ProductStore, "get", return_value=product), \
             patch("scripts.pipeline.TikTokAutoCutterPipeline.run", return_value=result):
            batch = batch_render.BatchRenderManager.create_batch(
                product_id="prod_auto_cover", angle_ids=["a1"], options={"export_mp4": True})
            batch_render.BatchRenderManager._run_batch_worker(batch["batch_id"])
    finally:
        batch_render.BATCH_REGISTRY.clear()


# --- C21: lots never cross ---------------------------------------------------

def test_select_angle_stays_in_the_lot_of_the_project():
    angles = [
        {"angle_id": "a1", "batch": 1, "project_name": "P-hook_1", "status": "posted", "posted_at": "x"},
        {"angle_id": "a1", "batch": 2, "project_name": "", "status": "scripted"},
    ]
    assert ps.select_angle(angles, "a1", project_name="P-hook_2")["batch"] == 2
    assert ps.select_angle(angles, "a1", project_name="P-hook_1")["batch"] == 1
    assert ps.select_angle(angles, "a1", batch=2)["batch"] == 2
    assert ps.select_angle(angles, "a1")["batch"] == 2  # first not posted
    assert ps.select_angle(angles, "zz") is None


def test_lot_two_render_is_not_refused_as_already_posted(isolated_storage, monkeypatch):
    """Before: the snapshot took the first angle with the id (lot 1, posted)
    and refused lot 2's render with 400."""
    product = ps.ProductStore.add(name="Lots", angles=[
        {"angle_id": "a1", "project_name": "LOT-hook_1", "status": "posted", "posted_at": "2026-11-01T00:00:00+07:00"}])
    ps.ProductStore.append_angles(product["id"], [{"angle_id": "a1", "project_name": "LOT-hook_2", "status": "scripted"}],
                               batch_index=2)
    stored = ps.ProductStore.get(product["id"])
    lot2 = next(a for a in stored["angles"] if (a.get("batch") or 1) == 2)
    picked = ps.select_angle(stored["angles"], lot2["angle_id"], project_name="LOT-hook_2")
    assert picked["batch"] == 2 and picked.get("status") != "posted"


def test_latest_for_angle_filters_by_lot(isolated_storage):
    root = isolated_storage
    exports = root / "04_Exports" / "main"
    exports.mkdir(parents=True, exist_ok=True)
    one, two = exports / "LOT-hook_1_20261101_100000.mp4", exports / "LOT-hook_2_20261102_100000.mp4"
    one.write_bytes(b"1")
    two.write_bytes(b"2")
    from scripts.db import DocumentTable
    docs = root / "_Docs"
    DocumentTable("export_registry", lambda: docs / "store.db", lambda: docs / "export_registry.json").save([
        {"id": "e1", "channel_id": "main", "product_id": "p", "angle_id": "a1", "project_name": "LOT-hook_1",
         "path": one.relative_to(root).as_posix(), "status": "rendered"},
        {"id": "e2", "channel_id": "main", "product_id": "p", "angle_id": "a1", "project_name": "LOT-hook_2",
         "path": two.relative_to(root).as_posix(), "status": "rendered"},
    ])
    assert ExportRegistry.latest_for_angle("p", "a1", channel_id="main", project_name="LOT-hook_1")["id"] == "e1"
    assert ExportRegistry.latest_for_angle("p", "a1", channel_id="main", batch=2)["id"] == "e2"


# --- C4: no second draft for an angle a surviving batch still holds -----------

def test_draft_chain_skips_angles_a_queued_batch_still_holds(monkeypatch):
    product = {"id": "p1", "name": "P", "angles": [
        {"angle_id": "a1", "batch": 1, "status": "scripted", "script_lines": ["x"]},
        {"angle_id": "a2", "batch": 1, "status": "scripted", "script_lines": ["y"]},
    ]}
    monkeypatch.setattr(production_chain.ProductStore, "get", lambda *a, **k: product)
    from scripts import batch_queue_store
    monkeypatch.setattr(batch_queue_store.BatchQueueStore, "load", classmethod(lambda cls: [
        {"batch_id": "b", "product_id": "p1", "status": "queued", "cancelled": False,
         "items": [{"angle_id": "a1", "batch": 1, "status": "queued"},
                   {"angle_id": "a2", "batch": 1, "status": "queued"}]},
    ]))
    voice_calls = []
    monkeypatch.setattr(production_chain, "_voice_step", lambda *a, **k: voice_calls.append(a) or {})

    summary = production_chain.run_draft_chain("t", "p1")

    assert summary["ok"] is True and summary["stopped_at"] == "already_queued"
    assert [r["angle_id"] for r in summary["already_queued"]] == ["a1", "a2"]
    assert voice_calls == []  # nothing new was started


def test_open_batch_keys_ignore_finished_cancelled_and_other_products(monkeypatch):
    from scripts import batch_queue_store
    monkeypatch.setattr(batch_queue_store.BatchQueueStore, "load", classmethod(lambda cls: [
        {"product_id": "p1", "status": "processing", "items": [
            {"angle_id": "a1", "batch": 2, "status": "in_production"},
            {"angle_id": "a2", "status": "draft_ready"}]},
        {"product_id": "p1", "status": "completed", "items": [{"angle_id": "a3", "status": "queued"}]},
        {"product_id": "p1", "status": "queued", "cancelled": True, "items": [{"angle_id": "a4", "status": "queued"}]},
        {"product_id": "p2", "status": "queued", "items": [{"angle_id": "a5", "status": "queued"}]},
    ]))
    assert production_chain._angles_in_open_batches("p1") == {"a1_b2"}


# --- C5: partial success is flagged; scan stop names the clip ----------------

def test_full_chain_partial_flag_and_label(monkeypatch):
    monkeypatch.setattr(production_chain, "run_draft_chain", lambda *a, **k: {
        "ok": True, "message": "สร้างดราฟต์ 2 มุม", "failed_count": 0, "partial": False,
        "drafts": {"created": [{"angle_id": "a1", "batch": 1}, {"angle_id": "a2", "batch": 1}], "failed": []}})
    monkeypatch.setattr(production_chain, "run_render_chain", lambda *a, **k: {
        "ok": True, "message": "เรนเดอร์เสร็จ 1 คลิป · ล้มเหลว 1 คลิป", "stopped_at": None,
        "rendered": [{"angle_id": "a1"}], "failed": [{"angle_id": "a2"}], "skipped": [],
        "failed_count": 1, "partial": True})
    summary = production_chain.run_full_chain("t", "p1")
    assert summary["ok"] is True and summary["partial"] is True and summary["failed_count"] == 1

    labels = []
    monkeypatch.setattr(production_chain.TaskManager, "complete_task",
                        lambda task_id, **kw: labels.append(kw["step_label"]))
    monkeypatch.setattr(production_chain, "run_full_chain", lambda *a, **k: summary)
    production_chain._run_chain("t", "p1", "full", None, None, None, None)
    assert labels and labels[0].startswith("เสร็จบางส่วน · ")


def test_clean_full_chain_is_not_partial(monkeypatch):
    monkeypatch.setattr(production_chain, "run_draft_chain", lambda *a, **k: {
        "ok": True, "message": "", "failed_count": 0,
        "drafts": {"created": [{"angle_id": "a1", "batch": 1}], "failed": []}})
    monkeypatch.setattr(production_chain, "run_render_chain", lambda *a, **k: {
        "ok": True, "message": "", "rendered": [{"angle_id": "a1"}], "failed": [], "skipped": [],
        "failed_count": 0, "partial": False})
    summary = production_chain.run_full_chain("t", "p1")
    assert summary["partial"] is False


def test_scan_stop_names_the_clip(monkeypatch, tmp_path):
    from scripts import api_products
    from scripts.gemini_vision_matcher import GeminiVisionMatcher

    clip = tmp_path / "unreadable_take.mp4"
    clip.write_bytes(b"x")
    monkeypatch.setattr(api_products, "collect_canonical_videos", lambda product: [str(clip)])
    monkeypatch.setattr(GeminiVisionMatcher, "get_cached_catalog", staticmethod(lambda path: None))
    monkeypatch.setattr(api_products, "run_scene_scan", lambda *a, **k: {
        "ok": True, "indexed": {}, "not_analyzed": {str(clip): "quota"}})
    monkeypatch.setattr(production_chain.TaskManager, "create_task", lambda **kw: {"id": "child"})

    @contextmanager
    def no_mirror(*a, **k):
        yield

    monkeypatch.setattr(production_chain, "_mirror_child", no_mirror)
    monkeypatch.setattr(production_chain, "_progress", lambda *a, **k: None)
    report = production_chain._scan_step("t", {"id": "p1", "name": "P"}, None, None)
    assert report["ok"] is False
    assert "unreadable_take.mp4" in report["error"]
