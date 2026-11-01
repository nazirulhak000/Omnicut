const test = require('node:test');
const assert = require('node:assert/strict');
const { createBatchRunner, BATCH_STATES } = require('./batch_runner.js');

test('BatchRunner: transitions through clip lifecycle and completes full batch', async () => {
  const clips = [
    { id: 'clip-1', name: 'Clip 1', hook_title: 'Hook 1' },
    { id: 'clip-2', name: 'Clip 2', hook_title: 'Hook 2' },
  ];

  const executionLog = [];
  const stateLog = [];

  const mockActions = {
    prepareClip: async (clip) => {
      executionLog.push(`prepare:${clip.id}`);
      return { success: true, job_id: `job-${clip.id}` };
    },
    uploadVideo: async (clip) => {
      executionLog.push(`uploadVideo:${clip.id}`);
      return { success: true };
    },
    fillDetails: async (clip, mode) => {
      executionLog.push(`fillDetails:${clip.id}:${mode}`);
      return { success: true, completed: ['caption', 'product', 'schedule', 'cover'] };
    },
    submitPost: async (clip, mode) => {
      executionLog.push(`submitPost:${clip.id}:${mode}`);
      return { success: true, posted: true, outcome: mode === 'draft' ? 'draft_saved' : 'scheduled_on_platform' };
    },
    reconcile: async (clip, outcome) => {
      executionLog.push(`reconcile:${clip.id}:${outcome}`);
      return { success: true, outcome };
    },
    resetUploadPage: async () => {
      executionLog.push('resetUploadPage');
      return { success: true };
    },
  };

  const runner = createBatchRunner({
    clips,
    options: {
      mode: 'smart',
      cooldownSeconds: 0.05, // very fast for tests
      maxScheduleQuota: 30,
      currentScheduleCount: 0,
    },
    actions: mockActions,
    onStateChange: (state, stats) => {
      stateLog.push(state);
    },
  });

  const summary = await runner.start();

  assert.equal(summary.total, 2);
  assert.equal(summary.successful, 2);
  assert.equal(summary.failed, 0);
  assert.equal(runner.getState(), BATCH_STATES.COMPLETED);

  // Verifying lifecycle execution sequence
  assert.ok(executionLog.includes('prepare:clip-1'));
  assert.ok(executionLog.includes('uploadVideo:clip-1'));
  assert.ok(executionLog.includes('fillDetails:clip-1:schedule'));
  assert.ok(executionLog.includes('submitPost:clip-1:schedule'));
  assert.ok(executionLog.includes('reconcile:clip-1:scheduled_on_platform'));

  assert.ok(executionLog.includes('prepare:clip-2'));
  assert.ok(executionLog.includes('uploadVideo:clip-2'));
  assert.ok(executionLog.includes('fillDetails:clip-2:schedule'));
  assert.ok(executionLog.includes('submitPost:clip-2:schedule'));
  assert.ok(executionLog.includes('reconcile:clip-2:scheduled_on_platform'));
});

test('BatchRunner: auto-switches to draft mode when schedule quota is reached', async () => {
  const clips = [
    { id: 'clip-1', name: 'Clip 1' },
    { id: 'clip-2', name: 'Clip 2' },
  ];

  const modesUsed = [];

  const mockActions = {
    prepareClip: async () => ({ success: true }),
    uploadVideo: async () => ({ success: true }),
    fillDetails: async (clip, mode) => {
      modesUsed.push(mode);
      return { success: true };
    },
    submitPost: async (clip, mode) => ({ success: true, outcome: mode === 'draft' ? 'draft_saved' : 'scheduled_on_platform' }),
    reconcile: async () => ({ success: true }),
    resetUploadPage: async () => ({ success: true }),
  };

  const runner = createBatchRunner({
    clips,
    options: {
      mode: 'smart',
      cooldownSeconds: 0.01,
      maxScheduleQuota: 10,
      currentScheduleCount: 10, // Already at max quota!
    },
    actions: mockActions,
  });

  const summary = await runner.start();

  assert.equal(summary.successful, 2);
  assert.deepEqual(modesUsed, ['draft', 'draft']);
});

test('BatchRunner: resilient auto-skip on single clip failure without halting queue', async () => {
  const clips = [
    { id: 'clip-1', name: 'Clip 1' },
    { id: 'clip-failing', name: 'Failing Clip' },
    { id: 'clip-3', name: 'Clip 3' },
  ];

  const processed = [];

  const mockActions = {
    prepareClip: async (clip) => {
      if (clip.id === 'clip-failing') throw new Error('Out of stock error on Showcase item');
      return { success: true };
    },
    uploadVideo: async () => ({ success: true }),
    fillDetails: async () => ({ success: true }),
    submitPost: async (clip) => {
      processed.push(clip.id);
      return { success: true, outcome: 'scheduled_on_platform' };
    },
    reconcile: async () => ({ success: true }),
    resetUploadPage: async () => ({ success: true }),
  };

  const runner = createBatchRunner({
    clips,
    options: {
      mode: 'smart',
      cooldownSeconds: 0.01,
      autoSkipOnError: true,
    },
    actions: mockActions,
  });

  const summary = await runner.start();

  assert.equal(summary.total, 3);
  assert.equal(summary.successful, 2);
  assert.equal(summary.failed, 1);
  assert.deepEqual(processed, ['clip-1', 'clip-3']);
  assert.equal(summary.errors.length, 1);
  assert.equal(summary.errors[0].clipId, 'clip-failing');
});

test('BatchRunner: pause, resume, and stop controls operate smoothly', async () => {
  const clips = [
    { id: 'clip-1', name: 'Clip 1' },
    { id: 'clip-2', name: 'Clip 2' },
    { id: 'clip-3', name: 'Clip 3' },
  ];

  const completed = [];

  const mockActions = {
    prepareClip: async () => ({ success: true }),
    uploadVideo: async () => ({ success: true }),
    fillDetails: async () => ({ success: true }),
    submitPost: async (clip) => {
      completed.push(clip.id);
      return { success: true, outcome: 'scheduled_on_platform' };
    },
    reconcile: async () => ({ success: true }),
    resetUploadPage: async () => ({ success: true }),
  };

  const runner = createBatchRunner({
    clips,
    options: {
      cooldownSeconds: 0.05,
    },
    actions: mockActions,
  });

  // Start runner in background
  const runPromise = runner.start();

  // Allow first clip to start, then request pause
  await new Promise((r) => setTimeout(r, 20));
  runner.pause();
  assert.equal(runner.getState(), BATCH_STATES.PAUSED);

  // Resume after brief pause
  await new Promise((r) => setTimeout(r, 50));
  runner.resume();

  // Stop before finishing all clips
  await new Promise((r) => setTimeout(r, 80));
  runner.stop();

  const summary = await runPromise;
  assert.equal(runner.getState(), BATCH_STATES.STOPPED);
  assert.ok(summary.processed < 3);
});
