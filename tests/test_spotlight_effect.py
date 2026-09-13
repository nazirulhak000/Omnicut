from __future__ import annotations

import json

from scripts.spotlight_effect import (
    DEFAULT_DIM_OPACITY,
    DEFAULT_FEATHER,
    DEFAULT_FOCUS,
    DEFAULT_SHAPE,
    SCHEMA_VERSION,
    build_ffmpeg_filter,
    deserialize_spotlight,
    is_no_op,
    normalize_spotlight,
    serialize_spotlight,
)


def enabled_config(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "shape": "ellipse",
        "focus": {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.4},
        "dim_opacity": 0.4,
        "feather": 0.03,
        "corner_radius": 0.08,
    }
    value.update(overrides)
    return value


def test_missing_and_disabled_values_are_stable_no_ops():
    missing = normalize_spotlight(None)
    disabled = normalize_spotlight({"enabled": False})

    assert is_no_op(None)
    assert missing["enabled"] is False
    assert disabled["enabled"] is False
    assert disabled["reason"] == "disabled"
    assert disabled["shape"] == DEFAULT_SHAPE
    assert disabled["focus"] == DEFAULT_FOCUS
    assert build_ffmpeg_filter(disabled, 1080, 1920) is None


def test_enabled_defaults_are_safe_and_serialisable():
    effect = normalize_spotlight({"enabled": True})

    assert effect["enabled"] is True
    assert effect["shape"] == DEFAULT_SHAPE
    assert effect["dim_opacity"] == DEFAULT_DIM_OPACITY
    assert effect["feather"] == DEFAULT_FEATHER
    assert effect["focus"] == DEFAULT_FOCUS


def test_focus_and_visual_values_are_clamped_inside_safe_ranges():
    effect = normalize_spotlight(
        enabled_config(
            focus={"x": 9, "y": -4, "width": 9, "height": -2},
            dim_opacity=4,
            feather=-1,
            corner_radius=2,
        )
    )

    assert effect["focus"] == {"x": 0.5, "y": 0.01, "width": 1.0, "height": 0.02}
    assert effect["dim_opacity"] == 0.95
    assert effect["feather"] == 0.0
    assert effect["corner_radius"] == 0.01


def test_invalid_top_level_values_fall_back_to_no_op():
    assert normalize_spotlight([])["reason"] == "invalid_config"
    assert normalize_spotlight({"enabled": "yes"})["reason"] == "invalid_enabled"
    assert normalize_spotlight({"enabled": True, "shape": "triangle"})["reason"] == "invalid_shape"
    assert normalize_spotlight({"enabled": True, "focus": []})["reason"] == "invalid_focus"
    assert normalize_spotlight({"schema_version": 99, "enabled": True})["reason"] == "unsupported_schema"
    assert build_ffmpeg_filter({"enabled": True, "shape": "triangle"}, 1080, 1920) is None


def test_serialisation_is_deterministic_and_round_trips():
    effect = normalize_spotlight(enabled_config(shape="rounded-rectangle"))
    payload = serialize_spotlight(effect)

    assert payload == serialize_spotlight(effect)
    assert json.loads(payload)["shape"] == "rounded_rect"
    assert deserialize_spotlight(payload) == effect
    assert deserialize_spotlight("not-json")["enabled"] is False
    assert deserialize_spotlight(123)["enabled"] is False


def test_filter_builder_supports_all_shapes_and_feathering_without_injection():
    for shape in ("ellipse", "rectangle", "rounded_rect"):
        effect = normalize_spotlight(enabled_config(shape=shape))
        fragment = build_ffmpeg_filter(effect, 1080, 1920)

        assert fragment is not None
        assert "split=2" in fragment
        assert "colorchannelmixer" in fragment
        assert "overlay=0:0" in fragment
        assert "gblur=sigma=" in fragment
        assert "rembg" not in fragment.lower()
        assert "onnx" not in fragment.lower()
        assert "\n" not in fragment
        assert ";;" not in fragment


def test_filter_builder_has_no_side_effect_and_rejects_unsafe_dimensions():
    effect = enabled_config()
    fragment = build_ffmpeg_filter(effect, 1080, 1920)

    assert isinstance(fragment, str)
    assert all(token not in fragment for token in ("/tmp", "C:\\", "-i ", "rm "))
    assert build_ffmpeg_filter(effect, 0, 1920) is None
    assert build_ffmpeg_filter(effect, 1080, 20000) is None
    assert build_ffmpeg_filter(effect, 1080.0, 1920) is None
    assert build_ffmpeg_filter(effect, True, 1920) is None


def test_rectangle_alias_is_canonicalised():
    assert normalize_spotlight(enabled_config(shape="rect"))["shape"] == "rectangle"
    assert normalize_spotlight(enabled_config(shape="rounded-rect"))["shape"] == "rounded_rect"

