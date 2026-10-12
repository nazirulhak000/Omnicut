import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ACTIVE_CHANNEL_KEY, channelCacheKey, readChannelCache, writeChannelCache,
  migrateLegacyMain, readActiveChannel, writeActiveChannel,
  createChannelRequestGuard, decideChannelSwitch,
} from './channelState.js';

function fakeStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    values,
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); },
  };
}

test('channel/resource cache keys isolate channels and ambiguous resource names', () => {
  assert.notEqual(channelCacheKey('main', 'tasks'), channelCacheKey('second', 'tasks'));
  assert.notEqual(channelCacheKey('main', 'a:b'), channelCacheKey('main', 'a%3Ab'));
  for (const id of ['Main', '', '../main', 'main\n', null]) {
    assert.throws(() => channelCacheKey(id, 'tasks'), { code: 'channel_scope_invalid' });
  }
  assert.throws(() => channelCacheKey('main', ''), TypeError);
});

test('cache round trips copied data independently per channel', () => {
  const storage = fakeStorage();
  const data = { channel_id: 'main', tasks: ['one'] };
  writeChannelCache(storage, 'main', 'tasks', data);
  data.tasks.push('mutated');
  writeChannelCache(storage, 'second', 'tasks', { channel_id: 'second', tasks: ['two'] });
  assert.deepEqual(readChannelCache(storage, 'main', 'tasks').tasks, ['one']);
  assert.deepEqual(readChannelCache(storage, 'second', 'tasks').tasks, ['two']);
  assert.equal(readChannelCache(storage, 'third', 'tasks'), null);
});

test('malformed/versionless/wrong owner caches are refused without deleting evidence', () => {
  const key = channelCacheKey('main', 'tasks');
  const candidates = ['bad json', 'null', '[]', '{"data":1}',
    '{"schema_version":2,"channel_id":"main","data":1}',
    '{"schema_version":1,"channel_id":"Main","data":1}',
    '{"schema_version":1,"channel_id":"second","data":1}',
    '{"schema_version":1,"channel_id":"main","data":{"channel_id":"second"}}'];
  for (const raw of candidates) {
    const storage = fakeStorage({ [key]: raw });
    assert.equal(readChannelCache(storage, 'main', 'tasks'), null);
    assert.equal(storage.getItem(key), raw);
  }
});

test('invalid payload writes fail before touching stored cache', () => {
  const storage = fakeStorage();
  writeChannelCache(storage, 'main', 'tasks', ['original']);
  const before = [...storage.values];
  for (const data of [{ channel_id: 'second' }, { channel_id: null }, { channel_id: 'main\n' }]) {
    assert.throws(() => writeChannelCache(storage, 'main', 'tasks', data), { code: 'channel_scope_conflict' });
  }
  assert.throws(() => writeChannelCache(storage, 'main', 'tasks', undefined), TypeError);
  assert.throws(() => writeChannelCache(storage, 'main', 'tasks', {
    toJSON() { return { channel_id: 'second' }; },
  }), { code: 'channel_scope_conflict' });
  assert.deepEqual([...storage.values], before);
});

test('migration is main-only and one-time, reads back destination before removing source', () => {
  const storage = fakeStorage({ legacy: '{"tasks":["old"]}' });
  assert.equal(migrateLegacyMain(storage, 'second', 'tasks', 'legacy').status, 'not_main');
  assert.equal(storage.values.size, 1);
  const remove = storage.removeItem.bind(storage);
  storage.removeItem = key => {
    assert.deepEqual(readChannelCache(storage, 'main', 'tasks'), { tasks: ['old'] });
    remove(key);
  };
  assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'migrated');
  assert.equal(storage.getItem('legacy'), null);
  storage.setItem('legacy', '{"tasks":["new"]}');
  assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'already_migrated');
  assert.equal(storage.getItem('legacy'), '{"tasks":["new"]}');
});

test('migration never clobbers an existing main entry, including corrupt entries', () => {
  for (const existing of ['corrupt', '{"schema_version":1,"channel_id":"main","data":123}']) {
    const storage = fakeStorage({ legacy: '456', [channelCacheKey('main', 'tasks')]: existing });
    const before = [...storage.values];
    assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'existing_main');
    assert.deepEqual([...storage.values], before);
  }
});

test('migration preserves malformed or foreign-owner legacy data', () => {
  for (const raw of ['bad json', '{"channel_id":"second"}', '{"channel_id":null}']) {
    const storage = fakeStorage({ legacy: raw });
    assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'invalid_legacy');
    assert.deepEqual([...storage.values], [['legacy', raw]]);
  }
  assert.equal(migrateLegacyMain(fakeStorage(), 'main', 'tasks', 'legacy').status, 'missing');
});

test('plain-string legacy keys have an explicit decoder and migration key cannot be scoped', () => {
  const storage = fakeStorage({ legacy: 'my-project' });
  assert.equal(migrateLegacyMain(storage, 'main', 'project', 'legacy', { decodeLegacy: raw => raw }).status, 'migrated');
  assert.equal(readChannelCache(storage, 'main', 'project'), 'my-project');
  assert.throws(() => migrateLegacyMain(storage, 'main', 'project', channelCacheKey('second', 'project')), TypeError);
});

test('migration recovers failures at each mutation without losing legacy data', () => {
  for (const failAt of [1, 2, 3, 4]) {
    const storage = fakeStorage({ legacy: '{"project":"old"}' });
    let mutations = 0;
    for (const name of ['setItem', 'removeItem']) {
      const original = storage[name].bind(storage);
      storage[name] = (...args) => {
        mutations += 1;
        if (mutations === failAt) throw new Error('storage unavailable');
        return original(...args);
      };
    }
    assert.throws(() => migrateLegacyMain(storage, 'main', 'project', 'legacy'), /storage unavailable/);
    // Source may be removed only when a correct destination has already persisted.
    if (storage.getItem('legacy') === null) {
      assert.deepEqual(readChannelCache(storage, 'main', 'project'), { project: 'old' });
    }
    assert.equal(migrateLegacyMain(storage, 'main', 'project', 'legacy').status, 'migrated');
    assert.deepEqual(readChannelCache(storage, 'main', 'project'), { project: 'old' });
    assert.equal(storage.getItem('legacy'), null);
  }
});

test('interrupted migration refuses a changed source or changed destination', () => {
  for (const changeTarget of [false, true]) {
    const storage = fakeStorage({ legacy: '{"project":"old"}' });
    const remove = storage.removeItem.bind(storage);
    storage.removeItem = () => { throw new Error('interrupted'); };
    assert.throws(() => migrateLegacyMain(storage, 'main', 'project', 'legacy'));
    storage.removeItem = remove;
    if (changeTarget) writeChannelCache(storage, 'main', 'project', { project: 'new' });
    else storage.setItem('legacy', '{"project":"changed"}');
    const before = [...storage.values];
    assert.equal(migrateLegacyMain(storage, 'main', 'project', 'legacy').status,
      changeTarget ? 'existing_main' : 'source_changed');
    assert.deepEqual([...storage.values], before);
  }
});

test('unverified target write cannot delete legacy data', () => {
  const storage = fakeStorage({ legacy: '123' });
  const set = storage.setItem.bind(storage);
  storage.setItem = (key, value) => {
    if (key !== channelCacheKey('main', 'tasks')) set(key, value);
  };
  assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'write_unverified');
  assert.equal(storage.getItem('legacy'), '123');
});

test('malformed migration journal causes no mutation', () => {
  const key = `${channelCacheKey('main', 'tasks')}:legacy_migration`;
  for (const raw of ['corrupt', 'null', '{"status":"done","channel_id":"second"}']) {
    const storage = fakeStorage({ legacy: '123', [key]: raw });
    const before = [...storage.values];
    assert.equal(migrateLegacyMain(storage, 'main', 'tasks', 'legacy').status, 'invalid_journal');
    assert.deepEqual([...storage.values], before);
  }
});

test('per-tab selection stays isolated; shared preferred channel is only fallback', () => {
  const tabA = fakeStorage();
  const tabB = fakeStorage();
  const shared = fakeStorage({ [ACTIVE_CHANNEL_KEY]: 'second' });
  assert.equal(readActiveChannel(tabA, { sharedStorage: shared }), 'second');
  writeActiveChannel(tabA, 'main');
  writeActiveChannel(tabB, 'third');
  assert.equal(readActiveChannel(tabA, { sharedStorage: shared }), 'main');
  assert.equal(readActiveChannel(tabB, { sharedStorage: shared }), 'third');
  assert.equal(shared.getItem(ACTIVE_CHANNEL_KEY), 'second');
  assert.throws(() => writeActiveChannel(tabA, 'MAIN'), { code: 'channel_scope_invalid' });
  assert.equal(readActiveChannel(fakeStorage({ [ACTIVE_CHANNEL_KEY]: 'Main' })), 'main');
});

test('request guard rejects late A responses across A to B to A, forged and foreign tokens', () => {
  const guard = createChannelRequestGuard('main');
  const firstA = guard.capture();
  assert.equal(guard.isCurrent(firstA), true);
  guard.activate('second');
  const b = guard.capture();
  assert.equal(guard.isCurrent(firstA), false);
  guard.activate('main');
  const secondA = guard.capture();
  assert.equal(guard.isCurrent(firstA), false);
  assert.equal(guard.isCurrent(b), false);
  assert.equal(guard.isCurrent(secondA), true);
  assert.equal(guard.isCurrent({ ...secondA }), false);
  assert.equal(guard.isCurrent(createChannelRequestGuard('main').capture()), false);
  assert.equal(guard.isCurrent(null), false);
  assert.throws(() => guard.activate('Main'), { code: 'channel_scope_invalid' });
  assert.equal(guard.isCurrent(secondA), true);
});

test('unsaved-switch decisions require confirmation or completed save before switching', () => {
  const decide = options => decideChannelSwitch('main', 'second', options).action;
  assert.equal(decide(), 'switch');
  assert.equal(decide({ hasUnsavedChanges: true }), 'confirm');
  assert.equal(decide({ hasUnsavedChanges: true, decision: 'save' }), 'save_before_switch');
  assert.equal(decide({ hasUnsavedChanges: true, decision: 'discard' }), 'switch');
  assert.equal(decide({ hasUnsavedChanges: true, decision: 'cancel' }), 'stay');
  assert.equal(decideChannelSwitch('main', 'main', { hasUnsavedChanges: true }).action, 'stay');
  assert.throws(() => decide({ decision: 'autosave' }), TypeError);
});
