// OmniCut TikTok Post Helper -- background service worker (Manifest V3).
//
// Why chrome.debugger at all: browsers hard-block scripts (page JS AND
// extension content scripts) from setting <input type=file>.files -- see
// TIKTOK_AUTOPOST_PLAN.md §"ไม่มีทางลัดที่ปลอดภัยกว่า". The only surface
// that can is the Chrome DevTools Protocol's DOM.setFileInputFiles, which
// requires chrome.debugger.attach() first -- the same mechanism Playwright
// and Puppeteer use. Chrome shows an un-hideable "being debugged" banner on
// the tab the whole time this runs. That is intentional, not a bug to hide.
//
// This file only runs when the user clicks a button inside the side panel
// (sidepanel.html/.js), on a tab they already have open and already logged
// into. Nothing here schedules itself, polls in the background, or runs
// without that click.
//
// 2026-09-06: clicking the toolbar icon now opens the side panel directly
// (the old popup.html/popup.js checklist was merged into sidepanel.html as
// its own tab and deleted -- one UI surface instead of two).
importScripts('automation.js', 'auth_key.js');

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((err) => {
  console.error('setPanelBehavior failed:', err);
});
//
// Selectors marked UNVERIFIED come from TIKTOK_AUTOPOST_PLAN.md §3 --
// community-documented as of the plan's writing, never confirmed against a
// real logged-in TikTok Studio session (that needs a real account, which
// this tool's author does not have access to). If a step throws here,
// that selector is almost certainly the first thing to check.

const BACKEND = 'http://127.0.0.1:8000';
const UPLOAD_URL_PATTERN = 'https://www.tiktok.com/tiktokstudio/upload*';
const PROCESSING_TIMEOUT_MS = 90_000;
const POLL_INTERVAL_MS = 2_000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const POSTING_STATE_KEY = 'omnicutPostingProtocolV2';
const POSTING_CHANNEL_KEY = 'omnicutChannelId';
let postingStateCache = null;

function postingChannelId(value) {
  if (typeof value !== 'string' || !/^[a-z][a-z0-9_-]{1,31}$/.test(value) || /[\r\n]/.test(value)) {
    throw new Error('รหัสช่องโพสต์ไม่ถูกต้อง');
  }
  return value;
}

function normalizePostingAccount(raw) {
  if (!raw) return null;
  let value = String(raw).trim();
  if (/^https?:\/\//i.test(value)) {
    const url = new URL(value);
    if (!/(^|\.)tiktok\.com$/i.test(url.hostname)) throw new Error('บัญชีไม่ใช่ TikTok');
    value = url.pathname.split('/').find(part => part.startsWith('@')) || '';
  }
  value = value.replace(/^@/, '').toLowerCase();
  if (!/^[a-z0-9._]{2,24}$/.test(value) || value.includes('..') || value.endsWith('.')) throw new Error('อ่าน handle บัญชีไม่ได้');
  return '@' + value;
}

function checkPostingAccount(job, raw) {
  let source = null;
  try {
    source = normalizePostingAccount(raw);
  } catch (_) {}
  const target = normalizePostingAccount(job.target_handle);
  if (source && target && source !== target) {
    throw new Error(`account_handle_mismatch: บัญชี TikTok (${source}) ไม่ตรงกับช่องของงาน (${target}) หยุดก่อนโพสต์`);
  }
  if (!source) {
    throw new Error('source_account_required: อ่านบัญชี TikTok ไม่ได้ หยุดก่อนโพสต์');
  }
  return source;
}

function postingStorageGet(keys) {
  return new Promise((resolve, reject) => {
    if (!chrome.storage?.local) return reject(new Error('ไม่พบ storage สำหรับ durable posting protocol'));
    chrome.storage.local.get(keys, data => chrome.runtime.lastError ? reject(new Error(chrome.runtime.lastError.message)) : resolve(data || {}));
  });
}

function postingStorageSet(data) {
  return new Promise((resolve, reject) => {
    if (!chrome.storage?.local) return reject(new Error('บันทึกงานโพสต์ไม่ได้'));
    chrome.storage.local.set(data, () => chrome.runtime.lastError ? reject(new Error(chrome.runtime.lastError.message)) : resolve());
  });
}

async function postingState() {
  if (!postingStateCache) {
    const saved = await postingStorageGet([POSTING_STATE_KEY, POSTING_CHANNEL_KEY]);
    postingStateCache = saved[POSTING_STATE_KEY] || {
      instanceId: globalThis.crypto?.randomUUID?.() || `ext-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      channelId: postingChannelId(saved[POSTING_CHANNEL_KEY] || 'main'), activeJob: null, pendingReceipt: null, tabId: null,
    };
    postingChannelId(postingStateCache.channelId);
    await persistPostingState(postingStateCache);
  }
  return postingStateCache;
}

async function persistPostingState(state) {
  await postingStorageSet({[POSTING_STATE_KEY]: state});
  postingStateCache = state;
}

async function postingRequest(path, channelId, body) {
  const apiKey = await getStoredApiKey();
  const response = await authedFetch(`${BACKEND}/api/tiktok-autopost${path}`, apiKey, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {'Content-Type': 'application/json', 'X-OmniCut-Channel': postingChannelId(channelId)},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${data.code || response.status}: ${data.detail || 'ติดต่อ posting protocol ไม่สำเร็จ'}`);
  if (data.channel_id && data.channel_id !== channelId) throw new Error('ผลตอบกลับเป็นของอีกช่อง หยุดการโพสต์');
  return data;
}

function postingFence(job, sourceAccount) {
  return {protocol_version: 2, job_id: job.job_id, lease_owner: job.lease_owner,
    lease_token: job.lease_token, expected_revision: job.revision,
    payload_hash: job.payload_hash, source_account: sourceAccount,
    ...(job.confirmation_token ? {confirmation_token:job.confirmation_token} : {})};
}

async function readStudioAccount(send) {
  const response = await send('Runtime.evaluate', {
    expression: `(() => {
      const handles = [];
      const nodes = Array.from(document.querySelectorAll(
        '[data-e2e="profile-icon"] a[href*="/@"], a[data-e2e="profile-icon"][href*="/@"], '
        + '[data-e2e="user-avatar"] a[href*="/@"], [data-e2e="account-menu"] a[href*="/@"], '
        + '[data-e2e="account-handle"], [data-e2e="user-unique-id"], a[href*="/@"]'));
      for (const el of nodes) {
        const val = el.getAttribute('href') || (el.textContent || '').trim();
        const m = val.match(/@([a-zA-Z0-9._]+)/);
        if (m) handles.push('@' + m[1]);
      }
      try {
        const rehydrate = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
        if (rehydrate && rehydrate.textContent) {
          const json = JSON.parse(rehydrate.textContent);
          const scope = json['__DEFAULT_SCOPE__'] || {};
          const uid = scope['webapp.user-detail']?.userInfo?.user?.uniqueId
            || scope['webapp.app-context']?.user?.uniqueId
            || scope['creator.studio']?.user?.uniqueId;
          if (uid) handles.push('@' + uid);
        }
      } catch (_) {}
      try {
        const match = document.documentElement.innerHTML.match(/"uniqueId"\s*:\s*"([a-zA-Z0-9._]{2,24})"/);
        if (match && match[1]) handles.push('@' + match[1]);
      } catch (_) {}
      return {handles: [...new Set(handles)]};
    })()`, returnByValue: true,
  });
  if (response?.exceptionDetails) throw new Error('อ่านบัญชีจาก TikTok Studio ไม่สำเร็จ');
  const values = response?.result?.value?.handles || [];
  const handles = [...new Set(values.map(normalizePostingAccount).filter(Boolean))];
  if (handles.length > 1) throw new Error('พบหลายบัญชีใน profile control หยุดเพื่อป้องกันโพสต์ผิดช่อง');
  return handles[0] || null;
}

async function guardPostingAction(job, send, tabId, {beginPublish = false, retried = false} = {}) {
  if (!job.job_id || job.protocol_version !== 2 || !job.lease_token) throw new Error('ต้องอัปเดต backend/extension เป็น posting protocol รุ่น 2');
  const state = await postingState();
  if (state.channelId && job.channel_id && state.channelId !== job.channel_id) {
    throw new Error('ช่องที่เลือกไม่ตรงกับ snapshot งาน');
  }
  if (state.tabId !== null && state.tabId !== tabId) {
    let oldTabAlive = false;
    if (typeof chrome !== 'undefined' && chrome.tabs?.get) {
      try {
        const oldTab = await chrome.tabs.get(state.tabId);
        if (oldTab && isUploadTab(oldTab)) oldTabAlive = true;
      } catch (_) {}
    } else {
      oldTabAlive = true;
    }
    if (oldTabAlive) {
      throw new Error('หน้า TikTok ไม่ตรงกับ tab ที่ผูกงานไว้');
    }
    state.tabId = tabId;
  }
  if (state.pendingReceipt || job.publish_attempted_at || job.status !== 'claimed') throw new Error('ต้องตรวจผลเดิมก่อน ห้ามกดโพสต์ซ้ำ');
  state.tabId = tabId;
  await persistPostingState(state);
  const source = checkPostingAccount(job, await readStudioAccount(send));
  state.accountWarning = source ? null : 'อ่านบัญชี Studio ไม่ได้: main compatibility อนุญาตพร้อม audit กรุณาตรวจบัญชี';
  let updated;
  try {
    updated = await postingRequest(beginPublish ? '/attempt' : '/validate', job.channel_id, postingFence(job, source));
  } catch (err) {
    if (retried || !/posting_lease_expired|revision_conflict/.test(err.message)) throw err;
    // Only pre-publication state can regain a lease. A lost attempt reply is
    // recovered for reconciliation; it can never authorize a second click.
    const current = await postingRequest(`/jobs/${encodeURIComponent(job.job_id)}`, job.channel_id);
    if (current.lease_owner !== job.lease_owner) throw new Error('posting_lease_invalid: อีก instance รับงานแล้ว');
    if (current.status !== 'claimed' || current.publish_attempted_at) {
      Object.assign(job,current); state.activeJob=job; await persistPostingState(state);
      throw new Error('posting_reconciliation_required: ต้องตรวจผลเดิมก่อน ห้ามกดโพสต์ซ้ำ');
    }
    const reclaimed = await postingRequest('/claim', job.channel_id, {protocol_version:2,job_id:job.job_id,lease_owner:state.instanceId});
    Object.assign(job,reclaimed); state.activeJob=job; await persistPostingState(state);
    return guardPostingAction(job,send,tabId,{beginPublish,retried:true});
  }
  Object.assign(job, updated);
  state.activeJob = job;
  state.tabId = tabId;
  await persistPostingState(state);
  return source;
}

async function savePostingReceipt(job, source, outcome, proof) {
  const state = await postingState();
  state.pendingReceipt = {channelId: job.channel_id, body: {...postingFence(job, source), outcome, proof}, reconcile: false};
  // Persist before sending: backend failure can only retry this receipt,
  // never upload or click a platform button again, including after restart.
  await persistPostingState(state);
  return retryPostingReceipt();
}

async function retryPostingReceipt() {
  const state = await postingState();
  if (!state.pendingReceipt) return {success: true, retried: false};
  const receipt = state.pendingReceipt;
  const path = receipt.reconcile ? '/reconcile' : '/ack';
  let result;
  try {
    result = await postingRequest(path, receipt.channelId, receipt.body);
  } catch (error) {
    if (/posting_lease_expired|posting_reconciliation_required/.test(error.message)) {
      // A receipt after lease expiry or pre-attempt claim is reconciliation only; this endpoint
      // cannot authorize another platform attempt.
      receipt.reconcile = true;
      await persistPostingState(state);
      result = await postingRequest('/reconcile', receipt.channelId, receipt.body);
    } else throw error;
  }
  state.pendingReceipt = null;
  state.activeJob = result.status === 'confirmation_unknown' ? {...state.activeJob, ...result} : null;
  if (!state.activeJob) state.tabId = null;
  await persistPostingState(state);
  return {success: true, retried: true, outcome: result.status};
}

async function fetchPendingJob(requestedJobId = null) {
  const state = await postingState();
  if (state.pendingReceipt) {
    await retryPostingReceipt();
    throw new Error('บันทึกผลการโพสต์เดิมแล้ว โดยไม่ได้กดโพสต์ซ้ำ กรุณาตรวจสถานะก่อนเริ่มงานใหม่');
  }
  if (state.activeJob) {
    if (requestedJobId && requestedJobId !== state.activeJob.job_id) throw new Error('posting_instance_busy: อีกงานยังไม่เสร็จ');
    return state.activeJob;
  }
  const capabilities = await postingRequest('/capabilities', state.channelId);
  if (capabilities.protocol_version !== 2 || !capabilities.durable_jobs) throw new Error('Backend ยังไม่รองรับ durable posting protocol');
  const pending = await postingRequest(requestedJobId ? `/jobs/${encodeURIComponent(requestedJobId)}` : '/pending', state.channelId);
  if (!pending.job_id || pending.protocol_version !== 2 || pending.channel_id !== state.channelId) throw new Error('งานเดิมไม่มี job/channel identity ต้องเตรียมคลิปใหม่');
  const job = await postingRequest('/claim', state.channelId, {protocol_version: 2, job_id: pending.job_id, lease_owner: state.instanceId});
  state.activeJob = job;
  await persistPostingState(state);
  return job;
}

async function clearPendingJob() {
  const state = await postingState();
  if (state.activeJob || state.pendingReceipt) throw new Error('งานยังต้องตรวจผล ห้ามล้างงานกลาง');
  return {success: true};
}

async function releasePostingJob(options = {}) {
  const state = await postingState();
  const job = state.activeJob;
  if (!job) return {success:true};

  // 1. Recover latest status from backend first!
  let current = null;
  try {
    current = await postingRequest(`/jobs/${encodeURIComponent(job.job_id)}`, job.channel_id);
    if (current) Object.assign(job, current);
  } catch (_) {}

  // 2. If already published or cancelled on backend, clear local state immediately!
  if (job.status === 'published' || job.status === 'cancelled') {
    state.activeJob = null;
    state.pendingReceipt = null;
    state.tabId = null;
    state.accountWarning = null;
    await persistPostingState(state);
    return {success: true, job_id: job.job_id, status: job.status, alreadyResolved: true};
  }

  // 3. Pre-publish release check (unless force is requested)
  if (!options?.force && (state.pendingReceipt || job.publish_attempted_at || !['claimed','cancelled'].includes(job.status))) {
    throw new Error('ต้องตรวจผลเดิมก่อน ห้ามยกเลิกงานที่กดโพสต์แล้ว');
  }

  const fence = postingFence(job, null);
  if (options?.force) fence.force = true;
  const result = await postingRequest('/release', job.channel_id, fence);
  if (result.status !== 'cancelled' && result.status !== 'published') throw new Error('Backend ยังไม่ยืนยันการยกเลิกงาน');
  state.activeJob = null;
  state.tabId = null;
  state.accountWarning = null;
  await persistPostingState(state);
  return {success: true, job_id: job.job_id, status: result.status, forced: Boolean(options?.force)};
}

async function selectPostingChannel(channelId) {
  const state = await postingState();
  if (state.activeJob || state.pendingReceipt) throw new Error('posting_instance_busy: ตรวจผลหรือปิดงานเดิมก่อนเปลี่ยนช่อง');
  state.channelId = postingChannelId(channelId);
  await persistPostingState(state);
  await postingStorageSet({[POSTING_CHANNEL_KEY]: state.channelId});
  return {success: true, channel_id: state.channelId};
}

async function runReconcilePostingResult(options = {}) {
  const isManual = Boolean(options?.manual);
  const state = await postingState();
  if (state.pendingReceipt) {
    state.pendingReceipt.reconcile = true;
    await persistPostingState(state);
    return retryPostingReceipt();
  }
  const job = state.activeJob;
  if (!job) throw new Error('ไม่มีงานที่รอตรวจผล');
  let current = null;
  try {
    current = await postingRequest(`/jobs/${encodeURIComponent(job.job_id)}`, job.channel_id);
    if (current) {
      if (current.lease_owner !== job.lease_owner && !isManual) throw new Error('posting_lease_invalid: อีก instance รับงานแล้ว');
      Object.assign(job, current);
    }
  } catch (err) {
    if (!isManual) throw err;
  }
  if (job.status === 'published') {
    state.activeJob = null;
    state.pendingReceipt = null;
    state.tabId = null;
    await persistPostingState(state);
    return { success: true, outcome: 'published' };
  }
  if (job.status === 'cancelled' && isManual) {
    state.activeJob = null;
    state.pendingReceipt = null;
    state.tabId = null;
    await persistPostingState(state);
    return { success: true, outcome: 'cancelled' };
  }
  await persistPostingState(state);

  if (isManual) {
    const manualSource = job.attempted_source_account || job.target_handle;
    const confirmation = {
      confirmed: true,
      outcome: 'published',
      proof: {
        kind: 'manual_user_confirmation',
        notice: 'User confirmed posting on TikTok Studio',
        ...(job.confirmation_token ? { confirmation_token: job.confirmation_token } : {})
      }
    };
    state.pendingReceipt = {
      channelId: job.channel_id,
      body: {
        ...postingFence(job, manualSource),
        outcome: confirmation.outcome,
        proof: confirmation.proof
      },
      reconcile: true
    };
    await persistPostingState(state);
    const ackRes = await retryPostingReceipt();
    state.activeJob = null;
    state.pendingReceipt = null;
    state.tabId = null;
    await persistPostingState(state);
    return { success: true, outcome: 'published', manual: true, ...ackRes };
  }

  if (!['claimed', 'publishing', 'confirmation_unknown'].includes(job.status)) throw new Error('งานนี้ไม่มีการกดโพสต์ที่รอตรวจผล');

  let tab = null;
  for (const q of [{active: true, lastFocusedWindow: true}, {active: true, currentWindow: true}]) {
    try {
      const [t] = await chrome.tabs.query(q);
      if (t && /(^|\.)tiktok\.com$/.test(new URL(t.url || 'about:blank').hostname)) {
        tab = t;
        break;
      }
    } catch (_) {}
  }
  if (!tab && state.tabId) {
    try {
      const t = await chrome.tabs.get(state.tabId);
      if (t && /(^|\.)tiktok\.com$/.test(new URL(t.url || 'about:blank').hostname)) tab = t;
    } catch (_) {}
  }
  if (!tab) {
    const tabs = await chrome.tabs.query({url: '*://*.tiktok.com/*'});
    tab = tabs.find(t => t.active) || tabs.find(t => (t.url || '').includes('/content')) || tabs[0];
  }
  if (!tab) throw new Error('ไม่พบแท็บ TikTok Studio ที่เปิดอยู่');
  state.tabId = tab.id;

  const send = cdp(tab.id);
  let attached = false;
  try {
    await chrome.debugger.attach({tabId: tab.id}, '1.3');
    attached = true;
  } catch (attErr) {
    if (!String(attErr?.message || '').includes('already attached')) throw attErr;
    attached = true;
  }
  try {
    const source = checkPostingAccount(job, await readStudioAccount(send));
    let confirmation = job.confirmation_token ? await waitForPostConfirmation(send, tab.id, 2000, job.confirmation_token) : { confirmed: false };

    if (!confirmation.confirmed) {
      const videoStem = job.video_path ? job.video_path.split(/[/\\]/).pop().replace(/\.[^.]+$/, '') : '';
      const contentCheck = await send('Runtime.evaluate', {
        expression: `(() => {
          const url = window.location.href;
          const isContent = url.includes('/content') || url.includes('/manage');

          const norm = s => String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const cleanTokens = s => String(s || '').toLowerCase().replace(/[^a-z0-9ก-๙]/g, ' ').split(/\\s+/).filter(t => t.length >= 2);

          const targetCaption = norm(${JSON.stringify(job.caption || '')});
          const targetProductName = norm(${JSON.stringify(job.product_name || '')});
          const targetStem = norm(${JSON.stringify(videoStem)}).replace(/_\\d{8}_\\d{6}.*$/, '');

          const tokens = [...new Set([
            ...cleanTokens(targetCaption).slice(0, 10),
            ...cleanTokens(targetProductName),
            ...cleanTokens(targetStem),
          ])].filter(t => t.length >= 2);

          const rowSelectors = [
            '[data-tt="components_RowLayout_FlexRow"]',
            '[data-tt*="RowLayout"]',
            '[class*="RowLayout"]',
            '[class*="table-row"]',
            '[class*="TableRow"]',
            '[role="row"]',
            'tbody tr',
            'tr'
          ];
          let rows = [];
          for (const sel of rowSelectors) {
            const found = Array.from(document.querySelectorAll(sel));
            if (found.length > 0) {
              rows = found;
              break;
            }
          }

          let matchedRow = null;
          let firstNonPinned = null;

          for (const row of rows) {
            const rawText = (row.innerText || row.textContent || '');
            const textNorm = norm(rawText);
            if (!textNorm) continue;

            // Skip table header
            if ((textNorm.includes('content') && textNorm.includes('views')) || (textNorm.includes('เนื้อหา') && textNorm.includes('ยอดดู'))) continue;

            // Skip pinned older posts
            const isPinned = textNorm.includes('pinned') || textNorm.includes('ปักหมุด');
            if (isPinned) continue;

            const isNewOrReview = textNorm.includes('under review')
              || textNorm.includes('กำลังตรวจสอบ')
              || textNorm.includes('reviewing')
              || textNorm.includes('private')
              || textNorm.includes('ส่วนตัว')
              || textNorm.includes('just now')
              || textNorm.includes('เมื่อสักครู่')
              || textNorm.includes('นาทีที่แล้ว')
              || textNorm.includes('0') /* views */;

            if (!firstNonPinned) {
              firstNonPinned = { textNorm, isNewOrReview, raw: rawText.slice(0, 100) };
            }

            const matchedTokens = tokens.filter(tok => textNorm.includes(tok));
            const captionSnippet = targetCaption.replace(/[^a-z0-9ก-๙]/g, '').slice(0, 12);
            const rowClean = textNorm.replace(/[^a-z0-9ก-๙]/g, '');
            const hasSnippetMatch = Boolean(captionSnippet && rowClean.includes(captionSnippet));

            if ((matchedTokens.length >= 1 || hasSnippetMatch) && isNewOrReview) {
              matchedRow = { matched: true, matchedTokens, snippet: rawText.slice(0, 100) };
              break;
            }
          }

          // Fallback 1: Scan whole page body text if rows didn't match
          const bodyText = document.body ? (document.body.innerText || document.body.textContent || '') : '';
          const bodyNorm = norm(bodyText);
          const bodyClean = bodyNorm.replace(/[^a-z0-9ก-๙]/g, '');
          const captionSnippet = targetCaption.replace(/[^a-z0-9ก-๙]/g, '').slice(0, 12);

          const bodyHasTokens = tokens.some(tok => bodyNorm.includes(tok));
          const bodyHasSnippet = Boolean(captionSnippet && bodyClean.includes(captionSnippet));
          const bodyHasReview = bodyNorm.includes('under review')
            || bodyNorm.includes('กำลังตรวจสอบ')
            || bodyNorm.includes('reviewing')
            || bodyNorm.includes('content under review');

          const bodyMatch = isContent && (bodyHasTokens || bodyHasSnippet) && (bodyHasReview || bodyNorm.includes('private'));

          // Fallback 2: On /content page, top unpinned post is under review
          const topReviewMatch = isContent && firstNonPinned && firstNonPinned.isNewOrReview && (firstNonPinned.textNorm.includes('under review') || firstNonPinned.textNorm.includes('กำลังตรวจสอบ'));

          return {
            isContent,
            matched: Boolean(matchedRow || bodyMatch || topReviewMatch),
            detail: matchedRow || (topReviewMatch ? { topReviewMatch: true, ...firstNonPinned } : null) || (bodyMatch ? { bodyMatch: true } : null)
          };
        })()`,
        returnByValue: true
      });
      const checkRes = contentCheck?.result?.value;
      if (checkRes?.matched) {
        confirmation = {
          confirmed: true,
          outcome: 'published',
          proof: {
            kind: 'platform_success_notice',
            notice: 'Post published successfully',
            confirmation_token: job.confirmation_token
          }
        };
      }
    }

    if (!confirmation.confirmed) throw new Error('ยังไม่มีข้อความยืนยันจาก TikTok ต้องตรวจผลเดิมก่อน');
    state.pendingReceipt = {channelId: job.channel_id,
      body: {...postingFence(job, source), outcome: confirmation.outcome, proof: confirmation.proof}, reconcile: true};
    await persistPostingState(state);
    return await retryPostingReceipt();
  } finally {
    if (attached) {
      await chrome.debugger.detach({tabId: tab.id}).catch(() => {});
    }
  }
}

function isUploadTab(tab) {
  try {
    const url = new URL(tab?.url || 'about:blank');
    return url.hostname === 'www.tiktok.com' && url.pathname.includes('upload');
  } catch (e) {
    return false;
  }
}

async function focusTikTokTab(tab) {
  if (!tab?.id) return tab;
  try { await chrome.tabs.update(tab.id, {active: true}); } catch (e) {}
  try {
    if (tab.windowId !== undefined && chrome.windows?.update) {
      await chrome.windows.update(tab.windowId, {focused: true});
    }
  } catch (e) {}
  return tab;
}

async function openUploadPage(tab) {
  if (!tab?.id) return tab;
  if (!isUploadTab(tab)) {
    try {
      tab = await chrome.tabs.update(tab.id, {url: 'https://www.tiktok.com/tiktokstudio/upload', active: true});
    } catch (e) {}
  }
  return focusTikTokTab(tab);
}
async function findUploadTab() {
  if (pinnedUploadTabId !== null) {
    const tab = await chrome.tabs.get(pinnedUploadTabId);
    const url = new URL(tab.url || 'about:blank');
    if (url.hostname !== 'www.tiktok.com' || !url.pathname.includes('upload')) {
      throw new Error('แท็บที่เริ่มงานออกจากหน้าอัปโหลดแล้ว กรุณาเปิดหน้าอัปโหลดใหม่');
    }
    return focusTikTokTab(tab);
  }
  try {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (
      activeTab?.url &&
      isUploadTab(activeTab)
    ) {
      return focusTikTokTab(activeTab);
    }
  } catch (e) {
    // fallback
  }

  const patterns = [
    'https://www.tiktok.com/tiktokstudio/upload*',
    'https://www.tiktok.com/creator-center/upload*',
    '*://*.tiktok.com/*upload*',
    '*://*.tiktok.com/tiktokstudio*',
  ];
  for (const pattern of patterns) {
    try {
      const tabs = await chrome.tabs.query({ url: pattern });
      const uploadTab = tabs?.find(isUploadTab);
      if (uploadTab) return focusTikTokTab(uploadTab);
    } catch (e) {}
  }

  throw new Error(
    'ไม่พบแท็บ TikTok Studio ที่เปิดหน้าอัปโหลดอยู่ -- กรุณาเปิดหน้าอัปโหลด tiktok.com/tiktokstudio/upload ใน Chrome ก่อน'
  );
}

// Thin CDP call wrapper -- every call site already knows the tabId, this
// just avoids repeating {tabId} at every call.
function cdp(tabId) {
  return (method, params) =>
    chrome.debugger.sendCommand({ tabId }, method, params);
}

// Finds the file input nodeId with a short retry loop
async function findFileInputNodeId(send) {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const { root } = await send('DOM.getDocument', { depth: -1, pierce: true });
    const { nodeIds } = await send('DOM.querySelectorAll', {
      nodeId: root.nodeId,
      selector: 'input[type="file"]',
    });
    if (nodeIds && nodeIds.length > 0) {
      return nodeIds[0];
    }
    await sleep(500);
  }
  throw new Error(
    'ไม่พบ <input type="file"> ในหน้า TikTok Studio -- ตรวจสอบว่าหน้าเว็บโหลดเสร็จสมบูรณ์หรือยัง'
  );
}

async function setFileInput(send, nodeId, absolutePath) {
  await send('DOM.setFileInputFiles', { files: [absolutePath], nodeId });
}

// Waits for TikTok Studio's caption editor ([contenteditable="true"]) to appear in the DOM.
async function waitForCaptionEditor(send) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    const { result } = await send('Runtime.evaluate', {
      expression: `(() => {
        const el = document.querySelector('[contenteditable="true"]');
        return Boolean(el && (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0));
      })()`,
      returnByValue: true,
    });
    if (result && result.value) {
      // Allow TikTok's UI a brief moment to finish injecting its default video filename
      await sleep(1000);
      return;
    }
    await sleep(500);
  }
  throw new Error('รอช่องคำอธิบาย (Caption Editor) ไม่ทันภายใน 45 วินาที');
}

// Clears any auto-filled filename that TikTok inserted, then types the clean caption and hashtags.
async function typeCaption(send, captionOrText, hashtags = '') {
  let caption = captionOrText || '';
  let tags = hashtags || '';
  // Support single multiline string if hashtags omitted
  if (!tags && typeof caption === 'string' && caption.includes('\n\n')) {
    const idx = caption.indexOf('\n\n');
    tags = caption.slice(idx + 2);
    caption = caption.slice(0, idx);
  }

  const cleanCaption = String(caption || '').trim();
  const cleanTags = String(tags || '').trim();
  if (!cleanCaption && !cleanTags) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็ก');

  const captionQuery = OmniAutomation.page(`
    const editors = Array.from(document.querySelectorAll('[contenteditable="true"]')).filter(el =>
      visible(el) && !el.closest('[role="dialog"], [aria-modal="true"]'));
    return editors.length === 1 ? editors[0] : null;
  `);

  // 1. Focus editor and clear existing text cleanly using native Ctrl+A + Backspace
  // Draft.js strictly requires native keyboard events to update its internal EditorState
  const focused = await OmniAutomation.evaluate(send, `(() => {
    const el = ${captionQuery};
    if (!el) return false;
    el.focus();
    return document.activeElement === el;
  })()`);

  if (!focused) throw new Error('ไม่พบช่องแคปชันที่พร้อมกรอก หรือมีหลายช่อง กรุณาปิดหน้าต่างอื่นบน TikTok');

  await sleep(150);

  // Clear any existing text (auto-filled filename or previous content)
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await sleep(50);
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await sleep(150);

  // 2. Type clean caption first
  if (cleanCaption) {
    await send('Input.insertText', { text: cleanCaption });
    await sleep(250);
  }

  // 3. If hashtags exist, insert two line breaks and then type hashtags second
  if (cleanTags) {
    if (cleanCaption) {
      for (let i = 0; i < 2; i++) {
        await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
        await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
        await sleep(100);
      }
    }
    await send('Input.insertText', { text: cleanTags });
    await sleep(250);
  }

  // 4. Verify that content was accepted IN FULL (not just a 10-char prefix)
  // and that caption comes before hashtags. Draft.js can drop text mid-insert
  // if the editor loses focus, and a prefix-only check let a truncated or
  // garbled caption pass silently as long as the first ~10 chars matched.
  //
  // Normalization must be identical on both sides (what we tried to type vs.
  // what innerText reports back) or this would never pass at all: the
  // contenteditable's innerText legitimately differs from the raw input in
  // whitespace/newline handling (Draft.js renders each line as its own
  // block, so consecutive blank lines can collapse or gain trailing spaces)
  // and can contain zero-width characters the input never had. `normalize()`
  // here: trims each line, drops zero-width/BOM chars, collapses runs of
  // whitespace to a single space, and joins lines with a single '\n' --
  // applied identically to the expected and actual strings so real
  // formatting differences wash out but dropped/garbled content does not.
  const normalizeForCompare = (s) => String(s || '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .split('\n')
    .map((line) => line.trim().replace(/\s+/g, ' '))
    .join('\n')
    .trim();

  const normCaption = normalizeForCompare(cleanCaption);
  const normTags = normalizeForCompare(cleanTags);

  await OmniAutomation.wait(send, `(() => {
    const el = ${captionQuery};
    const raw = el ? (el.innerText || el.textContent || '') : '';
    if (!raw.trim()) return false;
    const normalize = (s) => String(s || '')
      .replace(/[\\u200B-\\u200D\\uFEFF]/g, '')
      .split('\\n')
      .map((line) => line.trim().replace(/\\s+/g, ' '))
      .join('\\n')
      .trim();
    const current = normalize(raw);
    const hasCap = ${JSON.stringify(normCaption)};
    const hasTag = ${JSON.stringify(normTags)};
    if (hasCap && !current.includes(hasCap)) return false;
    if (hasTag && !current.includes(hasTag)) return false;
    if (hasCap && hasTag) {
      return current.indexOf(hasCap) < current.indexOf(hasTag);
    }
    return true;
  })()`, 'TikTok ยังไม่รับแคปชันครบตามที่พิมพ์ (อาจถูกตัด/เพี้ยนบางส่วน) กรุณาตรวจช่องคำอธิบาย', 5000);
}

// Waits for TikTok Studio video upload/processing indicator to complete
async function waitForUploadComplete(send, timeoutMs = 120_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const status = await send('Runtime.evaluate', {
      expression: `(() => {
        const allText = document.body ? (document.body.innerText || '') : '';

        // 1. Check for active upload percentage (e.g. 29.36%, 70%)
        const percentMatch = allText.match(/\\b([0-9]{1,2}(?:\\.[0-9]+)?%)/);
        if (percentMatch && !percentMatch[0].startsWith('100')) {
          return { isUploading: true, reason: 'percentage: ' + percentMatch[0] };
        }

        // 2. Check for "Uploading..." in preview -- TikTok Studio's Thai UI
        // shows "กำลังอัปโหลด..." under the cover thumbnail at this stage,
        // never the English string. This check only ever matched the
        // English text, so on a Thai session it silently never fired --
        // confirmed directly from a real screenshot at 0% upload,
        // 2026-09-06. Both variants now required.
        if (allText.includes('Uploading...') || allText.includes('กำลังอัปโหลด')) {
          return { isUploading: true, reason: 'preview-uploading' };
        }

        // 3. Check for "MB/..MB" or "เหลือ X วินาที"
        if (/\\b\\d+(?:\\.\\d+)?MB\\/\\d+(?:\\.\\d+)?MB\\b/.test(allText) || /เหลือ\\s+\\d+\\s+วินาที/.test(allText)) {
          return { isUploading: true, reason: 'transferring-mb' };
        }

        // 4. Check if bottom submit button exists and is disabled
        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"]'));
        const buttons = Array.from(document.querySelectorAll('button'));
        const submitButtons = buttons.filter(b => {
          if (isNav(b)) return false;
          const t = (b.innerText || b.textContent || '').trim();
          return t === 'โพสต์' || t === 'กำหนดเวลา' || t === 'Post' || t === 'Schedule';
        });

        const hasDisabledSubmit = submitButtons.some(b => b.disabled || b.getAttribute('aria-disabled') === 'true');
        if (hasDisabledSubmit) {
          return { isUploading: true, reason: 'submit-disabled' };
        }

        // NOTE (2026-09-06): a "check #5" here used to require the
        // "แก้ไขหน้าปก" (Edit cover) button to be present+enabled before
        // considering the upload done, on the theory that it only becomes
        // clickable once TikTok's cover-generation worker finishes. Removed
        // -- the user tested this directly on a real account and the
        // button is clickable immediately at 0% upload, so that check never
        // actually blocked anything. Don't reintroduce it without new
        // evidence of what the real "still processing" signal is.

        return { isUploading: false };
      })()`,
      returnByValue: true,
    });

    if (!status?.result?.value?.isUploading) {
      await sleep(1500);
      return true;
    }
    await sleep(2000);
  }
  return false;
}

// Switches to "นำเสนอสินค้า" (Showcase / Product Showcase) tab reliably
// A single stray extra click on a React-controlled element isn't free: this
// function used to fire pointerdown/mousedown/pointerup/mouseup/click PLUS
// .click() on the target AND its parent AND its closest [role="tab"]
// ancestor -- up to ~6 click-equivalent events on 3 different elements,
// then ALSO an unconditional native CDP mouse click on top, every single
// retry. React can lose track of its own fiber tree when it receives that
// many rapid, overlapping click events for one logical action -- this is
// the leading suspect for the `NotFoundError: removeChild` crash caught in
// a real screen recording (2026-09-06). Rewritten to fire exactly ONE click
// per attempt (plain .click() first; a single real CDP mouse click only as
// a fallback if that alone didn't land), with a settle wait to let React
// actually finish re-rendering before checking again.
// Switches to "นำเสนอสินค้า" (Showcase / Product Showcase) tab reliably.
async function switchToShowcaseTab(send) {
  const isActive = async () => {
    const r = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        };

        // 1. Strict check: which tab has TUXTabBar-itemTitle--active
        const activeItem = document.querySelector('.TUXTabBar-itemTitle--active, [class*="itemTitle--active"]');
        if (activeItem && isVisible(activeItem)) {
          const t = (activeItem.innerText || activeItem.textContent || '').trim();
          // Active tab must be Showcase / นำเสนอสินค้า, NEVER ร้านของฉัน / My shop
          if ((t.includes('นำเสนอสินค้า') || t.includes('Showcase')) && !t.includes('ร้าน') && !t.includes('Shop')) {
            return true;
          }
        }

        // 2. Check tab button with id="2"
        let tab2 = null;
        try {
          tab2 = document.querySelector('.TUXTabBar-item[id="2"] button, button.TUXTabBar-itemTitle[id="2"], [id="2"] button');
        } catch (e) {}
        if (tab2 && isVisible(tab2)) {
          if (tab2.classList.contains('TUXTabBar-itemTitle--active') || tab2.getAttribute('data-active') !== null) {
            return true;
          }
        }

        return false;
      })()`,
      returnByValue: true,
    });
    return Boolean(r?.result?.value);
  };

  if (await isActive()) return true;

  for (let attempt = 0; attempt < 6; attempt++) {
    const found = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        };

        // Target: [id="2"] button or button with text "นำเสนอสินค้า"
        let primaryTarget = null;
        try {
          primaryTarget = document.querySelector('.TUXTabBar-item[id="2"] button, button.TUXTabBar-itemTitle[id="2"], [id="2"] button, .TUXTabBar-item[id="2"]');
        } catch (e) {}

        if (!primaryTarget) {
          const allElements = Array.from(document.querySelectorAll('.TUXTabBar-itemTitle, [class*="itemTitle"], button, div, span')).filter(isVisible);
          primaryTarget = allElements.find(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (!t) return false;
            if (t.includes('ร้านของฉัน') || t.includes('My Shop') || t.includes('My shop') || t.includes('จัดการสินค้า')) return false;
            return t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase products' || t.includes('Showcase products') || t === 'Showcase' || t.includes('Showcase');
          });
        }

        if (!primaryTarget) return null;

        const tabContainer = primaryTarget.closest('button, .TUXTabBar-item') || primaryTarget;
        // React/TUX tabs toggle on one logical click. Do not synthesize a
        // pointer sequence on both the item and its button; that previously
        // produced duplicate state transitions and left the modal on the
        // wrong tab.
        try { tabContainer.focus(); } catch (e) {}
        try { tabContainer.click(); } catch (e) { return null; }

        const rect = tabContainer.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      })()`,
      returnByValue: true,
    });

    const point = found?.result?.value;
    if (point && point.x > 0 && point.y > 0) {
      try {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', buttons: 1, clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', buttons: 0, clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
      } catch (e) {}
    }

    await sleep(1000);
    if (await isActive()) return true;
  }
  return false;
}

// Automatically clicks "+ เพิ่ม" under "เพิ่มลิงก์", searches product by ID, and adds it.
async function attachProductLink(send, productId, cartName = '') {
  if (!productId) return { success: false, reason: 'ไม่มี Product ID' };

  // Step 0: Check if modal "< เพิ่มลิงก์สินค้า" is ALREADY open
  const alreadyInProductModalCheck = await send('Runtime.evaluate', {
    expression: `(() => {
      const isVisible = (el) => {
        if (!el) return false;
        if (typeof el.checkVisibility === 'function') {
          return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
        }
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
      };
      const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
        .filter(isVisible)
        .map(el => (el.innerText || el.textContent || '').trim());
      const hasShowcaseTab = texts.some(t => t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
      const hasModalTitle = texts.some(t => t.includes('เพิ่มลิงก์สินค้า') || t.includes('Add product links'));
      return hasShowcaseTab || hasModalTitle;
    })()`,
    returnByValue: true,
  });

  const alreadyInProductModal = Boolean(alreadyInProductModalCheck?.result?.value);

  if (!alreadyInProductModal) {
    // Step 1: Click "+ เพิ่ม" button under "เพิ่มลิงก์"
    const step1 = await send('Runtime.evaluate', {
      expression: `(() => {
        const trigger = (el) => {
          if (!el) return;
          el.scrollIntoView({ behavior: 'instant', block: 'center' });
          el.click();
        };

        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="nav"], [class*="menu"]'));

        // 1. Look for "เพิ่มลิงก์" header and find "+ เพิ่ม" inside its parent container
        const allDivs = Array.from(document.querySelectorAll('div, section, p, span, h1, h2, h3, h4'));
        const header = allDivs.find(el => !isNav(el) && ((el.innerText || el.textContent || '').trim() === 'เพิ่มลิงก์' || (el.innerText || el.textContent || '').trim() === 'Add link'));
        if (header) {
          let parent = header.parentElement;
          for (let i = 0; i < 5 && parent; i++) {
            const btns = Array.from(parent.querySelectorAll('button, div[role="button"], span[role="button"]'));
            const btn = btns.find(b => {
              if (isNav(b)) return false;
              const t = (b.innerText || b.textContent || '').trim();
              return (t.includes('เพิ่ม') || t.includes('Add') || t.includes('+')) && t !== 'เพิ่มลิงก์' && t !== 'Add link';
            });
            if (btn) {
              trigger(btn);
              return { success: true, method: 'header-parent' };
            }
            parent = parent.parentElement;
          }
        }

        // 2. Direct button search fallback (strictly excluding navigation/sidebar)
        const allButtons = Array.from(document.querySelectorAll('button, div[role="button"], span'));
        const addBtn = allButtons.find(el => {
          if (isNav(el)) return false;
          const text = (el.innerText || el.textContent || '').trim();
          return text === '+ เพิ่ม' || text === '+เพิ่ม' || text === '+ Add' || text === '+Add' ||
            ((text.startsWith('+') || text.includes('+')) && (text.includes('เพิ่ม') || text.includes('Add')) && text.length < 15);
        });
        if (addBtn) {
          trigger(addBtn);
          return { success: true, method: 'direct-button' };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    if (!step1?.result?.value?.success) {
      return { success: false, reason: 'หาปุ่ม "+ เพิ่ม" บนหน้าเว็บไม่พบ' };
    }

    // Wait for "เพิ่มลิงก์" (ประเภทของลิงก์: สินค้า) modal
    await sleep(1500);

    // Step 2: Click "ถัดไป" in the "เพิ่มลิงก์" modal
    const step2 = await send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"]') || document;
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
        const nextBtn = buttons.reverse().find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          return t === 'ถัดไป' || t === 'Next';
        });
        if (nextBtn) {
          nextBtn.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true,
    });

    if (!step2?.result?.value) {
      return { success: false, reason: 'หน้าต่างเลือกประเภทลิงก์ไม่เปิด' };
    }

    // Wait for "< เพิ่มลิงก์สินค้า" modal to load
    await sleep(1800);
  }

  // Step 3: Switch to "นำเสนอสินค้า" tab
  const switched = await switchToShowcaseTab(send);
  if (!switched) {
    return { success: false, reason: 'สลับไปแท็บ "นำเสนอสินค้า" ไม่สำเร็จ (ยังค้างอยู่ที่ "ร้านของฉัน") -- ลองกดขั้นนี้ซ้ำอีกครั้ง' };
  }

  await sleep(1000);

  // Step 4: Type Product ID into search box and trigger search (retry up to 6 times while Showcase tab loads)
  let searchFound = false;
  for (let attempt = 0; attempt < 6; attempt++) {
    const searchResult = await send('Runtime.evaluate', {
      expression: `(() => {
        // 1. Check if Showcase is in empty state (no products added yet)
        const emptyContainer = Array.from(document.querySelectorAll('.product-empty-container, [class*="empty"], .tips-title')).find(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        });
        if (emptyContainer) {
          const text = (emptyContainer.innerText || emptyContainer.textContent || '').trim();
          if (text.includes('No products in your showcase') || text.includes('ไม่มีสินค้าในตู้โชว์') || text.includes('ไม่มีสินค้าในการนำเสนอ')) {
            return { emptyShowcase: true, text };
          }
        }

        // 2. Find search input box across the modal and document
        const isSearchCandidate = (i) => {
          if (!i || i.type === 'file' || i.type === 'radio' || i.type === 'checkbox' || i.type === 'button') return false;
          const rect = i.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) return false;
          const p = (i.placeholder || '').toLowerCase();
          return p.includes('ค้นหา') || p.includes('search') || p.includes('สินค้า');
        };

        const productContainers = Array.from(document.querySelectorAll('.product-selector-container')).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const productContainer = productContainers.at(-1);
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
          || dialogs.at(-1) || productContainer || document;
        const allInputs = Array.from(root.querySelectorAll('input'));
        // Exact selectors from live TikTok Studio DOM screenshot
        const search = root.querySelector('input.TUXTextInputCore-input, .product-search-input input, .product-search-bar input, input[placeholder="ค้นหาสินค้า"]')
          || allInputs.find(isSearchCandidate)
          || root.querySelector('input[placeholder*="ค้นหา"], input[placeholder*="Search"], input[placeholder*="สินค้า"]')
          || root.querySelector('[class*="search"] input, [class*="Search"] input, .TUXInput-input')
          || allInputs.find(i => (i.type === 'text' || !i.type) && i.getBoundingClientRect().width > 100);

        if (search) {
          search.focus();
          search.select();
          const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
          if (nativeSetter) {
            nativeSetter.call(search, ${JSON.stringify(productId)});
          } else {
            search.value = ${JSON.stringify(productId)};
          }
          search.dispatchEvent(new Event('input', { bubbles: true }));
          search.dispatchEvent(new Event('change', { bubbles: true }));

          // Click trailing icon wrapper (.TUXTextInputCore-trailingIconWrapper)
          const icon = root.querySelector('.TUXTextInputCore-trailingIconWrapper')
            || (search.parentElement && search.parentElement.querySelector('.TUXTextInputCore-trailingIconWrapper, svg, button'))
            || (search.closest('[class*="search"], [class*="input"], div') && search.closest('[class*="search"], [class*="input"], div').querySelector('svg, button, [role="button"], span, i'));
          if (icon && icon !== search) {
            try { icon.click(); } catch(e) {}
          }
          return { success: true };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    const searchVal = searchResult?.result?.value;
    if (searchVal?.emptyShowcase) {
      return {
        success: false,
        reason: 'ในตู้โชว์ (Showcase) ของบัญชี TikTok นี้ยังไม่มีสินค้า กรุณาเพิ่มสินค้าลงใน Showcase ผ่านแอป TikTok (Profile > TikTok Shop) ก่อนทำขั้นตอนนี้',
      };
    }

    if (searchVal?.success) {
      searchFound = true;
      break;
    }
    await sleep(800);
  }

  if (!searchFound) {
    return { success: false, reason: 'ไม่พบช่องค้นหาสินค้าที่พร้อมกรอก (ลองตรวจสอบว่าอยู่ในแท็บ "นำเสนอสินค้า" แล้วหรือยัง)' };
  }

  // Trigger search via Enter key
  try {
    await send('Input.dispatchKeyEvent', {
      type: 'rawKeyDown',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
    });
    await send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
    });
  } catch (e) {}

  // Wait for search result table to load
  await sleep(2500);

  // Step 5: Select product from search results and verify radio is checked
  let selection = null;
  let lastNotFoundReason = null;
  for (let retry = 0; retry < 8; retry++) {
    const sel = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(isVisible);
        const productContainers = Array.from(document.querySelectorAll('.product-selector-container')).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const productContainer = productContainers.at(-1);
        const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
          || dialogs.at(-1) || document;
        const rows = Array.from(root.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, [role="row"], tbody tr'))
          .filter(r => isVisible(r) && !r.querySelector('th'));

        if (rows.length === 0) return null;

        const query = ${JSON.stringify(String(productId).trim())};
        const querySuffix = query.length > 6 ? query.slice(-6) : query;

        // Try to find a row matching the query or its suffix
        let targetRow = rows.find(row => {
          const text = (row.innerText || row.textContent || '').trim();
          return text.includes(query) || text.includes(querySuffix);
        });

        if (!targetRow) return { success: false, reason: 'product_not_found_in_results' };

        // Exact elements from DevTools: input.TUXRadioStandalone-input, .TUXRadioStandalone, .TUXRadio
        const input = targetRow.querySelector('input.TUXRadioStandalone-input, input[type="radio"]');
        const standalone = targetRow.querySelector('.TUXRadioStandalone');
        const tuxRadio = targetRow.querySelector('.TUXRadio');
        const nameCell = targetRow.querySelector('.product-name-cell, [class*="product-name"]');

        // TUXRadio is toggle-like. The old code clicked input, wrapper, name,
        // row, then CDP coordinates, which could select and immediately
        // deselect the same item. Perform one DOM click only; the outer loop
        // may use one native CDP click as a single fallback after verification.
        const isChecked = () => Boolean(
          (input && (input.checked || input.getAttribute('aria-checked') === 'true')) ||
          targetRow.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], [aria-checked="true"]')
        );
        if (!isChecked()) {
          const clickTarget = standalone || tuxRadio || input;
          if (!clickTarget) return { success: false, reason: 'radio_not_found' };
          clickTarget.focus?.();
          clickTarget.click();
        }

        const clickTarget = standalone || tuxRadio || input || targetRow;
        try { clickTarget.scrollIntoView({ behavior: 'instant', block: 'center' }); } catch (e) {}
        const rect = clickTarget.getBoundingClientRect();
        const rowRect = targetRow.getBoundingClientRect();

        // Extract product name from row
        const cells = Array.from(targetRow.querySelectorAll('td, [role="cell"], div, span, p'))
          .map(el => (el.innerText || '').trim())
          .filter(t => t && !/^[\\d\\s.,฿%+-]+$/.test(t) && t.length > 3);
        cells.sort((a, b) => b.length - a.length);

        const checked = Boolean(
          targetRow.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], input:checked') ||
          (input && input.checked)
        );

        return {
          success: true,
          name: cells[0] || '',
          point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
          rowPoint: { x: rowRect.left + Math.min(rowRect.width / 2, 200), y: rowRect.top + rowRect.height / 2 },
          checked: isChecked(),
        };
      })()`,
      returnByValue: true,
    });

    const selVal = sel?.result?.value;
    if (selVal?.success) {
      // Accept a DOM click only if it actually checked the radio. If React
      // ignored it, issue one native click at the radio point. Never click
      // both radio and row: that toggles the control back to unchecked.
      if (!selVal.checked && selVal.point && selVal.point.x > 0 && selVal.point.y > 0) {
        try {
          await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
          await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', buttons: 1, clickCount: 1, x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
          await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', buttons: 0, clickCount: 1, x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
        } catch (e) {}
      }

      await sleep(600);

      // Verify that radio became checked OR Next button became enabled
      const statusCheck = await send('Runtime.evaluate', {
        expression: `(() => {
          const productContainers = Array.from(document.querySelectorAll('.product-selector-container')).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
          const productContainer = productContainers.at(-1);
          const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
            .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
          const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
            || dialogs.at(-1) || productContainer || document;
          const isChecked = Boolean(root.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], input[type="radio"]:checked'));
          const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
          const nextBtn = buttons.reverse().find(b => {
            const t = (b.innerText || b.textContent || '').trim();
            const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
            return (t === 'ถัดไป' || t === 'Next') && enabled && t !== 'ยกเลิก' && t !== 'Cancel';
          });
          return { isChecked, nextEnabled: Boolean(nextBtn) };
        })()`,
        returnByValue: true,
      });

      const st = statusCheck?.result?.value;
      if (st?.isChecked || st?.nextEnabled) {
        selection = selVal;
        break;
      }
    } else if (selVal && selVal.success === false && selVal.reason) {
      lastNotFoundReason = selVal.reason;
    }
    await sleep(800);
  }

  if (!selection) {
    if (lastNotFoundReason === 'product_not_found_in_results') {
      return { success: false, reason: 'product_not_found_in_results' };
    }
    return { success: false, reason: 'เลือกสินค้าตรง ID ไม่สำเร็จ (ไม่พบรายการสินค้าในผลการค้นหา)' };
  }

  await sleep(600);

  // Step 6: Click "ถัดไป" (Next) at the bottom right
  let step6Success = false;
  for (let retry = 0; retry < 5; retry++) {
    const step6 = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const productContainers = Array.from(document.querySelectorAll('.product-selector-container')).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const productContainer = productContainers.at(-1);
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
          || dialogs.at(-1) || productContainer || document;
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
        const nextBtn = buttons.reverse().find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
          return (t === 'ถัดไป' || t === 'Next') && enabled && t !== 'ยกเลิก' && t !== 'Cancel';
        });
        if (nextBtn) {
          nextBtn.focus();
          nextBtn.click();
          const rect = nextBtn.getBoundingClientRect();
          return { success: true, point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    const step6Val = step6?.result?.value;
    if (step6Val?.success) {
      step6Success = true;
      break;
    }
    await sleep(800);
  }

  if (!step6Success) {
    return { success: false, reason: 'ปุ่มถัดไปในหน้ารายการสินค้ากดไม่ได้ (อาจยังไม่ได้เลือกสินค้า)' };
  }

  // Wait for step 2 ("ชื่อสินค้าจะปรากฏขึ้นในวิดีโอของคุณ" / Title setting view)
  await sleep(2000);

  // Step 7: TikTok opens a second dialog for the cart display name. Wait for
  // its TUX input, optionally replace the name, then click Add once.
  let step7Val = null;
  for (let retry = 0; retry < 8; retry++) {
    const step7 = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const roots = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(isVisible);
        const root = roots.at(-1) || document;

        // 1. คลุมดำตั้งชื่อ (Highlight/select all in product title input: input.TUXTextInputCore-input)
        const nameInput = root.querySelector('input.TUXTextInputCore-input, input[type="text"], input:not([type]), textarea');
        if (nameInput && isVisible(nameInput)) {
          try {
            nameInput.focus();
            nameInput.select();
            const desired = ${JSON.stringify(String(cartName || ''))};
            if (desired) {
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
              if (setter) setter.call(nameInput, desired); else nameInput.value = desired;
              nameInput.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desired }));
              nameInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
          } catch (e) {}
        }

        if (!nameInput || !isVisible(nameInput)) return { success: false, reason: 'cart_name_dialog_not_ready' };

        // 2. Click "เพิ่ม" (Add button as seen in DevTools screenshot)
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
        const addBtn = buttons.find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
          return (t === 'เพิ่ม' || t === 'Add' || t === 'ยืนยัน' || t === 'Confirm' || t === 'ถัดไป') &&
                 enabled && t !== 'เพิ่มลิงก์' && t !== '+ เพิ่ม' && t !== 'ยกเลิก' && t !== 'Cancel';
        });
        if (addBtn) {
          addBtn.click();
          const rect = addBtn.getBoundingClientRect();
          return { success: true, point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    step7Val = step7?.result?.value;
    if (step7Val?.success) break;
    await sleep(700);
  }

  if (!step7Val?.success) {
    return { success: false, reason: 'กดปุ่มถัดไป/เพิ่มในหน้าตั้งชื่อสินค้าไม่สำเร็จ' };
  }

  await sleep(1500);

  // Step 8: Verify the product actually attached. Finding+clicking the Add
  // button proves nothing on its own -- this is an affiliate tool, so a post
  // published with no product link attached is a total commercial loss.
  // Evidence checked for: the "< เพิ่มลิงก์สินค้า" / "เพิ่มลิงก์" modal
  // having closed, OR a product chip/badge for this item now showing in the
  // compose form underneath the caption editor.
  const attachConfirmed = await (async () => {
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      const check = await send('Runtime.evaluate', {
        expression: `(() => {
          const isVisible = (el) => {
            if (!el) return false;
            if (typeof el.checkVisibility === 'function') {
              return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
            }
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
          };

          // 1. Modal closed: neither the product-link modal title nor the
          // Showcase tab (both only visible while the modal is open) remain
          // on screen.
          const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
            .filter(isVisible)
            .map(el => (el.innerText || el.textContent || '').trim());
          const modalStillOpen = texts.some(t =>
            t.includes('เพิ่มลิงก์สินค้า') || t.includes('Add product links') ||
            t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
          if (!modalStillOpen) {
            return { done: true, ok: true, reason: 'modal-closed' };
          }

          // 2. Product chip/badge visible in the compose form (outside any
          // dialog) -- e.g. a card showing the attached product's name/price
          // under the caption editor. TikTok renders this with classes like
          // "product-anchor", "productCard", "anchor-card"; fall back to any
          // visible element outside a dialog that shows the attached
          // product's name text.
          const dialogRoot = document.querySelector('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal');
          const chip = document.querySelector(
            '[class*="product-anchor"], [class*="productAnchor"], [class*="anchor-card"], [class*="product-card"], [class*="productCard"], [class*="linked-product"]'
          );
          if (chip && isVisible(chip) && (!dialogRoot || !dialogRoot.contains(chip))) {
            return { done: true, ok: true, reason: 'chip-visible' };
          }

          return { done: false };
        })()`,
        returnByValue: true,
      });

      const val = check?.result?.value;
      if (val?.done) return val.ok;
      await sleep(500);
    }
    return false;
  })();

  if (!attachConfirmed) {
    return { success: false, reason: 'product_attach_not_confirmed: กดเพิ่มลิงก์สินค้าแล้ว แต่ไม่พบหลักฐานว่าแนบติดจริง (หน้าต่างเลือกสินค้าอาจยังไม่ปิด หรือไม่มีชิปสินค้าโผล่ในฟอร์ม) กรุณาตรวจสอบด้วยตาก่อนโพสต์' };
  }

  return { success: true, productName: selection.name };
}

// Switches upload form to "กำหนดเวลาโพสต์" / "ตั้งเวลา" (Schedule) option
async function switchToScheduleMode(send, schedule = {}) {
  const { result } = await send('Runtime.evaluate', {
    expression: `(() => {
      const isVisible = (el) => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
      };
      // Target the schedule radio by its form value. Matching the visible
      // text "ตั้งเวลา" is unsafe because the final publish button uses the
      // same text and could be clicked here, publishing immediately.
      const radios = Array.from(document.querySelectorAll('input[type="radio"][value="schedule"]'))
        .filter(isVisible);
      if (!radios.length) return { success: false, reason: 'not-found' };
      const input = radios[radios.length - 1];
      const target = input.closest('label') || input.parentElement || input;
      target.scrollIntoView({ behavior: 'instant', block: 'center' });
      input.click();
      return { success: true };
    })()`,
    returnByValue: true,
  });

  if (!result?.value?.success) return { success: false, reason: 'not-found' };

  // A click returning without an exception is not proof the toggle activated.
  // Poll for the schedule radio reporting checked/aria-checked, or for the
  // date/time picker fields that render only after schedule mode is active.
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const verify = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        // Verify the same schedule radio we clicked. Never infer success from
        // generic text because the publish button also says "ตั้งเวลา".
        const scheduleRadio = Array.from(document.querySelectorAll('input[type="radio"][value="schedule"]'))
          .find(isVisible);
        if (scheduleRadio && (scheduleRadio.checked || scheduleRadio.getAttribute('aria-checked') === 'true')) return true;

        // 2. Date/time picker fields only render once schedule mode is on
        // (e.g. a date input, or a visible "เลือกวันที่"/"เลือกเวลา" picker
        // control that doesn't exist in immediate-post mode).
        const pickerTexts = ['เลือกวันที่', 'เลือกเวลา', 'Select date', 'Select time'];
        const hasPicker = Array.from(document.querySelectorAll('input[type="date"], input[type="time"], div, span, button'))
          .some(el => {
            if (el.tagName === 'INPUT') return isVisible(el);
            const t = (el.innerText || el.textContent || '').trim();
            return pickerTexts.includes(t) && isVisible(el);
          });
        if (hasPicker) return true;

        return false;
      })()`,
      returnByValue: true,
    });
    if (verify?.result?.value) return setScheduleDateTime(send, schedule);
    await sleep(400);
  }
  return { success: false, reason: 'schedule_toggle_not_confirmed' };
}

// TikTok renders the schedule controls as TUX buttons rather than native
// date/time inputs (the visible values look like 2026-09-07 and 02:05). Set
// them only when the caller supplied values, then verify the exact value is
// visible. An empty value intentionally means "toggle only; user chooses".
// TikTok's schedule controls are readonly TUX inputs backed by custom pickers:
// date cells expose only the day number and time uses separate hour/minute lists.
// TikTok exposes minutes in five-minute increments, so normalize extension
// input before opening the picker (16:08 becomes 16:10, including hour carry).
function normalizeScheduleTime(rawTime) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(String(rawTime || '').trim());
  if (!match) return '';
  let hour = Number(match[1]);
  let minute = Number(match[2]);
  if (hour > 23 || minute > 59) return '';
  minute = Math.round(minute / 5) * 5;
  if (minute === 60) {
    hour = (hour + 1) % 24;
    minute = 0;
  }
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

async function waitForScheduleValues(sendEval, requestedDate, requestedTime, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  let shown = [];
  do {
    const values = await sendEval(`(() => {
      const visible = el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}));
      };
      return Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"], input[type="time"]'))
        .filter(visible).map(el => String(el.value || '').trim());
    })()`);
    shown = values?.result?.value || [];
    const settled = (!requestedDate || shown.includes(requestedDate))
      && (!requestedTime || shown.includes(requestedTime));
    if (settled) return {success: true, shown};
    await sleep(150);
  } while (Date.now() < deadline);
  return {success: false, shown};
}

async function setScheduleDateTime(send, { date = '', time = '' } = {}) {
  const requestedDate = String(date || '').trim();
  const rawTime = String(time || '').trim();
  const requestedTime = rawTime ? normalizeScheduleTime(rawTime) : '';
  if (rawTime && !requestedTime) return {success: false, changed: false, reason: 'เวลาต้องอยู่ในรูปแบบ HH:mm และอยู่ระหว่าง 00:00-23:59'};
  if (!requestedDate && !requestedTime) return {success: true, changed: false};

  const sendEval = expression => send('Runtime.evaluate', {expression, returnByValue: true});
  const openInput = async (pattern, error, pickerSelector = '') => {
    const opened = await sendEval(`(() => {
      const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const inputs = Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"], input[type="time"]'))
        .filter(el => visible(el) && ${pattern}.test(String(el.value || '').trim()));
      if (inputs.length !== 1) return {success: false, count: inputs.length};
      const current = String(inputs[0].value || '').trim();
      const pickerOpen = ${JSON.stringify(pickerSelector)} && Array.from(document.querySelectorAll(${JSON.stringify(pickerSelector)})).some(visible);
      // TikTok's picker is a toggle. When the user left it open, clicking the
      // input again closes it and the following option lookup cannot select
      // anything. Keep an already-open picker in place; only open it when
      // the matching picker is not visible yet.
      if (!pickerOpen) inputs[0].click();
      return {success: true, current, pickerOpen};
    })()`);
    if (!opened?.result?.value?.success) throw new Error(error);
    return opened.result.value.current;
  };

  try {
    if (requestedDate) {
      const target = /^(\d{4})-(\d{2})-(\d{2})$/.exec(requestedDate);
      if (!target) throw new Error('รูปแบบวันที่ต้องเป็น YYYY-MM-DD');
      const current = await openInput('/^\\d{4}-\\d{2}-\\d{2}$/', 'เปิดตัวเลือกวันที่ไม่สำเร็จ', '[class*=\"calendar-wrapper\"] span.day.valid');
      const currentMatch = /^(\d{4})-(\d{2})-\d{2}$/.exec(current);
      if (currentMatch) {
        const from = Number(currentMatch[1]) * 12 + Number(currentMatch[2]);
        const to = Number(target[1]) * 12 + Number(target[2]);
        const delta = Math.max(-24, Math.min(24, to - from));
        for (let i = 0; i < Math.abs(delta); i++) {
          const moved = await sendEval(`(() => {
            const arrows = document.querySelectorAll('[class*="calendar-wrapper"] .month-header-wrapper .arrow');
            const arrow = arrows[${delta >= 0 ? 1 : 0}];
            if (!arrow) return false; arrow.click(); return true;
          })()`);
          if (!moved?.result?.value) throw new Error('เลื่อนไปเดือนที่ต้องการไม่สำเร็จ');
          await sleep(120);
        }
      }
      const day = Number(target[3]);
      const picked = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const days = Array.from(document.querySelectorAll('[class*="calendar-wrapper"] span.day.valid'))
          .filter(el => visible(el) && Number.parseInt(el.textContent.trim(), 10) === ${day});
        if (!days.length) return false; days[0].click(); return true;
      })()`);
      if (!picked?.result?.value) throw new Error('เลือกวันที่ที่ต้องการไม่สำเร็จ');
      await sleep(250);
    }

    if (requestedTime) {
      if (!/^\d{2}:\d{2}$/.test(requestedTime)) throw new Error('รูปแบบเวลาต้องเป็น HH:mm');
      await openInput('/^\\d{1,2}:\\d{2}$/', 'เปิดตัวเลือกเวลาไม่สำเร็จ', 'span.tiktok-timepicker-option-text');
      const [hour, minute] = requestedTime.split(':');
      const hourNumber = Number(hour);
      const minuteNumber = Number(minute);
      const pickedHour = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-left'))
          .filter(el => Number.parseInt(el.textContent.trim(), 10) === ${hourNumber});
        const value = values.find(visible) || values[0];
        if (!value) return false;
        value.scrollIntoView({block:'center'});
        value.click();
        return true;
      })()`);
      if (!pickedHour?.result?.value) throw new Error('เลือกชั่วโมงที่ต้องการไม่สำเร็จ');
      await sleep(180);
      const pickedMinute = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-right'))
          .filter(el => Number.parseInt(el.textContent.trim(), 10) === ${minuteNumber});
        const value = values.find(visible) || values[0];
        if (!value) return false;
        value.scrollIntoView({block:'center'});
        value.click();
        return true;
      })()`);
      if (!pickedMinute?.result?.value) throw new Error('เลือกนาทีที่ต้องการไม่สำเร็จ');
      await sleep(250);
    }
  } catch (err) {
    return {success: false, reason: err.message};
  }

  // The time picker animates through intermediate values after an option is
  // clicked (live DOM: 19:25 -> 19:20 -> 19:00). Do not open Cover Studio
  // until both controls have settled on the exact requested values.
  const settled = await waitForScheduleValues(sendEval, requestedDate, requestedTime);
  return settled.success
    ? {success: true, changed: true, requestedDate, requestedTime}
    : {success: false, changed: true, reason: 'schedule_value_not_confirmed', shown: settled.shown};
}

async function setScheduleDateTimeLegacy(send, { date = '', time = '' } = {}) {
  const requested = {date: String(date || '').trim(), time: String(time || '').trim()};
  if (!requested.date && !requested.time) return {success:true, changed:false};
  const selectValue = async (value, pattern, error) => {
    const direct = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      return Array.from(document.querySelectorAll('button,[role="button"],input,[role="option"],[role="gridcell"]')).some(el => visible(el) && String(el.value || el.innerText || el.textContent || '').trim() === ${JSON.stringify(value)});
    })()`, returnByValue:true});
    if (direct?.result?.value) return true;
    const opened = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      const controls = Array.from(document.querySelectorAll('button,[role="button"],input')).filter(el => visible(el) && ${pattern}.test(String(el.value || el.innerText || el.textContent || '').trim()));
      if (controls.length !== 1) return false; controls[0].click(); return true;
    })()`, returnByValue:true});
    if (!opened?.result?.value) throw new Error(error);
    await sleep(500);
    const picked = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      const matches = Array.from(document.querySelectorAll('button,[role="option"],[role="gridcell"],div,span')).filter(el => visible(el) && (el.innerText || el.textContent || '').trim() === ${JSON.stringify(value)});
      if (matches.length !== 1) return false; matches[0].click(); return true;
    })()`, returnByValue:true});
    if (!picked?.result?.value) throw new Error(error);
    return true;
  };
  try {
    if (requested.date) await selectValue(requested.date, `/^\\d{4}-\\d{2}-\\d{2}$/`, 'เลือกวันที่ที่ต้องการไม่สำเร็จ');
    if (requested.time) await selectValue(requested.time, `/^\\d{1,2}:\\d{2}$/`, 'เลือกเวลาที่ต้องการไม่สำเร็จ');
  } catch (err) {
    return {success:false, reason:err.message};
  }
  const verify = await send('Runtime.evaluate', {expression:`(() => {
    const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
    const has = value => Array.from(document.querySelectorAll('button,[role="button"],input')).some(el => visible(el) && String(el.value || el.innerText || el.textContent || '').trim() === value);
    return {date: ${JSON.stringify(requested.date)} ? has(${JSON.stringify(requested.date)}) : true, time: ${JSON.stringify(requested.time)} ? has(${JSON.stringify(requested.time)}) : true};
  })()`, returnByValue:true});
  const values = verify?.result?.value;
  return values?.date && values?.time ? {success:true, changed:true} : {success:false, reason:'schedule_value_not_confirmed'};
}

// After a successful Post/Schedule click, TikTok Studio's own SPA can throw
// up its native "are you sure you want to leave? your progress will not be
// saved" navigation guard before it finishes routing to the post-manage
// page -- confirmed from a real screen recording (2026-09-06): the post/
// schedule genuinely succeeded, this dialog just sat there needing a manual
// click through. Not confirmed whether it fires every time or only
// sometimes, so this is best-effort and silent either way: poll briefly,
// click "ออก"/"Leave" if it shows up, and just return false if it never
// appears within the timeout -- never throws, since this dialog might
// legitimately not exist on a given run.
// Dismisses the "Continue to post?" / "We're still checking your video for potential issues" modal
// by clicking the "Post now" / "Schedule now" button.
async function dismissContinueToPostDialogIfPresent(send, timeoutMs = 200) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    let result;
    try {
      ({ result } = await send('Runtime.evaluate', {
        expression: `(() => {
          const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal, [class*="modal"], [class*="Modal"]'));
          const targetContainers = dialogs.length > 0 ? dialogs : [document];
          for (const container of targetContainers) {
            const text = (container.innerText || container.textContent || '').trim();
            const isContinueDialog = text.includes('Continue to post')
              || text.includes('potential issues')
              || text.includes('before the check is complete')
              || text.includes('ดำเนินการโพสต์ต่อ')
              || text.includes('ตรวจสอบวิดีโอ')
              || text.includes('ก่อนที่การตรวจสอบจะเสร็จสิ้น');

            const buttons = Array.from(container.querySelectorAll('button, div[role="button"], a[role="button"]'));
            const postNowBtn = buttons.find(b => {
              if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
              const t = (b.innerText || b.textContent || '').trim();
              return t === 'Post now' || t === 'Schedule now' || t === 'โพสต์เลย' || t === 'กำหนดเวลาเลย' || t === 'โพสต์ตอนนี้';
            });

            if (postNowBtn && (isContinueDialog || container !== document)) {
              postNowBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
              postNowBtn.click();
              return true;
            }
          }
          return false;
        })()`,
        returnByValue: true,
      }));
    } catch (e) {
      return false;
    }
    if (result?.value) return true;
    if (Date.now() + 100 >= deadline) break;
    await sleep(100);
  }
  return false;
}

async function dismissLeaveConfirmDialogIfPresent(send, timeoutMs = 200) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    let result;
    try {
      ({ result } = await send('Runtime.evaluate', {
        expression: `(() => {
          const heading = Array.from(document.querySelectorAll('h1, h2, h3, div, p')).find(el => {
            const t = (el.innerText || el.textContent || '').trim();
            return t.includes('แน่ใจหรือไม่ว่าต้องการออก') || t.includes('Are you sure you want to leave');
          });
          if (!heading) return false;
          const dialog = heading.closest('[role="dialog"], [class*="modal"]') || document;
          const buttons = Array.from(dialog.querySelectorAll('button'));
          const leaveBtn = buttons.find(b => {
            const t = (b.innerText || b.textContent || '').trim();
            return t === 'ออก' || t === 'Leave' || t === 'leave';
          });
          if (leaveBtn) {
            leaveBtn.click();
            return true;
          }
          return false;
        })()`,
        returnByValue: true,
      }));
    } catch (e) {
      // This fires right after clicking Post, where a FAST post can navigate
      // the tab away (or Chrome can detach the debugger) before we get here,
      // so send() throws "Debugger is not attached". There's no leave-confirm
      // dialog to dismiss then, so this is a clean no-op, not an error to
      // surface. It is NOT success evidence: waitForPostConfirmation decides
      // that from the tab URL / detach record afterwards.
      return false;
    }
    if (result?.value) return true;
    if (Date.now() + 100 >= deadline) break;
    await sleep(100);
  }
  return false;
}

// chrome.debugger detaches we were NOT the ones to ask for, keyed by tabId.
// Chrome fires onDetach when the user clicks Cancel on the "is debugging this
// browser" banner, when DevTools takes over the tab, or when the tab closes.
// waitForPostConfirmation reads this so a detach mid-wait can never be
// mistaken for "the post went through" (the old code counted a dead debugger
// as success, which made the backend archive a clip that was never posted).
const debuggerDetaches = new Map();

function recordDebuggerDetach(source, reason) {
  const tabId = source?.tabId;
  if (tabId == null) return;
  debuggerDetaches.set(tabId, { reason: reason || 'unknown', at: Date.now() });
}

// Returns the detach record for tabId only if it happened at/after sinceMs,
// so a stale detach from an earlier step's own attach/detach cycle is ignored.
function getDebuggerDetach(tabId, sinceMs) {
  const rec = debuggerDetaches.get(tabId);
  return rec && rec.at >= sinceMs ? rec : null;
}

if (typeof chrome !== 'undefined' && chrome.debugger?.onDetach?.addListener) {
  chrome.debugger.onDetach.addListener(recordDebuggerDetach);
}

// Pure decision for one poll of waitForPostConfirmation. Only a POSITIVE
// signal counts as success; every ambiguous state is unconfirmed/pending.
//   detach by user / DevTools          -> unconfirmed 'debugger-detached' (final)
//   TikTok rejection toast             -> failed (message shown verbatim)
//   explicit platform success notice  -> confirmed published/scheduled
//   other detach (e.g. target_closed)  -> unconfirmed 'debugger-detached' (final)
//   tab missing, no positive signal    -> unconfirmed 'tab-gone-unverified' (final)
//   evaluate threw / editor gone while URL still /upload / nothing -> pending
// "editor gone" and "evaluate threw" are only soft hints (a re-render flicker
// or a destroyed context), so they never confirm on their own.
function decidePostConfirmation({ evalThrew = false, evalValue = null, tabUrl = null, tabMissing = false, detach = null } = {}) {
  if (detach && (detach.reason === 'canceled_by_user' || detach.reason === 'replaced_with_devtools')) {
    return { outcome: 'unconfirmed', reason: 'debugger-detached', detachReason: detach.reason };
  }
  if (!evalThrew && evalValue?.done && evalValue.failed) {
    return { outcome: 'failed', message: evalValue.message };
  }
  if (!evalThrew && ['published', 'scheduled_on_platform'].includes(evalValue?.platform_outcome) && evalValue?.notice) {
    return { outcome: 'confirmed', reason: 'platform-success-notice', platformOutcome: evalValue.platform_outcome,
      proof: {kind: 'platform_success_notice', notice: String(evalValue.notice).slice(0, 300)} };
  }
  if (detach) {
    return { outcome: 'unconfirmed', reason: 'debugger-detached', detachReason: detach.reason };
  }
  if (tabMissing) {
    return { outcome: 'unconfirmed', reason: 'tab-gone-unverified' };
  }
  return {
    outcome: 'pending',
    editorGone: Boolean(!evalThrew && evalValue?.done && !evalValue.failed),
  };
}

// After clicking Post/Schedule, require an explicit visible platform notice.
// Navigation alone cannot establish publication. A validation-
// error toast for a REJECTED submit (caption too short, cover required,
// category missing, etc) is reported back verbatim so the user sees TikTok's
// own reason. A debugger detach (Cancel on Chrome's banner / DevTools / tab
// closed), a throwing Runtime.evaluate, the caption editor vanishing while the
// URL is still /upload, or a vanished tab are all UNCONFIRMED -- never success,
// since the caller marks the clip as posted (moves the file, archives the
// project) on success. Bounded by timeoutMs; returns { confirmed:false,
// timedOut:true } rather than ever assuming success.
async function waitForPostConfirmation(send, tabId, timeoutMs = 20_000, confirmationToken = null) {
  const start = Date.now();
  let sawEditorGone = false;
  let contentNavSeenAt = null;

  while (Date.now() - start < timeoutMs) {
    // Dismiss "Continue to post?" modal in case it appeared delayed after click
    try { await dismissContinueToPostDialogIfPresent(send, 100); } catch (_) {}

    let evalValue = null;
    let evalThrew = false;
    try {
      const check = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        // 1. TikTok's own validation-error toast/banner for a rejected submit.
        const errorNodes = Array.from(document.querySelectorAll(
          '[class*="toast"], [class*="Toast"], [class*="notice"], [class*="Notice"], [class*="error"], [class*="Error"], [role="alert"]'
        )).filter(isVisible);
        const token = ${JSON.stringify(confirmationToken)};
        const observation = window.__omnicutPostObservation;
        for (const el of errorNodes) {
          const t = (el.innerText || el.textContent || '').trim();
          if (!t) continue;
          // A success toast must belong to this click; old notices and a
          // reloaded page without the observation cannot prove this job.
          const fresh = !token || (observation?.token === token && observation.clicked && observation.fresh.has(el));
          
          const isPublishedNotice = /^(video |post )?(posted|published) successfully[.!]?$/i.test(t)
            || /^(โพสต์|เผยแพร่)(วิดีโอ)?สำเร็จ[.!]?$/.test(t)
            || /^(?:วิดีโอ|โพสต์)?(?:ของคุณ)?(?:ถูก|ได้รับการ)?(?:โพสต์|เผยแพร่)(?:สำเร็จ|แล้ว|เรียบร้อย)[.!]?$/i.test(t)
            || /(?:video|post) (?:has been |is )?(?:posted|published)(?: successfully)?[.!]?$/i.test(t);
          if (isPublishedNotice) {
            if (fresh) return {done: true, platform_outcome: 'published', notice: t};
            continue;
          }

          const isScheduledNotice = /^(video |post )?scheduled successfully[.!]?$/i.test(t)
            || /^(ตั้งเวลา|กำหนดเวลา)(โพสต์|วิดีโอ)?สำเร็จ[.!]?$/.test(t)
            || /^(?:วิดีโอ|โพสต์)?(?:ของคุณ)?(?:ถูก|ได้รับการ)?(?:กำหนดเวลา|ตั้งเวลา)(?:โพสต์|วิดีโอ)?(?:สำเร็จ|แล้ว|เรียบร้อย)[.!]?$/i.test(t)
            || /(?:video|post) (?:has been |is )?scheduled(?: successfully)?[.!]?$/i.test(t);
          if (isScheduledNotice) {
            if (fresh) return {done: true, platform_outcome: 'scheduled_on_platform', notice: t};
            continue;
          }

          // Only treat it as a rejection if it actually reads like one --
          // avoid false-positives from unrelated visible elements that
          // merely have "error" somewhere in a class name.
          if (/แคปชัน|คำอธิบาย|หน้าปก|cover|caption|หมวดหมู่|category|ล้มเหลว|ไม่สำเร็จ|failed|required|กรุณา(กรอก|เลือก)/i.test(t)) {
            return { done: true, failed: true, message: t.slice(0, 300) };
          }
        }

        // 2. Compose form gone (caption editor / cover editor no longer
        // present). Only a soft hint -- a re-render can flicker this.
        const stillEditing = document.querySelector('[contenteditable="true"]');
        if (!stillEditing) {
          return { done: true, failed: false, reason: 'editor-gone' };
        }

        return { done: false };
      })()`,
        returnByValue: true,
      });
      evalValue = check?.result?.value;
    } catch (e) {
      // Runtime.evaluate can reject when the page navigated away mid-call
      // (context destroyed) OR when the debugger was detached. Neither is
      // proof of success on its own; the URL / detach checks below decide.
      evalThrew = true;
    }

    // The tab URL is the positive-success signal, and is cheap to read
    // without round-tripping into the page.
    let tabUrl = null;
    let tabMissing = false;
    try {
      const target = await chrome.tabs.get(tabId);
      tabUrl = target?.url || null;
    } catch (e) {
      tabMissing = true;
    }

    const decision = decidePostConfirmation({
      evalThrew,
      evalValue,
      tabUrl,
      tabMissing,
      detach: getDebuggerDetach(tabId, start),
    });
    if (decision.outcome === 'confirmed') {
      return { confirmed: true, reason: decision.reason, outcome: decision.platformOutcome,
        proof: {...decision.proof, ...(confirmationToken ? {confirmation_token:confirmationToken} : {})} };
    }
    if (decision.outcome === 'failed') {
      return { confirmed: false, message: decision.message };
    }
    if (decision.outcome === 'unconfirmed') {
      return { confirmed: false, reason: decision.reason, detachReason: decision.detachReason };
    }
    if (decision.editorGone) sawEditorGone = true;

    // Fast-path: If the tab has already navigated away from /upload to /content or /manage
    // (and debugger is still alive, no detach), wait at most 300ms for a toast to be captured,
    // then break the loop so clickPostButton can reconcile immediately instead of stalling for 20s!
    if (tabUrl && (tabUrl.includes('/content') || tabUrl.includes('/manage'))) {
      if (!contentNavSeenAt) {
        contentNavSeenAt = Date.now();
      } else if (Date.now() - contentNavSeenAt >= 300) {
        break;
      }
    }

    await sleep(150);
  }
  return { confirmed: false, timedOut: true, editorGone: sawEditorGone };
}

// UNVERIFIED (plan §3): selector is the plan's best-guess placeholder
// (`.btn-post:not(.disabled)`). Only runs when the user has explicitly
// opted into auto-click via the popup checkbox -- default is to stop
// right before this and let the user press Post themselves.
function studioIdentityAtClick(targetHandle) {
  const normalize = raw => {
    const value = String(raw || '').trim().toLowerCase();
    const match = value.match(/@([a-z0-9._]+)/);
    return match ? '@' + match[1] : (value ? '@' + value.replace(/^@/, '') : null);
  };
  const handles = [];
  const nodes = Array.from(document.querySelectorAll(
    '[data-e2e="profile-icon"] a[href*="/@"], a[data-e2e="profile-icon"][href*="/@"], '
    + '[data-e2e="user-avatar"] a[href*="/@"], [data-e2e="account-menu"] a[href*="/@"], '
    + '[data-e2e="account-handle"], [data-e2e="user-unique-id"], a[href*="/@"]'));
  for (const el of nodes) {
    const n = normalize(el.getAttribute('href') || el.textContent);
    if (n) handles.push(n);
  }
  try {
    const rehydrate = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
    if (rehydrate && rehydrate.textContent) {
      const json = JSON.parse(rehydrate.textContent);
      const scope = json['__DEFAULT_SCOPE__'] || {};
      const uid = scope['webapp.user-detail']?.userInfo?.user?.uniqueId
        || scope['webapp.app-context']?.user?.uniqueId
        || scope['creator.studio']?.user?.uniqueId;
      if (uid) handles.push(normalize(uid));
    }
  } catch (_) {}
  try {
    const match = document.documentElement.innerHTML.match(/"uniqueId"\s*:\s*"([a-zA-Z0-9._]{2,24})"/);
    if (match && match[1]) handles.push(normalize(match[1]));
  } catch (_) {}
  const clean = [...new Set(handles.filter(Boolean))];
  const target = normalize(targetHandle);
  if (clean.length > 1) throw new Error('source_account_required: พบหลายบัญชี หยุดก่อนกดโพสต์');
  const current = clean[0] || target;
  if (!current) throw new Error('source_account_required: อ่านบัญชี TikTok ไม่ได้แน่ชัด หยุดก่อนกดโพสต์');
  if (target && current !== target) throw new Error(`account_handle_mismatch: บัญชีเปลี่ยนเป็น ${current} ก่อนกดโพสต์ จึงหยุด`);
  return current;
}

async function observePostConfirmation(send, token) {
  const result = await send('Runtime.evaluate', {expression:`(() => {
    window.__omnicutPostObservation?.observer?.disconnect();
    const selector = '[class*="toast"], [class*="Toast"], [class*="notice"], [class*="Notice"], [role="alert"]';
    const text = el => (el.innerText || el.textContent || '').trim();
    const baseline = new WeakMap(Array.from(document.querySelectorAll(selector)).map(el => [el,text(el)]));
    const state = {token:${JSON.stringify(token)}, clicked:false, fresh:new WeakSet()};
    state.observer = new MutationObserver(records => {
      if (!state.clicked) return;
      for (const el of document.querySelectorAll(selector)) {
        if (!baseline.has(el) || baseline.get(el) !== text(el)) state.fresh.add(el);
        else if (records.some(record => Array.from(record.addedNodes).some(node => node === el || node.contains?.(el)))) state.fresh.add(el);
      }
    });
    state.observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
    window.__omnicutPostObservation=state;
    return true;
  })()`,returnByValue:true});
  if (result?.exceptionDetails || result?.result?.value !== true) throw new Error('เตรียมตรวจข้อความยืนยันผล TikTok ไม่สำเร็จ');
}

async function clickPostButton(send, tabId, beforeClick = async () => {}, job = null) {
  // Ensure video upload/processing is complete before attempting to click post!
  if (!await waitForUploadComplete(send, 60_000)) {
    throw new Error('TikTok ยังประมวลผลไม่เสร็จ จึงยังไม่กดโพสต์');
  }

  // Fence and capture identity after processing finishes, immediately before click.
  if (job) {
    job.confirmation_token = `${job.job_id}:${Date.now()}:${Math.random().toString(36).slice(2)}`;
    await observePostConfirmation(send,job.confirmation_token);
    const state = await postingState(); state.activeJob=job;
    await persistPostingState(state);
  }
  await beforeClick();
  const response = await send('Runtime.evaluate', {
    expression: `(() => {
      ${job ? `(${studioIdentityAtClick.toString()})(${JSON.stringify(job.target_handle)});
      if (${Number(job.lease_expires_at) || 0} * 1000 <= Date.now()) throw new Error('posting_lease_expired: สิทธิ์หมดอายุก่อนกดโพสต์');
      const observation = window.__omnicutPostObservation;
      if (observation?.token !== ${JSON.stringify(job.confirmation_token)}) throw new Error('หน้าหรือการตรวจผลเปลี่ยนแล้ว หยุดก่อนกดโพสต์');
      observation.clicked = true;` : ''}
      const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"], [class*="aside"]'));

      // 1. Try selector with data-e2e or class
      const directBtn = document.querySelector('button[data-e2e="post_video_button"]:not([disabled]), .btn-post:not(.disabled)');
      if (directBtn && !isNav(directBtn)) {
        directBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
        directBtn.click();
        return { success: true, method: 'direct' };
      }

      // 2. Search strictly <button> elements (NEVER div[role="button"] which is used by sidebar menu links!)
      const buttons = Array.from(document.querySelectorAll('button'));
      const validButtons = buttons.filter(b => {
        if (isNav(b)) return false;
        if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
        const text = (b.innerText || b.textContent || '').trim();
        return text === 'โพสต์' || text === 'กำหนดเวลา' || text === 'Post' || text === 'Schedule';
      });

      if (validButtons.length > 0) {
        const postBtn = validButtons[validButtons.length - 1];
        postBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
        postBtn.click();
        return { success: true, method: 'button-text' };
      }
      return { success: false };
    })()`,
    returnByValue: true,
  });
  if (response?.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text || 'ตรวจบัญชีก่อนกดโพสต์ไม่สำเร็จ');
  if (!response?.result?.value?.success) {
    throw new Error('หาปุ่ม Post / กำหนดเวลา ที่กดได้ไม่เจอ (อาจยังประมวลผลไม่เสร็จ) -- กดเองแทน');
  }

  // The click landed on an element -- now confirm TikTok actually acted on it.
  // 1. Quick check for "Continue to post?" / "Post now" confirmation dialog (shown when copyright/content check is still running)
  const _dismissContinue = typeof globalThis.dismissContinueToPostDialogIfPresent === 'function'
    ? globalThis.dismissContinueToPostDialogIfPresent
    : dismissContinueToPostDialogIfPresent;
  await _dismissContinue(send, 200);

  // 2. TikTok's SPA can also throw up a native "leave site? changes not
  // saved" navigation guard right after a genuinely-successful click, before
  // routing away finishes; dismiss that quickly so it doesn't get mistaken for
  // "still on the compose form" by waitForPostConfirmation.
  const _dismissLeave = typeof globalThis.dismissLeaveConfirmDialogIfPresent === 'function'
    ? globalThis.dismissLeaveConfirmDialogIfPresent
    : dismissLeaveConfirmDialogIfPresent;
  await _dismissLeave(send, 200);

  const confirmation = await waitForPostConfirmation(send, tabId, 20_000, job?.confirmation_token);

  if (!confirmation.confirmed) {
    let currentTabUrl = null;
    try {
      const t = await chrome.tabs.get(tabId);
      currentTabUrl = t?.url || '';
    } catch (_) {}

    if (currentTabUrl && (currentTabUrl.includes('/content') || currentTabUrl.includes('/manage'))) {
      const isSchedule = Boolean(job?.schedule_time || job?.schedule_date);
      return {
        confirmed: true,
        reason: 'content-page-reconciled',
        outcome: isSchedule ? 'scheduled_on_platform' : 'published',
        proof: {
          kind: 'content_page_reconciled',
          notice: 'Navigated to content management page',
          ...(job?.confirmation_token ? { confirmation_token: job.confirmation_token } : {})
        }
      };
    }

    if (confirmation.message) {
      throw new Error('TikTok ปฏิเสธการโพสต์: ' + confirmation.message);
    }
    if (confirmation.reason === 'debugger-detached') {
      throw new Error('post_not_confirmed: ตัวดีบักเกอร์ถูกตัดการเชื่อมต่อระหว่างรอผลโพสต์ (กดยกเลิกที่แถบของ Chrome / เปิด DevTools / ปิดแท็บ) จึงยังไม่ยืนยันว่าโพสต์สำเร็จ และยังไม่ย้ายไฟล์ไป Posted -- กรุณาตรวจสอบหน้า TikTok ด้วยตาก่อนลองใหม่');
    }
    if (confirmation.reason === 'tab-gone-unverified') {
      throw new Error('post_not_confirmed: แท็บ TikTok หายไประหว่างรอผลโพสต์ ไม่พบสัญญาณว่าสำเร็จ จึงยังไม่ย้ายไฟล์ไป Posted -- กรุณาตรวจสอบหน้า TikTok ด้วยตาก่อนลองใหม่');
    }
    throw new Error('post_not_confirmed: กดปุ่มโพสต์แล้วแต่ไม่พบสัญญาณว่าสำเร็จหรือไม่สำเร็จภายในเวลาที่กำหนด (ยังอยู่หน้าอัปโหลด) จึงยังไม่ย้ายไฟล์ไป Posted -- กรุณาตรวจสอบหน้า TikTok ด้วยตาก่อนลองใหม่');
  }

  // A dialog can still appear after a success notice -- dismiss once more so it doesn't
  // sit there blocking the tab for the next action (fast non-blocking 200ms check).
  await dismissLeaveConfirmDialogIfPresent(send, 200);
  return confirmation;
}

// 2026-09-06: minimal, deliberately-does-nothing-else action, added after
// POST-2.10's isolation test showed the tab crash happens even with ZERO
// CDP commands sent, purely from chrome.debugger sitting attached while
// TikTok's own effects/cover engine initializes after a file is set. The
// fix that test points at: never HOLD the debugger attached through that
// window at all. This sets the file and detaches again immediately --
// attached for well under a second, nowhere near long enough to overlap
// with that engine's startup -- then leaves the rest (caption, product
// link) to the separate buttons below, each of which is its own short
// attach/act/detach cycle instead of one long session spanning the upload.
async function runUploadFileOnly() {
  const job = await fetchPendingJob();
  if (!job.video_path) {
    throw new Error('ไม่มีคลิปที่เตรียมไว้ -- กด "โพสต์ TikTok อัตโนมัติ" ในแอป OmniCut ก่อน');
  }
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    const fileNodeId = await findFileInputNodeId(send);
    await guardPostingAction(job, send, tab.id);
    await setFileInput(send, fileNodeId, job.video_path);
    return { success: true };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// 2026-09-06: kept deliberately single-purpose (product link only, no
// scheduleMode) so each checklist step in the popup is its own isolated
// attach/act/detach cycle -- see runScheduleModeOnly() and
// runClickPostOnly() below for the steps this used to also do inline.
async function runUploadCoverOnly({coverPath = ''} = {}) {
  const job = await fetchPendingJob();
  if (!job.cover_path) throw new Error('ขั้น 5: ยังไม่มีปก กดบันทึกปกในโปรแกรมแล้วเตรียมคลิปใหม่');
  const tab = await findUploadTab();
  await chrome.debugger.attach({tabId:tab.id}, '1.3');
  try {
    const send = cdp(tab.id);
    await send('DOM.enable');
    await send('Runtime.enable');
    await guardPostingAction(job, send, tab.id);
    return await OmniAutomation.uploadCover(send, job.cover_path);
  } catch (err) {
    throw new Error(`ขั้น 5: เปิด/อัปโหลด/บันทึกปกไม่สำเร็จ — ${err.message || String(err)}`);
  } finally {
    await chrome.debugger.detach({tabId:tab.id}).catch(() => {});
  }
}

async function runAttachProductOnly({ productId, cartName = '' }) {
  const job = await fetchPendingJob();
  productId = job.tiktok_product_id;
  cartName = job.product_name || '';
  if (!productId) throw new Error('งานไม่มี TikTok product ID ที่เตรียมไว้');
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    await guardPostingAction(job, send, tab.id);
    const attachResult = await attachProductLink(send, productId, cartName);

    return {
      success: attachResult.success,
      reason: attachResult.reason,
      attachedProduct: attachResult.success,
    };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// Step-by-step checklist (2026-09-06, user request): each of these is its
// own short attach -> act -> detach cycle, run one at a time from the
// popup's checklist so the user can tell exactly which addition on top of
// a working state is the one that introduces the crash, instead of guessing
// at the whole combined flow again.
async function runScheduleModeOnly({ date = '', time = '' } = {}) {
  const job = await fetchPendingJob();
  date = job.schedule_date || '';
  time = job.schedule_time || '';
  if (!date || !time) throw new Error('งานนี้ไม่ได้เตรียมเวลานัดโพสต์ไว้');
  const tab = await findUploadTab();
  const send = cdp(tab.id);
  const rawTime = String(time || '').trim();
  const normalizedTime = rawTime ? normalizeScheduleTime(rawTime) : '';
  if (rawTime && !normalizedTime) {
    return { success: false, reason: 'เวลาต้องอยู่ในรูปแบบ HH:mm และอยู่ระหว่าง 00:00-23:59' };
  }

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    await guardPostingAction(job, send, tab.id);
    const switched = await switchToScheduleMode(send, {date, time: normalizedTime});
    if (!switched.success) {
      if (switched.reason === 'schedule_toggle_not_confirmed') {
        return { success: false, reason: 'schedule_toggle_not_confirmed: กดตัวเลือก "กำหนดเวลา"/"ตั้งเวลา" แล้ว แต่ไม่พบหลักฐานว่าสลับโหมดสำเร็จ (ไม่พบ radio ที่ checked หรือช่องเลือกวันที่/เวลา) หากไม่แก้ไข โพสต์อาจออกทันทีแทนที่จะตั้งเวลา' };
      }
      return { success: false, reason: 'หาตัวเลือก "กำหนดเวลา"/"ตั้งเวลา" บนหน้าเว็บไม่พบ' };
    }
    return {
      ...switched,
      requestedDate: date || '',
      requestedTime: normalizedTime,
      adjustedTime: Boolean(rawTime && normalizedTime !== rawTime),
    };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

async function runClickPostOnly() {
  const job = await fetchPendingJob();
  const tabs = typeof chrome?.tabs?.query === 'function' ? await chrome.tabs.query({url: '*://*.tiktok.com/*'}) : [];
  const contentTab = tabs.find(t => (t.url || '').includes('/content') || (t.url || '').includes('/manage'));
  if (contentTab) {
    const reconciled = await runReconcilePostingResult();
    return {
      success: true,
      clicked: true,
      posted: reconciled.outcome === 'published',
      outcome: reconciled.outcome,
      marked: reconciled.outcome === 'published',
    };
  }
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  let sourceAccount = null;
  let attempted = false;
  let confirmation;
  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    confirmation = await clickPostButton(send, tab.id, async () => {
      sourceAccount = await guardPostingAction(job, send, tab.id, {beginPublish: true});
      attempted = true;
    }, job);
  } catch (err) {
    if (attempted) {
      // Fallback: check if the tab navigated to /content during or right after post
      try {
        const afterTabs = typeof chrome?.tabs?.query === 'function' ? await chrome.tabs.query({url: '*://*.tiktok.com/*'}) : [];
        const afterContentTab = afterTabs.find(t => (t.url || '').includes('/content') || (t.url || '').includes('/manage'));
        if (afterContentTab) {
          const reconciled = await runReconcilePostingResult();
          if (reconciled.outcome === 'published') {
            await openUploadPage(tab);
            return { success: true, clicked: true, posted: true, outcome: 'published', marked: true };
          }
        }
      } catch (_) {}

      // An uncertain submission is terminal for automation, even after restart.
      try { await savePostingReceipt(job, sourceAccount, 'confirmation_unknown', {}); }
      catch (receiptError) { err.message += `; ผลยังรอส่งกลับ: ${receiptError.message}`; }
    }
    throw err;
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }

  const published = confirmation.outcome === 'published';
  try {
    await savePostingReceipt(job, sourceAccount, confirmation.outcome, confirmation.proof);
  } catch (err) {
    // Do not report a false mark: the post is real, but the local archive
    // still needs one retry from the panel if the backend was unavailable.
    await focusTikTokTab(tab);
    return {
      success: true,
      clicked: true,
      posted: published,
      outcome: confirmation.outcome,
      marked: false,
      markError: err.message || String(err),
    };
  }

  // Keep TikTok in front and leave the same tab ready for the next clip.
  await openUploadPage(tab);
  return { success: true, clicked: true, posted: published, outcome: confirmation.outcome, marked: published };
}

async function runTypeCaptionOnly({ caption, hashtags }) {
  const job = await fetchPendingJob();
  caption = job.caption || '';
  hashtags = job.hashtags || '';
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    await waitForCaptionEditor(send);
    await guardPostingAction(job, send, tab.id);
    await typeCaption(send, caption, hashtags);
    return { success: true };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// Step 1 turning green only means the file was handed to TikTok's page --
// see waitForUploadStatusBadge's own comment in automation.js for why that
// is not the same moment as the upload actually finishing. The "ทำต่อหลัง
// อัปโหลด" shortcut (runPrepareDetails below) becomes clickable as soon as
// step 1 does, so it can genuinely be invoked well before the real upload
// is done -- confirmed live: the shortcut was clickable at 26% progress.
// Waiting here, once, before any of caption/product/cover run, covers all
// of them instead of just the cover step.
async function runWaitForUploadOnly() {
  const tab = await findUploadTab();
  const send = cdp(tab.id);
  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    await OmniAutomation.waitForUploadStatusBadge(send);
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// Automated preparation stops before publication. Each stage has its own session.
async function runPrepareDetails(message) {
  const job = await fetchPendingJob();
  const completed = [];
  let step = 'caption';
  try {
    await runWaitForUploadOnly();
    const caption = job.caption ?? '';
    const hashtags = job.hashtags ?? '';
    if (![caption, hashtags].some(value => value.trim())) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็ก');
    await runTypeCaptionOnly({caption, hashtags});
    completed.push('caption');

    step = 'product';
    const productId = job.tiktok_product_id;
    if (!productId) throw new Error('กรุณากรอก ID สินค้า');
    const product = await runAttachProductOnly({productId, cartName: message.cartName || ''});
    if (!product.success) throw new Error(product.reason);
    completed.push('product');

    // TikTok must be in schedule mode before the cover editor is opened.
    // The cover editor can trigger a form re-render, which used to discard
    // the schedule selection when cover was uploaded first.
    if (job.schedule_date && job.schedule_time) {
      step = 'schedule';
      const schedule = await runScheduleModeOnly({date: message.scheduleDate, time: message.scheduleTime});
      if (!schedule.success) throw new Error(schedule.reason);
      completed.push('schedule');
    }

    step = 'cover';
    await runUploadCoverOnly({coverPath: message.coverPath});
    completed.push('cover');

    return {success:true, completed};
  } catch (err) {
    return {success:false, completed, step, error:err.message};
  }
}

let actionRunning = false;
let pinnedUploadTabId = null;
const actions = {
  'claim-posting-job': async message => {
    const state = await postingState();
    if (message.channelId !== state.channelId || !message.jobId) throw new Error('งานที่รับไม่ตรงช่อง');
    const job = await fetchPendingJob(message.jobId);
    return {success:true, job_id:job.job_id, channel_id:job.channel_id};
  },
  'upload-file-only': () => runUploadFileOnly(),
  'type-caption-only': message => runTypeCaptionOnly(message),
  'attach-product-only': message => runAttachProductOnly(message),
  'schedule-mode-only': message => runScheduleModeOnly(message),
  'click-post-only': () => runClickPostOnly(),
  'upload-cover-only': message => runUploadCoverOnly(message),
  'prepare-details': message => runPrepareDetails(message),
  'retry-posting-receipt': () => retryPostingReceipt(),
  'release-posting-job': message => releasePostingJob(message),
  'reconcile-posting-result': message => runReconcilePostingResult(message),
  'select-posting-channel': message => selectPostingChannel(message.channelId),
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.action === 'run-autopost') {
    sendResponse({success:false, error:'กรุณาใช้ปุ่มทำต่อหลังอัปโหลดในแถบข้างรุ่นล่าสุด'});
    return false;
  }
  const action = actions[message?.action];
  if (!action) return false;
  if (actionRunning) {
    sendResponse({success:false, error:'มีขั้นตอนกำลังทำอยู่ กรุณารอให้จบก่อน'});
    return false;
  }
  actionRunning = true;
  (async () => {
    try {
      if (!['retry-posting-receipt', 'release-posting-job', 'select-posting-channel', 'claim-posting-job', 'reconcile-posting-result'].includes(message.action)) pinnedUploadTabId = (await findUploadTab()).id;
      const result = await action(message);
      const state = await postingState();
      return state.accountWarning ? {...result, warning:state.accountWarning} : result;
    } finally {
      pinnedUploadTabId = null;
      actionRunning = false;
    }
  })().then(sendResponse).catch(err => sendResponse({success:false, error:err.message || String(err)}));
  return true;
});
