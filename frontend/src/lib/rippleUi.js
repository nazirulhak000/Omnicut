/**
 * Pure helpers behind the ripple-delete UI (Toolbar scope toggle, Delete /
 * Shift+Delete, In/Out marks, the silence button, the cut markers on the voice
 * lane). The cutting itself lives in rippleRange.js; nothing here changes state,
 * so each rule is unit tested without a browser.
 *
 * Design: _Docs/Plans/PLAN_RIPPLE_ANCHOR_20261004.md section 6.
 */

import { FPS, snapToFrame } from './timelineMath.js';
import { mergeSpans } from './silenceRipple.js';
import {
  RIPPLE_SCOPE_ALL,
  RIPPLE_SCOPE_VIDEO,
  defaultRippleScope,
  describeRipplePlan,
} from './rippleRange.js';
import { normalizeCuts, sourceToProgram } from './voiceCutMap.js';

const ONE_FRAME = 1 / FPS;
const EPS = 1e-9;

const finite = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

// ---------------------------------------------------------------------------
// Scope toggle
// ---------------------------------------------------------------------------

/**
 * The scope a Delete uses right now. `choice` is the user's toggle ('all' |
 * 'video' | null = never touched). Without a voiceover there is nothing to cut
 * with the picture, so the scope is always 'video' and the toggle stays hidden.
 */
export function resolveRippleScope(choice, hasVoice) {
  if (!hasVoice) return RIPPLE_SCOPE_VIDEO;
  return choice === RIPPLE_SCOPE_VIDEO || choice === RIPPLE_SCOPE_ALL
    ? choice
    : defaultRippleScope(true);
}

/** Toolbar label of the scope toggle (names what Delete does now). */
export function rippleScopeLabel(scope) {
  return scope === RIPPLE_SCOPE_VIDEO ? 'ลบเฉพาะภาพ' : 'ลบพร้อมเสียงและซับ';
}

/** Tooltip of the scope toggle: what it does now and what a click switches to. */
export function rippleScopeHint(scope) {
  return scope === RIPPLE_SCOPE_VIDEO
    ? 'ตอนนี้ลบเฉพาะภาพ เสียงพากย์และซับไม่ขยับ (คลิกเพื่อเปลี่ยนเป็นลบพร้อมเสียงและซับ)'
    : 'ตอนนี้ลบภาพ เสียงพากย์ และซับพร้อมกัน (คลิกเพื่อเปลี่ยนเป็นลบเฉพาะภาพ)';
}

// ---------------------------------------------------------------------------
// Delete on clips
// ---------------------------------------------------------------------------

/**
 * Program-time ranges of the clips a Delete would remove, timeline order.
 * `ids` is the whole selection (the primary clip included). Overlapping or
 * touching ranges are merged by the planner, so adjacent clips become one cut.
 */
export function clipRangesFromSegments(segments, ids) {
  const wanted = new Set(Array.isArray(ids) ? ids : []);
  return (Array.isArray(segments) ? segments : [])
    .filter((seg) => seg?.clip && wanted.has(seg.clip.id))
    .map((seg) => ({ start: seg.segStart, end: seg.segEnd }))
    .filter((range) => Number.isFinite(range.start) && Number.isFinite(range.end) && range.end > range.start);
}

/**
 * Does this Delete go through the ripple dialog? Only a clip selection, and
 * only when the scope is 'all' (picture + voice + captions). Everything else --
 * captions, overlays, stickers, effects, and the 'video' scope -- keeps the
 * plain delete with no dialog.
 */
export function isRippleDelete({ selection, scope, hasVoice }) {
  return Boolean(hasVoice) && scope === RIPPLE_SCOPE_ALL && selection?.type === 'clip';
}

// ---------------------------------------------------------------------------
// In / Out marks
// ---------------------------------------------------------------------------

export const EMPTY_RANGE_MARK = Object.freeze({ inTime: null, outTime: null });

/**
 * Mark In or Out at `time` (frame-snapped). Marking In at or after Out drops the
 * Out (and the other way round), so the pair is always an increasing range or a
 * lone point; the mark just set always wins.
 */
export function markRangePoint(mark, which, time) {
  const t = Math.max(0, snapToFrame(time));
  const inTime = finite(mark?.inTime);
  const outTime = finite(mark?.outTime);
  if (which === 'in') {
    return { inTime: t, outTime: outTime !== null && outTime > t + EPS ? outTime : null };
  }
  if (which === 'out') {
    return { inTime: inTime !== null && inTime < t - EPS ? inTime : null, outTime: t };
  }
  return { inTime, outTime };
}

/** Is any In/Out mark set (Escape clears it)? */
export function hasRangeMark(mark) {
  return finite(mark?.inTime) !== null || finite(mark?.outTime) !== null;
}

/** The In-Out span as planner ranges, or [] until both marks make at least one frame. */
export function rangeMarkToRanges(mark) {
  const inTime = finite(mark?.inTime);
  const outTime = finite(mark?.outTime);
  if (inTime === null || outTime === null || outTime - inTime < ONE_FRAME - EPS) return [];
  return [{ start: inTime, end: outTime }];
}

// ---------------------------------------------------------------------------
// Silence button
// ---------------------------------------------------------------------------

/**
 * Silence spans (seconds of the ORIGINAL voice file, as /api/audio/silences
 * reports them) -> program-time ranges for the ripple planner.
 *
 * Merge the spans, take away what the existing voice cuts already removed (a
 * span half inside a cut keeps only its surviving part; one entirely inside a
 * cut disappears), then map each piece onto the timeline clock. Pieces shorter
 * than one frame are dropped.
 *
 * @param {Array} spans  `{start,end}` or `{cut_start,cut_end}`
 * @param {object|null} voiceEdit  the ACTIVE edit (null when none / stale)
 */
export function silenceSpansToProgramRanges(spans, voiceEdit, sourceDuration) {
  const duration = finite(sourceDuration) ?? finite(voiceEdit?.source?.duration) ?? 0;
  const cuts = duration > 0 ? normalizeCuts(voiceEdit?.cuts, duration) : [];

  const pieces = [];
  for (const span of mergeSpans(spans)) {
    let parts = [{ start: span.start, end: span.end }];
    for (const cut of cuts) {
      const next = [];
      for (const part of parts) {
        if (cut.end <= part.start + EPS || cut.start >= part.end - EPS) {
          next.push(part);
          continue;
        }
        if (cut.start > part.start + EPS) next.push({ start: part.start, end: cut.start });
        if (cut.end < part.end - EPS) next.push({ start: cut.end, end: part.end });
      }
      parts = next;
    }
    pieces.push(...parts);
  }

  return pieces
    .map((piece) => ({ start: sourceToProgram(piece.start, cuts), end: sourceToProgram(piece.end, cuts) }))
    .filter((range) => range.end - range.start >= ONE_FRAME - EPS);
}

// ---------------------------------------------------------------------------
// Confirm dialog text
// ---------------------------------------------------------------------------

/**
 * Dialog copy for a plan: `describeRipplePlan` as is, except the silence button
 * names how many silent stretches go ("ตัดช่วงเงียบ 5 ช่วงออก?") even when
 * the planner merged them into one range.
 */
export function describeRippleConfirm(plan, { source = 'delete', count = null } = {}) {
  const text = describeRipplePlan(plan);
  if (text.blocked) return text;
  if (source === 'silence') {
    const n = Number.isFinite(count) && count > 0 ? count : (plan?.ranges?.length || 1);
    return { ...text, title: `ตัดช่วงเงียบ ${n} ช่วงออก?` };
  }
  return text;
}

/**
 * The text shown when the planner refuses a cut. A refused Delete says how to
 * delete anyway: the scope toggle's "ลบเฉพาะภาพ" has no length rule on the voice.
 */
export function describeRippleBlocked(reason, { source = 'delete' } = {}) {
  const text = String(reason || '').trim() || 'ตัดช่วงนี้ไม่ได้';
  return source === 'delete'
    ? `${text} (ถ้าต้องการลบคลิปจริง ให้สลับเป็น "ลบเฉพาะภาพ" ที่แถบเครื่องมือ)`
    : text;
}

// ---------------------------------------------------------------------------
// Voice-cut markers and the re-mix trigger
// ---------------------------------------------------------------------------

/**
 * One marker per voice cut, positioned on the program clock where the cut
 * joins: `sourceToProgram(cut.start)`. `voiceEdit` is the ACTIVE edit (null when
 * the cuts are stale, so nothing is drawn for cuts the render ignores).
 */
export function voiceCutMarkers(voiceEdit) {
  const duration = finite(voiceEdit?.source?.duration);
  if (!duration || duration <= 0) return [];
  const cuts = normalizeCuts(voiceEdit?.cuts, duration);
  return cuts.map((cut) => {
    const seconds = cut.end - cut.start;
    return {
      id: cut.id || `${cut.start}-${cut.end}`,
      time: sourceToProgram(cut.start, cuts),
      seconds,
      title: `ตัด ${seconds.toFixed(2)} วิ`,
    };
  });
}

/**
 * A short string that changes whenever the cuts the render applies change.
 * Compared with the value loaded/rendered last to decide the audio mix has to
 * run again ('' = no cuts). Ids and reasons are ignored on purpose.
 */
export function voiceCutSignature(voiceEdit) {
  const duration = finite(voiceEdit?.source?.duration);
  if (!duration || duration <= 0) return '';
  return normalizeCuts(voiceEdit?.cuts, duration)
    .map((cut) => `${cut.start.toFixed(4)}-${cut.end.toFixed(4)}`)
    .join('|');
}
