"""Unit & Integration Tests for Google Drive Smart Archiving & Local Breadcrumb Retention.

Strict Rules Compliance:
- Fully deterministic and offline (uses pytest tmp_path fixtures).
- Never touches real production assets.
- Verifies Double SHA-256 verification before local video pruning.
- Verifies that 3:4 cover image thumbnails in 05_Covers_Thumbnails/ are strictly preserved locally.
- Verifies restoration capability from Google Drive back to local storage.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.gdrive_archive_engine import GDriveArchiveEngine, compute_file_sha256, format_bytes


@pytest.fixture
def archive_sandbox(tmp_path: Path):
    """Sets up a complete isolated sandbox imitating Home PC and Google Drive Desktop."""
    home_dir = tmp_path / "HomePC"
    gdrive_dir = tmp_path / "GoogleDrive" / "My Drive" / "Omnicut_Exports" / "02_Posted_Archive"
    
    docs_dir = home_dir / "_Docs"
    exports_dir = home_dir / "04_Exports" / "Posted"
    covers_dir = home_dir / "05_Covers_Thumbnails"
    raw_dir = home_dir / "01_Raw" / "TEST_PROD_1"
    projects_dir = home_dir / "03_Projects" / "TEST_PROD_1"

    for d in (docs_dir, exports_dir, covers_dir, raw_dir, projects_dir, gdrive_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Create a dummy posted video file (5MB of repeatable bytes)
    video_file = exports_dir / "TEST_PROD_1_hook_v1_posted.mp4"
    video_content = b"OMNICUT_SAMPLE_VERTICAL_VIDEO_DATA_916_" * 100000  # ~4MB
    video_file.write_bytes(video_content)
    video_sha = compute_file_sha256(video_file)

    # 2. Create a dummy cover image (100KB)
    cover_file = covers_dir / "TEST_PROD_1_cover_3x4.jpg"
    cover_content = b"FAKE_JPEG_IMAGE_COVER_HEADER" * 4000
    cover_file.write_bytes(cover_content)

    # 3. Create dummy raw material and project files
    (raw_dir / "clean_broll.mp4").write_bytes(b"RAW_BROLL_CLIP_DATA" * 5000)
    (projects_dir / "draft_content.json").write_text('{"draft": true}', encoding="utf-8")

    # 4. Populate export_registry.json
    export_registry = [
        {
            "id": "exp_test_001",
            "path": "04_Exports/Posted/TEST_PROD_1_hook_v1_posted.mp4",
            "product_id": "TEST_PROD_1",
            "angle_id": "hook_1",
            "project_name": "TEST_PROD_1",
            "status": "posted",
            "posted_at": "2026-10-31T10:00:00Z",
            "cover_path": "05_Covers_Thumbnails/TEST_PROD_1_cover_3x4.jpg",
        },
        {
            "id": "exp_unposted_002",
            "path": "04_Exports/TEST_UNPOSTED_clip.mp4",
            "product_id": "TEST_UNPOSTED",
            "status": "rendered",  # Still unposted! Should be ignored by archive
            "posted_at": None,
        }
    ]
    with open(docs_dir / "export_registry.json", "w", encoding="utf-8") as f:
        json.dump(export_registry, f, indent=2)

    # 5. Populate post_log.json
    post_log = [
        {
            "id": "post_test_001",
            "product_name": "TEST_PROD_1",
            "clip_file": "04_Exports/Posted/TEST_PROD_1_hook_v1_posted.mp4",
            "posted_at": "2026-10-31T10:00:00Z",
        }
    ]
    with open(docs_dir / "post_log.json", "w", encoding="utf-8") as f:
        json.dump(post_log, f, indent=2)

    return {
        "home_dir": home_dir,
        "gdrive_dir": gdrive_dir,
        "video_file": video_file,
        "video_sha": video_sha,
        "cover_file": cover_file,
        "raw_dir": raw_dir,
        "projects_dir": projects_dir,
    }


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"
    assert format_bytes(3 * 1024 * 1024 * 1024) == "3.00 GB"


def test_get_archive_status_identifies_posted_clips(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]

    status = GDriveArchiveEngine.get_archive_status(base_dir=home, custom_gdrive_root=gdrive)

    assert status["status"] == "ok"
    assert status["gdrive_available"] is True
    assert status["eligible_clips_count"] == 1
    assert status["archived_clips_count"] == 0
    assert status["total_reclaimable_bytes"] > 0
    assert len(status["products"]) == 1
    assert status["products"][0]["product_id"] == "TEST_PROD_1"


def test_archive_clips_video_only_reclaims_space_and_preserves_cover(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]
    video_file = archive_sandbox["video_file"]
    cover_file = archive_sandbox["cover_file"]
    original_video_sha = archive_sandbox["video_sha"]

    # Verify initial state: video and cover exist locally
    assert video_file.exists()
    assert cover_file.exists()

    # Execute archive
    res = GDriveArchiveEngine.archive_clips(
        export_ids=["exp_test_001"],
        scope="video_only",
        base_dir=home,
        custom_gdrive_root=gdrive,
    )

    assert res["status"] == "ok"
    assert res["archived_count"] == 1
    assert res["reclaimed_bytes"] > 0

    # 1. VERIFY: Heavy video file is deleted from local disk (reclaimed space!)
    assert not video_file.exists(), "Local video file should be pruned to reclaim space"

    # 2. VERIFY: Video file is fully intact on Google Drive
    gdrive_video = gdrive / "TEST_PROD_1" / "Videos" / video_file.name
    assert gdrive_video.exists(), "Video must be present on Google Drive"
    assert compute_file_sha256(gdrive_video) == original_video_sha, "SHA-256 must match bit-for-bit"

    # 3. CRITICAL: Local cover image MUST be preserved locally for UI gallery preview!
    assert cover_file.exists(), "Local 3:4 cover thumbnail must remain in 05_Covers_Thumbnails"

    # 4. VERIFY: Registry is updated with cloud status
    with open(home / "_Docs" / "export_registry.json", "r", encoding="utf-8") as f:
        registry = json.load(f)
    exp = next(x for x in registry if x["id"] == "exp_test_001")
    assert exp["cloud_status"] == "archived_gdrive"
    assert "G:" in exp["cloud_path"] or "GoogleDrive" in exp["cloud_path"]


def test_archive_clips_full_scope_archives_sources(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]
    raw_dir = archive_sandbox["raw_dir"]
    projects_dir = archive_sandbox["projects_dir"]

    assert raw_dir.exists()
    assert projects_dir.exists()

    # Execute full archive
    res = GDriveArchiveEngine.archive_clips(
        product_ids=["TEST_PROD_1"],
        scope="full",
        base_dir=home,
        custom_gdrive_root=gdrive,
    )

    assert res["status"] == "ok"
    assert not raw_dir.exists(), "Local raw folder should be pruned in full scope"
    assert not projects_dir.exists(), "Local project draft folder should be pruned in full scope"

    # Check existence on Google Drive
    dest_raw = gdrive / "TEST_PROD_1" / "Sources" / "Raw" / "clean_broll.mp4"
    dest_proj = gdrive / "TEST_PROD_1" / "Sources" / "Projects" / "draft_content.json"
    assert dest_raw.exists()
    assert dest_proj.exists()


def test_restore_clip_copies_video_back_from_drive(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]
    video_file = archive_sandbox["video_file"]
    original_video_sha = archive_sandbox["video_sha"]

    # Archive first
    GDriveArchiveEngine.archive_clips(
        export_ids=["exp_test_001"],
        base_dir=home,
        custom_gdrive_root=gdrive,
    )
    assert not video_file.exists()

    # Restore
    restore_res = GDriveArchiveEngine.restore_clip("exp_test_001", base_dir=home)
    assert restore_res["status"] == "ok"

    # Verify restored file
    assert video_file.exists()
    assert compute_file_sha256(video_file) == original_video_sha

    # Verify registry updated
    with open(home / "_Docs" / "export_registry.json", "r", encoding="utf-8") as f:
        registry = json.load(f)
    exp = next(x for x in registry if x["id"] == "exp_test_001")
    assert exp["cloud_status"] == "restored_local"


def test_archive_clips_progress_callback(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]

    progress_events = []
    def on_progress(p):
        progress_events.append(p)

    res = GDriveArchiveEngine.archive_clips(
        export_ids=["exp_test_001"],
        base_dir=home,
        custom_gdrive_root=gdrive,
        progress_callback=on_progress,
    )

    assert res["status"] == "ok"
    assert len(progress_events) >= 2
    assert any(p["stage"] == "copying" for p in progress_events)
    assert any(p["stage"] == "completed" for p in progress_events)
    assert progress_events[-1]["percent"] == 100.0


def test_archive_clips_smart_delta_skip(archive_sandbox):
    home = archive_sandbox["home_dir"]
    gdrive = archive_sandbox["gdrive_dir"]
    video_file = archive_sandbox["video_file"]

    # Pre-populate identical file in Google Drive destination
    dest_video = gdrive / "TEST_PROD_1" / "Videos" / video_file.name
    dest_video.parent.mkdir(parents=True, exist_ok=True)
    dest_video.write_bytes(video_file.read_bytes())

    res = GDriveArchiveEngine.archive_clips(
        export_ids=["exp_test_001"],
        base_dir=home,
        custom_gdrive_root=gdrive,
    )

    assert res["status"] == "ok"
    assert res["archived_count"] == 1
    # Check that delta_skipped is True
    assert res["records"][0]["delta_skipped"] is True
    assert not video_file.exists(), "Local file pruned even on delta skip"
    assert dest_video.exists()

