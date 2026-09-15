import test from 'node:test';
import assert from 'node:assert/strict';

import { createProjectAutosaveController, lifecycleSaveHeaders } from '../hooks/useProjectAutosave.js';
import { createLatestSaveQueue } from './projectSaveQueue.js';


const deferred = () => {
  let resolve;
  const promise = new Promise((ok) => { resolve = ok; });
  return { promise, resolve };
};

const makeController = (save, { maxSaveRetries, saveRetryDelayMs } = {}) => {
  const queue = createLatestSaveQueue(save);
  const timers = new Set();
  const statuses = [];
  const controller = createProjectAutosaveController({
    queue,
    schedule(callback) {
      timers.add(callback);
      return callback;
    },
    cancel(timer) {
      timers.delete(timer);
    },
    onStatusChange(status) {
      statuses.push(status);
    },
    ...(maxSaveRetries !== undefined ? { maxSaveRetries } : {}),
    ...(saveRetryDelayMs !== undefined ? { saveRetryDelayMs } : {}),
  });
  return {
    controller, queue, timers, statuses,
  };
};

// Fake `schedule` above hands back the callback itself as the "timer", so a
// scheduled callback is fired by grabbing it from `timers` and calling it —
// this stands in for the real delay elapsing.
const fireNextTimer = (timers) => {
  const callback = timers.values().next().value;
  timers.delete(callback);
  callback();
};


test('lifecycle save headers include the configured API key without emitting an empty header', () => {
  assert.deepEqual(lifecycleSaveHeaders('secret'), {
    'Content-Type': 'application/json',
    'X-API-Key': 'secret',
  });
  assert.deepEqual(lifecycleSaveHeaders(''), { 'Content-Type': 'application/json' });
});


test('reverting to the baseline clears an unflushed edit instead of saving stale state', async () => {
  const saved = [];
  const { controller, queue } = makeController(async (_name, payload) => saved.push(payload));

  controller.setBaseline('demo', { revision: 0 });
  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 500 });
  controller.observe({ projectName: 'demo', payload: { revision: 0 }, enabled: true, debounceMs: 500 });

  assert.equal(queue.hasPending(), false);
  await controller.flush();
  assert.deepEqual(saved, []);
});


test('reverting while a save is in flight writes the baseline after the older save', async () => {
  const gate = deferred();
  const saved = [];
  const { controller } = makeController(async (_name, payload) => {
    saved.push(`start-${payload.revision}`);
    if (payload.revision === 1) await gate.promise;
    saved.push(`end-${payload.revision}`);
  });

  controller.setBaseline('demo', { revision: 0 });
  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 500 });
  const flushing = controller.flush();
  await Promise.resolve();
  controller.observe({ projectName: 'demo', payload: { revision: 0 }, enabled: true, debounceMs: 500 });
  gate.resolve();

  await flushing;
  assert.deepEqual(saved, ['start-1', 'end-1', 'start-0', 'end-0']);
});


test('equivalent immutable payloads are queued once during autosave observation', async () => {
  const saved = [];
  const { controller } = makeController(async (_name, payload) => saved.push(payload));

  controller.setBaseline('demo', { revision: 0 });
  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 500 });
  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 500 });

  await controller.flush();
  assert.deepEqual(saved, [{ revision: 1 }]);
});


test('saveNow does not enqueue a duplicate while the same payload is in flight', async () => {
  const gate = deferred();
  const saved = [];
  const { controller } = makeController(async (_name, payload) => {
    saved.push(payload);
    await gate.promise;
  });

  const firstSave = controller.saveNow({
    projectName: 'demo',
    payload: { revision: 1 },
    enabled: true,
  });
  await Promise.resolve();
  const secondSave = controller.saveNow({
    projectName: 'demo',
    payload: { revision: 1 },
    enabled: true,
  });
  gate.resolve();

  await Promise.all([firstSave, secondSave]);
  assert.deepEqual(saved, [{ revision: 1 }]);
});


test('changing the baseline does not retry a failed save from the previous project', async () => {
  const gate = deferred();
  const { controller, queue } = makeController(async () => {
    await gate.promise;
    throw new Error('old project is no longer active');
  });

  controller.observe({ projectName: 'old-project', payload: { revision: 1 }, enabled: true, debounceMs: 500 });
  const flushing = controller.flush();
  await Promise.resolve();
  controller.setBaseline('new-project', { revision: 0 });
  gate.resolve();

  await assert.rejects(flushing, /old project is no longer active/);
  assert.equal(queue.hasPending(), false);
});


test('resetting the baseline for the same project follows an active save in order', async () => {
  const gate = deferred();
  const saved = [];
  const { controller } = makeController(async (_name, payload) => {
    saved.push(payload.revision);
    if (payload.revision === 1) await gate.promise;
  });

  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 500 });
  const flushing = controller.flush();
  await Promise.resolve();
  controller.setBaseline('demo', { revision: 0 });
  gate.resolve();

  await flushing;
  assert.deepEqual(saved, [1, 0]);
});


test('a save that keeps failing retries a bounded number of times before surfacing an error status', async () => {
  let attempts = 0;
  const { controller, queue, timers, statuses } = makeController(
    async () => {
      attempts += 1;
      throw new Error('boom');
    },
    { maxSaveRetries: 1, saveRetryDelayMs: 50 },
  );

  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 10 });
  assert.equal(timers.size, 1);
  fireNextTimer(timers);

  await assert.rejects(queue.flush(), /boom/);
  await Promise.resolve();
  assert.equal(attempts, 1);
  assert.deepEqual(statuses, []); // a retry is scheduled, so it's not "given up" yet
  assert.equal(timers.size, 1);

  fireNextTimer(timers);
  await assert.rejects(queue.flush(), /boom/);
  await Promise.resolve();
  assert.equal(attempts, 2);
  assert.deepEqual(statuses, ['error']);
  assert.equal(timers.size, 0); // retries exhausted, nothing else scheduled
  assert.equal(queue.hasPending(), true); // the failed edit is not lost
});


test('a manual save after exhausted retries reuses the stranded edit and clears the error', async () => {
  let attempts = 0;
  const { controller, queue, timers, statuses } = makeController(
    async () => {
      attempts += 1;
      if (attempts <= 2) throw new Error('offline');
    },
    { maxSaveRetries: 1, saveRetryDelayMs: 50 },
  );

  controller.observe({ projectName: 'demo', payload: { revision: 1 }, enabled: true, debounceMs: 10 });
  fireNextTimer(timers); // initial attempt
  await assert.rejects(queue.flush(), /offline/);
  await Promise.resolve();
  fireNextTimer(timers); // bounded retry, also fails
  await assert.rejects(queue.flush(), /offline/);
  await Promise.resolve();
  assert.deepEqual(statuses, ['error']);

  await controller.saveNow({ projectName: 'demo', payload: { revision: 1 }, enabled: true });

  assert.equal(attempts, 3);
  assert.equal(queue.hasPending(), false);
  assert.deepEqual(statuses, ['error']); // no further error re-triggered by the success
});
