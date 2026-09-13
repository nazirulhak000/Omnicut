"""Focused runtime wiring tests for ColorThemeV1."""

from scripts.color_theme import STYLE_FALLBACKS, resolve_color_theme
from scripts.api_schemas import RenderRequest
from scripts.pipeline_context import PipelineContext
from scripts.product_callout_builder import build_product_callouts


def _text(overlay):
    return ((overlay.get("tiers") or [{}])[0]).get("text") or ""


def test_explicit_theme_wins_over_product_colour_and_style():
    theme = resolve_color_theme(
        {"product_color": "#35C759"},
        explicit_theme={
            "primary": "#1234AB",
            "secondary": "#F06A3A",
            "neutral": "#F4F1E8",
            "ink": "#101010",
        },
        style_preset="clean_tech_review",
    )

    assert {key: theme[key] for key in ("primary", "secondary", "neutral", "ink")} == {
        "primary": "#1234AB",
        "secondary": "#F06A3A",
        "neutral": "#F4F1E8",
        "ink": "#101010",
    }


def test_green_product_uses_deterministic_orange_pair():
    theme = resolve_color_theme({"color": "#35C759"})

    assert theme["primary"] == "#35C759"
    assert theme["secondary"] == "#FF8A3D"
    assert theme["source_metadata"]["hue_sector"] == "green"


def test_default_clean_tech_review_fallback_remains_golden():
    theme = resolve_color_theme(style_preset="clean_tech_review")
    fallback = STYLE_FALLBACKS["clean_tech_review"]

    assert {key: theme[key] for key in fallback} == fallback
    assert theme["source_metadata"]["source"] == "style_fallback"


def test_callout_semantic_colour_is_deterministic_and_manual_look_wins():
    manual = {
        "id": "manual-feature",
        "kind": "text",
        "role": "product_callout",
        "origin": "manual",
        "callout_type": "feature",
        "start": 0,
        "end": 1,
        "text": "ANC",
        "look": {"color": "#FF00AA"},
    }
    overlays = build_product_callouts(
        [{"start": 0, "end": 1, "on_screen": "ANC"}],
        {"features": ["ANC", "Fast charge"]},
        [manual],
        {
            "primary": "#35C759",
            "secondary": "#FF8A3D",
            "neutral": "#FFFFFF",
            "ink": "#080B10",
        },
    )

    by_text = {_text(item): item for item in overlays}
    assert by_text["Fast charge"]["look"]["color"] == "#35C759"
    assert by_text["Fast charge"]["theme_role"] == "primary"
    assert by_text["ANC"]["look"]["color"] == "#FF00AA"


def test_manifest_reuses_resolved_theme_when_no_new_colour_or_override():
    persisted = resolve_color_theme({"product_color": "#35C759"})
    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path="unused.mp4",
        manifest={"color_theme": persisted},
    )

    assert ctx.resolve_color_theme_contract() == persisted


def test_render_request_accepts_explicit_color_theme_without_changing_defaults():
    request = RenderRequest(
        product_name="Gadget",
        raw_video_path="unused.mp4",
        key_features="Fast",
        pain_point="Slow",
        price_deal="Today",
        color_theme={"primary": "#35C759", "secondary": "#FF8A3D"},
    )

    assert request.color_theme["primary"] == "#35C759"
    assert request.style_preset == "clean_tech_review"
