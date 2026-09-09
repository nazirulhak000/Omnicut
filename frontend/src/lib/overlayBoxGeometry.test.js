import test from 'node:test';
import assert from 'node:assert/strict';
import {
  projectOverlayScale,
  positionPatchForBox,
  resolveSelectedBox,
  roundNormalizedPoint,
  scalePatchForBox,
  snapNormalizedPoint,
} from './overlayBoxGeometry.js';

const geometryArgs = {
  bounds: [],
  cues: [],
  captionStyle: { captionPosition: 'bottom' },
  overlays: [],
  effectiveStickersList: [],
  stickerStyle: {},
  isStickerHidden: false,
  effects: [],
  stickerImages: new Map(),
  canvasWidth: 540,
  canvasHeight: 960,
  captionY: { bottom: 0.85 },
  textPositions: { middle: 0.5 },
  resolveLook: (look) => ({ size_pct: 100, ...(look || {}) }),
  anchorTop: 'top',
};

test('selected-box resolver preserves type-specific fallback geometry', () => {
  const caption = resolveSelectedBox({
    ...geometryArgs,
    selection: { type: 'caption', id: 'cue-1' },
    cues: [{ _uid: 'cue-1', text: 'hello', scale: 1.2 }],
  });
  assert.equal(caption.type, 'caption');
  assert.equal(caption.normY, 0.85);
  assert.equal(caption.w, 120);

  const overlay = resolveSelectedBox({
    ...geometryArgs,
    selection: { type: 'hook', id: 'hook-1' },
    overlays: [{ id: 'hook-1', kind: 'hook', tiers: [{ text: 'Hook' }], anchor: 'top' }],
  });
  assert.equal(overlay.y, 480);
  assert.equal(overlay.sizePct, 100);

  const effect = resolveSelectedBox({
    ...geometryArgs,
    selection: { type: 'effect', id: 'effect-1' },
    effects: [{ id: 'effect-1', scale: 2, normX: 0.6, normY: 0.4, effectId: 'glow' }],
  });
  assert.deepEqual(
    { x: effect.x, y: effect.y, w: effect.w, h: effect.h },
    { x: 144, y: 204, w: 360, h: 360 },
  );
});

test('selected-box resolver prefers measured bounds and keeps hidden sticker behavior', () => {
  const measured = { type: 'sticker', id: 's1', x: 1, y: 2, w: 3, h: 4 };
  assert.equal(resolveSelectedBox({ ...geometryArgs, selection: measured, bounds: [measured] }), measured);
  assert.equal(resolveSelectedBox({
    ...geometryArgs,
    selection: { type: 'sticker', id: 's1' },
    isStickerHidden: true,
    effectiveStickersList: [{ id: 's1', badge: 'x.png' }],
  }), null);
});

test('normalized point snapping retains move guides and caption pointer-up guide policy', () => {
  assert.deepEqual(snapNormalizedPoint(0.49, 0.215), {
    x: 0.5, y: 0.2, snapX: 0.5, snapY: 0.2,
  });
  assert.deepEqual(snapNormalizedPoint(0.49, 0.215, { yGuides: [0.5] }), {
    x: 0.5, y: 0.215, snapX: 0.5, snapY: null,
  });
  assert.deepEqual(roundNormalizedPoint(0.12356, 0.98765), { x: 0.124, y: 0.988 });
});

test('resize projection preserves type-specific scale limits and rounding', () => {
  assert.equal(projectOverlayScale(1, -100, 100, 'caption'), 0.4);
  assert.equal(projectOverlayScale(1, 300, 100, 'sticker'), 3.5);
  assert.equal(projectOverlayScale(1, 12, 100, 'effect'), 1.12);
  assert.equal(projectOverlayScale(1, 12, 100, 'text_overlay'), 1.12);
});

test('commit adapters preserve type-specific position and scale fields', () => {
  assert.deepEqual(positionPatchForBox('caption', 0.4, 0.6), { x: 0.4, y: 0.6 });
  assert.deepEqual(positionPatchForBox('sticker', 0.4, 0.6), { normX: 0.4, normY: 0.6 });
  assert.deepEqual(positionPatchForBox('effect', 0.4, 0.6), { normX: 0.4, normY: 0.6 });
  assert.deepEqual(scalePatchForBox('hook', 1.23, { color: '#fff' }), {
    look: { color: '#fff', size_pct: 123 },
  });
  assert.deepEqual(scalePatchForBox('sticker', 1.23), { scale: 1.23 });
});
