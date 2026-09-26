/**
 * Planning a "cut silences" ripple delete on the clip timeline.
 *
 * The backend (scripts/silence_detect.py) reports dead air as spans on the
 * *voiceover* timeline. This module turns those spans into a concrete change
 * to the clip list, and it is deliberately split into plan-then-apply:
 *
 * - `planSilenceRipple` is pure and returns what *would* change, so the UI can
 *   show the user the edit before it happens. A ripple delete moves every clip
 *   after it, which is not something to spring on someone unannounced.
 * - `applySilenceRipple` performs it as one state change, so a single Ctrl+Z
 *   puts the timeline back exactly as it was.
 *
 * Trimming, not deleting, is the default: a silence in the middle of a clip
 * shortens that clip rather than splitting it, because a split would double
 * the clip count and scatter the user's per-clip settings across the copies.
 * A clip left entirely inside dead air is removed outright.
 */

import { MIN_CLIP_DURATION, buildSegments, clipDuration } from './timelineMath.js';

/**
 * Overlap in seconds between [aStart, aEnd) and [bStart, bEnd).
 * Zero when they merely touch, so an adjacent span never counts as a cut.
 */
function overlapOf(aStart, aEnd, bStart, bEnd) {
  return Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
}

/**
 * Merge overlapping or touching cut spans into a disjoint, sorted list.
 *
 * Spans arrive from silence detection padded at both ends, which can make two
 * neighbouring gaps overlap. Left unmerged, the same footage would be counted
 * twice and the reported saving would overstate the real one.
 */
export function mergeSpans(spans) {
  const clean = (Array.isArray(spans) ? spans : [])
    .map((s) => ({
      start: Number(s?.cut_start ?? s?.start),
      end: Number(s?.cut_end ?? s?.end),
    }))
    .filter((s) => Number.isFinite(s.start) && Number.isFinite(s.end) && s.end > s.start)
    .sort((a, b) => a.start - b.start);

  const merged = [];
  for (const span of clean) {
    const last = merged[merged.length - 1];
    if (last && span.start <= last.end) {
      last.end = Math.max(last.end, span.end);
    } else {
      merged.push({ ...span });
    }
  }
  return merged;
}

/**
 * Work out what cutting `spans` would do to `clips`.
 *
 * Returns `{ clips, removedIds, trimmedIds, removedSeconds, before, after,
 * blocked }`. `blocked` carries a reason when the edit must not be offered at
 * all -- currently when it would empty the timeline, which is never what
 * someone means by "tighten this up".
 *
 * `durations` maps clip id to source length, exactly as buildSegments takes it.
 */
export function planSilenceRipple(clips, spans, durations = {}) {
  const list = Array.isArray(clips) ? clips : [];
  const cuts = mergeSpans(spans);
  const segments = buildSegments(list, durations);
  const before = segments.length ? segments[segments.length - 1].segEnd : 0;

  if (!list.length || !cuts.length) {
    return {
      clips: list,
      removedIds: [],
      trimmedIds: [],
      removedSeconds: 0,
      before,
      after: before,
      blocked: null,
    };
  }

  const removedIds = [];
  const trimmedIds = [];
  const nextClips = [];
  let removedSeconds = 0;

  for (const seg of segments) {
    const { clip, segStart, segEnd, srcDur } = seg;
    const playedDur = clipDuration(clip, srcDur);
    // Speed changes how long a source second occupies the sequence, so a cut
    // measured on the timeline must be converted back before it is applied to
    // the source-space trim window.
    const speed = Number(clip.speed) > 0 ? Number(clip.speed) : 1;

    let covered = 0;
    for (const cut of cuts) covered += overlapOf(segStart, segEnd, cut.start, cut.end);

    if (covered <= 0) {
      nextClips.push(clip);
      continue;
    }

    // Entirely inside dead air, or what survives is too short to be a clip.
    if (playedDur - covered < MIN_CLIP_DURATION) {
      removedIds.push(clip.id);
      removedSeconds += playedDur;
      continue;
    }

    const trimStart = Number(clip.trim_start) || 0;
    const trimEnd = clip.trim_end ?? srcDur;

    // Dead air at the head moves the in-point; anything else is taken off the
    // tail. Handling only the edges keeps one clip as one clip -- splitting
    // mid-clip would fragment the user's per-clip settings across copies.
    const headCut = cuts.reduce((acc, cut) => (
      cut.start <= segStart + 1e-6
        ? acc + overlapOf(segStart, segEnd, cut.start, cut.end)
        : acc
    ), 0);

    const tailCut = Math.max(0, covered - headCut);

    const nextTrimStart = trimStart + (headCut * speed);
    const nextTrimEnd = trimEnd - (tailCut * speed);

    if (nextTrimEnd - nextTrimStart < MIN_CLIP_DURATION) {
      removedIds.push(clip.id);
      removedSeconds += playedDur;
      continue;
    }

    trimmedIds.push(clip.id);
    removedSeconds += covered;
    nextClips.push({
      ...clip,
      trim_start: Number(nextTrimStart.toFixed(3)),
      trim_end: Number(nextTrimEnd.toFixed(3)),
    });
  }

  if (!nextClips.length) {
    return {
      clips: list,
      removedIds: [],
      trimmedIds: [],
      removedSeconds: 0,
      before,
      after: before,
      blocked: 'ตัดแล้วจะไม่เหลือคลิปเลย',
    };
  }

  // The first clip can no longer fade in from something that precedes it.
  const normalized = nextClips.map((clip, i) => (
    i === 0 && clip.transition_in && clip.transition_in !== 'cut'
      ? { ...clip, transition_in: 'cut' }
      : clip
  ));

  const after = (() => {
    const segs = buildSegments(normalized, durations);
    return segs.length ? segs[segs.length - 1].segEnd : 0;
  })();

  return {
    clips: normalized,
    removedIds,
    trimmedIds,
    removedSeconds: Number(removedSeconds.toFixed(3)),
    before: Number(before.toFixed(3)),
    after: Number(after.toFixed(3)),
    blocked: null,
  };
}

/** True when a plan would actually change the timeline. */
export function planChangesAnything(plan) {
  return Boolean(plan)
    && !plan.blocked
    && (plan.removedIds.length > 0 || plan.trimmedIds.length > 0);
}

/**
 * A short Thai summary of a plan, for the confirmation step.
 * Phrased as what will happen, not as what was found.
 */
export function describePlan(plan) {
  if (!plan) return '';
  if (plan.blocked) return plan.blocked;
  if (!planChangesAnything(plan)) return 'ไม่พบช่วงเงียบที่ตัดได้';

  const parts = [];
  if (plan.trimmedIds.length) parts.push(`ตัดสั้นลง ${plan.trimmedIds.length} คลิป`);
  if (plan.removedIds.length) parts.push(`ลบทิ้ง ${plan.removedIds.length} คลิป`);
  const saved = Math.max(0, plan.before - plan.after);
  return `${parts.join(' · ')} — สั้นลง ${saved.toFixed(2)} วินาที (${plan.before.toFixed(2)} → ${plan.after.toFixed(2)})`;
}
