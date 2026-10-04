import test from 'node:test';
import assert from 'node:assert/strict';
import {
  KEYFRAME_TOLERANCE,
  keyframeStateAt,
  toggleKeyframePatch,
  keyframeSeekTarget,
} from './clipKeyframeOps.js';

test('keyframeStateAt: identifies active keyframe at playhead time within tolerance', () => {
  const seg = {
    segStart: 10,
    segEnd: 20,
    srcDur: 10,
    clip: {
      id: 'c1',
      speed: 1,
      trim_start: 0,
      trim_end: 10,
      zoom: 1.2,
      keyframes: [
        { time: 2.0, zoom: 1.0 },
        { time: 5.0, zoom: 1.5 },
      ],
    },
  };

  // Exactly at 2.0s inside clip -> timeline 12.0s
  const st1 = keyframeStateAt(seg, 12.0);
  assert.equal(st1.inside, true);
  assert.equal(st1.activeIndex, 0);
  assert.equal(st1.prev, null);
  assert.deepEqual(st1.next, { time: 5.0, zoom: 1.5 });

  // Between keyframes at timeline 14.0s (local time 4.0s)
  const st2 = keyframeStateAt(seg, 14.0);
  assert.equal(st2.inside, true);
  assert.equal(st2.activeIndex, -1);
  assert.deepEqual(st2.prev, { time: 2.0, zoom: 1.0 });
  assert.deepEqual(st2.next, { time: 5.0, zoom: 1.5 });

  // Playhead outside clip (timeline 5.0s < segStart 10.0s)
  const stOutside = keyframeStateAt(seg, 5.0);
  assert.equal(stOutside.inside, false);
});

test('toggleKeyframePatch: removes keyframe if active, adds new keyframe if none', () => {
  const seg = {
    segStart: 0,
    segEnd: 10,
    srcDur: 10,
    clip: {
      id: 'c1',
      speed: 1,
      zoom: 1.2,
      pan_x: 0.1,
      pan_y: -0.1,
      keyframes: [{ time: 3.0, zoom: 1.5 }],
    },
  };

  // At 3.0s: toggle removes the keyframe
  const patchRemove = toggleKeyframePatch(seg, 3.0);
  assert.deepEqual(patchRemove, { keyframes: undefined });

  // At 6.5s: toggle adds a new keyframe with current clip values
  const patchAdd = toggleKeyframePatch(seg, 6.5);
  assert.equal(patchAdd.keyframes.length, 2);
  assert.equal(patchAdd.keyframes[0].time, 3.0);
  assert.equal(patchAdd.keyframes[1].time, 6.5);
  assert.equal(patchAdd.keyframes[1].zoom, 1.2);
  assert.equal(patchAdd.keyframes[1].pan_x, 0.1);
  assert.equal(patchAdd.keyframes[1].pan_y, -0.1);

  // Outside clip: returns null
  assert.equal(toggleKeyframePatch(seg, 15.0), null);
});

test('keyframeSeekTarget: seeks to prev or next keyframe time on timeline', () => {
  const seg = {
    segStart: 10,
    segEnd: 25,
    srcDur: 15,
    clip: {
      id: 'c1',
      speed: 1,
      keyframes: [
        { time: 2.0 },
        { time: 5.0 },
        { time: 10.0 },
      ],
    },
  };

  // At timeline 16.0s (local time 6.0s):
  // Prev is at local 5.0s -> timeline 15.0s
  assert.equal(keyframeSeekTarget(seg, 16.0, -1), 15.0);
  // Next is at local 10.0s -> timeline 20.0s
  assert.equal(keyframeSeekTarget(seg, 16.0, 1), 20.0);

  // At first keyframe (local 2.0s -> timeline 12.0s): prev is null
  assert.equal(keyframeSeekTarget(seg, 12.0, -1), null);
  // At last keyframe (local 10.0s -> timeline 20.0s): next is null
  assert.equal(keyframeSeekTarget(seg, 20.0, 1), null);
});
