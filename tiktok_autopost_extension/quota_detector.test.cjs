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
