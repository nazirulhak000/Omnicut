import { normalizeThemeId, DEFAULT_GLASS_CONFIG } from './themeManager.js';
import { UI_THEME_PRESETS, UI_THEME_DEFAULTS, UI_THEME_CONTROL_RANGES, createDefaultThemePreferences } from './themeCatalog.js';

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const clamp = (value, min, max, fallback) => Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
const validId = value => typeof value === 'string' && /^custom-[a-z0-9-]{1,48}$/.test(value);

export function normalizeThemeOverrides(value) {
  if (!object(value)) return {};
  const safe = {};
  if (typeof value.accent === 'string' && /^#[a-f\d]{6}$/i.test(value.accent)) safe.accent = value.accent.toLowerCase();
  for (const [key, range] of Object.entries(UI_THEME_CONTROL_RANGES)) {
    if (Number.isFinite(value[key])) safe[key] = clamp(value[key], range.min, range.max, UI_THEME_DEFAULTS[key]);
  }
  return safe;
}

export function normalizeThemePreferences(value) {
  const defaults = createDefaultThemePreferences();
  if (!object(value)) return defaults;
  const customPresets = [];
  if (Array.isArray(value.customPresets)) {
    for (const entry of value.customPresets.slice(0, 12)) {
      if (!object(entry) || !validId(entry.id) || customPresets.some(p => p.id === entry.id)) continue;
      const name = typeof entry.name === 'string' ? entry.name.trim().slice(0, 48) : '';
      if (!name) continue;
      customPresets.push({ id: entry.id, name, baseFamily: 'balanced-glass', overrides: normalizeThemeOverrides(entry.overrides) });
    }
  }
  const allowed = [...UI_THEME_PRESETS.map(p => p.id), ...customPresets.map(p => p.id)];
  const legacyThemeId = normalizeThemeId(value.legacyThemeId);
  const activePresetId = allowed.includes(value.activePresetId) ? value.activePresetId : legacyThemeId;
  const overridesByPreset = {};
  if (object(value.overridesByPreset)) {
    for (const id of allowed) {
      if (Object.hasOwn(value.overridesByPreset, id)) overridesByPreset[id] = normalizeThemeOverrides(value.overridesByPreset[id]);
    }
  }
  const rawGlass = object(value.legacyGlassConfig) ? value.legacyGlassConfig : {};
  const legacyGlassConfig = {};
  for (const [key, min, max] of [['opacity', 5, 70], ['blur', 2, 36], ['glare', 10, 100], ['orbsGlow', 10, 100], ['saturate', 100, 280]]) {
    legacyGlassConfig[key] = clamp(rawGlass[key], min, max, DEFAULT_GLASS_CONFIG[key]);
  }
  return {
    schemaVersion: 2, activePresetId, legacyThemeId, overridesByPreset, customPresets,
    effects: value.effects === 'light' ? 'light' : ['off', 'reduced'].includes(value.effects) ? 'off' : 'full', ambientMotion: value.ambientMotion === true,
    legacyGlassConfig, legacyOrbsEnabled: typeof value.legacyOrbsEnabled === 'boolean' ? value.legacyOrbsEnabled : defaults.legacyOrbsEnabled,
  };
}

export function getPresetDefinition(preferences, presetId = preferences?.activePresetId) {
  const preset = UI_THEME_PRESETS.find(p => p.id === presetId);
  if (preset) return preset;
  const custom = preferences?.customPresets?.find(p => p.id === presetId);
  return custom ? { ...custom, description: 'ธีมที่บันทึกไว้', isLegacy: false, supportsGlass: true, defaults: { ...UI_THEME_DEFAULTS, ...custom.overrides } } : UI_THEME_PRESETS[0];
}

export function updatePresetOverrides(preferences, presetId, patch) {
  const safe = normalizeThemePreferences(preferences);
  if (getPresetDefinition(safe, presetId).id !== presetId) return safe;
  safe.overridesByPreset[presetId] = { ...safe.overridesByPreset[presetId], ...normalizeThemeOverrides(patch) };
  return safe;
}

export function createCustomPreset(preferences, { id, name, basePresetId } = {}) {
  const safe = normalizeThemePreferences(preferences);
  if (!validId(id) || typeof name !== 'string' || !name.trim() || safe.customPresets.length >= 12 || safe.customPresets.some(p => p.id === id)) return safe;
  const source = getPresetDefinition(safe, basePresetId || safe.activePresetId);
  if (source.isLegacy) return safe;
  const overrides = { ...source.defaults, ...safe.overridesByPreset[source.id] };
  safe.customPresets.push({ id, name: name.trim().slice(0, 48), baseFamily: 'balanced-glass', overrides: normalizeThemeOverrides(overrides) });
  safe.activePresetId = id;
  return safe;
}

export function deleteCustomPreset(preferences, id) {
  const safe = normalizeThemePreferences(preferences);
  safe.customPresets = safe.customPresets.filter(p => p.id !== id);
  delete safe.overridesByPreset[id];
  if (safe.activePresetId === id) safe.activePresetId = 'balanced-glass';
  return safe;
}

const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
const rgba = (hex, alpha) => `rgba(${rgb(hex).join(', ')}, ${alpha})`;
const luminance = hex => {
  const channels = rgb(hex).map(v => { const c = v / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; });
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
};
const contrast = (first, second) => (Math.max(luminance(first), luminance(second)) + .05) / (Math.min(luminance(first), luminance(second)) + .05);

export function resolveTheme(preferences, { reducedMotion = false, backdropSupported = true } = {}) {
  const safe = normalizeThemePreferences(preferences);
  const preset = getPresetDefinition(safe);
  const values = { ...preset.defaults, ...safe.overridesByPreset[preset.id] };
  const off = safe.effects === 'off';
  const light = safe.effects === 'light';
  const ambientEnabled = safe.effects === 'full' && (preset.isLegacy ? safe.legacyOrbsEnabled : values.ambientStrength > 0);
  // User intent remains in preferences. One accessible effective accent protects
  // text links, outlined actions and navigation on both reading surfaces.
  const effectiveAccent = ['#142033', '#0e1726'].every(surface => contrast(values.accent, surface) >= 4.5)
    ? values.accent : UI_THEME_DEFAULTS.accent;
  const canvas = rgb('#080e18').map(channel => Math.round(channel * (1 - values.backgroundStrength / 100)));
  const accentLight = luminance(effectiveAccent);
  const darkContrast = (accentLight + .05) / (luminance('#07131b') + .05);
  const whiteContrast = 1.05 / (accentLight + .05);
  const variables = {
    '--oc-ui-bg-canvas': `rgb(${canvas.join(', ')})`, '--oc-ui-bg-workspace': '#0e1726',
    '--oc-ui-surface-data': '#142033', '--oc-ui-surface-elevated': '#19283b', '--oc-ui-surface-control': '#0e1726',
    '--oc-ui-overlay-scrim': 'rgba(0, 0, 0, 0.64)', '--oc-ui-text-primary': '#f1f5f9',
    '--oc-ui-text-secondary': '#c0cddd', '--oc-ui-text-muted': '#a3b4c9', '--oc-ui-text-placeholder': '#93a5ba',
    '--oc-ui-accent': effectiveAccent, '--oc-ui-on-accent': darkContrast >= whiteContrast ? '#07131b' : '#ffffff',
    '--oc-ui-accent-hover': effectiveAccent, '--oc-ui-accent-subtle': rgba(effectiveAccent, .12),
    '--oc-ui-selection-fill': rgba(effectiveAccent, .16), '--oc-ui-focus-ring': '#8be4ef',
    '--oc-ui-border-default': 'rgba(182, 204, 226, 0.18)', '--oc-ui-border-control': '#637c99',
    '--oc-ui-divider': 'rgba(182, 204, 226, 0.12)', '--oc-ui-success': '#6ee7b7', '--oc-ui-warning': '#fcd34d',
    '--oc-ui-error': '#fda4af', '--oc-ui-info': '#93c5fd', '--oc-ui-glass-tint': '14, 23, 38',
    '--oc-ui-glass-shell-alpha': backdropSupported && !off ? String(1 - values.shellTransparency / 100) : '1',
    '--oc-ui-glass-shell-blur': `${backdropSupported && !off ? Math.min(values.blurPx, light ? 8 : 24) : 0}px`,
    '--oc-ui-glass-saturation': `${off ? 100 : values.saturationPct}%`, '--oc-ui-glass-rim': `rgba(255, 255, 255, ${values.rimStrength / 100})`,
    '--oc-ui-glass-sheen': off ? '0' : light ? '0.03' : '0.06',
    '--oc-ui-shadow-floating': off ? 'none' : `0 16px 40px rgba(0, 0, 0, ${values.shadowStrength / (light ? 200 : 100)})`,
    '--oc-ui-shadow-shell': off ? 'none' : `0 8px 28px rgba(0, 0, 0, ${values.shadowStrength / (light ? 350 : 175)}), inset 0 1px 0 rgba(255,255,255,.10)`,
    '--oc-ui-ambient-strength': ambientEnabled ? String(values.ambientStrength / 100) : '0',
  };
  return { presetId: preset.id, legacyThemeId: preset.isLegacy ? preset.id : safe.legacyThemeId, isLegacy: preset.isLegacy,
    variables, requestedAccent: values.accent, effectiveAccent, accentAdjusted: values.accent !== effectiveAccent,
    ambientEnabled, ambientMotion: ambientEnabled && safe.ambientMotion && !reducedMotion, effects: safe.effects };
}
