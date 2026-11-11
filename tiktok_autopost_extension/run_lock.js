// One batch run at a time across every open side panel. The run loop lives in a panel's memory, so a lock with a
// heartbeat in chrome.storage.local tells a second panel "someone is running", and tells a panel that opens after a
// crash/close "the last run was cut off" (stale lock) so it can park the orphaned job instead of leaving it claimed.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniRunLock = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const KEY = 'omnicutBatchRunLock';
  const TTL_MS = 45 * 1000;      // a lock whose heartbeat is older than this belongs to a dead run
  const BEAT_MS = 10 * 1000;

  const isFresh = (lock, now, ttl = TTL_MS) => Boolean(lock && lock.owner && now - Number(lock.beat || 0) < ttl);
  const read = async (storage) => (await storage.get(KEY))[KEY] || null;
  let pending = Promise.resolve();
  function mutex(fn) {
    if (globalThis.navigator?.locks?.request) return globalThis.navigator.locks.request('omnicut-run-lock-mutation', fn);
    if (typeof chrome !== 'undefined') return Promise.reject(new Error('เบราว์เซอร์ไม่รองรับตัวล็อกรอบ กรุณาอัปเดต Chrome'));
    const work = pending.then(fn); pending = work.catch(() => {}); return work;
  }

  // {ok:true, recovered?} or {ok:false, reason:'held'|'lost', lock}
  async function acquire(storage, owner, { now = Date.now, sleep = (ms) => new Promise((r) => setTimeout(r, ms)) } = {}) {
    return mutex(async () => {
    const current = await read(storage);
    if (isFresh(current, now()) && current.owner !== owner) return { ok: false, reason: 'held', lock: current };
    await storage.set({ [KEY]: { owner, beat: now(), startedAt: now() } });
    await sleep(150);                       // verify ownership even if an older extension version writes outside our mutex
    const after = await read(storage);
    if (!after || after.owner !== owner) return { ok: false, reason: 'lost', lock: after };
    return { ok: true, recovered: Boolean(current && current.owner !== owner) };
    });
  }

  async function beat(storage, owner, { now = Date.now } = {}) {
    return mutex(async () => {
    const current = await read(storage);
    if (!current || current.owner !== owner) return false;
    await storage.set({ [KEY]: { ...current, beat: now() } });
    return true;
    });
  }

  async function release(storage, owner) {
    return mutex(async () => {
    const current = await read(storage);
    if (current && current.owner === owner) await storage.remove(KEY);
    });
  }

  // Read an interrupted run without removing its marker; recovery releases it only after parking succeeds.
  async function takeOrphan(storage, { now = Date.now } = {}) {
    return mutex(async () => {
    const current = await read(storage);
    if (!current || isFresh(current, now())) return null;
    return current;
    });
  }

  return { KEY, TTL_MS, BEAT_MS, isFresh, acquire, beat, release, takeOrphan, read };
});
