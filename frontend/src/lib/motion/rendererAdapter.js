/**
 * Renderer-neutral adapter for the Canvas motion path.
 *
 * Motion contracts describe one phase.  This adapter adds the timeline
 * concerns a renderer needs: phase windows, loop wrapping, render defaults,
 * and a reduced-motion decision that is explicit in the returned metadata.
 * It deliberately returns fresh values and never mutates a contract.
 */

import {
  normalizeTime,
  sampleTrack,
  validateMotionContract,
} from './motionContract.js';

export const DEFAULT_RENDER_STATE = Object.freeze({
  scale: 1,
  alpha: 1,
  position: Object.freeze({ x: 0, y: 0 }),
  dy: 0,
  rotation: 0,
  blur: 0,
  reveal: 1,
});

export const DEFAULT_PHASE_TIMING = Object.freeze({
  in: Object.freeze({ start: 0, end: 0.25 }),
  loop: Object.freeze({ start: 0.25, end: 0.85 }),
  out: Object.freeze({ start: 0.85, end: 1 }),
});

const PHASES = Object.freeze(['in', 'loop', 'out']);
const EPSILON = 1e-9;

function cloneValue(value) {
  return structuredClone(value);
}

function assertObject(value, label) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
}

function normalizeWindow(window, label) {
  assertObject(window, label);
  const start = normalizeTime(window.start ?? 0);
  const end = normalizeTime(window.end ?? 1);
  if (end < start) throw new RangeError(`${label}.end must be greater than or equal to start`);
  return { start, end };
}

function mergeStateDefaults(defaults = {}) {
  assertObject(defaults, 'defaults');
  return {
    ...cloneValue(DEFAULT_RENDER_STATE),
    ...cloneValue(defaults),
    position: {
      ...cloneValue(DEFAULT_RENDER_STATE.position),
      ...(defaults.position ? cloneValue(defaults.position) : {}),
    },
  };
}

function isMotionContract(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && 'tracks' in value;
}

function resolvePlan(input) {
  if (isMotionContract(input)) {
    validateMotionContract(input);
    return {
      contracts: { [input.phase]: input },
      singlePhase: input.phase,
      source: input,
    };
  }

  assertObject(input, 'motion plan');
  const source = input.phases && typeof input.phases === 'object' ? input.phases : input;
  const contracts = {};
  for (const phase of PHASES) {
    if (source[phase] !== undefined && source[phase] !== null) {
      validateMotionContract(source[phase]);
      if (source[phase].phase !== phase) {
        throw new TypeError(`Motion contract phase does not match plan key ${phase}`);
      }
      contracts[phase] = source[phase];
    }
  }
  if (Object.keys(contracts).length === 0) throw new TypeError('motion plan must contain at least one phase contract');
  return { contracts, singlePhase: null, source: input };
}

function resolvePhaseWindows(plan, options) {
  const sourceTiming = plan.source.phase_timing || plan.source.metadata?.phase_timing;
  const optionTiming = options.phaseTiming;
  const hasPlan = plan.singlePhase === null;
  const windows = {};

  for (const phase of PHASES) {
    if (!plan.contracts[phase]) continue;
    const candidate = hasPlan
      ? optionTiming?.[phase] || sourceTiming?.[phase] || DEFAULT_PHASE_TIMING[phase]
      : (optionTiming?.start !== undefined || optionTiming?.end !== undefined
        ? optionTiming
        : optionTiming?.[phase] || sourceTiming?.[phase] || { start: 0, end: 1 });
    windows[phase] = normalizeWindow(candidate, `${phase} phase timing`);
  }

  if (options.outWindow !== undefined && windows.out) {
    windows.out = normalizeWindow(options.outWindow, 'outWindow');
  }
  return windows;
}

function choosePhase(windows, normalizedTime, preferredPhase) {
  if (preferredPhase) return preferredPhase;

  const phases = PHASES.filter((phase) => windows[phase]);
  for (const phase of phases) {
    const window = windows[phase];
    if (normalizedTime >= window.start - EPSILON && normalizedTime <= window.end + EPSILON) return phase;
  }

  const before = phases.filter((phase) => normalizedTime < windows[phase].start);
  if (before.length > 0) return before[0];
  return phases[phases.length - 1];
}

function phaseProgress(window, normalizedTime) {
  if (normalizedTime <= window.start) return 0;
  if (normalizedTime >= window.end) return 1;
  if (window.end - window.start <= EPSILON) return 1;
  return (normalizedTime - window.start) / (window.end - window.start);
}

function hasRepeatingTrack(contract, track) {
  return Boolean(contract.repeat || track.repeat || track.cycle_duration_ms);
}

function sampleContractState(contract, progress, options) {
  const state = mergeStateDefaults(options.defaults);
  const isLoop = contract.phase === 'loop';
  let loopIteration = 0;
  let loopProgress = progress;

  for (const [trackName, track] of Object.entries(contract.tracks)) {
    let trackTime = progress;
    if (isLoop && hasRepeatingTrack(contract, track)) {
      const cycleDuration = Number(track.cycle_duration_ms || contract.duration_ms || 0);
      const elapsedMs = progress * Number(contract.duration_ms || cycleDuration || 1);
      const cycleMs = cycleDuration > 0 ? cycleDuration : 1;
      trackTime = ((elapsedMs % cycleMs) + cycleMs) % cycleMs / cycleMs;
      loopProgress = trackTime;
      loopIteration = Math.floor(elapsedMs / cycleMs);
    }
    state[trackName] = sampleTrack(trackName, track, trackTime);
  }

  return { state, loopIteration, loopProgress };
}

function applyReducedMotion(contract, progress, options) {
  if (!options.reducedMotion) return { progress, applied: false, strategy: 'none' };
  if (contract.phase === 'in') return { progress: 1, applied: true, strategy: 'settle-in-freeze-loop-skip-out' };
  if (contract.phase === 'out') return { progress: 0, applied: true, strategy: 'settle-in-freeze-loop-skip-out' };
  return { progress: 0, applied: true, strategy: 'settle-in-freeze-loop-skip-out' };
}

/**
 * Sample a Canvas-ready state from one phase contract or a { in, loop, out }
 * motion plan. `normalizedTimeline` is clamped to [0, 1].
 */
export function sampleCanvasMotion(input, normalizedTimeline = 0, options = {}) {
  assertObject(options, 'options');
  const plan = resolvePlan(input);
  const normalizedTime = normalizeTime(
    typeof normalizedTimeline === 'object' && normalizedTimeline !== null
      ? normalizedTimeline.normalizedTime
      : normalizedTimeline,
  );
  const windows = resolvePhaseWindows(plan, options);
  const phase = choosePhase(windows, normalizedTime, plan.singlePhase);
  const contract = plan.contracts[phase];
  const window = windows[phase];
  const rawProgress = phaseProgress(window, normalizedTime);
  const reduced = applyReducedMotion(contract, rawProgress, options);
  const sampled = sampleContractState(contract, reduced.progress, options);

  return {
    state: sampled.state,
    metadata: {
      contractId: contract.id,
      role: contract.role,
      phase,
      normalizedTime,
      phaseProgress: reduced.progress,
      rawPhaseProgress: rawProgress,
      phaseWindow: { ...window },
      loopIteration: sampled.loopIteration,
      loopProgress: sampled.loopProgress,
      isRepeating: Boolean(contract.repeat || phase === 'loop'),
      reducedMotion: Boolean(options.reducedMotion),
      reducedMotionApplied: reduced.applied,
      reducedMotionStrategy: reduced.strategy,
    },
  };
}

export const sampleRendererState = sampleCanvasMotion;
