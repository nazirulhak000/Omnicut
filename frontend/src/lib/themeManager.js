/**
 * Theme Manager for OmniCut Studio
 * Supports 4 premier theme presets & Ultra-Realistic Glass Finetuning:
 * 1. glassmorphism (Apple visionOS / Pulse Hub Spatial UI)
 * 2. obsidian (Pro Studio Dark NLE)
 * 3. cyberpunk (Electric Neon Horizon)
 * 4. slate (Minimal Frosted Slate)
 */

export const STORAGE_KEY_THEME = 'omnicut_ui_theme';
export const STORAGE_KEY_ORBS = 'omnicut_ambient_orbs_enabled';
export const STORAGE_KEY_GLASS_CONFIG = 'omnicut_glass_config';

export const THEME_PRESETS = [
  {
    id: 'glassmorphism',
    name: 'Ultra-Realistic Glassmorphism',
    styleTag: 'แนะนำ / visionOS',
    description: 'กระจกใสสมจริง หักเหแสงผ่าน Ambient Orbs 3 จุดบนพื้น OLED Deep Space ล้ำสมัย',
    orbsDefault: true,
    bgClass: 'bg-[#030509]',
    accentColors: ['#00f2fe', '#f59e0b', '#818cf8'],
    features: 'กระจกใส Refractive Glass · แสง Orbs 3 จุด · ขอบเรืองแสงนุ่มนวล'
  },
  {
    id: 'obsidian',
    name: 'Obsidian Pro Dark',
    styleTag: 'ตัดต่อโปร / NLE Studio',
    description: 'ดำสนิท คมเข้ม สไตล์ DaVinci Resolve & Premiere Pro ไร้แสงสะท้อน สบายตาสำหรับการตัดต่อ',
    orbsDefault: false,
    bgClass: 'bg-[#07090e]',
    accentColors: ['#38bdf8', '#a855f7', '#64748b'],
    features: 'พื้นหลังทึบ OLED · ไร้แสงกวนสายตา · คอนทราสต์สูง คมชัด'
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk Neon Horizon',
    styleTag: 'นีออนจัดจ้าน / ไฮเทค',
    description: 'เรืองแสงนีออนไฟฟ้า Cyan (#00f2fe) และ Rose (#ec4899) สะท้อนขอบแก้วชัดเจน มีพลังสดใส',
    orbsDefault: true,
    bgClass: 'bg-[#05050d]',
    accentColors: ['#00f2fe', '#ec4899', '#f59e0b'],
    features: 'ขอบนีออนเรืองแสง · สีคู่ตรงข้าม Cyan-Rose · พลังงานสูง'
  },
  {
    id: 'slate',
    name: 'Minimal Frosted Slate',
    styleTag: 'มินิมอล / คลีนตา',
    description: 'กระจกฝ้าซอฟต์มินิมอล โทนสีเทา Slate นุ่มตา สะอาด เรียบง่าย ไร้การรบกวนสายตา',
    orbsDefault: false,
    bgClass: 'bg-[#0a0f1d]',
    accentColors: ['#94a3b8', '#38bdf8', '#475569'],
    features: 'กระจกฝ้าซอฟต์แมตต์ · โทนเทา Slate สบายตา · ดีไซน์มินิมอลสะอาดตา'
  }
];

export const VALID_THEME_IDS = THEME_PRESETS.map(t => t.id);
export const DEFAULT_THEME_ID = 'glassmorphism';

export const DEFAULT_GLASS_CONFIG = {
  opacity: 16,    // % (0.16)
  blur: 14,       // px
  glare: 95,      // % (0.95)
  orbsGlow: 75,   // % (0.75)
  saturate: 210   // % (210%)
};

export const GLASS_PRESETS = [
  {
    id: 'crystal',
    name: 'กระจกใสคริสตัล (Pulse Hub Pure)',
    desc: 'ใสแจ๋ว คมกริบ แสง Orbs นีออนทะลุเนื้อกระจกเต็มที่ สไตล์ Pulse Hub ต้นฉบับ',
    config: { opacity: 14, blur: 12, glare: 98, orbsGlow: 85, saturate: 220 }
  },
  {
    id: 'visionos',
    name: 'กระจกฝ้า Spatial (Apple visionOS)',
    desc: 'กระจกฝ้าละมุน สไตล์ visionOS Spatial UI นุ่มนวล สมดุล',
    config: { opacity: 24, blur: 18, glare: 85, orbsGlow: 70, saturate: 195 }
  },
  {
    id: 'smoky',
    name: 'กระจกรมควัน (Deep Smoky Glass)',
    desc: 'โทนเข้ม มืดขรึม สะท้อนแสงเงาหรูหรา คอนทราสต์สูง',
    config: { opacity: 38, blur: 14, glare: 90, orbsGlow: 50, saturate: 170 }
  }
];

export function normalizeThemeId(themeId) {
  if (typeof themeId === 'string' && VALID_THEME_IDS.includes(themeId.trim().toLowerCase())) {
    return themeId.trim().toLowerCase();
  }
  return DEFAULT_THEME_ID;
}

export function getStoredTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_THEME);
    return normalizeThemeId(stored);
  } catch {
    return DEFAULT_THEME_ID;
  }
}

export function getStoredOrbsEnabled(themeId = null) {
  const effectiveThemeId = normalizeThemeId(themeId || getStoredTheme());
  try {
    const raw = localStorage.getItem(STORAGE_KEY_ORBS);
    if (raw !== null) {
      return raw === 'true';
    }
  } catch {}
  const preset = THEME_PRESETS.find(t => t.id === effectiveThemeId);
  return preset ? preset.orbsDefault : true;
}

export function applyTheme(themeId) {
  const normalized = normalizeThemeId(themeId);
  try {
    localStorage.setItem(STORAGE_KEY_THEME, normalized);
  } catch {}

  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.setAttribute('data-theme', normalized);
  }
  return normalized;
}

export function setOrbsEnabled(enabled) {
  const boolVal = Boolean(enabled);
  try {
    localStorage.setItem(STORAGE_KEY_ORBS, boolVal ? 'true' : 'false');
  } catch {}
  return boolVal;
}

export function getStoredGlassConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_GLASS_CONFIG);
    if (raw) {
      const parsed = JSON.parse(raw) ?? {};
      return {
        opacity: Number.isFinite(parsed.opacity) ? Math.min(Math.max(parsed.opacity, 5), 70) : DEFAULT_GLASS_CONFIG.opacity,
        blur: Number.isFinite(parsed.blur) ? Math.min(Math.max(parsed.blur, 2), 36) : DEFAULT_GLASS_CONFIG.blur,
        glare: Number.isFinite(parsed.glare) ? Math.min(Math.max(parsed.glare, 10), 100) : DEFAULT_GLASS_CONFIG.glare,
        orbsGlow: Number.isFinite(parsed.orbsGlow) ? Math.min(Math.max(parsed.orbsGlow, 10), 100) : DEFAULT_GLASS_CONFIG.orbsGlow,
        saturate: Number.isFinite(parsed.saturate) ? Math.min(Math.max(parsed.saturate, 100), 280) : DEFAULT_GLASS_CONFIG.saturate,
      };
    }
  } catch {}
  return { ...DEFAULT_GLASS_CONFIG };
}

export function applyGlassConfig(config) {
  config = config ?? {};
  const safeConfig = {
    opacity: Number.isFinite(config.opacity) ? Math.min(Math.max(config.opacity, 5), 70) : DEFAULT_GLASS_CONFIG.opacity,
    blur: Number.isFinite(config.blur) ? Math.min(Math.max(config.blur, 2), 36) : DEFAULT_GLASS_CONFIG.blur,
    glare: Number.isFinite(config.glare) ? Math.min(Math.max(config.glare, 10), 100) : DEFAULT_GLASS_CONFIG.glare,
    orbsGlow: Number.isFinite(config.orbsGlow) ? Math.min(Math.max(config.orbsGlow, 10), 100) : DEFAULT_GLASS_CONFIG.orbsGlow,
    saturate: Number.isFinite(config.saturate) ? Math.min(Math.max(config.saturate, 100), 280) : DEFAULT_GLASS_CONFIG.saturate,
  };

  try {
    localStorage.setItem(STORAGE_KEY_GLASS_CONFIG, JSON.stringify(safeConfig));
  } catch {}

  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.style.setProperty('--glass-opacity', (safeConfig.opacity / 100).toFixed(2));
    document.documentElement.style.setProperty('--glass-blur', `${safeConfig.blur}px`);
    document.documentElement.style.setProperty('--glare-opacity', (safeConfig.glare / 100).toFixed(2));
    document.documentElement.style.setProperty('--orbs-opacity', (safeConfig.orbsGlow / 100).toFixed(2));
    document.documentElement.style.setProperty('--glass-saturate', `${safeConfig.saturate}%`);
  }
  return safeConfig;
}

export function resetGlassConfig() {
  return applyGlassConfig(DEFAULT_GLASS_CONFIG);
}

export function initTheme() {
  const themeId = getStoredTheme();
  applyTheme(themeId);
  const orbsEnabled = getStoredOrbsEnabled(themeId);
  const glassConfig = getStoredGlassConfig();
  applyGlassConfig(glassConfig);
  return { themeId, orbsEnabled, glassConfig };
}
