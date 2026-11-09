import test from 'node:test';
import assert from 'node:assert/strict';
import { startRenderStatusPoller, isTerminalRenderStatus } from './renderStatusPoller.js';

// Manual clock: run() fires the earliest pending timer.
function fakeClock() {
  let now = 0;
  let seq = 0;
  const timers = new Map();
  return {
    schedule: (fn, ms) => { const id = ++seq; timers.set(id, { fn, at: now + ms }); return id; },
    cancel: (id) => { timers.delete(id); },
    pending: () => timers.size,
    async run() {
      const [id, t] = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0] || [];
      if (!id) return false;
      timers.delete(id);
      now = t.at;
      t.fn();
      await new Promise((r) => setImmediate(r));
      return true;
    },
    get now() { return now; },
  };
}

test('one request in flight: the next tick waits for the previous response', async () => {
  const clock = fakeClock();
  let inFlight = 0;
  let maxInFlight = 0;
  let resolveFetch;
  const poller = startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: () => { inFlight += 1; maxInFlight = Math.max(maxInFlight, inFlight); return new Promise((r) => { resolveFetch = r; }); },
    onStatus: () => {},
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  await clock.run(); // first request starts and hangs
  assert.equal(clock.pending(), 0, 'no timer stacks up while the request is pending');
  inFlight -= 1;
  resolveFetch({ status: 'processing' });
  await new Promise((r) => setImmediate(r));
  assert.equal(clock.pending(), 1, 'next tick scheduled after the response');
  assert.equal(maxInFlight, 1);
  poller.stop();
  assert.equal(clock.pending(), 0);
});

test('a failed request backs off and retries instead of stopping for good', async () => {
  const clock = fakeClock();
  let calls = 0;
  const seen = [];
  const poller = startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: async () => { calls += 1; if (calls === 1) throw new Error('blip'); return { status: 'processing' }; },
    onStatus: (d) => seen.push(d.status),
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  await clock.run(); // fails
  assert.equal(poller.isStopped(), false);
  const before = clock.now;
  await clock.run(); // retry
  assert.ok(clock.now - before >= 2000, 'backoff grows past the base interval');
  assert.deepEqual(seen, ['processing']);
  poller.stop();
});

test('gives up only after maxFailures consecutive errors', async () => {
  const clock = fakeClock();
  let gaveUp = 0;
  const poller = startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: async () => { throw new Error('down'); },
    onStatus: () => {},
    onGiveUp: () => { gaveUp += 1; },
    maxFailures: 3,
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  for (let i = 0; i < 5; i += 1) await clock.run();
  assert.equal(gaveUp, 1);
  assert.equal(poller.isStopped(), true);
  assert.equal(clock.pending(), 0);
});

test('terminal status lingers, then finishes; stop() during the linger clears it', async () => {
  const clock = fakeClock();
  let finished = 0;
  startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: async () => ({ status: 'completed' }),
    onStatus: () => {},
    onFinished: () => { finished += 1; },
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  await clock.run();
  assert.equal(clock.pending(), 1, 'linger timer');
  await clock.run();
  assert.equal(finished, 1);
  assert.equal(clock.pending(), 0);

  const clock2 = fakeClock();
  let finished2 = 0;
  const p2 = startRenderStatusPoller({
    jobId: 'j2',
    fetchStatus: async () => ({ status: 'failed' }),
    onStatus: () => {},
    onFinished: () => { finished2 += 1; },
    schedule: clock2.schedule,
    cancel: clock2.cancel,
  });
  await clock2.run();
  p2.stop(); // unmount during the linger
  assert.equal(clock2.pending(), 0);
  assert.equal(finished2, 0, 'no state update after unmount');
});

test('a response that arrives after stop() is dropped', async () => {
  const clock = fakeClock();
  let resolveFetch;
  const seen = [];
  const poller = startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: () => new Promise((r) => { resolveFetch = r; }),
    onStatus: (d) => seen.push(d),
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  await clock.run();
  poller.stop();
  resolveFetch({ status: 'processing' });
  await new Promise((r) => setImmediate(r));
  assert.deepEqual(seen, []);
  assert.equal(clock.pending(), 0);
});

test('hidden page skips the request but keeps the schedule alive', async () => {
  const clock = fakeClock();
  let calls = 0;
  let hidden = true;
  const poller = startRenderStatusPoller({
    jobId: 'j1',
    fetchStatus: async () => { calls += 1; return { status: 'processing' }; },
    onStatus: () => {},
    isHidden: () => hidden,
    schedule: clock.schedule,
    cancel: clock.cancel,
  });
  await clock.run();
  assert.equal(calls, 0);
  hidden = false;
  await clock.run();
  assert.equal(calls, 1);
  poller.stop();
});

test('terminal statuses', () => {
  for (const s of ['completed', 'done', 'failed', 'error', 'cancelled', 'DONE']) assert.equal(isTerminalRenderStatus(s), true, s);
  for (const s of ['processing', 'queued', 'rendering', '', undefined]) assert.equal(isTerminalRenderStatus(s), false, String(s));
});
