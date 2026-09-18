/**
 * Declarative snapshots of the current motion defaults.
 *
 * These presets are data only.  They intentionally do not replace any live
 * renderer.  Values mirror the existing SequencePlayer/motion_effects
 * defaults so a future adapter can migrate one preset at a time.
 */

import { MOTION_CONTRACT_VERSION, validateMotionContract } from './motionContract.js';

const k = (t, value, easing = 'linear') => ({ t, value, easing });
const track = (keyframes, unit, extra = {}) => ({ keyframes, unit, ...extra });

const IN_PRESETS = {
  bounce: {
    duration_ms: 450,
    tracks: { scale: track([k(0, 0.6), k(150 / 450, 1.25), k(280 / 450, 0.92), k(380 / 450, 1.05), k(1, 1)], 'ratio') },
  },
  bounce_soft: {
    duration_ms: 450,
    tracks: { scale: track([k(0, 0.6), k(150 / 450, 1.25, { name: 'power', exponent: 0.6 }), k(280 / 450, 0.92), k(380 / 450, 1.05), k(1, 1, { name: 'power', exponent: 0.6 })], 'ratio') },
  },
  pop: {
    duration_ms: 200,
    tracks: { scale: track([k(0, 0.55), k(120 / 200, 1.18), k(1, 1)], 'ratio') },
  },
  pop_soft: {
    duration_ms: 200,
    tracks: { scale: track([k(0, 0.55), k(120 / 200, 1.18, { name: 'power', exponent: 0.6 }), k(1, 1, { name: 'power', exponent: 2.2 })], 'ratio') },
  },
  slam: {
    duration_ms: 180,
    tracks: {
      scale: track([k(0, 2.2), k(1, 1, { name: 'power', exponent: 2.2 })], 'ratio'),
      alpha: track([k(0, 0), k(50 / 180, 1)], 'opacity'),
    },
  },
  elastic_bounce: {
    duration_ms: 520,
    tracks: {
      scale: track([k(0, 0.4), k(160 / 520, 1.28, { name: 'power', exponent: 0.6 }), k(290 / 520, 0.88), k(390 / 520, 1.08), k(460 / 520, 0.98), k(1, 1, { name: 'power', exponent: 0.6 })], 'ratio'),
      alpha: track([k(0, 0), k(40 / 520, 1)], 'opacity'),
    },
  },
  fade: {
    duration_ms: 250,
    tracks: { alpha: track([k(0, 0), k(1, 1)], 'opacity') },
  },
  zoom: {
    duration_ms: 300,
    tracks: {
      scale: track([k(0, 1.8), k(1, 1)], 'ratio'),
      alpha: track([k(0, 0), k(0.5, 1)], 'opacity'),
    },
  },
  slide_up: {
    duration_ms: 300,
    tracks: {
      dy: track([k(0, 60), k(1, 0)], 'canvas_px'),
      alpha: track([k(0, 0), k(1, 1)], 'opacity'),
    },
  },
  typewriter: {
    duration_ms: 400,
    tracks: { reveal: track([k(0, 0), k(1, 1)], 'ratio') },
  },
  blur: {
    duration_ms: 350,
    tracks: {
      alpha: track([k(0, 0), k(1, 1)], 'opacity'),
      blur: track([k(0, 12), k(1, 0)], 'canvas_px'),
    },
  },
  snap: {
    duration_ms: 70,
    tracks: { scale: track([k(0, 1.25), k(1, 1)], 'ratio') },
  },
  pop_zoom: {
    duration_ms: 100,
    tracks: {
      scale: track([k(0, 1.45), k(1, 1)], 'ratio'),
      alpha: track([k(0, 0), k(0.7, 1)], 'opacity'),
    },
  },
  stamp: {
    duration_ms: 80,
    tracks: { scale: track([k(0, 1.65), k(1, 1)], 'ratio') },
  },
  quick_fade: {
    duration_ms: 150,
    tracks: { alpha: track([k(0, 0), k(1, 1)], 'opacity') },
  },
  rise: {
    duration_ms: 200,
    tracks: {
      dy: track([k(0, 40), k(1, 0)], 'canvas_px'),
      alpha: track([k(0, 0), k(1, 1)], 'opacity'),
    },
  },
  none: { duration_ms: 0, tracks: {} },
};

const LOOP_PRESETS = {
  pulse: { duration_ms: 700, repeat: true, tracks: { alpha: track([k(0, 1), k(0.5, 1 - 0x25 / 255), k(1, 1)], 'opacity', { repeat: true, cycle_duration_ms: 700 }) } },
  wave: { duration_ms: 1200, repeat: true, tracks: { rotation: track([k(0, 0), k(1 / 3, -3), k(2 / 3, 3), k(1, 0)], 'degrees', { repeat: true, cycle_duration_ms: 1200 }) } },
  shake: { duration_ms: 450, repeat: true, tracks: { rotation: track([k(0, 0), k(0.2, -3), k(0.4, 3), k(0.6, -2), k(0.8, 2), k(1, 0)], 'degrees', { repeat: true, cycle_duration_ms: 450 }) } },
  flicker: { duration_ms: 760, repeat: true, tracks: { alpha: track([k(0, 1), k(80 / 760, 1 - 0x30 / 255), k(230 / 760, 1), k(290 / 760, 1 - 0x45 / 255), k(490 / 760, 1), k(580 / 760, 1 - 0x20 / 255), k(1, 1)], 'opacity', { repeat: true, cycle_duration_ms: 760, interpolation: 'linear' }) } },
  lightsweep: { duration_ms: 500, repeat: true, tracks: {}, metadata: { secondary_pass: 'lightsweep' } },
  none: { duration_ms: 0, repeat: false, tracks: {} },
};

const OUT_PRESETS = {
  fade: { duration_ms: 150, tracks: { alpha: track([k(0, 1), k(1, 0)], 'opacity') } },
  slide: { duration_ms: 150, tracks: { alpha: track([k(0, 1), k(1, 0)], 'opacity'), dy: track([k(0, 0), k(1, 60)], 'canvas_px') } },
  zoom: { duration_ms: 150, tracks: { alpha: track([k(0, 1), k(1, 0)], 'opacity'), scale: track([k(0, 1), k(1, 1.4)], 'ratio') } },
  glitch: { duration_ms: 150, tracks: { rotation: track([k(0, -3), k(0.3636, 3), k(0.7272, 0), k(1, 0)], 'degrees'), alpha: track([k(0, 1), k(0.7333, 1), k(1, 0)], 'opacity') } },
  none: { duration_ms: 1, tracks: { alpha: track([k(0, 1), k(0.999, 1), k(1, 0)], 'opacity') } },
};

function asContract(id, role, phase, definition) {
  const contract = {
    version: MOTION_CONTRACT_VERSION,
    id,
    preset: id,
    role,
    phase,
    duration_ms: definition.duration_ms,
    repeat: Boolean(definition.repeat),
    tracks: definition.tracks,
    metadata: {
      source: 'existing_visual_default',
      renderer_bound: false,
      ...(definition.metadata || {}),
    },
  };
  validateMotionContract(contract);
  return Object.freeze(contract);
}

export const MOTION_PRESETS = Object.freeze({
  ...Object.fromEntries(Object.entries(IN_PRESETS).map(([id, definition]) => [`hook.in.${id}`, asContract(`hook.in.${id}`, 'hook', 'in', definition)])),
  ...Object.fromEntries(['snap', 'pop_zoom', 'stamp', 'quick_fade', 'rise', 'none'].map((id) => [`text.in.${id}`, asContract(`text.in.${id}`, 'text', 'in', IN_PRESETS[id])])),
  ...Object.fromEntries(Object.entries(LOOP_PRESETS).map(([id, definition]) => [`hook.loop.${id}`, asContract(`hook.loop.${id}`, 'hook', 'loop', definition)])),
  ...Object.fromEntries(Object.entries(OUT_PRESETS).map(([id, definition]) => [`hook.out.${id}`, asContract(`hook.out.${id}`, 'hook', 'out', definition)])),
});

export function getMotionPreset(role, phase, presetId) {
  const key = `${role}.${phase}.${presetId}`;
  return MOTION_PRESETS[key] || null;
}
