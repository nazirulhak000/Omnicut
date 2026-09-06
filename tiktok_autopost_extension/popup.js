const runBtn = document.getElementById('runBtn');
const typeCaptionOnlyBtn = document.getElementById('typeCaptionOnlyBtn');
const attachOnlyBtn = document.getElementById('attachOnlyBtn');
const statusEl = document.getElementById('status');
const autoClickPostEl = document.getElementById('autoClickPost');
const attachProductEl = document.getElementById('attachProduct');
const productIdInput = document.getElementById('productIdInput');
const captionInput = document.getElementById('captionInput');
const hashtagsInput = document.getElementById('hashtagsInput');
const scheduleModeEl = document.getElementById('scheduleMode');

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || '';
}

// Safely restore inputs state from storage
try {
  if (typeof chrome !== 'undefined' && chrome.storage?.local) {
    chrome.storage.local.get(['autoClickPost', 'attachProduct', 'productId', 'caption', 'hashtags', 'scheduleMode'], (data) => {
      // Round POST-2 note (2026-09-06, user feedback): autoClickPost is
      // deliberately NEVER restored from storage, even though it's still
      // saved below -- a prior test left it checked, it silently persisted
      // across popup opens, and the extension auto-clicked Post while
      // attachProductLink's fixed sleeps hadn't actually finished settling
      // the product-attach modal yet. User wants to always click Post
      // themselves for now ("ผมกดเอง ให้นายแค่ใส่ข้อมูลก่อน") -- so this
      // checkbox always opens unchecked; re-check it by hand each time.
      autoClickPostEl.checked = false;
      if (data && typeof data.attachProduct === 'boolean') {
        attachProductEl.checked = data.attachProduct;
      }
      if (data && typeof data.scheduleMode === 'boolean') {
        scheduleModeEl.checked = data.scheduleMode;
      }
      if (data && data.productId) {
        productIdInput.value = data.productId;
      }
      if (data && data.caption && !captionInput.value) {
        captionInput.value = data.caption;
      }
      if (data && data.hashtags && !hashtagsInput.value) {
        hashtagsInput.value = data.hashtags;
      }
    });

    const saveSettings = () => {
      try {
        chrome.storage.local.set({
          autoClickPost: autoClickPostEl.checked,
          attachProduct: attachProductEl.checked,
          scheduleMode: scheduleModeEl.checked,
          productId: productIdInput.value.trim(),
          caption: captionInput.value.trim(),
          hashtags: hashtagsInput.value.trim(),
        });
      } catch (err) {
        console.warn('Cannot save settings:', err);
      }
    };

    autoClickPostEl.addEventListener('change', saveSettings);
    attachProductEl.addEventListener('change', saveSettings);
    scheduleModeEl.addEventListener('change', saveSettings);
    productIdInput.addEventListener('input', saveSettings);
    captionInput.addEventListener('input', saveSettings);
    hashtagsInput.addEventListener('input', saveSettings);

    // Auto-fill from pending OmniCut job
    fetch('http://127.0.0.1:8000/api/tiktok-autopost/pending')
      .then((res) => (res.ok ? res.json() : null))
      .then((job) => {
        if (job) {
          const targetId = job.tiktok_product_id || job.product_id;
          if (targetId && !productIdInput.value) {
            productIdInput.value = targetId;
          }
          if (job.caption && (!captionInput.value || captionInput.value === '')) {
            captionInput.value = job.caption;
          }
          if (job.hashtags && (!hashtagsInput.value || hashtagsInput.value === '')) {
            hashtagsInput.value = job.hashtags;
          }
          saveSettings();
        }
      })
      .catch(() => {});
  }
} catch (err) {
  console.warn('Storage initialization warning:', err);
}

runBtn.addEventListener('click', () => {
  runBtn.disabled = true;
  setStatus('กำลังทำงาน... (ระบบจะอัปโหลด รอวิดีโอครบ 100% แล้วจึงปักตะกร้า)');

  try {
    chrome.runtime.sendMessage(
      {
        action: 'run-autopost',
        autoClickPost: autoClickPostEl.checked,
        attachProduct: attachProductEl.checked,
        productId: productIdInput.value.trim(),
        caption: captionInput.value.trim(),
        hashtags: hashtagsInput.value.trim(),
        scheduleMode: scheduleModeEl.checked,
      },
      (response) => {
        runBtn.disabled = false;
        if (chrome.runtime.lastError) {
          setStatus('เกิดข้อผิดพลาดจาก Extension: ' + chrome.runtime.lastError.message, 'error');
          return;
        }
        if (!response) {
          setStatus('ไม่ได้รับคำตอบจาก Extension -- ลองกดใหม่อีกครั้ง หรือรีโหลด Extension', 'error');
          return;
        }
        if (response.success) {
          const leaveNote = response.autoClickedPost && !response.leaveDialogDismissed
            ? ' (ถ้าเจอ dialog "แน่ใจหรือไม่ว่าต้องการออก" ค้างอยู่ กดออกเองได้เลย โพสต์ไปแล้วจริง)'
            : '';
          setStatus(
            (response.autoClickedPost
              ? 'เติมข้อมูล ปักตะกร้า และกดเผยแพร่ให้เรียบร้อยแล้ว 🎉'
              : 'เติมข้อมูลและปักตะกร้าสำเร็จ! -- ตรวจสอบวันเวลาที่ต้องการ แล้วกด "กำหนดเวลา" ได้เลย 🎉') + leaveNote,
            'success'
          );
        } else {
          setStatus(response.error || 'เกิดข้อผิดพลาดไม่ทราบสาเหตุ', 'error');
        }
      }
    );
  } catch (err) {
    runBtn.disabled = false;
    setStatus('เกิดข้อผิดพลาดในการส่งคำสั่ง: ' + (err.message || String(err)), 'error');
  }
});

typeCaptionOnlyBtn.addEventListener('click', () => {
  const cap = captionInput.value.trim();
  const hash = hashtagsInput.value.trim();
  if (!cap && !hash) {
    setStatus('กรุณากรอกคำอธิบายหรือแฮชแท็กก่อนกดพิมพ์', 'error');
    return;
  }
  typeCaptionOnlyBtn.disabled = true;
  setStatus('กำลังพิมพ์คำอธิบายและแฮชแท็ก...');

  try {
    chrome.runtime.sendMessage(
      {
        action: 'type-caption-only',
        caption: cap,
        hashtags: hash,
      },
      (response) => {
        typeCaptionOnlyBtn.disabled = false;
        if (chrome.runtime.lastError) {
          setStatus('เกิดข้อผิดพลาด: ' + chrome.runtime.lastError.message, 'error');
          return;
        }
        if (response?.success) {
          setStatus('พิมพ์คำอธิบายและแฮชแท็กเรียบร้อยแล้ว! ✍️', 'success');
        } else {
          setStatus('พิมพ์ไม่สำเร็จ: ' + (response?.error || 'ไม่ทราบสาเหตุ'), 'error');
        }
      }
    );
  } catch (err) {
    typeCaptionOnlyBtn.disabled = false;
    setStatus('เกิดข้อผิดพลาด: ' + (err.message || String(err)), 'error');
  }
});

attachOnlyBtn.addEventListener('click', () => {
  const pId = productIdInput.value.trim();
  if (!pId) {
    setStatus('กรุณากรอก ID สินค้าก่อนกดปักตะกร้า', 'error');
    return;
  }
  attachOnlyBtn.disabled = true;
  setStatus('กำลังปักตะกร้าสินค้า... (กรุณารอประมาณ 5-7 วินาที)');

  try {
    chrome.runtime.sendMessage(
      {
        action: 'attach-product-only',
        productId: pId,
        scheduleMode: scheduleModeEl.checked,
      },
      (response) => {
        attachOnlyBtn.disabled = false;
        if (chrome.runtime.lastError) {
          setStatus('เกิดข้อผิดพลาด: ' + chrome.runtime.lastError.message, 'error');
          return;
        }
        if (!response) {
          setStatus('ไม่ได้รับคำตอบจาก Extension', 'error');
          return;
        }
        if (response.success) {
          setStatus('ปักตะกร้าสินค้าสำเร็จเรียบร้อยแล้ว! 🎉', 'success');
        } else {
          setStatus('ปักตะกร้าไม่สำเร็จ: ' + (response.reason || response.error || 'ไม่ทราบสาเหตุ'), 'error');
        }
      }
    );
  } catch (err) {
    attachOnlyBtn.disabled = false;
    setStatus('เกิดข้อผิดพลาด: ' + (err.message || String(err)), 'error');
  }
});
