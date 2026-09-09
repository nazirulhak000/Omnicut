import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_STYLE_PRESET,
  STYLE_PRESET_CATALOG,
  getStylePreset,
  normalizeStylePreset,
  stylePresetFromManifest,
  uniqueStylePresets,
  withStylePresetPayload,
} from './stylePresetCatalog.js';

test('catalog has a unique renderer-supported default', () => {
  assert.ok(STYLE_PRESET_CATALOG.length > 0);
  assert.equal(normalizeStylePreset(DEFAULT_STYLE_PRESET), DEFAULT_STYLE_PRESET);
  assert.equal(new Set(STYLE_PRESET_CATALOG.map((preset) => preset.id)).size, STYLE_PRESET_CATALOG.length);
});

test('unknown and legacy casing safely resolve to the Golden Master', () => {
  assert.equal(normalizeStylePreset(' CLEAN_TECH_REVIEW '), DEFAULT_STYLE_PRESET);
  assert.equal(normalizeStylePreset('removed-style'), DEFAULT_STYLE_PRESET);
  assert.equal(getStylePreset('removed-style').id, DEFAULT_STYLE_PRESET);
});

test('visual tokens match the renderer-facing Golden Master palette', () => {
  const preset = getStylePreset(DEFAULT_STYLE_PRESET);
  assert.equal(preset.accent, '#FFE600');
  assert.equal(preset.status, '#25F4EE');
  assert.equal(preset.neutral, '#FFFFFF');
});

test('manifest compatibility reads top-level, render params, and style aliases', () => {
  assert.equal(stylePresetFromManifest({ style_preset: DEFAULT_STYLE_PRESET }), DEFAULT_STYLE_PRESET);
  assert.equal(stylePresetFromManifest({ render_params: { style_preset: DEFAULT_STYLE_PRESET } }), DEFAULT_STYLE_PRESET);
  assert.equal(stylePresetFromManifest({ style: { stylePreset: DEFAULT_STYLE_PRESET } }), DEFAULT_STYLE_PRESET);
  assert.equal(stylePresetFromManifest({}, { style_preset: DEFAULT_STYLE_PRESET }), DEFAULT_STYLE_PRESET);
});

test('payload helper preserves existing state and makes selection explicit', () => {
  const original = { clip_list: [{ source_path: 'clip.mp4' }], style: { font_name: 'IBMPlex' } };
  const payload = withStylePresetPayload(original, DEFAULT_STYLE_PRESET);
  assert.deepEqual(payload.clip_list, original.clip_list);
  assert.deepEqual(payload.style, original.style);
  assert.equal(payload.style_preset, DEFAULT_STYLE_PRESET);
  assert.equal(original.style_preset, undefined);
});

test('custom option lists stay duplicate-safe without mutating the catalog', () => {
  const options = [
    { id: 'alpha', label: 'A' },
    { id: 'ALPHA', label: 'duplicate' },
    { id: ' beta ', label: 'B' },
    { id: '', label: 'invalid' },
  ];
  assert.deepEqual(uniqueStylePresets(options).map((preset) => preset.id), ['alpha', ' beta ']);
  assert.equal(uniqueStylePresets().length, STYLE_PRESET_CATALOG.length);
});
