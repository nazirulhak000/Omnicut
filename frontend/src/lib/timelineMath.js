// Single source of truth for sequence timing, shared by SequencePlayer
// (canvas preview) and the editor Timeline. Must stay in lockstep with
// scripts/video_editor.py's clip_list branch -- if the two drift, what the
// user scrubs stops matching what Apply renders.

export const FADE_DURATION = 0.4;   // == video_editor.py FADE_DURATION
export const FPS = 30;              // == config.py FPS
export const MIN_CLIP_DURATION = 0.2;

// Zoom steps in pixels-per-second of timeline.
export const ZOOM_LEVELS = [10, 25, 50, 100, 200];
export const DEFAULT_ZOOM_INDEX = 2;

/** Kept length of a clip on the sequence timeline, after trim and speed. */
export function clipDuration(clip, srcDuration) {
  const end = clip.trim_end ?? srcDuration ?? 0;
  const raw = end - (clip.trim_start || 0);
  const speed = clip.speed || 1;
  return Math.max(MIN_CLIP_DURATION, raw / speed);
}

/**
 * Lay clips out on one timeline. A "fade" boundary overlaps the previous
 * clip by FADE_DURATION, so it eats that much from the running total --
 * same bookkeeping as video_editor.py's has_fade reduction.
 *
 * durations: { [clip.id]: sourceDurationSeconds }
 */
export function buildSegments(clips, durations = {}) {
  let acc = 0;
  return clips.map((clip, i) => {
    const srcDur = durations[clip.id] || 0;
    const dur = clipDuration(clip, srcDur);
    const isFade = i > 0 && clip.transition_in === 'fade';
    const segStart = i === 0 ? 0 : (isFade ? acc - FADE_DURATION : acc);
    const segEnd = segStart + dur;
    acc = segEnd;
    return { clip, index: i, srcDur, dur, isFade, segStart, segEnd };
  });
}

export function totalDuration(segments) {
  return segments.length ? segments[segments.length - 1].segEnd : 0;
}

/** Source-file time for a global sequence time inside one segment. */
export function localTimeAt(seg, t) {
  const speed = seg.clip.speed || 1;
  return (seg.clip.trim_start || 0) + (t - seg.segStart) * speed;
}

/**
 * Which clip(s) to draw at global time `t`, and at what alpha: two entries
 * (outgoing + incoming) inside a fade's overlap window, one otherwise.
 */
export function getDrawPlan(segments, t) {
  if (!segments.length) return [];
  // Search from the end: inside a fade's overlap window BOTH the outgoing
  // and incoming segments contain `t`, and the incoming one has to win --
  // it owns the crossfade. (findIndex from the front returns the outgoing
  // clip, which silently disabled the blend entirely.)
  let idx = -1;
  for (let i = segments.length - 1; i >= 0; i--) {
    if (t >= segments[i].segStart && t < segments[i].segEnd) { idx = i; break; }
  }
  if (idx === -1) idx = t < 0 ? 0 : segments.length - 1;

  const seg = segments[idx];
  const plan = [{ seg, localTime: localTimeAt(seg, t), alpha: 1 }];

  if (seg.isFade && idx > 0 && t < seg.segStart + FADE_DURATION) {
    const prevSeg = segments[idx - 1];
    const alpha = Math.max(0, Math.min(1, (t - seg.segStart) / FADE_DURATION));
    plan[0] = { seg: prevSeg, localTime: localTimeAt(prevSeg, t), alpha: 1 - alpha };
    plan.push({ seg, localTime: localTimeAt(seg, t), alpha });
  }
  return plan;
}

/** Snap `t` to the nearest candidate within `tolerance` seconds. */
export function snapTime(t, candidates, tolerance) {
  let best = t;
  let bestDist = tolerance;
  for (const c of candidates) {
    const d = Math.abs(c - t);
    if (d < bestDist) { bestDist = d; best = c; }
  }
  return best;
}

/** Every time a drag should snap to: clip edges plus the playhead. */
export function snapCandidates(segments, playhead) {
  const out = [0, playhead];
  segments.forEach(s => { out.push(s.segStart, s.segEnd); });
  return out;
}

/**
 * Split one clip at a global sequence time into two adjacent clips.
 * Returns null when the cut lands outside the clip or leaves a piece
 * shorter than MIN_CLIP_DURATION.
 */
export function splitClipAt(seg, t, makeId) {
  if (t <= seg.segStart + MIN_CLIP_DURATION) return null;
  if (t >= seg.segEnd - MIN_CLIP_DURATION) return null;

  const cutSource = localTimeAt(seg, t);
  const sourceEnd = seg.clip.trim_end ?? seg.srcDur;

  return [
    { ...seg.clip, id: makeId(), trim_end: cutSource },
    { ...seg.clip, id: makeId(), trim_start: cutSource, trim_end: sourceEnd, transition_in: 'cut' },
  ];
}

/** 00:04.2 style timecode (mm:ss.tenths). */
export function formatTimecode(seconds) {
  const s = Math.max(0, seconds || 0);
  const m = Math.floor(s / 60);
  const rest = s - m * 60;
  return `${String(m).padStart(2, '0')}:${rest.toFixed(1).padStart(4, '0')}`;
}

export function frameStep(direction = 1) {
  return direction / FPS;
}
