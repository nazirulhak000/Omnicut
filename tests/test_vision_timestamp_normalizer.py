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
    """Ensure _lookup_cached_matches applies MM.SS heuristic ONLY to catalog scans,
    never to direct Vision matches, and never writes back to cache during a read."""
    from copy import deepcopy
    from scripts.gemini_vision_matcher import GeminiVisionMatcher

    file_hash = "mock_hash_123"
    match_cache_key = "mock_hash_123_key_v2_1.50-2.50"
    cues = [{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}]

    # 1. Direct cached matches (no catalog scenes) must NOT apply MM.SS heuristic
    cache_direct = {
        "catalogs": {file_hash: {"duration": 85.0}},
        "matches": {
            match_cache_key: [
                {"cue_id": 1, "start_time": 1.18, "end_time": 1.38}
            ]
        }
    }
    direct_res = GeminiVisionMatcher._lookup_cached_matches(cache_direct, file_hash, match_cache_key, cues)
    assert direct_res is not None
    assert direct_res[0]["start_time"] == 1.18
    assert direct_res[0]["end_time"] == 1.38

    # 2. Cached catalog with legacy MM.SS scenes DOES normalize MM.SS
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
    snapshot = deepcopy(cache_catalog)
    cat_res = GeminiVisionMatcher._lookup_cached_matches(cache_catalog, file_hash, match_cache_key, cues)
    assert cat_res is not None
    assert cat_res[0]["scene_start"] == 5.0
    assert cat_res[0]["scene_end"] == 84.0
    assert cat_res[0]["start_time"] >= 5.0
    assert cache_catalog == snapshot


def test_normalize_scene_timestamps_a7_guards():
    """A7: reject >= .60 fractional MM.SS, clamp end <= raw_dur, respect allow_mmss_heuristic=False."""
    # 1. Fractional >= .60 (e.g. 1.75s) on a 300s video must stay 1.75s, NOT 135.0s!
    scenes_frac = [{"id": 1, "start": 0.0, "end": 1.75}]
    norm_frac = normalize_scene_timestamps(scenes_frac, raw_duration=300.0, allow_mmss_heuristic=True)
    assert norm_frac[0]["end"] == 1.75

    # 1b. Early shots ending < 15s on a 300s video (e.g. 14.0s > expected_mmss*1.15=5.75) stay real seconds
    scenes_early = [{"id": 1, "start": 2.0, "end": 14.0}]
    norm_early = normalize_scene_timestamps(scenes_early, raw_duration=300.0, allow_mmss_heuristic=True)
    assert norm_early[0]["start"] == 2.0
    assert norm_early[0]["end"] == 14.0

    # 2. allow_mmss_heuristic=False keeps direct Vision timestamps even if < 0.60
    scenes_direct = [{"cue_id": 1, "start_time": 0.15, "end_time": 1.24}]
    norm_direct = normalize_scene_timestamps(scenes_direct, raw_duration=85.0, allow_mmss_heuristic=False)
    assert norm_direct[0]["start_time"] == 0.15
    assert norm_direct[0]["end_time"] == 1.24

    # 3. end is strictly clamped <= raw_duration even when raw start >= raw_duration
    scenes_over = [{"id": 1, "start": 65.0, "end": 70.0}]
    norm_over = normalize_scene_timestamps(scenes_over, raw_duration=60.0)
    assert norm_over[0]["end"] <= 60.0
    assert norm_over[0]["start"] < norm_over[0]["end"]


def test_get_cached_catalog_skips_missing_duration_and_never_writes_cache(tmp_path, monkeypatch):
    """A7: get_cached_catalog skips normalization if duration is missing and never calls save."""
    from scripts.gemini_vision_matcher import GeminiVisionMatcher, VisionRequestContext

    fake_video = tmp_path / "raw.mp4"
    fake_video.write_bytes(b"00")
    scenes = [{"id": 1, "start": 0.05, "end": 1.24}]
    ctx_no_dur = VisionRequestContext(
        video_file=fake_video,
        file_hash="h1",
        cache={"catalogs": {"h1": {"scenes": [dict(s) for s in scenes]}}},
    )
    monkeypatch.setattr(
        GeminiVisionMatcher,
        "save_cached_catalog",
        classmethod(lambda cls, *a, **k: (_ for _ in ()).throw(AssertionError("read must not write cache"))),
    )
    cat_no_dur = GeminiVisionMatcher.get_cached_catalog(str(fake_video), request_context=ctx_no_dur)
    assert cat_no_dur["scenes"][0]["end"] == 1.24  # skipped when duration missing

    ctx_with_dur = VisionRequestContext(
        video_file=fake_video,
        file_hash="h2",
        cache={"catalogs": {"h2": {"duration": 85.0, "scenes": [dict(s) for s in scenes]}}},
    )
    cat_with_dur = GeminiVisionMatcher.get_cached_catalog(str(fake_video), request_context=ctx_with_dur)
    assert cat_with_dur["scenes"][0]["start"] == 5.0
    assert cat_with_dur["scenes"][0]["end"] == 84.0


def test_end_to_end_matcher_coalesce_and_ledger_no_excess_freeze_or_hold_only():
    """A1 + A6 end-to-end deterministic pipeline:
    match_script_with_catalog -> coalesce_short_windows -> _split_groups -> SourceWindowLedger
    must keep freeze_tail <= 1.0s, avoid hold_only when adjacent footage exists,
    and split shared windows to <= SHOT_CAP."""
    from scripts.gemini_vision_matcher import GeminiVisionMatcher
    from scripts.shot_source_window import SourceWindowLedger, coalesce_short_windows
    from scripts.stages.shot_matching_stage import _split_groups, _plan_split_points

    raw_duration = 30.0
    shot_cap = 3.125
    max_shot = 2.5

    # Case 1: 5s scene (10..15s) shared across 2x3s cues (6s total) -> 0s freeze via adjacent footage
    # Case 2: 4s scene (20..24s) shared across 3x2s cues (6s total) -> split & adjacent, freeze_tail <= 1.0
    catalog = {
        "scenes": [
            {"id": 1, "start": 10.0, "end": 15.0, "keywords": ["ชาร์จ"], "action_type": "port_connection", "description": "ชาร์จไว"},
            {"id": 2, "start": 20.0, "end": 24.0, "keywords": ["แม่เหล็ก"], "action_type": "feature_demo", "description": "แม่เหล็กประกบ"},
        ]
    }
    cues = [
        {"start": 0.0, "end": 3.0, "text": "ชาร์จไวมาก."},
        {"start": 3.0, "end": 6.0, "text": "ชาร์จเข้าเร็ว."},
        {"start": 6.0, "end": 8.0, "text": "แม่เหล็กดูดแน่น."},
        {"start": 8.0, "end": 10.0, "text": "แม่เหล็กประกบง่าย."},
        {"start": 10.0, "end": 12.0, "text": "แม่เหล็กจัดเก็บสะดวก."},
    ]

    matches = GeminiVisionMatcher.match_script_with_catalog(catalog, cues, raw_duration=raw_duration)
    assert len(matches) == 5

    # Group into per-cue groups (as ShotMatchingStage builds before coalescing)
    groups = [[i] for i in range(len(cues))]
    boundaries = [0.0] + [c["end"] for c in cues]
    onsets = [None] + [c["start"] for c in cues[1:]] + [None]

    overrides = {}
    exhausted = set()
    c_groups, c_times, c_onsets = coalesce_short_windows(
        groups, boundaries, onsets, matches, raw_duration,
        max_hold=1.0, overrides=overrides, exhausted=exhausted,
    )

    split_candidates = [(boundaries[i], cues[i]["start"]) for i in range(1, len(cues))]
    s_groups, s_times, _ = _split_groups(
        c_groups, c_times, c_onsets,
        lambda s, e: _plan_split_points(s, e, lambda _t: max_shot, split_candidates) if e - s > shot_cap + 1e-6 else [],
        skip_ids=exhausted,
    )

    ledger = SourceWindowLedger()
    for idx, grp in enumerate(s_groups):
        dur = s_times[idx + 1] - s_times[idx]
        if id(grp) not in exhausted:
            assert dur <= shot_cap + 1e-6, f"Shot {idx} exceeded SHOT_CAP: {dur}"
        match = overrides[id(grp)][1] if id(grp) in overrides else matches[grp[0]]
        alloc = ledger.allocate(match, raw_duration, match["start_time"], dur)
        assert alloc is not None
        assert alloc["freeze_tail"] <= 1.0 + 1e-6, f"Shot {idx} froze {alloc['freeze_tail']}s > 1.0s"
        assert alloc["hold_only"] is False, f"Shot {idx} hit hold_only despite adjacent footage!"


def test_a6_shared_window_within_hold_budget_is_still_split_to_shot_cap():
    """A6: 3 cues sharing a 5s window over 5.9s (fits 1.0s hold) must be split <= SHOT_CAP."""
    from scripts.shot_source_window import coalesce_short_windows
    from scripts.stages.shot_matching_stage import _split_groups, _plan_split_points

    shared_match = {"cue_ids": [1, 2, 3], "start_time": 10.0, "end_time": 15.0, "scene_start": 10.0, "scene_end": 15.0}
    matches = [shared_match, shared_match, shared_match]
    overrides, exhausted = {}, set()
    c_groups, c_times, c_onsets = coalesce_short_windows(
        [[0], [1], [2]], [0.0, 2.0, 4.0, 5.9], [None, 2.0, 4.0, None],
        matches, raw_duration=60.0, max_hold=1.0, overrides=overrides, exhausted=exhausted,
    )
    assert not exhausted
    s_groups, s_times, _ = _split_groups(
        c_groups, c_times, c_onsets,
        lambda s, e: _plan_split_points(s, e, lambda _t: 2.5, [(2.0, 2.0), (4.0, 4.0)]) if e - s > 3.125 + 1e-6 else [],
        skip_ids=exhausted,
    )
    assert len(s_groups) == 3
    assert s_times == [0.0, 2.0, 4.0, 5.9]

