"""Q5: style presets, angle defaults and colour fallbacks agree everywhere.

Parses the frontend catalog from Python so the JS and Python copies cannot
drift apart silently. Offline, read-only.
"""

import re
from pathlib import Path

import pytest

from scripts.batch_render import (
    ANGLE_TO_DEFAULT_STYLE,
    default_style_for_angle,
    resolve_batch_style_preset,
)
from scripts.color_theme import STYLE_FALLBACKS
from scripts.hook_styles import HOOK_TEMPLATES
from scripts.it_angles import IT_ANGLE_CATALOG
from scripts.overlay_model import template_for_style_preset
from scripts.style_motion_policy import STYLE_MOTION_POLICIES

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JS = ROOT / "frontend" / "src" / "lib" / "stylePresetCatalog.js"
BATCH_MODAL_JSX = ROOT / "frontend" / "src" / "components" / "BatchRenderModal.jsx"


def _js_source() -> str:
    return CATALOG_JS.read_text(encoding="utf-8")


def _js_angle_map() -> dict:
    block = re.search(r"export const ANGLE_TO_DEFAULT_STYLE = Object\.freeze\(\{(.*?)\}\);", _js_source(), re.S)
    assert block, "ANGLE_TO_DEFAULT_STYLE not found in stylePresetCatalog.js"
    return dict(re.findall(r"^\s*([a-z_]+):\s*'([a-z_]+)',?\s*$", block.group(1), re.M))


def _js_presets() -> dict:
    source = _js_source()
    default_id = re.search(r"export const DEFAULT_STYLE_PRESET = '([a-z_]+)';", source).group(1)
    body = re.search(r"const STYLE_PRESETS = \[(.*?)\n\];", source, re.S).group(1)
    presets = {}
    for chunk in re.findall(r"\{(.*?)\n  \}", body, re.S):
        fields = dict(re.findall(r"^\s*(\w+):\s*'([^']*)',", chunk, re.M))
        if "id" not in fields:
            assert re.search(r"^\s*id: DEFAULT_STYLE_PRESET,", chunk, re.M)
            fields["id"] = default_id
        presets[fields["id"]] = fields
    return presets


def test_js_and_python_angle_maps_are_identical():
    assert _js_angle_map() == ANGLE_TO_DEFAULT_STYLE


def test_every_angle_maps_to_a_real_preset():
    for angle, style in ANGLE_TO_DEFAULT_STYLE.items():
        assert style in STYLE_MOTION_POLICIES, (angle, style)


@pytest.mark.parametrize("angle_key", [a["key"] for a in IT_ANGLE_CATALOG])
def test_every_it_angle_key_has_an_explicit_preset(angle_key):
    assert angle_key in ANGLE_TO_DEFAULT_STYLE
    assert default_style_for_angle({"angle_id": angle_key}) == ANGLE_TO_DEFAULT_STYLE[angle_key]
    assert default_style_for_angle({"angle_key": angle_key, "angle_id": "a1"}) == ANGLE_TO_DEFAULT_STYLE[angle_key]


def test_batch_suffixed_angle_ids_resolve_to_their_base_angle():
    assert default_style_for_angle({"angle_id": "spec_compare_b2"}) == "tech_compare"
    assert default_style_for_angle({"angle_id": "unknown_angle"}) is None


def test_explicit_batch_choice_overrides_angle_default():
    angle = {"angle_id": "stop_scroll"}
    assert resolve_batch_style_preset(angle, {"style_preset": "premium_minimal"}) == "premium_minimal"
    assert resolve_batch_style_preset({**angle, "style_preset": "smart_hack"}, {"style_preset": "premium_minimal"}) == "premium_minimal"


@pytest.mark.parametrize("no_choice", [None, "", "auto", "AUTO", "commercial_premium", "removed-style"])
def test_auto_or_unknown_choice_falls_back_to_angle_then_default(no_choice):
    options = {} if no_choice is None else {"style_preset": no_choice}
    assert resolve_batch_style_preset({"angle_id": "stop_scroll"}, options) == "viral_punch"
    assert resolve_batch_style_preset({"angle_id": "x", "style_preset": "smart_hack"}, options) == "smart_hack"
    assert resolve_batch_style_preset({"angle_id": "x"}, options) == "clean_tech_review"


def test_catalog_ids_match_renderer_policies():
    assert set(_js_presets()) == set(STYLE_MOTION_POLICIES)
    assert len(STYLE_MOTION_POLICIES) == 10


@pytest.mark.parametrize("preset_id", sorted(STYLE_MOTION_POLICIES))
def test_catalog_colours_match_policy(preset_id):
    policy = STYLE_MOTION_POLICIES[preset_id]
    preset = _js_presets()[preset_id]
    assert preset["accent"].upper() == policy.accent_color.upper()
    assert preset["status"].upper() == policy.status_color.upper()
    assert preset["neutral"].upper() == policy.neutral_color.upper()


@pytest.mark.parametrize("preset_id", sorted(STYLE_MOTION_POLICIES))
def test_color_theme_fallback_matches_policy(preset_id):
    policy = STYLE_MOTION_POLICIES[preset_id]
    fallback = STYLE_FALLBACKS[preset_id]
    assert fallback["primary"] == policy.accent_color.upper()
    assert fallback["secondary"] == policy.status_color.upper()
    assert fallback["neutral"] == policy.neutral_color.upper()


@pytest.mark.parametrize("preset_id", sorted(STYLE_MOTION_POLICIES))
def test_hook_color_is_the_colour_the_hook_actually_renders(preset_id):
    """hookColor mirrors the rendered hook template's brand colour.

    For tech_product_showcase (cyan hook, #FFCC33 accent) and smooth_showcase
    (mint hook, #25F4EE accent) hookColor intentionally differs from accent:
    setting it to accent would make the picker/schedule chip show a colour
    the rendered hook never uses.
    """
    preset = _js_presets()[preset_id]
    template = template_for_style_preset(preset_id)
    assert preset["hookTemplate"] == template
    brand_colour = HOOK_TEMPLATES[template]["tiers"]["brand"]["color"]
    assert preset["hookColor"].upper() == brand_colour.upper()


_TYPE_KEYWORD = {
    "dissolve": "Dissolve", "fade": "Fade", "circleopen": "Circle",
    "slideleft": "Slide", "slideright": "Slide",
    "wipeleft": "Wipe", "wiperight": "Wipe",
}


@pytest.mark.parametrize("preset_id", sorted(STYLE_MOTION_POLICIES))
def test_transition_label_names_the_transition_the_policy_renders(preset_id):
    """M5: the label names every transition type the policy can emit.

    Derived from apply_transition_budget itself (24 boundaries, a circleopen
    candidate) instead of a per-family guess, so a label can no longer promise
    an effect the renderer never plays, nor hide one it does.
    """
    from scripts.style_motion_policy import apply_transition_budget

    family = STYLE_MOTION_POLICIES[preset_id].transition_family
    if family == "adaptive":
        pytest.skip("adaptive family picks transitions from shot context")
    emitted = {
        apply_transition_budget({"type": "circleopen", "duration": 0.5},
                                style_preset=preset_id, boundary_index=i)["type"]
        for i in range(1, 25)
    } - {"cut"}
    label = _js_presets()[preset_id]["transitions"]
    assert emitted
    for kind in emitted:
        assert _TYPE_KEYWORD[kind] in label, (preset_id, kind, label)
    promised = {kw for kw in set(_TYPE_KEYWORD.values()) if kw in label}
    assert promised == {_TYPE_KEYWORD[k] for k in emitted}, (preset_id, promised, emitted)


def test_catalog_drops_effect_promises_the_renderer_does_not_keep():
    source = _js_source()
    for phrase in ("Wipe ซ้ายขวา", "Zoom เฉพาะส่วน", "Slide นุ่มนวล", "Fade เฉพาะ Section", "Fade เฉพาะจุดสำคัญ"):
        assert phrase not in source


def test_batch_modal_sends_real_preset_ids():
    source = BATCH_MODAL_JSX.read_text(encoding="utf-8")
    assert "commercial_premium" not in source
    assert "STYLE_PRESET_CATALOG" in source
    assert "AUTO_STYLE_PRESET" in source
