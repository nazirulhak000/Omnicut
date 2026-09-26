"""Matching clip colour to an anchor clip.

Footage gathered from several sources rarely shares a white balance: one clip
runs cool, the next warm, and cutting between them looks like a mistake rather
than a style. This module measures each clip against a chosen anchor and
proposes the brightness/contrast/saturation corrections that bring them
together.

It only ever *proposes*. The values it returns are the same
brightness/contrast/saturation contract `resolve_color_finish` already
understands (scripts/video_editor.py), so a matched clip renders through the
existing `eq` filter with nothing new in the graph, and the editor can show
the numbers before they are applied.

Corrections are deliberately conservative:

- they are clamped to EQ_LIMITS, the range the renderer accepts, so a wildly
  different clip is pulled closer rather than pushed to an extreme
- a clip already close to the anchor is left exactly alone, because a
  correction too small to see is still a diff the user has to review
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# The renderer's own accepted ranges. Imported rather than restated so a
# change to what ffmpeg will be asked for cannot drift from what is proposed.
from scripts.video_editor import EQ_LIMITS

SIGNALSTATS_TIMEOUT_S = 180

# How many frames to sample per clip. Colour is judged across the clip, not
# from one frame that might be a cutaway or a flash; a handful of frames is
# enough to characterise a shot and keeps the probe fast.
SAMPLE_FRAMES = 12

# Below these deltas a correction is not worth making: the difference is not
# visible, and emitting one would add a filter and a diff for nothing.
MIN_BRIGHTNESS_DELTA = 0.015
MIN_CONTRAST_DELTA = 0.04
MIN_SATURATION_DELTA = 0.05


class ColorMatchError(RuntimeError):
    """Raised when a clip cannot be measured. Callers skip that clip."""


def _clamp(key: str, value: float) -> float:
    low, high, _ = EQ_LIMITS[key]
    return max(low, min(high, value))


def measure_clip(path: Path, *, sample_frames: int = SAMPLE_FRAMES) -> Dict[str, float]:
    """
    Average luma level, luma spread and saturation for one clip.

    Uses ffmpeg's `signalstats`, which reports per-frame statistics that
    `ffprobe` can read back as frame metadata. Values come back on ffmpeg's
    own 0-255 luma scale and are normalised to 0-1 here so the arithmetic
    downstream is independent of that detail.
    """
    source = Path(path)
    if not source.is_file():
        raise ColorMatchError(f"ไม่พบไฟล์: {source}")

    frames = max(1, int(sample_frames))
    cmd = [
        "ffprobe", "-v", "error",
        "-f", "lavfi",
        f"movie={_lavfi_source(source)},signalstats",
        # YLOW/YHIGH are the 10th/90th percentile luma. Their gap is the tonal
        # range the eye reads as contrast, and unlike YMIN/YMAX it is not
        # thrown off by one blown highlight or crushed shadow. (YDIF is the
        # frame-to-frame difference -- it is 0 on a still frame and measures
        # motion, not contrast.)
        "-show_entries", "frame_tags=lavfi.signalstats.YAVG,"
                         "lavfi.signalstats.YLOW,lavfi.signalstats.YHIGH,"
                         "lavfi.signalstats.SATAVG",
        "-read_intervals", f"%+#{frames}",
        "-of", "json",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=SIGNALSTATS_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise ColorMatchError(f"วัดค่าสีไม่สำเร็จ (เกินเวลา): {source.name}") from exc
    except OSError as exc:
        raise ColorMatchError(f"วัดค่าสีไม่สำเร็จ (เรียก ffprobe ไม่ได้): {exc}") from exc

    if result.returncode != 0:
        raise ColorMatchError(f"วัดค่าสีไม่สำเร็จสำหรับ {source.name}")

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ColorMatchError(f"อ่านผลวัดค่าสีไม่ได้: {source.name}") from exc

    luma: List[float] = []
    lows: List[float] = []
    highs: List[float] = []
    saturation: List[float] = []
    for frame in payload.get("frames") or []:
        tags = frame.get("tags") or {}
        _collect(tags, "lavfi.signalstats.YAVG", luma)
        _collect(tags, "lavfi.signalstats.YLOW", lows)
        _collect(tags, "lavfi.signalstats.YHIGH", highs)
        _collect(tags, "lavfi.signalstats.SATAVG", saturation)

    # Tonal range per frame, averaged: how far the shot spreads between its
    # dark and light ends.
    spread = [h - l for l, h in zip(lows, highs)]

    if not luma:
        raise ColorMatchError(f"ไม่ได้ค่าสีจากคลิป: {source.name}")

    return {
        "luma": _mean(luma) / 255.0,
        "spread": _mean(spread) / 255.0 if spread else 0.0,
        "saturation": _mean(saturation) / 255.0 if saturation else 0.0,
        "frames": float(len(luma)),
    }


def _lavfi_source(path: Path) -> str:
    """
    Path as a lavfi `movie=` source.

    lavfi treats `:` as an option separator, and a Windows drive letter puts
    one in every absolute path. Escaping it is not enough -- ffmpeg still
    tried to open `D` -- so the path is made relative to the working directory
    where possible, which removes the colon entirely. A path outside the tree
    falls back to escaping, which is the best available.
    """
    resolved = Path(path).resolve()
    try:
        text = str(resolved.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        text = str(resolved).replace("\\", "/").replace(":", "\\:")
    return text.replace("'", "\\'")


def _collect(tags: Dict[str, Any], key: str, into: List[float]) -> None:
    raw = tags.get(key)
    if raw is None:
        return
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return
    if value == value:  # reject NaN
        into.append(value)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def propose_correction(
    measurement: Dict[str, float],
    anchor: Dict[str, float],
) -> Dict[str, float]:
    """
    brightness/contrast/saturation that move `measurement` toward `anchor`.

    Returns only the keys worth changing; a clip already matching the anchor
    yields `{}`, which the caller should treat as "leave this clip alone"
    rather than as a correction of zero.

    - brightness is an additive luma offset, matching ffmpeg's `eq=brightness`
    - contrast and saturation are ratios, matching `eq=contrast`/`eq=saturation`
    """
    out: Dict[str, float] = {}

    brightness = anchor.get("luma", 0.0) - measurement.get("luma", 0.0)
    if abs(brightness) >= MIN_BRIGHTNESS_DELTA:
        out["brightness"] = round(_clamp("brightness", brightness), 3)

    # A ratio needs a non-trivial denominator: a nearly flat clip (spread ~0)
    # would otherwise produce an enormous contrast multiplier from noise.
    src_spread = measurement.get("spread", 0.0)
    dst_spread = anchor.get("spread", 0.0)
    if src_spread > 0.01 and dst_spread > 0.01:
        contrast = dst_spread / src_spread
        if abs(contrast - 1.0) >= MIN_CONTRAST_DELTA:
            out["contrast"] = round(_clamp("contrast", contrast), 3)

    src_sat = measurement.get("saturation", 0.0)
    dst_sat = anchor.get("saturation", 0.0)
    if src_sat > 0.01 and dst_sat > 0.01:
        saturation = dst_sat / src_sat
        if abs(saturation - 1.0) >= MIN_SATURATION_DELTA:
            out["saturation"] = round(_clamp("saturation", saturation), 3)

    return out


def plan_color_match(
    clips: List[Dict[str, Any]],
    *,
    anchor_id: Optional[str] = None,
    sample_frames: int = SAMPLE_FRAMES,
) -> Dict[str, Any]:
    """
    Measure every clip and propose corrections against one anchor.

    The anchor is `anchor_id` when given, otherwise the first clip -- the
    opening shot is usually the one whose look the rest should follow.

    Returns `{anchor_id, corrections, measurements, skipped}`. `corrections`
    maps clip id to the proposed eq values, and only holds clips that need
    one. `skipped` names clips that could not be measured, with the reason, so
    a failed probe is visible instead of silently leaving a clip unmatched.
    """
    usable = [c for c in (clips or []) if c.get("source_path")]
    if not usable:
        return {"anchor_id": None, "corrections": {}, "measurements": {}, "skipped": []}

    anchor_clip = next((c for c in usable if c.get("id") == anchor_id), usable[0])

    measurements: Dict[str, Dict[str, float]] = {}
    skipped: List[Dict[str, str]] = []
    for clip in usable:
        try:
            measurements[clip["id"]] = measure_clip(
                Path(clip["source_path"]), sample_frames=sample_frames
            )
        except ColorMatchError as exc:
            skipped.append({"id": clip.get("id", ""), "reason": str(exc)})

    anchor_measurement = measurements.get(anchor_clip.get("id"))
    if not anchor_measurement:
        return {
            "anchor_id": anchor_clip.get("id"),
            "corrections": {},
            "measurements": measurements,
            "skipped": skipped + [{
                "id": anchor_clip.get("id", ""),
                "reason": "วัดค่าสีคลิปอ้างอิงไม่สำเร็จ จึงเทียบสีไม่ได้",
            }],
        }

    corrections: Dict[str, Dict[str, float]] = {}
    for clip_id, measurement in measurements.items():
        if clip_id == anchor_clip.get("id"):
            continue
        proposed = propose_correction(measurement, anchor_measurement)
        if proposed:
            corrections[clip_id] = proposed

    return {
        "anchor_id": anchor_clip.get("id"),
        "corrections": corrections,
        "measurements": measurements,
        "skipped": skipped,
    }


def apply_corrections(
    clips: List[Dict[str, Any]],
    corrections: Dict[str, Dict[str, float]],
) -> List[Dict[str, Any]]:
    """
    Clips with corrections merged in, as a new list.

    Pure, so the caller can preview the result before committing it. Clips
    with no correction keep their identity, and an existing manual grade is
    overwritten only for the keys being corrected -- a user who set saturation
    by hand keeps it unless saturation itself is being matched.
    """
    if not corrections:
        return list(clips or [])
    return [
        {**clip, **corrections[clip["id"]]} if clip.get("id") in corrections else clip
        for clip in (clips or [])
    ]
