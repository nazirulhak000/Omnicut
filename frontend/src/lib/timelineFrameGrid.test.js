// EDITOR-CUT-QUALITY-R2 lane TM: whole-frame clip timing (B5) and eased
// transition progress. Mirrors tests/test_frame_grid_timing.py on the render
// side; tests/test_preview_render_parity.py runs both on one clip list.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FPS,
  CAMERA_EASINGS,
  EASED_TRANSITIONS,
  buildSegments,
  easeTransitionProgress,
  getDrawPlan,
  planSequenceFrames,
  sequenceFrameIndex,
  totalDuration,
  transitionEasingName,
} from './timelineMath.js';
import { manifestToEditorState, serializeTransitions } from './editorProjectState.js';

const cut = { type: 'cut' };

test('frame grid: cumulative boundaries, total == round(total*FPS)', () => {
  // 24 clips of 1.0167s: rounding each clip alone gives 31 frames apiece
  // (744), while the true total is 732.0 frames.
  const durs = Array.from({ length: 24 }, () => 1.0167);
  const plan = planSequenceFrames(durs, durs.slice(1).map(() => cut));
  const total = durs.reduce((a, b) => a + b, 0);
  assert.equal(plan.end.at(-1), Math.round(total * FPS));
  let acc = 0;
  durs.forEach((d, i) => {
    acc += d;
    assert.ok(Math.abs(plan.end[i] - acc * FPS) <= 0.5 + 1e-9, `edge ${i} within half a frame`);
    if (i > 0) assert.equal(plan.start[i], plan.end[i - 1], 'a cut starts where the last clip ended');
  });
});

test('frame grid: every clip keeps at least one frame', () => {
  const plan = planSequenceFrames([0.01, 0.01, 0.01], [cut, cut]);
  plan.start.forEach((s, i) => assert.ok(plan.end[i] - s >= 1));
});

test('frame grid: transition offset = boundary - overlap, both whole frames', () => {
  const durs = [1.03, 0.987, 1.2111, 0.95];
  const bounds = [{ type: 'fade', duration: 0.4 }, cut, { type: 'slideleft', duration: 0.3333 }];
  const plan = planSequenceFrames(durs, bounds);
  for (let i = 1; i < durs.length; i += 1) {
    assert.ok(Number.isInteger(plan.start[i]) && Number.isInteger(plan.overlap[i]));
    assert.equal(plan.start[i], plan.end[i - 1] - plan.overlap[i]);
  }
  assert.equal(plan.overlap[2], 0);
  assert.equal(plan.overlap[1], 12);  // 0.4s
  assert.equal(plan.overlap[3], 10);  // 0.3333s
});

test('frame grid: a transition is clamped like the render and never empties a clip', () => {
  const plan = planSequenceFrames([1.0, 1.0], [{ type: 'circleopen', duration: 2.0 }]);
  // min(clip) - 0.05 = 0.95s -> offset frame round(1.5) = 2 -> 28 frames
  assert.equal(plan.start[1], 2);
  assert.equal(plan.overlap[1], 28);
  assert.ok(plan.end[1] - plan.start[1] > plan.overlap[1]);
});

test('sequenceFrameIndex rounds halves up (== Python floor(x*fps+0.5))', () => {
  assert.equal(sequenceFrameIndex(0.05), 2);
  assert.equal(sequenceFrameIndex(1 / 60 - 1e-9), 0);
});

test('buildSegments: every edge sits on the 1/30 grid and matches the plan', () => {
  const clips = [
    { id: 'a', trim_start: 0.1, trim_end: 1.1333 },
    { id: 'b', trim_start: 0, trim_end: 2.0, speed: 1.7, transition_in: 'wipeleft', transition_duration: 0.37 },
    { id: 'c', trim_start: 0.5, trim_end: 1.49, freeze_tail: 0.21 },
  ];
  const segs = buildSegments(clips, { a: 5, b: 5, c: 5 });
  segs.forEach((s) => {
    for (const v of [s.segStart, s.segEnd, s.overlap, s.dur]) {
      assert.ok(Math.abs(v * FPS - Math.round(v * FPS)) < 1e-9, `${v} on grid`);
    }
    assert.equal(s.segStart, s.frames.start / FPS);
  });
  assert.equal(segs[1].frames.overlap, 11);
  assert.equal(totalDuration(segs), segs[2].frames.end / FPS);
});

test('eased transitions: only listed types honour easing, curves are the camera ones', () => {
  assert.equal(transitionEasingName('dissolve', 'ease_in_out'), 'linear');
  assert.equal(transitionEasingName('circleopen', 'ease_out'), 'linear');
  assert.equal(transitionEasingName('fade', 'bogus'), 'linear');
  for (const kind of EASED_TRANSITIONS) {
    for (const name of ['ease_in', 'ease_out', 'ease_in_out']) {
      for (const p of [0, 0.25, 0.5, 0.75, 1]) {
        assert.equal(easeTransitionProgress(kind, name, p), CAMERA_EASINGS[name](p));
      }
    }
  }
});

test('getDrawPlan: easing remaps progress; linear/absent unchanged', () => {
  const make = (easing) => buildSegments([
    { id: 'a', trim_start: 0, trim_end: 2 },
    { id: 'b', trim_start: 0, trim_end: 2, transition_in: 'slideleft', transition_duration: 0.4, ...(easing ? { transition_easing: easing } : {}) },
  ], { a: 2, b: 2 });
  const t = 1.6 + 0.1; // 25% into the 0.4s transition starting at 1.6s
  const lin = getDrawPlan(make(null), t);
  assert.ok(Math.abs(lin[1].progress - 0.25) < 1e-9);
  assert.deepEqual(getDrawPlan(make('linear'), t).map((e) => [e.progress, e.alpha]), lin.map((e) => [e.progress, e.alpha]));
  const eased = getDrawPlan(make('ease_in_out'), t);
  assert.ok(Math.abs(eased[1].progress - 0.125) < 1e-9);
  assert.equal(eased[1].alpha, eased[1].progress);
  const dissolve = buildSegments([
    { id: 'a', trim_start: 0, trim_end: 2 },
    { id: 'b', trim_start: 0, trim_end: 2, transition_in: 'dissolve', transition_duration: 0.4, transition_easing: 'ease_in_out' },
  ], { a: 2, b: 2 });
  assert.ok(Math.abs(getDrawPlan(dissolve, t)[1].progress - 0.25) < 1e-9, 'dissolve stays linear');
});

test('transition easing round-trips through the saved transitions list', () => {
  const clips = [
    { id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 2 },
    { id: 'b', source_path: 'b.mp4', trim_start: 0, trim_end: 2, transition_in: 'slideleft', transition_duration: 0.4, transition_easing: 'ease_in_out' },
    { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 2, transition_in: 'fade', transition_duration: 0.4, transition_easing: 'linear' },
    { id: 'd', source_path: 'd.mp4', trim_start: 0, trim_end: 2, transition_in: 'wipeup', transition_duration: 0.3 },
  ];
  const saved = serializeTransitions(clips);
  // only a non-linear easing is written; old manifests keep their exact shape
  assert.deepEqual(saved, [
    { type: 'slideleft', duration: 0.4, easing: 'ease_in_out' },
    { type: 'fade', duration: 0.4 },
    { type: 'wipeup', duration: 0.3 },
  ]);
  const state = manifestToEditorState({ clip_list: clips.map(({ id, transition_in, transition_duration, transition_easing, ...c }) => c), transitions: saved });
  assert.equal(state.clipList[1].transition_easing, 'ease_in_out');
  assert.equal('transition_easing' in state.clipList[2], false);
  assert.equal('transition_easing' in state.clipList[3], false);
  // and the player plays what was saved
  const segs = buildSegments(state.clipList, { 'clip-0': 2, 'clip-1': 2, 'clip-2': 2, 'clip-3': 2 });
  const t = segs[1].segStart + segs[1].overlap / 4;
  assert.ok(Math.abs(getDrawPlan(segs, t)[1].progress - 0.125) < 1e-9);
});
