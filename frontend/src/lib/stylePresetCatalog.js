/**
 * Frontend catalog for project-level editorial styles.
 *
 * Every entry mirrors a real renderer policy in scripts/style_motion_policy.py.
 * Unknown or legacy values still fall back to the Golden Master preset.
 */
export const DEFAULT_STYLE_PRESET = 'clean_tech_review';
export const DEFAULT_ONE_CLICK_STYLE_PRESET = 'viral_punch';

const STYLE_PRESETS = [
  {
    id: 'viral_punch',
    label: 'Viral Punch',
    labelTh: 'ไวรัล กระชับ มีพลัง',
    description: 'ตัดเร็วขึ้น เพิ่มกล้องเคลื่อนและ Slide แบบคุมจังหวะ เหมาะกับ Hook และคลิปขายสินค้า',
    motion: 'Motion ทุกช็อตที่ยาวพอ',
    transitions: 'สลับ Hard cut กับ Slide · Stylized เฉพาะจังหวะ',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
    accent: '#FE2C55',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    recommended: true,
  },
  {
    id: DEFAULT_STYLE_PRESET,
    label: 'Clean Tech Review',
    labelTh: 'รีวิวเทคแบบคลีน',
    description: 'ภาพชัด มีจังหวะ และใช้ motion เฉพาะช็อตที่ควรเด่น',
    motion: 'Motion แบบพอดี',
    transitions: 'Hard cut เป็นหลัก',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
    // Renderer-facing tokens mirror scripts/style_motion_policy.py. accent is
    // the semantic hook/highlight colour; cyan remains the status colour.
    accent: '#FFE600',
    status: '#25F4EE',
    neutral: '#FFFFFF',
  },
  {
    id: 'smooth_showcase',
    label: 'Smooth Showcase',
    labelTh: 'โชว์สินค้าไหลลื่น',
    description: 'กล้องเคลื่อนนุ่มและใช้ Dissolve เป็นช่วง เหมาะกับ Demo, Detail และภาพสินค้าที่ต้องดูต่อเนื่อง',
    motion: 'Push และ Pan ช้าแบบต่อเนื่อง',
    transitions: 'Dissolve ทุกประมาณ 3 รอยต่อ',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
    accent: '#25F4EE',
    status: '#FFE600',
    neutral: '#FFFFFF',
  },
  {
    id: 'premium_minimal',
    label: 'Premium Minimal',
    labelTh: 'เรียบหรู จังหวะนิ่ง',
    description: 'ลดการเคลื่อนไหว ใช้ Fade เฉพาะจุดสำคัญ และคุมสีทองสำหรับสินค้าพรีเมียม',
    motion: 'Motion เบา เว้นพื้นที่ให้สินค้า',
    transitions: 'Hard cut เป็นหลัก · Fade เฉพาะ Section',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
    accent: '#E6C24A',
    status: '#D8C58A',
    neutral: '#FFFFFF',
  },
];

export const STYLE_PRESET_CATALOG = Object.freeze(
  STYLE_PRESETS.map((preset) => Object.freeze({ ...preset })),
);

const STYLE_PRESET_IDS = new Set(STYLE_PRESET_CATALOG.map((preset) => preset.id));

/** Return a renderer-supported id, falling back safely for old/unknown data. */
export function normalizeStylePreset(value) {
  const key = String(value ?? '').trim().toLowerCase();
  return STYLE_PRESET_IDS.has(key) ? key : DEFAULT_STYLE_PRESET;
}

export function getStylePreset(value) {
  const id = normalizeStylePreset(value);
  return STYLE_PRESET_CATALOG.find((preset) => preset.id === id) || STYLE_PRESET_CATALOG[0];
}

/**
 * Read both current and legacy manifest locations used by the pipeline.
 * `fallbackStyle` is accepted for callers that already have migrated state.
 */
export function stylePresetFromManifest(manifest = {}, fallbackStyle = {}) {
  const candidates = [
    manifest.style_preset,
    manifest.stylePreset,
    manifest.render_params?.style_preset,
    manifest.render_params?.stylePreset,
    manifest.style?.style_preset,
    manifest.style?.stylePreset,
    fallbackStyle?.style_preset,
    fallbackStyle?.stylePreset,
  ];
  const value = candidates.find((candidate) => candidate !== null && candidate !== undefined && candidate !== '');
  return normalizeStylePreset(value);
}

/** Attach the project-level style contract without changing other payload data. */
export function withStylePresetPayload(payload = {}, value) {
  return {
    ...payload,
    style_preset: normalizeStylePreset(value),
  };
}

/** Keep custom/catalog options unique by id while preserving their first order. */
export function uniqueStylePresets(options = STYLE_PRESET_CATALOG) {
  const seen = new Set();
  return options.filter((preset) => {
    const id = String(preset?.id ?? '').trim().toLowerCase();
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}
