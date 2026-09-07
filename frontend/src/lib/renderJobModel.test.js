import test from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateJobProgress,
  clearActiveJob,
  formatJobError,
  getActiveJob,
  getActiveJobEntry,
  normalizeJobResult,
  saveActiveJob,
} from './renderJobModel.js';

function makeMockStorage() {
  const store = new Map();
  return {
    store,
    setItem: (k, v) => store.set(k, String(v)),
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    removeItem: (k) => store.delete(k),
  };
}

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
  const mockStorage = makeMockStorage();

  assert.equal(getActiveJob('proj_alpha', mockStorage), null);

  saveActiveJob('proj_alpha', 'job-12345', mockStorage);
  assert.equal(getActiveJob('proj_alpha', mockStorage), 'job-12345');

  clearActiveJob('proj_alpha', mockStorage);
  assert.equal(getActiveJob('proj_alpha', mockStorage), null);
});

test('a job saved under one project label is still found after the display name changes', () => {
  // Regression test for the bug: saveActiveJob/getActiveJob used to key the
  // sessionStorage entry by the project's display-name string. Renaming a
  // project (or simply looking it up under a differently-derived label)
  // between starting a render and checking on it meant the lookup key no
  // longer matched what was stored, and the in-flight job became silently
  // un-findable even though it was still running server-side.
  const mockStorage = makeMockStorage();

  saveActiveJob('เสื้อยืดสีฟ้า_unboxing_1', 'job-uuid-aaa', mockStorage);

  // The project was renamed (or is now looked up via a differently-computed
  // label) before the user navigated back to check on the render.
  const renamedLabel = 'เสื้อยืดสีฟ้า_unboxing_1_renamed';
  assert.equal(getActiveJob(renamedLabel, mockStorage), 'job-uuid-aaa');

  // The saved label is preserved on the side for callers that want it.
  assert.deepEqual(getActiveJobEntry(mockStorage), {
    jobId: 'job-uuid-aaa',
    projectKey: 'เสื้อยืดสีฟ้า_unboxing_1',
  });

  clearActiveJob(renamedLabel, mockStorage);
  assert.equal(getActiveJob(renamedLabel, mockStorage), null);
});

test('two renders that both fall back to the literal default label do not clobber each other beyond one active slot', () => {
  // Two different callers with no project_name/product_name both collapse
  // to the same literal fallback label ('วิดีโอ'). Since job entries are
  // addressed by job_id rather than by label, saving the second job does
  // not corrupt or merge with the first entry -- it simply becomes the
  // one active job for this tab (there is at most one in-flight render per
  // browser tab), and the stored payload always reflects the *current*
  // job_id/label pair consistently, never a mix of the two.
  const mockStorage = makeMockStorage();

  saveActiveJob('วิดีโอ', 'job-first', mockStorage);
  assert.equal(getActiveJob('วิดีโอ', mockStorage), 'job-first');

  saveActiveJob('วิดีโอ', 'job-second', mockStorage);
  const entry = getActiveJobEntry(mockStorage);
  assert.equal(entry.jobId, 'job-second');
  assert.equal(entry.projectKey, 'วิดีโอ');
});

test('a stale entry written under the old per-project-name storage scheme does not crash the new code', () => {
  const mockStorage = makeMockStorage();

  // Old scheme: `omnicut_active_render_${projectName}` -> raw jobId string
  // (no JSON, no `job` suffix). Simulate a leftover from before this fix.
  mockStorage.setItem('omnicut_active_render_proj_old_name', 'job-legacy-raw-string');

  // New code never reads that key shape, so it is simply invisible --
  // getActiveJob must return null (not throw, not return the stale value).
  assert.equal(getActiveJob('proj_old_name', mockStorage), null);
  assert.doesNotThrow(() => clearActiveJob('proj_old_name', mockStorage));

  // A malformed value under the *current* key shape (e.g. corrupted JSON,
  // or a raw string someone wrote by hand) must also not throw.
  mockStorage.setItem('omnicut_active_render_job', 'not-json{{');
  assert.equal(getActiveJob('anything', mockStorage), null);
  assert.equal(getActiveJobEntry(mockStorage), null);
});
