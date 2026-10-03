import test from 'node:test';
import assert from 'node:assert/strict';

import {
  CAPTION_TYPING_COALESCE_MS,
  captionPatchHistoryOptions,
  mergeCueReveals,
  reconcileCueReveal,
  reconcileCuesReveal,
  revealMatchesText,
  revealTrackForCue,
  splitCueReveal,
  typingHistoryOptions,
} from './captionEdits.js';
import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';

// build_word_reveal('รีวิวหูฟังไร้สายรุ่นใหม่', 1, 4) from scripts/subtitle/word_reveal.py
const TRACK = [
  { text: 'รีวิว', start: 1, end: 1.562 },
  { text: 'หูฟัง', start: 1.562, end: 2.125 },
  { text: 'ไร้สาย', start: 2.125, end: 3.062 },
  { text: 'รุ่นใหม่', start: 3.062, end: 4 },
];
const CUE = { _uid: 'c1', start: 1, end: 4, text: 'รีวิวหูฟังไร้สายรุ่นใหม่', word_reveal: TRACK };
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

test('a track is only usable while its words spell the caption', () => {
  assert.equal(revealMatchesText(TRACK, CUE.text), true);
  assert.equal(revealMatchesText(TRACK, 'รีวิว หูฟัง\\Nไร้สาย รุ่นใหม่'), true);
  assert.equal(revealMatchesText(TRACK, 'รีวิวหูฟังไร้สายรุ่นใหม'), false);
  assert.equal(revealTrackForCue(TRACK, { ...CUE, text: 'ทดสอบลำโพงพกพาเสียงดี' }), null);
  assert.equal(revealTrackForCue(TRACK, CUE), TRACK);
  assert.equal(revealTrackForCue(undefined, CUE), null);
});

test('a stale track on a moved cue is drawn on the cue span', () => {
  const moved = revealTrackForCue(TRACK, { ...CUE, start: 6, end: 9 });
  near(moved[0].start, 6);
  near(moved[2].start, 7.125);
  near(moved[3].end, 9);
});

test('typing new text drops the stored track; whitespace-only edits keep it', () => {
  const typed = reconcileCueReveal(CUE, { ...CUE, text: 'ทดสอบลำโพงพกพาเสียงดี' });
  assert.equal('word_reveal' in typed, false);
  const spaced = { ...CUE, text: 'รีวิว หูฟัง ไร้สาย รุ่นใหม่' };
  assert.equal(reconcileCueReveal(CUE, spaced), spaced);
});

test('moving or trimming a cue retimes its track onto the new span', () => {
  const moved = reconcileCueReveal(CUE, { ...CUE, start: 6, end: 9 });
  near(moved.word_reveal[1].start, 6.562);
  near(moved.word_reveal[3].end, 9);
  const trimmed = reconcileCueReveal(CUE, { ...CUE, end: 2.5 });
  near(trimmed.word_reveal[0].start, 1);
  near(trimmed.word_reveal[3].end, 2.5);
  // Many silent drag steps compose to the same place as one.
  let cue = CUE;
  for (let i = 1; i <= 50; i += 1) cue = reconcileCueReveal(cue, { ...cue, start: 1 + i * 0.1, end: 4 + i * 0.1 });
  near(cue.word_reveal[2].start, 7.125);
});

test('a list update reconciles each cue by uid and leaves untouched lists alone', () => {
  const other = { _uid: 'c2', start: 5, end: 6, text: 'ดี' };
  const prev = [CUE, other];
  assert.equal(reconcileCuesReveal(prev, prev), prev);
  const next = reconcileCuesReveal(prev, [{ ...CUE, text: 'ใหม่' }, other]);
  assert.equal('word_reveal' in next[0], false);
  assert.equal(next[1], other);
});

test('split hands each half only its own words, retimed onto its own span', () => {
  const [a, b] = splitCueReveal(CUE, 'รีวิวหูฟัง', 'ไร้สายรุ่นใหม่', 2.25);
  assert.deepEqual(a.map((w) => w.text), ['รีวิว', 'หูฟัง']);
  assert.deepEqual(b.map((w) => w.text), ['ไร้สาย', 'รุ่นใหม่']);
  near(a[1].end, 2.25);
  near(b[0].start, 2.25);
  // build_word_reveal('ไร้สายรุ่นใหม่', 2.25, 4) puts the second word at 3.125.
  // (python rounds the stored track to 1 ms)
  near(b[1].start, 3.125, 1e-3);
  near(b[1].end, 4);
  // A cut inside a word gives neither half a track.
  assert.deepEqual(splitCueReveal(CUE, 'รีวิวหู', 'ฟังไร้สายรุ่นใหม่', 1.8), [null, null]);
});

test('merge joins both tracks only when both still match their text', () => {
  const [a, b] = splitCueReveal(CUE, 'รีวิวหูฟัง', 'ไร้สายรุ่นใหม่', 2.25);
  const first = { start: 1, end: 2.25, text: 'รีวิวหูฟัง', word_reveal: a };
  const second = { start: 2.25, end: 4, text: 'ไร้สายรุ่นใหม่', word_reveal: b };
  const merged = { start: 1, end: 4, text: 'รีวิวหูฟัง ไร้สายรุ่นใหม่' };
  const joined = mergeCueReveals(first, second, merged);
  assert.deepEqual(joined.map((w) => w.text), TRACK.map((w) => w.text));
  near(joined[3].end, 4);
  assert.equal(mergeCueReveals(first, { ...second, text: 'อื่น' }, merged), null);
});

test('typing one caption field coalesces; other fields and captions do not', () => {
  assert.deepEqual(captionPatchHistoryOptions('c1', { text: 'a' }), typingHistoryOptions('caption:text:c1'));
  assert.equal(captionPatchHistoryOptions('c1', { start: 1 }), undefined);
  assert.equal(captionPatchHistoryOptions('c1', { text: 'a', start: 1 }), undefined);
  const explicit = { coalesceKey: 'x' };
  assert.equal(captionPatchHistoryOptions('c1', { text: 'a' }, explicit), explicit);
});

test('one typed sentence is one undo step (L3-10)', () => {
  const clock = { t: 0 };
  const history = createEditorHistoryModel(
    { cuesList: [{ _uid: 'c1', text: '' }, { _uid: 'c2', text: '' }] },
    { now: () => clock.t },
  );
  const type = (uid, field, value) => history.set(
    (s) => ({ ...s, cuesList: s.cuesList.map((c) => (c._uid === uid ? { ...c, [field]: value } : c)) }),
    captionPatchHistoryOptions(uid, { [field]: value }),
  );
  const sentence = 'รีวิวหูฟัง';
  // Keystrokes up to a second apart (a pause to think) stay one step.
  for (let i = 1; i <= sentence.length; i += 1) {
    type('c1', 'text', sentence.slice(0, i));
    clock.t += i % 3 === 0 ? 1000 : 180;
  }
  assert.ok(CAPTION_TYPING_COALESCE_MS > 1000);
  type('c1', 'translation', 'review');        // another field: its own step
  clock.t += 100;
  type('c2', 'text', 'ดี');                    // another caption: its own step
  history.undo();
  history.undo();
  assert.equal(history.getState().cuesList[0].text, sentence);
  history.undo();
  assert.equal(history.getState().cuesList[0].text, '');
  assert.equal(history.canUndo(), false);
});
