import test from 'node:test';
import assert from 'node:assert/strict';

import {
  capcutAdjustShadow,
  capcutAdjustHighlight,
  capcutDehazeChannel,
  CAPCUT_HSL_RANGES,
  capcutSplendorVibrance,
  capcutVignetteWeight,
  capcutParticleNoise,
  COLOR_FIELDS,
} from './inspectorModel.js';
import {
  CAPCUT_HIGH_SPEED_TRANSITIONS,
  capcutDampedCameraShake,
  applyCapcutHighSpeedTransition,
} from './timelineMath.js';

test('W3.1: evaluates shadow, highlight, and dark-channel dehaze curves accurately', () => {
  assert.ok(capcutAdjustShadow(0.2, 0.4) < 0.2);
  assert.ok(capcutAdjustShadow(0.2, -0.4) > 0.2);
  assert.ok(capcutAdjustHighlight(0.8, 0.4) > 0.8);
  assert.ok(capcutAdjustHighlight(0.8, -0.4) < 0.8);
  assert.ok(capcutDehazeChannel(0.5, 0.35, 0.85, 0.6) < 0.5);
});

test('W3.2: exposes 8-color HSL ranges and skin-tone protected Splendor Vibrance', () => {
  assert.equal(Object.keys(CAPCUT_HSL_RANGES).length, 8);
  assert.deepEqual(CAPCUT_HSL_RANGES.orange, [-10, 20, 40, 60]);

  const [rSkin] = capcutSplendorVibrance(0.85, 0.55, 0.45, 0.45);
  const [, , bSky] = capcutSplendorVibrance(0.2, 0.55, 0.85, 0.45);
  assert.ok(rSkin > 0.85);
  assert.ok(bSky > 0.85);
});

test('W3.3: evaluates radial vignette falloff and particle shader noise deterministically', () => {
  assert.ok(Math.abs(capcutVignetteWeight(0.5, 0.5, 0.7)) < 1e-5);
  assert.ok(capcutVignetteWeight(0.02, 0.02, 0.7) > 0.0);

  const n = capcutParticleNoise(1.25, 3.75);
  assert.ok(Math.abs(n) <= 0.08);
});

test('W3.1-W3.3: wires Shadows, Highlights, Vibrance, and Vignette into COLOR_FIELDS', () => {
  const keys = COLOR_FIELDS.map((f) => f.key);
  assert.ok(keys.includes('shadows'));
  assert.ok(keys.includes('highlights'));
  assert.ok(keys.includes('vibrance'));
  assert.ok(keys.includes('vignette'));
});

test('W3.4: provides 4 CapCut 7.1 high-speed transition presets and damped camera shake', () => {
  assert.deepEqual(
    CAPCUT_HIGH_SPEED_TRANSITIONS.map((p) => p.id),
    ['whip_pan', 'zoom_in_punch', 'flash_white', 'glitch_shake']
  );
  const zeroAtEnd = capcutDampedCameraShake(1.5);
  assert.equal(zeroAtEnd.dx, 0);
  assert.equal(zeroAtEnd.dy, 0);

  const midShake = capcutDampedCameraShake(0.05);
  assert.ok(Math.abs(midShake.dx) + Math.abs(midShake.dy) > 0);

  const updated = applyCapcutHighSpeedTransition({ id: 'clip_1', duration: 3.0 }, 'whip_pan');
  assert.equal(updated.capcut_transition_preset, 'whip_pan');
  assert.equal(updated.transition_in, 'slideleft');
  assert.ok(Math.abs(updated.transition_duration - 0.25) < 1e-5);
});
