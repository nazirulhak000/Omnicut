"""Unit contracts for the renderer-agnostic motion foundation."""

import math

import pytest

from scripts.subtitle.motion_contract import (
    MOTION_CONTRACT_VERSION,
    MOTION_PRESETS,
    MotionContractError,
    get_motion_preset,
    normalize_time,
    resolve_legacy_motion_id,
    sample_motion_contract,
    sample_track,
    validate_motion_contract,
)


def contract(**overrides):
    value = {
        "version": MOTION_CONTRACT_VERSION,
        "id": "test.in.sample",
        "role": "text",
        "phase": "in",
        "duration_ms": 100,
        "tracks": {
            "scale": {
                "unit": "ratio",
                "keyframes": [
                    {"t": 0.0, "value": 0.5, "easing": "linear"},
                    {"t": 1.0, "value": 1.0, "easing": "ease_out"},
                ],
            }
        },
    }
    value.update(overrides)
    return value


def test_schema_validation_accepts_all_declared_track_shapes():
    value = contract(
        tracks={
            "scale": {"keyframes": [{"t": 0, "value": 1}, {"t": 1, "value": 1.1}]},
            "alpha": {"keyframes": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]},
            "position": {"keyframes": [{"t": 0, "value": {"x": 0, "y": 10}}, {"t": 1, "value": {"x": 1, "y": 0}}]},
            "dy": {"keyframes": [{"t": 0, "value": 20}, {"t": 1, "value": 0}]},
            "rotation": {"keyframes": [{"t": 0, "value": -3}, {"t": 1, "value": 0}]},
            "blur": {"keyframes": [{"t": 0, "value": 12}, {"t": 1, "value": 0}]},
            "reveal": {"keyframes": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]},
        }
    )
    assert validate_motion_contract(value) is True


@pytest.mark.parametrize(
    "patch",
    [
        {"version": 2},
        {"role": "unknown"},
        {"phase": "hold"},
        {"duration_ms": -1},
        {"tracks": {"opacity": {"keyframes": [{"t": 0, "value": 1}]}}},
        {"tracks": {"scale": {"keyframes": [{"t": 0.5, "value": 1}, {"t": 0.4, "value": 1}]}}},
        {"tracks": {"position": {"keyframes": [{"t": 0, "value": {"x": 0}}]}}},
    ],
)
def test_schema_validation_rejects_invalid_documents(patch):
    value = contract()
    if "tracks" in patch:
        value["tracks"] = patch["tracks"]
    else:
        value.update(patch)
    with pytest.raises(MotionContractError):
        validate_motion_contract(value)


def test_normalized_time_is_clamped_and_rejects_non_finite_values():
    assert normalize_time(-10) == 0.0
    assert normalize_time(0.25) == 0.25
    assert normalize_time(10) == 1.0
    with pytest.raises(MotionContractError):
        normalize_time(math.inf)


def test_sampling_is_deterministic_and_uses_right_keyframe_easing():
    track = {
        "keyframes": [
            {"t": 0, "value": 0},
            {"t": 1, "value": 10, "easing": "ease_in"},
        ]
    }
    first = sample_track("scale", track, 0.5)
    second = sample_track("scale", track, 0.5)
    assert first == second == 2.5


def test_sampling_supports_position_vectors_and_contract_tracks():
    value = contract(
        tracks={
            "position": {
                "keyframes": [
                    {"t": 0, "value": {"x": 0, "y": 40}},
                    {"t": 1, "value": {"x": 1, "y": 0}},
                ]
            },
            "alpha": {"keyframes": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]},
        }
    )
    assert sample_motion_contract(value, 0.5) == {"position": {"x": 0.5, "y": 20.0}, "alpha": 0.5}


def test_legacy_mapping_keeps_text_aliases_role_scoped():
    assert resolve_legacy_motion_id("text", "in", "pop") == "snap"
    assert resolve_legacy_motion_id("text", "in", "zoom") == "pop_zoom"
    assert resolve_legacy_motion_id("text", "in", "slide") == "rise"
    assert resolve_legacy_motion_id("hook", "in", "pop") == "pop"
    assert resolve_legacy_motion_id("hook", "loop", "wave") == "wave"
    assert resolve_legacy_motion_id("hook", "out", "glitch") == "glitch"


def test_every_catalog_preset_is_valid_and_defensively_copied():
    assert MOTION_PRESETS
    for identifier, preset in MOTION_PRESETS.items():
        assert identifier == preset["id"]
        assert validate_motion_contract(preset) is True
    first = get_motion_preset("hook", "in", "bounce")
    second = get_motion_preset("hook", "in", "bounce")
    assert first == second
    first["tracks"]["scale"]["keyframes"][0]["value"] = 999
    assert second["tracks"]["scale"]["keyframes"][0]["value"] == 0.6
    assert get_motion_preset("text", "in", "snap")["role"] == "text"
