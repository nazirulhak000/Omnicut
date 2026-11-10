const BACKEND = 'http://127.0.0.1:8000';

const {
  buildExtensionClipList,
  getExtensionStatus,
  pickBatchCandidates,
} = window.OmniCutClipState || {};

// This panel talks to :8000 directly (no Vite proxy to inject the header

// for it, unlike the app's own frontend -- see auth_key.js). Cached here

// and refreshed on storage change rather than re-read on every request,

// since this panel is a long-lived page, not a service worker.

let apiKey = '';

let activeChannelId = 'main';

let channelEpoch = 0;

let channelReady;

function panelChannelId(value) {

  if (typeof value !== 'string' || !/^[a-z][a-z0-9_-]{1,31}$/.test(value) || /[\r\n]/.test(value)) throw new Error('รหัสช่องไม่ถูกต้อง');

  return value;

}

async function scopedPanelFetch(url, options = {}) {

  const channel = activeChannelId;

  const epoch = channelEpoch;

  const response = await authedFetch(url, apiKey, {...options,

    headers: {...options.headers, 'X-OmniCut-Channel': panelChannelId(channel)}});

  if (channel !== activeChannelId || epoch !== channelEpoch) throw new Error('ช่องเปลี่ยนแล้ว กรุณาโหลดข้อมูลใหม่');

  const readJson = response.json.bind(response);

  response.json = async () => {

    const data = await readJson();

    if (channel !== activeChannelId || epoch !== channelEpoch) throw new Error('ผลตอบกลับของช่องเดิมถูกปฏิเสธ');

    if (data.channel_id && data.channel_id !== channel) throw new Error('ผลตอบกลับเป็นของอีกช่อง');

    return data;

  };

  return response;

}

function scopedPanelMedia(url) {

  const result = new URL(withApiKeyParam(url, apiKey));

  result.searchParams.set('channel_id', panelChannelId(activeChannelId));

  return result.href;

}

function panelWorkerRequest(message) {

  return new Promise((resolve, reject) => chrome.runtime.sendMessage(message, result => {

    if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));

    if (!result?.success) return reject(new Error(result?.error || 'Extension ไม่รับคำขอ'));

    resolve(result);

  }));

}

// The very first loadExports() call below (at startup) must wait for this

// to resolve -- chrome.storage.local.get() is asynchronous, so without

// this, the panel's initial auto-load always fires with apiKey still ''

// (401, no header sent) regardless of what's actually saved; only a

// manual refresh clicked later -- by which point this promise has long

// since resolved -- would happen to work. Subsequent calls (manual

// refresh, mark-posted's reload) don't need to wait on this since apiKey

// is long since populated by the time a user can click anything.

const apiKeyReady = getStoredApiKey().then((key) => { apiKey = key; });

channelReady = new Promise((resolve, reject) => chrome.storage.local.get(['omnicutChannelId', 'omnicutPostingProtocolV2'], saved => {

  try {

    if (chrome.runtime.lastError) throw new Error(chrome.runtime.lastError.message);

    activeChannelId = panelChannelId(saved.omnicutPostingProtocolV2?.channelId || saved.omnicutChannelId || 'main');

    resolve();

  } catch (err) {reject(err);}

}));

if (typeof chrome !== 'undefined' && chrome.storage?.onChanged) {

  chrome.storage.onChanged.addListener((changes, area) => {

    if (area === 'local' && changes[OMNICUT_API_KEY_STORAGE_KEY]) {

      apiKey = changes[OMNICUT_API_KEY_STORAGE_KEY].newValue || '';

    }

  });

}

const apiKeySettingsBtn = document.getElementById('apiKeySettingsBtn');

const apiKeySettingsRow = document.getElementById('apiKeySettingsRow');

const apiKeyInput = document.getElementById('apiKeyInput');

const apiKeySaveBtn = document.getElementById('apiKeySaveBtn');

apiKeySettingsBtn?.addEventListener('click', async () => {

  apiKeySettingsRow?.classList.toggle('is-open');

  if (apiKeySettingsRow?.classList.contains('is-open')) {

    apiKeyInput.value = await getStoredApiKey();

  }

});

apiKeySaveBtn?.addEventListener('click', async () => {

  const val = apiKeyInput.value.trim();

  await setStoredApiKey(val);

  apiKey = val;

  apiKeySettingsRow?.classList.remove('is-open');

  setStatus('บันทึก API Key เรียบร้อยแล้ว', 'success');

  loadExports();

  initializeChannelSelector().catch(() => {});

});

const THEME_STORAGE_KEY = 'omnicutTheme';

const themeToggleBtn = document.getElementById('themeToggleBtn');

const themeIconSun = document.getElementById('themeIconSun');

const themeIconMoon = document.getElementById('themeIconMoon');

function applyTheme(theme) {

  const isDark = theme === 'dark';

  document.documentElement.setAttribute('data-theme', theme);

  document.body?.setAttribute('data-theme', theme);

  if (themeIconSun && themeIconMoon) {

    themeIconSun.style.display = isDark ? 'inline-block' : 'none';

    themeIconMoon.style.display = isDark ? 'none' : 'inline-block';

  }

}

if (typeof chrome !== 'undefined' && chrome.storage?.local) {

  chrome.storage.local.get([THEME_STORAGE_KEY], (res) => {

    const saved = res?.[THEME_STORAGE_KEY] || 'dark';

    applyTheme(saved);

  });

} else {

  applyTheme('dark');

}

themeToggleBtn?.addEventListener('click', () => {

  const current = document.documentElement.getAttribute('data-theme') || 'dark';

  const next = current === 'dark' ? 'light' : 'dark';

  applyTheme(next);

  if (typeof chrome !== 'undefined' && chrome.storage?.local) {

    chrome.storage.local.set({ [THEME_STORAGE_KEY]: next });

  }

});

const channelHandles = new Map();   // channel id -> TikTok handle, for the pre-run account check
async function initializeChannelSelector() {

  await Promise.all([apiKeyReady, channelReady]);

  const label = document.createElement('label'); label.textContent = 'เลือกช่อง';

  const select = document.createElement('select'); select.id = 'postingChannelSelect'; select.setAttribute('aria-label','เลือกช่องโพสต์');

  const response = await authedFetch(`${BACKEND}/api/channels?include_archived=false`, apiKey);

  if (!response.ok) throw new Error('โหลดช่องไม่สำเร็จ ต้องใช้ Backend รุ่น multi-channel');

  const data = await response.json();

  for (const channel of data.channels || []) {
    channelHandles.set(panelChannelId(channel.id), channel.handle || '');
    if (channel.status !== 'active') continue;

    const option = document.createElement('option'); option.value = panelChannelId(channel.id);

    option.textContent = `${channel.display_name || channel.id} (${channel.handle || channel.id})`;

    select.appendChild(option);

  }

  select.value = activeChannelId;

  select.addEventListener('change', async () => {

    const next = select.value;

    if (busy || activeClip) {select.value = activeChannelId; setStatus('ปิดงานเดิมก่อนเปลี่ยนช่อง', 'error'); return;}

    select.disabled = true;

    try {

      await panelWorkerRequest({action:'select-posting-channel', channelId:next});

      activeChannelId = panelChannelId(next); channelEpoch += 1;

      activeClip = null; allClips = []; resetChecklist(); renderActiveClipBanner();

      await loadExports();

    } catch (err) {select.value = activeChannelId; setStatus(err.message,'error');}

    finally {select.disabled = false;}

  });

  label.appendChild(select); apiKeySettingsRow?.appendChild(label);

  const release = document.createElement('button'); release.id='releasePostingBtn'; release.type='button'; release.textContent='ยกเลิกงานก่อนโพสต์';

  release.className='btn-copy-action'; release.style.minHeight='44px';

  release.title='ยกเลิกเฉพาะงานที่ยังไม่กดโพสต์ เพื่อเลือกคลิปหรือช่องใหม่';

  release.addEventListener('click', async () => {

    if (busy) return;

    release.disabled = true;

    try {

      const res = await panelWorkerRequest({action: 'release-posting-job'});

      activeClip = null; resetChecklist(); renderActiveClipBanner(); await loadExports();

      showTab('list'); scrollToTop();

      setStatus(res.alreadyResolved ? 'คลิปเดิมได้รับการเผยแพร่แล้ว ล้างงานเรียบร้อย' : 'ยกเลิกงานก่อนโพสต์แล้ว เลือกคลิปหรือช่องใหม่ได้', 'success');

    } catch (err) {

      if (err.message?.includes('ต้องตรวจผลเดิมก่อน')) {

        const confirmDiscard = confirm('งานนี้มีประวัติเคยกดโพสต์หรือกำลังรอตรวจผล\n\nระบบจะ "พักงานเดิม" ไว้เป็นรอตรวจ (ไม่ยกเลิก เพื่อกันโพสต์ซ้ำ) แล้วให้คุณเริ่มคลิปอื่นได้ทันที\nตรวจผลของงานเดิมภายหลังที่ TikTok Studio > Content\n\nพักงานเดิมแล้วเริ่มคลิปใหม่เลยไหม?');

        if (confirmDiscard) {

          try {

            await panelWorkerRequest({action: 'release-posting-job', park: true});

            activeClip = null; resetChecklist(); renderActiveClipBanner(); await loadExports();

            showTab('list'); scrollToTop();

            setStatus('พักงานเดิมไว้เป็นรอตรวจแล้ว (ไม่ได้ยกเลิก) เลือกคลิปถัดไปได้ทันที', 'success');

            return;

          } catch (forceErr) {

            setStatus('ยกเลิกงานไม่สำเร็จ: ' + forceErr.message, 'error');

            return;

          }

        }

      }

      setStatus(err.message, 'error');

    }

    finally { release.disabled = false; }

  });

  // Reuse the existing manual button as a read-only reconciliation action.

  const button = document.getElementById('markPostedBtn');

  button?.parentElement?.appendChild(release);

  if (button) {

    button.textContent = 'ยืนยันว่าโพสต์แล้ว (เปลี่ยนสถานะทันที)';

    button.title = 'กดยืนยันว่าคลิปโพสต์หรือตั้งเวลาบน TikTok เรียบร้อยแล้ว เพื่อมาร์กเสร็จสิ้นและเริ่มคลิปถัดไป';

  }

  const help = button?.parentElement?.querySelector('p');

  if (help) help.textContent = 'กดเมื่อโพสต์หรือตั้งเวลาบน TikTok เรียบร้อยแล้ว เพื่อมาร์กว่าโพสต์สำเร็จ ย้ายไฟล์ และเปิดรับคลิปถัดไปทันที';

  const saved = await new Promise(resolve => chrome.storage.local.get(['omnicutPostingProtocolV2'], resolve));

  let job = saved.omnicutPostingProtocolV2?.activeJob;

  if (job) {

    if (job.channel_id !== activeChannelId || !job.job_id) throw new Error('งานที่บันทึกไว้ไม่ตรงช่อง');

    let isFinished = false;

    try {

      const curRes = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/jobs/${encodeURIComponent(job.job_id)}`);

      if (curRes.ok) {

        const fresh = await curRes.json();

        if (fresh.status === 'published' || fresh.status === 'cancelled') {

          isFinished = true;

          saved.omnicutPostingProtocolV2.activeJob = null;

          saved.omnicutPostingProtocolV2.pendingReceipt = null;

          await new Promise(r => chrome.storage.local.set(saved, r));

          await panelWorkerRequest({action: 'release-posting-job', park: true}).catch(() => {});

          activeClip = null;

          resetChecklist();

          renderActiveClipBanner();

          showTab('list');

          scrollToTop();

          setStatus(fresh.status === 'published' ? 'คลิปเดิมเผยแพร่เรียบร้อยแล้ว พร้อมสำหรับคลิปถัดไป' : 'งานเดิมถูกยกเลิกแล้ว พร้อมสำหรับคลิปถัดไป', 'success');

        } else {

          if (fresh.cover_path) {

            job.cover_path = fresh.cover_path;

            saved.omnicutPostingProtocolV2.activeJob.cover_path = fresh.cover_path;

            await new Promise(r => chrome.storage.local.set(saved, r));

          }

          Object.assign(job, fresh);

        }

      }

    } catch (_) {}

    if (!isFinished) {

      activeClip = {...job, rel_path:job.video_path, hook_title:job.product_name || job.job_id};

      captionInput.value = job.caption || ''; hashtagsInput.value = job.hashtags || '';

      productIdInput.value = job.tiktok_product_id || ''; cartNameInput.value = job.product_name || '';

      scheduleDateInput.value = job.schedule_date || ''; scheduleTimeInput.value = job.schedule_time || '';

      renderActiveClipBanner(); showTab('checklist');

      setStatus('กู้คืนงานเดิมแล้ว ตรวจผลก่อนเริ่มงานใหม่ ไม่มีการกดโพสต์ซ้ำ', 'success');

    }

  }

}

const listEl = document.getElementById('list');

const statusEl = document.getElementById('status');

const refreshBtn = document.getElementById('refreshBtn');

const activeClipBanner = document.getElementById('activeClipBanner');

const captionInput = document.getElementById('captionInput');

const hashtagsInput = document.getElementById('hashtagsInput');

const productIdInput = document.getElementById('productIdInput');

const cartNameInput = document.getElementById('cartNameInput');

const scheduleDateInput = document.getElementById('scheduleDateInput');

const scheduleTimeInput = document.getElementById('scheduleTimeInput');

const markPostedBtn = document.getElementById('markPostedBtn');

const copyAllBtn = document.getElementById('copyAllBtn');

const clipSearchInput = document.getElementById('clipSearchInput');

const clipCountBadge = document.getElementById('clipCountBadge');

const batchStartBtn = document.getElementById('batchStartBtn');

const batchModeSelect = document.getElementById('batchModeSelect');

const batchCountBadge = document.getElementById('batchCountBadge');

const batchDashboard = document.getElementById('batchDashboard');

const batchStatusText = document.getElementById('batchStatusText');

const batchProgressPercent = document.getElementById('batchProgressPercent');

const batchProgressBar = document.getElementById('batchProgressBar');

const batchCurrentStep = document.getElementById('batchCurrentStep');

const batchEtaText = document.getElementById('batchEtaText');

const batchPauseBtn = document.getElementById('batchPauseBtn');

const batchResumeBtn = document.getElementById('batchResumeBtn');

const batchStopBtn = document.getElementById('batchStopBtn');

const batchLogBox = document.getElementById('batchLogBox');
const batchQuotaCard = document.getElementById('batchQuotaCard');
const btnCheckQuota = document.getElementById('btnCheckQuota');
const quotaScheduleValue = document.getElementById('quotaScheduleValue');
const quotaScheduleRemain = document.getElementById('quotaScheduleRemain');
const quotaDraftValue = document.getElementById('quotaDraftValue');
const quotaDraftRemain = document.getElementById('quotaDraftRemain');
const batchLimitSelect = document.getElementById('batchLimitSelect');
const batchLimitInfo = document.getElementById('batchLimitInfo');
const batchCappedCount = document.getElementById('batchCappedCount');
let activeBatchRunner = null;

let currentQuotaState = {
  scheduledCount: null,
  draftCount: null,
  remainingSchedule: 30,
  remainingDraft: 30,
  maxSchedule: 30,
  maxDraft: 30,
};

function updateQuotaUI() {
  const maxS = currentQuotaState.maxSchedule || 30;
  const maxD = currentQuotaState.maxDraft || 30;

  if (quotaScheduleValue) {
    quotaScheduleValue.textContent = currentQuotaState.scheduledCount != null
      ? `${currentQuotaState.scheduledCount} / ${maxS}`
      : `-- / ${maxS}`;
  }
  if (quotaScheduleRemain) {
    const rem = currentQuotaState.remainingSchedule;
    if (rem != null) {
      quotaScheduleRemain.textContent = rem === 0 ? 'เต็ม 30/30' : `เหลือ ${rem}`;
      quotaScheduleRemain.className = 'quota-badge ' + (rem === 0 ? 'danger' : (rem <= 5 ? 'warning' : 'success'));
    } else {
      quotaScheduleRemain.textContent = 'สูงสุด 30';
      quotaScheduleRemain.className = 'quota-badge neutral';
    }
  }

  if (quotaDraftValue) {
    quotaDraftValue.textContent = currentQuotaState.draftCount != null
      ? `${currentQuotaState.draftCount} / ${maxD}`
      : `-- / ${maxD}`;
  }
  if (quotaDraftRemain) {
    const rem = currentQuotaState.remainingDraft;
    if (rem != null) {
      quotaDraftRemain.textContent = rem === 0 ? 'เต็ม 30/30' : `เหลือ ${rem}`;
      quotaDraftRemain.className = 'quota-badge ' + (rem === 0 ? 'danger' : (rem <= 5 ? 'warning' : 'success'));
    } else {
      quotaDraftRemain.textContent = 'สูงสุด 30';
      quotaDraftRemain.className = 'quota-badge neutral';
    }
  }
}

function getEffectiveBatchLimit(totalAvailable, { forceAuto = false } = {}) {
  const mode = batchModeSelect?.value || 'smart';
  const limitChoice = forceAuto ? 'auto_quota' : (batchLimitSelect?.value || 'auto_quota');

  let cap = 30; // TikTok maximum quota per category

  if (limitChoice === 'auto_quota') {
    const sRem = currentQuotaState.remainingSchedule != null ? currentQuotaState.remainingSchedule : 30;
    const dRem = currentQuotaState.remainingDraft != null ? currentQuotaState.remainingDraft : 30;
    if (mode === 'schedule_only') cap = Math.min(30, sRem);
    else if (mode === 'draft_only') cap = Math.min(30, dRem);
    else cap = Math.min(30, sRem + dRem); // smart: schedule until the schedule quota is full, drafts after
  } else if (limitChoice === 'all') {
    cap = totalAvailable;
  } else {
    cap = parseInt(limitChoice, 10) || 30;
  }

  return Math.min(cap, totalAvailable);
}

function updateBatchCountDisplay(filteredCount = null) {
  const query = clipSearchInput ? clipSearchInput.value.trim().toLowerCase() : '';
  const count = filteredCount !== null ? filteredCount : (query
    ? allClips.filter((c) =>
        (c.product_name || '').toLowerCase().includes(query) ||
        (c.hook_title || '').toLowerCase().includes(query) ||
        (c.name || '').toLowerCase().includes(query)
      ).length
    : allClips.length);

  const picked = selectedClipsInList().length;
  const capped = picked > 0 ? getEffectiveBatchLimit(picked, { forceAuto: true }) : getEffectiveBatchLimit(count);

  if (batchLimitSelect) {
    batchLimitSelect.disabled = picked > 0;
    batchLimitSelect.title = picked > 0
      ? 'ติ๊กเลือกคลิปไว้ — จะโพสต์เฉพาะที่ติ๊ก ไม่ใช้ตัวจำกัดจำนวน'
      : 'จำกัดจำนวนคลิปที่จะอัปโหลดในรอบนี้ ป้องกันการล้นโควตา TikTok Studio';
  }
  if (batchCountBadge) {
    batchCountBadge.textContent = String(count);
  }
  if (batchCappedCount) {
    batchCappedCount.textContent = String(capped);
  }
  if (batchLimitInfo) {
    const limitChoice = batchLimitSelect?.value || 'auto_quota';
    if (picked > 0) {
      batchLimitInfo.textContent = picked > capped ? `เลือกไว้ ${picked} · โควตารับได้ ${capped}` : `เลือกเอง ${picked} คลิป`;
    } else if (limitChoice === 'auto_quota') {
      batchLimitInfo.textContent = `โควตาว่าง: ${capped} คลิป`;
    } else if (limitChoice === 'all') {
      batchLimitInfo.textContent = `รันทั้งหมด ${count} คลิป`;
    } else {
      batchLimitInfo.textContent = `ล็อก ${limitChoice} คลิป`;
    }
  }
  if (batchStartBtn && !activeBatchRunner) {
    batchStartBtn.disabled = capped === 0 || count === 0 || busy;
  }
}

async function checkTikTokQuota(silent = false, allowNavigate = false) {
  const btn = document.getElementById('btnCheckQuota');
  if (btn) btn.classList.add('loading');
  try {
    const res = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: 'detect-tiktok-quota', allowNavigate }, (r) => resolve(r || {}));
    });
    if (res && res.success) {
      // A silent refresh does not open the Content list, so it cannot see scheduled posts. Keep a count
      // read in the last 15 minutes instead of overwriting it with "unknown -> 30 free".
      const keepScheduled = res.scheduledCount == null && currentQuotaState.scheduledCount != null
        && Date.now() - (currentQuotaState.scheduledAt || 0) < 15 * 60 * 1000;
      const scheduledCount = keepScheduled ? currentQuotaState.scheduledCount : res.scheduledCount;
      currentQuotaState = {
        scheduledCount,
        scheduledAt: scheduledCount != null ? (keepScheduled ? currentQuotaState.scheduledAt : Date.now()) : null,
        draftCount: res.draftCount,
        remainingSchedule: keepScheduled
          ? currentQuotaState.remainingSchedule
          : (res.remainingSchedule ?? (res.scheduledCount != null ? Math.max(0, 30 - res.scheduledCount) : 30)),
        remainingDraft: res.remainingDraft ?? (res.draftCount != null ? Math.max(0, 30 - res.draftCount) : 30),
        maxSchedule: res.maxSchedule || 30,
        maxDraft: res.maxDraft || 30,
      };
      updateQuotaUI();
      updateBatchCountDisplay();
      if (!silent) setStatus(`อัปเดตโควตาสำเร็จ: ${res.message || ''}`, 'success');
    } else {
      if (!silent) setStatus(res?.message || 'ไม่พบข้อมูลโควตาจากแท็บ TikTok Studio', 'info');
    }
  } catch (err) {
    if (!silent) setStatus(`เช็คโควตาไม่สำเร็จ: ${err.message}`, 'error');
  } finally {
    if (btn) btn.classList.remove('loading');
    updateBatchCountDisplay();
  }
}

btnCheckQuota?.addEventListener('click', () => checkTikTokQuota(false, true));
batchLimitSelect?.addEventListener('change', () => updateBatchCountDisplay());
batchModeSelect?.addEventListener('change', () => { filterAndRenderClips(); });

const captionCharCount = document.getElementById('captionCharCount');

const copyProductIdBtn = document.getElementById('copyProductIdBtn');

const headerStatusPill = document.getElementById('headerStatusPill');

const headerStatusDot = document.getElementById('headerStatusDot');

const headerStatusText = document.getElementById('headerStatusText');

function updateHeaderBackendStatus(state) {

  if (!headerStatusPill || !headerStatusDot || !headerStatusText) return;

  headerStatusPill.classList.remove('is-online', 'is-offline', 'is-checking');

  headerStatusDot.classList.remove('is-online', 'is-offline', 'is-checking');

  if (state === 'online') {

    headerStatusPill.classList.add('is-online');

    headerStatusDot.classList.add('is-online');

    headerStatusText.textContent = 'Ready';

    headerStatusPill.title = 'OmniCut Backend: เชื่อมต่อสำเร็จ (พร้อมทำงาน)';

  } else if (state === 'offline') {

    headerStatusPill.classList.add('is-offline');

    headerStatusDot.classList.add('is-offline');

    headerStatusText.textContent = 'Offline';

    headerStatusPill.title = 'OmniCut Backend: ยังไม่ได้เปิด start_app.bat (คลิกเพื่อลองใหม่)';

  } else {

    headerStatusPill.classList.add('is-checking');

    headerStatusDot.classList.add('is-checking');

    headerStatusText.textContent = 'Checking';

    headerStatusPill.title = 'กำลังตรวจสอบการเชื่อมต่อ Backend...';

  }

}

headerStatusPill?.addEventListener('click', () => {

  loadExports();

});

const videoPreviewModal = document.getElementById('videoPreviewModal');

const previewBackdrop = document.getElementById('previewBackdrop');

const previewModalTitle = document.getElementById('previewModalTitle');

const previewCloseBtn = document.getElementById('previewCloseBtn');

const previewVideoPlayer = document.getElementById('previewVideoPlayer');

const previewSelectBtn = document.getElementById('previewSelectBtn');

let allClips = [];
// Clips the operator ticked in the list. When any is ticked, the batch posts exactly those
// (in list order) instead of "first N of the queue".
const selectedClipKeys = new Set();
let visibleClips = [];
function selectionKey(clip) {
  return String(clip.id || `k:${clip.export_id || clip.rel_path || clip.name || ''}`);
}
const BLOCK_REASON_TH = {
  no_export: 'ไม่มีไฟล์วิดีโอ',
  export_missing: 'ไฟล์ export หายจากระบบ',
  export_already_posted: 'โพสต์ไปแล้ว',
  export_qc_rejected: 'QC ไม่ผ่าน',
  price_in_caption: 'caption มีราคา/ส่วนลด',
  placeholder_in_caption: 'caption มี {…} ที่ยังไม่แทนค่า',
  empty_caption: 'ไม่มี caption/แฮชแท็ก',
  caption_too_long: 'caption ยาวเกิน 4000 ตัวอักษร',
  too_many_hashtags: 'แฮชแท็กเกิน 30 อัน',
  slot_passed_or_too_close: 'เวลาโพสต์ผ่านแล้วหรือใกล้เกินไป',
  no_schedule: 'ไม่มีเวลาโพสต์ (ในโหมดตั้งเวลาจะกลายเป็นโพสต์สด)',
  draft_in_draft_mode: 'โหมดแบบร่างอย่างเดียวไม่เผยแพร่แบบร่าง (เปลี่ยนเป็น Schedule Only หรือ Smart)',
};
// '' = usable; otherwise the guard code. One place for the list, the selection and the batch.
function blockCodeFor(clip, record, now = Date.now()) {
  const guard = globalThis.OmniPostGuard;
  if (!guard) return '';
  const draftOnly = (batchModeSelect?.value || 'schedule_only') === 'draft_only';
  if (clip.publish_draft && draftOnly) return 'draft_in_draft_mode';
  return guard.clipSkipReason(clip, record, now, { exportsKnown: Boolean(exportRecordIndex), ignoreSlot: draftOnly, requireSchedule: !draftOnly });
}
// '' = usable; otherwise why the batch would skip this clip (same guard the batch uses).
function clipBlockReason(clip) {
  const guard = globalThis.OmniPostGuard;
  if (!guard) return '';
  const record = exportRecordIndex ? exportRecordIndex.get(clip.export_id) : undefined;
  const code = blockCodeFor(clip, record);
  return code ? (BLOCK_REASON_TH[code] || code) : '';
}
function selectedClipsInList() {
  return allClips.filter((c) => selectedClipKeys.has(selectionKey(c)) && !clipBlockReason(c));
}
// Every ticked clip, usable or not. If anything is ticked the batch is "exactly these": when none of them is usable it must
// stop, never fall back to running the whole queue.
function selectedClipsRaw() {
  return allClips.filter((c) => selectedClipKeys.has(selectionKey(c)));
}
// export_id -> /api/exports row (null when the registry could not be read)
let exportRecordIndex = null;

function updateCaptionCounter() {

  if (!captionCharCount || !captionInput) return;

  const len = captionInput.value.length;

  captionCharCount.textContent = `${len.toLocaleString()} / 2,200`;

  captionCharCount.classList.remove('warning', 'danger');

  if (len > 2200) {

    captionCharCount.classList.add('danger');

  } else if (len > 1800) {

    captionCharCount.classList.add('warning');

  }

}

captionInput?.addEventListener('input', updateCaptionCounter);

copyProductIdBtn?.addEventListener('click', async () => {

  const pid = productIdInput?.value?.trim();

  if (!pid) {

    setStatus('ไม่มี ID สินค้าให้คัดลอก', 'error');

    return;

  }

  try {

    await navigator.clipboard.writeText(pid);

    setStatus('คัดลอก ID สินค้าแล้ว: ' + pid, 'success');

  } catch (err) {

    setStatus('คัดลอกไม่สำเร็จ: ' + err.message, 'error');

  }

});

function openVideoPreview(item) {

  if (!videoPreviewModal || !previewVideoPlayer) return;

  const vidPath = item.video_url || (item.rel_path ? `/api/media/${item.rel_path}` : '');

  if (!vidPath) {

    setStatus('ไม่พบที่อยู่วิดีโอสำหรับพรีวิว', 'error');

    return;

  }

  previewModalTitle.textContent = item.hook_title || item.product_name || item.name;

  previewVideoPlayer.src = scopedPanelMedia(`${BACKEND}${vidPath}`);

  previewVideoPlayer.currentTime = 0;

  previewVideoPlayer.play().catch(() => {});

  videoPreviewModal.hidden = false;

  previewSelectBtn.onclick = () => {

    closeVideoPreview();

    handlePrepareClick(item);

  };

}

function closeVideoPreview() {

  if (!videoPreviewModal || !previewVideoPlayer) return;

  previewVideoPlayer.pause();

  previewVideoPlayer.removeAttribute('src');

  previewVideoPlayer.load();

  videoPreviewModal.hidden = true;

}

previewCloseBtn?.addEventListener('click', closeVideoPreview);

previewBackdrop?.addEventListener('click', closeVideoPreview);

const tabBtnList = document.getElementById('tabBtnList');

const tabBtnChecklist = document.getElementById('tabBtnChecklist');

const tabBtnTools = document.getElementById('tabBtnTools');

const panelList = document.getElementById('panelList');

const panelChecklist = document.getElementById('panelChecklist');

const panelTools = document.getElementById('panelTools');

const confirmOverlay = document.getElementById('confirmOverlay');

const confirmText = document.getElementById('confirmText');

const confirmOkBtn = document.getElementById('confirmOkBtn');

const confirmCancelBtn = document.getElementById('confirmCancelBtn');

// The panel displays one captured channel/job; the durable lease lives in the worker.

let activeClip = null;

let busy = false;

const SCHEDULE_LEAD_MINUTES = 15;

function localDateValue(date) {

  const year = date.getFullYear();

  const month = String(date.getMonth() + 1).padStart(2, '0');

  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;

}

function minimumScheduleDateTime() {

  const minimum = new Date(Date.now() + SCHEDULE_LEAD_MINUTES * 60 * 1000);

  minimum.setSeconds(0, 0);

  const remainder = minimum.getMinutes() % 5;

  if (remainder) minimum.setMinutes(minimum.getMinutes() + (5 - remainder));

  return minimum;

}

function populateScheduleTimes() {

  const previous = scheduleTimeInput.value;

  const selectedDate = scheduleDateInput.value;

  const minimum = minimumScheduleDateTime();

  const today = localDateValue(minimum);

  const minimumTime = `${String(minimum.getHours()).padStart(2, '0')}:${String(minimum.getMinutes()).padStart(2, '0')}`;

  const options = ['<option value="">เลือกเวลา</option>'];

  for (let hour = 0; hour < 24; hour += 1) {

    for (let minute = 0; minute < 60; minute += 5) {

      const value = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;

      const disabled = selectedDate === today && value < minimumTime ? ' disabled' : '';

      options.push(`<option value="${value}"${disabled}>${value}</option>`);

    }

  }

  scheduleTimeInput.innerHTML = options.join('');

  const previousOption = scheduleTimeInput.querySelector(`option[value="${previous}"]`);

  if (previousOption && !previousOption.disabled) scheduleTimeInput.value = previous;

  else if (selectedDate === today) scheduleTimeInput.value = minimumTime;

}

function syncScheduleConstraints() {

  const minimum = minimumScheduleDateTime();

  const minimumDate = localDateValue(minimum);

  scheduleDateInput.min = minimumDate;

  if (scheduleDateInput.value && scheduleDateInput.value < minimumDate) scheduleDateInput.value = minimumDate;

  populateScheduleTimes();

}

scheduleDateInput.addEventListener('change', syncScheduleConstraints);

syncScheduleConstraints();

function setBusy(value) {

  busy = value;

  document.querySelectorAll('#panelChecklist button, #panelTools button, #list button, #refreshBtn, #panelChecklist input, #panelChecklist textarea')

    .forEach(el => { el.disabled = value; });

  markPostedBtn.disabled = value || !activeClip;

  // The loop above just force-enabled prepareDetailsBtn and prepareSchedule

  // along with every other checklist button/input when value is false --

  // reapply their own separate gating rules so finishing an unrelated step

  // doesn't un-grey either of them.

  if (!value) {

    syncPrepareDetailsBtnState();

    syncPrepareScheduleCheckboxState();

  }

}

function setStatus(text, kind) {

  let iconSvg = '';

  if (kind === 'success') {

    iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';

  } else if (kind === 'error') {

    iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>';

  } else if (kind === 'info') {

    iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>';

  }

  statusEl.innerHTML = iconSvg ? `${iconSvg} <span>${escapeHtml(text)}</span>` : escapeHtml(text);

  statusEl.className = kind || 'info';

  // Only scroll into view if there is an error on the checklist tab; NEVER scroll down on the list tab or on success

  if (kind === 'error' && panelChecklist?.classList?.contains('active')) {

    statusEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  }

}

function scrollToTop() {

  window.scrollTo({ top: 0, behavior: 'instant' });

  document.documentElement.scrollTop = 0;

  document.body.scrollTop = 0;

  if (panelList) panelList.scrollTop = 0;

  requestAnimationFrame(() => {

    window.scrollTo({ top: 0, behavior: 'instant' });

    document.documentElement.scrollTop = 0;

    document.body.scrollTop = 0;

    if (panelList) panelList.scrollTop = 0;

  });

}

function escapeHtml(s) {

  return String(s || '').replace(/[&<>"']/g, (c) => ({

    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',

  }[c]));

}

// ── Tabs ──────────────────────────────────────────────────────────────────

function showTab(name) {

  const isList = name === 'list';

  const isChecklist = name === 'checklist';

  const isTools = name === 'tools';

  tabBtnList.classList.toggle('active', isList);

  tabBtnChecklist.classList.toggle('active', isChecklist);

  tabBtnTools.classList.toggle('active', isTools);

  panelList.classList.toggle('active', isList);

  panelChecklist.classList.toggle('active', isChecklist);

  panelTools.classList.toggle('active', isTools);

  if (isList) {

    scrollToTop();

  }

}

tabBtnList.addEventListener('click', () => showTab('list'));

tabBtnChecklist.addEventListener('click', () => showTab('checklist'));

tabBtnTools.addEventListener('click', () => showTab('tools'));

// ── Confirm dialog (only shown when switching clips mid-checklist) ────────

function anyStepChecked() {

  return [1, 2, 3, 4, 5, 6].some((n) => document.getElementById(`chk${n}`).checked);

}

let settlePendingConfirm = null;
function askConfirm(message) {
  // a question that is still open is answered "no" before a new one is shown (no stacked listeners, no hanging promise)
  if (settlePendingConfirm) settlePendingConfirm(false);
  return new Promise((resolve) => {
    confirmText.textContent = message;
    confirmOverlay.classList.add('show');
    const cleanup = (result) => {
      settlePendingConfirm = null;
      confirmOverlay.classList.remove('show');
      confirmOkBtn.removeEventListener('click', onOk);
      confirmCancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    };
    settlePendingConfirm = cleanup;

    const onOk = () => cleanup(true);

    const onCancel = () => cleanup(false);

    confirmOkBtn.addEventListener('click', onOk);

    confirmCancelBtn.addEventListener('click', onCancel);

  });

}

function updatePipelineProgress() {

  const fill = document.getElementById('stepProgressFill');

  const text = document.getElementById('stepProgressText');

  if (!fill || !text) return;

  const count = [1, 2, 3, 4, 5, 6].filter(n => document.getElementById(`chk${n}`)?.checked).length;

  fill.style.width = `${Math.round((count / 6) * 100)}%`;

  text.textContent = `${count} / 6 สำเร็จ`;

  // This runs on every real state change to the checklist (wireStep setting

  // chk.checked = true on success, resetChecklist, a manual toggle) --

  // piggyback the shortcut button's own "step 1 done?" re-check on it

  // instead of chk1's 'change' event, which never fires for the `.checked =

  // true` assignments above (only real clicks dispatch 'change').

  syncPrepareDetailsBtnState();

}

function resetChecklist() {

  [1, 2, 3, 4, 5, 6].forEach((n) => {

    const checkbox = document.getElementById(`chk${n}`);

    checkbox.checked = false;

    checkbox.closest('.step-row')?.classList.remove('completed');

  });

  updatePipelineProgress();

  // Setting .checked via JS doesn't fire 'change', so chk1's own listener

  // won't catch this reset -- re-grey the shortcut button explicitly.

  syncPrepareDetailsBtnState();

}

function renderActiveClipBanner() {

  for (const input of [captionInput, hashtagsInput, productIdInput, cartNameInput, scheduleDateInput, scheduleTimeInput]) {

    input.readOnly = Boolean(activeClip);

    input.title = activeClip ? 'ใช้ snapshot งานที่เตรียมไว้ แก้ข้อมูลใน OmniCut ก่อนรับงานใหม่' : '';

  }

  markPostedBtn.disabled = busy || !activeClip;

  const cover = document.getElementById('activeCover');

  cover.hidden = !activeClip?.cover_url;

  if (activeClip?.cover_url) cover.src = scopedPanelMedia(`${BACKEND}${activeClip.cover_url}`);

  else cover.removeAttribute('src');

  if (!activeClip) {

    activeClipBanner.className = 'empty-state';

    activeClipBanner.style.cursor = 'pointer';

    activeClipBanner.title = 'คลิกเพื่อไปเลือกคลิปในแท็บรายการคลิป';

    activeClipBanner.innerHTML = `

      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.6;margin-bottom:2px"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg>

      <span>ยังไม่ได้เลือกคลิป — ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน</span>

    `;

    activeClipBanner.onclick = () => showTab('list');

    syncPrepareDetailsBtnState();

    return;

  }

  activeClipBanner.style.cursor = 'default';

  activeClipBanner.onclick = null;

  activeClipBanner.className = '';

  const productLabel = activeClip.product_name ? `<div style="font-size:9.5px;font-weight:700;color:var(--cyan);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:2px">${escapeHtml(activeClip.product_name)}</div>` : '';

  const timeLabel = activeClip.schedule_time ? `<div style="font-size:10px;color:var(--text-tertiary);margin-top:3px;display:flex;align-items:center;gap:4px"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> กำหนดโพสต์ ${escapeHtml(activeClip.schedule_date || '')} ${escapeHtml(activeClip.schedule_time || '')}</div>` : '';

  activeClipBanner.innerHTML = `

    <span class="active-badge"><span class="pulse-dot"></span>กำลังทำคลิป</span>

    ${productLabel}

    <span class="active-title">${escapeHtml(activeClip.hook_title || activeClip.name)}</span>

    ${timeLabel}

  `;

  syncPrepareDetailsBtnState();

}

function queueScheduleParts(iso) {

  if (!iso) return { schedule_date: '', schedule_time: '' };

  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) return { schedule_date: '', schedule_time: '' };

  const parts = new Intl.DateTimeFormat('en-CA', {

    timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit',

    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',

  }).formatToParts(date).reduce((out, part) => ({ ...out, [part.type]: part.value }), {});

  return { schedule_date: `${parts.year}-${parts.month}-${parts.day}`, schedule_time: `${parts.hour}:${parts.minute}` };

}

async function loadExports() {

  updateHeaderBackendStatus('checking');

  listEl.innerHTML = '<div class="empty">กำลังโหลดรายการคลิป...</div>';

  let items;

  try {

    await channelReady;

    const res = await scopedPanelFetch(`${BACKEND}/api/exports`);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    items = Array.isArray(data) ? data : (data.exports || data.items || []);
    exportRecordIndex = new Map(items.map((e) => [e.export_id || e.id, e]));

    updateHeaderBackendStatus('online');

  } catch (err) {

    updateHeaderBackendStatus('offline');

    listEl.innerHTML = `

      <div class="error error-box-with-retry">

        <p>โหลดไม่สำเร็จ -- ตรวจสอบว่า OmniCut Pro Studio เปิดอยู่ที่ localhost:8000 หรือไม่<br>(${escapeHtml(err.message)})</p>

        <button type="button" id="retryConnectionBtn" class="btn-retry-connection" title="ลองเชื่อมต่อ Backend ใหม่">

          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>

          <span>ลองเชื่อมต่อใหม่</span>

        </button>

      </div>`;

    document.getElementById('retryConnectionBtn')?.addEventListener('click', () => {

      loadExports();

    });

    return;

  }

  // When the desktop app has a durable schedule, the extension should show

  // that planned list first so date/time and the one-at-a-time handoff stay

  // aligned. If no schedule exists yet, retain the original ready-export

  // list for backwards compatibility.

  let scheduled = [];

  try {

    const queueRes = await scopedPanelFetch(`${BACKEND}/api/schedule-queue`);

    if (queueRes.ok) {

      const queueData = await queueRes.json();

      scheduled = (queueData.items || [])

        .filter((item) => ['planned', 'ready_for_extension', 'awaiting_post', 'failed', 'draft_on_platform'].includes(item.status))

        .map((item) => ({

          ...item,

          rel_path: item.video_path,

          export_id: item.export_id,

          name: item.project_name || item.video_path,

          product_name: item.product_name,

          hook_title: item.hook_title,

          tiktok_caption: item.caption,

          tiktok_hashtags: item.hashtags,

          tiktok_product_id: item.tiktok_product_id,

          cover_url: item.cover_url || (item.cover_path ? `/api/media/${item.cover_path}` : null),

          thumbnail_url: item.cover_url || (item.cover_path ? `/api/media/${item.cover_path}` : null),

          ...queueScheduleParts(item.scheduled_at),

        }));

    }

  } catch (err) {

    // The queue API was added after the extension; an older backend can still

    // serve the original ready-export list.

  }

  // Build the final list: scheduled queue items first, then unqueued exports.

  allClips = buildExtensionClipList(items, scheduled).map((item) => ({

    ...item,

    ...(item.is_scheduled ? {} : { is_scheduled: false }),

  }));

  filterAndRenderClips();
  checkTikTokQuota(true);
}

function filterAndRenderClips() {
  updateFilterChipCounts();

  const query = clipSearchInput ? clipSearchInput.value.trim().toLowerCase() : '';

  let list = allClips;
  if (currentStatusFilter === 'ready') {
    list = list.filter(c => getExtensionStatus(c).kind === 'ready' || !c.schedule_date);
  } else if (currentStatusFilter === 'draft') {
    list = list.filter(c => c.is_draft);
  } else if (currentStatusFilter === 'scheduled') {
    list = list.filter(c => Boolean(c.schedule_date) && !c.is_draft);
  } else if (currentStatusFilter === 'unscheduled') {
    list = list.filter(c => !c.schedule_date);
  }

  const filtered = query
    ? list.filter((c) =>
        (c.product_name || '').toLowerCase().includes(query) ||
        (c.hook_title || '').toLowerCase().includes(query) ||
        (c.name || '').toLowerCase().includes(query)
      )
    : list;

  if (clipCountBadge) {
    clipCountBadge.textContent = String(filtered.length);
  }
  // Drop ticks for clips that left the queue (posted / removed) so the count stays honest.
  const knownKeys = new Set(allClips.map(selectionKey));
  for (const key of [...selectedClipKeys]) if (!knownKeys.has(key)) selectedClipKeys.delete(key);
  visibleClips = filtered;
  updateBatchCountDisplay(filtered.length);

  renderClipCards(filtered);
  updateSelectionBar();

}

clipSearchInput?.addEventListener('input', filterAndRenderClips);

const selectAllVisible = document.getElementById('selectAllVisible');
const selectedInfo = document.getElementById('selectedInfo');
const clearSelectionBtn = document.getElementById('clearSelection');

function updateSelectionBar() {
  const picked = selectedClipsInList().length;
  const usableVisible = visibleClips.filter((c) => !clipBlockReason(c));
  const visiblePicked = usableVisible.filter((c) => selectedClipKeys.has(selectionKey(c))).length;
  if (selectedInfo) selectedInfo.textContent = picked ? `เลือกแล้ว ${picked} คลิป` : 'ยังไม่ได้เลือก';
  if (clearSelectionBtn) clearSelectionBtn.hidden = picked === 0;
  if (selectAllVisible) {
    selectAllVisible.disabled = usableVisible.length === 0;
    selectAllVisible.checked = usableVisible.length > 0 && visiblePicked === usableVisible.length;
    selectAllVisible.indeterminate = visiblePicked > 0 && visiblePicked < usableVisible.length;
  }
}

selectAllVisible?.addEventListener('change', () => {
  for (const clip of visibleClips) {
    if (selectAllVisible.checked && !clipBlockReason(clip)) selectedClipKeys.add(selectionKey(clip));
    else if (!selectAllVisible.checked) selectedClipKeys.delete(selectionKey(clip));
  }
  filterAndRenderClips();
});

clearSelectionBtn?.addEventListener('click', () => {
  selectedClipKeys.clear();
  filterAndRenderClips();
});

function renderClipCards(ready) {

  if (ready.length === 0) {

    listEl.innerHTML = '<div class="empty">ไม่พบคลิปที่ตรงกับการค้นหา</div>';

    return;

  }

  listEl.innerHTML = '';

  for (const item of ready) {

    const card = document.createElement('div');

    card.className = 'card';

    if (activeClip && (activeClip.export_id === item.export_id || activeClip.name === item.name)) {

      card.style.borderColor = 'rgba(34, 211, 238, 0.6)';

    }

    const key = selectionKey(item);
    const check = document.createElement('label');
    check.className = 'card-check';
    check.title = 'ติ๊กเพื่อเลือกคลิปนี้ไปโพสต์';
    const blockReason = clipBlockReason(item);
    // a blocked clip keeps its tick (shown unticked): dropping it silently made the batch run the whole queue instead
    const checkInput = document.createElement('input');
    checkInput.type = 'checkbox';
    checkInput.disabled = Boolean(blockReason);
    if (blockReason) check.title = `เลือกไม่ได้: ${blockReason}`;
    checkInput.checked = !blockReason && selectedClipKeys.has(key);
    checkInput.setAttribute('aria-label', `เลือกคลิป ${item.hook_title || item.name || ''}`);
    checkInput.addEventListener('change', () => {
      if (checkInput.checked) selectedClipKeys.add(key); else selectedClipKeys.delete(key);
      card.classList.toggle('selected', checkInput.checked);
      updateSelectionBar();
      updateBatchCountDisplay();
    });
    check.appendChild(checkInput);
    card.classList.toggle('selected', checkInput.checked);

    const thumbWrap = document.createElement('div');

    thumbWrap.className = 'card-thumb-wrap';

    thumbWrap.title = 'คลิกเพื่อพรีวิววิดีโอ 9:16';

    const thumb = document.createElement('img');

    thumb.src = item.thumbnail_url ? scopedPanelMedia(`${BACKEND}${item.thumbnail_url}`) : '';

    thumb.alt = '';

    thumbWrap.appendChild(thumb);

    const playOverlay = document.createElement('div');

    playOverlay.className = 'thumb-play-overlay';

    playOverlay.innerHTML = `

      <div class="thumb-play-icon">

        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"/></svg>

      </div>

    `;

    thumbWrap.appendChild(playOverlay);

    thumbWrap.addEventListener('click', (e) => {

      e.stopPropagation();

      openVideoPreview(item);

    });

    const body = document.createElement('div');

    body.className = 'card-body';

    const lifecycle = getExtensionStatus(item);

    body.innerHTML = `

      <div class="card-product">

        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8 8a2 2 0 0 0 2.828 0l7.172-7.172a2 2 0 0 0 0-2.828z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg>

        ${escapeHtml(item.product_name || 'ไม่ทราบสินค้า')}

      </div>

      <div class="card-hook">${escapeHtml(item.hook_title || item.name)}</div>

      <div class="card-status ${lifecycle.kind}">${escapeHtml(lifecycle.label)}</div>

      <div class="card-meta">

        ${item.schedule_date ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>กำหนด ${escapeHtml(item.schedule_date)} ${escapeHtml(item.schedule_time || '')}` : `${escapeHtml(item.size_mb || '')} MB · ${escapeHtml(item.modified_time || '')}`}

      </div>

    `;

    let btn;
    if (item.is_draft) {
      // A draft already sits on TikTok: tick it and run (publishes at the slot below), or post it now. No manual prepare:
      // that route uploads a file, a draft has none to upload.
      const meta = body.querySelector('.card-meta');
      if (meta) meta.textContent = item.schedule_date
        ? `แบบร่างอยู่บน TikTok · จะเผยแพร่ ${item.schedule_date} ${item.schedule_time || ''}`
        : 'แบบร่างอยู่บน TikTok · ยังไม่มีเวลา เลือกเวลาด้านล่าง';
      const slot = document.createElement('div');
      slot.className = 'draft-slot-controls';
      const label = document.createElement('span');
      label.textContent = 'เวลาเผยแพร่';
      const dateIn = document.createElement('input'); dateIn.type = 'date'; dateIn.value = item.schedule_date || ''; dateIn.setAttribute('aria-label', 'วันที่เผยแพร่');
      const timeIn = document.createElement('input'); timeIn.type = 'time'; timeIn.step = 60; timeIn.value = item.schedule_time || ''; timeIn.setAttribute('aria-label', 'เวลาเผยแพร่');
      const applySlot = () => { item.schedule_date = dateIn.value; item.schedule_time = timeIn.value; filterAndRenderClips(); };
      dateIn.addEventListener('change', applySlot);
      timeIn.addEventListener('change', applySlot);
      slot.append(label, dateIn, timeIn);
      body.appendChild(slot);
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-primary';
      btn.textContent = 'โพสต์ตอนนี้';
      btn.addEventListener('click', () => startDraftPublish(item, { now: true }));
    } else {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-primary';
      btn.innerHTML = `เตรียมคลิปนี้ <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>`;
      btn.addEventListener('click', () => handlePrepareClick(item));
    }
    body.appendChild(btn);

    card.appendChild(check);

    if (blockReason) {
      card.classList.add('blocked');
      const note = document.createElement('div');
      note.className = 'card-blocked-note';
      note.textContent = `ใช้ไม่ได้: ${blockReason}${item.is_draft && /ผ่านแล้ว/.test(blockReason) ? ' — เลือกเวลาใหม่ด้านล่าง' : ''}`;
      body.insertBefore(note, btn);
    }

    card.appendChild(thumbWrap);

    card.appendChild(body);

    listEl.appendChild(card);

  }

}

async function handlePrepareClick(item) {

  if (busy) return;

  if (activeClip && anyStepChecked()) {

    const ok = await askConfirm(

      `คลิปเดิม ("${activeClip.hook_title || activeClip.name}") ยังทำ checklist ไม่จบ -- เปลี่ยนเป็น "${item.hook_title || item.name}" เลยไหม? (ช่องติ๊กทั้งหมดจะรีเซ็ต)`

    );

    if (!ok) return;

  }

  await prepareClip(item);

}

async function prepareClip(item) {
  if (busy) return;
  // the manual route had no guard at all: same rules as the batch (already posted, QC, price text, placeholders, past slot)
  const manualBlock = (() => {
    const guard = globalThis.OmniPostGuard;
    if (!guard) return '';
    const record = exportRecordIndex ? exportRecordIndex.get(item.export_id) : undefined;
    const code = guard.clipSkipReason({ ...item, tiktok_caption: item.tiktok_caption || '' }, record, Date.now(), { exportsKnown: Boolean(exportRecordIndex), ignoreSlot: !(item.schedule_date && item.schedule_time) });
    return code ? (BLOCK_REASON_TH[code] || code) : '';
  })();
  if (manualBlock) {
    setStatus(`เตรียมคลิปนี้ไม่ได้: ${manualBlock}`, 'error');
    return;
  }
  setBusy(true);

  setStatus(`กำลังเตรียม "${item.hook_title || item.name}"...`);

  try {

    await panelWorkerRequest({action:'select-posting-channel', channelId:activeChannelId});

    const preparePayload = {

      video_path: item.rel_path,

      export_id: item.export_id || null,

      cover_path: item.cover_path || null,

      caption: item.tiktok_caption || '',

      hashtags: item.tiktok_hashtags || '',

      product_id: item.product_id || null,

      angle_id: item.angle_id || null,

      tiktok_product_id: item.tiktok_product_id || null,

      product_name: item.product_name || null,

      queue_id: item.is_scheduled ? item.id : null,

      schedule_date: item.schedule_date || null,

      schedule_time: item.schedule_time || null,

    };

    let res = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/prepare`, {

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify(preparePayload),

    });

    if (!res.ok) {

      const errBody = await res.json().catch(() => ({}));

      if (res.status === 409 && (errBody.code === 'posting_export_already_prepared' || errBody.detail?.includes('มีงานโพสต์อยู่แล้ว'))) {

        try {

          const pendingRes = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/pending`);

          if (pendingRes.ok) {

            const pendingData = await pendingRes.json();

            if (pendingData?.job_id && pendingData.status === 'prepared') {

              await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/clear`, {

                method: 'POST',

                headers: { 'Content-Type': 'application/json' },

                body: JSON.stringify({ job_id: pendingData.job_id }),

              });

              res = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/prepare`, {

                method: 'POST',

                headers: { 'Content-Type': 'application/json' },

                body: JSON.stringify(preparePayload),

              });

            }

          }

        } catch (_) {}

      }

      if (!res.ok) {

        const body = await res.json().catch(() => ({}));

        throw new Error(body.detail || errBody.detail || `HTTP ${res.status}`);

      }

    }

    const prepared = await res.json();

    if (prepared.protocol_version !== 2 || prepared.channel_id !== activeChannelId || !prepared.job_id) throw new Error('Backend ไม่รองรับ job/channel protocol ต้องอัปเดต Backend');

    await panelWorkerRequest({action:'claim-posting-job', jobId:prepared.job_id, channelId:activeChannelId});

    activeClip = {...item, job_id:prepared.job_id, channel_id:prepared.channel_id, cover_path: prepared.cover_path || item.cover_path || null};

    if (item.schedule_date) scheduleDateInput.value = item.schedule_date;

    if (item.schedule_time) scheduleTimeInput.value = item.schedule_time;

    syncScheduleConstraints();

    captionInput.value = item.tiktok_caption || '';

    updateCaptionCounter();

    hashtagsInput.value = item.tiktok_hashtags || '';

    productIdInput.value = item.tiktok_product_id || '';

    cartNameInput.value = item.product_name || '';

    resetChecklist();

    renderActiveClipBanner();

    markPostedBtn.disabled = false;

    showTab('checklist');

    try {

      await openTikTokUploadTab();

    } catch (openError) {

      setStatus('เตรียมคลิปแล้ว แต่เปิดหน้าอัปโหลดไม่สำเร็จ: ' + openError.message, 'error');

      return;

    }

    setStatus('เตรียมคลิปแล้ว และเปิดหน้าอัปโหลดให้แล้ว ทำต่อได้เลย', 'success');

  } catch (err) {

    setStatus('เตรียมคลิปไม่สำเร็จ: ' + err.message, 'error');

  } finally {

    setBusy(false);

  }

}

refreshBtn.addEventListener('click', loadExports);

// ── Checklist steps (each its own short attach/act/detach cycle in

// background.js -- see wireStep for why) ───────────────────────────────────

function wireStep(btnId, chkId, stepName, buildMessage, successText) {

  const btn = document.getElementById(btnId);

  const chk = document.getElementById(chkId);

  btn.addEventListener('click', () => {

    if (busy) return;

    setBusy(true);

    chk.checked = false;

    chk.closest('.step-row')?.classList.remove('completed');

    setStatus(`กำลังทำ ${stepName}...`);

    let message;

    try {

      message = buildMessage();

    } catch (err) {

      setBusy(false);

      setStatus(err.message || String(err), 'error');

      return;

    }

    try {

      chrome.runtime.sendMessage(message, (response) => {

        setBusy(false);

        if (chrome.runtime.lastError) {

          setStatus('เกิดข้อผิดพลาด (อาจเป็นเพราะแท็บแครช): ' + chrome.runtime.lastError.message, 'error');

          return;

        }

        if (!response) {

          setStatus('ไม่ได้รับคำตอบจาก Extension', 'error');

          return;

        }

        if (response.success) {

          chk.checked = true;

          chk.closest('.step-row')?.classList.add('completed');

          updatePipelineProgress();

          const messageText = typeof successText === 'function' ? successText(response) : successText;

          setStatus(messageText + (response.warning ? ` — ${response.warning}` : ''), 'success');

        } else {

          setStatus(response.error || response.reason || 'เกิดข้อผิดพลาดไม่ทราบสาเหตุ', 'error');

        }

      });

    } catch (err) {

      setBusy(false);

      setStatus('เกิดข้อผิดพลาดในการส่งคำสั่ง: ' + (err.message || String(err)), 'error');

    }

  });

}

wireStep('btn1', 'chk1', 'ขั้น 1 (อัปโหลดไฟล์)',

  () => ({ action: 'upload-file-only' }),

  'ขั้น 1 สำเร็จ -- ตั้งไฟล์แล้ว รอปกขึ้นครบเองด้วยตาก่อนทำขั้นถัดไป');

wireStep('btn2', 'chk2', 'ขั้น 2 (พิมพ์คำอธิบาย/แฮชแท็ก)',

  () => {

    const caption = captionInput.value.trim();

    const hashtags = hashtagsInput.value.trim();

    if (!caption && !hashtags) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็กก่อน');

    return { action: 'type-caption-only', caption, hashtags };

  },

  'ขั้น 2 สำเร็จ -- พิมพ์คำอธิบาย/แฮชแท็กแล้ว');

wireStep('btn3', 'chk3', 'ขั้น 3 (ปักตะกร้าสินค้า)',

  () => {

    const productId = productIdInput.value.trim();

    if (!productId) throw new Error('กรุณากรอก ID สินค้าก่อน');

    return { action: 'attach-product-only', productId, cartName: cartNameInput.value.trim() };

  },

  'ขั้น 3 สำเร็จ -- ปักตะกร้าสินค้าแล้ว');

wireStep('btn4', 'chk4', 'ขั้น 4 (สลับเป็นกำหนดเวลา)',

  () => ({ action: 'schedule-mode-only', date: scheduleDateInput.value, time: scheduleTimeInput.value }),

  response => {

    if (response.adjustedTime && response.requestedTime) scheduleTimeInput.value = response.requestedTime;

    const when = `${response.requestedDate || scheduleDateInput.value} ${response.requestedTime || scheduleTimeInput.value}`.trim();

    const adjusted = response.adjustedTime ? ' (ปรับเวลาเป็นช่วงละ 5 นาทีตาม TikTok)' : '';

    return `ขั้น 4 สำเร็จ -- เปลี่ยนเป็นกำหนดเวลา ${when} แล้ว${adjusted} กดขั้น 5 เมื่อต้องการโพสต์`;

  });

wireStep('btn5', 'chk5', 'ขั้น 6 (กด Post/กำหนดเวลา)',

  () => ({ action: 'click-post-only' }),

  response => {

    if (response.outcome === 'scheduled_on_platform') {

      activeClip = null; resetChecklist(); renderActiveClipBanner(); loadExports(); showTab('list'); scrollToTop();

      return 'TikTok ยืนยันนัดเวลาแล้ว ยังไม่นับว่าโพสต์เผยแพร่';

    }

    if (response.marked) {

      const postedTitle = activeClip?.hook_title || activeClip?.name || 'คลิป';

      activeClip = null;

      resetChecklist();

      renderActiveClipBanner();

      loadExports();

      showTab('list');

      scrollToTop();

      return postedTitle + ' โพสต์และมาร์คเป็นโพสต์แล้วอัตโนมัติ พร้อมเตรียมหน้าอัปโหลดสำหรับคลิปถัดไป';

    }

    return 'โพสต์ขึ้น TikTok แล้ว แต่ยังมาร์คใน OmniCut ไม่สำเร็จ: ' + (response.markError || 'ลองกดมาร์คอีกครั้ง');

  });

wireStep('btn6', 'chk6', 'แนบภาพปก',

  () => {

    if (!activeClip) throw new Error('ยังไม่ได้เลือกคลิป — ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน');

    return {action:'upload-cover-only', coverPath: activeClip.cover_path || ''};

  },

  'ส่งภาพปกและบันทึกแล้ว ตรวจภาพตัวอย่างบน TikTok ก่อนโพสต์');

const prepareDetailsBtn = document.getElementById('prepareDetailsBtn');

// 1-Click Automation: Executes Step 1 through Step 5 sequentially.

// - If Step 1 (upload) is not done, it uploads the video file first, marks Step 1,

//   and automatically proceeds to Steps 2-5 (caption, product, schedule, cover).

// - If Step 1 was already completed, it runs Steps 2-5 directly.

// - Enabled whenever an active clip is selected.

function syncPrepareDetailsBtnState() {

  if (!activeClip) {

    prepareDetailsBtn.disabled = true;

    prepareDetailsBtn.title = 'กรุณาเลือกคลิปจากแท็บ "รายการคลิป" ก่อน';

    prepareDetailsBtn.innerHTML = `

      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>

      เลือกคลิปก่อนเริ่มงาน

    `;

    return;

  }

  prepareDetailsBtn.disabled = false;

  const uploaded = document.getElementById('chk1')?.checked;

  if (!uploaded) {

    prepareDetailsBtn.title = 'คลิกเดียวรันอัตโนมัติตั้งแต่ขั้น 1 (อัปโหลด) จนถึงขั้น 5 (แนบภาพปก)';

    prepareDetailsBtn.innerHTML = `

      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>

      ดำเนินการอัตโนมัติ (ขั้น 1 ถึง 5)

    `;

  } else {

    prepareDetailsBtn.title = 'ทำต่อขั้นตอนที่ 2 ถึง 5 (พิมพ์คำอธิบาย, ปักตะกร้า, สลับตั้งเวลา, แนบภาพปก)';

    prepareDetailsBtn.innerHTML = `

      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>

      ทำต่อขั้นตอน 2 ถึง 5 (Auto-Fill & Cover)

    `;

  }

}

document.getElementById('chk1')?.addEventListener('change', syncPrepareDetailsBtnState);

syncPrepareDetailsBtnState();

// Same idea for the schedule checkbox -- ticking it with no date/time

// chosen yet just carries empty strings into runScheduleModeOnly, which

// then fails on TikTok's page instead of here where the problem is obvious.

const prepareScheduleCheckbox = document.getElementById('prepareSchedule');

function syncPrepareScheduleCheckboxState() {

  const hasDateTime = Boolean(scheduleDateInput.value && scheduleTimeInput.value);

  prepareScheduleCheckbox.disabled = !hasDateTime;

  prepareScheduleCheckbox.title = hasDateTime ? '' : 'เลือกวันเวลาก่อน';

  if (!hasDateTime) prepareScheduleCheckbox.checked = false;

}

scheduleDateInput.addEventListener('change', syncPrepareScheduleCheckboxState);

scheduleTimeInput.addEventListener('change', syncPrepareScheduleCheckboxState);

syncPrepareScheduleCheckboxState();

prepareDetailsBtn.addEventListener('click', async () => {

  if (busy) return;

  if (!activeClip) {

    setStatus('ยังไม่ได้เลือกคลิป — ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน', 'error');

    return;

  }

  if (!activeClip?.cover_path) {

    try {

      const curRes = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/jobs/${encodeURIComponent(activeClip.job_id || '')}`);

      if (curRes.ok) {

        const fresh = await curRes.json();

        if (fresh.cover_path) activeClip.cover_path = fresh.cover_path;

      }

    } catch (_) {}

  }

  if (!activeClip?.cover_path) {

    setStatus('ยังไม่มีภาพปกสำหรับคลิปนี้ กรุณาบันทึกภาพปกก่อนดำเนินการ', 'error');

    return;

  }

  if (!productIdInput.value.trim()) {

    setStatus('กรุณากรอก ID สินค้าสำหรับปักตะกร้าก่อนดำเนินการ', 'error');

    return;

  }

  const scheduleMode = document.getElementById('prepareSchedule').checked;

  setBusy(true);

  try {

    const chk1 = document.getElementById('chk1');

    // ขั้น 1: หากยังไม่ได้อัปโหลดวิดีโอ ให้ส่งคำสั่งอัปโหลดไฟล์ก่อน

    if (!chk1?.checked) {

      setStatus('ขั้นที่ 1/5: กำลังอัปโหลดไฟล์วิดีโอเข้าสู่ TikTok Studio...');

      const uploadResp = await new Promise((resolve, reject) => {

        chrome.runtime.sendMessage({ action: 'upload-file-only' }, (res) => {

          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));

          if (!res) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ในขั้นอัปโหลด'));

          resolve(res);

        });

      });

      if (!uploadResp?.success) {

        throw new Error(`ขั้น 1 ไม่สำเร็จ: ${uploadResp?.error || uploadResp?.reason || 'อัปโหลดไฟล์ไม่สำเร็จ'}`);

      }

      chk1.checked = true;

      chk1.closest('.step-row')?.classList.add('completed');

      updatePipelineProgress();

      setStatus('ขั้นที่ 1 สำเร็จ: ตั้งไฟล์วิดีโอแล้ว กำลังส่งต่อประมวลผลขั้น 2 ถึง 5 อัตโนมัติ...');

      // ให้เวลาหน้า TikTok DOM อัปเดตสถานะไฟล์เข้าฟอร์ม

      await new Promise(r => setTimeout(r, 1200));

    }

    // ขั้น 2 - 5: เตรียมสถานะก่อนเริ่ม

    [2, 3, 6, ...(scheduleMode ? [4] : [])].forEach(n => {

      const checkbox = document.getElementById(`chk${n}`);

      if (checkbox) {

        checkbox.checked = false;

        checkbox.closest('.step-row')?.classList.remove('completed');

      }

    });

    setStatus('กำลังประมวลผลอัตโนมัติ: พิมพ์คำอธิบาย, ปักตะกร้า, ตั้งเวลา และแนบปก (ขั้น 2 ถึง 5)...');

    const response = await new Promise((resolve, reject) => {

      chrome.runtime.sendMessage({

        action: 'prepare-details',

        caption: captionInput.value.trim(),

        hashtags: hashtagsInput.value.trim(),

        productId: productIdInput.value.trim(),

        scheduleMode,

        cartName: cartNameInput.value.trim(),

        scheduleDate: scheduleDateInput.value,

        scheduleTime: scheduleTimeInput.value,

        coverPath: activeClip.cover_path,
        coverFallback: Boolean(document.getElementById('coverFallbackToggle')?.checked),

      }, (res) => {

        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));

        if (!res) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ในการเตรียมรายละเอียด'));

        resolve(res);

      });

    });

    const checks = { caption: 2, product: 3, cover: 6, schedule: 4 };

    for (const step of response?.completed || []) {

      const checkbox = document.getElementById(`chk${checks[step]}`);

      if (checkbox) {

        checkbox.checked = true;

        checkbox.closest('.step-row')?.classList.add('completed');

      }

    }

    updatePipelineProgress();

    if (!response?.success) throw new Error(response?.error || 'ไม่ได้รับผลการทำงาน');

    setStatus('ดำเนินการครบขั้น 1 ถึง 5 เรียบร้อยแล้ว! ตรวจทานข้อมูลบนหน้า TikTok แล้วกดปุ่มโพสต์ (ขั้น 6) เพื่อเผยแพร่', 'success');

  } catch (err) {

    setStatus(`หยุดการทำงาน: ${err.message} — ขั้นที่ผ่านแล้วมีเครื่องหมายถูก สามารถทำขั้นที่ค้างแยกได้`, 'error');

  } finally {

    setBusy(false);

  }

});

// ── Copy caption + hashtags together (TikTok's own caption box takes both

// in one field -- typing them separately in our extension is just for

// editing convenience, so let a copy-paste user grab both at once) ──────

copyAllBtn.addEventListener('click', async () => {

  const caption = captionInput.value.trim();

  const hashtags = hashtagsInput.value.trim();

  const combined = [caption, hashtags].filter(Boolean).join('\n\n');

  if (!combined) {

    setStatus('ยังไม่มีคำอธิบายหรือแฮชแท็กให้คัดลอก', 'error');

    return;

  }

  try {

    await navigator.clipboard.writeText(combined);

  } catch (err) {

    setStatus('คัดลอกไม่สำเร็จ: ' + err.message, 'error');

    return;

  }

  copyAllBtn.classList.add('copied');

  const originalHtml = copyAllBtn.innerHTML;

  copyAllBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> คัดลอกแล้ว';

  setTimeout(() => {

    copyAllBtn.classList.remove('copied');

    copyAllBtn.innerHTML = originalHtml;

  }, 1500);

});

// ── Mark posted (manual, never touches TikTok -- see .mark-posted-card) ──

markPostedBtn.addEventListener('click', async () => {

  if (!activeClip) {

    setStatus('ยังไม่ได้เลือกคลิป -- ไปแท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน', 'error');

    return;

  }

  markPostedBtn.disabled = true;

  const postedTitle = activeClip.hook_title || activeClip.name || 'คลิป';

  setStatus(`กำลังมาร์ค "${postedTitle}" ว่าโพสต์แล้ว...`);

  try {

    // Only the original job receipt may authorize local publication effects.

    const result = await panelWorkerRequest({action: 'reconcile-posting-result', manual: true});

    if (result.outcome !== 'published' && result.outcome !== 'scheduled_on_platform') {

      throw new Error('Publication is not confirmed; no posted status was recorded');

    }

    activeClip = null;

    resetChecklist();

    renderActiveClipBanner();

    await loadExports();

    showTab('list');

    scrollToTop();

    // รีเฟรชหน้าอัปโหลด TikTok Studio เตรียมพร้อมสำหรับคลิปถัดไป เหมือนขั้นตอนที่ 6

    try {

      await openTikTokUploadTab(true);

    } catch (tabErr) {}

    setStatus(postedTitle + ' มาร์คว่าโพสต์แล้วเรียบร้อย (ผู้ใช้ยืนยัน) พร้อมเตรียมหน้าอัปโหลดสำหรับคลิปถัดไป', 'success');

    scrollToTop();

  } catch (err) {

    setStatus('มาร์คไม่สำเร็จ: ' + err.message, 'error');

  } finally {

    markPostedBtn.disabled = !activeClip;

  }

});

// ── Stats Sync: read Studio Posts table, POST rows to backend ──────────────

const syncStatsBtn = document.getElementById('syncStatsBtn');

// Build tag: proves which build this side panel is actually running. If this

// line is missing from the Tools tab, Chrome is running stale cached code --

// the exact cause of the ghost domain-restricted banner that no longer exists

// anywhere in this source.

const buildTag = document.getElementById('buildTag');

if (buildTag) {

  buildTag.textContent = 'build ' + (chrome?.runtime?.getManifest?.().version || 'unknown');

}

const brandVersionPill = document.getElementById('brandVersionPill');

if (brandVersionPill) {

  const v = chrome?.runtime?.getManifest?.().version;

  if (v) brandVersionPill.textContent = 'v' + v;

}

async function ensureStatsParser(tabId) {

  // executeScript runs func in an isolated world without the sidepanel's own

  // scripts, so inject the pure parser file first, then call it.

  await chrome.scripting.executeScript({ target: { tabId }, files: ['stats_parser.js'] });

}

const TIKTOK_URL_RE = /tiktok\.com/i;

// Read the page's own URL as the source of truth -- tab.url can come back

// undefined in some permission edge cases even with the "tabs" permission,

// and then a URL-string check silently rejects a perfectly good Studio page.

async function tiktokHrefOf(tabId, tabUrl) {

  if (tabUrl && TIKTOK_URL_RE.test(tabUrl)) return tabUrl;

  try {

    const [probe] = await chrome.scripting.executeScript({

      target: { tabId },

      func: () => location.href,

    });

    if (probe?.result && TIKTOK_URL_RE.test(probe.result)) return probe.result;

  } catch (_) { /* not injectable (e.g. a chrome:// page) */ }

  return null;

}

// Active tab first (focused window, then current), then any open TikTok tab --

// the Studio tab often lives in another window while the side panel is docked

// elsewhere. Never throws: resolves to { tabId, href } or { blocked: reason }.

async function resolveTikTokTab() {

  const seen = [];

  for (const q of [

    { active: true, lastFocusedWindow: true },

    { active: true, currentWindow: true },

  ]) {

    try {

      const [tab] = await chrome.tabs.query(q);

      if (!tab?.id) continue;

      seen.push(tab.url || '(แท็บที่ active อ่าน URL ไม่ได้)');

      const href = await tiktokHrefOf(tab.id, tab.url);

      if (href) return { tabId: tab.id, href };

    } catch (_) { /* window/tab vanished mid-query */ }

  }

  try {

    const tabs = await chrome.tabs.query({ url: ['*://*.tiktok.com/*', '*://tiktok.com/*'] });

    for (const tab of tabs) {

      const href = await tiktokHrefOf(tab.id, tab.url);

      if (href) {

        try { await chrome.tabs.update(tab.id, { active: true }); } catch (_) { /* background window */ }

        return { tabId: tab.id, href };

      }

    }

  } catch (_) { /* query unsupported */ }

  if (seen.length) {

    return { blocked: `แท็บที่ active ตอนนี้ไม่ใช่ TikTok (${seen[0]}) — สลับไปหน้า TikTok Studio แท็บ โพสต์ แล้วกดซิงก์อีกครั้ง` };

  }

  return { blocked: 'ไม่พบแท็บ TikTok ที่เปิดอยู่ — เปิดหน้า TikTok Studio แท็บ โพสต์ แล้วกดซิงก์อีกครั้ง' };

}

async function runStatsSync() {

  const capturedChannel = activeChannelId;

  const capturedEpoch = channelEpoch;

  if (!window.OmniCutStatsParser) {

    setStatus('โหลดตัวอ่านตารางไม่สำเร็จ — ลองปิดแล้วเปิดแถบข้างใหม่', 'error');

    return;

  }

  if (typeof chrome === 'undefined' || !chrome.scripting?.executeScript) {

    setStatus('extension เวอร์ชันนี้ยังไม่มีสิทธิ์อ่านหน้าเว็บ — โหลด extension ใหม่จาก chrome://extensions', 'error');

    return;

  }

  syncStatsBtn.disabled = true;

  setStatus('กำลังอ่านตารางโพสต์จากหน้านี้...');

  try {

    const found = await resolveTikTokTab();

    if (found.blocked) throw new Error(found.blocked);

    await ensureStatsParser(found.tabId);

    const injected = await chrome.scripting.executeScript({

      target: { tabId: found.tabId },

      func: () => {

        const result = window.OmniCutStatsParser.parsePostsTable(document);

        const nodes = document.querySelectorAll('[data-e2e="profile-icon"] a[href*="/@"], a[data-e2e="profile-icon"][href*="/@"], [data-e2e="user-avatar"] a[href*="/@"], [data-e2e="account-menu"] a[href*="/@"], [data-e2e="account-handle"], [data-e2e="user-unique-id"]');

        const handles = [...new Set(Array.from(nodes).map(el => {

          const raw = el.getAttribute('href') || (el.textContent || '').trim();

          return (raw.match(/@([a-zA-Z0-9._]+)/)?.[0] || raw).toLowerCase();

        }).filter(Boolean))];

        if (handles.length > 1) return {error:'อ่านบัญชี Studio ได้หลายบัญชี ต้องตรวจบัญชีก่อนซิงก์'};

        return {...result, source_account:handles[0] || null};

      },

    });

    const result = injected?.[0]?.result;

    if (!result) throw new Error('อ่านหน้า TikTok ไม่ได้ — รีเฟรชหน้า Studio แล้วลองใหม่');

    if (result.error) throw new Error(result.error);

    if (!result.rows.length) throw new Error('ไม่พบแถวโพสต์ในตาราง — เลื่อนลงให้ตารางโหลดก่อนกดซิงก์');

    if (activeChannelId !== capturedChannel || channelEpoch !== capturedEpoch) throw new Error('ช่องเปลี่ยนระหว่างอ่าน Studio ต้องเริ่มซิงก์ใหม่');

    setStatus(`พบ ${result.rows.length} โพสต์ กำลังส่งเข้า OmniCut...`);

    const res = await scopedPanelFetch(`${BACKEND}/api/tiktok-stats/import`, {

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify({ rows: result.rows, source_account: result.source_account || null }),

    });

    const body = await res.json().catch(() => ({}));

    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);

    const unmatched = (body.unmatched || []).length;

    const registered = body.registered || 0;

    setStatus(

      `ซิงก์สำเร็จ ${body.matched}/${body.total} คลิป อัปเดตตัวเลข ${body.updated} คลิป${registered ? ` ลงทะเบียนโพสต์ใหม่ ${registered} รายการ` : ''}${unmatched ? ` (รอตรวจ ${unmatched} คลิป ดูในแท็บผลงาน)` : ''}${body.account_check?.warning ? ' — อ่านบัญชีไม่ได้ เก็บรอตรวจสอบ ยังไม่อัปเดตสถิติ กรุณาซิงก์จากบัญชีที่ยืนยันได้' : ''}`,

      'success',

    );

  } catch (err) {

    setStatus('ซิงก์ไม่สำเร็จ: ' + err.message, 'error');

  } finally {

    syncStatsBtn.disabled = false;

  }

}

syncStatsBtn?.addEventListener('click', runStatsSync);

// ── Open TikTok Studio Upload Tab ─────────────────────────────────────────

const TIKTOK_UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';

async function findExistingTikTokTab() {

  if (typeof chrome === 'undefined' || !chrome.tabs) return null;

  try {

    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (

      activeTab?.url &&

      activeTab.url.includes('tiktok.com') &&

      (activeTab.url.includes('upload') || activeTab.url.includes('studio') || activeTab.url.includes('creator'))

    ) {

      return activeTab;

    }

  } catch (e) {}

  const patterns = [

    'https://www.tiktok.com/tiktokstudio/upload*',

    'https://www.tiktok.com/creator-center/upload*',

    '*://*.tiktok.com/*upload*',

    '*://*.tiktok.com/tiktokstudio*',

  ];

  for (const pattern of patterns) {

    try {

      const tabs = await chrome.tabs.query({ url: pattern });

      if (tabs && tabs.length > 0) return tabs[0];

    } catch (e) {}

  }

  return null;

}

async function openTikTokUploadTab(forceReload = false) {

  if (typeof chrome !== 'undefined' && chrome.tabs) {

    const tab = await findExistingTikTokTab();

    if (tab && tab.id) {

      let target = tab;

      if (forceReload || !String(tab.url || '').includes('/upload')) {

        target = await chrome.tabs.update(tab.id, {

          url: TIKTOK_UPLOAD_URL,

          active: true,

        });

      } else {

        target = await chrome.tabs.update(tab.id, {active: true});

      }

      if (target.windowId && chrome.windows) {

        await chrome.windows.update(target.windowId, {focused: true});

      }

      setStatus('เปิดหน้าอัปโหลด TikTok Studio ให้แล้ว', 'success');

      return target;

    }

    const created = await chrome.tabs.create({url: TIKTOK_UPLOAD_URL, active: true});

    if (created?.windowId && chrome.windows) {

      await chrome.windows.update(created.windowId, {focused: true});

    }

    setStatus('เปิดหน้าอัปโหลด TikTok Studio ให้แล้ว', 'success');

    return created;

  }

  window.open(TIKTOK_UPLOAD_URL, '_blank');

  return null;

}

document.getElementById('headerOpenTikTokBtn')?.addEventListener('click', openTikTokUploadTab);

[1, 2, 3, 4, 5, 6].forEach((n) => {

  document.getElementById(`chk${n}`)?.addEventListener('change', updatePipelineProgress);

});

renderActiveClipBanner();

apiKeyReady.then(loadExports);

initializeChannelSelector().catch(err => setStatus(err.message, 'error'));

updatePipelineProgress();

window.addEventListener('focus', () => {

  if (headerStatusPill?.classList.contains('is-offline')) {

    loadExports();

  }

});

// ── Batch Auto-Post Controller & Port Keep-Alive ───────────────────────────

let keepAlivePort = null;

let keepAliveTimer = null;

function startKeepAlive() {

  if (keepAliveTimer) return;

  try {

    if (!keepAlivePort && typeof chrome !== 'undefined' && chrome.runtime?.connect) {

      keepAlivePort = chrome.runtime.connect({ name: 'batch-runner-channel' });

      keepAlivePort.onDisconnect.addListener(() => { keepAlivePort = null; });

    }

  } catch (_) {}

  keepAliveTimer = setInterval(() => {

    try {

      if (!keepAlivePort && typeof chrome !== 'undefined' && chrome.runtime?.connect) {

        keepAlivePort = chrome.runtime.connect({ name: 'batch-runner-channel' });

        keepAlivePort.onDisconnect.addListener(() => { keepAlivePort = null; });

      }

      keepAlivePort?.postMessage({ type: 'ping' });

    } catch (_) {}

  }, 15000);

}

function stopKeepAlive() {

  if (keepAliveTimer) {

    clearInterval(keepAliveTimer);

    keepAliveTimer = null;

  }

  if (keepAlivePort) {

    try { keepAlivePort.disconnect(); } catch (_) {}

    keepAlivePort = null;

  }

}

let activeRecorder = null;   // OmniRunHistory recorder of the run in progress
function appendBatchLog(msg, kind = 'info') {
  try { activeRecorder?.log(kind, msg); } catch (_) {}
  if (!batchLogBox) return;

  const entry = document.createElement('div');

  entry.className = `batch-log-entry ${kind}`;

  const time = new Date().toLocaleTimeString('th-TH', { hour12: false });

  entry.textContent = `[${time}] ${msg}`;

  batchLogBox.appendChild(entry);

  batchLogBox.scrollTop = batchLogBox.scrollHeight;

}

// Drops clips that must not be posted unattended (stale/posted/QC-rejected export, price text in the
// caption, a schedule slot that already passed) and reports why, so nothing is skipped silently.
function guardBatchClips(clips) {
  const guard = globalThis.OmniPostGuard;
  if (!guard) return { kept: clips, skipped: [] };
  const kept = [];
  const skipped = [];
  const now = Date.now();
  for (const clip of clips) {
    const record = exportRecordIndex ? exportRecordIndex.get(clip.export_id) : undefined;
    const reason = blockCodeFor(clip, record, now);
    if (reason) skipped.push({ title: clip.hook_title || clip.name || clip.id, reason });
    else kept.push(clip);
  }
  return { kept, skipped };
}

// ── Pre-run readiness, run history, attention notices ──────────────────────
function newRunRecorder() {
  const history = globalThis.OmniRunHistory;
  const storage = typeof chrome !== 'undefined' ? chrome.storage?.local : null;
  return history && storage ? history.createRunRecorder({ storage }) : null;
}
async function gatherPreflight(mode, clipCount) {
  const backend = { ok: false };
  try {
    const res = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/capabilities`);
    backend.status = res.status;
    backend.ok = res.ok;
    if (res.ok) Object.assign(backend, await res.json().catch(() => ({})));
  } catch (err) { backend.error = err.message; }
  let worker;
  try { worker = await panelWorkerRequest({ action: 'run-preflight' }); }
  catch (err) { worker = { success: false, error: err.message }; }
  return globalThis.OmniPreflight.evaluatePreflight({
    backend, worker, mode, clipCount,
    channel: { id: activeChannelId, handle: channelHandles.get(activeChannelId) || '' },
  });
}
// Runs the check and prints it into the batch log. Returns the verdict ({ok, blockers, warnings, checks}).
async function runPreflightAndReport(mode, clipCount) {
  if (!globalThis.OmniPreflight) return { ok: false, blockers: [{ id: 'module', label: 'โมดูลตรวจความพร้อม', detail: 'ไม่พบ preflight.js — โหลดส่วนขยายใหม่' }], warnings: [], checks: [] };
  if (batchDashboard) batchDashboard.hidden = false;
  appendBatchLog('ตรวจความพร้อมก่อนรัน...', 'info');
  const result = await gatherPreflight(mode, clipCount);
  for (const check of result.checks) {
    appendBatchLog(`${check.status === 'ok' ? 'ผ่าน' : check.status === 'warn' ? 'เตือน' : 'ไม่ผ่าน'} · ${check.label}${check.detail ? ` — ${check.detail}` : ''}`, check.status === 'fail' ? 'error' : check.status === 'warn' ? 'warn' : 'success');
  }
  return result;
}
function notifyAttentionIfNeeded(verdict) {
  const needsPerson = ['unknown', 'partial', 'halted', 'error'].includes(verdict.finalKind);
  if (!needsPerson) return;
  panelWorkerRequest({ action: 'notify-attention', title: 'OmniCut: รอบโพสต์ต้องให้ตรวจ', message: verdict.text }).catch(() => {});
}
panelWorkerRequest({ action: 'clear-attention' }).catch(() => {});

// ── One run at a time (this panel and every other open panel) ───────────────
const PANEL_RUN_ID = `panel-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
let batchStarting = false;            // set synchronously on the first click, before any await
let runLockBeatTimer = null;
const lockStorage = () => (typeof chrome !== 'undefined' ? chrome.storage?.local : null);
function startRunLockBeat() {
  stopRunLockBeat();
  runLockBeatTimer = setInterval(() => {
    const storage = lockStorage();
    if (storage) globalThis.OmniRunLock?.beat(storage, PANEL_RUN_ID).catch(() => {});
  }, globalThis.OmniRunLock?.BEAT_MS || 10000);
}
function stopRunLockBeat() { if (runLockBeatTimer) { clearInterval(runLockBeatTimer); runLockBeatTimer = null; } }
async function releaseRunLock() {
  stopRunLockBeat();
  const storage = lockStorage();
  if (storage) { try { await globalThis.OmniRunLock?.release(storage, PANEL_RUN_ID); } catch (_) {} }
}
// A run that is cut off (panel closed/reloaded, browser crash) leaves its job claimed and the loop gone: park the job
// so it can never be posted twice, and say so.
async function recoverInterruptedRun() {
  const storage = lockStorage();
  const lockApi = globalThis.OmniRunLock;
  if (!storage || !lockApi) return;
  try {
    const orphan = await lockApi.takeOrphan(storage);
    if (!orphan) return;
    appendBatchLog('รอบรันก่อนหน้าถูกตัดกลางคัน (ปิดแผง/รีโหลด/เบราว์เซอร์ปิด) — พักงานที่ค้างไว้ ตรวจที่ TikTok Studio > Content ก่อนรันใหม่', 'warn');
    await panelWorkerRequest({ action: 'release-posting-job', park: true }).catch((err) => appendBatchLog(`พักงานที่ค้างไม่สำเร็จ: ${err.message}`, 'error'));
    setStatus('รอบรันก่อนหน้าถูกตัดกลางคัน — พักงานที่ค้างแล้ว ตรวจผลบน TikTok ก่อนรันใหม่', 'warn');
  } catch (_) {}
}
window.addEventListener('beforeunload', (event) => {
  if (batchStarting || activeBatchRunner) { event.preventDefault(); event.returnValue = ''; }
});
recoverInterruptedRun();

batchStartBtn?.addEventListener('click', async () => {
  if (busy || batchStarting) return;
  batchStarting = true;   // synchronous: a double click or a second event can never reach the confirm dialog twice
  try {
    await runBatchFromPanel();
  } finally {
    batchStarting = false;
    await releaseRunLock();   // idempotent; covers every early exit after the lock was taken
  }
});

// The clips a normal (list) run will post: the ticked ones, or the filtered queue, minus what the guard refuses, capped by quota.
function selectBatchClipsFromList() {
  const query = clipSearchInput ? clipSearchInput.value.trim().toLowerCase() : '';

  // Ticked clips win over the search box and the count limit: post exactly those, in list order.
  const { usingPicked, candidates: searchedClips } = pickBatchCandidates({
    allClips,
    selectedKeys: selectedClipKeys,
    keyOf: selectionKey,
    matchesQuery: (c) => !c.is_draft && (!query
      || (c.product_name || '').toLowerCase().includes(query)
      || (c.hook_title || '').toLowerCase().includes(query)
      || (c.name || '').toLowerCase().includes(query)),
  });
  const { kept: targetClips, skipped: guardSkipped } = guardBatchClips(searchedClips);

  if (!targetClips.length) {
    setStatus(usingPicked
      ? `คลิปที่ติ๊กไว้ใช้ไม่ได้ทั้งหมด (${guardSkipped.map((item) => item.reason).slice(0, 3).join(', ')}) จึงไม่เริ่มรัน และไม่ไปรันคลิปอื่นแทน`
      : 'ไม่มีคลิปในรายการสำหรับเริ่มอัปโหลด', 'error');
    return null;

  }

  const effectiveLimit = getEffectiveBatchLimit(targetClips.length, { forceAuto: usingPicked });
  if (effectiveLimit === 0) {
    setStatus('โควตาใน TikTok Studio เต็มแล้ว (30/30) กรุณารอให้คลิปเผยแพร่หรือลบแบบร่างเดิมก่อน', 'error');
    return null;
  }

  // Capped by TikTok Quota (maximum 30 per run)
  const slicedClips = targetClips.slice(0, effectiveLimit);
  return { usingPicked, guardSkipped, targetClips, slicedClips };
}

async function runBatchFromPanel(override = null) {

  const selection = override ? { usingPicked: true, guardSkipped: [], targetClips: override.clips, slicedClips: override.clips } : selectBatchClipsFromList();
  if (!selection) return;
  const { usingPicked, guardSkipped, targetClips, slicedClips } = selection;

  const selectedModeForCheck = override ? override.mode : (batchModeSelect?.value || 'smart');
  const readiness = await runPreflightAndReport(selectedModeForCheck, slicedClips.length);
  if (!readiness.ok) {
    setStatus(`ยังไม่พร้อมรัน: ${readiness.blockers.map((b) => `${b.label} (${b.detail})`).join('; ')}`, 'error');
    return;
  }

  const confirmMsg = override ? override.confirmText : usingPicked
    ? `ต้องการโพสต์เฉพาะคลิปที่ติ๊กเลือก ${slicedClips.length} คลิปใช่หรือไม่?` +
      (guardSkipped.length ? `
(ข้าม ${guardSkipped.length} คลิปที่ใช้ไม่ได้ เช่น ไฟล์หาย/เวลาผ่านแล้ว/มีราคาใน caption)` : '') +
      (slicedClips.length < targetClips.length ? `
(โควตา TikTok Studio รับได้ ${slicedClips.length} จาก ${targetClips.length} คลิปที่ติ๊ก)` : '')
    : `ต้องการเริ่มรันอัปโหลดอัตโนมัติ ${slicedClips.length} คลิปใช่หรือไม่?
(จำกัดตามโควตา TikTok Studio สูงสุด 30 รายการ จากคิวทั้งหมด ${targetClips.length} คลิป)`;

  const warnNote = readiness.warnings.length ? `\n\nคำเตือน: ${readiness.warnings.map((w) => `${w.label} — ${w.detail}`).join(' | ')}` : '';
  const ok = await askConfirm(confirmMsg + warnNote);
  if (!ok) return;
  const lockStore = lockStorage();
  if (!lockStore || !globalThis.OmniRunLock) {
    setStatus('ไม่พบตัวล็อกรอบ (run_lock.js) จึงไม่เริ่มรัน เพื่อกันรันซ้อน', 'error');
    return;
  }
  const lockResult = await globalThis.OmniRunLock.acquire(lockStore, PANEL_RUN_ID);
  if (!lockResult.ok) {
    setStatus('มีอีกแผง/อีกหน้าต่างกำลังรันอยู่ (หรือเพิ่งเริ่มพร้อมกัน) จึงไม่เริ่มรอบนี้ — รอให้รอบนั้นจบก่อน', 'error');
    return;
  }
  startRunLockBeat();
  activeRecorder = newRunRecorder();
  await activeRecorder?.start({ mode: override ? override.mode : (batchModeSelect?.value || 'smart'), kind: override ? 'publish_draft' : 'batch', channel: activeChannelId, clips: slicedClips.length, extension: chrome.runtime.getManifest?.().version, panel: PANEL_RUN_ID });
  if (lockResult.recovered) appendBatchLog('พบรอบรันเก่าที่ถูกตัดกลางคัน — งานที่ค้างจะถูกพักก่อนเริ่มคลิปแรก', 'warn');
  try {
    await openTikTokUploadTab(false);

  } catch (_) {}

  setBusy(true);

  if (batchStartBtn) batchStartBtn.disabled = true;

  if (batchDashboard) batchDashboard.hidden = false;

  if (batchLogBox) batchLogBox.innerHTML = '';




  startKeepAlive();

  const selectedMode = override ? (override.mode === 'publish_now' ? 'smart' : 'schedule_only') : (batchModeSelect?.value || 'smart');
  guardSkipped.forEach((item) => appendBatchLog(`ข้ามคลิป "${item.title}": ${item.reason}`, 'warn'));
  if (guardSkipped.length) appendBatchLog(`ข้ามทั้งหมด ${guardSkipped.length} คลิปที่ยังไม่ควรโพสต์อัตโนมัติ (เหตุผลข้างบน)`, 'warn');

  const batchActions = {
    prepareClip: async (clip, mode) => {
      await panelWorkerRequest({ action: 'release-posting-job', park: true }).catch((err) => appendBatchLog(`พักงานเดิมไม่สำเร็จ: ${err.message}`, 'warn'));
      await panelWorkerRequest({ action: 'select-posting-channel', channelId: activeChannelId });

      const isDraftMode = mode === 'draft';
      const preparePayload = {
        video_path: clip.rel_path || clip.path || clip.name,
        export_id: clip.export_id || null,
        cover_path: clip.cover_path || null,
        caption: clip.tiktok_caption || clip.caption || clip.hook_title || clip.name || '',
        hashtags: clip.tiktok_hashtags || clip.hashtags || '#OmniCut',
        product_id: clip.product_id || null,
        angle_id: clip.angle_id || null,
        tiktok_product_id: clip.tiktok_product_id || null,
        product_name: clip.product_name || clip.cart_name || null,
        queue_id: clip.is_scheduled ? clip.id : null,
        intent: clip.publish_draft ? 'publish_draft' : (isDraftMode ? 'draft' : 'schedule'),
        schedule_date: isDraftMode ? null : (clip.schedule_date || null),
        schedule_time: isDraftMode ? null : (clip.schedule_time || null),
        ...(clip.publish_draft && clip.publish_now ? { confirm_live: true } : {}),
      };

      let res = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/prepare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preparePayload),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        if (
          res.status === 409 &&
          (errBody.code === 'posting_export_already_prepared' ||
            errBody.detail?.includes('มีงานโพสต์อยู่แล้ว') ||
            errBody.detail?.includes('มีคลิปรอโพสต์ค้างอยู่'))
        ) {
          try {
            const pendingRes = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/pending`);
            if (pendingRes.ok) {
              const pendingData = await pendingRes.json();
              // Only a never-claimed ('prepared') job may be cleared here. A job
              // that was claimed/attempted is resolved by the worker's park +
              // reconcile path; force-cancelling it from the panel would let
              // the same export be posted twice.
              if (pendingData?.job_id && pendingData.status === 'prepared') {
                await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/clear`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ job_id: pendingData.job_id }),
                }).catch(() => {});
              }
            }
          } catch (_) {}

          res = await scopedPanelFetch(`${BACKEND}/api/tiktok-autopost/prepare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(preparePayload),
          });
        }
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || errBody.detail || `เตรียมคลิปล้มเหลว (HTTP ${res.status})`);
        }
      }

      const prepared = await res.json();
      if (prepared.protocol_version !== 2 || prepared.channel_id !== activeChannelId || !prepared.job_id) {
        throw new Error('Backend ไม่รองรับ job/channel protocol ต้องอัปเดต Backend');
      }

      await panelWorkerRequest({
        action: 'claim-posting-job',
        jobId: prepared.job_id,
        channelId: activeChannelId,
      });
      activeRecorder?.setJob(prepared.job_id, clip.hook_title || clip.name || clip.id || '');

      activeClip = {
        ...clip,
        job_id: prepared.job_id,
        channel_id: prepared.channel_id,
        cover_path: prepared.cover_path || clip.cover_path || null,
      };

      if (clip.schedule_date && scheduleDateInput) scheduleDateInput.value = clip.schedule_date;
      if (clip.schedule_time && scheduleTimeInput) scheduleTimeInput.value = clip.schedule_time;
      syncScheduleConstraints();
      if (captionInput) captionInput.value = preparePayload.caption;
      updateCaptionCounter();
      if (hashtagsInput) hashtagsInput.value = preparePayload.hashtags;
      if (productIdInput) productIdInput.value = clip.tiktok_product_id || '';
      if (cartNameInput) cartNameInput.value = clip.product_name || clip.cart_name || '';
      resetChecklist();
      renderActiveClipBanner();

      return prepared;
    },

    uploadVideo: async (clip) => {
      // a draft publication has nothing to upload: open the draft and put the form in the mode the job needs
      if (clip?.publish_draft) return panelWorkerRequest({ action: 'open-draft-for-publish' });
      const uploadResp = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: 'upload-file-only' }, (r) => {
          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          if (!r) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ในขั้นอัปโหลด'));
          resolve(r);
        });
      });
      if (!uploadResp?.success) {
        throw new Error(uploadResp?.error || uploadResp?.reason || 'อัปโหลดไฟล์วิดีโอไม่สำเร็จ');
      }
      await new Promise((r) => setTimeout(r, 1200));
      return uploadResp;
    },

    awaitProcessing: async (clip) => {
      if (clip?.publish_draft) return { success: true, skipped: 'draft' };   // the video of a draft is already on TikTok
      const waitResp = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: 'wait-for-upload-only' }, (r) => {
          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          if (!r) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ขณะรออัปโหลดวิดีโอ'));
          resolve(r);
        });
      });
      if (waitResp?.error || waitResp?.success === false) {
        throw new Error(waitResp.error || waitResp.reason || 'รอประมวลผลวิดีโอไม่สำเร็จ');
      }
      return waitResp;
    },

    fillDetails: async (clip, mode) => {
      if (clip?.publish_draft) return { success: true, skipped: 'draft' };   // caption, product and cover are already in the draft
      const scheduleMode = (mode === 'schedule');
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
          action: 'prepare-details',
          caption: (clip.tiktok_caption || clip.caption || clip.hook_title || clip.name || '').trim(),
          hashtags: (clip.tiktok_hashtags || clip.hashtags || '#OmniCut').trim(),
          productId: (clip.tiktok_product_id || clip.product_id || '').trim(),
          scheduleMode,
          cartName: (clip.product_name || clip.cart_name || '').trim(),
          scheduleDate: scheduleMode ? (clip.schedule_date || '') : '',
          scheduleTime: scheduleMode ? (clip.schedule_time || '') : '',
          coverPath: activeClip?.cover_path || clip.cover_path || '',
          coverFallback: Boolean(document.getElementById('coverFallbackToggle')?.checked),
        }, (r) => {
          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          if (!r) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ในการเตรียมรายละเอียด'));
          resolve(r);
        });
      });
      if (!response?.success) {
        throw new Error(response?.error || 'เตรียมรายละเอียดบนหน้า TikTok ไม่สำเร็จ');
      }
      return response;
    },

    submitPost: async (_clip, mode) => {
      // A draft target must never press Post (with no schedule that publishes live): it has its own step.
      const submitAction = mode === 'draft' ? 'save-draft-only' : 'click-post-only';
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: submitAction }, (r) => {
          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          if (!r) return reject(new Error('ไม่ได้รับคำตอบจาก Extension ในการกดโพสต์'));
          resolve(r);
        });
      });
      if (!response?.success) {
        const failure = new Error(response?.error || response?.reason || 'กดโพสต์บนหน้า TikTok ไม่สำเร็จ');
        // true = the click happened, false = provably not; missing (port closed, worker restarted) = unknown
        if (typeof response?.postAttempted === 'boolean') failure.postAttempted = response.postAttempted;
        throw failure;
      }
      return response;
    },

    reconcile: async (_clip, outcome, result) => {
      if (globalThis.OmniBatchOrchestrator?.shouldReconcileAfterPost?.(outcome, result)) {
        await panelWorkerRequest({ action: 'reconcile-posting-result', manual: false })
          .catch((err) => appendBatchLog(`ตรวจผลซ้ำกับ TikTok ไม่สำเร็จ (${err.message}) — ตรวจที่ TikTok Studio > Content เอง`, 'warn'));
      }
      loadExports().catch(() => {});
      return outcome || { success: true };
    },

    // Second proof, independent of the success toast: the clip must be listed on Studio > Content.
    verifySuccessToast: async (clip, _mode, submitResult) => {
      if (!['published', 'scheduled_on_platform'].includes(submitResult?.outcome)) return submitResult;
      const scheduled = submitResult.outcome === 'scheduled_on_platform';
      const caption = globalThis.OmniPostGuard?.clipCaptionText(clip).caption || '';
      let verdict;
      try {
        verdict = await panelWorkerRequest({
          action: 'verify-post-content',
          caption,
          scheduleDate: scheduled ? (clip.schedule_date || '') : '',
          scheduleTime: scheduled ? (clip.schedule_time || '') : '',
        });
      } catch (err) {
        verdict = { verified: false, reason: err.message };
      }
      if (verdict?.verified) return { ...submitResult, verified: true };
      appendBatchLog(`ตรวจหน้า Content แล้วไม่ยืนยัน (${verdict?.reason || 'ไม่ทราบสาเหตุ'}) — ถือว่ายังไม่แน่ใจ`, 'warn');
      return { ...submitResult, outcome: 'confirmation_unknown', verified: false, verifyReason: verdict?.reason };
    },
    checkQuota: async () => {
      if (override && override.mode === 'publish_now') return {};   // publishing now uses no schedule slot
      try {
        await checkTikTokQuota(true, true);
      } catch (err) {
        appendBatchLog(`นับโควตาสดไม่สำเร็จ (${err.message}) — ใช้ตัวเลขล่าสุดที่มี`, 'warn');
      }
      return currentQuotaState;
    },
    // Failed / unconfirmed clip: keep what the page looked like (redacted by the history) next to the log.
    captureEvidence: async (_clip, info) => {
      const page = await panelWorkerRequest({ action: 'capture-evidence' }).catch((err) => ({ found: false, reason: err.message }));
      await activeRecorder?.addEvidence({ ...info, ...(page || {}) });
    },
    notifySignal: async (signal) => {
      try {
        chrome.runtime.sendMessage({ action: 'broadcast-batch-signal', signal }, () => {});
      } catch (_) {}
    },
    resetUploadPage: async () => {
      await panelWorkerRequest({ action: 'release-posting-job', park: true }).catch((err) => appendBatchLog(`พักงานเดิมไม่สำเร็จ: ${err.message}`, 'warn'));
      const res = await new Promise((resolve) => {
        chrome.runtime.sendMessage({ action: 'reset-upload-page' }, (r) => resolve(r || {}));
      });
      return res;
    },
  };

  const runnerModule = globalThis.OmniBatchOrchestrator || (typeof window !== 'undefined' ? window.OmniBatchOrchestrator : null);
  if (!runnerModule || !runnerModule.createBatchOrchestrator) {
    // hard stop: there is no weaker fallback runner any more (no circuit breaker / unknown handling there)
    appendBatchLog('ไม่พบโมดูล batch_orchestrator.js จึงไม่เริ่มรัน', 'error');
    setStatus('ไม่พบโมดูล batch_orchestrator.js — โหลดส่วนขยายใหม่', 'error');
    setBusy(false);
    if (batchStartBtn) batchStartBtn.disabled = false;
    stopKeepAlive();
    await releaseRunLock();
    return;
  }

  const runner = runnerModule.createBatchOrchestrator({

    clips: slicedClips,

    options: {

      mode: selectedMode,

      cooldownSeconds: 22,

      maxScheduleQuota: 30,

      autoSkipOnError: true,
      allowDraft: true, // the panel has a real "Save draft" step now (save-draft-only)
      requiredActions: ['prepareClip', 'uploadVideo|injectFile', 'awaitProcessing', 'fillDetails|fillMetadata', 'submitPost|triggerSubmit', 'verifySuccessToast', 'reconcile|updateBackend'],

    },

    actions: batchActions,

    onStateChange: (state, stats) => {

      const pct = typeof stats.percent === 'number' ? stats.percent : Math.round((stats.processed / Math.max(1, stats.total)) * 100);

      if (batchProgressPercent) batchProgressPercent.textContent = `${pct}%`;

      if (batchProgressBar) batchProgressBar.style.width = `${pct}%`;

      if (batchStatusText) {

        batchStatusText.textContent = stats.hudText || `คลิปที่ ${Math.min(stats.total, stats.currentIndex + 1)}/${stats.total} [${pct}%] - ${stats.stageLabel || 'กำลังดำเนินการ...'}`;

      }

      if (batchCurrentStep) {

        const stepLabels = {

          PREPARING_CLIP: 'เตรียมข้อมูล',

          UPLOADING_VIDEO: 'อัปโหลดวิดีโอ',

          WAITING_UPLOAD: 'รอวิดีโอ 100%',

          FILLING_METADATA: 'กรอกแคปชัน & ตะกร้า & ปก',

          UPLOADING_COVER: 'แนบปก 3:4',

          SUBMITTING_POST: 'กดโพสต์/บันทึก',

          RECONCILING: 'ซิงค์ระบบ OmniCut',

          COOLDOWN: 'พักเครื่อง',

          COMPLETED: 'เสร็จสิ้นทั้งหมด',

          PAUSED: 'พักชั่วคราว',

          STOPPED: 'หยุดการทำงาน',

        };

        batchCurrentStep.textContent = stepLabels[stats.state] || stats.state;

      }

      if (batchEtaText) {

        const m = Math.floor(stats.etaSeconds / 60);

        const s = stats.etaSeconds % 60;

        batchEtaText.textContent = stats.etaSeconds > 0 ? `เหลือประมาณ ${m}น. ${s}วิ.` : 'ใกล้เสร็จ';

      }

      if (stats.isPaused) {

        if (batchPauseBtn) batchPauseBtn.hidden = true;

        if (batchResumeBtn) batchResumeBtn.hidden = false;

      } else {

        if (batchPauseBtn) batchPauseBtn.hidden = false;

        if (batchResumeBtn) batchResumeBtn.hidden = true;

      }

    },

    onLog: (msg, kind) => {

      appendBatchLog(msg, kind);

      setStatus(msg, kind);

    },

    onCooldownTick: (remaining) => {

      if (batchCurrentStep) {

        batchCurrentStep.textContent = remaining > 0 ? `พักเครื่อง (${remaining}s)` : 'พร้อมคลิปถัดไป';

      }

    },

  });

  activeBatchRunner = runner;

  try {

    const summary = await runner.start();
    const verdict = runnerModule.finalVerdict(summary);
    appendBatchLog(`สรุปผลลัพธ์: ${verdict.text}`, verdict.kind);
    setStatus(verdict.text, verdict.kind);
    notifyAttentionIfNeeded({ ...verdict, finalKind: summary.finalKind });
    await activeRecorder?.finish({ finalKind: summary.finalKind, successful: summary.successful, failed: summary.failed, unknown: summary.unknown, total: summary.total, haltReason: summary.haltReason || '', circuitReason: summary.circuitReason || '' });

  } catch (err) {

    appendBatchLog(`หยุดทำงาน: ${err.message}`, 'error');
    setStatus(`การอัปโหลดแบบกลุ่มหยุดลง: ${err.message}`, 'error');
    notifyAttentionIfNeeded({ finalKind: 'error', text: `รอบโพสต์หยุดกลางคัน: ${err.message}` });
    await activeRecorder?.finish({ finalKind: 'error', error: err.message });
  } finally {
    stopKeepAlive();
    activeBatchRunner = null;
    activeRecorder = null;
    setBusy(false);
    if (batchStartBtn) batchStartBtn.disabled = false;
    if (batchPauseBtn) batchPauseBtn.hidden = false;
    if (batchResumeBtn) batchResumeBtn.hidden = true;
    await releaseRunLock();
    await loadExports();
  }
}

batchPauseBtn?.addEventListener('click', () => {

  activeBatchRunner?.pause();

});

batchResumeBtn?.addEventListener('click', () => {

  activeBatchRunner?.resume();

});

batchStopBtn?.addEventListener('click', async () => {

  const ok = await askConfirm('ต้องการหยุดการทำงานของ Batch Auto-Post ใช่หรือไม่? (ถ้ากำลังกดโพสต์ ระบบจะรอตรวจผลของคลิปนี้ให้จบก่อนจึงหยุด)');

  if (ok) {

    activeBatchRunner?.stop();

  }

});



// Global Esc key handler
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (typeof closeVideoPreview === 'function') {
      const modal = document.getElementById('videoPreviewModal');
      if (modal && !modal.hidden) {
        closeVideoPreview();
      }
    }
    const confirmOverlay = document.getElementById('confirmOverlay');
    if (confirmOverlay && confirmOverlay.classList.contains('show')) {
      const cancelBtn = document.getElementById('confirmCancelBtn');
      cancelBtn?.click();
    }
  }
});



let currentStatusFilter = 'all';

function updateFilterChipCounts() {
  const totalAll = allClips.length;
  const totalReady = allClips.filter(c => getExtensionStatus(c).kind === 'ready' || !c.schedule_date).length;
  const totalScheduled = allClips.filter(c => Boolean(c.schedule_date) && !c.is_draft).length;
  const totalUnscheduled = allClips.filter(c => !c.schedule_date).length;
  const totalDraft = allClips.filter(c => c.is_draft).length;

  const countAll = document.getElementById('filterCountAll');
  const countReady = document.getElementById('filterCountReady');
  const countSched = document.getElementById('filterCountScheduled');
  const countUnsched = document.getElementById('filterCountUnscheduled');
  const countDraft = document.getElementById('filterCountDraft');
  if (countAll) countAll.textContent = String(totalAll);
  if (countReady) countReady.textContent = String(totalReady);
  if (countSched) countSched.textContent = String(totalScheduled);
  if (countUnsched) countUnsched.textContent = String(totalUnscheduled);
  if (countDraft) countDraft.textContent = String(totalDraft);
}

document.querySelectorAll('.filter-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    currentStatusFilter = chip.dataset.filter || 'all';
    filterAndRenderClips();
  });
});

const batchCopyLogBtn = document.getElementById('batchCopyLogBtn');
const batchClearLogBtn = document.getElementById('batchClearLogBtn');
batchCopyLogBtn?.addEventListener('click', () => {
  if (!batchLogBox) return;
  const text = batchLogBox.innerText || batchLogBox.textContent || '';
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(() => {
    setStatus('คัดลอกบันทึกการทำงาน (Log) เรียบร้อยแล้ว', 'success');
  }).catch(() => {
    setStatus('คัดลอก Log ไม่สำเร็จ', 'error');
  });
});
batchClearLogBtn?.addEventListener('click', () => {
  if (batchLogBox) batchLogBox.innerHTML = '';
});

// ── Preflight button and "copy last run history" ───────────────────────────
document.getElementById('batchPreflightBtn')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  if (busy || batchStarting) return;
  button.disabled = true;
  try {
    const mode = batchModeSelect?.value || 'smart';
    const count = (selectedClipsInList().length || allClips.filter((c) => !clipBlockReason(c)).length);
    const result = await runPreflightAndReport(mode, count);
    setStatus(result.ok ? (result.warnings.length ? `พร้อมรัน (มีคำเตือน ${result.warnings.length} ข้อ)` : 'พร้อมรัน ตรวจครบทุกข้อแล้ว') : `ยังไม่พร้อมรัน: ${result.blockers.map((b) => b.label).join(', ')}`, result.ok ? (result.warnings.length ? 'warn' : 'success') : 'error');
  } finally {
    button.disabled = false;
  }
});
document.getElementById('batchHistoryBtn')?.addEventListener('click', async () => {
  const recorder = newRunRecorder();
  const text = recorder ? await recorder.exportText(0) : '';
  if (!text) { setStatus('ยังไม่มีประวัติรอบการรัน', 'warn'); return; }
  try { await navigator.clipboard.writeText(text); setStatus('คัดลอกประวัติรอบล่าสุดแล้ว (มีหลักฐานตอนล้ม ตัดข้อมูลส่วนตัวแล้ว)', 'success'); }
  catch (err) { setStatus(`คัดลอกไม่สำเร็จ: ${err.message}`, 'error'); }
});

// ── Publish a draft that sits on TikTok ─────────────────────────────────────
// Scheduled publication = tick the draft cards and run (the normal batch). "Post now" is the button on the card: it is
// LIVE at once, so it is its own run with an explicit confirmation.
async function startDraftPublish(item, when) {
  if (busy || batchStarting) return;
  const clip = { ...item, publish_draft: true, is_draft: true, force_mode: 'schedule', publish_now: when.now === true, schedule_date: '', schedule_time: '' };
  const guard = globalThis.OmniPostGuard;
  const reason = guard?.clipSkipReason(clip, undefined, Date.now(), { exportsKnown: false, ignoreSlot: true, requireSchedule: false });
  if (reason) { setStatus(`เผยแพร่แบบร่างนี้ไม่ได้: ${BLOCK_REASON_TH[reason] || reason}`, 'error'); return; }
  const title = item.hook_title || item.caption || item.video_path;
  const confirmText = `โพสต์ "${title}" จากแบบร่าง "ตอนนี้" — คลิปจะขึ้นเผยแพร่สดทันที ไม่ใช่การตั้งเวลา ยืนยันหรือไม่?`;
  batchStarting = true;
  try {
    await runBatchFromPanel({ clips: [clip], mode: 'publish_now', confirmText });
  } finally {
    batchStarting = false;
    await releaseRunLock();
  }
}
