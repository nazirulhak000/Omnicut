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
    """Masks the right half opaque and tints it, so the cut-out subject is
    distinguishable from the footage behind it.

    The tint matters: the composite keeps the original footage as the base
    layer, so a subject carrying the source's own colour would be invisible
    against it and a pixel assertion could not tell the two apart.
    """

    def remove(self, rgb, session=None):
        rgba = rgb.convert("RGBA")
        subject = Image.new("RGBA", rgb.size, (255, 0, 0, 255))
        rgba.paste(subject, (rgb.width // 2, 0))
        alpha = Image.new("L", rgb.size, 0)
        alpha.paste(255, (rgb.width // 2, 0, rgb.width, rgb.height))
        rgba.putalpha(alpha)
        return rgba


class _Worker:
    def _get_session(self, model):
        return _Segmenter(), None


def test_sparse_cutout_runs_ai_only_on_selected_frames_and_keeps_alpha_gaps(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "color=c=blue:s=16x16:r=4:d=1", "-c:v", "libx264", str(source)],
                   check=True, capture_output=True)

    class CountingSegmenter(_Segmenter):
        calls = 0

        def remove(self, rgb, session=None):
            self.calls += 1
            return super().remove(rgb, session=session)

    class CountingWorker:
        def __init__(self):
            self.segmenter = CountingSegmenter()

        def _get_session(self, model):
            return self.segmenter, None

    worker = CountingWorker()
    result = video_worker.process_background_isolation_video(
        source, tmp_path / ".cache", {"enabled": True}, source_fingerprint="sparse-fixture",
        start=0, duration=1, fps=4, timebase="1/4", width=16, height=16,
        rotation=0, rembg_worker=worker,
        active_intervals=[(0.25, 0.5), (0.75, 1.0)],
    )
    directory = tmp_path / ".cache" / video_worker.VIDEO_NAMESPACE / result["artifact_id"]
    manifest = json.loads((directory / "manifest.json").read_text())
    assert result["frame_count"] == 4
    assert worker.segmenter.calls == manifest["isolated_frame_count"] == 2
    assert manifest["active_intervals"] == [[0.25, 0.5], [0.75, 1.0]]
    decoded = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-c:v", "libvpx-vp9",
                              "-i", str(directory / "cutout.webm"), "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"],
                             check=True, capture_output=True).stdout
    frame_bytes = 16 * 16 * 4
    opaque = [max(decoded[i * frame_bytes + 3:(i + 1) * frame_bytes:4]) > 0 for i in range(4)]
    assert opaque == [False, True, False, True]
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", tmp_path)
    config = {"enabled": True, "scope_mode": "behind_text_windows",
              "artifact": {"id": result["artifact_id"], "status": "ready"},
              "active_intervals": [{"start": 0.25, "end": 0.5}, {"start": 0.75, "end": 1.0}]}
    assert video_editor._read_ready_background_sequence(config, 0, 1) is not None
    moved = {**config, "active_intervals": [{"start": 0, "end": 0.5}]}
    assert video_editor._read_ready_background_sequence(moved, 0, 1) is None
    stale = {**config, "artifact": {"id": result["artifact_id"], "status": "stale"}}
    assert video_editor._read_ready_background_sequence(stale, 0, 1) is None


def test_sparse_cache_id_tracks_intervals_and_actual_temporal_mode():
    args = dict(fingerprint="source-fingerprint", config={"enabled": True},
                start=0, duration=10, fps=30, timebase="1/30",
                width=1080, height=1920, rotation=0)
    legacy = video_worker.video_artifact_id(**args)
    first = video_worker.video_artifact_id(**args, active_intervals=[(0, 5)])
    moved = video_worker.video_artifact_id(**args, active_intervals=[(1, 5)])
    assert legacy != first != moved
    assert first == video_worker.video_artifact_id(**args, active_intervals=[(0, 5)])
    assert legacy == video_worker.video_artifact_id(**{**args, "config": {
        "enabled": True, "temporal_mode": "legacy"}})
    assert first == video_worker.video_artifact_id(**{**args, "config": {
        "enabled": True, "temporal_mode": "motion"}}, active_intervals=[(0, 5)])
    assert first != video_worker.video_artifact_id(**{**args, "config": {
        "enabled": True, "temporal_mode": "legacy"}}, active_intervals=[(0, 5)])


def test_proxy_retains_master_alpha_pts_and_api_range_without_affecting_render(tmp_path, monkeypatch, isolated_storage):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc2=s=64x64:r=30:d=0.2", "-c:v", "libx264", str(source)],
                   check=True, capture_output=True)
    original = video_worker.build_alpha_preview
    monkeypatch.setattr(video_worker, "build_alpha_preview", lambda *args, **kwargs:
                        original(*args, **kwargs, max_width=32, max_height=32))
    root = isolated_storage / "03_Projects"
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
    with TestClient(app) as client:
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
    # Left half: the mask is transparent, so the blue source footage shows
    # through -- it must NOT be painted over (that regression flattened the
    # background to solid #0B1220 and lost the layer the hook text sits on).
    assert left[2] > left[0] + 70, f"footage should remain visible behind the mask: {left}"
    # The artifact has red RGB, but only its alpha is used. The opaque half
    # must retain the exact source colour rather than introducing another RGB frame.
    assert right[2] > right[0] + 70, f"subject must use source RGB: {right}"


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


def _tiny_source(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=16x16:r=2:d=1", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    return source


def _prepare(source, cache_root, fingerprint):
    return video_worker.process_background_isolation_video(
        source, cache_root, {"enabled": True}, source_fingerprint=fingerprint,
        start=0.0, duration=1.0, fps=2, timebase="1/2", width=16, height=16,
        rotation=0, rembg_worker=_Worker(),
    )


def test_debris_without_master_or_manifest_is_reclaimed(tmp_path):
    """A half-written artifact directory must not wedge the feature.

    Only a fully staged directory is ever renamed into place, so a target
    holding neither cutout.webm nor manifest.json is always debris from an
    interrupted run. Refusing it made "prepare cutout" fail identically
    forever with nothing the user could do about it -- which is exactly what
    happened in this project when a test purged the cache mid-build.
    """
    source = _tiny_source(tmp_path)
    cache_root = tmp_path / "03_Projects" / ".cache"
    fingerprint = "sha256:" + "f" * 64

    first = _prepare(source, cache_root, fingerprint)
    directory = cache_root / video_worker.VIDEO_NAMESPACE / first["artifact_id"]

    # Reproduce the debris seen in the field: the master and manifest are
    # gone, only a derived file remains. (This fixture is below the preview
    # downscale threshold, so build_alpha_preview writes none -- the stray
    # file is created here to match what a real interrupted build leaves.)
    (directory / "cutout.webm").unlink()
    (directory / "manifest.json").unlink()
    (directory / "preview.webm").write_bytes(b"orphaned derived file")
    assert [p.name for p in directory.iterdir()] == ["preview.webm"]

    again = _prepare(source, cache_root, fingerprint)

    assert again["status"] == "ready"
    assert again["cache_hit"] is False, "debris should force a real rebuild"
    assert (directory / "cutout.webm").is_file()
    assert (directory / "manifest.json").is_file()


def test_empty_artifact_directory_is_reclaimed(tmp_path):
    source = _tiny_source(tmp_path)
    cache_root = tmp_path / "03_Projects" / ".cache"
    fingerprint = "sha256:" + "1" * 64

    first = _prepare(source, cache_root, fingerprint)
    directory = cache_root / video_worker.VIDEO_NAMESPACE / first["artifact_id"]
    shutil.rmtree(directory)
    directory.mkdir(parents=True)

    assert _prepare(source, cache_root, fingerprint)["status"] == "ready"


def test_artifact_with_a_manifest_is_still_refused(tmp_path):
    """The other half of the contract: anything carrying a manifest may be a
    real artifact whose checksum drifted, so it is never deleted silently."""
    source = _tiny_source(tmp_path)
    cache_root = tmp_path / "03_Projects" / ".cache"
    fingerprint = "sha256:" + "2" * 64

    first = _prepare(source, cache_root, fingerprint)
    directory = cache_root / video_worker.VIDEO_NAMESPACE / first["artifact_id"]
    # Master gone, manifest kept -- ambiguous, so it must not be reclaimed.
    (directory / "cutout.webm").unlink()

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        _prepare(source, cache_root, fingerprint)

    assert (directory / "manifest.json").is_file(), "refused artifact must survive"
