import test from 'node:test';
import assert from 'node:assert/strict';
import { OVERLAY_ANIM, overlayAnimState, overlayAnimTiming } from './stickerAnimation.js';

test('entrance is 7 frames, exit 6 frames, both capped at 40% of the window', () => {
  assert.deepEqual(overlayAnimTiming(1, 4), { inSec: 7 / 30, outSec: 6 / 30 });
  // 0.4 s visible -> floor(0.4 * 0.4 * 30) = 4 frames each
  assert.deepEqual(overlayAnimTiming(0.5, 0.9), { inSec: 4 / 30, outSec: 4 / 30 });
  // no end (or the Canvas 999999 sentinel) -> no exit fade
  assert.deepEqual(overlayAnimTiming(0.5, null), { inSec: 7 / 30, outSec: 0 });
  assert.deepEqual(overlayAnimTiming(0, 999999), { inSec: 7 / 30, outSec: 0 });
  assert.deepEqual(overlayAnimTiming(2, 2), { inSec: 0, outSec: 0 });
});

test('resting frame is untouched; entrance starts transparent and smaller', () => {
  assert.deepEqual(overlayAnimState(2, 1, 4), { alpha: 1, scale: 1 });
  const first = overlayAnimState(1, 1, 4);
  assert.equal(first.alpha, 0);
  assert.equal(first.scale, OVERLAY_ANIM.SCALE_FROM);
  const mid = overlayAnimState(1 + 7 / 60, 1, 4);
  assert.ok(Math.abs(mid.alpha - 0.5) < 1e-12);
  assert.ok(Math.abs(mid.scale - (0.88 + 0.12 * 0.75)) < 1e-12); // ease_out(0.5) = 0.75
  assert.equal(overlayAnimState(4, 1, 4).alpha, 0);
  assert.ok(Math.abs(overlayAnimState(3.9, 1, 4).alpha - 0.5) < 1e-9);
  assert.equal(overlayAnimState(1.1, 1, 4, { scaleIn: false }).scale, 1);
});
