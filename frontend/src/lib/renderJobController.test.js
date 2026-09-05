import test from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateJobProgress,
  clearActiveJob,
  getActiveJob,
  normalizeJobResult,
  saveActiveJob,
} from './renderJobModel.js';

test('render job controller isolates jobs across different projects', async () => {
  const store = new Map();
  const mockStorage = {
    setItem: (k, v) => store.set(k, String(v)),
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    removeItem: (k) => store.delete(k),
  };

  saveActiveJob('Project_A', 'job-a-99', mockStorage);
  saveActiveJob('Project_B', 'job-b-100', mockStorage);

  assert.equal(getActiveJob('Project_A', mockStorage), 'job-a-99');
  assert.equal(getActiveJob('Project_B', mockStorage), 'job-b-100');

  clearActiveJob('Project_A', mockStorage);
  assert.equal(getActiveJob('Project_A', mockStorage), null);
  assert.equal(getActiveJob('Project_B', mockStorage), 'job-b-100');
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
