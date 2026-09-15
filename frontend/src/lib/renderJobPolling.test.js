import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import { createRenderJobPollController } from '../hooks/useRenderJob.js';

const hookSource = fs.readFileSync(new URL('../hooks/useRenderJob.js', import.meta.url), 'utf8');

test('stale render response cannot stop or publish the newer job poll', async () => {
  const pending = new Map();
  const published = [];
  const fetchStatus = (jobId) => new Promise((resolve) => {
    pending.set(jobId, resolve);
  });
  const poller = createRenderJobPollController({
    fetchStatus,
    isActive: () => true,
    onResponse: (status, jobId) => published.push({ status, jobId }),
    intervalMs: 60_000,
  });

  poller.start('old-job', 'Project_A');
  poller.start('new-job', 'Project_A');

  pending.get('old-job')({ status: 'completed', result: { mp4: 'old.mp4' } });
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(published, [], 'old completion must be ignored after a new job starts');

  pending.get('new-job')({ status: 'rendering', progress: 0.5 });
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(published, [
    { status: { status: 'rendering', progress: 0.5 }, jobId: 'new-job' },
  ]);
  poller.stop();
});

test('render polling schedules one follow-up only after the previous request settles', async () => {
  const scheduled = [];
  const resolvers = [];
  let requests = 0;
  let inFlight = 0;
  let maxInFlight = 0;
  const fetchStatus = () => {
    requests += 1;
    inFlight += 1;
    maxInFlight = Math.max(maxInFlight, inFlight);
    return new Promise((resolve) => {
      resolvers.push((status) => {
        inFlight -= 1;
        resolve(status);
      });
    });
  };
  const poller = createRenderJobPollController({
    fetchStatus,
    isActive: () => true,
    setTimeoutFn: (callback) => {
      scheduled.push(callback);
      return callback;
    },
    clearTimeoutFn: () => {},
  });

  poller.start('job-1', 'Project_A');
  assert.equal(requests, 1);
  assert.equal(scheduled.length, 0, 'no next request is scheduled while the first is pending');

  resolvers.shift()({ status: 'rendering', progress: 0.25 });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(scheduled.length, 1);

  scheduled.shift()();
  assert.equal(requests, 2);
  assert.equal(inFlight, 1);
  assert.equal(maxInFlight, 1, 'poll requests must never overlap');

  poller.stop();
  resolvers.shift()({ status: 'rendering', progress: 0.5 });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(scheduled.length, 0, 'stopped pollers do not schedule another request');
});

test('render resume is project-scoped and cleanup resets stale UI state', () => {
  assert.match(hookSource, /const jobEntry = getActiveJobEntry\(\);/);
  assert.match(hookSource, /jobEntry\.projectKey === projectName/);
  assert.match(hookSource, /setJobId\(null\);\s*setIsRendering\(false\);\s*setJobStatus\(null\);/s);
  assert.match(hookSource, /return \(\) => \{\s*clearTimer\(\);\s*\};/s);
});
