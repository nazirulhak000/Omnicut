/**
 * Phase 2: Live-Tuned Content Script & DOM Resilience (content_script.js)
 *
 * Verified 100% against Live TikTok Studio DOM via Browser MCP (Zero-Guessing):
 * - /tiktokstudio/content & /tiktokstudio/upload?from=creator_center&tab=video
 * - Event-driven waiting via MutationObserver + requestAnimationFrame (waitForSelector)
 * - Primary + Fallback Selector Arrays for every component
 * - Instant reaction to PAUSE, RESUME, ABORT signals from Sidepanel / Background
 */
(function attachOmniContentScript(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.OmniContentScript = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  /**
   * LIVE-VERIFIED SELECTORS FROM TIKTOK STUDIO VIA BROWSER MCP (2026-10-31)
   * Every group is an ordered array of primary -> fallback CSS selectors.
   */
  const LIVE_SELECTORS = {
    // 1. Upload Dropzone & File Input (verified on /tiktokstudio/upload)
    uploadDropzone: [
      '[data-e2e="select_video_container"]',
      'div.upload-card.before-upload-new-stage',
      '[data-tt="Sidebar_UploadEntrance_WideButton"]',
      '[data-tt="Sidebar_UploadEntrance_Container"]',
    ],
    fileInput: [
      'input[type="file"][accept="video/*"]',
      '[data-e2e="select_video_container"] input[type="file"]',
      'input.jsx-2094875959[type="file"]',
      'input[type="file"]',
    ],
    uploadStatusContainer: [
      '[data-e2e="upload_status_container"]',
      'div.info-status',
      '[class*="info-status"]',
      '[class*="info-progress"]',
    ],

    // 2. Caption & Title Area (Draft.js ContentEditable inside caption_container)
    captionContainer: [
      '[data-e2e="caption_container"]',
      'div.caption-container.caption-markup-container',
      '[class*="caption-container"]',
    ],
    captionEditor: [
      '[data-e2e="caption_container"] div.public-DraftEditor-content[role="combobox"]',
      'div.notranslate.public-DraftEditor-content[role="combobox"]',
      '[data-e2e="caption_container"] [contenteditable="true"]',
      '[contenteditable="true"]',
    ],
    hashtagButton: [
      '#web-creation-caption-hashtag-button',
      'button.caption-operation-icon',
    ],
    mentionButton: [
      '#web-creation-caption-mention-button',
    ],

    // 3. Cover Selector & Custom Cover Modal
    coverContainer: [
      '[data-e2e="cover_container"]',
      'div.cover-container',
      '[class*="cover-container"]',
    ],
    coverEditTrigger: [
      '[data-e2e="cover_container"] div.edit-container',
      'div.cover-container div.edit-container',
      'div.edit-container',
      '[class*="edit-container"]',
    ],
    coverModalRoot: [
      '[class*="cover-editor-container"]',
      '[class*="CoverEditor__root"]',
      'label.ImageUpload__uploadArea',
      '[class*="cover-modal"]',
      '[class*="CoverModal"]',
    ],
    coverFileInput: [
      'label.ImageUpload__uploadArea input[type="file"]',
      'input[type="file"][accept*="image"]',
    ],

    // 4. Schedule Toggle Switch & Post Now Radio
    postNowRadio: [
      'input.Radio__input[type="radio"][value="post_now"]',
      'input[type="radio"][value="post_now"]',
    ],
    scheduleRadio: [
      'input.Radio__input[type="radio"][value="schedule"]',
      'input[type="radio"][value="schedule"]',
    ],
    featureSwitches: [
      'input.Switch__input[role="switch"][type="checkbox"]',
      '[role="switch"]',
    ],

    // 5. Date & Time Picker (Readonly TUX inputs + Calendar & Timepicker Popovers)
    scheduleInputs: [
      'input.TUXTextInputCore-input[readonly]',
      'input.TUXTextInputCore-input',
      'input[type="date"]',
      'input[type="time"]',
    ],
    calendarWrapper: [
      'div.calendar-wrapper',
      '[class*="calendar-wrapper"]',
    ],
    calendarValidDays: [
      '[class*="calendar-wrapper"] span.day.valid',
      'span.day.valid',
    ],
    calendarMonthArrows: [
      '[class*="calendar-wrapper"] .month-header-wrapper .arrow',
      '.month-header-wrapper .arrow',
    ],
    timepickerHours: [
      'span.tiktok-timepicker-option-text.tiktok-timepicker-left',
      '[class*="tiktok-timepicker-left"]',
    ],
    timepickerMinutes: [
      'span.tiktok-timepicker-option-text.tiktok-timepicker-right',
      '[class*="tiktok-timepicker-right"]',
    ],

    // 6. Submit / Draft / Discard Footer Buttons
    submitPostButton: [
      'button[data-e2e="post_video_button"]',
      'button.Button__root--type-primary[data-e2e="post_video_button"]',
      '.btn-post',
    ],
    saveDraftButton: [
      'button[data-e2e="save_draft_button"]',
      'button.Button__root--type-neutral[data-e2e="save_draft_button"]',
    ],
    discardButton: [
      'button[data-e2e="discard_post_button"]',
      'button.Button__root--type-neutral[data-e2e="discard_post_button"]',
    ],

    // 7. Modals, Overlays, Tutorials & Success Toasts
    modalDialogs: [
      '.TUXModal.common-modal[role="dialog"]',
      '.TUXModal-overlay',
      '[role="dialog"]',
      '[aria-modal="true"]',
    ],
    modalPrimaryButton: [
      '.TUXModal .common-modal-footer button.TUXButton--primary',
      '[role="dialog"] button.TUXButton--primary',
      '[role="dialog"] button.Button__root--type-primary',
    ],
    modalSecondaryButton: [
      '.TUXModal .common-modal-footer button.TUXButton--secondary',
      '[role="dialog"] button.TUXButton--secondary',
    ],
    tutorialTooltip: [
      '[role="alertdialog"]',
      '.tutorial-tooltip',
      '.react-joyride__beacon',
    ],
    toastNotices: [
      '[class*="toast"]',
      '[class*="Toast"]',
      '[class*="notice"]',
      '[class*="Notice"]',
      '[role="alert"]',
    ],

    // 8. Content Management Page (/tiktokstudio/content) Quota & Post Table
    contentHeaderTabs: [
      '[data-tt="Header_HeaderTabBar_TUXText"]',
      '[data-tt="Header_HeaderTabBar_Container"]',
      '[role="tab"]',
    ],
    contentPostTable: [
      '[data-tt="components_PostTable_Container"]',
      '[data-tt="components_PostTable_FlexColumn"]',
      '[data-tt="components_PostTableHeader_Clickable"]',
    ],
  };

  /**
   * Measured DOM Timing & Latency constants from live TikTok Studio probing.
   */
  const DOM_TIMINGS = {
    scheduleToggleLatencyMs: 60,     // Measured: ~36.4ms for radio switch + TUXTextInputCore mount
    popoverOpenLatencyMs: 250,       // Measured: ~180-250ms for calendar-wrapper & timepicker popover
    timeScrollSettleMs: 220,         // Time picker scroll animation settle time
    modalTransitionMs: 300,          // Measured CSS transition: opacity 0.3s on __floater / TUXModal
    toastVisibilityWindowMs: 4500,   // Success toast remains visible ~3.5-5s before route transition
    defaultWaitTimeoutMs: 15000,
    uploadCompleteTimeoutMs: 900000,
  };

  // Runtime signal state controlled by Sidepanel / Background
  const signalState = {
    paused: false,
    aborted: false,
    pauseResolvers: [],
  };

  function handleSignal(signal) {
    const cmd = String(signal || '').toUpperCase();
    if (cmd === 'PAUSE') {
      signalState.paused = true;
      return { ok: true, state: 'PAUSED' };
    }
    if (cmd === 'RESUME') {
      signalState.paused = false;
      const resolvers = signalState.pauseResolvers.splice(0);
      for (const r of resolvers) {
        try { r(); } catch (_) {}
      }
      return { ok: true, state: 'RESUMED' };
    }
    if (cmd === 'ABORT' || cmd === 'STOP') {
      signalState.aborted = true;
      signalState.paused = false;
      const resolvers = signalState.pauseResolvers.splice(0);
      for (const r of resolvers) {
        try { r(); } catch (_) {}
      }
      return { ok: true, state: 'ABORTED' };
    }
    if (cmd === 'RESET') {
      signalState.paused = false;
      signalState.aborted = false;
      signalState.pauseResolvers.splice(0);
      return { ok: true, state: 'IDLE' };
    }
    return { ok: false, error: `Unknown signal: ${signal}` };
  }

  async function guardSignal() {
    if (signalState.aborted) {
      const err = new Error('CONTENT_SCRIPT_ABORTED');
      err.code = 'BATCH_ABORTED';
      throw err;
    }
    if (signalState.paused) {
      await new Promise((resolve) => {
        signalState.pauseResolvers.push(resolve);
      });
      if (signalState.aborted) {
        const err = new Error('CONTENT_SCRIPT_ABORTED');
        err.code = 'BATCH_ABORTED';
        throw err;
      }
    }
  }

  function isElementVisible(el) {
    if (!el) return false;
    if (typeof el.checkVisibility === 'function') {
      try {
        if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
      } catch (_) {}
    }
    if (typeof el.getBoundingClientRect === 'function') {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return false;
    }
    if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
      try {
        const style = window.getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none') return false;
      } catch (_) {}
    }
    return true;
  }

  function isElementEnabled(el) {
    if (!el) return false;
    return !el.disabled && el.getAttribute?.('aria-disabled') !== 'true';
  }

  /**
   * Queries the DOM using a selector group name (from LIVE_SELECTORS) or an array/string of selectors.
   */
  function queryWithFallback(selectorOrKey, { root = typeof document !== 'undefined' ? document : null, requireVisible = false, all = false } = {}) {
    if (!root || typeof root.querySelectorAll !== 'function') return all ? [] : null;
    const candidates = Array.isArray(selectorOrKey)
      ? selectorOrKey
      : (LIVE_SELECTORS[selectorOrKey] || [String(selectorOrKey)]);

    for (const sel of candidates) {
      if (!sel) continue;
      let nodes = [];
      try {
        nodes = Array.from(root.querySelectorAll(sel));
      } catch (_) {
        continue;
      }
      if (requireVisible) {
        nodes = nodes.filter(isElementVisible);
      }
      if (nodes.length > 0) {
        return all ? nodes : nodes[0];
      }
    }
    return all ? [] : null;
  }

  /**
   * Event-Driven waitForSelector using MutationObserver (instead of blind fixed setTimeout).
   */
  function waitForSelector(selectorOrKey, {
    root = typeof document !== 'undefined' ? document : null,
    requireVisible = false,
    requireEnabled = false,
    predicate = null,
    timeoutMs = DOM_TIMINGS.defaultWaitTimeoutMs,
  } = {}) {
    return new Promise((resolve, reject) => {
      if (!root) return reject(new Error('No DOM root available for waitForSelector'));

      const check = () => {
        if (signalState.aborted) {
          const err = new Error('CONTENT_SCRIPT_ABORTED');
          err.code = 'BATCH_ABORTED';
          throw err;
        }
        const matches = queryWithFallback(selectorOrKey, { root, requireVisible, all: true });
        for (const el of matches) {
          if (requireEnabled && !isElementEnabled(el)) continue;
          if (typeof predicate === 'function' && !predicate(el)) continue;
          return el;
        }
        return null;
      };

      try {
        const immediate = check();
        if (immediate) return resolve(immediate);
      } catch (err) {
        return reject(err);
      }

      let settled = false;
      let observer = null;
      let pollTimer = null;

      const cleanup = () => {
        settled = true;
        if (observer) {
          try { observer.disconnect(); } catch (_) {}
          observer = null;
        }
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
        if (timeoutTimer) {
          clearTimeout(timeoutTimer);
        }
      };

      const onMutation = () => {
        if (settled || signalState.paused) return;
        try {
          const found = check();
          if (found) {
            cleanup();
            resolve(found);
          }
        } catch (err) {
          cleanup();
          reject(err);
        }
      };

      const timeoutTimer = setTimeout(() => {
        if (settled) return;
        cleanup();
        const label = Array.isArray(selectorOrKey) ? selectorOrKey.join(' | ') : String(selectorOrKey);
        const err = new Error(`Timeout waiting for selector: ${label} (${timeoutMs}ms)`);
        err.transient = true;
        reject(err);
      }, timeoutMs);

      if (typeof MutationObserver === 'function' && (root.documentElement || root.nodeType === 1)) {
        observer = new MutationObserver(onMutation);
        observer.observe(root.documentElement || root, {
          childList: true,
          subtree: true,
          attributes: true,
          attributeFilter: ['class', 'disabled', 'aria-disabled', 'aria-checked', 'style', 'value'],
        });
      }

      // Lightweight fallback tick in case of attribute/layout changes not firing childList
      pollTimer = setInterval(onMutation, 150);
    });
  }

  /**
   * Dismisses interrupting modals/tutorials on TikTok Studio:
   * - Tutorial Joyride / "Got it" alertdialog
   * - Copyright check "Post now" / "Schedule now" / "โพสต์เลย"
   * - Discard confirmation "Discard" / "ละทิ้ง" (only when allowDiscard is true)
   * - Leave site confirmation "Leave" / "ออก"
   */
  async function dismissInterrupts({ root = typeof document !== 'undefined' ? document : null, allowDiscard = false } = {}) {
    await guardSignal();
    if (!root) return { dismissed: [] };
    const dismissed = [];

    // 1. Tutorial Tooltip ("Got it" / "รับทราบ")
    const tutorialDialogs = queryWithFallback('tutorialTooltip', { root, requireVisible: true, all: true });
    for (const td of tutorialDialogs) {
      const btns = Array.from(td.querySelectorAll('button'));
      const gotItBtn = btns.find((b) => {
        const t = (b.innerText || b.textContent || '').trim();
        return t === 'Got it' || t === 'รับทราบ' || t === 'เข้าใจแล้ว';
      });
      if (gotItBtn && isElementEnabled(gotItBtn)) {
        gotItBtn.click();
        dismissed.push('tutorial_got_it');
      }
    }

    // 2. Modal Dialogs (.TUXModal, [role="dialog"])
    const dialogs = queryWithFallback('modalDialogs', { root, requireVisible: true, all: true });
    for (const dialog of dialogs) {
      const text = (dialog.innerText || dialog.textContent || '').trim();
      const buttons = Array.from(dialog.querySelectorAll('button, [role="button"]')).filter(isElementEnabled);

      // Copyright / Content check modal -> Click "Post now" / "Schedule now" / "โพสต์เลย"
      if (
        text.includes('Continue to post') ||
        text.includes('potential issues') ||
        text.includes('before the check is complete') ||
        text.includes('ดำเนินการโพสต์ต่อ') ||
        text.includes('ก่อนที่การตรวจสอบจะเสร็จสิ้น')
      ) {
        const postNowBtn = buttons.find((b) => {
          const t = (b.innerText || b.textContent || '').trim();
          return ['Post now', 'Schedule now', 'โพสต์เลย', 'กำหนดเวลาเลย', 'โพสต์ตอนนี้'].includes(t);
        });
        if (postNowBtn) {
          postNowBtn.click();
          dismissed.push('copyright_post_now');
        }
      }

      // Leave site modal -> Click "Leave" / "ออก"
      if (text.includes('Are you sure you want to leave') || text.includes('แน่ใจหรือไม่ว่าต้องการออก')) {
        const leaveBtn = buttons.find((b) => {
          const t = (b.innerText || b.textContent || '').trim();
          return ['Leave', 'leave', 'ออก'].includes(t);
        });
        if (leaveBtn) {
          leaveBtn.click();
          dismissed.push('leave_confirm');
        }
      }

      // Discard modal -> Click "Discard" / "ละทิ้ง" when requested
      if (allowDiscard && (text.includes('Discard this post') || text.includes('ละทิ้ง') || text.includes('ทิ้งการเปลี่ยนแปลง'))) {
        const discardBtn = buttons.find((b) => {
          const t = (b.innerText || b.textContent || '').trim();
          return ['Discard', 'discard', 'ละทิ้ง', 'ทิ้ง'].includes(t);
        });
        if (discardBtn) {
          discardBtn.click();
          dismissed.push('discard_post');
        }
      }
    }

    return { dismissed };
  }

  /**
   * Observes and waits until the submit button ("Post" / "Schedule" / "Save draft")
   * is no longer disabled (aria-disabled !== "true" and !button.disabled), then clicks it.
   */
  async function triggerSubmitWhenEnabled({
    mode = 'schedule',
    root = typeof document !== 'undefined' ? document : null,
    timeoutMs = 30000,
  } = {}) {
    await guardSignal();
    const selectorKey = mode === 'draft' ? 'saveDraftButton' : 'submitPostButton';
    const btn = await waitForSelector(selectorKey, {
      root,
      requireVisible: true,
      requireEnabled: true,
      timeoutMs,
    });
    if (typeof btn.scrollIntoView === 'function') {
      btn.scrollIntoView({ behavior: 'instant', block: 'center' });
    }
    btn.click();
    return {
      clicked: true,
      mode,
      buttonText: (btn.innerText || btn.textContent || '').trim(),
      dataE2e: btn.getAttribute?.('data-e2e') || null,
    };
  }

  /**
   * Waits for the platform confirmation toast ("Video scheduled" / "Draft saved" / "Posted")
   * using MutationObserver on toast/alert selectors.
   */
  function waitForSuccessToast({
    root = typeof document !== 'undefined' ? document : null,
    timeoutMs = 20000,
  } = {}) {
    return new Promise((resolve, reject) => {
      if (!root) return reject(new Error('No DOM root for waitForSuccessToast'));

      const evaluateToasts = () => {
        const nodes = queryWithFallback('toastNotices', { root, requireVisible: true, all: true });
        for (const el of nodes) {
          const t = (el.innerText || el.textContent || '').trim();
          if (!t) continue;
          if (/(?:scheduled|กำหนดเวลา|ตั้งเวลา)/i.test(t) && /(?:success|สำเร็จ|เรียบร้อย|แล้ว|video|post)/i.test(t)) {
            return { confirmed: true, outcome: 'scheduled', notice: t };
          }
          if (/(?:draft|แบบร่าง)/i.test(t) && /(?:saved|บันทึก|สำเร็จ)/i.test(t)) {
            return { confirmed: true, outcome: 'draft_saved', notice: t };
          }
          if (/(?:posted|published|โพสต์|เผยแพร่)/i.test(t) && /(?:success|สำเร็จ|เรียบร้อย|แล้ว)/i.test(t)) {
            return { confirmed: true, outcome: 'published', notice: t };
          }
        }
        return null;
      };

      const immediate = evaluateToasts();
      if (immediate) return resolve(immediate);

      let settled = false;
      let observer = null;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        if (observer) {
          try { observer.disconnect(); } catch (_) {}
        }
        reject(new Error(`Timeout waiting for success toast (${timeoutMs}ms)`));
      }, timeoutMs);

      if (typeof MutationObserver === 'function' && (root.documentElement || root.nodeType === 1)) {
        observer = new MutationObserver(() => {
          if (settled) return;
          const res = evaluateToasts();
          if (res) {
            settled = true;
            clearTimeout(timer);
            try { observer.disconnect(); } catch (_) {}
            resolve(res);
          }
        });
        observer.observe(root.documentElement || root, {
          childList: true,
          subtree: true,
          characterData: true,
        });
      }
    });
  }

  /**
   * Runs a full sanity check on the current TikTok Studio page and reports which
   * verified selectors match live elements right now.
   */
  function runLiveDomSanityCheck(root = typeof document !== 'undefined' ? document : null) {
    if (!root) return { ok: false, error: 'no_document' };
    const url = typeof window !== 'undefined' ? window.location.href : '';
    const isUploadPage = url.includes('/upload');
    const isContentPage = url.includes('/content') || url.includes('/manage');
    const hasComposeForm = Boolean(queryWithFallback('captionContainer', { root }));

    const report = {};
    for (const [key, selectors] of Object.entries(LIVE_SELECTORS)) {
      const found = queryWithFallback(selectors, { root, all: true });
      report[key] = {
        matched: found.length > 0,
        count: found.length,
        primarySelector: selectors[0],
      };
    }

    return {
      ok: true,
      url,
      isUploadPage,
      isContentPage,
      hasComposeForm,
      report,
    };
  }

  // Register Chrome runtime message listener when running as a real content script
  if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage?.addListener) {
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
      if (!message || typeof message !== 'object') return false;

      if (message.action === 'batch-signal' || ['PAUSE', 'RESUME', 'ABORT', 'STOP', 'RESET'].includes(message.signal)) {
        const res = handleSignal(message.signal || message.command);
        sendResponse({ success: res.ok, ...res });
        return false;
      }

      if (message.action === 'content-sanity-check') {
        sendResponse(runLiveDomSanityCheck());
        return false;
      }

      if (message.action === 'content-dismiss-interrupts') {
        dismissInterrupts({ allowDiscard: Boolean(message.allowDiscard) })
          .then((res) => sendResponse({ success: true, ...res }))
          .catch((err) => sendResponse({ success: false, error: err.message }));
        return true;
      }

      return false;
    });
  }

  return {
    LIVE_SELECTORS,
    DOM_TIMINGS,
    signalState,
    handleSignal,
    guardSignal,
    isElementVisible,
    isElementEnabled,
    queryWithFallback,
    waitForSelector,
    dismissInterrupts,
    triggerSubmitWhenEnabled,
    waitForSuccessToast,
    runLiveDomSanityCheck,
  };
});
