import {
  LEGACY_BG_STYLES,
  PILL_PAD_X_EM,
  PILL_PAD_Y_EM,
} from './overlayModel.js';
import { CAMERA_MOTION_LIMITS, MIN_CLIP_DURATION, generateSmartCameraKeyframes } from './timelineMath.js';

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

// == video_editor.py clip `speed` clamp (min(4.0, max(0.25, speed))).
export const MIN_CLIP_SPEED = 0.25;
export const MAX_CLIP_SPEED = 4.0;

/** Clip playback speed clamped between 0.25 and 4.0 (the range the render accepts) */
export function clampSpeed(speed) {
  return clampValue(speed, MIN_CLIP_SPEED, MAX_CLIP_SPEED, 1.0);
}

/** Typed speed: clamp to the render range and keep two decimals (1.25, not 1.2500001). */
export function normalizeSpeed(speed) {
  return Math.round(clampSpeed(speed) * 100) / 100;
}

/** Keep a numeric trim edit inside a playable source window. */
export function clampTrimStart(value, clip = {}, sourceDuration = 0) {
  const end = clip.trim_end ?? (sourceDuration > 0 ? sourceDuration : Infinity);
  return clampValue(value, 0, Math.max(0, end - MIN_CLIP_DURATION), 0);
}

export function clampTrimEnd(value, clip = {}, sourceDuration = 0) {
  if (value === '' || value === null) return null;
  const min = (Number(clip.trim_start) || 0) + MIN_CLIP_DURATION;
  const max = sourceDuration > 0 ? Math.max(min, sourceDuration) : Infinity;
  return clampValue(value, min, max, min);
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
  return clampValue(dur, min, max, 5.0);
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

// ───────────────────────── Clip camera motion (keyframes) ─────────────────────────
//
// The pipeline writes `keyframes: [{time, zoom, pan_x, pan_y}, ...]` on clips it
// builds, and preview + render both let a keyframe track beat the clip's static
// zoom / pan_x / pan_y (timelineMath.resolveClipTransforms,
// video_editor.resolve_clip_transforms). These helpers are what the Inspector
// uses to make that hidden override visible and removable.

const CAMERA_PROPS = Object.keys(CAMERA_MOTION_LIMITS);

/** Camera properties a keyframe point drives, in either keyframe vocabulary. */
function cameraPropsOfPoint(point) {
  if (!point || typeof point !== 'object') return [];
  if (!Number.isFinite(Number(point.time))) return [];
  const props = CAMERA_PROPS.filter(
    (prop) => point[prop] !== undefined && Number.isFinite(Number(point[prop])),
  );
  if (
    !props.length
    && CAMERA_PROPS.includes(point.property)
    && Number.isFinite(Number(point.value))
  ) {
    props.push(point.property);
  }
  return props;
}

/**
 * How much camera keyframing a clip carries. `points` counts keyframe points
 * that drive zoom/pan; `zoom` / `pan` say which static sliders they override.
 */
export function cameraKeyframeSummary(clip) {
  const tracks = { zoom: 0, pan_x: 0, pan_y: 0 };
  let points = 0;
  const list = Array.isArray(clip?.keyframes) ? clip.keyframes : [];
  for (const point of list) {
    const props = cameraPropsOfPoint(point);
    if (!props.length) continue;
    points += 1;
    props.forEach((prop) => { tracks[prop] += 1; });
  }
  return {
    points,
    tracks,
    zoom: tracks.zoom > 0,
    pan: tracks.pan_x > 0 || tracks.pan_y > 0,
  };
}

/** Keyframes with every zoom/pan point removed (anything else is kept). */
export function withoutCameraKeyframes(keyframes) {
  const list = Array.isArray(keyframes) ? keyframes : [];
  return list.filter((point) => cameraPropsOfPoint(point).length === 0);
}

/** Patch that drops a clip's camera motion so the static sliders apply again. */
export function clearCameraMotionPatch(clip) {
  return { keyframes: withoutCameraKeyframes(clip?.keyframes) };
}

/**
 * Patch for the framing reset: static zoom/pan back to default, and the camera
 * keyframes that would otherwise keep overriding them removed. `keyframes` is
 * only written when there is something to remove.
 */
export function framingResetPatch(clip) {
  const patch = { zoom: undefined, pan_x: undefined, pan_y: undefined };
  if (cameraKeyframeSummary(clip).points > 0) {
    patch.keyframes = withoutCameraKeyframes(clip.keyframes);
  }
  return patch;
}

/**
 * Seconds a clip actually plays (after trim and speed, without the freeze tail).
 * Same span timelineMath.motionTimeAt clamps motion time to -- keyframe times
 * live on this clock, not on source-file time.
 */
export function clipPlayedDuration(clip, sourceDuration = 0) {
  const speed = Number(clip?.speed) || 1;
  const end = Number(clip?.trim_end ?? sourceDuration ?? 0);
  const span = (end - (Number(clip?.trim_start) || 0)) / speed;
  return Number.isFinite(span) ? Math.max(0, span) : 0;
}

export const SLOW_ZOOM_PRESETS = Object.freeze([
  { id: 'in10', label: 'ซูมเข้า 10%', direction: 'in', percent: 0.10 },
  { id: 'in15', label: 'ซูมเข้า 15%', direction: 'in', percent: 0.15 },
  { id: 'out10', label: 'ซูมออก 10%', direction: 'out', percent: 0.10 },
]);

/**
 * Two-point slow zoom across the whole played clip:
 * `[{time: 0, zoom: z0}, {time: playedDuration, zoom: z1}]`. The start is the
 * clip's current static zoom; a push-in ends `percent` above it, a pull-out
 * starts there and settles on it. Zoom stays inside the camera limits.
 * Returns null when there is no real move to make (clip too short, or already
 * at the maximum zoom).
 */
export function buildSlowZoomKeyframes(clip, sourceDuration, { direction = 'in', percent = 0.1 } = {}) {
  const duration = clipPlayedDuration(clip, sourceDuration);
  if (duration < MIN_CLIP_DURATION) return null;
  const { min, max } = CAMERA_MOTION_LIMITS.zoom;
  const base = clampValue(clip?.zoom ?? 1, min, max, 1);
  const far = clampValue(base * (1 + percent), min, max, base);
  if (Math.abs(far - base) < 0.005) return null;
  const [from, to] = direction === 'out' ? [far, base] : [base, far];
  const round = (value, places) => Math.round(value * 10 ** places) / 10 ** places;
  // The end point's easing shapes the move (timelineMath CAMERA_EASINGS):
  // ease_in_out starts and settles softly instead of a constant-speed crawl.
  return [
    { time: 0, zoom: round(from, 4) },
    { time: round(duration, 3), zoom: round(to, 4), easing: 'ease_in_out' },
  ];
}

/**
 * Keyframes for the clip after a slow-zoom preset: the preset replaces the
 * clip's zoom/pan motion (a leftover pipeline pan would fight a manual zoom),
 * anything that is not camera motion stays.
 */
export function slowZoomPatch(clip, sourceDuration, preset) {
  const moves = buildSlowZoomKeyframes(clip, sourceDuration, preset);
  if (!moves) return null;
  return { keyframes: [...withoutCameraKeyframes(clip?.keyframes), ...moves] };
}

// ───────────────────────── Clip slider undo + apply to all ─────────────────────────

/** One key per clip and field, so a drag is one undo step and clips never merge. */
export function clipSliderCoalesceKey(clipId, field) {
  return `clip:${clipId}:${field}`;
}

/**
 * Looks that "use this on every clip" may copy. Keyframes, trim and the source
 * are deliberately not in any group: those are per-clip content.
 */
export const APPLY_ALL_GROUPS = Object.freeze({
  color: Object.freeze(['brightness', 'contrast', 'saturation']),
  framing: Object.freeze(['zoom', 'pan_x', 'pan_y']),
  speed: Object.freeze(['speed']),
});

const APPLY_ALL_ALLOWED_FIELDS = new Set(Object.values(APPLY_ALL_GROUPS).flat());

/** Only fields from APPLY_ALL_GROUPS survive; anything else in a patch is dropped. */
function sanitizeApplyAllPatch(patch) {
  return Object.fromEntries(
    Object.entries(patch || {}).filter(([key]) => APPLY_ALL_ALLOWED_FIELDS.has(key)),
  );
}

/** The selected clip's values for one group (unset stays unset, so targets reset too). */
export function pickApplyAllPatch(clip, group) {
  const fields = APPLY_ALL_GROUPS[group];
  if (!fields || !clip) return null;
  return Object.fromEntries(fields.map((field) => [field, clip[field]]));
}

function clipAlreadyMatches(clip, patch) {
  return Object.keys(patch).every((key) => clip[key] === patch[key]);
}

/**
 * Returns the clip list with `patch` applied to every clip. The same array comes
 * back when nothing would change, so a history `set` can skip the undo step.
 */
export function applyPatchToAllClips(clipList, patch) {
  const list = Array.isArray(clipList) ? clipList : [];
  const safe = sanitizeApplyAllPatch(patch);
  if (!Object.keys(safe).length) return list;
  let changed = false;
  const next = list.map((clip) => {
    if (!clip || clipAlreadyMatches(clip, safe)) return clip;
    changed = true;
    return { ...clip, ...safe };
  });
  return changed ? next : list;
}

/** Editor state with one clip patched (what useEditorCommands.patchClip commits). */
export function patchClipInState(state, clipId, patch) {
  return {
    ...state,
    clipList: state.clipList.map((c) => (c.id === clipId ? { ...c, ...patch } : c)),
  };
}

/** Editor state with a look applied to every clip; the same state back when nothing changes. */
export function patchAllClipsInState(state, patch) {
  const clipList = applyPatchToAllClips(state.clipList, patch);
  return clipList === state.clipList ? state : { ...state, clipList };
}

/**
 * What an apply-to-all would do: how many clips change, and how many of those
 * carry their own camera keyframes (a zoom/pan value is invisible on them).
 */
export function summarizeApplyToAll(clipList, patch) {
  const list = Array.isArray(clipList) ? clipList : [];
  const safe = sanitizeApplyAllPatch(patch);
  const touchesFraming = APPLY_ALL_GROUPS.framing.some((key) => key in safe);
  let changed = 0;
  let cameraKeyframeClips = 0;
  for (const clip of list) {
    if (!clip || clipAlreadyMatches(clip, safe)) continue;
    changed += 1;
    if (touchesFraming && cameraKeyframeSummary(clip).points > 0) cameraKeyframeClips += 1;
  }
  return { changed, cameraKeyframeClips };
}

/** How many clips other than `exceptId` carry camera keyframes. */
export function countOtherCameraKeyframeClips(clipList, exceptId) {
  return (Array.isArray(clipList) ? clipList : [])
    .filter((clip) => clip && clip.id !== exceptId && cameraKeyframeSummary(clip).points > 0)
    .length;
}


export const SMART_CAMERA_PRESETS = Object.freeze([
  { id: 'slow_push', label: 'ซูมเข้า 9:16', preset: 'slow_push' },
  { id: 'slow_pull', label: 'ซูมออก 9:16', preset: 'slow_pull' },
  { id: 'pan_left', label: 'แพนซ้าย 9:16', preset: 'pan_left' },
  { id: 'pan_right', label: 'แพนขวา 9:16', preset: 'pan_right' },
]);

export function smartCameraPatch(clip, sourceDuration, presetName = 'slow_push') {
  const duration = clipPlayedDuration(clip, sourceDuration);
  if (duration < MIN_CLIP_DURATION) return null;
  const moves = generateSmartCameraKeyframes({ duration, preset: presetName });
  if (!moves || !moves.length) return null;
  return { keyframes: [...withoutCameraKeyframes(clip?.keyframes), ...moves] };
}

export const KEYFRAME_EASING_OPTIONS = Object.freeze([
  { id: 'ease_in_out', label: 'สมูท (Ease In-Out)' },
  { id: 'linear', label: 'คงที่ (Linear)' },
  { id: 'montage', label: 'Montage (CapCut)' },
  { id: 'hero_in', label: 'Hero In (CapCut)' },
  { id: 'bullet_stop', label: 'Bullet Stop (CapCut)' },
  { id: 'jump_cut', label: 'Jump Cut (CapCut)' },
]);

/** CapCut 7.1 LogWheel crossover thresholds (`Resources/LogWheel/log_wheel_v0/Wheel/xshader/fshader.frag`). */
export const LOG_WHEEL_CROSSOVER = Object.freeze({ rugDown: 0.333, rugUp: 0.555 });

/**
 * CapCut 7.1 PrimaryWheel per-channel Lift/Gamma/Gain formula
 * (`Resources/PrimaryWheel/primary_wheel_v0/Wheel/xshader/fshader.frag`).
 */
export function processPrimaryWheelChannel(srcColor, lift = 0, gamma = 1, gain = 1) {
  const s = clampValue(srcColor, 0, 1, 0);
  let liftX = lift >= 0.5 ? -1e6 : lift / (lift - 0.5);
  let gainX = gain === 0 ? 1e6 : 1.0 / gain;
  if (liftX >= gainX) gainX = liftX + 1e-6;
  let res = (s - liftX) / (gainX - liftX);
  if (res > 0) res = Math.exp(gamma * Math.log(res));
  return clampValue(res, 0, 1, 0);
}

/**
 * CapCut 7.1 Shadow recovery curve (`merge_all_adjust_color/xshader/colorAdjustBundle.frag`).
 */
export function capcutAdjustShadow(c, p = 0) {
  const s = clampValue(c, 0, 1, 0);
  const param = clampValue(p, -0.5, 0.5, 0);
  if (Math.abs(param) < 1e-6) return s;
  let res;
  if (param <= 0) {
    res = Math.pow(s, param + 1.0) - 0.1 * param * Math.pow(1.0 - s, 5.0);
  } else {
    res = Math.pow(s, 1.0 / Math.max(1.0 - param, 1e-5));
  }
  return clampValue(res, 0, 1, 0);
}

/**
 * CapCut 7.1 Highlight recovery curve (`merge_all_adjust_color/xshader/colorAdjustBundle.frag`).
 */
export function capcutAdjustHighlight(c, p = 0) {
  const s = clampValue(c, 0, 1, 0);
  const param = clampValue(p, -0.5, 0.5, 0);
  if (Math.abs(param) < 1e-6) return s;
  let res;
  if (param < 0) {
    res = 1.0 - Math.pow(Math.max(0, 1.0 - s - 0.1 * param * s), param + 1.0);
  } else {
    res = 1.0 - Math.pow(1.0 - s, 1.0 / Math.max(1.0 - param, 1e-5));
  }
  return clampValue(res, 0, 1, 0);
}

/**
 * CapCut 7.1 Dark-Channel Dehaze (`AmazingFeature_dehazing/xshader/dehaze.frag`).
 */
export function capcutDehazeChannel(oriColor, darkColor = 0.35, airLight = 0.85, dehazeParam = 0) {
  const c = clampValue(oriColor, 0, 1, 0);
  const p = clampValue(dehazeParam, 0, 0.95, 0);
  if (p <= 1e-6) return c;
  const dehazeWeight = Math.max(0.5, Math.min(0.95, p));
  const trans = Math.max(0.1, 1.0 - dehazeWeight * clampValue(darkColor, 0, 1, 0.35));
  const res = (c - airLight) / trans + airLight;
  return clampValue(c * (1 - p) + res * p, 0, 1, 0);
}

/**
 * CapCut 7.1 8-Band HSL Hue Windows (`AmazingFeature_hsl/xshader/fshader.frag`).
 */
export const CAPCUT_HSL_RANGES = Object.freeze({
  red: Object.freeze([-45, -20, 10, 45]),
  orange: Object.freeze([-10, 20, 40, 60]),
  yellow: Object.freeze([20, 50, 70, 105]),
  green: Object.freeze([50, 80, 160, 190]),
  cyan: Object.freeze([140, 170, 210, 240]),
  blue: Object.freeze([145, 195, 245, 275]),
  purple: Object.freeze([240, 270, 290, 330]),
  magenta: Object.freeze([285, 315, 345, 365]),
});

/**
 * CapCut 7.1 Skin-Tone Protected Vibrance (`AmazingFeature_splendor` + `AmazingFeature_hsl`).
 * Boosts low-saturation pixels while protecting skin-tone hues (15..45 deg, orange weight 0.35).
 */
export function capcutSplendorVibrance(r, g, b, vibrance = 0) {
  const rr = clampValue(r, 0, 1, 0);
  const gg = clampValue(g, 0, 1, 0);
  const bb = clampValue(b, 0, 1, 0);
  const v = clampValue(vibrance, -0.5, 0.5, 0);
  if (Math.abs(v) < 1e-6) return [rr, gg, bb];
  const maxC = Math.max(rr, gg, bb);
  const minC = Math.min(rr, gg, bb);
  const delta = maxC - minC;
  const sat = maxC <= 1e-6 ? 0 : delta / maxC;
  let hue = 0;
  if (delta > 1e-6) {
    if (maxC === rr) hue = 60 * (((gg - bb) / delta) % 6);
    else if (maxC === gg) hue = 60 * ((bb - rr) / delta + 2);
    else hue = 60 * ((rr - gg) / delta + 4);
    if (hue < 0) hue += 360;
  }
  const skinProtection = (hue >= 15 && hue <= 45) ? 0.35 : 1.0;
  const boost = 1.0 + v * (1.0 - sat) * skinProtection;
  const lum = 0.299 * rr + 0.587 * gg + 0.114 * bb;
  return [
    clampValue(lum + (rr - lum) * boost, 0, 1, 0),
    clampValue(lum + (gg - lum) * boost, 0, 1, 0),
    clampValue(lum + (bb - lum) * boost, 0, 1, 0),
  ];
}

/**
 * CapCut 7.1 Vignette radial smoothstep falloff (`AmazingFeature_vignetting/xshader/vignetting.frag`).
 */
export function capcutVignetteWeight(u, v, intensity = 0) {
  const p = clampValue(intensity, -1, 1, 0);
  if (Math.abs(p) < 1e-6) return 0;
  const SQRT2 = 1.415;
  const ux = 2.0 * clampValue(u, 0, 1, 0.5) - 1.0;
  const vy = 2.0 * clampValue(v, 0, 1, 0.5) - 1.0;
  const dist = Math.hypot(ux, vy);
  const absP = Math.abs(p);
  const r0 = (p < 0 ? (1.0 + (0.2 - 1.0) * absP) : (1.0 + (0.1 - 1.0) * absP)) * SQRT2;
  const r1 = (p < 0 ? (1.4 + (0.9 - 1.4) * absP) : (1.4 + (0.85 - 1.4) * absP)) * SQRT2;
  const t = clampValue((dist - r0) / Math.max(1e-6, r1 - r0), 0, 1, 0);
  return t * t * (3.0 - 2.0 * t);
}

/**
 * CapCut 7.1 Procedural Film Particle Noise (`AmazingFeature_particle/xshader/noise.frag`).
 */
export function capcutParticleNoise(u, v, seed = 0.25, intensity = 0.08) {
  const SCALE = 9331.99;
  const frac = (x) => x - Math.floor(x);
  let x = frac(u * SCALE * 0.1031) + seed;
  let y = frac(v * SCALE * 0.1031) + seed;
  let z = frac(seed * SCALE * 0.1031) + seed;
  const dot = x * (y + 33.33) + y * (z + 33.33) + z * (x + 33.33);
  x += dot;
  y += dot;
  z += dot;
  return (frac((x + y) * z) - 0.5) * intensity;
}

/**
 * Standard CapCut 7.1 Video Color Adjustment Fields.
 */
export const COLOR_FIELDS = Object.freeze([
  { key: 'brightness', label: 'ความสว่าง', min: -0.3, max: 0.3, step: 0.02, def: 0 },
  { key: 'contrast', label: 'คอนทราสต์', min: 0.5, max: 2, step: 0.05, def: 1 },
  { key: 'saturation', label: 'ความสด', min: 0, max: 3, step: 0.05, def: 1 },
  { key: 'temperature', label: 'อุณหภูมิสี (Warm/Cool)', min: -0.3, max: 0.3, step: 0.02, def: 0 },
  { key: 'gamma', label: 'แกมม่า (Gamma / LogWheel)', min: 0.5, max: 2.0, step: 0.05, def: 1 },
  { key: 'shadows', label: 'ดึงเงามืด (Shadows)', min: -0.5, max: 0.5, step: 0.05, def: 0 },
  { key: 'highlights', label: 'ลดแสงจ้า (Highlights)', min: -0.5, max: 0.5, step: 0.05, def: 0 },
  { key: 'vibrance', label: 'เร่งสีสดถนอมผิว (Splendor Vibrance)', min: -0.5, max: 0.5, step: 0.05, def: 0 },
  { key: 'vignette', label: 'ขอบมืดโฟกัสสินค้า (Vignette)', min: 0, max: 1.0, step: 0.05, def: 0 },
]);
