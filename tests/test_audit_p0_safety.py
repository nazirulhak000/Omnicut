"""Data-loss and media disclosure regressions; all files are temporary fixtures."""

import asyncio
import io
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient

from scripts.db import DocumentTable
from scripts import api_videos as videos


@pytest.mark.parametrize("invalid", [
    "", " \n\t", "[", "{}", "[null]", '[{"name":"missing id"}]',
    '[{"id":"good"},null]', '[{"id":null}]', '[{"id":""}]',
    '[{"id":"same"},{"id":"same"}]', '[{"id":[]}]',
])
def test_invalid_mirror_never_replaces_committed_records(tmp_path, invalid):
    mirror = tmp_path / "mirror.json"
    table = DocumentTable("audit", lambda: tmp_path / "store.db", lambda: mirror)
    original = [{"id": "original", "name": "preserve"}]
    table.save(original)
    stamp = mirror.stat().st_mtime_ns
    mirror.write_text(invalid, encoding="utf-8")
    os.utime(mirror, ns=(stamp + 1_000_000, stamp + 1_000_000))

    assert table.load() == original
    assert mirror.read_text(encoding="utf-8") == invalid
    # A later complete external edit must still be picked up.
    mirror.write_text('[{"id":"repaired"}]', encoding="utf-8")
    os.utime(mirror, ns=(stamp + 2_000_000, stamp + 2_000_000))
    assert table.load() == [{"id": "repaired"}]


def test_explicit_empty_snapshot_and_store_clear_remain_supported(tmp_path):
    mirror = tmp_path / "mirror.json"
    table = DocumentTable("audit", lambda: tmp_path / "store.db", lambda: mirror)
    table.save([{"id": "one"}])
    stamp = mirror.stat().st_mtime_ns
    mirror.write_text("[]", encoding="utf-8")
    os.utime(mirror, ns=(stamp + 1_000_000, stamp + 1_000_000))
    assert table.load() == []
    table.save([{"id": "two"}])
    table.save([])
    assert table.load() == []
    assert json.loads(mirror.read_text(encoding="utf-8")) == []


@pytest.fixture
def media_client(tmp_path, monkeypatch):
    monkeypatch.setattr(videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(videos, "CAPCUT_DRAFT_DIR", tmp_path / "capcut-drafts")
    app = FastAPI()
    app.include_router(videos.router)
    return TestClient(app)


@pytest.mark.parametrize("relative", [
    ".env", "frontend/.env", "_Docs/store.db", "scripts/config.py",
    "03_Projects/project/project.json", "03_Projects/project/.env",
    "03_Projects/.upload-staging/secret.mp4", "scripts/secret.mp4",
    "03_Projects/.cache/.checkpoint/frame.png", "03_Projects/project/private.html",
])
def test_media_denies_private_files_even_inside_workspace(tmp_path, media_client, relative):
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"synthetic-private-data")
    response = media_client.get("/api/media/" + relative)
    assert response.status_code == 403
    assert b"synthetic-private-data" not in response.content


@pytest.mark.parametrize("relative", [
    "00_Inbox/clip.mp4", "01_Raw/product/clip.MOV", "02_Assets/Fonts/font.ttf",
    "02_Assets/Fonts/font.woff2", "02_Assets/LUTs_ColorPresets/look.cube",
    "02_Assets/Refs/reference.webp", "03_Projects/project/voice.wav",
    "03_Projects/project/captions.srt", "03_Projects/project/captions.vtt",
    "03_Projects/.cache/filmstrips/strip.jpg", "04_Exports/Ready_to_post/video.mp4",
    "05_Covers_Thumbnails/.cache/cover.png", "06_Archive/Posted/video.mp4",
    "test_voice.wav", "capcut-drafts/project/resources/video.mp4",
])
def test_media_keeps_existing_asset_and_preview_contracts(tmp_path, media_client, relative):
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"fixture-media")
    response = media_client.get("/api/media/" + relative)
    assert response.status_code == 200
    assert response.content == b"fixture-media"


def test_media_rejects_link_to_private_file(tmp_path, media_client):
    secret = tmp_path / ".env"
    secret.write_bytes(b"synthetic-private-data")
    link = tmp_path / "01_Raw" / "innocent.mp4"
    link.parent.mkdir()
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("OS account cannot create symbolic links")
    assert media_client.get("/api/media/01_Raw/innocent.mp4").status_code == 403


@pytest.fixture
def upload_dirs(tmp_path, monkeypatch):
    for key, name in [("INBOX_DIR", "inbox"), ("RAW_DIR", "raw"),
                      ("ASSETS_DIR", "assets"), ("SFX_DIR", "sfx"), ("MUSIC_DIR", "music")]:
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(videos, key, directory)
    monkeypatch.setattr(videos.time, "time", lambda: 123456)
    monkeypatch.setattr(videos, "get_file_info", lambda p: {"path": str(p), "name": p.name})
    monkeypatch.setattr(videos.AssetRegistry, "rebuild", lambda: None)
    return tmp_path


def do_upload(payload, *, asset=False, filename="same.mp4"):
    file = UploadFile(filename=filename, file=io.BytesIO(payload))
    if asset:
        return asyncio.run(videos.upload_asset(file=file, asset_type="music"))
    return asyncio.run(videos.upload_file(file=file, target_dir="inbox", product_id=None, custom_name=None))


@pytest.mark.parametrize("asset", [False, True])
def test_repeated_same_name_uploads_preserve_every_payload(upload_dirs, asset):
    payloads = [b"first", b"second", b"third"]
    results = [do_upload(p, asset=asset, filename="same.wav") for p in payloads]
    paths = [Path(r["file"]["path"]) for r in results]
    assert len(set(paths)) == len(payloads)
    assert [p.read_bytes() for p in paths] == payloads


def test_concurrent_uploads_never_clobber_each_other(upload_dirs):
    barrier = threading.Barrier(8)
    def upload(index):
        payload = str(index).encode()
        barrier.wait(timeout=5)
        result = do_upload(payload)
        return Path(result["file"]["path"]), payload
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(upload, range(8)))
    assert len({p for p, _ in results}) == 8
    assert all(p.read_bytes() == payload for p, payload in results)


@pytest.mark.parametrize("failure", [OSError("upload disconnected"), asyncio.CancelledError()])
def test_failed_upload_never_publishes_partial_media(upload_dirs, failure):
    class InterruptedUpload:
        filename = "same.mp4"
        calls = 0
        async def read(self, size):
            self.calls += 1
            if self.calls == 1:
                return b"partial"
            raise failure
    original = videos.INBOX_DIR / "same.mp4"
    original.write_bytes(b"original")
    with pytest.raises(type(failure)):
        asyncio.run(videos.upload_file(file=InterruptedUpload(), target_dir="inbox", product_id=None, custom_name=None))
    assert list(videos.INBOX_DIR.iterdir()) == [original]
    assert original.read_bytes() == b"original"


def test_heic_conversion_never_overwrites_existing_jpeg(upload_dirs, monkeypatch):
    original = videos.INBOX_DIR / "photo.jpg"
    original.write_bytes(b"original-jpeg")
    def convert(command, **kwargs):
        Path(command[-1]).write_bytes(b"converted-jpeg")
    monkeypatch.setattr(videos.subprocess, "run", convert)
    result = do_upload(b"heic-source", filename="photo.heic")
    assert original.read_bytes() == b"original-jpeg"
    assert Path(result["file"]["path"]).read_bytes() == b"converted-jpeg"
    assert len(list(videos.INBOX_DIR.iterdir())) == 2
