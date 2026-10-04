import test from 'node:test';
import assert from 'node:assert/strict';

import { keepRanges } from './voiceCutMap.js';
import {
  VOICE_CUT_FADE_S,
  contextTimeAt,
  programTimeAt,
  rangeGainAt,
  scheduleVoiceCut,
  scheduleVoiceEdit,
  voiceEditCutsAnything,
} from './voiceCutScheduler.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} != ${b}`);
const F = VOICE_CUT_FADE_S;

// Source 6 s, cut [2.0, 2.5] -> keep [0,2]@0 and [2.5,6]@2 (program length 5.5).
const ONE_CUT = keepRanges([{ start: 2, end: 2.5 }], 6);

test('fade length equals the render constant (sfx_manager.VOICE_CUT_FADE_S)', () => {
  assert.equal(VOICE_CUT_FADE_S, 0.008);
});

test('zero cuts: a single node over the whole file, no ramps', () => {
  const plan = scheduleVoiceCut(keepRanges([], 6), { t: 0, ctxNow: 10, sourceDuration: 6 });
  assert.equal(plan.length, 1);
  assert.deepEqual(
    [plan[0].when, plan[0].offset, plan[0].duration, plan[0].fadeIn, plan[0].fadeOut, plan[0].gainAtStart],
    [10, 0, 6, 0, 0, 1],
  );
  assert.equal(voiceEditCutsAnything({ source: { duration: 6 }, cuts: [] }), false);
});

test('one interior cut from t = 0: two nodes back to back, ramps only at the join', () => {
  const plan = scheduleVoiceCut(ONE_CUT, { t: 0, ctxNow: 100, sourceDuration: 6 });
  assert.equal(plan.length, 2);
  const [a, b] = plan;
  assert.deepEqual([a.when, a.offset, a.duration, a.fadeIn, a.fadeOut], [100, 0, 2, 0, F]);
  assert.deepEqual([b.when, b.offset, b.duration, b.fadeIn, b.fadeOut], [102, 2.5, 3.5, F, 0]);
  assert.equal(a.rangeFadeIn, false, 'file head: no ramp (render: start == 0)');
  assert.equal(b.rangeFadeOut, false, 'file tail: no ramp (render: is_tail)');
  near(a.when + a.duration, b.when);
});

test('head cut fades the new start in; tail cut fades the new end out', () => {
  const head = scheduleVoiceCut(keepRanges([{ start: 0, end: 1 }], 6), { t: 0, ctxNow: 0, sourceDuration: 6 });
  assert.equal(head.length, 1);
  assert.deepEqual([head[0].offset, head[0].duration, head[0].fadeIn, head[0].fadeOut, head[0].gainAtStart], [1, 5, F, 0, 0]);
  const tail = scheduleVoiceCut(keepRanges([{ start: 5, end: 6 }], 6), { t: 0, ctxNow: 0, sourceDuration: 6 });
  assert.equal(tail.length, 1);
  assert.deepEqual([tail[0].offset, tail[0].duration, tail[0].fadeIn, tail[0].fadeOut], [0, 5, 0, F]);
});

test('several cuts: interior ranges carry both ramps', () => {
  const ranges = keepRanges([{ start: 1, end: 1.5 }, { start: 3, end: 4 }], 6);
  const plan = scheduleVoiceCut(ranges, { t: 0, ctxNow: 0, sourceDuration: 6 });
  assert.deepEqual(plan.map((p) => [p.when, p.offset, p.duration, p.fadeIn, p.fadeOut]), [
    [0, 0, 1, 0, F],
    [1, 1.5, 1.5, F, F],
    [2.5, 4, 2, F, 0],
  ]);
});

test('starting mid-range: offset moves in, earlier ranges are skipped, later ones wait', () => {
  const plan = scheduleVoiceCut(ONE_CUT, { t: 1.25, ctxNow: 50, sourceDuration: 6 });
  assert.equal(plan.length, 2);
  near(plan[0].when, 50);
  near(plan[0].offset, 1.25);
  near(plan[0].duration, 0.75);
  assert.equal(plan[0].fadeIn, 0);
  assert.equal(plan[0].fadeOut, F);
  near(plan[1].when, 50.75);
  near(plan[1].offset, 2.5);
  const later = scheduleVoiceCut(ONE_CUT, { t: 3, ctxNow: 50, sourceDuration: 6 });
  assert.equal(later.length, 1);
  near(later[0].offset, 3.5); // program 3.0 = source 3.5 (0.5 s cut before it)
  near(later[0].duration, 2.5);
  assert.equal(later[0].fadeIn, 0, 'started past the ramp: nothing left of it');
  assert.equal(later[0].gainAtStart, 1);
});

test('starting exactly on the join (the cut gap has no program length): plays the far side', () => {
  const plan = scheduleVoiceCut(ONE_CUT, { t: 2, ctxNow: 7, sourceDuration: 6 });
  assert.equal(plan.length, 1);
  assert.deepEqual([plan[0].when, plan[0].offset, plan[0].duration, plan[0].fadeIn, plan[0].gainAtStart], [7, 2.5, 3.5, F, 0]);
  // A hair before the join: the tail of the first range still plays (its fade-out window).
  const before = scheduleVoiceCut(ONE_CUT, { t: 2 - 0.004, ctxNow: 7, sourceDuration: 6 });
  assert.equal(before.length, 2);
  near(before[0].duration, 0.004);
  near(before[0].fadeOut, 0.004);
  near(before[0].gainAtStart, 0.5, 1e-9);
  near(before[1].when, 7.004);
});

test('starting inside a fade-in ramp resumes the ramp part-way', () => {
  const plan = scheduleVoiceCut(ONE_CUT, { t: 2.002, ctxNow: 0, sourceDuration: 6 });
  assert.equal(plan.length, 1);
  near(plan[0].offset, 2.502);
  near(plan[0].fadeIn, 0.006);
  near(plan[0].gainAtStart, 0.25);
});

test('starting at or after the end: nothing to schedule', () => {
  assert.deepEqual(scheduleVoiceCut(ONE_CUT, { t: 5.5, ctxNow: 0, sourceDuration: 6 }), []);
  assert.deepEqual(scheduleVoiceCut(ONE_CUT, { t: 9, ctxNow: 0, sourceDuration: 6 }), []);
});

test('negative / missing t is treated as 0', () => {
  const plan = scheduleVoiceCut(ONE_CUT, { t: -3, ctxNow: 1, sourceDuration: 6 });
  assert.equal(plan[0].when, 1);
  assert.equal(plan[0].offset, 0);
});

test('scheduleVoiceEdit normalises the cuts like the render (snap + merge)', () => {
  const edit = { source: { duration: 6 }, cuts: [{ id: 'a', start: 2.01, end: 2.49 }, { id: 'b', start: 2.4, end: 2.5 }] };
  const plan = scheduleVoiceEdit(edit, { t: 0, ctxNow: 0 });
  assert.deepEqual(plan.map((p) => [p.offset, p.duration]), [[0, 2], [2.5, 3.5]]);
  assert.equal(voiceEditCutsAnything(edit), true);
  assert.equal(voiceEditCutsAnything({ source: { duration: 6 }, cuts: [{ start: 0, end: 6 }] }), false, 'all cut -> render ignores the cuts');
  assert.equal(voiceEditCutsAnything(null), false);
});

test('node starts are contiguous on the context clock for any start point', () => {
  const ranges = keepRanges([{ start: 0.5, end: 1 }, { start: 2, end: 2.2 }, { start: 4, end: 5.1 }], 7.3);
  for (const t of [0, 0.3, 0.5, 1.4, 2.7, 4.1]) {
    const plan = scheduleVoiceCut(ranges, { t, ctxNow: 3, sourceDuration: 7.3 });
    near(plan[0].when, 3);
    for (let i = 1; i < plan.length; i += 1) near(plan[i - 1].when + plan[i - 1].duration, plan[i].when, 1e-9);
    // Program time of the first node == t.
    near(plan[0].progStart + (plan[0].offset - plan[0].srcStart), t, 1e-9);
  }
});

test('envelope matches afade: linear, product of the two ramps', () => {
  const flags = { fadeIn: true, fadeOut: true };
  near(rangeGainAt(0, 1, flags), 0);
  near(rangeGainAt(0.004, 1, flags), 0.5);
  near(rangeGainAt(0.5, 1, flags), 1);
  near(rangeGainAt(1 - 0.002, 1, flags), 0.25);
  near(rangeGainAt(1, 1, flags), 0);
  near(rangeGainAt(0, 1, { fadeIn: false, fadeOut: false }), 1);
});

test('master clock: program <-> context time round trip', () => {
  const clock = { startT: 4.2, ctxStart: 12.5 };
  near(programTimeAt(clock, 12.5), 4.2);
  near(programTimeAt(clock, 42.5), 34.2);
  near(contextTimeAt(clock, programTimeAt(clock, 20.123)), 20.123);
  const plan = scheduleVoiceCut(ONE_CUT, { t: clock.startT, ctxNow: clock.ctxStart, sourceDuration: 6 });
  near(programTimeAt(clock, plan[0].when), 4.2);
});
