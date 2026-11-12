import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { isTiktokSharp } from './tiktokSharp.js';

test('isTiktokSharp is true for a clip the backend sharpened in place after the render', () => {
  assert.equal(isTiktokSharp({ name: '20261112_fan_hook_v1.mp4', tiktok_enhanced: true }), true);
});

test('isTiktokSharp is true for the copy the manual button writes', () => {
  assert.equal(isTiktokSharp({ name: '20261112_fan_hook_v1_tiktok_sharp.mp4' }), true);
  assert.equal(isTiktokSharp({ rel_path: '04_Exports/main/20261112_fan_hook_v1_tiktok_sharp.mp4' }), true);
});

test('isTiktokSharp is false for a plain render, a stale flag value and a missing item', () => {
  assert.equal(isTiktokSharp({ name: '20261112_fan_hook_v1.mp4', tiktok_enhanced: false }), false);
  assert.equal(isTiktokSharp({ name: '20261112_fan_hook_v1.mp4' }), false);
  assert.equal(isTiktokSharp({ name: 'clip.mp4', tiktok_enhanced: 'true' }), false);
  assert.equal(isTiktokSharp(null), false);
});

test('ExportGallery reads the sharpness state through isTiktokSharp, never from the file name alone', () => {
  const source = readFileSync(
    fileURLToPath(new URL('../components/ExportGallery.jsx', import.meta.url)), 'utf8');
  assert.ok(source.includes("from '../lib/tiktokSharp.js'"));
  assert.ok(!source.includes("includes('_tiktok_sharp')"));
  // badge on the card + disabled, style and label of the manual button
  assert.ok(source.match(/isTiktokSharp\(/g).length >= 2);
});
