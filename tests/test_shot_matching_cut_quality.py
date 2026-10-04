"""Cut-quality contracts for the auto shot planner (round EDITOR-CUT-QUALITY-R1).

Offline and deterministic: every analyser that would touch real media
(ffprobe, librosa, opencv, Gemini) is patched, and nothing is written outside
pytest's tmp_path.
"""

from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.motion_analyzer import MotionAnalyzer
from scripts.pipeline_context import PipelineContext
from scripts.sfx_manager import SFXManager, bgm_tempo_ratio
from scripts.stages.shot_matching_stage import ShotMatchingStage

STAGE = "scripts.stages.shot_matching_stage"


def _cue(start, end, text):
    return {"start": start, "end": end, "text": text}


def _context(cues, total_duration, *, use_ai_vision=False):
    ctx = PipelineContext(
        product_name="Cut quality test",
        raw_video_path="raw.mp4",
        clip_list=None,
        total_duration=total_duration,
        export_mp4=False,
    )
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = cues
    ctx.micro_cues = cues
    ctx.editorial_pacing = None
    ctx.use_ai_vision = use_ai_vision
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    return ctx


def _run(ctx, *, raw_duration=60.0, beat_times=None, motion=([], []), ai_shots=None, extra=()):
    with ExitStack() as stack:
        stack.enter_context(patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": raw_duration}))
        stack.enter_context(patch(
            f"{STAGE}.SFXManager.resolve_bgm_path",
            return_value=Path("bgm.wav") if beat_times is not None else None,
        ))
        stack.enter_context(patch(f"{STAGE}.BeatSync.get_beat_times", return_value=list(beat_times or [])))
        stack.enter_context(patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=motion))
        stack.enter_context(patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]))
        if ai_shots is not None:
            stack.enter_context(patch(f"{STAGE}.GeminiVisionMatcher.is_available", return_value=True))
            stack.enter_context(patch(f"{STAGE}.GeminiVisionMatcher.prepare_request_context", return_value=None))
            stack.enter_context(patch(f"{STAGE}.GeminiVisionMatcher.get_cached_matches", return_value=ai_shots))
        for p in extra:
            stack.enter_context(p)
        ShotMatchingStage.run(ctx)
    return ctx.actual_clip_list


def _cut_times(clips):
    """Output-timeline instants of each internal cut (clips play back to back)."""
    acc, cuts = 0.0, []
    for clip in clips[:-1]:
        acc += clip["duration"]
        cuts.append(round(acc, 3))
    return cuts


def _four_even_cues(text="cue"):
    return [_cue(2.0 * i, 2.0 * (i + 1), text) for i in range(4)]


def test_generated_transition_easing_is_saved_for_preview():
    ctx = _context(_four_even_cues(), 8)
    ctx.style_preset = "viral_punch"
    clips = _run(ctx)
    eased = 0
    for clip, boundary in zip(clips[1:], ctx.transitions):
        if boundary.get("easing"):
            assert clip["transition_easing"] == boundary["easing"]
            eased += 1
    assert eased > 0


# ── A2: beat grid follows the tempo the mixer actually plays ──────────────

def test_tempo_ratio_helper_is_what_the_mixer_renders(tmp_path):
    cues = [_cue(0.0, 2.0, "ก" * 25), _cue(2.0, 4.0, "ข" * 25)]
    ratio = bgm_tempo_ratio(cues)
    assert ratio == 1.08  # 12.5 chars/s clamps to the +8% ceiling

    bgm = tmp_path / "bed.wav"
    bgm.write_bytes(b"\0")
    commands = []

    def fake_run(cmd, *args, **kwargs):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    with patch.object(SFXManager, "resolve_bgm_path", return_value=bgm), \
         patch.object(SFXManager, "resolve", return_value=None), \
         patch("scripts.sfx_manager.subprocess.run", side_effect=fake_run):
        SFXManager.mix_audio_track(
            voice_audio_path=str(tmp_path / "voice.wav"),
            cues=cues,
            total_duration=4.0,
            output_audio_path=str(tmp_path / "mix.wav"),
        )
    graph = " ".join(str(part) for part in commands[0])
    assert f"atempo={ratio:.3f}," in graph


def test_tempo_ratio_neutral_without_cues():
    assert bgm_tempo_ratio([]) == 1.0
    assert bgm_tempo_ratio(None) == 1.0


def test_beat_snap_uses_tempo_scaled_beat_times():
    cues = _four_even_cues("ก" * 25)  # ratio 1.08
    ratio = bgm_tempo_ratio(cues)
    heard_beat = 4.233333333  # inside the narration's J-lead window
    source_beat = round(heard_beat * ratio, 3)  # 4.572 in the untouched file
    clips = _run(_context(cues, 8.0), beat_times=[source_beat])
    # Natural cut is 4.1667 (4.0 + 0.18 J-lead on the frame grid); the heard
    # beat is inside the snap and narration windows; the raw-file beat is not.
    assert _cut_times(clips)[1] == pytest.approx(heard_beat, abs=1e-3)


# ── A1: motion snap and motion score use the raw-footage time base ────────

def test_motion_snap_lands_on_raw_footage_trough():
    cues = _four_even_cues()
    times = [round(i * 0.1, 1) for i in range(601)]
    trough_raw = {7.2, 17.0}  # still frames that also respect narration lead
    scores = [0.0 if t in trough_raw else 1.0 for t in times]
    ai_shots = [
        {"cue_id": i + 1, "start_time": 5.0 + 10.0 * i, "end_time": 9.0 + 10.0 * i, "punch_zoom": 1.1}
        for i in range(4)
    ]
    windows = []
    real_mean = MotionAnalyzer.segment_mean_score

    def spy(t, s, t0, t1):
        windows.append((round(t0, 3), round(t1, 3)))
        return real_mean(t, s, t0, t1)

    clips = _run(
        _context(cues, 8.0, use_ai_vision=True),
        motion=(times, scores),
        ai_shots=ai_shots,
        extra=(patch(f"{STAGE}.MotionAnalyzer.segment_mean_score", side_effect=spy),),
    )
    # Shot 0 plays raw 5.0.. -> trough at 7.2 means cut 2.2;
    # shot 1 plays raw 15.0.. from 2.2 -> trough 17.0 means cut 4.2.
    assert clips[0]["trim_start"] == 5.0
    assert clips[0]["duration"] == pytest.approx(2.2, abs=1e-3)
    assert clips[1]["trim_start"] == 15.0
    assert clips[1]["duration"] == pytest.approx(2.0, abs=1e-3)
    # Emphasis scoring reads each shot's own raw window, not timeline time.
    assert windows[0] == (5.0, 7.2)
    assert windows[1] == (15.0, 17.0)


def test_beat_cannot_move_picture_outside_narration_lead():
    cues = _four_even_cues("ก" * 25)
    ratio = bgm_tempo_ratio(cues)
    clips = _run(_context(cues, 8.0), beat_times=[4.3 * ratio])
    assert _cut_times(clips)[1] == pytest.approx(4.167, abs=1e-3)


def test_second_nearest_beat_is_used_when_nearest_conflicts_with_voice():
    cues = _four_even_cues("ก" * 25)
    ratio = bgm_tempo_ratio(cues)
    clips = _run(_context(cues, 8.0), beat_times=[4.133333333 * ratio, 4.233333333 * ratio])
    assert _cut_times(clips)[1] == pytest.approx(4.233333333, abs=1e-3)


def test_motion_cannot_move_picture_outside_narration_lead():
    ai_shots = [{"cue_id": i + 1, "start_time": 5. + 10. * i, "end_time": 9. + 10. * i} for i in range(4)]
    clips = _run(_context(_four_even_cues(), 8., use_ai_vision=True),
                 motion=([7.3], [0.]), ai_shots=ai_shots)
    assert _cut_times(clips)[0] == pytest.approx(2.167, abs=1e-3)


def test_short_shot_lead_and_missing_voice_timing_are_preserved():
    from scripts.stages.shot_matching_stage import _snap_preserves_voice_lead
    assert _snap_preserves_voice_lead(.1, 0., .1)
    assert not _snap_preserves_voice_lead(.2, 0., .1)
    assert _snap_preserves_voice_lead(10., None, .1)


def test_motion_uses_eligible_trough_instead_of_quieter_out_of_window_frame():
    ai_shots = [{"cue_id": i + 1, "start_time": 5. + 10. * i, "end_time": 9. + 10. * i} for i in range(4)]
    clips = _run(_context(_four_even_cues(), 8., use_ai_vision=True),
                 motion=([7.233333333, 7.3], [.1, 0.]), ai_shots=ai_shots)
    assert _cut_times(clips)[0] == pytest.approx(2.233, abs=1e-3)


def test_no_motion_data_keeps_cuts_on_cue_rhythm():
    clips = _run(_context(_four_even_cues(), 8.0))
    assert _cut_times(clips) == pytest.approx([2.167, 4.167, 6.167], abs=1e-3)


# ── A4: a merged AI shot split across groups keeps playing forward ───────

def test_split_ai_shot_advances_source_offset():
    cues = _four_even_cues()
    for cue in cues:
        cue["sentence_end"] = True  # These are genuinely separate sentences.
    merged = {"cue_ids": [1, 2, 3, 4], "start_time": 10.0, "end_time": 20.0, "punch_zoom": 1.1}
    clips = _run(_context(cues, 8.0, use_ai_vision=True), ai_shots=[merged])
    assert len(clips) == 4
    starts = [c["trim_start"] for c in clips]
    assert len(set(starts)) == 4, f"footage replayed: {starts}"
    # Each group continues exactly where the previous group's footage ended.
    for prev, nxt in zip(clips, clips[1:]):
        assert nxt["trim_start"] == pytest.approx(prev["trim_end"], abs=2e-3)
    assert starts[0] == 10.0


def test_same_ai_thought_is_one_continuous_shot_when_source_is_sufficient():
    clips = _run(_context(_four_even_cues(), 8., use_ai_vision=True),
                 ai_shots=[{"cue_ids": [1, 2, 3, 4], "start_time": 10., "end_time": 20.}])
    assert len(clips) == 1
    assert clips[0]["trim_start"] == 10.
    assert clips[0]["trim_end"] == 18.
    assert clips[0]["duration"] == 8.
    assert clips[0]["speed"] == 1.
    assert not clips[0].get("freeze_tail")


@pytest.mark.parametrize("signal", ["explicit", "line_idx", "parent", "suffix"])
def test_complete_thought_hold_respects_real_sentence_metadata(signal):
    cues = [_cue(i * 2, (i + 1) * 2, "feature") for i in range(6)]
    if signal == "explicit":
        for i, cue in enumerate(cues):
            cue["sentence_end"] = i in (3, 5)
    elif signal == "line_idx":
        for i, cue in enumerate(cues):
            cue["line_idx"] = 0 if i < 4 else 1
    elif signal == "suffix":
        cues[3]["text"] += " ครับ"
        cues[5]["text"] += " ครับ"
    ctx = _context(cues, 12., use_ai_vision=True)
    if signal == "parent":
        ctx.cues = [_cue(0., 8., "sentence one"), _cue(8., 12., "sentence two")]
    clips = _run(ctx, ai_shots=[{"cue_ids": list(range(1, 7)), "start_time": 10., "end_time": 25.}])
    assert len(clips) == 2
    assert _cut_times(clips) == pytest.approx([8.166666667], abs=.002)
    assert clips[1]["trim_start"] == pytest.approx(clips[0]["trim_end"], abs=.002)
    assert sum(c["duration"] for c in clips) == pytest.approx(12.)


def test_different_ai_feature_still_changes_before_sentence_end():
    cues = _four_even_cues()
    for cue in cues:
        cue["sentence_end"] = False
    matches = [{"cue_ids": [1, 2], "start_time": 10., "end_time": 20.},
               {"cue_ids": [3, 4], "start_time": 30., "end_time": 40.}]
    clips = _run(_context(cues, 8., use_ai_vision=True), ai_shots=matches)
    assert len(clips) == 2
    assert [c["trim_start"] for c in clips] == [10., 30.]
    assert _cut_times(clips) == pytest.approx([4.166666667], abs=.002)


def test_explicit_pacing_keeps_its_cuts_inside_shared_ai_topic():
    ctx = _context(_four_even_cues(), 8., use_ai_vision=True)
    ctx.editorial_pacing = {"beats": [2., 4., 6.]}
    clips = _run(ctx, ai_shots=[{"cue_ids": [1, 2, 3, 4], "start_time": 10., "end_time": 20.}])
    assert len(clips) == 4


@pytest.mark.parametrize("signal", ["line_idx", "parent"])
def test_polite_ending_inside_known_sentence_does_not_split_the_thought(signal):
    cues = _four_even_cues()
    cues[1]["text"] += " ครับ"
    cues[-1]["text"] += " ครับ"
    ctx = _context(cues, 8., use_ai_vision=True)
    if signal == "line_idx":
        for cue in cues:
            cue["line_idx"] = 0
    else:
        ctx.cues = [_cue(0., 8., "full sentence")]
    assert ShotMatchingStage._sentence_end_flags(cues, ctx.cues) == [False, False, False, True]
    clips = _run(ctx, ai_shots=[{"cue_ids": [1, 2, 3, 4], "start_time": 10., "end_time": 20.}])
    assert len(clips) == 1
    assert clips[0]["duration"] == 8.


def test_short_ai_window_plays_once_then_holds_without_crossing_topic():
    ctx = _context(_four_even_cues(), 8, use_ai_vision=True)
    clips = _run(ctx, ai_shots=[{"cue_ids": [1, 2, 3, 4], "start_time": 10, "end_time": 12}])
    assert len(clips) == 1
    assert clips[0]["trim_start"] == 10
    assert clips[0]["trim_end"] == 12
    assert clips[0]["freeze_tail"] == 6
    assert clips[0]["footage_shortage"]["missing_seconds"] == 6
    assert clips[0]["duration"] == 8
    assert clips[0]["speed"] == 1


def test_long_shortage_uses_only_last_frame_after_window_is_exhausted():
    cues = [_cue(i * 2, (i + 1) * 2, "same topic") for i in range(12)]
    clips = _run(_context(cues, 24, use_ai_vision=True),
                 ai_shots=[{"cue_ids": list(range(1, 13)), "start_time": 10, "end_time": 12}])
    assert sum(c["duration"] for c in clips) == pytest.approx(24)
    assert all(c["trim_end"] <= 12 for c in clips)
    assert all(c.get("freeze_tail", 0) <= 10 for c in clips)
    assert clips[1]["trim_start"] == pytest.approx(12 - 1 / 30, abs=1e-6)


# ── A5: hold to a sentence end instead of cutting mid-sentence ───────────

@pytest.mark.parametrize("first_length, expected_cut", [(0.4, 0.5), (0.8, 29 / 30)])
def test_short_topics_keep_both_ai_selected_features(first_length, expected_cut):
    cues = [_cue(0, first_length, "feature A"), _cue(first_length, 1.6, "feature B")]
    matches = [{"cue_ids": [1], "start_time": 10, "end_time": 14},
               {"cue_ids": [2], "start_time": 30, "end_time": 35}]
    clips = _run(_context(cues, 1.6, use_ai_vision=True), ai_shots=matches)
    assert [clip["trim_start"] for clip in clips] == [10, 30]
    assert sum(clip["duration"] for clip in clips) == pytest.approx(1.6)
    assert _cut_times(clips) == pytest.approx([expected_cut], abs=.002)


def test_short_cues_with_one_ai_topic_still_hold_one_shot():
    cues = [_cue(0, .8, "feature A"), _cue(.8, 1.6, "feature A continued")]
    matches = [{"cue_ids": [1, 2], "start_time": 10, "end_time": 14}]
    clips = _run(_context(cues, 1.6, use_ai_vision=True), ai_shots=matches)
    assert len(clips) == 1
    assert clips[0]["trim_start"] == 10
    assert clips[0]["duration"] == pytest.approx(1.6)


def test_tiny_topic_borrows_frames_without_extending_narration():
    cues = [_cue(0, .1, "feature A"), _cue(.1, 1.6, "feature B")]
    matches = [{"cue_ids": [1], "start_time": 2, "end_time": 6},
               {"cue_ids": [2], "start_time": 10, "end_time": 14}]
    clips = _run(_context(cues, 1.6, use_ai_vision=True), ai_shots=matches)
    assert [c["trim_start"] for c in clips] == [2, 10]
    assert sum(c["duration"] for c in clips) == pytest.approx(1.6)
    assert clips[0]["duration"] == .2


def test_too_many_tiny_topics_do_not_extend_the_voice(capsys):
    cues = [_cue(i / 10, (i + 1) / 10, str(i)) for i in range(4)]
    matches = [{"cue_ids": [i + 1], "start_time": i * 4, "end_time": i * 4 + 3} for i in range(4)]
    clips = _run(_context(cues, .4, use_ai_vision=True), ai_shots=matches)
    assert sum(c["duration"] for c in clips) == pytest.approx(.4)
    assert "รักษาเวลาเสียง" in capsys.readouterr().out


def test_short_unmatched_lead_does_not_hide_next_ai_topic():
    cues = [_cue(0, .8, "unmatched"), _cue(.8, 1.6, "feature B")]
    clips = _run(_context(cues, 1.6, use_ai_vision=True),
                 ai_shots=[{"cue_ids": [2], "start_time": 30, "end_time": 35}])
    assert len(clips) == 2
    assert clips[1]["trim_start"] == 30

def _a5_cues(sentence_markers):
    end = " ครับ" if sentence_markers else ""
    return [
        _cue(0.0, 0.8, "ก"),
        _cue(0.8, 1.6, "ข"),
        _cue(1.6, 2.2, "ค" + end),
        _cue(2.2, 3.4, "ง"),
        _cue(3.4, 4.6, "จ" + end),
    ]


def test_cut_waits_for_sentence_end_within_max_shot():
    clips = _run(_context(_a5_cues(True), 4.6))
    # Cut after "ค ครับ" (2.2 + 0.15 lead on the grid = 2.333), not mid-sentence at 1.733.
    assert [c["duration"] for c in clips] == pytest.approx([2.333, 2.267], abs=1e-3)


def test_cues_without_sentence_info_group_as_before():
    clips = _run(_context(_a5_cues(False), 4.6))
    assert [c["duration"] for c in clips] == pytest.approx([1.733, 2.867], abs=1e-3)


# ── Frame grid ─────────────────────────────────────────────────────────────

def test_cut_times_land_on_30fps_grid_and_keep_total():
    cues = [
        _cue(0.237, 1.911, "a"),
        _cue(1.911, 3.777, "b"),
        _cue(3.777, 5.502, "c"),
        _cue(5.502, 7.913, "d"),
    ]
    clips = _run(_context(cues, 8.4))
    durations = [c["duration"] for c in clips]
    assert all(d > 0 for d in durations)
    # Clips start at 0.0 (the first shot covers the TTS lead-in silence, R2/A6)
    # and run to the exact total, so the picture is as long as the voice.
    assert sum(durations) == pytest.approx(8.4, abs=2e-3)
    for cut in _cut_times(clips):
        frames = cut * 30
        assert abs(frames - round(frames)) < 0.06, f"cut {cut} is off the 1/30 s grid"


# ── R2/A6: the plan starts at 0.0 whatever the TTS lead-in silence ────────

@pytest.mark.parametrize("fcs", [0.0, 0.1, 0.3, 0.4])
def test_first_shot_covers_tts_lead_in_and_cuts_keep_the_j_lead(fcs):
    cues = [_cue(round(fcs + 2.0 * i, 3), round(fcs + 2.0 * (i + 1), 3), "cue") for i in range(4)]
    total = round(fcs + 8.0, 3)
    clips = _run(_context(cues, total))
    assert sum(c["duration"] for c in clips) == pytest.approx(total, abs=2e-3)
    # every cut = next cue's voice onset + 0.18 s J-lead on the frame grid
    for cut, cue in zip(_cut_times(clips), cues[1:]):
        assert 0.15 <= cut - cue["start"] <= 0.25, (fcs, cut, cue["start"])
    # gadget rule: no shot outside 1.5-3.0 s even with the longer first shot
    assert all(1.5 <= c["duration"] <= 3.0 for c in clips), [c["duration"] for c in clips]


# ── R2/style cut rhythm ────────────────────────────────────────────────────

def test_default_style_cuts_exactly_like_the_old_constants():
    a = _run(_context(_four_even_cues(), 8.0))
    ctx = _context(_four_even_cues(), 8.0)
    ctx.style_preset = "clean_tech_review"
    b = _run(ctx)
    assert [c["duration"] for c in a] == [c["duration"] for c in b]
    assert _cut_times(a) == pytest.approx([2.167, 4.167, 6.167], abs=1e-3)


def test_style_j_lead_and_max_shot_reach_the_planner():
    ctx = _context(_four_even_cues(), 8.0)
    ctx.style_preset = "premium_minimal"  # j_lead 0.24
    cuts = _cut_times(_run(ctx))
    assert cuts[:2] == pytest.approx([2.233, 4.233], abs=1e-3)
    # flash_deal max 2.0: 1.2 s cues cannot be paired into one 2.4 s shot
    cues = [_cue(1.2 * i, 1.2 * (i + 1), "x") for i in range(6)]
    ctx = _context(cues, 7.2)
    ctx.style_preset = "flash_deal"
    fast = _run(ctx)
    ctx = _context(cues, 7.2)
    default = _run(ctx)
    assert len(fast) >= len(default)


# ── R2/A7a: pacing path uses the same J-lead ───────────────────────────────

def test_pacing_boundaries_get_the_j_lead_after_the_next_word():
    from scripts.stages.shot_matching_stage import _pacing_j_cut_boundaries

    # boundary 2.0 sits at the start of a 0.3 s pause; next word starts 2.3
    out, onsets = _pacing_j_cut_boundaries([0.0, 2.0, 4.4, 5.7], [0.1, 2.3, 4.4], 0.18, 1.5)
    assert out[1] == pytest.approx(round((2.3 + 0.18) * 30) / 30)
    assert onsets[1] == 2.3
    # 4.4 -> 4.567 would leave 1.133 s < 0.8 x 1.5 before 5.7: kept
    assert out[2] == 4.4 and onsets[2] is None
    assert out[0] == 0.0 and out[-1] == 5.7


def test_pacing_plan_cuts_after_voice_onset():
    cues = _four_even_cues()
    ctx = _context(cues, 8.0)
    words = [{"text": f"w{i}", "start": 2.0 * i + 0.05, "end": 2.0 * i + 1.6, "source_index": i} for i in range(4)]
    ctx.editorial_pacing = {"words": words, "beats": [{"timestamp": 3.6}, {"timestamp": 5.6}]}
    clips = _run(ctx)
    cuts = _cut_times(clips)
    assert len(cuts) == 2
    for cut, onset in zip(cuts, (4.05, 6.05)):
        assert 0.15 <= cut - onset <= 0.25, (cuts, onset)


# ── R2/voice valley snap ───────────────────────────────────────────────────

def _voice_with_dip(sr, total, dip_at, dip_len=0.02):
    import numpy as np

    t = np.arange(int(total * sr)) / sr
    # 1 kHz: a 10 ms window holds whole periods, so loudness is flat except the dip
    x = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    a = int((dip_at - dip_len / 2) * sr)
    x[a:a + int(dip_len * sr)] = 0.0
    return x


def test_voice_valley_snap_moves_to_quiet_frame_inside_j_window():
    from scripts.stages.shot_matching_stage import _voice_valley_snap

    sr = 16000
    onset, cut = 2.0, round(2.18 * 30) / 30          # 2.1667
    dip = round(2.2333 * 30) / 30                     # 2 frames later, lead 0.233
    x = _voice_with_dip(sr, 6.0, dip)
    assert _voice_valley_snap(cut, onset, x, sr, 0.0, 4.0, 1.5) == pytest.approx(dip)
    # Short-shot lead below .15 cannot be moved into an even earlier dip.
    early_cut = round(2.1333 * 30) / 30
    early_dip = round(2.0667 * 30) / 30
    x_early = _voice_with_dip(sr, 6.0, early_dip)
    assert _voice_valley_snap(early_cut, onset, x_early, sr, 0.0, 4.0, 1.5) == pytest.approx(early_cut)
    # min shot: the next shot would drop below 1.5 s -> stays
    assert _voice_valley_snap(cut, onset, x, sr, 0.0, dip + 1.49, 1.5) == pytest.approx(cut)
    # no audio -> unchanged
    assert _voice_valley_snap(cut, onset, None, sr, 0.0, 4.0, 1.5) == cut


def test_voice_valley_snap_reads_the_voice_track_and_skips_unreadable(tmp_path):
    import wave

    import numpy as np

    sr = 16000
    x = _voice_with_dip(sr, 8.0, round(4.2333 * 30) / 30)
    path = tmp_path / "voice.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    ctx = _context(_four_even_cues(), 8.0)
    ctx.voice_audio_path = path
    cuts = _cut_times(_run(ctx))
    assert cuts[1] == pytest.approx(4.233, abs=2e-3)
    # unreadable voice file: silently the plain rhythm
    bad = tmp_path / "broken.wav"
    bad.write_bytes(b"not a wav")
    ctx = _context(_four_even_cues(), 8.0)
    ctx.voice_audio_path = bad
    assert _cut_times(_run(ctx)) == pytest.approx([2.167, 4.167, 6.167], abs=1e-3)
