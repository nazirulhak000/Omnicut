"""Safety contracts for /api/delete-file (trash fallback) and /api/raw-vault/batch-delete."""

from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from scripts import api_videos
from scripts.api_server import app
from scripts.product_store import ProductStore


def _patch_roots(monkeypatch, tmp_path):
    inbox = tmp_path / "00_Inbox"
    raw = tmp_path / "01_Raw"
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    archive = tmp_path / "06_Archive"
    for d in (inbox, raw, exports, posted, archive):
        d.mkdir(parents=True)
    monkeypatch.setattr(api_videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_videos, "INBOX_DIR", inbox)
    monkeypatch.setattr(api_videos, "RAW_DIR", raw)
    monkeypatch.setattr(api_videos, "ARCHIVE_DIR", archive)
    monkeypatch.setattr(ProductStore, "_load", lambda: [])
    monkeypatch.setattr(ProductStore, "rollback_by_video_or_project", lambda *a, **k: [])
    return inbox, raw, exports, posted, archive


def _lock_unlink(monkeypatch, locked_name):
    """Make Path.unlink raise PermissionError for one file name (simulated lock)."""
    real_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        if self.name == locked_name:
            raise PermissionError("locked")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fake_unlink)
    monkeypatch.setattr(api_videos.time, "sleep", lambda *_: None)


def test_locked_file_is_moved_to_trash_and_kept(monkeypatch, tmp_path):
    inbox, _, _, _, archive = _patch_roots(monkeypatch, tmp_path)
    target = inbox / "locked_clip.mp4"
    target.write_bytes(b"precious bytes")
    _lock_unlink(monkeypatch, "locked_clip.mp4")

    resp = TestClient(app).post("/api/delete-file", json={"file_path": str(target)})

    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
    assert resp.json()["filename"] == "locked_clip.mp4"
    assert not target.exists()
    kept = list((archive / ".trash").glob("*locked_clip.mp4"))
    assert len(kept) == 1
    assert kept[0].read_bytes() == b"precious bytes"


def test_trash_names_never_collide(monkeypatch, tmp_path):
    inbox, _, _, _, archive = _patch_roots(monkeypatch, tmp_path)
    for i in range(2):
        f = inbox / "same.mp4"
        f.write_bytes(f"v{i}".encode())
        api_videos._move_to_trash(f)
    assert len(list((archive / ".trash").glob("*same.mp4"))) == 2


def test_posted_folder_still_protected(monkeypatch, tmp_path):
    _, _, _, posted, archive = _patch_roots(monkeypatch, tmp_path)
    proof = posted / "proof.mp4"
    proof.write_bytes(b"posted proof")
    _lock_unlink(monkeypatch, "proof.mp4")

    resp = TestClient(app).post("/api/delete-file", json={"file_path": str(proof)})

    assert resp.status_code == 400
    assert proof.exists()
    assert not (archive / ".trash").exists() or not list((archive / ".trash").iterdir())


def test_fails_closed_when_trash_move_fails(monkeypatch, tmp_path):
    inbox, _, _, _, _ = _patch_roots(monkeypatch, tmp_path)
    target = inbox / "stuck.mp4"
    target.write_bytes(b"stuck")
    _lock_unlink(monkeypatch, "stuck.mp4")

    def boom(_src):
        raise PermissionError("still locked")

    monkeypatch.setattr(api_videos, "_move_to_trash", boom)
    resp = TestClient(app).post("/api/delete-file", json={"file_path": str(target)})

    assert resp.status_code == 500
    assert target.exists()


def test_batch_delete_trashes_and_keeps_other_products_same_named_reference(monkeypatch, tmp_path):
    _, raw, _, _, archive = _patch_roots(monkeypatch, tmp_path)
    (raw / "A").mkdir()
    (raw / "B").mkdir()
    clip_a = raw / "A" / "clip.mp4"
    clip_b = raw / "B" / "clip.mp4"
    clip_a.write_bytes(b"clip A")
    clip_b.write_bytes(b"clip B")

    products = [
        {"id": "pa", "videos": [
            {"name": "clip.mp4", "path": str(clip_a.resolve()), "rel_path": "01_Raw/A/clip.mp4"},
        ]},
        {"id": "pb", "videos": [
            {"name": "clip.mp4", "path": str(clip_b.resolve()), "rel_path": "01_Raw/B/clip.mp4"},
        ]},
    ]

    @contextmanager
    def fake_mutate():
        yield products

    monkeypatch.setattr(ProductStore, "_mutate", staticmethod(fake_mutate))

    resp = TestClient(app).post("/api/raw-vault/batch-delete", json={"video_paths": [str(clip_a)]})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["deleted_count"] == 1
    assert body["errors"] == []
    # File is trashed (recoverable), not destroyed; the other clip is untouched.
    assert not clip_a.exists()
    assert clip_b.exists()
    kept = list((archive / ".trash").glob("*clip.mp4"))
    assert len(kept) == 1 and kept[0].read_bytes() == b"clip A"
    # Only the matching reference is dropped.
    assert products[0]["videos"] == []
    assert len(products[1]["videos"]) == 1
    assert products[1]["videos"][0]["path"] == str(clip_b.resolve())
