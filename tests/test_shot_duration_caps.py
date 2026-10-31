"""Q2 shot-length caps + Q7 fail-loud for the auto shot planner.

Offline and deterministic: Gemini, ffprobe, librosa and opencv are mocked;
nothing is written outside pytest's tmp_path.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import gemini_vision_matcher as gvm
from scripts.error_handler import AppError
from scripts.shot_source_window import coalesce_short_windows
from scripts.stages.shot_matching_stage import (
    MAX_FREEZE_HOLD_SEC,
    SHOT_CAP_FACTOR,
    _coalesce_ai_thought_groups,
)
from scripts.style_motion_policy import resolve_style_motion_policy
from tests.test_shot_matching_cut_quality import STAGE, _context, _cue, _run

STYLES = ("clean_tech_review", "viral_punch", "smooth_showcase", "premium_minimal", "flash_deal")


def _cap(style):
    return resolve_style_motion_policy(style).max_shot * SHOT_CAP_FACTOR


def _assert_caps(clips, style):
    cap = _cap(style)
    for clip in clips:
        if clip.get("hold_reason"):
            continue
        assert clip["duration"] <= cap + 1e-6, (style, clip)
        assert clip.get("freeze_tail", 0) <= MAX_FREEZE_HOLD_SEC + 1e-6, (style, clip)


# ── Gemini prompt follows the active preset ───────────────────────────────

def _capture_prompt(monkeypatch, tmp_path, **kwargs):
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", tmp_path / ".vision_cache.json")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_or_upload_video",
                        classmethod(lambda cls, client, path: MagicMock(name="remote_video")))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    prompts = []

    def factory(*, api_key, http_options=None):
        client = MagicMock()

        def generate_content(*, model, contents, config=None):
            prompts.append(contents[1])
            resp = MagicMock()
            resp.text = json.dumps({"matched_shots": [{"cue_ids": [1], "start_time": 0, "end_time": 2}]})
            return resp

        client.models.generate_content.side_effect = generate_content
        return client

    with patch("google.genai.Client", side_effect=factory):
        gvm.GeminiVisionMatcher.match_script_to_video(
            str(raw), [{"start": 0.0, "end": 2.0, "text": "หนึ่ง"}], raw_duration=10.0, **kwargs)
    assert prompts
    return prompts[0]


def test_vision_prompt_uses_the_preset_shot_range(monkeypatch, tmp_path):
    prompt = _capture_prompt(monkeypatch, tmp_path, min_shot=1.5, max_shot=2.2)
    assert "1.5 - 2.2 วินาที" in prompt
    assert "ห้ามเกิน 2.8 วินาที" in prompt  # 2.2 x 1.25
    assert "2.0 - 6.0" not in prompt


def test_vision_prompt_defaults_to_config_shot_range(monkeypatch, tmp_path):
    from scripts.config import MAX_SHOT_DURATION, MIN_SHOT_DURATION

    prompt = _capture_prompt(monkeypatch, tmp_path)
    assert f"{MIN_SHOT_DURATION:.1f} - {MAX_SHOT_DURATION:.1f} วินาที" in prompt


def test_stage_passes_the_style_range_to_gemini():
    seen = {}

    def fake_match(**kwargs):
        seen.update(kwargs)
        return []

    ctx = _context([_cue(2.0 * i, 2.0 * (i + 1), "cue") for i in range(3)], 6.0, use_ai_vision=True)
    ctx.style_preset = "viral_punch"
    with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 30.0}), \
         patch(f"{STAGE}.SFXManager.resolve_bgm_path", return_value=None), \
         patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=([], [])), \
         patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]), \
         patch(f"{STAGE}.GeminiVisionMatcher.is_available", return_value=True), \
         patch(f"{STAGE}.GeminiVisionMatcher.prepare_request_context", return_value=None), \
         patch(f"{STAGE}.GeminiVisionMatcher.get_cached_matches", return_value=None), \
         patch(f"{STAGE}.GeminiVisionMatcher.match_script_to_video", side_effect=fake_match):
        from scripts.stages.shot_matching_stage import ShotMatchingStage
        ShotMatchingStage.run(ctx)
    assert (seen["min_shot"], seen["max_shot"]) == (1.5, 2.2)


# ── merge caps ────────────────────────────────────────────────────────────

def test_topic_coalesce_stops_at_the_cap():
    topic = {"start_time": 0, "end_time": 30}
    matches = [topic] * 4
    cut_points = [0.0, 2.0, 4.0, 6.0, 8.0]
    groups = [[0], [1], [2], [3]]
    flags = [False] * 4
    assert _coalesce_ai_thought_groups(groups, matches, flags) == [[0, 1, 2, 3]]  # legacy call
    capped = _coalesce_ai_thought_groups(groups, matches, flags, cut_points, 3.125)
    assert capped == [[0], [1], [2], [3]]
    assert _coalesce_ai_thought_groups(groups, matches, flags, cut_points, 4.0) == [[0, 1], [2, 3]]


@pytest.mark.parametrize("style", STYLES)
def test_long_single_topic_never_exceeds_the_cap(style):
    cues = [_cue(2.0 * i, 2.0 * (i + 1), "same feature") for i in range(8)]
    ctx = _context(cues, 16.0, use_ai_vision=True)
    ctx.style_preset = style
    clips = _run(ctx, ai_shots=[{"cue_ids": list(range(1, 9)), "start_time": 10.0, "end_time": 40.0}])
    _assert_caps(clips, style)
    assert sum(c["duration"] for c in clips) == pytest.approx(16.0, abs=0.01)
    # Strict Topic Hold: the pieces keep playing the same source forward.
    for prev, nxt in zip(clips, clips[1:]):
        assert nxt["trim_start"] == pytest.approx(prev["trim_end"], abs=2e-3)


@pytest.mark.parametrize("style", STYLES)
def test_force_merged_ultra_short_cue_is_split_back_under_the_cap(style):
    cues = [_cue(0.0, 3.0, "อันแรกครับ"), _cue(3.0, 3.5, "นะ"), _cue(3.5, 6.5, "อันสองครับ"),
            _cue(6.5, 9.0, "อันสามครับ")]
    ctx = _context(cues, 9.0)
    ctx.style_preset = style
    clips = _run(ctx)
    _assert_caps(clips, style)
    assert sum(c["duration"] for c in clips) == pytest.approx(9.0, abs=0.01)
    assert min(c["duration"] for c in clips) >= 0.2


# ── freeze-hold cap ───────────────────────────────────────────────────────

def test_short_window_continues_on_adjacent_footage_instead_of_freezing():
    match = {"start_time": 10, "end_time": 12}
    overrides, exhausted = {}, set()
    groups, times, onsets = coalesce_short_windows(
        [[0], [1], [2]], [0, 2, 4, 6], [None, 2, 4, None], [match] * 3, 60,
        max_hold=1.0, overrides=overrides, exhausted=exhausted)
    assert times == [0, 2, 6]
    assert groups[0] == [0, 1, 2] and groups[1] == [0, 1, 2]
    assert groups[0] is not groups[1]
    adjacent = overrides[id(groups[1])][1]
    assert (adjacent["start_time"], adjacent["end_time"]) == (12, 16)
    assert adjacent["adjacent_to"] == {"start": 10, "end": 12}
    assert not exhausted


def test_shortfall_within_one_second_keeps_the_legacy_hold():
    match = {"start_time": 10, "end_time": 13}
    overrides = {}
    groups, times, _ = coalesce_short_windows(
        [[0], [1]], [0, 2, 4], [None, 2, None], [match] * 2, 60, max_hold=1.0, overrides=overrides)
    assert groups == [[0, 1]] and times == [0, 4] and not overrides


def test_no_adjacent_footage_falls_back_to_hold_and_is_reported():
    match = {"start_time": 0, "end_time": 2}
    overrides, exhausted = {}, set()
    groups, times, _ = coalesce_short_windows(
        [[0], [1]], [0, 4, 8], [None, 4, None], [match] * 2, 2.0,
        max_hold=1.0, overrides=overrides, exhausted=exhausted)
    assert times == [0, 8] and not overrides
    assert id(groups[0]) in exhausted


@pytest.mark.parametrize("style", STYLES)
def test_stage_fixture_has_no_long_freeze_without_hold_reason(style):
    cues = [_cue(2.0 * i, 2.0 * (i + 1), "feature") for i in range(6)]
    ctx = _context(cues, 12.0, use_ai_vision=True)
    ctx.style_preset = style
    ai_shots = [{"cue_ids": [1, 2, 3], "start_time": 10, "end_time": 11.5},
                {"cue_ids": [4, 5, 6], "start_time": 30, "end_time": 31}]
    clips = _run(ctx, ai_shots=ai_shots)
    _assert_caps(clips, style)
    assert not any(c.get("hold_reason") for c in clips)
    assert sum(c["duration"] for c in clips) == pytest.approx(12.0, abs=0.01)


# ── Q7: planning failures are loud ───────────────────────────────────────

def test_shot_planning_bug_raises_a_thai_domain_error_instead_of_one_long_clip():
    ctx = _context([_cue(0.0, 2.0, "a"), _cue(2.0, 4.0, "b")], 4.0)
    messages = []
    ctx.notify = lambda message, *args: messages.append(message)
    boom = patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", side_effect=RuntimeError("bad cue"))
    with pytest.raises(AppError) as info:
        with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 30.0}), \
             patch(f"{STAGE}.SFXManager.resolve_bgm_path", return_value=None), \
             patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=([], [])), boom:
            from scripts.stages.shot_matching_stage import ShotMatchingStage
            ShotMatchingStage.run(ctx)
    assert info.value.code == "SHOT_PLANNING_FAILED"
    assert "วางแผนช็อต" in info.value.message_th
    assert "bad cue" in info.value.details
    assert ctx.actual_clip_list is None
    assert any("วางแผนช็อตไม่สำเร็จ" in m for m in messages)


def test_tone_quota_hit_degrades_without_failing_the_plan():
    from scripts.error_handler import ErrorCategory

    quota = AppError(category=ErrorCategory.AI_PROVIDER, code="AI_QUOTA_EXCEEDED",
                     message_th="เกินโควต้า", suggestion_th="รอพรุ่งนี้")
    ctx = _context([_cue(0.0, 2.0, "a"), _cue(2.0, 4.0, "b")], 4.0)
    messages = []
    ctx.notify = lambda message, *args: messages.append(message)
    clips = _run(ctx, extra=(patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", side_effect=quota),))
    assert len(clips) >= 2
    assert sum(c["duration"] for c in clips) == pytest.approx(4.0, abs=1e-3)
    assert any("โควต้า" in m for m in messages)
