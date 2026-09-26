"""Dead-air detection for the timeline's Cut Silences action.

Short-form retention falls off over silent gaps, so the editor offers to strip
them. This module only *finds* the gaps; it deliberately does not cut anything.
The timeline shows the proposed removals for confirmation first, because a
ripple delete moves every clip after it and an unreviewed automatic cut is the
kind of edit a user cannot easily undo by eye.

Detection is ffmpeg `silencedetect`, whose thresholds come from the master
plan: quieter than -32 dB for at least 0.35s counts as dead air. Each detected
gap keeps a `padding` of natural pause at both ends so speech does not get
clipped to an abrupt start -- cutting a gap to zero makes the read sound
truncated, which is worse than the pause it removed.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

# Thresholds from _Docs/Plans/CAPCUT_PREMIERE_TECH_INTEGRATION_PLAN.md.
DEFAULT_NOISE_DB = -32.0
DEFAULT_MIN_SILENCE_S = 0.35

# Natural pause left at each end of a removed gap. Without it, consecutive
# phrases butt together and the delivery sounds clipped.
DEFAULT_PADDING_S = 0.10

# A gap shorter than this after padding is not worth a cut: the ripple costs
# more in timeline churn than the tenths of a second it saves.
MIN_USEFUL_CUT_S = 0.05

SILENCE_DETECT_TIMEOUT_S = 300

_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_END_RE = re.compile(r"silence_end:\s*(-?[\d.]+)")


class SilenceDetectError(RuntimeError):
    """Raised when silence detection cannot run. Callers must not fall back to
    cutting nothing *silently* -- the user asked for an edit and deserves to
    hear that it did not happen."""


def _probe_duration(path: Path) -> float:
    """Media duration in seconds, or 0.0 when it cannot be determined."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, encoding="utf-8",
            errors="ignore", timeout=60,
        )
        return max(0.0, float((result.stdout or "").strip()))
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def _parse_silence_log(stderr: str, duration: float) -> List[Dict[str, float]]:
    """
    Turn silencedetect's stderr into [{start, end}] spans.

    ffmpeg reports a `silence_start` and later a matching `silence_end`. A
    file ending mid-silence produces a start with no end, which is a real
    trailing gap and is closed at the known duration rather than dropped --
    dead air at the tail is exactly what the feature exists to remove.
    """
    spans: List[Dict[str, float]] = []
    pending: float | None = None

    for line in (stderr or "").splitlines():
        start_match = _START_RE.search(line)
        if start_match:
            pending = max(0.0, float(start_match.group(1)))
            continue
        end_match = _END_RE.search(line)
        if end_match and pending is not None:
            end = float(end_match.group(1))
            if end > pending:
                spans.append({"start": pending, "end": end})
            pending = None

    if pending is not None and duration > pending:
        spans.append({"start": pending, "end": duration})

    return spans


def detect_silences(
    media: Path,
    *,
    noise_db: float = DEFAULT_NOISE_DB,
    min_silence_s: float = DEFAULT_MIN_SILENCE_S,
    padding_s: float = DEFAULT_PADDING_S,
) -> Dict[str, Any]:
    """
    Find dead-air spans in `media`.

    Returns `{duration, silences, total_silence_s, removable_s, settings}`.
    Each entry in `silences` carries the raw detected `start`/`end` plus the
    padded `cut_start`/`cut_end` the editor would actually remove, so the UI
    can show what it found and what it proposes to do as two separate things.

    Spans whose padded length falls below MIN_USEFUL_CUT_S are dropped: they
    are detections, not worthwhile edits.
    """
    source = Path(media)
    if not source.is_file():
        raise SilenceDetectError(f"ไม่พบไฟล์: {source}")

    padding = max(0.0, float(padding_s))
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(source),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_s}",
        "-f", "null", "-",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=SILENCE_DETECT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SilenceDetectError(
            f"ตรวจช่วงเงียบไม่สำเร็จ (เกินเวลา {SILENCE_DETECT_TIMEOUT_S}s): {source.name}"
        ) from exc
    except OSError as exc:
        raise SilenceDetectError(f"ตรวจช่วงเงียบไม่สำเร็จ (เรียก ffmpeg ไม่ได้): {exc}") from exc

    # silencedetect writes to stderr and exits 0; a non-zero code means the
    # input never decoded, so there is no result to report.
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:300]
        raise SilenceDetectError(f"ตรวจช่วงเงียบไม่สำเร็จสำหรับ {source.name}: {detail}")

    duration = _probe_duration(source)
    detected = _parse_silence_log(result.stderr or "", duration)

    silences: List[Dict[str, float]] = []
    for span in detected:
        cut_start = span["start"] + padding
        cut_end = span["end"] - padding
        if duration > 0:
            cut_end = min(cut_end, duration)
        if cut_end - cut_start < MIN_USEFUL_CUT_S:
            continue
        silences.append({
            "start": round(span["start"], 3),
            "end": round(span["end"], 3),
            "duration": round(span["end"] - span["start"], 3),
            "cut_start": round(cut_start, 3),
            "cut_end": round(cut_end, 3),
            "cut_duration": round(cut_end - cut_start, 3),
        })

    return {
        "duration": round(duration, 3),
        "silences": silences,
        "total_silence_s": round(sum(s["duration"] for s in silences), 3),
        "removable_s": round(sum(s["cut_duration"] for s in silences), 3),
        "settings": {
            "noise_db": noise_db,
            "min_silence_s": min_silence_s,
            "padding_s": padding,
        },
    }


def build_keep_ranges(duration: float, silences: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Invert cut spans into the ranges that survive, in order.

    This is what a ripple delete keeps. Returned separately from
    `detect_silences` so the caller can preview the result before committing:
    the sum of these ranges is the new timeline length.

    A fully silent track yields [] -- "everything would be cut" -- which the
    caller must refuse rather than produce an empty timeline.
    """
    total = max(0.0, float(duration))
    keeps: List[Dict[str, float]] = []
    cursor = 0.0

    for span in sorted(silences, key=lambda s: s["cut_start"]):
        start = max(cursor, float(span["cut_start"]))
        if start > cursor:
            keeps.append({"start": round(cursor, 3), "end": round(start, 3)})
        cursor = max(cursor, float(span["cut_end"]))

    if cursor < total:
        keeps.append({"start": round(cursor, 3), "end": round(total, 3)})

    return [k for k in keeps if k["end"] - k["start"] > 0]
