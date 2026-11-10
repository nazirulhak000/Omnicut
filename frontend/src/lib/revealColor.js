/**
 * The colour of the word being spoken under a ghost reveal, taken from the
 * clip's own hook so the nameplate and the captions share one tone.
 *
 * Mirror of scripts/subtitle/reveal_color.py -- same thresholds, same walk over
 * the hook overlay's tiers. tests/fixtures/reveal_color_parity_cases.json runs
 * through both, so the preview lights the colour the export burns in.
 */
export const REVEAL_FALLBACK_COLOR = '#66FF00';

const HEX_RE = /^#[0-9A-Fa-f]{6}$/;
const MIN_SATURATION = 0.35;
const MIN_VALUE = 0.40;
const MIN_LUMINANCE = 0.15;
const LIFT_TOWARD_WHITE = 0.30;

const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

function isChromatic(hex) {
  const [r, g, b] = rgb(hex).map((c) => c / 255);
  const hi = Math.max(r, g, b);
  const lo = Math.min(r, g, b);
  if (hi < MIN_VALUE) return false;
  const saturation = hi === 0 ? 0 : (hi - lo) / hi;
  return saturation >= MIN_SATURATION;
}

function luminance(hex) {
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const [r, g, b] = rgb(hex).map((c) => lin(c / 255));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function lift(hex) {
  const mixed = rgb(hex).map((c) => Math.floor(c + (255 - c) * LIFT_TOWARD_WHITE + 0.5));
  return `#${mixed.map((c) => c.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
}

/** `hex` upper-cased, lifted toward white when too dark to read on video. */
export function legibleRevealHex(hex) {
  const out = String(hex).toUpperCase();
  return luminance(out) < MIN_LUMINANCE ? lift(out) : out;
}

/**
 * The hook's accent as `#RRGGBB`, or null when the hook has no coloured tier
 * (the caller then keeps the SOP green). Reads the first visible `kind: 'hook'`
 * overlay and takes its first chromatic tier colour in brand/model/label order.
 */
export function pickRevealHex(overlays) {
  for (const overlay of overlays || []) {
    if (!overlay || overlay.kind !== 'hook' || overlay.hidden) continue;
    for (const tier of overlay.tiers || []) {
      const colour = tier?.look?.color;
      if (typeof colour === 'string' && HEX_RE.test(colour) && isChromatic(colour)) {
        return legibleRevealHex(colour);
      }
    }
    return null;
  }
  return null;
}

/**
 * The colour the preview paints the active word: the hook's accent when sync is
 * on (default) and the hook has one, otherwise the SOP green.
 */
export function resolveRevealColor(overlays, sync = true) {
  return (sync !== false && pickRevealHex(overlays)) || REVEAL_FALLBACK_COLOR;
}
