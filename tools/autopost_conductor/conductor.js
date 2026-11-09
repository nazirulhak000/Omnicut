'use strict';
// Sequential, unattended TikTok posting. One clip at a time, per channel.
// All TikTok DOM work is delegated to the verified extension worker through
// `worker.send(action)`; this module owns ordering, safety stops and results.

const FATAL_RE = /captcha|verify it'?s you|ยืนยันตัวตน|account_handle_mismatch|source_account_required|posting_receipt_unsent|posting_instance_busy|login_required|\b401\b/i;
// Channel rule: never publish price / discount text (breaks TikTok rules).
const PRICE_RE = /฿|\bTHB\b|\d[\d,]*\s*บาท|ราคา|ลดราคา|ส่วนลด|ลด\s*\d+\s*%|\d+\s*%\s*off|\$\s*\d/i;
const MIN_LEAD_MS = 15 * 60 * 1000;
const READY_STATUSES = ['planned', 'ready_for_extension'];

class FatalError extends Error {
  constructor(message, step) { super(message); this.name = 'FatalError'; this.step = step; }
}

function clipFromQueueItem(item) {
  const at = String(item.scheduled_at || '');
  return {
    id: item.id,
    queue_id: item.id,
    title: item.hook_title || item.project_name || item.video_path,
    rel_path: item.video_path,
    export_id: item.export_id,
    cover_path: item.cover_path || null,
    caption: item.caption || item.hook_title || item.project_name || '',
    hashtags: item.hashtags || '',
    product_id: item.product_id || null,
    angle_id: item.angle_id || null,
    tiktok_product_id: item.tiktok_product_id || null,
    product_name: item.product_name || null,
    scheduled_at: at,
    schedule_date: /^\d{4}-\d{2}-\d{2}/.test(at) ? at.slice(0, 10) : '',
    schedule_time: (/T(\d{2}:\d{2})/.exec(at) || [])[1] || '',
  };
}

// Returns '' when the clip can be posted, otherwise a short skip reason.
function skipReason(clip, { now = Date.now(), allowPriceCaption = false } = {}) {
  if (!clip.export_id || !clip.rel_path) return 'no_export';
  if (!clip.schedule_date || !clip.schedule_time) return 'no_schedule';
  const slot = new Date(`${clip.schedule_date}T${clip.schedule_time}:00`).getTime();
  if (!Number.isFinite(slot) || slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
  if (!clip.tiktok_product_id) return 'no_tiktok_product_id';
  if (!allowPriceCaption && PRICE_RE.test(`${clip.caption} ${clip.hashtags}`)) return 'price_in_caption';
  return '';
}

async function pickClips(api, { queueId = null, limit = 10, now = Date.now(), allowPriceCaption = false } = {}) {
  const res = await api.get('/api/schedule-queue');
  if (!res.ok) throw new Error(`schedule-queue ${res.status}: ${res.data?.detail || ''}`);
  const items = (res.data.items || [])
    .filter(item => READY_STATUSES.includes(item.status) && (!queueId || item.id === queueId))
    .map(clipFromQueueItem)
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));
  const clips = [];
  const skipped = [];
  for (const clip of items) {
    const reason = skipReason(clip, { now, allowPriceCaption });
    if (reason) skipped.push({ id: clip.id, title: clip.title, reason });
    else if (clips.length < limit) clips.push(clip);
  }
  return { clips, skipped };
}

function expectOk(reply, what) {
  if (!reply || reply.success === false || reply.error) {
    throw new Error(reply?.error || reply?.reason || `${what} ไม่สำเร็จ`);
  }
  return reply;
}

function shouldReconcile(outcome, result) {
  return outcome === 'confirmation_unknown' || result?.outcome === 'confirmation_unknown' || Boolean(result?.markError);
}

async function runClip(deps, clip, { dryRun = false, channelId = 'main' } = {}) {
  const { worker, api, log, shot, dumpDom, sleep } = deps;
  const send = (action, payload) => worker.send(action, payload);
  let step = 'prepare';
  try {
    const payload = {
      video_path: clip.rel_path, export_id: clip.export_id, cover_path: clip.cover_path,
      caption: clip.caption, hashtags: clip.hashtags, product_id: clip.product_id, angle_id: clip.angle_id,
      tiktok_product_id: clip.tiktok_product_id, product_name: clip.product_name,
      queue_id: clip.queue_id, schedule_date: clip.schedule_date, schedule_time: clip.schedule_time,
    };
    let res = await api.post('/api/tiktok-autopost/prepare', payload);
    if (!res.ok && res.status === 409 && /already_prepared|มีงานโพสต์อยู่แล้ว|มีคลิปรอโพสต์ค้างอยู่/.test(JSON.stringify(res.data))) {
      // Only a never-claimed job of the SAME export may be cleared. Anything
      // claimed/attempted could already be live on TikTok: never touch it.
      const pending = await api.get('/api/tiktok-autopost/pending');
      const job = pending.ok ? pending.data : null;
      if (job?.job_id && job.status === 'prepared' && job.export_id === clip.export_id) {
        await api.post('/api/tiktok-autopost/clear', { job_id: job.job_id });
        res = await api.post('/api/tiktok-autopost/prepare', payload);
      } else {
        return { status: 'skipped', reason: 'export_already_has_job' };
      }
    }
    if (!res.ok) throw new Error(`prepare ${res.status}: ${res.data?.detail || res.data?.code || ''}`);
    const prepared = res.data;
    if (prepared.protocol_version !== 2 || prepared.channel_id !== channelId || !prepared.job_id) {
      throw new Error('prepare คืน job ที่ไม่ตรง protocol/ช่อง');
    }

    step = 'claim';
    expectOk(await send('claim-posting-job', { jobId: prepared.job_id, channelId }), 'รับงาน');
    step = 'upload';
    expectOk(await send('upload-file-only'), 'อัปโหลดไฟล์วิดีโอ');
    await sleep(1200);
    step = 'wait_upload';
    expectOk(await send('wait-for-upload-only'), 'รออัปโหลดวิดีโอ');
    step = 'details';
    expectOk(await send('prepare-details', {
      caption: clip.caption, hashtags: clip.hashtags, productId: clip.tiktok_product_id,
      scheduleMode: true, cartName: clip.product_name || '',
      scheduleDate: clip.schedule_date, scheduleTime: clip.schedule_time,
      coverPath: prepared.cover_path || clip.cover_path || '',
    }), 'กรอกรายละเอียด');

    if (dryRun) {
      await shot(`${clip.id}_filled`);
      await dumpDom(`${clip.id}_filled`);
      step = 'dry_release';
      expectOk(await send('release-posting-job', { park: true }), 'ปล่อยงาน dry-run');
      await send('reset-upload-page');
      return { status: 'dry_run_ok' };
    }

    step = 'post';
    const result = await send('click-post-only');
    await shot(`${clip.id}_after_post`);
    expectOk(result, 'กดโพสต์');
    const outcome = result.outcome || (result.posted ? 'published' : 'confirmation_unknown');
    step = 'reconcile';
    if (shouldReconcile(outcome, result)) await send('reconcile-posting-result', { manual: false }).catch(() => {});
    await send('retry-posting-receipt').catch(() => {});
    const status = outcome === 'published' ? 'posted' : outcome === 'scheduled_on_platform' ? 'scheduled' : 'unknown';
    return { status, outcome, job_id: prepared.job_id };
  } catch (error) {
    const message = error?.message || String(error);
    if (FATAL_RE.test(message)) throw new FatalError(message, step);
    return { status: 'failed', step, error: message };
  }
}

async function betweenClips(deps) {
  const { worker, log } = deps;
  const parked = await worker.send('release-posting-job', { park: true }).catch(e => ({ success: false, error: e.message }));
  if (parked.success === false) {
    const message = parked.error || 'park failed';
    if (FATAL_RE.test(message)) throw new FatalError(message, 'park');
    log('warn', `พักงานเดิมไม่สำเร็จ: ${message}`);
  }
  await worker.send('reset-upload-page').catch(e => log('warn', `reset หน้าอัปโหลดไม่สำเร็จ: ${e.message}`));
}

async function runBatch(deps, { clips, dryRun = false, channelId = 'main', cooldownSec = [20, 40],
  maxConsecutiveFailures = 3, maxConsecutiveUnknown = 2, shouldStop = () => false, random = Math.random } = {}) {
  const { log, sleep } = deps;
  const results = [];
  let failStreak = 0;
  let unknownStreak = 0;
  let aborted = null;
  for (let i = 0; i < clips.length; i += 1) {
    if (shouldStop()) { aborted = 'stopped_by_user'; break; }
    const clip = clips[i];
    log('info', `[${i + 1}/${clips.length}] ${clip.title} (${clip.schedule_date} ${clip.schedule_time})${dryRun ? ' [dry-run]' : ''}`);
    let result;
    try {
      await betweenClips(deps);
      result = await runClip(deps, clip, { dryRun, channelId });
    } catch (error) {
      aborted = `fatal@${error.step || '?'}: ${error.message}`;
      results.push({ id: clip.id, title: clip.title, status: 'fatal', error: error.message, step: error.step });
      log('error', `หยุดทั้งงาน: ${aborted}`);
      break;
    }
    results.push({ id: clip.id, title: clip.title, ...result });
    log(result.status === 'failed' ? 'error' : 'info', `→ ${result.status}${result.error ? `: ${result.error}` : ''}`);
    failStreak = result.status === 'failed' ? failStreak + 1 : 0;
    unknownStreak = result.status === 'unknown' ? unknownStreak + 1 : 0;
    if (failStreak >= maxConsecutiveFailures) { aborted = `ล้มเหลวติดกัน ${failStreak} คลิป`; break; }
    if (unknownStreak >= maxConsecutiveUnknown) { aborted = `ยืนยันผลไม่ได้ติดกัน ${unknownStreak} คลิป`; break; }
    if (i < clips.length - 1) {
      const [lo, hi] = dryRun ? [2, 4] : cooldownSec;
      await sleep(Math.round((lo + random() * (hi - lo)) * 1000));
    }
  }
  const count = status => results.filter(r => r.status === status).length;
  return {
    total: clips.length, aborted,
    posted: count('posted'), scheduled: count('scheduled'), unknown: count('unknown'),
    skipped: count('skipped'), failed: count('failed'), dry_run_ok: count('dry_run_ok'), results,
  };
}

module.exports = { FATAL_RE, PRICE_RE, FatalError, clipFromQueueItem, skipReason, pickClips, runClip, runBatch, shouldReconcile };
