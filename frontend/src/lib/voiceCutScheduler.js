/**
 * Preview playback plan for a voice with ripple cuts (manifest `voice_edit`).
 *
 * The voice file is never rewritten. The render drops the cut spans with
 * `atrim + asetpts + afade + concat` (scripts/sfx_manager.py
 * `build_voice_cut_graph`); the preview plays the SAME kept spans of the decoded
 * file as one AudioBufferSourceNode each, back to back on the AudioContext clock.
 * This module is the pure part: which node starts when, from where, for how
 * long, and with which 8 ms ramps -- no WebAudio, so node --test can check it.
 *
 * Fade rules (exactly the render's, per kept range of length L):
 *   fade in  (0 -> 1 over FADE from the range head)  iff srcStart > 1e-9
 *   fade out (1 -> 0 over FADE ending at the range end) iff srcEnd < sourceDuration - 1e-9
 * i.e. ramps only at edges a cut created, never at the file's own head/tail.
 * afade's default curve is linear ("tri"), so linear ramps reproduce it; the
 * two fades multiply (gain = in(x) * out(x)), as two chained afades do.
 *
 * Clock: program time t maps to context time as
 *   ctxTime = ctxNow + (t - tNow)      and back:  t = clock.startT + (ctx.currentTime - clock.ctxStart)
 * (programTimeAt / contextTimeAt below), the same clock the nodes are started on,
 * so picture and voice cannot drift apart.
 */

import { keepRanges, VOICE_CUT_EPS } from './voiceCutMap.js';

/** == scripts/sfx_manager.py VOICE_CUT_FADE_S */
export const VOICE_CUT_FADE_S = 0.008;

/** Render envelope of a kept range of length `length` at `x` seconds into it. */
export function rangeGainAt(x, length, { fadeIn, fadeOut }, fade = VOICE_CUT_FADE_S) {
  let gain = 1;
  if (fadeIn) gain *= Math.min(1, Math.max(0, x / fade));
  if (fadeOut) {
    // afade=t=out:st=max(0, L - fade):d=fade
    const st = Math.max(0, length - fade);
    gain *= Math.min(1, Math.max(0, 1 - (x - st) / fade));
  }
  return gain;
}

/**
 * The AudioBufferSourceNodes to start so the voice plays program time `t`
 * onwards, the moment the context clock reads `ctxNow`.
 *
 * @param {Array<{srcStart:number, srcEnd:number, progStart:number}>} ranges keepRanges(cuts, sourceDuration)
 * @param {object} o
 * @param {number} o.t               program time to start from (clamped to >= 0)
 * @param {number} o.ctxNow          AudioContext time that corresponds to `t`
 * @param {number} o.sourceDuration  duration the cuts were normalised against
 * @param {number} [o.fade]          ramp length, default 0.008 s
 * @returns {Array<{when, offset, duration, fadeIn, fadeOut, gainAtStart, srcStart, srcEnd, progStart, rangeFadeIn, rangeFadeOut}>}
 *   when      context time to call `start(when, offset, duration)`
 *   offset    seconds into the source buffer
 *   duration  seconds to play
 *   fadeIn    seconds of 0->1 ramp still to run after `when` (0 = none)
 *   fadeOut   seconds of ->0 ramp ending at `when + duration` (0 = none)
 *   gainAtStart  the render envelope's value at `offset` (1 unless t lands inside a ramp)
 *   rangeFadeIn / rangeFadeOut  whether the whole range carries that ramp in the render
 */
export function scheduleVoiceCut(ranges, { t, ctxNow, sourceDuration, fade = VOICE_CUT_FADE_S } = {}) {
  const from = Math.max(0, Number(t) || 0);
  const now = Number(ctxNow) || 0;
  const duration = Number(sourceDuration);
  const plan = [];
  for (const range of Array.isArray(ranges) ? ranges : []) {
    const length = range.srcEnd - range.srcStart;
    const progEnd = range.progStart + length;
    // A t exactly on a join belongs to the range AFTER it (programToSource).
    if (progEnd - from < VOICE_CUT_EPS) continue;
    const into = Math.max(0, from - range.progStart);
    const rangeFadeIn = range.srcStart > VOICE_CUT_EPS;
    const rangeFadeOut = Number.isFinite(duration) ? range.srcEnd < duration - VOICE_CUT_EPS : false;
    const flags = { fadeIn: rangeFadeIn, fadeOut: rangeFadeOut };
    const remaining = length - into;
    const fadeOutStart = Math.max(0, length - fade);
    plan.push({
      when: now + Math.max(0, range.progStart - from),
      offset: range.srcStart + into,
      duration: remaining,
      fadeIn: rangeFadeIn ? Math.max(0, fade - into) : 0,
      // Whole ramp still ahead -> exactly `fade` (no float noise); else what is left of it.
      fadeOut: rangeFadeOut ? (into <= fadeOutStart ? Math.min(fade, length) : remaining) : 0,
      gainAtStart: rangeGainAt(into, length, flags, fade),
      srcStart: range.srcStart,
      srcEnd: range.srcEnd,
      progStart: range.progStart,
      rangeFadeIn,
      rangeFadeOut,
    });
  }
  return plan;
}

/** keepRanges + scheduleVoiceCut in one call, for a `voiceEdit` object `{source:{duration}, cuts}`. */
export function scheduleVoiceEdit(voiceEdit, { t, ctxNow, fade = VOICE_CUT_FADE_S } = {}) {
  const sourceDuration = Number(voiceEdit?.source?.duration);
  const ranges = keepRanges(voiceEdit?.cuts, sourceDuration);
  return scheduleVoiceCut(ranges, { t, ctxNow, sourceDuration, fade });
}

/**
 * True when `voiceEdit` actually removes something -- the same test as the
 * render's `_voice_cut_graph` (no cuts, everything cut, or one range covering
 * the whole file all mean "play the voice untouched").
 */
export function voiceEditCutsAnything(voiceEdit) {
  const sourceDuration = Number(voiceEdit?.source?.duration);
  if (!Array.isArray(voiceEdit?.cuts) || voiceEdit.cuts.length === 0) return false;
  const ranges = keepRanges(voiceEdit.cuts, sourceDuration);
  if (ranges.length === 0) return false;
  return !(ranges.length === 1 && ranges[0].srcStart <= VOICE_CUT_EPS
    && ranges[0].srcEnd >= sourceDuration - VOICE_CUT_EPS);
}

/** Program time shown at context time `ctxTime` for a clock `{startT, ctxStart}`. */
export function programTimeAt(clock, ctxTime) {
  return clock.startT + (ctxTime - clock.ctxStart);
}

/** Context time at which program time `t` plays for a clock `{startT, ctxStart}`. */
export function contextTimeAt(clock, t) {
  return clock.ctxStart + (t - clock.startT);
}
