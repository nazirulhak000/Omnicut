"""Translate declarative motion contracts into deterministic ASS tags.

The adapter is deliberately opt-in.  Existing overlay payloads continue to
use the legacy builders; callers must provide a motion contract (or a known
contract id) to use this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from scripts.subtitle.motion_contract import (
    MOTION_CONTRACT_VERSION,
    MotionContractError,
    _easing_progress,
    get_motion_preset,
    validate_motion_contract,
)


class MotionAssAdapterError(ValueError):
    """Raised when a contract cannot be translated into safe ASS output."""


class UnsupportedMotionPropertyError(MotionAssAdapterError):
    """Raised when a contract asks ASS to render a property without context."""


@dataclass(frozen=True)
class AssMotionSegment:
    track: str
    start_ms: int
    end_ms: int
    from_value: Any
    to_value: Any
    easing: Any
    ass_tags: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track": self.track,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "easing": self.easing,
            "ass_tags": self.ass_tags,
        }


@dataclass(frozen=True)
class AssMotionPlan:
    contract_id: str
    phase: str
    window_ms: Mapping[str, int]
    initial_tags: str
    segments: Tuple[AssMotionSegment, ...]
    unsupported: Tuple[Mapping[str, str], ...] = ()

    @property
    def ass(self) -> str:
        return f"{self.initial_tags}{''.join(segment.ass_tags for segment in self.segments)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "phase": self.phase,
            "window_ms": dict(self.window_ms),
            "initial_tags": self.initial_tags,
            "segments": [segment.to_dict() for segment in self.segments],
            "unsupported": [dict(item) for item in self.unsupported],
        }


# ASS ``\t(t1,t2,accel,tags)`` eases with progress = t ** accel, so only these contract
# easings have an exact single-accel equivalent (ease_in is t*t).  Everything else
# (ease_out = t*(2-t), ease_in_out, sine_in_out, spring, step) is baked into
# piecewise-linear ``\t`` segments sampled from the contract's own easing function.
_ASS_ACCELERATION = {
    "linear": None,
    "ease_in": 2.0,
}

_BAKED_EASING_STEPS = {
    "ease_out": 8,      # quadratic: piecewise-linear error <= 1 / (4 * 8**2) ~ 0.4%
    "ease_in_out": 8,
    "sine_in_out": 8,
}


def _number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise MotionAssAdapterError(f"{label} must be numeric") from exc
    return result


def _integer(value: Any) -> int:
    return int(round(_number(value, "time")))


def _alpha_tag(opacity: Any) -> str:
    alpha = int(round((1.0 - max(0.0, min(1.0, _number(opacity, "opacity")))) * 255.0))
    return f"\\alpha&H{alpha:02X}&"


def _scale_value(value: Any, scale_base: float) -> int:
    return int(round(_number(value, "scale") * scale_base))


def _tag_for_value(
    track: str,
    value: Any,
    *,
    scale_base: float,
    canvas_px_scale: float,
) -> str:
    if track == "scale":
        scale = _scale_value(value, scale_base)
        return f"\\fscx{scale}\\fscy{scale}"
    if track == "alpha":
        return _alpha_tag(value)
    if track == "rotation":
        return f"\\frz{_number(value, 'rotation'):g}"
    if track == "blur":
        return f"\\blur{_number(value, 'blur') * canvas_px_scale:g}"
    raise MotionAssAdapterError(f"track {track} has no direct ASS value tag")


def _easing_name(easing: Any) -> str:
    return easing if isinstance(easing, str) else (easing or {}).get("name", "linear")


def _easing_acceleration(easing: Any) -> Optional[float]:
    name = _easing_name(easing)
    if name == "power" and isinstance(easing, Mapping):
        exponent = _number(easing.get("exponent", 1), "power exponent")
        return exponent if exponent > 0 else None
    return _ASS_ACCELERATION.get(name)


def _baked_step_count(easing: Any) -> int:
    """Sub-segments needed to bake ``easing``; 0 when a plain/accel ``\\t`` is exact."""
    name = _easing_name(easing)
    if name == "spring":
        spec = easing if isinstance(easing, Mapping) else {}
        mass = _number(spec.get("mass", 1) or 1, "spring mass")
        stiffness = _number(spec.get("stiffness", 100) or 100, "spring stiffness")
        cycles = math.sqrt(stiffness / mass) / (2 * math.pi)
        return max(12, min(48, int(math.ceil(cycles * 12))))  # ~12 samples per oscillation
    return _BAKED_EASING_STEPS.get(name, 0)


def _transition(
    start_ms: int,
    end_ms: int,
    easing: Any,
    track: str,
    from_value: Any,
    to_value: Any,
    *,
    scale_base: float,
    canvas_px_scale: float,
) -> str:
    def tags_for(value: Any) -> str:
        return _tag_for_value(track, value, scale_base=scale_base, canvas_px_scale=canvas_px_scale)

    if _easing_name(easing) == "step":
        # Contract: hold the start value, jump on the last tick of the segment.
        return f"\\t({max(start_ms, end_ms - 1)},{end_ms},{tags_for(to_value)})"

    steps = _baked_step_count(easing)
    if steps and end_ms - start_ms > 1:
        span = end_ms - start_ms
        start_number = _number(from_value, f"{track} value")
        delta = _number(to_value, f"{track} value") - start_number
        bounds = sorted({start_ms + int(round(span * index / steps)) for index in range(steps + 1)})
        parts = []
        for left, right in zip(bounds, bounds[1:]):
            # The segment must land exactly on its keyframe (spring(1) overshoots).
            progress = 1.0 if right == end_ms else _easing_progress(easing, (right - start_ms) / span)
            parts.append(f"\\t({left},{right},{tags_for(start_number + delta * progress)})")
        return "".join(parts)

    acceleration = _easing_acceleration(easing)
    if acceleration is None:
        return f"\\t({start_ms},{end_ms},{tags_for(to_value)})"
    return f"\\t({start_ms},{end_ms},{acceleration:g},{tags_for(to_value)})"


def _keyframe_segments(
    track_name: str,
    track: Mapping[str, Any],
    *,
    start_ms: int,
    end_ms: int,
    scale_base: float,
    canvas_px_scale: float,
) -> Iterable[AssMotionSegment]:
    points = list(track["keyframes"])
    duration = end_ms - start_ms
    for left, right in zip(points, points[1:]):
        left_t = float(left["t"])
        right_t = float(right["t"])
        segment_start = start_ms + int(round(duration * left_t))
        segment_end = start_ms + int(round(duration * right_t))
        if segment_end <= segment_start:
            continue
        yield AssMotionSegment(
            track=track_name,
            start_ms=segment_start,
            end_ms=segment_end,
            from_value=left["value"],
            to_value=right["value"],
            easing=right.get("easing", "linear"),
            ass_tags=(
                ""
                if track_name == "dy"
                else _transition(
                    segment_start,
                    segment_end,
                    right.get("easing", "linear"),
                    track_name,
                    left["value"],
                    right["value"],
                    scale_base=scale_base,
                    canvas_px_scale=canvas_px_scale,
                )
            ),
        )


def _repeat_segments(
    track_name: str,
    track: Mapping[str, Any],
    *,
    start_ms: int,
    end_ms: int,
    cycle_duration_ms: int,
    scale_base: float,
    canvas_px_scale: float,
) -> Iterable[AssMotionSegment]:
    cursor = start_ms
    while cursor < end_ms:
        cycle_end = min(end_ms, cursor + cycle_duration_ms)
        if cycle_end - cursor < cycle_duration_ms:
            points = list(track["keyframes"])
            first = points[0]
            last = points[-1]
            if cycle_end > cursor:
                yield AssMotionSegment(
                    track=track_name,
                    start_ms=cursor,
                    end_ms=cycle_end,
                    from_value=first["value"],
                    to_value=last["value"],
                    easing=last.get("easing", "linear"),
                    ass_tags=(
                        ""
                        if track_name == "dy"
                        else _transition(
                            cursor,
                            cycle_end,
                            last.get("easing", "linear"),
                            track_name,
                            first["value"],
                            last["value"],
                            scale_base=scale_base,
                            canvas_px_scale=canvas_px_scale,
                        )
                    ),
                )
            break
        yield from _keyframe_segments(
            track_name,
            track,
            start_ms=cursor,
            end_ms=cycle_end,
            scale_base=scale_base,
            canvas_px_scale=canvas_px_scale,
        )
        if cycle_end <= cursor:
            break
        cursor = cycle_end


def _unsupported(track: str, reason: str) -> Dict[str, str]:
    return {"track": track, "reason": reason}


def build_ass_motion_segments(
    contract: Mapping[str, Any],
    *,
    start_ms: Any = 0,
    end_ms: Any = None,
    base_scale: Any = 100.0,
    scale_base: Any = None,
    base_position: Optional[Tuple[Any, Any]] = None,
    canvas_px_scale: Any = 1.0,
    unsupported: str = "report",
) -> AssMotionPlan:
    """Build ASS tags for one contract inside a bounded millisecond window.

    ``unsupported='report'`` is the export-safe default: unsupported tracks
    are omitted and returned in ``plan.unsupported``.  ``'error'`` is useful
    for strict validation and tests.  No legacy fallback occurs inside this
    function; the caller decides whether to use the legacy renderer.
    """

    if unsupported not in {"report", "error"}:
        raise MotionAssAdapterError("unsupported must be 'report' or 'error'")
    try:
        validate_motion_contract(contract)
    except MotionContractError as exc:
        raise MotionAssAdapterError(str(exc)) from exc

    window_start = max(0, _integer(start_ms))
    if end_ms is None:
        end_ms = window_start + _integer(contract.get("duration_ms", 0))
    window_end = _integer(end_ms)
    if window_end < window_start:
        window_end = window_start

    resolved_scale_base = base_scale if scale_base is None else scale_base
    scale_base_value = _number(resolved_scale_base, "scale base")
    if scale_base_value <= 0:
        raise MotionAssAdapterError("scale base must be greater than zero")
    canvas_px_scale_value = _number(canvas_px_scale, "canvas px scale")
    if canvas_px_scale_value <= 0:
        raise MotionAssAdapterError("canvas px scale must be greater than zero")

    initial_parts = []
    segments = []
    unsupported_tracks = []
    tracks = contract.get("tracks", {})

    for track_name, track in tracks.items():
        points = list(track["keyframes"])
        first_value = points[0]["value"]
        if track_name in {"scale", "alpha", "rotation", "blur"}:
            initial_parts.append(_tag_for_value(
                track_name,
                first_value,
                scale_base=scale_base_value,
                canvas_px_scale=canvas_px_scale_value,
            ))
            if window_end > window_start:
                if track.get("repeat") or contract.get("repeat") and track.get("cycle_duration_ms"):
                    cycle = int(round(_number(track.get("cycle_duration_ms") or contract.get("duration_ms"), "cycle duration")))
                    cycle = max(1, cycle)
                    segments.extend(_repeat_segments(
                        track_name,
                        track,
                        start_ms=window_start,
                        end_ms=window_end,
                        cycle_duration_ms=cycle,
                        scale_base=scale_base_value,
                        canvas_px_scale=canvas_px_scale_value,
                    ))
                else:
                    segments.extend(_keyframe_segments(
                        track_name,
                        track,
                        start_ms=window_start,
                        end_ms=window_end,
                        scale_base=scale_base_value,
                        canvas_px_scale=canvas_px_scale_value,
                    ))
            continue

        if track_name == "dy" and base_position is not None:
            x = _number(base_position[0], "base x")
            y = _number(base_position[1], "base y")
            initial_y = y + _number(first_value, "dy") * canvas_px_scale_value
            initial_parts.append(f"\\pos({x:g},{initial_y:g})")
            if window_end > window_start:
                for segment in _keyframe_segments(
                    track_name,
                    track,
                    start_ms=window_start,
                    end_ms=window_end,
                    scale_base=scale_base_value,
                    canvas_px_scale=canvas_px_scale_value,
                ):
                    from_y = y + _number(segment.from_value, "dy") * canvas_px_scale_value
                    to_y = y + _number(segment.to_value, "dy") * canvas_px_scale_value
                    move = f"\\move({x:g},{from_y:g},{x:g},{to_y:g},{segment.start_ms},{segment.end_ms})"
                    segments.append(AssMotionSegment(
                        track=segment.track,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        from_value=segment.from_value,
                        to_value=segment.to_value,
                        easing=segment.easing,
                        ass_tags=move,
                    ))
            continue

        if track_name == "dy":
            item = _unsupported(track_name, "ASS dy needs base_position context.")
        elif track_name == "position":
            item = _unsupported(track_name, "ASS position needs a coordinate-aware event context.")
        elif track_name == "reveal":
            item = _unsupported(track_name, "ASS reveal needs text geometry or a clip rectangle; the normalized contract has no glyph bounds.")
        else:
            item = _unsupported(track_name, "ASS adapter does not support this track.")
        unsupported_tracks.append(item)

    if unsupported == "error" and unsupported_tracks:
        names = ", ".join(item["track"] for item in unsupported_tracks)
        raise UnsupportedMotionPropertyError(f"Unsupported motion properties for ASS: {names}")

    return AssMotionPlan(
        contract_id=str(contract["id"]),
        phase=str(contract["phase"]),
        window_ms={"start": window_start, "end": window_end},
        initial_tags="".join(initial_parts),
        segments=tuple(segments),
        unsupported=tuple(unsupported_tracks),
    )


def adapt_motion_contract(*args: Any, **kwargs: Any) -> AssMotionPlan:
    """Compatibility alias for callers that prefer the adapter terminology."""

    return build_ass_motion_segments(*args, **kwargs)


def adapt_motion_preset(
    role: str,
    phase: str,
    preset_id: str,
    **kwargs: Any,
) -> Optional[AssMotionPlan]:
    """Resolve a catalog preset and adapt it, returning ``None`` if unknown."""

    contract = get_motion_preset(role, phase, preset_id)
    if contract is None:
        return None
    return build_ass_motion_segments(contract, **kwargs)


def resolve_motion_contract_id(
    contract_id: Any,
    *,
    role: str,
    phase: str,
) -> Optional[Mapping[str, Any]]:
    """Resolve ``role.phase.preset`` or bare preset ids without raising.

    Unknown ids intentionally return ``None`` so export callers can preserve
    the legacy path for old or partially migrated project files.
    """

    if not isinstance(contract_id, str) or not contract_id.strip():
        return None
    raw = contract_id.strip()
    parts = raw.split(".")
    preset_id = parts[-1]
    if len(parts) >= 3:
        if parts[-3] != role or parts[-2] != phase:
            return None
    return get_motion_preset(role, phase, preset_id)
