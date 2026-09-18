/**
 * Renderer-neutral performance guards for motion sampling.
 *
 * This module is intentionally standalone. It does not patch Canvas, React,
 * or the existing renderer. A future integration can opt in at one seam and
 * keep the current visual path unchanged until parity has been verified.
 */

const DEFAULT_FRAME_RATE = 30;
const DEFAULT_MAX_CACHE_ENTRIES = 120;
const REDUCED_MOTION_NONE = Object.freeze({
  applied: false,
  progress: null,
  strategy: 'none',
});

const REDUCED_MOTION_SETTLED = Object.freeze({
  in: Object.freeze({
    applied: true,
    progress: 1,
    strategy: 'settle-in-freeze-loop-skip-out',
  }),
  loop: Object.freeze({
    applied: true,
    progress: 0,
    strategy: 'settle-in-freeze-loop-skip-out',
  }),
  out: Object.freeze({
    applied: true,
    progress: 0,
    strategy: 'settle-in-freeze-loop-skip-out',
  }),
});

function assertFiniteNumber(value, label) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${label} must be a finite number`);
  }
}

function assertPositiveInteger(value, label) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new RangeError(`${label} must be a positive integer`);
  }
}

function clamp01(value) {
  return Math.min(1, Math.max(0, value));
}

/**
 * Quantize a normalized timeline position to a deterministic video frame.
 * Using an integer frame in cache keys prevents equivalent RAF timestamps
 * from producing duplicate samples.
 */
export function quantizeFrame(normalizedTime, durationMs, frameRate = DEFAULT_FRAME_RATE) {
  assertFiniteNumber(normalizedTime, 'normalizedTime');
  assertFiniteNumber(durationMs, 'durationMs');
  assertFiniteNumber(frameRate, 'frameRate');
  if (durationMs < 0) throw new RangeError('durationMs must not be negative');
  if (frameRate <= 0) throw new RangeError('frameRate must be greater than zero');
  return Math.round(clamp01(normalizedTime) * durationMs / 1000 * frameRate);
}

function encodeKeyPart(value) {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';

  switch (typeof value) {
    case 'string': return `s${value.length}:${value}`;
    case 'number':
      assertFiniteNumber(value, 'cache key number');
      return `n${value}`;
    case 'boolean': return value ? 'b1' : 'b0';
    default:
      throw new TypeError('cache key parts must be primitive values');
  }
}

/**
 * Build a collision-resistant primitive-only key without JSON.stringify.
 * Callers should pass a stable contract revision instead of the full motion
 * object so the hot path never serializes a large contract per frame.
 */
export function createMotionCacheKey({
  contractId,
  phase,
  frame,
  reducedMotion = false,
  revision = 0,
  variant = '',
} = {}) {
  // Keep this concatenation explicit: an array + map + join allocates
  // unnecessary temporaries for every sampled frame.
  return `${encodeKeyPart(contractId)}|${encodeKeyPart(phase)}|${encodeKeyPart(frame)}|${encodeKeyPart(reducedMotion)}|${encodeKeyPart(revision)}|${encodeKeyPart(variant)}`;
}

function touchLru(cache, key, value) {
  cache.delete(key);
  cache.set(key, value);
}

/**
 * Bounded memoizer for frame sampling.
 *
 * `sample` receives the caller's input and its result is returned by identity
 * on a cache hit. The result is therefore a read-only value from the
 * renderer's point of view; cloning here would defeat the allocation guard.
 */
export function createFrameSamplingMemo({
  sample,
  maxEntries = DEFAULT_MAX_CACHE_ENTRIES,
  keyOf = (input) => input,
} = {}) {
  if (typeof sample !== 'function') throw new TypeError('sample must be a function');
  assertPositiveInteger(maxEntries, 'maxEntries');
  if (typeof keyOf !== 'function') throw new TypeError('keyOf must be a function');

  const cache = new Map();
  let hits = 0;
  let misses = 0;

  function sampleMemoized(input) {
    const key = keyOf(input);
    if (cache.has(key)) {
      hits += 1;
      const value = cache.get(key);
      touchLru(cache, key, value);
      return value;
    }

    misses += 1;
    const value = sample(input);
    cache.set(key, value);
    if (cache.size > maxEntries) cache.delete(cache.keys().next().value);
    return value;
  }

  sampleMemoized.has = (input) => cache.has(keyOf(input));
  sampleMemoized.clear = () => cache.clear();
  sampleMemoized.stats = () => Object.freeze({
    hits,
    misses,
    size: cache.size,
    maxEntries,
  });

  return sampleMemoized;
}

/**
 * Resolve the reduced-motion policy once per frame before sampling tracks.
 * The returned objects are shared constants, so repeated calls do not create
 * a policy object in the hot path.
 */
export function resolveReducedMotionSettle(phase, reducedMotion) {
  if (!REDUCED_MOTION_SETTLED[phase]) throw new TypeError(`Invalid motion phase: ${phase}`);
  if (!reducedMotion) return REDUCED_MOTION_NONE;
  return REDUCED_MOTION_SETTLED[phase];
}

/**
 * A test/development-only budget probe. Production render code can call the
 * two tiny mark methods around known expensive seams without monkey-patching
 * globals. It cannot observe arbitrary allocations automatically; the probe
 * makes that limitation explicit instead of pretending to be a profiler.
 */
export function createHotPathProbe({
  maxStringifyPerFrame = 0,
  maxAllocationsPerFrame = Number.POSITIVE_INFINITY,
} = {}) {
  assertFiniteNumber(maxStringifyPerFrame, 'maxStringifyPerFrame');
  if (maxStringifyPerFrame < 0) throw new RangeError('maxStringifyPerFrame must not be negative');
  if (maxAllocationsPerFrame !== Number.POSITIVE_INFINITY) {
    assertFiniteNumber(maxAllocationsPerFrame, 'maxAllocationsPerFrame');
    if (maxAllocationsPerFrame < 0) throw new RangeError('maxAllocationsPerFrame must not be negative');
  }

  let frameStringify = 0;
  let frameAllocations = 0;
  let frames = 0;
  let violations = 0;

  function beginFrame() {
    frameStringify = 0;
    frameAllocations = 0;
    frames += 1;
  }

  function markStringify(count = 1) {
    assertPositiveInteger(count, 'stringify count');
    frameStringify += count;
  }

  function markAllocation(count = 1) {
    assertPositiveInteger(count, 'allocation count');
    frameAllocations += count;
  }

  function endFrame() {
    const snapshot = Object.freeze({
      stringify: frameStringify,
      allocations: frameAllocations,
      withinBudget: frameStringify <= maxStringifyPerFrame
        && frameAllocations <= maxAllocationsPerFrame,
    });
    if (!snapshot.withinBudget) violations += 1;
    return snapshot;
  }

  return Object.freeze({
    beginFrame,
    markStringify,
    markAllocation,
    endFrame,
    stats: () => Object.freeze({
      frames,
      violations,
      lastFrame: Object.freeze({ stringify: frameStringify, allocations: frameAllocations }),
      budgets: Object.freeze({ maxStringifyPerFrame, maxAllocationsPerFrame }),
    }),
  });
}

export const MOTION_PERFORMANCE_DEFAULTS = Object.freeze({
  frameRate: DEFAULT_FRAME_RATE,
  maxCacheEntries: DEFAULT_MAX_CACHE_ENTRIES,
});
