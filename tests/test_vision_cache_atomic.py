"""Vision cache safety: atomic writes and corrupt-file backup (tmp_path only)."""

import json
import os

import pytest

import scripts.gemini_vision_matcher as gvm


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / ".vision_cache.json"
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", path)
    return path


def test_corrupt_cache_is_backed_up_not_overwritten(cache_file):
    cache_file.write_text("{not valid json", encoding="utf-8")

    assert gvm.GeminiVisionMatcher._load_cache() == {}

    backup = cache_file.with_name(cache_file.name + ".corrupt")
    assert backup.read_text(encoding="utf-8") == "{not valid json"

    gvm.GeminiVisionMatcher._save_cache({"ok": 1})
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {"ok": 1}
    assert backup.read_text(encoding="utf-8") == "{not valid json"


def test_second_corrupt_file_does_not_clobber_first_backup(cache_file):
    backup = cache_file.with_name(cache_file.name + ".corrupt")
    cache_file.write_text("first bad", encoding="utf-8")
    gvm.GeminiVisionMatcher._load_cache()
    cache_file.write_text("second bad", encoding="utf-8")
    gvm.GeminiVisionMatcher._load_cache()

    assert backup.read_text(encoding="utf-8") == "first bad"
    backups = [p for p in cache_file.parent.glob(cache_file.name + "*.corrupt")]
    assert sorted(p.read_text(encoding="utf-8") for p in backups) == ["first bad", "second bad"]


def test_save_is_atomic_when_replace_fails(cache_file, monkeypatch):
    cache_file.write_text(json.dumps({"original": True}), encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(gvm.os, "replace", boom)
    gvm.GeminiVisionMatcher._save_cache({"new": True})

    assert json.loads(cache_file.read_text(encoding="utf-8")) == {"original": True}
    # No temp file left behind.
    assert [p.name for p in cache_file.parent.iterdir()] == [cache_file.name]


def test_save_then_load_round_trip(cache_file):
    gvm.GeminiVisionMatcher._save_cache({"k": "ไทย"})
    assert gvm.GeminiVisionMatcher._load_cache() == {"k": "ไทย"}
    assert [p.name for p in cache_file.parent.iterdir()] == [cache_file.name]
