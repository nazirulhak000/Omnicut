"""Read-only full-timeline technical and corruption scan for a rendered video."""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, timeout=timeout, check=False)


def _parse_intervals(log_text: str, kind: str, duration_s: float) -> list[dict[str, float]]:
    """Pair start/end events across log lines; close an open event at media EOF.

    FFmpeg emits freeze_duration before freeze_end, often on separate lines,
    and a freeze that continues to EOF has no end event. Duration is derived
    from timestamps rather than requiring a particular duration-log ordering.
    """
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    pattern = re.compile(rf"\b{kind}_(start|end):\s*({number})")
    intervals = []
    start = None

    def append_interval(first: float, last: float) -> None:
        first = min(duration_s, max(0.0, first))
        last = min(duration_s, max(0.0, last))
        if last > first:
            intervals.append({"start_s": first, "end_s": last, "duration_s": last - first})

    for match in pattern.finditer(log_text):
        at_s = float(match.group(2))
        if match.group(1) == "start":
            start = at_s
        elif start is not None:
            append_interval(start, at_s)
            start = None
    if start is not None:
        append_interval(start, duration_s)
    return intervals


def _parse_volume(log_text: str) -> dict[str, float | None]:
    result: dict[str, float | None] = {"mean_db": None, "peak_db": None}
    for label, key in (("mean_volume", "mean_db"), ("max_volume", "peak_db")):
        match = re.search(rf"{label}:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB", log_text, re.IGNORECASE)
        if match and match.group(1).lower() not in {"inf", "-inf"}:
            result[key] = float(match.group(1))
    return result


def _rate(value: str | None) -> float | None:
    try:
        result = float(Fraction(value or "0"))
    except (ValueError, ZeroDivisionError):
        return None
    return result if result > 0 else None


def audit_export(path: Path, *, ffprobe: str | None = None, ffmpeg: str | None = None,
                 timeout_s: int = 1800, black_min_s: float = 0.4,
                 freeze_min_s: float = 1.5, silence_min_s: float = 1.0) -> dict[str, Any]:
    """Inspect stream specs and scan the complete duration for black/freeze/silence."""
    ffprobe = ffprobe or shutil.which("ffprobe")
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    report: dict[str, Any] = {"schema_version": "full-export-audit.v1", "path": str(path.resolve(strict=False)),
                              "read_only": True, "status": "fail", "signals": [], "events": {}}
    try:
        if not path.is_file():
            raise RuntimeError("ไฟล์วิดีโอไม่พบ")
        if timeout_s <= 0 or min(black_min_s, freeze_min_s, silence_min_s) <= 0:
            raise ValueError("timeout และ threshold ต้องมากกว่า 0")
        if not ffprobe or not ffmpeg:
            raise RuntimeError("ต้องติดตั้ง FFmpeg และ FFprobe ไว้ใน PATH")
        probe = _run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], 60)
        if probe.returncode:
            raise RuntimeError(probe.stderr.decode("utf-8", "replace")[-1000:].strip() or "ffprobe failed")
        data = json.loads(probe.stdout.decode("utf-8"))
        streams = data.get("streams", [])
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        if not video:
            raise RuntimeError("ไม่พบ video stream")
        duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
        fps = _rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        specs = {"duration_s": duration, "width": int(video.get("width") or 0),
                 "height": int(video.get("height") or 0), "fps": fps,
                 "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name") if audio else None,
                 "has_audio": bool(audio)}
        report["media"] = specs
        expected = {"width": 1080, "height": 1920, "fps": 30.0, "video_codec": "h264", "audio_codec": "aac"}
        mismatches = []
        for key, expected_value in expected.items():
            actual = specs.get(key)
            matched = abs(actual - expected_value) < 0.02 if key == "fps" and actual is not None else actual == expected_value
            if not matched:
                mismatches.append({"field": key, "actual": actual, "expected": expected_value})
        if not audio:
            mismatches.append({"field": "audio_codec", "actual": None, "expected": "aac"})
        if duration <= 0:
            mismatches.append({"field": "duration_s", "actual": duration, "expected": "> 0"})
        if mismatches:
            report["signals"].append({"code": "export_spec_mismatch", "severity": "fail", "details": mismatches})

        filters = f"blackdetect=d={black_min_s}:pix_th=0.10,freezedetect=n=-50dB:d={freeze_min_s}"
        command = [ffmpeg, "-hide_banner", "-nostats", "-v", "info", "-i", str(path), "-vf", filters]
        if audio:
            command += ["-af", f"silencedetect=n=-50dB:d={silence_min_s},volumedetect"]
        command += ["-f", "null", "-"]
        scan = _run(command, timeout_s)
        log_text = (scan.stderr or b"").decode("utf-8", "replace")
        if scan.returncode:
            raise RuntimeError(log_text[-1200:].strip() or f"FFmpeg scan failed with exit code {scan.returncode}")
        events = {"black": _parse_intervals(log_text, "black", duration),
                  "freeze": _parse_intervals(log_text, "freeze", duration),
                  "silence": _parse_intervals(log_text, "silence", duration) if audio else []}
        report["events"] = events
        if audio:
            volume = _parse_volume(log_text)
            report["audio_levels"] = volume
            if volume["peak_db"] is None:
                report["signals"].append({"code": "audio_level_unavailable", "severity": "review",
                                          "message": "ไม่สามารถอ่าน sample peak จาก FFmpeg ได้"})
            elif volume["peak_db"] > -0.1:
                report["signals"].append({"code": "audio_clipping_risk", "severity": "review",
                                          "peak_db": volume["peak_db"], "threshold_db": -0.1})
        for kind, intervals in events.items():
            if intervals:
                report["signals"].append({"code": f"{kind}_intervals_detected", "severity": "review",
                                          "count": len(intervals), "intervals": intervals})
        if any(signal["severity"] == "fail" for signal in report["signals"]):
            report["status"] = "fail"
        elif report["signals"]:
            report["status"] = "review_required"
        else:
            report["status"] = "screened_no_anomaly_detected"
        report["thresholds"] = {"black_min_s": black_min_s, "black_pixel_threshold": 0.10,
                                 "freeze_min_s": freeze_min_s, "freeze_noise_db": -50,
                                 "silence_min_s": silence_min_s, "silence_noise_db": -50}
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        report["signals"].append({"code": "export_audit_failed", "severity": "fail", "message": str(exc)[:1200]})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    default_output = Path(__file__).resolve().parents[1] / ".tmp" / f"full_export_audit_{stamp}.json"
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--black-min", type=float, default=0.4)
    parser.add_argument("--freeze-min", type=float, default=1.5)
    parser.add_argument("--silence-min", type=float, default=1.0)
    args = parser.parse_args(argv)
    output_path = args.output.expanduser().resolve(strict=False)
    if output_path == args.video.expanduser().resolve(strict=False):
        parser.error("report output must not overwrite the source video")
    if output_path.exists():
        parser.error("report output already exists; choose a new path to avoid overwriting it")
    report = audit_export(args.video, timeout_s=args.timeout, black_min_s=args.black_min,
                          freeze_min_s=args.freeze_min, silence_min_s=args.silence_min)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(args.output)}, ensure_ascii=True))
    return 0 if report["status"] != "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
