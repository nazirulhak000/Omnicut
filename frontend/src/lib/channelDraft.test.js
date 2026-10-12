import test from 'node:test';
import assert from 'node:assert/strict';
import { createChannelDraftParticipant } from './channelDraft.js';

test('failed manual save keeps the editable draft dirty', async () => {
  const draft = createChannelDraftParticipant({ time: '09:00' });
  draft.observe({ time: '10:00' }, { save: async () => { throw Error('offline'); }, reset() {} });
  await assert.rejects(draft.save(), /offline/);
  assert.equal(draft.isDirty(), true);
});

test('save captures its payload and newer edits remain dirty', async () => {
  const draft = createChannelDraftParticipant({ time: '09:00' });
  let done, submitted;
  draft.observe({ time: '10:00' }, { save: value => { submitted = value; return new Promise(resolve => { done = resolve; }); }, reset() {} });
  const saving = draft.save();
  draft.observe({ time: '11:00' }, { save() {}, reset() {} });
  await Promise.resolve();
  assert.deepEqual(submitted, { time: '10:00' });
  done();
  await saving;
  assert.equal(draft.isDirty(), true);
});

test('discard waits for a pending successful mutation before restoring its committed baseline', async () => {
  const draft = createChannelDraftParticipant('before');
  let done, restored;
  draft.observe('committed', { save: () => new Promise(resolve => { done = resolve; }), reset: value => { restored = value; } });
  const saving = draft.save();
  await Promise.resolve();
  const discarding = draft.discard();
  assert.equal(restored, undefined);
  done();
  await Promise.all([saving, discarding]);
  assert.equal(restored, 'committed');
  assert.equal(draft.isDirty(), false);
});

test('pending auxiliary operations fence switching even without an edited form', async () => {
  const draft = createChannelDraftParticipant('before');
  let done, reset;
  draft.observe('before', { reset: value => { reset = value; } });
  const copying = draft.run(() => new Promise(resolve => { done = resolve; }));
  await Promise.resolve();
  assert.equal(draft.isDirty(), true);
  const discarded = draft.discard();
  assert.equal(reset, undefined);
  done();
  await Promise.all([copying, discarded]);
  assert.equal(reset, 'before');
});

test('late external refresh does not overwrite a dirty local form', () => {
  const draft = createChannelDraftParticipant('before');
  draft.observe('edited', {});
  assert.equal(draft.acceptExternal('late'), false);
  assert.equal(draft.isDirty(), true);
});
