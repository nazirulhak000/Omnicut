"""Unit tests for AssetDedupEngine using isolated temporary media files."""
from pathlib import Path
import time
import pytest

from scripts.asset_dedup import AssetDedupEngine


@pytest.fixture
def isolated_media_env(tmp_path: Path, monkeypatch):
    inbox = tmp_path / "00_Inbox"
    raw = tmp_path / "01_Raw"
    archive = tmp_path / "06_Archive"

    inbox.mkdir(parents=True)
    raw.mkdir(parents=True)
    archive.mkdir(parents=True)

    monkeypatch.setattr("scripts.asset_dedup.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.asset_dedup.INBOX_DIR", inbox)
    monkeypatch.setattr("scripts.asset_dedup.RAW_DIR", raw)
    monkeypatch.setattr("scripts.asset_dedup.ARCHIVE_DIR", archive)
    monkeypatch.setattr("scripts.asset_dedup.TRASH_DIR", archive / ".trash")

    return {
        "root": tmp_path,
        "inbox": inbox,
        "raw": raw,
        "archive": archive,
    }


def test_dedup_detects_duplicates_across_inbox_and_raw(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    raw = isolated_media_env["raw"]

    # 1. Unique file in inbox
    (inbox / "unique_video.mp4").write_bytes(b"unique content 12345" * 100)

    # 2. Master file in raw (created first)
    master = raw / "clip_master.mp4"
    master.write_bytes(b"shared video content" * 200)

    # Slight pause to ensure distinct mtime
    time.sleep(0.05)

    # 3. Duplicate in inbox (same content, created later)
    dup1 = inbox / "sync_from_phone_1.mp4"
    dup1.write_bytes(b"shared video content" * 200)

    # 4. Another duplicate in raw subfolder
    sub_raw = raw / "20260912_batch"
    sub_raw.mkdir()
    dup2 = sub_raw / "sync_from_phone_2.mp4"
    dup2.write_bytes(b"shared video content" * 200)

    # Scan
    scan_res = AssetDedupEngine.scan_duplicates(search_dirs=[inbox, raw], min_file_size_bytes=10)

    assert scan_res["total_scanned_files"] == 4
    assert scan_res["duplicate_groups_count"] == 1
    assert scan_res["total_duplicate_files"] == 2

    group = scan_res["groups"][0]
    assert group["original"]["file_name"] == "clip_master.mp4"
    dup_names = [d["file_name"] for d in group["duplicates"]]
    assert "sync_from_phone_1.mp4" in dup_names
    assert "sync_from_phone_2.mp4" in dup_names
    assert scan_res["reclaimable_bytes"] == dup1.stat().st_size * 2


def test_clean_duplicates_moves_to_trash(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    archive = isolated_media_env["archive"]
    trash = archive / ".trash"

    orig = inbox / "original.mp4"
    orig.write_bytes(b"some media" * 100)
    dup = inbox / "duplicate.mp4"
    dup.write_bytes(b"some media" * 100)

    clean_res = AssetDedupEngine.clean_duplicates([str(dup.resolve())], move_to_trash=True)
    assert clean_res["status"] == "ok"
    assert clean_res["cleaned_count"] == 1
    assert clean_res["freed_bytes"] > 0

    # Orig still exists, dup moved to trash
    assert orig.exists()
    assert not dup.exists()
    assert (trash / "duplicate.mp4").exists()


def test_clean_duplicates_security_rejects_outside_path(isolated_media_env):
    root = isolated_media_env["root"]
    outside_file = root / "system_file.mp4"
    outside_file.write_bytes(b"critical data")

    clean_res = AssetDedupEngine.clean_duplicates([str(outside_file.resolve())])
    assert clean_res["cleaned_count"] == 0
    assert len(clean_res["errors"]) == 1
    assert "Security" in clean_res["errors"][0]
    assert outside_file.exists()


def test_clean_refuses_when_original_and_duplicate_both_requested(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    raw = isolated_media_env["raw"]
    a = inbox / "copy_a.mp4"
    b = raw / "copy_b.mp4"
    a.write_bytes(b"identical payload" * 50)
    b.write_bytes(b"identical payload" * 50)

    res = AssetDedupEngine.clean_duplicates([str(a), str(b)], move_to_trash=True)

    assert res["cleaned_count"] == 0
    assert res["freed_bytes"] == 0
    assert len(res["errors"]) == 2
    assert len(res["skipped"]) == 2
    assert a.exists() and b.exists()


def test_clean_keeps_one_survivor_when_all_copies_requested_hard_delete(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    files = [inbox / f"c{i}.mp4" for i in range(3)]
    for f in files:
        f.write_bytes(b"triple content" * 50)

    res = AssetDedupEngine.clean_duplicates([str(f) for f in files], move_to_trash=False)

    assert res["cleaned_count"] == 0
    assert all(f.exists() for f in files)


def test_clean_never_deletes_unique_file(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    unique = inbox / "only_one.mp4"
    unique.write_bytes(b"one of a kind" * 50)
    (inbox / "other.mp4").write_bytes(b"different content" * 50)

    for trash_flag in (True, False):
        res = AssetDedupEngine.clean_duplicates([str(unique)], move_to_trash=trash_flag)
        assert res["cleaned_count"] == 0
        assert len(res["errors"]) == 1
        assert unique.exists()


def test_clean_hard_delete_with_surviving_copy(isolated_media_env):
    inbox = isolated_media_env["inbox"]
    orig = inbox / "orig.mp4"
    dup = inbox / "dup.mp4"
    orig.write_bytes(b"same same" * 50)
    dup.write_bytes(b"same same" * 50)

    res = AssetDedupEngine.clean_duplicates([str(dup)], move_to_trash=False)

    assert res["cleaned_count"] == 1
    assert orig.exists() and not dup.exists()


def test_clean_resolves_relative_path_against_base_dir(isolated_media_env, tmp_path_factory, monkeypatch):
    inbox = isolated_media_env["inbox"]
    orig = inbox / "orig.mp4"
    dup = inbox / "dup.mp4"
    orig.write_bytes(b"relative payload" * 50)
    dup.write_bytes(b"relative payload" * 50)

    # cwd is somewhere unrelated: relative input must still resolve vs BASE_DIR.
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    res = AssetDedupEngine.clean_duplicates(["00_Inbox/dup.mp4"], move_to_trash=True)

    assert res["cleaned_count"] == 1
    assert res["errors"] == []
    assert orig.exists() and not dup.exists()
    assert (isolated_media_env["archive"] / ".trash" / "dup.mp4").exists()
