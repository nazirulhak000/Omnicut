import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSegments, getDrawPlan, totalDuration, TRANSITIONS } from './timelineMath.js';
import { createPreviewTimelineIndex, pauseInactivePreviewVideos } from './previewTimelineScheduler.js';

function fixture(count = 120) {
  return buildSegments(Array.from({ length: count }, (_, i) => ({
    id: `clip-${i}`, trim_start: (i % 7) / 3, trim_end: 3 + (i % 7) / 3,
    speed: [.5, 1, 1.5, 2][i % 4], freeze_tail: i % 11 === 0 ? .8 : 0,
    ...(i % 13 === 0 ? { held_source_time: 2.1 } : {}),
    transition_in: i % 3 === 0 ? 'cut' : TRANSITIONS[i % TRANSITIONS.length].id,
    transition_duration: [.1, .4, 1, 2][i % 4],
    transition_easing: ['linear', 'ease_in', 'ease_out', 'ease_in_out'][i % 4],
  })));
}

function assertEquivalent(segments, times) {
  const index = createPreviewTimelineIndex(segments);
  for (const t of times) {
    assert.deepEqual(index.planAt(t), getDrawPlan(segments, t), `draw plan at ${t}`);
    assert.equal(index.upcomingAt(t), segments.find((s) => s.segStart > t && s.segStart <= t + 1.2), `preroll at ${t}`);
  }
}

test('indexed playback retains every 30fps frame including speed, freeze and all transition geometries', () => {
  const segments = fixture();
  assertEquivalent(segments, Array.from({ length: Math.ceil(totalDuration(segments) * 30) }, (_, i) => i / 30));
});

test('random/backward seeks, exact boundaries, overlap midpoint and out-of-range time match shared math', () => {
  const segments = fixture(250);
  const end = totalDuration(segments);
  let seed = 42;
  const times = [-10, -.001, 0, end, end + .001, end + 10, NaN, Infinity, -Infinity];
  for (let i = 0; i < 1500; i++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    times.push((seed / 2 ** 32) * end);
  }
  for (const seg of [...segments].reverse()) {
    times.push(seg.segStart, seg.segStart - .001, seg.segEnd, seg.segEnd - .001,
      seg.segStart + seg.overlap / 2, seg.segStart + seg.overlap);
  }
  assertEquivalent(segments, times);
});

test('empty, duplicate starts, positive initial gap and gaps preserve original fallback semantics', () => {
  assertEquivalent([], [-1, 0, 1]);
  const base = fixture(3);
  const duplicate = base.map((s) => ({ ...s, segStart: 0, segEnd: 3 }));
  assertEquivalent(duplicate, [-1, 0, .1, 1.5, 3, 10]);
  const gaps = base.map((s, i) => ({ ...s, segStart: 5 + i * 4, segEnd: 6 + i * 4, isFade: false }));
  assertEquivalent(gaps, [-1, 0, 4, 5, 6, 7, 9, 10, 13, 14, 20]);
});

test('nonmonotonic starts/ends and invalid timestamps use the original scan', () => {
  const base = fixture(4);
  assertEquivalent([base[2], base[0], base[3], base[1]], [-1, 0, 1, 2, 3, 4, 5, 20]);
  assertEquivalent(base.map((s, i) => ({ ...s, segEnd: i === 1 ? 100 : s.segEnd })), [0, 1, 3, 6, 30, 99, 101]);
  assertEquivalent(base.map((s, i) => ({ ...s, segStart: i === 1 ? NaN : s.segStart })), [0, 1, 3, 6, 30]);
});

test('decoder scheduling pauses outgoing transition videos once and leaves active/preroll untouched', () => {
  const calls = [];
  const video = (id, paused = false) => ({ paused, playbackRate: 2, pause() { this.paused = true; calls.push(id); } });
  const videos = { out: video('out'), incoming: video('incoming'), preroll: video('preroll', true), removed: undefined };
  pauseInactivePreviewVideos(new Set(['out', 'incoming', 'removed']), new Set(['incoming']), videos);
  pauseInactivePreviewVideos(new Set(['out']), new Set(['incoming']), videos);
  assert.deepEqual(calls, ['out']);
  assert.equal(videos.out.playbackRate, 1);
  assert.equal(videos.incoming.playbackRate, 2);
  assert.equal(videos.incoming.paused, false);
  assert.equal(videos.preroll.paused, true);
});

test('active decoder scan is bounded by previous plan size even on a many-clip timeline', () => {
  const reads = [];
  const videos = new Proxy({}, { get(_target, id) { reads.push(id); return { paused: true }; }, ownKeys() { throw Error('must not enumerate all videos'); } });
  pauseInactivePreviewVideos(new Set(['old-a', 'old-b']), new Set(['old-b', 'new']), videos);
  assert.deepEqual(reads, ['old-a']);
});
