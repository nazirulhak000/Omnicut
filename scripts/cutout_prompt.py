"""Hybrid auto-prompt helpers for SAM 2 product cutouts.

Pure Pillow/numpy maths only: no rembg, no FFmpeg, and no file IO.  The caller
(``background_isolation_video_worker``) owns frame extraction and the rembg
session; this module turns a foreground mask -- or explicit points picked in
the editor -- into the prompt payload the SAM 2 worker understands.

Why this exists: the SAM 2 worker falls back to a single centre point when no
prompt is supplied, so a hand-held product that sits off centre was replaced by
the hand.  Measured on a real clip (Jbl tune 310c, frame at 2.0s): the centre
point produced a 38.74% mask covering both hands while a point on the product
produced a 0.58% mask on the earbuds.
"""

from __future__ import annotations

import io
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image

MAX_SUBJECT_POINTS = 8
MAX_WORKER_PROMPT_POINTS = 1024
# A mask outside this band cannot describe a hand-held product: below it the
# heuristic probably grabbed a speck, above it the whole frame (which is what
# the centre-point fallback produced).
MIN_SUBJECT_AREA_RATIO = 0.002
MAX_SUBJECT_AREA_RATIO = 0.75
ALPHA_FOREGROUND_THRESHOLD = 32
COMPONENT_GRID_MAX_SIDE = 160
# The second stage of the heuristic.  On hand-held footage the cutout model
# often returns ONE blob containing both the hand and the product (measured
# 25% for isnet-general-use on the Jbl clip), so the product is found as the
# colour-outlier region inside that blob: the darkest/oddest pixels are the
# product, the bulk median colour is the hand.
OUTLIER_QUANTILE = 0.97
OUTLIER_MIN_GRID_AREA = 4.0


def _clamp_unit(value: Any) -> float | None:
    """Return ``value`` as a 0..1 float, or ``None`` when it is not usable."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not np.isfinite(number):
        return None
    return min(1.0, max(0.0, number))


def _point_from(value: Any) -> tuple[float, float, int, int | None] | None:
    frame = None
    if isinstance(value, Mapping):
        x = _clamp_unit(value.get("x"))
        y = _clamp_unit(value.get("y"))
        label = value.get("label", 1)
        if "frame" in value and value["frame"] is not None:
            try:
                frame = max(0, int(value["frame"]))
            except (ValueError, TypeError, OverflowError):
                return None
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 2:
        x = _clamp_unit(value[0])
        y = _clamp_unit(value[1])
        label = value[2] if len(value) > 2 else 1
        if len(value) > 3 and value[3] is not None:
            try:
                frame = max(0, int(value[3]))
            except (ValueError, TypeError, OverflowError):
                return None
    else:
        return None
    if x is None or y is None:
        return None
    return x, y, 0 if label in (0, False, "0") else 1, frame


def normalize_subject_points(value: Any) -> list[dict[str, Any]]:
    """Normalize editor-picked points into ``[{x, y, label}]`` (with optional ``frame``).

    Accepts ``{"x": .., "y": .., "label": .., "frame": ..}``, ``[x, y]``,
    ``[x, y, label]``, and ``[x, y, label, frame]`` entries.
    Invalid entries are dropped, coordinates are clamped to the frame,
    and the list is capped so a hostile payload cannot flood the worker.
    """
    if value is None or isinstance(value, (str, bytes, bool)):
        return []
    if not isinstance(value, Iterable):
        return []
    points: list[dict[str, Any]] = []
    frame_counts: dict[int, int] = {}
    for item in value:
        parsed = _point_from(item)
        if parsed is None:
            continue
        x, y, label, frame = parsed
        pt: dict[str, Any] = {"x": round(x, 5), "y": round(y, 5), "label": label}
        if frame is not None:
            pt["frame"] = frame
        frame_key = frame or 0
        if frame_counts.get(frame_key, 0) >= MAX_SUBJECT_POINTS:
            continue
        frame_counts[frame_key] = frame_counts.get(frame_key, 0) + 1
        points.append(pt)
        if len(points) > MAX_WORKER_PROMPT_POINTS:
            raise ValueError("too many SAM2 prompt points; split the source window")
    return points


def foreground_mask(alpha: Any) -> np.ndarray:
    """Boolean foreground mask from an alpha plane, an RGBA array or a mask.

    An already-boolean mask is returned as-is: comparing ``True > 32`` would
    silently produce an all-background mask and every derived point would be
    dropped.
    """
    array = np.asarray(alpha)
    if array.ndim == 3:
        array = array[..., -1]
    if array.ndim != 2 or array.size == 0:
        return np.zeros((0, 0), dtype=bool)
    if array.dtype == bool:
        return array.copy()
    return array > ALPHA_FOREGROUND_THRESHOLD


def _skin_like(mean_rgb: Sequence[float] | None) -> bool:
    """Crude skin test used to prefer the product over the hand holding it.

    Hand-held product footage is the case this whole module exists for, and on
    that footage the hand is both the biggest and the skin-toned component.
    """
    if mean_rgb is None:
        return False
    red, green, blue = (float(channel) for channel in mean_rgb)
    total = red + green + blue
    if total <= 0 or red < green or green < blue:
        return False
    return (
        red / total > 0.36
        and 0.28 < green / total < 0.40
        and 0.18 < blue / total < 0.34
        and red - blue > 15
    )


def _components(mask: np.ndarray, image: Any = None) -> list[dict[str, Any]]:
    """4-connected components with area, centroid and (when given) mean colour.

    The scan runs on a downscaled grid so a 1080x1920 mask costs a few thousand
    cells instead of two million, and stays numpy-only (scipy is installed here
    but is not declared in requirements.txt).
    """
    height, width = mask.shape[:2]
    if height == 0 or width == 0:
        return []
    factor = max(1, int(max(height, width) // COMPONENT_GRID_MAX_SIDE))
    grid = mask[::factor, ::factor]
    rows, columns = grid.shape
    small_image = None
    if image is not None:
        array = np.asarray(image)
        if array.ndim == 3 and array.shape[:2] == (height, width):
            small_image = array[::factor, ::factor]
    visited = np.zeros_like(grid, dtype=bool)
    components: list[dict[str, Any]] = []
    for start_y in range(rows):
        for start_x in range(columns):
            if visited[start_y, start_x] or not grid[start_y, start_x]:
                continue
            stack = [(start_y, start_x)]
            visited[start_y, start_x] = True
            count = 0
            sum_x = 0.0
            sum_y = 0.0
            sum_rgb = np.zeros(3, dtype=float)
            while stack:
                y, x = stack.pop()
                count += 1
                sum_x += x
                sum_y += y
                if small_image is not None:
                    sum_rgb += small_image[y, x, :3]
                for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= next_y < rows and 0 <= next_x < columns:
                        if grid[next_y, next_x] and not visited[next_y, next_x]:
                            visited[next_y, next_x] = True
                            stack.append((next_y, next_x))
            components.append({
                "x": min(width, max(0.0, (sum_x / count) * factor + factor / 2)),
                "y": min(height, max(0.0, (sum_y / count) * factor + factor / 2)),
                "grid_area": float(count),
                "area_ratio": (count * factor * factor) / float(height * width),
                "mean_rgb": (sum_rgb / count) if small_image is not None else None,
            })
    return components


def _colour_outlier_component(foreground: np.ndarray, image: Any) -> dict[str, Any] | None:
    """Largest colour-outlier region inside a merged foreground mask.

    ``foreground`` is boolean; ``image`` must be the same-sized RGB/RGBA array.
    The median colour of the mask stands in for "the bulk of the subject" (the
    hand), and the pixels far from it are where the product is.
    """
    if image is None:
        return None
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[:2] != foreground.shape[:2]:
        return None
    rows, columns = np.nonzero(foreground)
    if rows.size == 0:
        return None
    colours = array[rows, columns, :3].astype(float)
    median = np.median(colours, axis=0)
    distance = np.linalg.norm(colours - median, axis=1)
    threshold = float(np.quantile(distance, OUTLIER_QUANTILE))
    if threshold <= 0:
        return None
    outlier = np.zeros_like(foreground)
    keep = distance >= threshold
    outlier[rows[keep], columns[keep]] = True
    candidates = [
        component for component in _components(outlier, array)
        if component["grid_area"] >= OUTLIER_MIN_GRID_AREA
        and component["area_ratio"] <= MAX_SUBJECT_AREA_RATIO
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda component: component["grid_area"])


def subject_points_from_mask(mask: Any, image: Any = None, *, max_points: int = 1) -> list[dict[str, float]]:
    """Pick positive prompt points from a foreground mask.

    Stage 1: when the model separated the subjects, the largest usable
    non-skin component is the product (the hand is skin-toned).
    Stage 2: otherwise -- a single merged blob -- the colour-outlier region
    inside that blob is used instead.
    Returns ``[]`` when neither stage produces something trustworthy, which
    leaves the caller on its legacy behaviour.
    """
    array = np.asarray(mask)
    if array.size == 0:
        return []
    height, width = array.shape[:2]
    foreground = foreground_mask(array)
    usable = [
        component for component in _components(foreground, image)
        if MIN_SUBJECT_AREA_RATIO <= component["area_ratio"] <= MAX_SUBJECT_AREA_RATIO
    ]
    chosen: dict[str, Any] | None = None
    if usable:
        usable.sort(key=lambda component: component["grid_area"], reverse=True)
        chosen = usable[0]
        if _skin_like(chosen["mean_rgb"]):
            chosen = next(
                (component for component in usable[1:] if not _skin_like(component["mean_rgb"])),
                None,
            )
    if chosen is None:
        chosen = _colour_outlier_component(foreground, image)
    if chosen is None:
        return []
    points = [{
        "x": round(chosen["x"] / width, 5),
        "y": round(chosen["y"] / height, 5),
        "label": 1,
    }]
    return points[:max_points]


def background_point(mask: Any, subject: Sequence[Mapping[str, float]] = ()) -> dict[str, float] | None:
    """Pick the background pixel farthest from the subject, used as a negative point."""
    array = np.asarray(mask)
    if array.size == 0:
        return None
    height, width = array.shape[:2]
    background = ~foreground_mask(array)
    if not background.any():
        return None
    subject_x = sum(float(point.get("x", 0.5)) for point in subject) / max(1, len(subject))
    subject_y = sum(float(point.get("y", 0.5)) for point in subject) / max(1, len(subject))
    rows, columns = np.nonzero(background)
    distance = (rows / height - subject_y) ** 2 + (columns / width - subject_x) ** 2
    best = int(np.argmax(distance))
    return {
        "x": round(float(columns[best]) / width, 5),
        "y": round(float(rows[best]) / height, 5),
        "label": 0,
    }


def format_prompt_points(points: Any) -> str:
    """Serialize points as ``x,y,label`` or ``x,y,label,frame;...`` for the SAM 2 worker CLI.

    A quote-free payload survives the Windows command line, where JSON on
    ``argv`` loses its double quotes before the child process parses it.
    """
    chunks = []
    for point in normalize_subject_points(points):
        if "frame" in point and point["frame"] is not None:
            chunks.append(f"{point['x']},{point['y']},{point['label']},{point['frame']}")
        else:
            chunks.append(f"{point['x']},{point['y']},{point['label']}")
    return ";".join(chunks)


def parse_prompt_points(text: Any) -> list[dict[str, Any]]:
    """Parse the ``x,y,label`` or ``x,y,label,frame;...`` payload back into points (inverse of format)."""
    if not isinstance(text, str) or not text.strip():
        return []
    points: list[Any] = []
    for chunk in text.split(";"):
        parts = [part.strip() for part in chunk.split(",")]
        if len(parts) < 2:
            continue
        item: dict[str, Any] = {"x": parts[0], "y": parts[1], "label": parts[2] if len(parts) > 2 else 1}
        if len(parts) > 3:
            item["frame"] = parts[3]
        points.append(item)
    return normalize_subject_points(points)


def build_sam2_prompts(
    *,
    subject_points: Any = None,
    mask: Any = None,
    image: Any = None,
    add_background_point: bool = True,
) -> list[dict[str, Any]] | None:
    """Build the SAM 2 prompt payload, or ``None`` meaning "no information".

    ``None`` keeps the worker's historical centre point, so a failed derivation
    degrades to the old behaviour instead of breaking the job.  Explicit editor
    points always win over the mask heuristic.
    """
    points = normalize_subject_points(subject_points)
    if not points and mask is not None:
        points = subject_points_from_mask(mask, image)
    if not points:
        return None
    if add_background_point and mask is not None and not any(point["label"] == 0 for point in points):
        negative = background_point(mask, points)
        if negative is not None:
            points = [*points, negative]
    return [{
        "object_id": 1,
        "points": [[point["x"], point["y"]] for point in points],
        "labels": [point["label"] for point in points],
    }]


def _rgba_array(frame_image: Any, remove_background: Any) -> np.ndarray | None:
    """Run a rembg-style callable over one frame and return its RGBA array.

    ``remove_background`` is injected (the worker passes
    ``lambda image: rembg.remove(image, session=session)``) so the derivation is
    testable without rembg installed.  Any failure means "no information".
    """
    if not callable(remove_background):
        return None
    try:
        result = remove_background(frame_image)
        if isinstance(result, (bytes, bytearray)):
            with Image.open(io.BytesIO(result)) as decoded:
                return np.asarray(decoded.convert("RGBA"))
        return np.asarray(result.convert("RGBA"))
    except Exception:
        return None


def subject_points_from_frame(frame_image: Any, *, remove_background: Any) -> list[dict[str, float]] | None:
    """Derive SAM 2 prompts from a single frame using an existing cutout model.

    This is the automatic half of the hybrid flow: the same rembg model that
    already runs for the CPU engine supplies the foreground mask, its largest
    non-skin component becomes the positive point, and the far background
    becomes the negative point.  Returns ``None`` when nothing trustworthy can
    be derived, which keeps the worker on its legacy centre point.
    """
    array = _rgba_array(frame_image, remove_background)
    if array is None or array.ndim != 3 or array.shape[-1] < 4:
        return None
    points = subject_points_from_mask(array[..., 3], array)
    if not points:
        return None
    negative = background_point(array[..., 3], points)
    return [*points, negative] if negative is not None else points

