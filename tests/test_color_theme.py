"""Focused tests for the standalone ColorThemeV1 resolver."""

from scripts.color_theme import STYLE_FALLBACKS, contrast_ratio, resolve_color_theme


def test_green_product_uses_fixed_orange_pair():
    theme = resolve_color_theme("#5EDB42", style_preset="tech_product_showcase")

    assert theme["primary"] == "#5EDB42"
    assert theme["secondary"] == "#FF8A3D"
    assert theme["source_metadata"]["hue_sector"] == "green"
    assert theme["source_metadata"]["secondary_source"] == "hue_sector_pair"


def test_blue_product_uses_fixed_amber_pair():
    theme = resolve_color_theme({"dominant_color": "#2F80ED"})

    assert theme["primary"] == "#2F80ED"
    assert theme["secondary"] == "#FFB000"
    assert theme["source_metadata"]["hue_sector"] == "cyan_blue"


def test_grayscale_product_uses_complete_style_fallback():
    theme = resolve_color_theme("#808080", style_preset="premium_minimal")

    assert theme["primary"] == STYLE_FALLBACKS["premium_minimal"]["primary"]
    assert theme["secondary"] == STYLE_FALLBACKS["premium_minimal"]["secondary"]
    assert theme["source_metadata"]["source"] == "style_fallback"
    assert theme["source_metadata"]["hue_sector"] is None


def test_invalid_product_hex_and_unknown_style_use_safe_fallback():
    theme = resolve_color_theme("not-a-colour", style_preset="unknown")

    assert theme["primary"] == STYLE_FALLBACKS["clean_tech_review"]["primary"]
    assert theme["source_metadata"]["fallback_style"] == "clean_tech_review"
    assert theme["source_metadata"]["product_color"] is None


def test_explicit_theme_wins_per_field_over_product_and_style():
    theme = resolve_color_theme(
        "#5EDB42",
        style_preset="premium_minimal",
        explicit_theme={
            "primary": "#1234AB",
            "secondary": "#F06A3A",
            "neutral": "#F4F1E8",
            "ink": "#101010",
        },
    )

    assert theme["primary"] == "#1234AB"
    assert theme["secondary"] == "#F06A3A"
    assert theme["neutral"] == "#F4F1E8"
    assert theme["ink"] == "#101010"
    assert theme["source_metadata"]["primary_source"] == "explicit"
    assert theme["source_metadata"]["secondary_source"] == "explicit"


def test_invalid_or_low_contrast_explicit_values_fall_through_safely():
    theme = resolve_color_theme(
        "#2F80ED",
        explicit_theme={"primary": "#12345", "secondary": "#000000"},
    )

    assert theme["primary"] == "#2F80ED"
    assert theme["secondary"] == "#FFB000"
    assert theme["source_metadata"]["invalid_fields"] == ["primary"]
    assert theme["source_metadata"]["contrast_fallback_fields"] == ["secondary"]
    assert theme["source_metadata"]["source"] == "product_derived"


def test_result_is_deterministic_and_metadata_is_serialisable():
    source = {"productColor": "#A855F7", "frame_indices": [20, 50, 80]}

    first = resolve_color_theme(source, style_preset="tech_product_showcase")
    second = resolve_color_theme(source, style_preset="tech_product_showcase")

    assert first == second
    assert first["contract"] == "ColorThemeV1"
    assert first["version"] == 1
    assert first["secondary"] == "#B7FF00"
    assert contrast_ratio(first["primary"], first["ink"]) >= 2.2
