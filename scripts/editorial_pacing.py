'''Deterministic pacing primitives for the Professional Editing Style System.

Phase 2A only normalizes existing timing data and returns inspectable
candidates. It has no FastAPI, FFmpeg, filesystem, or AI dependency and does
not change the existing render flow.
'''

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class PacingPolicy:
    short_pause_min: float = 0.25
    cut_gap_min: float = 0.55
    target_beat_interval: float = 2.2
    min_beat_interval: float = 1.5
    max_beat_interval: float = 3.0
    boundary_tolerance: float = 0.12

    def __post_init__(self) -> None:
        if self.short_pause_min < 0:
            raise ValueError('short_pause_min ต้องไม่ติดลบ')
        if self.cut_gap_min < self.short_pause_min:
            raise ValueError('cut_gap_min ต้องไม่น้อยกว่า short_pause_min')
        if not 0 < self.min_beat_interval <= self.target_beat_interval <= self.max_beat_interval:
            raise ValueError('beat interval ต้องเรียง min <= target <= max และมากกว่า 0')
        if self.boundary_tolerance < 0:
            raise ValueError('boundary_tolerance ต้องไม่ติดลบ')


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float
    source_index: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SilenceGap:
    start: float
    end: float
    duration: float
    kind: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BeatCandidate:
    timestamp: float
    reason: str
    source_timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_words(
    words: Optional[Iterable[Mapping[str, Any]]],
    duration: Optional[float] = None,
) -> List[TimedWord]:
    '''Normalize valid word records without moving valid timestamps.'''

    limit = _number(duration) if duration is not None else None
    if limit is not None and limit <= 0:
        limit = None
    normalized: List[TimedWord] = []
    for index, raw in enumerate(words or []):
        if not isinstance(raw, Mapping):
            continue
        text = str(raw.get('text') or raw.get('word') or '').strip()
        start = _number(raw.get('start', raw.get('start_time')))
        end = _number(raw.get('end', raw.get('end_time')))
        if not text or start is None or end is None:
            continue
        start = max(0.0, start)
        if limit is not None:
            if start >= limit:
                continue
            end = min(limit, end)
        if end <= start:
            continue
        normalized.append(TimedWord(text, start, end, index))
    return sorted(normalized, key=lambda item: (item.start, item.end, item.source_index))


def find_silence_gaps(
    words: Sequence[TimedWord],
    duration: Optional[float] = None,
    policy: PacingPolicy = PacingPolicy(),
) -> List[SilenceGap]:
    '''Find word-free pauses and classify them as pause or cut candidates.'''

    if not words:
        limit = _number(duration) if duration is not None else None
        if limit is not None and limit >= policy.cut_gap_min:
            return [SilenceGap(0.0, limit, limit, 'cut_candidate')]
        return []

    ranges: List[Tuple[float, float]] = []
    if words[0].start >= policy.short_pause_min:
        ranges.append((0.0, words[0].start))
    for previous, current in zip(words, words[1:]):
        start, end = max(0.0, previous.end), current.start
        if end - start >= policy.short_pause_min:
            ranges.append((start, end))
    limit = _number(duration) if duration is not None else None
    if limit is not None and limit - words[-1].end >= policy.short_pause_min:
        ranges.append((words[-1].end, limit))

    result: List[SilenceGap] = []
    for start, end in ranges:
        gap_duration = end - start
        kind = 'cut_candidate' if gap_duration >= policy.cut_gap_min else 'short_pause'
        result.append(SilenceGap(start, end, gap_duration, kind))
    return result


def _safe_points(gaps: Sequence[SilenceGap]) -> List[float]:
    points = {round(point, 6) for gap in gaps for point in (gap.start, gap.end)}
    return sorted(points)


def _snap_to_safe_point(value: float, points: Sequence[float], tolerance: float) -> Optional[float]:
    if not points:
        return None
    nearest = min(points, key=lambda point: (abs(point - value), point))
    return nearest if abs(nearest - value) <= tolerance else None


def build_beat_candidates(
    words: Sequence[TimedWord],
    scene_boundaries: Optional[Iterable[Any]] = None,
    duration: Optional[float] = None,
    policy: PacingPolicy = PacingPolicy(),
) -> List[BeatCandidate]:
    '''Build scene and interval beats snapped to safe word boundaries.'''

    gaps = find_silence_gaps(words, duration, policy)
    points = _safe_points(gaps)
    limit = _number(duration) if duration is not None else None
    candidates: Dict[float, BeatCandidate] = {}

    boundaries: List[float] = []
    for raw in scene_boundaries or []:
        value = _number(raw)
        if value is None or value <= 0 or (limit is not None and value >= limit):
            continue
        boundaries.append(value)
    for boundary in sorted(set(boundaries)):
        snapped = _snap_to_safe_point(boundary, points, policy.boundary_tolerance)
        if snapped is not None and snapped > 0 and (limit is None or snapped < limit):
            candidates[snapped] = BeatCandidate(snapped, 'scene_boundary', boundary)

    if points:
        cursor = 0.0
        while True:
            target = cursor + policy.target_beat_interval
            options = [
                point for point in sorted(set(points) | set(candidates))
                if point >= cursor + policy.min_beat_interval
                and point <= cursor + policy.max_beat_interval
                and (limit is None or point < limit)
            ]
            if not options:
                break
            chosen = min(
                options,
                key=lambda point: (
                    round(abs(point - target), 6),
                    0 if point in candidates else 1,
                    point,
                ),
            )
            if chosen <= cursor:
                break
            candidates.setdefault(chosen, BeatCandidate(chosen, 'interval', target))
            cursor = chosen

    return [candidates[key] for key in sorted(candidates)]


def build_pacing_plan(
    words: Optional[Iterable[Mapping[str, Any]]],
    scene_boundaries: Optional[Iterable[Any]] = None,
    duration: Optional[float] = None,
    policy: PacingPolicy = PacingPolicy(),
) -> Dict[str, Any]:
    '''Return the serializable Phase 2A pacing contract.'''

    normalized = normalize_words(words, duration)
    gaps = find_silence_gaps(normalized, duration, policy)
    beats = build_beat_candidates(normalized, scene_boundaries, duration, policy)
    return {
        'words': [word.to_dict() for word in normalized],
        'silence_gaps': [gap.to_dict() for gap in gaps],
        'beats': [beat.to_dict() for beat in beats],
        'cut_candidates': [gap.to_dict() for gap in gaps if gap.kind == 'cut_candidate'],
    }


def build_pacing_plan_from_cues(
    cues: Optional[Iterable[Mapping[str, Any]]],
    duration: Optional[float] = None,
    scene_boundaries: Optional[Iterable[Any]] = None,
    policy: PacingPolicy = PacingPolicy(),
) -> Optional[Dict[str, Any]]:
    '''Adapt pre-subtitle sentence cues into the pacing contract.

    VoiceStage attaches absolute ``word_timings`` to sentence cues.  This
    adapter deliberately returns ``None`` when that optional data is absent,
    so legacy projects remain a no-op instead of receiving a synthetic
    full-duration cut candidate.
    '''

    cue_list = [cue for cue in (cues or []) if isinstance(cue, Mapping)]
    word_records: List[Mapping[str, Any]] = []
    cue_boundaries: List[float] = []
    duration_value = _number(duration) if duration is not None else None

    for cue in cue_list:
        timings = cue.get('word_timings')
        if isinstance(timings, Iterable) and not isinstance(timings, (str, bytes, Mapping)):
            word_records.extend(item for item in timings if isinstance(item, Mapping))

        for key in ('start', 'end'):
            value = _number(cue.get(key))
            if value is not None and value > 0:
                cue_boundaries.append(value)
                if duration_value is None:
                    duration_value = max(duration_value or 0.0, value)

    normalized = normalize_words(word_records, duration_value)
    if not normalized:
        return None

    if duration_value is None:
        duration_value = max(word.end for word in normalized)

    boundaries = list(scene_boundaries or [])
    boundaries.extend(cue_boundaries)
    return build_pacing_plan(
        [word.to_dict() for word in normalized],
        scene_boundaries=boundaries,
        duration=duration_value,
        policy=policy,
    )


def resolve_pacing_boundaries(
    plan: Optional[Mapping[str, Any]],
    duration: Optional[float],
    min_segment_duration: float = 0.2,
) -> Optional[List[float]]:
    '''Return safe timeline boundaries from a persisted pacing plan.

    The resolver is intentionally conservative: malformed plans, missing
    beats, non-positive durations, and beats that would create a tiny segment
    all return ``None`` so the caller can keep its legacy grouping path.
    '''

    limit = _number(duration)
    minimum = _number(min_segment_duration)
    if limit is None or limit <= 0 or minimum is None or minimum <= 0:
        return None
    if not isinstance(plan, Mapping):
        return None

    timestamps: List[float] = []
    raw_beats = plan.get('beats')
    if not isinstance(raw_beats, Iterable) or isinstance(raw_beats, (str, bytes, Mapping)):
        return None
    for raw_beat in raw_beats:
        value = _number(raw_beat.get('timestamp') if isinstance(raw_beat, Mapping) else raw_beat)
        if value is not None and minimum <= value < limit - minimum:
            timestamps.append(round(value, 6))

    points = sorted(set([0.0, limit, *timestamps]))
    if len(points) < 3 or any((right - left) < minimum for left, right in zip(points, points[1:])):
        return None
    return points


__all__ = [
    'BeatCandidate',
    'PacingPolicy',
    'SilenceGap',
    'TimedWord',
    'build_beat_candidates',
    'build_pacing_plan',
    'build_pacing_plan_from_cues',
    'find_silence_gaps',
    'normalize_words',
    'resolve_pacing_boundaries',
]
