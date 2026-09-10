"""Focused tests for the renderer's Phase 4 colour-finishing contract."""

import math

from scripts.video_editor import (
    DEFAULT_ACCENT_PALETTE,
    build_eq_filter,
    normalize_lut_intensity,
    resolve_accent_palette,
    resolve_color_finish,
)
from scripts.overlay_recolor import (
    build_overlay_hue_filter,
    overlay_asset_recolor_metadata,
    resolve_overlay_recolor,
)


def test_legacy_empty_clip_keeps_the_zero_cost_colour_path():
    assert resolve_color_finish({}) == {
        "style_preset": DEFAULT_ACCENT_PALETTE,
        "eq": {},
        "palette": {
            "name": DEFAULT_ACCENT_PALETTE,
            "primary": "#FFE600",
            "status": "#25F4EE",
            "neutral": "#FFFFFF",
        },
    }
    assert build_eq_filter({}) == ""


def test_nested_look_is_normalized_and_flat_legacy_fields_win():
    clip = {
        "style_preset": "clean_tech_review",
        "look": {"brightness": 0.05, "contrast": 1.2, "saturation": 1.4},
        # Flat fields are the old manifest vocabulary and have precedence.
        "contrast": 99,
        "accentColor": "#abc",
    }

    result = resolve_color_finish(clip)

    assert result["eq"] == {"brightness": 0.05, "contrast": 2.0, "saturation": 1.4}
    assert result["palette"]["primary"] == "#AABBCC"
    assert build_eq_filter(clip) == "eq=brightness=0.05:contrast=2.0:saturation=1.4,"


def test_invalid_and_non_finite_values_fall_back_without_nan_filter_text():
    clip = {
        "brightness": "not-a-number",
        "contrast": math.nan,
        "saturation": math.inf,
        "look": {"brightness": -99},
    }

    assert resolve_color_finish(clip)["eq"] == {"brightness": -0.3}
    rendered = build_eq_filter(clip)
    assert "nan" not in rendered.lower()
    assert "inf" not in rendered.lower()
    assert rendered == "eq=brightness=-0.3,"


def test_unknown_palette_and_bad_colours_use_the_style_safe_fallback():
    palette = resolve_accent_palette(
        {"primary": "red", "status": "#12", "neutral": "#123456"},
        style_preset="unknown-style",
    )

    assert palette == {
        "name": DEFAULT_ACCENT_PALETTE,
        "primary": "#FFE600",
        "status": "#25F4EE",
        "neutral": "#123456",
    }


def test_every_selectable_style_resolves_to_its_own_render_palette():
    expected = {
        "clean_tech_review": "#FFE600",
        "viral_punch": "#FE2C55",
        "smooth_showcase": "#25F4EE",
        "premium_minimal": "#E6C24A",
    }

    for style_preset, accent in expected.items():
        palette = resolve_accent_palette(style_preset=style_preset)
        assert palette["name"] == style_preset
        assert palette["primary"] == accent


def test_lut_strength_is_finite_and_bounded():
    assert normalize_lut_intensity(None) == 1.0
    assert normalize_lut_intensity("junk") == 1.0
    assert normalize_lut_intensity(math.nan) == 1.0
    assert normalize_lut_intensity(math.inf) == 1.0
    assert normalize_lut_intensity(-3) == 0.0
    assert normalize_lut_intensity(3) == 1.0
    assert normalize_lut_intensity(0.35) == 0.35


def test_palette_is_pure_and_does_not_mutate_clip_payload():
    clip = {
        "look": {"accent_palette": {"primary": "#123456"}},
        "brightness": 0.1,
    }
    before = {"look": {"accent_palette": {"primary": "#123456"}}, "brightness": 0.1}

    result = resolve_color_finish(clip)

    assert result["palette"]["primary"] == "#123456"
    assert clip == before


def test_overlay_recolor_is_explicit_and_does_not_touch_semantic_badges():
    palette = resolve_accent_palette()
    assert overlay_asset_recolor_metadata("sticker", "arrow_pointer_cyan_3d.png")["recolorable"] is True
    assert overlay_asset_recolor_metadata("sticker", "badge_pros_review.png")["recolorable"] is False
    assert resolve_overlay_recolor(
        {"recolor": "accent"}, palette, kind="sticker", asset_id="arrow_pointer_cyan_3d.png"
    )["delta"] < -120
    assert resolve_overlay_recolor(
        {"recolor": "accent"}, palette, kind="sticker", asset_id="badge_pros_review.png"
    ) is None


def test_overlay_hue_filter_mirrors_canvas_contract_and_preserves_neutral_path():
    palette = resolve_accent_palette()
    tinted = build_overlay_hue_filter(
        "[2:v]", "[tinted]", {"recolor": "accent", "recolorSourceHue": 180}, palette,
        kind="sticker", asset_id="arrow_pointer_cyan_3d.png",
    )
    assert tinted == "[2:v]hue=h=-125.882[tinted];"
    assert build_overlay_hue_filter(
        "[2:v]", "[plain]", {}, palette, kind="sticker", asset_id="badge_pros_review.png"
    ) == ""
