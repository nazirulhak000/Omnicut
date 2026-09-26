"""Behavioral tests for scripts/proxy_manager.py.

A proxy is a 540p stand-in shown during editing while Render reads the
untouched master. Two failures would be invisible until a finished video is
wrong, so they get the most attention here:

- a proxy path reaching the render path (the export silently becomes 540p)
- a half-written proxy being treated as finished (the timeline shows a
  truncated clip and the user trims against it)

Every source is a tiny synthesized clip written by ffmpeg into tmp_path, and
PROJECTS_DIR is monkeypatched so no test ever writes into the real
03_Projects/.cache tree.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.proxy_manager as pm
from scripts.proxy_manager import ProxyError

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not available on PATH"
)


def _make_clip(path: Path, *, seconds: float = 1.0, size: str = "320x240") -> Path:
    """A real, decodable clip -- proxy encoding is the behavior under test, so
    a fake byte blob would not exercise it."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size={size}:rate=15:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ],
        capture_output=True, check=True, timeout=120,
    )
    return path


@pytest.fixture
def cache_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate the proxy cache under tmp_path."""
    projects = tmp_path / "03_Projects"
    projects.mkdir()
    monkeypatch.setattr(pm, "PROJECTS_DIR", projects)
    return projects / ".cache" / pm.PROXY_CACHE_NAMESPACE


@pytest.fixture
def master(tmp_path: Path) -> Path:
    return _make_clip(tmp_path / "master.mp4")


def _probe(path: Path, stream: str, fields: str) -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", stream,
         "-show_entries", fields, "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    return out.stdout.strip()


# ---------------------------------------------------------------------------
# Building proxies
# ---------------------------------------------------------------------------

def test_ensure_proxy_produces_a_playable_540p_file(cache_root, master):
    proxy = pm.ensure_proxy(master)
    assert proxy.is_file() and proxy.stat().st_size > 0
    assert _probe(proxy, "v:0", "stream=width,height") == f"{pm.PROXY_WIDTH},{pm.PROXY_HEIGHT}"


def test_proxy_is_much_smaller_than_master(cache_root, tmp_path):
    """The whole point is a cheaper file to stream. A proxy that is not
    smaller has no reason to exist."""
    big = _make_clip(tmp_path / "big.mp4", seconds=2.0, size="1920x1080")
    proxy = pm.ensure_proxy(big)
    assert proxy.stat().st_size < big.stat().st_size


def test_proxy_preserves_aspect_by_padding_not_stretching(cache_root, tmp_path):
    """A 16:9 source padded into 9:16 keeps its shape. If it were stretched,
    the user would reframe against a distorted picture and the render would
    not match what they saw."""
    wide = _make_clip(tmp_path / "wide.mp4", size="640x360")
    proxy = pm.ensure_proxy(wide)
    assert _probe(proxy, "v:0", "stream=width,height") == f"{pm.PROXY_WIDTH},{pm.PROXY_HEIGHT}"

    # Square pixels, checked explicitly: force_original_aspect_ratio otherwise
    # encodes the source's shape as a non-square SAR (a 640x360 source came
    # out SAR 1216:1215, DAR 76:135), and a player honoring that would draw
    # the proxy at different proportions than the render.
    assert _probe(proxy, "v:0", "stream=sample_aspect_ratio") in ("1:1", "0:1", "")
    assert _probe(proxy, "v:0", "stream=display_aspect_ratio") in ("9:16", "0:1", "")


def test_proxy_keeps_audio(cache_root, master):
    """Preview plays clip audio, so a video-only proxy would make the
    timeline silent where the render is not."""
    assert _probe(pm.ensure_proxy(master), "a:0", "stream=codec_type") == "audio"


def test_second_call_reuses_existing_proxy(cache_root, master, monkeypatch):
    first = pm.ensure_proxy(master)
    stamp = first.stat().st_mtime_ns

    def fail(*a, **k):
        raise AssertionError("encode must not run again for an existing proxy")

    monkeypatch.setattr(pm, "_encode", fail)
    assert pm.ensure_proxy(master) == first
    assert first.stat().st_mtime_ns == stamp


def test_force_rebuilds_even_when_present(cache_root, master):
    first = pm.ensure_proxy(master)
    calls = {"n": 0}
    orig = pm._encode

    def counting(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)

    pm._encode = counting
    try:
        pm.ensure_proxy(master, force=True)
    finally:
        pm._encode = orig
    assert calls["n"] == 1
    assert first.is_file()


# ---------------------------------------------------------------------------
# Cache identity
# ---------------------------------------------------------------------------

def test_replacing_the_master_invalidates_the_proxy(cache_root, tmp_path):
    """A re-exported source at the same path must not keep serving the old
    picture -- the user would edit against stale frames."""
    src = _make_clip(tmp_path / "clip.mp4", seconds=1.0, size="320x240")
    before = pm.proxy_path_for(src)
    pm.ensure_proxy(src)

    src.unlink()
    _make_clip(src, seconds=2.0, size="640x480")
    after = pm.proxy_path_for(src)
    assert before != after, "changed source must map to a different proxy"


def test_distinct_masters_get_distinct_proxies(cache_root, tmp_path):
    a = _make_clip(tmp_path / "a.mp4")
    b = _make_clip(tmp_path / "b.mp4", seconds=2.0)
    assert pm.proxy_path_for(a) != pm.proxy_path_for(b)


def test_proxy_path_is_pure_and_writes_nothing(cache_root, master):
    pm.proxy_path_for(master)
    assert not cache_root.exists(), "path math must not create the cache dir"


def test_version_bump_changes_the_proxy_path(cache_root, master, monkeypatch):
    """Changing encode settings without bumping PROXY_VERSION would serve
    proxies built under the old settings."""
    before = pm.proxy_path_for(master)
    monkeypatch.setattr(pm, "PROXY_VERSION", "v-next")
    assert pm.proxy_path_for(master) != before


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_missing_master_raises_proxy_error(cache_root, tmp_path):
    with pytest.raises(ProxyError):
        pm.ensure_proxy(tmp_path / "does_not_exist.mp4")


def test_undecodable_source_raises_and_leaves_no_artifact(cache_root, tmp_path):
    """A failed encode must not leave a zero-byte or partial .mp4 that a
    later call would mistake for a finished proxy."""
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video at all")
    with pytest.raises(ProxyError):
        pm.ensure_proxy(junk)
    leftovers = list(cache_root.glob("*")) if cache_root.exists() else []
    assert leftovers == [], f"failed encode left {leftovers}"


def test_no_temp_files_left_behind_after_success(cache_root, master):
    pm.ensure_proxy(master)
    assert [p.name for p in cache_root.glob(".proxy-*")] == []


def test_has_proxy_and_get_proxy_report_absence(cache_root, master):
    assert pm.has_proxy(master) is False
    assert pm.get_proxy(master) is None
    pm.ensure_proxy(master)
    assert pm.has_proxy(master) is True
    assert pm.get_proxy(master) is not None


def test_zero_byte_proxy_is_not_treated_as_ready(cache_root, master):
    """An interrupted write must read as 'no proxy', so the caller falls back
    to the master instead of playing an empty file."""
    target = pm.proxy_path_for(master)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()
    assert pm.has_proxy(master) is False
    assert pm.get_proxy(master) is None


def test_get_proxy_never_builds(cache_root, master, monkeypatch):
    monkeypatch.setattr(
        pm, "_encode",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("get_proxy must not encode")),
    )
    assert pm.get_proxy(master) is None


# ---------------------------------------------------------------------------
# Render isolation -- the guard that keeps exports at full resolution
# ---------------------------------------------------------------------------

def test_is_proxy_path_detects_cache_members(cache_root, master):
    proxy = pm.ensure_proxy(master)
    assert pm.is_proxy_path(proxy) is True
    assert pm.is_proxy_path(str(proxy)) is True


def test_is_proxy_path_rejects_masters_and_junk(cache_root, master):
    assert pm.is_proxy_path(master) is False
    assert pm.is_proxy_path(None) is False
    assert pm.is_proxy_path("") is False
    assert pm.is_proxy_path("   ") is False
    assert pm.is_proxy_path(12345) is False


def test_render_refuses_a_proxy_as_a_clip_source(cache_root, master, monkeypatch):
    """The guard that keeps exports at full resolution.

    A proxy reaching the render path would export at 540p and read as a bad
    encode rather than a wiring mistake, so build_video must fail closed. The
    call is driven far enough to hit source resolution and no further -- the
    error must arrive before any ffmpeg work begins."""
    from scripts import video_editor

    proxy = pm.ensure_proxy(master)
    monkeypatch.setattr(video_editor, "is_proxy_path", pm.is_proxy_path)

    out = cache_root.parent / "should_never_exist.mp4"
    with pytest.raises(ValueError, match="proxy"):
        video_editor.VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(proxy)],
            total_duration=1.0,
            mixed_audio_path="",
            ass_subtitle_path="",
            output_mp4_path=str(out),
            clip_list=[{"source_path": str(proxy), "trim_start": 0.0, "trim_end": 1.0}],
        )
    assert not out.exists(), "a refused render must not leave an output file"


def test_render_accepts_a_master_path(cache_root, master):
    """The guard must not reject legitimate sources -- a false positive here
    would block every render."""
    assert pm.is_proxy_path(master) is False


# ---------------------------------------------------------------------------
# Cache maintenance
# ---------------------------------------------------------------------------

def test_scan_reports_size_and_count(cache_root, master):
    empty = pm.scan_proxy_cache()
    assert empty["bytes"] == 0 and empty["count"] == 0
    pm.ensure_proxy(master)
    scanned = pm.scan_proxy_cache()
    assert scanned["count"] == 1 and scanned["bytes"] > 0


def test_purge_removes_proxies_but_not_the_master(cache_root, master):
    proxy = pm.ensure_proxy(master)
    result = pm.purge_proxy_cache()
    assert result["removed_count"] == 1 and result["freed_bytes"] > 0
    assert not proxy.exists()
    assert master.is_file(), "purging proxies must never touch source media"


def test_purge_leaves_the_shared_cache_parent_alone(cache_root, master, tmp_path):
    """03_Projects/.cache is shared with the Background Isolation caches.
    Purging proxies must not remove a sibling namespace's data."""
    pm.ensure_proxy(master)
    sibling = cache_root.parent / "background-isolation-foreground-sequences"
    sibling.mkdir(parents=True, exist_ok=True)
    keep = sibling / "keep.txt"
    keep.write_text("not mine", encoding="utf-8")

    pm.purge_proxy_cache()

    assert keep.is_file(), "purge must only remove its own namespace"
    assert cache_root.parent.is_dir()


def test_purge_on_empty_cache_is_a_noop(cache_root):
    result = pm.purge_proxy_cache()
    assert result["status"] == "ok"
    assert result["removed_count"] == 0


# ---------------------------------------------------------------------------
# storage_cleaner integration
# ---------------------------------------------------------------------------

def test_storage_cleaner_reports_the_proxy_cache(cache_root, master, monkeypatch):
    """Proxies must be visible as reclaimable space, or the user has no way
    to find out what is filling the disk."""
    from scripts import storage_cleaner

    pm.ensure_proxy(master)
    monkeypatch.setattr(storage_cleaner, "scan_proxy_cache", pm.scan_proxy_cache)
    monkeypatch.setattr(storage_cleaner, "PROJECTS_DIR", cache_root.parent.parent)

    scanned = storage_cleaner.scan_safe_reclaimable_cache()
    entry = next((i for i in scanned["items"] if i["id"] == "editing_proxies"), None)
    assert entry is not None, "proxy cache missing from the reclaimable list"
    assert entry["bytes"] > 0 and entry["count"] == 1


def test_storage_cleaner_purge_removes_proxies_and_keeps_masters(cache_root, master, monkeypatch):
    from scripts import storage_cleaner

    proxy = pm.ensure_proxy(master)
    monkeypatch.setattr(storage_cleaner, "purge_proxy_cache", pm.purge_proxy_cache)
    monkeypatch.setattr(storage_cleaner, "PROJECTS_DIR", cache_root.parent.parent)
    monkeypatch.setattr(storage_cleaner, "CAPCUT_DRAFT_DIR", cache_root.parent / "no_drafts")
    monkeypatch.setattr(storage_cleaner, "BASE_DIR", cache_root.parent.parent)

    result = storage_cleaner.execute_safe_purge()

    assert result["success"] is True
    assert not proxy.exists(), "purge should have removed the proxy"
    assert master.is_file(), "purge must never touch source media"
