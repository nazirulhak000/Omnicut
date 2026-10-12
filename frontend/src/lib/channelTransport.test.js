import test from 'node:test';
import assert from 'node:assert/strict';
import { createChannelRequestGuard } from './channelState.js';
import { createChannelTransport, projectApiPath, channelMediaData } from './channelTransport.js';

function transport(send) {
  const guard = createChannelRequestGuard('main');
  return { guard, request: createChannelTransport({ send, capture: () => guard.capture(),
    isCurrent: token => guard.isCurrent(token) }) };
}

test('dispatch captures owner and deep copies mutable JSON before transport', async () => {
  let sent;
  const body = { title: 'Original', nested: { text: 'Before' } };
  const { request } = transport(async options => { sent = options; return { headers: {}, data: {} }; });
  const pending = request({ url: '/api/products', method: 'post', data: body });
  body.nested.text = 'After';
  await pending;
  assert.equal(sent.headers['X-OmniCut-Channel'], 'main');
  assert.equal(sent.data.nested.text, 'Before');
});

test('late response after switching is rejected before data is consumed', async () => {
  let complete;
  const { request, guard } = transport(() => new Promise(resolve => { complete = resolve; }));
  const pending = request({ url: '/api/products' });
  guard.activate('second');
  complete({ headers: { 'X-OmniCut-Channel': 'main' }, data: { products: ['old'] } });
  await assert.rejects(pending, { code: 'channel_response_stale' });
});

test('late failed response cannot surface the old workspace error in a new channel', async () => {
  let reject;
  const { request, guard } = transport(() => new Promise((_, fail) => { reject = fail; }));
  const pending = request({ url: '/api/products' });
  guard.activate('second');
  reject(new Error('old owner provider failure'));
  await assert.rejects(pending, { code: 'channel_response_stale' });
});

test('foreign body and echoed owner fail closed', async () => {
  let calls = 0;
  const { request } = transport(async () => { calls++; return { headers: { 'X-OmniCut-Channel': 'second' } }; });
  await assert.rejects(request({ url: '/api/products', method: 'post', data: { channel_id: 'second' } }),
    { code: 'channel_scope_conflict' });
  assert.equal(calls, 0);
  await assert.rejects(request({ url: '/api/products' }), { code: 'channel_scope_conflict' });
});

test('registry traffic strips channel header and leaves profile owner intact', async () => {
  let sent;
  const { request } = transport(async options => { sent = options; return { headers: {}, data: {} }; });
  await request({ url: '/api/channels', method: 'post', data: { id: 'second', channel_id: 'second' } });
  assert.equal(sent.headers?.['X-OmniCut-Channel'], undefined);
  assert.equal(sent.data.channel_id, 'second');
});

test('multipart body is copied before dispatch and foreign scope is rejected', async () => {
  const form = new FormData();
  form.append('name', 'Before');
  let sent;
  const { request } = transport(async options => { sent = options; return { headers: {}, data: {} }; });
  const pending = request({ url: '/api/assets/upload', method: 'post', data: form });
  form.set('name', 'After');
  await pending;
  assert.equal(sent.data.get('name'), 'Before');
  form.append('channel_id', 'second');
  await assert.rejects(request({ url: '/api/assets/upload', method: 'post', data: form }),
    { code: 'channel_scope_conflict' });
});

test('media responses carry captured channel while external URLs remain unchanged', () => {
  const data = channelMediaData({ video: '/api/media/04_Exports/a.mp4',
    links: ['https://example.com/a.jpg', '/api/products'] }, { channelId: 'second' });
  assert.equal(data.video, '/api/media/04_Exports/a.mp4?channel=second');
  assert.deepEqual(data.links, ['https://example.com/a.jpg', '/api/products']);
});

test('nested project URL uses explicit route without slash-encoding ambiguity', () => {
  assert.equal(projectApiPath('legacy name'), '/projects/legacy%20name');
  assert.equal(projectApiPath('second/origin'), '/channel-projects/second/origin');
  assert.throws(() => projectApiPath('../secret'), { code: 'project_name_invalid' });
});
