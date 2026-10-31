"""M2 pacing curve (hook window) + interrupt guard for the auto shot planner.

Offline and deterministic: every analyser is mocked; no files are written.
"""

import pytest

from scripts.stages.shot_matching_stage import (
    CAMERA_PUNCH_DELTA,
    CAMERA_PUNCH_SEC,
    _apply_interrupt_guard,
    _plan_split_points,
)
from scripts.style_motion_policy import (
    FAMILY_PACING,
    STYLE_MOTION_POLICIES,
    StyleMotionPolicy,
    resolve_style_motion_policy,
    style_motion_catalog,
    style_motion_policy_from_dict,
)
from scripts.video_editor import dynamic_camera_filter, resolve_clip_transforms
from tests.test_shot_matching_cut_quality import _context, _cue, _cut_times, _run

FPS = 30
FAMILY_STYLES = {
    "energetic": "viral_punch",
    "adaptive": "clean_tech_review",
    "smooth": "smooth_showcase",
    "minimal": "premium_minimal",
}


# ── policy contract ───────────────────────────────────────────────────────

def test_family_values_match_the_roadmap():
    assert FAMILY_PACING == {
        "energetic": (1.0, 2.0),
        "adaptive": (1.3, 2.5),
        "smooth": (1.5, 3.0),
        "minimal": (1.8, 3.5),
    }
    for key, policy in STYLE_MOTION_POLICIES.items():
        assert policy.hook_window_sec == 3.0, key
        assert (policy.hook_max_shot, policy.max_static_sec) == FAMILY_PACING[policy.transition_family], key


def test_catalog_exposes_pacing_fields():
    for key, entry in style_motion_catalog().items():
        policy = resolve_style_motion_policy(key)
        assert entry["hook_window_sec"] == policy.hook_window_sec
        assert entry["hook_max_shot"] == policy.hook_max_shot
        assert entry["max_static_sec"] == policy.max_static_sec


def test_old_serialized_policy_without_pacing_fields_still_loads():
    old_entry = {k: v for k, v in style_motion_catalog()["viral_punch"].items()
                 if k not in ("hook_window_sec", "hook_max_shot", "max_static_sec")}
    old_entry["future_field"] = "ignored"
    policy = style_motion_policy_from_dict(old_entry)
    assert policy == resolve_style_motion_policy("viral_punch")
    assert style_motion_policy_from_dict(None) == resolve_style_motion_policy(None)
    assert style_motion_policy_from_dict({"key": "smooth_showcase", "hook_max_shot": 1.2}).hook_max_shot == 1.2


def test_policy_constructed_without_pacing_fields_derives_them_from_family():
    policy = StyleMotionPolicy(
        key="x", transition_stride=1, stylized_stride=0, max_transition_duration=0.3,
        transition_family="minimal", camera_motion_stride=1, camera_zoom_delta=0.1,
        camera_pan_extent=0.1, camera_min_duration=1.0, accent_color="#FFFFFF",
        status_color="#FFFFFF", neutral_color="#FFFFFF",
    )
    assert (policy.hook_max_shot, policy.max_static_sec) == (1.8, 3.5)


# ── hook window ───────────────────────────────────────────────────────────

def _shots(clips):
    out, t = [], 0.0
    for clip in clips:
        out.append((t, t + clip["duration"]))
        t += clip["duration"]
    return out


@pytest.mark.parametrize("family, style", sorted(FAMILY_STYLES.items()))
def test_no_shot_inside_the_hook_window_exceeds_hook_max(family, style):
    cues = [_cue(2.0 * i, 2.0 * (i + 1), "cue") for i in range(6)]
    ctx = _context(cues, 12.0)
    ctx.style_preset = style
    clips = _run(ctx)
    hook_max = FAMILY_PACING[family][0]
    for start, end in _shots(clips):
        if start < 3.0 - 1e-6:
            assert end - start <= hook_max + 1e-6, (style, start, end)
    assert sum(c["duration"] for c in clips) == pytest.approx(12.0, abs=0.01)


@pytest.mark.parametrize("style", sorted(FAMILY_STYLES.values()))
def test_hook_split_keeps_every_j_led_cue_cut(style):
    """The hook pass only adds cuts; the J-lead cuts stay where they were."""
    cues = [_cue(2.0 * i, 2.0 * (i + 1), "cue") for i in range(4)]
    ctx = _context(cues, 8.0)
    ctx.style_preset = style
    lead = resolve_style_motion_policy(style).j_lead
    cuts = _cut_times(_run(ctx))
    for onset in (2.0, 4.0, 6.0):
        expected = round((onset + min(lead, 0.25)) * FPS) / FPS
        assert any(abs(c - expected) <= 1.5e-3 for c in cuts), (style, onset, cuts)
        assert 0.15 - 2e-3 <= expected - onset <= 0.25 + 2e-3


def test_hook_split_prefers_j_safe_cue_cuts():
    # Short micro cues grouped into one 2.6 s opening shot by the min-shot
    # merge: the hook split must land on their J-led cuts, not mid-word.
    cues = [_cue(0.0, 0.7, "หนึ่ง"), _cue(0.7, 1.4, "สอง"), _cue(1.4, 2.1, "สาม"),
            _cue(2.1, 2.8, "สี่ครับ"), _cue(2.8, 5.0, "ห้า"), _cue(5.0, 7.0, "หก")]
    ctx = _context(cues, 7.0)
    ctx.style_preset = "viral_punch"
    cuts = _cut_times(_run(ctx))
    onsets = [c["start"] for c in cues[1:]]
    for cut in [c for c in cuts if c < 3.0]:
        assert any(0.15 - 2e-3 <= cut - onset <= 0.25 + 2e-3 for onset in onsets), (cut, cuts)


def test_split_planner_falls_back_to_balanced_points_without_candidates():
    points = _plan_split_points(0.0, 2.2, lambda t: 1.0 if t < 3.0 else None)
    assert [round(p, 3) for p, _ in points] == [0.733, 1.467]
    assert all(onset is None for _, onset in points)
    with_candidate = _plan_split_points(0.0, 2.2, lambda t: 1.3, [(0.9, 0.72)])
    assert with_candidate[0] == (0.9, 0.72)


def test_hook_pacing_does_not_touch_shots_after_the_window():
    cues = [_cue(0.0, 3.0, "เปิดครับ"), _cue(3.0, 5.4, "เนื้อหา"), _cue(5.4, 7.8, "ปิดครับ")]
    ctx = _context(cues, 7.8)
    ctx.style_preset = "clean_tech_review"
    shots = _shots(_run(ctx))
    late = [(s, e) for s, e in shots if s >= 3.0]
    assert late and all(e - s > 1.3 for s, e in late)


# ── interrupt guard ───────────────────────────────────────────────────────

def _max_static_run(clips):
    """Longest run of frames with no cut and no camera change (seconds)."""
    longest = 0.0
    for clip in clips:
        frames = int(round(clip["duration"] * FPS))
        run, previous = 0, None
        for f in range(frames):
            values = resolve_clip_transforms(clip, f / FPS, float(clip.get("zoom", 1.0)))
            key = tuple(round(values[k], 5) for k in ("zoom", "pan_x", "pan_y"))
            run = run + 1 if key == previous else 1
            previous = key
            longest = max(longest, run / FPS)
    return longest


def test_static_clip_gets_bounded_camera_punches_in_existing_keyframe_shape():
    clip = {"duration": 5.0, "zoom": 1.2}
    assert _apply_interrupt_guard([clip], 2.0) == 2
    keyframes = clip["keyframes"]
    assert keyframes[0] == {"time": 0.0, "zoom": 1.2, "pan_x": 0.0, "pan_y": 0.0}
    punches = [k for k in keyframes if k.get("easing")]
    assert [k["easing"] for k in punches] == ["ease_out", "ease_out"]
    assert punches[0]["zoom"] == pytest.approx(1.2 + CAMERA_PUNCH_DELTA)
    assert punches[1]["zoom"] == pytest.approx(1.2)  # alternates back out
    for k in punches:
        start = max(p["time"] for p in keyframes if p["time"] < k["time"])
        assert k["time"] - start == pytest.approx(CAMERA_PUNCH_SEC, abs=1e-4)
    assert _max_static_run([clip]) <= 2.0 + 1 / FPS
    assert dynamic_camera_filter(clip, 1.2)  # renderer accepts it


def test_frozen_tail_after_a_camera_move_is_guarded_too():
    clip = {"duration": 6.0, "zoom": 1.1, "keyframes": [
        {"time": 0.0, "zoom": 1.06, "pan_x": -0.1, "pan_y": 0.0},
        {"time": 2.0, "zoom": 1.14, "pan_x": 0.1, "pan_y": 0.0, "easing": "ease_in_out"},
    ]}
    assert _apply_interrupt_guard([clip], 2.5) == 1
    assert clip["keyframes"][:2] == [
        {"time": 0.0, "zoom": 1.06, "pan_x": -0.1, "pan_y": 0.0},
        {"time": 2.0, "zoom": 1.14, "pan_x": 0.1, "pan_y": 0.0, "easing": "ease_in_out"},
    ]
    assert all(k["time"] > 2.0 for k in clip["keyframes"][2:])
    assert _max_static_run([clip]) <= 2.5 + 1 / FPS


def test_short_or_moving_clips_are_left_alone():
    short = {"duration": 1.9, "zoom": 1.0}
    moving = {"duration": 3.0, "zoom": 1.0, "keyframes": [
        {"time": 0.0, "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0},
        {"time": 3.0, "zoom": 1.1, "pan_x": 0.0, "pan_y": 0.0},
    ]}
    before = dict(moving)
    assert _apply_interrupt_guard([short, moving], 2.0) == 0
    assert "keyframes" not in short and moving == before
    assert _apply_interrupt_guard([{"duration": 9.0}], 0) == 0  # disabled


@pytest.mark.parametrize("family, style", sorted(FAMILY_STYLES.items()))
def test_generated_plans_have_no_static_span_longer_than_the_style_allows(family, style):
    cues = [_cue(0.0, 2.0, "a"), _cue(2.0, 5.1, "b ครับ"), _cue(5.1, 8.2, "c ครับ"),
            _cue(8.2, 11.3, "d ครับ"), _cue(11.3, 14.4, "e ครับ")]
    ctx = _context(cues, 14.4)
    ctx.style_preset = style
    clips = _run(ctx)
    assert _max_static_run(clips) <= FAMILY_PACING[family][1] + 1 / FPS
    assert sum(c["duration"] for c in clips) == pytest.approx(14.4, abs=0.01)
