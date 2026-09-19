import test from 'node:test';
import assert from 'node:assert/strict';

import {
  computeAreaLineChart,
  findClosestChartPoint,
  sortChronological,
  aggregateDailyTrends,
  computeXAxisTicks,
} from './chartModel.js';

test('empty or non-array data returns empty chart geometry without crashing', () => {
  assert.deepEqual(computeAreaLineChart({ data: [] }), {
    points: [],
    areaPath: '',
    linePath: '',
    maxVal: 0,
    minVal: 0,
    yTicks: [],
    innerWidth: 0,
    innerHeight: 0,
  });

  assert.deepEqual(computeAreaLineChart({ data: null }), {
    points: [],
    areaPath: '',
    linePath: '',
    maxVal: 0,
    minVal: 0,
    yTicks: [],
    innerWidth: 0,
    innerHeight: 0,
  });
});

test('computes points accurately with custom valueKey and dateKey (PerformanceAnalyticsTab schema)', () => {
  const trendData = [
    { label: '2026-09-15', value: 637 },
    { label: '2026-09-16', value: 371 },
    { label: '2026-09-17', value: 278 },
  ];

  const chart = computeAreaLineChart({
    data: trendData,
    valueKey: 'value',
    dateKey: 'label',
    viewBoxWidth: 800,
    viewBoxHeight: 130,
  });

  assert.equal(chart.points.length, 3);
  assert.equal(chart.points[0].value, 637);
  assert.equal(chart.points[0].label, '2026-09-15');
  assert.equal(chart.points[1].value, 371);
  assert.equal(chart.points[1].label, '2026-09-16');
  assert.equal(chart.points[2].value, 278);
  assert.equal(chart.points[2].label, '2026-09-17');

  // Verify non-zero Y positioning reflects values (higher value -> lower Y in SVG)
  assert.ok(chart.points[0].y < chart.points[1].y, 'Higher views should have smaller Y coordinate');
  assert.ok(chart.points[1].y < chart.points[2].y, 'Medium views should have smaller Y than lower views');

  // Verify paths are generated
  assert.ok(chart.linePath.startsWith('M '));
  assert.ok(chart.areaPath.includes(' Z'));
  assert.ok(chart.maxVal >= 637);
});

test('detects schema mismatch: default tokens/date keys yield 0 on value/label data, while explicit keys restore values', () => {
  const trendData = [
    { label: '2026-09-15', value: 637 },
    { label: '2026-09-16', value: 371 },
  ];

  // When keys mismatch (the B14 root cause)
  const mismatched = computeAreaLineChart({
    data: trendData,
    // defaults: valueKey='tokens', dateKey='date'
  });
  assert.equal(mismatched.points[0].value, 0, 'Mismatched keys fall back to 0 value');
  assert.equal(mismatched.points[0].label, '', 'Mismatched keys fall back to empty label');

  // When keys are correctly specified
  const matched = computeAreaLineChart({
    data: trendData,
    valueKey: 'value',
    dateKey: 'label',
  });
  assert.equal(matched.points[0].value, 637);
  assert.equal(matched.points[0].label, '2026-09-15');
});

test('handles single point correctly without division by zero', () => {
  const single = [{ date: '2026-09-15', tokens: 1500 }];
  const chart = computeAreaLineChart({
    data: single,
    valueKey: 'tokens',
    dateKey: 'date',
  });

  assert.equal(chart.points.length, 1);
  assert.equal(chart.points[0].value, 1500);
  assert.ok(chart.linePath.startsWith('M '));
  assert.ok(chart.areaPath.endsWith(' Z'));
});

test('findClosestChartPoint correctly tracks nearest point by svgX', () => {
  const points = [
    { x: 42, index: 0 },
    { x: 411, index: 1 },
    { x: 780, index: 2 },
  ];

  assert.equal(findClosestChartPoint(points, 50)?.index, 0);
  assert.equal(findClosestChartPoint(points, 400)?.index, 1);
  assert.equal(findClosestChartPoint(points, 750)?.index, 2);
  assert.equal(findClosestChartPoint([], 100), null);
});

test('sortChronological correctly sorts posts monotonic ascending by posted_at', () => {
  const disordered = [
    { posted_at: '2026-09-17T19:00:00', views: 700 },
    { posted_at: '2026-08-05T12:00:00', views: 600 },
    { posted_at: '2026-09-15T10:00:00', views: 800 },
    { posted_at: '2026-09-08T09:00:00', views: 250 },
  ];

  const sorted = sortChronological(disordered, 'posted_at');
  assert.equal(sorted[0].posted_at, '2026-08-05T12:00:00');
  assert.equal(sorted[1].posted_at, '2026-09-08T09:00:00');
  assert.equal(sorted[2].posted_at, '2026-09-15T10:00:00');
  assert.equal(sorted[3].posted_at, '2026-09-17T19:00:00');
});

test('aggregateDailyTrends groups multiple clips on same day and sums views', () => {
  const clips = [
    { posted_at: '2026-09-15T10:00:00', views: 500, likes: 20 },
    { posted_at: '2026-09-15T19:00:00', views: 300, likes: 10 },
    { posted_at: '2026-09-16T12:00:00', views: 250, likes: 5 },
  ];

  const daily = aggregateDailyTrends(clips, {
    dateKey: 'posted_at',
    valueKey: 'views',
    metricsKeys: ['likes'],
  });

  assert.equal(daily.length, 2);
  assert.equal(daily[0].date, '2026-09-15');
  assert.equal(daily[0].value, 800);
  assert.equal(daily[0].count, 2);
  assert.equal(daily[0].metrics.likes, 30);
  assert.equal(daily[1].date, '2026-09-16');
  assert.equal(daily[1].value, 250);
  assert.equal(daily[1].count, 1);
});

test('computeXAxisTicks avoids duplicate identical adjacent tick labels', () => {
  const points = [
    { index: 0, label: '2026-09-15' },
    { index: 1, label: '2026-09-15' },
    { index: 2, label: '2026-09-15' },
    { index: 3, label: '2026-09-16' },
  ];

  const ticks = computeXAxisTicks(points, { maxTicks: 4, dateKey: 'label' });
  // Should only pick distinct dates and not repeat '09-15' consecutively
  assert.ok(ticks.includes(0));
  assert.ok(ticks.includes(3));
  assert.ok(ticks.length < points.length);
});

