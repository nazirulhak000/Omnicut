import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MIN_RIPPLE_ITEM_SECONDS,
  applyRipplePlan,
  defaultRippleScope,
  describeRipplePlan,
  formatRippleTime,
  planRippleRanges,
  revealIsUsable,
  rippleTimedItem,
  rippleTimedList,
} from './rippleRange.js';
import {
  buildSegments,
  getDrawPlan,
  interpolateKeyframes,
  splitClipAt,
  totalDuration,
} from './timelineMath.js';
import { shiftTime } from './voiceCutMap.js';
import {
  groupScopedBackgroundIsolationClips,
  resolveBackgroundIsolationConfig,
  scopedArtifactCoversClip,
} from './backgroundIsolationPreview.js';
import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** Three 5-second clips laid end to end: a 0-5, b 5-10, c 10-15 (all hard cuts). */
const abc = () => [
  { id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 5 },
  { id: 'b', source_path: 'b.mp4', trim_start: 0, trim_end: 5 },
  { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 5 },
];
const DURATIONS = { a: 10, b: 10, c: 10, d: 10 };

const state = (clipList, extra = {}) => ({
  clipList,
  cuesList: [],
  microCuesList: [],
  overlays: [],
  stickers: [],
  effects: [],
  voiceEdit: null,
  voiceEditStale: false,
  voiceEditNotice: null,
  style: { bgmName: 'upbeat', stickerBadge: '' },
  ...extra,
});

const idFactory = () => {
  let n = 0;
  return () => `new-${++n}`;
};

/** Options of a voiceover project: 15 s of voice under the 15 s picture. */
const voiceOpts = (extra = {}) => ({
  durations: DURATIONS,
  hasVoice: true,
  audioDuration: 15,
  newId: idFactory(),
  newCutId: () => 'cut-new',
  ...extra,
});

const approx = (actual, expected, message) => assert.ok(
  Math.abs(actual - expected) < 1e-6,
  `${message || 'value'}: ${actual} != ${expected}`,
);

const cue = (start, end, extra = {}) => ({ start, end, text: `cue ${start}`, _uid: `u${start}`, ...extra });

// ---------------------------------------------------------------------------
// defaultRippleScope
// ---------------------------------------------------------------------------

test('defaultRippleScope: voice present -> all, otherwise video', () => {
  assert.equal(defaultRippleScope(true), 'all');
  assert.equal(defaultRippleScope(false), 'video');
  assert.equal(defaultRippleScope(undefined), 'video');
});

// ---------------------------------------------------------------------------
// Clip list (plan 2.2 row "clipList")
// ---------------------------------------------------------------------------

test('a range covering a whole clip removes it; the clip after it becomes a hard cut', () => {
  // c fades in over b's last 0.4 s, so its layout is c 9.6-13.6.
  const clips = abc();
  clips[2] = { ...clips[2], trim_end: 4, transition_in: 'fade', transition_duration: 0.4 };
  const plan = planRippleRanges(state(clips), [{ start: 5, end: 10 }], voiceOpts({ scope: 'video' }));
  assert.equal(plan.blocked, null);
  const list = plan.state.clipList;
  assert.deepEqual(list.map((c) => c.id), ['a', 'c']);
  assert.equal(list[1].transition_in, 'cut', 'the new junction is a cut');
  approx(list[1].trim_start, 0.4, 'c lost its 0.4 s transition head');
  assert.equal(plan.summary.clips.removed, 1);
  assert.equal(plan.summary.clips.trimmed, 1);
  approx(plan.summary.pictureAfter, 8.6, 'a 5 + c 3.6');
});

test('tail trim: a range that starts inside a clip and runs past its end', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 4, end: 7 }], voiceOpts({ scope: 'video' }));
  const [a, b, c] = plan.state.clipList;
  assert.equal(a.id, 'a');
  assert.equal(a.trim_end, 4);
  assert.equal(b.trim_start, 2, 'b head trimmed by 7 - 5 s');
  assert.equal(b.trim_end, 5);
  assert.equal(c.id, 'c');
  approx(plan.summary.pictureAfter, 12);
  assert.equal(plan.summary.clips.trimmed, 2);
});

test('head trim keeps the clip id and its source window end', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 0, end: 2 }], voiceOpts({ scope: 'video' }));
  const [a] = plan.state.clipList;
  assert.equal(a.id, 'a');
  assert.equal(a.trim_start, 2);
  assert.equal(a.trim_end, 5);
});

test('a cut in the MIDDLE of a clip splits it, drops the middle piece and rebases the keyframes', () => {
  const clips = abc();
  clips[0] = {
    ...clips[0],
    keyframes: [
      { time: 0, property: 'zoom', value: 1 },
      { time: 4, property: 'zoom', value: 2, easing: 'ease_in' },
    ],
  };
  const plan = planRippleRanges(state(clips), [{ start: 1, end: 3 }], voiceOpts({ scope: 'video' }));
  const [left, right, b] = plan.state.clipList;
  assert.equal(plan.state.clipList.length, 4);
  assert.equal(left.id, 'a', 'the left piece stays the same clip');
  assert.equal(left.trim_end, 1);
  assert.equal(right.id, 'new-1');
  assert.equal(right.trim_start, 3);
  assert.equal(right.trim_end, 5);
  assert.equal(right.transition_in, 'cut');
  assert.equal(b.id, 'b');
  assert.equal(plan.summary.clips.split, 1);
  approx(plan.summary.pictureAfter, 13);

  // The keyframe maths is splitClipAt's, byte for byte: cut at 1 -> left half, cut at 3 -> right half.
  const seg = buildSegments(clips, DURATIONS)[0];
  let n = 0;
  const makeId = () => `ref-${++n}`;
  const refLeft = splitClipAt(seg, 1, makeId)[0];
  const refRight = splitClipAt(seg, 3, makeId)[1];
  assert.deepEqual(left.keyframes, refLeft.keyframes);
  assert.deepEqual(right.keyframes, refRight.keyframes);
  assert.ok(left.keyframes.length > 2, 'the eased segment was baked into linear samples');
  assert.ok(right.keyframes.length >= 1);

  // Position continuity: the right piece plays the original track from t = 3.
  const original = clips[0].keyframes;
  const close = (a, b, message) => assert.ok(Math.abs(a - b) < 1e-5, `${message}: ${a} != ${b}`);
  for (const local of [0, 0.25, 0.5, 1, 1.5]) {
    close(
      interpolateKeyframes(right.keyframes, local, 1),
      interpolateKeyframes(original, 3 + local, 1),
      `right piece at ${local}`,
    );
  }
  close(interpolateKeyframes(left.keyframes, 1, 1), interpolateKeyframes(original, 1, 1), 'left piece at the cut');
});

test('a speed-2 clip: the cut is measured on the timeline and applied x speed to the source', () => {
  const clips = [{ id: 'a', source_path: 'a.mp4', trim_start: 1, trim_end: 9, speed: 2 }, ...abc().slice(1)];
  // a plays 1-9 at 2x = 4 s on the timeline (0-4), then b, c.
  const plan = planRippleRanges(state(clips), [{ start: 1, end: 2 }], voiceOpts({ scope: 'video' }));
  const [left, right] = plan.state.clipList;
  assert.equal(left.trim_end, 3, 'left keeps 1 s of timeline = 2 s of source');
  assert.equal(right.trim_start, 5, 'right resumes after 2 s of timeline = 4 s of source');
  assert.equal(right.trim_end, 9);
});

test('freeze tail: cutting the tail drops the hold, cutting inside the hold shortens it', () => {
  const clips = [{ id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 4, freeze_tail: 2 }, ...abc().slice(1)];
  // a = 4 s of picture + 2 s hold = 0-6
  const cutPicture = planRippleRanges(state(clips), [{ start: 3, end: 5 }], voiceOpts({ scope: 'video' }));
  assert.equal(cutPicture.state.clipList[0].trim_end, 3);
  assert.equal(Object.hasOwn(cutPicture.state.clipList[0], 'freeze_tail'), false, 'the hold was in the cut range');

  const cutHold = planRippleRanges(state(clips), [{ start: 5, end: 6 }], voiceOpts({ scope: 'video' }));
  const a = cutHold.state.clipList[0];
  assert.equal(a.trim_end, 4, 'the picture stays whole');
  approx(a.freeze_tail, 1, 'the hold is 1 s shorter');
});

test('an edge inside a transition overlap is pushed out to the overlap edge and reported', () => {
  // a 0-5, b fades in over 4.6-5.0 (b 4.6-10.6), c 10.6-14.6
  const clips = [
    { id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 5 },
    { id: 'b', source_path: 'b.mp4', trim_start: 0, trim_end: 6, transition_in: 'fade', transition_duration: 0.4 },
    { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 4 },
  ];
  const plan = planRippleRanges(state(clips), [{ start: 4.8, end: 8 }], voiceOpts());
  approx(plan.ranges[0].start, 4.6, 'start pulled back to the overlap start');
  approx(plan.ranges[0].requestedStart, 4.8);
  approx(plan.summary.extended.transition, 0.2);
  assert.ok(plan.summary.warnings.some((w) => w.includes('ขยายช่วงให้พ้นทรานซิชัน')));
  const [a, b] = plan.state.clipList;
  approx(a.trim_end, 4.6);
  approx(b.trim_start, 3.4);
  assert.equal(b.transition_in, 'cut');

  // And the right-hand edge too.
  const right = planRippleRanges(state(clips), [{ start: 3, end: 4.8 }], voiceOpts({ scope: 'video' }));
  approx(right.ranges[0].end, 5);
  approx(right.state.clipList[1].trim_start, 0.4);
});

test('a sliver shorter than 0.2 s would be left behind -> the range swallows it and says so', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 0.1, end: 2 }], voiceOpts({ scope: 'video' }));
  approx(plan.ranges[0].start, 0, 'the 0.1 s head of a goes too');
  approx(plan.summary.extended.sliver, 0.1);
  assert.ok(plan.summary.warnings.some((w) => w.includes('0.2')));
});

test('the first clip never keeps a transition into a cut that removed what came before it', () => {
  const clips = abc();
  clips[1] = { ...clips[1], transition_in: 'wipeleft', transition_duration: 0.4 };
  const plan = planRippleRanges(state(clips), [{ start: 0, end: 5 }], voiceOpts({ scope: 'video' }));
  assert.equal(plan.state.clipList[0].id, 'b');
  assert.equal(plan.state.clipList[0].transition_in, 'cut');

  // A first clip the range does not touch keeps its opening transition.
  const opening = abc();
  opening[0] = { ...opening[0], transition_in: 'fade', transition_duration: 0.4 };
  const kept = planRippleRanges(state(opening), [{ start: 8, end: 10 }], voiceOpts({ scope: 'video' }));
  assert.equal(kept.state.clipList[0].transition_in, 'fade');
});

test('new pieces carry the source length of their parent clip', () => {
  const clips = [{ id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: null }, ...abc().slice(1)];
  const plan = planRippleRanges(state(clips), [{ start: 1, end: 2 }], voiceOpts({ scope: 'video' }));
  assert.equal(plan.state.clipList[1].trim_end, 10, 'trim_end null -> the known source length, never null');
});

test('a clip whose source length is not known yet blocks the cut with a reason', () => {
  const clips = [{ id: 'x', source_path: 'x.mp4', trim_start: 0, trim_end: null }, ...abc().slice(1)];
  const plan = planRippleRanges(state(clips), [{ start: 0, end: 1 }], { hasVoice: true, audioDuration: 15 });
  assert.ok(plan.blocked);
  assert.equal(plan.changed, false);
});

// ---------------------------------------------------------------------------
// Cues, micro cues, word tracks (plan 2.2 rows "cues" and "word_reveal")
// ---------------------------------------------------------------------------

test('cues: before stays, after shifts, inside is removed, straddlers are trimmed, a spanning cue is flagged', () => {
  const cues = [
    cue(0.5, 1.5),
    cue(6.5, 7.5, { sfx: 'pop' }),
    cue(5.5, 6.5),
    cue(7.5, 9),
    cue(5, 9, { text: 'spanning' }),
    cue(10, 12),
    cue(5.95, 6.5, { text: 'sliver' }),
  ];
  const plan = planRippleRanges(state(abc(), { cuesList: cues }), [{ start: 6, end: 8 }], voiceOpts());
  const out = plan.state.cuesList;
  assert.equal(out[0], cues[0], 'untouched cue keeps its identity');
  const byText = (text) => out.find((c) => c.text === text);
  assert.equal(byText('cue 6.5'), undefined, 'inside -> removed');
  assert.equal(byText('sliver'), undefined, 'trimmed to under 0.1 s -> removed');
  const left = out.find((c) => c._uid === 'u5.5');
  approx(left.start, 5.5);
  approx(left.end, 6, 'left straddler ends at t0');
  const rightStraddler = out.find((c) => c._uid === 'u7.5');
  approx(rightStraddler.start, 6, 'right straddler starts at t0');
  approx(rightStraddler.end, 7);
  const spanning = byText('spanning');
  approx(spanning.start, 5);
  approx(spanning.end, 7, 'end - d');
  assert.equal(spanning.ripple_text_cut, true);
  assert.equal(Object.hasOwn(left, 'ripple_text_cut'), false);
  const later = out.find((c) => c._uid === 'u10');
  approx(later.start, 8);
  approx(later.end, 10);

  assert.equal(plan.summary.cues.removed, 2);
  assert.equal(plan.summary.cues.textCut, 1);
  assert.equal(plan.summary.cues.retimed, 4);
  assert.equal(plan.summary.sfxRemoved, 1, 'the removed cue took its SFX with it');
  assert.ok(plan.summary.warnings.some((w) => w.includes('ซับ 1 บรรทัดยังแสดงข้อความเต็ม')));
});

test('micro cues follow exactly the same rules as cues', () => {
  const micro = [cue(0.5, 1.5), cue(6.2, 7.7), cue(5, 9, { text: 'micro span' }), cue(10, 12)];
  const plan = planRippleRanges(state(abc(), { microCuesList: micro }), [{ start: 6, end: 8 }], voiceOpts());
  const out = plan.state.microCuesList;
  assert.equal(out.length, 3);
  assert.equal(out[0], micro[0]);
  assert.equal(out[1].text, 'micro span');
  assert.equal(out[1].ripple_text_cut, true);
  approx(out[2].start, 8);
  assert.equal(plan.summary.microCues.removed, 1);
  assert.equal(plan.state.cuesList.length, 0, 'the two lists are independent');
});

test('word_reveal and word_timings are mapped with shiftTime; words inside the range collapse onto t0', () => {
  const words = [
    { text: 'one', start: 5, end: 6 },
    { text: 'two', start: 6, end: 7 },
    { text: 'three', start: 7, end: 8 },
    { text: 'four', start: 8, end: 9 },
  ];
  const target = cue(5, 9, { text: 'one two three four', word_reveal: words, word_timings: words });
  const plan = planRippleRanges(state(abc(), { cuesList: [target] }), [{ start: 6, end: 8 }], voiceOpts());
  const out = plan.state.cuesList[0];
  approx(out.end, 7);
  assert.deepEqual(
    out.word_reveal.map((w) => [w.text, w.start, w.end]),
    [['one', 5, 6], ['two', 6, 6], ['three', 6, 6], ['four', 6, 7]],
  );
  assert.deepEqual(out.word_timings.map((w) => [w.start, w.end]), out.word_reveal.map((w) => [w.start, w.end]));
  assert.equal(revealIsUsable(out.word_reveal), true);
  assert.equal(words[1].end, 7, 'the input track was not mutated');
});

test('a reveal that stops being usable (or no longer spells the caption) is dropped', () => {
  const oneWord = cue(5, 9, { text: 'one', word_reveal: [{ text: 'one', start: 5, end: 9 }] });
  const wrongText = cue(5, 9, {
    text: 'one two',
    word_reveal: [{ text: 'xxx', start: 5, end: 7 }, { text: 'yyy', start: 7, end: 9 }],
  });
  const plan = planRippleRanges(
    state(abc(), { cuesList: [oneWord, wrongText] }),
    [{ start: 6, end: 8 }],
    voiceOpts(),
  );
  assert.equal(Object.hasOwn(plan.state.cuesList[0], 'word_reveal'), false);
  assert.equal(Object.hasOwn(plan.state.cuesList[1], 'word_reveal'), false);
  assert.equal(plan.summary.cues.revealDropped, 2);
});

test('a cue that only moves keeps its (translated) reveal, even a single-word one', () => {
  const later = cue(10, 12, { text: 'solo', word_reveal: [{ text: 'solo', start: 10, end: 12 }] });
  const plan = planRippleRanges(state(abc(), { cuesList: [later] }), [{ start: 6, end: 8 }], voiceOpts());
  assert.deepEqual(plan.state.cuesList[0].word_reveal, [{ text: 'solo', start: 8, end: 10 }]);
});

// ---------------------------------------------------------------------------
// Overlays, stickers, effects, SFX, BGM
// ---------------------------------------------------------------------------

test('overlays, stickers and effects use the cue rule; hidden is kept; overlay SFX go with their owner', () => {
  const overlays = [
    { id: 'ovl_hook', kind: 'hook', start: 0, end: 5, hidden: false, sfx: 'boom' },
    { id: 'ovl_text', kind: 'text', start: 6.5, end: 7.5, hidden: true, sfx: 'pop' },
    { id: 'ovl_late', kind: 'text', start: 10, end: 12, hidden: true },
  ];
  const stickers = [{ id: 's1', badge: 'b.png', start: 9, end: 11, hidden: true }];
  const effects = [{ id: 'e1', effectId: 'spark', start: 5, end: 9, hidden: false }];
  const plan = planRippleRanges(
    state(abc(), { overlays, stickers, effects }),
    [{ start: 0, end: 1 }, { start: 6, end: 8 }],
    voiceOpts(),
  );
  const [hook, late] = plan.state.overlays;
  assert.equal(plan.state.overlays.length, 2, 'the text overlay inside [6,8) was removed');
  approx(hook.start, 0);
  approx(hook.end, 4, 'the hook lost its first second: 5 - 1');
  approx(late.start, 7);
  assert.equal(late.hidden, true);
  assert.equal(plan.state.stickers[0].hidden, true);
  approx(plan.state.stickers[0].start, 6);
  approx(plan.state.effects[0].end, 6, '9 - 1 - 2');
  assert.equal(plan.summary.overlays.removed, 1);
  assert.equal(plan.summary.sfxRemoved, 1, 'the text overlay SFX went with it');
});

test('BGM and every non-time setting are left alone', () => {
  const base = state(abc(), { cuesList: [cue(10, 12)] });
  const plan = planRippleRanges(base, [{ start: 6, end: 8 }], voiceOpts());
  assert.equal(Object.hasOwn(plan.state, 'style'), false, 'style (bgm, volumes, caption look) is not part of the patch');
  const next = applyRipplePlan(base, plan);
  assert.equal(next.style, base.style);
});

test('the legacy single-sticker mirror in style moves too, but only while stickers[] is empty', () => {
  const style = { bgmName: 'x', stickerBadge: 'badge.png', stickerStartTime: 9, stickerEndTime: 11 };
  const plan = planRippleRanges(state(abc(), { style }), [{ start: 6, end: 8 }], voiceOpts());
  assert.equal(plan.state.style.stickerStartTime, 7);
  assert.equal(plan.state.style.stickerEndTime, 9);
  assert.equal(plan.state.style.bgmName, 'x');
  const gone = planRippleRanges(
    state(abc(), { style: { ...style, stickerStartTime: 6.2, stickerEndTime: 7.5 } }),
    [{ start: 6, end: 8 }],
    voiceOpts(),
  );
  assert.equal(gone.state.style.stickerBadge, '');
  const real = planRippleRanges(
    state(abc(), { style, stickers: [{ id: 's', badge: 'badge.png', start: 9, end: 11 }] }),
    [{ start: 6, end: 8 }],
    voiceOpts(),
  );
  assert.equal(Object.hasOwn(real.state, 'style'), false);
});

test('rippleTimedItem: every position of an item against the removed range', () => {
  const t0 = 4;
  const t1 = 6;
  const status = (start, end) => rippleTimedItem({ start, end }, t0, t1, { isCue: true }).status;
  assert.equal(status(0, 4), 'same', 'ends exactly at t0');
  assert.equal(status(6, 8), 'shifted', 'starts exactly at t1');
  assert.equal(status(4, 6), 'removed', 'exactly the range');
  assert.equal(status(4.5, 5.5), 'removed');
  assert.equal(status(3, 5), 'trimmed');
  assert.equal(status(5, 8), 'trimmed');
  assert.equal(status(3, 8), 'trimmed');
  assert.equal(status(5, 5.05), 'removed', 'a zero-ish item inside');
  assert.equal(status(5.95, 6.04), 'removed', 'enters from the right and keeps only 0.04 s');
  const tiny = rippleTimedItem({ start: 3.95, end: 4.5 }, t0, t1);
  assert.equal(tiny.status, 'removed', `trimmed under ${MIN_RIPPLE_ITEM_SECONDS} s`);
  const untouchedTiny = rippleTimedItem({ start: 1, end: 1.02 }, t0, t1);
  assert.equal(untouchedTiny.status, 'same', 'a short item outside the range is never deleted');
  assert.equal(rippleTimedItem({ start: 'x', end: 5 }, t0, t1).status, 'same');
  assert.equal(rippleTimedItem(null, t0, t1).status, 'same');
});

test('rippleTimedList returns the same array when nothing moved', () => {
  const list = [{ start: 0, end: 1 }];
  const result = rippleTimedList(list, 5, 6);
  assert.equal(result.list, list);
  assert.equal(result.changed, false);
});

test('invariant: every surviving item sits at shiftTime(old start/end)', () => {
  let seed = 12345;
  const rnd = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };
  for (let round = 0; round < 200; round += 1) {
    const t0 = Math.floor(rnd() * 100) / 10;
    const t1 = t0 + 0.1 + Math.floor(rnd() * 50) / 10;
    const items = Array.from({ length: 12 }, () => {
      const start = Math.floor(rnd() * 150) / 10;
      return { start, end: start + 0.1 + Math.floor(rnd() * 40) / 10 };
    });
    const { list, removed } = rippleTimedList(items, t0, t1);
    const survivors = items.filter((item) => !removed.includes(item));
    assert.equal(list.length, survivors.length);
    survivors.forEach((old, i) => {
      approx(list[i].start, shiftTime(old.start, t0, t1), `start r${round}`);
      approx(list[i].end, shiftTime(old.end, t0, t1), `end r${round}`);
      assert.ok(list[i].end > list[i].start - 1e-9);
    });
  }
});

// ---------------------------------------------------------------------------
// Voice cuts (plan 2.2 row "เสียงพากย์", 2.5)
// ---------------------------------------------------------------------------

test('a first cut stores source-time cuts and sends only the duration as source', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 6, end: 8 }], voiceOpts());
  assert.deepEqual(plan.state.voiceEdit, {
    schema_version: 1,
    source: { duration: 15 },
    cuts: [{ id: 'cut-new', start: 6, end: 8, reason: 'manual' }],
  });
  assert.equal(plan.state.voiceEditStale, false);
  assert.equal(plan.state.voiceEditNotice, null);
  approx(plan.summary.voiceBefore, 15);
  approx(plan.summary.voiceAfter, 13);
  approx(plan.summary.voiceShortenedBy, 2);
  approx(plan.summary.removedSeconds, 2);
  approx(plan.summary.after, 13);
  assert.equal(plan.playhead, 6);
});

const EXISTING_EDIT = {
  schema_version: 1,
  source: { duration: 20, path: 'p/voice.wav', size: 123, mtime_ns: 456 },
  cuts: [{ id: 'old', start: 4, end: 5, reason: 'manual' }],
};

test('a new range is converted to source time through the existing cuts and merged with them', () => {
  // 20 s of voice minus 1 s = 19 s on the clock; the picture is 15 s.
  const base = state(abc(), { voiceEdit: EXISTING_EDIT });
  const opts = voiceOpts({ audioDuration: 19 });

  const after = planRippleRanges(base, [{ start: 10, end: 11 }], opts);
  assert.deepEqual(after.state.voiceEdit.cuts, [
    { id: 'old', start: 4, end: 5, reason: 'manual' },
    { id: 'cut-new', start: 11, end: 12, reason: 'manual' },
  ]);
  assert.deepEqual(after.state.voiceEdit.source, EXISTING_EDIT.source, 'the stored fingerprint is kept, never invented');

  // [3,5] on the clock covers the join at 4: source 3..6 swallows the old cut.
  const across = planRippleRanges(base, [{ start: 3, end: 5 }], opts);
  assert.deepEqual(across.state.voiceEdit.cuts, [{ id: 'cut-new', start: 3, end: 6, reason: 'manual' }]);
  approx(across.summary.voiceBefore, 19);
  approx(across.summary.voiceAfter, 17);
  approx(across.summary.voiceShortenedBy, 2, 'cuts never overlap, and the clock moved by exactly the range');

  // Cutting right after the join (range [4,5]) extends the old cut.
  const touch = planRippleRanges(base, [{ start: 4, end: 5 }], opts);
  assert.deepEqual(touch.state.voiceEdit.cuts, [{ id: 'old', start: 4, end: 6, reason: 'manual' }]);
});

test('the voice is only cut where there is voice: past its end the picture alone is cut', () => {
  // 12 s of voice under 15 s of picture.
  const opts = voiceOpts({ audioDuration: 12 });
  const past = planRippleRanges(state(abc()), [{ start: 13, end: 14 }], opts);
  assert.equal(Object.hasOwn(past.state, 'voiceEdit'), false, 'no voice cut for a range after the voice');
  approx(past.summary.voiceShortenedBy, 0);
  approx(past.summary.pictureAfter, 14);

  const across = planRippleRanges(state(abc()), [{ start: 11, end: 13 }], opts);
  assert.deepEqual(across.state.voiceEdit.cuts, [{ id: 'cut-new', start: 11, end: 12, reason: 'manual' }]);
  approx(across.summary.voiceShortenedBy, 1);
  approx(across.summary.pictureAfter, 13);
});

test('voice longer than the picture: a range after the picture only cuts voice and captions', () => {
  const clips = abc();
  const plan = planRippleRanges(
    state(clips, { cuesList: [cue(17, 19)] }),
    [{ start: 16, end: 18 }],
    voiceOpts({ audioDuration: 20 }),
  );
  assert.deepEqual(plan.state.clipList, clips);
  assert.deepEqual(plan.state.voiceEdit.cuts, [{ id: 'cut-new', start: 16, end: 18, reason: 'manual' }]);
  approx(plan.state.cuesList[0].start, 16);
  approx(plan.summary.pictureAfter, 15);
  approx(plan.summary.voiceAfter, 18);
});

test('scope video touches clipList only and warns that the picture will end before the voice', () => {
  const base = state(abc(), { cuesList: [cue(10, 12)], voiceEdit: EXISTING_EDIT });
  const plan = planRippleRanges(base, [{ start: 6, end: 8 }], voiceOpts({ scope: 'video', audioDuration: 19 }));
  assert.deepEqual(Object.keys(plan.state), ['clipList']);
  const next = applyRipplePlan(base, plan);
  assert.equal(next.cuesList, base.cuesList);
  assert.equal(next.voiceEdit, base.voiceEdit);
  assert.ok(plan.summary.warnings.some((w) => w.includes('ค้างเฟรมสุดท้าย')));
  approx(plan.summary.voiceShortenedBy, 0);
});

test('no-voice project: default scope is video; scope all still ripples captions but never invents a voice cut', () => {
  const base = state(abc(), { cuesList: [cue(10, 12)] });
  const video = planRippleRanges(base, [{ start: 6, end: 8 }], { durations: DURATIONS, newId: idFactory() });
  assert.equal(video.scope, 'video');
  assert.deepEqual(Object.keys(video.state), ['clipList']);

  const all = planRippleRanges(base, [{ start: 6, end: 8 }], {
    durations: DURATIONS, newId: idFactory(), scope: 'all', hasVoice: false,
  });
  assert.equal(all.scope, 'all');
  approx(all.state.cuesList[0].start, 8);
  assert.equal(Object.hasOwn(all.state, 'voiceEdit'), false);
});

test('a stale voice edit is not built on: a fresh edit starts and the user is told', () => {
  const stale = { ...EXISTING_EDIT, source: { ...EXISTING_EDIT.source, duration: 99 } };
  const plan = planRippleRanges(
    state(abc(), { voiceEdit: stale, voiceEditStale: true, voiceEditNotice: { kind: 'stale', reason: 'x' } }),
    [{ start: 6, end: 8 }],
    voiceOpts({ audioDuration: 15 }),
  );
  assert.deepEqual(plan.state.voiceEdit, {
    schema_version: 1,
    source: { duration: 15 },
    cuts: [{ id: 'cut-new', start: 6, end: 8, reason: 'manual' }],
  });
  assert.equal(plan.state.voiceEditStale, false);
  assert.equal(plan.state.voiceEditNotice, null);
  assert.ok(plan.summary.warnings.some((w) => w.includes('จุดตัดเสียงเดิมใช้ไม่ได้แล้ว')));
});

test('reason silence is stored on the cut', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 6, end: 8 }], voiceOpts({ reason: 'silence' }));
  assert.equal(plan.state.voiceEdit.cuts[0].reason, 'silence');
  assert.equal(plan.reason, 'silence');
});

// ---------------------------------------------------------------------------
// Edge cases (plan 2.5) and input handling
// ---------------------------------------------------------------------------

test('refuses when no clip would be left', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 0, end: 15 }], voiceOpts());
  assert.equal(plan.blocked, 'ตัดแล้วจะไม่เหลือคลิปเลย');
  assert.equal(plan.changed, false);
  assert.deepEqual(plan.state, {});
});

test('refuses when less than 1 s of picture or voice would be left', () => {
  const picture = planRippleRanges(state(abc()), [{ start: 0, end: 14.5 }], voiceOpts({ scope: 'video' }));
  assert.match(picture.blocked, /ภาพจะเหลือเพียง 0\.50 วินาที/);

  // 15 s of picture over only 3 s of voice: cutting [0.5, 3] would leave 0.5 s of voice.
  const voice = planRippleRanges(state(abc()), [{ start: 0.5, end: 3 }], voiceOpts({ audioDuration: 3 }));
  assert.match(voice.blocked, /เสียงพากย์จะเหลือเพียง 0\.50 วินาที/);
});

test('a range past the end is clamped to the total', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 14, end: 99 }], voiceOpts());
  approx(plan.ranges[0].end, 15);
  assert.equal(plan.state.clipList[2].trim_end, 4);
  approx(plan.summary.voiceAfter, 14);
  const outside = planRippleRanges(state(abc()), [{ start: 20, end: 30 }], voiceOpts());
  assert.ok(outside.blocked, 'entirely outside the timeline: nothing to do');
  assert.equal(outside.changed, false);
});

test('inputs are snapped to the 1/30 s frame grid', () => {
  const plan = planRippleRanges(state(abc()), [{ start: 1.01, end: 2.49 }], voiceOpts({ scope: 'video' }));
  assert.deepEqual(
    [plan.ranges[0].start, plan.ranges[0].end],
    [1, 2.5],
  );
  assert.equal(plan.state.clipList[1].trim_start, 2.5, 'the right piece resumes at the snapped time');
  const tooShort = planRippleRanges(state(abc()), [{ start: 1, end: 1.01 }], voiceOpts());
  assert.ok(tooShort.blocked);
});

test('accepted range shapes: {start,end}, {t0,t1}, {cut_start,cut_end}, [a,b]; junk is skipped', () => {
  const plan = planRippleRanges(
    state(abc()),
    [{ t0: 1, t1: 2 }, { cut_start: 3, cut_end: 4 }, [6, 7], { start: 'x', end: 2 }, null, { start: 5, end: 5 }],
    voiceOpts({ scope: 'video' }),
  );
  assert.deepEqual(plan.ranges.map((r) => [r.start, r.end]), [[1, 2], [3, 4], [6, 7]]);
});

test('several ranges apply from the LAST to the FIRST and equal two single cuts in that order', () => {
  const cues = [cue(0, 1), cue(2.5, 3.5), cue(5, 7), cue(8.2, 8.8), cue(9.5, 12)];
  const base = state(abc(), { cuesList: cues, overlays: [{ id: 'o', kind: 'text', start: 9, end: 14 }] });
  const both = planRippleRanges(base, [{ start: 8, end: 9 }, { start: 2, end: 3 }], voiceOpts());
  assert.deepEqual(both.ranges.map((r) => [r.start, r.end]), [[2, 3], [8, 9]], 'ascending, in original times');
  assert.equal(both.playhead, 2);

  const second = planRippleRanges(base, [{ start: 8, end: 9 }], voiceOpts());
  const afterSecond = applyRipplePlan(base, second);
  const first = planRippleRanges(afterSecond, [{ start: 2, end: 3 }], voiceOpts({ audioDuration: 14 }));
  const sequential = applyRipplePlan(afterSecond, first);
  const together = applyRipplePlan(base, both);
  assert.deepEqual(
    together.cuesList.map((c) => [c._uid, c.start, c.end]),
    sequential.cuesList.map((c) => [c._uid, c.start, c.end]),
  );
  assert.deepEqual(together.overlays, sequential.overlays);
  assert.deepEqual(
    together.voiceEdit.cuts.map((c) => [c.start, c.end]),
    [[2, 3], [8, 9]],
    'both cuts are in ORIGINAL file time',
  );
  assert.deepEqual(
    together.clipList.map((c) => [c.source_path, c.trim_start, c.trim_end]),
    sequential.clipList.map((c) => [c.source_path, c.trim_start, c.trim_end]),
  );
  approx(both.summary.voiceShortenedBy, 2);
});

test('overlapping and touching ranges are merged before anything is cut', () => {
  const plan = planRippleRanges(
    state(abc()),
    [{ start: 8, end: 9 }, { start: 2, end: 3 }, { start: 2.5, end: 4 }, { start: 4, end: 4.5 }],
    voiceOpts({ scope: 'video' }),
  );
  assert.deepEqual(plan.ranges.map((r) => [r.start, r.end]), [[2, 4.5], [8, 9]]);
});

test('an empty or missing request is refused, not applied', () => {
  assert.ok(planRippleRanges(state(abc()), [], voiceOpts()).blocked);
  assert.ok(planRippleRanges(state([]), [{ start: 1, end: 2 }], voiceOpts()).blocked);
  assert.ok(planRippleRanges(null, [{ start: 1, end: 2 }], voiceOpts()).blocked);
  const noop = planRippleRanges(state(abc()), [{ start: 1, end: 2 }], voiceOpts());
  assert.equal(applyRipplePlan(state(abc()), { ...noop, blocked: 'x' }).clipList.length, 3, 'a blocked plan applies nothing');
});

// ---------------------------------------------------------------------------
// Dialog text
// ---------------------------------------------------------------------------

test('formatRippleTime prints m:ss.cc', () => {
  assert.equal(formatRippleTime(4.6), '0:04.60');
  assert.equal(formatRippleTime(75.5), '1:15.50');
  assert.equal(formatRippleTime(59.999), '1:00.00');
  assert.equal(formatRippleTime(0), '0:00.00');
  assert.equal(formatRippleTime(-3), '0:00.00');
  assert.equal(formatRippleTime(Number.NaN), '0:00.00');
});

test('describeRipplePlan: the confirm text says what will happen, in Thai', () => {
  const cues = [cue(6.5, 7.5, { sfx: 'pop' }), cue(10, 12), cue(12, 13)];
  const plan = planRippleRanges(state(abc(), { cuesList: cues }), [{ start: 6, end: 8 }], voiceOpts());
  const text = describeRipplePlan(plan);
  assert.equal(text.title, 'ตัดช่วง 0:06.00–0:08.00 ออก?');
  assert.equal(text.subtitle, 'ภาพ เสียงพากย์ ซับ และข้อความหลังจุดนี้จะเลื่อนมาชิดกัน');
  assert.equal(
    text.summary,
    'เสียงพากย์สั้นลง 2.00 วินาที (15.00 → 13.00) · ลบซับ 1 บรรทัด · ปรับเวลาซับ 2 บรรทัด · ลบ SFX 1 เสียง · ตัดคลิป 1 คลิป',
  );
  assert.deepEqual(text.warnings, []);
  assert.equal(text.confirmLabel, 'ตัดช่วงนี้');
  assert.equal(text.cancelLabel, 'ยกเลิก');
  assert.equal(text.undoHint, 'กด Ctrl+Z ย้อนกลับได้ทันที');
  assert.equal(text.blocked, null);
});

test('describeRipplePlan: several ranges, silence wording, video scope and warnings', () => {
  const silence = planRippleRanges(
    state(abc()),
    [{ start: 1, end: 2 }, { start: 8, end: 9 }],
    voiceOpts({ reason: 'silence' }),
  );
  assert.equal(describeRipplePlan(silence).title, 'ตัดช่วงเงียบ 2 ช่วงออก?');
  const manual = planRippleRanges(state(abc()), [{ start: 1, end: 2 }, { start: 8, end: 9 }], voiceOpts());
  assert.equal(describeRipplePlan(manual).title, 'ตัด 2 ช่วงออก?');

  const video = planRippleRanges(state(abc()), [{ start: 6, end: 8 }], voiceOpts({ scope: 'video' }));
  const videoText = describeRipplePlan(video);
  assert.equal(videoText.title, 'ตัดช่วง 0:06.00–0:08.00 ออกจากภาพ?');
  assert.match(videoText.subtitle, /เสียงพากย์และซับไม่ขยับ/);
  assert.match(videoText.summary, /^ภาพสั้นลง 2\.00 วินาที \(15\.00 → 13\.00\)/);
  assert.ok(videoText.warnings.some((w) => w.includes('ค้างเฟรมสุดท้าย')));
});

test('describeRipplePlan: a refused plan shows its reason and nothing else', () => {
  const blocked = planRippleRanges(state(abc()), [{ start: 0, end: 15 }], voiceOpts());
  const text = describeRipplePlan(blocked);
  assert.equal(text.blocked, 'ตัดแล้วจะไม่เหลือคลิปเลย');
  assert.equal(text.summary, 'ตัดแล้วจะไม่เหลือคลิปเลย');
  assert.equal(describeRipplePlan(null).blocked, null);
});

// ---------------------------------------------------------------------------
// Undo: one ripple = one history step
// ---------------------------------------------------------------------------

test('one history set() applies the whole ripple and ONE undo brings everything back', () => {
  const initial = state(abc(), {
    cuesList: [cue(0, 1), cue(5, 9), cue(10, 12)],
    microCuesList: [cue(10, 11)],
    overlays: [{ id: 'o', kind: 'text', start: 9, end: 14 }],
    stickers: [{ id: 's', badge: 'b.png', start: 7, end: 8 }],
    effects: [{ id: 'e', effectId: 'x', start: 11, end: 12 }],
  });
  const model = createEditorHistoryModel(initial);
  const plan = planRippleRanges(initial, [{ start: 6, end: 8 }], voiceOpts());
  assert.equal(model.set((prev) => applyRipplePlan(prev, plan)), true);
  const changed = model.getState();
  assert.notEqual(changed, initial);
  assert.deepEqual(changed.voiceEdit.cuts.map((c) => [c.start, c.end]), [[6, 8]]);
  assert.equal(changed.stickers.length, 0);
  assert.equal(changed.clipList.length, 4);
  approx(changed.microCuesList[0].start, 8);

  assert.equal(model.undo(), true);
  assert.equal(model.getState(), initial, 'a single undo is back to the exact previous state');
  assert.equal(model.canUndo(), false, 'it was one step');
  assert.equal(model.redo(), true);
  assert.equal(model.getState(), changed);
});

// ---------------------------------------------------------------------------
// Picture invariant over random timelines
// ---------------------------------------------------------------------------

function seededRandom(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

test('random timelines: after a cut every frame shows the picture that was at its shifted time', () => {
  const kinds = ['cut', 'fade', 'wipeleft', 'dissolve'];
  let checked = 0;
  let planned = 0;
  for (let seed = 1; seed <= 400; seed += 1) {
    const rnd = seededRandom(seed);
    const count = 1 + Math.floor(rnd() * 6);
    const clips = [];
    const durations = {};
    for (let i = 0; i < count; i += 1) {
      const source = 6 + Math.floor(rnd() * 10);
      const trimStart = Math.floor(rnd() * 30) / 10;
      const clip = {
        id: `c${i}`,
        source_path: `s${i}.mp4`,
        trim_start: trimStart,
        trim_end: Math.min(trimStart + 1 + Math.floor(rnd() * 40) / 10, source),
        speed: [1, 1, 0.5, 2][Math.floor(rnd() * 4)],
      };
      if (i > 0) {
        clip.transition_in = kinds[Math.floor(rnd() * kinds.length)];
        clip.transition_duration = [0.2, 0.4, 0.8][Math.floor(rnd() * 3)];
      }
      if (rnd() < 0.15) clip.freeze_tail = 1 + Math.floor(rnd() * 20) / 10;
      if (rnd() < 0.3) {
        clip.keyframes = [
          { time: 0, property: 'zoom', value: 1 },
          { time: 1, property: 'zoom', value: 1.5, easing: 'ease_in' },
        ];
      }
      clips.push(clip);
      durations[clip.id] = source;
    }
    const before = buildSegments(clips, durations);
    const total = totalDuration(before);
    const start = Math.floor(rnd() * total * 30) / 30;
    const end = start + (1 + Math.floor(rnd() * 90)) / 30;
    const plan = planRippleRanges(
      { clipList: clips },
      [{ start, end }],
      { scope: 'video', durations, newId: idFactory() },
    );
    if (plan.blocked) continue;
    planned += 1;
    const next = plan.state.clipList;
    const nextDurations = { ...durations };
    next.forEach((clip) => { if (nextDurations[clip.id] === undefined) nextDurations[clip.id] = 20; });
    const after = buildSegments(next, nextDurations);
    const { start: cutStart, end: cutEnd } = plan.ranges[0];
    const removed = cutEnd - cutStart;
    const inWindow = (segs, t) => segs.some((s) => s.isFade && t >= s.segStart && t < s.segStart + s.overlap + 1 / 30);
    for (let k = 0; k < Math.floor(totalDuration(after) * 30); k += 1) {
      const tau = (k + 0.5) / 30;
      if (inWindow(after, tau)) continue;
      const topNew = getDrawPlan(after, tau).at(-1);
      // The junction (and every clip edge) may land a frame off: the layout
      // rounds cumulative edges, so allow +-2 frames of jitter around tau.
      let matched = false;
      let skip = false;
      for (const frames of [0, -1, 1, -2, 2]) {
        const shifted = tau + frames / 30;
        const oldTime = shifted < cutStart ? shifted : shifted + removed;
        if (inWindow(before, oldTime)) { skip = true; continue; }
        const topOld = getDrawPlan(before, oldTime).at(-1);
        const speed = topOld.seg.clip.speed || 1;
        const gap = Math.abs(Math.abs(topOld.localTime - topNew.localTime) - Math.abs(frames) * speed / 30);
        if (topOld.seg.clip.source_path === topNew.seg.clip.source_path && gap <= 1.01 * speed / 30 + 2e-3) {
          matched = true;
          break;
        }
      }
      if (!matched && skip) continue;
      checked += 1;
      if (!matched) {
        // Only the last 2 frames of a half-frame-rounded chain may be off.
        const nearEnd = tau > totalDuration(after) - 3 / 30;
        assert.ok(nearEnd, `seed ${seed}: frame ${k} shows ${topNew.seg.clip.source_path}@${topNew.localTime} which was not on screen near ${tau}`);
      }
    }
  }
  assert.ok(planned > 300, `planned ${planned}`);
  assert.ok(checked > 50000, `checked ${checked}`);
});

// ---------------------------------------------------------------------------
// Two things a ripple deliberately does NOT shift (lane RC audit)
//
//  1. Cutout `active_intervals` are SOURCE-footage seconds, never program time:
//     backgroundIsolationPreview.js:195-203 builds them as
//     `trim_start + (overlayStart - segStart) * speed`, the worker tests them
//     against the decoder's source time (background_isolation_video_worker.py:477-480)
//     and the artifact manifest must equal them exactly
//     (video_editor.py:145-148). They ride on `clip.background_isolation`, so a
//     ripple copies them with the clip. Shifting them by -d would corrupt the
//     match; the live recompute in EditorShell (:380) marks a changed window
//     'stale' instead, and the preview/render fall back to the plain picture.
//  2. `source_credits` is only an optional ASS argument of subtitle_engine.py
//     (:598, :860) used by tools/render_*.py. The editor state, the manifest and
//     the frontend never carry it, so there is nothing for a ripple to move.
// ---------------------------------------------------------------------------

const BEHIND_TEXT = { kind: 'text', subject_layer: 'behind', tiers: [{ text: 'SPEC' }] };

/** What EditorShell.jsx:377-382 derives live from clips + behind-text overlays. */
function liveCutoutPlan(st) {
  const groups = groupScopedBackgroundIsolationClips(st.clipList, st.overlays, { sourceDurations: DURATIONS });
  const byClip = Object.fromEntries(groups.flatMap((g) => g.clips.map((c) => [c.id, g.active_intervals])));
  return {
    groups,
    project: {
      enabled: true,
      scope_mode: 'behind_text_windows',
      active_clip_ids: Object.keys(byClip),
      active_intervals_by_clip: byClip,
    },
  };
}

/** What "prepare cutout" stores on each covered clip (EditorShell.jsx:1887-1905). */
function prepareCutout(st) {
  const { groups } = liveCutoutPlan(st);
  const clipList = st.clipList.map((clip) => {
    const group = groups.find((g) => g.clips.includes(clip));
    if (!group) return clip;
    return {
      ...clip,
      background_isolation: {
        scope_mode: 'behind_text_windows',
        active_intervals: group.active_intervals,
        artifact: { id: `seq-${clip.id}`, status: 'ready', source_start: group.start, source_duration: group.duration },
      },
    };
  });
  return { ...st, clipList };
}

const resolveCutout = (clip, st) => resolveBackgroundIsolationConfig(clip, liveCutoutPlan(st).project);
const cutoutIsReady = (clip, st) => {
  const config = resolveCutout(clip, st);
  return config?.enabled !== false && config?.artifact?.status === 'ready'
    && scopedArtifactCoversClip(config, clip, { sourceDurations: DURATIONS });
};

/** a 0-5, b 5-10, c 10-15 with one behind-text overlay on c at program 11-13 (= c source 1-3). */
function preparedCutoutState() {
  const prepared = prepareCutout(state(abc(), { overlays: [{ id: 'o', ...BEHIND_TEXT, start: 11, end: 13 }] }));
  const c = prepared.clipList.find((clip) => clip.id === 'c');
  assert.deepEqual(c.background_isolation.active_intervals, [{ start: 1, end: 3 }], 'source seconds of c');
  assert.equal(cutoutIsReady(c, prepared), true);
  return { prepared, c };
}

test('cutout windows are source time: a cut BEFORE the clip moves clip and overlay together, the artifact stays valid', () => {
  const { prepared, c } = preparedCutoutState();
  const plan = planRippleRanges(prepared, [{ start: 5, end: 10 }], voiceOpts());
  assert.equal(plan.blocked, null);
  const next = applyRipplePlan(prepared, plan);
  const moved = next.clipList.find((clip) => clip.id === 'c');
  assert.equal(moved.background_isolation, c.background_isolation, 'the stored windows ride along untouched');
  assert.deepEqual(next.overlays.map((o) => [o.start, o.end]), [[6, 8]], 'the overlay shifted by -d');
  assert.deepEqual(liveCutoutPlan(next).project.active_intervals_by_clip.c, [{ start: 1, end: 3 }],
    'the live windows are still source 1-3, so shifting the stored ones by d would have been wrong');
  assert.equal(cutoutIsReady(moved, next), true);
});

test('cutout windows: cutting the TAIL behind the window keeps the artifact valid (it still covers the shorter clip)', () => {
  const { prepared } = preparedCutoutState();
  const plan = planRippleRanges(prepared, [{ start: 13, end: 15 }], voiceOpts());
  const next = applyRipplePlan(prepared, plan);
  const c = next.clipList.find((clip) => clip.id === 'c');
  assert.equal(c.trim_end, 3);
  assert.deepEqual(c.background_isolation.active_intervals, [{ start: 1, end: 3 }]);
  assert.equal(cutoutIsReady(c, next), true);
});

test('cutout windows: trimming the HEAD of the clip keeps the stored source seconds and goes stale (never a wrong cutout)', () => {
  const { prepared, c } = preparedCutoutState();
  const plan = planRippleRanges(prepared, [{ start: 10, end: 12 }], voiceOpts());
  assert.equal(plan.blocked, null);
  const next = applyRipplePlan(prepared, plan);
  const head = next.clipList.find((clip) => clip.id === 'c');
  assert.equal(head.trim_start, 2);
  assert.equal(head.background_isolation, c.background_isolation, 'stored windows are not rewritten, not shifted by d');
  assert.deepEqual(next.overlays.map((o) => [o.start, o.end]), [[10, 11]]);
  assert.deepEqual(liveCutoutPlan(next).project.active_intervals_by_clip.c, [{ start: 2, end: 3 }]);
  assert.equal(resolveCutout(head, next).artifact.status, 'stale', 'mismatch -> "prepare again", plain picture meanwhile');
  assert.equal(cutoutIsReady(head, next), false);
});

test('cutout windows: a split keeps the parent windows on both halves; the half that shows the text goes stale, the other is switched off', () => {
  const { prepared, c } = preparedCutoutState();
  const plan = planRippleRanges(prepared, [{ start: 11, end: 12 }], voiceOpts());
  assert.equal(plan.blocked, null);
  const next = applyRipplePlan(prepared, plan);
  const [left, right] = next.clipList.filter((clip) => clip.id === 'c' || clip.id === 'new-1');
  assert.equal(left.id, 'c');
  assert.equal(right.id, 'new-1');
  assert.equal(left.background_isolation, c.background_isolation);
  assert.equal(right.background_isolation, c.background_isolation);
  assert.equal(right.trim_start, 2);
  assert.equal(resolveCutout(right, next).artifact.status, 'stale');
  assert.equal(resolveCutout(left, next).enabled, false, 'no behind-text window left on the left half');
  assert.equal(cutoutIsReady(left, next), false);
  assert.equal(cutoutIsReady(right, next), false);
});

test('cutout windows: one undo puts back clips, overlays and the stored windows together', () => {
  const { prepared } = preparedCutoutState();
  const model = createEditorHistoryModel(prepared);
  const plan = planRippleRanges(prepared, [{ start: 10, end: 12 }], voiceOpts());
  assert.equal(model.set((prev) => applyRipplePlan(prev, plan)), true);
  assert.equal(model.undo(), true);
  assert.equal(model.getState(), prepared);
  assert.equal(cutoutIsReady(model.getState().clipList.find((clip) => clip.id === 'c'), model.getState()), true);
});

test('source_credits is not editor state: a ripple neither moves it nor puts it in the plan', () => {
  const credits = [{ start: 0, end: 28, text: 'Source : mi.com' }];
  const initial = state(abc(), { source_credits: credits });
  const plan = planRippleRanges(initial, [{ start: 6, end: 8 }], voiceOpts());
  assert.equal(plan.blocked, null);
  assert.equal('source_credits' in plan.state, false);
  assert.equal(applyRipplePlan(initial, plan).source_credits, credits, 'left exactly as it was');
});
