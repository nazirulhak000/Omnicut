"""Audit S3-10 / S3-16: motion sample times follow the real frame timestamps
of variable-frame-rate footage, and parallel renders do not drop each
other's analysis-cache entries."""

import json
import shutil
import subprocess
import threading

import pytest

from scripts import motion_analyzer, script_tone_analyzer
from scripts.motion_analyzer import MotionAnalyzer

pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg is required"
)


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    cache = tmp_path / "motion_cache.json"
    monkeypatch.setattr(motion_analyzer, "MOTION_CACHE_FILE", cache)
    return cache


def _vfr_clip(path):
    """2 s at 30 fps followed by 2 s at 10 fps, one continuous timeline."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "testsrc=size=160x284:rate=30:duration=2",
         "-f", "lavfi", "-i", "testsrc=size=160x284:rate=10:duration=2",
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1[o]", "-map", "[o]",
         "-fps_mode", "vfr", "-c:v", "libx264", str(path)],
        check=True, capture_output=True,
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return [float(line.strip(",")) for line in probe.stdout.split() if line.strip(", ")]


def test_vfr_sample_times_match_ffprobe_pts(tmp_path, isolated_cache):
    pytest.importorskip("cv2")
    clip = tmp_path / "vfr.mp4"
    pts = _vfr_clip(clip)
    assert len(pts) == 80 and pts[-1] < 4.0

    times, scores = MotionAnalyzer.get_motion_scores(clip)

    assert times and len(times) == len(scores)
    for t in times:
        assert min(abs(t - p) for p in pts) <= 0.002, f"{t} is not a real frame time"
    assert times[-1] <= pts[-1] + 1e-3
    assert times == sorted(times)


def test_parallel_cache_writes_keep_every_entry(tmp_path, isolated_cache, monkeypatch):
    """Two renders analysing different raws at once both keep their entry."""
    pytest.importorskip("cv2")
    clips = []
    for name, pattern in (("a.mp4", "testsrc"), ("b.mp4", "rgbtestsrc")):
        clip = tmp_path / name
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
             "-i", f"{pattern}=size=160x284:rate=30:duration=1", "-c:v", "libx264", str(clip)],
            check=True, capture_output=True,
        )
        clips.append(clip)
    barrier = threading.Barrier(2)
    real_load = MotionAnalyzer._load_cache.__func__

    def racing_load(cls):
        cache = real_load(cls)
        try:
            barrier.wait(timeout=1.0)  # both renders read the empty cache together
        except threading.BrokenBarrierError:
            pass
        return cache

    monkeypatch.setattr(MotionAnalyzer, "_load_cache", classmethod(racing_load))
    results = {}
    workers = [
        threading.Thread(target=lambda c=c: results.__setitem__(c.name, MotionAnalyzer.get_motion_scores(c)))
        for c in clips
    ]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    assert all(results[c.name][0] for c in clips)
    stored = json.loads(isolated_cache.read_text(encoding="utf-8"))
    assert {MotionAnalyzer._compute_file_hash(c) for c in clips} <= set(stored)


def test_tone_cache_publish_is_atomic_and_merges(tmp_path, monkeypatch):
    cache = tmp_path / "tone.json"
    monkeypatch.setattr(script_tone_analyzer, "TONE_CACHE_FILE", cache)
    analyzer = script_tone_analyzer.ScriptToneAnalyzer
    analyzer._store_cache_entry("first", ["none"])
    cache_before = cache.read_bytes()

    def locked(source, destination):
        raise PermissionError("destination locked")

    monkeypatch.setattr(script_tone_analyzer.os, "replace", locked)
    analyzer._store_cache_entry("second", ["major"])
    assert cache.read_bytes() == cache_before
    assert list(tmp_path.iterdir()) == [cache]
    monkeypatch.undo()
    monkeypatch.setattr(script_tone_analyzer, "TONE_CACHE_FILE", cache)
    analyzer._store_cache_entry("second", ["major"])
    assert json.loads(cache.read_text(encoding="utf-8")) == {"first": ["none"], "second": ["major"]}
