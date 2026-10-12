import test from 'node:test';
import assert from 'node:assert/strict';
import { channelStorage } from './channelStorage.js';
import { readTrackerDraft, writeTrackerDraft, clearTrackerDraft } from './trackerDrafts.js';

test('identical exports retain channel-specific post/QC drafts through switch and reload', () => {
  const values = new Map();
  const disk = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  const a = channelStorage(disk, 'main'), b = channelStorage(disk, 'second');
  const item = { export_id: 'same', parentProduct: { id: 'p' }, angle_id: 'angle' };
  writeTrackerDraft(a, 'post', item, { caption: 'draft A', date: '2026-10-11' });
  writeTrackerDraft(a, 'qc', item, { note: 'fix audio' });
  assert.equal(readTrackerDraft(b, 'post', item), null);
  writeTrackerDraft(b, 'post', item, { caption: 'draft B' });
  assert.equal(readTrackerDraft(channelStorage(disk, 'main'), 'post', item).caption, 'draft A');
  clearTrackerDraft(b, 'post', item);
  assert.equal(readTrackerDraft(a, 'qc', item).note, 'fix audio');
  assert.equal(readTrackerDraft(a, 'post', item).caption, 'draft A');
  assert.equal(readTrackerDraft(a, 'post', { ...item, export_id: 'new-version' }), null);
});
