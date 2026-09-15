// Hook Header looks, mirrored from scripts/hook_styles.py -- which is where the
// reasoning lives. The canvas preview reads this table and the ASS writer reads
// that one; a look that exists on only one side is a preview that lies about
// the render, so the two are compared field by field in
// tests/test_preview_render_parity.py.

// Colour null on the model tier means "use the caption accent colour", which
// is what the banner did before templates existed.
const ACCENT = null;

export const HOOK_TEMPLATES = {
  tech: {
    label_th: 'เทค — แบรนด์ขาว รุ่นสีจัด (ของเดิม)',
    font: 'Chakra Petch',
    tiers: {
      brand: { size_pct: 130, color: '#FFFFFF', outline_color: '#000000', outline_px: 6.0, upper: true, pill: null },
      model: { size_pct: 100, color: ACCENT, outline_color: '#000000', outline_px: 6.0, upper: false, pill: null },
      label: { size_pct: 58, color: '#E0E0E0', outline_color: '#000000', outline_px: 6.0, upper: false, pill: null },
    },
    motion: { in: 'bounce', loop: 'pulse', out: 'fade', accent: 'underline', stagger: true },
  },
  cute: {
    label_th: 'คิ้วท์ — ตัวขาว ขอบชมพูหนา',
    font: 'Itim',
    tiers: {
      brand: { size_pct: 118, color: '#FFFFFF', outline_color: '#E86BC7', outline_px: 10.0, upper: false, pill: null },
      model: { size_pct: 100, color: '#FFFFFF', outline_color: '#E86BC7', outline_px: 10.0, upper: false, pill: null },
      label: { size_pct: 62, color: '#FFFFFF', outline_color: '#E86BC7', outline_px: 0.0, upper: false, pill: '#E86BC7' },
    },
    motion: { in: 'bounce_soft', loop: 'wave', out: 'fade', accent: 'none', stagger: true },
  },
  bold_pop: {
    label_th: 'ป็อปตัวหนา — บานเย็น ขอบขาวหนา',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 122, color: '#E038D8', outline_color: '#FFFFFF', outline_px: 14.0, upper: false, pill: null },
      model: { size_pct: 110, color: '#FFE04C', outline_color: '#FFFFFF', outline_px: 12.0, upper: false, pill: null },
      label: { size_pct: 78, color: '#4CE0FF', outline_color: '#FFFFFF', outline_px: 10.0, upper: false, pill: null },
    },
    motion: { in: 'pop', loop: 'shake', out: 'zoom', accent: 'badge', stagger: true },
  },
  plain: {
    label_th: 'เรียบ — ขาวหนา ไม่มีขอบ',
    font: 'Prompt',
    tiers: {
      brand: { size_pct: 130, color: '#FFFFFF', outline_color: '#000000', outline_px: 0.0, upper: false, pill: null },
      model: { size_pct: 82, color: ACCENT, outline_color: '#000000', outline_px: 0.0, upper: false, pill: null },
      label: { size_pct: 58, color: '#C8C8C8', outline_color: '#000000', outline_px: 0.0, upper: false, pill: null },
    },
    motion: { in: 'fade', loop: 'none', out: 'fade', accent: 'none', stagger: false },
  },
  clean: {
    label_th: 'คลีน — ขาว ขอบดำบาง',
    font: 'Anuphan',
    tiers: {
      brand: { size_pct: 126, color: '#FFFFFF', outline_color: '#101010', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 100, color: '#FFFFFF', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 60, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'lightsweep', out: 'fade', accent: 'none', stagger: true },
  },
  flash_sale: {
    label_th: 'โปรไฟลุก — แดงสด ป้ายส้มเหลืองสะดุดตา',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 128, color: '#FFFFFF', outline_color: '#FE2C55', outline_px: 10.0, upper: true, pill: null },
      model: { size_pct: 112, color: '#FFE04C', outline_color: '#000000', outline_px: 8.0, upper: false, pill: null },
      label: { size_pct: 68, color: '#FFFFFF', outline_color: '#000000', outline_px: 0.0, upper: false, pill: '#FE2C55' },
    },
    motion: { in: 'pop', loop: 'flicker', out: 'slide', accent: 'badge', stagger: true },
  },
  neon_cyber: {
    label_th: 'นีออน — ฟ้าไซเบอร์ ขอบมืดเรืองแสง',
    font: 'Chakra Petch',
    tiers: {
      brand: { size_pct: 130, color: '#FFFFFF', outline_color: '#000000', outline_px: 8.0, upper: true, pill: null },
      model: { size_pct: 105, color: '#25F4EE', outline_color: '#000000', outline_px: 8.0, upper: false, pill: null },
      label: { size_pct: 64, color: '#FFE04C', outline_color: '#000000', outline_px: 4.0, upper: false, pill: null },
    },
    motion: { in: 'pop_zoom', loop: 'wave', out: 'glitch', accent: 'underline', stagger: true },
  },
  minimal_luxury: {
    label_th: 'ลักชัวรี — ทองขาว คมชัด สไตล์แบรนด์เนม',
    font: 'Prompt',
    tiers: {
      brand: { size_pct: 124, color: '#FFFFFF', outline_color: '#1A1A1A', outline_px: 4.0, upper: true, pill: null },
      model: { size_pct: 96, color: '#E6C24A', outline_color: '#1A1A1A', outline_px: 4.0, upper: false, pill: null },
      label: { size_pct: 60, color: '#C8C8C8', outline_color: '#1A1A1A', outline_px: 2.0, upper: false, pill: null },
    },
    motion: { in: 'quick_fade', loop: 'lightsweep', out: 'fade', accent: 'underline', stagger: true },
  },
  b1_viral_red: {
    label_th: 'B1 (แดง+กระพริบ) — Viral Punch',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 130, color: '#FE2C55', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 107, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 60, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'flicker', out: 'fade', accent: 'none', stagger: true },
  },
  b2_clean_yellow: {
    label_th: 'B2 (เหลือง+สั่น) — Clean Tech',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 221, color: '#FFE600', outline_color: '#0A0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 182, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 103, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'shake', out: 'fade', accent: 'none', stagger: true },
  },
  b2_tech_cyan: {
    label_th: 'B2 (ฟ้า+สั่นเบา) — Tech Showcase',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 207, color: '#25F4EE', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 170, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 95, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'wave', out: 'fade', accent: 'none', stagger: true },
  },
  b1_smooth_mint: {
    label_th: 'B1 (เขียวมิ้นต์+กวาดแสง) — Smooth',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 170, color: '#00F2AA', outline_color: '#0A0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 140, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 79, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'lightsweep', out: 'fade', accent: 'none', stagger: true },
  },
  b2_premium_gold: {
    label_th: 'B2 (ทอง+สั่นเบา) — Premium',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 207, color: '#E6C24A', outline_color: '#0A0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 170, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 95, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'wave', out: 'fade', accent: 'none', stagger: true },
  },
  b1_deal_orange: {
    label_th: 'B1 (ส้ม+กระพริบ) — Flash Deal',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 130, color: '#FF7A00', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 107, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 60, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'flicker', out: 'fade', accent: 'none', stagger: true },
  },
  b1_pain_pink: {
    label_th: 'B1 (ชมพู+สั่น) — Pain Punch',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 130, color: '#FF2E93', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 107, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 60, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'shake', out: 'fade', accent: 'none', stagger: true },
  },
  b2_compare_blue: {
    label_th: 'B2 (น้ำเงิน+คลื่น) — Tech Comparison',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 207, color: '#3B82F6', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 170, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 95, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'wave', out: 'fade', accent: 'none', stagger: true },
  },
  b1_hack_lime: {
    label_th: 'B1 (เขียวมะนาว+กวาดแสง) — Smart Hack',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 170, color: '#84CC16', outline_color: '#0A0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 140, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 79, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'lightsweep', out: 'fade', accent: 'none', stagger: true },
  },
  b2_niche_purple: {
    label_th: 'B2 (ม่วง+คลื่น) — Niche Focus',
    font: 'Kanit',
    tiers: {
      brand: { size_pct: 207, color: '#A855F7', outline_color: '#0B0A0A', outline_px: 3.0, upper: true, pill: null },
      model: { size_pct: 170, color: '#F7F7F7', outline_color: '#0A0A0A', outline_px: 3.0, upper: false, pill: null },
      label: { size_pct: 95, color: '#D0D0D0', outline_color: '#101010', outline_px: 3.0, upper: false, pill: null },
    },
    motion: { in: 'slide_up', loop: 'wave', out: 'fade', accent: 'none', stagger: true },
  },
};

export const DEFAULT_HOOK_TEMPLATE = 'tech';
export const TIER_KEYS = ['brand', 'model', 'label'];
export const TIER_FIELDS = ['size_pct', 'color', 'outline_color', 'outline_px', 'upper', 'pill'];

let customHookTemplatesRegistry = {};

export function registerCustomHookTemplates(templates) {
  customHookTemplatesRegistry = { ...(templates || {}) };
}

export function getCustomHookTemplates() {
  return customHookTemplatesRegistry;
}

export function getAllHookTemplates(extraCustom) {
  return { ...HOOK_TEMPLATES, ...customHookTemplatesRegistry, ...(extraCustom || {}) };
}

/**
 * A template plus its overrides, flattened into one style the drawing code can
 * use. Mirrors resolve_hook_style() in scripts/hook_styles.py.
 *
 * `colors` is the older per-tier colour map that the colour pickers still
 * write; it wins over both, so a project keeps the colours it was saved with.
 */
export function resolveHookStyle(template, overrides, colors, extraTemplates) {
  const allTemplates = { ...HOOK_TEMPLATES, ...customHookTemplatesRegistry, ...(extraTemplates || {}) };
  const base = allTemplates[template] || allTemplates[DEFAULT_HOOK_TEMPLATE] || HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE];
  const over = overrides || {};
  const overTiers = over.tiers || {};
  const picked = colors || {};

  const resolved = {
    template: allTemplates[template] ? template : DEFAULT_HOOK_TEMPLATE,
    font: over.font || base.font,
    tiers: {},
    motion: { ...(over.motion || base.motion || {}) },
  };
  for (const key of TIER_KEYS) {
    const tier = { ...base.tiers[key] };
    for (const field of TIER_FIELDS) {
      const value = (overTiers[key] || {})[field];
      if (value !== null && value !== undefined) tier[field] = value;
    }
    if ((overTiers[key] || {}).font) tier.font = overTiers[key].font;
    if (picked[key]) tier.color = picked[key];
    resolved.tiers[key] = tier;
  }
  return resolved;
}
