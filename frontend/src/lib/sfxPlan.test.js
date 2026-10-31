import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { planSfxEvents, isSfxEventEligible, SFX_MIN_GAP_S } from './sfxPlan.js';
import { buildSegments, clipCutTimes } from './timelineMath.js';

// Shared with tests/test_preview_render_parity.py, which runs the same cases
// through plan_sfx_events() in scripts/sfx_manager.py.
const CASES = JSON.parse(
  readFileSync(new URL('../../../tests/fixtures/sfx_highlight_parity_cases.json', import.meta.url), 'utf-8'),
);

const r6 = (v) => Math.round(v * 1e6) / 1e6;

function runCase(c) {
  const o = c.options || {};
  const missing = new Set(o.missing || []);
  return planSfxEvents(c.cues, c.overlays, {
    totalDuration: o.total_duration ?? null,
    boomAvailable: o.boom_available ?? true,
    cutTimes: o.cut_times ?? null,
    sfxFilename: (tag) => (missing.has(tag) ? null : `sfx_${tag}.wav`),
  }).map((e) => ({
    source: e.source, index: e.index, start: r6(e.start), fire: r6(e.fire), role: e.role, exempt: e.exempt,
  }));
}

for (const c of CASES.sfx) {
  test(`sfx plan parity: ${c.name}`, () => {
    assert.deepEqual(runCase(c), c.expected);
  });
}

test('the density gap is the backend constant', () => {
  assert.equal(SFX_MIN_GAP_S, 2.0);
});

test('no hits at all still lays down the boom, and nothing without a boom file', () => {
  assert.deepEqual(planSfxEvents([], []).map((e) => e.source), ['boom']);
  assert.deepEqual(planSfxEvents([], [], { boomAvailable: false }), []);
});

test('eligibility follows the backend: explicit opt-out flags and non-objects are skipped', () => {
  assert.equal(isSfxEventEligible({ start: 1, sfx: 'pop', enabled: false }), false);
  assert.equal(isSfxEventEligible({ start: 1, sfx: 'pop', sfx_event: false }), false);
  assert.equal(isSfxEventEligible(['pop']), false);
  assert.equal(isSfxEventEligible({ start: '1.5', sfx: 'pop' }), true);
  assert.equal(isSfxEventEligible({ start: null, sfx: 'pop' }), false);
});

// clip_cut_times() in scripts/pipeline_context.py is the backend side of this
// fixture. Clips without trim_end are given their source duration the way the
// editor loads it from the probed file.
for (const c of CASES.cut_times) {
  test(`cut times parity: ${c.name}`, () => {
    const durations = Object.fromEntries(c.clips.map((clip) => [clip.id, clip.duration || 0]));
    const got = clipCutTimes(buildSegments(c.clips, durations));
    assert.equal(got.length, c.expected.length);
    got.forEach((t, i) => assert.ok(Math.abs(t - c.expected[i]) < 1e-6, `${t} vs ${c.expected[i]}`));
  });
}
