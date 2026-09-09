import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveSelectedItem } from './selectionResolver.js';

test('selected item resolver rejects a wrong selection type', () => {
  assert.equal(resolveSelectedItem(
    { type: 'caption', id: 's1' },
    'sticker',
    [{ id: 's1' }],
    { fallback: { id: 'fallback' } },
  ), null);
});

test('selected item resolver supports fallback only within the selected type', () => {
  const fallback = { id: 'first' };
  assert.equal(resolveSelectedItem(
    { type: 'sticker', id: 'missing' },
    'sticker',
    [fallback],
    { fallback },
  ), fallback);
  assert.deepEqual(resolveSelectedItem(
    { type: 'effect', id: 'e1' },
    ['sticker', 'effect'],
    [{ id: 'e1', effectId: 'glow' }],
  ), { id: 'e1', effectId: 'glow' });
});

test('selected item resolver accepts legacy id matchers and predicates', () => {
  const cue = { _uid: 'cue-1', id: 'legacy-1', text: 'hello' };
  assert.equal(resolveSelectedItem(
    { type: 'caption', id: 'cue-1' },
    'caption',
    [cue],
    { matches: (item, id) => item._uid === id || item.id === id },
  ), cue);
  assert.equal(resolveSelectedItem(
    { type: 'text_overlay', id: 'o1' },
    'text_overlay',
    [{ id: 'o1', kind: 'hook' }, { id: 'o1', kind: 'text' }],
    { matches: (item, id) => item.id === id && item.kind === 'text' },
  ).kind, 'text');
});
