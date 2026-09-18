import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  createFrameSamplingMemo,
  createHotPathProbe,
  createMotionCacheKey,
  quantizeFrame,
  resolveReducedMotionSettle,
} from './performanceGuard.js';

test('quantizeFrame maps equivalent RAF timestamps to one video frame', () => {
  assert.equal(quantizeFrame(0, 1000, 30), 0);
  assert.equal(quantizeFrame(0.499, 1000, 30), 15);
  assert.equal(quantizeFrame(0.501, 1000, 30), 15);
  assert.equal(quantizeFrame(-1, 1000, 30), 0);
  assert.equal(quantizeFrame(2, 1000, 30), 30);
});

test('cache keys are primitive-only, deterministic, and distinguish typed parts', () => {
  const first = createMotionCacheKey({
    contractId: 'pop|zoom',
    phase: 'in',
    frame: 12,
    reducedMotion: false,
    revision: 4,
    variant: 'default',
  });
  const second = createMotionCacheKey({
    contractId: 'pop|zoom',
    phase: 'in',
    frame: 12,
    reducedMotion: false,
    revision: 4,
    variant: 'default',
  });

  assert.equal(first, second);
  assert.notEqual(first, createMotionCacheKey({ contractId: 'pop|zoom', phase: 'in', frame: 13 }));
  assert.notEqual(
    createMotionCacheKey({ contractId: '12', phase: 'in', frame: 0 }),
    createMotionCacheKey({ contractId: 12, phase: 'in', frame: 0 }),
  );
});

test('frame sampling memo returns the same sampled object on hit and evicts oldest entries', () => {
  let sampleCalls = 0;
  const memo = createFrameSamplingMemo({
    maxEntries: 2,
    keyOf: (input) => createMotionCacheKey({
      contractId: input.id,
      phase: input.phase,
      frame: input.frame,
    }),
    sample: (input) => ({ frame: input.frame, sampleCall: ++sampleCalls }),
  });

  const first = memo({ id: 'text', phase: 'in', frame: 1 });
  const hit = memo({ id: 'text', phase: 'in', frame: 1 });
  assert.strictEqual(hit, first);
  assert.equal(sampleCalls, 1);
  assert.deepEqual(memo.stats(), { hits: 1, misses: 1, size: 1, maxEntries: 2 });

  memo({ id: 'text', phase: 'in', frame: 2 });
  memo({ id: 'text', phase: 'in', frame: 3 });
  assert.equal(memo.stats().size, 2);
  assert.equal(memo.has({ id: 'text', phase: 'in', frame: 1 }), false);
  assert.equal(memo.stats().misses, 3);
});

test('reduced-motion settle reuses immutable phase policies', () => {
  assert.strictEqual(resolveReducedMotionSettle('in', true), resolveReducedMotionSettle('in', true));
  assert.deepEqual(resolveReducedMotionSettle('in', true), {
    applied: true,
    progress: 1,
    strategy: 'settle-in-freeze-loop-skip-out',
  });
  assert.equal(resolveReducedMotionSettle('loop', true).progress, 0);
  assert.equal(resolveReducedMotionSettle('out', true).progress, 0);
  assert.deepEqual(resolveReducedMotionSettle('in', false), {
    applied: false,
    progress: null,
    strategy: 'none',
  });
  assert.throws(() => resolveReducedMotionSettle('invalid', true), /Invalid motion phase/);
  assert.throws(() => resolveReducedMotionSettle('invalid', false), /Invalid motion phase/);
});

test('hot-path probe records explicit stringify/allocation violations per frame', () => {
  const probe = createHotPathProbe({ maxStringifyPerFrame: 0, maxAllocationsPerFrame: 1 });

  probe.beginFrame();
  probe.markAllocation();
  assert.deepEqual(probe.endFrame(), { stringify: 0, allocations: 1, withinBudget: true });

  probe.beginFrame();
  probe.markStringify();
  probe.markAllocation(2);
  assert.deepEqual(probe.endFrame(), { stringify: 1, allocations: 2, withinBudget: false });
  assert.equal(probe.stats().violations, 1);
});

test('performance guard source does not call JSON.stringify in the hot-path utility', () => {
  const source = readFileSync(new URL('./performanceGuard.js', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /\bJSON\.stringify\s*\(/);
});
