import test from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateJobProgress,
  clearActiveJob,
  formatJobError,
  getActiveJob,
  normalizeJobResult,
  saveActiveJob,
} from './renderJobModel.js';

test('calculateJobProgress calculates percentages and status flags accurately', () => {
  // Empty or null
  const empty = calculateJobProgress(null);
  assert.equal(empty.percent, 0);
  assert.equal(empty.isDone, false);
  assert.equal(empty.isFailed, false);
  assert.equal(empty.isRunning, false);

  // In-flight progress
  const running = calculateJobProgress({
    status: 'rendering',
    progress: 0.456,
    message: 'กำลังประกอบเสียงและวิดีโอ',
  });
  assert.equal(running.percent, 46);
  assert.equal(running.isDone, false);
  assert.equal(running.isFailed, false);
  assert.equal(running.isRunning, true);
  assert.equal(running.message, 'กำลังประกอบเสียงและวิดีโอ');

  // Done status
  const done = calculateJobProgress({ status: 'completed', progress: 1.0 });
  assert.equal(done.percent, 100);
  assert.equal(done.isDone, true);
  assert.equal(done.isFailed, false);
  assert.equal(done.isRunning, false);
  assert.equal(done.message, 'เรนเดอร์เสร็จสมบูรณ์');

  // Failed status
  const failed = calculateJobProgress({ status: 'failed', error: 'FFmpeg encoding timeout' });
  assert.equal(failed.isDone, false);
  assert.equal(failed.isFailed, true);
  assert.equal(failed.isRunning, false);
  assert.equal(failed.message, 'FFmpeg encoding timeout');
});

test('normalizeJobResult handles multiple backend key variations', () => {
  assert.deepEqual(normalizeJobResult(null), { videoUrl: null, videoPath: null, raw: {} });

  const res1 = normalizeJobResult({ mp4: '04_Exports/video_1.mp4' });
  assert.equal(res1.videoPath, '04_Exports/video_1.mp4');

  const res2 = normalizeJobResult({ final_video_path: '04_Exports/v2.mp4', video_url: 'http://localhost/v2.mp4' });
  assert.equal(res2.videoPath, '04_Exports/v2.mp4');
  assert.equal(res2.videoUrl, 'http://localhost/v2.mp4');

  const res3 = normalizeJobResult({ mp4_video: '04_Exports/v3.mp4' });
  assert.equal(res3.videoPath, '04_Exports/v3.mp4');
});

test('formatJobError formats strings, nested details, and arrays', () => {
  assert.equal(formatJobError('Simple error'), 'Simple error');
  assert.equal(formatJobError({ message: 'Network offline' }), 'Network offline');
  assert.equal(formatJobError({ response: { data: { detail: 'Project missing' } } }), 'Project missing');
  assert.equal(
    formatJobError({ detail: [{ msg: 'field required' }, { msg: 'invalid value' }] }),
    'field required, invalid value',
  );
});

test('active job storage persists, retrieves, and clears', () => {
  const store = new Map();
  const mockStorage = {
    setItem: (k, v) => store.set(k, String(v)),
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    removeItem: (k) => store.delete(k),
  };

  assert.equal(getActiveJob('proj_alpha', mockStorage), null);

  saveActiveJob('proj_alpha', 'job-12345', mockStorage);
  assert.equal(getActiveJob('proj_alpha', mockStorage), 'job-12345');

  clearActiveJob('proj_alpha', mockStorage);
  assert.equal(getActiveJob('proj_alpha', mockStorage), null);
});
