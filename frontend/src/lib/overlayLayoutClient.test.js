import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getLayoutCacheKey,
  getCachedOverlayLayout,
  requestOverlayLayout,
  clearOverlayLayoutCache,
} from './overlayLayoutClient.js';

test('getLayoutCacheKey produces predictable deterministic keys', () => {
  const key1 = getLayoutCacheKey({
    text: 'โปรโมชั่นพิเศษ',
    fontName: 'Kanit',
    fontSizePx: 75,
    normX: 0.5,
    normY: 0.2,
  });
  const key2 = getLayoutCacheKey({
    text: 'โปรโมชั่นพิเศษ',
    fontName: 'Kanit',
    fontSizePx: 75,
    normX: 0.5,
    normY: 0.2,
  });
  assert.equal(key1, key2);
  assert.ok(key1.includes('โปรโมชั่นพิเศษ'));
});

test('getCachedOverlayLayout returns null when empty and returns cached layout once resolved', async () => {
  clearOverlayLayoutCache();
  const params = {
    text: 'ดีลเด็ด',
    fontName: 'Kanit',
    fontSizePx: 75,
    normX: 0.5,
    normY: 0.5,
  };

  assert.equal(getCachedOverlayLayout(params), null);
});
