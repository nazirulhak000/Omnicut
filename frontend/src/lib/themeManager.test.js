import test from 'node:test';
import assert from 'node:assert/strict';
import {
  THEME_PRESETS,
  VALID_THEME_IDS,
  DEFAULT_THEME_ID,
  normalizeThemeId,
  getStoredTheme,
  getStoredOrbsEnabled,
  applyTheme,
  setOrbsEnabled,
  STORAGE_KEY_THEME,
  STORAGE_KEY_ORBS
} from './themeManager.js';

test('themeManager exposes 4 premier presets including glassmorphism, obsidian, cyberpunk, and slate', () => {
  assert.equal(THEME_PRESETS.length, 4);
  assert.deepEqual(VALID_THEME_IDS, ['glassmorphism', 'obsidian', 'cyberpunk', 'slate']);
  assert.equal(DEFAULT_THEME_ID, 'glassmorphism');

  for (const preset of THEME_PRESETS) {
    assert.ok(preset.id, 'Preset must have an id');
    assert.ok(preset.name, 'Preset must have a name');
    assert.ok(preset.styleTag, 'Preset must have a styleTag');
    assert.ok(preset.description, 'Preset must have a description');
    assert.ok(Array.isArray(preset.accentColors), 'Preset must have accentColors');
    assert.equal(typeof preset.orbsDefault, 'boolean', 'Preset must declare orbsDefault');
  }
});

test('normalizeThemeId validates inputs and safely falls back to default', () => {
  assert.equal(normalizeThemeId('glassmorphism'), 'glassmorphism');
  assert.equal(normalizeThemeId('OBSIDIAN'), 'obsidian');
  assert.equal(normalizeThemeId('  cyberpunk  '), 'cyberpunk');
  assert.equal(normalizeThemeId('slate'), 'slate');
  assert.equal(normalizeThemeId('unknown-theme'), 'glassmorphism');
  assert.equal(normalizeThemeId(null), 'glassmorphism');
  assert.equal(normalizeThemeId(undefined), 'glassmorphism');
});

test('applyTheme and getStoredTheme manage localStorage and DOM data-theme attribute', () => {
  // Mock localStorage
  const storage = {};
  globalThis.localStorage = {
    getItem: (key) => storage[key] ?? null,
    setItem: (key, val) => { storage[key] = String(val); },
    removeItem: (key) => { delete storage[key]; }
  };

  // Mock documentElement
  const attributes = {};
  globalThis.document = {
    documentElement: {
      setAttribute: (k, v) => { attributes[k] = v; },
      getAttribute: (k) => attributes[k] ?? null
    }
  };

  // Initial without stored
  assert.equal(getStoredTheme(), 'glassmorphism');

  // Apply obsidian
  const applied = applyTheme('obsidian');
  assert.equal(applied, 'obsidian');
  assert.equal(storage[STORAGE_KEY_THEME], 'obsidian');
  assert.equal(attributes['data-theme'], 'obsidian');
  assert.equal(getStoredTheme(), 'obsidian');

  // Apply invalid theme
  const fallback = applyTheme('invalid');
  assert.equal(fallback, 'glassmorphism');
  assert.equal(storage[STORAGE_KEY_THEME], 'glassmorphism');
  assert.equal(attributes['data-theme'], 'glassmorphism');

  // Orbs toggling
  assert.equal(getStoredOrbsEnabled('obsidian'), false); // default for obsidian is false
  assert.equal(getStoredOrbsEnabled('glassmorphism'), true); // default for glassmorphism is true

  // Set explicit orbs preference
  setOrbsEnabled(true);
  assert.equal(storage[STORAGE_KEY_ORBS], 'true');
  assert.equal(getStoredOrbsEnabled('obsidian'), true); // overridden by explicit setting

  setOrbsEnabled(false);
  assert.equal(storage[STORAGE_KEY_ORBS], 'false');
  assert.equal(getStoredOrbsEnabled('glassmorphism'), false);
});
