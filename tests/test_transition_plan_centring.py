"""Transition plan built by VideoAssemblyStage (round EDITOR-CUT-QUALITY-R2, A7c/A7d).

Plan-building helpers only -- VideoAssemblyStage.run is never called here (it
writes exports). Offline and deterministic.
"""

import pytest

from scripts.stages.video_assembly_stage import (
    _centre_transition_overlaps,
    _fill_undecided_transitions,
)


def _clips(n=4, dur=2.0):
    return [
        {"id": f"c{i}", "trim_start": 10.0 * i + 1.0, "trim_end": 10.0 * i + 1.0 + dur,
         "duration": dur, "speed": 1.0, "zoom": 1.0}
        for i in range(n)
    ]


def _starts(clips):
    """Timeline start of every clip the way VideoEditor/preview chain them:
    the incoming clip starts ``transition_duration`` before the outgoing ends."""
    acc, starts = 0.0, []
    for i, c in enumerate(clips):
        overlap = float(c.get("transition_duration") or 0.0) if i and c.get("transition_in", "cut") != "cut" else 0.0
        start = acc - overlap if i else 0.0
        starts.append(start)
        acc = start + float(c["duration"])
    return starts, acc


def test_transition_is_centred_on_the_planned_cut_and_total_is_kept():
    clips = _clips()
    planned_cuts = [2.0, 4.0, 6.0]
    transitions = [{"type": "wipeleft", "duration": 0.35}, {"type": "cut", "duration": 0.0},
                   {"type": "dissolve", "duration": 0.25}]
    for c, t in zip(clips[1:], transitions):
        c["transition_in"], c["transition_duration"] = t["type"], t["duration"]
    _centre_transition_overlaps(clips, transitions)
    starts, end = _starts(clips)
    assert end == pytest.approx(8.0, abs=1e-3)  # total length unchanged
    # transition i runs [start of incoming, start + d]: its midpoint is the cut
    assert starts[1] + 0.35 / 2 == pytest.approx(planned_cuts[0], abs=1e-3)
    assert starts[2] == pytest.approx(planned_cuts[1], abs=1e-3)  # hard cut untouched
    assert starts[3] + 0.25 / 2 == pytest.approx(planned_cuts[2], abs=1e-3)
    # the incoming clip shows the planned source frame at the cut instant
    assert clips[1]["trim_start"] == pytest.approx(11.0 - 0.175, abs=1e-3)
    assert clips[1]["trim_start"] + (planned_cuts[0] - starts[1]) == pytest.approx(11.0, abs=1e-3)
    # applied once: a second pass changes nothing
    snapshot = [dict(c) for c in clips]
    _centre_transition_overlaps(clips, transitions)
    assert clips == snapshot


def test_centring_without_source_handle_moves_the_rest_to_the_tail():
    clips = _clips(2)
    clips[1]["trim_start"], clips[1]["trim_end"] = 0.05, 2.05
    clips[1]["transition_in"], clips[1]["transition_duration"] = "fade", 0.3
    _centre_transition_overlaps(clips, [{"type": "fade", "duration": 0.3}])
    assert clips[1]["trim_start"] == 0.0
    assert clips[1]["duration"] == pytest.approx(2.15)
    assert clips[1]["trim_end"] == pytest.approx(2.15)  # 0.10 s more at the tail
    _, end = _starts(clips)
    assert end == pytest.approx(4.0, abs=1e-3)


def test_all_cut_list_is_filled_through_the_style_budget():
    # clean_tech_review: one movement transition every 5 boundaries
    picks = _fill_undecided_transitions(_clips(7), "clean_tech_review")
    assert [p["type"] for p in picks][:4] == ["cut"] * 4
    assert picks[4]["type"] != "cut"
    # 4 clips = 3 boundaries: the style keeps them all hard cuts (was 3 wipes)
    assert all(p["type"] == "cut" for p in _fill_undecided_transitions(_clips(4), "clean_tech_review"))


def test_filled_slides_follow_the_outgoing_pan():
    clips = _clips(4)
    clips[1]["keyframes"] = [{"time": 0.0, "pan_x": 0.2}, {"time": 2.0, "pan_x": -0.2}]  # camera left
    picks = _fill_undecided_transitions(clips, "viral_punch")
    assert picks[1]["type"] == "slideright"
