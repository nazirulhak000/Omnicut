import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  APPLY_ALL_GROUPS,
  MAX_CLIP_SPEED,
  MIN_CLIP_SPEED,
  SLOW_ZOOM_PRESETS,
  applyPatchToAllClips,
  buildSlowZoomKeyframes,
  cameraKeyframeSummary,
  clampFreezeTail,
  clampHookDuration,
  clampPan,
  clampRotation,
  clampScale,
  clampSpeed,
  clampTrimEnd,
  clampTrimStart,
  clampValue,
  clampVolume,
  clampZoom,
  clearCameraMotionPatch,
  clipPlayedDuration,
  clipSliderCoalesceKey,
  countOtherCameraKeyframeClips,
  bgStyleOf,
  formatShortTime,
  framingResetPatch,
  normalizeSpeed,
  patchAllClipsInState,
  patchClipInState,
  pickApplyAllPatch,
  pillForBgStyle,
  slowZoomPatch,
  summarizeApplyToAll,
  withoutCameraKeyframes,
} from './inspectorModel.js';
import {
  CAMERA_MOTION_LIMITS,
  buildSegments,
  motionTimeAt,
  resolveClipTransforms,
} from './timelineMath.js';
import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';

test('formatShortTime formats seconds into mm:ss.t', () => {
  assert.equal(formatShortTime(0), '00:00.0');
  assert.equal(formatShortTime(5.42), '00:05.4');
  assert.equal(formatShortTime(65.89), '01:05.8');
  assert.equal(formatShortTime(null), '00:00.0');
  assert.equal(formatShortTime(NaN), '00:00.0');
});

test('clampValue clamps within min and max and uses fallback on NaN', () => {
  assert.equal(clampValue(5, 0, 10), 5);
  assert.equal(clampValue(-2, 0, 10), 0);
  assert.equal(clampValue(15, 0, 10), 10);
  assert.equal(clampValue('invalid', 0, 10, 3), 3);
});

test('clampScale clamps caption scale between 0.4 and 2.2', () => {
  assert.equal(clampScale(1.0), 1.0);
  assert.equal(clampScale(0.1), 0.4);
  assert.equal(clampScale(3.0), 2.2);
});

test('clampVolume clamps audio volume between 0.0 and 1.0', () => {
  assert.equal(clampVolume(0.5), 0.5);
  assert.equal(clampVolume(-0.2), 0.0);
  assert.equal(clampVolume(1.5), 1.0);
});

test('clampSpeed accepts the whole render range 0.25 to 4 and clamps outside it', () => {
  assert.equal(clampSpeed(1.5), 1.5);
  assert.equal(clampSpeed(1.25), 1.25);
  assert.equal(clampSpeed(0.25), 0.25);
  assert.equal(clampSpeed(4), 4);
  assert.equal(clampSpeed(0.1), 0.25);
  assert.equal(clampSpeed(5.0), 4.0);
  assert.equal(clampSpeed('bad'), 1.0);
  assert.equal(MIN_CLIP_SPEED, 0.25);
  assert.equal(MAX_CLIP_SPEED, 4);
});

test('speed range matches the renderer clamp in video_editor.py', () => {
  const source = readFileSync(new URL('../../../scripts/video_editor.py', import.meta.url), 'utf8');
  assert.ok(source.includes('speed = min(4.0, max(0.25, speed))'));
});

test('normalizeSpeed keeps two decimals inside the render range', () => {
  assert.equal(normalizeSpeed(1.2500001), 1.25);
  assert.equal(normalizeSpeed('3'), 3);
  assert.equal(normalizeSpeed(0.001), 0.25);
  assert.equal(normalizeSpeed(99), 4);
});

test('numeric trim edits cannot invert a clip or run beyond known source duration', () => {
  assert.equal(clampTrimStart(99, { trim_start: 0, trim_end: 3 }, 4), 2.8);
  assert.equal(clampTrimStart(-2, { trim_end: 3 }, 4), 0);
  assert.equal(clampTrimEnd(0.1, { trim_start: 1 }, 4), 1.2);
  assert.equal(clampTrimEnd(99, { trim_start: 1 }, 4), 4);
  assert.equal(clampTrimEnd('', { trim_start: 1 }, 4), null);
});

test('clampRotation wraps angles correctly to [0, 360)', () => {
  assert.equal(clampRotation(90), 90);
  assert.equal(clampRotation(360), 0);
  assert.equal(clampRotation(450), 90);
  assert.equal(clampRotation(-90), 270);
  assert.equal(clampRotation('bad'), 0);
});

test('clampFreezeTail clamps freeze tail duration between 0.0 and 10.0', () => {
  assert.equal(clampFreezeTail(2.5), 2.5);
  assert.equal(clampFreezeTail(-1), 0.0);
  assert.equal(clampFreezeTail(15), 10.0);
});

test('clampZoom and clampPan clamp viewport parameters properly', () => {
  assert.equal(clampZoom(1.5), 1.5);
  assert.equal(clampZoom(0.8), 1.0);
  assert.equal(clampZoom(4.0), 3.0);

  assert.equal(clampPan(0.2), 0.2);
  assert.equal(clampPan(-1.5), -1.0);
  assert.equal(clampPan(2.0), 1.0);
});

test('clampHookDuration clamps duration between min and max', () => {
  assert.equal(clampHookDuration(3.0, 1.0, 8.0), 3.0);
  assert.equal(clampHookDuration(0.5, 1.0, 8.0), 1.0);
  assert.equal(clampHookDuration(10.0, 1.0, 8.0), 8.0);
});

test('pillForBgStyle and bgStyleOf map presets roundtrip', () => {
  const pill = pillForBgStyle('pill');
  assert.ok(pill);
  assert.equal(bgStyleOf(pill), 'pill');
  assert.equal(bgStyleOf(null), 'none');
  assert.equal(pillForBgStyle('nonexistent'), null);
});

// ─────────────── L2-01: camera keyframes hidden behind the sliders ───────────────

// The shape shot_matching_stage / style_motion_policy.camera_keyframes_for_clip writes.
const pipelineKeyframes = () => [
  { time: 0, zoom: 1.0, pan_x: -0.2, pan_y: 0 },
  { time: 4, zoom: 1.08, pan_x: 0.2, pan_y: 0 },
];

test('a pipeline keyframe track beats the zoom slider value (the L2-01 claim)', () => {
  const clip = { id: 'a', zoom: 1.04, keyframes: pipelineKeyframes() };
  const dragged = { ...clip, zoom: 2.5 };
  // The slider only changes the static base; the keyframes still decide.
  assert.equal(resolveClipTransforms(dragged, 2).zoom, 1.04);
  assert.equal(resolveClipTransforms(dragged, 0).zoom, 1.0);
  // Once the camera motion is cleared the slider value is what plays.
  const cleared = { ...dragged, ...clearCameraMotionPatch(dragged) };
  assert.equal(resolveClipTransforms(cleared, 2).zoom, 2.5);
});

test('cameraKeyframeSummary counts camera points and says which sliders they override', () => {
  assert.deepEqual(cameraKeyframeSummary({}).points, 0);
  assert.deepEqual(cameraKeyframeSummary({ keyframes: [] }).points, 0);
  assert.equal(cameraKeyframeSummary(null).points, 0);

  const both = cameraKeyframeSummary({ keyframes: pipelineKeyframes() });
  assert.equal(both.points, 2);
  assert.equal(both.zoom, true);
  assert.equal(both.pan, true);

  const zoomOnly = cameraKeyframeSummary({ keyframes: [{ time: 0, zoom: 1 }, { time: 2, zoom: 1.1 }] });
  assert.equal(zoomOnly.points, 2);
  assert.equal(zoomOnly.zoom, true);
  assert.equal(zoomOnly.pan, false);

  // The {property, time, value} vocabulary is read too.
  const tagged = cameraKeyframeSummary({ keyframes: [{ property: 'pan_x', time: 1, value: 0.3 }] });
  assert.equal(tagged.points, 1);
  assert.equal(tagged.pan, true);
  assert.equal(tagged.zoom, false);

  // Non-camera and unusable points do not count.
  const noise = cameraKeyframeSummary({
    keyframes: [
      { property: 'opacity', time: 1, value: 0.5 },
      { time: 'x', zoom: 1.2 },
      { time: 1, zoom: 'x' },
      null,
    ],
  });
  assert.equal(noise.points, 0);
});

test('clearCameraMotionPatch drops camera keyframes and keeps anything else', () => {
  assert.deepEqual(clearCameraMotionPatch({ keyframes: pipelineKeyframes() }), { keyframes: [] });
  assert.deepEqual(clearCameraMotionPatch({}), { keyframes: [] });
  const other = { property: 'opacity', time: 1, value: 0.5 };
  assert.deepEqual(
    withoutCameraKeyframes([...pipelineKeyframes(), other]),
    [other],
  );
});

test('framing reset also clears camera keyframes, and only writes them when present', () => {
  assert.deepEqual(framingResetPatch({ zoom: 1.5, keyframes: pipelineKeyframes() }), {
    zoom: undefined,
    pan_x: undefined,
    pan_y: undefined,
    keyframes: [],
  });
  const plain = framingResetPatch({ zoom: 1.5 });
  assert.ok(!('keyframes' in plain));
  assert.deepEqual(Object.keys(plain).sort(), ['pan_x', 'pan_y', 'zoom']);
});

// ─────────────── L2-03: slow zoom presets ───────────────

test('clipPlayedDuration is the played span motionTimeAt clamps to, without the freeze tail', () => {
  const clip = { id: 'a', trim_start: 1, trim_end: 7, speed: 2, freeze_tail: 2 };
  const [seg] = buildSegments([clip], { a: 10 });
  assert.equal(clipPlayedDuration(clip, 10), 3);
  assert.equal(motionTimeAt(seg, seg.segStart + 1000), 3);
  assert.equal(seg.dur, 5, 'segment length still includes the freeze tail');
  // No trim_end: the source duration is the end.
  assert.equal(clipPlayedDuration({ trim_start: 0.5 }, 5.5), 5);
  assert.equal(clipPlayedDuration({}, 0), 0);
});

test('slow zoom builds two keyframes over the played time and stays inside the camera limits', () => {
  const clip = { trim_start: 1, trim_end: 7, speed: 2, zoom: 1.5 };
  const pushIn = buildSlowZoomKeyframes(clip, 10, { direction: 'in', percent: 0.1 });
  assert.deepEqual(pushIn, [{ time: 0, zoom: 1.5 }, { time: 3, zoom: 1.65 }]);

  const pullOut = buildSlowZoomKeyframes({ trim_end: 5 }, 5, { direction: 'out', percent: 0.15 });
  assert.deepEqual(pullOut, [{ time: 0, zoom: 1.15 }, { time: 5, zoom: 1 }]);

  const nearMax = buildSlowZoomKeyframes({ trim_end: 4, zoom: 2.95 }, 4, { direction: 'in', percent: 0.15 });
  assert.deepEqual(nearMax, [{ time: 0, zoom: 2.95 }, { time: 4, zoom: 3 }]);

  const { min, max } = CAMERA_MOTION_LIMITS.zoom;
  for (const preset of SLOW_ZOOM_PRESETS) {
    for (const zoom of [undefined, 1, 1.5, 2.5, 2.99]) {
      const points = buildSlowZoomKeyframes({ trim_end: 6, zoom }, 6, preset);
      for (const point of points || []) {
        assert.ok(point.zoom >= min && point.zoom <= max, `${preset.id} zoom ${zoom}: ${point.zoom}`);
      }
    }
  }
});

test('slow zoom refuses when there is no real move to make', () => {
  assert.equal(buildSlowZoomKeyframes({ trim_end: 4, zoom: 3 }, 4, { direction: 'in', percent: 0.1 }), null);
  assert.equal(buildSlowZoomKeyframes({ trim_end: 4, zoom: 3 }, 4, { direction: 'out', percent: 0.1 }), null);
  assert.equal(buildSlowZoomKeyframes({ trim_end: 0.1 }, 0.1, { direction: 'in', percent: 0.1 }), null);
  assert.equal(buildSlowZoomKeyframes({}, 0, { direction: 'in', percent: 0.1 }), null);
  assert.equal(slowZoomPatch({}, 0, SLOW_ZOOM_PRESETS[0]), null);
});

test('a slow zoom replaces the pipeline motion and drives the same transform as the preview', () => {
  const clip = {
    id: 'a', trim_start: 0, trim_end: 4, zoom: 1.04, keyframes: pipelineKeyframes(),
  };
  const patch = slowZoomPatch(clip, 4, SLOW_ZOOM_PRESETS[0]);
  assert.ok(patch);
  const next = { ...clip, ...patch };
  // The old pan keyframes are gone, so pan falls back to the (unset) static value.
  assert.equal(cameraKeyframeSummary(next).pan, false);
  assert.equal(resolveClipTransforms(next, 1).pan_x, 0);
  // Zoom runs 1.04 -> 1.144 across the 4s played span, linearly.
  assert.equal(resolveClipTransforms(next, 0).zoom, 1.04);
  assert.ok(Math.abs(resolveClipTransforms(next, 2).zoom - 1.092) < 1e-9);
  assert.ok(Math.abs(resolveClipTransforms(next, 4).zoom - 1.144) < 1e-9);
  assert.ok(Math.abs(resolveClipTransforms(next, 9).zoom - 1.144) < 1e-9, 'holds the last value past the end');
  // Non-camera keyframes survive the preset.
  const withOther = slowZoomPatch(
    { ...clip, keyframes: [...pipelineKeyframes(), { property: 'opacity', time: 1, value: 0.5 }] },
    4,
    SLOW_ZOOM_PRESETS[1],
  );
  assert.equal(withOther.keyframes.filter((p) => p.property === 'opacity').length, 1);
  // Clear brings the static sliders back.
  assert.equal(resolveClipTransforms({ ...next, ...clearCameraMotionPatch(next) }, 2).zoom, 1.04);
});

// ─────────────── L2-05 / L7-01: slider drags coalesce into one undo step ───────────────

function sliderHistory() {
  let now = 0;
  const history = createEditorHistoryModel(
    { clipList: [{ id: 'a' }, { id: 'b' }] },
    { now: () => now },
  );
  const tick = (ms) => { now += ms; };
  const drag = (id, field, from, to, steps, stepMs = 16) => {
    for (let i = 1; i <= steps; i += 1) {
      tick(stepMs);
      const value = from + ((to - from) * i) / steps;
      history.set(
        (state) => patchClipInState(state, id, { [field]: value }),
        { coalesceKey: clipSliderCoalesceKey(id, field) },
      );
    }
  };
  const clip = (id) => history.getState().clipList.find((c) => c.id === id);
  return { history, tick, drag, clip };
}

test('the coalesce key is per clip and field', () => {
  assert.equal(clipSliderCoalesceKey('a', 'zoom'), 'clip:a:zoom');
  assert.notEqual(clipSliderCoalesceKey('a', 'zoom'), clipSliderCoalesceKey('b', 'zoom'));
  assert.notEqual(clipSliderCoalesceKey('a', 'zoom'), clipSliderCoalesceKey('a', 'pan_x'));
});

test('one slider drag is one undo step and undo returns to the value before the drag', () => {
  const { history, drag, clip } = sliderHistory();
  history.set((state) => patchClipInState(state, 'a', { mirror: true }));
  drag('a', 'zoom', 1, 2, 40);
  assert.equal(clip('a').zoom, 2);
  assert.equal(history.undo(), true);
  assert.equal(clip('a').zoom, undefined);
  assert.equal(clip('a').mirror, true, 'the earlier edit is still there');
  assert.equal(history.undo(), true);
  assert.equal(clip('a').mirror, undefined);
  assert.equal(history.canUndo(), false);
  // Redo walks the same two steps forward.
  history.redo();
  history.redo();
  assert.equal(clip('a').zoom, 2);
});

test('slider drags on another field or another clip are never merged', () => {
  const { history, drag, clip } = sliderHistory();
  drag('a', 'zoom', 1, 1.5, 10);
  drag('a', 'pan_x', 0, 0.5, 10);
  drag('b', 'pan_x', 0, -0.5, 10);
  assert.equal(history.undo(), true);
  assert.equal(clip('b').pan_x, undefined);
  assert.equal(clip('a').pan_x, 0.5);
  assert.equal(history.undo(), true);
  assert.equal(clip('a').pan_x, undefined);
  assert.equal(clip('a').zoom, 1.5);
  assert.equal(history.undo(), true);
  assert.equal(clip('a').zoom, undefined);
  assert.equal(history.canUndo(), false);
});

test('a discrete edit between two drags of the same slider splits them into two steps', () => {
  const { history, drag, tick, clip } = sliderHistory();
  drag('a', 'zoom', 1, 1.5, 10);
  history.set((state) => patchClipInState(state, 'a', { mirror: true }));
  drag('a', 'zoom', 1.5, 2, 10);
  history.undo();
  assert.equal(clip('a').zoom, 1.5);
  history.undo();
  assert.equal(clip('a').mirror, undefined);
  history.undo();
  assert.equal(clip('a').zoom, undefined);
  assert.equal(history.canUndo(), false);

  // A pause longer than the window also starts a new step.
  const second = sliderHistory();
  second.drag('a', 'zoom', 1, 1.5, 10);
  second.tick(1000);
  second.drag('a', 'zoom', 1.5, 2, 10);
  second.history.undo();
  assert.equal(second.clip('a').zoom, 1.5);
  void tick;
});

test('the undo stack cap survives many slider drags (50 steps hold 50 drags, not 50 ticks)', () => {
  const { history, drag, tick } = sliderHistory();
  for (let i = 0; i < 12; i += 1) {
    drag('a', 'zoom', 1, 2, 30);
    tick(1000);
  }
  let undone = 0;
  while (history.undo()) undone += 1;
  assert.equal(undone, 12);
});

// ─────────────── L2-02: apply a look to every clip ───────────────

const lookClips = () => [
  {
    id: 'a', source_path: 'a.mp4', trim_start: 1, trim_end: 5, brightness: 0.1, zoom: 1.3, pan_x: 0.2, speed: 1.25,
  },
  {
    id: 'b', source_path: 'b.mp4', trim_start: 2, trim_end: 9, keyframes: pipelineKeyframes(),
  },
  {
    id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 3, zoom: 1.3, pan_x: 0.2,
  },
];

test('apply-all groups hold only look fields, never keyframes, trim or source', () => {
  assert.deepEqual(APPLY_ALL_GROUPS.color, ['brightness', 'contrast', 'saturation']);
  assert.deepEqual(APPLY_ALL_GROUPS.framing, ['zoom', 'pan_x', 'pan_y']);
  assert.deepEqual(APPLY_ALL_GROUPS.speed, ['speed']);
  const all = Object.values(APPLY_ALL_GROUPS).flat();
  for (const field of ['keyframes', 'trim_start', 'trim_end', 'source_path', 'id', 'duration']) {
    assert.ok(!all.includes(field), field);
  }
});

test('pickApplyAllPatch copies the group values and leaves unset values unset', () => {
  const [a] = lookClips();
  assert.deepEqual(pickApplyAllPatch(a, 'color'), {
    brightness: 0.1, contrast: undefined, saturation: undefined,
  });
  assert.deepEqual(pickApplyAllPatch(a, 'speed'), { speed: 1.25 });
  assert.equal(pickApplyAllPatch(a, 'nope'), null);
  assert.equal(pickApplyAllPatch(null, 'color'), null);
});

test('applyPatchToAllClips applies the look and leaves keyframes, trim and source alone', () => {
  const clips = lookClips();
  const next = applyPatchToAllClips(clips, pickApplyAllPatch(clips[0], 'framing'));
  assert.equal(next[1].zoom, 1.3);
  assert.equal(next[1].pan_x, 0.2);
  assert.equal(next[1].pan_y, undefined);
  assert.equal(next[1].keyframes, clips[1].keyframes, 'keyframes are the same array, not copied or cleared');
  assert.equal(next[1].trim_start, 2);
  assert.equal(next[1].trim_end, 9);
  assert.equal(next[1].source_path, 'b.mp4');
  assert.equal(next[0], clips[0], 'a clip that already matches is returned untouched');
  assert.equal(next[2], clips[2]);
  assert.equal(clips[1].zoom, undefined, 'the input is not mutated');
});

test('applyPatchToAllClips drops fields outside the look groups and reports no change', () => {
  const clips = lookClips();
  const sneaky = {
    keyframes: [], trim_start: 9, trim_end: 9, source_path: 'x.mp4', id: 'zzz', duration: 1,
  };
  assert.equal(applyPatchToAllClips(clips, sneaky), clips);
  const mixed = applyPatchToAllClips(clips, { speed: 2, keyframes: [], trim_start: 9 });
  assert.equal(mixed[0].speed, 2);
  assert.equal(mixed[0].trim_start, 1);
  assert.equal(mixed[1].keyframes, clips[1].keyframes);
});

test('applyPatchToAllClips returns the same list when every clip already matches', () => {
  const clips = lookClips();
  assert.equal(applyPatchToAllClips(clips, {}), clips, 'an empty patch changes nothing');
  const same = [{ id: 'a', brightness: 0.1 }, { id: 'b', brightness: 0.1 }];
  assert.equal(applyPatchToAllClips(same, { brightness: 0.1 }), same);
});

test('summarizeApplyToAll counts changed clips and camera-keyframe clips for framing only', () => {
  const clips = lookClips();
  const framing = summarizeApplyToAll(clips, pickApplyAllPatch(clips[0], 'framing'));
  assert.deepEqual(framing, { changed: 1, cameraKeyframeClips: 1 });
  const color = summarizeApplyToAll(clips, pickApplyAllPatch(clips[0], 'color'));
  assert.deepEqual(color, { changed: 2, cameraKeyframeClips: 0 });
  assert.deepEqual(summarizeApplyToAll([], { speed: 2 }), { changed: 0, cameraKeyframeClips: 0 });
});

test('countOtherCameraKeyframeClips skips the selected clip', () => {
  const clips = lookClips();
  assert.equal(countOtherCameraKeyframeClips(clips, 'a'), 1);
  assert.equal(countOtherCameraKeyframeClips(clips, 'b'), 0);
  assert.equal(countOtherCameraKeyframeClips(undefined, 'a'), 0);
});

test('apply-all through history is a single undo step and a no-op adds none', () => {
  const history = createEditorHistoryModel({ clipList: lookClips(), cuesList: [] });
  const before = history.getState();
  assert.equal(
    history.set((state) => patchAllClipsInState(state, pickApplyAllPatch(before.clipList[0], 'framing'))),
    true,
  );
  assert.equal(history.getState().clipList.every((c) => c.zoom === 1.3), true);
  assert.equal(
    history.set((state) => patchAllClipsInState(state, pickApplyAllPatch(before.clipList[0], 'framing'))),
    false,
    'applying the same look again changes nothing and pushes no undo step',
  );
  assert.equal(history.undo(), true);
  assert.equal(history.getState(), before);
  assert.equal(history.canUndo(), false);
});
