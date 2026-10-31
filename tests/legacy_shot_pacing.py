"""Shared helpers for shot-planner contract suites written before M2.

Those suites pin the BODY planner (J-lead cut times, beat/voice/motion snap,
Strict Topic Hold, source-window continuity) with tiny fixtures whose first
shot always sits inside the 3 s hook window. The M2 pacing curve (hook split)
and interrupt guard (camera punch) are separate passes on top of that plan and
are covered by tests/test_pacing_curve.py, so these suites switch only those
two passes off. Q2 caps and the M6 still-frame rules stay ON for them.
"""

from dataclasses import replace
from unittest.mock import patch

import pytest

STAGE = "scripts.stages.shot_matching_stage"


def _without_pacing_curve(real):
    def resolve(style_preset):
        return replace(real(style_preset), hook_max_shot=0.0, max_static_sec=0.0)

    return resolve


def pacing_curve_disabled():
    """Context manager form, for module-scoped fixtures and helpers."""
    from scripts.stages import shot_matching_stage as stage

    return patch(f"{STAGE}.resolve_style_motion_policy", side_effect=_without_pacing_curve(stage.resolve_style_motion_policy))


@pytest.fixture
def legacy_body_pacing():
    with pacing_curve_disabled():
        yield
