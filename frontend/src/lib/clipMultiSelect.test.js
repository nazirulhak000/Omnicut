import test from 'node:test';
import assert from 'node:assert/strict';

import {
  EMPTY_CLIP_SELECTION,
  applyClipClick,
  baseSelectionState,
  clickMode,
  extraClipIds,
  selectedClipIdsInOrder,
} from './clipMultiSelect.js';

const ORDER = ['a', 'b', 'c', 'd', 'e'];
const ids = (s) => [s.primaryId, ...s.extraIds].sort();

test('clickMode: Ctrl/Cmd toggle, Shift range, otherwise replace', () => {
  assert.equal(clickMode({}), 'replace');
  assert.equal(clickMode(null), 'replace');
  assert.equal(clickMode({ ctrlKey: true }), 'toggle');
  assert.equal(clickMode({ metaKey: true }), 'toggle');
  assert.equal(clickMode({ shiftKey: true }), 'range');
  // Ctrl wins over Shift so Ctrl+Shift+click never silently becomes a range.
  assert.equal(clickMode({ ctrlKey: true, shiftKey: true }), 'toggle');
});

test('replace selects exactly that clip and anchors on it', () => {
  const s = applyClipClick({ primaryId: 'a', extraIds: ['b'], anchorId: 'a' }, 'c', 'replace', ORDER);
  assert.deepEqual(s, { primaryId: 'c', extraIds: [], anchorId: 'c' });
});

test('toggle adds a clip as the new primary and keeps the earlier ones', () => {
  let s = applyClipClick(EMPTY_CLIP_SELECTION, 'b', 'toggle', ORDER);
  assert.deepEqual(s, { primaryId: 'b', extraIds: [], anchorId: 'b' });
  s = applyClipClick(s, 'd', 'toggle', ORDER);
  assert.equal(s.primaryId, 'd');
  assert.deepEqual(ids(s), ['b', 'd']);
  s = applyClipClick(s, 'a', 'toggle', ORDER);
  assert.equal(s.primaryId, 'a');
  assert.deepEqual(ids(s), ['a', 'b', 'd']);
});

test('toggle on a member removes it; removing the primary promotes the latest remaining', () => {
  let s = { primaryId: 'd', extraIds: ['b', 'a'], anchorId: 'd' };
  s = applyClipClick(s, 'b', 'toggle', ORDER); // an extra
  assert.equal(s.primaryId, 'd');
  assert.deepEqual(ids(s), ['a', 'd']);
  s = applyClipClick(s, 'd', 'toggle', ORDER); // the primary
  assert.equal(s.primaryId, 'a');
  assert.deepEqual(s.extraIds, []);
  s = applyClipClick(s, 'a', 'toggle', ORDER); // the last one
  assert.equal(s, EMPTY_CLIP_SELECTION);
});

test('range runs from the anchor to the clicked clip, either direction, anchor stays', () => {
  const base = { primaryId: 'b', extraIds: [], anchorId: 'b' };
  let s = applyClipClick(base, 'd', 'range', ORDER);
  assert.equal(s.primaryId, 'd');
  assert.equal(s.anchorId, 'b');
  assert.deepEqual(ids(s), ['b', 'c', 'd']);
  // A second shift+click pivots on the same anchor and shrinks the range.
  s = applyClipClick(s, 'c', 'range', ORDER);
  assert.deepEqual(ids(s), ['b', 'c']);
  s = applyClipClick(s, 'a', 'range', ORDER);
  assert.deepEqual(ids(s), ['a', 'b']);
  assert.equal(s.primaryId, 'a');
});

test('range without a usable anchor selects just the clicked clip', () => {
  assert.deepEqual(applyClipClick(EMPTY_CLIP_SELECTION, 'c', 'range', ORDER), { primaryId: 'c', extraIds: [], anchorId: 'c' });
  const stale = { primaryId: 'gone', extraIds: [], anchorId: 'gone' };
  assert.deepEqual(applyClipClick(stale, 'c', 'range', ORDER), { primaryId: 'c', extraIds: [], anchorId: 'c' });
  assert.deepEqual(applyClipClick(EMPTY_CLIP_SELECTION, 'zz', 'range', ORDER), { primaryId: 'zz', extraIds: [], anchorId: 'zz' });
});

test('focus (right-click) keeps the set when the clip is in it, else replaces', () => {
  const s = { primaryId: 'a', extraIds: ['c', 'd'], anchorId: 'a' };
  const inSet = applyClipClick(s, 'd', 'focus', ORDER);
  assert.equal(inSet.primaryId, 'd');
  assert.deepEqual(ids(inSet), ['a', 'c', 'd']);
  assert.deepEqual(applyClipClick(s, 'e', 'focus', ORDER), { primaryId: 'e', extraIds: [], anchorId: 'e' });
});

test('a click with no id clears everything', () => {
  assert.equal(applyClipClick({ primaryId: 'a', extraIds: ['b'], anchorId: 'a' }, null, 'replace', ORDER), EMPTY_CLIP_SELECTION);
});

test('selectedClipIdsInOrder: timeline order, only existing clips, only while primary matches', () => {
  const s = { primaryId: 'd', extraIds: ['b', 'zz', 'a'], anchorId: 'd' };
  assert.deepEqual(selectedClipIdsInOrder(s, 'd', ORDER), ['a', 'b', 'd']);
  assert.deepEqual(extraClipIds(s, 'd', ORDER), ['a', 'b']);
  // The primary moved on (e.g. split): the old extras are ignored, not resurrected.
  assert.deepEqual(selectedClipIdsInOrder(s, 'e', ORDER), ['e']);
  assert.deepEqual(extraClipIds(s, 'e', ORDER), []);
  assert.deepEqual(selectedClipIdsInOrder(s, null, ORDER), []);
});

test('baseSelectionState: a different current primary starts fresh', () => {
  const s = { primaryId: 'a', extraIds: ['b'], anchorId: 'a' };
  assert.equal(baseSelectionState(s, 'a'), s);
  assert.deepEqual(baseSelectionState(s, 'c'), { primaryId: 'c', extraIds: [], anchorId: 'c' });
  assert.equal(baseSelectionState(s, null), EMPTY_CLIP_SELECTION);
});
