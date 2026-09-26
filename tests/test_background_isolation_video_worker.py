"""Real FFmpeg video artifact gate with an offline segmentation stub."""

import json
import subprocess
import shutil

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from PIL import Image

from scripts import background_isolation_video_worker as video_worker
from scripts import video_editor
from scripts import api_background_isolation as isolation_api


class _Segmenter:
    def remove(self, rgb, session=None):
        rgba = rgb.convert("RGBA")
        alpha = Image.new("L", rgb.size, 0)
        alpha.paste(255, (rgb.width // 2, 0, rgb.width, rgb.height))
        rgba.putalpha(alpha)
        return rgba


class _Worker:
    def _get_session(self, model):
        return _Segmenter(), None


def test_proxy_retains_master_alpha_pts_and_api_range_without_affecting_render(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc2=s=64x64:r=30:d=0.2", "-c:v", "libx264", str(source)],
                   check=True, capture_output=True)
    original = video_worker.build_alpha_preview
    monkeypatch.setattr(video_worker, "build_alpha_preview", lambda *args, **kwargs:
                        original(*args, **kwargs, max_width=32, max_height=32))
    root = tmp_path / "projects"
    result = video_worker.process_background_isolation_video(source, root / ".cache", {"enabled": True},
        source_fingerprint="proxy-test", start=0, duration=0.2, fps=30, timebase="1/30",
        width=64, height=64, rotation=0, rembg_worker=_Worker())
    directory = root / ".cache" / video_worker.VIDEO_NAMESPACE / result["artifact_id"]
    manifest = json.loads((directory / "manifest.json").read_text())
    proxy = manifest["preview"]
    assert proxy["master_sha256"] == manifest["sha256"]
    assert (proxy["width"], proxy["height"], proxy["frame_count"]) == (32, 32, 6)
    pts = []
    for name in ("cutout.webm", "preview.webm"):
        decoded = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(directory / name)],
            check=True, capture_output=True)
        pts.append([f["best_effort_timestamp_time"] for f in json.loads(decoded.stdout)["frames"]])
    assert pts[0] == pts[1]
    monkeypatch.setattr(isolation_api, "PROJECTS_DIR", root)
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", root)
    app = FastAPI()
    app.include_router(isolation_api.router)
    client = TestClient(app)
    url = f"/api/background-isolation/videos/{result['artifact_id']}/preview.webm"
    assert client.get(url, headers={"Range": "bytes=0-15"}).status_code == 206
    config = {"enabled": True, "artifact": {"id": result["artifact_id"], "status": "ready"}}
    assert video_editor._read_ready_background_sequence(config, 0, .2)["video_path"].name == "cutout.webm"
    (directory / "preview.webm").unlink()
    assert client.get(url).status_code == 404
    metadata = client.get(f"/api/background-isolation/sequences/{result['artifact_id']}/manifest").json()
    assert "preview" not in metadata


def test_video_cutout_is_one_seekable_alpha_artifact_and_render_reads_it(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=16x16:r=2:d=1", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    project_root = tmp_path / "03_Projects"
    cache = project_root / ".cache"
    fingerprint = "sha256:" + "a" * 64
    result = video_worker.process_background_isolation_video(
        source, cache, {"enabled": True}, source_fingerprint=fingerprint,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )
    directory = cache / video_worker.VIDEO_NAMESPACE / result["artifact_id"]
    assert result["frame_count"] == 2
    assert {p.name for p in directory.iterdir()} == {"manifest.json", "cutout.webm"}
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["source_duration"] == 1.0
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", project_root)
    config = {"enabled": True, "artifact": {"id": result["artifact_id"],
                                            "status": "ready", "source_fingerprint": fingerprint}}
    render_input = video_editor._read_ready_background_sequence(config, 0.0, 1.0)
    assert render_input["video_path"] == directory / "cutout.webm"
    assert render_input["video_start"] == 0.0
    monkeypatch.setattr(isolation_api, "PROJECTS_DIR", project_root)
    app = FastAPI()
    app.include_router(isolation_api.router)
    client = TestClient(app)
    metadata = client.get(f"/api/background-isolation/sequences/{result['artifact_id']}/manifest")
    assert metadata.status_code == 200
    assert metadata.json()["schema_version"] == 2
    response = client.get(
        f"/api/background-isolation/videos/{result['artifact_id']}/cutout.webm",
        headers={"Range": "bytes=0-15"},
    )
    assert response.status_code == 206
    assert len(response.content) == 16
    assert video_worker.process_background_isolation_video(
        source, cache, {"enabled": True}, source_fingerprint=fingerprint,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )["cache_hit"] is True
    (directory / "cutout.webm").write_bytes(b"damaged")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        video_worker.process_background_isolation_video(
            source, cache, {"enabled": True}, source_fingerprint=fingerprint,
            start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
            rotation=0, rembg_worker=_Worker(),
        )


@pytest.mark.render_regression
def test_mask_video_composites_in_real_ffmpeg_export(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg is required")
    source = tmp_path / "source.mp4"
    audio = tmp_path / "audio.wav"
    subtitles = tmp_path / "subtitles.ass"
    output = tmp_path / "rendered.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=30:d=0.4",
                    "-c:v", "libx264", str(source)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
                    "-c:a", "pcm_s16le", str(audio)], check=True, capture_output=True)
    subtitles.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )
    project_root = tmp_path / "03_Projects"
    fingerprint = "sha256:" + "b" * 64
    result = video_worker.process_background_isolation_video(
        source, project_root / ".cache", {"enabled": True},
        source_fingerprint=fingerprint, start=0.0, duration=0.4,
        fps=30, timebase="1/30", width=64, height=64, rotation=0,
        rembg_worker=_Worker(),
    )
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", project_root)
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    config = {"enabled": True, "artifact": {"id": result["artifact_id"],
                                            "status": "ready", "source_fingerprint": fingerprint}}
    video_editor.VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)], total_duration=0.4,
        mixed_audio_path=str(audio), ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{"source_path": str(source), "trim_start": 0.0,
                    "trim_end": 0.4, "duration": 0.4}],
        background_isolation=config, export_preset="draft",
    )
    assert output.is_file() and output.stat().st_size > 0
    frame = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "0.15",
         "-i", str(output), "-frames:v", "1", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "pipe:1"],
        check=True, capture_output=True,
    ).stdout
    assert len(frame) == 720 * 1280 * 3
    left = frame[(640 * 720 + 100) * 3:(640 * 720 + 100) * 3 + 3]
    right = frame[(640 * 720 + 600) * 3:(640 * 720 + 600) * 3 + 3]
    assert right[2] > left[2] + 70


def test_manifest_records_measured_encode_performance(tmp_path):
    """Phase 0 baseline: the worker must record what the encode actually cost.

    The round's own report had to disclaim its only size figure as read off a
    screenshot rather than measured. Writing the numbers into the manifest at
    encode time means a later run can be compared against this one instead of
    against a recollection.
    """
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=16x16:r=2:d=1", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    result = video_worker.process_background_isolation_video(
        source, tmp_path / "03_Projects" / ".cache", {"enabled": True},
        source_fingerprint="sha256:" + "b" * 64,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )
    directory = (tmp_path / "03_Projects" / ".cache"
                 / video_worker.VIDEO_NAMESPACE / result["artifact_id"])
    perf = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))["performance"]

    # Measured, not asserted: a zero or missing duration would mean the clock
    # was never started and the "baseline" would be fiction.
    assert perf["encode_seconds"] > 0
    assert perf["frame_count"] == 2
    assert perf["source_seconds"] == 1.0
    assert perf["seconds_per_frame"] > 0
    assert perf["realtime_factor"] > 0
    # Output size is recorded so a codec change shows up as a size regression.
    assert perf["output_bytes"] == (directory / "cutout.webm").stat().st_size
    assert perf["bytes_per_frame"] == round(perf["output_bytes"] / 2)
    assert (perf["width"], perf["height"]) == (16, 16)


def test_default_temporal_mode_is_motion(tmp_path):
    """A project that never chose a temporal mode must get the one that works.

    Measured 2026-09-26 across two real BLU01 windows: the previous default
    ("legacy") scored -0.7% and -0.3% against raw rembg -- no better than
    doing nothing -- because it only blends pixels differing by less than 24
    from the previous frame, so moving edges keep their raw mask. "motion"
    scored +20.5% and +12.7%. See
    _Docs/Reports/CUTOUT_PHASE4_EDGE_STABILITY_20260926.md.
    """
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=16x16:r=2:d=1", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    result = video_worker.process_background_isolation_video(
        source, tmp_path / "03_Projects" / ".cache", {"enabled": True},
        source_fingerprint="sha256:" + "d" * 64,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )
    directory = (tmp_path / "03_Projects" / ".cache"
                 / video_worker.VIDEO_NAMESPACE / result["artifact_id"])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["temporal_mode"] == "motion"


def test_explicit_temporal_mode_still_wins(tmp_path):
    """Changing the default must not override a project that chose for itself."""
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=16x16:r=2:d=1", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    result = video_worker.process_background_isolation_video(
        source, tmp_path / "03_Projects" / ".cache",
        {"enabled": True, "temporal_mode": "legacy"},
        source_fingerprint="sha256:" + "e" * 64,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )
    directory = (tmp_path / "03_Projects" / ".cache"
                 / video_worker.VIDEO_NAMESPACE / result["artifact_id"])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["temporal_mode"] == "legacy"
