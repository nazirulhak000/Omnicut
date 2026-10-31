import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeThemePreferences, updatePresetOverrides, resolveTheme, createCustomPreset, deleteCustomPreset } from './themeResolver.js';
import { readThemePreferences, saveThemePreferences, STORAGE_KEY_UI_PREFERENCES } from './themeStorage.js';

function memory(initial = {}) {
  const data = { ...initial };
  const writes = [];
  return { data, writes, getItem: key => data[key] ?? null, setItem: (key, value) => { data[key] = value; writes.push(key); } };
}

test('schema rejects arbitrary CSS, malformed values and prototype inputs; preset updates stay isolated', () => {
  for (const value of [null, [], 1, 'oops']) assert.equal(normalizeThemePreferences(value).activePresetId, 'glassmorphism');
  const source = normalizeThemePreferences({ activePresetId: 'balanced-glass', overridesByPreset: {
    'balanced-glass': { accent: 'url(secret)', blurPx: Infinity, shellTransparency: 99, fake: 'CSS' },
  } });
  assert.deepEqual(source.overridesByPreset['balanced-glass'], { shellTransparency: 55 });
  const changed = updatePresetOverrides(source, 'slate', { blurPx: -5 });
  assert.equal(changed.overridesByPreset.slate.blurPx, 0);
  assert.equal(source.overridesByPreset.slate, undefined);
  assert.equal(changed.overridesByPreset['balanced-glass'].shellTransparency, 55);
});

test('legacy migration preserves selected theme, glass and orbs without storage writes', () => {
  const store = memory({ omnicut_ui_theme: 'obsidian', omnicut_glass_config: '{"opacity":38,"blur":18}', omnicut_ambient_orbs_enabled: 'true' });
  const loaded = readThemePreferences(store);
  assert.equal(loaded.preferences.activePresetId, 'obsidian');
  assert.equal(loaded.preferences.legacyGlassConfig.opacity, 38);
  assert.equal(loaded.preferences.legacyGlassConfig.blur, 18);
  assert.equal(loaded.preferences.legacyOrbsEnabled, true);
  assert.deepEqual(store.writes, []);
  assert.equal(resolveTheme(loaded.preferences).isLegacy, true);
});

test('future schema is read only and cannot be overwritten even by direct save', () => {
  const raw = '{"schemaVersion":3,"future":"keep"}';
  const store = memory({ [STORAGE_KEY_UI_PREFERENCES]: raw });
  assert.equal(readThemePreferences(store).readOnly, true);
  assert.equal(saveThemePreferences({}, store).error, 'future-schema');
  assert.equal(store.data[STORAGE_KEY_UI_PREFERENCES], raw);
  assert.deepEqual(store.writes, []);
});

test('persistence is a single bounded transaction and detects a stale tab', () => {
  const store = memory();
  const first = readThemePreferences(store);
  const draft = updatePresetOverrides({ ...first.preferences, activePresetId: 'balanced-glass' }, 'balanced-glass', { accent: '#AAFFEE' });
  assert.equal(store.writes.length, 0);
  const saved = saveThemePreferences(draft, store, { expectedRevision: first.revision });
  assert.equal(saved.ok, true);
  assert.equal(store.writes.length, 1);
  assert.equal(readThemePreferences(store).preferences.overridesByPreset['balanced-glass'].accent, '#aaffee');
  assert.equal(saveThemePreferences(first.preferences, store, { expectedRevision: first.revision }).error, 'conflict');
});

test('corrupt and unavailable storage fall back without throwing or reporting a false save', () => {
  const store = memory({ [STORAGE_KEY_UI_PREFERENCES]: 'null' });
  assert.equal(readThemePreferences(store).source, 'recovered');
  const blocked = { getItem() { throw Error('blocked'); }, setItem() { throw Error('quota'); } };
  assert.equal(readThemePreferences(blocked).source, 'unavailable');
  assert.equal(saveThemePreferences({}, blocked).ok, false);
});

test('resolver supports reduced effects, motion and solid fallback without changing status colors', () => {
  const full = normalizeThemePreferences({ activePresetId: 'balanced-glass', ambientMotion: true });
  const result = resolveTheme(full);
  assert.equal(result.variables['--oc-ui-glass-shell-alpha'], '0.6');
  assert.equal(result.ambientMotion, true);
  assert.equal(resolveTheme(full, { reducedMotion: true }).ambientMotion, false);
  assert.equal(resolveTheme(full, { backdropSupported: false }).variables['--oc-ui-glass-shell-blur'], '0px');
  assert.equal(resolveTheme(full, { backdropSupported: false }).variables['--oc-ui-glass-shell-alpha'], '1');
  const reduced = resolveTheme({ ...full, effects: 'reduced' });
  assert.equal(reduced.effects, 'off');
  assert.equal(reduced.ambientEnabled, false);
  assert.equal(reduced.variables['--oc-ui-glass-shell-blur'], '0px');
  assert.equal(reduced.variables['--oc-ui-glass-saturation'], '100%');
  assert.equal(reduced.variables['--oc-ui-shadow-floating'], 'none');
  const light = resolveTheme({ ...full, effects: 'light' });
  assert.equal(light.effects, 'light');
  assert.equal(light.ambientEnabled, false);
  assert.equal(light.variables['--oc-ui-glass-shell-blur'], '8px');
  assert.notEqual(light.variables['--oc-ui-shadow-floating'], result.variables['--oc-ui-shadow-floating']);
  const recolored = resolveTheme(updatePresetOverrides(full, 'balanced-glass', { accent: '#ee33cc' }));
  for (const role of ['success', 'warning', 'error', 'info']) assert.equal(recolored.variables[`--oc-ui-${role}`], result.variables[`--oc-ui-${role}`]);
  const darkPreferences = updatePresetOverrides(full, 'balanced-glass', { accent: '#000000' });
  const dark = resolveTheme(darkPreferences);
  assert.equal(darkPreferences.overridesByPreset['balanced-glass'].accent, '#000000');
  assert.equal(dark.requestedAccent, '#000000');
  assert.equal(dark.accentAdjusted, true);
  assert.equal(dark.variables['--oc-ui-accent'], '#67d7e7');
});

test('custom themes capture values, stay bounded, survive reload and delete without losing other themes', () => {
  const original = updatePresetOverrides({ activePresetId: 'balanced-glass' }, 'balanced-glass', { blurPx: 20 });
  const custom = createCustomPreset(original, { id: 'custom-mine', name: '  My workspace  ' });
  assert.equal(custom.activePresetId, 'custom-mine');
  assert.equal(resolveTheme(custom).variables['--oc-ui-glass-shell-blur'], '20px');
  assert.equal(original.customPresets.length, 0);
  assert.equal(createCustomPreset(custom, { id: 'custom-mine', name: 'Duplicate' }).customPresets.length, 1);
  assert.equal(createCustomPreset(custom, { id: '__proto__', name: 'Bad' }).customPresets.length, 1);
  assert.equal(createCustomPreset({}, { id: 'custom-legacy', name: 'Legacy' }).customPresets.length, 0);
  const store = memory();
  saveThemePreferences(custom, store);
  assert.equal(readThemePreferences(store).preferences.customPresets[0].name, 'My workspace');
  const deleted = deleteCustomPreset(custom, 'custom-mine');
  assert.equal(deleted.activePresetId, 'balanced-glass');
  assert.equal(deleted.customPresets.length, 0);
});
