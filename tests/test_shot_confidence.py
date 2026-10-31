"""M6 matching confidence + still-footage rejection (Gemini mocked, offline)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import gemini_vision_matcher as gvm
from scripts.gemini_vision_matcher import (
    CATALOG_LOW_CONFIDENCE,
    CATALOG_MATCH_CONFIDENCE,
    GeminiVisionMatcher,
    normalize_match_confidence,
)
from scripts.stages.shot_matching_stage import HOOK_MOTION_THRESHOLD, _match_confidence
from tests.legacy_shot_pacing import legacy_body_pacing  # noqa: F401  (fixture)
from tests.test_shot_matching_cut_quality import _context, _cue, _cut_times, _run


def _four_cues():
    return [_cue(2.0 * i, 2.0 * (i + 1), "cue") for i in range(4)]


# ── Gemini schema ─────────────────────────────────────────────────────────

def test_confidence_is_optional_and_normalised():
    shots = [{"cue_ids": [1]}, {"cue_ids": [2], "confidence": "0.7"}, {"cue_ids": [3], "confidence": 85},
             {"cue_ids": [4], "confidence": "high"}, {"cue_ids": [5], "confidence": -2},
             {"cue_ids": [6], "confidence": 1.4}, "garbage"]
    out = normalize_match_confidence(shots)
    assert "confidence" not in out[0]
    assert out[1]["confidence"] == 0.7
    assert out[2]["confidence"] == 0.85
    assert "confidence" not in out[3]
    assert out[4]["confidence"] == 0.0
    assert out[5]["confidence"] == 1.0
    assert out[6] == "garbage"
    assert shots[1]["confidence"] == "0.7"  # input not mutated
    assert normalize_match_confidence(None) == []


def test_stage_reads_confidence_tolerantly():
    assert _match_confidence({"confidence": 0.4}) == 0.4
    assert _match_confidence({"confidence": "x"}) is None
    assert _match_confidence({}) is None
    assert _match_confidence(None) is None


def test_vision_prompt_asks_for_confidence_and_response_is_parsed(monkeypatch, tmp_path):
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", tmp_path / ".vision_cache.json")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(GeminiVisionMatcher, "get_or_upload_video",
                        classmethod(lambda cls, client, path: MagicMock(name="remote_video")))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    prompts = []
    shots = [{"cue_ids": [1], "start_time": 0, "end_time": 2, "confidence": "0.3"},
             {"cue_ids": [2], "start_time": 4, "end_time": 6}]

    def factory(*, api_key, http_options=None):
        client = MagicMock()

        def generate_content(*, model, contents, config=None):
            prompts.append(contents[1])
            resp = MagicMock()
            resp.text = "```json\n" + json.dumps({"matched_shots": shots}) + "\n```"
            return resp

        client.models.generate_content.side_effect = generate_content
        return client

    cues = [{"start": 0.0, "end": 2.0, "text": "หนึ่ง"}, {"start": 2.0, "end": 4.0, "text": "สอง"}]
    with patch("google.genai.Client", side_effect=factory):
        result = GeminiVisionMatcher.match_script_to_video(str(raw), cues, raw_duration=10.0)
    assert '"confidence": 0.85' in prompts[0]
    assert result[0]["confidence"] == 0.3
    assert "confidence" not in result[1]


# ── catalog path ──────────────────────────────────────────────────────────

def test_catalog_marks_keyword_matches_confident_and_guesses_low():
    catalog = {"scenes": [
        {"id": 1, "start": 0, "end": 10, "action_type": "port_connection", "keywords": ["USB-C"],
         "description": "เสียบ USB-C"},
        {"id": 2, "start": 10, "end": 20, "action_type": "overview", "keywords": ["กล่อง"], "description": "กล่อง"},
    ]}
    cues = [{"start": 4.0, "end": 7.0, "text": "เสียบ USB-C ครับ"}, {"start": 7.0, "end": 10.0, "text": "สวยมากครับ"}]
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, cues, 20)
    assert matches[0]["confidence"] == CATALOG_MATCH_CONFIDENCE
    assert matches[1]["confidence"] == CATALOG_LOW_CONFIDENCE
    assert not matches[1].get("hero_fallback")  # outside the hook: no hero swap


def test_unmatched_hook_prefers_moving_hero_footage_over_a_static_overview():
    catalog = {"scenes": [
        {"id": 1, "start": 0, "end": 6, "action_type": "overview", "angle_phase": "front",
         "keywords": ["ตัวเครื่อง"], "description": "วางนิ่งบนโต๊ะ"},
        {"id": 2, "start": 6, "end": 12, "action_type": "turntable_spin", "angle_phase": "side",
         "keywords": ["หมุน"], "description": "หมุนโชว์รอบตัว"},
    ]}
    cues = [{"start": 0.0, "end": 2.5, "text": "ตัวนี้ดีจริงครับ"}]
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, cues, 12)
    assert matches[0]["scene_id"] == 2
    assert matches[0]["hero_fallback"] is True
    assert matches[0]["confidence"] == CATALOG_LOW_CONFIDENCE


# ── stage: hook window ────────────────────────────────────────────────────

def _motion(still_until=30.0, moving=(40.0, 44.0)):
    times = [round(i * 0.1, 1) for i in range(601)]
    scores = [1.0 if moving[0] <= t < moving[1] else 0.02 for t in times]
    return times, scores


def test_low_confidence_hook_match_is_replaced_by_the_most_moving_footage():
    ai_shots = [{"cue_id": i + 1, "start_time": 5.0 + 5 * i, "end_time": 9.0 + 5 * i, "confidence": 0.2}
                for i in range(4)]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=_motion(), ai_shots=ai_shots)
    assert 40.0 <= clips[0]["trim_start"] < 44.0
    # Later (non-hook) shots keep their AI match.
    assert clips[-1]["trim_start"] == pytest.approx(20.0, abs=0.3)


def test_confident_hook_match_keeps_its_topic():
    ai_shots = [{"cue_id": i + 1, "start_time": 5.0 + 5 * i, "end_time": 9.0 + 5 * i, "confidence": 0.9}
                for i in range(4)]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=_motion(), ai_shots=ai_shots)
    assert clips[0]["trim_start"] == 5.0


def test_catalog_hero_fallback_is_not_second_guessed():
    ai_shots = [{"cue_id": i + 1, "start_time": 5.0 + 5 * i, "end_time": 9.0 + 5 * i,
                 "confidence": 0.35, "hero_fallback": True} for i in range(4)]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=_motion(), ai_shots=ai_shots)
    assert clips[0]["trim_start"] == 5.0


def test_no_ai_match_opens_on_the_most_moving_window_not_a_position_guess():
    clips = _run(_context(_four_cues(), 8.0), motion=_motion(moving=(30.0, 34.0)))
    assert 30.0 <= clips[0]["trim_start"] < 34.0


def test_hook_window_inside_a_match_moves_off_near_still_frames():
    times = [round(i * 0.1, 1) for i in range(601)]
    scores = [1.0 if 12.0 <= t < 16.0 else 0.0 for t in times]
    ai_shots = [{"cue_ids": [1, 2], "start_time": 5.0, "end_time": 20.0, "confidence": 0.9},
                {"cue_ids": [3, 4], "start_time": 30.0, "end_time": 40.0, "confidence": 0.9}]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=(times, scores), ai_shots=ai_shots)
    assert 12.0 - 1e-6 <= clips[0]["trim_start"] < 16.0  # same match window, moving part
    from scripts.motion_analyzer import MotionAnalyzer
    first = MotionAnalyzer.segment_mean_score(times, scores, clips[0]["trim_start"], clips[0]["trim_end"])
    assert first >= HOOK_MOTION_THRESHOLD


def test_hook_keeps_window_when_no_moving_alternative_exists():
    times = [round(i * 0.1, 1) for i in range(601)]
    scores = [0.0] * len(times)
    ai_shots = [{"cue_ids": [1, 2, 3, 4], "start_time": 5.0, "end_time": 20.0}]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=(times, scores), ai_shots=ai_shots)
    assert clips[0]["trim_start"] == 5.0


# ── motion snap never lands on a near-still frame ────────────────────────

@pytest.mark.usefixtures("legacy_body_pacing")
def test_motion_snap_rejects_near_still_trough():
    ai_shots = [{"cue_id": i + 1, "start_time": 5. + 10. * i, "end_time": 9. + 10. * i} for i in range(4)]
    times = [round(i * 0.1, 1) for i in range(601)]
    scores = [0.0 if t == 7.2 else 1.0 for t in times]
    clips = _run(_context(_four_cues(), 8., use_ai_vision=True), motion=(times, scores), ai_shots=ai_shots)
    assert _cut_times(clips)[0] == pytest.approx(2.167, abs=1e-3)  # stays on the J-lead cut


@pytest.mark.usefixtures("legacy_body_pacing")
def test_motion_snap_still_uses_a_calm_but_moving_frame():
    ai_shots = [{"cue_id": i + 1, "start_time": 5. + 10. * i, "end_time": 9. + 10. * i} for i in range(4)]
    times = [round(i * 0.1, 1) for i in range(601)]
    scores = [0.3 if t == 7.2 else 1.0 for t in times]
    clips = _run(_context(_four_cues(), 8., use_ai_vision=True), motion=(times, scores), ai_shots=ai_shots)
    assert _cut_times(clips)[0] == pytest.approx(2.2, abs=1e-3)
