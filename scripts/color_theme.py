"""Deterministic product colour themes for editorial overlays.

This module deliberately has no renderer or pipeline dependencies.  It turns
an optional product colour and/or explicit theme into a small, serialisable
``ColorThemeV1`` contract that later stages can consume.
"""

from __future__ import annotations

import colorsys
import re
from collections.abc import Mapping
from typing import Any


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# These are deliberately kept local.  Importing the renderer's style policy
# here would make this foundational resolver part of the render dependency
# graph before it is wired into the pipeline.
STYLE_FALLBACKS: dict[str, dict[str, str]] = {
    "clean_tech_review": {
        "primary": "#FFE600",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "viral_punch": {
        "primary": "#FE2C55",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "smooth_showcase": {
        "primary": "#25F4EE",
        "secondary": "#FFB000",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "premium_minimal": {
        "primary": "#E6C24A",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "tech_product_showcase": {
        "primary": "#FFCC33",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "flash_deal": {
        "primary": "#FF7A00",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "pain_punch": {
        "primary": "#FF2E93",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "tech_compare": {
        "primary": "#3B82F6",
        "secondary": "#FFE600",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "smart_hack": {
        "primary": "#84CC16",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
    "niche_focus": {
        "primary": "#A855F7",
        "secondary": "#25F4EE",
        "neutral": "#FFFFFF",
        "ink": "#080B10",
    },
}

DEFAULT_STYLE = "clean_tech_review"

# Fixed editorial pairings.  The source colour is retained as primary; the
# second colour is selected by hue sector so the same input always produces
# the same two-colour mood.
HUE_SECTOR_PAIRS: tuple[tuple[str, float, float, str], ...] = (
    ("red_pink", 0.0, 20.0, "#25F4EE"),
    ("orange_yellow", 20.0, 75.0, "#4455FF"),
    ("green", 75.0, 165.0, "#FF8A3D"),
    ("cyan_blue", 165.0, 255.0, "#FFB000"),
    ("purple", 255.0, 340.0, "#B7FF00"),
    ("red_pink", 340.0, 360.0, "#25F4EE"),
)

# A colour must be visibly distinct from the dark ink used for editorial
# text/strokes.  This rejects black-ish product samples that would produce an
# unreadable accent while allowing saturated dark blue/green products.
MIN_ACCENT_INK_CONTRAST = 2.2
MIN_SATURATION = 0.12
MIN_VALUE = 0.12


def normalize_hex(value: Any) -> str | None:
    """Return an uppercase six-digit HEX colour, or ``None`` if invalid."""

    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if len(candidate) == 4 and candidate.startswith("#"):
        candidate = "#" + "".join(char * 2 for char in candidate[1:])
    if not HEX_COLOR_RE.fullmatch(candidate):
        return None
    return candidate.upper()


def _relative_luminance(value: str) -> float:
    rgb = [int(value[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]

    def linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: Any, second: Any) -> float:
    """Return WCAG contrast for two HEX colours, or ``0`` for invalid input."""

    first_hex = normalize_hex(first)
    second_hex = normalize_hex(second)
    if first_hex is None or second_hex is None:
        return 0.0
    first_luminance = _relative_luminance(first_hex)
    second_luminance = _relative_luminance(second_hex)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _hsv_details(value: str) -> tuple[float, float, float]:
    red = int(value[1:3], 16) / 255.0
    green = int(value[3:5], 16) / 255.0
    blue = int(value[5:7], 16) / 255.0
    hue, saturation, brightness = colorsys.rgb_to_hsv(red, green, blue)
    return hue * 360.0, saturation, brightness


def _sector_for(value: str) -> tuple[str, str] | None:
    hue, saturation, brightness = _hsv_details(value)
    if saturation < MIN_SATURATION or brightness < MIN_VALUE:
        return None
    for sector, lower, upper, pair in HUE_SECTOR_PAIRS:
        if lower <= hue < upper:
            return sector, pair
    return None


def _is_usable_accent(value: Any, ink: str, neutral: str | None = None) -> str | None:
    candidate = normalize_hex(value)
    if candidate is None:
        return None
    _, saturation, brightness = _hsv_details(candidate)
    if saturation < MIN_SATURATION or brightness < MIN_VALUE:
        return None
    if contrast_ratio(candidate, ink) < MIN_ACCENT_INK_CONTRAST and (
        neutral is None or contrast_ratio(candidate, neutral) < MIN_ACCENT_INK_CONTRAST
    ):
        return None
    return candidate


def _source_colour(source: Any) -> Any:
    if isinstance(source, str):
        return source
    if not isinstance(source, Mapping):
        return None
    for key in (
        "product_color",
        "productColor",
        "dominant_color",
        "dominantColor",
        "sampled_color",
        "sampledColor",
        "color",
        "hex",
        "primary",
    ):
        if key in source:
            value = source[key]
            return _source_colour(value) if isinstance(value, Mapping) else value
    return None


def extract_explicit_theme(source: Any) -> dict[str, Any] | None:
    """Read an explicit theme nested in product metadata, if present.

    Product records have used both ``color_theme`` and ``theme`` in different
    API paths.  Only mappings containing at least one ColorTheme field count;
    an unrelated product ``theme`` value must not accidentally become a
    colour override.
    """

    if not isinstance(source, Mapping):
        return None
    for key in ("color_theme", "colorTheme", "editorial_color_theme", "theme"):
        value = source.get(key)
        if isinstance(value, Mapping) and any(
            field in value for field in ("primary", "secondary", "neutral", "ink")
        ):
            return dict(value)
    return None


def is_color_theme(value: Any) -> bool:
    """Return whether a persisted value is a complete usable ColorThemeV1."""

    if not isinstance(value, Mapping) or value.get("contract") != "ColorThemeV1":
        return False
    return all(normalize_hex(value.get(field)) for field in ("primary", "secondary", "neutral", "ink"))


def _fallback_style(style_preset: Any) -> tuple[str, dict[str, str]]:
    requested = style_preset.strip() if isinstance(style_preset, str) else ""
    style = requested if requested in STYLE_FALLBACKS else DEFAULT_STYLE
    return style, STYLE_FALLBACKS[style]


def resolve_color_theme(
    source: Any = None,
    *,
    explicit_theme: Mapping[str, Any] | None = None,
    style_preset: str | None = None,
) -> dict[str, Any]:
    """Resolve a serialisable ``ColorThemeV1`` without side effects.

    ``source`` may be a HEX string or a mapping containing a product colour
    under common metadata keys.  Explicit values win per field when valid;
    missing/invalid explicit values fall through to product-derived values or
    the selected style fallback.  Grayscale product samples intentionally use
    the complete style fallback so a neutral product cannot create a muddy
    accent palette.
    """

    fallback_style, fallback = _fallback_style(style_preset)
    explicit = explicit_theme if isinstance(explicit_theme, Mapping) else {}
    invalid_fields: list[str] = []
    contrast_fallback_fields: list[str] = []

    explicit_ink = normalize_hex(explicit.get("ink"))
    ink = explicit_ink or fallback["ink"]
    if "ink" in explicit and explicit_ink is None:
        invalid_fields.append("ink")

    explicit_neutral = normalize_hex(explicit.get("neutral"))
    neutral = explicit_neutral or fallback["neutral"]
    if "neutral" in explicit and explicit_neutral is None:
        invalid_fields.append("neutral")

    product_colour = normalize_hex(_source_colour(source))
    product_sector = _sector_for(product_colour) if product_colour else None
    derived_primary = (
        _is_usable_accent(product_colour, ink) if product_sector is not None else None
    )
    if product_colour and product_sector is None:
        contrast_fallback_fields.append("product_color")
    elif product_colour and derived_primary is None:
        contrast_fallback_fields.append("product_color")

    explicit_primary = _is_usable_accent(explicit.get("primary"), ink, neutral)
    if "primary" in explicit and explicit_primary is None:
        if normalize_hex(explicit.get("primary")) is None:
            invalid_fields.append("primary")
        else:
            contrast_fallback_fields.append("primary")

    explicit_secondary = _is_usable_accent(explicit.get("secondary"), ink, neutral)
    if "secondary" in explicit and explicit_secondary is None:
        if normalize_hex(explicit.get("secondary")) is None:
            invalid_fields.append("secondary")
        else:
            contrast_fallback_fields.append("secondary")

    primary = explicit_primary or derived_primary or fallback["primary"]
    if explicit_primary is not None:
        primary_source = "explicit"
    elif derived_primary is not None:
        primary_source = "product_derived"
    else:
        primary_source = "style_fallback"

    derived_secondary = product_sector[1] if product_sector else None
    secondary = explicit_secondary or derived_secondary or fallback["secondary"]
    if explicit_secondary is not None:
        secondary_source = "explicit"
    elif derived_secondary is not None:
        secondary_source = "hue_sector_pair"
    else:
        secondary_source = "style_fallback"

    explicit_was_used = any(
        value is not None
        for value in (explicit_primary, explicit_secondary, explicit_neutral, explicit_ink)
    )
    if explicit_was_used:
        overall_source = "explicit"
    elif derived_primary is not None:
        overall_source = "product_derived"
    else:
        overall_source = "style_fallback"

    source_metadata = {
        "source": overall_source,
        "style_preset": style_preset,
        "fallback_style": fallback_style,
        "product_color": product_colour,
        "hue_sector": product_sector[0] if product_sector else None,
        "primary_source": primary_source,
        "secondary_source": secondary_source,
        "invalid_fields": sorted(set(invalid_fields)),
        "contrast_fallback_fields": sorted(set(contrast_fallback_fields)),
    }
    return {
        "contract": "ColorThemeV1",
        "version": 1,
        "primary": primary,
        "secondary": secondary,
        "neutral": neutral,
        "ink": ink,
        "source_metadata": source_metadata,
    }


__all__ = [
    "DEFAULT_STYLE",
    "HUE_SECTOR_PAIRS",
    "STYLE_FALLBACKS",
    "ColorThemeV1",
    "contrast_ratio",
    "extract_explicit_theme",
    "is_color_theme",
    "normalize_hex",
    "resolve_color_theme",
]


# A small runtime alias keeps the contract name discoverable without adding a
# second mutable model.  The resolver returns a plain dict intentionally so it
# can be persisted directly in a manifest and consumed by future adapters.
ColorThemeV1 = dict[str, Any]
