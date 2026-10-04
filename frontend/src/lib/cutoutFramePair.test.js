import test from 'node:test';
import assert from 'node:assert/strict';
import { cutoutFramesMatch, createCutoutFramePair, trackPresentedSource } from './cutoutFramePair.js';

test('pair timestamps include artifact origin and reject adjacent 30fps frames', () => {
  for (const speed of [0.5, 1, 1.3155, 2, 4]) {
    const time = 8 + speed / 30;
    assert.equal(cutoutFramesMatch(time, time - 8, 8), true);
    assert.equal(cutoutFramesMatch(time, time - 8 + 1 / 30, 8), false);
  }
  assert.equal(cutoutFramesMatch(null, 0, 0), false);
});

test('decoded clock remains at displayed frame and clears on seek/source swap', () => {
  const events = new Map(); let callback; let cancelled = false;
  const video = { currentTime: 5.2, paused: false, seeking: false,
    addEventListener: (name, fn) => events.set(name, fn),
    removeEventListener: name => events.delete(name),
    requestVideoFrameCallback: fn => { callback = fn; return 1; },
    cancelVideoFrameCallback: () => { cancelled = true; },
  };
  const clock = trackPresentedSource(video);
  assert.equal(clock.time(), null);
  callback(0, { mediaTime: 5 });
  assert.equal(clock.time(), 5);
  video.currentTime = 5.4;
  assert.equal(clock.time(), 5);
  events.get('seeking')();
  assert.equal(clock.time(), null);
  callback(0, { mediaTime: 8 });
  assert.equal(clock.time(), 8);
  events.get('emptied')();
  assert.equal(clock.time(), null);
  clock.dispose();
  assert.equal(events.size, 0); assert.equal(cancelled, true);
});

test('holds a complete pair on mask lag, never reuses it across seek or artifact switch', () => {
  const canvas = () => ({ getContext: () => ({ drawImage() {}, clearRect() {} }) });
  const pairs = createCutoutFramePair(canvas);
  const source = { videoWidth: 64, videoHeight: 64, readyState: 4, seeking: false };
  const args = { source, mask: { readyState: 4 }, sourceTime: 8, maskTime: 0,
    sourceStart: 8, fps: 30, requestedTime: 8, artifactKey: 'a' };
  const subject = pairs.resolve(args);
  assert.ok(subject._cutoutSourceFrame);
  assert.equal(pairs.resolve({ ...args, sourceTime: 8.1, requestedTime: 8.1 }), subject);
  assert.equal(pairs.resolve({ ...args, sourceTime: 8.4, requestedTime: 8.4 }), null);
  assert.ok(pairs.resolve(args));
  source.seeking = true;
  assert.equal(pairs.resolve(args), null);
  source.seeking = false;
  assert.ok(pairs.resolve(args));
  assert.equal(pairs.resolve({ ...args, artifactKey: 'b', maskTime: 0.1 }), null);
  assert.ok(pairs.resolve(args));
  assert.equal(pairs.resolve({ ...args, sourceTime: 12, requestedTime: 12 }), null);
});
