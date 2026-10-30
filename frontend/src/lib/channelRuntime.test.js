import test from 'node:test';
import assert from 'node:assert/strict';

test('invalid explicit link blocks selection until recovery and clears old mobile entry intent', async () => {
  const values = new Map();
  const before = globalThis.window;
  globalThis.window = {
    location: { search: '?channel=BAD&mobile_session=oldA', href: 'https://local/?mode=mobile&channel=BAD&mobile_session=oldA' },
    sessionStorage: { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) },
    history: { replaceState: (_, __, value) => {
      window.location.href = value.toString(); window.location.search = new URL(value).search;
    } },
  };
  try {
    const runtime = await import('./channelRuntime.js?invalid-link-regression');
    assert.ok(runtime.channelSelectionError());
    const failedRevision = runtime.channelRuntimeRevision();
    runtime.activateChannel('main');
    assert.ok(runtime.channelRuntimeRevision() > failedRevision);
    assert.equal(runtime.channelSelectionError(), null);
    assert.equal(new URL(window.location.href).searchParams.get('mobile_session'), null);
    window.location.href = 'https://local/?mode=mobile&channel=main&mobile_session=ownedA&project=same&quick_post=1&mobile_post=1&pid=old&aid=angle&eid=export&video=private&film=1';
    runtime.activateChannel('second');
    const query = new URL(window.location.href).searchParams;
    assert.equal(query.get('channel'), 'second');
    assert.equal(query.get('mode'), 'mobile');
    assert.equal(query.get('mobile_session'), null);
    assert.equal(query.get('project'), null);
    for (const key of ['quick_post', 'mobile_post', 'pid', 'aid', 'eid', 'video', 'film']) assert.equal(query.get(key), null);
  } finally { globalThis.window = before; }
});

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { values, getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, String(value)) };
}

test('reopening the PWA (fresh session) restores the channel from localStorage; ?channel still wins', async () => {
  const before = globalThis.window;
  const local = memoryStorage({ 'omnicut:active_channel:v1': 'second' });
  globalThis.window = {
    location: { search: '', href: 'https://local/' },
    sessionStorage: memoryStorage(),
    localStorage: local,
    history: { replaceState: (_, __, value) => { window.location.href = value.toString(); window.location.search = new URL(value).search; } },
  };
  try {
    const runtime = await import('./channelRuntime.js?pwa-reopen');
    assert.equal(runtime.activeChannel(), 'second');
    runtime.activateChannel('third');
    assert.equal(local.values.get('omnicut:active_channel:v1'), 'third');
    assert.equal(window.sessionStorage.values.get('omnicut:active_channel:v1'), 'third');

    window.location.search = '?channel=main';
    window.location.href = 'https://local/?channel=main';
    const linked = await import('./channelRuntime.js?pwa-link-priority');
    assert.equal(linked.activeChannel(), 'main');
  } finally { globalThis.window = before; }
});

test('a blocked localStorage never blocks a channel switch', async () => {
  const before = globalThis.window;
  globalThis.window = {
    location: { search: '', href: 'https://local/' },
    sessionStorage: memoryStorage(),
    get localStorage() { throw new Error('SecurityError'); },
    history: { replaceState: (_, __, value) => { window.location.href = value.toString(); window.location.search = new URL(value).search; } },
  };
  try {
    const runtime = await import('./channelRuntime.js?blocked-local');
    assert.equal(runtime.activeChannel(), 'main');
    runtime.activateChannel('second');
    assert.equal(runtime.activeChannel(), 'second');
  } finally { globalThis.window = before; }
});
