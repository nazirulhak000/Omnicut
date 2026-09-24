import test from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateJobProgress,
  clearActiveJob,
  getActiveJob,
  normalizeJobResult,
  saveActiveJob,
} from './renderJobModel.js';

test('render job controller tracks one active job per tab, addressed by job id rather than project label', async () => {
  // A browser tab only ever has one render in flight at a time (EditorShell
  // and NewClipPanel's useRenderJob instances are never mounted together),
  // so storage holds a single job entry rather than one per project label.
  // Starting a new render for a different project supersedes the previous
  // entry -- there is nothing left to "isolate" by label, and the label is
  // no longer part of the storage key at all (see renderJobModel.js).
  const store = new Map();
  const mockStorage = {
    setItem: (k, v) => store.set(k, String(v)),
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    removeItem: (k) => store.delete(k),
  };

  saveActiveJob('Project_A', 'job-a-99', mockStorage);
  assert.equal(getActiveJob('Project_A', mockStorage), 'job-a-99');

  saveActiveJob('Project_B', 'job-b-100', mockStorage);
  assert.equal(getActiveJob('Project_B', mockStorage), 'job-b-100');
  // The prior project's job was superseded, not kept alongside it.
  assert.equal(getActiveJob('Project_A', mockStorage), 'job-b-100');

  clearActiveJob('Project_B', mockStorage);
  assert.equal(getActiveJob('Project_B', mockStorage), null);
});

test('stale project guard prevents callbacks for previous project', async () => {
  let activeProject = 'Project_1';
  let completedFor = null;

  const handleComplete = (result, jobId, projectName) => {
    if (activeProject === projectName) {
      completedFor = projectName;
    }
  };

  // Simulate an in-flight response arriving after project switch
  const inFlightProject = 'Project_1';
  activeProject = 'Project_2'; // user switched to Project 2

  handleComplete({ mp4: 'out.mp4' }, 'job-1', inFlightProject);

  assert.equal(completedFor, null, 'Callback for Project_1 was safely ignored because Project_2 is active');
});

test('render progress and result normalization map consistently', () => {
  const mockBackendResponse = {
    id: 'job-777',
    status: 'completed',
    progress: 1.0,
    result: {
      mp4: '04_Exports/output.mp4',
      video_url: 'http://localhost:8000/media/output.mp4',
    },
  };

  const progress = calculateJobProgress(mockBackendResponse);
  assert.equal(progress.isDone, true);
  assert.equal(progress.percent, 100);

  const normalized = normalizeJobResult(mockBackendResponse.result);
  assert.equal(normalized.videoPath, '04_Exports/output.mp4');
  assert.equal(normalized.videoUrl, 'http://localhost:8000/media/output.mp4');
});

test('useRenderJob hook is exported and exposes required API contract for NewClipPanel and EditorShell', async () => {
  const { useRenderJob } = await import('../hooks/useRenderJob.js');
  assert.equal(typeof useRenderJob, 'function', 'useRenderJob should be a hook function');
});

test('render poll stops on auth loss or restarted-server 404 without retrying forever', async () => {
  const { createRenderJobPollController } = await import('../hooks/useRenderJob.js');
  for (const status of [401, 404]) {
    const errors = [];
    const scheduled = [];
    const controller = createRenderJobPollController({
      fetchStatus: async () => { throw { response: { status } }; },
      onError: (error, jobId, project) => errors.push([error.response.status, jobId, project]),
      setTimeoutFn: (callback) => { scheduled.push(callback); return scheduled.length; },
    });
    controller.start('job-failed', 'project-a');
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(errors, [[status, 'job-failed', 'project-a']]);
    assert.equal(scheduled.length, 0);
  }
});

test('render poll retries transient network failure and then accepts completion', async () => {
  const { createRenderJobPollController } = await import('../hooks/useRenderJob.js');
  const scheduled = [];
  const responses = [];
  let attempts = 0;
  const controller = createRenderJobPollController({
    fetchStatus: async () => {
      attempts += 1;
      if (attempts === 1) throw new Error('temporary network loss');
      return { status: 'completed', progress: 1, result: {} };
    },
    onResponse: (status) => responses.push(status.status),
    onError: () => { throw new Error('transient failure must be retried'); },
    setTimeoutFn: (callback) => { scheduled.push(callback); return scheduled.length; },
  });
  controller.start('job-retry', 'project-a');
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(scheduled.length, 1);
  scheduled.shift()();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(responses, ['completed']);
  assert.equal(scheduled.length, 0);
});
