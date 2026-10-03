from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import full_export_audit as audit


def _probe_result(*, width=1080, height=1920, fps="30/1", video_codec="h264", audio_codec="aac"):
    streams = [{"codec_type": "video", "width": width, "height": height,
                "avg_frame_rate": fps, "codec_name": video_codec, "duration": "4"},
               {"codec_type": "audio", "codec_name": audio_codec}]
    return subprocess.CompletedProcess([], 0, json.dumps({"streams": streams, "format": {"duration": "4"}}).encode(), b"")


def test_full_timeline_events_are_reported_as_review_not_automatic_failure(tmp_path, monkeypatch):
    video = tmp_path / "export.mp4"
    video.write_bytes(b"placeholder")
    calls = []

    def fake_run(command, _timeout):
        calls.append(command)
        if command[0] == "ffprobe":
            return _probe_result()
        log = (b"[blackdetect] black_start:1 black_end:1.5 black_duration:0.5\n"
               b"[freezedetect] freeze_start:2\n"
               b"[freezedetect] freeze_duration:1.5\n"
               b"[freezedetect] freeze_end:3.5\n"
               b"[silencedetect] silence_start:0 silence_end:1 silence_duration:1\n"
               b"mean_volume: -18.0 dB\nmax_volume: -3.0 dB\n")
        return subprocess.CompletedProcess(command, 0, b"", log)

    monkeypatch.setattr(audit, "_run", fake_run)
    report = audit.audit_export(video, ffprobe="ffprobe", ffmpeg="ffmpeg")

    assert report["status"] == "review_required"
    assert len(report["events"]["black"]) == 1
    assert report["events"]["freeze"] == [{"start_s": 2.0, "end_s": 3.5, "duration_s": 1.5}]
    assert len(report["events"]["freeze"]) == 1
    assert len(report["events"]["silence"]) == 1
    assert report["audio_levels"]["peak_db"] == -3.0
    assert "-vf" in calls[1]


def test_invalid_export_specs_fail_closed(tmp_path, monkeypatch):
    video = tmp_path / "wrong.mp4"
    video.write_bytes(b"placeholder")
    monkeypatch.setattr(audit, "_run", lambda command, _timeout: _probe_result(width=720, height=1280, fps="25/1")
                        if command[0] == "ffprobe" else subprocess.CompletedProcess(command, 0, b"", b""))

    report = audit.audit_export(video, ffprobe="ffprobe", ffmpeg="ffmpeg")

    assert report["status"] == "fail"
    details = report["signals"][0]["details"]
    assert {item["field"] for item in details} >= {"width", "height", "fps"}


def test_clean_export_is_screened_but_not_claimed_perfect(tmp_path, monkeypatch):
    video = tmp_path / "good.mp4"
    video.write_bytes(b"placeholder")
    monkeypatch.setattr(audit, "_run", lambda command, _timeout: _probe_result()
                        if command[0] == "ffprobe" else subprocess.CompletedProcess(
                            command, 0, b"", b"mean_volume: -16.0 dB\nmax_volume: -2.0 dB\n"))

    report = audit.audit_export(video, ffprobe="ffprobe", ffmpeg="ffmpeg")

    assert report["status"] == "screened_no_anomaly_detected"
    assert report["read_only"] is True


def test_cli_cannot_overwrite_export_video(tmp_path):
    video = tmp_path / "export.mp4"
    original = b"keep-this-export"
    video.write_bytes(original)

    try:
        audit.main([str(video), "--output", str(video)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI should reject output path that collides with export")
    assert video.read_bytes() == original


@pytest.mark.parametrize("terminal_freeze", [False, True], ids=["middle", "end-of-file"])
def test_real_ffmpeg_freeze_requires_review(tmp_path, terminal_freeze):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe are needed for synthetic full-timeline verification")
    if terminal_freeze:
        graph = "testsrc2=size=1080x1920:rate=30:duration=1,tpad=stop_mode=clone:stop_duration=2[out]"
        duration = 3
    else:
        graph = (
            "testsrc2=size=1080x1920:rate=30:duration=1[m0];"
            "color=c=red:size=1080x1920:rate=30:duration=2[still];"
            "testsrc2=size=1080x1920:rate=30:duration=1[m1];"
            "[m0][still][m1]concat=n=3:v=1:a=0[out]"
        )
        duration = 4
    video = tmp_path / "freeze.mp4"
    try:
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
            "-filter_complex_threads", "1", "-filter_complex", graph,
            "-map", "[out]", "-map", "0:a", "-c:v", "libx264", "-threads", "2",
            "-preset", "ultrafast", "-crf", "32", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(video),
        ], check=True, capture_output=True, timeout=60)
        report = audit.audit_export(video, ffprobe=ffprobe, ffmpeg=ffmpeg, freeze_min_s=1.0)

        assert report["status"] == "review_required", report
        assert not any(signal["severity"] == "fail" for signal in report["signals"]), report
        freezes = report["events"]["freeze"]
        assert len(freezes) == 1, report
        assert 0.8 <= freezes[0]["start_s"] <= 1.1
        assert 2.8 <= freezes[0]["end_s"] <= 3.1
        assert freezes[0]["duration_s"] >= 1.8
        assert any(signal["code"] == "freeze_intervals_detected" for signal in report["signals"])
    finally:
        video.unlink(missing_ok=True)
