import test from 'node:test';
import assert from 'node:assert/strict';
import { createUiThemeSession } from './uiThemeSession.js';
import { normalizeThemePreferences, updatePresetOverrides } from './themeResolver.js';
import { STORAGE_KEY_UI_PREFERENCES } from './themeStorage.js';

function memory(seed = {}) {
  const values = new Map(Object.entries(seed));
  const writes = [];
  return { values, writes, getItem: key => values.get(key) ?? null, setItem(key, value) { writes.push([key, value]); values.set(key, value); } };
}
const candidate = () => normalizeThemePreferences({ activePresetId: 'balanced-glass' });

test('initialization and editing or cancelling a draft make no persisted or applied changes', () => {
  const storage = memory();
  const session = createUiThemeSession(storage);
  const before = session.getSnapshot();
  const draft = updatePresetOverrides(candidate(), 'balanced-glass', { blurPx: 22 });
  assert.equal(draft.overridesByPreset['balanced-glass'].blurPx, 22);
  assert.equal(session.getSnapshot(), before);
  assert.equal(storage.writes.length, 0);
  assert.equal(before.preferences.activePresetId, 'glassmorphism');
});

test('apply publishes a reactive update and persists one complete transaction without legacy writes', () => {
  const storage = memory({ omnicut_ui_theme: 'obsidian' });
  const session = createUiThemeSession(storage);
  let notifications = 0;
  const unsubscribe = session.subscribe(() => notifications++);
  const result = session.applyPreferences(candidate(), { expectedRevision: 0 });
  assert.equal(result.ok, true);
  assert.equal(result.persisted, true);
  assert.equal(storage.writes.length, 1);
  assert.equal(storage.writes[0][0], STORAGE_KEY_UI_PREFERENCES);
  assert.equal(storage.getItem('omnicut_ui_theme'), 'obsidian');
  assert.equal(session.getSnapshot().status.kind, 'saved');
  assert.equal(session.getSnapshot().revision, 1);
  assert.equal(notifications, 1);
  unsubscribe();
  session.applyPreferences(candidate());
  assert.equal(notifications, 1);
  assert.equal(createUiThemeSession(storage).getSnapshot().preferences.activePresetId, 'balanced-glass');
});

test('cross-tab updates preserve a stale draft and reject it until explicitly rebased', () => {
  const storage = memory();
  const first = createUiThemeSession(storage);
  const other = createUiThemeSession(storage);
  const draft = updatePresetOverrides(candidate(), 'balanced-glass', { blurPx: 20 });
  other.applyPreferences(updatePresetOverrides(candidate(), 'balanced-glass', { blurPx: 6 }));
  const rejected = first.applyPreferences(draft, { expectedRevision: 0 });
  assert.equal(rejected.conflict, true);
  assert.equal(storage.writes.length, 1);
  assert.equal(first.getSnapshot().preferences.overridesByPreset['balanced-glass'].blurPx, 6);
  assert.equal(draft.overridesByPreset['balanced-glass'].blurPx, 20);
  assert.equal(first.applyPreferences(draft, { expectedRevision: 0 }).conflict, true);
  assert.equal(first.applyPreferences(draft, { expectedRevision: first.getSnapshot().revision }).ok, true);
});

test('future schema cannot be overwritten and a newly arriving future record locks editing', () => {
  const storage = memory();
  const session = createUiThemeSession(storage);
  const future = JSON.stringify({ schemaVersion: 99, custom: 'preserve me' });
  storage.values.set(STORAGE_KEY_UI_PREFERENCES, future);
  assert.equal(session.applyPreferences(candidate()).error, 'future-schema');
  assert.equal(session.getSnapshot().readOnly, true);
  assert.equal(session.applyPreferences(candidate()).error, 'future-schema');
  assert.equal(storage.writes.length, 0);
  assert.equal(storage.getItem(STORAGE_KEY_UI_PREFERENCES), future);
});

test('blocked storage applies only to the session and never reports a saved status', () => {
  const storage = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } };
  const session = createUiThemeSession(storage);
  const result = session.applyPreferences(candidate());
  assert.equal(result.ok, true);
  assert.equal(result.persisted, false);
  assert.equal(result.error, 'storage-unavailable');
  assert.equal(session.getSnapshot().status.kind, 'session');
  assert.equal(session.getSnapshot().preferences.activePresetId, 'balanced-glass');
});

test('unchanged reloads preserve snapshot identity and external updates publish once', () => {
  const storage = memory();
  const session = createUiThemeSession(storage);
  const before = session.getSnapshot();
  assert.equal(session.reloadPreferences(), before);
  const other = createUiThemeSession(storage);
  other.applyPreferences(candidate());
  session.reloadPreferences();
  const after = session.getSnapshot();
  assert.notEqual(before, after);
  assert.equal(after.revision, 1);
  assert.equal(session.reloadPreferences(), after);
});
