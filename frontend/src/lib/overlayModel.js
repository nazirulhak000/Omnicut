// One shape for every piece of text burned into the frame.
//
// Mirrored from scripts/overlay_model.py -- which is where the reasoning
// lives. The canvas preview reads this table and the ASS writer reads that
// one; a field that exists on only one side is a preview that lies about the
// render, so the two are compared in tests/test_preview_render_parity.py.

import {
  DEFAULT_HOOK_TEMPLATE,
  TIER_KEYS,
  resolveHookStyle,
} from './hookStyles.js';

// Canvas is 540x960, the render is 1080x1920 -- exactly half. Anything in
// render pixels is halved for the preview (parity rule 2.3). `outline_px` is
// the documented exception: ASS grows an outline outward only while
// ctx.strokeText centres its stroke, so half the same number lands outside
// and both sides carry the identical figure (parity rule 2.6).
export const CANVAS_SCALE = 0.5;

// Base font size as a fraction of frame width. A banner and a body line have
// different natural sizes, so the ratio rides on the overlay rather than the
// look, and size_pct stays a number the user recognises.
export const HOOK_FS_RATIO = 0.065;

// Mirrors HOOK_NAMEPLATE_DEFAULT_SEC in scripts/overlay_model.py: the default
// nameplate length (was 5.0 until M1, when the hook line took the first 1.8 s).
export const HOOK_NAMEPLATE_DEFAULT_SEC = 3.0;
export const TEXT_FS_RATIO = 0.0463;

// Ask a face for a weight it does not ship and the browser synthesises one
// heavier than the render's, so a family that only has a regular cut says 400.
//
// The last three are the ids the editor stores rather than family names -- a
// text overlay saves fontName 'IBMPlex', not 'IBM Plex Sans Thai'.
export const FONT_WEIGHTS = {
  Kanit: 700,
  Prompt: 700,
  'Chakra Petch': 700,
  Anuphan: 400,
  'IBM Plex Sans Thai': 700,
  'Bai Jamjuree': 700,
  Krub: 700,
  Mitr: 700,
  Pridi: 700,
  Sarabun: 700,
  Mali: 700,
  Itim: 400,
  Chonburi: 400,
  IBMPlex: 700,
  'Noto Sans Thai': 400,
  NotoSansThai: 400,
};
export const DEFAULT_FONT_WEIGHT = 700;

export const TEXT_LOOK_FIELDS = [
  'font', 'size_pct', 'color',
  'outline_color', 'outline_px',
  'shadow', 'pill', 'upper', 'skew',
  'bold', 'italic', 'underline',
  'accent_color',
];

// A dark copy of the glyphs, offset down-right. Offsets are RENDER pixels --
// halve for canvas. The two engines draw it differently, so the blur will
// never match exactly; position, size and colour must (parity rule 5).
export const DEFAULT_SHADOW = { dx: 1.5, dy: 2.0, blur: 4.0, color: '#000000' };
export const HOOK_SHADOW = { dx: 2.0, dy: 3.0, blur: 7.0, color: '#000000' };

// Pill padding is a multiple of the line's own font size, so the pill follows
// the text when the size changes. The hook's flat 12px is carried over as the
// ratio it was at 100% -- its pill grows with its tier now instead of staying
// put. Radius caps in render pixels.
export const PILL_PAD_X_EM = 0.6;
export const PILL_PAD_Y_EM = 0.35;
export const PILL_RADIUS_MAX_PX = 28.0;
export const HOOK_PILL_PAD_X_EM = 0.342;
export const HOOK_PILL_PAD_Y_EM = 0.171;

export const DEFAULT_TEXT_LOOK = {
  font: 'Kanit',
  size_pct: 100,
  color: '#FFFFFF',
  outline_color: '#000000',
  // The TextOverlayMain style's own Outline. The canvas used to derive its
  // own number from the font size (max(2, fs*0.12) -- 3px where the render
  // burned 5), so the preview under-drew every text overlay's outline.
  outline_px: 5.0,
  shadow: DEFAULT_SHADOW,
  pill: null,
  upper: false,
  skew: 0.0,
  bold: false,
  italic: false,
  underline: false,
  accent_color: null,
};

// bgStyle + badgeColor collapse into one pill object.
export const LEGACY_BG_STYLES = {
  none: null,
  pill: { fill: 'rgba(0, 0, 0, 0.65)', border: null },
  badge_red: { fill: '#FE2C55', border: null },
  badge_yellow: { fill: '#FFE600', border: null },
  badge_cyan: { fill: 'rgba(37, 244, 238, 0.2)', border: '#25F4EE' },
};

// A text overlay's single `anim` was always an entrance; the exit was a
// hardcoded 150ms fade it had no way to name. That fade runs over the last
// 150ms, which is exactly what the banner's `out: fade` already did, so the
// two exits were the same picture under two spellings and only the entrance
// needed reconciling.
export const DEFAULT_ANIM = {
  in: 'snap', loop: 'none', out: 'fade', accent: 'none', stagger: false, word_stagger_ms: 0,
};
export const HOOK_ANIM = {
  in: 'bounce', loop: 'pulse', out: 'fade', accent: 'underline', stagger: true, reveal: 'simultaneous',
};

// Three entrance names meant different animations on the two sides -- a text
// overlay's `pop` snapped 1.25x down in 70ms while the banner's overshot to
// 1.18x over 200ms. Both are worth keeping, so the text ones are renamed
// rather than merged, and every existing project keeps the motion it had.
// The user picks from Thai labels, so these ids never surface.
export const LEGACY_TEXT_ANIM = {
  pop: 'snap',         // 1.25 -> 1.0 over 70ms
  zoom: 'pop_zoom',    // 1.45 -> 1.0 over 100ms, alpha over 70ms
  stamp: 'stamp',      // 1.65 -> 1.0 over 80ms
  fade: 'quick_fade',  // alpha over 150ms
  slide: 'rise',       // dy 40 -> 0 over 200ms, alpha with it
  none: 'none',
};
export const LEGACY_TEXT_ANIM_REVERSE = Object.fromEntries(
  Object.entries(LEGACY_TEXT_ANIM).map(([k, v]) => [v, k]),
);

// Which banner look a clip's narration tone asks for. The tone is already
// chosen per angle by the script AI and carried through angleToForm.js, so a
// first render can dress its banner to match the voice instead of landing on
// the same 'tech' every time. Whatever the user picks by hand still wins.
export const AD_TONE_TO_TEMPLATE = {
  commercial_expert: 'tech',
  commercial_hype: 'bold_pop',
  commercial_aesthetic: 'plain',
  commercial_premium: 'clean',
  tech_journalism_calm: 'tech',
};

export const STYLE_PRESET_TO_TEMPLATE = {
  viral_punch: 'b1_viral_red',
  clean_tech_review: 'b2_clean_yellow',
  tech_product_showcase: 'b2_tech_cyan',
  smooth_showcase: 'b1_smooth_mint',
  premium_minimal: 'b2_premium_gold',
  flash_deal: 'b1_deal_orange',
  pain_punch: 'b1_pain_pink',
  tech_compare: 'b2_compare_blue',
  smart_hack: 'b1_hack_lime',
  niche_focus: 'b2_niche_purple',
};

export function templateForAdTone(adTone) {
  return AD_TONE_TO_TEMPLATE[adTone || ''] || DEFAULT_HOOK_TEMPLATE;
}

export function templateForStylePreset(stylePreset) {
  return STYLE_PRESET_TO_TEMPLATE[stylePreset || ''] || null;
}

// The banner's block is anchored to the top of the frame: ASS MarginV 180 of
// 1920, canvas y 90 of 960 (top Safe Zone 9.4%) -- the same fraction, per parity rule 2.8.
export const HOOK_TOP_Y = 180.0 / 1920.0;
export const TEXT_POSITIONS = { top: 0.20, middle: 0.50, bottom: 0.72 };

// Which edge of the block `y` names, which is what an ASS Alignment says.
// Parity rule 2.8: a multi-line block anchored at the wrong edge slides by
// half its own height, so this cannot default to "centre everything".
export const ANCHOR_TOP = 'top';       // ASS Alignment 8 -- the banner
export const ANCHOR_MIDDLE = 'middle'; // ASS Alignment 5 -- text overlays
export const ASS_ALIGNMENT = { [ANCHOR_TOP]: 8, [ANCHOR_MIDDLE]: 5 };

// Past this many wrapped lines the block shrinks (to a floor of 0.7) rather
// than growing unbounded. The banner needs it because it shares the top of
// the frame with the sticker badge; a text overlay is placed by hand and has
// no neighbour to crowd, so it says null and keeps the size it was given.
export const HOOK_COMFORTABLE_LINES = 4;

// ASS Layer: lower numbers paint first, so this is z-order. The banner sat on
// layers 1-2 and the text overlays on 3-4, which is why a text overlay has
// always covered the banner rather than the other way round. Captions are
// layer 0 and paint under both.
export const HOOK_LAYER = 2;
export const TEXT_LAYER = 4;

/**
 * Renderer policy shared by the canonical hook/text overlay model.
 *
 * The drawing pass is one function, but these switches are intentional
 * behavior differences: hooks use the banner motion defaults and layout
 * shrink rule, while text overlays own word staggering and keep their size.
 * Keeping the differences as data makes the dispatch auditable without
 * pretending the two visual policies are identical.
 */
export const OVERLAY_RENDER_PROFILES = Object.freeze({
  hook: Object.freeze({
    kind: 'hook',
    defaultAnim: HOOK_ANIM,
    supportsWordStagger: false,
    clearLayout: true,
    boundsType: 'hook',
  }),
  text: Object.freeze({
    kind: 'text',
    defaultAnim: DEFAULT_ANIM,
    supportsWordStagger: true,
    clearLayout: false,
    boundsType: 'text_overlay',
  }),
});

/**
 * Returns the Canvas renderer policy while preserving the old fallback:
 * unknown frontend overlay kinds were rendered using the text path.
 */
export function overlayRenderProfile(overlay) {
  return overlay?.kind === 'hook'
    ? OVERLAY_RENDER_PROFILES.hook
    : OVERLAY_RENDER_PROFILES.text;
}

// The model tier's colour is null in the template table, meaning "use the
// caption accent colour". null also means "inherit" everywhere else here, so
// the two are spelled apart: the accent is a value, not an absence.
export const ACCENT_COLOR = 'accent';

/**
 * An overlay's look plus one tier's overrides, flattened. Absent and null
 * both mean "keep the base" -- same contract as resolveHookStyle().
 * Mirrors resolve_look() in scripts/overlay_model.py.
 */
export function resolveLook(base, override) {
  const look = { ...DEFAULT_TEXT_LOOK };
  for (const source of [base || {}, override || {}]) {
    for (const field of TEXT_LOOK_FIELDS) {
      const value = source[field];
      if (value !== null && value !== undefined) look[field] = value;
    }
  }
  return look;
}

export function fontWeight(font) {
  return FONT_WEIGHTS[font || ''] || DEFAULT_FONT_WEIGHT;
}

export function baseFsRatio(kind) {
  return kind === 'hook' ? HOOK_FS_RATIO : TEXT_FS_RATIO;
}

function pillFromLegacy(bgStyle, badgeColor) {
  const style = bgStyle || 'none';
  const preset = LEGACY_BG_STYLES[style];
  if (preset) {
    const fill = badgeColor && !['#FE2C55', '#FFE600', '#25F4EE'].includes(badgeColor)
      ? badgeColor : preset.fill;
    return { fill, border: preset.border, pad_x_em: PILL_PAD_X_EM, pad_y_em: PILL_PAD_Y_EM };
  }
  if (style === 'none' && badgeColor) {
    return { fill: badgeColor, border: null, pad_x_em: PILL_PAD_X_EM, pad_y_em: PILL_PAD_Y_EM };
  }
  return null;
}

function hookTierLook(resolvedFont, tier) {
  const tierFont = tier.font || resolvedFont;
  const pill = tier.pill
    ? { fill: tier.pill, border: null, pad_x_em: HOOK_PILL_PAD_X_EM, pad_y_em: HOOK_PILL_PAD_Y_EM }
    : null;
  return {
    font: tierFont,
    size_pct: tier.size_pct,
    color: tier.color === null || tier.color === undefined ? ACCENT_COLOR : tier.color,
    outline_color: tier.outline_color,
    outline_px: Number(tier.outline_px),
    shadow: { ...HOOK_SHADOW },
    pill,
    upper: !!tier.upper,
    bold: !!tier.bold,
    italic: !!tier.italic,
    underline: !!tier.underline,
  };
}

/**
 * The three banner scalars as one overlay. Returns null when all three tiers
 * are empty -- an overlay that says nothing is simply not in the array, which
 * is what `showHookHeader` used to be for.
 */
export function hookOverlayFromLegacy(brand, model, label, duration, motion, colors, style) {
  const texts = [brand || '', model || '', label || ''];
  if (!texts.some((t) => t.trim())) return null;
  const template = (style || {}).template || DEFAULT_HOOK_TEMPLATE;
  const resolved = resolveHookStyle(template, style || {}, colors || {});
  const dur = Number(duration) || HOOK_NAMEPLATE_DEFAULT_SEC;
  return {
    id: 'ovl_hook',
    kind: 'hook',
    template: resolved.template,
    start: 0.0,
    end: Math.round(dur * 1000) / 1000,
    position: 'top',
    anchor: ANCHOR_TOP,
    comfortable_lines: HOOK_COMFORTABLE_LINES,
    layer: HOOK_LAYER,
    x: 0.5,
    y: HOOK_TOP_Y,
    base_fs_ratio: HOOK_FS_RATIO,
    look: { font: resolved.font, shadow: { ...HOOK_SHADOW } },
    tiers: TIER_KEYS.map((key, i) => ({
      text: texts[i],
      look: hookTierLook(resolved.font, resolved.tiers[key]),
    })),
    anim: { ...HOOK_ANIM, ...(resolved.motion || {}), ...(motion || {}) },
    // The banner is what the top gradient was always for; it is a property of
    // this overlay now rather than a second reading of hook_duration.
    scrim: true,
    sfx: null,
    sfx_label: null,
    template_id: null,
    hidden: false,
  };
}

/** One flat text_overlays[] entry as an overlay with a single tier. */
export function textOverlayFromLegacy(item) {
  const scale = item.scale === null || item.scale === undefined ? 1.0 : Number(item.scale);
  const legacyAnim = item.anim || 'pop';
  return {
    id: item.id || 'ovl_text',
    kind: 'text',
    template: null,
    start: Number(item.start) || 0.0,
    end: Number(item.end) || 0.0,
    position: item.position || 'middle',
    anchor: ANCHOR_MIDDLE,
    comfortable_lines: null,
    layer: TEXT_LAYER,
    x: item.x === undefined ? null : item.x,
    y: item.y === undefined ? null : item.y,
    base_fs_ratio: TEXT_FS_RATIO,
    look: {
      // fontName was written by the inspector and read by nobody: the canvas
      // took the caption's font and the ASS writer never looked. It is the
      // look's font now, on the one path that draws anything.
      font: item.fontName || item.font || DEFAULT_TEXT_LOOK.font,
      size_pct: Math.round(scale * 100),
      color: item.color || DEFAULT_TEXT_LOOK.color,
      outline_color: DEFAULT_TEXT_LOOK.outline_color,
      outline_px: DEFAULT_TEXT_LOOK.outline_px,
      shadow: { ...DEFAULT_SHADOW },
      pill: pillFromLegacy(item.bgStyle, item.badgeColor),
      upper: false,
    },
    tiers: [{ text: item.text || '', look: {} }],
    anim: { ...DEFAULT_ANIM, in: LEGACY_TEXT_ANIM[legacyAnim] || legacyAnim },
    scrim: false,
    sfx: item.sfx || null,
    sfx_label: item.sfxLabel || item.sfx_label || null,
    template_id: item.templateId || item.template_id || null,
    hidden: false,
  };
}

function manifestGet(manifest, key, fallback) {
  if (manifest[key] !== null && manifest[key] !== undefined) return manifest[key];
  const value = (manifest.render_params || {})[key];
  return value === null || value === undefined ? fallback : value;
}

/**
 * Every overlay in a project, whichever era it was saved in. A manifest that
 * already carries `overlays` is returned as-is; otherwise the banner scalars
 * and text_overlays[] are read and converted. Legacy keys are read forever
 * and never written again, so an old project opens without anyone touching
 * the file on disk. Mirrors migrate_to_overlays() in scripts/overlay_model.py.
 */
export function migrateToOverlays(manifest) {
  const data = manifest || {};
  const existing = manifestGet(data, 'overlays', null);
  if (Array.isArray(existing)) return existing.map((o) => ({ ...o }));

  const overlays = [];
  const hook = hookOverlayFromLegacy(
    manifestGet(data, 'hook_brand', '') || '',
    manifestGet(data, 'hook_model', '') || '',
    manifestGet(data, 'hook_label', '') || '',
    manifestGet(data, 'hook_duration', HOOK_NAMEPLATE_DEFAULT_SEC) || HOOK_NAMEPLATE_DEFAULT_SEC,
    manifestGet(data, 'hook_motion', null) || {},
    manifestGet(data, 'hook_colors', null) || {},
    manifestGet(data, 'hook_style', null) || {},
  );
  if (hook) overlays.push(hook);
  const rawText = manifestGet(data, 'text_overlays', null) || [];
  if (Array.isArray(rawText)) {
    for (const item of rawText) {
      if (item && typeof item === 'object') overlays.push(textOverlayFromLegacy(item));
    }
  }
  return overlays;
}


/**
 * Best-effort brand/model split from a free-text product name -- assumes the
 * common "Brand Model" word order (Logitech Wave Keys, Apple iPhone 15).
 * Wrong for names that do not lead with a brand, so it only ever pre-fills a
 * banner tier that is still empty: a wrong guess costs one edit, never a
 * silent wrong render.
 *
 * It used to live in NewClipPanel and fire from the product-name field's
 * onBlur, which meant it never ran at all on the product flow -- angleToForm
 * sets that field in code, and code does not blur.
 */
export function guessBrandModel(productName) {
  const trimmed = String(productName || '').trim();
  if (!trimmed) return { brand: '', model: '' };
  const parts = trimmed.split(/\s+/);
  if (parts.length <= 1) return { brand: trimmed, model: '' };
  return { brand: parts[0], model: parts.slice(1).join(' ') };
}

// ------------------------------------------------------------ constructors
// Both sides make overlays: the editor when the user adds one, the render API
// when a first generate arrives with nothing but the three banner strings.

export function newTextOverlay({
  id, text = '', start = 0, end = 2.5, look = null,
  animIn = null, sfx = null, sfxLabel = null, templateId = null,
}) {
  return {
    id,
    kind: 'text',
    template: null,
    start: Math.round(start * 1000) / 1000,
    end: Math.round(end * 1000) / 1000,
    position: 'middle',
    anchor: ANCHOR_MIDDLE,
    comfortable_lines: null,
    layer: TEXT_LAYER,
    x: 0.5,
    y: 0.5,
    base_fs_ratio: TEXT_FS_RATIO,
    look: { ...DEFAULT_TEXT_LOOK, ...(look || {}) },
    tiers: [{ text, look: {} }],
    anim: { ...DEFAULT_ANIM, ...(animIn ? { in: animIn } : {}) },
    scrim: false,
    sfx,
    sfx_label: sfxLabel,
    template_id: templateId,
    hidden: false,
  };
}

/** The banner as an overlay, dressed in `template`. null when it is blank. */
export function newHookOverlay({
  brand = '', model = '', label = '', template = null, start = 0, duration = HOOK_NAMEPLATE_DEFAULT_SEC,
}) {
  const overlay = hookOverlayFromLegacy(
    brand, model, label, duration, null, null,
    { template: template || DEFAULT_HOOK_TEMPLATE },
  );
  if (overlay && start) {
    overlay.start = Math.round(start * 1000) / 1000;
    overlay.end = Math.round((start + duration) * 1000) / 1000;
  }
  return overlay;
}

/**
 * One tier's look changed, returned as a whole new overlay. A tier holds only
 * the fields it overrides, so writing one field never freezes the rest of the
 * template into place -- switching template afterwards still moves everything
 * the user did not touch.
 */
export function withTierLook(overlay, tierIdx, patch) {
  const tiers = (overlay.tiers || []).map((tier, i) => (
    i === tierIdx ? { ...tier, look: { ...(tier.look || {}), ...patch } } : tier
  ));
  return { ...overlay, tiers };
}

/** A tier's text changed. */
export function withTierText(overlay, tierIdx, text) {
  const tiers = (overlay.tiers || []).map((tier, i) => (
    i === tierIdx ? { ...tier, text } : tier
  ));
  return { ...overlay, tiers };
}

/** The tier fields that differ from what `template` would have produced. */
function tierOverrides(overlay, template) {
  const texts = TIER_KEYS.map((_, i) => ((overlay.tiers || [])[i] || {}).text || 'x');
  const baseline = hookOverlayFromLegacy(
    texts[0], texts[1], texts[2], 1, null, null, { template },
  );
  return TIER_KEYS.map((_, i) => {
    const current = ((overlay.tiers || [])[i] || {}).look || {};
    const base = ((baseline && baseline.tiers[i]) || {}).look || {};
    const kept = {};
    for (const field of TEXT_LOOK_FIELDS) {
      if (field === 'shadow') continue;
      if (field === 'font') {
        if (current.font && current.font !== base.font) {
          kept.font = current.font;
        }
        continue;
      }
      // An absent field means "inherit", which is not an override.
      if (current[field] === undefined || current[field] === null) continue;
      if (JSON.stringify(current[field]) !== JSON.stringify(base[field])) {
        kept[field] = current[field];
      }
    }
    return kept;
  });
}

/** Set master font for hook, updating tiers that follow the master font. */
export function withHookFont(overlay, newFont) {
  if (!overlay || !newFont) return overlay;
  const prevMaster = overlay.look?.font || 'Kanit';
  const updatedTiers = (overlay.tiers || []).map((tier) => {
    const currentTierFont = tier.look?.font;
    const shouldUpdateTier = !currentTierFont || currentTierFont === prevMaster;
    return {
      ...tier,
      look: {
        ...(tier.look || {}),
        font: shouldUpdateTier ? newFont : currentTierFont,
      },
    };
  });
  return {
    ...overlay,
    look: {
      ...(overlay.look || {}),
      font: newFont,
    },
    tiers: updatedTiers,
  };
}

/**
 * A banner re-dressed in another template. A tier field counts as the user's
 * only if it differs from what the template it was set under would have
 * produced; those carry across and everything else takes the new look. That
 * is what switching template was always documented to do -- the old
 * `setHookStyle({ template })` threw every edit away instead.
 */
export function withHookTemplate(overlay, template) {
  const texts = TIER_KEYS.map((_, i) => ((overlay.tiers || [])[i] || {}).text || '');
  const duration = Math.max(0.1, (overlay.end || 0) - (overlay.start || 0));
  const fresh = hookOverlayFromLegacy(
    texts[0], texts[1], texts[2], duration, null, null, { template },
  );
  if (!fresh) return overlay;
  const kept = tierOverrides(overlay, overlay.template || DEFAULT_HOOK_TEMPLATE);
  return {
    ...overlay,
    template: fresh.template,
    look: { ...fresh.look },
    anim: { ...fresh.anim },
    tiers: fresh.tiers.map((tier, i) => {
      const overrides = { ...(kept[i] || {}) };
      delete overrides.size_pct;
      return {
        text: texts[i],
        look: { ...tier.look, ...overrides },
      };
    }),
  };
}

/** Drops every tier override, back to the template's own look. */
export function withHookTemplateReset(overlay) {
  const texts = TIER_KEYS.map((_, i) => ((overlay.tiers || [])[i] || {}).text || '');
  const duration = Math.max(0.1, (overlay.end || 0) - (overlay.start || 0));
  const fresh = hookOverlayFromLegacy(
    texts[0], texts[1], texts[2], duration, null, null,
    { template: overlay.template || DEFAULT_HOOK_TEMPLATE },
  );
  if (!fresh) return overlay;
  return { ...overlay, look: { ...fresh.look }, anim: { ...fresh.anim }, tiers: fresh.tiers };
}

/** Which tier fields the user has moved off the template, for the UI's dots. */
export function overriddenTierFields(overlay) {
  if (overlay.kind !== 'hook') return [];
  return tierOverrides(overlay, overlay.template || DEFAULT_HOOK_TEMPLATE)
    .map((fields) => Object.keys(fields));
}

/**
 * A card from the text-template gallery, as an overlay. The gallery's entries
 * are still written in the flat legacy vocabulary, so this goes through the
 * same conversion a saved project does -- one mapping, not two that can drift.
 * A template may also carry a whole `look`, which wins over the flat fields.
 */
export function overlayFromTextTemplate(tpl, { id, start, end }) {
  const overlay = textOverlayFromLegacy({
    id,
    text: tpl.text,
    start,
    end,
    position: 'middle',
    x: 0.5,
    y: 0.5,
    scale: tpl.scale,
    color: tpl.color,
    fontName: tpl.fontName,
    bgStyle: tpl.bgStyle,
    badgeColor: tpl.badgeColor,
    anim: tpl.anim,
    sfx: tpl.sfx,
    sfxLabel: tpl.sfxLabel,
    templateId: tpl.id,
  });
  if (tpl.look) overlay.look = { ...overlay.look, ...tpl.look };
  if (tpl.anim_channels) overlay.anim = { ...overlay.anim, ...tpl.anim_channels };
  return overlay;
}

/** The same card applied to an overlay that already exists, keeping its text. */
export function restyleOverlayFromTemplate(overlay, tpl) {
  const dressed = overlayFromTextTemplate(tpl, {
    id: overlay.id, start: overlay.start, end: overlay.end,
  });
  return {
    ...overlay,
    look: dressed.look,
    anim: dressed.anim,
    sfx: dressed.sfx,
    sfx_label: dressed.sfx_label,
    template_id: dressed.template_id,
  };
}
