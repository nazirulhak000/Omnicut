const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
  ORCHESTRATOR_STATES,
  CLIP_STAGES,
  calculateHumanJitter,
  createBatchOrchestrator,
} = require('./batch_orchestrator.js');

const {
  LIVE_SELECTORS,
  DOM_TIMINGS,
  handleSignal,
  queryWithFallback,
  waitForSelector,
  dismissInterrupts,
  triggerSubmitWhenEnabled,
  waitForSuccessToast,
  runLiveDomSanityCheck,
} = require('./content_script.js');

test('Phase 1: Happy Path executes IDLE -> CHECK_QUOTA -> FETCH_BATCH -> LOOP_CYCLE (all 10 stages) -> COMPLETED', async () => {
  const stateHistory = [];
  const stageHistory = [];
  const logs = [];
  const backendUpdates = [];

  const mockClips = [
    { id: 'c1', hook_title: 'คลิปทดสอบ 1', cover_path: 'c1.webp', schedule_date: '2026-11-01', schedule_time: '12:00' },
    { id: 'c2', hook_title: 'คลิปทดสอบ 2', cover_path: 'c2.webp', schedule_date: '2026-11-01', schedule_time: '15:00' },
  ];

  const orchestrator = createBatchOrchestrator({
    options: {
      mode: 'smart',
      maxBatchCap: 30,
      maxScheduleQuota: 30,
      cooldownSeconds: 0.05,
      minJitter: 0,
      maxJitter: 0.05,
    },
    actions: {
      checkQuota: async () => ({ scheduledCount: 5, draftCount: 0, recommendedBatchLimit: 25 }),
      fetchBatch: async () => mockClips,
      injectFile: async () => ({ injected: true }),
      awaitProcessing: async () => ({ uploaded: 100 }),
      fillMetadata: async () => ({ filled: true }),
      handleCover: async () => ({ coverUploaded: true }),
      dismissInterrupts: async () => ({ dismissed: [] }),
      applyScheduleOrDraft: async (_clip, mode) => ({ applied: mode }),
      triggerSubmit: async () => ({ submitted: true }),
      verifySuccessToast: async (_clip, mode) => ({ confirmed: true, outcome: mode === 'schedule' ? 'scheduled' : 'draft_saved' }),
      updateBackend: async (clip, outcome) => {
        backendUpdates.push({ id: clip.id, outcome });
      },
      resetUploadPage: async () => {},
    },
    onStateChange: (st) => {
      if (stateHistory[stateHistory.length - 1] !== st) stateHistory.push(st);
    },
    onStageChange: (stg) => {
      if (stg) stageHistory.push(stg);
    },
    onLog: (msg, kind) => logs.push({ msg, kind }),
  });

  assert.equal(orchestrator.getState(), ORCHESTRATOR_STATES.IDLE);

  const summary = await orchestrator.start();

  assert.equal(summary.state, ORCHESTRATOR_STATES.COMPLETED);
  assert.equal(summary.total, 2);
  assert.equal(summary.successful, 2);
  assert.equal(summary.failed, 0);
  assert.equal(summary.percent, 100);
  assert.ok(summary.hudText.includes('เสร็จสิ้น 2/2 คลิป [100%]'));

  // Verify top-level state transitions
  assert.ok(stateHistory.includes(ORCHESTRATOR_STATES.CHECK_QUOTA));
  assert.ok(stateHistory.includes(ORCHESTRATOR_STATES.FETCH_BATCH));
  assert.ok(stateHistory.includes(ORCHESTRATOR_STATES.LOOP_CYCLE));
  assert.equal(stateHistory[stateHistory.length - 1], ORCHESTRATOR_STATES.COMPLETED);

  // Verify all 10 stages ran in sequence for Clip 1
  const expectedFirstClipStages = [
    CLIP_STAGES.INJECT_FILE,
    CLIP_STAGES.AWAIT_PROCESSING,
    CLIP_STAGES.FILL_METADATA,
    CLIP_STAGES.HANDLE_COVER,
    CLIP_STAGES.DISMISS_INTERRUPTS,
    CLIP_STAGES.APPLY_SCHEDULE_OR_DRAFT,
    CLIP_STAGES.TRIGGER_SUBMIT,
    CLIP_STAGES.VERIFY_SUCCESS_TOAST,
    CLIP_STAGES.UPDATE_BACKEND,
    CLIP_STAGES.CALCULATED_JITTER,
  ];
  assert.deepEqual(stageHistory.slice(0, 10), expectedFirstClipStages);
  assert.deepEqual(backendUpdates, [
    { id: 'c1', outcome: 'scheduled' },
    { id: 'c2', outcome: 'scheduled' },
  ]);
});

test('Phase 1: Interrupting Modal (Copyright / Tutorial / Discard) is dismissed during DISMISS_INTERRUPTS and post-submit', async () => {
  const interruptCalls = [];
  const orchestrator = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'คลิปติดตรวจลิขสิทธิ์' }],
    options: { cooldownSeconds: 0 },
    actions: {
      dismissInterrupts: async (clip, opts = {}) => {
        interruptCalls.push({ id: clip.id, postSubmit: Boolean(opts.postSubmit) });
        return { dismissed: opts.postSubmit ? ['copyright_post_now'] : ['tutorial_got_it'] };
      },
      triggerSubmit: async () => ({ clicked: true }),
      verifySuccessToast: async () => ({ confirmed: true, outcome: 'scheduled' }),
    },
  });

  const summary = await orchestrator.start();
  assert.equal(summary.successful, 1);
  assert.deepEqual(interruptCalls, [
    { id: 'c1', postSubmit: false },
    { id: 'c1', postSubmit: true },
  ]);
});

test('Phase 1: Quota Full scenario stops safely in schedule_only mode; smart mode stops (never posts live) once the schedule quota is full', async () => {
  // 1. schedule_only mode when 30/30 full -> stops immediately with 0 uploads
  let uploadedCount = 0;
  const fullSchedOrchestrator = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'Clip 1' }],
    options: { mode: 'schedule_only', maxScheduleQuota: 30, cooldownSeconds: 0 },
    actions: {
      checkQuota: async () => ({ scheduledCount: 30, draftCount: 5, recommendedBatchLimit: 0 }),
      injectFile: async () => { uploadedCount += 1; },
    },
  });

  const fullSummary = await fullSchedOrchestrator.start();
  assert.equal(fullSummary.state, ORCHESTRATOR_STATES.COMPLETED);
  assert.equal(uploadedCount, 0);

  // 2. smart mode when 29/30 scheduled -> Clip 1 is 'schedule'; Clip 2 would be a draft, which the side panel
  //    cannot save (its submit step presses Post = publish live), so the batch must stop before touching it
  const modesApplied = [];
  const smartOrchestrator = createBatchOrchestrator({
    clips: [
      { id: 'c1', hook_title: 'Clip 30' },
      { id: 'c2', hook_title: 'Clip 31 (Overflow to Draft)' },
    ],
    options: { mode: 'smart', maxScheduleQuota: 30, cooldownSeconds: 0 },
    actions: {
      checkQuota: async () => ({ scheduledCount: 29, draftCount: 0 }),
      applyScheduleOrDraft: async (clip, targetMode) => {
        modesApplied.push({ id: clip.id, mode: targetMode });
      },
    },
  });

  const smartSummary = await smartOrchestrator.start();
  assert.equal(smartSummary.successful, 1);
  assert.deepEqual(modesApplied, [
    { id: 'c1', mode: 'schedule' },
  ]);

  // draft_only never starts a clip either
  let draftOnlyUploads = 0;
  const draftOnly = createBatchOrchestrator({
    clips: [{ id: 'd1', hook_title: 'Draft clip' }],
    options: { mode: 'draft_only', maxScheduleQuota: 30, cooldownSeconds: 0 },
    actions: { checkQuota: async () => ({ scheduledCount: 0, draftCount: 0 }), injectFile: async () => { draftOnlyUploads += 1; } },
  });
  await draftOnly.start();
  assert.equal(draftOnlyUploads, 0);

  // an embedder that really saves drafts can still opt in
  const modes = [];
  const optIn = createBatchOrchestrator({
    clips: [{ id: 'e1', hook_title: 'Draft clip' }],
    options: { mode: 'draft_only', allowDraft: true, maxScheduleQuota: 30, cooldownSeconds: 0 },
    actions: { checkQuota: async () => ({ scheduledCount: 0, draftCount: 0 }), applyScheduleOrDraft: async (clip, targetMode) => { modes.push(targetMode); } },
  });
  await optIn.start();
  assert.deepEqual(modes, ['draft']);
});

test('Phase 1: Transient Network Disconnect automatically retries and recovers without failing the clip', async () => {
  let fillAttempts = 0;
  let backendAttempts = 0;

  const orchestrator = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'คลิปเน็ตกระตุก' }],
    options: {
      cooldownSeconds: 0,
      maxRetriesPerStage: 2,
      retryDelayMs: 10,
    },
    actions: {
      fillMetadata: async () => {
        fillAttempts += 1;
        if (fillAttempts === 1) {
          throw new Error('Network timeout while waiting for DOM transition');
        }
        return { ok: true };
      },
      updateBackend: async () => {
        backendAttempts += 1;
        if (backendAttempts < 3) {
          throw new Error('fetch failed: ECONNRESET 503');
        }
        return { synced: true };
      },
    },
  });

  const summary = await orchestrator.start();
  assert.equal(summary.state, ORCHESTRATOR_STATES.COMPLETED);
  assert.equal(summary.successful, 1);
  assert.equal(summary.failed, 0);
  assert.equal(fillAttempts, 2);
  assert.equal(backendAttempts, 3);
});

test('Phase 1: User Pause, Resume, and Abort/Stop signals work deterministically mid-loop', async () => {
  const signalsSent = [];
  const clips = [
    { id: 'c1', hook_title: 'Clip 1' },
    { id: 'c2', hook_title: 'Clip 2' },
    { id: 'c3', hook_title: 'Clip 3' },
  ];

  let orchestrator;
  orchestrator = createBatchOrchestrator({
    clips,
    options: { cooldownSeconds: 0 },
    actions: {
      notifySignal: async (sig) => { signalsSent.push(sig); },
      injectFile: async (clip) => {
        if (clip.id === 'c2') {
          orchestrator.pause();
          setTimeout(() => orchestrator.resume(), 30);
        }
      },
      triggerSubmit: async (clip) => {
        if (clip.id === 'c2') {
          orchestrator.abort();
        }
      },
    },
  });

  const summary = await orchestrator.start();
  assert.equal(summary.state, ORCHESTRATOR_STATES.ABORTED);
  assert.equal(summary.successful, 1); // c1 finished, c2 aborted at triggerSubmit, c3 never ran
  assert.ok(signalsSent.includes('PAUSE'));
  assert.ok(signalsSent.includes('RESUME'));
  assert.ok(signalsSent.includes('ABORT'));
});

test('Phase 1: Human-Paced Jitter stays within natural bounds', () => {
  assert.equal(calculateHumanJitter(0), 0);
  const low = calculateHumanJitter(20, -3, 5, () => 0);
  const high = calculateHumanJitter(20, -3, 5, () => 1);
  assert.equal(low, 17);
  assert.equal(high, 25);
});

test('Phase 2: Content Script Live Selectors, Event-Driven waitForSelector, and Interrupt Dismissers', async () => {
  assert.ok(Array.isArray(LIVE_SELECTORS.fileInput));
  assert.equal(LIVE_SELECTORS.fileInput[0], 'input[type="file"][accept="video/*"]');
  assert.equal(LIVE_SELECTORS.submitPostButton[0], 'button[data-e2e="post_video_button"]');
  assert.equal(LIVE_SELECTORS.saveDraftButton[0], 'button[data-e2e="save_draft_button"]');
  assert.ok(DOM_TIMINGS.popoverOpenLatencyMs > 0);

  // Signal state handling
  assert.equal(handleSignal('PAUSE').state, 'PAUSED');
  assert.equal(handleSignal('RESUME').state, 'RESUMED');
  assert.equal(handleSignal('ABORT').state, 'ABORTED');
  assert.equal(handleSignal('RESET').state, 'IDLE');

  // Mock DOM for waitForSelector, dismissInterrupts, triggerSubmitWhenEnabled, waitForSuccessToast
  let postNowClicked = false;
  let submitClicked = false;
  const mockPostBtn = {
    disabled: false,
    innerText: 'Schedule',
    getAttribute: (attr) => (attr === 'aria-disabled' ? 'false' : (attr === 'data-e2e' ? 'post_video_button' : null)),
    getBoundingClientRect: () => ({ width: 120, height: 40 }),
    scrollIntoView: () => {},
    click: () => { submitClicked = true; },
  };
  const mockDialog = {
    innerText: 'Continue to post? We are still checking your video before the check is complete.',
    getBoundingClientRect: () => ({ width: 400, height: 200 }),
    querySelectorAll: () => [
      {
        disabled: false,
        innerText: 'Post now',
        getAttribute: () => 'false',
        click: () => { postNowClicked = true; },
      },
    ],
  };
  const mockToast = {
    innerText: 'Video scheduled successfully',
    getBoundingClientRect: () => ({ width: 250, height: 48 }),
  };

  const mockRoot = {
    nodeType: 1,
    querySelectorAll: (sel) => {
      if (sel.includes('post_video_button')) return [mockPostBtn];
      if (sel.includes('TUXModal') || sel === '[role="dialog"]') return [mockDialog];
      if (sel.includes('toast') || sel === '[role="alert"]') return [mockToast];
      return [];
    },
  };

  const foundBtn = await waitForSelector('submitPostButton', { root: mockRoot, requireVisible: true, requireEnabled: true, timeoutMs: 500 });
  assert.equal(foundBtn, mockPostBtn);

  const disRes = await dismissInterrupts({ root: mockRoot });
  assert.deepEqual(disRes.dismissed, ['copyright_post_now']);
  assert.equal(postNowClicked, true);

  const subRes = await triggerSubmitWhenEnabled({ mode: 'schedule', root: mockRoot, timeoutMs: 500 });
  assert.equal(subRes.clicked, true);
  assert.equal(submitClicked, true);

  const toastRes = await waitForSuccessToast({ root: mockRoot, timeoutMs: 500 });
  assert.equal(toastRes.confirmed, true);
  assert.equal(toastRes.outcome, 'scheduled');

  const sanity = runLiveDomSanityCheck(mockRoot);
  assert.equal(sanity.ok, true);
  assert.equal(sanity.report.submitPostButton.matched, true);
});

test('B2: shouldReconcileAfterPost reads the string outcome and the result object', () => {
  const { shouldReconcileAfterPost } = require('./batch_orchestrator.js');
  assert.equal(shouldReconcileAfterPost('confirmation_unknown', null), true);
  assert.equal(shouldReconcileAfterPost('scheduled', {markError: 'ack failed'}), true);
  assert.equal(shouldReconcileAfterPost('scheduled', {outcome: 'confirmation_unknown'}), true);
  assert.equal(shouldReconcileAfterPost({outcome: 'confirmation_unknown'}), true);
  assert.equal(shouldReconcileAfterPost('published', {success: true, outcome: 'published'}), false);
  assert.equal(shouldReconcileAfterPost('scheduled', undefined), false);
});

test('a pre-submit failure retries the clip once from a clean page; a post-submit failure never does', async () => {
  let injects = 0, resets = 0, submits = 0;
  const pre = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'คลิปพลาดก่อนโพสต์' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, retryDelayMs: 1 },
    actions: {
      injectFile: async () => { injects += 1; if (injects === 1) throw new Error('เลือกสินค้าตรง ID ไม่สำเร็จ'); },
      resetUploadPage: async () => { resets += 1; },
    },
  });
  const ok = await pre.start();
  assert.equal(ok.successful, 1);
  assert.equal(ok.failed, 0);
  assert.equal(injects, 2);
  assert.equal(resets, 1);

  const post = createBatchOrchestrator({
    clips: [{ id: 'c2', hook_title: 'คลิปพลาดหลังกดโพสต์' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, retryDelayMs: 1 },
    actions: {
      submitPost: async () => { submits += 1; throw new Error('post_not_confirmed'); },
      resetUploadPage: async () => {},
    },
  });
  const bad = await post.start();
  assert.equal(bad.failed, 1);
  assert.equal(submits, 1);
});

test('worker channel errors (port closed / context invalidated) are retried as transient', async () => {
  let waits = 0;
  const o = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'worker ถูกปิดกลางงาน' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 2, retryDelayMs: 1 },
    actions: {
      awaitProcessing: async () => { waits += 1; if (waits === 1) throw new Error('A listener indicated an asynchronous response by returning true, but the message port closed before a response was received'); },
    },
  });
  const res = await o.start();
  assert.equal(res.successful, 1);
  assert.equal(waits, 2);
});

test('3 failed clips in a row open the circuit breaker instead of grinding through the whole batch', async () => {
  let injects = 0;
  const o = createBatchOrchestrator({
    clips: ['a', 'b', 'c', 'd', 'e'].map(id => ({ id, hook_title: `คลิป ${id}` })),
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, maxClipAttempts: 1, retryDelayMs: 1 },
    actions: { injectFile: async () => { injects += 1; throw new Error('selector missing'); }, resetUploadPage: async () => {} },
  });
  const res = await o.start();
  assert.equal(res.state, ORCHESTRATOR_STATES.ERROR);
  assert.equal(res.failed, 3);
  assert.equal(injects, 3);
});

test('an unconfirmed post is counted as unknown (never success); two in a row stop the run', async () => {
  const o = createBatchOrchestrator({
    clips: ['a', 'b', 'c', 'd'].map(id => ({ id, hook_title: `คลิป ${id}` })),
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, maxClipAttempts: 1, retryDelayMs: 1 },
    actions: {
      submitPost: async () => ({ success: true, outcome: 'confirmation_unknown' }),
      resetUploadPage: async () => {},
    },
  });
  const res = await o.start();
  assert.equal(res.successful, 0);
  assert.equal(res.unknown, 2);
  assert.equal(res.state, ORCHESTRATOR_STATES.ERROR);
  assert.ok(res.results.every(r => r.success === false && r.unknown === true));

  const mixed = createBatchOrchestrator({
    clips: ['a', 'b', 'c'].map(id => ({ id, hook_title: `คลิป ${id}` })),
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, maxClipAttempts: 1, retryDelayMs: 1 },
    actions: {
      submitPost: async clip => ({ success: true, outcome: clip.id === 'b' ? 'confirmation_unknown' : 'scheduled_on_platform' }),
      resetUploadPage: async () => {},
    },
  });
  const ok = await mixed.start();
  assert.equal(ok.successful, 2);
  assert.equal(ok.unknown, 1);
  assert.equal(ok.state, ORCHESTRATOR_STATES.COMPLETED);
});

test('Draft mode (allowDraft): smart schedules until the schedule quota is full, then saves drafts with the draft step', async () => {
  const submitted = [];
  const orchestrator = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'Last schedule slot' }, { id: 'c2', hook_title: 'First draft' }, { id: 'c3', hook_title: 'Second draft' }],
    options: { mode: 'smart', allowDraft: true, maxScheduleQuota: 30, maxDraftQuota: 30, cooldownSeconds: 0 },
    actions: {
      checkQuota: async () => ({ scheduledCount: 29, draftCount: 0 }),
      submitPost: async (clip, targetMode) => { submitted.push({ id: clip.id, mode: targetMode }); return { success: true, outcome: targetMode === 'draft' ? 'draft_saved' : 'scheduled_on_platform' }; },
    },
  });
  const summary = await orchestrator.start();
  assert.equal(summary.successful, 3);
  assert.deepEqual(submitted, [
    { id: 'c1', mode: 'schedule' },
    { id: 'c2', mode: 'draft' },
    { id: 'c3', mode: 'draft' },
  ]);
});

test('Draft mode: draft quota full (30/30) stops the batch and never saves a 31st draft', async () => {
  const submitted = [];
  const logs = [];
  const orchestrator = createBatchOrchestrator({
    clips: [{ id: 'd1', hook_title: 'Draft 30' }, { id: 'd2', hook_title: 'Draft 31' }, { id: 'd3', hook_title: 'Draft 32' }],
    options: { mode: 'draft_only', allowDraft: true, maxDraftQuota: 30, cooldownSeconds: 0 },
    onLog: (line) => logs.push(String(line)),
    actions: {
      checkQuota: async () => ({ scheduledCount: 10, draftCount: 29 }),
      submitPost: async (clip, targetMode) => { submitted.push({ id: clip.id, mode: targetMode }); return { success: true, outcome: 'draft_saved' }; },
    },
  });
  const summary = await orchestrator.start();
  assert.equal(summary.successful, 1);
  assert.deepEqual(submitted, [{ id: 'd1', mode: 'draft' }]);
  assert.ok(logs.some((line) => /โควตาแบบร่างเต็ม/.test(line)));
});

test('Draft mode: draft_saved counts as success (not unknown) and is never sent to reconcile', async () => {
  const { shouldReconcileAfterPost } = require('./batch_orchestrator.js');
  assert.equal(shouldReconcileAfterPost('draft_saved', { outcome: 'draft_saved' }), false);
  assert.equal(shouldReconcileAfterPost('confirmation_unknown', {}), true);
});
