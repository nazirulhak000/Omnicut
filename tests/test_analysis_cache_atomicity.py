"""Disposable analysis caches cannot interrupt a render or damage committed data."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import beat_sync, motion_analyzer


@pytest.fixture(params=["beat", "motion"])
def cache_target(request, monkeypatch, tmp_path):
    if request.param == "beat":
        module, analyzer, binding = beat_sync, beat_sync.BeatSync, "BEAT_CACHE_FILE"
    else:
        module, analyzer, binding = motion_analyzer, motion_analyzer.MotionAnalyzer, "MOTION_CACHE_FILE"
    path = tmp_path / "cache" / "analysis.json"
    monkeypatch.setattr(module, binding, path)
    return module, analyzer, path


@pytest.mark.parametrize("content", ["[]", "null", '"invalid"', "42", "true", "{broken"])
def test_invalid_cache_root_does_not_break_optional_analysis(cache_target, content, monkeypatch):
    module, analyzer, path = cache_target
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")
    source = path.parent / "source.bin"
    source.write_bytes(b"synthetic input")
    if module is beat_sync:
        def unavailable_audio(*args, **kwargs):
            raise RuntimeError("optional audio decoder unavailable")

        monkeypatch.setitem(sys.modules, "librosa", SimpleNamespace(load=unavailable_audio))
        assert analyzer.get_beat_times(source) == []
        assert analyzer.get_beat_grid(source) == {"bpm": None, "major_beats": [], "minor_beats": []}
    else:
        monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace(
            VideoCapture=lambda *args: SimpleNamespace(isOpened=lambda: False),
        ))
        assert analyzer.get_motion_scores(source) == ([], [])


def test_atomic_publish_has_complete_payload_and_cleans_temp(cache_target, monkeypatch):
    module, analyzer, path = cache_target
    payload = {"track": {"times": [0.25], "scores": [0.5]}, "label": "music"}
    real_replace = module.os.replace
    published = []

    def observe_replace(source, destination):
        temporary = Path(source)
        assert temporary.parent == path.parent
        assert temporary != path
        assert json.loads(temporary.read_text(encoding="utf-8")) == payload
        published.append(destination)
        real_replace(source, destination)

    monkeypatch.setattr(module.os, "replace", observe_replace)
    analyzer._save_cache(payload)
    assert published == [path]
    assert analyzer._load_cache() == payload
    assert list(path.parent.iterdir()) == [path]


def test_failed_atomic_publish_keeps_previous_cache_and_removes_temp(cache_target, monkeypatch):
    module, analyzer, path = cache_target
    path.parent.mkdir()
    original = '{"existing": [0.25]}'
    path.write_text(original, encoding="utf-8")

    def locked_destination(source, destination):
        assert Path(source).exists()
        raise PermissionError("destination locked")

    monkeypatch.setattr(module.os, "replace", locked_destination)
    analyzer._save_cache({"new": [1.0]})
    assert path.read_text(encoding="utf-8") == original
    assert list(path.parent.iterdir()) == [path]


def test_payload_serialization_failure_keeps_previous_cache(cache_target):
    _, analyzer, path = cache_target
    analyzer._save_cache({"existing": [0.25]})
    previous = path.read_bytes()
    analyzer._save_cache({"cannot_encode": object()})
    assert path.read_bytes() == previous
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("entry", ["bad", {}, [float("nan")], [float("inf")], [-0.1], [True]])
def test_invalid_beat_entry_is_reanalyzed_safely(tmp_path, monkeypatch, entry):
    source = tmp_path / "track.wav"
    source.write_bytes(b"synthetic input")
    cache = tmp_path / "beats.json"
    monkeypatch.setattr(beat_sync, "BEAT_CACHE_FILE", cache)
    key = f"{source.name}:{source.stat().st_size}"
    cache.write_text(json.dumps({key: entry}), encoding="utf-8")

    def unavailable_audio(*args, **kwargs):
        raise RuntimeError("optional audio decoder unavailable")

    monkeypatch.setitem(sys.modules, "librosa", SimpleNamespace(load=unavailable_audio))
    assert beat_sync.BeatSync.get_beat_times(source) == []


@pytest.mark.parametrize("entry", [
    {"bpm": 120, "major_beats": 42, "minor_beats": []},
    {"bpm": float("nan"), "major_beats": [0.5], "minor_beats": []},
    {"bpm": True, "major_beats": [0.5], "minor_beats": []},
    {"bpm": 120, "major_beats": [], "minor_beats": ["bad"]},
])
def test_invalid_grid_entry_rebuilds_from_valid_beats(tmp_path, monkeypatch, entry):
    source = tmp_path / "track.wav"
    source.write_bytes(b"synthetic input")
    cache = tmp_path / "beats.json"
    monkeypatch.setattr(beat_sync, "BEAT_CACHE_FILE", cache)
    key = f"{source.name}:{source.stat().st_size}"
    cache.write_text(json.dumps({key: [0.0, 0.5, 1.0], "v2:" + key: entry}), encoding="utf-8")
    assert beat_sync.BeatSync.get_beat_grid(source) == {
        "bpm": 120.0, "major_beats": [0.0], "minor_beats": [0.5, 1.0],
    }


@pytest.mark.parametrize("entry", [
    [], {"times": [0.25], "scores": []},
    {"times": [float("nan")], "scores": [0.5]},
    {"times": [0.25], "scores": [float("inf")]},
    {"times": [0.25], "scores": [1.5]},
    {"times": [True], "scores": [0.5]},
])
def test_invalid_motion_entry_cannot_reach_timeline_math(tmp_path, monkeypatch, entry):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic input")
    cache = tmp_path / "motion.json"
    monkeypatch.setattr(motion_analyzer, "MOTION_CACHE_FILE", cache)
    key = motion_analyzer.MotionAnalyzer._compute_file_hash(source)
    cache.write_text(json.dumps({key: entry}), encoding="utf-8")
    monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace(
        VideoCapture=lambda *args: SimpleNamespace(isOpened=lambda: False),
    ))
    assert motion_analyzer.MotionAnalyzer.get_motion_scores(source) == ([], [])
