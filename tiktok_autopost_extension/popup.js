const captionInput = document.getElementById('captionInput');
const hashtagsInput = document.getElementById('hashtagsInput');
const productIdInput = document.getElementById('productIdInput');
const statusEl = document.getElementById('status');

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || '';
}

// Restore text inputs from storage (not the checklist ticks -- those are
// per-session progress, not a saved preference) and auto-fill from
// whatever OmniCut last prepared, same as before.
try {
  if (typeof chrome !== 'undefined' && chrome.storage?.local) {
    chrome.storage.local.get(['productId', 'caption', 'hashtags'], (data) => {
      if (data?.productId) productIdInput.value = data.productId;
      if (data?.caption && !captionInput.value) captionInput.value = data.caption;
      if (data?.hashtags && !hashtagsInput.value) hashtagsInput.value = data.hashtags;
    });

    const saveInputs = () => {
      try {
        chrome.storage.local.set({
          productId: productIdInput.value.trim(),
          caption: captionInput.value.trim(),
          hashtags: hashtagsInput.value.trim(),
        });
      } catch (err) {
        console.warn('Cannot save inputs:', err);
      }
    };
    productIdInput.addEventListener('input', saveInputs);
    captionInput.addEventListener('input', saveInputs);
    hashtagsInput.addEventListener('input', saveInputs);

    fetch('http://127.0.0.1:8000/api/tiktok-autopost/pending')
      .then((res) => (res.ok ? res.json() : null))
      .then((job) => {
        if (!job) return;
        const targetId = job.tiktok_product_id || job.product_id;
        if (targetId && !productIdInput.value) productIdInput.value = targetId;
        if (job.caption && !captionInput.value) captionInput.value = job.caption;
        if (job.hashtags && !hashtagsInput.value) hashtagsInput.value = job.hashtags;
        saveInputs();
      })
      .catch(() => {});
  }
} catch (err) {
  console.warn('Storage initialization warning:', err);
}

// Generic runner for one checklist step: disables its own button while
// running, sends the message, ticks its checkbox on success, reports the
// error plainly on failure (including "tab crashed" -- chrome.runtime
// reports a disconnected port the same way a normal error would show up).
function wireStep(btnId, chkId, stepName, buildMessage, successText) {
  const btn = document.getElementById(btnId);
  const chk = document.getElementById(chkId);

  btn.addEventListener('click', () => {
    btn.disabled = true;
    setStatus(`กำลังทำ ${stepName}...`);

    let message;
    try {
      message = buildMessage();
    } catch (err) {
      btn.disabled = false;
      setStatus(err.message || String(err), 'error');
      return;
    }

    try {
      chrome.runtime.sendMessage(message, (response) => {
        btn.disabled = false;
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
          setStatus(successText, 'success');
        } else {
          setStatus(response.error || response.reason || 'เกิดข้อผิดพลาดไม่ทราบสาเหตุ', 'error');
        }
      });
    } catch (err) {
      btn.disabled = false;
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
    return { action: 'attach-product-only', productId };
  },
  'ขั้น 3 สำเร็จ -- ปักตะกร้าสินค้าแล้ว');

wireStep('btn4', 'chk4', 'ขั้น 4 (สลับเป็นกำหนดเวลา)',
  () => ({ action: 'schedule-mode-only' }),
  'ขั้น 4 สำเร็จ -- สลับเป็นกำหนดเวลาแล้ว');

wireStep('btn5', 'chk5', 'ขั้น 5 (กด Post/กำหนดเวลา)',
  () => ({ action: 'click-post-only' }),
  'ขั้น 5 สำเร็จ -- กด Post/กำหนดเวลาให้แล้ว 🎉');
