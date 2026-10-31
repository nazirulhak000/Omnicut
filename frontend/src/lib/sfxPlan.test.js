import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { planSfxEvents, isSfxEventEligible, SFX_MIN_GAP_S } from './sfxPlan.js';

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
