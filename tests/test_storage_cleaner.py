"""
Unit tests for Safe Storage Optimizer & Cache Cleaner (Round STORAGE-OPTIMIZER-1).
Verifies safe cleanup of transient files, scanning of vision proxies and temp previews,
and STRICT RULE 1 (NEVER touches 01_Raw or 02_Assets).
"""

import pytest
from pathlib import Path

from scripts.config import BASE_DIR, RAW_DIR, ASSETS_DIR, PROJECTS_DIR
from scripts.storage_cleaner import (
    scan_safe_reclaimable_cache,
    execute_safe_purge,
    is_strictly_protected_path,
)


def test_strictly_protected_path_rule_1():
    """Verify STRICT RULE 1 protection check."""
    raw_subfile = RAW_DIR / "test_product" / "video.mp4"
    assets_subfile = ASSETS_DIR / "Music" / "bgm.mp3"
    projects_file = PROJECTS_DIR / "proj1" / "preview_test.wav"
    vision_proxy = BASE_DIR / ".vision_proxies" / "thumb.jpg"

    assert is_strictly_protected_path(RAW_DIR) is True
    assert is_strictly_protected_path(raw_subfile) is True
    assert is_strictly_protected_path(ASSETS_DIR) is True
    assert is_strictly_protected_path(assets_subfile) is True

    assert is_strictly_protected_path(projects_file) is False
    assert is_strictly_protected_path(vision_proxy) is False


def test_scan_and_purge_safe_reclaimable_cache(tmp_path, monkeypatch):
    """Test safe cache scanning and purging without touching critical assets."""
    fake_base = tmp_path / "app_root"
    fake_raw = fake_base / "01_Raw"
    fake_assets = fake_base / "02_Assets"
    fake_projects = fake_base / "03_Projects"
    fake_proxies = fake_base / ".vision_proxies"
    fake_capcut = tmp_path / "CapCutDrafts"

    fake_raw.mkdir(parents=True)
    fake_assets.mkdir(parents=True)
    fake_projects.mkdir(parents=True)
    fake_proxies.mkdir(parents=True)
    fake_capcut.mkdir(parents=True)

    # 1. Create protected files
    raw_file = fake_raw / "sample_footage.mp4"
    raw_file.write_bytes(b"ORIGINAL_RAW_FOOTAGE_DO_NOT_DELETE")

    asset_file = fake_assets / "important_font.ttf"
    asset_file.write_bytes(b"ORIGINAL_FONT_DO_NOT_DELETE")

    # 2. Create transient files
    proxy_file = fake_proxies / "thumb_vision.jpg"
    proxy_file.write_bytes(b"PREVIEW_THUMB_DATA_12345")

    temp_preview_wav = fake_projects / "preview_tts_test.wav"
    temp_preview_wav.write_bytes(b"TEMP_AUDIO_WAV_BYTES_67890")

    cutout_cache_dir = fake_projects / ".cache" / "background-isolation-videos" / "frames"
    cutout_cache_dir.mkdir(parents=True)
    (cutout_cache_dir / "frame_000000.png").write_bytes(b"CUTOUT_FRAME_TRANSIENT_PNG")

    cloud_cache_dir = fake_capcut / ".cloud_cache_draft_1"
    cloud_cache_dir.mkdir()
    (cloud_cache_dir / "temp.dat").write_bytes(b"CAPCUT_TRANSIENT_CACHE")

    # Monkeypatch paths
    monkeypatch.setattr("scripts.storage_cleaner.BASE_DIR", fake_base)
    monkeypatch.setattr("scripts.storage_cleaner.RAW_DIR", fake_raw)
    monkeypatch.setattr("scripts.storage_cleaner.ASSETS_DIR", fake_assets)
    monkeypatch.setattr("scripts.storage_cleaner.PROJECTS_DIR", fake_projects)
    monkeypatch.setattr("scripts.storage_cleaner.CAPCUT_DRAFT_DIR", fake_capcut)

    # Scan
    scan_res = scan_safe_reclaimable_cache()
    assert scan_res["items_count"] >= 3
    assert any(item["id"] == "cutout_cache" for item in scan_res["items"])
    assert scan_res["total_bytes"] > 0

    # Purge
    purge_res = execute_safe_purge()
    assert purge_res["success"] is True
    assert purge_res["purged_files"] >= 3

    # Verify transient files removed
    assert not proxy_file.exists()
    assert not temp_preview_wav.exists()
    assert not (fake_projects / ".cache" / "background-isolation-videos").exists()
    assert not cloud_cache_dir.exists()

    # STRICT RULE 1 VERIFICATION: Protected files MUST STILL EXIST UNTOUCHED
    assert raw_file.exists()
    assert raw_file.read_bytes() == b"ORIGINAL_RAW_FOOTAGE_DO_NOT_DELETE"
    assert asset_file.exists()
    assert asset_file.read_bytes() == b"ORIGINAL_FONT_DO_NOT_DELETE"


def test_scan_and_purge_cutout_cache_only(tmp_path, monkeypatch):
    fake_projects = tmp_path / "03_Projects"
    fake_projects.mkdir()
    cutout_cache = fake_projects / ".cache" / "background-isolation-videos" / "frames"
    cutout_cache.mkdir(parents=True)
    frame_file = cutout_cache / "frame_000001.png"
    frame_file.write_bytes(b"CUTOUT_TARGET_FRAME")
    source_proxy = fake_projects / ".cache" / "proxies" / "rgb.mp4"
    source_proxy.parent.mkdir()
    source_proxy.write_bytes(b"PRESERVE_RGB_PROXY")
    unknown = fake_projects / ".cache" / "other-cache.json"
    unknown.write_text("keep")

    monkeypatch.setattr("scripts.storage_cleaner.PROJECTS_DIR", fake_projects)

    from scripts.storage_cleaner import scan_cutout_cache, purge_cutout_cache_only

    scan_res = scan_cutout_cache()
    assert scan_res["bytes"] == len(b"CUTOUT_TARGET_FRAME")
    assert scan_res["count"] == 1

    purge_res = purge_cutout_cache_only()
    assert purge_res["success"] is True
    assert purge_res["purged_files"] == 1
    assert not frame_file.exists()
    assert source_proxy.read_bytes() == b"PRESERVE_RGB_PROXY"
    assert unknown.read_text() == "keep"

    # Re-scan should be 0
    rescan = scan_cutout_cache()
    assert rescan["bytes"] == 0
    assert rescan["count"] == 0
