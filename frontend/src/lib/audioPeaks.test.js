import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AUDIO_PEAK_LOD,
  getLODBucketCount,
  getAudioPeaksForZoom,
} from './audioPeaks.js';

test('AUDIO_PEAK_LOD defines standard CapCut 7.1 pyramid levels', () => {
  assert.equal(AUDIO_PEAK_LOD.LOD1X, 600);
  assert.equal(AUDIO_PEAK_LOD.LOD4X, 2400);
  assert.equal(AUDIO_PEAK_LOD.LOD16X, 9600);
});

test('getLODBucketCount selects correct pyramid level for timeline zoom', () => {
  // Low zoom (<= 40 px/s): LOD 1x (600 buckets)
  assert.equal(getLODBucketCount(20), 600);
  assert.equal(getLODBucketCount(40), 600);

  // Medium zoom (41 - 150 px/s): LOD 4x (2400 buckets)
  assert.equal(getLODBucketCount(50), 2400);
  assert.equal(getLODBucketCount(120), 2400);
  assert.equal(getLODBucketCount(150), 2400);

  // High zoom (> 150 px/s): LOD 16x (9600 buckets)
  assert.equal(getLODBucketCount(200), 9600);
  assert.equal(getLODBucketCount(500), 9600);
});

test('getAudioPeaksForZoom returns null cleanly on missing or empty url', async () => {
  const resNull = await getAudioPeaksForZoom(null, 50);
  assert.equal(resNull, null);
  const resEmpty = await getAudioPeaksForZoom('', 50);
  assert.equal(resEmpty, null);
});
