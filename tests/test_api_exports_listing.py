# -*- coding: utf-8 -*-
"""S6-04 / X-05: GET /api/exports must not auto-register a broken, truncated
or in-progress MP4 as ``rendered``. Uses the real central media gate."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from scripts import api_exports, export_registry
from tests.test_matching_lookup_perf_fix import _seed_products, isolated_exports  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                                reason="ffmpeg/ffprobe required")


def _real_clip(path, seconds=2.0):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(path),
    ], check=True, capture_output=True, timeout=120)
    return path


def test_invalid_and_partial_exports_are_not_registered_as_rendered(isolated_exports):  # noqa: F811
    tmp_path = isolated_exports
    _seed_products(tmp_path, [])
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"

    good = _real_clip(exports_dir / "20261109_good_hook_v1.mp4")
    data = good.read_bytes()
    (exports_dir / "20261109_cut_hook_v1.mp4").write_bytes(data[: len(data) // 2])
    (exports_dir / "20261109_fake_hook_v1.mp4").write_bytes(
        b"\x00\x00\x00\x18ftypmp42" + b"\x00" * (128 * 1024))
    (exports_dir / "20261109_busy_hook_v1.partial.mp4").write_bytes(data)  # encode in progress

    result = api_exports.list_exports()
    names = {item["name"] for item in result["exports"]}
    assert "20261109_good_hook_v1.mp4" in names
    assert "20261109_cut_hook_v1.mp4" not in names
    assert "20261109_fake_hook_v1.mp4" not in names
    assert "20261109_busy_hook_v1.partial.mp4" not in names

    registered = {str(rec.get("path") or "").replace("\\", "/").rsplit("/", 1)[-1]: rec
                  for rec in export_registry.ExportRegistry.all()}
    assert registered.get("20261109_good_hook_v1.mp4", {}).get("status") == "rendered"
    for bad in ("20261109_cut_hook_v1.mp4", "20261109_fake_hook_v1.mp4", "20261109_busy_hook_v1.partial.mp4"):
        assert bad not in registered, f"{bad} must not be auto-registered"


def test_scheduled_on_platform_export_is_tagged_in_list_exports(isolated_exports):  # noqa: F811
    tmp_path = isolated_exports
    _seed_products(tmp_path, [])
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"

    clip = _real_clip(exports_dir / "20261109_sched_hook_v1.mp4")
    reg = export_registry.ExportRegistry.ensure(clip, status="rendered")

    from scripts.schedule_store import ScheduleQueueStore
    with ScheduleQueueStore.transaction(channel_id="main") as records:
        records.append({
            "id": "q_sched_test",
            "channel_id": "main",
            "export_id": reg["id"],
            "video_path": str(clip),
            "status": "scheduled_on_platform",
            "scheduled_at": "2026-11-15T09:00:00+07:00",
        })

    try:
        result = api_exports.list_exports()
        matched = next((item for item in result["exports"] if item["name"] == "20261109_sched_hook_v1.mp4"), None)
        assert matched is not None
        assert matched.get("scheduled_on_platform") is True
        assert matched.get("is_scheduled_on_platform") is True
        assert matched.get("export_status") == "scheduled_on_platform"
        assert matched.get("scheduled_at") == "2026-11-15T09:00:00+07:00"
    finally:
        with ScheduleQueueStore.transaction(channel_id="main") as records:
            records[:] = [r for r in records if r.get("id") != "q_sched_test"]

