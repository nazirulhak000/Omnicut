import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LEGACY_MOTION_IDS,
  MOTION_PHASES,
  resolveLegacyMotionId,
  sampleMotionContract,
} from './motionContract.js';
import { getMotionPreset, MOTION_PRESETS } from './motionPresets.js';
import { getMotionUiModel, getMotionUiPresets } from './motionUiModel.js';
import { sampleCanvasMotion } from './rendererAdapter.js';

const EXPECTED_PRESET_IDS = new Set([
  'hook.in.blur', 'hook.in.bounce', 'hook.in.bounce_soft', 'hook.in.elastic_bounce',
  'hook.in.fade', 'hook.in.none', 'hook.in.pop', 'hook.in.pop_soft', 'hook.in.pop_zoom',
  'hook.in.quick_fade', 'hook.in.slam', 'hook.in.slide_up', 'hook.in.snap', 'hook.in.stamp',
  'hook.in.typewriter', 'hook.in.zoom', 'hook.in.rise', 'hook.loop.flicker', 'hook.loop.lightsweep',
  'hook.loop.none', 'hook.loop.pulse', 'hook.loop.shake', 'hook.loop.wave', 'hook.out.fade',
  'hook.out.glitch', 'hook.out.none', 'hook.out.slide', 'hook.out.zoom', 'text.in.none',
  'text.in.pop_zoom', 'text.in.quick_fade', 'text.in.rise', 'text.in.snap', 'text.in.stamp',
]);

const TEXT_LEGACY_MAP = Object.freeze({
  pop: 'snap', zoom: 'pop_zoom', stamp: 'stamp', fade: 'quick_fade', slide: 'rise', none: 'none',
});

function assertFiniteTree(value) {
  if (typeof value === 'number') {
    assert.equal(Number.isFinite(value), true);
  } else if (Array.isArray(value)) {
    value.forEach(assertFiniteTree);
  } else if (value && typeof value === 'object') {
    Object.values(value).forEach(assertFiniteTree);
  }
}

test('the frontend catalog is exactly the shared 34-preset parity surface', () => {
  assert.equal(Object.keys(MOTION_PRESETS).length, 34);
  assert.deepEqual(new Set(Object.keys(MOTION_PRESETS)), EXPECTED_PRESET_IDS);
});

test('all 34 presets sample at shared normalized frame times without invalid state', () => {
  for (const preset of Object.values(MOTION_PRESETS)) {
    for (const normalizedTime of [0, 0.25, 0.5, 0.75, 1]) {
      const sampled = sampleMotionContract(preset, normalizedTime);
      assertFiniteTree(sampled);
    }
  }
});

test('phase order is explicit and the UI maps loop to hold', () => {
  assert.deepEqual(MOTION_PHASES, ['in', 'loop', 'out']);
  const model = getMotionUiModel({ role: 'hook' });
  assert.deepEqual(model.phaseOrder, ['in', 'hold', 'out']);
  assert.deepEqual(model.contractPhaseOrder, ['in', 'loop', 'out']);
  assert.deepEqual(model.groups.map((group) => group.id), ['in', 'hold', 'out']);
});

test('legacy mapping is exhaustive and remains role-scoped', () => {
  assert.deepEqual(LEGACY_MOTION_IDS.text.in, TEXT_LEGACY_MAP);
  for (const [legacyId, canonicalId] of Object.entries(TEXT_LEGACY_MAP)) {
    assert.equal(resolveLegacyMotionId('text', 'in', legacyId), canonicalId);
  }
  for (const role of ['text', 'hook', 'caption']) {
    for (const phase of ['in', 'loop', 'out']) {
      assert.equal(resolveLegacyMotionId(role, phase, 'unknown_motion_id'), 'unknown_motion_id');
    }
  }
  assert.equal(resolveLegacyMotionId('hook', 'in', 'pop'), 'pop');
});

test('short-duration presets remain sampleable, including the 70/80/100ms cases', () => {
  const short = Object.values(MOTION_PRESETS).filter(({ duration_ms }) => duration_ms >= 70 && duration_ms < 120);
  assert.deepEqual(new Set(short.map((preset) => preset.id)), new Set([
    'hook.in.pop_zoom', 'hook.in.snap', 'hook.in.stamp',
    'text.in.pop_zoom', 'text.in.snap', 'text.in.stamp',
  ]));
  for (const preset of short) {
    for (const normalizedTime of [0, 0.5, 1]) {
      assertFiniteTree(sampleCanvasMotion(preset, normalizedTime).state);
    }
  }
});

test('reduced motion is explicit for every preset and never claims normal motion was applied', () => {
  for (const preset of Object.values(MOTION_PRESETS)) {
    const result = sampleCanvasMotion(preset, 0.5, { reducedMotion: true });
    assert.equal(result.metadata.reducedMotion, true, preset.id);
    assert.equal(result.metadata.reducedMotionApplied, true, preset.id);
    assert.equal(result.metadata.reducedMotionStrategy, 'settle-in-freeze-loop-skip-out', preset.id);
    if (preset.phase === 'in') assert.equal(result.metadata.phaseProgress, 1, preset.id);
    if (preset.phase === 'loop') assert.equal(result.metadata.phaseProgress, 0, preset.id);
    if (preset.phase === 'out') assert.equal(result.metadata.phaseProgress, 0, preset.id);
  }
});

test('UI metadata exposes renderer binding without advertising unsupported controls', () => {
  for (const role of ['hook', 'text', 'caption']) {
    for (const phase of ['in', 'hold', 'out']) {
      for (const preset of getMotionUiPresets(role, phase)) {
        const contract = MOTION_PRESETS[preset.contractId];
        assert.ok(contract, `${role}.${phase}.${preset.id}`);
        assert.equal(preset.rendererBound, contract.metadata.renderer_bound, preset.contractId);
        assert.equal(preset.enabled, contract.metadata.renderer_bound, preset.contractId);
        assert.equal(preset.parityLevel, contract.metadata.parity_level, preset.contractId);
        if (preset.contractId === 'hook.in.typewriter') {
          assert.equal(contract.metadata.renderer_bound, false, preset.contractId);
          assert.deepEqual(contract.metadata.unsupported_tracks, ['reveal']);
        } else {
          assert.equal(contract.metadata.renderer_bound, true, preset.contractId);
          assert.deepEqual(contract.metadata.unsupported_tracks, []);
        }
        assert.equal(preset.capabilities.speed.supported, false, preset.contractId);
        assert.equal(preset.capabilities.intensity.supported, false, preset.contractId);
        assert.equal(preset.repeat, Boolean(contract.repeat), preset.contractId);
        assert.equal(preset.durationMs, contract.duration_ms, preset.contractId);
      }
    }
  }
});

test('UI only exposes catalog-backed phases and presets', () => {
  assert.equal(getMotionPreset('text', 'hold', 'pulse'), null);
  assert.equal(getMotionPreset('caption', 'in', 'snap'), null);
  const hookModel = getMotionUiModel({ role: 'hook' });
  const textModel = getMotionUiModel({ role: 'text' });
  const visibleIds = new Set([
    ...hookModel.groups.flatMap((group) => group.presets.map((preset) => preset.contractId)),
    ...textModel.groups.flatMap((group) => group.presets.map((preset) => preset.contractId)),
  ]);
  assert.deepEqual(visibleIds, EXPECTED_PRESET_IDS);
});
