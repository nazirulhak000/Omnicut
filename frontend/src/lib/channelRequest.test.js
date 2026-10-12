import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  CHANNEL_HEADER, createChannelRequestContext, prepareChannelRequest,
  scopedMediaUrl, assertChannelResponseScope,
} from './channelRequest.js';

const main = createChannelRequestContext({ channelId: 'main' });
const second = createChannelRequestContext({ channelId: 'tech_th' });
const compat = createChannelRequestContext({ compat: true });
const code = expected => error => error.code === expected;
const prepare = (options, context = main, scope = 'channel') => prepareChannelRequest(context, options, { scope });

test('explicit context snapshots ID and rejects normalization, empty and malformed IDs', () => {
  const selection = { channelId: 'main' };
  const context = createChannelRequestContext(selection);
  selection.channelId = 'tech_th';
  assert.equal(context.channelId, 'main');
  assert.ok(Object.isFrozen(context));
  assert.throws(() => createChannelRequestContext(), code('channel_scope_missing'));
  for (const id of ['', 'Main', ' main', 'main\n', 'a', 'a'.repeat(33), 42]) {
    assert.throws(() => createChannelRequestContext({ channelId: id }), code('channel_scope_invalid'));
  }
});

test('complete config is copied without mutation and concurrent scopes stay separate', () => {
  const controller = new AbortController();
  const options = { url: '/api/products', method: 'POST', timeout: 1234,
    headers: { Accept: 'application/json' }, data: { channel_id: 'main', nested: { tags: ['x'] } },
    params: { page: 2 }, signal: controller.signal, responseType: 'json' };
  const before = structuredClone({ ...options, signal: undefined });
  const prepared = prepare(options);
  assert.deepEqual({ ...options, signal: undefined }, before);
  assert.equal(prepared.signal, controller.signal);
  assert.equal(prepared.timeout, 1234);
  assert.equal(prepared.headers[CHANNEL_HEADER], 'main');
  assert.equal(prepare({ url: '/api/products' }, second).headers[CHANNEL_HEADER], 'tech_th');
  options.data.nested.tags.push('changed');
  options.params.page = 7;
  options.headers.Accept = 'text/plain';
  assert.deepEqual(prepared.data.nested.tags, ['x']);
  assert.equal(prepared.params.page, 2);
  assert.equal(prepared.headers.Accept, 'application/json');
  assert.ok(Object.isFrozen(prepared.data.nested.tags));
  assert.throws(() => { prepared.headers[CHANNEL_HEADER] = 'tech_th'; }, TypeError);
});

test('scope classification is explicit; global and shared do not guess channel from URL', () => {
  assert.throws(() => prepareChannelRequest(main, { url: '/api/status' }), code('channel_policy_missing'));
  for (const scope of ['global', 'shared']) {
    assert.equal(prepare({ url: '/api/status' }, main, scope).headers[CHANNEL_HEADER], 'main');
    assert.deepEqual(prepare({ url: '/api/status' }, compat, scope), { url: '/api/status' });
  }
});

test('explicit compat preserves unscoped request shape, including existing options', () => {
  const options = { url: '/api/products', method: 'get', headers: { Accept: '*/*' }, params: { q: 'x' } };
  assert.deepEqual(prepare(options, compat), options);
  assert.deepEqual(prepare({ url: '/api/products' }, compat), { url: '/api/products' });
});

test('case-insensitive header duplicates reject conflicts and invalid explicit scope', () => {
  assert.equal(prepare({ url: '/api/products', headers: {
    'x-omnicut-channel': 'main', 'X-OmniCut-Channel': 'main', Accept: '*/*',
  } }).headers[CHANNEL_HEADER], 'main');
  for (const headers of [
    { 'x-omnicut-channel': 'tech_th' },
    [['X-OmniCut-Channel', 'main'], ['x-omnicut-channel', 'tech_th']],
    { [CHANNEL_HEADER]: ['main', 'tech_th'] },
  ]) assert.throws(() => prepare({ url: '/api/products', headers }), code('channel_scope_conflict'));
  for (const value of ['', 'Main', 'main, main']) {
    assert.throws(() => prepare({ url: '/api/products', headers: { [CHANNEL_HEADER]: value } }), code('channel_scope_invalid'));
  }
  assert.equal(prepare({ url: '/api/products', headers: new Headers({ [CHANNEL_HEADER]: 'main' }) }).headers[CHANNEL_HEADER], 'main');
});

test('body conflict checks support axios data, JSON fetch body and repeated FormData fields', () => {
  for (const key of ['data', 'body']) {
    assert.throws(() => prepare({ url: '/api/products', [key]: { channel_id: 'tech_th' } }), code('channel_scope_conflict'));
    assert.throws(() => prepare({ url: '/api/products', [key]: '{"channel_id":"tech_th"}' }), code('channel_scope_conflict'));
    assert.throws(() => prepare({ url: '/api/products', [key]: { channel_id: '' } }), code('channel_scope_invalid'));
  }
  const form = new FormData();
  form.append('channel_id', 'main');
  form.append('channel_id', 'tech_th');
  assert.throws(() => prepare({ url: '/api/upload', body: form }), code('channel_scope_conflict'));
  assert.throws(() => prepare({ url: '/api/products', headers: { [CHANNEL_HEADER]: 'main' }, data: { channel_id: 'tech_th' } }, compat), code('channel_scope_conflict'));
});

test('registry recovery strips stale headers and accepts stale malformed selection', () => {
  const stale = { channelId: 'OLD INVALID ID' };
  for (const url of ['/api/channels', '/api/channels/main', '/api/channels/main/readiness', '/api/channels/main/activate']) {
    const options = { url, headers: { [CHANNEL_HEADER]: 'bad ID', 'x-omnicut-channel': 'other', Accept: 'json' }, data: { channel_id: 'tech_th' } };
    const prepared = prepareChannelRequest(stale, options);
    assert.deepEqual(prepared.headers, { Accept: 'json' });
    assert.equal(options.headers[CHANNEL_HEADER], 'bad ID');
    assert.deepEqual(prepared.data, options.data);
  }
  assert.throws(() => prepareChannelRequest(stale, { url: '/api/channels-other' }), code('channel_scope_invalid'));
});

test('all policy query-enabled GET paths are supported, including currently shared media', () => {
  const policy = JSON.parse(readFileSync(new URL('../../../scripts/channel_route_policy.json', import.meta.url), 'utf8'));
  const rows = policy.routes.filter(row => row.allow_query_scope);
  assert.equal(rows.length, 7);
  for (const row of rows) {
    const path = row.path.replace(/\{[^}]+\}/g, 'sample');
    assert.equal(scopedMediaUrl(path, main), `${path}?channel=main`);
    assert.equal(prepare({ url: `${path}?channel=main` }, main, row.scope).headers[CHANNEL_HEADER], 'main');
    assert.throws(() => prepare({ url: `${path}?channel=main`, method: 'POST' }), code('channel_query_not_allowed'));
  }
});

test('media URL preserves encoded file path, all query spelling and hash', () => {
  const url = '/api/media/folder/%E0%B8%81%20x%23.mp4?path=a%2Fb&v=1+2#t=3';
  assert.equal(scopedMediaUrl(url, second), `${url.split('#')[0]}&channel=tech_th#t=3`);
  assert.equal(scopedMediaUrl('/api/editor/filmstrip?', main), '/api/editor/filmstrip?channel=main');
  assert.equal(scopedMediaUrl('/api/media/folder%2Fclip.mp4', main), '/api/media/folder%2Fclip.mp4?channel=main');
  assert.equal(scopedMediaUrl(url, compat), url);
  assert.equal(scopedMediaUrl('/api/media/a?channel=main#t=1', main), '/api/media/a?channel=main#t=1');
});

test('query conflicts, malformed values, duplicates and unapproved routes fail closed', () => {
  for (const query of ['channel=tech_th', 'channel=main&channel=tech_th']) {
    assert.throws(() => scopedMediaUrl(`/api/media/a?${query}`, main), code('channel_scope_conflict'));
  }
  assert.equal(scopedMediaUrl('/api/media/a?channel=main&channel=main', main), '/api/media/a?channel=main&channel=main');
  for (const query of ['channel=', 'channel=Main']) {
    assert.throws(() => scopedMediaUrl(`/api/media/a?${query}`, main), code('channel_scope_invalid'));
  }
  for (const path of ['/api/products', '/api/media', '/api/editor/filmstrip/extra', '/api/producer/ref-media/a/b', '/api/producer/ref-media/a%2Fb', '/api/channels']) {
    assert.throws(() => scopedMediaUrl(path, main), code('channel_query_not_allowed'));
    assert.throws(() => prepare({ url: `${path}?channel=main` }), code('channel_query_not_allowed'));
  }
});

test('transport params cannot bypass URL query allowlist or scope conflict checks', () => {
  for (const params of [{ channel: 'main' }]) {
    assert.throws(() => prepare({ url: '/api/products', params }), code('channel_query_not_allowed'));
    assert.throws(() => prepare({ url: '/api/channels', params }), code('channel_query_not_allowed'));
    assert.equal(prepare({ url: '/api/media/a', params }).headers[CHANNEL_HEADER], 'main');
  }
  assert.throws(() => prepare({ url: '/api/media/a', params: new URLSearchParams('channel=main') }), code('channel_request_unsupported'));
  for (const params of [{ channel: 'tech_th' }, { channel: ['main', 'tech_th'] }, new URLSearchParams('channel=main&channel=tech_th')]) {
    assert.throws(() => prepare({ url: '/api/media/a', params }), code('channel_scope_conflict'));
  }
  for (const channel of ['', null, undefined, 'Main']) {
    assert.throws(() => prepare({ url: '/api/media/a', params: { channel } }), code('channel_scope_invalid'));
  }
  assert.throws(() => prepare({ url: '/api/media/a?channel=tech_th', params: { channel: 'main' } }), code('channel_scope_conflict'));
});

test('foreign origins and ambiguous URLs cannot receive channel data or auth headers', () => {
  const origin = 'https://studio.example';
  for (const url of ['https://evil.example/api/media/a', '//evil.example/api/media/a', 'https://studio.example.evil/api/media/a', 'https://user:pass@studio.example/api/media/a']) {
    assert.throws(() => scopedMediaUrl(url, main, { origin }), code('channel_url_external'));
    assert.throws(() => prepareChannelRequest(main, { url, headers: { Authorization: 'secret' } }, { scope: 'channel', origin }), code('channel_url_external'));
  }
  assert.throws(() => scopedMediaUrl('https://studio.example/api/media/a', main), code('channel_url_external'));
  assert.equal(scopedMediaUrl('https://studio.example/api/media/a', main, { origin }), 'https://studio.example/api/media/a?channel=main');
  for (const url of ['/api/media/../a', '/api/media/%2e%2e/a', '/api/media/a%2F..%2Fb', '/api/media/a\\b', '/api/media/%ZZ', ' /api/media/a', '/api/media/a\n']) {
    assert.throws(() => scopedMediaUrl(url, main), code('channel_url_invalid'));
  }
});

test('axios baseURL cannot redirect scoped config or change classified route prefix', () => {
  const options = { url: '/api/products', headers: { Authorization: 'secret' } };
  const origin = 'https://studio.example';
  for (const baseURL of ['https://evil.example', '//evil.example', '//studio.example', 'https://user:pass@studio.example']) {
    assert.throws(() => prepareChannelRequest(main, { ...options, baseURL }, { scope: 'channel', origin }), code('channel_url_external'));
  }
  for (const baseURL of ['/api', 'https://studio.example/api', '/?channel=other']) {
    assert.throws(() => prepareChannelRequest(main, { ...options, baseURL }, { scope: 'channel', origin }), code('channel_url_invalid'));
  }
  assert.equal(prepareChannelRequest(main, { ...options, baseURL: origin }, { scope: 'channel', origin }).baseURL, origin);
  assert.equal(prepare({ ...options, baseURL: '/' }).baseURL, '/');
  assert.throws(() => prepare({ ...options, baseURL: origin }), code('channel_url_external'));
});

test('mutable native scope carriers are rejected before a later setter can change scope', () => {
  const body = new FormData();
  body.append('channel_id', 'main');
  body.append('title', 'test');
  const params = new URLSearchParams('channel=main&v=1');
  const headers = new Headers({ Accept: '*/*' });
  assert.throws(() => prepare({ url: '/api/media/a', body }), code('channel_request_unsupported'));
  assert.throws(() => prepare({ url: '/api/media/a', params }), code('channel_request_unsupported'));
  assert.throws(() => prepare({ url: '/api/products', headers }, compat), code('channel_request_unsupported'));
  body.set('channel_id', 'tech_th');
  params.set('channel', 'tech_th');
  headers.set(CHANNEL_HEADER, 'tech_th');
  assert.throws(() => prepare({ url: '/api/media/a', body }), code('channel_scope_conflict'));
  assert.throws(() => prepare({ url: '/api/media/a', params }), code('channel_scope_conflict'));
  assert.throws(() => prepare({ url: '/api/products', headers }), code('channel_scope_conflict'));
  for (const option of ['transformRequest', 'paramsSerializer', 'adapter']) {
    assert.throws(() => prepare({ url: '/api/products', [option]: () => {} }), code('channel_request_unsupported'));
  }
});

test('null-prototype payload maps also preserve immutable channel fields', () => {
  const data = Object.assign(Object.create(null), { channel_id: 'main', title: 'test' });
  const prepared = prepare({ url: '/api/products', data });
  data.channel_id = 'tech_th';
  assert.equal(prepared.data.channel_id, 'main');
  assert.ok(Object.isFrozen(prepared.data));
});

test('serializer hooks, custom prototypes, accessors and cycles cannot rewrite wire scope', () => {
  class OwnerCarrier { constructor() { this.channel_id = 'main'; } }
  const cyclic = { channel_id: 'main' };
  cyclic.self = cyclic;
  const accessor = { get channel_id() { return 'main'; } };
  const hook = { channel_id: 'main', toJSON() { return { channel_id: 'tech_th' }; } };
  for (const value of [hook, new OwnerCarrier(), cyclic, accessor, { nested: { toJSON() { return 'changed'; } } }]) {
    for (const field of ['data', 'body', 'params']) {
      assert.throws(() => prepare({ url: '/api/products', [field]: value }), code('channel_request_unsupported'));
    }
  }
  const prepared = prepare({ url: '/api/products', data: { channel_id: 'main', nested: [1, 'two', null] } });
  assert.equal(JSON.parse(JSON.stringify(prepared.data)).channel_id, 'main');
  const blob = new Blob(['binary'], { type: 'application/octet-stream' });
  assert.equal(prepare({ url: '/api/upload', data: blob }).data, blob);
});

test('config getters and plain header serializers are rejected before alternate reads', () => {
  let reads = 0;
  const options = { url: '/api/products', get data() { reads += 1; return { channel_id: reads === 1 ? 'main' : 'tech_th' }; } };
  assert.throws(() => prepare(options), code('channel_request_unsupported'));
  assert.equal(reads, 0);
  const headers = { Accept: '*/*', toJSON() { return { [CHANNEL_HEADER]: 'tech_th' }; } };
  assert.throws(() => prepare({ url: '/api/products', headers }, compat), code('channel_request_unsupported'));
});

test('response guard rejects mismatches and tolerates absent compat echo', () => {
  assert.equal(assertChannelResponseScope(compat, {}), true);
  assert.equal(assertChannelResponseScope(main, new Headers({ [CHANNEL_HEADER]: 'main' })), true);
  assert.throws(() => assertChannelResponseScope(main, { 'x-omnicut-channel': 'tech_th' }), code('channel_scope_conflict'));
  assert.throws(() => assertChannelResponseScope(main, { [CHANNEL_HEADER]: 'Main' }), code('channel_scope_invalid'));
});
