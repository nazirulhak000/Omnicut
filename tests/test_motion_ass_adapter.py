"""Behavioral tests for the isolated normalized-motion -> ASS adapter."""

import pytest

from scripts.subtitle.motion_ass_adapter import (
    UnsupportedMotionPropertyError,
    build_ass_motion_segments,
)
from scripts.subtitle.motion_contract import MOTION_CONTRACT_VERSION


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
                "ass_tags": r"\t(10,110,0.5,\fscx100\fscy100)",
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
