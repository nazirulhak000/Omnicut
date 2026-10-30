import assert from 'node:assert/strict';
import * as nodeTest from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  MobileShell,
  MOBILE_TABS,
  normalizeMobileTab,
  readMobileTabFromSearch,
  buildMobileTabUrl,
} from './MobileShell.jsx';
import { ServerSleepingBanner } from './ServerSleepingBanner.jsx';
import { TodayScreen } from './TodayScreen.jsx';

const testFn = globalThis.it || globalThis.test || nodeTest.test;

function createFakeWindow(initialHref = 'https://studio.example/?mode=mobile') {
  const entries = [{ href: initialHref, state: null }];
  let idx = 0;
  const listeners = {};
  const location = {};

  const syncLocation = () => {
    const parsed = new URL(entries[idx].href, 'https://studio.example');
    location.href = parsed.href;
    location.search = parsed.search;
    location.pathname = parsed.pathname;
    location.hash = parsed.hash;
  };
  syncLocation();

  return {
    location,
    entries: () => entries.map((e) => e.href),
    history: {
      get state() {
        return entries[idx].state;
      },
      pushState(state, _title, url) {
        const resolved = new URL(url, location.href).href;
        entries.splice(idx + 1);
        entries.push({ href: resolved, state });
        idx += 1;
        syncLocation();
      },
      replaceState(state, _title, url) {
        const resolved = new URL(url, location.href).href;
        entries[idx] = { href: resolved, state };
        syncLocation();
      },
    },
    addEventListener(type, fn) {
      listeners[type] = fn;
    },
    removeEventListener(type, fn) {
      if (listeners[type] === fn) delete listeners[type];
    },
    trigger(type, ev = {}) {
      if (listeners[type]) listeners[type](ev);
    },
  };
}

testFn('MOBILE_TABS defines exact 5 mobile tabs in order: today, create, review, post, more', () => {
  assert.deepEqual(
    MOBILE_TABS.map((t) => ({ id: t.id, label: t.label })),
    [
      { id: 'today', label: 'วันนี้' },
      { id: 'create', label: 'สร้าง' },
      { id: 'review', label: 'ตรวจ' },
      { id: 'post', label: 'โพสต์' },
      { id: 'more', label: 'อื่นๆ' },
    ]
  );
  assert.equal(normalizeMobileTab('today'), 'today');
  assert.equal(normalizeMobileTab('REVIEW'), 'review');
  assert.equal(normalizeMobileTab('unknown'), null);
  assert.equal(readMobileTabFromSearch('?mode=mobile&tab=post'), 'post');
  assert.equal(
    buildMobileTabUrl('https://studio.example/?mode=mobile&intake=1', 'create'),
    '/?mode=mobile&intake=1&tab=create'
  );
});

testFn('MobileShell renders 5 bottom navigation tabs with badges and defaults to TodayScreen', () => {
  const win = createFakeWindow('https://studio.example/?mode=mobile');
  const html = renderToStaticMarkup(
    React.createElement(MobileShell, {
      win,
      badges: { create: 3, review: 12, post: 120 },
      jobs: [
        {
          product_name: 'พัดลมไอเย็น TTZ K106',
          completed_clips: 7,
          total_clips: 20,
          status: 'running',
        },
      ],
      todoCounts: { scriptsPending: 4, reviewPending: 9, postDue: 2 },
      health: { colab: 'ออนไลน์', gpu: 'Tesla T4 (NVENC)', apiKeys: 'พร้อมใช้ 5 คีย์' },
    })
  );

  // 5 tab labels exist
  for (const label of ['วันนี้', 'สร้าง', 'ตรวจ', 'โพสต์', 'อื่นๆ']) {
    assert.ok(html.includes(label), `Missing tab label ${label}`);
  }

  // Badges render properly (including 99+ cap)
  assert.ok(html.includes('mobile-tab-badge-create'));
  assert.ok(html.includes('mobile-tab-badge-review'));
  assert.ok(html.includes('99+'));

  // TodayScreen content rendered by default
  assert.ok(html.includes('7/20 คลิป'));
  assert.ok(html.includes('กำลังผลิต'));
  assert.ok(html.includes('ดูงานที่กำลังผลิต'));
  assert.ok(html.includes('รายการต้องทำวันนี้'));
  assert.ok(html.includes('4 รายการ'));
  assert.ok(html.includes('9 รายการ'));
  assert.ok(html.includes('2 รายการ'));
  assert.ok(html.includes('Tesla T4 (NVENC)'));
});

testFn('MobileShell renders "more" tab with clean 44px action buttons (library, command, /agy, settings, desktop)', () => {
  const win = createFakeWindow('https://studio.example/?mode=mobile&tab=more');
  const html = renderToStaticMarkup(
    React.createElement(MobileShell, {
      win,
      activeTab: 'more',
    })
  );

  assert.ok(html.includes('more-action-library'));
  assert.ok(html.includes('เปิดคลังคลิป'));
  assert.ok(html.includes('more-action-command'));
  assert.ok(html.includes('สั่งงาน AI'));
  assert.ok(html.includes('more-action-agy'));
  assert.ok(html.includes('เปิด AGY Terminal'));
  assert.ok(html.includes('more-action-settings'));
  assert.ok(html.includes('ตั้งค่าระบบ'));
  assert.ok(html.includes('more-action-desktop'));
  assert.ok(html.includes('สลับไปโหมดเดสก์ท็อป'));
});

testFn('MobileShell supports custom tab renderers and ServerSleepingBanner when sleeping/offline', () => {
  const html = renderToStaticMarkup(
    React.createElement(MobileShell, {
      activeTab: 'create',
      serverStatus: 'sleeping',
      renderCreate: () => React.createElement('div', { 'data-testid': 'custom-create' }, 'Custom Create View'),
    })
  );

  assert.ok(html.includes('custom-create'));
  assert.ok(html.includes('Custom Create View'));
  assert.ok(html.includes('เซิร์ฟเวอร์ Colab หลับหรือขาดการเชื่อมต่อ'));
  assert.ok(html.includes('ลองเชื่อมต่อใหม่'));
});

testFn('TodayScreen shows "ไม่ทราบ" for unavailable system health fields per Rule 8', () => {
  const html = renderToStaticMarkup(
    React.createElement(TodayScreen, {
      jobs: [],
      todoCounts: {},
      health: {},
      fetchImpl: null,
    })
  );

  assert.ok(html.includes('0/20 คลิป'));
  const unknownMatches = html.match(/ไม่ทราบ/g) || [];
  assert.equal(unknownMatches.length, 3);
});

testFn('ServerSleepingBanner hides when online and renders accessible alert when sleeping or offline', () => {
  const onlineHtml = renderToStaticMarkup(
    React.createElement(ServerSleepingBanner, { status: 'online' })
  );
  assert.equal(onlineHtml, '');

  const sleepingHtml = renderToStaticMarkup(
    React.createElement(ServerSleepingBanner, {
      status: 'sleeping',
      lastSeenAt: 1700000000000,
    })
  );
  assert.ok(sleepingHtml.includes('role="alert"'));
  assert.ok(sleepingHtml.includes('เซิร์ฟเวอร์ Colab หลับหรือขาดการเชื่อมต่อ'));
  assert.ok(sleepingHtml.includes('ลองเชื่อมต่อใหม่'));
});
