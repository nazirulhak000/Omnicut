import test from 'node:test';
import assert from 'node:assert/strict';

import { createLatestSaveQueue } from './projectSaveQueue.js';


const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail; });
  return { promise, resolve, reject };
};


test('rapid pending edits coalesce to the newest payload', async () => {
  const saved = [];
  const queue = createLatestSaveQueue(async (projectName, payload) => saved.push([projectName, payload]));
  queue.enqueue('demo', { revision: 1 });
  queue.enqueue('demo', { revision: 2 });
  queue.enqueue('demo', { revision: 3 });

  await queue.flush();

  assert.deepEqual(saved, [['demo', { revision: 3 }]]);
});


test('an in-flight save finishes before the newest edit is written', async () => {
  const first = deferred();
  const order = [];
  const queue = createLatestSaveQueue(async (_projectName, payload) => {
    order.push(`start-${payload.revision}`);
    if (payload.revision === 1) await first.promise;
    order.push(`end-${payload.revision}`);
  });
  queue.enqueue('demo', { revision: 1 });
  const flushing = queue.flush();
  await Promise.resolve();
  queue.enqueue('demo', { revision: 2 });
  first.resolve();

  await flushing;

  assert.deepEqual(order, ['start-1', 'end-1', 'start-2', 'end-2']);
});


test('a failed latest save remains pending for an explicit retry', async () => {
  let attempts = 0;
  const queue = createLatestSaveQueue(async () => {
    attempts += 1;
    if (attempts === 1) throw new Error('offline');
  });
  queue.enqueue('demo', { revision: 1 });

  await assert.rejects(queue.flush(), /offline/);
  assert.equal(queue.hasPending(), true);
  await queue.flush();

  assert.equal(attempts, 2);
  assert.equal(queue.hasPending(), false);
});
