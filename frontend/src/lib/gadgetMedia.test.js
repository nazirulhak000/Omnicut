import assert from 'node:assert/strict';
import test from 'node:test';
import {
  campaignProgress,
  readinessCounts,
  seriesLabel,
  statusLabel,
  generateScriptTemplate,
  calculateCampaignAnalytics,
} from './gadgetMedia.js';

test('campaignProgress reports 21 slots and published percentage', () => {
  const campaign = {
    slots: [
      { status: 'published' },
      { status: 'edited' },
      { status: 'planned' },
    ],
  };

  assert.deepEqual(campaignProgress(campaign), {
    total: 3,
    published: 1,
    edited: 1,
    inProgress: 1,
    percent: 33,
  });
});

test('labels and readiness counts have safe fallbacks', () => {
  assert.equal(seriesLabel('watch_before_buy'), 'ดูคลิปนี้ก่อนซื้อ');
  assert.equal(statusLabel('edited'), 'ตัดต่อแล้ว');
  assert.equal(statusLabel('unknown'), 'unknown');
  assert.deepEqual(readinessCounts({ ready_slots: 2, blocked_slots: 19, total_slots: 21 }), {
    ready: 2,
    blocked: 19,
    total: 21,
  });
});

test('generateScriptTemplate formats 5-part script without dots', () => {
  const res = generateScriptTemplate('watch_before_buy', { topic: 'Galaxy S26 FE', brand: 'Samsung' });
  assert.ok(res.hook.includes('Galaxy S26 FE'));
  assert.ok(res.script.includes('[Hook 0-2s]'));
  assert.ok(res.script.includes('[Evidence 3-8s]'));
  assert.ok(res.script.includes('[Explain 9-28s]'));
  assert.ok(res.script.includes('[Verdict 29-36s]'));
  assert.ok(res.script.includes('[CTA 37-40s]'));
  // Rule: ห้ามใส่ "..."/"…"/จุดไข่ปลาในบทพูดสคริปต์
  assert.ok(!res.script.includes('...'));
  assert.ok(!res.script.includes('…'));
});

test('calculateCampaignAnalytics aggregates views, follows, and rates', () => {
  const campaign = {
    slots: [
      { series: 'watch_before_buy', metrics: { views: 1000, follows: 50, comments: 10, completion_rate: 45.0 } },
      { series: 'watch_before_buy', metrics: { views: 2000, follows: 100, comments: 20, completion_rate: 55.0 } },
      { series: 'spec_in_plain_language', metrics: { views: 1000, follows: 30, comments: 5, completion_rate: 40.0 } },
      { series: 'real_vs_marketing', metrics: { views: 0, follows: 0, comments: 0, completion_rate: 0 } },
    ],
  };

  const analytics = calculateCampaignAnalytics(campaign);
  assert.equal(analytics.totalViews, 4000);
  assert.equal(analytics.totalFollows, 180);
  assert.equal(analytics.totalComments, 35);
  // (45 + 55 + 40) / 3 = 46.7%
  assert.equal(analytics.avgCompletionRate, 46.7);
  // (180 / 4000) * 1000 = 45.0
  assert.equal(analytics.followsPer1000Views, 45.0);
  assert.equal(analytics.series.watch_before_buy.views, 3000);
  assert.equal(analytics.series.watch_before_buy.follows, 150);
});
