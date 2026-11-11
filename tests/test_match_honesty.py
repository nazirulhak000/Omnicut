"""Script-to-footage matching must not hide a guess (offline, Gemini mocked).

Three contracts:
  * a shot that plays footage the matcher itself called a guess carries
    ``match_review`` on its clip, without changing where the clip cuts;
  * Viral Lint lists that clip (VISUAL_MATCH) until the user moves it onto
    other footage;
  * the placeholder scene catalog (fixed 5 s slices, made without looking at
    the video) is never reported as a successful scan.
"""

import copy

import pytest

from scripts import gemini_vision_matcher as gvm
from scripts.gemini_vision_matcher import GeminiVisionMatcher, summarize_catalog_scan
from scripts.stages.shot_matching_stage import LOW_MATCH_CONFIDENCE
from scripts.viral_lint import layout_clips, lint_manifest
from tests.legacy_shot_pacing import legacy_body_pacing  # noqa: F401  (fixture)
from tests.test_shot_confidence import _four_cues, _motion
from tests.test_shot_matching_cut_quality import _context, _run


def _plan(confidences, **extra):
    """Four 2 s cues, one AI match each, 5 s apart in the raw footage."""
    ai_shots = []
    for i, confidence in enumerate(confidences):
        shot = {"cue_id": i + 1, "start_time": 5.0 + 5 * i, "end_time": 9.0 + 5 * i, **extra}
        if confidence is not None:
            shot["confidence"] = confidence
        ai_shots.append(shot)
    return _run(_context(_four_cues(), 8.0, use_ai_vision=True), ai_shots=ai_shots)


def _visual(issues):
    return [issue for issue in issues if issue.code == "VISUAL_MATCH"]


# -- the planner records the guess -------------------------------------------


def test_low_confidence_body_shot_is_marked_and_pinned_to_its_footage():
    clips = _plan([0.9, 0.9, 0.9, 0.2])
    assert [bool(c.get("match_review")) for c in clips[:-1]] == [False] * (len(clips) - 1)
    review = clips[-1]["match_review"]
    assert review["reason"] == "low_confidence"
    assert review["confidence"] == 0.2
    assert review["trim_start"] == clips[-1]["trim_start"]


def test_marking_a_guess_does_not_change_the_cut():
    keys = ("trim_start", "trim_end", "duration", "zoom", "transition_in")
    guessed, confident = _plan([0.9, 0.9, 0.9, 0.2]), _plan([0.9, 0.9, 0.9, 0.9])
    assert [[c.get(k) for k in keys] for c in guessed] == [[c.get(k) for k in keys] for c in confident]


@pytest.mark.parametrize("confidence", [LOW_MATCH_CONFIDENCE, 0.85, None])
def test_trusted_or_unrated_matches_are_not_marked(confidence):
    assert not any(c.get("match_review") for c in _plan([confidence] * 4))


def test_a_catalog_hero_pick_is_not_a_guess():
    assert not any(c.get("match_review") for c in _plan([0.35] * 4, hero_fallback=True))


def test_hook_shot_replaced_by_moving_footage_carries_no_review():
    """The rejected match is not what plays, so there is nothing to review."""
    ai_shots = [{"cue_id": i + 1, "start_time": 5.0 + 5 * i, "end_time": 9.0 + 5 * i, "confidence": 0.2}
                for i in range(4)]
    clips = _run(_context(_four_cues(), 8.0, use_ai_vision=True), motion=_motion(), ai_shots=ai_shots)
    assert 40.0 <= clips[0]["trim_start"] < 44.0  # the moving window, not the match
    assert "match_review" not in clips[0]
    assert clips[-1]["match_review"]["confidence"] == 0.2


def test_the_matchers_reason_is_kept_short_for_the_editor():
    clips = _plan([0.9, 0.9, 0.9, 0.3], visual_reason="ภาพกล่องสินค้า " * 40)
    assert 0 < len(clips[-1]["match_review"]["note"]) <= 120


# -- Viral Lint shows it ------------------------------------------------------


def _manifest(clips):
    return {"clip_list": copy.deepcopy(clips), "style_preset": "clean_tech_review"}


def test_lint_lists_the_guessed_shot_at_its_place_on_the_timeline():
    clips = _plan([0.9, 0.9, 0.9, 0.2])
    issues = _visual(lint_manifest(_manifest(clips)))
    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity == "warn"
    assert issue.clip_index == len(clips) - 1
    last = layout_clips(_manifest(clips))[-1]  # transitions overlap, so use the lint's own layout
    assert (issue.start, issue.end) == (pytest.approx(last["start"], abs=0.01), pytest.approx(last["end"], abs=0.01))
    assert issue.start > 4.0  # the fourth line, not the opening
    assert "20%" in issue.message_th


def test_lint_is_silent_for_a_confident_plan():
    assert _visual(lint_manifest(_manifest(_plan([0.9] * 4)))) == []


def test_warning_clears_once_the_user_moves_the_clip_to_other_footage():
    manifest = _manifest(_plan([0.9, 0.9, 0.9, 0.2]))
    manifest["clip_list"][-1]["trim_start"] += 3.0
    manifest["clip_list"][-1]["trim_end"] += 3.0
    assert _visual(lint_manifest(manifest)) == []


@pytest.mark.parametrize("review", [None, "low", {}, {"reason": "other", "trim_start": 1.0},
                                    {"reason": "low_confidence"}, {"reason": "low_confidence", "trim_start": "x"}])
def test_lint_ignores_malformed_or_foreign_review_records(review):
    clip = {"source_path": "raw.mp4", "trim_start": 1.0, "trim_end": 3.0, "speed": 1, "match_review": review}
    assert _visual(lint_manifest({"clip_list": [clip]})) == []


# -- the placeholder catalog is never a scan result ---------------------------


def test_scan_without_an_api_key_returns_a_marked_uncached_placeholder(monkeypatch, tmp_path):
    cache_file = tmp_path / ".vision_cache.json"
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", cache_file)
    from scripts import config
    monkeypatch.setattr(config, "get_gemini_api_keys", lambda: [])
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")

    catalog = GeminiVisionMatcher.index_raw_video_catalog(str(raw), raw_duration=20.0)

    assert GeminiVisionMatcher.is_fallback_catalog(catalog)
    assert catalog["fallback_reason"] == "no_api_key"
    assert "API key" in GeminiVisionMatcher.fallback_reason_th(catalog)
    assert GeminiVisionMatcher.get_cached_catalog(str(raw)) is None  # the next scan retries


def test_a_real_catalog_is_not_a_placeholder():
    real = {"scenes": [{"id": 1}], "indexed_by": "gemini-2.5-flash"}
    assert not GeminiVisionMatcher.is_fallback_catalog(real)
    assert GeminiVisionMatcher.fallback_reason_th(real) == ""
    assert not GeminiVisionMatcher.is_fallback_catalog(None)


def test_scan_that_analysed_nothing_is_a_failure_with_the_reason():
    outcome = summarize_catalog_scan({}, {"a.mp4": "ยังไม่ได้ตั้งค่า Gemini API key", "b.mp4": "x"})
    assert outcome["ok"] is False
    assert "2 คลิป" in outcome["error"] and "API key" in outcome["error"]
    assert "สำเร็จ" not in outcome["step_label"].replace("ไม่สำเร็จ", "")


def test_partial_scan_counts_only_real_scenes_and_says_what_was_skipped():
    outcome = summarize_catalog_scan({"a.mp4": {"scenes_count": 7}}, {"b.mp4": "x"})
    assert outcome["ok"] is True and outcome["total_scenes"] == 7
    assert "1 คลิป รวม 7 ฉาก" in outcome["step_label"]
    assert "วิเคราะห์ไม่ได้ 1 คลิป" in outcome["step_label"]


def test_full_scan_label_is_unchanged():
    outcome = summarize_catalog_scan({"a.mp4": {"scenes_count": 4}, "b.mp4": {"scenes_count": 5}}, {})
    assert outcome == {"ok": True, "total_scenes": 9, "error": "", "step_label": "สแกนสำเร็จ 2 คลิป รวม 9 ฉาก"}
