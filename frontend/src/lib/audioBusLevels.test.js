import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TARGET_LUFS_SOCIAL,
  TRUE_PEAK_MAX_DB,
  amplitudeToLufs,
  calculateLoudnessGain,
  clampBusVolume,
} from './audioBusLevels.js';

test('audioBusLevels exports CapCut 7.1 loudness constants', () => {
  assert.equal(TARGET_LUFS_SOCIAL, -14.0);
  assert.equal(TRUE_PEAK_MAX_DB, -1.0);
});

test('amplitudeToLufs calculates K-weighted approximation', () => {
  // 1.0 full scale amplitude: 20*log10(1.0) - 0.691 = -0.691 -> -0.7 LUFS
  assert.equal(amplitudeToLufs(1.0), -0.7);
  // 0.5 amplitude: 20*log10(0.5) - 0.691 = -6.02 - 0.691 = -6.71 -> -6.7 LUFS
  assert.equal(amplitudeToLufs(0.5), -6.7);
});

test('calculateLoudnessGain computes required adjustment towards -14 LUFS', () => {
  // If current is -20 LUFS, target is -14 LUFS -> need +6 dB gain
  const adj = calculateLoudnessGain(-20.0, -14.0);
  assert.equal(adj.gainDb, 6.0);
  assert.ok(adj.linearGain > 1.99 && adj.linearGain < 2.01);
});

test('clampBusVolume maintains bounds', () => {
  assert.equal(clampBusVolume(-0.5, 0.5), 0.0);
  assert.equal(clampBusVolume(1.5, 0.5), 1.0);
  assert.equal(clampBusVolume(0.8, 0.5), 0.8);
});
