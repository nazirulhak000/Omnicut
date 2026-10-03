// Options and duration rules for the timeline's transition popover. Both read
// from timelineMath.js (the catalog the preview draws and the parity test
// pins to video_editor.py XFADE_TRANSITIONS) so the popover never offers a
// shorter or different list than the renderer can execute.

import { TRANSITIONS, MAX_TRANSITION_DURATION, FADE_DURATION } from './timelineMath.js';

// == video_editor.py normalize_transitions `max(0.1, dur)` and
// timelineMath.js transitionOverlap's lower clamp.
export const MIN_TRANSITION_DURATION = 0.1;
export const TRANSITION_DURATION_STEP = 0.05;
export const TRANSITION_DURATION_PRESETS = Object.freeze([0.3, 0.5, 0.8, 1.0]);

/** Every transition the renderer supports, in catalog order. */
export const TRANSITION_POPOVER_OPTIONS = TRANSITIONS;

/** Clamp to the renderer's accepted range (no snapping). */
export function boundTransitionDuration(value) {
  const raw = Number(value);
  const base = Number.isFinite(raw) ? raw : FADE_DURATION;
  return Math.min(MAX_TRANSITION_DURATION, Math.max(MIN_TRANSITION_DURATION, base));
}

/** Clamp to the renderer's accepted range and snap to the slider step. */
export function clampTransitionDuration(value) {
  const snapped = Math.round(boundTransitionDuration(value) / TRANSITION_DURATION_STEP) * TRANSITION_DURATION_STEP;
  return Math.round(boundTransitionDuration(snapped) * 100) / 100;
}

/** Text shown next to the slider, e.g. "0.35s" -- the value the render uses. */
export function formatTransitionDuration(value) {
  return `${boundTransitionDuration(value).toFixed(2)}s`;
}
