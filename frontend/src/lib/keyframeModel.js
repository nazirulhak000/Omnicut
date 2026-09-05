/**
 * Keyframe Animation Model and Easing Contract.
 *
 * Implements deterministic interpolation for Zoom, Pan, Opacity, and Volume
 * across sequence playback and rendering.
 */

export const EASING_FUNCTIONS = {
  linear: (t) => t,
  ease_in: (t) => t * t,
  ease_out: (t) => t * (2 - t),
  ease_in_out: (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
};

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

/**
 * Clamps a numeric property value to its safe operating range.
 */
export function clampProperty(prop, value) {
  const num = Number.isFinite(Number(value)) ? Number(value) : PROPERTY_DEFAULTS[prop] ?? 0;
  const bounds = PROPERTY_BOUNDS[prop];
  if (!bounds) return num;
  return Math.min(bounds.max, Math.max(bounds.min, num));
}

/**
 * Interpolates keyframe values along a local timeline in seconds.
 *
 * @param {Array} keyframes - List of keyframe objects { time, value, easing }
 * @param {number} time - Current evaluation time in seconds
 * @param {number} fallback - Fallback value if keyframes are empty
 * @param {string} defaultEasing - Default easing method if unspecified
 * @returns {number} Interpolated value
 */
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
      const easingFn = EASING_FUNCTIONS[right.easing] || EASING_FUNCTIONS.linear;
      const easedRatio = easingFn(Math.min(1.0, Math.max(0.0, rawRatio)));

      return left.value + (right.value - left.value) * easedRatio;
    }
  }

  return last.value;
}

/**
 * Extracts and resolves animated transforms for a clip at a given local clip time.
 *
 * @param {Object} clip - Clip object with optional keyframes or static values
 * @param {number} localTime - Time within the clip in seconds
 * @returns {Object} Evaluated transforms { zoom, pan_x, pan_y, opacity, volume }
 */
export function resolveClipTransforms(clip = {}, localTime = 0) {
  const keyframes = Array.isArray(clip.keyframes) ? clip.keyframes : [];

  // If keyframes contain property-specific lists or mixed tags
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
