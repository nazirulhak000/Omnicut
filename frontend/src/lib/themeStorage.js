import { STORAGE_KEY_THEME, STORAGE_KEY_ORBS, STORAGE_KEY_GLASS_CONFIG, normalizeThemeId, THEME_PRESETS } from './themeManager.js';
import { normalizeThemePreferences } from './themeResolver.js';

export const STORAGE_KEY_UI_PREFERENCES = 'omnicut_ui_preferences_v2';
const getStorage = supplied => supplied ?? globalThis.localStorage;
const parse = raw => { try { return JSON.parse(raw); } catch { return null; } };

export function readThemePreferences(storage) {
  try {
    const store = getStorage(storage);
    const revision = store.getItem(STORAGE_KEY_UI_PREFERENCES);
    const parsed = parse(revision);
    if (parsed?.schemaVersion > 2) {
      return { preferences: normalizeThemePreferences(null), source: 'future', readOnly: true, error: 'future-schema', revision };
    }
    if (parsed?.schemaVersion === 2 && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return { preferences: normalizeThemePreferences(parsed), source: 'v2', readOnly: false, error: null, revision };
    }
    const legacyThemeId = normalizeThemeId(store.getItem(STORAGE_KEY_THEME));
    const orbsRaw = store.getItem(STORAGE_KEY_ORBS);
    const preferences = normalizeThemePreferences({
      activePresetId: legacyThemeId, legacyThemeId,
      legacyGlassConfig: parse(store.getItem(STORAGE_KEY_GLASS_CONFIG)),
      legacyOrbsEnabled: orbsRaw === null ? THEME_PRESETS.find(p => p.id === legacyThemeId).orbsDefault : orbsRaw === 'true',
    });
    return { preferences, source: revision === null ? 'legacy' : 'recovered', readOnly: false, error: revision === null ? null : 'invalid-preferences', revision };
  } catch {
    return { preferences: normalizeThemePreferences(null), source: 'unavailable', readOnly: false, error: 'storage-unavailable', revision: null };
  }
}

export function saveThemePreferences(preferences, storage, options = {}) {
  const safe = normalizeThemePreferences(preferences);
  try {
    const store = getStorage(storage);
    const revision = store.getItem(STORAGE_KEY_UI_PREFERENCES);
    if (parse(revision)?.schemaVersion > 2) return { ok: false, preferences: safe, error: 'future-schema' };
    if (Object.hasOwn(options, 'expectedRevision') && revision !== options.expectedRevision) {
      return { ok: false, preferences: safe, error: 'conflict' };
    }
    const nextRevision = JSON.stringify(safe);
    store.setItem(STORAGE_KEY_UI_PREFERENCES, nextRevision);
    return { ok: true, preferences: safe, error: null, revision: nextRevision };
  } catch {
    return { ok: false, preferences: safe, error: 'storage-unavailable' };
  }
}
