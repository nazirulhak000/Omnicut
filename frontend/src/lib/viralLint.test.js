import test from 'node:test';
import assert from 'node:assert/strict';
import {
  analyzeRenderPreflight, mergeViralLint, normalizeViralLintReport, preflightBlockingMessage, viralLintHeatmapSpans,
} from './renderPreflight.js';
import { footageCoverageSummary } from './footageCoverageSummary.js';

const clip = (extra = {}) => ({ id: 'a', source_path: 'synthetic.mp4', trim_start: 0, trim_end: 2, ...extra });

const viralPayload = () => ({
  score: 61.4,
  summary: { block: 1, warn: 2, info: 1 },
  issues: [
    { code: 'LONG_SHOT', severity: 'warn', start: 3.2, end: 7.2, message_th: 'ช็อตยาว', clip_index: 2, detail: null },
    { code: 'COMPLIANCE', severity: 'block', start: 12.2, end: 16, message_th: 'ห้ามพูดราคา', clip_index: null, detail: 'NO_PRICE' },
    { code: 'STRUCTURE', severity: 'warn', start: null, end: null, message_th: 'ไม่มี open loop', clip_index: null, detail: 'STRUCT_NO_OPEN_LOOP' },
    { code: 'HOLD', severity: 'info', start: 1, end: 3, message_th: 'ค้างภาพตามที่อนุญาต', clip_index: 0, detail: 'source_window_exhausted' },
  ],
});

test('normalizeViralLintReport keeps valid issues, derives counts and rounds the score', () => {
  const report = normalizeViralLintReport(viralPayload());
  assert.deepEqual(report.summary, { block: 1, warn: 2, info: 1 });
  assert.equal(report.score, 61);
  assert.equal(report.issues[0].message, 'ช็อตยาว');
  assert.equal(report.issues[0].clipIndex, 2);
  assert.equal(report.issues[2].start, null);
});

test('normalizeViralLintReport rejects malformed payloads and drops bad rows', () => {
  assert.equal(normalizeViralLintReport(null), null);
  assert.equal(normalizeViralLintReport({ issues: 'x' }), null);
  const report = normalizeViralLintReport({ score: 400, issues: [
    { code: 'A', severity: 'fatal', message_th: 'x' }, null, { code: 'B', severity: 'warn' },
    { code: 'C', severity: 'warn', start: 5, end: 2, message_th: 'ok' }] });
  assert.equal(report.issues.length, 1);
  assert.equal(report.issues[0].end, 5);
  assert.equal(report.score, 100);
});

test('compliance block stops render; warnings and info never do', () => {
  const clips = [clip(), clip({ id: 'b' })];
  const base = analyzeRenderPreflight({ clips });
  const merged = mergeViralLint(base, normalizeViralLintReport(viralPayload()), clips);
  assert.equal(merged.canRender, false);
  assert.deepEqual(merged.errors.map((i) => i.code), ['viral_compliance']);
  assert.equal(merged.warnings.length, 2);
  assert.equal(merged.infos.length, 1);
  assert.equal(merged.viralScore, 61);
  assert.match(preflightBlockingMessage(merged), /ห้ามพูดราคา/);

  const advisory = mergeViralLint(base, normalizeViralLintReport({ ...viralPayload(),
    issues: viralPayload().issues.filter((i) => i.severity !== 'block') }), clips);
  assert.equal(advisory.canRender, true);
  assert.equal(advisory.errors.length, 0);
});

test('merge keeps structural errors blocking and sorts by time, untimed last', () => {
  const base = analyzeRenderPreflight({ clips: [clip({ source_path: '' })] });
  const merged = mergeViralLint(base, normalizeViralLintReport(viralPayload()));
  assert.equal(merged.canRender, false);
  const starts = merged.issues.map((i) => i.start);
  assert.deepEqual(starts, [...starts].sort((a, b) => (a ?? Infinity) - (b ?? Infinity)));
  assert.equal(merged.issues.at(-1).start, null);
});

test('a lint HOLD already reported as footage_hold is not listed twice', () => {
  const clips = [clip({ id: 'a', trim_end: 4, freeze_tail: 2, footage_shortage: { reason: 'source_window_exhausted' } })];
  const base = analyzeRenderPreflight({ clips });
  const viral = normalizeViralLintReport({ score: 99, issues: [
    { code: 'HOLD', severity: 'info', start: 0, end: 4, message_th: 'ค้างภาพ', clip_index: 0 }] });
  assert.deepEqual(mergeViralLint(base, viral, clips).issues.map((i) => i.code), ['footage_hold']);
});

test('merge without a lint report leaves the structural report untouched', () => {
  const base = analyzeRenderPreflight({ clips: [clip()] });
  assert.deepEqual(mergeViralLint(base, null).issues, base.issues);
  assert.equal(mergeViralLint(base, null).canRender, true);
});

test('heatmap spans: warn and block only, markers for point issues, block drawn last', () => {
  const spans = viralLintHeatmapSpans(normalizeViralLintReport({ score: 50, issues: [
    { code: 'COMPLIANCE', severity: 'block', start: 2, end: 4, message_th: 'b' },
    { code: 'DEAD_AIR', severity: 'warn', start: 1, end: 3, message_th: 'w' },
    { code: 'HOOK_SLOW', severity: 'warn', start: 0, end: 0, message_th: 'p' },
    { code: 'HOLD', severity: 'info', start: 5, end: 6, message_th: 'i' },
    { code: 'STRUCTURE', severity: 'warn', start: null, end: null, message_th: 'untimed' }] }));
  assert.deepEqual(spans.map((s) => s.code), ['HOOK_SLOW', 'DEAD_AIR', 'COMPLIANCE']);
  assert.equal(spans[0].end, 0.25);
  assert.deepEqual(viralLintHeatmapSpans(null), []);
});

test('planner holds (hold_reason) count as footage coverage, including a hold-only clip span', () => {
  const clips = [
    { trim_start: 2, trim_end: 4, speed: 1, freeze_tail: 0, hold_reason: 'source_window_exhausted', held_source_time: 3.9 },
    { trim_start: 0, trim_end: 2, speed: 1, freeze_tail: 1.5, hold_reason: 'source_window_exhausted' },
    { trim_start: 0, trim_end: 2, speed: 1 },
  ];
  assert.deepEqual(footageCoverageSummary(clips), { count: 2, seconds: 3.5 });
});
