const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
  ORCHESTRATOR_STATES,
  CLIP_STAGES,
  calculateHumanJitter,
  createBatchOrchestrator,
} = require('./batch_orchestrator.js');

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

  const recorded = [];
  let orchestrator;
  orchestrator = createBatchOrchestrator({
    clips,
    options: { cooldownSeconds: 0 },
    actions: {
      updateBackend: async (clip) => { recorded.push(clip.id); },
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
  // Stop pressed while c2's post click was happening: c2 still gets verified and recorded (a live post must never go
  // unrecorded), the loop stops at the clip boundary, c3 never runs.
  assert.equal(summary.successful, 2);
  assert.deepEqual(recorded, ['c1', 'c2']);
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
  // an error after the submit started is "unknown" (the click may have happened), never "failed", never retried
  assert.equal(bad.failed, 0);
  assert.equal(bad.unknown, 1);
  assert.equal(submits, 1);

  // an error that provably happened before the click is a plain failure (and may be retried from a clean page)
  let clean = 0;
  const before = createBatchOrchestrator({
    clips: [{ id: 'c3', hook_title: 'คลิปพลาดก่อนกด' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, retryDelayMs: 1, maxClipAttempts: 1 },
    actions: {
      submitPost: async () => { clean += 1; const e = new Error('หาปุ่ม Post ไม่เจอ'); e.postAttempted = false; throw e; },
      resetUploadPage: async () => {},
    },
  });
  const notClicked = await before.start();
  assert.equal(notClicked.failed, 1);
  assert.equal(notClicked.unknown, 0);
  assert.equal(clean, 1);
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

test('R3: the submit stage is never retried, even for a "message port closed" style error', async () => {
  let submits = 0, recorded = [];
  const o = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'พอร์ตปิดหลังกด' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 3, retryDelayMs: 1 },
    actions: {
      submitPost: async () => { submits += 1; throw new Error('The message port closed before a response was received'); },
      updateBackend: async (_c, outcome) => { recorded.push(outcome); },
      resetUploadPage: async () => {},
    },
  });
  const stats = await o.start();
  assert.equal(submits, 1);
  assert.equal(stats.unknown, 1);
  assert.equal(stats.failed, 0);
  assert.deepEqual(recorded, ['confirmation_unknown']);   // reconcile is asked to look, once
  assert.equal(stats.finalKind, 'unknown');
});

test('R3: an error while verifying/recording after the click is unknown, not failed', async () => {
  const o = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'ตรวจผลล้ม' }],
    options: { cooldownSeconds: 0, maxRetriesPerStage: 0, retryDelayMs: 1 },
    actions: {
      submitPost: async () => ({ success: true, outcome: 'scheduled_on_platform' }),
      verifySuccessToast: async () => { throw new Error('verify crashed'); },
      updateBackend: async () => {},
      resetUploadPage: async () => {},
    },
  });
  const stats = await o.start();
  assert.equal(stats.unknown, 1);
  assert.equal(stats.failed, 0);
  assert.equal(stats.results[0].outcome, 'confirmation_unknown');
});

test('R3: Stop during the verify stage still records the result of that clip, then stops', async () => {
  const log = [];
  let o;
  o = createBatchOrchestrator({
    clips: [{ id: 'c1', hook_title: 'หนึ่ง' }, { id: 'c2', hook_title: 'สอง' }],
    options: { cooldownSeconds: 0 },
    actions: {
      submitPost: async (clip) => { log.push(`submit:${clip.id}`); return { success: true, outcome: 'published' }; },
      verifySuccessToast: async (clip, _m, r) => { o.abort(); log.push(`verify:${clip.id}`); return r; },
      updateBackend: async (clip, outcome) => { log.push(`update:${clip.id}:${outcome}`); },
    },
  });
  const stats = await o.start();
  assert.deepEqual(log, ['submit:c1', 'verify:c1', 'update:c1:published']);
  assert.equal(stats.state, ORCHESTRATOR_STATES.ABORTED);
  assert.equal(stats.successful, 1);
});

test('R3: final verdict is honest (partial / halted / success / missing action)', async () => {
  const ok = { submitPost: async () => ({ success: true, outcome: 'scheduled_on_platform' }), resetUploadPage: async () => {}, updateBackend: async () => {} };
  const all = await createBatchOrchestrator({ clips: [{ id: 'a' }, { id: 'b' }], options: { cooldownSeconds: 0 }, actions: ok }).start();
  assert.equal(all.finalKind, 'success');
  let n = 0;
  const some = await createBatchOrchestrator({
    clips: [{ id: 'a' }, { id: 'b' }], options: { cooldownSeconds: 0, maxClipAttempts: 1, retryDelayMs: 1, maxRetriesPerStage: 0 },
    actions: { ...ok, injectFile: async () => { n += 1; if (n === 1) throw new Error('boom'); } },
  }).start();
  assert.equal(some.finalKind, 'partial');
  assert.equal(some.failed, 1);
  assert.match(some.hudText, /ล้มเหลว 1/);
  const halted = await createBatchOrchestrator({
    clips: [{ id: 'a', force_mode: 'draft' }, { id: 'b' }], options: { cooldownSeconds: 0, mode: 'draft_only', allowDraft: false }, actions: ok,
  }).start();
  assert.equal(halted.finalKind, 'halted');
  assert.ok(halted.haltReason);
  const missing = await createBatchOrchestrator({ clips: [{ id: 'a' }], options: { requiredActions: ['injectFile|uploadVideo', 'submitPost|triggerSubmit'] }, actions: { submitPost: async () => ({}) } }).start();
  assert.equal(missing.state, ORCHESTRATOR_STATES.ERROR);
  assert.equal(missing.processed, 0);
});

test('R3: finalVerdict never paints a run green unless every clip ended as planned', () => {
  const { finalVerdict } = require('./batch_orchestrator.js');
  const base = { successful: 2, failed: 0, unknown: 0, total: 2 };
  assert.equal(finalVerdict({ ...base, finalKind: 'success' }).kind, 'success');
  assert.equal(finalVerdict({ ...base, successful: 1, unknown: 1, finalKind: 'unknown' }).kind, 'warn');
  assert.match(finalVerdict({ ...base, successful: 1, unknown: 1, finalKind: 'unknown' }).text, /ยืนยันผลไม่ได้/);
  assert.equal(finalVerdict({ ...base, successful: 1, failed: 1, finalKind: 'partial' }).kind, 'warn');
  assert.equal(finalVerdict({ ...base, finalKind: 'halted', haltReason: 'โควตาเต็ม' }).kind, 'error');
  assert.equal(finalVerdict({ ...base, finalKind: 'error', circuitReason: 'ล้มติดกัน 3 คลิป' }).kind, 'error');
  assert.equal(finalVerdict({ ...base, finalKind: 'aborted' }).kind, 'warn');
  assert.notEqual(finalVerdict({ ...base, finalKind: 'running' }).kind, 'success');   // unexpected state is never "success"
});

test('R5: a failed or unconfirmed clip asks the embedder for page evidence; a broken evidence hook never breaks the run', async () => {
  const seen = [];
  const failing = createBatchOrchestrator({
    clips: [{ id: 'a', hook_title: 'ล้ม' }],
    options: { cooldownSeconds: 0, maxClipAttempts: 1, maxRetriesPerStage: 0, retryDelayMs: 1 },
    actions: {
      injectFile: async () => { throw new Error('boom'); },
      captureEvidence: async (clip, info) => { seen.push([clip.id, info.kind, info.stage]); },
      resetUploadPage: async () => {},
    },
  });
  await failing.start();
  assert.deepEqual(seen, [['a', 'failed', 'INJECT_FILE']]);

  const unknownSeen = [];
  const unknown = createBatchOrchestrator({
    clips: [{ id: 'b', hook_title: 'ไม่แน่ใจ' }],
    options: { cooldownSeconds: 0 },
    actions: {
      submitPost: async () => { throw new Error('port closed'); },
      updateBackend: async () => {},
      captureEvidence: async (clip, info) => { unknownSeen.push(info.kind); throw new Error('evidence failed'); },
      resetUploadPage: async () => {},
    },
  });
  const stats = await unknown.start();
  assert.deepEqual(unknownSeen, ['unknown']);
  assert.equal(stats.unknown, 1);                       // the run still finished and counted the clip
});

test('a forced schedule (publishing a draft) stops when the schedule slots are used up, instead of failing at TikTok', async () => {
  const sent = [];
  const o = createBatchOrchestrator({
    clips: [{ id: 'd1', hook_title: 'แบบร่าง', force_mode: 'schedule', publish_draft: true }],
    options: { cooldownSeconds: 0, currentScheduleCount: 30, maxScheduleQuota: 30, mode: 'smart' },
    actions: { submitPost: async () => { sent.push('submit'); return { success: true, outcome: 'scheduled_on_platform' }; }, updateBackend: async () => {} },
  });
  const stats = await o.start();
  assert.deepEqual(sent, []);
  assert.equal(stats.finalKind, 'halted');
  assert.match(stats.haltReason, /ช่องตั้งเวลาเต็ม/);
});
