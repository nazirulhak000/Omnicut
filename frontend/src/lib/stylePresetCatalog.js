/**
 * Frontend catalog for project-level editorial styles.
 *
 * Every entry mirrors a real renderer policy in scripts/style_motion_policy.py.
 * Unknown or legacy values still fall back to the Golden Master preset.
 */
export const DEFAULT_STYLE_PRESET = 'clean_tech_review';
// Keep One Click on the original Golden Master contract. The richer presets
// remain available as explicit user choices, but must never silently alter a
// render just because the UI was updated.
export const DEFAULT_ONE_CLICK_STYLE_PRESET = DEFAULT_STYLE_PRESET;

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
    hookTemplate: 'b1_viral_red',
    hookBadge: 'T1 · FLICKER',
    hookColor: '#FE2C55',
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
    hookTemplate: 'b2_clean_yellow',
    hookBadge: 'T1 · SHAKE',
    hookColor: '#FFE600',
  },
  {
    id: 'tech_product_showcase',
    label: 'Tech Product Showcase',
    labelTh: 'รีวิวสินค้าไอทีแบบภาพเด่น',
    description: 'โชว์สินค้าเต็มเฟรม ใช้ Title ใหญ่สีขาวตัดเหลือง Motion พอดี และเปลี่ยนช็อตเฉพาะจังหวะสำคัญ',
    motion: 'Hero push/pan ทุกช็อตที่เหมาะสม',
    transitions: 'Hard cut เป็นหลัก + Slide/Circle เฉพาะจุด',
    audio: 'Voice นำหน้า พร้อม SFX ตอนเปิดกล่อง/ชี้จุดเด่น/CTA',
    accent: '#FFCC33',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 'b2_tech_cyan',
    hookBadge: 'T1 · WAVE',
    hookColor: '#25F4EE',
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
    hookTemplate: 'b1_smooth_mint',
    hookBadge: 'T1 · LIGHTSWEEP',
    hookColor: '#00F2AA',
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
    hookTemplate: 'b2_premium_gold',
    hookBadge: 'T1 · WAVE',
    hookColor: '#E6C24A',
  },
  {
    id: 'flash_deal',
    label: 'Flash Deal',
    labelTh: 'โปรไฟลุก ดีลเด็ด',
    description: 'จังหวะเร็ว กระตุ้นความสนใจและจำกัดเวลา เหมาะกับคลิปโปรโมชั่นและส่วนลดพิเศษ',
    motion: 'Motion เร็ว เน้นกระตุ้นการมอง',
    transitions: 'สลับ Hard cut กับ Slide เร็ว',
    audio: 'Voice นำหน้า พร้อม SFX เพิ่มความตื่นเต้น',
    accent: '#FF7A00',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 'b1_deal_orange',
    hookBadge: 'T1 · FLICKER',
    hookColor: '#FF7A00',
  },
  {
    id: 'pain_punch',
    label: 'Pain Punch',
    labelTh: 'ชี้ปัญหา กระตุกอารมณ์',
    description: 'เปิดด้วยปัญหาที่คนดูเจอ ขยี้จุดเจ็บและตัดเข้าทางแก้ปัญหาอย่างชัดเจน',
    motion: 'Motion สั่นเน้นย้ำจุดปัญหา',
    transitions: 'Hard cut ฉับไว ตัดเข้าไฮไลต์',
    audio: 'Voice นำหน้า พร้อม SFX จุดสะดุดใจ',
    accent: '#FF2E93',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 'b1_pain_pink',
    hookBadge: 'T1 · SHAKE',
    hookColor: '#FF2E93',
  },
  {
    id: 'tech_compare',
    label: 'Tech Comparison',
    labelTh: 'เทียบสเปก วิเคราะห์ชัด',
    description: 'เน้นความน่าเชื่อถือ เปรียบเทียบของเดิมกับของใหม่ เห็นความต่างชัดเจน',
    motion: 'Motion นิ่งและแม่นยำ',
    transitions: 'Hard cut และ Wipe ซ้ายขวา',
    audio: 'Voice คมชัด SFX อารมณ์เทคโนโลยี',
    accent: '#3B82F6',
    status: '#FFE600',
    neutral: '#FFFFFF',
    hookTemplate: 'b2_compare_blue',
    hookBadge: 'T1 · WAVE',
    hookColor: '#3B82F6',
  },
  {
    id: 'smart_hack',
    label: 'Smart Hack',
    labelTh: 'ทริกลึก เคล็ดลับป้ายยา',
    description: 'บอกวิธีใช้งานหรือทริกที่คนส่วนใหญ่ไม่รู้ ดูเพลินและน่าแชร์ต่อ',
    motion: 'Motion กวาดสายตาแบบ Step-by-step',
    transitions: 'Slide นุ่มนวล เชื่อมแต่ละทริก',
    audio: 'Voice สบายๆ เป็นกันเอง SFX กวาดเสียง',
    accent: '#84CC16',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 'b1_hack_lime',
    hookBadge: 'T1 · LIGHTSWEEP',
    hookColor: '#84CC16',
  },
  {
    id: 'niche_focus',
    label: 'Niche Focus',
    labelTh: 'เจาะกลุ่ม เฉพาะสาย',
    description: 'เน้นคุณสมบัติเฉพาะที่ตอบโจทย์กลุ่มเป้าหมายเฉพาะทางอย่างตรงจุด',
    motion: 'Motion เจาะลึกเฉพาะฟังก์ชัน',
    transitions: 'Hard cut สลับ Zoom เฉพาะส่วน',
    audio: 'Voice นิ่ง มั่นใจ โทนผู้เชี่ยวชาญ',
    accent: '#A855F7',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 'b2_niche_purple',
    hookBadge: 'T1 · WAVE',
    hookColor: '#A855F7',
  },
];

export const STYLE_PRESET_CATALOG = Object.freeze(
  STYLE_PRESETS.map((preset) => Object.freeze({ ...preset })),
);

const STYLE_PRESET_IDS = new Set(STYLE_PRESET_CATALOG.map((preset) => preset.id));

/** 1-to-1 default mapping between 10 script angles and 10 editorial style presets. */
export const ANGLE_TO_DEFAULT_STYLE = Object.freeze({
  stop_scroll: 'viral_punch',
  fomo_deal: 'flash_deal',
  pain_point: 'pain_punch',
  spec_review: 'clean_tech_review',
  comparison: 'tech_compare',
  unboxing: 'tech_product_showcase',
  life_hack: 'smart_hack',
  niche_target: 'niche_focus',
  longterm_review: 'smooth_showcase',
  math_value: 'premium_minimal',
});

/** Return recommended default style preset for an angle id, or fallback default. */
export function getRecommendedStyleForAngle(angleId) {
  const normalizedAngle = String(angleId || '').trim().toLowerCase();
  return ANGLE_TO_DEFAULT_STYLE[normalizedAngle] || DEFAULT_STYLE_PRESET;
}

/** Return a renderer-supported id, falling back safely for old/unknown data. */
export function normalizeStylePreset(value) {
  const key = String(value ?? '').trim().toLowerCase();
  return STYLE_PRESET_IDS.has(key) ? key : DEFAULT_STYLE_PRESET;
}

export function getStylePreset(value) {
  const id = normalizeStylePreset(value);
  return STYLE_PRESET_CATALOG.find((preset) => preset.id === id) || STYLE_PRESET_CATALOG[0];
}

/** Get matched hook template id for the given style preset. */
export function getHookTemplateForStyle(stylePreset) {
  const preset = getStylePreset(stylePreset);
  return preset?.hookTemplate || 'b2_clean_yellow';
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
