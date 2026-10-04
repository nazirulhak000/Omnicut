import test from 'node:test';
import assert from 'node:assert/strict';

import {
  FPS,
  MIN_CLIP_DURATION,
  buildSegments,
  formatTimecode,
  resolveSplitTarget,
  snapSeekTime,
  snapToFrame,
  splitClipAt,
} from './timelineMath.js';
import { frameTickSpacing, tickStep } from './timelineTrackModel.js';

const clip = (id, extra = {}) => ({
  id, source_path: `${id}.mp4`, trim_start: 0, trim_end: 4, speed: 1,
  transition_in: 'cut', keyframes: [], ...extra,
});

// Two 4 second clips back to back: A = [0, 4), B = [4, 8)
const twoClips = () => buildSegments([clip('a'), clip('b')], { a: 10, b: 10 });

test('formatTimecode keeps the tenths form by default', () => {
  assert.equal(formatTimecode(4.2), '00:04.2');
  assert.equal(formatTimecode(65.8), '01:05.8');
  assert.equal(formatTimecode(null), '00:00.0');
});

test('formatTimecode frames mode prints mm:ss:ff at 30 fps', () => {
  const f = (s) => formatTimecode(s, { frames: true });
  assert.equal(f(0), '00:00:00');
  assert.equal(f(1 / 30), '00:00:01');
  assert.equal(f(29 / 30), '00:00:29');
  assert.equal(f(1), '00:01:00');
  assert.equal(f(4.2), '00:04:06', '4.2 s is frame 126, never frame 125 from float error');
  assert.equal(f(65.8), '01:05:24');
  assert.equal(f(59.999), '01:00:00', 'rounds up into the next second/minute, ff never reaches fps');
  assert.equal(f(-3), '00:00:00');
  assert.equal(f(Number.NaN), '00:00:00');
  assert.equal(formatTimecode(1, { frames: true, fps: 25 }), '00:01:00');
  assert.equal(formatTimecode(1.04, { frames: true, fps: 25 }), '00:01:01');
});

test('snapToFrame rounds to the nearest whole frame and stays a float of seconds', () => {
  assert.equal(FPS, 30);
  assert.equal(snapToFrame(1.23), 37 / 30);
  assert.equal(snapToFrame(1.2), 36 / 30);
  assert.equal(snapToFrame(3), 3);
  assert.ok(Object.is(snapToFrame(-0.001), 0), 'never returns -0');
  assert.equal(snapToFrame(Number.NaN), 0);
  assert.equal(snapToFrame(undefined), 0);
  for (const t of [0.01, 0.499, 1.5, 7.77, 59.99]) {
    assert.equal(snapToFrame(snapToFrame(t)), snapToFrame(t), `idempotent for ${t}`);
    assert.ok(Math.abs(snapToFrame(t) - t) <= 1 / (2 * FPS) + 1e-9, `within half a frame for ${t}`);
  }
});

test('stepping one frame from a snapped playhead lands on the next frame exactly once', () => {
  let t = 0;
  for (let frame = 1; frame <= 120; frame += 1) {
    t = snapToFrame(t + 1 / FPS);
    assert.equal(Math.round(t * FPS), frame);
  }
});

test('snapSeekTime never rounds a seek to a clip start back into the previous clip', () => {
  // Clip B starts at 2.98: nearest frame would be 2.9667 (inside clip A).
  const segs = [
    { segStart: 0, segEnd: 2.98 },
    { segStart: 2.98, segEnd: 6 },
  ];
  const at = snapSeekTime(2.98, segs);
  assert.ok(at >= 2.98 - 1e-9, `seek ${at} must not be before the clip start`);
  assert.ok(Math.abs(at * FPS - Math.round(at * FPS)) < 1e-9, 'still on the frame grid');
  assert.equal(snapSeekTime(2.98 + 1e-9, segs), at, 'float fuzz at the start still counts as the start');
  // Away from clip starts it is a plain nearest-frame snap.
  assert.equal(snapSeekTime(1.23, segs), snapToFrame(1.23));
  assert.equal(snapSeekTime(1.23), snapToFrame(1.23), 'segments are optional');
  assert.equal(snapSeekTime('x', segs), 0);
});

test('resolveSplitTarget prefers the selected clip when the playhead is inside it', () => {
  const segs = twoClips();
  const target = resolveSplitTarget(segs, segs[1], 5.01);
  assert.equal(target.seg, segs[1]);
  assert.equal(target.time, snapToFrame(5.01));
});

test('resolveSplitTarget falls back to the clip under the playhead (L1-05)', () => {
  const segs = twoClips();
  // Clip B is selected but the playhead sits inside clip A.
  const target = resolveSplitTarget(segs, segs[1], 2);
  assert.equal(target.seg, segs[0], 'cuts the clip under the playhead, not nothing');
  assert.equal(target.message, undefined);
  // And with nothing selected it behaves the same.
  assert.equal(resolveSplitTarget(segs, null, 6).seg, segs[1]);
});

test('resolveSplitTarget explains every refusal instead of staying silent', () => {
  const segs = twoClips();
  const empty = resolveSplitTarget([], null, 1);
  assert.equal(empty.seg, null);
  assert.match(empty.message, /ยังไม่มีคลิป/);

  const past = resolveSplitTarget(segs, segs[0], 20);
  assert.equal(past.seg, null);
  assert.match(past.message, /ไม่ได้อยู่บนคลิป/);

  const nearEdge = resolveSplitTarget(segs, segs[0], 0.1);
  assert.equal(nearEdge.seg, null);
  assert.match(nearEdge.message, /ใกล้ขอบ/);
  assert.ok(nearEdge.message.includes(String(MIN_CLIP_DURATION)));

  for (const result of [empty, past, nearEdge]) {
    assert.ok(!/\.\.\.|…/.test(result.message), 'no ellipsis in UI text');
  }
});

test('resolveSplitTarget agrees with splitClipAt for every frame (button state == command)', () => {
  const segs = twoClips();
  const makeId = (() => { let n = 0; return () => `n${++n}`; })();
  for (const selected of [null, segs[0], segs[1]]) {
    for (let frame = -5; frame <= 8 * FPS + 30; frame += 1) {
      const playhead = frame / FPS;
      const target = resolveSplitTarget(segs, selected, playhead);
      if (target.seg) {
        assert.ok(splitClipAt(target.seg, target.time, makeId), `frame ${frame}: promised cut must succeed`);
        assert.equal(target.message, undefined);
      } else {
        assert.equal(typeof target.message, 'string');
        for (const seg of segs) {
          assert.equal(splitClipAt(seg, target.time, makeId), null, `frame ${frame}: refused cut must be impossible`);
        }
      }
    }
  }
});

test('resolveSplitTarget picks the incoming clip inside a transition overlap when the outgoing one is too short', () => {
  // B fades in over the last 0.5 s of A, so [3.5, 4) belongs to both.
  const segs = buildSegments(
    [clip('a'), clip('b', { transition_in: 'fade', transition_duration: 0.5 })],
    { a: 10, b: 10 },
  );
  const t = segs[1].segStart + 0.3; // 0.2 s before A ends: too close for A
  const target = resolveSplitTarget(segs, null, t);
  assert.equal(target.seg, segs[1]);
});

test('splitting keeps what the left piece and keyframes already had (no new drift)', () => {
  const keyframes = [{ time: 0, zoom: 1 }, { time: 3, zoom: 1.4 }];
  const segs = buildSegments(
    [clip('a', { keyframes, transition_in: 'fade', transition_duration: 0.4 }), clip('b')],
    { a: 10, b: 10 },
  );
  // The cut itself is the only thing the frame snap may change.
  const target = resolveSplitTarget(segs, segs[1], 2);
  assert.equal(target.seg, segs[0]);
  let n = 0;
  const [left, right] = splitClipAt(target.seg, target.time, () => `p${++n}`);
  assert.equal(left.trim_start, 0);
  assert.equal(left.trim_end, right.trim_start, 'pieces meet exactly at the cut');
  assert.ok(Math.abs(right.trim_start - 2) < 1 / (2 * FPS) + 1e-9, 'cut within half a frame of the playhead');
  // Keyframes are split at the cut (B4), not copied: the left half ends on
  // the interpolated value at the cut, the right half starts from it.
  const zoomAtCut = 1 + 0.4 * (2 / 3);
  assert.deepEqual(left.keyframes, [keyframes[0], { time: 2, property: 'zoom', value: zoomAtCut }]);
  assert.deepEqual(right.keyframes, [{ time: 0, property: 'zoom', value: zoomAtCut }, { time: 1, zoom: 1.4 }]);
  assert.deepEqual(keyframes, [{ time: 0, zoom: 1 }, { time: 3, zoom: 1.4 }], 'source keyframes untouched');
  assert.equal(left.transition_in, 'fade');
  assert.equal(right.transition_in, 'cut');
});

test('frameTickSpacing draws frame ticks only when a frame is wide enough to see', () => {
  assert.equal(frameTickSpacing(10), null);
  assert.equal(frameTickSpacing(50), null);
  assert.equal(frameTickSpacing(100), null);
  assert.ok(Math.abs(frameTickSpacing(200) - 200 / 30) < 1e-12, 'top zoom step shows frames');
  assert.equal(frameTickSpacing(Number.NaN), null);
  assert.equal(frameTickSpacing(60, 10, 6), 6);
  // The 1 s labels stay readable at the zoom where frames appear.
  assert.equal(tickStep(200), 1);
});
