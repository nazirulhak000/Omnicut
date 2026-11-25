"""Unit tests for Gemini Vision Matcher timestamp parsing and normalizer."""

import pytest
from scripts.gemini_vision_matcher import (
    parse_timestamp_seconds,
    normalize_scene_timestamps,
)


def test_parse_timestamp_seconds_numeric():
    assert parse_timestamp_seconds(0) == 0.0
    assert parse_timestamp_seconds(12.5) == 12.5
    assert parse_timestamp_seconds(84.71) == 84.71
    assert parse_timestamp_seconds(None) is None
    assert parse_timestamp_seconds(float("nan")) is None


def test_parse_timestamp_seconds_strings():
    assert parse_timestamp_seconds("5.0") == 5.0
    assert parse_timestamp_seconds("15.5s") == 15.5
    assert parse_timestamp_seconds("15.5sec") == 15.5
    assert parse_timestamp_seconds("0:05") == 5.0
    assert parse_timestamp_seconds("01:24") == 84.0
    assert parse_timestamp_seconds("01:04.5") == 64.5
    assert parse_timestamp_seconds("00:01:24") == 84.0
    assert parse_timestamp_seconds("invalid") is None


def test_normalize_scene_timestamps_normal_seconds():
    scenes = [
        {"id": 1, "start": 0.0, "end": 5.0, "action_type": "overview"},
        {"id": 2, "start": 5.0, "end": 12.0, "action_type": "closeup"},
        {"id": 3, "start": 12.0, "end": 20.0, "action_type": "hands_on"},
    ]
    norm = normalize_scene_timestamps(scenes, raw_duration=25.0)
    assert len(norm) == 3
    assert norm[0]["start"] == 0.0
    assert norm[0]["end"] == 5.0
    assert norm[1]["start"] == 5.0
    assert norm[1]["end"] == 12.0
    assert norm[2]["start"] == 12.0
    assert norm[2]["end"] == 20.0


def test_normalize_scene_timestamps_mmss_compression_bug():
    """Reproduce TRANYOO GS-01 IMG_8207.MOV bug where Gemini returned 0.05..1.24 for 84.7s video."""
    corrupted_scenes = [
        {"id": 1, "start": 0.0, "end": 0.05, "action_type": "overview"},
        {"id": 2, "start": 0.05, "end": 0.11, "action_type": "closeup"},
        {"id": 3, "start": 0.11, "end": 0.17, "action_type": "unboxing"},
        {"id": 4, "start": 0.17, "end": 0.24, "action_type": "unboxing"},
        {"id": 5, "start": 0.24, "end": 0.30, "action_type": "unboxing"},
        {"id": 6, "start": 0.30, "end": 0.37, "action_type": "hands_on"},
        {"id": 7, "start": 0.37, "end": 0.44, "action_type": "feature_demo"},
        {"id": 8, "start": 0.44, "end": 0.50, "action_type": "hands_on"},
        {"id": 9, "start": 0.50, "end": 0.57, "action_type": "feature_demo"},
        {"id": 10, "start": 0.57, "end": 1.04, "action_type": "feature_demo"},
        {"id": 11, "start": 1.04, "end": 1.11, "action_type": "feature_demo"},
        {"id": 12, "start": 1.11, "end": 1.18, "action_type": "hands_on"},
        {"id": 13, "start": 1.18, "end": 1.24, "action_type": "closeup"},
    ]
    raw_duration = 84.71
    norm = normalize_scene_timestamps(corrupted_scenes, raw_duration=raw_duration)

    assert len(norm) == 13
    # Scene 1: 0 to 5s
    assert norm[0]["start"] == 0.0
    assert norm[0]["end"] == 5.0
    # Scene 2: 5 to 11s
    assert norm[1]["start"] == 5.0
    assert norm[1]["end"] == 11.0
    # Scene 10: 57s to 64s (1:04)
    assert norm[9]["start"] == 57.0
    assert norm[9]["end"] == 64.0
    # Scene 11: 64s to 71s (1:11)
    assert norm[10]["start"] == 64.0
    assert norm[10]["end"] == 71.0
    # Scene 13: 78s to 84s (1:24)
    assert norm[12]["start"] == 78.0
    assert norm[12]["end"] == 84.0

    # Ensure every scene is at least 4s long and covers up to 84s
    assert max(s["end"] for s in norm) == 84.0
    assert all(s["end"] > s["start"] for s in norm)


def test_normalize_scene_timestamps_string_colons():
    string_scenes = [
        {"id": 1, "start": "0:00", "end": "0:06", "action_type": "overview"},
        {"id": 2, "start": "0:06", "end": "0:15", "action_type": "closeup"},
        {"id": 3, "start": "0:15", "end": "1:05", "action_type": "hands_on"},
    ]
    norm = normalize_scene_timestamps(string_scenes, raw_duration=70.0)
    assert len(norm) == 3
    assert norm[0]["start"] == 0.0
    assert norm[0]["end"] == 6.0
    assert norm[1]["start"] == 6.0
    assert norm[1]["end"] == 15.0
    assert norm[2]["start"] == 15.0
    assert norm[2]["end"] == 65.0


def test_lookup_cached_matches_normalizes_legacy_mmss_timestamps():
    """Ensure _lookup_cached_matches normalizes legacy MM.SS timestamps from cache."""
    from scripts.gemini_vision_matcher import GeminiVisionMatcher

    file_hash = "mock_hash_123"
    match_cache_key = "mock_hash_123_key_v2_1.50-2.50"
    cues = [{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}]

    # 1. Direct cached matches with legacy MM.SS (e.g. 1.24 meaning 84.0s on 85s video)
    cache_direct = {
        "catalogs": {file_hash: {"duration": 85.0}},
        "matches": {
            match_cache_key: [
                {"cue_id": 1, "start_time": 1.18, "end_time": 1.24}
            ]
        }
    }
    direct_res = GeminiVisionMatcher._lookup_cached_matches(cache_direct, file_hash, match_cache_key, cues)
    assert direct_res is not None
    assert direct_res[0]["start_time"] == 78.0
    assert direct_res[0]["end_time"] == 84.0

    # 2. Cached catalog with legacy MM.SS scenes
    cache_catalog = {
        "catalogs": {
            file_hash: {
                "duration": 85.0,
                "scenes": [
                    {"id": 1, "start": 0.05, "end": 1.24, "action_type": "closeup", "description": "ทดสอบ"}
                ]
            }
        },
        "matches": {
            match_cache_key: [
                {"cue_ids": [1], "scene_id": 1, "start_time": 0.05, "end_time": 1.24}
            ]
        }
    }
    cat_res = GeminiVisionMatcher._lookup_cached_matches(cache_catalog, file_hash, match_cache_key, cues)
    assert cat_res is not None
    # Scene should be normalized from 0.05..1.24 to 5.0..84.0s
    assert cat_res[0]["scene_start"] == 5.0
    assert cat_res[0]["scene_end"] == 84.0
    assert cat_res[0]["start_time"] >= 5.0


def test_match_script_with_catalog_rotates_when_keyword_scene_exhausted():
    """When a single keyword scene is exhausted (<0.35s remaining and cannot rewind),
    it must rotate to fallback scenes instead of collapsing to 1-frame 0.033s."""
    from scripts.gemini_vision_matcher import GeminiVisionMatcher

    catalog = {
        "scenes": [
            # Scene 0: only 2.0s long! Cannot cover a 3.0s cue or rewind to cover multiple 3.0s cues.
            {"id": 0, "start": 0.0, "end": 2.0, "keywords": ["USB-C"], "action_type": "closeup", "description": "USB-C port"},
            # Fallback scenes with plenty of footage
            {"id": 1, "start": 10.0, "end": 20.0, "keywords": ["overview"], "action_type": "overview", "description": "Product body"},
            {"id": 2, "start": 20.0, "end": 30.0, "keywords": ["hands_on"], "action_type": "hands_on", "description": "Using device"},
        ]
    }
    cues = [
        {"start": 0.0, "end": 3.0, "text": "USB-C charging."},
        {"start": 3.0, "end": 6.0, "text": "USB-C charging."},
        {"start": 6.0, "end": 9.0, "text": "USB-C charging."},
    ]
    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, cues, raw_duration=30.0)
    assert len(matches) == 3
    # First match uses keyword scene 0
    assert matches[0]["scene_id"] == 0
    # Second and third matches must NOT collapse onto exhausted scene 0 with 0.033s!
    # They must rotate to fallback scenes (1 or 2)
    assert matches[1]["scene_id"] != 0
    assert matches[2]["scene_id"] != 0
    # Every match must have viable playable duration (> 0.35s)
    for m in matches:
        playable = m["end_time"] - m["start_time"]
        assert playable >= 0.35


def test_split_groups_never_slices_exhausted_window_into_hold_only():
    """_split_groups must never split a group into sub-clips where a sub-clip gets <= 0.11s playable footage."""
    from scripts.stages.shot_matching_stage import _split_groups

    # Setup: 1 group spanning 0.0 to 4.0s (longer than SHOT_CAP 3.0s)
    # But assigned source match only has 2.0s of footage!
    groups = [[0]]
    boundary_times = [0.0, 4.0]
    boundary_onsets = [None, 0.0]

    matches = [{
        "cue_ids": [0],
        "start_time": 5.0,
        "end_time": 7.0,  # Only 2.0s source span!
        "scene_start": 5.0,
        "scene_end": 7.0,
    }]

    # Split fn wants to split at 2.0s:
    split_fn = lambda s, e: [(2.0, 2.0)]

    out_groups, out_times, out_onsets = _split_groups(
        groups, boundary_times, boundary_onsets, split_fn,
        skip_ids=frozenset(), matches=matches, raw_duration=10.0, min_subclip_sec=0.5
    )
    # Because source_span (2.0s) < group_dur (4.0s) - 0.1, splitting is skipped!
    assert len(out_groups) == 1
    assert out_times == [0.0, 4.0]
