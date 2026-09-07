import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from scripts.api_server import app
import scripts.api_tiktok_autopost as tap
import scripts.media_service as media
import scripts.api_exports as exports_api

client = TestClient(app)

@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    exports = tmp_path / '04_Exports' / 'Ready_to_post'
    covers = tmp_path / '05_Covers_Thumbnails'
    exports.mkdir(parents=True)
    covers.mkdir()
    monkeypatch.setattr(tap, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(tap, 'EXPORTS_DIR', exports)
    monkeypatch.setattr(tap, 'POSTED_DIR', tmp_path / '04_Exports' / 'Posted')
    monkeypatch.setattr(tap, 'COVERS_DIR', covers)
    monkeypatch.setattr(tap, '_pending', None)
    monkeypatch.setattr(media, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(media, 'COVERS_DIR', covers)


@pytest.mark.parametrize('suffix', ['_cover.jpg', '_cover_3x4.jpg'])
def test_export_cover_path_reaches_pending_job(suffix):
    video = tap.EXPORTS_DIR / 'review.mp4'
    video.write_bytes(b'fixture')
    cover = tap.COVERS_DIR / f'review{suffix}'
    cover.write_bytes(b'fixture')
    item = media.get_file_info(video)
    assert item['cover_path'] == f'05_Covers_Thumbnails/review{suffix}'
    response = client.post('/api/tiktok-autopost/prepare', json={
        'video_path': item['rel_path'], 'cover_path': item['cover_path'],
    })
    assert response.status_code == 200
    pending = client.get('/api/tiktok-autopost/pending').json()
    assert Path(pending['cover_path']) == cover.resolve()
    assert Path(pending['video_path']) == video.resolve()


def test_explicit_9x16_cover_uses_matching_tiktok_3x4_variant():
    video = tap.EXPORTS_DIR / 'review.mp4'
    video.write_bytes(b'fixture')
    cover_9x16 = tap.COVERS_DIR / 'review_cover.jpg'
    cover_3x4 = tap.COVERS_DIR / 'review_cover_3x4.jpg'
    cover_9x16.write_bytes(b'9x16')
    cover_3x4.write_bytes(b'3x4')

    response = client.post('/api/tiktok-autopost/prepare', json={
        'video_path': str(video),
        'cover_path': str(cover_9x16),
    })

    assert response.status_code == 200
    assert response.json()['cover_path'] == '05_Covers_Thumbnails/review_cover_3x4.jpg'
    pending = client.get('/api/tiktok-autopost/pending').json()
    assert Path(pending['cover_path']) == cover_3x4.resolve()


def test_missing_cover_does_not_replace_pending_job():
    video = tap.EXPORTS_DIR / 'review.mp4'
    video.write_bytes(b'fixture')
    previous = {'caption': 'previous job'}
    tap._pending = previous
    response = client.post('/api/tiktok-autopost/prepare', json={
        'video_path': str(video), 'cover_path': '05_Covers_Thumbnails/missing.jpg',
    })
    assert response.status_code == 404
    assert tap._pending == previous


def test_cover_update_refreshes_prepared_job_without_repreparing_video():
    video = tap.EXPORTS_DIR / 'review.mp4'
    video.write_bytes(b'fixture')
    old_cover = tap.COVERS_DIR / 'old.jpg'
    new_cover = tap.COVERS_DIR / 'new.jpg'
    old_cover.write_bytes(b'old')
    new_cover.write_bytes(b'new')
    assert client.post('/api/tiktok-autopost/prepare', json={
        'video_path': str(video), 'cover_path': str(old_cover),
    }).status_code == 200

    response = client.post('/api/tiktok-autopost/cover', json={
        'cover_path': '05_Covers_Thumbnails/new.jpg',
    })
    assert response.status_code == 200
    pending = client.get('/api/tiktok-autopost/pending').json()
    assert Path(pending['video_path']) == video.resolve()
    assert Path(pending['cover_path']) == new_cover.resolve()


def test_cover_update_uses_matching_tiktok_3x4_variant():
    video = tap.EXPORTS_DIR / 'review.mp4'
    video.write_bytes(b'fixture')
    cover_9x16 = tap.COVERS_DIR / 'review_cover.jpg'
    cover_3x4 = tap.COVERS_DIR / 'review_cover_3x4.jpg'
    cover_9x16.write_bytes(b'9x16')
    cover_3x4.write_bytes(b'3x4')
    assert client.post('/api/tiktok-autopost/prepare', json={
        'video_path': str(video),
        'cover_path': str(cover_9x16),
    }).status_code == 200

    response = client.post('/api/tiktok-autopost/cover', json={
        'cover_path': '05_Covers_Thumbnails/review_cover.jpg',
    })

    assert response.status_code == 200
    assert Path(response.json()['cover_path']) == cover_3x4.resolve()
    pending = client.get('/api/tiktok-autopost/pending').json()
    assert Path(pending['cover_path']) == cover_3x4.resolve()


def test_prepare_resolves_product_cover_when_request_path_is_missing(tmp_path, monkeypatch):
    video = tap.EXPORTS_DIR / 'logitech_wave_keys_new_angle_20260907_110509.mp4'
    video.write_bytes(b'fixture')
    cover = tap.COVERS_DIR / 'Logitech Wave Keys_cover_3x4.jpg'
    cover.write_bytes(b'cover')
    monkeypatch.setattr(tap.ProductStore, 'get_all', lambda: [{
        'id': 'product-1',
        'name': 'Logitech Wave Keys',
        'angles': [],
    }])

    response = client.post('/api/tiktok-autopost/prepare', json={
        'video_path': str(video),
        'product_id': 'product-1',
    })

    assert response.status_code == 200
    assert response.json()['cover_path'] == '05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg'
    pending = client.get('/api/tiktok-autopost/pending').json()
    assert Path(pending['cover_path']) == cover.resolve()


def test_pending_repairs_missing_cover_before_extension_reads_it(tmp_path, monkeypatch):
    video = tap.EXPORTS_DIR / 'logitech_wave_keys_new_angle.mp4'
    video.write_bytes(b'fixture')
    cover = tap.COVERS_DIR / 'Logitech Wave Keys_cover_3x4.jpg'
    cover.write_bytes(b'cover')
    monkeypatch.setattr(tap.ProductStore, 'get_all', lambda: [{
        'id': 'product-1',
        'name': 'Logitech Wave Keys',
        'angles': [],
    }])
    tap._pending = {
        'video_path': str(video.resolve()),
        'cover_path': None,
        'product_id': 'product-1',
        'angle_id': None,
        'product_name': None,
    }

    pending = client.get('/api/tiktok-autopost/pending').json()

    assert Path(pending['cover_path']) == cover.resolve()


def test_product_named_cover_fallback_is_case_insensitive(tmp_path, monkeypatch):
    covers = tmp_path / '05_Covers_Thumbnails'
    covers.mkdir(exist_ok=True)
    cover = covers / 'Logitech Wave Keys_cover.jpg'
    cover.write_bytes(b'cover')
    monkeypatch.setattr(exports_api, 'COVERS_DIR', covers)

    assert exports_api._find_product_cover('logitech wave keys') == cover


def test_project_named_cover_lookup_is_case_insensitive(tmp_path, monkeypatch):
    covers = tmp_path / '05_Covers_Thumbnails'
    covers.mkdir(exist_ok=True)
    cover = covers / 'LOG01-แกะกล่องว้าว_1_cover.jpg'
    cover.write_bytes(b'cover')
    monkeypatch.setattr(exports_api, 'COVERS_DIR', covers)

    assert exports_api._find_project_cover('log01-แกะกล่องว้าว_1') == cover


def test_list_exports_prefers_project_named_cover_over_product_fallback(tmp_path, monkeypatch):
    exports_dir = tmp_path / '04_Exports' / 'Ready_to_post'
    posted_dir = tmp_path / '04_Exports' / 'Posted'
    covers = tmp_path / '05_Covers_Thumbnails'
    exports_dir.mkdir(parents=True, exist_ok=True)
    posted_dir.mkdir(parents=True, exist_ok=True)
    covers.mkdir(parents=True, exist_ok=True)

    video = exports_dir / 'rendered.mp4'
    video.write_bytes(b'video')
    project_cover = covers / 'LOG01-แกะกล่องว้าว_1_cover.jpg'
    project_cover.write_bytes(b'project cover')
    product_cover = covers / 'Logitech Wave Keys_cover.jpg'
    product_cover.write_bytes(b'product cover')

    monkeypatch.setattr(exports_api, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(exports_api, 'EXPORTS_DIR', exports_dir)
    monkeypatch.setattr(exports_api, 'POSTED_DIR', posted_dir)
    monkeypatch.setattr(exports_api, 'COVERS_DIR', covers)
    monkeypatch.setattr(media, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(media, 'COVERS_DIR', covers)
    monkeypatch.setattr(exports_api.ProductStore, 'get_all', lambda: [{
        'id': 'product-1',
        'name': 'Logitech Wave Keys',
        'angles': [{
            'angle_id': 'unboxing',
            'project_name': 'LOG01-แกะกล่องว้าว_1',
            'video_url': '04_Exports/Ready_to_post/rendered.mp4',
            'status': 'rendered',
        }],
    }])

    item = exports_api.list_exports()['exports'][0]
    assert item['cover_path'] == '05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover.jpg'


def test_list_exports_promotes_3x4_cover_and_keeps_9x16_fallback(tmp_path, monkeypatch):
    exports_dir = tmp_path / '04_Exports' / 'Ready_to_post'
    posted_dir = tmp_path / '04_Exports' / 'Posted'
    covers = tmp_path / '05_Covers_Thumbnails'
    exports_dir.mkdir(parents=True, exist_ok=True)
    posted_dir.mkdir(parents=True, exist_ok=True)
    covers.mkdir(parents=True, exist_ok=True)

    video = exports_dir / 'rendered.mp4'
    video.write_bytes(b'video')
    cover_9x16 = covers / 'LOG01-review_1_cover.jpg'
    cover_3x4 = covers / 'LOG01-review_1_cover_3x4.jpg'
    cover_9x16.write_bytes(b'9x16')
    cover_3x4.write_bytes(b'3x4')

    monkeypatch.setattr(exports_api, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(exports_api, 'EXPORTS_DIR', exports_dir)
    monkeypatch.setattr(exports_api, 'POSTED_DIR', posted_dir)
    monkeypatch.setattr(exports_api, 'COVERS_DIR', covers)
    monkeypatch.setattr(media, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(media, 'COVERS_DIR', covers)
    monkeypatch.setattr(exports_api.ProductStore, 'get_all', lambda: [{
        'id': 'product-1',
        'name': 'Logitech Wave Keys',
        'angles': [{
            'angle_id': 'review',
            'project_name': 'LOG01-review_1',
            'video_url': '04_Exports/Ready_to_post/rendered.mp4',
            'status': 'rendered',
        }],
    }])

    item = exports_api.list_exports()['exports'][0]
    assert item['cover_path'] == '05_Covers_Thumbnails/LOG01-review_1_cover_3x4.jpg'
    assert item['cover_3x4_path'] == '05_Covers_Thumbnails/LOG01-review_1_cover_3x4.jpg'
    assert item['cover_9x16_path'] == '05_Covers_Thumbnails/LOG01-review_1_cover.jpg'

def test_prepare_and_get_pending_with_schedule_time(tmp_path, monkeypatch):
    # Ensure pending is cleared first
    tap._pending = None

    # Create dummy mp4 file under EXPORTS_DIR
    dummy_video = tap.EXPORTS_DIR / "dummy_test_schedule.mp4"
    dummy_video.write_bytes(b"dummy")

    try:
        res = client.post("/api/tiktok-autopost/prepare", json={
            "video_path": str(dummy_video),
            "caption": "Test caption",
            "hashtags": "#test",
            "product_id": "p123",
            "angle_id": "a456",
            "tiktok_product_id": "1737088044189583209",
            "schedule_time": "12:30",
        })
        assert res.status_code == 200
        assert res.json() == {"success": True, "cover_path": None}

        # Check pending
        pending_res = client.get("/api/tiktok-autopost/pending")
        assert pending_res.status_code == 200
        data = pending_res.json()
        assert data["caption"] == "Test caption"
        assert data["schedule_time"] == "12:30"
        assert data["tiktok_product_id"] == "1737088044189583209"

        # Clear pending
        clear_res = client.post("/api/tiktok-autopost/clear")
        assert clear_res.status_code == 200

        # Should now be 404
        assert client.get("/api/tiktok-autopost/pending").status_code == 404
    finally:
        if dummy_video.exists():
            dummy_video.unlink()
