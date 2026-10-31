// SFX density plan -- a line-for-line port of plan_sfx_events() in
// scripts/sfx_manager.py, so the editor preview lays down exactly the SFX hits
// the render's mix keeps (Preview = Render, AGENTS.md rule 9).
//
// The render keeps at most one SFX per SFX_MIN_GAP_S window (measured at the
// time the sound is heard, transition pre-roll included), lets the hook line's
// own early SFX replace the automatic boom at 0.0, and only lets a whoosh that
// is bound to a visual cut skip the gap rule. Any rule changed there must be
// changed here: tests/fixtures/sfx_highlight_parity_cases.json is run through
// both implementations (tests/test_preview_render_parity.py and
// sfxPlan.test.js) and both must produce the stored expectation.

export const SFX_MIN_GAP_S = 2.0;
export const SFX_OPENER_WINDOW_S = 0.5;
export const SFX_CUT_SNAP_S = 0.1;
const SFX_TRANSITION_WORDS = ['whoosh', 'swish', 'swoosh', 'transition'];
export const SFX_PRE_ROLL_S = 0.12;
const SFX_MIN_FIRE_S = 0.02;
const SFX_ROLE_PRIORITY = { opener: 2, closer: 2, line: 1 };
const SFX_SOURCE_ORDER = { boom: 0, cue: 1, overlay: 2 };

const PY_FLOAT_RE = /^[+-]?(?:\d+(?:_\d+)*\.?(?:\d+(?:_\d+)*)?|\.\d+(?:_\d+)*)(?:[eE][+-]?\d+(?:_\d+)*)?$/;
const PY_NONFINITE_RE = /^[+-]?(?:inf|infinity|nan)$/i;

// Python's float(): numbers and numeric strings only; null for what it rejects.
function pyFloat(value) {
  if (typeof value === 'number') return value;
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (typeof value !== 'string') return null;
  const s = value.trim();
  if (PY_NONFINITE_RE.test(s)) return Number.NaN;
  if (!PY_FLOAT_RE.test(s)) return null;
  return Number(s.replace(/_/g, ''));
}

function isMapping(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

// _event_start(): `event.get("start", default)` then float(); null when unusable.
function eventStart(event, fallback) {
  const raw = event.start !== undefined ? event.start : fallback;
  const start = pyFloat(raw);
  return start !== null && Number.isFinite(start) ? start : null;
}

export function isSfxEventEligible(event, { totalDuration = null, defaultStart = null } = {}) {
  if (!isMapping(event)) return false;
  const name = event.sfx;
  if (typeof name !== 'string' || !name.trim()) return false;
  if (['sfx_enabled', 'sfx_event', 'enabled'].some((flag) => event[flag] === false)) return false;

  const start = eventStart(event, defaultStart);
  if (start === null || start < 0) return false;
  if (totalDuration !== null && totalDuration !== undefined) {
    const duration = pyFloat(totalDuration);
    if (duration === null || !Number.isFinite(duration) || duration < 0 || start > duration) return false;
  }
  if (event.end !== undefined && event.end !== null) {
    const end = pyFloat(event.end);
    if (end === null || !Number.isFinite(end) || end < start) return false;
  }
  return true;
}

export function sfxEventStart(event, fallback = 0) {
  const start = eventStart(event, fallback);
  return start === null ? fallback : start;
}

export function isTransitionSfxName(name) {
  const low = String(name || '').toLowerCase();
  return SFX_TRANSITION_WORDS.some((w) => low.includes(w));
}

const rankKey = (c) => [
  -SFX_ROLE_PRIORITY[c.role],
  c.fire,
  SFX_SOURCE_ORDER[c.source],
  c.index === null ? -1 : c.index,
];

function compareKeys(a, b) {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return 0;
}

/**
 * Which SFX events the mix keeps. Pure and deterministic.
 *
 * `sfxFilename(tag)` returns the resolved file name for a cue/overlay tag, or
 * null when the file is missing (such an event never takes a slot). Without
 * it the tag itself is the name. Returns kept events in mix order (boom, cues
 * by index, overlays by index), each
 * `{source, index, sfx, start, fire, role, exempt}`.
 */
export function planSfxEvents(cues, overlays = null, {
  totalDuration = null,
  boomAvailable = true,
  minGap = SFX_MIN_GAP_S,
  cutTimes = null,
  sfxFilename = null,
} = {}) {
  const resolveName = typeof sfxFilename === 'function' ? sfxFilename : (tag) => tag;
  const cuts = [];
  for (const t of cutTimes || []) {
    const value = pyFloat(t);
    if (value !== null && Number.isFinite(value)) cuts.push(value);
  }

  const candidates = [];
  const add = (source, index, event, defaultStart) => {
    if (!isSfxEventEligible(event, { totalDuration, defaultStart })) return;
    const tag = event.sfx;
    const name = resolveName(tag);
    if (!name) return;
    const start = sfxEventStart(event, defaultStart === null ? 0 : defaultStart);
    const transition = isTransitionSfxName(name);
    const fire = Math.max(SFX_MIN_FIRE_S, start - (transition ? SFX_PRE_ROLL_S : 0));
    const bound = event.cut_bound === true || cuts.some((c) => Math.abs(start - c) <= SFX_CUT_SNAP_S);
    candidates.push({
      source, index, sfx: tag, start, fire, role: 'line', exempt: Boolean(transition && bound),
    });
  };

  (cues || []).forEach((cue, idx) => add('cue', idx, cue, null));
  (overlays || []).forEach((item, idx) => add('overlay', idx, item, 0));

  const cueEvents = candidates
    .filter((c) => c.source === 'cue')
    .sort((a, b) => compareKeys([a.fire, a.index], [b.fire, b.index]));
  const hookCarriesOpener = cueEvents.length > 0 && cueEvents[0].start <= SFX_OPENER_WINDOW_S;
  if (hookCarriesOpener) {
    cueEvents[0].role = 'opener';
  } else if (boomAvailable) {
    candidates.unshift({
      source: 'boom', index: null, sfx: 'boom', start: 0, fire: 0, role: 'opener', exempt: false,
    });
  }
  if (cueEvents.length > 0 && cueEvents[cueEvents.length - 1].role === 'line') {
    cueEvents[cueEvents.length - 1].role = 'closer';
  }

  const kept = [];
  const ranked = [...candidates].sort((a, b) => compareKeys(rankKey(a), rankKey(b)));
  for (const cand of ranked) {
    if (cand.exempt) {
      kept.push(cand);
      continue;
    }
    if (kept.every((k) => k.exempt || Math.abs(k.fire - cand.fire) >= minGap - 1e-9)) kept.push(cand);
  }

  kept.sort((a, b) => compareKeys(
    [SFX_SOURCE_ORDER[a.source], a.index === null ? -1 : a.index],
    [SFX_SOURCE_ORDER[b.source], b.index === null ? -1 : b.index],
  ));
  return kept;
}
