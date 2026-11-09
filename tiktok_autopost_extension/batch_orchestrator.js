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
      maxBatchCap = 30,
      maxScheduleQuota = 30,
      maxDraftQuota = 30,
      currentScheduleCount = 0,
      currentDraftCount = 0,
      cooldownSeconds = 22,
      minJitter = -3,
      maxJitter = 6,
      autoSkipOnError = true,
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
        return `เสร็จสิ้น ${successful}/${total} คลิป [100%] - อัปโหลดครบชุดเรียบร้อย`;
      }
      if (state === ORCHESTRATOR_STATES.ABORTED || state === ORCHESTRATOR_STATES.STOPPED) {
        return `หยุดที่คลิป ${clipNum}/${total} [${pct}%] - ผู้ใช้สั่งหยุดลูป`;
      }
      if (total > 0) {
        return `คลิปที่ ${clipNum}/${total} [${pct}%] - ${label}`;
      }
      return label;
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

    async function runWithRetry(stageName, fn) {
      let attempt = 0;
      while (true) {
        await checkControlGate();
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
      const clipTitle = clip.hook_title || clip.title || clip.name || `คลิปที่ ${index + 1}`;
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
      log(`[${index + 1}/${total}] 5/10 DISMISS_INTERRUPTS: ตรวจจับและกดปิด Modal ขัดจังหวะอัตโนมัติ...`);
      if (actions.dismissInterrupts) {
        await runWithRetry(CLIP_STAGES.DISMISS_INTERRUPTS, () => actions.dismissInterrupts(clip));
      }

      // 6. APPLY_SCHEDULE_OR_DRAFT
      setStage(CLIP_STAGES.APPLY_SCHEDULE_OR_DRAFT);
      await checkControlGate();
      log(`[${index + 1}/${total}] 6/10 APPLY_SCHEDULE_OR_DRAFT: ตั้งค่าโหมด ${targetMode === 'schedule' ? 'ตั้งเวลาโพสต์' : 'บันทึกแบบร่าง'}...`);
      if (actions.applyScheduleOrDraft) {
        await runWithRetry(CLIP_STAGES.APPLY_SCHEDULE_OR_DRAFT, () => actions.applyScheduleOrDraft(clip, targetMode));
      }

      // 7. TRIGGER_SUBMIT
      setStage(CLIP_STAGES.TRIGGER_SUBMIT);
      await checkControlGate();
      log(`[${index + 1}/${total}] 7/10 TRIGGER_SUBMIT: คลิกปุ่มส่งเมื่อพ้นสถานะ disabled...`);
      const submitFn = actions.triggerSubmit || actions.submitPost;
      let submitResult = { success: true };
      if (submitFn) {
        submitResult = (await runWithRetry(CLIP_STAGES.TRIGGER_SUBMIT, () => submitFn(clip, targetMode))) || { success: true };
      }

      // Secondary interrupt check right after submit (e.g. Copyright "Post now" modal)
      if (actions.dismissInterrupts) {
        try { await actions.dismissInterrupts(clip, { postSubmit: true }); } catch (_) {}
      }

      // 8. VERIFY_SUCCESS_TOAST
      setStage(CLIP_STAGES.VERIFY_SUCCESS_TOAST);
      await checkControlGate();
      log(`[${index + 1}/${total}] 8/10 VERIFY_SUCCESS_TOAST: รอยืนยัน Toast ความสำเร็จ...`);
      let toastResult = submitResult;
      if (actions.verifySuccessToast) {
        toastResult = (await runWithRetry(CLIP_STAGES.VERIFY_SUCCESS_TOAST, () => actions.verifySuccessToast(clip, targetMode, submitResult))) || submitResult;
      }

      const finalOutcome = toastResult?.outcome || submitResult?.outcome || (targetMode === 'draft' ? 'draft_saved' : 'scheduled');

      // 9. UPDATE_BACKEND
      setStage(CLIP_STAGES.UPDATE_BACKEND);
      await checkControlGate();
      log(`[${index + 1}/${total}] 9/10 UPDATE_BACKEND: อัปเดตสถานะ "${finalOutcome}" กลับไปยัง FastAPI Backend...`);
      const updateFn = actions.updateBackend || actions.reconcile;
      if (updateFn) {
        await runWithRetry(CLIP_STAGES.UPDATE_BACKEND, () => updateFn(clip, finalOutcome, toastResult));
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
          try { await actions.resetUploadPage(); } catch (_) {}
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
            if (clipAttempts[currentIndex] < maxClipAttempts && !isAborted && !POST_SUBMIT_STAGES.has(stage)) {
              log(`🔁 พลาดที่ขั้น ${stage} ก่อนกดโพสต์ (${err.message}) — ลองคลิปนี้ใหม่จากหน้าสะอาด (${clipAttempts[currentIndex] + 1}/${maxClipAttempts})`, 'warn');
              if (actions.resetUploadPage) {
                try { await actions.resetUploadPage(); } catch (_) {}
              }
              continue;
            }
            failed += 1;
            const clipTitle = clip?.hook_title || clip?.title || clip?.name || `คลิปที่ ${currentIndex + 1}`;
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
              try { await actions.resetUploadPage(); } catch (_) {}
            }
          }
          currentIndex += 1;
        }

        stage = null;
        if (circuitReason) {
          setState(ORCHESTRATOR_STATES.ERROR);
          log(`🛑 หยุดอัตโนมัติ: ${circuitReason} (สำเร็จ ${successful}, ล้มเหลว ${failed}, ยืนยันไม่ได้ ${unknown}) — ตรวจสาเหตุก่อนรันต่อ`, 'error');
        } else if (isAborted) {
          setState(ORCHESTRATOR_STATES.ABORTED);
          log(`⏹️ หยุดลูปการอัปโหลดแล้ว (สำเร็จ ${successful}/${batchClips.length} คลิป)`, 'warn');
        } else {
          setState(ORCHESTRATOR_STATES.COMPLETED);
          log(`🎉 อัปโหลดครบชุดเสร็จสมบูรณ์! สำเร็จ: ${successful}/${batchClips.length} คลิป (ข้าม/ล้มเหลว: ${failed})`, 'success');
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

  return {
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
