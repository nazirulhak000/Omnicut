import { getDrawPlan } from './timelineMath.js';

/** Index only temporal lookup. The shared renderer math still owns every frame. */
export function createPreviewTimelineIndex(segments) {
  const ordered = segments.every((seg, i) => Number.isFinite(seg.segStart)
    && Number.isFinite(seg.segEnd) && (i === 0 || (
      seg.segStart >= segments[i - 1].segStart && seg.segEnd >= segments[i - 1].segEnd
    )));
  const after = (t) => {
    let lo = 0;
    let hi = segments.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (segments[mid].segStart <= t) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  };
  return {
    planAt(t) {
      if (!ordered || !Number.isFinite(t) || !segments.length) return getDrawPlan(segments, t);
      let idx = after(t) - 1;
      if (idx < 0 || !(t < segments[idx].segEnd)) idx = t < 0 ? 0 : segments.length - 1;
      // Include the preceding clip so all transition/easing/freeze/source-time
      // calculations execute in the original shared implementation unchanged.
      return getDrawPlan(segments.slice(Math.max(0, idx - 1), idx + 1), t);
    },
    upcomingAt(t, lookahead = 1.2) {
      if (!ordered || !Number.isFinite(t)) {
        return segments.find((seg) => seg.segStart > t && seg.segStart <= t + lookahead);
      }
      const seg = segments[after(t)];
      return seg && seg.segStart <= t + lookahead ? seg : undefined;
    },
  };
}

/** Only previously active decoders can need pausing at a boundary/seek. */
export function pauseInactivePreviewVideos(previousIds, neededIds, videos) {
  for (const id of previousIds) {
    if (neededIds.has(id)) continue;
    const video = videos[id];
    if (video && !video.paused) {
      video.playbackRate = 1;
      video.pause();
    }
  }
}
