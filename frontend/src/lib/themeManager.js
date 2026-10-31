/**
 * Theme Manager for OmniCut Studio
 * Supports 4 premier theme presets:
 * 1. glassmorphism (Apple visionOS / Pulse Hub Spatial UI)
 * 2. obsidian (Pro Studio Dark NLE)
 * 3. cyberpunk (Electric Neon Horizon)
 * 4. slate (Minimal Frosted Slate)
 */

export const STORAGE_KEY_THEME = 'omnicut_ui_theme';
export const STORAGE_KEY_ORBS = 'omnicut_ambient_orbs_enabled';

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

export function initTheme() {
  const themeId = getStoredTheme();
  applyTheme(themeId);
  const orbsEnabled = getStoredOrbsEnabled(themeId);
  return { themeId, orbsEnabled };
}
