const { test } = require('node:test');
const assert = require('node:assert/strict');
const detector = require('./quota_detector.js');

function mockTab(text, role = 'tab', className = 'TUXTabBar-tab') {
  return {
    innerText: text,
    textContent: text,
    getAttribute(name) {
      if (name === 'role') return role;
      if (name === 'class') return className;
      return null;
    },
    className,
  };
}

function mockDoc(tabs = [], rehydrationJson = null) {
  return {
    querySelectorAll(sel) {
      if (sel.includes('tab') || sel.includes('button')) {
        return tabs;
      }
      return [];
    },
    getElementById(id) {
      if (id === '__UNIVERSAL_DATA_FOR_REHYDRATION__' && rehydrationJson) {
        return { textContent: typeof rehydrationJson === 'string' ? rehydrationJson : JSON.stringify(rehydrationJson) };
      }
      return null;
    },
  };
}

test('extractCount parses various Thai and English quota string formats', () => {
  assert.deepEqual(detector.extractCount('กำหนดเวลาแล้ว (5)'), { count: 5, max: null });
  assert.deepEqual(detector.extractCount('กำหนดเวลาแล้ว 18/30'), { count: 18, max: 30 });
  assert.deepEqual(detector.extractCount('Scheduled (25/30)'), { count: 25, max: 30 });
  assert.deepEqual(detector.extractCount('แบบร่าง (3)'), { count: 3, max: null });
  assert.deepEqual(detector.extractCount('Drafts [0]'), { count: 0, max: null });
  assert.deepEqual(detector.extractCount('ตั้งเวลา 12 รายการ'), { count: 12, max: null });
  assert.equal(detector.extractCount('ไม่มีตัวเลขในนี้'), null);
});

test('parseTabsFromDocument parses Thai TikTok Studio tab bar', () => {
  const tabs = [
    mockTab('วิดีโอ (155)'),
    mockTab('กำหนดเวลาแล้ว (7)'),
    mockTab('แบบร่าง (3)'),
  ];
  const doc = mockDoc(tabs);
  const res = detector.parseTabsFromDocument(doc);
  assert.equal(res.published, 155);
  assert.equal(res.scheduled, 7);
  assert.equal(res.draft, 3);
});

test('parseTabsFromDocument parses English TikTok Studio tab bar', () => {
  const tabs = [
    mockTab('Videos (42)'),
    mockTab('Scheduled (29/30)'),
    mockTab('Drafts (10/30)'),
  ];
  const doc = mockDoc(tabs);
  const res = detector.parseTabsFromDocument(doc);
  assert.equal(res.published, 42);
  assert.equal(res.scheduled, 29);
  assert.equal(res.draft, 10);
});

test('parseRehydrationData extracts counts from nested hydration state', () => {
  const payload = {
    __DEFAULT_SCOPE__: {
      'webapp.creator-manage': {
        scheduled_count: 14,
        draft_count: 5,
      },
    },
  };
  const res = detector.parseRehydrationData(JSON.stringify(payload));
  assert.equal(res.scheduled, 14);
  assert.equal(res.draft, 5);
});

test('detectQuota computes remaining slots and safe recommended batch size', () => {
  const tabs = [
    mockTab('วิดีโอ (100)'),
    mockTab('กำหนดเวลาแล้ว (12)'),
    mockTab('แบบร่าง (4)'),
  ];
  const doc = mockDoc(tabs);
  const q = detector.detectQuota(doc);

  assert.equal(q.success, true);
  assert.equal(q.scheduledCount, 12);
  assert.equal(q.remainingSchedule, 18);
  assert.equal(q.draftCount, 4);
  assert.equal(q.remainingDraft, 26);
  assert.equal(q.isScheduleFull, false);
  assert.equal(q.isDraftFull, false);
  assert.equal(q.recommendedBatchLimit, 18);
  assert.match(q.message, /ตั้งเวลาแล้ว 12\/30/);
});

test('detectQuota flags quota full when scheduled count reaches 30', () => {
  const tabs = [
    mockTab('กำหนดเวลาแล้ว (30/30)'),
    mockTab('แบบร่าง (30/30)'),
  ];
  const doc = mockDoc(tabs);
  const q = detector.detectQuota(doc);

  assert.equal(q.success, true);
  assert.equal(q.scheduledCount, 30);
  assert.equal(q.remainingSchedule, 0);
  assert.equal(q.isScheduleFull, true);
  assert.equal(q.isDraftFull, true);
  assert.equal(q.recommendedBatchLimit, 0);
});

test('detectQuota degrades safely on empty/null document', () => {
  const q = detector.detectQuota(null);
  assert.equal(q.success, false);
  assert.equal(q.scheduledCount, null);
  assert.equal(q.remainingSchedule, null);
  assert.equal(q.recommendedBatchLimit, 30);
});

// ---- scheduled count from the Studio > Content list ----
const NOW = Date.parse('2026-11-10T04:30:00Z'); // 2026-11-10 11:30 Bangkok

function listText(rows) {
  return ['Upload', 'MANAGE', 'Posts 217', 'Drafts 0', 'Posts (Created on)'].concat(
    rows.flatMap(([dur, caption, badge]) => [dur, caption, badge, 'Everyone', '0', '0', '0'])).join('\n');
}

test('parseBadgeTime reads English and Thai badges, 12h/24h, with or without GMT', () => {
  const bkk = (iso) => Date.parse(iso) - 7 * 3600 * 1000; // wall clock in Bangkok -> epoch
  assert.equal(detector.parseBadgeTime('Nov 10, 6:00 PM (GMT+7) Bangkok', NOW), bkk('2026-11-10T18:00:00Z'));
  assert.equal(detector.parseBadgeTime('Nov 10, 7:00 AM', NOW), bkk('2026-11-10T07:00:00Z'));
  assert.equal(detector.parseBadgeTime('10 พ.ย. 10:00 PM', NOW), bkk('2026-11-10T22:00:00Z'));
  assert.equal(detector.parseBadgeTime('11 พ.ย. 10:00 AM (GMT+7) Bangkok', NOW), bkk('2026-11-11T10:00:00Z'));
  assert.equal(detector.parseBadgeTime('Nov 10, 12:05 AM', NOW), bkk('2026-11-10T00:05:00Z'));
  assert.equal(detector.parseBadgeTime('Nov 10, 12:05 PM', NOW), bkk('2026-11-10T12:05:00Z'));
  assert.equal(detector.parseBadgeTime('Nov 10, 18:00', NOW), bkk('2026-11-10T18:00:00Z'));
  assert.equal(detector.parseBadgeTime('10 พ.ย. 2569 18:00', NOW), bkk('2026-11-10T18:00:00Z')); // Buddhist year
  assert.equal(detector.parseBadgeTime('Nov 10, 2025, 6:00 PM', NOW), bkk('2025-11-10T18:00:00Z'));
  // an explicit offset wins over the Bangkok default
  assert.equal(detector.parseBadgeTime('Nov 10, 6:00 PM (GMT+0)', NOW), Date.parse('2026-11-10T18:00:00Z'));
  for (const junk of ['Pinned', 'Everyone', '00:28', '0', '', null, 'Nov 40, 6:00 PM', 'Nov 10, 13:00 PM']) {
    assert.equal(detector.parseBadgeTime(junk, NOW), null, String(junk));
  }
});

test('year-less badges: far-future dates mean last year, far-past dates mean next year', () => {
  assert.equal(detector.parseBadgeTime('Dec 20, 8:00 AM', Date.parse('2026-01-05T00:00:00Z')), Date.parse('2025-12-20T01:00:00Z'));
  assert.equal(detector.parseBadgeTime('Jan 20, 8:00 AM', Date.parse('2026-12-30T00:00:00Z')), Date.parse('2027-01-20T01:00:00Z'));
});

test('countScheduledFromListText counts only future badges and ignores pinned rows', () => {
  const text = listText([
    ['00:44', 'BLUEWOW', 'Nov 10, 10:00 PM'],            // scheduled
    ['00:29', 'Toshino', 'Nov 10, 8:00 PM (GMT+7) Bangkok'], // scheduled
    ['00:28', 'JBL', 'Nov 11, 8:00 AM'],                  // scheduled
    ['00:27', 'BASIKE', 'Nov 10, 10:10 AM (GMT+7) Bangkok'], // already published (10:10 < 11:30)
    ['00:21', 'pinned clip', 'Pinned'],
    ['00:30', 'old', 'Nov 9, 7:35 AM'],
  ]);
  const r = detector.countScheduledFromListText(text, NOW);
  assert.equal(r.count, 3);
  assert.equal(r.rowsParsed, 5);
  assert.equal(r.complete, false); // never saw a row older than 31 days: not proven final
});

test('countScheduledFromListText is complete once a published row older than 31 days is reached', () => {
  const text = listText([
    ['00:44', 'a', 'Nov 10, 10:00 PM'],
    ['00:44', 'b', 'Oct 2, 7:00 AM'],  // 39 days ago
    ['00:44', 'c', 'Nov 20, 7:00 AM'], // must not be counted: list is sorted, but we stopped
  ]);
  const r = detector.countScheduledFromListText(text, NOW);
  assert.equal(r.count, 1);
  assert.equal(r.complete, true);
});

test('countScheduledFromListText never guesses: no readable badge -> null', () => {
  assert.equal(detector.countScheduledFromListText('', NOW).count, null);
  assert.equal(detector.countScheduledFromListText('Posts 217\nDrafts 0', NOW).count, null);
  assert.equal(detector.countScheduledFromListText(listText([['00:10', 'x', 'Pinned']]), NOW).count, null);
});

test('countScheduledFromListText handles a Thai-language page', () => {
  const text = ['โพสต์ 217', 'แบบร่าง 0',
    '00:28', 'เทียบกันชัดๆ', '11 พ.ย. 10:00 AM (GMT+7) Bangkok', 'ทุกคน', '0',
    '00:26', 'รีวิว', '10 พ.ย. 4:20 PM', 'ทุกคน', '0',
    '00:21', 'แกะกล่อง', '10 พ.ย. 10:10 AM', 'ทุกคน', '0'].join('\n');
  const r = detector.countScheduledFromListText(text, NOW);
  assert.equal(r.count, 2);
});

test('applyScheduledCount folds a list count into a detectQuota result', () => {
  const base = { success: true, draftCount: 0, maxDraft: 30, remainingDraft: 30, scheduledCount: null, remainingSchedule: null, source: 'dom_tabs' };
  const q = detector.applyScheduledCount(base, 15);
  assert.equal(q.scheduledCount, 15);
  assert.equal(q.remainingSchedule, 15);
  assert.equal(q.recommendedBatchLimit, 15);
  assert.equal(q.isScheduleFull, false);
  assert.equal(q.source, 'dom_tabs+content_rows');
  assert.match(q.message, /15\/30/);
  assert.equal(detector.applyScheduledCount(base, 30).isScheduleFull, true);
  assert.equal(detector.applyScheduledCount(base, 31).remainingSchedule, 0);
  assert.equal(detector.applyScheduledCount(base, null), base); // unknown stays unknown
  assert.equal(detector.applyScheduledCount(null, 4).scheduledCount, 4);
});

test('virtualized list: merging several partial reads counts every row once', () => {
  // each read only holds the rows near the viewport; consecutive reads overlap
  const read1 = listText([['00:44', 'a', 'Nov 10, 10:00 PM'], ['00:29', 'b', 'Nov 10, 8:00 PM'], ['00:28', 'c', 'Nov 11, 8:00 AM']]);
  const read2 = listText([['00:28', 'c', 'Nov 11, 8:00 AM'], ['00:27', 'd', 'Nov 10, 10:10 AM'], ['00:26', 'e', 'Nov 9, 7:00 AM']]);
  const read3 = listText([['00:26', 'e', 'Nov 9, 7:00 AM'], ['00:25', 'f', 'Oct 1, 7:00 AM']]);
  const seen = new Map();
  let r;
  for (const read of [read1, read2]) {
    for (const row of detector.parseListRows(read, NOW)) seen.set(row.key, row.ts);
    r = detector.summarizeRows(seen, NOW);
  }
  assert.equal(r.count, 3);          // a, b, c scheduled; d, e published; c not double counted
  assert.equal(r.rowsParsed, 5);
  assert.equal(r.complete, false);   // keep scrolling
  for (const row of detector.parseListRows(read3, NOW)) seen.set(row.key, row.ts);
  r = detector.summarizeRows(seen, NOW);
  assert.equal(r.count, 3);
  assert.equal(r.complete, true);    // reached a published row older than 31 days
  assert.equal(detector.summarizeRows(new Map(), NOW).count, null);
});

test('parseDraftCountFromText reads the Drafts tab in English and Thai, null when absent', () => {
  assert.equal(detector.parseDraftCountFromText('Posts 219\nDrafts 1\nYou can save up to 30 drafts'), 1);
  assert.equal(detector.parseDraftCountFromText('โพสต์ 219\nแบบร่าง 12\nx'), 12);
  assert.equal(detector.parseDraftCountFromText('Posts 219\nDrafts 0'), 0);
  assert.equal(detector.parseDraftCountFromText('You can save up to 30 drafts. Drafts expire after 60 days'), null);
  assert.equal(detector.parseDraftCountFromText(''), null);
});

test('applyDraftCount sets remaining drafts and flags a full draft quota', () => {
  const base = { success: true, scheduledCount: 12, remainingSchedule: 18 };
  const q = detector.applyDraftCount(base, 4);
  assert.equal(q.draftCount, 4);
  assert.equal(q.remainingDraft, 26);
  assert.equal(q.isDraftFull, false);
  assert.equal(q.scheduledCount, 12);
  assert.equal(detector.applyDraftCount(base, 30).isDraftFull, true);
  assert.equal(detector.applyDraftCount(base, 35).remainingDraft, 0);
  assert.equal(detector.applyDraftCount(base, null), base);
});
