"""M5: all ten style presets must be genuinely different, deterministically.

The audit (AI_EDITOR_VIRAL_AUDIT_20261031 s3) found only four distinct motion
families; the user chose to KEEP all ten presets and make each one feel
different. This file is the guard: a numeric distance between every pair of
presets, a structural "no two presets share a motion recipe" check, and a
transition fingerprint check. Offline and deterministic: no render, no I/O
beyond reading the catalog.

Metric (documented so the threshold is not magic)
-------------------------------------------------
Each preset becomes a vector:
  * 13 numeric policy fields, each scaled to 0..1 by a FIXED span
    (``SPAN``: the sane range every preset must stay inside), so a field moving
    across its whole span contributes 1.0 and a 10% move contributes 0.1;
  * 3 categorical fields (transition family, transition easing, camera
    easing) contributing ``CATEGORICAL_WEIGHT`` (0.5) when two presets differ.
The distance is Euclidean. ``MIN_PAIRWISE_DISTANCE`` is 0.90.

Before M5 the closest pairs were viral_punch/flash_deal 0.17,
viral_punch/pain_punch 0.26, flash_deal/pain_punch 0.35, tech_product_showcase/
niche_focus 0.68 and clean_tech_review/tech_compare 0.88 (all below 0.90);
after M5 the minimum over all 45 pairs is about 0.97.
"""

import itertools
import math
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.style_motion_policy import (
    CAMERA_EASING_NAMES,
    DEFAULT_CAMERA_EASING,
    STYLE_MOTION_POLICIES,
    apply_transition_budget,
    camera_keyframes_for_clip,
    resolve_style_motion_policy,
    style_motion_catalog,
    style_motion_policy_from_dict,
)

ROOT = Path(__file__).resolve().parents[1]

# (low, high) of the sane range for each numeric field; the span is hi - lo.
SPAN = {
    "transition_stride": (1, 6),
    "stylized_stride": (0, 12),
    "max_transition_duration": (0.15, 0.40),
    "camera_motion_stride": (1, 3),
    "camera_zoom_delta": (0.03, 0.24),
    "camera_pan_extent": (0.04, 0.30),
    "camera_min_duration": (0.5, 1.5),
    "min_shot": (1.5, 2.0),
    "max_shot": (1.8, 3.0),
    "j_lead": (0.17, 0.22),
    "beat_snap_tolerance": (0.08, 0.16),
    "hook_max_shot": (0.9, 1.8),
    "max_static_sec": (1.8, 3.5),
}
CATEGORICAL = ("transition_family", "transition_easing", "camera_easing")
CATEGORICAL_WEIGHT = 0.5
MIN_PAIRWISE_DISTANCE = 0.90


def style_distance(a, b) -> float:
    total = 0.0
    for field, (lo, hi) in SPAN.items():
        total += ((getattr(a, field) - lo) / (hi - lo) - (getattr(b, field) - lo) / (hi - lo)) ** 2
    for field in CATEGORICAL:
        if getattr(a, field) != getattr(b, field):
            total += CATEGORICAL_WEIGHT ** 2
    return math.sqrt(total)


def _pairs(policies):
    return sorted(
        ((style_distance(policies[a], policies[b]), a, b) for a, b in itertools.combinations(sorted(policies), 2)),
        key=lambda row: row[0],
    )


# The ten presets exactly as they were before M5 (hook/static from the family
# default, camera easing the old fixed ease_in_out). Kept so the metric is
# demonstrably not vacuous: it must FAIL on the old near-duplicates.
_LEGACY_FIELDS = (
    "transition_stride", "stylized_stride", "max_transition_duration", "transition_family",
    "camera_motion_stride", "camera_zoom_delta", "camera_pan_extent", "camera_min_duration",
    "min_shot", "max_shot", "j_lead", "beat_snap_tolerance", "transition_easing",
    "hook_max_shot", "max_static_sec",
)
_LEGACY_ROWS = {
    "clean_tech_review": (5, 10, .35, "adaptive", 2, .08, .14, .8, 1.5, 2.5, .18, .15, "ease_in_out", 1.3, 2.5),
    "viral_punch": (2, 6, .28, "energetic", 1, .12, .18, .65, 1.5, 2.2, .17, .12, "ease_out", 1.0, 2.0),
    "tech_product_showcase": (3, 6, .30, "energetic", 1, .10, .16, .75, 1.6, 2.6, .18, .12, "ease_in_out", 1.0, 2.0),
    "smooth_showcase": (3, 0, .35, "smooth", 1, .05, .08, 1.0, 1.8, 2.8, .21, .10, "ease_in_out", 1.5, 3.0),
    "premium_minimal": (6, 0, .30, "minimal", 3, .04, .06, 1.2, 1.8, 3.0, .22, .08, "ease_in_out", 1.8, 3.5),
    "flash_deal": (2, 6, .28, "energetic", 1, .12, .18, .65, 1.5, 2.0, .17, .12, "ease_out", 1.0, 2.0),
    "pain_punch": (2, 5, .28, "energetic", 1, .14, .16, .65, 1.5, 2.3, .18, .12, "ease_out", 1.0, 2.0),
    "tech_compare": (3, 6, .32, "adaptive", 2, .08, .14, .8, 1.7, 2.7, .20, .12, "ease_in_out", 1.3, 2.5),
    "smart_hack": (3, 0, .30, "smooth", 1, .06, .10, .9, 1.6, 2.4, .18, .14, "ease_out", 1.5, 3.0),
    "niche_focus": (4, 6, .30, "energetic", 2, .10, .14, .85, 1.6, 2.6, .20, .12, "ease_in_out", 1.0, 2.0),
}
LEGACY = {
    key: SimpleNamespace(**dict(zip(_LEGACY_FIELDS, row)), camera_easing="ease_in_out")
    for key, row in _LEGACY_ROWS.items()
}


def test_the_metric_catches_the_pre_m5_near_duplicates():
    rows = _pairs(LEGACY)
    near = {(a, b): d for d, a, b in rows}
    assert near[("flash_deal", "viral_punch")] < 0.2
    assert near[("pain_punch", "viral_punch")] < 0.3
    assert near[("flash_deal", "pain_punch")] < 0.4
    assert near[("niche_focus", "tech_product_showcase")] < MIN_PAIRWISE_DISTANCE
    assert near[("clean_tech_review", "tech_compare")] < MIN_PAIRWISE_DISTANCE
    assert rows[0][0] < MIN_PAIRWISE_DISTANCE  # the old catalog fails the gate


def test_every_pair_of_the_ten_presets_is_far_enough_apart():
    assert len(STYLE_MOTION_POLICIES) == 10
    rows = _pairs(STYLE_MOTION_POLICIES)
    assert len(rows) == 45
    too_close = [(a, b, round(d, 3)) for d, a, b in rows if d < MIN_PAIRWISE_DISTANCE]
    assert not too_close, too_close


def test_presets_stay_inside_the_sane_ranges_the_vector_assumes():
    for key, policy in STYLE_MOTION_POLICIES.items():
        for field, (lo, hi) in SPAN.items():
            assert lo - 1e-9 <= getattr(policy, field) <= hi + 1e-9, (key, field)


def test_no_two_presets_share_a_motion_recipe():
    recipes = {}
    for key, policy in STYLE_MOTION_POLICIES.items():
        recipe = (
            policy.transition_family,
            policy.transition_stride,
            policy.camera_motion_stride,
            (policy.min_shot, policy.max_shot),
        )
        assert recipe not in recipes, (key, recipes.get(recipe))
        recipes[recipe] = key
    assert len(recipes) == 10


def _fingerprint(key):
    return tuple(
        apply_transition_budget({"type": "circleopen", "duration": 0.5}, style_preset=key, boundary_index=i)["type"]
        for i in range(1, 25)
    )


def test_every_preset_has_its_own_transition_fingerprint():
    """What the viewer sees at the joins differs, not just the numbers.

    The first 24 boundaries of every preset (the picker offered a circleopen)
    must be a unique pattern of cut / slide / wipe / dissolve / fade / circle.
    smooth_showcase and smart_hack used to be the same dissolve-every-3 plan.
    """
    prints = {key: _fingerprint(key) for key in STYLE_MOTION_POLICIES}
    seen = {}
    for key, fp in prints.items():
        assert fp not in seen, (key, seen.get(fp))
        seen[fp] = key
    # the dissolve look belongs to smooth_showcase alone
    dissolving = [k for k, fp in prints.items() if "dissolve" in fp]
    assert "smooth_showcase" in dissolving
    assert "smart_hack" not in dissolving and "tech_compare" not in dissolving


# -- the design intent of each preset, pinned -------------------------------


def _p(key):
    return resolve_style_motion_policy(key)


def test_punch_group_is_three_different_things():
    viral, flash, pain = _p("viral_punch"), _p("flash_deal"), _p("pain_punch")
    # flash_deal: the densest cuts of any preset, the tightest hook, a calmer camera
    assert flash.max_shot == min(p.max_shot for p in STYLE_MOTION_POLICIES.values())
    assert flash.hook_max_shot == min(p.hook_max_shot for p in STYLE_MOTION_POLICIES.values())
    assert flash.camera_zoom_delta < viral.camera_zoom_delta
    assert flash.camera_motion_stride > viral.camera_motion_stride
    # pain_punch: the heaviest zoom-in of any preset, mostly push (little pan),
    # slower cuts than flash_deal, and the impact lands with ease_out
    assert pain.camera_zoom_delta == max(p.camera_zoom_delta for p in STYLE_MOTION_POLICIES.values())
    assert pain.camera_pan_extent < pain.camera_zoom_delta
    assert pain.min_shot > flash.min_shot and pain.max_shot > flash.max_shot
    assert pain.camera_easing == "ease_out"
    # viral_punch keeps the identity it had (the base of the group)
    assert (viral.transition_stride, viral.camera_zoom_delta, viral.max_shot) == (2, 0.12, 2.2)


def test_tech_group_separates_pan_forward_from_tight_push_in():
    showcase, niche = _p("tech_product_showcase"), _p("niche_focus")
    assert showcase.camera_pan_extent == max(p.camera_pan_extent for p in STYLE_MOTION_POLICIES.values())
    assert showcase.camera_pan_extent > showcase.camera_zoom_delta
    assert niche.camera_zoom_delta > niche.camera_pan_extent
    assert niche.camera_zoom_delta > showcase.camera_zoom_delta
    assert niche.min_shot > showcase.min_shot  # longer holds


def test_smart_hack_is_crisp_not_a_smooth_clone():
    hack, smooth = _p("smart_hack"), _p("smooth_showcase")
    assert hack.transition_family != "smooth"
    assert hack.max_transition_duration < smooth.max_transition_duration
    assert hack.camera_min_duration < smooth.camera_min_duration  # quick nudges
    assert hack.transition_stride > smooth.transition_stride  # more hard cuts
    types = {t for t in _fingerprint("smart_hack")}
    assert types == {"cut", "slideleft", "slideright"}


def test_clean_default_keeps_its_body_and_tightens_only_the_hook():
    clean = _p("clean_tech_review")
    assert (clean.min_shot, clean.max_shot, clean.j_lead, clean.beat_snap_tolerance) == (1.5, 2.5, 0.18, 0.15)
    assert (clean.transition_stride, clean.camera_motion_stride) == (5, 2)
    assert clean.hook_max_shot == 1.2 < 1.3  # was 1.3 (adaptive family default)
    assert clean.camera_easing == DEFAULT_CAMERA_EASING


def test_premium_minimal_stays_the_most_restrained():
    premium = _p("premium_minimal")
    others = [p for k, p in STYLE_MOTION_POLICIES.items() if k != "premium_minimal"]
    assert premium.transition_stride == max(p.transition_stride for p in STYLE_MOTION_POLICIES.values())
    assert premium.camera_motion_stride == max(p.camera_motion_stride for p in STYLE_MOTION_POLICIES.values())
    assert premium.camera_zoom_delta < min(p.camera_zoom_delta for p in others)
    # (niche_focus and pain_punch push in with almost no pan, so pan is only
    # bounded, not minimal)
    assert premium.camera_pan_extent <= 0.06
    assert premium.max_shot == 3.0 and premium.camera_easing == DEFAULT_CAMERA_EASING


def test_tech_compare_is_a_regular_wipe_slide_rhythm():
    compare = _p("tech_compare")
    assert compare.transition_family == "compare"
    kinds = [t for t in _fingerprint("tech_compare") if t != "cut"]
    assert kinds[:4] == ["wipeleft", "slideleft", "wiperight", "slideleft"]
    gaps = {
        b - a
        for a, b in zip(
            [i for i, t in enumerate(_fingerprint("tech_compare")) if t != "cut"],
            [i for i, t in enumerate(_fingerprint("tech_compare")) if t != "cut"][1:],
        )
    }
    assert gaps == {compare.transition_stride}  # perfectly regular
    # an even cadence: the narrowest shot-length window after flash_deal
    spreads = {k: p.max_shot - p.min_shot for k, p in STYLE_MOTION_POLICIES.items()}
    assert spreads["tech_compare"] <= sorted(spreads.values())[1] + 1e-9


@pytest.mark.parametrize("key", sorted(STYLE_MOTION_POLICIES))
def test_retention_bounds_from_the_s1_audit_hold_for_every_preset(key):
    policy = _p(key)
    assert policy.hook_max_shot <= 1.8
    assert policy.max_static_sec <= 3.5
    assert policy.max_shot <= 3.0
    assert policy.beat_snap_tolerance <= policy.j_lead  # never in front of the voice
    assert 0.17 <= policy.j_lead <= 0.22


# -- the one new field: camera_easing ----------------------------------------


def test_camera_easing_is_in_the_catalog_and_is_a_valid_renderer_easing():
    for key, entry in style_motion_catalog().items():
        assert entry["camera_easing"] in CAMERA_EASING_NAMES, key
        assert entry["camera_easing"] == STYLE_MOTION_POLICIES[key].camera_easing


def test_camera_easing_names_match_renderer_and_preview_tables():
    """Preview parity: the preview reads the keyframe's own `easing`, so the
    names the policy may write must exist in BOTH easing tables."""
    from scripts.video_editor import CAMERA_EASINGS

    assert set(CAMERA_EASING_NAMES) == set(CAMERA_EASINGS)
    js = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
    block = js[js.index("export const CAMERA_EASINGS"):]
    block = block[: block.index("};")]
    assert set(re.findall(r"^\s*(\w+)\s*:", block, flags=re.M)) == set(CAMERA_EASING_NAMES)


@pytest.mark.parametrize("key", sorted(STYLE_MOTION_POLICIES))
def test_generated_camera_move_carries_the_styles_easing_in_the_manifest_keyframe(key):
    policy = _p(key)
    for index in range(0, 6):
        frames = camera_keyframes_for_clip(1.2, 2.0, index, style_preset=key)
        if frames:
            assert frames[0].get("easing") is None
            assert frames[-1]["easing"] == policy.camera_easing
            break
    else:  # pragma: no cover
        pytest.fail(f"{key} never animated a 2 s shot")


def test_an_unknown_camera_easing_falls_back_to_the_default():
    from dataclasses import replace

    from scripts import style_motion_policy as module

    bad = replace(STYLE_MOTION_POLICIES["viral_punch"], camera_easing="bounce")
    original = module.STYLE_MOTION_POLICIES["viral_punch"]
    module.STYLE_MOTION_POLICIES["viral_punch"] = bad
    try:
        frames = camera_keyframes_for_clip(1.2, 2.0, 0, style_preset="viral_punch")
    finally:
        module.STYLE_MOTION_POLICIES["viral_punch"] = original
    assert frames[-1]["easing"] == DEFAULT_CAMERA_EASING


def test_a_serialized_policy_from_before_m5_keeps_its_old_camera_easing():
    old = {k: v for k, v in style_motion_catalog()["pain_punch"].items() if k != "camera_easing"}
    assert style_motion_policy_from_dict(old).camera_easing == DEFAULT_CAMERA_EASING
    # a current entry (with the field) keeps its own value
    current = style_motion_catalog()["pain_punch"]
    assert style_motion_policy_from_dict(current).camera_easing == "ease_out"
    # nothing to override -> the registered preset as is
    assert style_motion_policy_from_dict({"key": "pain_punch"}) == _p("pain_punch")


def test_old_manifest_policy_entries_still_load_with_their_old_numbers():
    """Presets baked into old clips stay as they were: a pre-M5 entry carries
    its own numbers, which override the new registered preset."""
    legacy = LEGACY["flash_deal"]
    entry = {"key": "flash_deal", **{f: getattr(legacy, f) for f in _LEGACY_FIELDS}}
    loaded = style_motion_policy_from_dict(entry)
    for field in _LEGACY_FIELDS:
        assert getattr(loaded, field) == getattr(legacy, field), field
    assert loaded.camera_easing == DEFAULT_CAMERA_EASING


# -- plan level: the planner really produces different clips per preset -----


@pytest.mark.parametrize("key", sorted(STYLE_MOTION_POLICIES))
def test_planner_honours_each_presets_own_hook_and_static_bounds(key):
    from tests.test_pacing_curve import _max_static_run, _shots
    from tests.test_shot_matching_cut_quality import _context, _cue, _run

    cues = [_cue(0.0, 2.0, "a"), _cue(2.0, 5.1, "b ครับ"), _cue(5.1, 8.2, "c ครับ"),
            _cue(8.2, 11.3, "d ครับ"), _cue(11.3, 14.4, "e ครับ")]
    ctx = _context(cues, 14.4)
    ctx.style_preset = key
    clips = _run(ctx)
    policy = _p(key)
    assert sum(c["duration"] for c in clips) == pytest.approx(14.4, abs=0.01)
    for start, end in _shots(clips):
        if start < policy.hook_window_sec - 1e-6:
            assert end - start <= policy.hook_max_shot + 1e-6, (key, start, end)
    assert _max_static_run(clips) <= policy.max_static_sec + 1 / 30
    assert all(c["duration"] <= policy.max_shot * 1.25 + 1e-6 for c in clips if not c.get("hold_reason")), key


def test_planner_output_differs_between_presets():
    """Same script and footage: the ten plans are not interchangeable."""
    from tests.test_shot_matching_cut_quality import _context, _cue, _run

    cues = [_cue(2.0 * i, 2.0 * (i + 1), "cue ครับ") for i in range(8)]
    signatures = {}
    for key in STYLE_MOTION_POLICIES:
        ctx = _context(cues, 16.0)
        ctx.style_preset = key
        clips = _run(ctx)
        signatures[key] = (
            tuple(round(c["duration"], 2) for c in clips),
            tuple(c.get("transition_in") for c in clips),
            tuple(bool(c.get("keyframes")) for c in clips),
            tuple(round(float(c.get("keyframes", [{}])[-1].get("zoom", 0)), 2) if c.get("keyframes") else 0 for c in clips),
        )
    assert len(set(signatures.values())) == 10, {
        sig: [k for k, v in signatures.items() if v == sig] for sig in set(signatures.values())
        if list(signatures.values()).count(sig) > 1
    }
