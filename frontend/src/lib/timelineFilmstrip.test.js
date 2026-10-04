import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FILMSTRIP_COUNT_BUCKETS,
  createFilmstripCache,
  filmstripKey,
  filmstripRequestCount,
  filmstripSlotCount,
  filmstripTileIndex,
  filmstripTileStyles,
  filmstripUrl,
  filmstripWindow,
} from './timelineFilmstrip.js';

test('slot count follows clip width and is bounded', () => {
  assert.equal(filmstripSlotCount(0), 0);
  assert.equal(filmstripSlotCount(NaN), 0);
  assert.equal(filmstripSlotCount(14), 1);
  assert.equal(filmstripSlotCount(480), 10);
  assert.equal(filmstripSlotCount(1e6), 120);
});

test('request count is bucketed, so small zoom changes reuse one sprite', () => {
  assert.equal(filmstripRequestCount(1), 2);
  assert.equal(filmstripRequestCount(9), 12);
  assert.equal(filmstripRequestCount(10), 12);
  assert.equal(filmstripRequestCount(12), 12);
  assert.equal(filmstripRequestCount(500), 40);
  for (const n of FILMSTRIP_COUNT_BUCKETS) assert.ok(n >= 2 && n <= 40, 'server clamps to 2..40');
});

test('window is the trim range, rounded; whole file omits start/end', () => {
  assert.equal(filmstripWindow({}), null);
  assert.deepEqual(filmstripWindow({ source_path: 'a.mp4', trim_start: 0, trim_end: null }),
    { path: 'a.mp4', start: null, end: null });
  assert.deepEqual(filmstripWindow({ source_path: 'a.mp4', trim_start: 1.234, trim_end: 3.96 }),
    { path: 'a.mp4', start: 1.2, end: 4 });
  // A sub-step trim nudge keeps the same cache key.
  const a = filmstripKey(filmstripWindow({ source_path: 'a.mp4', trim_start: 1.21, trim_end: 4 }));
  const b = filmstripKey(filmstripWindow({ source_path: 'a.mp4', trim_start: 1.23, trim_end: 4.01 }));
  assert.equal(a, b);
  assert.notEqual(a, filmstripKey(filmstripWindow({ source_path: 'b.mp4', trim_start: 1.21, trim_end: 4 })));
  // Never an empty or inverted window.
  const tiny = filmstripWindow({ source_path: 'a.mp4', trim_start: 2.01, trim_end: 2.02 });
  assert.ok(tiny.end > tiny.start);
});

test('url matches the api.js filmstripUrlFor shape', () => {
  assert.equal(filmstripUrl({ path: 'x/a b.mp4', start: null, end: null }, 8),
    '/api/editor/filmstrip?path=x%2Fa+b.mp4&count=8');
  assert.equal(filmstripUrl({ path: 'a.mp4', start: 1.2, end: 4 }, 4),
    '/api/editor/filmstrip?path=a.mp4&count=4&start=1.20&end=4.00');
});

test('tile index spreads slots evenly across a larger sprite', () => {
  assert.deepEqual([0, 1, 2, 3].map((i) => filmstripTileIndex(i, 4, 4)), [0, 1, 2, 3]);
  assert.deepEqual([0, 1].map((i) => filmstripTileIndex(i, 2, 8)), [2, 6]);
  assert.deepEqual([0, 1, 2, 3].map((i) => filmstripTileIndex(i, 4, 2)), [0, 0, 1, 1]);
});

test('tile styles cover-crop each tile into its slot', () => {
  assert.deepEqual(filmstripTileStyles({ slots: 2, count: 2, naturalWidth: 0, naturalHeight: 10, slotWidth: 5, slotHeight: 5 }), []);
  // Two 160x284 portrait tiles into 48x64 slots: width-limited scale 0.3.
  const styles = filmstripTileStyles({
    slots: 2, count: 2, naturalWidth: 320, naturalHeight: 284, slotWidth: 48, slotHeight: 64,
  });
  assert.equal(styles.length, 2);
  assert.equal(styles[0].backgroundSize, '96px 85.2px');
  assert.equal(styles[0].backgroundPosition, '0px -10.6px');
  assert.equal(styles[1].backgroundPosition, '-48px -10.6px');
  // Landscape tiles into the same slots: height-limited, centred horizontally.
  const wide = filmstripTileStyles({
    slots: 1, count: 1, naturalWidth: 160, naturalHeight: 90, slotWidth: 48, slotHeight: 64,
  });
  const [w, h] = wide[0].backgroundSize.split(' ').map(parseFloat);
  assert.ok(Math.abs(h - 64) < 0.01 && w > 48);
  assert.ok(parseFloat(wide[0].backgroundPosition) < 0);
});

test('cache keeps the richest sprite per window and remembers failures', () => {
  const cache = createFilmstripCache();
  assert.equal(cache.needs('k', 4), true);
  cache.store('k', { url: 'u8', count: 8, naturalWidth: 1, naturalHeight: 1 });
  assert.equal(cache.needs('k', 4), false, 'a bigger sprite serves a smaller request');
  assert.equal(cache.needs('k', 12), true);
  cache.store('k', { url: 'u4', count: 4, naturalWidth: 1, naturalHeight: 1 });
  assert.equal(cache.best('k').url, 'u8');
  cache.fail('u12');
  assert.equal(cache.hasFailed('u12'), true);
  assert.equal(cache.hasFailed('u8'), false);
});
