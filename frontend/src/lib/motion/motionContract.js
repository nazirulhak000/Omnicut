/**
 * Declarative motion contract for text overlays and hook banners.
 *
 * This module is intentionally renderer-agnostic.  It describes motion as
 * normalized keyframes so Canvas, ASS, and future renderers can consume the
 * same data without changing the current visual path.
 */

export const MOTION_CONTRACT_VERSION = 1;

export const MOTION_ROLES = Object.freeze(['text', 'hook', 'caption']);
export const MOTION_PHASES = Object.freeze(['in', 'loop', 'out']);
export const MOTION_TRACKS = Object.freeze([
  'scale',
  'alpha',
  'position',
  'dy',
  'rotation',
  'blur',
  'reveal',
]);

export const MOTION_EASINGS = Object.freeze([
  'linear',
  'ease_in',
  'ease_out',
  'ease_in_out',
  'power',
  'step',
  'sine_in_out',
  'spring',
]);

export const MOTION_CONTRACT_SCHEMA = Object.freeze({
  version: MOTION_CONTRACT_VERSION,
  roles: MOTION_ROLES,
  phases: MOTION_PHASES,
  tracks: MOTION_TRACKS,
  normalized_time: [0, 1],
});

const NUMBER_TRACKS = new Set(['scale', 'alpha', 'dy', 'rotation', 'blur', 'reveal']);

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function assert(condition, message) {
  if (!condition) throw new TypeError(`Invalid motion contract: ${message}`);
}

function assertFinite(value, label) {
  assert(isFiniteNumber(value), `${label} must be a finite number`);
}

function assertJsonObject(value, label) {
  assert(value !== null && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
}

function validateValue(trackName, value) {
  if (NUMBER_TRACKS.has(trackName)) {
    assertFinite(value, `${trackName} value`);
    return;
  }

  if (trackName === 'position') {
    assertJsonObject(value, 'position value');
    assertFinite(value.x, 'position.x');
    assertFinite(value.y, 'position.y');
    return;
  }

  throw new TypeError(`Invalid motion contract: unsupported track ${trackName}`);
}

function validateEasing(easing) {
  const spec = typeof easing === 'string' ? { name: easing } : easing;
  assertJsonObject(spec, 'easing');
  assert(MOTION_EASINGS.includes(spec.name), `unsupported easing ${spec.name}`);

  if (spec.name === 'power') {
    assertFinite(spec.exponent, 'power exponent');
    assert(spec.exponent > 0, 'power exponent must be greater than zero');
  }
  if (spec.name === 'spring') {
    for (const key of ['mass', 'stiffness', 'damping']) {
      if (spec[key] !== undefined) assertFinite(spec[key], `spring ${key}`);
    }
  }
}

export function normalizeTime(value) {
  const time = Number(value);
  assert(Number.isFinite(time), 'normalized time must be finite');
  return Math.min(1, Math.max(0, time));
}

export function validateMotionTrack(trackName, track) {
  assert(MOTION_TRACKS.includes(trackName), `unsupported track ${trackName}`);
  assertJsonObject(track, `${trackName} track`);
  assert(Array.isArray(track.keyframes) && track.keyframes.length > 0, `${trackName} keyframes must be non-empty`);

  let previousTime = -1;
  for (const [index, keyframe] of track.keyframes.entries()) {
    assertJsonObject(keyframe, `${trackName} keyframe ${index}`);
    assertFinite(keyframe.t, `${trackName} keyframe ${index}.t`);
    assert(keyframe.t >= 0 && keyframe.t <= 1, `${trackName} keyframe ${index}.t must be between 0 and 1`);
    assert(keyframe.t > previousTime, `${trackName} keyframe times must be strictly increasing`);
    validateValue(trackName, keyframe.value);
    if (keyframe.easing !== undefined) validateEasing(keyframe.easing);
    previousTime = keyframe.t;
  }

  if (track.default !== undefined) validateValue(trackName, track.default);
  if (track.unit !== undefined) assert(typeof track.unit === 'string' && track.unit.length > 0, `${trackName} unit must be a string`);
  if (track.repeat !== undefined) assert(typeof track.repeat === 'boolean', `${trackName} repeat must be boolean`);
  if (track.cycle_duration_ms !== undefined) {
    assertFinite(track.cycle_duration_ms, `${trackName} cycle_duration_ms`);
    assert(track.cycle_duration_ms > 0, `${trackName} cycle_duration_ms must be greater than zero`);
  }
  return true;
}

export function validateMotionContract(contract) {
  assertJsonObject(contract, 'contract');
  assert(contract.version === MOTION_CONTRACT_VERSION, `version must be ${MOTION_CONTRACT_VERSION}`);
  assert(typeof contract.id === 'string' && contract.id.length > 0, 'id must be a non-empty string');
  assert(MOTION_ROLES.includes(contract.role), `unsupported role ${contract.role}`);
  assert(MOTION_PHASES.includes(contract.phase), `unsupported phase ${contract.phase}`);
  assertFinite(contract.duration_ms, 'duration_ms');
  assert(contract.duration_ms >= 0, 'duration_ms must not be negative');
  assertJsonObject(contract.tracks, 'tracks');

  for (const [trackName, track] of Object.entries(contract.tracks)) {
    validateMotionTrack(trackName, track);
  }
  if (contract.preset !== undefined) assert(typeof contract.preset === 'string' && contract.preset.length > 0, 'preset must be a string');
  if (contract.metadata !== undefined) assertJsonObject(contract.metadata, 'metadata');
  return true;
}

function easingProgress(easing, progress) {
  const spec = typeof easing === 'string' ? { name: easing } : (easing || { name: 'linear' });
  const t = Math.min(1, Math.max(0, progress));
  switch (spec.name) {
    case 'ease_in': return t * t;
    case 'ease_out': return t * (2 - t);
    case 'ease_in_out': return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    case 'power': return t ** (Number(spec.exponent) || 1);
    case 'step': return t >= 1 ? 1 : 0;
    case 'sine_in_out': return -(Math.cos(Math.PI * t) - 1) / 2;
    case 'spring': {
      const mass = Number(spec.mass) || 1;
      const stiffness = Number(spec.stiffness) || 100;
      const damping = Number(spec.damping) || 10;
      const frequency = Math.sqrt(stiffness / mass);
      return 1 - Math.exp(-damping * t / (2 * mass)) * Math.cos(frequency * t);
    }
    case 'linear':
    default: return t;
  }
}

function interpolateValue(left, right, progress) {
  if (typeof left === 'number' && typeof right === 'number') {
    return left + (right - left) * progress;
  }
  return {
    x: left.x + (right.x - left.x) * progress,
    y: left.y + (right.y - left.y) * progress,
  };
}

export function sampleTrack(trackName, track, normalizedTime = 0) {
  validateMotionTrack(trackName, track);
  const time = normalizeTime(normalizedTime);
  const points = track.keyframes;
  if (time <= points[0].t) return structuredClone(points[0].value);
  const last = points[points.length - 1];
  if (time >= last.t) return structuredClone(last.value);

  for (let index = 1; index < points.length; index += 1) {
    const right = points[index];
    if (time <= right.t) {
      const left = points[index - 1];
      const span = right.t - left.t;
      const local = (time - left.t) / span;
      return interpolateValue(left.value, right.value, easingProgress(right.easing, local));
    }
  }
  return structuredClone(last.value);
}

export function sampleMotionContract(contract, normalizedTime = 0) {
  validateMotionContract(contract);
  const sampled = {};
  for (const [trackName, track] of Object.entries(contract.tracks)) {
    sampled[trackName] = sampleTrack(trackName, track, normalizedTime);
  }
  return sampled;
}

const TEXT_ENTRANCE_LEGACY_IDS = Object.freeze({
  pop: 'snap',
  zoom: 'pop_zoom',
  stamp: 'stamp',
  fade: 'quick_fade',
  slide: 'rise',
  none: 'none',
});

export const LEGACY_MOTION_IDS = Object.freeze({
  text: Object.freeze({ in: TEXT_ENTRANCE_LEGACY_IDS }),
  hook: Object.freeze({
    in: Object.freeze({}),
    loop: Object.freeze({}),
    out: Object.freeze({}),
  }),
});

export function resolveLegacyMotionId(role, phase, legacyId) {
  assert(MOTION_ROLES.includes(role), `unsupported role ${role}`);
  assert(MOTION_PHASES.includes(phase), `unsupported phase ${phase}`);
  assert(typeof legacyId === 'string' && legacyId.length > 0, 'legacy id must be a non-empty string');
  return LEGACY_MOTION_IDS[role]?.[phase]?.[legacyId] || legacyId;
}
