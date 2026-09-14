"""Pure Preview/Render seam for compositing subject-isolation sequences.

This module deliberately contains no media, filesystem, subprocess, or model
runtime code.  It turns a validated sequence manifest into a deterministic
per-clip plan.  The future Preview and Render callers can consume the same
plan, which keeps the important ordering explicit:

    source trim -> source transform -> alpha composite -> transition/concat
    -> subtitle and callout overlays

An unavailable sequence never becomes an active compositor.  It resolves to
the configured legacy fallback (``spotlight`` by default), preserving the
existing default/no-op path until a complete artifact is available.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from .background_isolation import (
    DEFAULT_ENGINE,
    DEFAULT_FALLBACK,
    DEFAULT_MODE,
    DEFAULT_MODEL,
    DEFAULT_QUALITY,
    SUPPORTED_ENGINES,
    SUPPORTED_FALLBACKS,
    SUPPORTED_MODES,
    SUPPORTED_MODELS,
    SUPPORTED_QUALITIES,
)


COMPOSITOR_SCHEMA_VERSION = 1
SEQUENCE_FRAME_PATTERN = "frames/frame_%06d.png"
SEQUENCE_STATUSES = frozenset(
    {"missing", "processing", "ready", "stale", "error", "cancelled"}
)
_READY = "ready"
_ARTIFACT_ID_RE = re.compile(r"^bgseq1-[0-9a-f]{16}$")
_STREAM_LABEL_RE = re.compile(r"^\[[A-Za-z_][A-Za-z0-9_]*\]$")
_TIMEBASE_RE = re.compile(r"^[1-9][0-9]*/[1-9][0-9]*$")
_FALLBACK_REASONS = frozenset(
    {
        "missing",
        "disabled",
        "invalid_config",
        "invalid_enabled",
        "invalid_option",
        "invalid_artifact",
        "invalid_metadata",
        "artifact_missing",
        "artifact_processing",
        "artifact_stale",
        "artifact_error",
        "artifact_cancelled",
        "artifact_not_ready",
        "artifact_mismatch",
    }
)


class CompositorValidationError(ValueError):
    """Raised when a direct mapping/filter input cannot be made deterministic."""


def _fallback(value: Any) -> str:
    if isinstance(value, str) and value.strip().lower() in SUPPORTED_FALLBACKS:
        return value.strip().lower()
    return DEFAULT_FALLBACK


def _disabled(
    reason: str,
    *,
    fallback: str = DEFAULT_FALLBACK,
    requested_enabled: bool = False,
    artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stable inactive plan/config without dropping fallback intent."""

    artifact_value = artifact or {"id": None, "status": "missing"}
    return {
        "schema_version": COMPOSITOR_SCHEMA_VERSION,
        "enabled": False,
        "requested_enabled": requested_enabled,
        "ready": False,
        "mode": DEFAULT_MODE,
        "engine": DEFAULT_ENGINE,
        "model": DEFAULT_MODEL,
        "quality": DEFAULT_QUALITY,
        "fallback": _fallback(fallback),
        "artifact": dict(artifact_value),
        "sequence": None,
        "reason": reason if reason in _FALLBACK_REASONS else "invalid_config",
    }


def _positive_ratio(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise CompositorValidationError(f"invalid {label}")
    if isinstance(value, (tuple, list)) and len(value) == 2:
        value = f"{value[0]}/{value[1]}"
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        if not numerator.isdigit() or not denominator.isdigit():
            raise CompositorValidationError(f"invalid {label}")
        result = Fraction(int(numerator), int(denominator))
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise CompositorValidationError(f"invalid {label}")
        result = Fraction(str(value))
    else:
        raise CompositorValidationError(f"invalid {label}")
    if result <= 0:
        raise CompositorValidationError(f"invalid {label}")
    return result


def _ratio_text(value: Any, label: str) -> str:
    ratio = _positive_ratio(value, label)
    return f"{ratio.numerator}/{ratio.denominator}"


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CompositorValidationError(f"invalid {label}")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 256:
        raise CompositorValidationError(f"invalid {label}")
    return value.strip()


def _artifact(value: Any) -> dict[str, Any]:
    if value is None:
        return {"id": None, "status": "missing"}
    if not isinstance(value, Mapping):
        raise CompositorValidationError("invalid artifact")
    artifact_id = value.get("sequence_id", value.get("id"))
    if artifact_id is not None and (
        not isinstance(artifact_id, str) or not _ARTIFACT_ID_RE.fullmatch(artifact_id)
    ):
        raise CompositorValidationError("invalid artifact id")
    status = value.get("status", "missing")
    if not isinstance(status, str) or status.strip().lower() not in SEQUENCE_STATUSES:
        raise CompositorValidationError("invalid artifact status")
    result = {"id": artifact_id, "status": status.strip().lower()}
    if result["status"] == _READY and result["id"] is None:
        raise CompositorValidationError("ready artifact requires a sequence id")
    if value.get("source_fingerprint") is not None:
        result["source_fingerprint"] = _text(
            value["source_fingerprint"], "source fingerprint"
        )
    if value.get("sequence_id") is not None:
        result["sequence_id"] = artifact_id
    return result


def _manifest(value: Any) -> dict[str, Any]:
    """Validate the metadata needed by both consumers without reading cache files."""

    if not isinstance(value, Mapping):
        raise CompositorValidationError("invalid metadata")
    if value.get("schema_version") != 1:
        raise CompositorValidationError("unsupported sequence schema")
    artifact_id = _text(value.get("artifact_id"), "sequence artifact id")
    if not _ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise CompositorValidationError("invalid sequence artifact id")
    status = value.get("status")
    if not isinstance(status, str) or status.strip().lower() not in SEQUENCE_STATUSES:
        raise CompositorValidationError("invalid sequence status")
    frame_count = _positive_int(value.get("frame_count"), "frame count")
    fps = _positive_ratio(value.get("fps"), "fps")
    timebase = _ratio_text(value.get("timebase"), "timebase")
    width = _positive_int(value.get("width"), "width")
    height = _positive_int(value.get("height"), "height")
    rotation = value.get("rotation", 0)
    if isinstance(rotation, bool) or rotation not in (0, 90, 180, 270):
        raise CompositorValidationError("invalid rotation")
    frame_pattern = value.get("frame_pattern", SEQUENCE_FRAME_PATTERN)
    if frame_pattern != SEQUENCE_FRAME_PATTERN:
        raise CompositorValidationError("invalid frame pattern")
    result = {
        "schema_version": value.get("schema_version", 1),
        "artifact_id": artifact_id,
        "status": status.strip().lower(),
        "frame_count": frame_count,
        "fps": float(fps) if fps.denominator != 1 else fps.numerator,
        "fps_ratio": f"{fps.numerator}/{fps.denominator}",
        "timebase": timebase,
        "width": width,
        "height": height,
        "rotation": rotation,
        "frame_pattern": SEQUENCE_FRAME_PATTERN,
    }
    for key in ("source_fingerprint", "algorithm", "engine", "model", "quality", "worker_version"):
        result[key] = _text(value.get(key), key.replace("_", " "))
    return result


def normalize_compositor_config(
    value: Any,
    sequence_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a config and activate it only when its sequence is ready.

    ``enabled`` is intentionally ``False`` for an incomplete artifact.  The
    original request is retained as ``requested_enabled`` so UI/task layers
    can explain why fallback was selected without accidentally rendering an
    incomplete sequence.
    """

    if value is None:
        return _disabled("missing")
    if not isinstance(value, Mapping):
        return _disabled("invalid_config")
    requested_enabled = value.get("enabled", False)
    if not isinstance(requested_enabled, bool):
        return _disabled("invalid_enabled")
    fallback = _fallback(value.get("fallback"))
    if not requested_enabled:
        return _disabled("disabled", fallback=fallback)
    raw_fallback = value.get("fallback")
    if raw_fallback is not None and (
        not isinstance(raw_fallback, str)
        or raw_fallback.strip().lower() not in SUPPORTED_FALLBACKS
    ):
        return _disabled("invalid_option", fallback=fallback, requested_enabled=True)

    choices = {}
    for key, allowed, default in (
        ("mode", SUPPORTED_MODES, DEFAULT_MODE),
        ("engine", SUPPORTED_ENGINES, DEFAULT_ENGINE),
        ("model", SUPPORTED_MODELS, DEFAULT_MODEL),
        ("quality", SUPPORTED_QUALITIES, DEFAULT_QUALITY),
    ):
        raw = value.get(key, default)
        if not isinstance(raw, str) or raw.strip().lower() not in allowed:
            return _disabled("invalid_option", fallback=fallback, requested_enabled=True)
        choices[key] = raw.strip().lower()

    try:
        artifact = _artifact(value.get("artifact"))
    except CompositorValidationError:
        return _disabled("invalid_artifact", fallback=fallback, requested_enabled=True)
    if artifact["status"] != _READY:
        reason = f"artifact_{artifact['status']}" if artifact["status"] in {"missing", "processing", "stale", "error", "cancelled"} else "artifact_not_ready"
        return _disabled(reason, fallback=fallback, requested_enabled=True, artifact=artifact)

    manifest_value = sequence_manifest
    if manifest_value is None and isinstance(value.get("sequence"), Mapping):
        manifest_value = value["sequence"]
    try:
        manifest = _manifest(manifest_value)
    except CompositorValidationError:
        return _disabled("invalid_metadata", fallback=fallback, requested_enabled=True, artifact=artifact)
    if manifest["status"] != _READY:
        reason = f"artifact_{manifest['status']}" if manifest["status"] in {"missing", "processing", "stale", "error", "cancelled"} else "artifact_not_ready"
        return _disabled(reason, fallback=fallback, requested_enabled=True, artifact=artifact)
    if artifact["id"] is not None and artifact["id"] != manifest["artifact_id"]:
        return _disabled("artifact_mismatch", fallback=fallback, requested_enabled=True, artifact=artifact)
    if artifact.get("source_fingerprint") is not None and artifact["source_fingerprint"] != manifest["source_fingerprint"]:
        return _disabled("artifact_mismatch", fallback=fallback, requested_enabled=True, artifact=artifact)

    return {
        "schema_version": COMPOSITOR_SCHEMA_VERSION,
        "enabled": True,
        "requested_enabled": True,
        "ready": True,
        **choices,
        "fallback": fallback,
        "artifact": artifact,
        "sequence": manifest,
        "reason": "ready",
    }


def artifact_is_composable(
    value: Any,
    sequence_manifest: Mapping[str, Any] | None = None,
) -> bool:
    """Return true only for an enabled, validated, ready sequence."""

    return normalize_compositor_config(value, sequence_manifest)["enabled"] is True


def map_source_time_to_frame_index(
    source_time: int | float | str,
    *,
    fps: Any,
    timebase: Any,
    frame_count: int,
    source_time_unit: str = "seconds",
) -> int:
    """Map source time to a zero-based frame index with floor + clamp.

    ``source_time`` is seconds by default.  It is first quantized to the
    source timebase (floor), then converted to a frame number (floor).  This
    makes exact frame-boundary behaviour stable across Preview and Render.
    Pass ``source_time_unit='ticks'`` when the caller already has an integer
    PTS in the supplied timebase.
    """

    count = _positive_int(frame_count, "frame count")
    fps_ratio = _positive_ratio(fps, "fps")
    timebase_ratio = _positive_ratio(timebase, "timebase")
    try:
        time_value = Fraction(str(source_time))
    except (ValueError, ZeroDivisionError):
        raise CompositorValidationError("invalid source time") from None
    if time_value.denominator <= 0:
        raise CompositorValidationError("invalid source time")
    if source_time_unit == "seconds":
        # A Python float such as ``1 / 30`` can be a few ulps below the exact
        # boundary.  The tiny rational epsilon accepts that representation,
        # while values materially before the boundary (for example 0.033333333)
        # still remain in the preceding timebase tick.
        boundary_epsilon = Fraction(1, 10**12)
        pts = math.floor(time_value / timebase_ratio + boundary_epsilon)
        effective_seconds = Fraction(pts) * timebase_ratio
    elif source_time_unit == "ticks":
        if time_value.denominator != 1:
            raise CompositorValidationError("tick source time must be an integer")
        effective_seconds = time_value * timebase_ratio
    else:
        raise CompositorValidationError("invalid source time unit")
    raw_index = math.floor(effective_seconds * fps_ratio)
    return max(0, min(raw_index, count - 1))


def _stream_label(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _STREAM_LABEL_RE.fullmatch(value):
        raise CompositorValidationError(f"invalid {label} stream label")
    return value


def build_alpha_composite_filter_fragment(
    *,
    source_stream: str = "[clip_transformed]",
    foreground_stream: str = "[foreground_frame]",
    alpha_stream: str = "[alpha_frame]",
    output_stream: str = "[clip_composited]",
    subject_stream: str = "[subject_rgba]",
) -> str:
    """Build the small FFmpeg fragment used after per-clip transform.

    The caller owns trim, transform, transition, concat, and text overlays.
    Labels are restricted to FFmpeg stream labels so this helper remains a
    safe pure string builder rather than a command/path execution layer.
    """

    source = _stream_label(source_stream, "source")
    foreground = _stream_label(foreground_stream, "foreground")
    alpha = _stream_label(alpha_stream, "alpha")
    output = _stream_label(output_stream, "output")
    subject = _stream_label(subject_stream, "subject")
    return (
        f"{foreground}{alpha}alphamerge{subject};"
        f"{source}{subject}overlay=eof_action=pass:format=auto{output}"
    )


def build_compositing_plan(
    config: Any,
    sequence_manifest: Mapping[str, Any] | None = None,
    source_time: int | float | str = 0,
    *,
    source_time_unit: str = "seconds",
    source_stream: str = "[clip_transformed]",
    foreground_stream: str = "[foreground_frame]",
    alpha_stream: str = "[alpha_frame]",
    output_stream: str = "[clip_composited]",
) -> dict[str, Any]:
    """Create a shared per-clip compositor plan or a legacy fallback plan."""

    normalized = normalize_compositor_config(config, sequence_manifest)
    if not normalized["enabled"]:
        return {
            "schema_version": COMPOSITOR_SCHEMA_VERSION,
            "enabled": False,
            "action": "fallback",
            "fallback": normalized["fallback"],
            "reason": normalized["reason"],
            "stage_order": ["legacy_source", "legacy_effects", "legacy_overlays"],
            "config": normalized,
        }

    sequence = normalized["sequence"]
    try:
        frame_index = map_source_time_to_frame_index(
            source_time,
            fps=sequence["fps_ratio"],
            timebase=sequence["timebase"],
            frame_count=sequence["frame_count"],
            source_time_unit=source_time_unit,
        )
        fragment = build_alpha_composite_filter_fragment(
            source_stream=source_stream,
            foreground_stream=foreground_stream,
            alpha_stream=alpha_stream,
            output_stream=output_stream,
        )
    except CompositorValidationError:
        return {
            "schema_version": COMPOSITOR_SCHEMA_VERSION,
            "enabled": False,
            "action": "fallback",
            "fallback": normalized["fallback"],
            "reason": "invalid_metadata",
            "stage_order": ["legacy_source", "legacy_effects", "legacy_overlays"],
            "config": _disabled(
                "invalid_metadata",
                fallback=normalized["fallback"],
                requested_enabled=True,
                artifact=normalized["artifact"],
            ),
        }

    frame_path = sequence["frame_pattern"] % frame_index
    stage_order = [
        "source_trim",
        "source_transform",
        "alpha_composite",
        "transition",
        "concat",
        "subtitle_callout_overlays",
    ]
    return {
        "schema_version": COMPOSITOR_SCHEMA_VERSION,
        "enabled": True,
        "action": "composite",
        "fallback": None,
        "artifact_id": sequence["artifact_id"],
        "frame_index": frame_index,
        "frame_path": frame_path,
        "filter_fragment": fragment,
        "stage_order": stage_order,
        "alpha_applied_after": ["source_trim", "source_transform"],
        "alpha_applied_before": ["transition", "concat"],
        "operations": [
            {"stage": "source_trim", "output": "[clip_trimmed]"},
            {"stage": "source_transform", "input": "[clip_trimmed]", "output": source_stream},
            {
                "stage": "alpha_composite",
                "input": [source_stream, foreground_stream, alpha_stream],
                "output": output_stream,
                "filter": fragment,
                "frame_index": frame_index,
                "frame_path": frame_path,
            },
            {"stage": "transition", "input": output_stream},
            {"stage": "concat", "input": "[transition]"},
            {"stage": "subtitle_callout_overlays", "input": "[concat]"},
        ],
        "config": normalized,
    }


def build_ffmpeg_filter_fragment(**kwargs: Any) -> str:
    """Descriptive alias for callers that only need the alpha fragment."""

    return build_alpha_composite_filter_fragment(**kwargs)


def serialize_compositor_config(
    value: Any,
    sequence_manifest: Mapping[str, Any] | None = None,
) -> str:
    """Serialize the canonical compositor contract with stable key ordering."""

    return json.dumps(
        normalize_compositor_config(value, sequence_manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_compositor_config(value: Any) -> dict[str, Any]:
    """Deserialize safely; malformed or legacy payloads become a no-op."""

    if not isinstance(value, str):
        return _disabled("invalid_config")
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return _disabled("invalid_config")
    if not isinstance(decoded, Mapping):
        return _disabled("invalid_config")
    return normalize_compositor_config(decoded, decoded.get("sequence"))


__all__ = [
    "COMPOSITOR_SCHEMA_VERSION",
    "CompositorValidationError",
    "SEQUENCE_FRAME_PATTERN",
    "SEQUENCE_STATUSES",
    "artifact_is_composable",
    "build_alpha_composite_filter_fragment",
    "build_compositing_plan",
    "build_ffmpeg_filter_fragment",
    "deserialize_compositor_config",
    "map_source_time_to_frame_index",
    "normalize_compositor_config",
    "serialize_compositor_config",
]
