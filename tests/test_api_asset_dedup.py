"""Unit tests for /api/assets/duplicates endpoints."""
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.api_asset_dedup import router


@pytest.fixture
def dedup_test_client(tmp_path: Path, monkeypatch):
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

    # Create dummy files
    f1 = inbox / "orig.mp4"
    f1.write_bytes(b"duplicate data content" * 100)
    f2 = raw / "copy.mp4"
    f2.write_bytes(b"duplicate data content" * 100)

    app = FastAPI()
    app.include_router(router)
    return TestClient(app), f2


def test_api_dedup_scan_and_clean(dedup_test_client):
    client, copy_file = dedup_test_client

    # Scan
    scan_res = client.get("/api/assets/duplicates/scan?min_size_kb=1")
    assert scan_res.status_code == 200
    data = scan_res.json()
    assert data["status"] == "ok"
    assert data["duplicate_groups_count"] == 1
    assert data["total_duplicate_files"] == 1

    # Clean
    clean_res = client.post("/api/assets/duplicates/clean", json={
        "duplicate_paths": [str(copy_file.resolve())],
        "move_to_trash": True
    })
    assert clean_res.status_code == 200
    assert clean_res.json()["cleaned_count"] == 1

    # Scan again -> 0 duplicates
    scan_again = client.get("/api/assets/duplicates/scan?min_size_kb=1")
    assert scan_again.json()["total_duplicate_files"] == 0


def test_api_dedup_clean_refuses_to_remove_every_copy(dedup_test_client):
    client, copy_file = dedup_test_client
    orig_file = copy_file.parent.parent / "00_Inbox" / "orig.mp4"

    clean_res = client.post("/api/assets/duplicates/clean", json={
        "duplicate_paths": [str(copy_file.resolve()), str(orig_file.resolve())],
        "move_to_trash": False,
    })

    assert clean_res.status_code == 200
    body = clean_res.json()
    assert body["cleaned_count"] == 0
    assert len(body["errors"]) == 2
    assert copy_file.exists() and orig_file.exists()
