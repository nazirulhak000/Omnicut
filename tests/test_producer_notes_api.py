import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import tempfile

from scripts.api_server import app
import scripts.api_producer as api_producer

@pytest.fixture
def client():
    return TestClient(app)

def test_producer_notes_roundtrip(client, monkeypatch, tmp_path):
    # Use temporary test notes file
    test_notes_file = tmp_path / "playbook_notes.json"
    monkeypatch.setattr(api_producer, "NOTES_FILE", test_notes_file)

    # 1. Get initial notes (should return starter notes if file doesn't exist)
    res = client.get("/api/producer/notes")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["notes"]) >= 2
    assert data["revision"]

    # 2. Add a new note with multi-images
    sample_note = {
        "text": "Idea with multiple reference images for boss",
        "url": "https://www.tiktok.com/@example/video/123",
        "images": ["/assets/Refs/ref1.png", "/assets/Refs/ref2.png", "/assets/Refs/ref3.png"],
        "tag": "Hook",
        "productName": "Ergonomic Keyboard",
        "productCode": "KEY-01"
    }

    res_add = client.post("/api/producer/notes/add", json=sample_note)
    assert res_add.status_code == 200
    added_note = res_add.json()["note"]
    assert added_note["text"] == sample_note["text"]
    assert len(added_note["images"]) == 3
    assert added_note["imageUrl"] == "/assets/Refs/ref1.png"
    note_id = added_note["id"]

    # 3. Read back and verify persistence
    res_get = client.get("/api/producer/notes")
    assert res_get.status_code == 200
    notes = res_get.json()["notes"]
    assert len(notes) == 3
    assert notes[0]["id"] == note_id
    assert len(notes[0]["images"]) == 3

    # 4. Save bulk notes update (clear starter notes and keep just 1)
    updated_notes = [
        {
            "id": note_id,
            "text": "Updated note with 4 images",
            "images": ["/assets/Refs/1.png", "/assets/Refs/2.png", "/assets/Refs/3.png", "/assets/Refs/4.png"],
            "tag": "Visual"
        }
    ]
    res_save = client.post("/api/producer/notes", json={"notes": updated_notes})
    assert res_save.status_code == 200
    assert len(res_save.json()["notes"]) == 1

    # Verify updated
    res_get2 = client.get("/api/producer/notes")
    assert len(res_get2.json()["notes"]) == 1
    assert res_get2.json()["notes"][0]["text"] == "Updated note with 4 images"
    assert len(res_get2.json()["notes"][0]["images"]) == 4

    # 5. Delete note
    res_del = client.delete(f"/api/producer/notes/{note_id}")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Verify deleted
    res_get3 = client.get("/api/producer/notes")
    assert res_get3.json()["notes"] == []


def test_producer_notes_reject_stale_bulk_revision(client, monkeypatch, tmp_path):
    monkeypatch.setattr(api_producer, "NOTES_FILE", tmp_path / "playbook_notes.json")

    initial = client.get("/api/producer/notes").json()
    note = {"text": "fresh note", "tag": "Hook"}
    added = client.post("/api/producer/notes/add", json=note)
    assert added.status_code == 200
    current = client.get("/api/producer/notes").json()
    assert current["revision"] != initial["revision"]

    stale = client.post(
        "/api/producer/notes",
        json={"notes": [], "base_revision": initial["revision"]},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["revision"] == current["revision"]
    assert stale.json()["detail"]["notes"] == current["notes"]


def test_producer_notes_reject_oversized_unuploaded_image(client, monkeypatch, tmp_path):
    monkeypatch.setattr(api_producer, "NOTES_FILE", tmp_path / "playbook_notes.json")
    oversized_data_url = "data:image/png;base64," + ("a" * 2_000_001)

    res = client.post(
        "/api/producer/notes/add",
        json={"text": "pending image", "images": [oversized_data_url]},
    )

    assert res.status_code == 400
    assert "อัปโหลดไม่เสร็จ" in res.json()["detail"]
