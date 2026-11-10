'use strict';
// One source of truth shared with the extension (price rule, Content-page row matching).
const { PRICE_RE, PLACEHOLDER_RE, contentReason, rowMatchesClip } = require('../../tiktok_autopost_extension/post_guard.js');
// Sequential, unattended TikTok posting. One clip at a time, per channel.
// All TikTok DOM work is delegated to the verified extension worker through
// `worker.send(action)`; this module owns ordering, safety stops and results.

const FATAL_RE = /captcha|verify it'?s you|ยืนยันตัวตน|account_handle_mismatch|source_account_required|posting_receipt_unsent|posting_instance_busy|login_required|\b401\b/i;
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
function skipReason(clip, { now = Date.now(), allowPriceCaption = false, mode = 'schedule' } = {}) {
  if (!clip.export_id || !clip.rel_path) return 'no_export';
  if (mode !== 'draft') {
    // a draft has no publish time, so only a scheduled post needs a future slot
    if (!clip.schedule_date || !clip.schedule_time) return 'no_schedule';
    const slot = new Date(`${clip.schedule_date}T${clip.schedule_time}:00`).getTime();
    if (!Number.isFinite(slot) || slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
  }
  if (!clip.tiktok_product_id) return 'no_tiktok_product_id';
  const content = contentReason(clip.caption, clip.hashtags, {allowPrice: allowPriceCaption});
  if (content) return content;
  return '';
}

// Dry-run never posts, so a slot that already passed is replaced by a synthetic
// one (2 days ahead, 12:00) just to exercise the TikTok schedule picker.
function dryRunSlot(now) {
  const d = new Date(now + 2 * 24 * 3600 * 1000);
  const pad = n => String(n).padStart(2, '0');
  return { date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, time: '12:00' };
}

// id -> export record, or null when the registry cannot be read (then prepare is the judge).
async function loadExportIndex(api) {
  try {
    const res = await api.get('/api/exports');
    if (!res.ok) return null;
    const list = Array.isArray(res.data) ? res.data : (res.data?.exports || res.data?.items);
    if (!Array.isArray(list)) return null;
    return new Map(list.map(e => [e.id || e.export_id, e]));
  } catch (_) { return null; }
}

async function pickClips(api, { queueId = null, limit = 10, now = Date.now(), allowPriceCaption = false, dryRun = false, mode = 'schedule' } = {}) {
  const res = await api.get('/api/schedule-queue');
  if (!res.ok) throw new Error(`schedule-queue ${res.status}: ${res.data?.detail || ''}`);
  const items = (res.data.items || [])
    .filter(item => READY_STATUSES.includes(item.status) && (!queueId || item.id === queueId))
    .map(clipFromQueueItem)
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));
  const exportIndex = await loadExportIndex(api);
  const clips = [];
  const skipped = [];
  for (const clip of items) {
    const record = exportIndex?.get(clip.export_id);
    if (exportIndex && !record) { skipped.push({ id: clip.id, title: clip.title, reason: 'export_missing' }); continue; }
    if (record?.is_posted || record?.export_status === 'posted') { skipped.push({ id: clip.id, title: clip.title, reason: 'export_already_posted' }); continue; }
    if (record?.is_qc_rejected) { skipped.push({ id: clip.id, title: clip.title, reason: 'export_qc_rejected' }); continue; }
    let reason = skipReason(clip, { now, allowPriceCaption, mode });
    if (reason === 'slot_passed_or_too_close' && dryRun) {
      const slot = dryRunSlot(now);
      clip.schedule_date = slot.date;
      clip.schedule_time = slot.time;
      clip.schedule_overridden = true;
      reason = skipReason(clip, { now, allowPriceCaption });
    }
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

class ClipCancelled extends Error {
  constructor() { super('clip_cancelled: คลิปนี้หมดเวลาแล้ว จึงไม่ส่งคำสั่งต่อไปยังเบราว์เซอร์'); this.name = 'ClipCancelled'; }
}

async function runClip(deps, clip, { dryRun = false, channelId = 'main', coverFallback = false, mode = 'schedule', run = null } = {}) {
  const draft = mode === 'draft';
  const { worker, log, shot, dumpDom, sleep } = deps;
  // `run` is this clip's generation token. When the watchdog gives up on the clip it flips run.cancelled, and from then
  // on every worker/API call of the abandoned run throws instead of reaching the (new) worker -- most importantly it
  // can never press Post after the batch has moved on to the next clip.
  const ensureActive = () => { if (run?.cancelled) throw new ClipCancelled(); };
  const send = async (action, payload) => {
    ensureActive();
    if (run && (action === 'click-post-only' || action === 'save-draft-only')) run.postSent = true;
    return worker.send(action, payload);
  };
  const api = {
    get: async (route) => { ensureActive(); return deps.api.get(route); },
    post: async (route, body) => { ensureActive(); return deps.api.post(route, body); },
  };
  let step = 'prepare';
  try {
    const payload = {
      video_path: clip.rel_path, export_id: clip.export_id, cover_path: clip.cover_path,
      caption: clip.caption, hashtags: clip.hashtags, product_id: clip.product_id, angle_id: clip.angle_id,
      tiktok_product_id: clip.tiktok_product_id, product_name: clip.product_name,
      queue_id: clip.queue_id, intent: draft ? 'draft' : 'schedule',
      schedule_date: draft ? null : clip.schedule_date, schedule_time: draft ? null : clip.schedule_time,
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
    if (!res.ok && [404, 409, 422].includes(res.status)) {
      // A data problem with this clip (stale export, not ready, ...): nothing was
      // prepared, so skip it with the reason instead of counting a failure.
      return { status: 'skipped', reason: `prepare_${res.status}: ${res.data?.detail || res.data?.code || ''}` };
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
    const details = await send('prepare-details', {
      caption: clip.caption, hashtags: clip.hashtags, productId: clip.tiktok_product_id,
      scheduleMode: !draft, cartName: clip.product_name || '',
      scheduleDate: draft ? '' : clip.schedule_date, scheduleTime: draft ? '' : clip.schedule_time,
      coverPath: prepared.cover_path || clip.cover_path || '',
    });
    let coverFallbackUsed = false;
    // This Studio build may offer no custom-cover upload (only frame/sticker/text).
    // Everything before the cover step must have succeeded; then, only when the
    // operator allowed it (or in dry-run), keep TikTok's automatic cover.
    const beforeCover = ['caption', 'product', 'schedule'];
    if (details?.success === false && details.step === 'cover' && (coverFallback || dryRun)
        && beforeCover.every(k => details.completed?.includes(k))) {
      log('warn', `อัปโหลดปกไม่สำเร็จ (${details.error || 'ไม่ทราบสาเหตุ'}) — ใช้ปกอัตโนมัติของ TikTok แทน`);
      await deps.dismissCoverModal?.();
      coverFallbackUsed = true;
    } else {
      expectOk(details, 'กรอกรายละเอียด');
    }

    if (dryRun) {
      await shot(`${clip.id}_filled`);
      await dumpDom(`${clip.id}_filled`);
      step = 'dry_release';
      expectOk(await send('release-posting-job', { park: true }), 'ปล่อยงาน dry-run');
      await send('reset-upload-page');
      return { status: 'dry_run_ok', cover_fallback: coverFallbackUsed };
    }

    step = 'post';
    // A draft never presses Post (with no schedule that would publish LIVE): it has its own step.
    const result = await send(draft ? 'save-draft-only' : 'click-post-only');
    await shot(`${clip.id}_after_post`);
    expectOk(result, 'กดโพสต์');
    const outcome = result.outcome || (draft ? 'confirmation_unknown' : (result.posted ? 'published' : 'confirmation_unknown'));
    step = 'reconcile';
    if (shouldReconcile(outcome, result)) {
      await send('reconcile-posting-result', { manual: false }).catch(e => log('warn', `ตรวจผลซ้ำกับ TikTok ไม่สำเร็จ: ${e.message}`));
    }
    await send('retry-posting-receipt').catch(e => log('warn', `ส่งผลกลับ backend ไม่สำเร็จ (จะลองใหม่รอบหน้า): ${e.message}`));
    let status = outcome === 'published' ? 'posted' : outcome === 'scheduled_on_platform' ? 'scheduled' : outcome === 'draft_saved' ? 'drafted' : 'unknown';
    if (draft && status === 'posted') throw new Error('draft run got a published outcome: stop (the Post button must never be pressed in draft mode)');
    // Second, independent proof: the clip must really be listed on TikTok Studio > Content.
    let verified = null;
    if (status === 'drafted') {
      // Draft proof: Content > Drafts must list a row for this caption (the worker already saw it once).
      step = 'verify';
      const reply = await send('verify-draft-content', { caption: prepared.caption || clip.caption }).catch(e => ({ verified: false, reason: e.message }));
      verified = { ok: Boolean(reply?.verified), reason: reply?.reason || '' };
      if (!verified.ok) {
        log('warn', `ตรวจหน้า Drafts แล้วไม่ยืนยัน: ${verified.reason} — ถือว่ายังไม่แน่ใจ`);
        status = 'unknown';
      }
    } else if (status !== 'unknown' && deps.verifyOnContentPage) {
      step = 'verify';
      verified = await deps.verifyOnContentPage(clip).catch(e => ({ ok: false, reason: e.message }));
      if (!verified.ok) {
        log('warn', `ตรวจหน้า Content แล้วไม่ยืนยัน: ${verified.reason} — ถือว่ายังไม่แน่ใจ`);
        status = 'unknown';
      }
    }
    return { status, outcome, job_id: prepared.job_id, cover_fallback: coverFallbackUsed, verified: verified ? verified.ok : null,
      ...(verified && !verified.ok ? { error: `${draft ? 'drafts' : 'content'}_page_not_verified: ${verified.reason}` } : {}) };
  } catch (error) {
    if (error instanceof ClipCancelled) return { status: 'failed', step: 'cancelled', error: error.message };
    const message = error?.message || String(error);
    // Evidence first: what did the page look like when this step failed?
    await Promise.resolve(shot?.(`${clip.id}_FAIL_${step}`)).catch(() => {});
    await Promise.resolve(dumpDom?.(`${clip.id}_FAIL_${step}`)).catch(() => {});
    if (FATAL_RE.test(message)) throw new FatalError(message, step);
    return { status: 'failed', step, error: message };
  }
}

async function betweenClips(deps) {
  const { worker, log } = deps;
  // The browser may have died or hung since the last clip: bring it back first.
  if (deps.ensureBrowser) {
    try { await deps.ensureBrowser(); }
    catch (error) {
      const message = error?.message || String(error);
      if (FATAL_RE.test(message)) throw new FatalError(message, 'browser');
      log('warn', `ตรวจ/เปิดเบราว์เซอร์ไม่สำเร็จ: ${message}`);
    }
  }
  const parked = await worker.send('release-posting-job', { park: true }).catch(e => ({ success: false, error: e.message }));
  if (parked.success === false) {
    const message = parked.error || 'park failed';
    if (FATAL_RE.test(message)) throw new FatalError(message, 'park');
    log('warn', `พักงานเดิมไม่สำเร็จ: ${message}`);
  }
  await worker.send('reset-upload-page').catch(e => log('warn', `reset หน้าอัปโหลดไม่สำเร็จ: ${e.message}`));
}

const PRE_POST_STEPS = new Set(['prepare', 'claim', 'upload', 'wait_upload', 'details', 'dry_release']);

class ClipTimeout extends Error {
  constructor(ms) { super(`clip_timeout: เกินเวลาต่อคลิป ${Math.round(ms / 60000)} นาที`); this.name = 'ClipTimeout'; }
}

// Races a clip against its time budget. On timeout the zombie browser actions are
// killed (deps.recover) so the next clip starts from a clean worker.
async function runClipGuarded(deps, clip, options, budgetMs) {
  let timer;
  const run = { cancelled: false, postSent: false };
  const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(new ClipTimeout(budgetMs)), budgetMs); });
  try {
    return await Promise.race([runClip(deps, clip, { ...options, run }), timeout]);
  } catch (error) {
    if (error instanceof ClipTimeout) {
      run.cancelled = true;           // BEFORE recover(): the zombie run must not send anything to the replacement worker
      await deps.recover?.();
      // Once Post / Save draft was sent the click may have happened: that is "unknown" (never retried), not "failed".
      if (run.postSent) return { status: 'unknown', step: 'timeout', error: `${error.message} (หลังส่งคำสั่งกดโพสต์แล้ว ผลไม่แน่ชัด)` };
      return { status: 'failed', step: 'timeout', error: error.message };
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

// Queue rows an earlier run could not confirm. They are never picked again (not READY), but the operator must see them.
async function findUnresolved(api) {
  try {
    const res = await api.get('/api/schedule-queue');
    if (!res?.ok) return [];
    return (res.data?.items || []).filter(item => item.status === 'confirmation_unknown');
  } catch (_) { return []; }
}

async function runBatch(deps, { clips, dryRun = false, channelId = 'main', coverFallback = false, mode = 'schedule', clipBudgetMs = 25 * 60 * 1000, maxClipAttempts = 2, cooldownSec = [20, 40],
  maxConsecutiveFailures = 3, maxConsecutiveUnknown = 2, shouldStop = () => false, random = Math.random } = {}) {
  const { log, sleep } = deps;
  const results = [];
  let failStreak = 0;
  let unknownStreak = 0;
  let aborted = null;
  // TikTok caps scheduled posts and drafts (30 each). Read the live counts once and never plan more clips
  // than what is left; when the counts cannot be read, say so and fall back to the operator's --limit.
  if (!dryRun) {
    const unresolved = await findUnresolved(deps.api);
    if (unresolved.length) {
      log('warn', `มี ${unresolved.length} คลิปที่รอบก่อนยืนยันผลไม่ได้ (${unresolved.slice(0, 3).map(i => i.hook_title || i.id).join(', ')}) — จะไม่รันซ้ำ ตรวจที่ TikTok Studio > Content แล้วแก้สถานะในแอป`);
    }
  }
  let quota = null;
  if (!dryRun && deps.quota) {
    quota = await deps.quota().catch(error => ({ success: false, error: error.message }));
    const used = mode === 'draft' ? quota?.draftCount : quota?.scheduledCount;
    const left = mode === 'draft' ? quota?.remainingDraft : quota?.remainingSchedule;
    if (typeof used === 'number' && typeof left === 'number') {
      log('info', `โควตา TikTok (${mode === 'draft' ? 'แบบร่าง' : 'ตั้งเวลา'}): ใช้ไป ${used}/30 · เหลือ ${left}`);
      if (left <= 0) {
        log('error', `โควตา${mode === 'draft' ? 'แบบร่าง' : 'ตั้งเวลา'}เต็ม 30/30 หยุดก่อนเริ่ม`);
        return { total: 0, aborted: `quota_full_${mode}`, quota, posted: 0, scheduled: 0, drafted: 0, unknown: 0, skipped: 0, failed: 0, dry_run_ok: 0, results: [] };
      }
      if (clips.length > left) {
        log('warn', `มี ${clips.length} คลิป แต่โควตาเหลือ ${left} — รันเฉพาะ ${left} คลิปแรก`);
        clips = clips.slice(0, left);
      }
    } else {
      log('warn', `อ่านโควตา TikTok ไม่ได้${quota?.error ? ` (${quota.error})` : ''} — ใช้ --limit เป็นตัวกัน`);
    }
  }
  for (let i = 0; i < clips.length; i += 1) {
    if (shouldStop()) { aborted = 'stopped_by_user'; break; }
    const clip = clips[i];
    log('info', `[${i + 1}/${clips.length}] ${clip.title} (${mode === 'draft' ? 'แบบร่าง' : `${clip.schedule_date} ${clip.schedule_time}`})${dryRun ? ' [dry-run]' : ''}`);
    let result;
    try {
      await betweenClips(deps);
      result = await runClipGuarded(deps, clip, { dryRun, channelId, coverFallback, mode }, clipBudgetMs);
      // A transient hiccup BEFORE the post click (caption not accepted, slow list, ...) is
      // retried once from a clean page. Never after the click: that could post twice.
      if (result.status === 'failed' && PRE_POST_STEPS.has(result.step) && maxClipAttempts > 1) {
        log('warn', `พลาดที่ขั้น ${result.step} (${result.error}) — ลองใหม่อีกครั้งจากหน้าสะอาด`);
        await betweenClips(deps);
        result = await runClipGuarded(deps, clip, { dryRun, channelId, coverFallback, mode }, clipBudgetMs);
        result.retried = true;
      }
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
    total: clips.length, aborted, mode, quota,
    posted: count('posted'), scheduled: count('scheduled'), drafted: count('drafted'), unknown: count('unknown'),
    skipped: count('skipped'), failed: count('failed'), dry_run_ok: count('dry_run_ok'), results,
  };
}

module.exports = { runClipGuarded, ClipTimeout, ClipCancelled, findUnresolved, rowMatchesClip, FATAL_RE, PRICE_RE, FatalError, clipFromQueueItem, skipReason, pickClips, runClip, runBatch, shouldReconcile };
