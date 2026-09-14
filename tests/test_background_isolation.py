from __future__ import annotations

import json

from scripts.background_isolation import (
    ARTIFACT_SCHEMA_VERSION,
    DEFAULT_ENGINE,
    DEFAULT_FALLBACK,
    DEFAULT_MODEL,
    DEFAULT_MODE,
    DEFAULT_QUALITY,
    SCHEMA_VERSION,
    artifact_is_ready,
    build_artifact_id,
    deserialize_background_isolation,
    is_no_op,
    normalize_background_isolation,
    serialize_background_isolation,
    with_artifact_id,
)


def enabled_config(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "mode": "cutout",
        "engine": "rembg",
        "model": "u2netp",
        "quality": "balanced",
        "fallback": "spotlight",
    }
    value.update(overrides)
    return value


def test_missing_and_disabled_values_are_stable_no_ops():
    missing = normalize_background_isolation(None)
    disabled = normalize_background_isolation({"enabled": False})

    assert is_no_op(None)
    assert missing["enabled"] is False
    assert disabled["enabled"] is False
    assert disabled["reason"] == "disabled"
    assert disabled["mode"] == DEFAULT_MODE
    assert disabled["engine"] == DEFAULT_ENGINE
    assert disabled["model"] == DEFAULT_MODEL
    assert disabled["quality"] == DEFAULT_QUALITY
    assert disabled["fallback"] == DEFAULT_FALLBACK
    assert artifact_is_ready(disabled) is False


def test_enabled_defaults_have_a_missing_artifact_until_worker_finishes():
    normalized = normalize_background_isolation({"enabled": True})

    assert normalized["enabled"] is True
    assert normalized["mode"] == DEFAULT_MODE
    assert normalized["engine"] == DEFAULT_ENGINE
    assert normalized["model"] == DEFAULT_MODEL
    assert normalized["quality"] == DEFAULT_QUALITY
    assert normalized["fallback"] == DEFAULT_FALLBACK
    assert normalized["artifact"] == {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "id": None,
        "status": "missing",
    }
    assert artifact_is_ready(normalized) is False


def test_artifact_identity_is_stable_and_changes_with_source_or_settings():
    config = enabled_config()
    first = build_artifact_id("clip:size=100:mtime=1", config)

    assert first == build_artifact_id("clip:size=100:mtime=1", config)
    assert first.startswith("bgiso1-")
    assert first != build_artifact_id("clip:size=100:mtime=2", config)
    assert first != build_artifact_id("clip:size=100:mtime=1", enabled_config(model="u2net"))
    assert build_artifact_id("clip:size=100:mtime=1", {"enabled": False}) is None
    assert build_artifact_id(None, config) is None


def test_with_artifact_id_carries_the_same_identity_for_future_consumers():
    resolved = with_artifact_id(enabled_config(), "clip:size=100:mtime=1")

    assert resolved["artifact"]["id"] == build_artifact_id("clip:size=100:mtime=1", resolved)
    assert resolved["artifact"]["status"] == "missing"
    assert artifact_is_ready(resolved) is False


def test_ready_artifact_requires_a_valid_id():
    ready = enabled_config(
        artifact={
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "id": "bgiso1-0123456789abcdef",
            "status": "ready",
            "source_fingerprint": "clip:size=100:mtime=1",
        }
    )

    normalized = normalize_background_isolation(ready)
    assert artifact_is_ready(normalized) is True
    assert normalized["artifact"]["id"] == "bgiso1-0123456789abcdef"


def test_invalid_schema_options_and_artifacts_fail_closed():
    assert normalize_background_isolation([])["reason"] == "invalid_config"
    assert normalize_background_isolation({"enabled": "yes"})["reason"] == "invalid_enabled"
    assert normalize_background_isolation({"enabled": True, "engine": "other"})["reason"] == "invalid_option"
    assert normalize_background_isolation({"enabled": True, "model": ""})["reason"] == "invalid_option"
    assert normalize_background_isolation({"enabled": True, "artifact": []})["reason"] == "invalid_artifact"
    assert normalize_background_isolation({"schema_version": 99, "enabled": True})["reason"] == "unsupported_schema"
    assert normalize_background_isolation(
        enabled_config(artifact={"status": "ready"})
    )["reason"] == "invalid_artifact"
    assert normalize_background_isolation(
        enabled_config(artifact={"id": "absolute-path", "status": "missing"})
    )["reason"] == "invalid_artifact"


def test_serialization_is_deterministic_and_round_trips_without_paths():
    value = with_artifact_id(enabled_config(quality="quality"), "clip:size=100:mtime=1")
    payload = serialize_background_isolation(value)

    assert payload == serialize_background_isolation(value)
    assert json.loads(payload)["artifact"]["id"].startswith("bgiso1-")
    assert "source_fingerprint" not in payload
    assert "C:\\" not in payload
    assert deserialize_background_isolation(payload) == value
    assert deserialize_background_isolation("not-json")["enabled"] is False
    assert deserialize_background_isolation(123)["enabled"] is False
