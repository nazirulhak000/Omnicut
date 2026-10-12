import test from 'node:test';
import assert from 'node:assert/strict';
import { channelStorage } from './channelStorage.js';
import { activateChannel, captureChannel, isCurrentChannel, registerChannelSwitchParticipant,
  saveBeforeChannelSwitch, discardBeforeChannelSwitch } from './channelRuntime.js';
import { rememberProjectRevision, getProjectRevision } from './projectRevision.js';
import { createChannelTransport } from './channelTransport.js';
import { createProjectAutosaveController } from '../hooks/useProjectAutosave.js';
import { createLatestSaveQueue } from './projectSaveQueue.js';
import { projectWatermark } from './channelIdentity.js';
import { toMediaUrl } from './mediaUrl.js';

function storage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}

test('real workspace caches migrate only main and delayed writes retain original owner', () => {
  const disk = storage({ capcut_task_cache: '["legacy-main"]' });
  const main = channelStorage(disk, 'main'), second = channelStorage(disk, 'second');
  assert.equal(second.getItem('capcut_task_cache'), null);
  assert.equal(main.getItem('capcut_task_cache'), '["legacy-main"]');
  second.setItem('capcut_task_cache', '["second"]');
  main.setItem('capcut_task_cache', '["delayed-main"]');
  assert.equal(second.getItem('capcut_task_cache'), '["second"]');
  second.removeItem('capcut_task_cache');
  assert.equal(main.getItem('capcut_task_cache'), '["delayed-main"]');
});

test('identical project names cannot share editor save revisions', () => {
  rememberProjectRevision('same', 'a'.repeat(64), 'main');
  rememberProjectRevision('same', 'b'.repeat(64), 'second');
  assert.equal(getProjectRevision('same', 'main'), 'a'.repeat(64));
  assert.equal(getProjectRevision('same', 'second'), 'b'.repeat(64));
});

test('a delayed autosave dispatch after switch sends A header and rejects stale response', async () => {
  activateChannel('main');
  const token = captureChannel();
  activateChannel('second');
  let sent;
  const request = createChannelTransport({ capture: captureChannel, isCurrent: isCurrentChannel,
    send: async options => { sent = options; return { data: {}, headers: { 'x-omnicut-channel': 'main' } }; } });
  await assert.rejects(request({ channelToken: token, method: 'PATCH', url: '/api/projects/same/state', data: { title: 'edit-A' } }), { code: 'channel_response_stale' });
  assert.equal(sent.headers['X-OmniCut-Channel'], 'main');
  assert.equal(sent.channelToken, undefined);
  activateChannel('main');
});

test('failed save keeps switch blocked; discard removes queued edits before unmount flush', async () => {
  let writes = 0;
  const queue = createLatestSaveQueue(async () => { writes++; throw new Error('offline'); });
  const controller = createProjectAutosaveController({ queue, schedule: () => 1, cancel: () => {}, maxSaveRetries: 0 });
  controller.setBaseline('same', { title: 'old' });
  controller.observe({ projectName: 'same', payload: { title: 'new' }, enabled: true });
  const unregister = registerChannelSwitchParticipant({ isDirty: () => controller.hasUnsavedWork(), save: () => controller.flush(), discard: () => controller.discard() });
  try {
    await assert.rejects(saveBeforeChannelSwitch(), /offline/);
    assert.equal(controller.hasUnsavedWork(), true);
    await discardBeforeChannelSwitch();
    await controller.flush();
    assert.equal(writes, 1);
    assert.equal(controller.hasUnsavedWork(), false);
  } finally { unregister(); }
});

test('preview content comes from immutable project identity and missing secondary never uses main', () => {
  const snapshot = { channel_id: 'second', watermark_text: 'frozen second' };
  assert.equal(projectWatermark(snapshot, 'second'), 'frozen second');
  assert.equal(projectWatermark(snapshot, 'main'), null);
  assert.equal(projectWatermark(null, 'second'), null);
  assert.match(projectWatermark(null, 'main'), /rizanntry/);
});

test('a successful save advances actual baseline and permits save-and-switch', async () => {
  const queue = createLatestSaveQueue(async () => {});
  const controller = createProjectAutosaveController({ queue, schedule: () => 1, cancel: () => {} });
  const edit = { projectName: 'same', payload: { title: 'new' }, enabled: true };
  controller.setBaseline('same', { title: 'old' });
  controller.observe(edit);
  const unregister = registerChannelSwitchParticipant({
    isDirty: () => controller.hasUnsavedWork() || controller.hasUnsavedPayload(edit),
    save: () => controller.flush(), discard: () => controller.discard(),
  });
  try {
    await saveBeforeChannelSwitch();
    assert.equal(controller.hasUnsavedPayload(edit), false);
  } finally { unregister(); }
});

test('native generated media carries channel; foreign explicit carrier is rejected', () => {
  assert.equal(toMediaUrl('03_Projects/second/same/audio.wav', 'second'), '/api/media/03_Projects/second/same/audio.wav?channel=second');
  assert.equal(toMediaUrl('02_Assets/Music/shared.wav', 'second'), '/api/media/02_Assets/Music/shared.wav');
  assert.throws(() => toMediaUrl('/api/media/04_Exports/main.mp4?channel=main', 'second'), { code: 'channel_scope_conflict' });
});
