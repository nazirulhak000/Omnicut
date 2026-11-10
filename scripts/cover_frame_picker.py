"""
Which frame of an exported clip makes the best default cover.

The cover wants the moment the hook nameplate (brand / model / label) is fully
on screen *and* the product is sharp in frame. The old default was a fixed
0.5 s grab -- before the nameplate has even appeared on a clip that opens with a
hook line -- so the cover showed neither the brand nor a considered shot.

Three steps, all pure apart from reading the video:

1. `resolve_hook_window` -- when the nameplate is up, read from the project's own
   `kind: "hook"` overlay (a clip the user retimed, or an older one whose
   nameplate runs 0-5 s, is handled by data, not by a constant).
2. `candidate_times` -- sample that window.
3. `score_frame` -- sharpness of the product band (the middle of the frame,
   between the hook text above and the captions below) so blur and a frame
   caught mid-cut lose.

The exported mp4 already has the nameplate burned in, so a frame chosen inside
the window carries the brand and model by itself; nothing needs stamping on top.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import cv2
import numpy as np

from scripts.hook_line import HOOK_LINE_END_SEC
from scripts.overlay_model import HOOK_NAMEPLATE_DEFAULT_SEC

# The nameplate slides in; its tiers are only fully settled after this long.
SETTLE_AFTER_START_SEC = 0.6
# Stay clear of the nameplate's fade-out at the other end.
CLEAR_BEFORE_END_SEC = 0.3
# Never pick a frame this close to either end of the clip.
EDGE_MARGIN_SEC = 0.2
# One decode of the window at this rate; neighbours in the stream are the
# frames compared to spot a cut, so a step is also the cut probe distance.
SAMPLE_FPS = 8
MAX_SAMPLES = 48

# Product band as fractions of the frame: below the hook text (which tops out
# near 25%) and above the captions (which start near 72%).
BAND_X = (0.08, 0.92)
BAND_Y = (0.28, 0.68)
# The frames either side of a candidate are compared to spot a cut.
CUT_DIFF_THRESHOLD = 18.0   # mean absolute grey difference, 0-255
CUT_PENALTY = 0.3
# Sharpness is measured on a fixed-width crop so resolution does not change it.
SCORE_WIDTH = 360


def resolve_hook_window(
    overlays: Optional[Sequence[Mapping[str, Any]]],
    total_duration: float,
) -> Tuple[float, float]:
    """The span in which the nameplate is fully legible, clamped inside the clip."""
    start, end = HOOK_LINE_END_SEC, HOOK_LINE_END_SEC + HOOK_NAMEPLATE_DEFAULT_SEC
    for overlay in overlays or []:
        if isinstance(overlay, Mapping) and overlay.get("kind") == "hook" and not overlay.get("hidden"):
            try:
                start = float(overlay.get("start") or 0.0)
                end = float(overlay.get("end") or 0.0)
            except (TypeError, ValueError):
                break
            break
    lo = start + SETTLE_AFTER_START_SEC
    hi = end - CLEAR_BEFORE_END_SEC
    if hi <= lo:                       # a very short nameplate: use what there is
        lo, hi = start + 0.2, max(end - 0.1, start + 0.3)
    top = max(EDGE_MARGIN_SEC, float(total_duration) - EDGE_MARGIN_SEC)
    lo = min(max(lo, EDGE_MARGIN_SEC), top)
    hi = min(max(hi, lo), top)
    return round(lo, 3), round(hi, 3)


def candidate_times(window: Tuple[float, float]) -> List[float]:
    """Sample times across `window` at SAMPLE_FPS, never more than MAX_SAMPLES."""
    lo, hi = window
    if hi - lo < 1e-6:
        return [round(lo, 3)]
    count = min(MAX_SAMPLES, int((hi - lo) * SAMPLE_FPS) + 1)
    if count <= 1:
        return [round((lo + hi) / 2.0, 3)]
    return [round(lo + (hi - lo) * i / (count - 1), 3) for i in range(count)]


def _grey_small(frame: np.ndarray) -> np.ndarray:
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = grey.shape[:2]
    return cv2.resize(grey, (SCORE_WIDTH, max(1, int(round(h * SCORE_WIDTH / w)))), interpolation=cv2.INTER_AREA)


def _band(grey: np.ndarray) -> np.ndarray:
    h, w = grey.shape[:2]
    return grey[int(h * BAND_Y[0]):int(h * BAND_Y[1]), int(w * BAND_X[0]):int(w * BAND_X[1])]


def score_frame(
    frame: np.ndarray,
    before: Optional[np.ndarray] = None,
    after: Optional[np.ndarray] = None,
) -> float:
    """
    Higher is a better cover. Laplacian variance of the product band, cut down
    when the neighbouring frames differ enough to say a cut sits on this frame.
    """
    grey = _grey_small(frame)
    sharp = float(cv2.Laplacian(_band(grey), cv2.CV_64F).var())
    if before is not None and after is not None:
        diff = float(np.mean(np.abs(_grey_small(before).astype(np.int16) - _grey_small(after).astype(np.int16))))
        if diff > CUT_DIFF_THRESHOLD:
            sharp *= CUT_PENALTY
    return sharp


def _decode_window(video_path: Path, start: float, count: int, width: int, height: int) -> List[np.ndarray]:
    """`count` frames at SAMPLE_FPS from `start`, scaled to width x height, in one decode."""
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-i", str(video_path),
        "-vf", f"fps={SAMPLE_FPS},scale={width}:{height}", "-frames:v", str(count),
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-",
    ]
    out = subprocess.run(cmd, capture_output=True, timeout=60).stdout
    size = width * height * 3
    return [
        np.frombuffer(out[i * size:(i + 1) * size], dtype=np.uint8).reshape(height, width, 3)
        for i in range(len(out) // size)
    ]


def pick_cover_timestamp(
    video_path: Path,
    overlays: Optional[Sequence[Mapping[str, Any]]] = None,
    total_duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    The best default cover moment for `video_path`.

    Returns `{"timestamp", "window", "score", "scored": [(t, score), ...],
    "reason"}`. `reason` is "scored" normally and "fallback" when the video could
    not be read, in which case `timestamp` is the window's midpoint.
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        cap.release()
    duration = float(total_duration) if total_duration else (frames / fps if fps else 0.0)
    if duration <= 0:
        duration = HOOK_LINE_END_SEC + HOOK_NAMEPLATE_DEFAULT_SEC + 1.0
    window = resolve_hook_window(overlays, duration)
    mid = round((window[0] + window[1]) / 2.0, 3)
    if src_w <= 0 or src_h <= 0:
        return {"timestamp": mid, "window": window, "score": 0.0, "scored": [], "reason": "fallback"}

    width = SCORE_WIDTH
    height = max(2, int(round(src_h * width / src_w)) // 2 * 2)
    # One frame of lead-in and lead-out so the first and last candidates also
    # have a neighbour to compare against for the cut test.
    lead = 1.0 / SAMPLE_FPS
    start = max(0.0, window[0] - lead)
    count = int((window[1] - start) * SAMPLE_FPS) + 2
    try:
        stream = _decode_window(video_path, start, count, width, height)
    except (OSError, subprocess.SubprocessError):
        stream = []

    scored: List[Tuple[float, float]] = []
    for i, frame in enumerate(stream):
        t = round(start + i / SAMPLE_FPS, 3)
        if t < window[0] - 1e-6 or t > window[1] + 1e-6:
            continue
        before = stream[i - 1] if i > 0 else None
        after = stream[i + 1] if i + 1 < len(stream) else None
        scored.append((t, round(score_frame(frame, before, after), 3)))
    if not scored:
        return {"timestamp": mid, "window": window, "score": 0.0, "scored": [], "reason": "fallback"}
    best_t, best_score = max(scored, key=lambda item: item[1])
    return {"timestamp": best_t, "window": window, "score": best_score, "scored": scored, "reason": "scored"}


def frame_has_nameplate(overlays: Optional[Sequence[Mapping[str, Any]]], seconds: float) -> bool:
    """
    Whether the exported video already shows its hook nameplate at `seconds`.

    True only when a visible `kind: "hook"` overlay covers the moment (after its
    entrance has begun). Unknown overlays answer False, so a cover for a clip we
    cannot read about is stamped exactly as before.
    """
    for overlay in overlays or []:
        if isinstance(overlay, Mapping) and overlay.get("kind") == "hook" and not overlay.get("hidden"):
            try:
                start, end = float(overlay.get("start") or 0.0), float(overlay.get("end") or 0.0)
            except (TypeError, ValueError):
                return False
            return start + 0.3 <= float(seconds) <= end
    return False


def find_project_overlays(
    video_path: Path, projects_dir: Path,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[float]]:
    """
    `(overlays, total_duration)` of the project that exported `video_path`, or
    `(None, None)`. Matched on the mp4 recorded in `artifacts.mp4_video`, never by
    fuzzy name -- a wrong project would hand back the wrong nameplate window.
    """
    if not projects_dir.exists():
        return None, None
    name = video_path.name
    for folder in projects_dir.iterdir():
        manifest = folder / "project.json"
        if not manifest.is_file():
            continue
        try:
            text = manifest.read_text(encoding="utf-8")
            if name not in text:               # cheap reject before parsing a large file
                continue
            data = json.loads(text)
        except (OSError, ValueError):
            continue
        entry = (data.get("artifacts") or {}).get("mp4_video")
        recorded = entry.get("path", "") if isinstance(entry, dict) else (entry or "")
        if recorded and Path(str(recorded)).name == name:
            overlays = data.get("overlays")
            duration = data.get("total_duration")
            return (overlays if isinstance(overlays, list) else None,
                    float(duration) if duration else None)
    return None, None
