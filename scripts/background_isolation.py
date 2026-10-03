"""Safe BackgroundIsolationV1 contract for product subject cutouts.

This module is deliberately pure.  It does not import ``rembg``, open media,
write cache files, or invoke FFmpeg.  Phase 1 only defines the data boundary
that the future preprocess worker, Preview, and Render must share.  Keeping
the boundary independent prevents an accidental per-frame inference call in
the existing render graph.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from scripts.cutout_prompt import normalize_subject_points


SCHEMA_VERSION = 1
ARTIFACT_SCHEMA_VERSION = 1
SUPPORTED_MODES = ("cutout",)
SUPPORTED_ENGINES = ("rembg", "sam2")
SUPPORTED_MODELS = (
    "u2netp", "u2net", "isnet-general-use",
    "sam2.1_hiera_tiny", "sam2.1_hiera_small", "sam2.1_hiera_base_plus"
)
SUPPORTED_QUALITIES = ("draft", "balanced", "quality")
SUPPORTED_FALLBACKS = ("spotlight", "original", "skip")
ARTIFACT_STATUSES = ("missing", "processing", "ready", "stale", "error")
DEFAULT_MODE = "cutout"
DEFAULT_ENGINE = "rembg"
# The compact model is fast but tends to absorb hands/background on close-up
# product footage. Use the fuller model for new jobs; persisted configs keep
# their explicit model so existing artifacts are never silently replaced.
DEFAULT_MODEL = "u2net"
DEFAULT_QUALITY = "balanced"
DEFAULT_FALLBACK = "spotlight"
DEFAULT_ARTIFACT_STATUS = "missing"
MAX_SOURCE_FINGERPRINT_LENGTH = 256
MAX_ARTIFACT_ID_LENGTH = 80
_ARTIFACT_ID_RE = re.compile(r"^bgiso1-[0-9a-f]{16}$")


def _no_op(reason: str) -> dict[str, Any]:
    """Return a stable disabled contract for missing or invalid input."""

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": False,
        "mode": DEFAULT_MODE,
        "engine": DEFAULT_ENGINE,
        "model": DEFAULT_MODEL,
        "quality": DEFAULT_QUALITY,
        "fallback": DEFAULT_FALLBACK,
        "artifact": {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "id": None,
            "status": DEFAULT_ARTIFACT_STATUS,
        },
        "reason": reason,
    }


def _normalise_choice(value: Any, allowed: tuple[str, ...], default: str) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    return candidate if candidate in allowed else None


def _normalise_source_fingerprint(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_SOURCE_FINGERPRINT_LENGTH:
        return None
    return candidate


def _normalise_artifact(value: Any) -> dict[str, Any] | None:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        return None

    schema_version = value.get("schema_version", ARTIFACT_SCHEMA_VERSION)
    if schema_version != ARTIFACT_SCHEMA_VERSION:
        return None

    artifact_id = value.get("id")
    if artifact_id is not None:
        if not isinstance(artifact_id, str) or len(artifact_id) > MAX_ARTIFACT_ID_LENGTH or not _ARTIFACT_ID_RE.fullmatch(artifact_id):
            return None

    status = _normalise_choice(value.get("status"), ARTIFACT_STATUSES, DEFAULT_ARTIFACT_STATUS)
    if status is None:
        return None
    if status == "ready" and artifact_id is None:
        return None

    source_fingerprint = _normalise_source_fingerprint(value.get("source_fingerprint"))
    if "source_fingerprint" in value and value.get("source_fingerprint") is not None and source_fingerprint is None:
        return None

    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "id": artifact_id,
        "status": status,
        **({"source_fingerprint": source_fingerprint} if source_fingerprint else {}),
    }


def normalize_background_isolation(value: Any) -> dict[str, Any]:
    """Return a canonical, safe BackgroundIsolationV1 dictionary.

    The feature is opt-in.  A missing value, unsupported schema, invalid
    engine/model, or malformed artifact becomes a disabled no-op.  An enabled
    contract without a ready artifact is still valid, but its declared
    fallback must be used by the future consumer.
    """

    if value is None:
        return _no_op("missing")
    if not isinstance(value, Mapping):
        return _no_op("invalid_config")

    schema_version = value.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        return _no_op("unsupported_schema")

    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        return _no_op("invalid_enabled")
    if not enabled:
        return _no_op("disabled")

    mode = _normalise_choice(value.get("mode"), SUPPORTED_MODES, DEFAULT_MODE)
    engine_default = "sam2" if str(value.get("model", "")).startswith("sam2.") else DEFAULT_ENGINE
    engine = _normalise_choice(value.get("engine"), SUPPORTED_ENGINES, engine_default)
    model_default = "sam2.1_hiera_tiny" if engine == "sam2" else DEFAULT_MODEL
    model = _normalise_choice(value.get("model"), SUPPORTED_MODELS, model_default)
    quality = _normalise_choice(value.get("quality"), SUPPORTED_QUALITIES, DEFAULT_QUALITY)
    fallback = _normalise_choice(value.get("fallback"), SUPPORTED_FALLBACKS, DEFAULT_FALLBACK)
    if None in (mode, engine, model, quality, fallback):
        return _no_op("invalid_option")
    if (engine == "sam2") != model.startswith("sam2."):
        return _no_op("invalid_engine_model")

    artifact = _normalise_artifact(value.get("artifact"))
    if artifact is None:
        return _no_op("invalid_artifact")

    temporal_mode = value.get("temporal_mode")
    if temporal_mode is not None and temporal_mode not in ("legacy", "motion", "off"):
        return _no_op("invalid_temporal_mode")
    request_id = value.get("request_id")
    if request_id is not None and (not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,80}", request_id)):
        return _no_op("invalid_request_id")
    auto_prompt = value.get("auto_prompt")
    if auto_prompt is not None and not isinstance(auto_prompt, bool):
        return _no_op("invalid_auto_prompt")
    # Points picked in the editor are clamped and capped here as well, so the
    # worker can trust every coordinate it receives.
    subject_points = normalize_subject_points(value.get("subject_points"))

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "mode": mode,
        "engine": engine,
        "model": model,
        "quality": quality,
        "fallback": fallback,
        "artifact": artifact,
        **({"temporal_mode": temporal_mode} if temporal_mode is not None else {}),
        **({"request_id": request_id} if request_id is not None else {}),
        **({"subject_points": subject_points} if subject_points else {}),
        **({"auto_prompt": False} if auto_prompt is False else {}),

    }


def is_no_op(value: Any) -> bool:
    """Return whether the value resolves to the disabled contract."""

    return not normalize_background_isolation(value)["enabled"]


def artifact_is_ready(value: Any) -> bool:
    """Return whether a normalized config can consume a foreground artifact."""

    normalized = normalize_background_isolation(value)
    artifact = normalized["artifact"]
    return normalized["enabled"] and artifact["status"] == "ready" and bool(artifact["id"])


def build_artifact_id(source_fingerprint: Any, value: Any) -> str | None:
    """Build a deterministic cache identity without reading the source file.

    The caller supplies a stable source fingerprint (for example path + size
    + mtime or a content hash).  The persisted artifact id includes only the
    source fingerprint and segmentation settings, never an absolute path.
    """

    fingerprint = _normalise_source_fingerprint(source_fingerprint)
    normalized = normalize_background_isolation(value)
    if not normalized["enabled"] or fingerprint is None:
        return None

    identity = {
        "source_fingerprint": fingerprint,
        "mode": normalized["mode"],
        "engine": normalized["engine"],
        "model": normalized["model"],
        "quality": normalized["quality"],
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"bgiso1-{digest}"


def with_artifact_id(value: Any, source_fingerprint: Any) -> dict[str, Any]:
    """Return a canonical config carrying the shared Preview/Render identity.

    This helper marks the artifact ``missing`` until a worker has actually
    produced it.  It therefore cannot accidentally make an unfinished cache
    look renderable.
    """

    normalized = normalize_background_isolation(value)
    if not normalized["enabled"]:
        return normalized
    artifact_id = build_artifact_id(source_fingerprint, normalized)
    artifact = dict(normalized["artifact"])
    artifact.update({"id": artifact_id, "status": "missing"})
    return {**normalized, "artifact": artifact}


def serialize_background_isolation(value: Any) -> str:
    """Serialize the canonical contract with stable key ordering."""

    return json.dumps(
        normalize_background_isolation(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_background_isolation(value: Any) -> dict[str, Any]:
    """Parse JSON safely; malformed payloads become a disabled no-op."""

    if not isinstance(value, str):
        return _no_op("invalid_serialized_config")
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return _no_op("invalid_serialized_config")
    return normalize_background_isolation(decoded)
