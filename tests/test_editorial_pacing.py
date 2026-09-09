'''Deterministic contract tests for the isolated editorial pacing core.'''

import pytest

from scripts.editorial_pacing import (
    PacingPolicy,
    build_beat_candidates,
    build_pacing_plan,
    build_pacing_plan_from_cues,
    find_silence_gaps,
    normalize_words,
    resolve_pacing_boundaries,
)


def test_normalize_words_discards_bad_records_without_shifting_valid_times():
    words = normalize_words(
        [
            {'text': 'late', 'start': 2.0, 'end': 2.4},
            {'text': 'bad', 'start': 'nope', 'end': 3},
            {'text': 'negative', 'start': -0.2, 'end': 0.4},
            {'text': 'outside', 'start': 9, 'end': 10},
            {'text': 'reversed', 'start': 4, 'end': 3},
            {'text': 'early', 'start': 0.5, 'end': 0.9},
        ],
        duration=5,
    )

    assert [(word.text, word.start, word.end) for word in words] == [
        ('negative', 0.0, 0.4),
        ('early', 0.5, 0.9),
        ('late', 2.0, 2.4),
    ]


def test_silence_gaps_classify_short_pause_and_cut_candidate():
    words = normalize_words(
        [
            {'text': 'one', 'start': 0.0, 'end': 0.5},
            {'text': 'two', 'start': 0.8, 'end': 1.2},
            {'text': 'three', 'start': 2.0, 'end': 2.4},
        ],
        duration=3.0,
    )

    gaps = find_silence_gaps(words, duration=3.0)
    assert [(gap.start, gap.end, gap.kind) for gap in gaps] == [
        (0.5, 0.8, 'short_pause'),
        (1.2, 2.0, 'cut_candidate'),
        (2.4, 3.0, 'cut_candidate'),
    ]


def test_scene_boundary_inside_word_is_not_accepted_without_safe_boundary():
    words = normalize_words(
        [
            {'text': 'long', 'start': 0.0, 'end': 1.8},
            {'text': 'pause', 'start': 2.4, 'end': 2.8},
        ],
        duration=3.0,
    )

    beats = build_beat_candidates(words, scene_boundaries=[1.2, 1.82], duration=3.0)
    assert any(beat.reason == 'scene_boundary' and beat.timestamp == 1.8 for beat in beats)
    assert not any(beat.reason == 'scene_boundary' and beat.source_timestamp == 1.2 for beat in beats)


def test_interval_beats_are_deterministic_and_avoid_duplicate_scene_beats():
    words = normalize_words(
        [
            {'text': 'a', 'start': 0.0, 'end': 0.4},
            {'text': 'b', 'start': 2.0, 'end': 2.4},
            {'text': 'c', 'start': 4.4, 'end': 4.8},
        ],
        duration=5.0,
    )
    policy = PacingPolicy(target_beat_interval=2.2)

    first = build_pacing_plan(
        [{'text': word.text, 'start': word.start, 'end': word.end} for word in words],
        scene_boundaries=[2.0, 2.0, 'bad', 9],
        duration=5.0,
        policy=policy,
    )
    second = build_pacing_plan(
        [{'text': word.text, 'start': word.start, 'end': word.end} for word in words],
        scene_boundaries=[2.0, 2.0, 'bad', 9],
        duration=5.0,
        policy=policy,
    )

    assert first == second
    assert [beat['timestamp'] for beat in first['beats']] == [2.0, 4.4]
    assert all(beat['timestamp'] in {0.4, 2.0, 2.4, 4.4, 4.8, 5.0} for beat in first['beats'])


def test_empty_input_is_safe_and_serializable():
    assert build_pacing_plan([], duration=1.0) == {
        'words': [],
        'silence_gaps': [{'start': 0.0, 'end': 1.0, 'duration': 1.0, 'kind': 'cut_candidate'}],
        'beats': [],
        'cut_candidates': [{'start': 0.0, 'end': 1.0, 'duration': 1.0, 'kind': 'cut_candidate'}],
    }


def test_invalid_policy_is_rejected():
    with pytest.raises(ValueError):
        PacingPolicy(short_pause_min=0.8, cut_gap_min=0.5)


def test_cue_adapter_collects_absolute_word_timings_and_cue_boundaries():
    plan = build_pacing_plan_from_cues(
        [
            {
                'start': 0.0,
                'end': 1.5,
                'word_timings': [
                    {'text': 'one', 'start': 0.0, 'end': 0.35},
                    {'text': 'two', 'start': 0.95, 'end': 1.3},
                ],
            },
            {
                'start': 1.6,
                'end': 3.0,
                'word_timings': [
                    {'text': 'three', 'start': 1.7, 'end': 2.1},
                    {'text': 'four', 'start': 2.7, 'end': 2.95},
                ],
            },
        ],
        duration=3.0,
    )

    assert plan is not None
    assert [word['text'] for word in plan['words']] == ['one', 'two', 'three', 'four']
    assert plan['words'][2]['start'] == 1.7
    assert any(gap['kind'] == 'cut_candidate' for gap in plan['cut_candidates'])


def test_cue_adapter_is_noop_for_legacy_cues_without_word_timings():
    assert build_pacing_plan_from_cues(
        [{'start': 0.0, 'end': 2.0, 'text': 'legacy'}],
        duration=2.0,
    ) is None


def test_cue_adapter_ignores_malformed_word_timing_records():
    plan = build_pacing_plan_from_cues(
        [
            {
                'start': 0.0,
                'end': 2.0,
                'word_timings': [
                    {'text': '', 'start': 0.0, 'end': 0.3},
                    {'text': 'bad', 'start': 'x', 'end': 0.6},
                    {'text': 'valid', 'start': 0.4, 'end': 0.8},
                ],
            }
        ],
        duration=2.0,
    )

    assert plan is not None
    assert [word['text'] for word in plan['words']] == ['valid']


def test_resolve_pacing_boundaries_is_conservative_and_deterministic():
    plan = {'beats': [{'timestamp': 4.0}, {'timestamp': 2.0}, {'timestamp': 2.0}]}

    assert resolve_pacing_boundaries(plan, duration=6.0, min_segment_duration=1.0) == [0.0, 2.0, 4.0, 6.0]
    assert resolve_pacing_boundaries({'beats': [{'timestamp': 0.3}]}, duration=2.0, min_segment_duration=1.0) is None
    assert resolve_pacing_boundaries({'beats': [{'timestamp': 'bad'}]}, duration=2.0) is None
    assert resolve_pacing_boundaries(None, duration=2.0) is None
