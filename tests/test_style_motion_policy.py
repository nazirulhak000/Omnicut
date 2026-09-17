"""Deterministic contracts for the project-level motion style policy."""

from scripts.pipeline_context import PipelineContext
from scripts.style_motion_policy import (
    apply_transition_budget,
    camera_keyframes_for_clip,
    resolve_style_motion_policy,
    style_visual_palette,
    style_motion_catalog,
)


def test_clean_tech_review_keeps_most_boundaries_as_hard_cuts():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.5},
            style_preset="clean_tech_review",
            boundary_index=index,
        )
        for index in range(1, 11)
    ]

    assert [pick["type"] for pick in picks] == [
        "cut", "cut", "cut", "cut", "dissolve",
        "cut", "cut", "cut", "cut", "circleopen",
    ]
    assert sum(pick["type"] == "cut" for pick in picks) == 8
    assert picks[4]["duration"] == 0.25
    assert picks[9]["duration"] == 0.35


def test_policy_caps_transition_duration_and_preserves_movement_slot():
    pick = apply_transition_budget(
        {"type": "slideleft", "duration": 0.9},
        style_preset="clean_tech_review",
        boundary_index=5,
    )

    assert pick == {"type": "slideleft", "duration": 0.35}


def test_clean_tech_review_camera_motion_is_subtle_and_budgeted():
    first = camera_keyframes_for_clip(
        1.25, 2.0, 0, style_preset="clean_tech_review"
    )
    rest = camera_keyframes_for_clip(
        1.25, 2.0, 1, style_preset="clean_tech_review"
    )
    short = camera_keyframes_for_clip(
        1.25, 0.5, 2, style_preset="clean_tech_review"
    )

    assert first == [
        {"time": 0.0, "zoom": 1.21, "pan_x": -0.14, "pan_y": 0.0},
        {"time": 2.0, "zoom": 1.29, "pan_x": 0.14, "pan_y": 0.0},
    ]
    assert rest == []
    assert short == []


def test_unknown_style_falls_back_to_golden_master_and_catalog_is_json_safe():
    assert resolve_style_motion_policy("not-a-style").key == "clean_tech_review"
    catalog = style_motion_catalog()
    assert set(catalog) == {
        "clean_tech_review",
        "viral_punch",
        "tech_product_showcase",
        "smooth_showcase",
        "premium_minimal",
        "flash_deal",
        "pain_punch",
        "tech_compare",
        "smart_hack",
        "niche_focus",
    }
    assert catalog["clean_tech_review"]["transition_stride"] == 5
    assert catalog["clean_tech_review"]["camera_motion_stride"] == 2


def test_viral_punch_uses_frequent_directional_motion_without_transition_spam():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.8},
            style_preset="viral_punch",
            boundary_index=index,
        )
        for index in range(1, 7)
    ]

    assert [pick["type"] for pick in picks] == [
        "cut", "slideleft", "cut", "slideright", "cut", "circleopen",
    ]
    assert all(pick.get("duration", 0.0) <= 0.28 for pick in picks)


def test_tech_product_showcase_keeps_product_motion_visible_but_budgeted():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.8},
            style_preset="tech_product_showcase",
            boundary_index=index,
        )
        for index in range(1, 7)
    ]

    assert [pick["type"] for pick in picks] == [
        "cut", "cut", "slideleft", "cut", "cut", "circleopen",
    ]
    assert all(pick.get("duration", 0.0) <= 0.30 for pick in picks)
    assert camera_keyframes_for_clip(
        1.2, 1.0, 0, style_preset="tech_product_showcase"
    ) == [
        {"time": 0.0, "zoom": 1.15, "pan_x": -0.16, "pan_y": 0.0},
        {"time": 1.0, "zoom": 1.25, "pan_x": 0.16, "pan_y": 0.0},
    ]


def test_smooth_and_premium_styles_apply_their_own_transition_families():
    smooth = apply_transition_budget(
        {"type": "wipeleft", "duration": 0.9},
        style_preset="smooth_showcase",
        boundary_index=3,
    )
    premium = apply_transition_budget(
        {"type": "circleopen", "duration": 0.9},
        style_preset="premium_minimal",
        boundary_index=6,
    )

    assert smooth == {"type": "dissolve", "duration": 0.35}
    assert premium == {"type": "fade", "duration": 0.3}


def test_style_preset_is_part_of_project_snapshot_contract():
    ctx = PipelineContext(
        product_name="Style contract",
        raw_video_path="raw.mp4",
        style_preset="clean_tech_review",
    )

    snapshot = ctx._manifest_snapshot_from_context()

    assert snapshot["style_preset"] == "clean_tech_review"
    assert snapshot["render_params"]["style_preset"] == "clean_tech_review"


def test_style_preset_visual_palette_is_explicit_and_serializable():
    palette = style_visual_palette("clean_tech_review")
    assert palette == {
        "accent_color": "#FFE600",
        "status_color": "#25F4EE",
        "neutral_color": "#FFFFFF",
    }
    assert style_visual_palette("unknown-style") == palette

    catalog = style_motion_catalog()["clean_tech_review"]
    assert catalog["accent_color"] == palette["accent_color"]
    assert catalog["status_color"] == palette["status_color"]
    assert catalog["neutral_color"] == palette["neutral_color"]
