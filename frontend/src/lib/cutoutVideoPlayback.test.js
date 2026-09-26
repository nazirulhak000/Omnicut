import test from 'node:test';
import assert from 'node:assert/strict';
import { createCutoutVideoPlayback } from './cutoutVideoPlayback.js';

function decoder({ callbacks = true } = {}) {
  const events = new Map();
  let callback;
  const video = {
    currentTime: 0, duration: 120, readyState: 4, paused: true, seeking: false, playbackRate: 1,
    addEventListener: (name, fn) => events.set(name, fn),
    removeEventListener: (name) => events.delete(name),
    play() { this.paused = false; return Promise.resolve(); },
    pause() { this.paused = true; }, removeAttribute() {}, load() {},
    cancelVideoFrameCallback() { callback = null; },
  };
  if (callbacks) video.requestVideoFrameCallback = (fn) => { callback = fn; return 1; };
  return { video, events, present: (time) => callback?.(0, { mediaTime: time }) };
}

for (const rate of [0.5, 1, 1.3155, 2, 4]) {
  test(`source clock runs continuously at ${rate}x without repeated hard seeks`, async () => {
    const { video, present } = decoder();
    const playback = createCutoutVideoPlayback(video);
    let available = 0;
    for (let i = 0; i < 600; i += 1) {
      if (!video.paused) video.currentTime += video.playbackRate / 60;
      const target = i * rate / 60;
      present(Math.floor(video.currentTime * 30 + 1e-6) / 30);
      available += playback.sync({ time: target, isPlaying: true, rate, now: i * 1000 / 60 });
      await Promise.resolve();
    }
    assert.ok(playback.metrics.seeks <= 1, JSON.stringify(playback.metrics));
    assert.ok(available / 600 > 0.99, String(available));
    assert.ok(Math.abs(video.currentTime - 599 * rate / 60) <= 1 / 30);
  });
}

test('paused rapid seeks reject the previous decoded frame and show only the latest target', () => {
  const { video, present } = decoder();
  const playback = createCutoutVideoPlayback(video);
  playback.sync({ time: 12, now: 0 });
  video.seeking = true;
  playback.sync({ time: 2, now: 10 });
  assert.equal(video.currentTime, 2);
  video.seeking = false;
  present(12);
  assert.equal(playback.ready(), false);
  present(2);
  assert.equal(playback.ready(), true);
  assert.equal(video.paused, true);
  for (let i = 0; i < 30; i += 1) playback.sync({ time: 2, now: 20 + i * 16 });
  assert.equal(playback.metrics.seeks, 2);
});

test('freeze holds the final artifact frame, teardown releases callbacks and listeners', () => {
  const { video, present, events } = decoder();
  const playback = createCutoutVideoPlayback(video);
  video.duration = 2;
  playback.sync({ time: 2, isPlaying: false, now: 0 });
  present(59 / 30);
  assert.equal(playback.ready(), true);
  assert.equal(video.paused, true);
  playback.dispose();
  assert.equal(events.size, 0);
  assert.equal(playback.ready(), false);
});

test('seeked fallback supports browsers without video frame callbacks', () => {
  const { video, events } = decoder({ callbacks: false });
  const playback = createCutoutVideoPlayback(video);
  playback.sync({ time: 3, now: 0 });
  events.get('seeked')();
  assert.equal(playback.ready(), true);
});
