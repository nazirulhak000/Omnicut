"""Behavioral tests for the isolated normalized-motion -> ASS adapter."""

import re

import pytest

from scripts.subtitle.motion_ass_adapter import (
    UnsupportedMotionPropertyError,
    build_ass_motion_segments,
)
from scripts.subtitle.motion_contract import MOTION_CONTRACT_VERSION, sample_track


def motion_contract(*, phase="in", duration_ms=100, tracks=None, repeat=False):
    return {
        "version": MOTION_CONTRACT_VERSION,
        "id": f"test.{phase}",
        "role": "text",
        "phase": phase,
        "duration_ms": duration_ms,
        "repeat": repeat,
        "tracks": tracks or {},
    }


def track(name, values, *, unit="ratio", **extra):
    return {
        name: {
            "unit": unit,
            "keyframes": [
                {"t": time, "value": value, "easing": easing}
                for time, value, easing in values
            ],
            **extra,
        }
    }


def test_supported_tracks_emit_deterministic_ass_initial_tags_and_segments():
    contract = motion_contract(
        tracks={
            **track("scale", [(0, 0.5, "linear"), (1, 1, "ease_out")]),
            **track("alpha", [(0, 0, "linear"), (1, 1, "linear")], unit="opacity"),
            **track("rotation", [(0, -3, "linear"), (1, 0, "linear")], unit="degrees"),
            **track("blur", [(0, 12, "linear"), (1, 0, "linear")], unit="canvas_px"),
        }
    )

    plan = build_ass_motion_segments(contract, start_ms=10, end_ms=110)

    assert plan.to_dict() == {
        "contract_id": "test.in",
        "phase": "in",
        "window_ms": {"start": 10, "end": 110},
        "initial_tags": r"\fscx50\fscy50\alpha&HFF&\frz-3\blur12",
        "segments": [
            {
                "track": "scale",
                "start_ms": 10,
                "end_ms": 110,
                "from_value": 0.5,
                "to_value": 1.0,
                "easing": "ease_out",
                # ease_out is t*(2-t) in the contract, which no single ASS accel can
                # express, so it is baked into 8 linear \t steps sampled from the contract.
                "ass_tags": (
                    r"\t(10,22,\fscx61\fscy61)\t(22,35,\fscx72\fscy72)"
                    r"\t(35,48,\fscx81\fscy81)\t(48,60,\fscx88\fscy88)"
                    r"\t(60,72,\fscx93\fscy93)\t(72,85,\fscx97\fscy97)"
                    r"\t(85,98,\fscx99\fscy99)\t(98,110,\fscx100\fscy100)"
                ),
            },
            {
                "track": "alpha",
                "start_ms": 10,
                "end_ms": 110,
                "from_value": 0.0,
                "to_value": 1.0,
                "easing": "linear",
                "ass_tags": r"\t(10,110,\alpha&H00&)",
            },
            {
                "track": "rotation",
                "start_ms": 10,
                "end_ms": 110,
                "from_value": -3.0,
                "to_value": 0.0,
                "easing": "linear",
                "ass_tags": r"\t(10,110,\frz0)",
            },
            {
                "track": "blur",
                "start_ms": 10,
                "end_ms": 110,
                "from_value": 12.0,
                "to_value": 0.0,
                "easing": "linear",
                "ass_tags": r"\t(10,110,\blur0)",
            },
        ],
        "unsupported": [],
    }


def test_timing_is_integer_clamped_and_zero_length_windows_are_safe():
    contract = motion_contract(
        tracks=track("alpha", [(0, 0, "linear"), (0.5, 0.5, "linear"), (1, 1, "linear")], unit="opacity")
    )

    plan = build_ass_motion_segments(contract, start_ms=-25, end_ms=25.9)

    assert plan.window_ms == {"start": 0, "end": 26}
    assert [(segment.start_ms, segment.end_ms) for segment in plan.segments] == [(0, 13), (13, 26)]

    empty = build_ass_motion_segments(contract, start_ms=50, end_ms=10)
    assert empty.window_ms == {"start": 50, "end": 50}
    assert empty.segments == ()


def test_loop_tracks_repeat_until_window_end_without_escaping_the_window():
    contract = motion_contract(
        phase="loop",
        duration_ms=100,
        repeat=True,
        tracks=track(
            "rotation",
            [(0, 0, "linear"), (0.5, -3, "linear"), (1, 0, "linear")],
            unit="degrees",
            repeat=True,
            cycle_duration_ms=100,
        ),
    )

    plan = build_ass_motion_segments(contract, start_ms=100, end_ms=350)

    assert [(segment.start_ms, segment.end_ms) for segment in plan.segments] == [
        (100, 150),
        (150, 200),
        (200, 250),
        (250, 300),
        (300, 350),
    ]
    assert all(100 <= segment.start_ms < segment.end_ms <= 350 for segment in plan.segments)


def test_dy_uses_base_position_and_reports_reveal_without_geometry_context():
    contract = motion_contract(
        tracks={
            **track("dy", [(0, 60, "linear"), (1, 0, "ease_out")], unit="canvas_px"),
            **track("reveal", [(0, 0, "linear"), (1, 1, "linear")], unit="ratio"),
        }
    )

    plan = build_ass_motion_segments(contract, base_position=(270, 480))

    assert plan.initial_tags == r"\pos(270,540)"
    assert plan.segments[0].ass_tags == r"\move(270,540,270,480,0,100)"
    assert plan.unsupported == (
        {
            "track": "reveal",
            "reason": "ASS reveal needs text geometry or a clip rectangle; the normalized contract has no glyph bounds.",
        },
    )


def test_canvas_pixel_tracks_scale_to_export_resolution_and_power_easing_is_preserved():
    contract = motion_contract(
        tracks={
            **track("dy", [(0, 60, "linear"), (1, 0, {"name": "power", "exponent": 0.6})], unit="canvas_px"),
            **track("blur", [(0, 12, "linear"), (1, 0, {"name": "power", "exponent": 2.2})], unit="canvas_px"),
        }
    )

    plan = build_ass_motion_segments(
        contract,
        base_position=(540, 960),
        canvas_px_scale=2,
    )

    assert plan.initial_tags == r"\pos(540,1080)\blur24"
    assert plan.segments[0].ass_tags == r"\move(540,1080,540,960,0,100)"
    assert plan.segments[1].ass_tags == r"\t(0,100,2.2,\blur0)"


def test_position_is_reported_or_can_fail_explicitly_without_silent_fallback():
    contract = motion_contract(
        tracks={
            "position": {
                "unit": "canvas_px",
                "keyframes": [
                    {"t": 0, "value": {"x": 0, "y": 10}},
                    {"t": 1, "value": {"x": 0, "y": 0}},
                ],
            }
        }
    )

    plan = build_ass_motion_segments(contract)
    assert plan.segments == ()
    assert plan.unsupported[0]["track"] == "position"

    with pytest.raises(UnsupportedMotionPropertyError, match="position"):
        build_ass_motion_segments(contract, unsupported="error")


def test_out_phase_keeps_requested_window_and_legacy_alpha_direction():
    contract = motion_contract(
        phase="out",
        duration_ms=150,
        tracks=track("alpha", [(0, 1, "linear"), (1, 0, "linear")], unit="opacity"),
    )

    plan = build_ass_motion_segments(contract, start_ms=850, end_ms=1000)

    assert plan.initial_tags == r"\alpha&H00&"
    assert plan.segments[0].ass_tags == r"\t(850,1000,\alpha&HFF&)"


# ---------------------------------------------------------------------------
# B3 (EDITOR-CUT-QUALITY-R1): easing must follow the motion contract, not an
# ASS accel that merely resembles it
# ---------------------------------------------------------------------------

_TRANSITION = re.compile(r"\\t\((\d+),(\d+),(?:([\d.]+),)?\\fscx(\d+)\\fscy\d+\)")


def _scale_track(easing, start=0.5, end=1.0):
    return track("scale", [(0, start, "linear"), (1, end, easing)])


def _parsed(ass_tags):
    return [
        (int(a), int(b), float(acc) if acc else None, int(scale))
        for a, b, acc, scale in _TRANSITION.findall(ass_tags)
    ]


def _plan_scale(easing, *, start_ms=10, end_ms=110):
    contract = motion_contract(tracks=_scale_track(easing))
    plan = build_ass_motion_segments(contract, start_ms=start_ms, end_ms=end_ms)
    assert len(plan.segments) == 1
    return contract, plan


def _rendered_scale_at(plan, time_ms):
    """What a renderer shows at `time_ms`: linear between the baked transition endpoints."""
    start = plan.window_ms["start"]
    points = [(start, float(re.search(r"\\fscx(\d+)", plan.initial_tags).group(1)))]
    points += [(end, float(scale)) for _, end, _, scale in _parsed(plan.segments[0].ass_tags)]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if time_ms <= t1:
            return v0 + (v1 - v0) * (time_ms - t0) / (t1 - t0)
    return points[-1][1]


@pytest.mark.parametrize(
    "easing, tolerance",
    [
        ("ease_out", 1.0),
        ("ease_in_out", 1.5),
        ("sine_in_out", 1.5),
        ({"name": "spring"}, 3.0),
        ({"name": "spring", "stiffness": 400, "damping": 14}, 6.0),
    ],
)
def test_baked_easings_track_the_contract_curve_at_every_millisecond(easing, tolerance):
    contract, plan = _plan_scale(easing)
    tags = plan.segments[0].ass_tags
    window = plan.window_ms

    steps = _parsed(tags)
    assert len(steps) >= 8, "no single accel can express this easing, it must be baked"
    # contiguous, strictly increasing, inside the window, landing on the keyframe value
    assert steps[0][0] == window["start"] and steps[-1][1] == window["end"]
    assert all(a < b for a, b, _, _ in steps)
    assert all(prev[1] == nxt[0] for prev, nxt in zip(steps, steps[1:]))
    assert steps[-1][3] == 100
    assert all(acc is None for _, _, acc, _ in steps)

    span = window["end"] - window["start"]
    for ms in range(window["start"], window["end"] + 1):
        expected = sample_track("scale", contract["tracks"]["scale"], (ms - window["start"]) / span) * 100
        # sample_track returns the raw keyframe at the very end; spring(1) would overshoot
        if ms == window["end"]:
            expected = 100
        assert abs(_rendered_scale_at(plan, ms) - expected) <= tolerance, (easing, ms)


def test_ease_out_is_not_the_old_sqrt_accel_and_matches_t_times_two_minus_t():
    _, plan = _plan_scale("ease_out", start_ms=0, end_ms=100)
    tags = plan.segments[0].ass_tags

    assert ",0.5," not in tags
    # Quarter point: t*(2-t) = 0.4375 -> 0.5 + 0.5 * 0.4375 = 71.875%; the old
    # sqrt accel would have shown 75% there.
    assert _rendered_scale_at(plan, 25) == pytest.approx(71.875, abs=1.0)
    assert abs(_rendered_scale_at(plan, 25) - 75.0) > 2.0
    # ease_out starts fast and finishes slow
    first_move = _rendered_scale_at(plan, 10) - _rendered_scale_at(plan, 0)
    last_move = _rendered_scale_at(plan, 100) - _rendered_scale_at(plan, 90)
    assert first_move > 2 * last_move


def test_ease_in_keeps_its_exact_single_accel_and_linear_stays_plain():
    _, ease_in = _plan_scale("ease_in", start_ms=0, end_ms=100)
    assert ease_in.segments[0].ass_tags == r"\t(0,100,2,\fscx100\fscy100)"

    _, linear = _plan_scale("linear", start_ms=0, end_ms=100)
    assert linear.segments[0].ass_tags == r"\t(0,100,\fscx100\fscy100)"


def test_step_easing_holds_then_jumps_instead_of_pretending_to_be_linear():
    _, plan = _plan_scale("step", start_ms=0, end_ms=100)
    assert plan.segments[0].ass_tags == r"\t(99,100,\fscx100\fscy100)"


@pytest.mark.parametrize("window_ms", [1, 2, 3, 5])
def test_baked_easing_in_tiny_windows_never_emits_empty_or_duplicate_steps(window_ms):
    _, plan = _plan_scale("ease_out", start_ms=40, end_ms=40 + window_ms)
    steps = _parsed(plan.segments[0].ass_tags)
    assert steps and all(a < b for a, b, _, _ in steps)
    assert steps[0][0] == 40 and steps[-1][1] == 40 + window_ms and steps[-1][3] == 100


def test_baked_easing_applies_to_other_tracks_and_the_partial_loop_cycle():
    contract = motion_contract(
        phase="loop",
        duration_ms=100,
        repeat=True,
        tracks=track(
            "rotation",
            [(0, 0, "linear"), (1, -10, "ease_out")],
            unit="degrees",
            repeat=True,
            cycle_duration_ms=100,
        ),
    )

    plan = build_ass_motion_segments(contract, start_ms=0, end_ms=150)

    # one full cycle + one 50 ms partial cycle, both baked (no accel), all inside the window
    assert [(s.start_ms, s.end_ms) for s in plan.segments] == [(0, 100), (100, 150)]
    for segment in plan.segments:
        assert segment.ass_tags.count(r"\t(") >= 8
        windows = [(int(a), int(b)) for a, b in re.findall(r"\\t\((\d+),(\d+),\\frz", segment.ass_tags)]
        assert windows[0][0] == segment.start_ms and windows[-1][1] == segment.end_ms
        assert all(a < b for a, b in windows)
    # full cycle: quarter-way (t=0.25) is -4.375 degrees by t*(2-t); sqrt would be -5
    quarter = re.findall(r"\\t\(\d+,(\d+),\\frz(-?[\d.]+)\)", plan.segments[0].ass_tags)
    assert dict((int(t), float(v)) for t, v in quarter)[25] == pytest.approx(-4.375, abs=0.01)
