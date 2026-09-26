import test from 'node:test';
import assert from 'node:assert/strict';
import { rememberProjectRevision, withProjectRevision } from './projectRevision.js';

test('loaded revision follows project identity and does not mutate the editor payload', () => {
  const payload = { clip_list: [] };
  rememberProjectRevision('one', 'a'.repeat(64));
  rememberProjectRevision('two', 'b'.repeat(64));
  assert.equal(withProjectRevision('one', payload).base_revision, 'a'.repeat(64));
  assert.equal(withProjectRevision('two', payload).base_revision, 'b'.repeat(64));
  assert.equal(payload.base_revision, undefined);
  rememberProjectRevision('one', null);
  assert.equal(withProjectRevision('one', payload), payload);
});
