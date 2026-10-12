"""Offline P3-E ownership boundaries, with every store and media path in tmp_path."""
import json

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from scripts import api_analytics, api_producer, api_tiktok_stats, config, post_log, product_store, schedule_store, tiktok_pending
from scripts.channel_scope import ChannelScope, get_channel_scope
from scripts.tiktok_pending import TikTokPending, TikTokIgnored


@pytest.fixture
def env(tmp_path, monkeypatch):
    docs = tmp_path / '_Docs'
    docs.mkdir()
    monkeypatch.delenv(config.MULTI_CHANNEL_STRICT_ENV, raising=False)
    for module in (api_producer, product_store, tiktok_pending):
        monkeypatch.setattr(module, 'BASE_DIR', tmp_path)
    for module, key, name in [
        (product_store, 'STORE_PATH', 'products.json'),
        (post_log, 'LOG_PATH', 'posts.json'),
        (schedule_store, 'SCHEDULE_QUEUE_PATH', 'queue.json'),
        (tiktok_pending, 'PENDING_PATH', 'pending.json'),
        (tiktok_pending, 'IGNORED_PATH', 'ignored.json'),
    ]:
        monkeypatch.setattr(module, key, docs / name)
    refs = tmp_path / '02_Assets' / 'Refs'
    refs.mkdir(parents=True)
    monkeypatch.setattr(api_producer, 'ASSETS_DIR', refs.parent)
    monkeypatch.setattr(api_producer, 'REFS_DIR', refs)
    monkeypatch.setattr(api_producer, 'NOTES_FILE', refs / 'notes.json')

    # Test router boundaries independently of the already-tested scope middleware.
    def request_scope(channel: str = Header(None, alias='X-OmniCut-Channel')):
        owner = channel or 'main'
        return ChannelScope(owner, 'header' if channel else 'default', False,
                            channel={'id': owner, 'status': 'archived' if owner == 'old' else 'active'})
    app = FastAPI()
    app.dependency_overrides[get_channel_scope] = request_scope
    for router in (api_producer.router, api_analytics.router, api_tiktok_stats.router):
        app.include_router(router)
    return tmp_path, TestClient(app)


def test_sync_and_ignored_identity_are_channel_local(env):
    root, client = env
    row = {'video_id': 'same', 'title': 'same title'}
    TikTokPending.replace_from_sync([row], 'a', channel_id='main')
    TikTokPending.replace_from_sync([row], 'b', channel_id='second')
    second = TikTokPending.list_rows(channel_id='second')[0]
    assert client.post('/api/tiktok-stats/pending/ignore', json={'pending_id': second['id']}).status_code == 404
    ignored = TikTokPending.ignore(second['id'], channel_id='second')
    TikTokPending.replace_from_sync([row], 'c', channel_id='main')
    TikTokPending.replace_from_sync([row], 'd', channel_id='second')
    assert len(TikTokPending.list_rows(channel_id='main')) == 1
    assert TikTokPending.list_rows(channel_id='second') == []
    TikTokPending.restore(ignored['id'], channel_id='second')
    assert len(TikTokPending.list_rows(channel_id='second')) == 1
    assert TikTokIgnored.list_rows(channel_id='second') == []


def test_sync_no_nested_writer_when_ignored_mirror_needs_import(env):
    root, _ = env
    tiktok_pending.IGNORED_PATH.write_text(json.dumps([{'id': 'legacy', 'video_id': 'skip'}]), encoding='utf-8')
    assert TikTokPending.replace_from_sync([{'video_id': 'skip'}, {'video_id': 'keep'}], 'now', channel_id='main') == 1
    assert TikTokPending.list_rows(channel_id='main')[0]['video_id'] == 'keep'


def test_restore_failure_retains_source_and_retry_deduplicates(env, monkeypatch):
    _, _client = env
    ignored = TikTokIgnored.add({'video_id': 'retry'}, channel_id='second')
    original = TikTokIgnored.remove
    monkeypatch.setattr(TikTokIgnored, 'remove', classmethod(lambda cls, *args, **kwargs: (_ for _ in ()).throw(OSError('interrupt'))))
    with pytest.raises(OSError):
        TikTokPending.restore(ignored['id'], channel_id='second')
    assert len(TikTokPending.list_rows(channel_id='second')) == 1
    assert TikTokIgnored.get(ignored['id'], channel_id='second')
    monkeypatch.setattr(TikTokIgnored, 'remove', original)
    TikTokPending.restore(ignored['id'], channel_id='second')
    assert len(TikTokPending.list_rows(channel_id='second')) == 1
    assert TikTokIgnored.list_rows(channel_id='second') == []


def test_implicit_main_http_filters_foreign_posts_and_pending(env):
    _, client = env
    for owner in ['main', 'second']:
        TikTokPending.replace_from_sync([{'video_id': owner}], 'now', channel_id=owner)
        with post_log._TABLE.scoped_mutate(owner) as rows:
            rows.append({'id': owner, 'channel_id': owner, 'tiktok_video_id': owner, 'metrics': {'views': 5000}})
    assert [row['video_id'] for row in client.get('/api/tiktok-stats/pending').json()['rows']] == ['main']
    assert [row['id'] for row in client.get('/api/tiktok-stats/latest').json()['posts']] == ['main']
    second = client.get('/api/tiktok-stats/latest', headers={'X-OmniCut-Channel': 'second'}).json()
    assert [row['id'] for row in second['posts']] == ['second']


def test_candidates_and_analytics_use_effective_owner(env):
    _, client = env
    with product_store._TABLE.mutate() as rows:
        for owner in ['main', 'second']:
            rows.append({'id': owner, 'channel_id': owner, 'name': owner,
                         'angles': [{'angle_id': owner, 'hook_title': owner, 'status': 'rendered', 'video_url': owner + '.mp4'}]})
    assert {row['product_name'] for row in client.get('/api/tiktok-stats/clip-candidates').json()['candidates']} == {'main'}
    production = client.get('/api/analytics/production')
    assert production.status_code == 200
    assert production.json()['summary']['total_angles'] == 1
    inventory = client.get('/api/analytics/inventory', headers={'X-OmniCut-Channel': 'second'})
    assert inventory.status_code == 200
    assert inventory.json()['summary']['total_products'] == 1


def test_foreign_candidate_cannot_be_attached(env):
    _, client = env
    TikTokPending.replace_from_sync([{'video_id': 'pending'}], 'now', channel_id='main')
    row = TikTokPending.list_rows(channel_id='main')[0]
    response = client.post('/api/tiktok-stats/attach', json={'pending_id': row['id'], 'candidate': {'clip_file': 'foreign.mp4'}})
    assert response.status_code == 404
    assert TikTokPending.get(row['id'], channel_id='main')


def test_notes_and_reference_media_are_channel_local(env):
    root, client = env
    for owner in ['main', 'second']:
        headers = {} if owner == 'main' else {'X-OmniCut-Channel': owner}
        assert client.post('/api/producer/notes', headers=headers, json={'notes': [{'id': 'same', 'text': owner}]}).status_code == 200
        response = client.post('/api/producer/upload-ref-media', headers=headers, files={'file': ('sample.png', b'png', 'image/png')})
        assert response.status_code == 200
        name = response.json()['filename']
        assert client.get('/api/producer/ref-media/' + name, headers=headers).status_code == 200
        foreign = {'X-OmniCut-Channel': 'second' if owner == 'main' else 'main'}
        assert client.get('/api/producer/ref-media/' + name, headers=foreign).status_code == 404
    assert client.get('/api/producer/notes').json()['notes'][0]['text'] == 'main'
    assert client.get('/api/producer/notes', headers={'X-OmniCut-Channel': 'second'}).json()['notes'][0]['text'] == 'second'
    foreign_note = client.post('/api/producer/notes', json={'notes': [{'id': 'x', 'channel_id': 'second', 'text': 'wrong'}]})
    assert foreign_note.status_code == 422


def test_archived_mutations_block_before_storage(env):
    root, client = env
    headers = {'X-OmniCut-Channel': 'old'}
    assert client.post('/api/producer/notes', headers=headers, json={'notes': []}).status_code == 409
    assert client.post('/api/tiktok-stats/pending/ignore-all', headers=headers).status_code == 409
    assert not (root / '_Docs' / 'producer' / 'old').exists()
