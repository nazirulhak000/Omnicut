import test from 'node:test';
import assert from 'node:assert/strict';

import {
  POST_RENDER_ACTIONS as A,
  decidePostRenderSync,
  fetchSettledProject,
  isProjectRevision,
  stableStringify,
} from './postRenderRevision.js';
import { getProjectRevision, rememberProjectRevision, withProjectRevision } from './projectRevision.js';
import { editorStateToSavePayload, manifestToEditorState } from './editorProjectState.js';
import { stylePresetFromManifest, withStylePresetPayload } from './stylePresetCatalog.js';
import { createProjectAutosaveController } from '../hooks/useProjectAutosave.js';
import { createLatestSaveQueue } from './projectSaveQueue.js';

const R1 = '1'.repeat(64);
const R2 = '2'.repeat(64);
const R3 = '3'.repeat(64);

// Same derivation EditorShell uses for both sides of the comparison.
const toPayload = (manifest) => {
  const loaded = manifestToEditorState(manifest);
  const preset = stylePresetFromManifest(manifest, loaded.style);
  return withStylePresetPayload(
    editorStateToSavePayload({ ...loaded, style: { ...loaded.style, style_preset: preset } }),
    preset,
  );
};

const baseManifest = (revision, extra = {}) => ({
  _editor_revision: revision,
  clip_list: [
    { source_path: '01_Raw/x/a.mp4', trim_start: 0, trim_end: 2, duration: 2 },
    { source_path: '01_Raw/x/b.mp4', trim_start: 1, trim_end: 4, duration: 3 },
  ],
  transitions: [{ type: 'cut', duration: 0.3 }],
  cues: [{ text: 'สวัสดี', start: 0, end: 1 }],
  style: { caption_scale: 1, font_name: 'IBMPlex' },
  ...extra,
});

const decide = (overrides = {}) => {
  const loaded = baseManifest(R1);
  return decidePostRenderSync({
    fetchOk: true,
    manifest: baseManifest(R2, { updated_at: 'later', artifacts: { final: { path: 'x.mp4' } } }),
    projectName: 'p',
    targetProject: 'p',
    revisionAtStart: R1,
    revisionNow: R1,
    editorClean: true,
    currentPayload: toPayload(loaded),
    toPayload,
    ...overrides,
  });
};

test('stableStringify ignores key order but not array order', () => {
  assert.equal(stableStringify({ b: 1, a: { d: 2, c: 3 } }), stableStringify({ a: { c: 3, d: 2 }, b: 1 }));
  assert.notEqual(stableStringify([1, 2]), stableStringify([2, 1]));
  assert.ok(isProjectRevision(R1));
  assert.ok(!isProjectRevision('abc'));
});

test('clean editor + pipeline touched only non-editor fields -> remember the new revision', () => {
  const d = decide();
  assert.equal(d.action, A.REMEMBER);
  assert.equal(d.revision, R2);
});

test('clean editor + pipeline changed an editor-owned field -> reload, never remember silently', () => {
  const changed = baseManifest(R2);
  changed.clip_list = [changed.clip_list[0]];
  const d = decide({ manifest: changed });
  assert.equal(d.action, A.RELOAD);
});

test('failed render path: content change asks the user instead of reloading', () => {
  const changed = baseManifest(R2);
  changed.cues = [{ text: 'อื่น', start: 0, end: 1 }];
  assert.equal(decide({ manifest: changed, allowReload: false }).action, A.NOTIFY);
});

test('dirty editor -> notify, never remember and never reload over the edits', () => {
  for (const manifest of [baseManifest(R2), { ...baseManifest(R2), clip_list: [] }]) {
    const d = decide({ manifest, editorClean: false });
    assert.equal(d.action, A.NOTIFY);
    assert.equal(d.revision, undefined);
  }
});

test('same revision as remembered -> nothing to do', () => {
  assert.equal(decide({ manifest: baseManifest(R1) }).action, A.NOOP);
});

test('a save or load moved the revision during the fetch -> stale response is skipped', () => {
  // Remembered went R1 -> R3 while the GET (which saw R2) was in flight.
  assert.equal(decide({ revisionNow: R3 }).action, A.SKIP);
  // Even a response equal to an older revision must not roll it back.
  assert.equal(decide({ manifest: baseManifest(R1), revisionNow: R3 }).action, A.SKIP);
});

test('network failure, malformed response or switched project -> skip', () => {
  assert.equal(decide({ fetchOk: false }).action, A.SKIP);
  assert.equal(decide({ manifest: null }).action, A.SKIP);
  assert.equal(decide({ manifest: 'oops' }).action, A.SKIP);
  assert.equal(decide({ manifest: { ...baseManifest(R2), _editor_revision: 'not-a-hash' } }).action, A.SKIP);
  assert.equal(decide({ manifest: { ...baseManifest(R2), _editor_revision: undefined } }).action, A.SKIP);
  assert.equal(decide({ projectName: 'other' }).action, A.SKIP);
  assert.equal(decide({ toPayload: () => { throw new Error('bad'); } }).action, A.SKIP);
});

test('guard stays intact: only REMEMBER advances the revision a save sends', () => {
  // Mirrors EditorShell: only REMEMBER calls rememberProjectRevision.
  const apply = (decision) => {
    if (decision.action === A.REMEMBER) rememberProjectRevision('p', decision.revision);
  };
  const cases = [
    decide({ editorClean: false }),
    decide({ fetchOk: false }),
    decide({ revisionNow: R3, revisionAtStart: R1 }),
    decide({ manifest: { ...baseManifest(R2), clip_list: [] } }),
    decide({ manifest: { ...baseManifest(R2), cues: [] }, allowReload: false }),
  ];
  for (const decision of cases) {
    rememberProjectRevision('p', R1);
    apply(decision);
    assert.equal(withProjectRevision('p', {}).base_revision, R1, `${decision.action}/${decision.reason}`);
  }
  rememberProjectRevision('p', R1);
  apply(decide());
  assert.equal(getProjectRevision('p'), R2);
  rememberProjectRevision('p', null);
  assert.equal(getProjectRevision('p'), null);
});

test('fetchSettledProject waits for two matching reads', async () => {
  const reads = [baseManifest(R1), baseManifest(R2), baseManifest(R2)];
  let i = 0;
  const waits = [];
  const got = await fetchSettledProject(async () => reads[i++], { wait: async (ms) => waits.push(ms), delayMs: 5 });
  assert.equal(got._editor_revision, R2);
  assert.equal(i, 3);
  assert.deepEqual(waits, [5, 5]);
});

test('fetchSettledProject gives up on errors, malformed data or no stable read', async () => {
  const noWait = { wait: async () => {} };
  assert.equal(await fetchSettledProject(async () => { throw new Error('net'); }, noWait), null);
  assert.equal(await fetchSettledProject(async () => ({}), noWait), null);
  let n = 0;
  const flapping = async () => baseManifest(n++ % 2 ? R1 : R2);
  assert.equal(await fetchSettledProject(flapping, { ...noWait, attempts: 4 }), null);
});

test('autosave controller reports 409 as a conflict and keeps the edit pending', async () => {
  const conflicts = [];
  const statuses = [];
  const queue = createLatestSaveQueue(async () => {
    const err = new Error('conflict');
    err.response = { status: 409 };
    throw err;
  });
  const controller = createProjectAutosaveController({
    queue,
    schedule: (cb) => cb,
    cancel: () => {},
    onStatusChange: (s) => statuses.push(s),
    onConflict: (e) => conflicts.push(e.response.status),
  });
  controller.setBaseline('p', { v: 0 });
  assert.equal(controller.hasUnsavedWork(), false);
  controller.observe({ projectName: 'p', payload: { v: 1 }, enabled: true });
  assert.equal(controller.hasUnsavedWork(), true);
  await assert.rejects(controller.flush());
  assert.deepEqual(conflicts, [409]);
  assert.equal(statuses.at(-1), 'error');
  // The user's edit is not dropped: it stays pending until a reload.
  assert.deepEqual(queue.peekPending()?.payload, { v: 1 });
  assert.equal(controller.hasUnsavedWork(), true);
});
