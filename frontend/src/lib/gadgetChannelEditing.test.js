import test from 'node:test';
import assert from 'node:assert/strict';
import { createGadgetDraftParticipant } from '../components/gadget-media/gadgetDraftParticipant.js';
import { registerChannelSwitchParticipant, dirtyChannelParticipants, saveBeforeChannelSwitch,
  discardBeforeChannelSwitch } from './channelRuntime.js';
import { projectWatermark } from './channelIdentity.js';

test('Gadget manual edit participates in real save-and-switch lifecycle', async () => {
  const participant = createGadgetDraftParticipant({ clips: ['before'] });
  let saved;
  participant.observe({ clips: ['after'] }, { save: async () => { saved = 'after'; }, reset() {} });
  const unregister = registerChannelSwitchParticipant(participant);
  try {
    assert.equal(dirtyChannelParticipants().includes(participant), true);
    await saveBeforeChannelSwitch();
    assert.equal(saved, 'after');
    assert.equal(participant.isDirty(), false);
  } finally { unregister(); }
});

test('Gadget failed saves remain dirty and discard restores only saved state', async () => {
  const participant = createGadgetDraftParticipant({ text: 'baseline' });
  let restored;
  participant.observe({ text: 'edit' }, { save: async () => { throw Error('offline'); }, reset: value => { restored = value; } });
  const unregister = registerChannelSwitchParticipant(participant);
  try {
    await assert.rejects(saveBeforeChannelSwitch(), /offline/);
    assert.equal(participant.isDirty(), true);
    await discardBeforeChannelSwitch();
    assert.deepEqual(restored, { text: 'baseline' });
    assert.equal(participant.isDirty(), false);
  } finally { unregister(); }
});

test('edits made during manual save stay dirty and cannot be silently switched away', async () => {
  const participant = createGadgetDraftParticipant('initial');
  let resolve;
  participant.observe('first', { save: () => new Promise(done => { resolve = done; }), reset() {} });
  const unregister = registerChannelSwitchParticipant(participant);
  try {
    const pending = saveBeforeChannelSwitch();
    await Promise.resolve();
    participant.observe('newer', { save: async () => {}, reset() {} });
    resolve();
    await assert.rejects(pending, /บันทึกการแก้ไขยังไม่เสร็จ/);
    assert.equal(participant.isDirty(), true);
  } finally { unregister(); }
});

test('Gadget preview consumes persisted channel identity and rejects missing secondary identity', () => {
  assert.equal(projectWatermark({ channel_id: 'second', watermark_text: 'Frozen secondary' }, 'second'), 'Frozen secondary');
  assert.equal(projectWatermark(null, 'second'), null);
  assert.equal(projectWatermark({ channel_id: 'main', watermark_text: 'Main' }, 'second'), null);
});

test('saving Gadget before a channel switch persists the draft without advancing its stage', async () => {
  const participant = createGadgetDraftParticipant('initial');
  let advanced = false;
  let persisted = false;
  participant.observe('edited', {
    save: async () => { advanced = true; },
    saveForSwitch: async () => { persisted = true; },
    reset() {},
  });
  const unregister = registerChannelSwitchParticipant({
    isDirty: () => participant.isDirty(),
    save: () => participant.save({ forSwitch: true }),
    discard: () => participant.discard(),
  });
  try {
    await saveBeforeChannelSwitch();
    assert.equal(persisted, true);
    assert.equal(advanced, false);
    assert.equal(participant.isDirty(), false);
  } finally { unregister(); }
});

test('a rebuilt Gadget timeline refreshes a clean draft and preserves a newer local edit', () => {
  const participant = createGadgetDraftParticipant({ trim: 1 });
  participant.observe({ trim: 1 }, { reset() {}, save: async () => {} });
  assert.equal(participant.acceptExternal({ trim: 2 }), true);
  participant.observe({ trim: 3 }, { reset() {}, save: async () => {} });
  assert.equal(participant.acceptExternal({ trim: 4 }), false);
  assert.equal(participant.isDirty(), true);
});
