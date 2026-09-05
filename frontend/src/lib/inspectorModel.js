import {
  LEGACY_BG_STYLES,
  PILL_PAD_X_EM,
  PILL_PAD_Y_EM,
} from './overlayModel.js';

/** Format seconds to mm:ss.tenths (e.g. 01:23.4) */
export function formatShortTime(sec) {
  if (sec == null || isNaN(sec)) return '00:00.0';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
}

/** General numeric clamp */
export function clampValue(value, min, max, fallback = min) {
  const num = parseFloat(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.max(min, Math.min(max, num));
}

/** Caption / text scale clamped between 0.4 and 2.2 */
export function clampScale(scale) {
  return clampValue(scale, 0.4, 2.2, 1.0);
}

/** Audio volume clamped between 0.0 and 1.0 */
export function clampVolume(volume) {
  return clampValue(volume, 0.0, 1.0, 1.0);
}

/** Clip playback speed clamped between 0.5 and 2.0 */
export function clampSpeed(speed) {
  return clampValue(speed, 0.5, 2.0, 1.0);
}

/** Rotation clamped to standard degrees [0, 360) */
export function clampRotation(deg) {
  const n = parseInt(deg, 10);
  if (!Number.isFinite(n)) return 0;
  return ((n % 360) + 360) % 360;
}

/** Freeze tail duration in seconds [0, 10.0] */
export function clampFreezeTail(sec) {
  return clampValue(sec, 0.0, 10.0, 0.0);
}

/** Video zoom factor [1.0, 3.0] */
export function clampZoom(zoom) {
  return clampValue(zoom, 1.0, 3.0, 1.0);
}

/** Video pan coordinate [-1.0, 1.0] */
export function clampPan(pan) {
  return clampValue(pan, -1.0, 1.0, 0.0);
}

/** Hook duration clamp [min, max] */
export function clampHookDuration(dur, min = 1.0, max = 8.0) {
  return clampValue(dur, min, max, 3.0);
}

/**
 * Background style pill preset mapper.
 */
export function pillForBgStyle(id) {
  const preset = LEGACY_BG_STYLES[id];
  if (!preset) return null;
  return { ...preset, pad_x_em: PILL_PAD_X_EM, pad_y_em: PILL_PAD_Y_EM };
}

/**
 * Identify background style preset from pill configuration.
 */
export function bgStyleOf(pill) {
  if (!pill) return 'none';
  for (const [id, preset] of Object.entries(LEGACY_BG_STYLES)) {
    if (preset && preset.fill === pill.fill && preset.border === pill.border) return id;
  }
  return 'none';
}
