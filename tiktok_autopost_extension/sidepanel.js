const BACKEND = 'http://127.0.0.1:8000';
const {
  buildExtensionClipList,
  getExtensionStatus,
} = window.OmniCutClipState || {};

// This panel talks to :8000 directly (no Vite proxy to inject the header
// for it, unlike the app's own frontend -- see auth_key.js). Cached here
// and refreshed on storage change rather than re-read on every request,
// since this panel is a long-lived page, not a service worker.
let apiKey = '';
// The very first loadExports() call below (at startup) must wait for this
// to resolve -- chrome.storage.local.get() is asynchronous, so without
// this, the panel's initial auto-load always fires with apiKey still ''
// (401, no header sent) regardless of what's actually saved; only a
// manual refresh clicked later -- by which point this promise has long
// since resolved -- would happen to work. Subsequent calls (manual
// refresh, mark-posted's reload) don't need to wait on this since apiKey
// is long since populated by the time a user can click anything.
const apiKeyReady = getStoredApiKey().then((key) => { apiKey = key; });
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
  apiKeySettingsRow.hidden = !apiKeySettingsRow.hidden;
  if (!apiKeySettingsRow.hidden) apiKeyInput.value = await getStoredApiKey();
});
apiKeySaveBtn?.addEventListener('click', async () => {
  await setStoredApiKey(apiKeyInput.value.trim());
  apiKey = apiKeyInput.value.trim();
  apiKeySettingsRow.hidden = true;
});

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

// The one clip currently being worked on. Only one at a time -- matches
// the backend's own single in-memory "pending" job (see
// scripts/api_tiktok_autopost.py's docstring: "a local single-user tool
// run by one person clicking one button at a time, not a queue").
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
}
tabBtnList.addEventListener('click', () => showTab('list'));
tabBtnChecklist.addEventListener('click', () => showTab('checklist'));
tabBtnTools.addEventListener('click', () => showTab('tools'));

// ── Confirm dialog (only shown when switching clips mid-checklist) ────────
function anyStepChecked() {
  return [1, 2, 3, 4, 5, 6].some((n) => document.getElementById(`chk${n}`).checked);
}

function askConfirm(message) {
  return new Promise((resolve) => {
    confirmText.textContent = message;
    confirmOverlay.classList.add('show');
    const cleanup = (result) => {
      confirmOverlay.classList.remove('show');
      confirmOkBtn.removeEventListener('click', onOk);
      confirmCancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    };
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
  markPostedBtn.disabled = busy || !activeClip;
  const cover = document.getElementById('activeCover');
  cover.hidden = !activeClip?.cover_url;
  if (activeClip?.cover_url) cover.src = withApiKeyParam(`${BACKEND}${activeClip.cover_url}`, apiKey);
  else cover.removeAttribute('src');
  if (!activeClip) {
    activeClipBanner.className = 'empty-state';
    activeClipBanner.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.6;margin-bottom:2px"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg>
      <span>ยังไม่ได้เลือกคลิป — ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน</span>
    `;
    return;
  }
  activeClipBanner.className = '';
  const productLabel = activeClip.product_name ? `<div style="font-size:9.5px;font-weight:700;color:var(--cyan);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:2px">${escapeHtml(activeClip.product_name)}</div>` : '';
  const timeLabel = activeClip.schedule_time ? `<div style="font-size:10px;color:var(--text-tertiary);margin-top:3px;display:flex;align-items:center;gap:4px"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> กำหนดโพสต์ ${escapeHtml(activeClip.schedule_date || '')} ${escapeHtml(activeClip.schedule_time || '')}</div>` : '';
  activeClipBanner.innerHTML = `
    <span class="active-badge"><span class="pulse-dot"></span>กำลังทำคลิป</span>
    ${productLabel}
    <span class="active-title">${escapeHtml(activeClip.hook_title || activeClip.name)}</span>
    ${timeLabel}
  `;
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
  listEl.innerHTML = '<div class="empty">กำลังโหลด...</div>';
  let items;
  try {
    const res = await authedFetch(`${BACKEND}/api/exports`, apiKey);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    items = Array.isArray(data) ? data : (data.exports || data.items || []);
  } catch (err) {
    listEl.innerHTML = `<div class="error">โหลดไม่สำเร็จ -- ตรวจสอบว่า OmniCut Pro Studio เปิดอยู่ที่ localhost:8000 หรือไม่<br>(${escapeHtml(err.message)})</div>`;
    return;
  }

  // When the desktop app has a durable schedule, the extension should show
  // that planned list first so date/time and the one-at-a-time handoff stay
  // aligned. If no schedule exists yet, retain the original ready-export
  // list for backwards compatibility.
  let scheduled = [];
  try {
    const queueRes = await authedFetch(`${BACKEND}/api/schedule-queue`, apiKey);
    if (queueRes.ok) {
      const queueData = await queueRes.json();
      scheduled = (queueData.items || [])
        .filter((item) => ['planned', 'ready_for_extension', 'awaiting_post', 'failed'].includes(item.status))
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
  // Build the final list: scheduled queue items first (they already have
  // a date/time the user committed to), then any rendered exports that are
  // NOT already represented in the queue.  The old "scheduled.length ?
  // scheduled : exports" OR-logic hid newly-rendered clips whenever any
  // older schedule entry was still in ready_for_extension state -- BUG-EXT-1.
  const ready = buildExtensionClipList(items, scheduled).map((item) => ({
    ...item,
    ...(item.is_scheduled ? {} : { is_scheduled: false }),
  }));
  if (ready.length === 0) {
    listEl.innerHTML = '<div class="empty">ยังไม่มีคลิปที่ตัดต่อเสร็จรอโพสต์ตอนนี้</div>';
    return;
  }

  listEl.innerHTML = '';
  for (const item of ready) {
    const card = document.createElement('div');
    card.className = 'card';

    const thumb = document.createElement('img');
    thumb.src = item.thumbnail_url ? withApiKeyParam(`${BACKEND}${item.thumbnail_url}`, apiKey) : '';
    thumb.alt = '';

    const body = document.createElement('div');
    body.className = 'card-body';
    const lifecycle = getExtensionStatus(item);
    body.innerHTML = `
      <div class="card-product">${escapeHtml(item.product_name || 'ไม่ทราบสินค้า')}</div>
      <div class="card-hook">${escapeHtml(item.hook_title || item.name)}</div>
      <div class="card-status ${lifecycle.kind}">${escapeHtml(lifecycle.label)}</div>
      <div class="card-meta">${item.schedule_date ? `กำหนด ${escapeHtml(item.schedule_date)} ${escapeHtml(item.schedule_time || '')}` : `${escapeHtml(item.size_mb || '')} MB · ${escapeHtml(item.modified_time || '')}`}</div>
    `;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-primary';
    btn.innerHTML = `เตรียมคลิปนี้ <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>`;
    btn.addEventListener('click', () => handlePrepareClick(item));
    body.appendChild(btn);

    card.appendChild(thumb);
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
  setBusy(true);
  setStatus(`กำลังเตรียม "${item.hook_title || item.name}"...`);
  try {
    const res = await authedFetch(`${BACKEND}/api/tiktok-autopost/prepare`, apiKey, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: item.rel_path,
        export_id: item.export_id || null,
        cover_path: item.cover_path || null,
        caption: item.tiktok_caption || '',
        hashtags: item.tiktok_hashtags || '',
        product_id: item.product_id || null,
        angle_id: item.angle_id || null,
        tiktok_product_id: item.tiktok_product_id || null,
        product_name: item.product_name || null,
        queue_id: item.id || null,
        schedule_date: item.schedule_date || null,
        schedule_time: item.schedule_time || null,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    const prepared = await res.json();
    activeClip = {...item, cover_path: prepared.cover_path || item.cover_path || null};
    if (item.schedule_date) scheduleDateInput.value = item.schedule_date;
    if (item.schedule_time) scheduleTimeInput.value = item.schedule_time;
    syncScheduleConstraints();
    captionInput.value = item.tiktok_caption || '';
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
          setStatus(messageText, 'success');
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
    if (response.marked) {
      const postedTitle = activeClip?.hook_title || activeClip?.name || 'คลิป';
      activeClip = null;
      resetChecklist();
      renderActiveClipBanner();
      loadExports();
      showTab('list');
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
const prepareDetailsBtnReadyLabel = prepareDetailsBtn.innerHTML;

// Greyed out (see .hero-post-btn:disabled) until step 1 is done -- clicking
// it before the clip is uploaded has nothing to fill in on the TikTok page
// yet, so this heads that off instead of letting it run and fail partway.
// Note: step 1 turning green only means the file was handed to TikTok's
// page (see runUploadFileOnly in background.js) -- it does not wait for
// TikTok to finish actually receiving/processing it, since holding the
// debugger attached that long is exactly what caused the tab-crash issue
// noted elsewhere in background.js. So this button becomes clickable as
// soon as step 1 is done, which is not necessarily the same moment as the
// upload reaching 100% in TikTok's own UI.
function syncPrepareDetailsBtnState() {
  const uploaded = document.getElementById('chk1')?.checked;
  prepareDetailsBtn.disabled = !uploaded;
  prepareDetailsBtn.title = uploaded ? '' : 'อัปโหลดก่อน';
  prepareDetailsBtn.innerHTML = uploaded ? prepareDetailsBtnReadyLabel : 'อัปโหลดก่อน';
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
  if (!document.getElementById('chk1')?.checked) {
    setStatus('อัปโหลดก่อน', 'error');
    return;
  }
  if (!activeClip?.cover_path || !productIdInput.value.trim()) {
    setStatus('ต้องเตรียมคลิปที่มีปก และกรอก ID สินค้าก่อน', 'error');
    return;
  }
  const scheduleMode = document.getElementById('prepareSchedule').checked;
  setBusy(true);
  [2, 3, 6, ...(scheduleMode ? [4] : [])].forEach(n => {
    const checkbox = document.getElementById(`chk${n}`);
    checkbox.checked = false;
    checkbox.closest('.step-row')?.classList.remove('completed');
  });
  setStatus('กำลังกรอกข้อมูล ปักตะกร้า และแนบปก โปรดรอผลก่อนแก้ไขหน้า TikTok');
  try {
    const response = await chrome.runtime.sendMessage({
      action:'prepare-details', caption:captionInput.value.trim(),
      hashtags:hashtagsInput.value.trim(), productId:productIdInput.value.trim(), scheduleMode,
      cartName:cartNameInput.value.trim(), scheduleDate:scheduleDateInput.value, scheduleTime:scheduleTimeInput.value,
      coverPath: activeClip.cover_path,
    });
    const checks = {caption:2, product:3, cover:6, schedule:4};
    for (const step of response?.completed || []) {
      const checkbox = document.getElementById(`chk${checks[step]}`);
      checkbox.checked = true;
      checkbox.closest('.step-row')?.classList.add('completed');
    }
    updatePipelineProgress();
    if (!response?.success) throw new Error(response?.error || 'ไม่ได้รับผลการทำงาน');
    setStatus('เตรียมครบแล้ว ตรวจข้อมูลบน TikTok และกดโพสต์ได้เลย', 'success');
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
  setStatus(`กำลังมาร์ค "${activeClip.hook_title || activeClip.name}" ว่าโพสต์แล้ว...`);
  try {
    const res = await authedFetch(`${BACKEND}/api/exports/mark-posted`, apiKey, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: activeClip.rel_path,
        export_id: activeClip.export_id || null,
        product_id: activeClip.product_id || null,
        angle_id: activeClip.angle_id || null,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    setStatus(`มาร์ค "${activeClip.hook_title || activeClip.name}" ว่าโพสต์แล้ว -- ย้ายไฟล์ไป Posted/ แล้ว`, 'success');
    activeClip = null;
    resetChecklist();
    renderActiveClipBanner();
    await loadExports();
    showTab('list');
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
      func: () => window.OmniCutStatsParser.parsePostsTable(document),
    });
    const result = injected?.[0]?.result;
    if (!result) throw new Error('อ่านหน้า TikTok ไม่ได้ — รีเฟรชหน้า Studio แล้วลองใหม่');
    if (result.error) throw new Error(result.error);
    if (!result.rows.length) throw new Error('ไม่พบแถวโพสต์ในตาราง — เลื่อนลงให้ตารางโหลดก่อนกดซิงก์');
    setStatus(`พบ ${result.rows.length} โพสต์ กำลังส่งเข้า OmniCut...`);
    const res = await authedFetch(`${BACKEND}/api/tiktok-stats/import`, apiKey, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows: result.rows }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    const unmatched = (body.unmatched || []).length;
    const registered = body.registered || 0;
    setStatus(
      `ซิงก์สำเร็จ ${body.matched}/${body.total} คลิป อัปเดตตัวเลข ${body.updated} คลิป${registered ? ` ลงทะเบียนโพสต์ใหม่ ${registered} รายการ` : ''}${unmatched ? ` (ไม่เจอคู่ ${unmatched} คลิป ดูในแท็บผลงาน)` : ''}`,
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

async function openTikTokUploadTab() {
  if (typeof chrome !== 'undefined' && chrome.tabs) {
    const tab = await findExistingTikTokTab();
    if (tab && tab.id) {
      let target = tab;
      if (!String(tab.url || '').includes('/upload')) {
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
updatePipelineProgress();
