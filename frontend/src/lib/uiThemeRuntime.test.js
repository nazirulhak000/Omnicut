import test from 'node:test';
import assert from 'node:assert/strict';
import { applyResolvedUiTheme, applyLegacyUiTheme, isUiThemeV2Enabled } from './uiThemeRuntime.js';

function rootFixture() {
  const attrs = new Map([['data-theme', 'obsidian']]);
  const vars = new Map([['--oc-ui-accent', ['old', 'important']], ['--caption-color', ['white', '']]]);
  return {
    attrs, vars,
    getAttribute: (key) => attrs.get(key) ?? null,
    setAttribute: (key, value) => attrs.set(key, value),
    removeAttribute: (key) => attrs.delete(key),
    style: {
      getPropertyValue: (key) => vars.get(key)?.[0] || '',
      getPropertyPriority: (key) => vars.get(key)?.[1] || '',
      setProperty: (key, value, priority = '') => vars.set(key, [value, priority]),
      removeProperty: (key) => vars.delete(key),
    },
  };
}

const candidate = { isLegacy: false, effects: 'full', variables: { '--oc-ui-accent': '#67D7E7', '--oc-ui-glass-shell-blur': '12px', '--caption-color': 'red' } };

test('new UI renderer requires the explicit build opt-in and makes zero writes otherwise', () => {
  for (const value of [undefined, null, '', 'false', true, '1']) assert.equal(isUiThemeV2Enabled(value), false);
  assert.equal(isUiThemeV2Enabled('true'), true);
  const root = rootFixture();
  const before = [...root.vars];
  applyResolvedUiTheme(root, candidate)();
  assert.deepEqual([...root.vars], before);
  assert.equal(root.attrs.has('data-ui-theme'), false);
});

test('candidate activation is reversible and never changes video/legacy namespaces', () => {
  const root = rootFixture();
  const restore = applyResolvedUiTheme(root, candidate, true);
  assert.equal(root.attrs.get('data-ui-theme'), 'balanced');
  assert.equal(root.attrs.get('data-theme'), 'obsidian');
  assert.equal(root.vars.get('--caption-color')[0], 'white');
  assert.equal(root.vars.get('--oc-ui-accent')[0], '#67D7E7');
  restore();
  assert.equal(root.attrs.has('data-ui-theme'), false);
  assert.deepEqual(root.vars.get('--oc-ui-accent'), ['old', 'important']);
  assert.equal(root.vars.has('--oc-ui-glass-shell-blur'), false);
});

test('legacy selection and absent DOM stay untouched even in an opt-in build', () => {
  const root = rootFixture();
  applyResolvedUiTheme(root, { ...candidate, isLegacy: true }, true)();
  assert.equal(root.attrs.has('data-ui-theme'), false);
  assert.doesNotThrow(() => applyResolvedUiTheme(null, candidate, true)());
});

test('migrated legacy snapshots restore exact optics without touching video properties', () => {
  const root = rootFixture();
  const preferences = { activePresetId: 'slate', legacyGlassConfig: { opacity: 38, blur: 18, glare: 85, orbsGlow: 70, saturate: 195 } };
  const restore = applyLegacyUiTheme(root, preferences, true);
  assert.equal(root.attrs.get('data-theme'), 'slate');
  assert.equal(root.vars.get('--glass-opacity')[0], '0.38');
  assert.equal(root.vars.get('--glass-blur')[0], '18px');
  assert.equal(root.vars.get('--caption-color')[0], 'white');
  assert.equal(root.attrs.has('data-ui-theme'), false);
  restore();
  assert.equal(root.attrs.get('data-theme'), 'obsidian');
  assert.equal(root.vars.has('--glass-opacity'), false);
});
