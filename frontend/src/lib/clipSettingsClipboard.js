/**
 * Copy / paste of a clip's settings.
 *
 * "Settings" are the per-clip looks a user tunes and wants to repeat: speed,
 * zoom / pan together with the camera keyframes that drive them (easing per
 * point included), colour and the incoming transition. Trim, source, volume,
 * rotation, mirror, fit/blur and Cutout stay with the clip they belong to.
 *
 * Camera keyframe times live on the clip's played clock (see clipPlayedDuration),
 * so a move copied onto a clip of a different length is scaled to that clip:
 * a whole-clip push-in stays a whole-clip push-in.
 *
 * Pure and DOM-free so it can be unit tested.
 */
import { clipPlayedDuration, withoutCameraKeyframes } from './inspectorModel.js';

export const CLIP_SETTING_FIELDS = Object.freeze({
  speed: Object.freeze(['speed', 'smooth_slowmo']),
  framing: Object.freeze(['zoom', 'pan_x', 'pan_y']),
  color: Object.freeze(['brightness', 'contrast', 'saturation']),
  transition: Object.freeze(['transition_in', 'transition_duration', 'transition_easing']),
});

const SETTING_FIELDS = Object.freeze(Object.values(CLIP_SETTING_FIELDS).flat());

/** Durations closer than one frame count as the same length (no rescale). */
const SAME_LENGTH_TOLERANCE = 1 / 30;

const round3 = (n) => Math.round(n * 1000) / 1000;

/** The camera (zoom/pan) points of a keyframe list; everything else is not copied. */
export function cameraKeyframesOf(keyframes) {
  const list = Array.isArray(keyframes) ? keyframes : [];
  return list.filter((point) => withoutCameraKeyframes([point]).length === 0);
}

/**
 * Scales keyframe times from a clip played for `fromDuration` seconds to one
 * played for `toDuration`. Returns copies; times stay inside 0..toDuration.
 */
export function rescaleCameraKeyframes(points, fromDuration, toDuration) {
  const copies = (Array.isArray(points) ? points : []).map((point) => ({ ...point }));
  const from = Number(fromDuration);
  const to = Number(toDuration);
  if (!(from > 0) || !(to > 0) || Math.abs(from - to) <= SAME_LENGTH_TOLERANCE) return copies;
  const k = to / from;
  return copies.map((point) => ({
    ...point,
    time: round3(Math.min(to, Math.max(0, Number(point.time) * k))),
  }));
}

/**
 * Snapshot of `clip`'s settings. A setting the clip leaves unset stays unset in
 * the snapshot, so pasting it puts the target back to the default too.
 */
export function copyClipSettings(clip, sourceDuration = 0) {
  if (!clip) return null;
  return {
    values: Object.fromEntries(SETTING_FIELDS.map((field) => [field, clip[field]])),
    cameraKeyframes: cameraKeyframesOf(clip.keyframes).map((point) => ({ ...point })),
    playedDuration: clipPlayedDuration(clip, sourceDuration),
  };
}

/** What the target clip would look like after the paste (same object if nothing differs). */
function pasteOntoClip(clip, snapshot, sourceDuration) {
  const merged = { ...clip, ...snapshot.values };
  const moves = rescaleCameraKeyframes(
    snapshot.cameraKeyframes,
    snapshot.playedDuration,
    // Speed was just pasted, so the played length is measured on the merged clip.
    clipPlayedDuration(merged, sourceDuration),
  );
  const next = { ...merged, keyframes: [...withoutCameraKeyframes(clip.keyframes), ...moves] };
  const touched = [...SETTING_FIELDS, 'keyframes'];
  const same = touched.every((key) => JSON.stringify(clip[key] ?? null) === JSON.stringify(next[key] ?? null));
  return same ? clip : next;
}

/**
 * Pastes `snapshot` onto the clips whose id is in `targetIds`.
 * `sourceDurations` maps clip id -> source file duration (for clips with no
 * trim_end). Returns `{ clipList, changed }`; `clipList` is the very same array
 * when no clip changes, so a history `set` can skip the undo step.
 */
export function pasteClipSettingsToClips(clipList, snapshot, targetIds, sourceDurations = {}) {
  const list = Array.isArray(clipList) ? clipList : [];
  if (!snapshot) return { clipList: list, changed: 0 };
  const targets = new Set(targetIds || []);
  let changed = 0;
  const next = list.map((clip) => {
    if (!clip || !targets.has(clip.id)) return clip;
    const pasted = pasteOntoClip(clip, snapshot, sourceDurations[clip.id] ?? 0);
    if (pasted !== clip) changed += 1;
    return pasted;
  });
  return changed ? { clipList: next, changed } : { clipList: list, changed: 0 };
}

/** Editor state with the paste applied; the same state back when nothing changes. */
export function pasteClipSettingsInState(state, snapshot, targetIds, sourceDurations = {}) {
  const { clipList, changed } = pasteClipSettingsToClips(state.clipList, snapshot, targetIds, sourceDurations);
  return changed ? { ...state, clipList } : state;
}
