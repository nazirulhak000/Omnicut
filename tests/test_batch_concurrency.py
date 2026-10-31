"""M7: batch items render on BATCH_MAX_WORKERS threads, resume skips valid MP4s.

Offline and deterministic: the pipeline is a fake that sleeps, ffprobe is
mocked, all storage lives under tmp_path. No FFmpeg, no network, nothing is
written to 04_Exports.
"""

import json
import subprocess
import threading
import time
from unittest.mock import patch

import pytest

import scripts.batch_queue_store as batch_queue_store
import scripts.batch_render as batch_render
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


def _fake_ffprobe_ok(command):
    return subprocess.CompletedProcess(
        command, 0, stdout=json.dumps({"streams": [{"codec_type": "video"}], "format": {"duration": "31.5"}}), stderr=""
    )


def _write_mp4(path, size=batch_render.MIN_VALID_MP4_BYTES + 1):
    with open(path, "wb") as handle:
        handle.write(b"\x00\x00\x00\x18ftypisom")
        handle.truncate(size)


def test_resume_skips_items_with_a_valid_output_from_this_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_render, "_ffprobe_binary", lambda: "ffprobe")
    monkeypatch.setattr(batch_render, "_run_ffprobe", _fake_ffprobe_ok)
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
    monkeypatch.setattr(batch_render, "_ffprobe_binary", lambda: "ffprobe")
    monkeypatch.setattr(batch_render, "_run_ffprobe", _fake_ffprobe_ok)
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
    assert len(fake.calls) == 4  # second wave never started
    assert all(item["status"] == "cancelled" for item in batch["items"])
    assert batch["completed_items"] == 0


def test_is_valid_mp4_checks_size_stream_and_duration(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_render, "_ffprobe_binary", lambda: "ffprobe")
    monkeypatch.setattr(batch_render, "_run_ffprobe", _fake_ffprobe_ok)
    good = tmp_path / "good.mp4"
    _write_mp4(good)
    small = tmp_path / "small.mp4"
    _write_mp4(small, size=1024)
    assert is_valid_mp4(good) is True
    assert is_valid_mp4(small) is False
    assert is_valid_mp4(tmp_path / "missing.mp4") is False

    monkeypatch.setattr(
        batch_render, "_run_ffprobe",
        lambda cmd: subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"streams": [], "format": {"duration": "3"}}), stderr=""),
    )
    assert is_valid_mp4(good) is False  # no video stream

    monkeypatch.setattr(
        batch_render, "_run_ffprobe",
        lambda cmd: subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"streams": [{"codec_type": "video"}], "format": {"duration": "0"}}), stderr=""),
    )
    assert is_valid_mp4(good) is False  # zero duration

    monkeypatch.setattr(batch_render, "_run_ffprobe", lambda cmd: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="moov atom not found"))
    assert is_valid_mp4(good) is False  # undecodable


def test_is_valid_mp4_without_ffprobe_falls_back_to_atom_check(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_render, "_ffprobe_binary", lambda: None)

    def fail_if_called(cmd):
        raise AssertionError("ffprobe must not run when it is missing")

    monkeypatch.setattr(batch_render, "_run_ffprobe", fail_if_called)
    with_moov = tmp_path / "with_moov.mp4"
    _write_mp4(with_moov)
    with open(with_moov, "r+b") as handle:
        handle.seek(64)
        handle.write(b"\x00\x00\x00\x08moov")
    without_moov = tmp_path / "without_moov.mp4"
    _write_mp4(without_moov)
    assert is_valid_mp4(with_moov) is True
    assert is_valid_mp4(without_moov) is False


def test_ffprobe_oserror_is_handled(tmp_path, monkeypatch):
    monkeypatch.setattr(batch_render, "_ffprobe_binary", lambda: "ffprobe")

    def boom(cmd):
        raise FileNotFoundError("ffprobe vanished")

    monkeypatch.setattr(batch_render, "_run_ffprobe", boom)
    good = tmp_path / "good.mp4"
    _write_mp4(good)
    assert is_valid_mp4(good) is False
