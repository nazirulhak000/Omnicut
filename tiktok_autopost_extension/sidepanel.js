const BACKEND = 'http://127.0.0.1:8000';

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
const panelList = document.getElementById('panelList');
const panelChecklist = document.getElementById('panelChecklist');

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
  document.querySelectorAll('#panelChecklist button, #list button, #refreshBtn, #panelChecklist input, #panelChecklist textarea')
    .forEach(el => { el.disabled = value; });
}

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || 'info';
}

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// ── Tabs ──────────────────────────────────────────────────────────────────
function showTab(name) {
  const listActive = name === 'list';
  tabBtnList.classList.toggle('active', listActive);
  tabBtnChecklist.classList.toggle('active', !listActive);
  panelList.classList.toggle('active', listActive);
  panelChecklist.classList.toggle('active', !listActive);
}
tabBtnList.addEventListener('click', () => showTab('list'));
tabBtnChecklist.addEventListener('click', () => showTab('checklist'));

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

function resetChecklist() {
  [1, 2, 3, 4, 5, 6].forEach((n) => {
    const checkbox = document.getElementById(`chk${n}`);
    checkbox.checked = false;
    checkbox.closest('.step-row')?.classList.remove('completed');
  });
}

function renderActiveClipBanner() {
  const cover = document.getElementById('activeCover');
  cover.hidden = !activeClip?.cover_url;
  if (activeClip?.cover_url) cover.src = `${BACKEND}${activeClip.cover_url}`;
  else cover.removeAttribute('src');
  if (!activeClip) {
    activeClipBanner.className = 'empty-state';
    activeClipBanner.textContent = 'ยังไม่ได้เลือกคลิป -- ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน';
    return;
  }
  activeClipBanner.className = '';
  activeClipBanner.innerHTML = `<b>กำลังทำคลิป:</b>${escapeHtml(activeClip.hook_title || activeClip.name)}`;
}

// ── "ตัดต่อเสร็จ" == ProductStore angle status 'rendered' (see
// PIPELINE_PHASES in ContentTrackerHub.jsx) -- exports whose matched angle
// has already advanced further (mobile_ready/posted) or has no matched
// angle at all are deliberately left out; this panel is specifically
// "what's done editing and ready to post", not a general file browser.
function isReadyToPost(item) {
  return item.angle_status === 'rendered' && item.is_latest !== false;
}

async function loadExports() {
  listEl.innerHTML = '<div class="empty">กำลังโหลด...</div>';
  let items;
  try {
    const res = await fetch(`${BACKEND}/api/exports`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    items = Array.isArray(data) ? data : (data.exports || data.items || []);
  } catch (err) {
    listEl.innerHTML = `<div class="error">โหลดไม่สำเร็จ -- ตรวจสอบว่า OmniCut Pro Studio เปิดอยู่ที่ localhost:8000 หรือไม่<br>(${escapeHtml(err.message)})</div>`;
    return;
  }

  const ready = items.filter(isReadyToPost);
  if (ready.length === 0) {
    listEl.innerHTML = '<div class="empty">ยังไม่มีคลิปที่ตัดต่อเสร็จรอโพสต์ตอนนี้</div>';
    return;
  }

  listEl.innerHTML = '';
  for (const item of ready) {
    const card = document.createElement('div');
    card.className = 'card';

    const thumb = document.createElement('img');
    thumb.src = item.thumbnail_url ? `${BACKEND}${item.thumbnail_url}` : '';
    thumb.alt = '';

    const body = document.createElement('div');
    body.className = 'card-body';
    body.innerHTML = `
      <div class="card-product">${escapeHtml(item.product_name || 'ไม่ทราบสินค้า')}</div>
      <div class="card-hook">${escapeHtml(item.hook_title || item.name)}</div>
      <div class="card-meta">${escapeHtml(item.size_mb)} MB · ${escapeHtml(item.modified_time || '')}</div>
    `;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-primary';
    btn.textContent = 'เตรียมคลิปนี้ ➜';
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
    const res = await fetch(`${BACKEND}/api/tiktok-autopost/prepare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: item.rel_path,
        cover_path: item.cover_path || null,
        caption: item.tiktok_caption || '',
        hashtags: item.tiktok_hashtags || '',
        product_id: item.product_id || null,
        angle_id: item.angle_id || null,
        tiktok_product_id: item.tiktok_product_id || null,
        product_name: item.product_name || null,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    const prepared = await res.json();
    activeClip = {...item, cover_path: prepared.cover_path || item.cover_path || null};
    captionInput.value = item.tiktok_caption || '';
    hashtagsInput.value = item.tiktok_hashtags || '';
    productIdInput.value = item.tiktok_product_id || '';
    cartNameInput.value = item.product_name || '';
    resetChecklist();
    renderActiveClipBanner();
    showTab('checklist');
    setStatus('เตรียมคลิปแล้ว! กดทำทีละขั้นด้านล่างได้เลย 🎉', 'success');
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

wireStep('btn5', 'chk5', 'ขั้น 5 (กด Post/กำหนดเวลา)',
  () => ({ action: 'click-post-only' }),
  'ขั้น 5 สำเร็จ -- กด Post/กำหนดเวลาให้แล้ว 🎉');

wireStep('btn6', 'chk6', 'แนบภาพปก',
  () => {
    if (!activeClip) throw new Error('ยังไม่ได้เลือกคลิป — ไปที่แท็บ "รายการคลิป" แล้วกด "เตรียมคลิปนี้" ก่อน');
    return {action:'upload-cover-only', coverPath: activeClip.cover_path || ''};
  },
  'ส่งภาพปกและบันทึกแล้ว ตรวจภาพตัวอย่างบน TikTok ก่อนโพสต์');

document.getElementById('prepareDetailsBtn').addEventListener('click', async () => {
  if (busy) return;
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
  copyAllBtn.innerHTML = '<span class="ic">✅</span> คัดลอกแล้ว';
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
    const res = await fetch(`${BACKEND}/api/exports/mark-posted`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: activeClip.rel_path,
        product_id: activeClip.product_id || null,
        angle_id: activeClip.angle_id || null,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    setStatus(`มาร์ค "${activeClip.hook_title || activeClip.name}" ว่าโพสต์แล้ว -- ย้ายไฟล์ไป Posted/ แล้ว 🎉`, 'success');
    activeClip = null;
    resetChecklist();
    renderActiveClipBanner();
    loadExports();
  } catch (err) {
    setStatus('มาร์คไม่สำเร็จ: ' + err.message, 'error');
  } finally {
    markPostedBtn.disabled = false;
  }
});

renderActiveClipBanner();
loadExports();
