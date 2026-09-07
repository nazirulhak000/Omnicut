"""
Direct behavioral coverage for scripts/hook_styles.py.

tests/test_preview_render_parity.py already checks HOOK_TEMPLATES field-by-
field against frontend/src/lib/hookStyles.js, and tests/test_phase1_smoke.py
uses resolve_hook_style() as a helper inside font-glyph-scale assertions. Ihat
leaves resolve_hook_style()'s own precedence contract (template defaults <
per-tier overrides < the older colour map) and the template table's structural
invariants uncovered directly -- this file covers those.

Pure functions, no filesystem or network: no tmp_path/monkeypatch needed.
"""
import math

import pytest

from scripts.hook_styles import (
    DEFAULT_HOOK_TEMPLATE,
    HOOK_TEMPLATES,
    TIER_FIELDS,
    TIER_KEYS,
    resolve_hook_style,
)


# ------------------------------------------------------------- table shape

def test_default_template_exists_in_the_table():
    assert DEFAULT_HOOK_TEMPLATE in HOOK_TEMPLATES


def test_every_template_defines_all_three_tiers_with_every_field():
    for name, tpl in HOOK_TEMPLATES.items():
        assert set(tpl["tiers"].keys()) == set(TIER_KEYS), name
        for tier_key in TIER_KEYS:
            tier = tpl["tiers"][tier_key]
            for field in TIER_FIELDS:
                assert field in tier, f"{name}.{tier_key} missing {field}"


def test_every_template_size_pct_and_outline_are_finite_and_positive():
    """These numbers ride straight into the ASS writer's Fontsize/Outline
    fields -- a NaN or negative here corrupts every hook banner frame."""
    for name, tpl in HOOK_TEMPLATES.items():
        for tier_key in TIER_KEYS:
            tier = tpl["tiers"][tier_key]
            assert math.isfinite(tier["size_pct"]) and tier["size_pct"] > 0, name
            assert math.isfinite(tier["outline_px"]) and tier["outline_px"] >= 0, name


def test_every_template_has_a_font_and_a_motion_map():
    for name, tpl in HOOK_TEMPLATES.items():
        assert tpl.get("font"), name
        assert isinstance(tpl.get("motion"), dict) and tpl["motion"], name


# ------------------------------------------------------- resolve_hook_style

def test_resolve_hook_style_with_no_args_returns_default_template_resolved():
    resolved = resolve_hook_style()
    assert resolved["template"] == DEFAULT_HOOK_TEMPLATE
    assert resolved["font"] == HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE]["font"]
    for key in TIER_KEYS:
        assert resolved["tiers"][key] == HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE]["tiers"][key]


def test_resolve_hook_style_unknown_template_falls_back_to_default():
    resolved = resolve_hook_style("nonsense_template")
    assert resolved["template"] == DEFAULT_HOOK_TEMPLATE


def test_resolve_hook_style_named_template_resolves_its_own_tiers():
    resolved = resolve_hook_style("cute")
    assert resolved["template"] == "cute"
    assert resolved["font"] == HOOK_TEMPLATES["cute"]["font"]
    assert resolved["tiers"]["brand"]["outline_color"] == "#E86BC7"


def test_resolve_hook_style_font_override_wins_over_template_font():
    resolved = resolve_hook_style("tech", {"font": "Sarabun"})
    assert resolved["font"] == "Sarabun"


def test_resolve_hook_style_tier_override_only_changes_named_fields():
    resolved = resolve_hook_style("tech", {"tiers": {"brand": {"size_pct": 200}}})
    base_brand = HOOK_TEMPLATES["tech"]["tiers"]["brand"]
    assert resolved["tiers"]["brand"]["size_pct"] == 200
    # untouched fields on the same tier keep the template's value
    assert resolved["tiers"]["brand"]["outline_color"] == base_brand["outline_color"]
    assert resolved["tiers"]["brand"]["outline_px"] == base_brand["outline_px"]
    # other tiers are entirely untouched
    assert resolved["tiers"]["model"] == HOOK_TEMPLATES["tech"]["tiers"]["model"]


def test_resolve_hook_style_colors_map_wins_over_tier_override_and_template():
    """`colors` is the older per-tier colour map, still written by the colour
    pickers -- it must win over both the template and a tiers override, so an
    existing project keeps the colours it was saved with."""
    resolved = resolve_hook_style(
        "tech",
        overrides={"tiers": {"model": {"color": "#111111"}}},
        colors={"model": "#00FF00"},
    )
    assert resolved["tiers"]["model"]["color"] == "#00FF00"


def test_resolve_hook_style_none_override_values_keep_the_template_value():
    """A tier override field set to None must not blank out the template's
    own value -- same 'absent and None both mean keep-the-base' contract as
    overlay_model.resolve_look()."""
    resolved = resolve_hook_style("tech", {"tiers": {"brand": {"size_pct": None}}})
    assert resolved["tiers"]["brand"]["size_pct"] == HOOK_TEMPLATES["tech"]["tiers"]["brand"]["size_pct"]


def test_resolve_hook_style_empty_colors_value_does_not_override():
    """An empty-string colour in the picked_colors map must not stomp the
    tier's real colour -- `if picked_colors.get(key)` is falsy-guarded."""
    resolved = resolve_hook_style("tech", colors={"model": ""})
    assert resolved["tiers"]["model"]["color"] == HOOK_TEMPLATES["tech"]["tiers"]["model"]["color"]


def test_resolve_hook_style_motion_override_replaces_the_whole_map():
    resolved = resolve_hook_style("tech", {"motion": {"in": "typewriter", "loop": "none"}})
    assert resolved["motion"] == {"in": "typewriter", "loop": "none"}


def test_resolve_hook_style_no_motion_override_keeps_template_motion():
    resolved = resolve_hook_style("plain")
    assert resolved["motion"] == HOOK_TEMPLATES["plain"]["motion"]


def test_resolve_hook_style_does_not_mutate_the_template_table():
    """Mutating a returned tier dict must never leak back into HOOK_TEMPLATES
    -- every call has to start from a fresh copy."""
    before = dict(HOOK_TEMPLATES["tech"]["tiers"]["brand"])
    resolved = resolve_hook_style("tech", {"tiers": {"brand": {"size_pct": 999}}})
    resolved["tiers"]["brand"]["outline_color"] = "#FFFFFF"
    assert HOOK_TEMPLATES["tech"]["tiers"]["brand"] == before
