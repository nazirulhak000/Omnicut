"""Visual variety must not outrank the feature the narration describes."""
from copy import deepcopy
import hashlib
import pytest

from scripts.gemini_vision_matcher import GeminiVisionMatcher


def _scene(index, keyword, angle="front", description=None):
    return {"id": index, "start": index * 10, "end": index * 10 + 8,
            "action_type": "closeup", "angle_phase": angle,
            "description": description or keyword, "keywords": [keyword], "punch_zoom": 1.1}


def _cues(text, count=4):
    return [{"start": i * 3, "end": i * 3 + 3, "text": text + "."} for i in range(count)]


def test_repeated_feature_stays_relevant_despite_repeat_penalties():
    catalog = {"scenes": [_scene(0, "USB-C", "macro_closeup"),
                          _scene(1, "screen"), _scene(2, "logo"), _scene(3, "box")]}
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, _cues("USB-C charging"), 40)
    assert [m["scene_id"] for m in matches] == [0] * 4


def test_variety_uses_only_relevant_alternatives():
    catalog = {"scenes": [_scene(0, "USB-C", "macro_closeup"), _scene(1, "USB-C", "side"),
                          _scene(2, "screen"), _scene(3, "logo")]}
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, _cues("USB-C charging"), 40)
    chosen = [m["scene_id"] for m in matches]
    assert set(chosen) == {0, 1}
    assert all(a != b for a, b in zip(chosen, chosen[1:]))


def test_description_evidence_survives_missing_scene_keywords():
    relevant = _scene(0, "", "macro_closeup", "เสียบสายเข้าพอร์ต USB-C")
    relevant["keywords"] = []
    catalog = {"scenes": [relevant, _scene(1, "logo"), _scene(2, "box")]}
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, _cues("เสียบพอร์ต USB-C"), 30)
    assert [m["scene_id"] for m in matches] == [0] * 4


def test_no_feature_evidence_keeps_visual_variety_fallback():
    catalog = {"scenes": [_scene(0, "USB-C"), _scene(1, "screen", "side"), _scene(2, "logo", "45deg")]}
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, _cues("A great product"), 30)
    assert len({m["scene_id"] for m in matches}) == 3


@pytest.mark.parametrize("keyword", ["คมชัด", "ใส"])
@pytest.mark.parametrize("in_keywords", [True, False])
def test_broad_quality_words_cannot_lock_a_logo_over_the_actual_feature(keyword, in_keywords):
    hero = _scene(0, keyword, "macro_closeup", f"โลโก้ {keyword}")
    if not in_keywords:
        hero["keywords"] = []
    feature = _scene(1, "USB-C", "side")
    matches = GeminiVisionMatcher.match_script_with_catalog({"scenes": [hero, feature]}, _cues(f"USB-C เสียง{keyword}"), 30)
    assert [item["scene_id"] for item in matches] == [1] * 4
    assert all(keyword not in item["selection_evidence"] for item in matches)


def test_cached_catalog_rematches_old_choices_without_cache_write_or_api(tmp_path, monkeypatch):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"synthetic identity; never decoded")
    cues = _cues("USB-C charging")
    catalog = {"scenes": [_scene(0, "USB-C"), _scene(1, "logo")]}
    key = "source_" + hashlib.md5("|".join(c["text"] for c in cues).encode()).hexdigest()
    old = [{"scene_id": i % 2, "cue_ids": [i + 1], "start_time": (i % 2) * 10,
            "end_time": (i % 2) * 10 + 8} for i in range(4)]
    cache = {"catalogs": {"source": catalog}, "matches": {key: old}}
    before = deepcopy(cache)
    monkeypatch.setattr(GeminiVisionMatcher, "_compute_file_hash", lambda _: "source")
    monkeypatch.setattr(GeminiVisionMatcher, "_load_cache", lambda: cache)
    monkeypatch.setattr(GeminiVisionMatcher, "_save_cache", lambda _: (_ for _ in ()).throw(AssertionError("No cache write")))
    context = GeminiVisionMatcher.prepare_request_context(str(raw), cues)
    assert [m["scene_id"] for m in context.cached_matches] == [0] * 4
    assert all("usb-c" in m["selection_evidence"] for m in context.cached_matches)
    assert cache == before
    shorter = [{**cue, "start": i * .5, "end": i * .5 + .5} for i, cue in enumerate(cues)]
    refreshed = GeminiVisionMatcher.prepare_request_context(str(raw), shorter)
    assert len(refreshed.cached_matches) == 1
    assert refreshed.cached_matches[0]["cue_ids"] == [1, 2, 3, 4]
    # This path must hit the locally rematched plan before upload or budgeting.
    monkeypatch.setattr(GeminiVisionMatcher, "get_cached_catalog", lambda *a, **k: (_ for _ in ()).throw(AssertionError("No miss path")))
    assert GeminiVisionMatcher.match_script_to_video(str(raw), cues, request_context=context) == context.cached_matches


def test_direct_vision_cache_without_scene_ids_is_preserved(tmp_path, monkeypatch):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"synthetic identity")
    cues = _cues("USB-C charging", 1)
    key = "source_" + hashlib.md5(cues[0]["text"].encode()).hexdigest()
    matches = [{"cue_ids": [1], "start_time": 5, "end_time": 8}]
    cache = {"matches": {key: matches}, "catalogs": {"source": {"scenes": [_scene(0, "USB-C")]}}}
    monkeypatch.setattr(GeminiVisionMatcher, "_compute_file_hash", lambda _: "source")
    monkeypatch.setattr(GeminiVisionMatcher, "_load_cache", lambda: cache)
    assert GeminiVisionMatcher.prepare_request_context(str(raw), cues).cached_matches == matches
