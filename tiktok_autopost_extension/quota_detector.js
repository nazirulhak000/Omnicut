// OmniCut TikTok Studio Quota Detector
// Detects current Scheduled and Draft post counts from TikTok Studio,
// calculates remaining quota (out of max 30 each), and advises safe batch limits.
// Pure & dependency-free: runs in sidepanel, background worker, or Node tests.
(function attachQuotaDetector(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.OmniCutQuotaDetector = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  const MAX_SCHEDULE_QUOTA = 30;
  const MAX_DRAFT_QUOTA = 30;

  const KEYWORDS = {
    schedule: ['กำหนดเวลาแล้ว', 'กำหนดเวลา', 'ตั้งเวลาแล้ว', 'ตั้งเวลา', 'scheduled', 'schedule'],
    draft: ['แบบร่าง', 'ดราฟต์', 'ดราฟท์', 'drafts', 'draft'],
    published: ['วิดีโอ', 'โพสต์แล้ว', 'เผยแพร่แล้ว', 'videos', 'published', 'posts'],
  };

  function norm(str) {
    return String(str || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  // Extracts number from a string like "กำหนดเวลาแล้ว (5)", "5/30", "Drafts (12)", "แบบร่าง 0"
  function extractCount(text) {
    if (!text) return null;
    const str = String(text).trim();

    // Pattern 1: "(5/30)" or "5/30"
    const ratioMatch = str.match(/(\d+)\s*\/\s*(\d+)/);
    if (ratioMatch) {
      return { count: parseInt(ratioMatch[1], 10), max: parseInt(ratioMatch[2], 10) };
    }

    // Pattern 2: "(5)" or "[5]"
    const parenMatch = str.match(/[\(\[\{]\s*(\d+)\s*[\)\]\}]/);
    if (parenMatch) {
      return { count: parseInt(parenMatch[1], 10), max: null };
    }

    // Pattern 3: Trailing or leading number e.g. "กำหนดเวลา 5" or "5 Drafts"
    const numMatch = str.match(/\b(\d+)\b/);
    if (numMatch) {
      return { count: parseInt(numMatch[1], 10), max: null };
    }

    return null;
  }

  function matchesKind(text, kind) {
    const t = norm(text);
    if (!t) return false;
    const list = KEYWORDS[kind] || [];
    return list.some(k => t.includes(norm(k)));
  }

  function parseTabsFromDocument(doc) {
    if (!doc || typeof doc.querySelectorAll !== 'function') {
      return { scheduled: null, draft: null, published: null };
    }

    const tabSelectors = [
      '[role="tab"]',
      '[data-tt*="tab"]',
      '[data-tt*="Tab"]',
      '.TUXTabBar-tab',
      '.TUXTabBar-item',
      '[class*="TabBar"] button',
      '[class*="tabBar"] button',
      '[class*="tab_"]',
      '[class*="Tab_"]',
      'button[id*="tab"]',
    ];

    let tabs = [];
    for (const sel of tabSelectors) {
      try {
        const found = Array.from(doc.querySelectorAll(sel));
        if (found.length > 0) {
          tabs = found;
          break;
        }
      } catch (_) {}
    }

    // Fallback: query all buttons and links in main header nav if no explicit tabs
    if (!tabs.length) {
      try {
        tabs = Array.from(doc.querySelectorAll('header button, nav button, [class*="header"] button, [class*="nav"] button, div[role="navigation"] button'));
      } catch (_) {}
    }

    let scheduled = null;
    let draft = null;
    let published = null;

    for (const tab of tabs) {
      const fullText = (tab.innerText || tab.textContent || '').trim();
      if (!fullText) continue;

      if (matchesKind(fullText, 'schedule')) {
        const res = extractCount(fullText);
        scheduled = res ? res.count : (scheduled ?? 0);
      } else if (matchesKind(fullText, 'draft')) {
        const res = extractCount(fullText);
        draft = res ? res.count : (draft ?? 0);
      } else if (matchesKind(fullText, 'published')) {
        const res = extractCount(fullText);
        published = res ? res.count : (published ?? null);
      }
    }

    return { scheduled, draft, published };
  }

  function parseRehydrationData(doc) {
    if (!doc) return { scheduled: null, draft: null };
    let json = null;
    try {
      if (typeof doc === 'string') {
        json = JSON.parse(doc);
      } else if (typeof doc.getElementById === 'function') {
        const el = doc.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
        if (el && el.textContent) json = JSON.parse(el.textContent);
      }
    } catch (_) {
      return { scheduled: null, draft: null };
    }

    if (!json || typeof json !== 'object') return { scheduled: null, draft: null };

    const searchObj = (obj, depth = 0) => {
      if (!obj || depth > 4 || typeof obj !== 'object') return {};
      let foundSched = null;
      let foundDraft = null;

      for (const [k, v] of Object.entries(obj)) {
        const lk = k.toLowerCase();
        if ((lk.includes('schedule') || lk.includes('scheduled')) && (lk.includes('count') || lk.includes('total'))) {
          if (typeof v === 'number') foundSched = v;
        }
        if (lk.includes('draft') && (lk.includes('count') || lk.includes('total'))) {
          if (typeof v === 'number') foundDraft = v;
        }
        if (foundSched !== null && foundDraft !== null) break;
      }

      if (foundSched === null || foundDraft === null) {
        for (const v of Object.values(obj)) {
          if (v && typeof v === 'object') {
            const nested = searchObj(v, depth + 1);
            if (foundSched === null && nested.scheduled !== null) foundSched = nested.scheduled;
            if (foundDraft === null && nested.draft !== null) foundDraft = nested.draft;
          }
        }
      }
      return { scheduled: foundSched, draft: foundDraft };
    };

    return searchObj(json);
  }

  function detectQuota(doc, options = {}) {
    const maxSchedule = options.maxScheduleQuota || MAX_SCHEDULE_QUOTA;
    const maxDraft = options.maxDraftQuota || MAX_DRAFT_QUOTA;

    let scheduledCount = null;
    let draftCount = null;
    let publishedCount = null;
    let source = 'unknown';

    // 1. Try DOM tabs
    if (doc) {
      const fromTabs = parseTabsFromDocument(doc);
      if (fromTabs.scheduled !== null || fromTabs.draft !== null) {
        scheduledCount = fromTabs.scheduled;
        draftCount = fromTabs.draft;
        publishedCount = fromTabs.published;
        source = 'dom_tabs';
      }

      // 2. Try Rehydration script if tabs didn't yield both
      if (scheduledCount === null || draftCount === null) {
        const fromRehyd = parseRehydrationData(doc);
        if (fromRehyd.scheduled !== null && scheduledCount === null) {
          scheduledCount = fromRehyd.scheduled;
          source = source === 'unknown' ? 'rehydration' : 'hybrid';
        }
        if (fromRehyd.draft !== null && draftCount === null) {
          draftCount = fromRehyd.draft;
          source = source === 'unknown' ? 'rehydration' : 'hybrid';
        }
      }
    }

    const remainingSchedule = scheduledCount != null ? Math.max(0, maxSchedule - scheduledCount) : null;
    const remainingDraft = draftCount != null ? Math.max(0, maxDraft - draftCount) : null;

    const isScheduleFull = remainingSchedule === 0;
    const isDraftFull = remainingDraft === 0;

    let recommendedBatchLimit = 30;
    if (remainingSchedule !== null) {
      recommendedBatchLimit = Math.min(30, Math.max(0, remainingSchedule));
    }

    let message = '';
    if (scheduledCount != null && draftCount != null) {
      message = `ตรวจพบใน TikTok Studio: ตั้งเวลาแล้ว ${scheduledCount}/${maxSchedule} (เหลือ ${remainingSchedule}) · แบบร่าง ${draftCount}/${maxDraft} (เหลือ ${remainingDraft})`;
    } else if (scheduledCount != null) {
      message = `ตรวจพบใน TikTok Studio: ตั้งเวลาแล้ว ${scheduledCount}/${maxSchedule} (เหลือโควตา ${remainingSchedule} คลิป)`;
    } else if (draftCount != null) {
      message = `ตรวจพบใน TikTok Studio: แบบร่าง ${draftCount}/${maxDraft} (เหลือโควตา ${remainingDraft} คลิป)`;
    } else {
      message = 'ยังไม่ได้เปิดหรือตรวจไม่พบข้อมูลโควตาในแท็บ TikTok Studio — ใช้โควตามาตรฐานสูงสุด 30 คลิป';
    }

    return {
      success: scheduledCount !== null || draftCount !== null,
      scheduledCount,
      draftCount,
      publishedCount,
      maxSchedule,
      maxDraft,
      remainingSchedule,
      remainingDraft,
      isScheduleFull,
      isDraftFull,
      recommendedBatchLimit,
      source,
      message,
    };
  }

  return {
    MAX_SCHEDULE_QUOTA,
    MAX_DRAFT_QUOTA,
    norm,
    extractCount,
    matchesKind,
    parseTabsFromDocument,
    parseRehydrationData,
    detectQuota,
  };
});
