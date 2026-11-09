import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EFFECT_PLAYBACK,
  disposeEffectVideos,
  reconcileEffectPlayback,
  wrapEffectTime,
} from './effectPlayback.js';

test('effect timeline wraps a looping overlay to the timeline clock', () => {
  assert.equal(wrapEffectTime(2.75, 1.0, 0.5), 0.25);
  assert.equal(wrapEffectTime(0.75, 1.0, 0.5), 0);
});

test('paused effect seeks to the timeline position before starting', () => {
  const decision = reconcileEffectPlayback({
    timelineTime: 2.25,
    effectStart: 1.0,
    mediaTime: 0,
    mediaDuration: 0.5,
    paused: true,
  });

  assert.equal(decision.action, 'seek-and-play');
  assert.equal(decision.targetTime, 0.25);
  assert.equal(decision.playbackRate, 1);
});

test('small effect drift is corrected with a gentle playback-rate slew', () => {
  const behind = reconcileEffectPlayback({
    timelineTime: 2.25,
    effectStart: 1.0,
    mediaTime: 0.19,
    mediaDuration: 0.5,
    paused: false,
  });
  const ahead = reconcileEffectPlayback({
    timelineTime: 2.25,
    effectStart: 1.0,
    mediaTime: 0.31,
    mediaDuration: 0.5,
    paused: false,
  });

  assert.equal(behind.action, 'slew');
  assert.equal(behind.playbackRate, EFFECT_PLAYBACK.SLEW_FAST_RATE);
  assert.equal(ahead.action, 'slew');
  assert.equal(ahead.playbackRate, EFFECT_PLAYBACK.SLEW_SLOW_RATE);
});

test('large effect drift hard-seeks instead of showing a stale frame', () => {
  const decision = reconcileEffectPlayback({
    timelineTime: 7.2,
    effectStart: 1.0,
    mediaTime: 0.02,
    mediaDuration: 0.5,
    paused: false,
  });

  assert.equal(decision.action, 'seek');
  assert.ok(Math.abs(decision.targetTime - 0.2) < 1e-9);
  assert.equal(decision.playbackRate, 1);
});

function fakeVideo() {
  const calls = [];
  return {
    calls,
    pause: () => calls.push('pause'),
    removeAttribute: (name) => calls.push(`removeAttribute:${name}`),
    load: () => calls.push('load'),
  };
}

test('disposeEffectVideos stops the bare <video> elements the map stores (S4-07)', () => {
  const a = fakeVideo();
  const b = fakeVideo();
  const map = new Map([['fx_a', a], ['fx_b', b]]);
  disposeEffectVideos(map);
  for (const v of [a, b]) {
    assert.deepEqual(v.calls, ['pause', 'removeAttribute:src', 'load']);
  }
  assert.equal(map.size, 0);
});

test('disposeEffectVideos still accepts a { video } wrapper and tolerates a missing map', () => {
  const v = fakeVideo();
  const map = new Map([['fx', { video: v }]]);
  disposeEffectVideos(map);
  assert.deepEqual(v.calls, ['pause', 'removeAttribute:src', 'load']);
  assert.doesNotThrow(() => disposeEffectVideos(null));
});
