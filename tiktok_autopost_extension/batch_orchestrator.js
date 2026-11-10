/**
 * Phase 1: Batch State Machine & Orchestrator (batch_orchestrator.js)
 * Controls the 1-Click Autonomous Batch Upload Loop (up to 30 clips per quota).
 *
 * Top-level State Machine:
 *   IDLE -> CHECK_QUOTA -> FETCH_BATCH -> LOOP_CYCLE -> COMPLETED / PAUSED / ABORTED / ERROR
 *
 * Per-Clip 10-Stage Cycle inside LOOP_CYCLE:
 *   1. INJECT_FILE
 *   2. AWAIT_PROCESSING
 *   3. FILL_METADATA
 *   4. HANDLE_COVER
 *   5. DISMISS_INTERRUPTS
 *   6. APPLY_SCHEDULE_OR_DRAFT
 *   7. TRIGGER_SUBMIT
 *   8. VERIFY_SUCCESS_TOAST
 *   9. UPDATE_BACKEND
 *  10. CALCULATED_JITTER
 */
(function attachBatchOrchestrator(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.OmniBatchOrchestrator = api;
    // Also expose on OmniBatchRunner if not already overridden, or keep compatible
    if (!root.OmniBatchRunner) {
      root.OmniBatchRunner = api;
    }
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  const LIMITS = (typeof module === 'object' && module.exports) ? require('./limits.js') : globalThis.OmniLimits;

  const ORCHESTRATOR_STATES = {
    IDLE: 'IDLE',
    CHECK_QUOTA: 'CHECK_QUOTA',
    FETCH_BATCH: 'FETCH_BATCH',
    LOOP_CYCLE: 'LOOP_CYCLE',
    PAUSED: 'PAUSED',
    ABORTED: 'ABORTED',
    STOPPED: 'STOPPED',
    COMPLETED: 'COMPLETED',
    ERROR: 'ERROR',
  };

  const CLIP_STAGES = {
    INJECT_FILE: 'INJECT_FILE',
    AWAIT_PROCESSING: 'AWAIT_PROCESSING',
    FILL_METADATA: 'FILL_METADATA',
    HANDLE_COVER: 'HANDLE_COVER',
    DISMISS_INTERRUPTS: 'DISMISS_INTERRUPTS',
    APPLY_SCHEDULE_OR_DRAFT: 'APPLY_SCHEDULE_OR_DRAFT',
    TRIGGER_SUBMIT: 'TRIGGER_SUBMIT',
    VERIFY_SUCCESS_TOAST: 'VERIFY_SUCCESS_TOAST',
    UPDATE_BACKEND: 'UPDATE_BACKEND',
    CALCULATED_JITTER: 'CALCULATED_JITTER',
  };

  const POST_SUBMIT_STAGES = new Set(['TRIGGER_SUBMIT', 'VERIFY_SUCCESS_TOAST', 'UPDATE_BACKEND', 'CALCULATED_JITTER']);

  const STAGE_LABELS_TH = {
    IDLE: 'พร้อมทำงาน',
    CHECK_QUOTA: 'กำลังตรวจสอบโควตา TikTok Studio...',
    FETCH_BATCH: 'กำลังดึงรายการคิวคลิป...',
    INJECT_FILE: 'กำลังส่งไฟล์วิดีโอเข้า TikTok Studio...',
    AWAIT_PROCESSING: 'กำลังรออัปโหลดวิดีโอ 100%...',
    FILL_METADATA: 'กำลังป้อนแคปชัน แฮชแท็ก และตะกร้า...',
    HANDLE_COVER: 'กำลังอัปโหลดภาพปก 3:4...',
    DISMISS_INTERRUPTS: 'กำลังตรวจและปิดป๊อปอัปแทรกซ้อน...',
    APPLY_SCHEDULE_OR_DRAFT: 'กำลังตั้งเวลาโพสต์ / บันทึกแบบร่าง...',
    TRIGGER_SUBMIT: 'กำลังกดยืนยันส่งโพสต์...',
    VERIFY_SUCCESS_TOAST: 'กำลังรอยืนยันสถานะความสำเร็จ (Toast)...',
    UPDATE_BACKEND: 'กำลังซิงค์สถานะกลับฐานข้อมูล OmniCut...',
    CALCULATED_JITTER: 'กำลังพักหน่วงเวลาปลอดภัย (Human-Paced Jitter)...',
    PAUSED: 'พักการทำงานชั่วคราว',
    ABORTED: 'ยกเลิกการทำงาน',
    STOPPED: 'หยุดการทำงาน',
    COMPLETED: 'เสร็จสิ้นทั้งหมด',
    ERROR: 'เกิดข้อผิดพลาด',
  };

  /**
   * Computes human-paced jitter in seconds between baseMin and baseMax.
   */
  function calculateHumanJitter(baseSeconds = 22, minJitter = -4, maxJitter = 8, rng = Math.random) {
    const base = Math.max(0, Number(baseSeconds) || 0);
    if (base === 0) return 0;
    const span = maxJitter - minJitter;
    const delta = minJitter + rng() * span;
    return Math.max(1, Math.round((base + delta) * 10) / 10);
  }

  function createBatchOrchestrator({
    clips: initialClips = [],
    options = {},
    actions = {},
    onStateChange = () => {},
    onStageChange = () => {},
    onLog = () => {},
    onCooldownTick = () => {},
  } = {}) {
    const {
      mode = 'smart', // 'smart' | 'schedule_only' | 'draft_only'
      allowDraft = false, // only an embedder that really saves drafts may set this
      maxBatchCap = LIMITS.SCHEDULE_CAP,
      maxScheduleQuota = LIMITS.SCHEDULE_CAP,
      maxDraftQuota = LIMITS.DRAFT_CAP,
      currentScheduleCount = 0,
      currentDraftCount = 0,
      cooldownSeconds = LIMITS.COOLDOWN_SECONDS,
      minJitter = -3,
      maxJitter = 6,
      autoSkipOnError = true,
      requiredActions = [], // names of actions the embedder must provide (any of a|b means an alias pair)
      maxRetriesPerStage = 2,
      maxClipAttempts = 2,
      maxConsecutiveFailures = 3,
      maxConsecutiveUnknown = 2,
      retryDelayMs = 250,
      rng = Math.random,
    } = options;

    let state = ORCHESTRATOR_STATES.IDLE;
    let stage = null;
    let batchClips = Array.isArray(initialClips) ? [...initialClips] : [];
    let currentIndex = 0;
    let successful = 0;
    let failed = 0;
    let unknown = 0;
    let consecutiveFailures = 0;
    let consecutiveUnknown = 0;
    let circuitReason = '';
    let scheduleUsed = currentScheduleCount;
    let draftUsed = currentDraftCount;
    let quotaInfo = null;
    const errors = [];
    const results = [];

    let isPaused = false;
    let isAborted = false;
    let inCriticalSection = false;   // true from the post click until its result is recorded
    let haltReason = '';
    let pauseResolver = null;
    let remainingCooldown = 0;

    function getProgressPercent() {
      const total = batchClips.length;
      if (!total) return 0;
      const stageOrder = Object.values(CLIP_STAGES);
      const stageIdx = stage ? Math.max(0, stageOrder.indexOf(stage)) : 0;
      const stageFraction = state === ORCHESTRATOR_STATES.LOOP_CYCLE
        ? (stageIdx / stageOrder.length)
        : 0;
      const completedUnits = Math.min(total, successful + failed + unknown + stageFraction);
      return Math.min(100, Math.round((completedUnits / total) * 100));
    }

    function getHudStatusText() {
      const total = batchClips.length;
      const clipNum = Math.min(total, currentIndex + 1);
      const pct = getProgressPercent();
      const label = STAGE_LABELS_TH[stage] || STAGE_LABELS_TH[state] || state;
      if (state === ORCHESTRATOR_STATES.COMPLETED) {
        return getFinalKind() === 'success'
          ? `เสร็จสิ้น ${successful}/${total} คลิป [100%] - อัปโหลดครบชุดเรียบร้อย`
          : `จบรอบ: สำเร็จ ${successful}/${total}, ล้มเหลว ${failed}, ยืนยันไม่ได้ ${unknown}`;
      }
      if (state === ORCHESTRATOR_STATES.ABORTED || state === ORCHESTRATOR_STATES.STOPPED) {
        return `หยุดที่คลิป ${clipNum}/${total} [${pct}%] - ผู้ใช้สั่งหยุดลูป`;
      }
      if (total > 0) {
        return `คลิปที่ ${clipNum}/${total} [${pct}%] - ${label}`;
      }
      return label;
    }

    // Honest one-word verdict for the UI: success only when every clip ended as planned.
    function getFinalKind() {
      if (state === ORCHESTRATOR_STATES.ERROR) return 'error';
      if (state === ORCHESTRATOR_STATES.ABORTED || state === ORCHESTRATOR_STATES.STOPPED) return 'aborted';
      if (state !== ORCHESTRATOR_STATES.COMPLETED) return 'running';
      if (haltReason) return 'halted';
      if (failed > 0) return 'partial';
      if (unknown > 0) return 'unknown';
      if (batchClips.length === 0) return 'empty';
      return successful >= batchClips.length ? 'success' : 'halted';
    }

    function getStats() {
      const total = batchClips.length;
      const remainingClips = Math.max(0, total - (successful + failed + unknown));
      const estSecPerClip = 45 + (cooldownSeconds || 0);
      const etaSeconds = remainingClips * estSecPerClip;

      return {
        state,
        stage,
        stageLabel: STAGE_LABELS_TH[stage] || STAGE_LABELS_TH[state] || state,
        hudText: getHudStatusText(),
        percent: getProgressPercent(),
        total,
        currentIndex,
        clipNumber: total > 0 ? Math.min(total, currentIndex + 1) : 0,
        processed: successful + failed + unknown,
        successful,
        failed,
        unknown,
        scheduleUsed,
        draftUsed,
        quotaInfo,
        remainingClips,
        activeClip: batchClips[currentIndex] || null,
        remainingCooldown,
        etaSeconds,
        isPaused,
        isStopped: isAborted,
        isAborted,
        haltReason,
        circuitReason,
        finalKind: getFinalKind(),
        errors: [...errors],
        results: [...results],
      };
    }

    function setState(nextState) {
      state = nextState;
      onStateChange(state, getStats());
    }

    function setStage(nextStage) {
      stage = nextStage;
      onStageChange(stage, getStats());
      onStateChange(state, getStats());
    }

    function log(msg, kind = 'info') {
      onLog(msg, kind, getStats());
    }

    async function checkControlGate() {
      if (inCriticalSection) return;   // after the post click: verify/update must finish, Stop waits for the clip boundary
      if (isAborted) {
        const err = new Error('BATCH_ABORTED');
        err.code = 'BATCH_ABORTED';
        throw err;
      }
      if (isPaused) {
        const prevState = state;
        setState(ORCHESTRATOR_STATES.PAUSED);
        log('⏸️ พักการทำงานชั่วคราว (Paused)...', 'warn');
        if (actions.notifySignal) {
          try { await actions.notifySignal('PAUSE'); } catch (_) {}
        }
        await new Promise((resolve) => {
          pauseResolver = resolve;
        });
        if (isAborted) {
          const err = new Error('BATCH_ABORTED');
          err.code = 'BATCH_ABORTED';
          throw err;
        }
        if (actions.notifySignal) {
          try { await actions.notifySignal('RESUME'); } catch (_) {}
        }
        setState(prevState === ORCHESTRATOR_STATES.PAUSED ? ORCHESTRATOR_STATES.LOOP_CYCLE : prevState);
      }
    }

    async function runWithRetry(stageName, fn, { gate = true } = {}) {
      let attempt = 0;
      while (true) {
        if (gate) await checkControlGate();
        try {
          return await fn(attempt);
        } catch (err) {
          if (err?.code === 'BATCH_ABORTED' || err?.message === 'BATCH_ABORTED' || err?.message === 'BATCH_STOPPED') {
            throw err;
          }
          attempt += 1;
          const isTransient = Boolean(
            err?.transient ||
            /network|timeout|fetch|offline|ECONN|502|503|504|ไม่ทัน|ยังโหลดไม่เสร็จ|transition|message port closed|Receiving end does not exist|Extension context invalidated|Could not establish connection|ไม่ได้รับคำตอบจาก Extension|cdp_timeout/i.test(String(err?.message || ''))
          );
          if (!isTransient || attempt > maxRetriesPerStage) {
            throw err;
          }
          log(`🔄 [${stageName}] ลองซ้ำครั้งที่ ${attempt}/${maxRetriesPerStage} เนื่องจาก: ${err.message}`, 'warn');
          await new Promise((r) => setTimeout(r, retryDelayMs));
        }
      }
    }

    // Best effort: ask the embedder what the page looked like (it redacts and stores it). Never throws, never blocks a run.
    async function collectEvidence(clip, info) {
      if (typeof actions.captureEvidence !== 'function') return;
      try { await actions.captureEvidence(clip, info); }
      catch (evidenceErr) { log(`⚠️ เก็บหลักฐานหน้าเว็บไม่สำเร็จ (${evidenceErr?.message || evidenceErr})`, 'warn'); }
    }

    async function safeResetUploadPage() {
      try { await actions.resetUploadPage(); }
      catch (resetErr) { log(`⚠️ รีเซ็ตหน้าอัปโหลดไม่สำเร็จ (${resetErr?.message || resetErr}) — ถ้าคลิปถัดไปล้ม ให้ตรวจแท็บ TikTok Studio`, 'warn'); }
    }

    async function sleepJitter(seconds) {
      remainingCooldown = Math.round(seconds * 10) / 10;
      const step = 0.5;
      while (remainingCooldown > 0) {
        await checkControlGate();
        onCooldownTick(Math.ceil(remainingCooldown), getStats());
        const waitMs = Math.min(step, remainingCooldown) * 1000;
        if (waitMs > 0) {
          await new Promise((r) => setTimeout(r, waitMs));
        }
        remainingCooldown = Math.max(0, Math.round((remainingCooldown - step) * 10) / 10);
      }
      remainingCooldown = 0;
      onCooldownTick(0, getStats());
    }

    function resolveTargetMode(clip) {
      if (clip?.force_mode === 'draft' || mode === 'draft_only') return 'draft';
      if (clip?.force_mode === 'schedule' || mode === 'schedule_only') return 'schedule';
      if (scheduleUsed < maxScheduleQuota) return 'schedule';
      return 'draft';
    }

    async function executeSingleClipStages(clip, index) {
      const total = batchClips.length;
      const clipTitle = `${clip.episode_no ? `EP${clip.episode_no} · ` : ''}${clip.hook_title || clip.title || clip.name || `คลิปที่ ${index + 1}`}`;
      const targetMode = resolveTargetMode(clip);

      log(`▶️ คลิปที่ ${index + 1}/${total}: "${clipTitle}" (โหมด: ${targetMode === 'schedule' ? 'ตั้งเวลา' : 'แบบร่าง'})`);

      // Prepare clip job with backend if prepareClip is provided
      if (actions.prepareClip) {
        await checkControlGate();
        stage = 'PREPARE_JOB';
        await runWithRetry('PREPARE_JOB', () => actions.prepareClip(clip, targetMode));
      }

      // 1. INJECT_FILE
      setStage(CLIP_STAGES.INJECT_FILE);
      await checkControlGate();
      log(`[${index + 1}/${total}] 1/10 INJECT_FILE: ส่งไฟล์วิดีโอเข้า Input จริง...`);
      const injectFn = actions.injectFile || actions.uploadVideo;
      if (injectFn) {
        await runWithRetry(CLIP_STAGES.INJECT_FILE, () => injectFn(clip));
      }

      // 2. AWAIT_PROCESSING
      setStage(CLIP_STAGES.AWAIT_PROCESSING);
      await checkControlGate();
      log(`[${index + 1}/${total}] 2/10 AWAIT_PROCESSING: รออัปโหลดและประมวลผลวิดีโอครบ 100%...`);
      if (actions.awaitProcessing) {
        await runWithRetry(CLIP_STAGES.AWAIT_PROCESSING, () => actions.awaitProcessing(clip));
      }

      // 3. FILL_METADATA
      setStage(CLIP_STAGES.FILL_METADATA);
      await checkControlGate();
      log(`[${index + 1}/${total}] 3/10 FILL_METADATA: กรอก Caption, Title, Hashtag และตะกร้าสินค้า...`);
      const fillFn = actions.fillMetadata || actions.fillDetails;
      if (fillFn) {
        await runWithRetry(CLIP_STAGES.FILL_METADATA, () => fillFn(clip, targetMode));
      }

      // 4. HANDLE_COVER
      setStage(CLIP_STAGES.HANDLE_COVER);
      await checkControlGate();
      if (clip.cover_path !== false && actions.handleCover) {
        log(`[${index + 1}/${total}] 4/10 HANDLE_COVER: อัปโหลดภาพปก 3:4...`);
        await runWithRetry(CLIP_STAGES.HANDLE_COVER, () => actions.handleCover(clip));
      } else {
        log(`[${index + 1}/${total}] 4/10 HANDLE_COVER: ปกถูกจัดการในขั้นกรอกรายละเอียดแล้ว (ถ้าหน้า TikTok ไม่มีช่องอัปโหลดปก ใช้ปกอัตโนมัติของ TikTok)`);
      }

      // 5. DISMISS_INTERRUPTS
      setStage(CLIP_STAGES.DISMISS_INTERRUPTS);
      await checkControlGate();
      log(actions.dismissInterrupts
        ? `[${index + 1}/${total}] 5/10 DISMISS_INTERRUPTS: ตรวจจับและกดปิด Modal ขัดจังหวะอัตโนมัติ...`
        : `[${index + 1}/${total}] 5/10 DISMISS_INTERRUPTS: ข้าม (ไม่มีขั้นนี้ในแผง — ตรวจ modal ตอนกดโพสต์)`);
      if (actions.dismissInterrupts) {
        await runWithRetry(CLIP_STAGES.DISMISS_INTERRUPTS, () => actions.dismissInterrupts(clip));
      }

      // 6. APPLY_SCHEDULE_OR_DRAFT
      setStage(CLIP_STAGES.APPLY_SCHEDULE_OR_DRAFT);
      await checkControlGate();
      log(actions.applyScheduleOrDraft
        ? `[${index + 1}/${total}] 6/10 APPLY_SCHEDULE_OR_DRAFT: ตั้งค่าโหมด ${targetMode === 'schedule' ? 'ตั้งเวลาโพสต์' : 'บันทึกแบบร่าง'}...`
        : `[${index + 1}/${total}] 6/10 APPLY_SCHEDULE_OR_DRAFT: ข้าม (ตั้งค่าไว้แล้วในขั้นกรอกรายละเอียด)`);
      if (actions.applyScheduleOrDraft) {
        await runWithRetry(CLIP_STAGES.APPLY_SCHEDULE_OR_DRAFT, () => actions.applyScheduleOrDraft(clip, targetMode));
      }

      // 7-9. SUBMIT / VERIFY / UPDATE. From the moment the submit action starts, a click may already have happened:
      //  - the submit stage is never retried (a second click could post twice),
      //  - Stop/Pause cannot interrupt the verify/update stages (a live post must always be recorded),
      //  - an error after a possible click is "unknown + reconcile", never "failed".
      setStage(CLIP_STAGES.TRIGGER_SUBMIT);
      await checkControlGate();
      log(`[${index + 1}/${total}] 7/10 TRIGGER_SUBMIT: คลิกปุ่มส่งเมื่อพ้นสถานะ disabled...`);
      const submitFn = actions.triggerSubmit || actions.submitPost;
      let submitResult = { success: true };
      let toastResult = submitResult;
      let finalOutcome;
      let submitStarted = false;
      try {
        if (submitFn) {
          submitStarted = true;
          submitResult = (await submitFn(clip, targetMode)) || { success: true };
        }
        inCriticalSection = true;

        // Secondary interrupt check right after submit (e.g. Copyright "Post now" modal)
        if (actions.dismissInterrupts) {
          try { await actions.dismissInterrupts(clip, { postSubmit: true }); }
          catch (dismissErr) { log(`⚠️ ปิดป๊อปอัปหลังกดโพสต์ไม่สำเร็จ (${dismissErr.message})`, 'warn'); }
        }

        // 8. VERIFY_SUCCESS_TOAST
        setStage(CLIP_STAGES.VERIFY_SUCCESS_TOAST);
        log(`[${index + 1}/${total}] 8/10 VERIFY_SUCCESS_TOAST: รอยืนยัน Toast ความสำเร็จ...`);
        toastResult = submitResult;
        if (actions.verifySuccessToast) {
          toastResult = (await runWithRetry(CLIP_STAGES.VERIFY_SUCCESS_TOAST, () => actions.verifySuccessToast(clip, targetMode, submitResult), { gate: false })) || submitResult;
        } else {
          log(`[${index + 1}/${total}] 8/10 ข้าม: ไม่มีขั้นตรวจซ้ำ`, 'warn');
        }

        finalOutcome = toastResult?.outcome || submitResult?.outcome || (targetMode === 'draft' ? 'draft_saved' : 'scheduled');

        // 9. UPDATE_BACKEND
        setStage(CLIP_STAGES.UPDATE_BACKEND);
        log(`[${index + 1}/${total}] 9/10 UPDATE_BACKEND: อัปเดตสถานะ "${finalOutcome}" กลับไปยัง FastAPI Backend...`);
        const updateFn = actions.updateBackend || actions.reconcile;
        if (updateFn) {
          await runWithRetry(CLIP_STAGES.UPDATE_BACKEND, () => updateFn(clip, finalOutcome, toastResult), { gate: false });
        }
      } catch (postErr) {
        // BATCH_ABORTED cannot come from here (the gates are off after the click); anything else is classified now.
        if (!submitStarted || postErr?.postAttempted === false) throw postErr;   // provably before the click: a plain failure
        finalOutcome = 'confirmation_unknown';
        toastResult = { outcome: finalOutcome, error: postErr?.message || String(postErr), postSubmitError: true };
        log(`⚠️ [${index + 1}/${total}] ผิดพลาดหลังเริ่มกดโพสต์ (${postErr?.message || postErr}) — ถือว่า "ยืนยันผลไม่ได้" ไม่นับเป็นล้ม และจะไม่ลองกดซ้ำ`, 'warn');
        await collectEvidence(clip, { kind: 'unknown', stage, error: postErr?.message || String(postErr) });
        const recordFn = actions.updateBackend || actions.reconcile;
        if (recordFn) {
          try { await recordFn(clip, finalOutcome, toastResult); }
          catch (recordErr) { log(`⚠️ บันทึกสถานะ "ยืนยันไม่ได้" ไม่สำเร็จ (${recordErr.message}) — ตรวจที่ TikTok Studio ก่อนรันต่อ`, 'error'); }
        }
      } finally {
        inCriticalSection = false;
      }

      if (targetMode === 'schedule') {
        scheduleUsed += 1;
      } else {
        draftUsed += 1;
      }
      consecutiveFailures = 0;
      if (finalOutcome === 'confirmation_unknown') {
        // The post may or may not be live: never count it as a success, never retry it.
        unknown += 1;
        consecutiveUnknown += 1;
        results.push({ clipId: clip.id, clipTitle, mode: targetMode, outcome: finalOutcome, success: false, unknown: true });
        log(`⚠️ [${index + 1}/${total}] ยืนยันผลไม่ได้: "${clipTitle}" — ตรวจที่ TikTok Studio > Content ก่อนส่งซ้ำ`, 'warn');
      } else {
        consecutiveUnknown = 0;
        successful += 1;
        results.push({ clipId: clip.id, clipTitle, mode: targetMode, outcome: finalOutcome, success: true });
        log(`✅ [${index + 1}/${total}] สำเร็จ: "${clipTitle}" (${finalOutcome})`, 'success');
      }

      // 10. CALCULATED_JITTER
      if (index + 1 < total) {
        if (actions.resetUploadPage) {
          await safeResetUploadPage();
        }
        setStage(CLIP_STAGES.CALCULATED_JITTER);
        const jitterSec = calculateHumanJitter(cooldownSeconds, minJitter, maxJitter, rng);
        if (jitterSec > 0) {
          log(`⏳ [${index + 1}/${total}] 10/10 CALCULATED_JITTER: พักเครื่อง ${jitterSec} วินาทีก่อนเริ่มคลิปถัดไป...`);
          await sleepJitter(jitterSec);
        }
      }
    }

    async function start() {
      if (state !== ORCHESTRATOR_STATES.IDLE && state !== ORCHESTRATOR_STATES.PAUSED) {
        return getStats();
      }

      isAborted = false;
      isPaused = false;

      const missing = requiredActions.filter((name) => !String(name).split('|').some((alias) => typeof actions[alias] === 'function'));
      if (missing.length) {
        log(`⛔ ขาดขั้นตอนที่จำเป็น (${missing.join(', ')}) จึงไม่เริ่มรัน เพื่อไม่ให้ขั้นที่หายถูกนับว่าสำเร็จ`, 'error');
        haltReason = `ขาดขั้นตอน ${missing.join(', ')}`;
        setState(ORCHESTRATOR_STATES.ERROR);
        return getStats();
      }

      try {
        // Phase A: CHECK_QUOTA
        setState(ORCHESTRATOR_STATES.CHECK_QUOTA);
        await checkControlGate();
        log('🔍 กำลังตรวจสอบโควตา TikTok Studio ล่าสุด (CHECK_QUOTA)...');

        let allowedCap = maxBatchCap;
        if (actions.checkQuota) {
          try {
            quotaInfo = await runWithRetry('CHECK_QUOTA', () => actions.checkQuota());
          } catch (quotaErr) {
            if (quotaErr?.code === 'BATCH_ABORTED' || quotaErr?.message === 'BATCH_ABORTED') throw quotaErr;
            log(`⚠️ ตรวจสอบโควตาสดไม่สำเร็จ (${quotaErr.message}) — ใช้โควตาเริ่มต้นแทน`, 'warn');
            quotaInfo = null;
          }
          if (quotaInfo) {
            if (typeof quotaInfo.scheduledCount === 'number') {
              scheduleUsed = quotaInfo.scheduledCount;
            }
            if (typeof quotaInfo.draftCount === 'number') {
              draftUsed = quotaInfo.draftCount;
            }
            const remSched = Math.max(0, maxScheduleQuota - scheduleUsed);
            const remDraft = Math.max(0, maxDraftQuota - draftUsed);

            if (mode === 'schedule_only' && remSched <= 0) {
              log('⛔ โควตาตั้งเวลา (Schedule) เต็ม 30/30 คลิปแล้ว หยุดการทำงานเพื่อความปลอดภัย', 'error');
              setState(ORCHESTRATOR_STATES.COMPLETED);
              return getStats();
            }
            if (mode === 'draft_only' && remDraft <= 0) {
              log('⛔ โควตาแบบร่าง (Draft) เต็ม 30/30 คลิปแล้ว หยุดการทำงาน', 'error');
              setState(ORCHESTRATOR_STATES.COMPLETED);
              return getStats();
            }
            if (quotaInfo.isQuotaFull || (remSched <= 0 && remDraft <= 0)) {
              log('⛔ โควตา TikTok Studio เต็มทั้งหมดแล้ว ไม่สามารถอัปโหลดเพิ่มได้', 'error');
              setState(ORCHESTRATOR_STATES.COMPLETED);
              return getStats();
            }
            if (typeof quotaInfo.recommendedBatchLimit === 'number' && mode === 'schedule_only') {
              allowedCap = Math.min(maxBatchCap, quotaInfo.recommendedBatchLimit);
            }
          }
        }

        // Phase B: FETCH_BATCH
        setState(ORCHESTRATOR_STATES.FETCH_BATCH);
        await checkControlGate();
        log('📥 กำลังดึงรายการคิวคลิปสำหรับอัปโหลด (FETCH_BATCH)...');
        if (actions.fetchBatch) {
          const fetched = await runWithRetry('FETCH_BATCH', () => actions.fetchBatch({ limit: allowedCap, mode }));
          if (Array.isArray(fetched)) {
            batchClips = fetched;
          }
        }

        if (batchClips.length > allowedCap) {
          log(`🛡️ จำกัดจำนวนคลิปในรอบนี้ไว้ที่ ${allowedCap} คลิปตามโควตาปลอดภัย (จากทั้งหมด ${batchClips.length} คลิป)`, 'warn');
          batchClips = batchClips.slice(0, allowedCap);
        }

        if (batchClips.length === 0) {
          log('ℹ️ ไม่มีคลิปที่รออัปโหลดในคิว', 'warn');
          setState(ORCHESTRATOR_STATES.COMPLETED);
          return getStats();
        }

        // Phase C: LOOP_CYCLE
        setState(ORCHESTRATOR_STATES.LOOP_CYCLE);
        log(`🚀 เริ่มลูปอัปโหลดอัตโนมัติ (LOOP_CYCLE): รวม ${batchClips.length} คลิป`);

        const clipAttempts = {};
        while (currentIndex < batchClips.length && !isAborted) {
          const clip = batchClips[currentIndex];
          // The side panel has no "save as draft" step: its submit step presses Post, which with no schedule
          // set publishes LIVE. So a draft target (Draft Only, or Smart once the schedule quota is full) must
          // stop the batch instead of posting by accident, unless the embedder really saves drafts (the panel does).
          if (!allowDraft && resolveTargetMode(clip) === 'draft') {
            haltReason = 'โควตาตั้งเวลาเต็ม (หรือเลือกโหมดแบบร่าง) แต่แผงยังไม่รองรับการบันทึกแบบร่าง';
            log(`⛔ ${haltReason} จึงหยุดเพื่อกันโพสต์สดโดยไม่ตั้งใจ`, 'error');
            break;
          }
          if (clip.force_mode === 'schedule' && resolveTargetMode(clip) === 'schedule' && scheduleUsed >= maxScheduleQuota) {
            // e.g. publishing a draft: it needs one of the schedule slots like any scheduled post
            haltReason = `ช่องตั้งเวลาเต็ม ${maxScheduleQuota}/${maxScheduleQuota} (การเผยแพร่แบบร่างแบบตั้งเวลาก็ใช้ช่องนี้ — ใช้ "โพสต์ตอนนี้" หรือรอให้มีช่องว่าง)`;
            log(`⛔ ${haltReason}`, 'error');
            break;
          }
          if (resolveTargetMode(clip) === 'draft' && draftUsed >= maxDraftQuota) {
            haltReason = `โควตาแบบร่างเต็ม ${maxDraftQuota}/${maxDraftQuota}`;
            log(`⛔ ${haltReason} หยุดการทำงาน (ลบแบบร่างเก่าบน TikTok ก่อนจึงจะบันทึกเพิ่มได้)`, 'error');
            break;
          }
          try {
            await executeSingleClipStages(clip, currentIndex);
            if (consecutiveUnknown >= maxConsecutiveUnknown) {
              circuitReason = `ยืนยันผลไม่ได้ติดกัน ${consecutiveUnknown} คลิป`;
              break;
            }
          } catch (err) {
            if (err?.code === 'BATCH_ABORTED' || err?.message === 'BATCH_ABORTED' || err?.message === 'BATCH_STOPPED') {
              break;
            }
            // One more try from a clean page when the hiccup happened BEFORE the post click.
            // Never after it: the post may already be live, and the backend job is parked, not retried.
            clipAttempts[currentIndex] = (clipAttempts[currentIndex] || 0) + 1;
            if (clipAttempts[currentIndex] < maxClipAttempts && !isAborted && (!POST_SUBMIT_STAGES.has(stage) || err?.postAttempted === false)) {
              log(`🔁 พลาดที่ขั้น ${stage} ก่อนกดโพสต์ (${err.message}) — ลองคลิปนี้ใหม่จากหน้าสะอาด (${clipAttempts[currentIndex] + 1}/${maxClipAttempts})`, 'warn');
              if (actions.resetUploadPage) {
                await safeResetUploadPage();
              }
              continue;
            }
            failed += 1;
            await collectEvidence(clip, { kind: 'failed', stage, error: err.message || String(err) });
            const clipTitle = `${clip?.episode_no ? `EP${clip.episode_no} · ` : ''}${clip?.hook_title || clip?.title || clip?.name || `คลิปที่ ${currentIndex + 1}`}`;
            errors.push({
              clipId: clip?.id,
              clipTitle,
              index: currentIndex,
              stage,
              error: err.message || String(err),
            });
            results.push({ clipId: clip?.id, clipTitle, stage, error: err.message || String(err), success: false });
            log(`❌ [${currentIndex + 1}/${batchClips.length}] คลิป "${clipTitle}" ล้มเหลวที่ขั้น ${stage}: ${err.message}`, 'error');

            if (!autoSkipOnError) {
              setStage( null );
              setState(ORCHESTRATOR_STATES.ERROR);
              throw err;
            }

            consecutiveFailures += 1;
            consecutiveUnknown = 0;
            if (consecutiveFailures >= maxConsecutiveFailures) {
              circuitReason = `ล้มเหลวติดกัน ${consecutiveFailures} คลิป`;
              break;
            }
            log(`⏭️ ข้ามไปทำคลิปถัดไปอัตโนมัติ (Resilient Auto-Skip)...`, 'warn');
            if (actions.resetUploadPage) {
              await safeResetUploadPage();
            }
          }
          currentIndex += 1;
        }

        stage = null;
        const left = Math.max(0, batchClips.length - (successful + failed + unknown));
        const tally = `สำเร็จ ${successful}, ล้มเหลว ${failed}, ยืนยันไม่ได้ ${unknown}, ยังไม่ได้ทำ ${left}`;
        if (circuitReason) {
          setState(ORCHESTRATOR_STATES.ERROR);
          log(`🛑 หยุดอัตโนมัติ: ${circuitReason} (${tally}) — ตรวจสาเหตุก่อนรันต่อ`, 'error');
        } else if (isAborted) {
          setState(ORCHESTRATOR_STATES.ABORTED);
          log(`⏹️ หยุดลูปการอัปโหลดแล้ว (${tally})`, 'warn');
        } else if (haltReason) {
          setState(ORCHESTRATOR_STATES.COMPLETED);
          log(`⛔ จบรอบก่อนครบ: ${haltReason} (${tally})`, 'error');
        } else {
          setState(ORCHESTRATOR_STATES.COMPLETED);
          const clean = failed === 0 && unknown === 0;
          log(`${clean ? '🎉 อัปโหลดครบชุดเสร็จสมบูรณ์' : '⚠️ จบรอบแต่มีคลิปที่ไม่สำเร็จ'}: ${tally}`, clean ? 'success' : 'warn');
        }
      } catch (fatalErr) {
        stage = null;
        if (fatalErr?.code === 'BATCH_ABORTED' || fatalErr?.message === 'BATCH_ABORTED' || fatalErr?.message === 'BATCH_STOPPED') {
          setState(ORCHESTRATOR_STATES.ABORTED);
        } else {
          setState(ORCHESTRATOR_STATES.ERROR);
          log(`💥 ระบบลูปหยุดทำงานเนื่องจากข้อผิดพลาดร้ายแรง: ${fatalErr.message}`, 'error');
        }
      }

      return getStats();
    }

    function pause() {
      if (
        state === ORCHESTRATOR_STATES.COMPLETED ||
        state === ORCHESTRATOR_STATES.ABORTED ||
        state === ORCHESTRATOR_STATES.STOPPED
      ) {
        return;
      }
      isPaused = true;
      setState(ORCHESTRATOR_STATES.PAUSED);
    }

    function resume() {
      if (!isPaused) return;
      isPaused = false;
      if (pauseResolver) {
        const resolve = pauseResolver;
        pauseResolver = null;
        resolve();
      }
    }

    function abort() {
      isAborted = true;
      if (inCriticalSection) log('⏹️ รับคำสั่งหยุดแล้ว — รอตรวจผลโพสต์ของคลิปนี้ให้จบก่อน จึงจะหยุด', 'warn');
      isPaused = false;
      if (actions.notifySignal) {
        try { actions.notifySignal('ABORT'); } catch (_) {}
      }
      if (pauseResolver) {
        const resolve = pauseResolver;
        pauseResolver = null;
        resolve();
      }
      setState(ORCHESTRATOR_STATES.ABORTED);
    }

    // Alias stop() -> abort() for backward compatibility with batch_runner.js
    function stop() {
      abort();
    }

    return {
      start,
      pause,
      resume,
      abort,
      stop,
      getState: () => state,
      getStage: () => stage,
      getStats,
    };
  }

  // The orchestrator hands reconcile the outcome as a string plus the raw
  // submit/toast result; accept either shape so an unconfirmed post is never
  // silently treated as done.
  function shouldReconcileAfterPost(outcome, result) {
    const outcomeName = typeof outcome === 'string' ? outcome : outcome?.outcome;
    const raw = (outcome && typeof outcome === 'object') ? outcome : result;
    return outcomeName === 'confirmation_unknown'
      || raw?.outcome === 'confirmation_unknown'
      || Boolean(raw?.markError);
  }

  // One honest line (and colour) for the end of a run, from the orchestrator's final stats.
  function finalVerdict(summary) {
    const { successful, failed, unknown, total, finalKind, haltReason, circuitReason } = summary;
    const tally = `สำเร็จ ${successful}/${total}, ล้มเหลว ${failed}, ยืนยันไม่ได้ ${unknown}`;
    switch (finalKind) {
      case 'success': return { kind: 'success', text: `อัปโหลดแบบกลุ่มเสร็จสิ้น! ${tally}` };
      case 'unknown': return { kind: 'warn', text: `จบรอบ แต่มีคลิปที่ยืนยันผลไม่ได้ — ตรวจที่ TikTok Studio > Content ก่อนส่งซ้ำ (${tally})` };
      case 'partial': return { kind: 'warn', text: `จบรอบ แต่มีคลิปล้มเหลว (${tally})` };
      case 'halted': return { kind: 'error', text: `จบรอบก่อนครบ: ${haltReason || 'ไม่ทราบสาเหตุ'} (${tally})` };
      case 'aborted': return { kind: 'warn', text: `หยุดรอบตามคำสั่ง (${tally})` };
      case 'error': return { kind: 'error', text: `หยุดอัตโนมัติ: ${circuitReason || haltReason || 'เกิดข้อผิดพลาด'} (${tally})` };
      case 'empty': return { kind: 'warn', text: 'ไม่มีคลิปที่รออัปโหลด' };
      default: return { kind: 'warn', text: `รอบสิ้นสุดในสถานะไม่คาดคิด (${finalKind || 'unknown'}) — ${tally}` };
    }
  }

  return {
    finalVerdict,
    shouldReconcileAfterPost,
    ORCHESTRATOR_STATES,
    BATCH_STATES: ORCHESTRATOR_STATES,
    CLIP_STAGES,
    STAGE_LABELS_TH,
    calculateHumanJitter,
    createBatchOrchestrator,
    createBatchRunner: createBatchOrchestrator,
  };
});
