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

  // ---- Counting scheduled posts from the Studio > Content list (no "Scheduled" tab exists) ----
  // Each row shows a date badge: a FUTURE time = scheduled post, a past time = already published.
  const MONTHS = {
    jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
    'ม.ค.': 0, 'ก.พ.': 1, 'มี.ค.': 2, 'เม.ย.': 3, 'พ.ค.': 4, 'มิ.ย.': 5, 'ก.ค.': 6, 'ส.ค.': 7, 'ก.ย.': 8, 'ต.ค.': 9, 'พ.ย.': 10, 'ธ.ค.': 11,
  };
  const DAY_MS = 24 * 3600 * 1000;
  const DEFAULT_TZ_HOURS = 7; // the channel is on Bangkok time: "(GMT+7) Bangkok"
  const EN_BADGE = /^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?,?\s+(\d{1,2}):(\d{2})\s*(AM|PM)?(?:\s*\(GMT([+-]\d{1,2})(?::?\d{2})?\).*)?$/i;
  const TH_BADGE = /^(\d{1,2})\s+(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)(?:\s+(\d{4}))?,?\s+(\d{1,2}):(\d{2})\s*(AM|PM)?(?:\s*\(GMT([+-]\d{1,2})(?::?\d{2})?\).*)?$/i;

  // One badge line -> epoch ms, or null when the line is not a date badge.
  function parseBadgeTime(line, nowMs = Date.now()) {
    const text = String(line || '').replace(/\s+/g, ' ').trim();
    let day, month, year, hour, minute, ampm, tz;
    let m = EN_BADGE.exec(text);
    if (m) {
      month = MONTHS[m[1].toLowerCase()];
      day = +m[2]; year = m[3] ? +m[3] : null; hour = +m[4]; minute = +m[5]; ampm = m[6]; tz = m[7];
    } else if ((m = TH_BADGE.exec(text))) {
      month = MONTHS[m[2]];
      day = +m[1]; year = m[3] ? +m[3] : null; hour = +m[4]; minute = +m[5]; ampm = m[6]; tz = m[7];
    } else {
      return null;
    }
    if (month === undefined || day < 1 || day > 31 || minute > 59) return null;
    if (ampm) {
      const pm = ampm.toUpperCase() === 'PM';
      if (hour < 1 || hour > 12) return null;
      hour = (hour % 12) + (pm ? 12 : 0);
    } else if (hour > 23) {
      return null;
    }
    const offsetMs = (tz !== undefined ? Number(tz) : DEFAULT_TZ_HOURS) * 3600 * 1000;
    const at = (y) => Date.UTC(y, month, day, hour, minute) - offsetMs;
    if (year) return at(year > 2400 ? year - 543 : year);
    // No year shown: a scheduled post is at most ~30 days ahead, a published one is in the past.
    const nowYear = new Date(nowMs + offsetMs).getUTCFullYear();
    let ts = at(nowYear);
    if (ts > nowMs + 31 * DAY_MS) ts = at(nowYear - 1);
    else if (ts < nowMs - 335 * DAY_MS) ts = at(nowYear + 1);
    return ts;
  }

  // Studio > Content innerText -> how many rows are scheduled (badge time in the future).
  // `complete` is true once a published row older than 31 days was seen: anything created earlier
  // cannot still be scheduled (TikTok allows at most 30 days ahead), so the count is final.
  // count is null when no row had a readable badge (never guess 0).
  // The Content list is virtualized: only the rows near the viewport exist in the DOM, so a single
  // read sees ~8 rows. parseListRows() turns one read into keyed rows; the caller scrolls step by step
  // and merges every read into one Map (key -> badge time) before summarizeRows().
  function parseListRows(text, nowMs = Date.now()) {
    const chunks = String(text || '').split(/\n(?=\d{1,2}:\d{2}(?::\d{2})?\n)/).slice(1);
    const rows = [];
    for (const chunk of chunks) {
      const lines = chunk.split('\n').map((l) => l.trim()).filter(Boolean);
      let ts = null;
      let badge = '';
      for (const line of lines) {
        const parsed = parseBadgeTime(line, nowMs);
        if (parsed !== null) { ts = parsed; badge = line; }
      }
      if (ts === null) continue; // pinned rows and anything without a date badge
      rows.push({ key: `${lines[0]}|${lines[1] || ''}|${badge}`.slice(0, 220), ts });
    }
    return rows;
  }

  // rows: array of { ts } (or a Map key -> ts). count is null when no row had a readable badge.
  function summarizeRows(rows, nowMs = Date.now()) {
    const list = rows instanceof Map ? Array.from(rows.values()).map((ts) => ({ ts })) : rows;
    let scheduled = 0;
    let complete = false;
    for (const row of list) {
      if (row.ts > nowMs) scheduled += 1;
      else if (row.ts < nowMs - 31 * DAY_MS) complete = true;
    }
    return { count: list.length ? scheduled : null, rowsParsed: list.length, complete };
  }

  // One-shot variant for a text that already holds the whole list (tests, non-virtualized pages).
  // Stops at the first published row older than 31 days.
  function countScheduledFromListText(text, nowMs = Date.now()) {
    const kept = [];
    for (const row of parseListRows(text, nowMs)) {
      kept.push(row);
      if (row.ts < nowMs - 31 * DAY_MS) break;
    }
    return summarizeRows(kept, nowMs);
  }

  // Fold a scheduled count read from the list into a detectQuota() result.
  function applyScheduledCount(quota, count, options = {}) {
    const maxSchedule = options.maxScheduleQuota || MAX_SCHEDULE_QUOTA;
    const base = quota || {};
    if (typeof count !== 'number') return base;
    const remainingSchedule = Math.max(0, maxSchedule - count);
    const draftPart = base.draftCount != null ? ` · แบบร่าง ${base.draftCount}/${base.maxDraft || MAX_DRAFT_QUOTA}` : '';
    return {
      ...base,
      success: true,
      scheduledCount: count,
      maxSchedule,
      remainingSchedule,
      isScheduleFull: remainingSchedule === 0,
      recommendedBatchLimit: Math.min(30, remainingSchedule),
      source: base.source && base.source !== 'unknown' ? `${base.source}+content_rows` : 'content_rows',
      message: `ตรวจพบใน TikTok Studio: ตั้งเวลาแล้ว ${count}/${maxSchedule} (เหลือ ${remainingSchedule})${draftPart}`,
    };
  }

  // "Drafts 3" / "แบบร่าง 3" is the second tab of Studio > Content. null when the page has no such tab.
  function parseDraftCountFromText(text) {
    const m = /(?:^|\n)\s*(?:Drafts|แบบร่าง)\s+(\d+)\s*(?:\n|$)/i.exec(String(text || ''));
    return m ? Number(m[1]) : null;
  }

  // Fold a draft count read from the Content page into a quota result (keeps the schedule fields as they are).
  function applyDraftCount(quota, count, options = {}) {
    const maxDraft = options.maxDraftQuota || MAX_DRAFT_QUOTA;
    const base = quota || {};
    if (typeof count !== 'number') return base;
    const remainingDraft = Math.max(0, maxDraft - count);
    return {
      ...base,
      success: true,
      draftCount: count,
      maxDraft,
      remainingDraft,
      isDraftFull: remainingDraft === 0,
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
    parseBadgeTime,
    parseListRows,
    summarizeRows,
    countScheduledFromListText,
    applyScheduledCount,
    parseDraftCountFromText,
    applyDraftCount,
  };
});
