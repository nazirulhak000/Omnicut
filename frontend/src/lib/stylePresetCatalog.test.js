import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ANGLE_TO_DEFAULT_STYLE,
  AUTO_STYLE_PRESET,
  DEFAULT_ONE_CLICK_STYLE_PRESET,
  DEFAULT_STYLE_PRESET,
  STYLE_PRESET_CATALOG,
  getRecommendedStyleForAngle,
  getStylePreset,
  normalizeStylePreset,
  stylePresetFromManifest,
  uniqueStylePresets,
  withStylePresetPayload,
} from './stylePresetCatalog.js';
import { DEFAULT_STUDIO_FORM, STYLE_PRESET_STORAGE_VERSION, migrateSavedStudioForm } from './studioDefaults.js';

test('catalog has a unique renderer-supported default', () => {
  assert.equal(STYLE_PRESET_CATALOG.length, 10);
  assert.equal(normalizeStylePreset(DEFAULT_STYLE_PRESET), DEFAULT_STYLE_PRESET);
  assert.equal(new Set(STYLE_PRESET_CATALOG.map((preset) => preset.id)).size, STYLE_PRESET_CATALOG.length);
  assert.deepEqual(STYLE_PRESET_CATALOG.map((preset) => preset.id), [
    'viral_punch',
    'clean_tech_review',
    'tech_product_showcase',
    'smooth_showcase',
    'premium_minimal',
    'flash_deal',
    'pain_punch',
    'tech_compare',
    'smart_hack',
    'niche_focus',
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

test('every angle default points at a real preset, including IT angle keys and batch suffixes', () => {
  for (const [angle, style] of Object.entries(ANGLE_TO_DEFAULT_STYLE)) {
    assert.equal(normalizeStylePreset(style), style, angle);
  }
  for (const key of ['spec_compare', 'fake_vs_real', 'real_test', 'spec_explained', 'pain_point', 'dont_cheap_out', 'how_to_setup', 'worth_upgrade']) {
    assert.ok(Object.hasOwn(ANGLE_TO_DEFAULT_STYLE, key), key);
  }
  assert.equal(getRecommendedStyleForAngle('spec_compare_b2'), 'tech_compare');
  assert.equal(getRecommendedStyleForAngle(' HOW_TO_SETUP '), 'smart_hack');
  assert.equal(getRecommendedStyleForAngle('unknown'), DEFAULT_STYLE_PRESET);
});

test('M5: every preset describes its own motion and transitions (no copy-paste labels)', () => {
  for (const field of ['description', 'motion', 'transitions']) {
    const values = STYLE_PRESET_CATALOG.map((preset) => preset[field]);
    assert.equal(new Set(values).size, STYLE_PRESET_CATALOG.length, `${field} must be unique per preset`);
  }
  const byId = Object.fromEntries(STYLE_PRESET_CATALOG.map((preset) => [preset.id, preset]));
  // The wording names what the renderer plays (scripts/style_motion_policy.py).
  assert.match(byId.smooth_showcase.transitions, /Dissolve/);
  assert.doesNotMatch(byId.smart_hack.transitions, /Dissolve/);
  assert.match(byId.smart_hack.transitions, /Slide/);
  assert.match(byId.tech_compare.transitions, /Wipe/);
  assert.match(byId.niche_focus.transitions, /Circle/);
  assert.match(byId.premium_minimal.transitions, /Fade/);
});

test('batch auto choice is not a preset id, so it never masks an angle default', () => {
  assert.equal(AUTO_STYLE_PRESET, 'auto');
  assert.ok(!STYLE_PRESET_CATALOG.some((preset) => preset.id === AUTO_STYLE_PRESET));
});
