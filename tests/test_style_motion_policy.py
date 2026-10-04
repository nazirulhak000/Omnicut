"""Deterministic contracts for the project-level motion style policy.

Commit 0a07a34 expanded STYLE_MOTION_POLICIES from 5 to 10 styles.
This file now covers all 10 with both catalog completeness checks and
per-style behavioural contracts.
"""

from scripts.pipeline_context import PipelineContext
from scripts.style_motion_policy import (
    apply_transition_budget,
    camera_keyframes_for_clip,
    resolve_style_motion_policy,
    style_visual_palette,
    style_motion_catalog,
)

# ---------------------------------------------------------------------------
# clean_tech_review (stride-5, adaptive)
# ---------------------------------------------------------------------------


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

    # clean_tech_review is a calm style: its slide settles with ease_in_out.
    assert pick == {"type": "slideleft", "duration": 0.35, "easing": "ease_in_out"}


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
        {"time": 2.0, "zoom": 1.29, "pan_x": 0.14, "pan_y": 0.0, "easing": "ease_in_out"},
    ]
    assert rest == []
    assert short == []


# ---------------------------------------------------------------------------
# Catalog completeness — ALL 10 styles must be present
# ---------------------------------------------------------------------------


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


def test_catalog_has_exactly_10_styles():
    """Guard against accidental additions or deletions."""
    assert len(style_motion_catalog()) == 10


# ---------------------------------------------------------------------------
# viral_punch (stride-2, energetic)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# tech_product_showcase (stride-3, energetic)
# ---------------------------------------------------------------------------


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
        {"time": 1.0, "zoom": 1.25, "pan_x": 0.16, "pan_y": 0.0, "easing": "ease_in_out"},
    ]


# ---------------------------------------------------------------------------
# smooth_showcase (stride-3, smooth) + premium_minimal (stride-6, minimal)
# ---------------------------------------------------------------------------


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
    assert premium == {"type": "fade", "duration": 0.3, "easing": "ease_in_out"}


# ---------------------------------------------------------------------------
# flash_deal (stride-2, energetic) — added in commit 0a07a34
# ---------------------------------------------------------------------------


def test_flash_deal_is_energetic_and_respects_stride_2():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.9},
            style_preset="flash_deal",
            boundary_index=index,
        )
        for index in range(1, 7)
    ]
    # stride-2 energetic: cut, slideleft, cut, slideright, cut, stylized
    assert [pick["type"] for pick in picks] == [
        "cut", "slideleft", "cut", "slideright", "cut", "circleopen",
    ]
    assert all(pick.get("duration", 0.0) <= 0.28 for pick in picks)
    assert style_motion_catalog()["flash_deal"]["accent_color"] == "#FF7A00"


# ---------------------------------------------------------------------------
# pain_punch (stride-2, energetic, stylized_stride=5) — added in commit 0a07a34
# ---------------------------------------------------------------------------


def test_pain_punch_is_energetic_with_pink_accent():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.9},
            style_preset="pain_punch",
            boundary_index=index,
        )
        for index in range(1, 7)
    ]
    # pain_punch: stride=2, stylized_stride=5
    # boundary % stride != 0  => cut (off-stride)
    # boundary % stride == 0  => energetic movement slot:
    #   if boundary % stylized_stride == 0 => circleopen
    #   else => slideleft/slideright alternating
    # boundary 1: 1%2=1 -> cut
    # boundary 2: 2%2=0, 2%5=2 -> slideleft (slot=1, 1%2=1 -> slideleft)
    # boundary 3: 3%2=1 -> cut
    # boundary 4: 4%2=0, 4%5=4 -> slideright (slot=2, 2%2=0 -> slideright)
    # boundary 5: 5%2=1 -> cut  (5 is NOT a stride-2 slot, it's off-stride!)
    # boundary 6: 6%2=0, 6%5=1 -> slideleft (slot=3, 3%2=1 -> slideleft)
    assert picks[0]["type"] == "cut"       # boundary 1
    assert picks[1]["type"] == "slideleft" # boundary 2
    assert picks[2]["type"] == "cut"       # boundary 3
    assert picks[3]["type"] == "slideright"# boundary 4
    assert picks[4]["type"] == "cut"       # boundary 5 — off-stride! 5%2=1
    assert picks[5]["type"] == "slideleft" # boundary 6
    assert all(pick.get("duration", 0.0) <= 0.28 for pick in picks)
    assert style_motion_catalog()["pain_punch"]["accent_color"] == "#FF2E93"


# ---------------------------------------------------------------------------
# tech_compare (stride-3, adaptive) — added in commit 0a07a34
# ---------------------------------------------------------------------------


def test_tech_compare_uses_adaptive_family_and_stride_3():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.9},
            style_preset="tech_compare",
            boundary_index=index,
        )
        for index in range(1, 7)
    ]
    # tech_compare: stride=3, stylized_stride=6, family="adaptive"
    # adaptive family: on stride slot with stylized kind and stylized_stride check:
    #   kind="circleopen" in _STYLIZED_TRANSITIONS and 3%6!=0 => dissolve
    #   kind="circleopen" in _STYLIZED_TRANSITIONS and 6%6==0 => kind passes through (circleopen)
    # boundary 1,2: off-stride -> cut
    # boundary 3: on-stride, adaptive, kind=circleopen in STYLIZED, 3%6!=0 -> dissolve
    # boundary 4,5: off-stride -> cut
    # boundary 6: on-stride, adaptive, kind=circleopen in STYLIZED, 6%6==0 -> circleopen passes
    assert [pick["type"] for pick in picks] == [
        "cut", "cut", "dissolve", "cut", "cut", "circleopen",
    ]
    assert all(pick.get("duration", 0.0) <= 0.32 for pick in picks)
    assert style_motion_catalog()["tech_compare"]["accent_color"] == "#3B82F6"


# ---------------------------------------------------------------------------
# smart_hack (stride-3, smooth) — added in commit 0a07a34
# ---------------------------------------------------------------------------


def test_smart_hack_uses_smooth_dissolve_family():
    pick_on_stride = apply_transition_budget(
        {"type": "wipeleft", "duration": 0.9},
        style_preset="smart_hack",
        boundary_index=3,
    )
    pick_off_stride = apply_transition_budget(
        {"type": "wipeleft", "duration": 0.9},
        style_preset="smart_hack",
        boundary_index=1,
    )
    # smooth family coerces the transition to dissolve on budget slots
    assert pick_on_stride == {"type": "dissolve", "duration": 0.30}
    assert pick_off_stride == {"type": "cut", "duration": 0.0}
    assert style_motion_catalog()["smart_hack"]["accent_color"] == "#84CC16"


# ---------------------------------------------------------------------------
# niche_focus (stride-4, energetic) — added in commit 0a07a34
# ---------------------------------------------------------------------------


def test_niche_focus_energetic_stride_4_with_purple_accent():
    picks = [
        apply_transition_budget(
            {"type": "circleopen", "duration": 0.9},
            style_preset="niche_focus",
            boundary_index=index,
        )
        for index in range(1, 9)
    ]
    _STYLIZED = {"circleopen", "circleclose", "wipeleft", "wiperight", "wipeup", "wipedown"}
    # niche_focus: stride=4, stylized_stride=6, family="energetic"
    # boundary 1,2,3: off-stride -> cut
    # boundary 4: 4%4=0, 4%6=4 -> energetic slideleft (slot=1, 1%2=1)
    # boundary 5: off-stride -> cut
    # boundary 6: 6%4=2 != 0 -> off-stride -> cut  (NOT a stride-4 slot!)
    # boundary 7: off-stride -> cut
    # boundary 8: 8%4=0, 8%6=2 -> energetic slideright (slot=2, 2%2=0)
    assert picks[0]["type"] == "cut"        # boundary 1
    assert picks[1]["type"] == "cut"        # boundary 2
    assert picks[2]["type"] == "cut"        # boundary 3
    assert picks[3]["type"] == "slideleft"  # boundary 4 — first stride-4 hit
    assert picks[4]["type"] == "cut"        # boundary 5
    assert picks[5]["type"] == "cut"        # boundary 6 — 6%4=2, off-stride!
    assert picks[6]["type"] == "cut"        # boundary 7
    assert picks[7]["type"] == "slideright" # boundary 8 — second stride-4 hit
    assert all(pick.get("duration", 0.0) <= 0.30 for pick in picks)
    assert style_motion_catalog()["niche_focus"]["accent_color"] == "#A855F7"


# ---------------------------------------------------------------------------
# Shared contracts (pipeline context + visual palette)
# ---------------------------------------------------------------------------


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


def test_all_10_styles_resolve_without_fallback():
    """Every known style key must resolve to its own policy, not the default."""
    known_styles = [
        "clean_tech_review", "viral_punch", "tech_product_showcase",
        "smooth_showcase", "premium_minimal",
        "flash_deal", "pain_punch", "tech_compare", "smart_hack", "niche_focus",
    ]
    for style in known_styles:
        policy = resolve_style_motion_policy(style)
        assert policy.key == style, f"Expected key={style!r}, got {policy.key!r}"


def test_all_10_styles_have_valid_accent_and_transition_config():
    """Guard that each catalog entry is well-formed."""
    catalog = style_motion_catalog()
    for key, entry in catalog.items():
        assert entry["accent_color"].startswith("#"), f"{key}: bad accent_color"
        assert entry["transition_stride"] >= 1, f"{key}: transition_stride must be >= 1"
        assert entry["max_transition_duration"] > 0, f"{key}: max_transition_duration must be > 0"


# ---------------------------------------------------------------------------
# Cut rhythm per style (round EDITOR-CUT-QUALITY-R2)
# ---------------------------------------------------------------------------


def test_golden_master_cut_rhythm_equals_the_old_global_constants():
    from scripts.config import J_CUT_OFFSET_SECONDS, MAX_SHOT_DURATION, MIN_SHOT_DURATION

    policy = resolve_style_motion_policy("clean_tech_review")
    assert (policy.min_shot, policy.max_shot, policy.j_lead, policy.beat_snap_tolerance) == (
        MIN_SHOT_DURATION, MAX_SHOT_DURATION, J_CUT_OFFSET_SECONDS, 0.15,
    )
    # an unknown / unset style resolves to the same numbers
    assert resolve_style_motion_policy(None).j_lead == J_CUT_OFFSET_SECONDS


def test_every_style_cut_rhythm_stays_inside_the_gadget_and_j_cut_rules():
    rhythms = set()
    for key, entry in style_motion_catalog().items():
        # gadget rule: shots 1.5-3.0 s
        assert 1.5 <= entry["min_shot"] < entry["max_shot"] <= 3.0, key
        # J-cut 150-250 ms even after +-17 ms frame rounding
        assert 0.17 <= entry["j_lead"] <= 0.22, key
        # a beat snap can never pull the picture in front of the voice
        assert 0 < entry["beat_snap_tolerance"] <= entry["j_lead"], key
        rhythms.add((entry["min_shot"], entry["max_shot"], entry["j_lead"], entry["beat_snap_tolerance"]))
    assert len(rhythms) == 10, "each style should have its own cut rhythm"


# ---------------------------------------------------------------------------
# Slide direction follows the outgoing shot's pan
# ---------------------------------------------------------------------------


def test_slide_direction_sign_table():
    from scripts.style_motion_policy import orient_slide_to_pan

    rising = [{"time": 0.0, "pan_x": -0.1}, {"time": 2.0, "pan_x": 0.1, "easing": "ease_in_out"}]
    falling = [{"time": 0.0, "pan_x": 0.1}, {"time": 2.0, "pan_x": -0.1, "easing": "ease_in_out"}]
    still = [{"time": 0.0, "zoom": 1.0, "pan_x": 0.0}, {"time": 2.0, "zoom": 1.1, "pan_x": 0.0}]
    property_shape = [
        {"time": 0.0, "property": "pan_x", "value": 0.2},
        {"time": 1.0, "property": "pan_x", "value": 0.5},
    ]
    for pick in ("slideleft", "slideright"):
        # pan_x rising = crop window moves right = camera pans right = content moves left
        assert orient_slide_to_pan({"type": pick, "duration": 0.3}, rising)["type"] == "slideleft"
        assert orient_slide_to_pan({"type": pick, "duration": 0.3}, falling)["type"] == "slideright"
        assert orient_slide_to_pan({"type": pick, "duration": 0.3}, property_shape)["type"] == "slideleft"
        # no pan -> today's slot alternation is kept
        assert orient_slide_to_pan({"type": pick}, still)["type"] == pick
        assert orient_slide_to_pan({"type": pick}, None)["type"] == pick
    # non-slide picks are never touched, and the duration survives
    assert orient_slide_to_pan({"type": "dissolve"}, rising) == {"type": "dissolve"}
    assert orient_slide_to_pan({"type": "slideright", "duration": 0.28}, rising) == {
        "type": "slideleft", "duration": 0.28,
    }


def test_generated_camera_pan_sign_matches_the_slide_it_picks():
    from scripts.style_motion_policy import orient_slide_to_pan

    # camera_keyframes_for_clip: even motion slots pan right (pan_x rising)
    kf = camera_keyframes_for_clip(1.2, 2.0, 0, style_preset="viral_punch")
    assert kf[-1]["pan_x"] > kf[0]["pan_x"]
    assert orient_slide_to_pan({"type": "slideright"}, kf)["type"] == "slideleft"


# ---------------------------------------------------------------------------
# Eased transitions per style (round EDITOR-CUT-QUALITY-R2, lane E3)
# ---------------------------------------------------------------------------

STYLE_EASING = {
    # calm / premium: settle softly
    "smooth_showcase": "ease_in_out",
    "premium_minimal": "ease_in_out",
    "clean_tech_review": "ease_in_out",
    "tech_product_showcase": "ease_in_out",
    "niche_focus": "ease_in_out",
    "tech_compare": "ease_in_out",
    # punchy: hit fast, decelerate
    "viral_punch": "ease_out",
    "flash_deal": "ease_out",
    "pain_punch": "ease_out",
    "smart_hack": "ease_out",
}
HONOURS_EASING = {
    "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
}
CANDIDATE_KINDS = (
    "circleopen", "circleclose", "dissolve", "fade", "fadeblack", "fadewhite",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
)


def test_every_style_has_an_easing_in_the_catalog_table():
    from scripts.video_editor import CAMERA_EASINGS

    catalog = style_motion_catalog()
    assert set(STYLE_EASING) == set(catalog)
    for key, entry in catalog.items():
        assert entry["transition_easing"] == STYLE_EASING[key], key
        assert entry["transition_easing"] in CAMERA_EASINGS, key
        assert resolve_style_motion_policy(key).transition_easing == STYLE_EASING[key]


def test_policy_only_eases_types_the_renderer_honours_and_never_the_costly_ones():
    from scripts.style_motion_policy import _POLICY_EASED_TRANSITIONS
    from scripts.video_editor import EASED_TRANSITIONS

    assert _POLICY_EASED_TRANSITIONS == HONOURS_EASING
    assert _POLICY_EASED_TRANSITIONS <= set(EASED_TRANSITIONS)
    # fadeblack/fadewhite render ~8-13 s slower per eased transition
    for kind in ("fadeblack", "fadewhite", "dissolve", "circleopen", "circleclose", "cut"):
        assert kind not in _POLICY_EASED_TRANSITIONS


def test_generated_transitions_carry_the_style_easing_only_on_supported_types():
    eased_per_style = {}
    for style, expected in STYLE_EASING.items():
        eased_per_style[style] = 0
        for kind in CANDIDATE_KINDS:
            for index in range(1, 25):
                pick = apply_transition_budget(
                    {"type": kind, "duration": 0.5}, style_preset=style, boundary_index=index,
                )
                where = f"{style}/{kind}/{index}"
                if pick["type"] == "cut":
                    assert pick == {"type": "cut", "duration": 0.0}, where
                elif pick["type"] in HONOURS_EASING:
                    assert pick["easing"] == expected, where
                    eased_per_style[style] += 1
                else:
                    # dissolve, circleopen/close, fadeblack/fadewhite: linear
                    assert "easing" not in pick, where
    # Not vacuous: styles that can pick a slide/fade/wipe do get an easing
    # (smooth_showcase and smart_hack are dissolve-only families).
    for style, count in eased_per_style.items():
        if style in ("smooth_showcase", "smart_hack"):
            assert count == 0, style
        else:
            assert count > 0, style


def test_policy_never_changes_type_or_duration_when_it_adds_easing():
    for style in STYLE_EASING:
        for kind in CANDIDATE_KINDS:
            for index in range(1, 13):
                pick = apply_transition_budget(
                    {"type": kind, "duration": 0.5}, style_preset=style, boundary_index=index,
                )
                bare = {key: value for key, value in pick.items() if key != "easing"}
                assert set(bare) == {"type", "duration"}
                assert apply_transition_budget(
                    {"type": kind, "duration": 0.5}, style_preset=style, boundary_index=index,
                ) == pick  # deterministic


def test_an_easing_already_on_the_pick_is_kept_and_unsupported_types_drop_it():
    kept = apply_transition_budget(
        {"type": "slideleft", "duration": 0.3, "easing": "ease_in"},
        style_preset="viral_punch", boundary_index=2,
    )
    assert kept["easing"] == "ease_in"
    dropped = apply_transition_budget(
        {"type": "circleopen", "duration": 0.3, "easing": "ease_in"},
        style_preset="viral_punch", boundary_index=6,
    )
    assert dropped["type"] == "circleopen" and "easing" not in dropped


def test_refill_path_gives_the_same_style_easing_and_slide_orientation_keeps_it():
    from scripts.stages.video_assembly_stage import _fill_undecided_transitions

    def clips(n):
        return [{"id": f"c{i}", "zoom": 1.0} for i in range(n)]

    for style, expected in STYLE_EASING.items():
        picks = _fill_undecided_transitions(clips(13), style)
        assert len(picks) == 12
        for pick in picks:
            if pick["type"] in HONOURS_EASING:
                assert pick["easing"] == expected, style
            else:
                assert "easing" not in pick, (style, pick)

    # a rising pan flips a generated slide to slideleft and the easing survives
    rising = [{"time": 0.0, "pan_x": -0.1}, {"time": 2.0, "pan_x": 0.1, "easing": "ease_in_out"}]
    base = clips(3)
    base[1]["keyframes"] = rising
    picks = _fill_undecided_transitions(base, "viral_punch")
    assert picks[1] == {"type": "slideleft", "duration": 0.28, "easing": "ease_out"}


def _graph_for(style, n_clips, tmp_path, monkeypatch):
    from scripts.stages.video_assembly_stage import _fill_undecided_transitions
    from tests.test_frame_grid_timing import _fake_clips, capture_graph

    clips = _fake_clips(tmp_path, [(0.0, 1.5, {"zoom": 1.0}) for _ in range(n_clips)])
    transitions = _fill_undecided_transitions(clips, style)
    graph = capture_graph(tmp_path, monkeypatch, clips, transitions, 1.5 * n_clips)
    return transitions, graph


def test_generated_plan_renders_the_easing_expression_through_the_real_graph(tmp_path, monkeypatch):
    # viral_punch over 7 clips: cut, slide, cut, slide, cut, circleopen
    transitions, graph = _graph_for("viral_punch", 7, tmp_path, monkeypatch)
    kinds = [t["type"] for t in transitions]
    assert [k.startswith("slide") for k in kinds[:5]] == [False, True, False, True, False]
    assert kinds[0] == kinds[2] == kinds[4] == "cut"
    assert transitions[5]["type"] == "circleopen"
    # supported type: custom expression with the ease_out curve (P*P)
    assert graph.count("xfade=transition=custom:expr=") == 2
    assert "(P*P)" in graph
    # unsupported type: untouched built-in transition, no easing expression for it
    assert graph.count("xfade=transition=circleopen:duration=") == 1
    assert "xfade=transition=slide" not in graph

    # premium_minimal over 7 clips: only boundary 6 is a (calm, eased) fade
    transitions, graph = _graph_for("premium_minimal", 7, tmp_path, monkeypatch)
    assert [t["type"] for t in transitions].count("fade") == 1
    assert graph.count("xfade=transition=custom:expr=") == 1
    assert "(if(gt(P,0.5),1-2*(1-P)*(1-P),2*P*P))" in graph

    # smooth_showcase picks dissolve only: the graph keeps the built-in text
    transitions, graph = _graph_for("smooth_showcase", 7, tmp_path, monkeypatch)
    assert {t["type"] for t in transitions} <= {"cut", "dissolve"}
    assert "xfade=transition=custom" not in graph
    assert "xfade=transition=dissolve:duration=" in graph
