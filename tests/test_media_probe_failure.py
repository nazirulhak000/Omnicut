"""Audit S3-04 / S3-14 / S3-15: unreadable or ambiguous raw footage is rejected
with a Thai message instead of being planned on made-up numbers."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.error_handler import AppError
from scripts.pipeline_context import PipelineContext
from scripts.stages import source_resolution
from scripts.stages.shot_matching_stage import ShotMatchingStage
from scripts.video_editor import VideoEditor


def test_probe_timeout_reports_zero_duration_not_sixty(monkeypatch):
    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=60)

    monkeypatch.setattr("scripts.video_editor.subprocess.run", hang)
    info = VideoEditor.get_media_info("whatever.mp4")
    assert info["duration"] == 0.0
    assert info["probe_failed"] is True
    assert "TimeoutExpired" in info["probe_error"]


def test_truncated_file_probes_to_zero(tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"\x00" * 4096)
    assert VideoEditor.get_media_info(str(broken))["duration"] == 0.0


def _ctx(raw):
    ctx = PipelineContext(product_name="probe test", raw_video_path=str(raw), total_duration=6.0, export_mp4=False)
    ctx.raw_video = Path(raw)
    ctx.cues = [{"id": 1, "start": 0.0, "end": 6.0, "text": "ทดสอบ"}]
    ctx.micro_cues = list(ctx.cues)
    ctx.use_ai_vision = False
    return ctx


@pytest.mark.parametrize("info", [
    {"duration": 0.0, "probe_failed": True, "probe_error": "TimeoutExpired"},
    {"duration": 0.0},
])
def test_shot_matching_rejects_unreadable_raw_with_thai_error(info):
    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value=info):
        with pytest.raises(AppError) as exc_info:
            ShotMatchingStage.run(_ctx("raw.mp4"))
    assert exc_info.value.code == "RAW_VIDEO_UNREADABLE"
    assert "อ่านความยาวไฟล์วิดีโอดิบ" in exc_info.value.message_th


def test_shot_matching_keeps_user_clip_list_without_probing_raw():
    ctx = _ctx("raw.mp4")
    ctx.clip_list = [{"id": "c0", "source_path": "a.mp4", "trim_start": 0.0, "trim_end": 2.0, "duration": 2.0}]
    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 0.0}):
        ShotMatchingStage.run(ctx)
    assert ctx.actual_clip_list == ctx.clip_list


@pytest.fixture
def media_roots(tmp_path, monkeypatch):
    base = tmp_path / "base"
    raw = base / "01_Raw"
    inbox = base / "00_Inbox"
    raw.mkdir(parents=True)
    inbox.mkdir(parents=True)
    monkeypatch.setattr(source_resolution, "BASE_DIR", base)
    monkeypatch.setattr(source_resolution, "RAW_DIR", raw)
    monkeypatch.setattr(source_resolution, "INBOX_DIR", inbox)
    return base, raw


def test_stale_path_with_two_same_name_raws_is_not_guessed(media_roots):
    base, raw = media_roots
    for product in ("20261101_fanA-hook", "20261102_fanB-hook"):
        (raw / product).mkdir()
        (raw / product / "clip.mp4").write_bytes(b"x" * 2048)
    ctx = PipelineContext(product_name="fan", raw_video_path=r"D:/old/Capcut/01_Raw/somewhere/clip.mp4")
    with pytest.raises(AppError) as exc_info:
        source_resolution.SourceResolutionStage.run(ctx)
    assert exc_info.value.code == "RAW_VIDEO_AMBIGUOUS"
    assert "clip.mp4" in exc_info.value.message_th


def test_missing_clip_list_file_fails_in_thai(media_roots):
    base, raw = media_roots
    source = raw / "raw.mp4"
    source.write_bytes(b"x" * 2048)
    ctx = PipelineContext(product_name="fan", raw_video_path=str(source))
    ctx.clip_list = [{"id": "c0", "source_path": str(raw / "gone.mp4"), "trim_start": 0, "trim_end": 1}]
    with pytest.raises(FileNotFoundError, match="ไม่พบไฟล์ของคลิปที่ 1"):
        source_resolution.SourceResolutionStage.run(ctx)


def test_image_folder_order_is_sorted(media_roots, monkeypatch, tmp_path):
    base, raw = media_roots
    folder = raw / "images"
    folder.mkdir()
    for name in ("c.jpg", "a.jpg", "b.png"):
        (folder / name).write_bytes(b"img")
    reversed_listing = sorted(folder.iterdir(), reverse=True)
    real_iterdir = Path.iterdir
    monkeypatch.setattr(Path, "iterdir", lambda self: iter(reversed_listing) if self == folder else real_iterdir(self))
    monkeypatch.setattr(source_resolution.ProjectManifest, "dir_for", staticmethod(lambda name: tmp_path / "proj" / name))
    ctx = PipelineContext(product_name="fan", raw_video_path=str(folder), project_name="sorted_test")
    source_resolution.SourceResolutionStage.run(ctx)
    assert [Path(p).name for p in ctx.image_files] == ["a.jpg", "b.png", "c.jpg"]
