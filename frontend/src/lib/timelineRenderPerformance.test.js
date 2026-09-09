import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const timelineSource = readFileSync(
  new URL('../components/editor/Timeline.jsx', import.meta.url),
  'utf8',
);

test('timeline memoizes repeated segment collections before mapping lanes', () => {
  assert.match(timelineSource, /const transitionSegments = useMemo\(\(\) => segments\.slice\(1\), \[segments\]\);/);
  assert.match(timelineSource, /const clipAudioSegments = useMemo\(/);
  assert.match(timelineSource, /transitionSegments\.map\(\(seg\) =>/);
  assert.match(timelineSource, /clipAudioSegments\.map\(\(s\) =>/);
  assert.doesNotMatch(timelineSource, /segments\.slice\(1\)\.map\(/);
  assert.doesNotMatch(timelineSource, /segments\.filter\(\(s\) => Number\(s\.clip\.volume\) > 0\)\.map\(/);
});

test('timeline indexes sticker assets while preserving name-first and first-match lookup', () => {
  assert.match(timelineSource, /const stickerAssetIndex = useMemo\(\(\) =>/);
  assert.match(timelineSource, /const byName = new Map\(\);/);
  assert.match(timelineSource, /const byPath = new Map\(\);/);
  assert.match(timelineSource, /!byName\.has\(asset\.name\)/);
  assert.match(timelineSource, /!byPath\.has\(asset\.path\)/);
  assert.match(timelineSource, /stickerAssetIndex\.byName\.get\(item\.badge\)/);
  assert.match(timelineSource, /stickerAssetIndex\.byPath\.get\(item\.badge\)/);
  assert.doesNotMatch(timelineSource, /\(stickerAssets \|\| \[\]\)\.find\(/);
});
