/**
 * Batch Runner State Machine for OmniCut TikTok Post Helper
 * Controls sequential multi-clip automated publishing lifecycle with
 * keep-alive heartbeat, dynamic quota tracking, and error-resilient skip.
 */

const BATCH_STATES = {
  IDLE: 'IDLE',
  PREPARING_CLIP: 'PREPARING_CLIP',
  UPLOADING_VIDEO: 'UPLOADING_VIDEO',
  WAITING_UPLOAD: 'WAITING_UPLOAD',
  FILLING_METADATA: 'FILLING_METADATA',
  UPLOADING_COVER: 'UPLOADING_COVER',
  SUBMITTING_POST: 'SUBMITTING_POST',
  RECONCILING: 'RECONCILING',
  COOLDOWN: 'COOLDOWN',
  PAUSED: 'PAUSED',
  STOPPED: 'STOPPED',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
};

function createBatchRunner({
  clips = [],
  options = {},
  actions = {},
  onStateChange = () => {},
  onLog = () => {},
  onCooldownTick = () => {},
}) {
  const {
    mode = 'smart', // 'smart', 'schedule_only', 'draft_only'
    cooldownSeconds = 25,
    maxScheduleQuota = 30,
    currentScheduleCount = 0,
    autoSkipOnError = true,
  } = options;

  let state = BATCH_STATES.IDLE;
  let currentIndex = 0;
  let successful = 0;
  let failed = 0;
  let scheduleCount = currentScheduleCount;
  const errors = [];
  let isPaused = false;
  let isStopped = false;
  let pauseResolver = null;
  let cooldownTimer = null;
  let remainingCooldown = 0;

  function setState(newState) {
    state = newState;
    onStateChange(state, getStats());
  }

  function getStats() {
    const total = clips.length;
    const remainingClips = Math.max(0, total - currentIndex);
    // Estimated average ~45s per clip + cooldown
    const estSecPerClip = 45 + (cooldownSeconds || 0);
    const etaSeconds = remainingClips * estSecPerClip;

    return {
      state,
      total,
      currentIndex,
      processed: successful + failed,
      successful,
      failed,
      remainingClips,
      activeClip: clips[currentIndex] || null,
      remainingCooldown,
      etaSeconds,
      isPaused,
      isStopped,
    };
  }

  function log(msg, kind = 'info') {
    onLog(msg, kind, getStats());
  }

  async function checkPause() {
    if (isStopped) throw new Error('BATCH_STOPPED');
    if (isPaused) {
      setState(BATCH_STATES.PAUSED);
      log('⏸️ พักการทำงานชั่วคราว (Paused)...', 'warn');
      await new Promise((resolve) => {
        pauseResolver = resolve;
      });
      if (isStopped) throw new Error('BATCH_STOPPED');
    }
  }

  async function sleepWithInterrupt(seconds) {
    remainingCooldown = Math.round(seconds);
    const step = 0.5;
    while (remainingCooldown > 0) {
      if (isStopped) throw new Error('BATCH_STOPPED');
      await checkPause();
      onCooldownTick(remainingCooldown);
      await new Promise((r) => setTimeout(r, step * 1000));
      remainingCooldown = Math.max(0, remainingCooldown - step);
    }
    remainingCooldown = 0;
    onCooldownTick(0);
  }

  function determineClipMode(clip) {
    if (mode === 'draft_only') return 'draft';
    if (mode === 'schedule_only') return 'schedule';
    // 'smart' mode: up to maxScheduleQuota is schedule, rest is draft
    if (scheduleCount < maxScheduleQuota) {
      return 'schedule';
    }
    return 'draft';
  }

  async function runSingleClipCycle(clip, index) {
    await checkPause();
    const clipTitle = clip.hook_title || clip.name || `คลิปที่ ${index + 1}`;
    const targetMode = determineClipMode(clip);

    log(`▶️ [${index + 1}/${clips.length}] เริ่มต้นคลิป "${clipTitle}" (โหมด: ${targetMode === 'schedule' ? 'ตั้งเวลา' : 'แบบร่าง'})...`);

    // 1. Prepare with Backend
    setState(BATCH_STATES.PREPARING_CLIP);
    await checkPause();
    log(`[${index + 1}/${clips.length}] ดึงข้อมูลและสร้าง Job...`);
    if (actions.prepareClip) {
      await actions.prepareClip(clip);
    }

    // 2. Upload Video file
    setState(BATCH_STATES.UPLOADING_VIDEO);
    await checkPause();
    log(`[${index + 1}/${clips.length}] กำลังอัปโหลดไฟล์วิดีโอเข้า TikTok Studio...`);
    if (actions.uploadVideo) {
      await actions.uploadVideo(clip);
    }

    // 3. Fill Metadata (Caption, Product Basket, Schedule/Draft, Cover)
    setState(BATCH_STATES.FILLING_METADATA);
    await checkPause();
    log(`[${index + 1}/${clips.length}] กำลังกรอกแคปชัน ปักตะกร้า และแนบปก...`);
    if (actions.fillDetails) {
      await actions.fillDetails(clip, targetMode);
    }

    // 4. Submit Post
    setState(BATCH_STATES.SUBMITTING_POST);
    await checkPause();
    log(`[${index + 1}/${clips.length}] กำลังกด Submit / ยืนยันโพสต์...`);
    let postResult = { success: true };
    if (actions.submitPost) {
      postResult = await actions.submitPost(clip, targetMode);
    }

    // 5. Reconcile with OmniCut
    setState(BATCH_STATES.RECONCILING);
    log(`[${index + 1}/${clips.length}] ซิงค์ผลการโพสต์กลับสู่ฐานข้อมูล OmniCut...`);
    if (actions.reconcile) {
      await actions.reconcile(clip, postResult.outcome || (targetMode === 'draft' ? 'draft_saved' : 'scheduled_on_platform'));
    }

    if (targetMode === 'schedule') {
      scheduleCount += 1;
    }
    successful += 1;
    log(`✅ [${index + 1}/${clips.length}] คลิป "${clipTitle}" สำเร็จเรียบร้อย!`, 'success');

    // 6. Reset Upload Page for Next Clip
    if (index + 1 < clips.length) {
      if (actions.resetUploadPage) {
        await actions.resetUploadPage();
      }

      // 7. Cooldown jitter
      setState(BATCH_STATES.COOLDOWN);
      const jitter = (Math.random() * 4 - 2); // ±2s
      const actualCooldown = Math.max(1, cooldownSeconds + jitter);
      log(`⏳ พักเครื่อง ${Math.round(actualCooldown)} วินาทีก่อนเริ่มคลิปถัดไป (กัน TikTok Rate Limit)...`);
      await sleepWithInterrupt(actualCooldown);
    }
  }

  async function start() {
    if (state !== BATCH_STATES.IDLE && state !== BATCH_STATES.PAUSED) {
      return getStats();
    }

    isStopped = false;
    isPaused = false;
    log(`🚀 เริ่มต้น Batch Auto-Post: รวม ${clips.length} คลิป`);

    try {
      while (currentIndex < clips.length && !isStopped) {
        const clip = clips[currentIndex];
        try {
          await runSingleClipCycle(clip, currentIndex);
        } catch (err) {
          if (err.message === 'BATCH_STOPPED') break;
          failed += 1;
          errors.push({
            clipId: clip.id,
            clipTitle: clip.hook_title || clip.name,
            index: currentIndex,
            error: err.message || String(err),
          });

          log(`❌ [${currentIndex + 1}/${clips.length}] คลิป "${clip.hook_title || clip.name}" เกิดข้อผิดพลาด: ${err.message}`, 'error');

          if (!autoSkipOnError) {
            setState(BATCH_STATES.ERROR);
            throw err;
          }

          log(`⏭️ ข้ามไปทำคลิปถัดไปอัตโนมัติ (Resilient Auto-Skip)...`, 'warn');
          if (actions.resetUploadPage) {
            try { await actions.resetUploadPage(); } catch (_) {}
          }
        }
        currentIndex += 1;
      }

      if (isStopped) {
        setState(BATCH_STATES.STOPPED);
        log(`⏹️ ผู้ใช้สั่งหยุดการทำงาน (Stopped) สำเร็จ ${successful}/${clips.length} คลิป`, 'warn');
      } else {
        setState(BATCH_STATES.COMPLETED);
        log(`🎉 ดำเนินการเสร็จสิ้นทุกคลิปในคิว! สำเร็จ: ${successful}, ล้มเหลว/ข้าม: ${failed}`, 'success');
      }
    } catch (fatalErr) {
      if (fatalErr.message === 'BATCH_STOPPED') {
        setState(BATCH_STATES.STOPPED);
      } else {
        setState(BATCH_STATES.ERROR);
        log(`💥 Fatal Error: ${fatalErr.message}`, 'error');
      }
    }

    return {
      total: clips.length,
      processed: currentIndex,
      successful,
      failed,
      errors,
      state,
    };
  }

  function pause() {
    if (state === BATCH_STATES.COMPLETED || state === BATCH_STATES.STOPPED) return;
    isPaused = true;
    setState(BATCH_STATES.PAUSED);
  }

  function resume() {
    if (!isPaused) return;
    isPaused = false;
    if (pauseResolver) {
      const res = pauseResolver;
      pauseResolver = null;
      res();
    }
  }

  function stop() {
    isStopped = true;
    isPaused = false;
    if (pauseResolver) {
      const res = pauseResolver;
      pauseResolver = null;
      res();
    }
    setState(BATCH_STATES.STOPPED);
  }

  return {
    start,
    pause,
    resume,
    stop,
    getState: () => state,
    getStats,
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    BATCH_STATES,
    createBatchRunner,
  };
}

if (typeof globalThis !== 'undefined') {
  globalThis.OmniBatchRunner = {
    BATCH_STATES,
    createBatchRunner,
  };
}
