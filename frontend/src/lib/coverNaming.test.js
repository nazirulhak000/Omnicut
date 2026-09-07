import test from 'node:test';
import assert from 'node:assert/strict';

import { resolveCoverExportStem } from './coverNaming.js';

test('prefers the canonical project name for cover output', () => {
  assert.equal(
    resolveCoverExportStem({
      project_name: 'LOG01-แกะกล่องว้าว_1',
      name: 'logitech_wave_keys_แกะกล่องว้าว_1.mp4',
    }),
    'LOG01-แกะกล่องว้าว_1',
  );
});

test('falls back to a video stem for legacy items without project metadata', () => {
  assert.equal(
    resolveCoverExportStem({ path: '04_Exports/Ready_to_post/clip_20260907.mp4' }),
    'clip_20260907',
  );
});

test('returns null when no usable identity exists', () => {
  assert.equal(resolveCoverExportStem({}), null);
});
