/**
 * Keyframe Animation Model and Easing Contract.
 *
 * Implements deterministic interpolation for Zoom, Pan, Opacity, and Volume
 * across sequence playback and rendering.
 *
 * Upgraded with CapCut 7.1 Parametric Cubic-Bézier and 9:16 Smart Camera Motion.
 */

export function solveCubicBezier(p1x, p1y, p2x, p2y, t) {
  if (t <= 0.0) return 0.0;
  if (t >= 1.0) return 1.0;
  if (p1x === p1y && p2x === p2y) return t;

  const cx = 3.0 * p1x;
  const bx = 3.0 * (p2x - p1x) - cx;
  const ax = 1.0 - cx - bx;

  const cy = 3.0 * p1y;
  const by = 3.0 * (p2y - p1y) - cy;
  const ay = 1.0 - cy - by;

  const sampleX = (u) => ((ax * u + bx) * u + cx) * u;
  const sampleY = (u) => ((ay * u + by) * u + cy) * u;
  const sampleDx = (u) => (3.0 * ax * u + 2.0 * bx) * u + cx;

  // Newton-Raphson iteration
  let u = t;
  for (let i = 0; i < 8; i++) {
    const xErr = sampleX(u) - t;
    if (Math.abs(xErr) < 1e-7) return sampleY(u);
    const dx = sampleDx(u);
    if (Math.abs(dx) < 1e-6) break;
    u -= xErr / dx;
  }

  // Binary subdivision fallback
  let u0 = 0.0;
  let u1 = 1.0;
  u = t;
  for (let i = 0; i < 16; i++) {
    const xCurr = sampleX(u);
    if (Math.abs(xCurr - t) < 1e-7) return sampleY(u);
    if (xCurr > t) u1 = u;
    else u0 = u;
    u = (u0 + u1) * 0.5;
  }

  return sampleY(u);
}

export const CUBIC_BEZIER_PRESETS = Object.freeze({
  linear: [0.0, 0.0, 1.0, 1.0],
  ease_in: [0.42, 0.0, 1.0, 1.0],
  ease_out: [0.0, 0.0, 0.58, 1.0],
  ease_in_out: [0.42, 0.0, 0.58, 1.0],
  montage: [0.7, 0.0, 0.3, 1.0],
  hero_in: [0.0, 0.0, 0.2, 1.0],
  bullet_stop: [0.17, 0.89, 0.32, 1.28],
  jump_cut: [1.0, 0.0, 0.0, 1.0],
});

export const EASING_FUNCTIONS = {
  linear: (t) => t,
  ease_in: (t) => t * t,
  ease_out: (t) => t * (2 - t),
  ease_in_out: (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
  montage: (t) => solveCubicBezier(0.7, 0.0, 0.3, 1.0, t),
  hero_in: (t) => solveCubicBezier(0.0, 0.0, 0.2, 1.0, t),
  bullet_stop: (t) => solveCubicBezier(0.17, 0.89, 0.32, 1.28, t),
  jump_cut: (t) => solveCubicBezier(1.0, 0.0, 0.0, 1.0, t),
};

export function resolveEasingRatio(easingSpec, rawRatio) {
  const t = Math.min(1.0, Math.max(0.0, rawRatio));
  if (!easingSpec) return t;

  if (typeof easingSpec === 'string') {
    if (CUBIC_BEZIER_PRESETS[easingSpec]) {
      const [x1, y1, x2, y2] = CUBIC_BEZIER_PRESETS[easingSpec];
      return solveCubicBezier(x1, y1, x2, y2, t);
    }
    if (EASING_FUNCTIONS[easingSpec]) {
      return EASING_FUNCTIONS[easingSpec](t);
    }
    return t;
  }

  if (Array.isArray(easingSpec) && easingSpec.length === 4) {
    return solveCubicBezier(easingSpec[0], easingSpec[1], easingSpec[2], easingSpec[3], t);
  }

  if (typeof easingSpec === 'object' && easingSpec !== null) {
    if (easingSpec.curve === 'cubic_bezier' && Array.isArray(easingSpec.points) && easingSpec.points.length === 4) {
      const [x1, y1, x2, y2] = easingSpec.points;
      return solveCubicBezier(x1, y1, x2, y2, t);
    }
  }

  return t;
}

export const PROPERTY_DEFAULTS = {
  zoom: 1.0,
  pan_x: 0.0,
  pan_y: 0.0,
  opacity: 1.0,
  volume: 1.0,
};

export const PROPERTY_BOUNDS = {
  zoom: { min: 0.5, max: 3.0 },
  pan_x: { min: -1.0, max: 1.0 },
  pan_y: { min: -1.0, max: 1.0 },
  opacity: { min: 0.0, max: 1.0 },
  volume: { min: 0.0, max: 2.0 },
};

export function clampProperty(prop, value) {
  const num = Number.isFinite(Number(value)) ? Number(value) : PROPERTY_DEFAULTS[prop] ?? 0;
  const bounds = PROPERTY_BOUNDS[prop];
  if (!bounds) return num;
  return Math.min(bounds.max, Math.max(bounds.min, num));
}

export function interpolateNumericKeyframes(
  keyframes = [],
  time = 0,
  fallback = 1.0,
  defaultEasing = 'linear'
) {
  const points = (Array.isArray(keyframes) ? keyframes : [])
    .filter((p) => Number.isFinite(Number(p?.time)) && Number.isFinite(Number(p?.value)))
    .map((p) => ({
      time: Number(p.time),
      value: Number(p.value),
      easing: p.easing || defaultEasing,
    }))
    .sort((a, b) => a.time - b.time);

  if (!points.length) return fallback;
  if (time <= points[0].time) return points[0].value;
  const last = points[points.length - 1];
  if (time >= last.time) return last.value;

  for (let i = 1; i < points.length; i += 1) {
    const right = points[i];
    if (time <= right.time) {
      const left = points[i - 1];
      const span = right.time - left.time;
      if (span <= 0) return right.value;

      const rawRatio = (time - left.time) / span;
      const easedRatio = resolveEasingRatio(right.easing, rawRatio);

      return left.value + (right.value - left.value) * easedRatio;
    }
  }

  return last.value;
}

export function resolveClipTransforms(clip = {}, localTime = 0) {
  const keyframes = Array.isArray(clip.keyframes) ? clip.keyframes : [];

  const extractTrack = (prop) => {
    return keyframes
      .filter((k) => k[prop] !== undefined || k.property === prop)
      .map((k) => ({
        time: k.time,
        value: k[prop] !== undefined ? k[prop] : k.value,
        easing: k.easing,
      }));
  };

  const zoomTrack = extractTrack('zoom');
  const panXTrack = extractTrack('pan_x');
  const panYTrack = extractTrack('pan_y');
  const opacityTrack = extractTrack('opacity');
  const volumeTrack = extractTrack('volume');

  const baseZoom = clip.zoom ?? clip.scale ?? PROPERTY_DEFAULTS.zoom;
  const basePanX = clip.pan_x ?? clip.x ?? PROPERTY_DEFAULTS.pan_x;
  const basePanY = clip.pan_y ?? clip.y ?? PROPERTY_DEFAULTS.pan_y;
  const baseOpacity = clip.opacity ?? PROPERTY_DEFAULTS.opacity;
  const baseVolume = clip.volume ?? PROPERTY_DEFAULTS.volume;

  const rawZoom = zoomTrack.length ? interpolateNumericKeyframes(zoomTrack, localTime, baseZoom) : baseZoom;
  const rawPanX = panXTrack.length ? interpolateNumericKeyframes(panXTrack, localTime, basePanX) : basePanX;
  const rawPanY = panYTrack.length ? interpolateNumericKeyframes(panYTrack, localTime, basePanY) : basePanY;
  const rawOpacity = opacityTrack.length ? interpolateNumericKeyframes(opacityTrack, localTime, baseOpacity) : baseOpacity;
  const rawVolume = volumeTrack.length ? interpolateNumericKeyframes(volumeTrack, localTime, baseVolume) : baseVolume;

  return {
    zoom: clampProperty('zoom', rawZoom),
    pan_x: clampProperty('pan_x', rawPanX),
    pan_y: clampProperty('pan_y', rawPanY),
    opacity: clampProperty('opacity', rawOpacity),
    volume: clampProperty('volume', rawVolume),
  };
}

/**
 * CapCut 7.1 Smart Camera Movement (camera-movement.ini, E7)
 */
export const SMART_CAMERA_CONFIG = Object.freeze({
  vertical_strength: 0.6,
  horizon_strength: 0.2,
  base_crop: 0.8,
  smooth_size: 3,
});

export function generateSmartCameraKeyframes(duration = 5.0, preset = 'slow_push') {
  const dur = Math.max(0.5, Number(duration) || 5.0);
  const baseZoom = 1.0 / SMART_CAMERA_CONFIG.base_crop; // 1.25
  const vs = SMART_CAMERA_CONFIG.vertical_strength; // 0.6
  const hs = SMART_CAMERA_CONFIG.horizon_strength; // 0.2

  if (preset === 'slow_push') {
    return [
      { time: 0.0, zoom: baseZoom, pan_x: 0.0, pan_y: 0.0, easing: 'ease_out' },
      { time: dur, zoom: baseZoom * 1.15, pan_x: 0.0, pan_y: -0.05 * vs, easing: 'linear' },
    ];
  } else if (preset === 'slow_pull') {
    return [
      { time: 0.0, zoom: baseZoom * 1.15, pan_x: 0.0, pan_y: -0.05 * vs, easing: 'ease_out' },
      { time: dur, zoom: baseZoom, pan_x: 0.0, pan_y: 0.0, easing: 'linear' },
    ];
  } else if (preset === 'pan_left') {
    return [
      { time: 0.0, zoom: baseZoom * 1.05, pan_x: 0.1 * hs, pan_y: 0.0, easing: 'ease_in_out' },
      { time: dur, zoom: baseZoom * 1.05, pan_x: -0.1 * hs, pan_y: 0.0, easing: 'linear' },
    ];
  } else if (preset === 'pan_right') {
    return [
      { time: 0.0, zoom: baseZoom * 1.05, pan_x: -0.1 * hs, pan_y: 0.0, easing: 'ease_in_out' },
      { time: dur, zoom: baseZoom * 1.05, pan_x: 0.1 * hs, pan_y: 0.0, easing: 'linear' },
    ];
  }
  return [
    { time: 0.0, zoom: baseZoom, pan_x: 0.0, pan_y: 0.0, easing: 'linear' },
    { time: dur, zoom: baseZoom, pan_x: 0.0, pan_y: 0.0, easing: 'linear' },
  ];
}
