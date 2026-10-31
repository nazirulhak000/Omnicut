import React, { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { normalizeThemePreferences, resolveTheme } from '../lib/themeResolver.js';
import { STORAGE_KEY_UI_PREFERENCES } from '../lib/themeStorage.js';
import { createUiThemeSession } from '../lib/uiThemeSession.js';
import { applyResolvedUiTheme, applyLegacyUiTheme, isUiThemeV2Enabled } from '../lib/uiThemeRuntime.js';

export const UI_THEME_V2_ENABLED = isUiThemeV2Enabled(import.meta.env?.VITE_UI_THEME_V2);
const disabledPreferences = normalizeThemePreferences(null);
const disabledSnapshot = { preferences: disabledPreferences, readOnly: true, revision: 0, status: { kind: 'idle', message: '' } };
const noop = () => {};
const disabledSession = { getSnapshot: () => disabledSnapshot, subscribe: () => noop, applyPreferences: () => ({ ok: false, error: 'disabled' }), reloadPreferences: noop };
const ThemeContext = createContext({ ...disabledSnapshot, enabled: false, resolved: resolveTheme(disabledPreferences), applyPreferences: disabledSession.applyPreferences, reloadPreferences: noop, restoreLegacy: noop });

export function ThemeProvider({ children, enabled = UI_THEME_V2_ENABLED }) {
  const [session] = useState(() => enabled ? createUiThemeSession() : disabledSession);
  const snapshot = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getSnapshot);
  const [reducedMotion, setReducedMotion] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
  const backdropSupported = typeof CSS === 'undefined' || CSS.supports('backdrop-filter', 'blur(1px)') || CSS.supports('-webkit-backdrop-filter', 'blur(1px)');
  const resolved = useMemo(() => resolveTheme(snapshot.preferences, { reducedMotion, backdropSupported }), [snapshot.preferences, reducedMotion, backdropSupported]);

  useEffect(() => {
    if (!enabled) return;
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const onMotion = () => setReducedMotion(!!media?.matches);
    const onStorage = (event) => {
      if (event.key === STORAGE_KEY_UI_PREFERENCES || event.key === null) session.reloadPreferences();
    };
    media?.addEventListener?.('change', onMotion);
    window.addEventListener('storage', onStorage);
    return () => { media?.removeEventListener?.('change', onMotion); window.removeEventListener('storage', onStorage); };
  }, [enabled, session]);

  useEffect(() => {
    if (!enabled || snapshot.readOnly) return;
    if (resolved.isLegacy) return applyLegacyUiTheme(document.documentElement, snapshot.preferences, true);
    return applyResolvedUiTheme(document.documentElement, resolved, true);
  }, [enabled, resolved, snapshot.preferences, snapshot.readOnly]);

  const restoreLegacy = useCallback(() => session.applyPreferences({ ...snapshot.preferences, activePresetId: snapshot.preferences.legacyThemeId }), [session, snapshot.preferences]);
  const value = useMemo(() => ({ ...snapshot, enabled, resolved, applyPreferences: session.applyPreferences, reloadPreferences: session.reloadPreferences, restoreLegacy }), [snapshot, enabled, resolved, session, restoreLegacy]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemeSettings() {
  return useContext(ThemeContext);
}
