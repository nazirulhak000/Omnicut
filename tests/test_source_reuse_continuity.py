"""Offline contracts for consumed scene footage; no production assets touched."""
import pytest

from scripts.gemini_vision_matcher import GeminiVisionMatcher
from tests.test_shot_matching_cut_quality import _context, _run
from scripts.shot_source_window import SourceWindowLedger


def _match(cue_id, start=2, end=7, scene_id=1, zoom=1.15):
    return {"cue_ids": [cue_id], "scene_id": scene_id, "scene_start": start,
            "scene_end": end, "start_time": start, "end_time": end, "punch_zoom": zoom}


@pytest.mark.parametrize("sweet_spot", [False, True])
def test_catalog_reuses_unequal_duration_groups_without_rewinding(sweet_spot):
    cues = [{"start": a, "end": b, "text": "USB-C ครับ"}
            for a, b in [(0, 3), (3, 5), (5, 9), (9, 12)]]
    matches = GeminiVisionMatcher.match_script_with_catalog(
        {"scenes": [{"id": 1, "start": 2, "end": 10, "keywords": ["USB-C"],
                     "action_type": "port_connection"}]}, cues, 12, sweet_spot)
    assert len(matches) == 4
    for previous, current in zip(matches, matches[1:]):
        consumed = min(10, previous["start_time"] + cues[previous["cue_ids"][0] - 1]["end"]
                       - cues[previous["cue_ids"][0] - 1]["start"])
        assert current.get("consumed_source_until", current["start_time"]) >= consumed - 1e-6


def test_stage_distinct_matches_of_same_scene_continue_then_hold_and_warn():
    cues = [{"start": i * 2, "end": (i + 1) * 2, "text": "USB-C ครับ"} for i in range(4)]
    ctx = _context(cues, 8, use_ai_vision=True)
    messages = []
    ctx.notify = lambda message, *args: messages.append(message)
    clips = _run(ctx, raw_duration=12, ai_shots=[_match(i + 1) for i in range(4)])
    assert len(clips) == 4
    assert clips[0]["trim_start"] == 2
    for previous, current in zip(clips[:2], clips[1:3]):
        # Final picture spans include the voice-leading cut adjustment.
        assert current["trim_start"] == pytest.approx(previous["trim_end"], abs=1e-6)
    assert clips[2]["trim_end"] == 7
    assert clips[2]["freeze_tail"] > 0
    assert clips[3]["held_source_time"] < 7
    assert clips[3]["footage_shortage"]["reason"] == "source_window_exhausted"
    assert any("ค้างภาพสุดท้าย" in message for message in messages)


def test_revisited_exhausted_topic_retains_its_own_camera_pose():
    cues = [{"start": i * 2, "end": (i + 1) * 2, "text": f"feature {i} ครับ"} for i in range(3)]
    clips = _run(_context(cues, 6, use_ai_vision=True), raw_duration=20,
                 ai_shots=[_match(1, 2, 3, zoom=1.1), _match(2, 10, 15, 2, 1.35), _match(3, 2, 3)])
    assert clips[1]["trim_start"] == 10
    assert clips[2]["trim_start"] == pytest.approx(3 - 1 / 30, abs=1e-6)
    assert clips[2]["zoom"] == clips[0]["zoom"]
    assert clips[2]["keyframes"] == [{**clips[0]["keyframes"][-1], "time": 0}]


def test_actual_played_span_wins_over_catalog_hint_and_timeline_gap():
    ledger = SourceWindowLedger()
    first = ledger.allocate(_match(1), 12, 2, .7)
    later = {**_match(2), "start_time": 5, "consumed_source_until": 5}
    next_span = ledger.allocate(later, 12, 9, .3)
    assert next_span["raw_offset"] == pytest.approx(first["source_end"], abs=1e-6)
    assert next_span["source_end"] == pytest.approx(3)


def test_same_scene_id_on_different_source_or_semantic_window_is_independent():
    ledger = SourceWindowLedger()
    ledger.allocate({**_match(1), "source_path": "a.mp4"}, 12, 2, 2)
    other_source = ledger.allocate({**_match(2), "source_path": "b.mp4"}, 12, 2, 2)
    other_window = ledger.allocate({**_match(3, 8, 10), "source_path": "a.mp4"}, 12, 8, 1)
    assert other_source["raw_offset"] == 2
    assert other_window["raw_offset"] == 8


@pytest.mark.render_regression
@pytest.mark.parametrize("revisit", [False, True])
def test_real_frames_continue_and_held_pose_matches_production_preview(tmp_path, monkeypatch, revisit):
    import json
    import shutil
    from pathlib import Path
    from tempfile import TemporaryDirectory
    import numpy as np
    from scripts.video_editor import VideoEditor
    from tests.test_real_render_cut_alignment import (
        _run as command, _write_index_coded_source, _write_empty_ass, _write_voice,
        _plan_shots, _decoded_indices, _gray_frames, ROOT,
    )
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/FFprobe unavailable")
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    with TemporaryDirectory(dir=tmp_path) as directory:
        root = Path(directory)
        raw, ass, voice, out = [root / name for name in ("raw.mp4", "empty.ass", "voice.wav", "out.mp4")]
        _write_index_coded_source(raw, n_frames=180, pattern=True)
        _write_empty_ass(ass)
        _write_voice(voice, [0, .8, 1.6], 2.4)
        cues = [{"start": i * .8, "end": (i + 1) * .8, "text": f"feature {i}"} for i in range(3)]
        matches = ([_match(1, 2, 2.5, zoom=1.1), _match(2, 4, 5, 2, 1.35), _match(3, 2, 2.5)]
                   if revisit else [_match(i + 1, 2, 3.6) for i in range(3)])
        clips = _plan_shots(raw, cues, 2.4, ai_shots=matches)
        clips = [{**clip, "transition_in": "cut"} for clip in clips]
        for clip in clips:
            clip.pop("transition_duration", None)
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(raw)], total_duration=2.4, mixed_audio_path=str(voice),
            ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
            transitions=["cut", "cut"], export_preset="draft",
        )
        indices = _decoded_indices(out)
        assert len(indices) == 72
        preview = command(["node", "--input-type=module", "-e", """
            import {buildSegments, getDrawPlan} from './frontend/src/lib/timelineMath.js';
            let input = ''; for await (const data of process.stdin) input += data;
            const segments = buildSegments(JSON.parse(input));
            console.log(JSON.stringify(Array.from({length:72}, (_,k) =>
                Math.round(getDrawPlan(segments, k/30 + 1e-6)[0].localTime * 30))));
        """], input=json.dumps(clips), text=True, cwd=ROOT)
        expected = json.loads(preview.stdout)
        assert max(abs(a - b) for a, b in zip(indices, expected)) <= 1
        if revisit:
            assert set(indices[-12:]) == {74}
            assert 120 in indices, "distinct topic must remain visible"
            gray = _gray_frames(out)
            assert np.abs(gray[-12:] - gray[18]).mean() < 1.0, "revisit must retain its own held camera pose"
        else:
            assert indices[:48] == list(range(60, 108)), "no reused frames before exhaustion"
            assert set(indices[48:]) == {107}
    assert not list(tmp_path.rglob("*.mp4")), "cleanup must remove all synthetic media"
