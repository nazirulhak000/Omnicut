"""Offline golden-master probe for rendered video artifacts.

The probe does not render or mutate a project. It asks FFprobe for metadata,
asks FFmpeg for three small grayscale frame samples, and runs volumedetect for
basic audio checks. The resulting JSON is a numeric record that can be
compared before and after a style change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = "golden-master.v1"
FRAME_WIDTH = 32
FRAME_HEIGHT = 32
SAMPLE_LABELS = ("entry", "hold", "exit")
Runner = Callable[[Sequence[str]], Any]


@dataclass(frozen=True)
class ProbeThresholds:
    """Review thresholds; these are included in every report."""

    black_luma_max: float = 2.0
    clipping_peak_db: float = -0.1
    silence_peak_db: float = -60.0
    max_av_duration_delta_s: float = 0.25
    frame_width: int = FRAME_WIDTH
    frame_height: int = FRAME_HEIGHT


def _default_runner(command: Sequence[str]) -> Any:
    return subprocess.run(list(command), check=False, capture_output=True)


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _invoke(command: Sequence[str], runner: Runner) -> tuple[bytes, bytes]:
    result = runner(command)
    returncode = getattr(result, "returncode", 0)
    stdout = getattr(result, "stdout", b"")
    stderr = getattr(result, "stderr", b"")
    if returncode:
        detail = _text(stderr).strip() or f"exit code {returncode}"
        raise RuntimeError(f"{command[0]} failed: {detail}")
    return (
        _text(stdout).encode("utf-8") if isinstance(stdout, str) else stdout,
        _text(stderr).encode("utf-8") if isinstance(stderr, str) else stderr,
    )


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _fps(value: Any) -> float | None:
    if value in (None, "", "0/0"):
        return None
    try:
        result = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def _signal(code: str, severity: str, message: str, *, value: Any = None,
            threshold: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "severity": severity, "message": message}
    if value is not None:
        item["value"] = value
    if threshold is not None:
        item["threshold"] = threshold
    return item


def _sample_points(duration_s: float, fps: float | None) -> list[dict[str, float | str]]:
    """Return entry/hold/exit times, keeping every seek inside the artifact."""
    if duration_s <= 0:
        return []
    epsilon = 1.0 / fps if fps and fps > 0 else 0.001
    return [
        {"label": "entry", "time_s": 0.0},
        {"label": "hold", "time_s": round(duration_s / 2.0, 6)},
        {"label": "exit", "time_s": round(max(0.0, duration_s - epsilon), 6)},
    ]


def _frame_metrics(raw: bytes, thresholds: ProbeThresholds) -> dict[str, Any]:
    if not raw:
        raise ValueError("FFmpeg returned no frame bytes")
    values = list(raw)
    mean = sum(values) / len(values)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "sample_width": thresholds.frame_width,
        "sample_height": thresholds.frame_height,
        "byte_count": len(raw),
        "mean_luma": round(mean, 4),
        "min_luma": min(values),
        "max_luma": max(values),
        "is_black": mean <= thresholds.black_luma_max,
    }


def _parse_audio_levels(output: bytes) -> dict[str, float]:
    levels: dict[str, float] = {}
    pattern = r"\b(mean_volume|max_volume):\s*(-?(?:\d+(?:\.\d+)?|inf))\s+dB"
    for name, value in re.findall(pattern, _text(output), re.I):
        parsed = _float(value)
        if parsed is not None:
            levels[name] = parsed
    return levels


def _empty_report(path: Path, thresholds: ProbeThresholds) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": {"path": str(path), "exists": exists, "size_bytes": path.stat().st_size if exists else 0},
        "thresholds": asdict(thresholds),
        "expectations": {},
        "options": {},
        "media": {},
        "samples": [],
        "audio": {},
        "signals": [],
        "score": {"passed_checks": 0, "warning_signals": 0, "failed_signals": 0, "pass_rate_pct": 0.0},
        "status": "fail",
    }


def _finish(report: dict[str, Any]) -> dict[str, Any]:
    signals = report["signals"]
    failed = sum(item["severity"] == "fail" for item in signals)
    warnings = sum(item["severity"] == "warn" for item in signals)
    # Keep one explicit "artifact is structurally readable" check even when
    # no signal was emitted. Warnings remain review items, but do not make the
    # numeric score look like zero successful checks.
    total = max(1, len(signals) + 1)
    passed = max(0, total - failed - warnings)
    report["score"] = {
        "passed_checks": passed,
        "warning_signals": warnings,
        "failed_signals": failed,
        "pass_rate_pct": round((passed / total) * 100.0, 2),
    }
    report["status"] = "fail" if failed else ("warn" if warnings else "pass")
    return report


def probe_artifact(
    artifact_path: str | Path,
    *,
    runner: Runner | None = None,
    thresholds: ProbeThresholds | None = None,
    expected: Mapping[str, Any] | None = None,
    require_audio: bool = False,
) -> dict[str, Any]:
    """Inspect one rendered artifact and return a JSON-serializable report.

    ``runner`` is for deterministic tests and is not needed by normal callers.
    ``expected`` accepts numeric ``width``, ``height`` and ``fps`` values.
    Missing audio is a warning by default, or a failure when required.
    """
    path = Path(artifact_path)
    thresholds = thresholds or ProbeThresholds()
    runner = runner or _default_runner
    report = _empty_report(path, thresholds)
    report["expectations"] = dict(expected or {})
    report["options"] = {"require_audio": require_audio}
    if not path.is_file():
        report["signals"].append(_signal("artifact_missing", "fail", "Artifact path does not contain a file"))
        return _finish(report)

    try:
        stdout, _ = _invoke([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
        ], runner)
        metadata = json.loads(stdout.decode("utf-8"))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        report["signals"].append(_signal("probe_failed", "fail", "FFprobe could not read the artifact", value=str(exc)))
        return _finish(report)

    streams = metadata.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_data = metadata.get("format") or {}
    duration_s = _float(format_data.get("duration"))
    if duration_s is None:
        duration_s = _float((video or {}).get("duration")) or _float((audio or {}).get("duration"))
    duration_s = duration_s or 0.0
    video_duration_s = _float((video or {}).get("duration"))
    audio_duration_s = _float((audio or {}).get("duration"))
    fps = _fps((video or {}).get("avg_frame_rate")) or _fps((video or {}).get("r_frame_rate"))
    report["media"] = {
        "duration_s": round(duration_s, 6),
        "video": {
            "width": video.get("width") if video else None,
            "height": video.get("height") if video else None,
            "fps": round(fps, 6) if fps is not None else None,
            "frame_count": int(video["nb_frames"]) if video and str(video.get("nb_frames", "")).isdigit() else None,
            "duration_s": video_duration_s,
        },
        "audio": {
            "sample_rate": int(audio["sample_rate"]) if audio and str(audio.get("sample_rate", "")).isdigit() else None,
            "channels": audio.get("channels") if audio else None,
            "duration_s": audio_duration_s,
        },
    }

    if video is None:
        report["signals"].append(_signal("video_stream_missing", "fail", "Artifact has no video stream"))
        return _finish(report)
    if duration_s <= 0:
        report["signals"].append(_signal("duration_invalid", "fail", "Artifact duration is zero or unavailable", value=duration_s))
    if not video.get("width") or not video.get("height"):
        report["signals"].append(_signal("dimensions_invalid", "fail", "Video dimensions are missing"))

    for field in ("width", "height", "fps"):
        if field in report["expectations"]:
            actual = report["media"]["video"].get(field)
            target = _float(report["expectations"].get(field))
            if actual is None or target is None or abs(float(actual) - target) > 0.001:
                report["signals"].append(_signal(
                    f"{field}_mismatch", "fail", f"Video {field} differs from the expected value",
                    value=actual, threshold=target,
                ))

    # Container duration can be slightly longer than the video stream when
    # the audio tail has padding. Sampling from that combined duration can
    # seek past the final video packet and produce a false failure.
    sample_duration_s = video_duration_s if video_duration_s and video_duration_s > 0 else duration_s
    for point in _sample_points(sample_duration_s, fps):
        try:
            raw, _ = _invoke([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                "-ss", f"{point['time_s']:.6f}", "-frames:v", "1",
                "-vf", f"scale={thresholds.frame_width}:{thresholds.frame_height}:flags=bilinear,format=gray",
                "-f", "rawvideo", "-",
            ], runner)
            metrics = _frame_metrics(raw, thresholds)
        except (OSError, RuntimeError, ValueError) as exc:
            report["signals"].append(_signal("frame_sample_failed", "fail", f"Could not sample {point['label']} frame", value=str(exc)))
            continue
        report["samples"].append({**point, **metrics})
        if metrics["is_black"]:
            report["signals"].append(_signal(
                "black_frame_sample", "warn", f"The {point['label']} sample is near-black; review whether intentional",
                value=metrics["mean_luma"], threshold=thresholds.black_luma_max,
            ))

    hashes = [sample["sha256"] for sample in report["samples"]]
    if len(hashes) >= 2 and len(set(hashes)) == 1:
        report["signals"].append(_signal(
            "identical_sample_frames", "warn", "Entry, hold and exit fingerprints are identical; possible frozen render",
            value=len(hashes), threshold=2,
        ))

    report["audio"] = {"present": audio is not None}
    if audio is None:
        report["signals"].append(_signal(
            "audio_stream_missing", "fail" if require_audio else "warn",
            "Artifact has no audio stream" + (" and audio is required" if require_audio else ""),
        ))
    else:
        if video_duration_s is not None and audio_duration_s is not None:
            av_delta = round(abs(video_duration_s - audio_duration_s), 6)
            report["audio"]["video_audio_duration_delta_s"] = av_delta
            if av_delta > thresholds.max_av_duration_delta_s:
                report["signals"].append(_signal(
                    "audio_video_duration_mismatch", "warn", "Audio and video durations differ beyond the review threshold",
                    value=av_delta, threshold=thresholds.max_av_duration_delta_s,
                ))
        try:
            _, audio_stderr = _invoke([
                "ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(path),
                "-vn", "-af", "volumedetect", "-f", "null", "-",
            ], runner)
            levels = _parse_audio_levels(audio_stderr)
            report["audio"].update({key + "_db": round(value, 4) for key, value in levels.items()})
            peak = levels.get("max_volume")
            if peak is not None and peak >= thresholds.clipping_peak_db:
                report["signals"].append(_signal(
                    "audio_peak_near_clip", "warn", "Measured audio peak is at or above the clipping review threshold",
                    value=peak, threshold=thresholds.clipping_peak_db,
                ))
            if peak is not None and peak <= thresholds.silence_peak_db:
                report["signals"].append(_signal(
                    "audio_near_silence", "warn", "Measured audio peak is near silence; review the mix",
                    value=peak, threshold=thresholds.silence_peak_db,
                ))
        except (OSError, RuntimeError) as exc:
            report["signals"].append(_signal("audio_probe_failed", "warn", "Could not measure audio loudness", value=str(exc)))

    return _finish(report)


def compare_reports(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Compare stable numeric metrics without comparing machine-specific paths."""
    ref_media = reference.get("media") or {}
    cand_media = candidate.get("media") or {}
    ref_video = ref_media.get("video") or {}
    cand_video = cand_media.get("video") or {}
    ref_audio = reference.get("audio") or {}
    cand_audio = candidate.get("audio") or {}

    def delta(key: str, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
        before = _float(left.get(key))
        after = _float(right.get(key))
        return {"before": before, "after": after, "delta": round(after - before, 6) if before is not None and after is not None else None}

    ref_samples = {item.get("label"): item for item in reference.get("samples", [])}
    cand_samples = {item.get("label"): item for item in candidate.get("samples", [])}
    sample_deltas = {
        label: delta("mean_luma", ref_samples[label], cand_samples[label])
        for label in SAMPLE_LABELS if label in ref_samples and label in cand_samples
    }
    ref_codes = {item.get("code") for item in reference.get("signals", [])}
    cand_codes = {item.get("code") for item in candidate.get("signals", [])}
    ref_score = _float((reference.get("score") or {}).get("pass_rate_pct"), 0.0) or 0.0
    cand_score = _float((candidate.get("score") or {}).get("pass_rate_pct"), 0.0) or 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "status_before": reference.get("status"),
        "status_after": candidate.get("status"),
        "numeric_deltas": {
            "duration_s": delta("duration_s", ref_media, cand_media),
            "width": delta("width", ref_video, cand_video),
            "height": delta("height", ref_video, cand_video),
            "fps": delta("fps", ref_video, cand_video),
            "mean_volume_db": delta("mean_volume_db", ref_audio, cand_audio),
            "max_volume_db": delta("max_volume_db", ref_audio, cand_audio),
            "sample_mean_luma": sample_deltas,
        },
        "signals_added": sorted(cand_codes - ref_codes),
        "signals_removed": sorted(ref_codes - cand_codes),
        "score_delta_pct": round(cand_score - ref_score, 2),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe a rendered artifact for golden-master metrics")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, help="Write the JSON report to this explicit path")
    parser.add_argument("--baseline", type=Path, help="Compare against a previous probe JSON report")
    parser.add_argument("--expected-width", type=int)
    parser.add_argument("--expected-height", type=int)
    parser.add_argument("--expected-fps", type=float)
    parser.add_argument("--require-audio", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    expected = {key: value for key, value in {
        "width": args.expected_width, "height": args.expected_height, "fps": args.expected_fps,
    }.items() if value is not None}
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "fail", "signals": [{"code": "ffmpeg_missing", "severity": "fail", "message": "ffmpeg and ffprobe are required"}]}, indent=2))
        return 1
    report = probe_artifact(args.artifact, expected=expected, require_audio=args.require_audio)
    if args.baseline:
        report["comparison"] = compare_reports(json.loads(args.baseline.read_text(encoding="utf-8")), report)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
