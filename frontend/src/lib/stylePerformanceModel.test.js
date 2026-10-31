import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MIN_RELIABLE_SAMPLE,
  STYLE_GROUPS,
  buildStylePerformanceRows,
  formatCompletionRate,
  formatWatchTime,
  maxMedianViews,
  styleGroupLabel,
} from './stylePerformanceModel.js';

// Shape of PostLog.style_performance_report (tests/test_export_style_metadata.py).
const REPORT = {
  measured: 18,
  by_style_preset: [
    { style_preset: 'viral_punch', count: 7, median_views: 2400, avg_watch_time_sec: 9.5, completion_rate: 0.42 },
    { style_preset: 'smooth_showcase', count: 2, median_views: 9000, avg_watch_time_sec: null, completion_rate: null },
    { style_preset: 'clean_tech_review', count: 6, median_views: 1800, avg_watch_time_sec: 8.25, completion_rate: 0.3 },
    { style_preset: 'unspecified', count: 3, median_views: null, avg_watch_time_sec: null, completion_rate: null },
  ],
  by_hook_style: [
    { hook_style: 'warning', count: 4, median_views: 500, avg_watch_time_sec: 7, completion_rate: 0.5 },
    { hook_style: 'mystery_new', count: 1, median_views: 100, avg_watch_time_sec: null, completion_rate: null },
  ],
  by_story_format: [
    { story_format: 'classic', count: 18, median_views: 1500, avg_watch_time_sec: 8.0, completion_rate: 0.35 },
  ],
};

test('three groupings, matching the endpoint group_by values', () => {
  assert.deepEqual(STYLE_GROUPS.map((g) => g.id), ['style_preset', 'hook_style', 'story_format']);
});

test('rows keep the server order, sample size and nulls', () => {
  const rows = buildStylePerformanceRows(REPORT, 'style_preset');
  assert.deepEqual(rows.map((r) => r.id), ['viral_punch', 'smooth_showcase', 'clean_tech_review', 'unspecified']);
  assert.deepEqual(rows.map((r) => r.count), [7, 2, 6, 3]);
  assert.equal(rows[1].avgWatchTimeSec, null);
  assert.equal(rows[3].medianViews, null);
});

test('a group under the sample floor is low-sample and never the top group', () => {
  assert.equal(MIN_RELIABLE_SAMPLE, 5);
  const rows = buildStylePerformanceRows(REPORT, 'style_preset');
  const smooth = rows.find((r) => r.id === 'smooth_showcase');
  assert.equal(smooth.lowSample, true);
  assert.equal(smooth.isTop, false, 'highest median but only 2 posts');
  assert.deepEqual(rows.filter((r) => r.isTop).map((r) => r.id), ['viral_punch']);
});

test('no top group unless two groups have enough data', () => {
  assert.ok(buildStylePerformanceRows(REPORT, 'hook_style').every((r) => !r.isTop));
  assert.ok(buildStylePerformanceRows(REPORT, 'story_format').every((r) => !r.isTop));
  const tie = { by_style_preset: [
    { style_preset: 'viral_punch', count: 5, median_views: 100 },
    { style_preset: 'flash_deal', count: 9, median_views: 100 },
  ] };
  assert.ok(buildStylePerformanceRows(tie, 'style_preset').every((r) => !r.isTop), 'a tie has no winner');
});

test('labels come from the style catalog, hook styles and story formats', () => {
  assert.deepEqual(styleGroupLabel('style_preset', 'viral_punch'), { label: 'ไวรัล กระชับ มีพลัง', sublabel: 'Viral Punch' });
  assert.equal(styleGroupLabel('hook_style', 'warning').label, 'เตือนภัย / หยุดก่อน');
  assert.equal(styleGroupLabel('story_format', 'countdown').label, 'นับถอยหลัง 3 เหตุผล');
  assert.equal(styleGroupLabel('style_preset', 'unspecified').label, 'ไม่ระบุ');
  assert.deepEqual(styleGroupLabel('hook_style', 'mystery_new'), { label: 'mystery_new', sublabel: '' });
  assert.deepEqual(styleGroupLabel('style_preset', 'legacy_x'), { label: 'legacy_x', sublabel: '' });
});

test('empty or malformed reports give no rows', () => {
  assert.deepEqual(buildStylePerformanceRows(null, 'style_preset'), []);
  assert.deepEqual(buildStylePerformanceRows({ by_style_preset: 'x' }, 'style_preset'), []);
  assert.equal(maxMedianViews([]), 0);
});

test('formatting: watch time in seconds, completion as a percent of a 0..1 fraction', () => {
  assert.equal(formatWatchTime(8.25), '8.3 วิ');
  assert.equal(formatWatchTime(null), null);
  assert.equal(formatCompletionRate(0.4235), '42.4%');
  assert.equal(formatCompletionRate(null), null);
  assert.equal(maxMedianViews(buildStylePerformanceRows(REPORT, 'style_preset')), 9000);
});
