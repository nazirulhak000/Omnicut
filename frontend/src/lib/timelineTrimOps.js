/**
 * Pure helpers for the manual-cut verbs: trim a clip's head/tail to the
 * playhead (Q / W), jump to the previous/next edit point, and keep the
 * playhead out of its own snap targets.
 *
 * No React/DOM, so it is unit tested with node. It only READS timelineMath.js
 * (segment layout, frame snapping, MIN_CLIP_DURATION): the trim values it
 * produces follow exactly the rules the drag handles in TimelineClip.jsx use,
 * so a keyboard trim and a handle trim land on the same frame.
 */
import { FPS, MIN_CLIP_DURATION, localTimeAt, snapSeekTime, snapToFrame } from './timelineMath.js';

const EPS = 1e-6;

export const TRIM_MESSAGES = Object.freeze({
  noClips: 'ยังไม่มีคลิปบน Timeline ให้ตัด',
  outside: 'หัวอ่านไม่ได้อยู่บนคลิปวิดีโอ เลื่อนหัวอ่านไปบนคลิปที่ต้องการตัดก่อน',
  unknownSource: 'ยังไม่ทราบความยาวต้นฉบับของคลิปนี้ จึงตัดไม่ได้',
  freeze: 'หัวอ่านอยู่ในช่วงค้างภาพท้ายคลิป ตัดตรงนี้ไม่ได้',
  headAtEdge: 'หัวอ่านอยู่ที่หัวคลิปแล้ว ไม่มีช่วงหน้าให้ตัดออก',
  tailAtEdge: 'หัวอ่านอยู่ที่ท้ายคลิปแล้ว ไม่มีช่วงท้ายให้ตัดออก',
  headTooShort: `ตัดหัวคลิปตรงนี้ไม่ได้ เพราะจะเหลือคลิปสั้นกว่า ${MIN_CLIP_DURATION} วินาที`,
  tailTooShort: `ตัดท้ายคลิปตรงนี้ไม่ได้ เพราะจะเหลือคลิปสั้นกว่า ${MIN_CLIP_DURATION} วินาที`,
});

/**
 * Whether trimming `edge` ('head' | 'tail') of `seg` at sequence time `time`
 * is possible. Returns { ok: true, patch, seekTo } or { ok: false, reason }.
 * `patch` is the clip fields to change (source seconds, whole 30 fps frame,
 * clamped so the clip keeps MIN_CLIP_DURATION). `seekTo` is where the playhead
 * should go so the preview keeps showing the same frame (head trim only: the
 * remaining part slides back to the clip's own start).
 */
function planTrim(edge, seg, time, fps) {
  if (!seg || !seg.clip) return { ok: false, reason: 'outside' };
  if (time < seg.segStart - EPS || time > seg.segEnd + EPS) return { ok: false, reason: 'outside' };

  const clip = seg.clip;
  const speed = clip.speed || 1;
  const trimStart = clip.trim_start || 0;
  const trimEnd = clip.trim_end ?? seg.srcDur;
  if (!(Number.isFinite(trimEnd) && trimEnd > trimStart)) return { ok: false, reason: 'unknownSource' };

  const playedEnd = seg.segStart + (trimEnd - trimStart) / speed;
  if (time > playedEnd + EPS) return { ok: false, reason: 'freeze' };

  const halfFrame = 0.5 / fps;
  const cutSource = snapToFrame(localTimeAt(seg, time), fps);

  if (edge === 'head') {
    if (time - seg.segStart < halfFrame) return { ok: false, reason: 'headAtEdge' };
    if (playedEnd - time < MIN_CLIP_DURATION - EPS) return { ok: false, reason: 'headTooShort' };
    const next = Math.min(cutSource, trimEnd - MIN_CLIP_DURATION * speed);
    if (next <= trimStart + EPS) return { ok: false, reason: 'headAtEdge' };
    return { ok: true, patch: { trim_start: next }, seekTo: seg.segStart };
  }

  if (playedEnd - time < halfFrame) return { ok: false, reason: 'tailAtEdge' };
  if (time - seg.segStart < MIN_CLIP_DURATION - EPS) return { ok: false, reason: 'tailTooShort' };
  const next = Math.max(cutSource, trimStart + MIN_CLIP_DURATION * speed);
  if (next >= trimEnd - EPS) return { ok: false, reason: 'tailAtEdge' };
  return { ok: true, patch: { trim_end: next }, seekTo: null };
}

/**
 * Which clip a Q (head) / W (tail) trim would change, and how. Same targeting
 * as Split: the selected clip when the (frame-snapped) playhead is on it and
 * the trim works there, otherwise the clip under the playhead (the later one
 * inside a transition overlap, which is the one on screen).
 *
 * Success: { seg, time, patch, seekTo }.
 * Refusal: { seg: null, time, message } -- `message` says why in plain Thai.
 */
export function resolveTrimTarget(edge, segments, selectedSeg, playhead, fps = FPS) {
  const side = edge === 'tail' ? 'tail' : 'head';
  const time = snapToFrame(playhead, fps);
  const list = Array.isArray(segments) ? segments : [];
  if (list.length === 0) return { seg: null, time, message: TRIM_MESSAGES.noClips };

  const attempts = [];
  if (selectedSeg) attempts.push(selectedSeg);
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (list[i] !== selectedSeg) attempts.push(list[i]);
  }

  let firstReason = null;
  for (const seg of attempts) {
    const plan = planTrim(side, seg, time, fps);
    if (plan.ok) return { seg, time, patch: plan.patch, seekTo: plan.seekTo };
    // `outside` is only the answer when no clip is under the playhead at all;
    // a clip that IS under it explains the refusal better.
    if (plan.reason !== 'outside' && firstReason === null) firstReason = plan.reason;
  }
  return { seg: null, time, message: TRIM_MESSAGES[firstReason ?? 'outside'] };
}

export const resolveTrimHead = (segments, selectedSeg, playhead, fps = FPS) => (
  resolveTrimTarget('head', segments, selectedSeg, playhead, fps)
);
export const resolveTrimTail = (segments, selectedSeg, playhead, fps = FPS) => (
  resolveTrimTarget('tail', segments, selectedSeg, playhead, fps)
);

/**
 * Every time the up/down arrows can stop at: the sequence start, each clip's
 * start and end, and (when given) each subtitle cue's start and end. Sorted,
 * raw (not frame-landed) seconds.
 */
export function collectEditPoints(segments = [], cues = []) {
  const points = [0];
  for (const seg of segments || []) {
    if (Number.isFinite(seg?.segStart)) points.push(seg.segStart);
    if (Number.isFinite(seg?.segEnd)) points.push(seg.segEnd);
  }
  for (const cue of cues || []) {
    if (Number.isFinite(cue?.start)) points.push(cue.start);
    if (Number.isFinite(cue?.end)) points.push(cue.end);
  }
  return points.filter((p) => p >= 0).sort((a, b) => a - b);
}

/**
 * The edit point before/after `playhead`. Points are compared where a seek
 * would actually land (`land`, default: nearest whole frame; the editor passes
 * snapSeekTime so a clip start rounds forward), so pressing the key again from
 * a landed point always moves on instead of returning the same point.
 *
 * @param {number[]} points raw edit-point times
 * @param {number} playhead current time
 * @param {-1|1} direction -1 previous, +1 next
 * @returns {number | null} the landed time, or null when there is none that way
 */
export function prevNextEditPoint(points, playhead, direction, { land = (t) => snapToFrame(t), fps = FPS } = {}) {
  const here = Number.isFinite(playhead) ? playhead : 0;
  const half = 0.5 / fps;
  let best = null;
  for (const raw of points || []) {
    if (!Number.isFinite(raw)) continue;
    const landed = land(raw);
    if (direction > 0) {
      if (landed > here + half && (best === null || landed < best)) best = landed;
    } else if (landed < here - half && (best === null || landed > best)) {
      best = landed;
    }
  }
  return best;
}

/** Convenience wrapper: the edit point to jump to, using the editor's own seek landing. */
export function jumpTargetForEdit(segments, cues, playhead, direction, fps = FPS) {
  return prevNextEditPoint(collectEditPoints(segments, cues), playhead, direction, {
    land: (t) => snapSeekTime(t, segments, fps),
    fps,
  });
}

/**
 * Where a navigation shortcut action sends the playhead, or null when it has
 * nowhere to go (no earlier/later edit point). Actions: prevEdit, nextEdit,
 * seekStart (Home), seekEnd (End = end of the clips, not of the voice track).
 */
export function editNavigationTarget(action, { segments = [], cues = [], playhead = 0, totalDuration = 0, fps = FPS } = {}) {
  if (action === 'seekStart') return 0;
  if (action === 'seekEnd') return Math.max(0, Number(totalDuration) || 0);
  if (action === 'prevEdit' || action === 'nextEdit') {
    return jumpTargetForEdit(segments, cues, playhead, action === 'nextEdit' ? 1 : -1, fps);
  }
  return null;
}

/**
 * Snap candidates without the playhead's own entry. snapCandidates() always
 * adds the playhead as a target; while the playhead itself is the thing being
 * dragged, that target is wherever the pointer just was, so snapping to it
 * freezes the scrub. Exactly one matching entry is dropped, so a clip edge that
 * sits on the same time stays a target.
 */
export function withoutPlayheadCandidate(candidates, playhead) {
  const list = Array.isArray(candidates) ? candidates : [];
  const at = list.indexOf(playhead);
  if (at === -1) return list;
  return list.filter((_, i) => i !== at);
}

/**
 * Candidates for a handle drag during which the playhead is moved to show the
 * dragged edge. The playhead target stays where it was when the drag began
 * (`frozenPlayhead`) instead of following the edge the user is dragging, which
 * would make the edge snap to itself.
 */
export function freezePlayheadCandidate(candidates, livePlayhead, frozenPlayhead) {
  const list = Array.isArray(candidates) ? candidates : [];
  if (livePlayhead === frozenPlayhead || frozenPlayhead === undefined) return list;
  const at = list.indexOf(livePlayhead);
  if (at === -1) return list;
  const out = list.slice();
  out[at] = frozenPlayhead;
  return out;
}

/** The frame to show while a trim handle is dragged: the first kept frame of a head trim, the last kept frame of a tail trim. */
export function trimDragSeekTime(edge, segStart, sequenceDuration, fps = FPS) {
  if (edge === 'start') return segStart;
  return Math.max(segStart, segStart + sequenceDuration - 1 / fps);
}
