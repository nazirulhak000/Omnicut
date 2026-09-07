"""
Direct behavioral coverage for scripts/overlay_model.py.

tests/test_preview_render_parity.py, tests/test_refactor_baseline_contracts.py
and tests/test_final_compatibility_signoff.py already cover migrate_to_overlays/
overlays_to_legacy round-trips and Python<->JS parity for several tables. This
file covers what those leave untouched: resolve_look's override precedence,
font_weight/base_fs_ratio lookups, template_for_ad_tone, guess_brand_model,
the new_text_overlay/new_hook_overlay constructors, and _pill_from_legacy's
branch matrix -- all pure functions, no filesystem or network involved.

No tmp_path/monkeypatch needed: overlay_model.py has no module-level paths,
no I/O, and no import-time side effects to isolate from.
"""
import math

import pytest

from scripts.overlay_model import (
    DEFAULT_FONT_WEIGHT,
    DEFAULT_TEXT_LOOK,
    FONT_WEIGHTS,
    HOOK_FS_RATIO,
    TEXT_FS_RATIO,
    ANCHOR_MIDDLE,
    ANCHOR_TOP,
    ACCENT_COLOR,
    TEXT_LAYER,
    HOOK_LAYER,
    base_fs_ratio,
    font_weight,
    guess_brand_model,
    hook_overlay_from_legacy,
    new_hook_overlay,
    new_text_overlay,
    resolve_look,
    template_for_ad_tone,
    _pill_from_legacy,
)
from scripts.hook_styles import DEFAULT_HOOK_TEMPLATE, HOOK_TEMPLATES


# --------------------------------------------------------------- resolve_look

def test_resolve_look_starts_from_defaults_when_nothing_given():
    look = resolve_look(None, None)
    assert look == DEFAULT_TEXT_LOOK
    # must be a copy, not the same dict the module keeps as its default
    look["color"] = "#ABCDEF"
    assert DEFAULT_TEXT_LOOK["color"] != "#ABCDEF"


def test_resolve_look_base_overrides_defaults_field_by_field():
    look = resolve_look({"color": "#111111", "size_pct": 120}, None)
    assert look["color"] == "#111111"
    assert look["size_pct"] == 120
    # fields the base didn't mention keep the default
    assert look["font"] == DEFAULT_TEXT_LOOK["font"]
    assert look["outline_px"] == DEFAULT_TEXT_LOOK["outline_px"]


def test_resolve_look_override_wins_over_base_which_wins_over_default():
    base = {"color": "#111111", "size_pct": 120, "font": "Prompt"}
    override = {"color": "#222222"}
    look = resolve_look(base, override)
    assert look["color"] == "#222222"   # override beats base
    assert look["size_pct"] == 120       # base beats default
    assert look["font"] == "Prompt"


def test_resolve_look_none_values_mean_keep_the_base_not_erase_it():
    """Absent and None both mean 'keep the base' -- an override that sets a
    field to None must not blank out a base value, matching resolve_hook_style()'s
    contract in hook_styles.py."""
    base = {"color": "#111111"}
    override = {"color": None, "font": "Kanit"}
    look = resolve_look(base, override)
    assert look["color"] == "#111111"
    assert look["font"] == "Kanit"


def test_resolve_look_ignores_fields_outside_the_text_look_contract():
    look = resolve_look({"unknown_field": "x"}, None)
    assert "unknown_field" not in look


# --------------------------------------------------------------- font_weight

def test_font_weight_known_family_names_its_table_value():
    assert font_weight("Kanit") == 700
    assert font_weight("Anuphan") == 400
    assert font_weight("Itim") == 400


def test_font_weight_unknown_or_missing_family_falls_back_to_default():
    assert font_weight("SomeFontNobodyHasHeardOf") == DEFAULT_FONT_WEIGHT
    assert font_weight(None) == DEFAULT_FONT_WEIGHT
    assert font_weight("") == DEFAULT_FONT_WEIGHT


def test_font_weight_covers_every_entry_in_its_own_table():
    for family, weight in FONT_WEIGHTS.items():
        assert font_weight(family) == weight


# ------------------------------------------------------------ base_fs_ratio

def test_base_fs_ratio_hook_vs_text():
    assert base_fs_ratio("hook") == HOOK_FS_RATIO
    assert base_fs_ratio("text") == TEXT_FS_RATIO
    # anything that isn't literally "hook" reads as a text overlay
    assert base_fs_ratio("something_else") == TEXT_FS_RATIO
    assert base_fs_ratio("") == TEXT_FS_RATIO


# ------------------------------------------------------- template_for_ad_tone

def test_template_for_ad_tone_known_tones():
    assert template_for_ad_tone("commercial_hype") == "bold_pop"
    assert template_for_ad_tone("commercial_expert") == "tech"
    assert template_for_ad_tone("commercial_aesthetic") == "plain"
    assert template_for_ad_tone("commercial_premium") == "clean"


def test_template_for_ad_tone_unknown_or_none_falls_back_to_default():
    assert template_for_ad_tone("nonsense_tone") == DEFAULT_HOOK_TEMPLATE
    assert template_for_ad_tone(None) == DEFAULT_HOOK_TEMPLATE
    assert template_for_ad_tone("") == DEFAULT_HOOK_TEMPLATE


# --------------------------------------------------------------- guess_brand_model

@pytest.mark.parametrize("name,brand,model", [
    ("Logitech Wave Keys", "Logitech", "Wave Keys"),
    ("Apple iPhone 15", "Apple", "iPhone 15"),
    ("Nike", "Nike", ""),
    ("", "", ""),
    ("   ", "", ""),
    ("  Sony  WH-1000XM5  ", "Sony", "WH-1000XM5"),
])
def test_guess_brand_model_splits_on_first_word(name, brand, model):
    assert guess_brand_model(name) == (brand, model)


def test_guess_brand_model_none_input_is_empty():
    assert guess_brand_model(None) == ("", "")


# --------------------------------------------------------------- _pill_from_legacy

def test_pill_from_legacy_none_style_and_no_badge_color_is_none():
    assert _pill_from_legacy(None, None) is None
    assert _pill_from_legacy("none", None) is None


def test_pill_from_legacy_named_preset():
    pill = _pill_from_legacy("badge_red", None)
    assert pill["fill"] == "#FE2C55"
    assert pill["border"] is None
    assert pill["pad_x_em"] > 0
    assert pill["pad_y_em"] > 0


def test_pill_from_legacy_badge_color_overrides_preset_fill_but_keeps_border():
    """A badgeColor naming a different colour than its preset overrides the
    fill but keeps the preset's border, matching the old branch order."""
    pill = _pill_from_legacy("badge_cyan", "#123456")
    assert pill["fill"] == "#123456"
    assert pill["border"] == "#25F4EE"  # badge_cyan's own border, unchanged


def test_pill_from_legacy_badge_color_matching_its_own_preset_keeps_preset():
    pill = _pill_from_legacy("badge_red", "#FE2C55")
    assert pill["fill"] == "#FE2C55"


def test_pill_from_legacy_arbitrary_fill_with_no_bg_style():
    pill = _pill_from_legacy("none", "#0A0A0A")
    assert pill == {
        "fill": "#0A0A0A", "border": None,
        "pad_x_em": pytest.approx(0.6), "pad_y_em": pytest.approx(0.35),
    }


def test_pill_from_legacy_pill_style_uses_translucent_black():
    pill = _pill_from_legacy("pill", None)
    assert pill["fill"] == "rgba(0, 0, 0, 0.65)"
    assert pill["border"] is None


# --------------------------------------------------------------- new_text_overlay

def test_new_text_overlay_defaults():
    overlay = new_text_overlay("ovl_1")
    assert overlay["id"] == "ovl_1"
    assert overlay["kind"] == "text"
    assert overlay["anchor"] == ANCHOR_MIDDLE
    assert overlay["layer"] == TEXT_LAYER
    assert overlay["tiers"] == [{"text": "", "look": {}}]
    assert overlay["anim"]["in"] == "snap"  # DEFAULT_ANIM's entrance
    assert overlay["hidden"] is False
    assert overlay["start"] == 0.0
    assert overlay["end"] == 2.5


def test_new_text_overlay_rounds_start_and_end_to_three_decimals():
    overlay = new_text_overlay("x", start=1.23456, end=4.98765)
    assert overlay["start"] == 1.235
    assert overlay["end"] == 4.988


def test_new_text_overlay_custom_look_merges_over_defaults():
    overlay = new_text_overlay("x", look={"color": "#FF0000"})
    assert overlay["look"]["color"] == "#FF0000"
    assert overlay["look"]["font"] == DEFAULT_TEXT_LOOK["font"]


def test_new_text_overlay_custom_anim_in_overrides_default_entrance_only():
    overlay = new_text_overlay("x", anim_in="rise")
    assert overlay["anim"]["in"] == "rise"
    assert overlay["anim"]["out"] == "fade"  # untouched default exit


def test_new_text_overlay_carries_text_sfx_and_template_id():
    overlay = new_text_overlay(
        "x", text="hello", sfx="sfx_whoosh", sfx_label="Whoosh", template_id="tmpl_1",
    )
    assert overlay["tiers"][0]["text"] == "hello"
    assert overlay["sfx"] == "sfx_whoosh"
    assert overlay["sfx_label"] == "Whoosh"
    assert overlay["template_id"] == "tmpl_1"


# --------------------------------------------------------------- new_hook_overlay

def test_new_hook_overlay_blank_texts_return_none():
    assert new_hook_overlay("", "", "") is None
    assert new_hook_overlay("   ", "", "") is None
    assert new_hook_overlay(None, None, None) is None


def test_new_hook_overlay_with_text_produces_three_tiers():
    overlay = new_hook_overlay("Logitech", "Wave Keys", "Keyboard")
    assert overlay is not None
    assert overlay["kind"] == "hook"
    assert len(overlay["tiers"]) == 3
    assert [t["text"] for t in overlay["tiers"]] == ["Logitech", "Wave Keys", "Keyboard"]
    assert overlay["anchor"] == ANCHOR_TOP
    assert overlay["layer"] == HOOK_LAYER


def test_new_hook_overlay_default_start_end_is_zero_to_duration():
    overlay = new_hook_overlay("A", "B", "C", duration=4.0)
    assert overlay["start"] == 0.0
    assert overlay["end"] == 4.0


def test_new_hook_overlay_custom_start_shifts_end_by_duration():
    overlay = new_hook_overlay("A", "B", "C", start=2.0, duration=3.5)
    assert overlay["start"] == 2.0
    assert overlay["end"] == 5.5


def test_new_hook_overlay_uses_requested_template():
    overlay = new_hook_overlay("A", "B", "C", template="cute")
    assert overlay["template"] == "cute"
    assert overlay["look"]["font"] == HOOK_TEMPLATES["cute"]["font"]


def test_new_hook_overlay_unknown_template_falls_back_to_default():
    overlay = new_hook_overlay("A", "B", "C", template="does_not_exist")
    assert overlay["template"] == DEFAULT_HOOK_TEMPLATE


# ------------------------------------------------------- hook_overlay_from_legacy

def test_hook_overlay_from_legacy_none_when_all_tiers_blank():
    assert hook_overlay_from_legacy("", "", "") is None
    assert hook_overlay_from_legacy("  ", "\t", "") is None


def test_hook_overlay_from_legacy_partial_text_still_produces_overlay():
    """A banner with no brand still exists -- the old !!brand check dropped
    it, then autosave wrote '' over the model and label it had not looked at."""
    overlay = hook_overlay_from_legacy("", "Wave Keys", "Keyboard")
    assert overlay is not None
    assert [t["text"] for t in overlay["tiers"]] == ["", "Wave Keys", "Keyboard"]


def test_hook_overlay_from_legacy_model_color_defaults_to_accent():
    overlay = hook_overlay_from_legacy("Brand", "Model", "Label")
    model_tier = overlay["tiers"][1]
    assert model_tier["look"]["color"] == ACCENT_COLOR


def test_hook_overlay_from_legacy_explicit_color_wins_over_accent():
    overlay = hook_overlay_from_legacy(
        "Brand", "Model", "Label",
        colors={"model": "#00FF00"},
    )
    model_tier = overlay["tiers"][1]
    assert model_tier["look"]["color"] == "#00FF00"


def test_hook_overlay_from_legacy_all_numeric_fields_are_finite():
    """Every numeric field this feeds to the ASS writer must be finite and
    sane -- a NaN/inf here would corrupt every rendered frame."""
    overlay = hook_overlay_from_legacy("Brand", "Model", "Label", duration=3.7)
    assert math.isfinite(overlay["start"])
    assert math.isfinite(overlay["end"])
    assert overlay["end"] > overlay["start"]
    assert math.isfinite(overlay["x"])
    assert math.isfinite(overlay["y"])
    assert math.isfinite(overlay["base_fs_ratio"])
    for tier in overlay["tiers"]:
        assert math.isfinite(tier["look"]["size_pct"])
        assert math.isfinite(tier["look"]["outline_px"])
