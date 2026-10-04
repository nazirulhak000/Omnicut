import test from 'node:test';
import assert from 'node:assert/strict';

import {
  clipDuration,
  buildSegments,
  totalDuration,
  localTimeAt,
  motionTimeAt,
  resolveClipTransforms,
  transitionOverlap,
  splitClipAt,
  splitKeyframesAt,
  shiftTrimWindow,
  resizeTrimWindow,
  snapTime,
  snapCandidates,
  resolveSnapCandidateLabel,
  formatTimecode,
  MIN_CLIP_DURATION,
  FADE_DURATION,
  MAX_TRANSITION_DURATION,
} from './timelineMath.js';

import {
  applyCaptionMagneticRipple,
  packTextOverlays,
  indexFromX,
  timeFromEvent,
  tickStep,
} from './timelineTrackModel.js';

test('clipDuration accounts for trim, speed, and freeze tail with MIN_CLIP_DURATION floor', () => {
  // basic duration: 5s
  const c1 = { trim_start: 0, trim_end: 5, speed: 1 };
  assert.equal(clipDuration(c1, 10), 5);

  // with 2x speed: 5s / 2 = 2.5s
  const c2 = { trim_start: 0, trim_end: 5, speed: 2 };
  assert.equal(clipDuration(c2, 10), 2.5);

  // with freeze tail: 2.5s + 1.5s = 4.0s
  const c3 = { trim_start: 0, trim_end: 5, speed: 2, freeze_tail: 1.5 };
  assert.equal(clipDuration(c3, 10), 4.0);

  // very short trim clamps to MIN_CLIP_DURATION (0.2s)
  const c4 = { trim_start: 0, trim_end: 0.05, speed: 1 };
  assert.equal(clipDuration(c4, 10), MIN_CLIP_DURATION);
});

test('transitionOverlap clamps duration between 0.1 and MAX_TRANSITION_DURATION', () => {
  assert.equal(transitionOverlap({ transition_in: 'cut' }), 0);
  assert.equal(transitionOverlap({ transition_in: 'fade', transition_duration: 0.5 }), 0.5);
  // clamped minimum 0.1
  assert.equal(transitionOverlap({ transition_in: 'fade', transition_duration: 0.01 }), 0.1);
  // clamped maximum MAX_TRANSITION_DURATION (2.0)
  assert.equal(transitionOverlap({ transition_in: 'fade', transition_duration: 5.0 }), MAX_TRANSITION_DURATION);
});

test('buildSegments accurately positions segments with transition overlaps', () => {
  const clips = [
    { id: 'c1', trim_start: 0, trim_end: 4 },
    { id: 'c2', trim_start: 0, trim_end: 4, transition_in: 'fade', transition_duration: 0.5 },
    { id: 'c3', trim_start: 0, trim_end: 3, transition_in: 'cut' },
  ];
  const durations = { c1: 4, c2: 4, c3: 3 };
  const segs = buildSegments(clips, durations);

  assert.equal(segs.length, 3);
  // seg 0: start 0, end 4
  assert.equal(segs[0].segStart, 0);
  assert.equal(segs[0].segEnd, 4);
  assert.equal(segs[0].overlap, 0);

  // seg 1: overlaps seg 0 by 0.5s -> starts at 3.5, length 4 -> ends at 7.5
  assert.equal(segs[1].segStart, 3.5);
  assert.equal(segs[1].segEnd, 7.5);
  assert.equal(segs[1].overlap, 0.5);

  // seg 2: cut -> starts at 7.5, length 3 -> ends at 10.5
  assert.equal(segs[2].segStart, 7.5);
  assert.equal(segs[2].segEnd, 10.5);
  assert.equal(segs[2].overlap, 0);

  assert.equal(totalDuration(segs), 10.5);
});

test('localTimeAt correctly maps sequence time into source clip time with freeze tail hold', () => {
  const seg = {
    clip: { trim_start: 1.0, trim_end: 4.0, speed: 1, freeze_tail: 2.0 },
    srcDur: 10,
    segStart: 5.0,
    segEnd: 10.0,
  };

  // at start of segment: 5.0 -> 1.0s
  assert.equal(localTimeAt(seg, 5.0), 1.0);
  // 1.5s in: 6.5 -> 2.5s
  assert.equal(localTimeAt(seg, 6.5), 2.5);
  // at end of played span (5.0 + 3.0 = 8.0s) -> 4.0s
  assert.equal(localTimeAt(seg, 8.0), 4.0 - .75 / 30);
  // during freeze tail (9.5s) -> still holds 4.0s (freeze last frame)
  assert.equal(localTimeAt(seg, 9.5), 4.0 - .75 / 30);
});

test('resolveClipTransforms applies linear camera keyframes with live clamps', () => {
  const clip = {
    zoom: 1.2,
    keyframes: [
      { time: 0, zoom: 0.2, pan_x: -4, pan_y: 0.25 },
      { time: 2, zoom: 2.2, pan_x: 4, pan_y: 1.5 },
    ],
  };

  assert.deepEqual(resolveClipTransforms(clip, 0), { zoom: 1.0, pan_x: -1.0, pan_y: 0.25 });
  assert.deepEqual(resolveClipTransforms(clip, 1), { zoom: 1.2, pan_x: 0.0, pan_y: 0.875 });
  assert.deepEqual(resolveClipTransforms(clip, 2), { zoom: 2.2, pan_x: 1.0, pan_y: 1.0 });
  assert.deepEqual(resolveClipTransforms({}, 0), { zoom: 1.0, pan_x: 0.0, pan_y: 0.0 });
});

test('motionTimeAt uses played time and holds the last keyframe through freeze tail', () => {
  const seg = {
    clip: { trim_start: 4, trim_end: 8, speed: 2, freeze_tail: 1 },
    srcDur: 10,
    segStart: 3,
  };
  assert.equal(motionTimeAt(seg, 3), 0);
  assert.equal(motionTimeAt(seg, 4), 1);
  assert.equal(motionTimeAt(seg, 5), 2);
  assert.equal(motionTimeAt(seg, 6), 2);
});

test('splitClipAt returns two valid clip pieces and reserves freeze tail for the right piece only', () => {
  let nextId = 100;
  const makeId = () => `id-${nextId++}`;

  const seg = {
    clip: { id: 'orig', trim_start: 0, trim_end: 6, freeze_tail: 1.5 },
    srcDur: 6,
    segStart: 0,
    segEnd: 7.5,
  };

  // split at 2.5s
  const pieces = splitClipAt(seg, 2.5, makeId);
  assert.ok(pieces);
  assert.equal(pieces.length, 2);

  const [left, right] = pieces;
  assert.equal(left.trim_start, 0);
  assert.equal(left.trim_end, 2.5);
  assert.equal(left.freeze_tail, undefined); // left piece drops freeze tail

  assert.equal(right.trim_start, 2.5);
  assert.equal(right.trim_end, 6);
  assert.equal(right.transition_in, 'cut'); // cut boundary between pieces
  assert.equal(right.freeze_tail, 1.5); // right piece keeps freeze tail
});

const closeTo = (actual, expected, label) => {
  assert.ok(Math.abs(actual - expected) < 1e-6, `${label}: ${actual} != ${expected}`);
};

test('splitClipAt splits camera keyframes at the played cut with no jump (B4)', () => {
  let nextId = 1;
  const clip = {
    id: 'orig', trim_start: 1, trim_end: 7, speed: 2, zoom: 1.0,
    keyframes: [
      { time: 0, zoom: 1.0, pan_x: -0.5 },
      { time: 2, zoom: 2.0, pan_x: 0.5 },
      { time: 3, property: 'pan_y', value: 0.4 },
      { time: 0, property: 'pan_y', value: -0.2 },
    ],
  };
  // played span = 6 / 2 = 3s; cut 1.25s into the played clip (2.5s of source)
  const seg = { clip, srcDur: 10, segStart: 4, segEnd: 7 };
  const cut = 1.25;
  const [left, right] = splitClipAt(seg, seg.segStart + cut, () => `p${nextId++}`);

  assert.equal(left.trim_end, 3.5);
  assert.equal(right.trim_start, 3.5);
  assert.ok(left.keyframes.every((p) => !Number.isFinite(p.time) || p.time <= cut + 1e-9));
  assert.ok(right.keyframes.every((p) => p.time >= 0));

  const leftEnd = resolveClipTransforms(left, cut);
  const rightStart = resolveClipTransforms(right, 0);
  const original = resolveClipTransforms(clip, cut);
  for (const prop of ['zoom', 'pan_x', 'pan_y']) {
    closeTo(leftEnd[prop], original[prop], `left end ${prop}`);
    closeTo(rightStart[prop], original[prop], `right start ${prop}`);
  }
  for (const local of [0, 0.3, 0.75, 1.0, 1.75]) {
    const r = resolveClipTransforms(right, local);
    const o = resolveClipTransforms(clip, cut + local);
    for (const prop of ['zoom', 'pan_x', 'pan_y']) closeTo(r[prop], o[prop], `right ${prop}@${local}`);
  }
  for (const local of [0, 0.5, 1.0]) {
    const l = resolveClipTransforms(left, local);
    const o = resolveClipTransforms(clip, local);
    for (const prop of ['zoom', 'pan_x', 'pan_y']) closeTo(l[prop], o[prop], `left ${prop}@${local}`);
  }
  // the source clip is not mutated
  assert.equal(clip.keyframes.length, 4);
  assert.equal(clip.keyframes[1].time, 2);
});

test('splitClipAt keeps a keyframe that sits exactly on the cut without duplicating it', () => {
  const clip = {
    id: 'orig', trim_start: 0, trim_end: 4,
    keyframes: [{ time: 0, zoom: 1 }, { time: 2, zoom: 2 }, { time: 4, zoom: 1.5 }],
  };
  const seg = { clip, srcDur: 4, segStart: 0, segEnd: 4 };
  const [left, right] = splitClipAt(seg, 2, () => 'x');
  assert.deepEqual(left.keyframes, [{ time: 0, zoom: 1 }, { time: 2, zoom: 2 }]);
  assert.deepEqual(right.keyframes, [{ time: 0, zoom: 2 }, { time: 2, zoom: 1.5 }]);
});

test('splitClipAt leaves empty or absent keyframes untouched', () => {
  const base = { id: 'orig', trim_start: 0, trim_end: 4 };
  const seg = (clip) => ({ clip, srcDur: 4, segStart: 0, segEnd: 4 });
  const [l1, r1] = splitClipAt(seg({ ...base, keyframes: [] }), 1.5, () => 'x');
  assert.deepEqual(l1.keyframes, []);
  assert.deepEqual(r1.keyframes, []);
  const [l2, r2] = splitClipAt(seg(base), 1.5, () => 'x');
  assert.equal('keyframes' in l2, false);
  assert.equal('keyframes' in r2, false);
});

test('splitKeyframesAt holds a track that only exists on one side of the cut', () => {
  const { left, right } = splitKeyframesAt([{ time: 0, zoom: 1 }, { time: 1, zoom: 2 }], 3);
  assert.deepEqual(left, [{ time: 0, zoom: 1 }, { time: 1, zoom: 2 }]);
  assert.deepEqual(right, [{ time: 0, property: 'zoom', value: 2 }]);
  const late = splitKeyframesAt([{ time: 2, zoom: 1.5 }, { time: 3, zoom: 2.5 }], 1);
  assert.deepEqual(late.left, [{ time: 1, property: 'zoom', value: 1.5 }]);
  assert.deepEqual(late.right, [{ time: 1, zoom: 1.5 }, { time: 2, zoom: 2.5 }]);
});

test('camera easing on a point shapes the segment that ends there; none stays linear', () => {
  const kf = (easing) => ({ keyframes: [{ time: 0, zoom: 1 }, { time: 2, zoom: 1.5, ...(easing && { easing }) }] });
  const at = (clip, t) => resolveClipTransforms(clip, t).zoom;
  assert.equal(at(kf(), 0.5), 1.125);
  assert.equal(at(kf('linear'), 0.5), 1.125);
  assert.equal(at(kf('nonsense'), 0.5), 1.125);
  assert.equal(at(kf('ease_in'), 1), 1.125);
  assert.equal(at(kf('ease_out'), 1), 1.375);
  assert.equal(at(kf('ease_in_out'), 0.5), 1.0625);
  assert.equal(at(kf('ease_in_out'), 1), 1.25);
  assert.equal(at(kf('ease_in_out'), 1.5), 1.4375);
  assert.equal(at(kf('ease_in_out'), 2), 1.5);
  // Property-form points carry easing too; clamps still apply after easing.
  const prop = { keyframes: [{ time: 0, property: 'pan_x', value: 0 }, { time: 1, property: 'pan_x', value: 4, easing: 'ease_in' }] };
  assert.equal(resolveClipTransforms(prop, 0.25).pan_x, 0.25);
  assert.equal(resolveClipTransforms(prop, 0.75).pan_x, 1);
});

test('splitKeyframesAt bakes an eased segment so both halves follow the curve', () => {
  const clip = {
    keyframes: [
      { time: 0, zoom: 1, pan_x: -0.4 },
      { time: 4, zoom: 1.5, pan_x: 0.4, easing: 'ease_in_out' },
      { time: 5, zoom: 1.2, pan_x: 0.4, easing: 'ease_out' },
    ],
  };
  const cut = 1.3;
  const { left, right } = splitKeyframesAt(clip.keyframes, cut);
  const L = { keyframes: left };
  const R = { keyframes: right };
  const orig = (t) => resolveClipTransforms(clip, t);
  for (const prop of ['zoom', 'pan_x']) {
    assert.ok(Math.abs(resolveClipTransforms(L, cut)[prop] - orig(cut)[prop]) < 1e-9);
    assert.ok(Math.abs(resolveClipTransforms(R, 0)[prop] - orig(cut)[prop]) < 1e-9);
  }
  let worst = 0;
  for (let t = 0; t <= cut + 1e-9; t += 0.05) {
    const a = resolveClipTransforms(L, t); const o = orig(t);
    worst = Math.max(worst, Math.abs(a.zoom - o.zoom), Math.abs(a.pan_x - o.pan_x));
  }
  for (let t = 0; t <= 5 - cut + 1e-9; t += 0.05) {
    const a = resolveClipTransforms(R, t); const o = orig(cut + t);
    worst = Math.max(worst, Math.abs(a.zoom - o.zoom), Math.abs(a.pan_x - o.pan_x));
  }
  assert.ok(worst < 3e-3, `worst ${worst}`);
  // The combined end point lost zoom/pan_x to linear property points; the
  // later ease_out segment is untouched and the emptied point was dropped.
  assert.ok(right.some((p) => p.time === 3.7 && p.easing === 'ease_out' && p.zoom === 1.2));
  assert.ok(!right.some((p) => p.time === 2.7 && p.zoom !== undefined));
  assert.ok(!right.some((p) => Object.keys(p).every((k) => k === 'time' || k === 'easing')));
  // Linear tracks still split exactly as before (no extra samples).
  assert.equal(splitKeyframesAt([{ time: 0, zoom: 1 }, { time: 2, zoom: 2 }], 1).right.length, 2);
});

test('splitClipAt returns null when cut position is too close to boundaries', () => {
  const seg = {
    clip: { id: 'orig', trim_start: 0, trim_end: 2 },
    srcDur: 2,
    segStart: 0,
    segEnd: 2,
  };
  // cut at 0.1s (< MIN_CLIP_DURATION) -> invalid
  assert.equal(splitClipAt(seg, 0.1, () => 'x'), null);
  // cut at 1.95s (> segEnd - MIN_CLIP_DURATION) -> invalid
  assert.equal(splitClipAt(seg, 1.95, () => 'x'), null);
});

test('shiftTrimWindow moves the trim window by deltaSource, keeping its span constant', () => {
  // matches the feature's own motivating example: 1.5-4.13 (2.63s span) -> shift +6.5s -> 8.0-10.63
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  assert.deepEqual(shiftTrimWindow(clip, 6.5, 20), { trim_start: 8.0, trim_end: 10.63 });
});

test('shiftTrimWindow clamps at the start of the source, preserving span', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = shiftTrimWindow(clip, -100, 20);
  assert.equal(result.trim_start, 0);
  assert.equal(Math.round((result.trim_end - result.trim_start) * 100) / 100, 2.63);
});

test('shiftTrimWindow clamps at the end of the source, preserving span', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = shiftTrimWindow(clip, 100, 20);
  assert.equal(result.trim_end, 20);
  assert.equal(Math.round((result.trim_end - result.trim_start) * 100) / 100, 2.63);
});

test('shiftTrimWindow pins to the tiny remaining room when the span nearly fills the source', () => {
  const clip = { trim_start: 0.05, trim_end: 9.95 }; // 9.9s span in a 10s source -> 0.1s of room total
  const result = shiftTrimWindow(clip, 5, 10);
  // maxStart = srcDur - span = 0.1, so a large positive delta pins there, not at 0
  assert.equal(result.trim_start, 0.1);
  assert.equal(Math.round((result.trim_end - result.trim_start) * 100) / 100, 9.9);
});

test('shiftTrimWindow computes span against srcDur when trim_end starts null', () => {
  const clip = { trim_start: 2, trim_end: null };
  const result = shiftTrimWindow(clip, 1, 10);
  // original span = 10 - 2 = 8s; shifted +1 -> would need trim_end=11 > srcDur, so clamps to start=2
  assert.equal(result.trim_start, 2);
  assert.equal(result.trim_end, 10);
});

test('resizeTrimWindow moves the start edge, changing the span', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = resizeTrimWindow('start', clip, 1.0, 20);
  assert.equal(result.trim_start, 2.5);
  assert.equal(result.trim_end, 4.13); // end edge untouched
});

test('resizeTrimWindow moves the end edge, changing the span', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = resizeTrimWindow('end', clip, 2.0, 20);
  assert.equal(result.trim_start, 1.5); // start edge untouched
  assert.equal(result.trim_end, 6.13);
});

test('resizeTrimWindow clamps the start edge at 0', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = resizeTrimWindow('start', clip, -100, 20);
  assert.equal(result.trim_start, 0);
  assert.equal(result.trim_end, 4.13);
});

test('resizeTrimWindow clamps the end edge at srcDur', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const result = resizeTrimWindow('end', clip, 100, 20);
  assert.equal(result.trim_start, 1.5);
  assert.equal(result.trim_end, 20);
});

test('resizeTrimWindow never lets either edge cross past MIN_CLIP_DURATION from the other', () => {
  const clip = { trim_start: 1.5, trim_end: 4.13 };
  const startResult = resizeTrimWindow('start', clip, 100, 20); // pushes start way past end
  assert.equal(startResult.trim_start, Math.round((4.13 - MIN_CLIP_DURATION) * 100) / 100);

  const endResult = resizeTrimWindow('end', clip, -100, 20); // pushes end way before start
  assert.equal(endResult.trim_end, Math.round((1.5 + MIN_CLIP_DURATION) * 100) / 100);
});

test('resizeTrimWindow computes span against srcDur when trim_end starts null', () => {
  const clip = { trim_start: 2, trim_end: null };
  const result = resizeTrimWindow('end', clip, 3, 10);
  assert.equal(result.trim_start, 2);
  assert.equal(result.trim_end, 10); // was null -> resolves to srcDur, +3 clamps back to srcDur
});

test('snapTime snaps to nearest candidate within tolerance', () => {
  const candidates = [0, 2.5, 5.0, 7.5, 10.0];
  // 2.47 is within 0.1 of 2.5 -> snaps to 2.5
  assert.equal(snapTime(2.47, candidates, 0.1), 2.5);
  // 2.30 is outside 0.1 of both 2.5 and 0 -> stays 2.30
  assert.equal(snapTime(2.30, candidates, 0.1), 2.30);
});

test('snapCandidates includes 0, playhead, clip boundaries and extra points', () => {
  const segments = [
    { segStart: 0, segEnd: 3.5 },
    { segStart: 3.5, segEnd: 8.0 },
  ];
  const candidates = snapCandidates(segments, 1.25, [9.0]);
  assert.deepEqual(candidates, [0, 1.25, 9.0, 0, 3.5, 3.5, 8.0]);
});

test('formatTimecode formats seconds to mm:ss.t', () => {
  assert.equal(formatTimecode(0), '00:00.0');
  assert.equal(formatTimecode(4.2), '00:04.2');
  assert.equal(formatTimecode(65.8), '01:05.8');
});

test('applyCaptionMagneticRipple pushes subsequent cues on expand and pulls on shrink without gaps', () => {
  const cues = [
    { _uid: 'c1', start: 0.0, end: 2.0, text: 'First' },
    { _uid: 'c2', start: 2.0, end: 4.5, text: 'Second' },
    { _uid: 'c3', start: 4.5, end: 6.0, text: 'Third' },
  ];

  // Case 1: Trim c1 end from 2.0 to 3.0 (+1.0s expansion)
  const pushed = applyCaptionMagneticRipple(cues, 'c1', 0.0, 3.0);
  assert.equal(pushed[0].start, 0.0);
  assert.equal(pushed[0].end, 3.0);
  assert.equal(pushed[1].start, 3.0); // c2 pushed forward by 1.0s
  assert.equal(pushed[1].end, 5.5);
  assert.equal(pushed[2].start, 5.5); // c3 pushed forward by 1.0s
  assert.equal(pushed[2].end, 7.0);

  // Case 2: Trim c1 end from 2.0 to 1.5 (-0.5s contraction -> magnetic pull)
  const pulled = applyCaptionMagneticRipple(cues, 'c1', 0.0, 1.5);
  assert.equal(pulled[0].start, 0.0);
  assert.equal(pulled[0].end, 1.5);
  assert.equal(pulled[1].start, 1.5); // c2 magnetically pulled backward
  assert.equal(pulled[1].end, 4.0);
  assert.equal(pulled[2].start, 4.0); // c3 magnetically pulled backward
  assert.equal(pulled[2].end, 5.5);
});

test('packTextOverlays assigns non-overlapping lanes to overlapping text overlays', () => {
  const overlays = [
    { id: 't1', start: 0.0, end: 3.0 },
    { id: 't2', start: 1.5, end: 4.0 }, // overlaps t1 -> lane 1
    { id: 't3', start: 3.5, end: 5.0 }, // starts after t1 ends -> can reuse lane 0
  ];
  const { packedTextOverlays, textLaneCount } = packTextOverlays(overlays);
  assert.equal(textLaneCount, 2);
  const byId = Object.fromEntries(packedTextOverlays.map((o) => [o.id, o.lane]));
  assert.equal(byId.t1, 0);
  assert.equal(byId.t2, 1);
  assert.equal(byId.t3, 0);
});

test('indexFromX and timeFromEvent correctly map pixel coordinates to timeline index and time', () => {
  const laneRect = { left: 100, width: 800 };
  const pxPerSec = 50; // 50 px/s -> 100px = 2s
  const segments = [
    { segStart: 0, segEnd: 2.0 },
    { segStart: 2.0, segEnd: 5.0 },
  ];

  // clientX 150 = 50px from lane left = 1.0s -> midpoint of seg 0 is 1.0s -> index 0 or 1
  assert.equal(indexFromX(120, laneRect, pxPerSec, segments), 0);
  // clientX 300 = 200px from lane left = 4.0s -> after seg 0 (midpoint 1.0s), midpoint of seg 1 is 3.5s -> index 1 or 2
  assert.equal(indexFromX(300, laneRect, pxPerSec, segments), 2);

  // timeFromEvent at clientX 200 = (200-100)/50 = 2.0s
  assert.equal(timeFromEvent(200, laneRect, pxPerSec, 10), 2.0);
  // clamped to maxDuration
  assert.equal(timeFromEvent(800, laneRect, pxPerSec, 5), 5.0);
});

test('resolveSnapCandidateLabel identifies candidate origins accurately', () => {
  const segments = [
    { segStart: 0, segEnd: 3.5 },
    { segStart: 3.5, segEnd: 8.0 },
  ];
  const cues = [
    { start: 0.5, end: 2.0 },
    { start: 2.2, end: 4.1 },
  ];

  assert.equal(resolveSnapCandidateLabel(0, { playhead: 5 }), 'จุดเริ่มต้น (0:00)');
  assert.equal(resolveSnapCandidateLabel(5.0, { playhead: 5.0, segments }), 'หัวอ่าน (Playhead)');
  assert.equal(resolveSnapCandidateLabel(12.5, { playhead: 5.0, audioDuration: 12.5 }), 'จุดจบเสียงพากย์ (Audio End)');
  assert.equal(resolveSnapCandidateLabel(3.5, { playhead: 1.0, segments }), 'รอยต่อคลิป #1 ↔ #2');
  assert.equal(resolveSnapCandidateLabel(8.0, { playhead: 1.0, segments }), 'ท้ายคลิป #2');
  assert.equal(resolveSnapCandidateLabel(0.5, { playhead: 1.0, segments, cues }), 'หัวซับ #1');
  assert.equal(resolveSnapCandidateLabel(4.1, { playhead: 1.0, segments, cues }), 'ท้ายซับ #2');
  assert.equal(resolveSnapCandidateLabel(99.9, { playhead: 1.0 }), 'จุดตัด (Snap)');
});

