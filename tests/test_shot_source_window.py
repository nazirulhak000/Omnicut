import pytest
from scripts.shot_source_window import source_window, allocate_window, coalesce_short_windows


def test_scene_end_and_raw_end_limit_the_selected_window():
    assert source_window({"start_time": 2, "end_time": 8, "scene_end": 4}, 10) == (60, 120)
    assert source_window({"start_time": 2, "end_time": 8}, 5) == (60, 150)
    assert source_window({"start_time": 2}, 5) is None


@pytest.mark.parametrize("start", [2, 3, 4, 8])
def test_allocation_never_crosses_window_and_keeps_program_duration(start):
    result = allocate_window((60, 120), start, 6)
    assert result["raw_offset"] >= 2
    assert result["source_end"] <= 4
    assert result["source_end"] > result["raw_offset"]
    assert result["source_end"] - result["raw_offset"] + result["freeze_tail"] == pytest.approx(6)
    if start >= 4:
        assert result["raw_offset"] == pytest.approx(4 - 1 / 30, abs=1e-6)


def test_short_shared_window_merges_but_distinct_topics_remain_separate():
    a = {"start_time": 10, "end_time": 13}
    b = {"start_time": 30, "end_time": 35}
    groups, times, onsets = coalesce_short_windows([[0], [1], [2]], [0, 2, 4, 6],
                                                  [None, 2, 4, None], [a, a, b], 60)
    assert groups == [[0, 1], [2]]
    assert times == [0, 4, 6]
    assert onsets == [None, 4, None]


def test_catalog_does_not_expand_short_scene_or_shift_into_previous_topic():
    from scripts.gemini_vision_matcher import GeminiVisionMatcher
    scene = {"id": 1, "start": 2, "end": 2.1, "description": "USB-C", "keywords": ["USB-C"]}
    result = GeminiVisionMatcher.match_script_with_catalog(
        {"scenes": [scene]}, [{"start": 0, "end": 8, "text": "USB-C"}], raw_duration=10)
    assert result[0]["start_time"] >= 2
    assert result[0]["end_time"] <= 2.1
    assert result[0]["scene_end"] == 2.1


def test_old_catalog_match_gets_real_scene_end_without_mutating_cache():
    from scripts.gemini_vision_matcher import GeminiVisionMatcher
    cached = [{"scene_id": 1, "start_time": 2, "end_time": 3.8}]
    result = GeminiVisionMatcher._bind_catalog_windows(cached, {"scenes": [{"id": 1, "start": 2, "end": 2.1}]})
    assert result[0]["end_time"] == 2.1
    assert result[0]["scene_end"] == 2.1
    assert cached[0]["end_time"] == 3.8
