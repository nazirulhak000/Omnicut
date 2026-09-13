import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_ONE_CLICK_STYLE_PRESET,
  DEFAULT_STYLE_PRESET,
  STYLE_PRESET_CATALOG,
  getStylePreset,
  normalizeStylePreset,
  stylePresetFromManifest,
  uniqueStylePresets,
  withStylePresetPayload,
} from './stylePresetCatalog.js';
import { DEFAULT_STUDIO_FORM, STYLE_PRESET_STORAGE_VERSION, migrateSavedStudioForm } from './studioDefaults.js';

test('catalog has a unique renderer-supported default', () => {
  assert.equal(STYLE_PRESET_CATALOG.length, 5);
  assert.equal(normalizeStylePreset(DEFAULT_STYLE_PRESET), DEFAULT_STYLE_PRESET);
  assert.equal(new Set(STYLE_PRESET_CATALOG.map((preset) => preset.id)).size, STYLE_PRESET_CATALOG.length);
  assert.deepEqual(STYLE_PRESET_CATALOG.map((preset) => preset.id), [
    'viral_punch',
    'clean_tech_review',
    'tech_product_showcase',
    'smooth_showcase',
    'premium_minimal',
  ]);
  assert.equal(STYLE_PRESET_CATALOG.filter((preset) => preset.recommended).length, 1);
});

test('new One Click sessions default to the Golden Master style', () => {
  assert.equal(DEFAULT_ONE_CLICK_STYLE_PRESET, DEFAULT_STYLE_PRESET);
  assert.equal(DEFAULT_STUDIO_FORM.stylePreset, DEFAULT_ONE_CLICK_STYLE_PRESET);
  assert.equal(getStylePreset(DEFAULT_STUDIO_FORM.stylePreset).id, DEFAULT_STYLE_PRESET);
});

test('legacy saved forms migrate the implicit style without overwriting an explicit choice', () => {
  assert.equal(migrateSavedStudioForm({ stylePreset: 'viral_punch' }).stylePreset, DEFAULT_STYLE_PRESET);
  assert.equal(
    migrateSavedStudioForm({ stylePreset: 'viral_punch', stylePresetVersion: STYLE_PRESET_STORAGE_VERSION }).stylePreset,
    'viral_punch',
  );
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

test('each selectable style carries a distinct renderer-facing accent', () => {
  const accents = STYLE_PRESET_CATALOG.map((preset) => preset.accent);
  assert.equal(new Set(accents).size, STYLE_PRESET_CATALOG.length);
  for (const preset of STYLE_PRESET_CATALOG) {
    assert.match(preset.accent, /^#[0-9A-F]{6}$/);
    assert.match(preset.status, /^#[0-9A-F]{6}$/);
    assert.match(preset.neutral, /^#[0-9A-F]{6}$/);
  }
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
