import test from 'node:test';
import assert from 'node:assert/strict';

import {
  BUS_VOLUME_MAX,
  BUS_VOLUME_MIN,
  busVolumesFromManifest,
  clampBusVolume,
  SFX_VOLUME_DEFAULT,
  VOICE_VOLUME_DEFAULT,
} from './audioBusLevels.js';
import { manifestToEditorState, serializeStyle } from './editorProjectState.js';

test('defaults match the render config (Voice 1.0 / SFX 0.28) and the [0, 1] ceiling', () => {
  assert.equal(VOICE_VOLUME_DEFAULT, 1.0);
  assert.equal(SFX_VOLUME_DEFAULT, 0.28);
  assert.equal(BUS_VOLUME_MIN, 0);
  assert.equal(BUS_VOLUME_MAX, 1);
});

test('clampBusVolume clamps, rounds and falls back on unusable input', () => {
  assert.equal(clampBusVolume(0.5, 1), 0.5);
  assert.equal(clampBusVolume('0.35', 1), 0.35);
  assert.equal(clampBusVolume(1.8, 0.28), 1);
  assert.equal(clampBusVolume(-0.2, 0.28), 0);
  assert.equal(clampBusVolume(0, 0.28), 0);
  assert.equal(clampBusVolume(0.123456, 1), 0.123);
  for (const bad of [undefined, null, '', 'abc', NaN, Infinity, -Infinity, true, false]) {
    assert.equal(clampBusVolume(bad, 0.28), 0.28, `input ${String(bad)}`);
  }
});

test('an old manifest without the fields loads the defaults', () => {
  assert.deepEqual(busVolumesFromManifest({}), { voiceVolume: 1, sfxVolume: 0.28 });
  assert.deepEqual(busVolumesFromManifest(null, null), { voiceVolume: 1, sfxVolume: 0.28 });
  const state = manifestToEditorState({ cues: [], clip_list: [] });
  assert.equal(state.style.voiceVolume, 1);
  assert.equal(state.style.sfxVolume, 0.28);
});

test('stored levels load from top level, render_params, or saved style, clamped', () => {
  assert.deepEqual(
    busVolumesFromManifest({ voice_volume: 0.6, render_params: { sfx_volume: 0.5 } }),
    { voiceVolume: 0.6, sfxVolume: 0.5 },
  );
  assert.deepEqual(
    busVolumesFromManifest({}, { voiceVolume: 3, sfxVolume: -1 }),
    { voiceVolume: 1, sfxVolume: 0 },
  );
});

test('serializeStyle writes clamped voice_volume/sfx_volume for the mix stage', () => {
  const defaults = serializeStyle({});
  assert.equal(defaults.voice_volume, 1);
  assert.equal(defaults.sfx_volume, 0.28);
  const set = serializeStyle({ voiceVolume: 0.7, sfxVolume: 5 });
  assert.equal(set.voice_volume, 0.7);
  assert.equal(set.sfx_volume, 1);
});
