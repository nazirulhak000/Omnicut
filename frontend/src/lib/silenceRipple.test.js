import test from 'node:test';
import assert from 'node:assert/strict';

import {
  describePlan,
  mergeSpans,
  planChangesAnything,
  planSilenceRipple,
} from './silenceRipple.js';
import { buildSegments } from './timelineMath.js';

/** Three 4-second clips, laid end to end at 0-4, 4-8, 8-12. */
function threeClips() {
  return [
    { id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 4 },
    { id: 'b', source_path: 'b.mp4', trim_start: 0, trim_end: 4 },
    { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 4 },
  ];
}
const DURATIONS = { a: 10, b: 10, c: 10 };

const spanAt = (start, end) => ({ cut_start: start, cut_end: end });

// ---------------------------------------------------------------------------
// mergeSpans
// ---------------------------------------------------------------------------

test('mergeSpans combines overlapping cuts', () => {
  // Detection pads each gap, so neighbouring gaps can overlap. Counting the
  // same footage twice would overstate the saving.
  assert.deepEqual(
    mergeSpans([spanAt(1, 3), spanAt(2, 5)]),
    [{ start: 1, end: 5 }],
  );
});

test('mergeSpans combines touching cuts', () => {
  assert.deepEqual(mergeSpans([spanAt(1, 2), spanAt(2, 3)]), [{ start: 1, end: 3 }]);
});

test('mergeSpans sorts unordered input', () => {
  assert.deepEqual(
    mergeSpans([spanAt(5, 6), spanAt(1, 2)]),
    [{ start: 1, end: 2 }, { start: 5, end: 6 }],
  );
});

test('mergeSpans accepts the raw start/end shape too', () => {
  assert.deepEqual(mergeSpans([{ start: 1, end: 2 }]), [{ start: 1, end: 2 }]);
});

test('mergeSpans drops degenerate and malformed spans', () => {
  const merged = mergeSpans([
    spanAt(2, 2), spanAt(3, 1), spanAt(NaN, 5), spanAt(1, null), null, undefined,
  ]);
  assert.deepEqual(merged, []);
});

test('mergeSpans handles a missing list', () => {
  assert.deepEqual(mergeSpans(null), []);
  assert.deepEqual(mergeSpans(undefined), []);
});

// ---------------------------------------------------------------------------
// planSilenceRipple -- the core arithmetic
// ---------------------------------------------------------------------------

test('a clip entirely inside dead air is removed', () => {
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 8)], DURATIONS);
  assert.deepEqual(plan.removedIds, ['b']);
  assert.equal(plan.clips.length, 2);
  assert.deepEqual(plan.clips.map((c) => c.id), ['a', 'c']);
});

test('dead air at a clip head moves its in-point', () => {
  // Silence over 4.0-5.0 is the first second of clip b.
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 5)], DURATIONS);
  const b = plan.clips.find((c) => c.id === 'b');
  assert.equal(b.trim_start, 1);
  assert.equal(b.trim_end, 4, 'the tail must not move when only the head is silent');
  assert.deepEqual(plan.trimmedIds, ['b']);
});

test('dead air at a clip tail pulls the out-point in', () => {
  // Silence over 7.0-8.0 is the last second of clip b.
  const plan = planSilenceRipple(threeClips(), [spanAt(7, 8)], DURATIONS);
  const b = plan.clips.find((c) => c.id === 'b');
  assert.equal(b.trim_start, 0, 'the head must not move when only the tail is silent');
  assert.equal(b.trim_end, 3);
});

test('the sequence really does get shorter by what was cut', () => {
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 5)], DURATIONS);
  assert.equal(plan.before, 12);
  assert.equal(plan.after, 11);
  const segs = buildSegments(plan.clips, DURATIONS);
  assert.equal(segs[segs.length - 1].segEnd, 11, 'ripple must close the gap, not leave a hole');
});

test('clips after a cut close up with no gap left behind', () => {
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 8)], DURATIONS);
  const segs = buildSegments(plan.clips, DURATIONS);
  assert.equal(segs[0].segStart, 0);
  assert.equal(segs[1].segStart, segs[0].segEnd, 'a removed clip must not leave a hole');
});

test('speed is accounted for when converting a cut to source time', () => {
  // At 2x, one second of timeline is two seconds of source.
  const clips = [{ id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 8, speed: 2 }];
  const plan = planSilenceRipple(clips, [spanAt(0, 1)], { a: 20 });
  assert.equal(plan.clips[0].trim_start, 2);
});

test('untouched clips keep their object identity', () => {
  const clips = threeClips();
  const plan = planSilenceRipple(clips, [spanAt(4, 5)], DURATIONS);
  assert.equal(plan.clips[0], clips[0], 'a clip outside the cut must not be rebuilt');
});

test('per-clip settings survive a trim', () => {
  const clips = threeClips();
  clips[1].zoom = 1.4;
  clips[1].volume = 0.5;
  const plan = planSilenceRipple(clips, [spanAt(4, 5)], DURATIONS);
  const b = plan.clips.find((c) => c.id === 'b');
  assert.equal(b.zoom, 1.4);
  assert.equal(b.volume, 0.5);
});

test('a silence spanning several clips trims and removes together', () => {
  // 3.0-9.0 covers the tail of a, all of b, and the head of c.
  const plan = planSilenceRipple(threeClips(), [spanAt(3, 9)], DURATIONS);
  assert.deepEqual(plan.removedIds, ['b']);
  assert.equal(plan.clips.find((c) => c.id === 'a').trim_end, 3);
  assert.equal(plan.clips.find((c) => c.id === 'c').trim_start, 1);
});

// ---------------------------------------------------------------------------
// Refusals and edge cases
// ---------------------------------------------------------------------------

test('cutting everything is blocked rather than emptying the timeline', () => {
  const plan = planSilenceRipple(threeClips(), [spanAt(0, 12)], DURATIONS);
  assert.ok(plan.blocked, 'an all-silent timeline must not be silently emptied');
  assert.equal(plan.clips.length, 3, 'the original clips are returned untouched');
  assert.equal(planChangesAnything(plan), false);
});

test('no spans means no change', () => {
  const clips = threeClips();
  const plan = planSilenceRipple(clips, [], DURATIONS);
  assert.equal(plan.clips, clips);
  assert.equal(plan.removedSeconds, 0);
  assert.equal(planChangesAnything(plan), false);
});

test('an empty timeline is handled without throwing', () => {
  const plan = planSilenceRipple([], [spanAt(0, 1)], {});
  assert.deepEqual(plan.clips, []);
  assert.equal(plan.before, 0);
});

test('a cut leaving less than the minimum clip length removes the clip', () => {
  // Leaving 0.05s behind is not a clip anyone can use.
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 7.95)], DURATIONS);
  assert.deepEqual(plan.removedIds, ['b']);
});

test('a span outside the sequence changes nothing', () => {
  const clips = threeClips();
  const plan = planSilenceRipple(clips, [spanAt(50, 60)], DURATIONS);
  assert.equal(planChangesAnything(plan), false);
  assert.deepEqual(plan.clips.map((c) => c.id), ['a', 'b', 'c']);
});

test('a span touching a clip boundary is not treated as a cut', () => {
  // [0,4) and [4,8) merely touch at 4.0 -- zero overlap, so clip a is intact.
  const plan = planSilenceRipple(threeClips(), [spanAt(4, 5)], DURATIONS);
  assert.ok(!plan.trimmedIds.includes('a'));
});

test('the first surviving clip cannot fade in from nothing', () => {
  const clips = threeClips();
  clips[1].transition_in = 'fade';
  const plan = planSilenceRipple(clips, [spanAt(0, 4)], DURATIONS);
  assert.equal(plan.clips[0].id, 'b');
  assert.equal(plan.clips[0].transition_in, 'cut');
});

test('planning never mutates the input clips', () => {
  const clips = threeClips();
  const snapshot = JSON.parse(JSON.stringify(clips));
  planSilenceRipple(clips, [spanAt(4, 5)], DURATIONS);
  assert.deepEqual(clips, snapshot, 'plan must be pure so the preview can be discarded');
});

// ---------------------------------------------------------------------------
// describePlan
// ---------------------------------------------------------------------------

test('describePlan states what will happen and the time saved', () => {
  const text = describePlan(planSilenceRipple(threeClips(), [spanAt(4, 8)], DURATIONS));
  assert.match(text, /ลบทิ้ง 1 คลิป/);
  assert.match(text, /4\.00 วินาที/);
});

test('describePlan reports a blocked plan as its reason', () => {
  const text = describePlan(planSilenceRipple(threeClips(), [spanAt(0, 12)], DURATIONS));
  assert.match(text, /ไม่เหลือคลิป/);
});

test('describePlan says so when there is nothing to cut', () => {
  assert.match(describePlan(planSilenceRipple(threeClips(), [], DURATIONS)), /ไม่พบช่วงเงียบ/);
});

test('describePlan tolerates a missing plan', () => {
  assert.equal(describePlan(null), '');
});
