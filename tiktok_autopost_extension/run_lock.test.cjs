const { test } = require('node:test');
const assert = require('node:assert/strict');
const lock = require('./run_lock.js');

function memoryStorage() {
  const data = {};
  return {
    data,
    get: async (key) => (key in data ? { [key]: data[key] } : {}),
    set: async (obj) => { Object.assign(data, JSON.parse(JSON.stringify(obj))); },
    remove: async (key) => { delete data[key]; },
  };
}
const nosleep = async () => {};

test('a second panel cannot start while a fresh lock is held', async () => {
  const storage = memoryStorage();
  let t = 1000;
  const opts = { now: () => t, sleep: nosleep };
  assert.equal((await lock.acquire(storage, 'A', opts)).ok, true);
  const second = await lock.acquire(storage, 'B', opts);
  assert.equal(second.ok, false);
  assert.equal(second.reason, 'held');
  t += 5000; await lock.beat(storage, 'A', opts);
  t += lock.TTL_MS - 1000;                       // still inside the TTL of the last heartbeat
  assert.equal((await lock.acquire(storage, 'B', opts)).ok, false);
});

test('a lock nobody refreshes is stale: another panel may take over and sees it was recovered', async () => {
  const storage = memoryStorage();
  let t = 1000;
  const opts = { now: () => t, sleep: nosleep };
  await lock.acquire(storage, 'A', opts);
  t += lock.TTL_MS + 1;
  const taken = await lock.acquire(storage, 'B', opts);
  assert.equal(taken.ok, true);
  assert.equal(taken.recovered, true);
});

test('release only removes your own lock; takeOrphan returns only a stale lock', async () => {
  const storage = memoryStorage();
  let t = 1000;
  const opts = { now: () => t, sleep: nosleep };
  await lock.acquire(storage, 'A', opts);
  await lock.release(storage, 'B');
  assert.ok(storage.data[lock.KEY]);
  assert.equal(await lock.takeOrphan(storage, opts), null);   // fresh: someone is running, not an orphan
  t += lock.TTL_MS + 1;
  const orphan = await lock.takeOrphan(storage, opts);
  assert.equal(orphan.owner, 'A');
  assert.equal(storage.data[lock.KEY], undefined);
  await lock.acquire(storage, 'A', opts);
  await lock.release(storage, 'A');
  assert.equal(storage.data[lock.KEY], undefined);
});

test('two panels racing: the later writer wins and the earlier one is told it lost', async () => {
  const storage = memoryStorage();
  const opts = { now: () => 5000, sleep: async () => { await storage.set({ [lock.KEY]: { owner: 'B', beat: 5000 } }); } };
  const result = await lock.acquire(storage, 'A', opts);
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'lost');
});

test('a heartbeat from a panel that lost the lock does nothing', async () => {
  const storage = memoryStorage();
  const opts = { now: () => 1, sleep: nosleep };
  await lock.acquire(storage, 'A', opts);
  assert.equal(await lock.beat(storage, 'B', opts), false);
  assert.equal(await lock.beat(storage, 'A', opts), true);
});
