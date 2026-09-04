// Single source of truth for sequence timing, shared by SequencePlayer
// (canvas preview) and the editor Timeline. Must stay in lockstep with
// scripts/video_editor.py's clip_list branch -- if the two drift, what the
// user scrubs stops matching what Apply renders.

export const FADE_DURATION = 0.4;   // == video_editor.py DEFAULT_TRANSITION_DURATION
export const MAX_TRANSITION_DURATION = 2.0;

// == video_editor.py XFADE_TRANSITIONS. A boundary is "cut" or one of these.
export const TRANSITIONS = [
  { id: 'fade', label: 'จางเข้าหากัน' },
  { id: 'fadeblack', label: 'จางผ่านดำ' },
  { id: 'fadewhite', label: 'จางผ่านขาว' },
  { id: 'dissolve', label: 'ละลาย' },
  { id: 'wipeleft', label: 'ปาดไปซ้าย' },
  { id: 'wiperight', label: 'ปาดไปขวา' },
  { id: 'wipeup', label: 'ปาดขึ้น' },
  { id: 'wipedown', label: 'ปาดลง' },
  { id: 'slideleft', label: 'เลื่อนซ้าย' },
  { id: 'slideright', label: 'เลื่อนขวา' },
  { id: 'slideup', label: 'เลื่อนขึ้น' },
  { id: 'slidedown', label: 'เลื่อนลง' },
  { id: 'circleopen', label: 'วงกลมเปิด' },
  { id: 'circleclose', label: 'วงกลมปิด' },
];

/**
 * Seconds this boundary overlaps the previous clip. "cut" overlaps nothing;
 * every other type eats its own duration, clamped exactly like
 * video_editor.py's normalize_transitions so the preview and the render
 * agree on where every later clip starts.
 */
export function transitionOverlap(clip) {
  const kind = clip?.transition_in || 'cut';
  if (kind === 'cut') return 0;
  const raw = clip.transition_duration ?? FADE_DURATION;
  return Math.min(MAX_TRANSITION_DURATION, Math.max(0.1, raw));
}
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
 * Lay clips out on one timeline. A transition boundary overlaps the previous
 * clip by its own duration, so it eats that much from the running total --
 * same bookkeeping as video_editor.py's per-boundary xfade reduction.
 *
 * durations: { [clip.id]: sourceDurationSeconds }
 */
export function buildSegments(clips, durations = {}) {
  let acc = 0;
  return clips.map((clip, i) => {
    const srcDur = durations[clip.id] || 0;
    const dur = clipDuration(clip, srcDur);
    const overlap = i > 0 ? transitionOverlap(clip) : 0;
    const isFade = overlap > 0;
    const segStart = i === 0 ? 0 : acc - overlap;
    const segEnd = segStart + dur;
    acc = segEnd;
    return { clip, index: i, srcDur, dur, isFade, overlap, segStart, segEnd };
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

  // Every transition type previews as a crossfade -- the canvas cannot wipe or
  // slide, and pretending otherwise would be a preview that lies. The rendered
  // file uses the real xfade type.
  if (seg.isFade && idx > 0 && t < seg.segStart + seg.overlap) {
    const prevSeg = segments[idx - 1];
    const alpha = Math.max(0, Math.min(1, (t - seg.segStart) / seg.overlap));
    // Alphas are PAINT-ORDER alphas, not per-clip contributions: entries are
    // drawn in order, each over the previous, so the base layer is opaque and
    // only the incoming one blends. Giving the outgoing clip `1 - alpha` here
    // instead left the composite at a*B + (1-a)^2*A over a cleared canvas --
    // total coverage sagging to 0.75 mid-transition, i.e. a visible dip to
    // the background that ffmpeg's xfade never shows.
    plan[0] = { seg: prevSeg, localTime: localTimeAt(prevSeg, t), alpha: 1 };
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

/** Every time a drag should snap to: clip edges, the playhead, plus any extra
 * marks the caller wants included (e.g. where the voiceover audio ends). */
export function snapCandidates(segments, playhead, extra = []) {
  const out = [0, playhead, ...extra];
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
