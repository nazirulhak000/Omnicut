"""Metadata-only audit contracts. All file fixtures are synthetic temp JSON."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.editorial_plan_audit import audit_file, audit_manifest


def _clip(start=0, end=2, **fields):
    return {"source_path": "missing-test-source.mp4", "trim_start": start,
            "trim_end": end, "speed": 1, **fields}


def test_disjoint_same_source_is_not_replay_and_audit_does_not_mutate(monkeypatch):
    from scripts.video_editor import VideoEditor
    monkeypatch.setattr(VideoEditor, "get_media_info", lambda *args: pytest.fail("must not probe media"))
    manifest = {"clip_list": [_clip(), _clip(4, 6)], "total_duration": 4,
                "cues": [{"start": .5, "end": 3.5, "text": "test"}]}
    original = copy.deepcopy(manifest)
    report = audit_manifest(manifest)
    assert manifest == original
    assert report["summary"]["source_count"] == 1
    assert report["reuses"] == []
    assert report["cue_coverage"][0]["uncovered"] == []
    assert "sentence_boundaries_not_explicit" in report["unknowns"]
    assert report["summary"]["uncovered_sentence_count"] is None
    assert "visual_topic_accuracy" in report["unknowns"]


@pytest.mark.parametrize("fields,classification", [
    ({}, "unmarked_replay_risk"), ({"manual_pinned": True}, "manual_reuse_review"),
    ({"allow_source_reuse": True}, "intentional_reuse"),
])
def test_replay_distinguishes_manual_and_explicit_intent(fields, classification):
    report = audit_manifest({"clip_list": [_clip(), _clip(1, 3, **fields)]})
    assert report["reuses"][0]["classification"] == classification
    assert report["summary"]["reused_source_seconds"] == 1


def test_repeat_union_does_not_double_count_previous_duplicate_spans():
    report = audit_manifest({"clip_list": [_clip(), _clip(), _clip()]})
    assert report["summary"]["reused_source_seconds"] == 4
    assert report["reuses"][1]["source_seconds"] == 2


def test_exhausted_held_frame_is_not_counted_as_moving_replay():
    report = audit_manifest({"clip_list": [_clip(), _clip(2 - 1 / 30, 2,
        freeze_tail=2 - 1 / 30, held_source_time=2 - .75 / 30,
        source_window={"start": 0, "end": 2},
        footage_shortage={"reason": "source_window_exhausted", "missing_seconds": 2 - 1 / 30})]})
    assert report["reuses"] == []
    assert report["summary"]["hold_count"] == 1
    assert report["summary"]["declared_shortage_count"] == 1
    assert report["holds"][0]["classification"] == "exhaustion_hold_as_declared"


def test_transition_head_tail_handle_is_not_harmful_replay_but_middle_rewind_is():
    handle = audit_manifest({"clip_list": [_clip(), _clip(1.8, 3.8)],
                             "transitions": [{"type": "fade", "duration": .2}]})
    assert handle["reuses"][0]["classification"] == "transition_handle_overlap"
    assert handle["summary"]["replay_risk_count"] == 0
    assert handle["planned_timeline_end"] == pytest.approx(3.8)
    rewind = audit_manifest({"clip_list": [_clip(), _clip(.5, 2.5)],
                             "transitions": [{"type": "fade", "duration": .2}]})
    assert rewind["reuses"][0]["classification"] == "unmarked_replay_risk"


def test_explicit_sentence_timing_can_show_uncovered_time_but_cues_are_not_sentences():
    report = audit_manifest({"clip_list": [_clip()], "total_duration": 4,
        "cues": [{"start": 1, "end": 3}], "sentences": [{"id": "s1", "start": 1, "end": 3}]})
    assert report["timeline_gaps"] == [[2, 4]]
    assert report["cue_coverage"][0]["uncovered"] == [[2, 3]]
    assert report["sentence_coverage"][0]["uncovered"] == [[2, 3]]
    assert report["summary"]["uncovered_sentence_count"] == 1
    assert "sentence_boundaries_not_explicit" not in report["unknowns"]


def test_subframe_output_rounding_and_total_duration_crop_are_accounted():
    report = audit_manifest({"clip_list": [_clip(0, 2)], "total_duration": 2.004,
                             "cues": [{"start": 1, "end": 2.004}]})
    assert report["timeline_gaps"] == []
    assert report["cue_coverage"][0]["uncovered"] == []
    cropped = audit_manifest({"clip_list": [_clip(0, 4)], "total_duration": 2,
                               "cues": [{"start": 3, "end": 4}]})
    assert cropped["cue_coverage"][0]["uncovered"] == [[3, 4]]


def test_missing_timing_and_multitrack_are_unknown_not_false_gaps():
    invalid = audit_manifest({"clip_list": [_clip(), {"source_path": "b.mp4", "trim_start": 2}],
                               "total_duration": 10})
    assert invalid["timeline_gaps"] is None
    assert invalid["summary"]["uncovered_cue_count"] is None
    multi = audit_manifest({"clip_list": [_clip(track_id="video-1"), _clip(track_id="video-2")]})
    assert multi["planned_timeline_end"] is None
    assert "multitrack_or_explicit_timeline_layout" in multi["unknowns"]


def test_window_violation_and_invalid_held_frame_are_metadata_facts():
    report = audit_manifest({"clip_list": [_clip(1, 3, source_window={"start": 2, "end": 3},
        freeze_tail=1, held_source_time=4)]})
    kinds = {item["kind"] for item in report["issues"]}
    assert {"semantic_window_bounds_violation", "held_frame_outside_trim"} <= kinds


def test_speed_controls_played_time_not_saved_duration():
    report = audit_manifest({"clip_list": [_clip(0, 2, speed=2, duration=99)]})
    assert report["planned_timeline_end"] == 1
    assert report["issues"][0]["kind"] == "saved_duration_differs_from_trim_speed"


@pytest.mark.parametrize("speed,expected", [(.1, 8), (8, .5)])
def test_render_speed_clamp_is_reported_and_applied(speed, expected):
    report = audit_manifest({"clip_list": [_clip(speed=speed)]})
    assert report["planned_timeline_end"] == expected
    assert report["issues"][0]["kind"] == "speed_clamped_by_renderer"


def test_numeric_string_hold_is_unrecognized_and_does_not_hide_source_replay():
    report = audit_manifest({"clip_list": [_clip(), _clip(2 - 1 / 30, 2, freeze_tail=1,
        held_source_time="1.975", source_window={"start": 0, "end": 2})]})
    assert report["reuses"][0]["classification"] == "unmarked_replay_risk"
    assert any(item["kind"] == "unrecognized_held_source_time" for item in report["issues"])


def test_source_span_minimum_uses_renderer_bounded_window_rule():
    bounded = audit_manifest({"clip_list": [_clip(0, .1, speed=2, source_window={"start": 0, "end": 1})]})
    assert bounded["clips"][0]["played_duration"] == pytest.approx(.05)
    legacy = audit_manifest({"clip_list": [_clip(0, .1, speed=2)]})
    assert legacy["clips"][0]["played_duration"] == .2
    assert any(item["kind"] == "source_span_expanded_by_renderer" for item in legacy["issues"])


def test_file_reader_bounded_hashed_and_cli_has_no_write_side_effect(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    path = tmp_path / "project.json"
    content = json.dumps({"project_name": "ทดสอบ", "clip_list": [_clip()]}, ensure_ascii=False).encode("utf-8")
    path.write_bytes(content)
    with pytest.raises(ValueError, match="byte limit"):
        audit_file(path, max_bytes=1)
    report = audit_file(path)
    assert report["manifest_sha256"] == hashlib.sha256(content).hexdigest()
    assert report["manifest_bytes"] == len(content)
    command = subprocess.run([sys.executable, "tools/editorial_plan_audit.py", str(path)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding="utf-8", check=True)
    assert json.loads(command.stdout)["project_name"] == "ทดสอบ"
    assert path.read_bytes() == content
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("field", ["clip_list", "cues", "sentences"])
def test_unbounded_metadata_lists_are_rejected(monkeypatch, field):
    monkeypatch.setattr("tools.editorial_plan_audit.MAX_ITEMS", 1)
    with pytest.raises(ValueError, match="exceeds"):
        audit_manifest({field: [{}, {}]})
