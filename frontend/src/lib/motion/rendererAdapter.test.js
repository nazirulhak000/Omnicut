import test from 'node:test';
import assert from 'node:assert/strict';

import { getMotionPreset } from './motionPresets.js';
import {
  DEFAULT_RENDER_STATE,
  sampleCanvasMotion,
  sampleRendererState,
} from './rendererAdapter.js';

function contract(id, phase, tracks, extra = {}) {
  return {
    version: 1,
    id,
    role: 'text',
    phase,
    duration_ms: 100,
    tracks,
    ...extra,
  };
}

function scaleTrack(from, to) {
  return { unit: 'ratio', keyframes: [{ t: 0, value: from }, { t: 1, value: to }] };
}

test('returns render defaults when a contract has no tracks', () => {
  const result = sampleCanvasMotion(getMotionPreset('text', 'in', 'none'), 0.5);

  assert.deepEqual(result.state, DEFAULT_RENDER_STATE);
  assert.equal(result.metadata.phase, 'in');
  assert.equal(result.metadata.phaseProgress, 0.5);
});

test('samples a single contract inside an explicit phase window', () => {
  const source = contract('text.in.scale', 'in', { scale: scaleTrack(0, 1) });
  const result = sampleCanvasMotion(source, 0.5, {
    phaseTiming: { start: 0.25, end: 0.75 },
    defaults: { alpha: 0.8, position: { x: 12, y: -4 } },
  });

  assert.equal(result.state.scale, 0.5);
  assert.equal(result.state.alpha, 0.8);
  assert.deepEqual(result.state.position, { x: 12, y: -4 });
  assert.equal(result.metadata.phaseProgress, 0.5);
});

test('selects in, repeating loop, and out phases on a normalized timeline', () => {
  const plan = {
    in: contract('in', 'in', { scale: scaleTrack(0, 1) }),
    loop: contract('loop', 'loop', {
      rotation: {
        unit: 'degrees',
        repeat: true,
        cycle_duration_ms: 20,
        keyframes: [{ t: 0, value: 0 }, { t: 1, value: 10 }],
      },
    }, { repeat: true }),
    out: contract('out', 'out', { alpha: scaleTrack(1, 0) }),
  };
  const phaseTiming = {
    in: { start: 0, end: 0.2 },
    loop: { start: 0.2, end: 0.8 },
    out: { start: 0.8, end: 1 },
  };

  assert.equal(sampleCanvasMotion(plan, 0.1, { phaseTiming }).metadata.phase, 'in');
  const loop = sampleCanvasMotion(plan, 0.5, { phaseTiming });
  assert.equal(loop.metadata.phase, 'loop');
  assert.equal(loop.metadata.loopIteration, 2);
  assert.ok(Math.abs(loop.metadata.loopProgress - 0.5) < 1e-9);
  assert.ok(Math.abs(loop.state.rotation - 5) < 1e-9);

  const out = sampleCanvasMotion(plan, 0.9, { phaseTiming });
  assert.equal(out.metadata.phase, 'out');
  assert.equal(out.state.alpha, 0.5);
});

test('outWindow overrides the default out phase window', () => {
  const plan = {
    in: contract('in', 'in', { scale: scaleTrack(0, 1) }),
    out: contract('out', 'out', { alpha: scaleTrack(1, 0) }),
  };
  const result = sampleCanvasMotion(plan, 0.75, { outWindow: { start: 0.7, end: 1 } });

  assert.equal(result.metadata.phase, 'out');
  assert.ok(Math.abs(result.metadata.phaseProgress - (1 / 6)) < 1e-9);
  assert.equal(result.metadata.phaseWindow.start, 0.7);
});

test('reduced motion settles entrance, freezes loop, and skips exit', () => {
  const plan = {
    in: contract('in', 'in', { scale: scaleTrack(0, 1) }),
    loop: getMotionPreset('hook', 'loop', 'pulse'),
    out: contract('out', 'out', { alpha: scaleTrack(1, 0) }),
  };
  const phaseTiming = {
    in: { start: 0, end: 0.2 },
    loop: { start: 0.2, end: 0.8 },
    out: { start: 0.8, end: 1 },
  };

  const entrance = sampleCanvasMotion(plan, 0, { phaseTiming, reducedMotion: true });
  assert.equal(entrance.state.scale, 1);
  assert.equal(entrance.metadata.reducedMotionApplied, true);

  const loop = sampleCanvasMotion(plan, 0.5, { phaseTiming, reducedMotion: true });
  assert.equal(loop.state.alpha, 1);

  const exit = sampleCanvasMotion(plan, 0.9, { phaseTiming, reducedMotion: true });
  assert.equal(exit.state.alpha, 1);
  assert.equal(exit.metadata.reducedMotionStrategy, 'settle-in-freeze-loop-skip-out');
});

test('does not mutate contracts, nested defaults, or timeline input', () => {
  const source = contract('text.in.immutable', 'in', {
    position: { unit: 'canvas_px', keyframes: [{ t: 0, value: { x: 0, y: 0 } }, { t: 1, value: { x: 10, y: 20 } }] },
  });
  const before = structuredClone(source);
  const timeline = { normalizedTime: 0.25 };
  const defaults = { position: { x: 3, y: 4 } };

  const result = sampleRendererState(source, timeline, { defaults });
  result.state.position.x = 999;

  assert.deepEqual(source, before);
  assert.deepEqual(timeline, { normalizedTime: 0.25 });
  assert.deepEqual(defaults, { position: { x: 3, y: 4 } });
});
