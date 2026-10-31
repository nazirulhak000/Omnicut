import { THEME_PRESETS, DEFAULT_GLASS_CONFIG } from './themeManager.js';

export const UI_THEME_DEFAULTS = Object.freeze({
  accent: '#67d7e7', shellTransparency: 40, blurPx: 12, rimStrength: 24,
  shadowStrength: 35, ambientStrength: 14, saturationPct: 125, backgroundStrength: 0,
});

export const UI_THEME_CONTROL_RANGES = Object.freeze({
  shellTransparency: { min: 15, max: 55, step: 1, label: 'ความโปร่งของกระจก' },
  blurPx: { min: 0, max: 24, step: 1, label: 'ความฝ้าของกระจก' },
  rimStrength: { min: 0, max: 45, step: 1, label: 'ความเข้มขอบกระจก' },
  shadowStrength: { min: 0, max: 60, step: 1, label: 'ความลึกของเงา' },
  ambientStrength: { min: 0, max: 30, step: 1, label: 'แสงพื้นหลัง' },
  saturationPct: { min: 100, max: 160, step: 1, label: 'ความสดของกระจก' },
  backgroundStrength: { min: 0, max: 20, step: 1, label: 'ความเข้มพื้นหลัง' },
});

export const UI_THEME_PRESETS = Object.freeze([
  ...THEME_PRESETS.map(preset => ({
    ...preset, isLegacy: true, supportsGlass: false, defaults: { ...UI_THEME_DEFAULTS },
  })),
  {
    id: 'balanced-glass', name: 'Balanced Glass Workspace',
    description: 'กรอบกระจกและพื้นที่ทำงานอ่านง่าย สไตล์ Professional SaaS',
    isLegacy: false, supportsGlass: true, defaults: { ...UI_THEME_DEFAULTS },
  },
]);

export function createDefaultThemePreferences() {
  return {
    schemaVersion: 2, activePresetId: 'glassmorphism', legacyThemeId: 'glassmorphism',
    overridesByPreset: {}, effects: 'full', ambientMotion: false, customPresets: [],
    legacyGlassConfig: { ...DEFAULT_GLASS_CONFIG }, legacyOrbsEnabled: true,
  };
}
