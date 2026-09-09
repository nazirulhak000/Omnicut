import json
from types import SimpleNamespace

from tools.golden_master_probe import ProbeThresholds, compare_reports, probe_artifact


def _result(stdout=b"", stderr=b"", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _runner_factory(*, frozen=False, black=False, loudness="mean_volume: -18.0 dB\nmax_volume: -3.0 dB\n",
                    format_duration="2.0", video_duration="2.0", audio_duration="2.0"):
    calls = []

    def runner(command):
        calls.append(list(command))
        if command[0] == "ffprobe":
            return _result(json.dumps({
                "streams": [
                    {"codec_type": "video", "width": 540, "height": 960,
                     "avg_frame_rate": "30/1", "nb_frames": "60", "duration": video_duration},
                    {"codec_type": "audio", "sample_rate": "48000", "channels": 2,
                     "duration": audio_duration},
                ],
                "format": {"duration": format_duration},
            }).encode())
        if "-af" in command:
            return _result(stderr=loudness.encode())
        if black:
            value = b"\x00" * 32 * 32
        elif frozen:
            value = b"\x80" * 32 * 32
        else:
            value = {
                "0.000000": b"\x20" * 32 * 32,
                "1.000000": b"\x80" * 32 * 32,
                "1.966667": b"\xe0" * 32 * 32,
            }.get(command[command.index("-ss") + 1], b"\x80" * 32 * 32)
        return _result(stdout=value)

    runner.calls = calls
    return runner


def test_probe_is_numeric_deterministic_and_samples_entry_hold_exit(tmp_path):
    artifact = tmp_path / "render.mp4"
    artifact.write_bytes(b"fixture marker")
    runner = _runner_factory()

    first = probe_artifact(artifact, runner=runner, expected={"width": 540, "height": 960, "fps": 30})
    second = probe_artifact(artifact, runner=_runner_factory(), expected={"width": 540, "height": 960, "fps": 30})

    assert first == second
    assert first["status"] == "pass"
    assert [sample["label"] for sample in first["samples"]] == ["entry", "hold", "exit"]
    assert first["samples"][0]["mean_luma"] < first["samples"][1]["mean_luma"] < first["samples"][2]["mean_luma"]
    assert first["audio"]["mean_volume_db"] == -18.0
    assert first["audio"]["max_volume_db"] == -3.0
    assert all(isinstance(sample["sha256"], str) and len(sample["sha256"]) == 64 for sample in first["samples"])
    assert any(command[0] == "ffprobe" for command in runner.calls)


def test_probe_reports_frozen_and_clipping_signals_as_review_warnings(tmp_path):
    artifact = tmp_path / "suspicious.mp4"
    artifact.write_bytes(b"fixture marker")
    report = probe_artifact(
        artifact,
        runner=_runner_factory(frozen=True, loudness="mean_volume: -1.0 dB\nmax_volume: 0.0 dB\n"),
        thresholds=ProbeThresholds(clipping_peak_db=-0.1),
    )

    codes = {signal["code"] for signal in report["signals"]}
    assert report["status"] == "warn"
    assert {"identical_sample_frames", "audio_peak_near_clip"}.issubset(codes)
    assert report["score"]["warning_signals"] == 2
    assert report["score"]["failed_signals"] == 0


def test_probe_uses_video_duration_when_audio_tail_is_longer(tmp_path):
    artifact = tmp_path / "audio-tail.mp4"
    artifact.write_bytes(b"fixture marker")
    report = probe_artifact(
        artifact,
        runner=_runner_factory(format_duration="2.2", video_duration="2.0", audio_duration="2.2"),
        expected={"width": 540, "height": 960, "fps": 30},
    )

    assert report["status"] == "pass"
    assert [sample["label"] for sample in report["samples"]] == ["entry", "hold", "exit"]
    assert not any(signal["code"] == "frame_sample_failed" for signal in report["signals"])


def test_probe_marks_near_black_frames_and_near_silence_for_review(tmp_path):
    artifact = tmp_path / "black.mp4"
    artifact.write_bytes(b"fixture marker")
    report = probe_artifact(
        artifact,
        runner=_runner_factory(black=True, loudness="mean_volume: -70.0 dB\nmax_volume: -70.0 dB\n"),
    )
    codes = {signal["code"] for signal in report["signals"]}
    assert report["status"] == "warn"
    assert "black_frame_sample" in codes
    assert "audio_near_silence" in codes


def test_missing_artifact_is_a_fail_and_does_not_call_external_tools(tmp_path):
    calls = []
    report = probe_artifact(tmp_path / "missing.mp4", runner=lambda command: calls.append(command))
    assert report["status"] == "fail"
    assert report["signals"][0]["code"] == "artifact_missing"
    assert calls == []


def test_compare_reports_returns_numeric_deltas_and_signal_changes():
    reference = {
        "schema_version": "golden-master.v1",
        "status": "pass",
        "media": {"duration_s": 2.0, "video": {"width": 540, "height": 960, "fps": 30}},
        "audio": {"mean_volume_db": -18.0, "max_volume_db": -3.0},
        "samples": [{"label": "entry", "mean_luma": 32}, {"label": "hold", "mean_luma": 128}, {"label": "exit", "mean_luma": 224}],
        "signals": [], "score": {"pass_rate_pct": 100.0},
    }
    candidate = {
        **reference,
        "status": "warn",
        "media": {"duration_s": 2.25, "video": {"width": 540, "height": 960, "fps": 29.97}},
        "audio": {"mean_volume_db": -16.0, "max_volume_db": -1.0},
        "samples": [{"label": "entry", "mean_luma": 40}, {"label": "hold", "mean_luma": 120}, {"label": "exit", "mean_luma": 210}],
        "signals": [{"code": "audio_peak_near_clip"}], "score": {"pass_rate_pct": 80.0},
    }

    comparison = compare_reports(reference, candidate)

    assert comparison["status_before"] == "pass"
    assert comparison["status_after"] == "warn"
    assert comparison["numeric_deltas"]["duration_s"]["delta"] == 0.25
    assert comparison["numeric_deltas"]["fps"]["delta"] == -0.03
    assert comparison["numeric_deltas"]["sample_mean_luma"]["hold"]["delta"] == -8
    assert comparison["signals_added"] == ["audio_peak_near_clip"]
    assert comparison["score_delta_pct"] == -20.0
