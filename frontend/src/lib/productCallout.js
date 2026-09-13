import {
  ANCHOR_MIDDLE,
  DEFAULT_ANIM,
  DEFAULT_TEXT_LOOK,
  LEGACY_TEXT_ANIM,
  TEXT_FS_RATIO,
  TEXT_LAYER,
} from './overlayModel.js';

/**
 * Semantic metadata for a product callout. The renderer deliberately still
 * receives kind: "text"; this module only makes the editorial contract
 * explicit and safe to persist.
 */
export const PRODUCT_CALLOUT_ROLE = 'product_callout';
export const PRODUCT_CALLOUT_TYPES = Object.freeze([
  'brand', 'model', 'feature', 'spec', 'price', 'proof', 'cta',
]);
export const PRODUCT_CALLOUT_ORIGINS = Object.freeze(['auto', 'manual', 'imported']);

export const PRODUCT_CALLOUT_DEFAULTS = Object.freeze({
  kind: 'text',
  role: PRODUCT_CALLOUT_ROLE,
  callout_type: 'feature',
  origin: 'manual',
  timing: Object.freeze({ start: 0, end: 2.5 }),
  x: 0.5,
  y: 0.5,
  position: 'middle',
  anchor: ANCHOR_MIDDLE,
  layer: TEXT_LAYER,
  base_fs_ratio: TEXT_FS_RATIO,
});

const POSITION_Y = Object.freeze({ top: 0.2, middle: 0.5, bottom: 0.72 });
const LEGACY_SOURCE = Object.freeze({ kind: 'legacy_text_overlay' });

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (isObject(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, clone(item)]));
  return value;
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function round(value, digits = 3) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null);
}

function normalizeTiming(input) {
  const raw = isObject(input.timing) ? input.timing : {};
  const start = numberOr(firstDefined(raw.start, input.start), 0);
  const defaultEnd = start + PRODUCT_CALLOUT_DEFAULTS.timing.end;
  const end = numberOr(firstDefined(raw.end, input.end), defaultEnd);
  return { start: round(start), end: round(end) };
}

function normalizeSource(input, legacy) {
  if (isObject(input.source)) return clone(input.source);
  if (typeof input.source === 'string' && input.source.trim()) {
    return { kind: 'asset', path: input.source.trim() };
  }
  return legacy ? clone(LEGACY_SOURCE) : { kind: 'manual' };
}

function normalizeLook(input, legacy) {
  const rawLook = isObject(input.look) ? input.look : {};
  const legacyScale = input.scale === undefined || input.scale === null
    ? undefined
    : numberOr(input.scale, 1) * 100;
  const look = {
    ...clone(DEFAULT_TEXT_LOOK),
    ...(legacy && legacyScale !== undefined ? { size_pct: Math.round(legacyScale) } : {}),
    ...(legacy && input.fontName ? { font: input.fontName } : {}),
    ...(legacy && input.font ? { font: input.font } : {}),
    ...(legacy && input.color ? { color: input.color } : {}),
    ...clone(rawLook),
  };
  if (look.size_pct !== undefined) look.size_pct = numberOr(look.size_pct, DEFAULT_TEXT_LOOK.size_pct);
  if (look.outline_px !== undefined) look.outline_px = numberOr(look.outline_px, DEFAULT_TEXT_LOOK.outline_px);
  look.shadow = isObject(look.shadow) ? clone(look.shadow) : clone(DEFAULT_TEXT_LOOK.shadow);
  if (look.pill !== null && look.pill !== undefined) look.pill = clone(look.pill);
  return look;
}

function legacyPill(input) {
  if (input.bgStyle === 'pill') return { fill: 'rgba(0, 0, 0, 0.65)', border: null };
  if (input.bgStyle === 'badge_red') return { fill: '#FE2C55', border: null };
  if (input.bgStyle === 'badge_yellow') return { fill: '#FFE600', border: null };
  if (input.bgStyle === 'badge_cyan') return { fill: 'rgba(37, 244, 238, 0.2)', border: '#25F4EE' };
  if (input.bgStyle === 'none' && input.badgeColor) return { fill: input.badgeColor, border: null };
  return null;
}

function normalizeAnim(input, legacy) {
  const raw = isObject(input.anim) ? input.anim : {};
  const legacyName = typeof input.anim === 'string' ? input.anim : null;
  const entrance = legacyName ? (LEGACY_TEXT_ANIM[legacyName] || legacyName) : undefined;
  return {
    ...clone(DEFAULT_ANIM),
    ...(legacy && entrance ? { in: entrance } : {}),
    ...clone(raw),
  };
}

function normalizeTiers(input) {
  if (Array.isArray(input.tiers)) {
    return input.tiers.map((tier) => ({
      text: typeof tier?.text === 'string' ? tier.text : String(tier?.text ?? ''),
      look: isObject(tier?.look) ? clone(tier.look) : {},
    }));
  }
  return [{
    text: typeof input.text === 'string' ? input.text : String(input.text ?? ''),
    look: {},
  }];
}

function isLegacyTextOverlay(input) {
  const kind = input.kind || input.type;
  return kind === undefined || kind === 'text' || kind === 'text_overlay';
}

function buildNormalized(input = {}, includeId = true) {
  const raw = isObject(input) ? input : {};
  const kind = raw.kind === 'text_overlay' || raw.type === 'text_overlay' ? 'text' : (raw.kind || 'text');
  const legacy = isLegacyTextOverlay(raw) && raw.role !== PRODUCT_CALLOUT_ROLE;
  const position = raw.position || PRODUCT_CALLOUT_DEFAULTS.position;
  const timing = normalizeTiming(raw);
  const lookInput = legacy && !raw.look && legacyPill(raw)
    ? { ...raw, look: { pill: legacyPill(raw) } }
    : raw;
  const normalized = {
    kind,
    role: raw.role || PRODUCT_CALLOUT_ROLE,
    callout_type: raw.callout_type || raw.calloutType || PRODUCT_CALLOUT_DEFAULTS.callout_type,
    origin: raw.origin || (legacy ? 'imported' : PRODUCT_CALLOUT_DEFAULTS.origin),
    source: normalizeSource(raw, legacy),
    timing,
    start: timing.start,
    end: timing.end,
    position,
    anchor: raw.anchor || ANCHOR_MIDDLE,
    layer: numberOr(raw.layer, TEXT_LAYER),
    x: numberOr(raw.x, 0.5),
    y: numberOr(raw.y, raw.y === null || raw.y === undefined ? (POSITION_Y[position] ?? 0.5) : 0.5),
    base_fs_ratio: numberOr(raw.base_fs_ratio, TEXT_FS_RATIO),
    tiers: normalizeTiers(raw),
    look: normalizeLook(lookInput, legacy),
    anim: normalizeAnim(raw, legacy),
    scrim: Boolean(raw.scrim),
    sfx: raw.sfx ?? null,
    sfx_label: raw.sfx_label ?? raw.sfxLabel ?? null,
    template_id: raw.template_id ?? raw.templateId ?? null,
    hidden: Boolean(raw.hidden),
  };

  if (includeId) normalized.id = typeof raw.id === 'string' && raw.id.trim()
    ? raw.id.trim()
    : createProductCalloutId(normalized);
  return normalized;
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (isObject(value)) {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

function stableStringify(value) {
  return JSON.stringify(stableValue(value));
}

function hashText(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36).padStart(7, '0');
}

/** Normalize a canonical callout or a legacy flat text overlay without mutation. */
export function normalizeProductCallout(input = {}) {
  return buildNormalized(input, true);
}

/** Create an id from semantic content, ignoring any supplied/non-semantic id. */
export function createProductCalloutId(input = {}) {
  return `callout-${hashText(stableStringify(buildNormalized(input, false)))}`;
}

/**
 * Validate the canonical contract. Errors are stable strings so callers can
 * show them directly or use them in deterministic tests.
 */
export function validateProductCallout(input) {
  const value = input;
  const errors = [];
  if (!isObject(value)) return { valid: false, errors: ['overlay must be an object'] };
  if (value.kind !== 'text') errors.push('kind must be text');
  if (value.role !== PRODUCT_CALLOUT_ROLE) errors.push(`role must be ${PRODUCT_CALLOUT_ROLE}`);
  if (!PRODUCT_CALLOUT_TYPES.includes(value.callout_type)) errors.push('callout_type is not allowed');
  if (!PRODUCT_CALLOUT_ORIGINS.includes(value.origin)) errors.push('origin is not allowed');
  if (!isObject(value.source)) errors.push('source must be an object');

  const timing = isObject(value.timing) ? value.timing : {};
  const start = Number(timing.start);
  const end = Number(timing.end);
  if (!Number.isFinite(start) || start < 0) errors.push('timing.start must be >= 0');
  if (!Number.isFinite(end) || end <= start) errors.push('timing.end must be greater than timing.start');
  if (Number(value.start) !== start || Number(value.end) !== end) errors.push('start/end must mirror timing');

  for (const axis of ['x', 'y']) {
    const coordinate = Number(value[axis]);
    if (!Number.isFinite(coordinate) || coordinate < 0 || coordinate > 1) {
      errors.push(`${axis} must be normalized between 0 and 1`);
    }
  }
  if (!Array.isArray(value.tiers) || value.tiers.length === 0) errors.push('tiers must contain at least one tier');
  else value.tiers.forEach((tier, index) => {
    if (!isObject(tier) || typeof tier.text !== 'string') errors.push(`tiers[${index}].text must be a string`);
    if (!isObject(tier?.look)) errors.push(`tiers[${index}].look must be an object`);
  });
  if (!isObject(value.look)) errors.push('look must be an object');
  else {
    if (typeof value.look.font !== 'string' || !value.look.font) errors.push('look.font must be a string');
    if (!Number.isFinite(Number(value.look.size_pct)) || Number(value.look.size_pct) <= 0) errors.push('look.size_pct must be > 0');
  }
  if (!isObject(value.anim)) errors.push('anim must be an object');
  else for (const key of ['in', 'loop', 'out']) if (typeof value.anim[key] !== 'string') errors.push(`anim.${key} must be a string`);
  return { valid: errors.length === 0, errors };
}

/** Serialize the normalized contract with sorted object keys for stable saves/ids. */
export function serializeProductCallout(input = {}) {
  return stableStringify(normalizeProductCallout(input));
}
