"""Renderer-agnostic declarative motion contract.

This module is a foundation seam only.  It deliberately does not import or
call the live ASS builders.  The values in ``MOTION_PRESETS`` are snapshots of
the current visual defaults so a later adapter can migrate one preset at a
time without changing behavior in this round.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Any, Dict, Mapping, MutableMapping, Sequence


MOTION_CONTRACT_VERSION = 1
MOTION_ROLES = ("text", "hook", "caption")
MOTION_PHASES = ("in", "loop", "out")
MOTION_TRACKS = ("scale", "alpha", "position", "dy", "rotation", "blur", "reveal")
MOTION_EASINGS = (
    "linear",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "power",
    "step",
    "sine_in_out",
    "spring",
)
MOTION_CONTRACT_SCHEMA = {
    "version": MOTION_CONTRACT_VERSION,
    "roles": MOTION_ROLES,
    "phases": MOTION_PHASES,
    "tracks": MOTION_TRACKS,
    "normalized_time": (0.0, 1.0),
}
_NUMBER_TRACKS = {"scale", "alpha", "dy", "rotation", "blur", "reveal"}


class MotionContractError(ValueError):
    """Raised when a declarative motion document is malformed."""


def _fail(message: str) -> None:
    raise MotionContractError(f"Invalid motion contract: {message}")


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        _fail(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        _fail(f"{label} must be a finite number")
    if not math.isfinite(number):
        _fail(f"{label} must be a finite number")
    return number


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be an object")
    return value


def _validate_value(track_name: str, value: Any) -> None:
    if track_name in _NUMBER_TRACKS:
        _finite(value, f"{track_name} value")
        return
    if track_name == "position":
        position = _object(value, "position value")
        _finite(position.get("x"), "position.x")
        _finite(position.get("y"), "position.y")
        return
    _fail(f"unsupported track {track_name}")


def _validate_easing(easing: Any) -> None:
    spec = {"name": easing} if isinstance(easing, str) else _object(easing, "easing")
    name = spec.get("name")
    if name not in MOTION_EASINGS:
        _fail(f"unsupported easing {name}")
    if name == "power":
        exponent = _finite(spec.get("exponent"), "power exponent")
        if exponent <= 0:
            _fail("power exponent must be greater than zero")
    if name == "spring":
        for key in ("mass", "stiffness", "damping"):
            if key in spec:
                _finite(spec[key], f"spring {key}")


def normalize_time(value: Any) -> float:
    """Clamp a finite sample time to the contract's normalized 0..1 domain."""

    time = _finite(value, "normalized time")
    return min(1.0, max(0.0, time))


def validate_motion_track(track_name: str, track: Mapping[str, Any]) -> bool:
    if track_name not in MOTION_TRACKS:
        _fail(f"unsupported track {track_name}")
    data = _object(track, f"{track_name} track")
    keyframes = data.get("keyframes")
    if not isinstance(keyframes, Sequence) or isinstance(keyframes, (str, bytes)) or not keyframes:
        _fail(f"{track_name} keyframes must be non-empty")

    previous_time = -1.0
    for index, keyframe in enumerate(keyframes):
        point = _object(keyframe, f"{track_name} keyframe {index}")
        time = _finite(point.get("t"), f"{track_name} keyframe {index}.t")
        if not 0 <= time <= 1:
            _fail(f"{track_name} keyframe {index}.t must be between 0 and 1")
        if time <= previous_time:
            _fail(f"{track_name} keyframe times must be strictly increasing")
        _validate_value(track_name, point.get("value"))
        if "easing" in point:
            _validate_easing(point["easing"])
        previous_time = time

    if "default" in data:
        _validate_value(track_name, data["default"])
    if "unit" in data and (not isinstance(data["unit"], str) or not data["unit"]):
        _fail(f"{track_name} unit must be a non-empty string")
    if "repeat" in data and not isinstance(data["repeat"], bool):
        _fail(f"{track_name} repeat must be boolean")
    if "cycle_duration_ms" in data:
        cycle = _finite(data["cycle_duration_ms"], f"{track_name} cycle_duration_ms")
        if cycle <= 0:
            _fail(f"{track_name} cycle_duration_ms must be greater than zero")
    return True


def validate_motion_contract(contract: Mapping[str, Any]) -> bool:
    data = _object(contract, "contract")
    if data.get("version") != MOTION_CONTRACT_VERSION:
        _fail(f"version must be {MOTION_CONTRACT_VERSION}")
    if not isinstance(data.get("id"), str) or not data["id"]:
        _fail("id must be a non-empty string")
    if data.get("role") not in MOTION_ROLES:
        _fail(f"unsupported role {data.get('role')}")
    if data.get("phase") not in MOTION_PHASES:
        _fail(f"unsupported phase {data.get('phase')}")
    duration = _finite(data.get("duration_ms"), "duration_ms")
    if duration < 0:
        _fail("duration_ms must not be negative")
    tracks = _object(data.get("tracks"), "tracks")
    for track_name, track in tracks.items():
        validate_motion_track(track_name, track)
    if "preset" in data and (not isinstance(data["preset"], str) or not data["preset"]):
        _fail("preset must be a non-empty string")
    if "metadata" in data:
        _object(data["metadata"], "metadata")
    return True


def _easing_progress(easing: Any, progress: float) -> float:
    spec = {"name": easing} if isinstance(easing, str) else (easing or {"name": "linear"})
    name = spec.get("name", "linear")
    t = min(1.0, max(0.0, progress))
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return t * (2 - t)
    if name == "ease_in_out":
        return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t
    if name == "power":
        return t ** float(spec.get("exponent", 1))
    if name == "step":
        return 1.0 if t >= 1 else 0.0
    if name == "sine_in_out":
        return -(math.cos(math.pi * t) - 1) / 2
    if name == "spring":
        mass = float(spec.get("mass", 1) or 1)
        stiffness = float(spec.get("stiffness", 100) or 100)
        damping = float(spec.get("damping", 10) or 10)
        frequency = math.sqrt(stiffness / mass)
        return 1 - math.exp(-damping * t / (2 * mass)) * math.cos(frequency * t)
    return t


def _interpolate(left: Any, right: Any, progress: float) -> Any:
    if isinstance(left, (int, float)) and not isinstance(left, bool):
        return float(left) + (float(right) - float(left)) * progress
    return {
        "x": float(left["x"]) + (float(right["x"]) - float(left["x"])) * progress,
        "y": float(left["y"]) + (float(right["y"]) - float(left["y"])) * progress,
    }


def sample_track(track_name: str, track: Mapping[str, Any], normalized_time: Any = 0.0) -> Any:
    validate_motion_track(track_name, track)
    time = normalize_time(normalized_time)
    points = list(track["keyframes"])
    if time <= float(points[0]["t"]):
        return deepcopy(points[0]["value"])
    if time >= float(points[-1]["t"]):
        return deepcopy(points[-1]["value"])
    for index in range(1, len(points)):
        right = points[index]
        if time <= float(right["t"]):
            left = points[index - 1]
            span = float(right["t"]) - float(left["t"])
            local = (time - float(left["t"])) / span
            progress = _easing_progress(right.get("easing", "linear"), local)
            return _interpolate(left["value"], right["value"], progress)
    return deepcopy(points[-1]["value"])


def sample_motion_contract(contract: Mapping[str, Any], normalized_time: Any = 0.0) -> Dict[str, Any]:
    validate_motion_contract(contract)
    return {
        track_name: sample_track(track_name, track, normalized_time)
        for track_name, track in contract["tracks"].items()
    }


def resolve_legacy_motion_id(role: str, phase: str, legacy_id: str) -> str:
    if role not in MOTION_ROLES:
        _fail(f"unsupported role {role}")
    if phase not in MOTION_PHASES:
        _fail(f"unsupported phase {phase}")
    if not isinstance(legacy_id, str) or not legacy_id:
        _fail("legacy id must be a non-empty string")
    return LEGACY_MOTION_IDS.get(role, {}).get(phase, {}).get(legacy_id, legacy_id)


LEGACY_MOTION_IDS = {
    "text": {"in": {"pop": "snap", "zoom": "pop_zoom", "stamp": "stamp", "fade": "quick_fade", "slide": "rise", "none": "none"}},
    "hook": {"in": {}, "loop": {}, "out": {}},
}


def _k(time: float, value: Any, easing: Any = "linear") -> Dict[str, Any]:
    return {"t": time, "value": value, "easing": easing}


def _track(keyframes: Sequence[Mapping[str, Any]], unit: str, **extra: Any) -> Dict[str, Any]:
    return {"keyframes": list(keyframes), "unit": unit, **extra}


def _contract(identifier: str, role: str, phase: str, duration_ms: float, tracks: Mapping[str, Any], **extra: Any) -> Dict[str, Any]:
    metadata = dict(extra.pop("metadata", {}))
    unsupported_tracks = [name for name in tracks if name in {"position", "reveal"}]
    renderer_bound = not unsupported_tracks
    parity_level = (
        "legacy_fallback"
        if unsupported_tracks
        else "bounded"
        if "blur" in tracks or metadata.get("secondary_pass")
        else "exact"
    )
    contract = {
        "version": MOTION_CONTRACT_VERSION,
        "id": identifier,
        "preset": identifier,
        "role": role,
        "phase": phase,
        "duration_ms": duration_ms,
        "repeat": bool(extra.pop("repeat", False)),
        "tracks": dict(tracks),
        "metadata": {
            "source": "existing_visual_default",
            "renderer_bound": renderer_bound,
            "parity_level": parity_level,
            "unsupported_tracks": unsupported_tracks,
            **metadata,
        },
        **extra,
    }
    validate_motion_contract(contract)
    return contract


def _build_presets() -> Dict[str, Dict[str, Any]]:
    # The catalog intentionally mirrors the current frontend/backend numbers.
    in_defs = {
        "bounce": (450, {"scale": _track([_k(0, 0.6), _k(150 / 450, 1.25), _k(280 / 450, 0.92), _k(380 / 450, 1.05), _k(1, 1)], "ratio")}),
        "bounce_soft": (450, {"scale": _track([_k(0, 0.6), _k(150 / 450, 1.25, {"name": "power", "exponent": 0.6}), _k(280 / 450, 0.92), _k(380 / 450, 1.05), _k(1, 1, {"name": "power", "exponent": 0.6})], "ratio")}),
        "pop": (200, {"scale": _track([_k(0, 0.55), _k(120 / 200, 1.18), _k(1, 1)], "ratio")}),
        "pop_soft": (200, {"scale": _track([_k(0, 0.55), _k(120 / 200, 1.18, {"name": "power", "exponent": 0.6}), _k(1, 1, {"name": "power", "exponent": 2.2})], "ratio")}),
        "slam": (180, {"scale": _track([_k(0, 2.2), _k(1, 1, {"name": "power", "exponent": 2.2})], "ratio"), "alpha": _track([_k(0, 0), _k(50 / 180, 1)], "opacity")}),
        "elastic_bounce": (520, {"scale": _track([_k(0, 0.4), _k(160 / 520, 1.28, {"name": "power", "exponent": 0.6}), _k(290 / 520, 0.88), _k(390 / 520, 1.08), _k(460 / 520, 0.98), _k(1, 1, {"name": "power", "exponent": 0.6})], "ratio"), "alpha": _track([_k(0, 0), _k(40 / 520, 1)], "opacity")}),
        "fade": (250, {"alpha": _track([_k(0, 0), _k(1, 1)], "opacity")}),
        "zoom": (300, {"scale": _track([_k(0, 1.8), _k(1, 1)], "ratio"), "alpha": _track([_k(0, 0), _k(0.5, 1)], "opacity")}),
        "slide_up": (300, {"dy": _track([_k(0, 60), _k(1, 0)], "canvas_px"), "alpha": _track([_k(0, 0), _k(1, 1)], "opacity")}),
        "typewriter": (400, {"reveal": _track([_k(0, 0), _k(1, 1)], "ratio")}),
        "blur": (350, {"alpha": _track([_k(0, 0), _k(1, 1)], "opacity"), "blur": _track([_k(0, 12), _k(1, 0)], "canvas_px")}),
        "snap": (70, {"scale": _track([_k(0, 1.25), _k(1, 1)], "ratio")}),
        "pop_zoom": (100, {"scale": _track([_k(0, 1.45), _k(1, 1)], "ratio"), "alpha": _track([_k(0, 0), _k(0.7, 1)], "opacity")}),
        "stamp": (80, {"scale": _track([_k(0, 1.65), _k(1, 1)], "ratio")}),
        "quick_fade": (150, {"alpha": _track([_k(0, 0), _k(1, 1)], "opacity")}),
        "rise": (200, {"dy": _track([_k(0, 40), _k(1, 0)], "canvas_px"), "alpha": _track([_k(0, 0), _k(1, 1)], "opacity")}),
        "none": (0, {}),
    }
    loop_defs = {
        "pulse": (700, {"alpha": _track([_k(0, 1), _k(0.5, 1 - 0x25 / 255), _k(1, 1)], "opacity", repeat=True, cycle_duration_ms=700)}),
        "wave": (1200, {"rotation": _track([_k(0, 0), _k(1 / 3, -3), _k(2 / 3, 3), _k(1, 0)], "degrees", repeat=True, cycle_duration_ms=1200)}),
        "shake": (450, {"rotation": _track([_k(0, 0), _k(0.2, -3), _k(0.4, 3), _k(0.6, -2), _k(0.8, 2), _k(1, 0)], "degrees", repeat=True, cycle_duration_ms=450)}),
        "flicker": (760, {"alpha": _track([_k(0, 1), _k(80 / 760, 1 - 0x30 / 255), _k(230 / 760, 1), _k(290 / 760, 1 - 0x45 / 255), _k(490 / 760, 1), _k(580 / 760, 1 - 0x20 / 255), _k(1, 1)], "opacity", repeat=True, cycle_duration_ms=760, interpolation="linear")}),
        "lightsweep": (500, {}),
        "none": (0, {}),
    }
    out_defs = {
        "fade": (150, {"alpha": _track([_k(0, 1), _k(1, 0)], "opacity")}),
        "slide": (150, {"alpha": _track([_k(0, 1), _k(1, 0)], "opacity"), "dy": _track([_k(0, 0), _k(1, 60)], "canvas_px")}),
        "zoom": (150, {"alpha": _track([_k(0, 1), _k(1, 0)], "opacity"), "scale": _track([_k(0, 1), _k(1, 1.4)], "ratio")}),
        "glitch": (150, {"rotation": _track([_k(0, -3), _k(0.3636, 3), _k(0.7272, 0), _k(1, 0)], "degrees"), "alpha": _track([_k(0, 1), _k(0.7333, 1), _k(1, 0)], "opacity")}),
        "none": (1, {"alpha": _track([_k(0, 1), _k(0.999, 1), _k(1, 0)], "opacity")}),
    }
    result: Dict[str, Dict[str, Any]] = {}
    for name, (duration, tracks) in in_defs.items():
        result[f"hook.in.{name}"] = _contract(f"hook.in.{name}", "hook", "in", duration, tracks)
        if name in {"snap", "pop_zoom", "stamp", "quick_fade", "rise", "none"}:
            result[f"text.in.{name}"] = _contract(f"text.in.{name}", "text", "in", duration, tracks)
    for name, (duration, tracks) in loop_defs.items():
        result[f"hook.loop.{name}"] = _contract(f"hook.loop.{name}", "hook", "loop", duration, tracks, repeat=True, metadata={"secondary_pass": "lightsweep"} if name == "lightsweep" else {})
    for name, (duration, tracks) in out_defs.items():
        result[f"hook.out.{name}"] = _contract(f"hook.out.{name}", "hook", "out", duration, tracks)
    return result


MOTION_PRESETS = _build_presets()


def get_motion_preset(role: str, phase: str, preset_id: str) -> Dict[str, Any] | None:
    """Return a defensive copy of a catalog preset, if present."""

    return deepcopy(MOTION_PRESETS.get(f"{role}.{phase}.{preset_id}"))
