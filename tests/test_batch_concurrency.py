"""M7: batch items render on BATCH_MAX_WORKERS threads, resume skips valid MP4s.

Offline and deterministic: the pipeline is a fake that sleeps, ffprobe is
mocked, all storage lives under tmp_path. No FFmpeg, no network, nothing is
written to 04_Exports.
"""

import json
from pathlib import Path
import subprocess
import threading
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import scripts.batch_queue_store as batch_queue_store
import scripts.batch_render as batch_render
from scripts import render_jobs
from scripts.batch_render import BATCH_REGISTRY, BatchRenderManager, is_valid_mp4
from scripts.product_store import ProductStore
from scripts.render_jobs import RenderCancelled
from scripts.task_manager import TaskManager

FAKE_RENDER_SECONDS = 1.0


@pytest.fixture(autouse=True)
def isolated_batch_state(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_queue_store, "BATCH_QUEUE_PATH", tmp_path / "batch_render_queue.json")
    monkeypatch.setattr(batch_render, "EXPORTS_DIR", tmp_path / "exports")
    monkeypatch.setattr(batch_render, "PROJECTS_DIR", tmp_path / "projects")
    (tmp_path / "exports").mkdir()
    for name in ("create_task", "update_progress", "complete_task", "fail_task", "cancel_task"):
        monkeypatch.setattr(TaskManager, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)
    BATCH_REGISTRY.clear()
    yield
    BATCH_REGISTRY.clear()


def _product(tmp_path, count):
    clip = tmp_path / "footage.mp4"
    clip.write_bytes(b"raw")
    angles = [
        {
            "angle_id": f"ang_{i}",
            "angle_name": f"มุมทดสอบ {i}",
            "status": "scripted",
            "selected_video": str(clip),
            "script_lines": ["ประโยคทดสอบ"],
            "project_name": f"CONC01-test_{i}_1",
        }
        for i in range(count)
    ]
    return {"id": "prod_conc", "title": "สินค้าทดสอบ", "angles": angles}


class FakePipeline:
    """Sleeping stand-in for TikTokAutoCutterPipeline.run that tracks overlap."""

    def __init__(self, seconds=FAKE_RENDER_SECONDS, wait_for_cancel=False):
        self.seconds = seconds
        self.wait_for_cancel = wait_for_cancel
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls = []
        self.started = threading.Event()

    def __call__(self, **kwargs):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls.append(kwargs["angle_id"])
        self.started.set()
        try:
            cancel_event = kwargs.get("cancel_event")
            if self.wait_for_cancel and cancel_event is not None:
                if cancel_event.wait(5.0):
                    raise RenderCancelled()
            else:
                time.sleep(self.seconds)
        finally:
            with self.lock:
                self.active -= 1
        return {"mp4": "", "project_name": kwargs["project_name"], "export_id": ""}


def _run_batch(tmp_path, count, fake, workers):
    product = _product(tmp_path, count)
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status"), \
         patch.object(ProductStore, "attach_project"), \
         patch.object(batch_render, "BATCH_MAX_WORKERS", workers), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc", options={"export_mp4": False})
        started = time.perf_counter()
        BatchRenderManager._run_batch_worker(res["batch_id"])
        elapsed = time.perf_counter() - started
    return BatchRenderManager.get_batch(res["batch_id"]), elapsed


def test_default_worker_count_follows_rule_24():
    assert batch_render.BATCH_MAX_WORKERS == 4


def test_eight_items_render_concurrently_within_40_percent_of_sequential(tmp_path):
    sequential_fake = FakePipeline()
    sequential_batch, sequential_elapsed = _run_batch(tmp_path, 8, sequential_fake, workers=1)
    assert sequential_fake.max_active == 1
    assert sequential_batch["completed_items"] == 8

    BATCH_REGISTRY.clear()
    parallel_fake = FakePipeline()
    batch, elapsed = _run_batch(tmp_path, 8, parallel_fake, workers=batch_render.BATCH_MAX_WORKERS)

    assert batch["status"] == "completed"
    assert batch["completed_items"] == 8
    assert batch["failed_items"] == 0
    assert all(item["status"] == "draft_ready" for item in batch["items"])
    assert sorted(parallel_fake.calls) == sorted(f"ang_{i}" for i in range(8))
    assert parallel_fake.max_active == 4
    assert elapsed <= 0.40 * sequential_elapsed, (elapsed, sequential_elapsed)


def test_concurrent_items_never_share_a_project_name(tmp_path):
    product = _product(tmp_path, 4)
    for angle in product["angles"]:
        angle["project_name"] = ""  # force synthesis while siblings run
    fake = FakePipeline(seconds=0.05)
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status"), \
         patch.object(ProductStore, "attach_project"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc", options={"export_mp4": False})
        BatchRenderManager._run_batch_worker(res["batch_id"])
    names = [item["project_name"] for item in BatchRenderManager.get_batch(res["batch_id"])["items"]]
    assert all(names)
    assert len(set(names)) == len(names)


_REAL_CLIP_CACHE = {}


def _real_clip_bytes():
    """Bytes of a tiny real 1080x1920@30 MP4 (passes the central gate)."""
    if "data" not in _REAL_CLIP_CACHE:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "clip.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=gray:s=1080x1920:r=30:d=0.5",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out),
            ], check=True, capture_output=True, timeout=120)
            _REAL_CLIP_CACHE["data"] = out.read_bytes()
    return _REAL_CLIP_CACHE["data"]


def _write_mp4(path):
    Path(path).write_bytes(_real_clip_bytes())


def test_resume_skips_items_with_a_valid_output_from_this_batch(tmp_path, monkeypatch):
    product = _product(tmp_path, 4)
    fake = FakePipeline(seconds=0.05)
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status") as update_status, \
         patch.object(ProductStore, "attach_project"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc")  # export_mp4 defaults to True
        batch_id = res["batch_id"]
        # Simulate a crash after two clips finished writing their MP4 but
        # before the checkpoint recorded it: items were left in_production.
        batch = BatchRenderManager.get_batch(batch_id)
        for item in batch["items"][:2]:
            item["status"] = "in_production"
            _write_mp4(batch_render.EXPORTS_DIR / f"{item['project_name']}_20261031_120000.mp4")
        BatchRenderManager._persist_batch(batch)
        BATCH_REGISTRY.clear()

        assert BatchRenderManager.recover_pending_batches() == 1
        BatchRenderManager._run_batch_worker(batch_id)

    batch = BatchRenderManager.get_batch(batch_id)
    assert sorted(fake.calls) == ["ang_2", "ang_3"]
    resumed = batch["items"][:2]
    assert all(item["status"] == "rendered" for item in resumed)
    assert all(item["video_url"].endswith(".mp4") for item in resumed)
    rendered_calls = [c for c in update_status.call_args_list if c.args[2] == "rendered"]
    assert {c.args[1] for c in rendered_calls} >= {"ang_0", "ang_1"}


def test_resume_ignores_exports_older_than_the_batch(tmp_path, monkeypatch):
    product = _product(tmp_path, 1)
    old = batch_render.EXPORTS_DIR / f"{product['angles'][0]['project_name']}_20250101_000000.mp4"
    _write_mp4(old)
    import os
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    fake = FakePipeline(seconds=0.01)
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status"), \
         patch.object(ProductStore, "attach_project"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc")
        BatchRenderManager._run_batch_worker(res["batch_id"])
    assert fake.calls == ["ang_0"]  # an intentional re-render still renders


def test_cancel_stops_running_wave_and_skips_remaining_items(tmp_path):
    product = _product(tmp_path, 8)
    fake = FakePipeline(wait_for_cancel=True)
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status"), \
         patch.object(ProductStore, "attach_project"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc", options={"export_mp4": False})
        batch_id = res["batch_id"]
        worker = threading.Thread(target=BatchRenderManager._run_batch_worker, args=(batch_id,))
        worker.start()
        assert fake.started.wait(5.0)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            with fake.lock:
                if fake.active == 4:
                    break
            time.sleep(0.01)
        assert BatchRenderManager.cancel_batch(batch_id) is True
        worker.join(10.0)
        assert not worker.is_alive()

    batch = BatchRenderManager.get_batch(batch_id)
    assert batch["status"] == "cancelled"
    assert len(fake.calls) == 4  # queued items never started
    assert all(item["status"] == "cancelled" for item in batch["items"])
    assert batch["completed_items"] == 0


def test_resume_gate_rejects_truncated_and_partial_outputs(tmp_path):
    """S6-03: the resume gate is the central validator, not a size/duration check."""
    good = tmp_path / "good.mp4"
    _write_mp4(good)
    assert is_valid_mp4(good) is True
    half = tmp_path / "half.mp4"
    data = good.read_bytes()
    half.write_bytes(data[: len(data) // 2])
    assert is_valid_mp4(half) is False
    fake = tmp_path / "fake.mp4"
    with open(fake, "wb") as handle:
        handle.write(b"\x00\x00\x00\x18ftypisom")
        handle.truncate(2 * 1024 * 1024)
    assert is_valid_mp4(fake) is False
    assert is_valid_mp4(tmp_path / "missing.mp4") is False


# --------------------------------------------------------- shared slot pool
@pytest.fixture
def pool_of(monkeypatch):
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    previous = render_jobs.render_concurrency()
    yield render_jobs.set_render_concurrency
    render_jobs.set_render_concurrency(previous)


class SlotTrackingPipeline(FakePipeline):
    """FakePipeline that also records how many render slots are held."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_slots = 0

    def __call__(self, **kwargs):
        with self.lock:
            self.max_slots = max(self.max_slots, render_jobs.active_count())
        return super().__call__(**kwargs)


def test_each_batch_item_holds_its_own_render_slot(tmp_path, pool_of):
    pool_of(4)
    fake = SlotTrackingPipeline(seconds=0.3)
    batch, _ = _run_batch(tmp_path, 8, fake, workers=4)
    assert batch["completed_items"] == 8
    assert fake.max_active == 4
    # One slot per running item, not one per wave.
    assert fake.max_slots == 4
    assert render_jobs.active_count() == 0


def test_batch_never_exceeds_the_render_pool(tmp_path, pool_of):
    pool_of(2)  # e.g. OMNICUT_RENDER_CONCURRENCY=2
    fake = FakePipeline(seconds=0.1)
    batch, _ = _run_batch(tmp_path, 6, fake, workers=4)
    assert batch["completed_items"] == 6
    assert fake.max_active == 2


def test_single_render_and_batch_share_the_pool(tmp_path, pool_of):
    """A single render holding one slot leaves three for the batch; together
    they never exceed the pool."""
    pool_of(4)
    fake = SlotTrackingPipeline(seconds=0.2)
    single_started = threading.Event()
    release_single = threading.Event()

    def single_render():
        with render_jobs.render_slot("single-render"):
            single_started.set()
            release_single.wait(10)

    single = threading.Thread(target=single_render)
    single.start()
    assert single_started.wait(5)
    try:
        batch, _ = _run_batch(tmp_path, 6, fake, workers=4)
    finally:
        release_single.set()
        single.join(5)
    assert batch["completed_items"] == 6
    assert fake.max_active == 3
    assert fake.max_slots == 4
    assert render_jobs.active_count() == 0


def test_a_freed_slot_is_reused_without_waiting_for_the_whole_wave(tmp_path, pool_of):
    """One slow item must not hold back the other workers (no wave barrier)."""
    pool_of(4)
    product = _product(tmp_path, 8)
    lock = threading.Lock()
    finished = []

    def fake(**kwargs):
        time.sleep(1.0 if kwargs["angle_id"] == "ang_0" else 0.1)
        with lock:
            finished.append(kwargs["angle_id"])
        return {"mp4": "", "project_name": kwargs["project_name"], "export_id": ""}

    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_status"), \
         patch.object(ProductStore, "attach_project"), \
         patch("scripts.pipeline.TikTokAutoCutterPipeline.run", side_effect=fake):
        res = BatchRenderManager.create_batch(product_id="prod_conc", options={"export_mp4": False})
        BatchRenderManager._run_batch_worker(res["batch_id"])
    # With waves, ang_4..ang_7 could only start after ang_0 (1s) finished.
    assert finished[-1] == "ang_0"
    assert BatchRenderManager.get_batch(res["batch_id"])["completed_items"] == 8


def test_item_retries_when_the_render_queue_is_full(tmp_path, pool_of, monkeypatch):
    pool_of(4)
    monkeypatch.setattr(batch_render, "_SLOT_RETRY_SECONDS", 0.01)
    real_slot = render_jobs.render_slot
    refusals = {"left": 2}

    def flaky_slot(job_id, *args, **kwargs):
        if refusals["left"] > 0:
            refusals["left"] -= 1
            raise HTTPException(status_code=429, detail="full")
        return real_slot(job_id, *args, **kwargs)

    monkeypatch.setattr(render_jobs, "render_slot", flaky_slot)
    fake = FakePipeline(seconds=0.01)
    batch, _ = _run_batch(tmp_path, 1, fake, workers=1)
    assert batch["completed_items"] == 1
    assert refusals["left"] == 0
