import test from 'node:test';
import assert from 'node:assert/strict';
import { effectiveAudioMutes } from './trackMix.js';

test('mute survives export without changing the other audio buses', () => {
  assert.deepEqual(effectiveAudioMutes({ mute: { bgm: true }, solo: {} }), { bgm: true });
});

test('solo exports only the selected stems, including clip original audio', () => {
  assert.deepEqual(
    effectiveAudioMutes({ mute: { voice: true }, solo: { bgm: true, clip: true } }),
    { voice: true, sfx: true },
  );
  assert.deepEqual(effectiveAudioMutes({ solo: { voice: true } }), {
    bgm: true, sfx: true, clip: true,
  });
});

test('a cleared solo restores the explicit mute state', () => {
  assert.deepEqual(effectiveAudioMutes({ mute: { bgm: true }, solo: { voice: false } }), {
    bgm: true,
  });
});
