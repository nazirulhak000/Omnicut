// Deterministic CPU microbenchmark; no media, browser or production files touched.
import { performance } from 'node:perf_hooks';
import { buildSegments, getDrawPlan, totalDuration } from '../frontend/src/lib/timelineMath.js';
import { createPreviewTimelineIndex, pauseInactivePreviewVideos } from '../frontend/src/lib/previewTimelineScheduler.js';

const repeats = 7;
const lookups = 12000;
let checksum = 0;
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
function measure(fn) {
  fn(); // JIT warmup
  const samples = [];
  for (let repeat = 0; repeat < repeats; repeat++) {
    const start = performance.now();
    fn();
    samples.push(performance.now() - start);
  }
  return Number(median(samples).toFixed(3));
}
for (const clipCount of [100, 1000, 5000]) {
  const segments = buildSegments(Array.from({ length: clipCount }, (_, i) => ({
    id: `clip-${i}`, trim_start: 0, trim_end: 2, speed: i % 5 === 0 ? 2 : 1,
    transition_in: i % 3 === 0 ? 'cut' : 'fade', transition_duration: .4,
  })));
  const index = createPreviewTimelineIndex(segments);
  const end = totalDuration(segments);
  const times = Array.from({ length: lookups }, (_, i) => ((i * 7919) % lookups) / lookups * end);
  const baselineLookupMs = measure(() => {
    for (const t of times) {
      checksum += getDrawPlan(segments, t).length;
      checksum += segments.find((s) => s.segStart > t && s.segStart <= t + 1.2) ? 1 : 0;
    }
  });
  const indexedLookupMs = measure(() => {
    for (const t of times) {
      checksum += index.planAt(t).length;
      checksum += index.upcomingAt(t) ? 1 : 0;
    }
  });
  const videos = Object.fromEntries(segments.map((s) => [s.clip.id, { paused: true }]));
  const previousIds = new Set(['clip-0', 'clip-1']);
  const neededIds = new Set(['clip-1', 'clip-2']);
  const baselinePauseMs = measure(() => {
    for (let i = 0; i < 1000; i++) {
      for (const [id, v] of Object.entries(videos)) {
        if (v && !v.paused && !neededIds.has(id)) { v.playbackRate = 1; v.pause(); }
      }
    }
  });
  const activePauseMs = measure(() => {
    for (let i = 0; i < 1000; i++) pauseInactivePreviewVideos(previousIds, neededIds, videos);
  });
  console.log(JSON.stringify({ clipCount, lookups, medianOf: repeats, baselineLookupMs, indexedLookupMs,
    lookupSpeedup: Number((baselineLookupMs / indexedLookupMs).toFixed(2)),
    pauseIterations: 1000, baselinePauseMs, activePauseMs }));
}
if (!checksum) throw Error('benchmark produced no plans');
