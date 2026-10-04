/**
 * Continuous timeline zoom (pixels per second).
 *
 * The old zoom was an index into five fixed steps. The value is now a plain
 * px/s number clamped to [MIN, MAX]: Ctrl+wheel scales it smoothly around the
 * cursor, while the toolbar buttons and +/- keys still hop between presets,
 * and "fit" can land on any value in between.
 */
import { DEFAULT_ZOOM_INDEX, ZOOM_LEVELS } from './timelineMath.js';

// The old five steps, plus two deeper ones: 400 px/s draws a frame tick every
// 13 px and 800 px/s every 27 px (frame ticks need >= 6 px, i.e. >= 180 px/s).
export const ZOOM_PRESETS = Object.freeze([...ZOOM_LEVELS, 400, 800]);
export const MIN_PX_PER_SEC = ZOOM_PRESETS[0];
export const MAX_PX_PER_SEC = ZOOM_PRESETS[ZOOM_PRESETS.length - 1];
export const DEFAULT_PX_PER_SEC = ZOOM_LEVELS[DEFAULT_ZOOM_INDEX] ?? 50;

// A preset counts as "reached" within 1%, so float drift from wheel zooming
// never makes a button press land on the step the view already shows.
const PRESET_TOLERANCE = 0.01;

export function clampPxPerSec(px) {
  const n = Number(px);
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_PX_PER_SEC;
  return Math.min(MAX_PX_PER_SEC, Math.max(MIN_PX_PER_SEC, n));
}

/** Next preset strictly beyond `px` in direction `dir` (+1 in, -1 out), clamped. */
export function stepZoomPreset(px, dir) {
  const cur = clampPxPerSec(px);
  if (dir > 0) {
    return ZOOM_PRESETS.find((p) => p > cur * (1 + PRESET_TOLERANCE)) ?? MAX_PX_PER_SEC;
  }
  if (dir < 0) {
    for (let i = ZOOM_PRESETS.length - 1; i >= 0; i--) {
      if (ZOOM_PRESETS[i] < cur * (1 - PRESET_TOLERANCE)) return ZOOM_PRESETS[i];
    }
    return MIN_PX_PER_SEC;
  }
  return cur;
}

/**
 * The toolbar's "N / count" position for `px`: the nearest preset on a log
 * scale, but only the real ends report index 0 or count-1, so a zoom button is
 * never disabled while there is still room to zoom that way.
 */
export function zoomPresetIndex(px) {
  const cur = clampPxPerSec(px);
  const last = ZOOM_PRESETS.length - 1;
  if (cur <= MIN_PX_PER_SEC * (1 + PRESET_TOLERANCE)) return 0;
  if (cur >= MAX_PX_PER_SEC * (1 - PRESET_TOLERANCE)) return last;
  let best = 0;
  let bestDist = Infinity;
  ZOOM_PRESETS.forEach((p, i) => {
    const d = Math.abs(Math.log(cur / p));
    if (d < bestDist) { bestDist = d; best = i; }
  });
  return Math.min(last - 1, Math.max(1, best));
}

/**
 * Multiplicative zoom factor for one wheel event. Mouse notches (|deltaY|
 * ~100) give ~1.22x per notch; trackpad pinches send many small deltas and
 * scale smoothly. Line/page delta modes are converted to pixels first.
 */
export function wheelZoomFactor(deltaY, deltaMode = 0) {
  const unit = deltaMode === 1 ? 16 : deltaMode === 2 ? 400 : 1;
  const dy = Number(deltaY) * unit;
  if (!Number.isFinite(dy) || dy === 0) return 1;
  return Math.min(2, Math.max(0.5, Math.exp(-dy * 0.002)));
}

/**
 * scrollLeft that keeps the time under the cursor fixed across a zoom.
 * `anchorX` is the cursor's x inside the scroll viewport, `gutter` the
 * left inset (px) of time 0 inside the scrolled content.
 */
export function scrollLeftForAnchor({ pxPerSec, nextPxPerSec, scrollLeft, anchorX, gutter = 0 }) {
  if (!(pxPerSec > 0) || !(nextPxPerSec > 0)) return Math.max(0, scrollLeft || 0);
  const t = Math.max(0, ((scrollLeft || 0) + anchorX - gutter) / pxPerSec);
  return Math.max(0, t * nextPxPerSec + gutter - anchorX);
}

/** px/s that shows `duration` seconds across `usableWidth` px, clamped. */
export function fitPxPerSec(usableWidth, duration) {
  if (!(usableWidth > 0) || !(duration > 0)) return null;
  return clampPxPerSec(usableWidth / duration);
}

/**
 * Map continuous px/s to a [0, 1] slider fraction on a logarithmic scale.
 */
export function pxPerSecToSlider(px) {
  const cur = clampPxPerSec(px);
  const logMin = Math.log(MIN_PX_PER_SEC);
  const logMax = Math.log(MAX_PX_PER_SEC);
  return Math.max(0, Math.min(1, (Math.log(cur) - logMin) / (logMax - logMin)));
}

/**
 * Map a [0, 1] slider fraction back to px/s on a logarithmic scale.
 */
export function sliderToPxPerSec(frac) {
  const f = Math.max(0, Math.min(1, Number(frac) || 0));
  const logMin = Math.log(MIN_PX_PER_SEC);
  const logMax = Math.log(MAX_PX_PER_SEC);
  return clampPxPerSec(Math.exp(logMin + f * (logMax - logMin)));
}

/**
 * Format zoom as a user-friendly percentage (100% at DEFAULT_PX_PER_SEC = 50 px/s).
 */
export function zoomPercentageLabel(px) {
  const cur = clampPxPerSec(px);
  const pct = Math.round((cur / DEFAULT_PX_PER_SEC) * 100);
  return `${pct}%`;
}

