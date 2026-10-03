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

/** Resolve a numeric keyframe track at local clip time (seconds). */
export function interpolateKeyframes(keyframes, time, fallback) {
  const points = (Array.isArray(keyframes) ? keyframes : [])
    .filter((p) => Number.isFinite(Number(p?.time)) && Number.isFinite(Number(p?.value)))
    .map((p) => ({ time: Number(p.time), value: Number(p.value) }))
    .sort((a, b) => a.time - b.time);
  if (!points.length) return fallback;
  if (time <= points[0].time) return points[0].value;
  const last = points[points.length - 1];
  if (time >= last.time) return last.value;
  for (let i = 1; i < points.length; i += 1) {
    const right = points[i];
    if (time <= right.time) {
      const left = points[i - 1];
      const span = right.time - left.time;
      const ratio = span > 0 ? (time - left.time) / span : 1;
      return left.value + (right.value - left.value) * ratio;
    }
  }
  return last.value;
}

// Camera motion is evaluated in the clip's played timeline (seconds after
// speed has been applied), not in source-file time. These limits mirror the
// live crop path in scripts/video_editor.py; keeping them here prevents a
// keyframe from asking Canvas to show a frame FFmpeg would reject.
export const CAMERA_MOTION_LIMITS = {
  zoom: { min: 1.0, max: 3.0 },
  pan_x: { min: -1.0, max: 1.0 },
  pan_y: { min: -1.0, max: 1.0 },
};

function clampCameraValue(property, value, fallback) {
  const numeric = Number.isFinite(Number(value)) ? Number(value) : fallback;
  const bounds = CAMERA_MOTION_LIMITS[property];
  return bounds
    ? Math.min(bounds.max, Math.max(bounds.min, numeric))
    : numeric;
}

/** Resolve the live camera transform at played local clip time. */
export function resolveClipTransforms(clip = {}, localTime = 0) {
  const keyframes = Array.isArray(clip.keyframes) ? clip.keyframes : [];
  const extractTrack = (property) => keyframes
    .filter((point) => point && typeof point === 'object'
      && (point[property] !== undefined || point.property === property))
    .map((point) => ({
      time: point.time,
      value: point[property] !== undefined ? point[property] : point.value,
    }));

  const base = {
    zoom: clip.zoom ?? clip.scale ?? 1.0,
    pan_x: clip.pan_x ?? clip.x ?? 0.0,
    pan_y: clip.pan_y ?? clip.y ?? 0.0,
  };
  return Object.fromEntries(Object.keys(base).map((property) => {
    const track = extractTrack(property);
    const value = track.length
      ? interpolateKeyframes(track, localTime, base[property])
      : base[property];
    return [property, clampCameraValue(property, value, base[property])];
  }));
}

// Zoom steps in pixels-per-second of timeline.
export const ZOOM_LEVELS = [10, 25, 50, 100, 200];
export const DEFAULT_ZOOM_INDEX = 2;

/**
 * Kept length of a clip on the sequence timeline, after trim, speed and the
 * freeze tail. The tail has to be counted here for the same reason
 * video_editor.py adds it to its own `duration`: every later clip's start --
 * and every transition offset -- is measured from this number, so leaving it
 * out made the preview run short and drift against the render.
 */
export function clipDuration(clip, srcDuration) {
  const end = clip.trim_end ?? srcDuration ?? 0;
  const raw = end - (clip.trim_start || 0);
  const speed = clip.speed || 1;
  const freezeTail = Math.min(10, Math.max(0, Number(clip.freeze_tail) || 0));
  return Math.max(MIN_CLIP_DURATION, raw / speed + freezeTail);
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
    // A transition cannot consume more than either neighboring clip leaves
    // available. Render clamps this same way before building xfade; applying
    // the clamp here prevents negative segment starts for short clips.
    const requestedOverlap = i > 0 ? transitionOverlap(clip) : 0;
    const overlap = i > 0
      ? Math.min(requestedOverlap, Math.max(0, acc), Math.max(0, dur) , Math.max(0, Math.min(acc, dur) - 0.05))
      : 0;
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

/**
 * Source-file time for a global sequence time inside one segment. Once the
 * played span is used up the freeze tail holds the last frame, matching
 * ffmpeg's tpad=stop_mode=clone.
 */
export function localTimeAt(seg, t) {
  const clip = seg.clip;
  const speed = clip.speed || 1;
  const start = clip.trim_start || 0;
  const playedSpan = ((clip.trim_end ?? seg.srcDur ?? 0) - start) / speed;
  const elapsed = Math.min(t - seg.segStart, playedSpan);
  return start + elapsed * speed;
}

/** Played local time used by visual keyframes (freeze holds the final value). */
export function motionTimeAt(seg, t) {
  const clip = seg.clip;
  const speed = clip.speed || 1;
  const playedSpan = ((clip.trim_end ?? seg.srcDur ?? 0) - (clip.trim_start || 0)) / speed;
  return Math.max(0, Math.min(playedSpan, t - seg.segStart));
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
  const plan = [{
    seg,
    localTime: localTimeAt(seg, t),
    motionTime: motionTimeAt(seg, t),
    alpha: 1,
    role: 'solo',
  }];

  // Inside an overlap the pair carries the boundary type and how far through it
  // is, so the canvas can wipe/slide/dissolve the way ffmpeg will instead of
  // crossfading everything. The geometry lives in SequencePlayer (it is the
  // side that owns pixels); this only says which transition and how far.
  if (seg.isFade && idx > 0 && t < seg.segStart + seg.overlap) {
    const prevSeg = segments[idx - 1];
    const alpha = Math.max(0, Math.min(1, (t - seg.segStart) / seg.overlap));
    const transition = seg.clip.transition_in || 'fade';
    // Alphas are PAINT-ORDER alphas, not per-clip contributions: entries are
    // drawn in order, each over the previous, so the base layer is opaque and
    // only the incoming one blends. Giving the outgoing clip `1 - alpha` here
    // instead left the composite at a*B + (1-a)^2*A over a cleared canvas --
    // total coverage sagging to 0.75 mid-transition, i.e. a visible dip to
    // the background that ffmpeg's xfade never shows.
    plan[0] = { seg: prevSeg, localTime: localTimeAt(prevSeg, t), alpha: 1, role: 'out', transition, progress: alpha, motionTime: motionTimeAt(prevSeg, t) };
    plan.push({ seg, localTime: localTimeAt(seg, t), alpha, role: 'in', transition, progress: alpha, motionTime: motionTimeAt(seg, t) });
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
    // Freeze belongs to the final piece of the source. Copying it to both
    // sides made a 6-second clip become 8 seconds after a split.
    { ...seg.clip, id: makeId(), trim_end: cutSource, freeze_tail: undefined },
    { ...seg.clip, id: makeId(), trim_start: cutSource, trim_end: sourceEnd, transition_in: 'cut' },
  ];
}

/**
 * Shift a clip's trim window by `deltaSource` source-seconds while holding
 * (trim_end - trim_start) exactly constant, clamped to [0, srcDur]. Used by
 * TrimAdjustModal's "drag the whole box" gesture -- distinct from
 * resizeTrimWindow, which changes the span instead of moving it.
 */
export function shiftTrimWindow(clip, deltaSource, srcDur) {
  const span = (clip.trim_end ?? srcDur ?? 0) - (clip.trim_start || 0);
  const maxStart = Math.max(0, (srcDur || 0) - span);
  const nextStart = Math.min(maxStart, Math.max(0, (clip.trim_start || 0) + deltaSource));
  return {
    trim_start: Math.round(nextStart * 100) / 100,
    trim_end: Math.round((nextStart + span) * 100) / 100,
  };
}

/**
 * Resize one edge of a clip's trim window by `deltaSource` source-seconds,
 * changing the span (unlike shiftTrimWindow, which holds it constant). Used
 * by TrimAdjustModal's edge-drag handles -- pixels there map directly to
 * source-seconds (the modal shows one raw file in isolation), so there is no
 * sequence/speed conversion or timeline-grid snapping to account for, unlike
 * the main timeline's own edge-drag-to-resize (TimelineClip.jsx).
 */
export function resizeTrimWindow(edge, clip, deltaSource, srcDur) {
  const trimStart = clip.trim_start || 0;
  const trimEnd = clip.trim_end ?? srcDur ?? 0;
  if (edge === 'start') {
    const next = Math.min(Math.max(0, trimStart + deltaSource), trimEnd - MIN_CLIP_DURATION);
    return { trim_start: Math.round(next * 100) / 100, trim_end: Math.round(trimEnd * 100) / 100 };
  }
  const next = Math.max(Math.min(srcDur || trimEnd, trimEnd + deltaSource), trimStart + MIN_CLIP_DURATION);
  return { trim_start: Math.round(trimStart * 100) / 100, trim_end: Math.round(next * 100) / 100 };
}

/**
 * 00:04.2 style timecode (mm:ss.tenths). With `{ frames: true }` it is the
 * frame-accurate form mm:ss:ff (ff = frame 0..fps-1), which is what a cut has
 * to be read against: one second is 30 frames, so tenths can hide ~3 frames.
 */
export function formatTimecode(seconds, { frames = false, fps = FPS } = {}) {
  const s = Math.max(0, Number.isFinite(Number(seconds)) ? Number(seconds) : 0);
  if (frames) {
    // Round to the nearest frame first so 4.2 (= 126 frames) never prints as
    // frame 125 because of float error, and ff can never reach `fps`.
    const total = Math.round(s * fps);
    const perMinute = 60 * fps;
    const mm = Math.floor(total / perMinute);
    const ss = Math.floor((total % perMinute) / fps);
    const ff = total % fps;
    return [mm, ss, ff].map((n) => String(n).padStart(2, '0')).join(':');
  }
  const m = Math.floor(s / 60);
  const rest = s - m * 60;
  return `${String(m).padStart(2, '0')}:${rest.toFixed(1).padStart(4, '0')}`;
}

/**
 * Round a time (seconds) to the nearest whole frame. The value stays a plain
 * float number of seconds -- the renderer reads seconds, not frame counts --
 * it is only quantised so the editor never lands between two frames.
 */
export function snapToFrame(seconds, fps = FPS) {
  const s = Number(seconds);
  if (!Number.isFinite(s)) return 0;
  // `+ 0` turns -0 into 0 so a snapped time never prints or compares as -0.
  return Math.round(s * fps) / fps + 0;
}

/**
 * Frame-snap a playhead seek. A seek that lands on a clip's first instant must
 * never round BEFORE that clip (the previous clip would then be the one under
 * the playhead), so those use the first frame at or after the clip start.
 */
export function snapSeekTime(seconds, segments = [], fps = FPS) {
  const s = Number(seconds);
  if (!Number.isFinite(s)) return 0;
  const isClipStart = segments.some((seg) => Math.abs(seg.segStart - s) < 1e-6);
  if (isClipStart) return Math.ceil(s * fps - 1e-6) / fps + 0;
  return snapToFrame(s, fps);
}

/**
 * Which clip a Split would cut, and where. Single source of truth for BOTH the
 * split command and the toolbar button's enabled state, so the button can
 * never promise a cut the command then silently refuses.
 *
 * Order: the selected clip if the (frame-snapped) playhead is inside it, else
 * the clip under the playhead. Returns { seg, time } on success, otherwise
 * { seg: null, time, message } where `message` says why in plain Thai.
 */
export function resolveSplitTarget(segments, selectedSeg, playhead, fps = FPS) {
  const time = snapToFrame(playhead, fps);
  const cuttable = (seg) => !!seg
    && time > seg.segStart + MIN_CLIP_DURATION
    && time < seg.segEnd - MIN_CLIP_DURATION;

  if (cuttable(selectedSeg)) return { seg: selectedSeg, time };
  const under = (segments || []).find(cuttable);
  if (under) return { seg: under, time };

  const edgeSeg = (segments || []).find((seg) => time >= seg.segStart && time <= seg.segEnd);
  let message;
  if (!segments || segments.length === 0) {
    message = 'ยังไม่มีคลิปบน Timeline ให้แยก';
  } else if (edgeSeg) {
    message = `หัวอ่านอยู่ใกล้ขอบคลิปเกินไป ต้องห่างขอบอย่างน้อย ${MIN_CLIP_DURATION} วินาที จึงจะแยกได้`;
  } else {
    message = 'หัวอ่านไม่ได้อยู่บนคลิปวิดีโอ เลื่อนหัวอ่านไปบนคลิปที่ต้องการแยกก่อน';
  }
  return { seg: null, time, message };
}

/**
 * Resolves a human-friendly label for a snapped time position.
 */
export function resolveSnapCandidateLabel(snappedTime, { playhead, segments = [], cues = [], audioDuration = 0, tolerance = 0.05 } = {}) {
  if (typeof snappedTime !== 'number' || !Number.isFinite(snappedTime)) return 'จุดแม่เหล็ก (Snap)';
  if (Math.abs(snappedTime - 0) <= tolerance) return 'จุดเริ่มต้น (0:00)';
  if (typeof playhead === 'number' && Math.abs(snappedTime - playhead) <= tolerance) return 'หัวอ่าน (Playhead)';
  if (typeof audioDuration === 'number' && audioDuration > 0 && Math.abs(snappedTime - audioDuration) <= tolerance) return 'จุดจบเสียงพากย์ (Audio End)';

  for (let i = 0; i < segments.length - 1; i++) {
    if (Math.abs(snappedTime - segments[i].segEnd) <= tolerance && Math.abs(snappedTime - segments[i + 1].segStart) <= tolerance) {
      return `รอยต่อคลิป #${i + 1} ↔ #${i + 2}`;
    }
  }

  for (let i = 0; i < segments.length; i++) {
    const s = segments[i];
    if (Math.abs(snappedTime - s.segStart) <= tolerance) return `หัวคลิป #${i + 1}`;
    if (Math.abs(snappedTime - s.segEnd) <= tolerance) return `ท้ายคลิป #${i + 1}`;
  }

  for (let i = 0; i < cues.length; i++) {
    const c = cues[i];
    if (typeof c.start === 'number' && Math.abs(snappedTime - c.start) <= tolerance) return `หัวซับ #${i + 1}`;
    if (typeof c.end === 'number' && Math.abs(snappedTime - c.end) <= tolerance) return `ท้ายซับ #${i + 1}`;
  }

  return 'จุดตัด (Snap)';
}

