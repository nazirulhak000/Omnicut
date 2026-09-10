import test from 'node:test';
import assert from 'node:assert/strict';

import {
  drawMediaWithAccentRecolor,
  getOverlayHueRotation,
  getOverlayRecolorMetadata,
} from './overlayRecolor.js';

test('only decorative baked assets opt into accent recolouring', () => {
  assert.deepEqual(getOverlayRecolorMetadata('sticker', 'arrow_pointer_cyan_3d.png'), {
    recolorable: true,
    recolor_source_hue: 180,
  });
  assert.deepEqual(getOverlayRecolorMetadata('sticker', 'badge_pros_review.png'), { recolorable: false });
  assert.deepEqual(getOverlayRecolorMetadata('effect', 'fx_arrow_01.webm'), {
    recolorable: true,
    recolor_source_hue: 205,
  });
});

test('accent rotation mirrors the bounded shortest hue delta used by FFmpeg', () => {
  assert.ok(Math.abs(getOverlayHueRotation({ recolor: 'accent', recolorSourceHue: 180 }, '#FFE600') + 125.8823529) < 1e-6);
  assert.ok(Math.abs(getOverlayHueRotation({ recolor: 'accent', recolorSourceHue: 52 }, '#FFE600', 'sticker', 'arrow_pointer_yellow_3d') - 2.1176471) < 1e-6);
  assert.equal(getOverlayHueRotation({ recolor: 'accent' }, '#FFE600', 'sticker', 'badge_pros_review'), null);
  assert.equal(getOverlayHueRotation({}, '#FFE600'), null);
});

test('Canvas helper leaves non-recoloured media path untouched and restores state', () => {
  const calls = [];
  const ctx = {
    filter: 'none',
    save: () => calls.push('save'),
    drawImage: (...args) => calls.push(args),
    restore: () => calls.push('restore'),
  };
  drawMediaWithAccentRecolor(ctx, 'media', 1, 2, 3, 4, {}, '#FFE600', 'sticker', 'badge_pros_review');
  assert.deepEqual(calls, ['save', ['media', 1, 2, 3, 4], 'restore']);
  assert.equal(ctx.filter, 'none');
});
