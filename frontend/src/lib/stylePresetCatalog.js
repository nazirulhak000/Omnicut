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
    description: 'แกนกลางของสาย Punch: ตัดเร็ว กล้องซูมและส่ายทุกช็อต Slide ถี่ เหมาะกับ Hook และคลิปขายสินค้า',
    motion: 'Push + Pan ทุกช็อตที่ยาวพอ',
    transitions: 'Slide ทุก 2 รอยต่อ · Circle ทุก 6 รอยต่อ ที่เหลือ Hard cut',
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
    description: 'ภาพชัด จังหวะพอดี ใช้ motion เฉพาะช็อตที่ควรเด่น และตัดกระชับขึ้นในช่วง Hook',
    motion: 'Motion แบบพอดี เฉพาะช็อตสลับกัน',
    transitions: 'Hard cut เป็นหลัก · เปลี่ยนช็อตทุกประมาณ 5 รอยต่อ',
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
    description: 'โชว์สินค้าเต็มเฟรม ใช้ Title ใหญ่สีขาวตัดเหลือง กล้องส่ายกว้างอย่างสม่ำเสมอเปิดรายละเอียดทีละจุด',
    motion: 'Pan กว้างทุกช็อต + Push เบา ๆ',
    transitions: 'Hard cut เป็นหลัก · Slide ต่อทิศทางกล้องทุก 3 รอยต่อ',
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
    description: 'ลดการเคลื่อนไหว ตัดช้าและนิ่ง ใช้ Fade เป็นระยะ และคุมสีทองสำหรับสินค้าพรีเมียม',
    motion: 'Motion เบา เว้นพื้นที่ให้สินค้า',
    transitions: 'Hard cut เป็นหลัก · Fade ทุกประมาณ 6 รอยต่อ',
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
    description: 'เร่งด้วยจังหวะตัด: ช็อตสั้นที่สุด Hook แน่นที่สุด กล้องนิ่งกว่า พลังมาจากการตัดไม่ใช่การซูม',
    motion: 'กล้องขยับเบาสลับช็อต ให้จังหวะตัดเป็นตัวเด่น',
    transitions: 'Slide เร็วทุก 2 รอยต่อ ที่เหลือ Hard cut',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
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
    description: 'เปิดด้วยปัญหาที่คนดูเจอ ซูมเข้าหนักตอนขยี้จุดเจ็บ ตัดช้ากว่า Flash Deal ให้ประโยคปัญหาค้างให้ได้ยินก่อน',
    motion: 'ซูมเข้าแรงทุกช็อต (Push ลึก แทบไม่ส่าย) กระแทกแล้วชะลอ',
    transitions: 'Slide ทุก 3 รอยต่อ · Circle ทุก 6 รอยต่อ ที่เหลือ Hard cut',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
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
    description: 'เน้นความน่าเชื่อถือ เปรียบเทียบของเดิมกับของใหม่ จังหวะตัดสม่ำเสมอ สลับ Wipe กับ Slide ให้เห็นความต่าง',
    motion: 'Pan กว้างสลับช็อต จังหวะสม่ำเสมอ',
    transitions: 'Hard cut เป็นหลัก · Wipe และ Slide สลับกันทุก 3 รอยต่อ',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
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
    description: 'บอกวิธีใช้งานหรือทริกทีละขั้น ตัดคมแบบ Hard cut กล้องสะกิดสั้น ๆ เข้าจังหวะทุกขั้น ดูเพลินและน่าแชร์ต่อ',
    motion: 'กล้องสะกิดสั้นเร็วทุกช็อต (ease-out) ไล่ดูทีละขั้น',
    transitions: 'Hard cut เป็นหลัก · Slide สั้น ๆ ทุก 4 รอยต่อ',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
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
    description: 'เน้นคุณสมบัติเฉพาะที่ตอบโจทย์กลุ่มเฉพาะ ซูมเข้าลึกและค้างภาพนานให้อ่านฟังก์ชันทัน',
    motion: 'Push-in ลึกทุก 2 ช็อต แทบไม่ส่าย ค้างภาพนานขึ้น',
    transitions: 'Hard cut เป็นหลัก · Circle (เปิดวงกลม) ทุก 4 รอยต่อ',
    audio: 'Voice นำหน้า พร้อม SFX เฉพาะ event สำคัญ',
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

/**
 * Default style preset per script angle. Covers the 10 classic angles and
 * every IT angle key in scripts/it_angles.py. Must stay identical to
 * ANGLE_TO_DEFAULT_STYLE in scripts/batch_render.py (enforced by
 * tests/test_style_preset_consistency.py).
 */
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
  spec_compare: 'tech_compare',
  fake_vs_real: 'viral_punch',
  real_test: 'tech_product_showcase',
  spec_explained: 'niche_focus',
  dont_cheap_out: 'pain_punch',
  how_to_setup: 'smart_hack',
  worth_upgrade: 'premium_minimal',
});

/** Return recommended default style preset for an angle id, or fallback default. */
export function getRecommendedStyleForAngle(angleId) {
  const normalizedAngle = String(angleId || '').trim().toLowerCase();
  const baseAngle = normalizedAngle.replace(/_b\d+$/, '');
  return ANGLE_TO_DEFAULT_STYLE[normalizedAngle] || ANGLE_TO_DEFAULT_STYLE[baseAngle] || DEFAULT_STYLE_PRESET;
}

/** Batch picker value meaning "use each angle's recommended style". */
export const AUTO_STYLE_PRESET = 'auto';

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
