"""Behavioral tests for scripts/motion_analyzer.py.

MotionAnalyzer feeds cut-boundary bias, punch-zoom intensity, and shot offset
decisions in scripts/pipeline.py, whose output (ai_matched_shots) is consumed
directly by scripts/video_editor.py's filter-graph construction. A bad value
here (NaN, an out-of-range score, a mismatched times/scores length) would
flow straight into that filter graph with only min/max clamps as a backstop.

All video fixtures are synthesized in-memory with OpenCV's VideoWriter and
written to tmp_path -- no real footage is used, and every clip is a couple of
frames at a tiny 160x284 analysis resolution so tests stay fast. The
module-level MOTION_CACHE_FILE binding (read from scripts.config at import
time) is monkeypatched directly on the motion_analyzer module -- patching
scripts.config alone would not affect the already-bound name.
"""
import json
import math

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from scripts import motion_analyzer as motion_analyzer_mod
from scripts.motion_analyzer import MotionAnalyzer


ANALYSIS_W = motion_analyzer_mod.ANALYSIS_WIDTH
ANALYSIS_H = motion_analyzer_mod.ANALYSIS_HEIGHT


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    """Redirect the motion cache to tmp_path so tests never touch or create
    02_Assets/.motion_cache.json in the real repo tree."""
    cache_file = tmp_path / ".motion_cache.json"
    monkeypatch.setattr(motion_analyzer_mod, "MOTION_CACHE_FILE", cache_file)
    return cache_file


def _make_video(path, frames, fps=30.0, w=ANALYSIS_W, h=ANALYSIS_H):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for f in frames:
        writer.write(f)
    writer.release()
    return path


def _static_frames(n, w=ANALYSIS_W, h=ANALYSIS_H, value=128):
    return [np.full((h, w, 3), value, dtype=np.uint8) for _ in range(n)]


def _moving_frames(n, w=ANALYSIS_W, h=ANALYSIS_H):
    """A white square sweeping left-to-right -- guarantees a real,
    non-trivial frame-to-frame difference for the analyzer to pick up."""
    frames = []
    for i in range(n):
        f = np.zeros((h, w, 3), dtype=np.uint8)
        x = (i * 5) % max(1, (w - 20))
        cv2.rectangle(f, (x, h // 4), (x + 20, h // 4 + 40), (255, 255, 255), -1)
        frames.append(f)
    return frames


def _finite_floats(values):
    return all(isinstance(v, float) and math.isfinite(v) for v in values)


# ---------------------------------------------------------------------------
# get_motion_scores: missing / no-file inputs
# ---------------------------------------------------------------------------

def test_get_motion_scores_returns_empty_for_none():
    assert MotionAnalyzer.get_motion_scores(None) == ([], [])


def test_get_motion_scores_returns_empty_for_missing_file(tmp_path):
    assert MotionAnalyzer.get_motion_scores(tmp_path / "missing.mp4") == ([], [])


def test_get_motion_scores_returns_empty_for_zero_length_clip(tmp_path):
    """A VideoWriter that never receives a frame still produces a (small,
    non-empty) container file on disk, but OpenCV cannot open it as a valid
    video -- this must degrade to ([], []), not raise, since pipeline.py
    treats that as 'no motion data'."""
    path = tmp_path / "zero_frames.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 30.0, (ANALYSIS_W, ANALYSIS_H))
    writer.release()
    assert path.exists()

    times, scores = MotionAnalyzer.get_motion_scores(path)
    assert times == []
    assert scores == []


def test_get_motion_scores_single_frame_clip_has_no_diff_pair(tmp_path):
    """A single-frame clip has nothing to diff against -- current behavior
    is an empty result, not a crash and not a fabricated score."""
    path = _make_video(tmp_path / "single_frame.mp4", _static_frames(1))
    times, scores = MotionAnalyzer.get_motion_scores(path)
    assert times == []
    assert scores == []


def test_get_motion_scores_clip_shorter_than_analysis_window(tmp_path):
    """SAMPLE_INTERVAL_SECONDS=0.25 at 30fps means frame_interval=8 frames.
    A 3-frame clip only ever samples frame index 0, so there's no second
    sample to diff against -- documents current behavior: empty result,
    not an error, and not a single-sample degenerate score."""
    path = _make_video(tmp_path / "short.mp4", _static_frames(3))
    times, scores = MotionAnalyzer.get_motion_scores(path)
    assert times == []
    assert scores == []


def test_get_motion_scores_no_motion_yields_zero_not_empty(tmp_path):
    """A clip long enough to sample twice, but with identical frames, must
    report an explicit zero motion score at that timestamp -- distinct from
    the 'too short to sample' case above, which returns no data at all."""
    path = _make_video(tmp_path / "static.mp4", _static_frames(10))
    times, scores = MotionAnalyzer.get_motion_scores(path)
    assert len(times) == len(scores) >= 1
    assert scores == [0.0] * len(scores)
    assert _finite_floats(times)


# ---------------------------------------------------------------------------
# get_motion_scores: real motion, numeric sanity
# ---------------------------------------------------------------------------

def test_get_motion_scores_moving_clip_is_finite_and_normalized(tmp_path):
    """Scores are normalized against this clip's own peak, so they must
    stay within [0, 1] and be finite -- an out-of-range or NaN score here
    would bias cut/zoom decisions in pipeline.py unpredictably."""
    path = _make_video(tmp_path / "moving.mp4", _moving_frames(20))
    times, scores = MotionAnalyzer.get_motion_scores(path)

    assert len(times) == len(scores) > 0
    assert _finite_floats(times)
    assert _finite_floats(scores)
    assert all(0.0 <= s <= 1.0 + 1e-9 for s in scores)
    # Scores are peak-normalized before the moving-average smoothing pass,
    # so the smoothed max can sit slightly under 1.0 -- assert it gets close
    # rather than requiring an exact peak, which the smoothing would blur.
    assert max(scores) > 0.9, "peak-normalized: max score should approach 1.0"
    assert times == sorted(times)


def test_get_motion_scores_caches_by_content_hash(tmp_path, monkeypatch):
    """Second call for the same file must be served from cache rather than
    re-decoding the clip -- verified by monkeypatching cv2.VideoCapture to
    fail loudly if invoked a second time."""
    path = _make_video(tmp_path / "moving.mp4", _moving_frames(10))

    first = MotionAnalyzer.get_motion_scores(path)
    assert first != ([], [])

    def _explode(*args, **kwargs):
        raise AssertionError("VideoCapture should not be invoked on a cache hit")

    monkeypatch.setattr(cv2, "VideoCapture", _explode)
    second = MotionAnalyzer.get_motion_scores(path)
    assert first == second


def test_get_motion_scores_cache_file_written_under_tmp_path(tmp_path, _isolate_cache):
    """Confirms the cache write lands in the monkeypatched location, not the
    real 02_Assets tree -- guards against polluting a real asset folder."""
    path = _make_video(tmp_path / "moving.mp4", _moving_frames(10))
    MotionAnalyzer.get_motion_scores(path)
    assert _isolate_cache.exists()
    data = json.loads(_isolate_cache.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) == 1


# ---------------------------------------------------------------------------
# segment_mean_score / nearest_trough
# ---------------------------------------------------------------------------

def test_segment_mean_score_none_when_no_data():
    assert MotionAnalyzer.segment_mean_score([], [], 0.0, 1.0) is None


def test_segment_mean_score_averages_values_in_window():
    times = [0.0, 0.25, 0.5, 0.75, 1.0]
    scores = [0.1, 0.2, 0.3, 0.4, 0.5]
    result = MotionAnalyzer.segment_mean_score(times, scores, 0.25, 0.75)
    assert result == pytest.approx((0.2 + 0.3) / 2)


def test_segment_mean_score_falls_back_to_nearest_when_window_empty():
    times = [0.0, 0.5, 1.0]
    scores = [0.1, 0.5, 0.9]
    result = MotionAnalyzer.segment_mean_score(times, scores, 0.24, 0.26)
    assert result == 0.1  # nearest to midpoint 0.25 is t=0.0


def test_nearest_trough_returns_lowest_motion_time_in_tolerance():
    times = [0.0, 0.25, 0.5, 0.75]
    scores = [0.9, 0.1, 0.8, 0.2]
    # within 0.3s of target=0.5: indices at t=0.25,0.5,0.75 -> lowest score at t=0.25
    result = MotionAnalyzer.nearest_trough(times, scores, target=0.5, tolerance=0.3)
    assert result == 0.25


def test_nearest_trough_none_when_no_candidates_in_range():
    times = [0.0, 0.5, 1.0]
    scores = [0.1, 0.2, 0.3]
    assert MotionAnalyzer.nearest_trough(times, scores, target=100.0, tolerance=0.1) is None


def test_nearest_trough_none_when_no_data():
    assert MotionAnalyzer.nearest_trough([], [], target=0.0, tolerance=1.0) is None
