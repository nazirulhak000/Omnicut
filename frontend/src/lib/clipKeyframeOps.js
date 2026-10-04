/**
 * Pure camera-keyframe operations for one timeline segment.
 *
 * Shared by the Inspector's diamond controls and the editor keyboard
 * shortcuts (D / , / .) so both decide "is there a keyframe under the
 * playhead" the same way. Keyframe `time` is the clip's played local time
 * (seconds since the segment started on the timeline, see motionTimeAt), so
 * a keyframe maps back to timeline time as `segStart + time`.
 */
import { motionTimeAt } from './timelineMath.js';

// Within ~1.5 frames at 30 fps: the playhead counts as "on" a keyframe.
export const KEYFRAME_TOLERANCE = 0.05;

const sortedKeyframes = (clip) => (Array.isArray(clip?.keyframes) ? clip.keyframes : [])
  .filter((k) => Number.isFinite(Number(k?.time)));

/**
 * Keyframe situation of `seg` at timeline time `playhead`.
 * @returns {{ localTime: number, keyframes: object[], activeIndex: number,
 *   prev: object|null, next: object|null, inside: boolean }}
 */
export function keyframeStateAt(seg, playhead) {
  if (!seg?.clip) {
    return { localTime: 0, keyframes: [], activeIndex: -1, prev: null, next: null, inside: false };
  }
  const t = Number(playhead) || 0;
  const inside = t >= seg.segStart - 1e-6 && t <= seg.segEnd + 1e-6;
  const localTime = motionTimeAt(seg, t);
  const keyframes = sortedKeyframes(seg.clip);
  const activeIndex = keyframes.findIndex(
    (k) => Math.abs(Number(k.time) - localTime) <= KEYFRAME_TOLERANCE,
  );
  let prev = null;
  let next = null;
  for (const k of keyframes) {
    const kt = Number(k.time);
    if (kt < localTime - KEYFRAME_TOLERANCE && (!prev || kt > Number(prev.time))) prev = k;
    if (kt > localTime + KEYFRAME_TOLERANCE && (!next || kt < Number(next.time))) next = k;
  }
  return { localTime, keyframes, activeIndex, prev, next, inside };
}

/**
 * Clip patch that toggles a keyframe at `playhead`: removes the one under the
 * playhead, or adds one holding the clip's current zoom/pan. Returns null when
 * the playhead is outside the segment (nothing sensible to key).
 */
export function toggleKeyframePatch(seg, playhead) {
  const st = keyframeStateAt(seg, playhead);
  if (!seg?.clip || !st.inside) return null;
  const clip = seg.clip;
  if (st.activeIndex !== -1) {
    const rest = st.keyframes.filter((_, i) => i !== st.activeIndex);
    return { keyframes: rest.length > 0 ? rest : undefined };
  }
  const added = {
    time: Math.round(st.localTime * 100) / 100,
    zoom: clip.zoom ?? 1,
    pan_x: clip.pan_x ?? 0,
    pan_y: clip.pan_y ?? 0,
    easing: 'linear',
  };
  const keyframes = [...st.keyframes, added].sort((a, b) => Number(a.time) - Number(b.time));
  return { keyframes };
}

/** Timeline time of the previous (dir < 0) or next (dir > 0) keyframe, or null. */
export function keyframeSeekTarget(seg, playhead, dir) {
  const st = keyframeStateAt(seg, playhead);
  const kf = dir < 0 ? st.prev : st.next;
  if (!kf) return null;
  return seg.segStart + Number(kf.time);
}
