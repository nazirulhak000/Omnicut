import test from 'node:test';
import assert from 'node:assert/strict';
import { HF_STYLE_PROFILES, draftFromProject, makeProjectPayload, makeFinalizePayload, handoffText, latestWorkflowJob, parseMediaRefs, projectWorkflowJobs, shouldPollRender, renderActions, workflowStep, productAngles } from './hyperframesWorkflow.js';

const product = { id: 'product-real', angles: [{ id: 'angle-real' }, { title: 'No stable ID' }] };
const draft = { brief: 'Explain saved product facts', script: '', duration: '15', audioMode: 'silent', styleId: 'pov_chat' };

test('standalone and Gadget drafts preserve source identities without invented ProductStore parents', () => {
  const standalone = makeProjectPayload({ draft: { ...draft, sourceType: 'standalone', title: 'Independent film', description: 'Saved facts' } });
  assert.deepEqual(standalone.source_binding, { type: 'standalone' });
  assert.equal(standalone.inputs.title, 'Independent film');
  assert.equal('product_id' in standalone.source_binding, false);
  const gadget = makeProjectPayload({ draft: { ...draft, sourceType: 'gadget_project', gadgetProjectId: 'gadget-real' } });
  assert.deepEqual(gadget.source_binding, { type: 'gadget_project', project_id: 'gadget-real' });
  assert.throws(() => makeProjectPayload({ draft: { ...draft, sourceType: 'standalone', title: ' ' } }));
  assert.throws(() => makeProjectPayload({ draft: { ...draft, sourceType: 'gadget_project', gadgetProjectId: '' } }));
  const restored = draftFromProject({ source_binding: gadget.source_binding, inputs: gadget.inputs });
  assert.equal(restored.sourceType, 'gadget_project');
  assert.equal(restored.gadgetProjectId, 'gadget-real');
});

test('project payload pins real parent and versioned concrete style without dummy voiceover', () => {
  const payload = makeProjectPayload({ product, angleId: 'angle-real', draft });
  assert.deepEqual(payload.source_binding, { type: 'product_angle', product_id: 'product-real', angle_id: 'angle-real' });
  assert.equal(payload.inputs.duration_seconds, 15);
  assert.equal(payload.inputs.style_profile.version, 1);
  assert.equal(payload.inputs.style_profile.tokens.motion, 'message-reveal');
  assert.equal('voiceover_path' in payload.inputs, false);
  assert.equal(productAngles(product).length, 1);
  payload.inputs.style_profile.tokens.motion = 'edited';
  assert.equal(HF_STYLE_PROFILES.find(item => item.id === 'pov_chat').tokens.motion, 'message-reveal');
});

test('invalid parent, missing real audio and invalid duration stop authoring setup', () => {
  assert.throws(() => makeProjectPayload({ product, angleId: 'invented', draft }));
  for (const change of [{ duration: '0' }, { duration: 'NaN' }, { styleId: 'invented' }, { brief: ' ' }, { audioMode: 'narration' }, { audioMode: 'music_only' }]) {
    assert.throws(() => makeProjectPayload({ product, angleId: 'angle-real', draft: { ...draft, ...change } }));
  }
});

test('audio mode changes omit stale voice path and preserve saved basket input', () => {
  const payload = makeProjectPayload({ product, angleId: 'angle-real', draft: { ...draft, voicePath: 'old.wav', musicPath: '02_Assets/music.wav', productId: 'basket-saved', audioMode: 'music_only' } });
  assert.equal('voiceover_path' in payload.inputs, false);
  assert.equal(payload.inputs.music_path, '02_Assets/music.wav');
  assert.equal(payload.inputs.tiktok_product_id, 'basket-saved');
});

test('only technically ready artifact permits human reviewed finalization', () => {
  const project = { project_id: 'project', revision: 8, inputs: { tiktok_product_id: 'saved-basket' } };
  const job = { revision: 6, status: 'qc_ready', artifact: { path: '.tmp/video.mp4', sha256: 'exacthash' } };
  assert.throws(() => makeFinalizePayload(project, job, { reviewed: false }));
  assert.throws(() => makeFinalizePayload(project, { ...job, status: 'rendering' }, { reviewed: true }));
  assert.throws(() => makeFinalizePayload(project, { status: 'qc_ready', artifact: { path: 'only-path' } }, { reviewed: true }));
  assert.deepEqual(makeFinalizePayload(project, job, { reviewed: true, caption: ' Caption ', hashtags: '#one #two', coverPath: '05_Covers_Thumbnails/main/cover.jpg', productId: 'untrusted-basket' }), {
    expected_revision: 6, artifact_hash: 'exacthash', publish_package: { caption: 'Caption', hashtags: ['#one', '#two'], tiktok_product_id: 'saved-basket', cover_path: '05_Covers_Thumbnails/main/cover.jpg', cover_format: '9x16' },
  });
});

test('finalize recovery never offers render retry or automatic duplicate effects', () => {
  assert.deepEqual(renderActions({ status: 'recovery_required' }), { cancel: false, retry: false, finalize: false });
  assert.deepEqual(renderActions({ status: 'finalized', export_id: 'export' }), { cancel: false, retry: false, finalize: false });
  assert.equal(renderActions({ status: 'interrupted' }).retry, true);
  assert.equal(renderActions({ status: 'cancelled' }).retry, false);
  assert.equal(renderActions({ status: 'finalizing' }).cancel, false);
  assert.equal(shouldPollRender({ status: 'rendering' }), true);
  assert.equal(shouldPollRender({ status: 'qc_ready' }), false);
  assert.equal(shouldPollRender({ status: 'recovery_required' }), false);
});

test('handoff preserves checkpoint and fenced API instructions with local scope', () => {
  const packet = { work_id: 'creative123', work_path: '03_Projects/_HyperFrames_Studio/work/creative123', input_hash: 'input1', checkpoint: { next_action: 'Finish scene 2' } };
  const text = handoffText(packet);
  assert.ok(text.includes('Finish scene 2'));
  assert.ok(text.includes('checkpoint / submit'));
  for (const work_path of ['../outside', 'C:\\outside', '/outside']) assert.throws(() => handoffText({ ...packet, work_path }));
  assert.throws(() => handoffText({ work_id: 'missing-fields' }));
});

test('flow reflects saved server states instead of elapsed time', () => {
  assert.equal(workflowStep(null), 0);
  assert.equal(workflowStep({ project_id: 'p' }), 1);
  assert.equal(workflowStep({ project_id: 'p' }, { status: 'submitted' }), 2);
  assert.equal(workflowStep({ accepted_revision: { id: 'r1' } }), 2);
  assert.equal(workflowStep({}, null, { status: 'rendering' }), 3);
  assert.equal(workflowStep({}, null, { status: 'finalized', export_id: 'e1' }), 4);
});

test('latest durable job is selected by creation time after unordered store reload', () => {
  const jobs = [{ id: 'new', created_at: 1001 }, { id: 'old', created_at: 1000 }];
  assert.equal(latestWorkflowJob(jobs).id, 'new');
  assert.equal(latestWorkflowJob([{ id: 'old', created_at: '2026-10-10T00:00:00Z' }, { id: 'new', created_at: '2026-10-11T00:00:00Z' }]).id, 'new');
  assert.equal(latestWorkflowJob([]), null);
  assert.deepEqual(jobs.map(item => item.id), ['new', 'old']);
});

test('media ledger rejects remote and escaping references and deduplicates local inputs', () => {
  assert.deepEqual(parseMediaRefs('01_Raw/p/image.png\n01_Raw/p/image.png\n02_Assets\\background.jpg'), [{ path: '01_Raw/p/image.png' }, { path: '02_Assets/background.jpg' }]);
  for (const path of ['https://cdn/clip.mp4', '../outside.mp4', '01_Raw/../outside.mp4', 'C:\\outside.mp4', '\\outside']) assert.throws(() => parseMediaRefs(path));
  assert.equal(makeProjectPayload({ product, angleId: 'angle-real', draft: { ...draft, mediaPaths: '01_Raw/p/image.png' } }).inputs.media_refs.length, 1);
});

test('editing saved brief preserves exact audio/style/assets and source stays separate', () => {
  const saved = makeProjectPayload({ product, angleId: 'angle-real', draft: { ...draft, audioMode: 'narration', script: 'Approved words', voicePath: '03_Projects/voice.wav', musicPath: '02_Assets/music.wav', productId: 'basket', mediaPaths: '01_Raw/p/image.png' } });
  const restored = draftFromProject({ inputs: saved.inputs });
  restored.brief = 'Revision 2 request';
  const updated = makeProjectPayload({ product, angleId: 'angle-real', draft: restored });
  assert.deepEqual(updated.source_binding, saved.source_binding);
  assert.equal(updated.inputs.voiceover_path, saved.inputs.voiceover_path);
  assert.equal(updated.inputs.tiktok_product_id, 'basket');
  assert.deepEqual(updated.inputs.media_refs, saved.inputs.media_refs);
  assert.equal(updated.inputs.brief, 'Revision 2 request');
  assert.equal(saved.inputs.brief, draft.brief);
});

test('new authoring revision does not show or finalize previous rendered export', () => {
  const project = { revision: 3, accepted_revision: { id: 'r1' } };
  const oldCreative = { id: 'a1', base_revision: 2, submitted_revision: { id: 'r1' }, status: 'submitted', created_at: 1000 };
  const oldRender = { id: 'render1', snapshot: { id: 'r1' }, status: 'finalized', export_id: 'export1', created_at: 1000 };
  assert.equal(projectWorkflowJobs(project, [oldCreative], [oldRender]).render.id, 'render1');
  const newCreative = { id: 'a2', base_revision: 3, status: 'queued', created_at: 1001 };
  const next = projectWorkflowJobs(project, [oldCreative, newCreative], [oldRender]);
  assert.equal(next.creative.id, 'a2');
  assert.equal(next.render, null);
  assert.equal(workflowStep(project, next.creative, oldRender), 1);
  assert.equal(oldRender.export_id, 'export1');
  const edited = { revision: 4, accepted_revision: null };
  assert.deepEqual(projectWorkflowJobs(edited, [oldCreative, newCreative], [oldRender]), { creative: null, render: null });
});

test('accepting new composition selects only render from that exact revision', () => {
  const project = { revision: 5, accepted_revision: { id: 'r2' } };
  const creative = { base_revision: 4, status: 'submitted', submitted_revision: { id: 'r2' } };
  const old = { id: 'old', snapshot: { id: 'r1' }, created_at: 2000 };
  const current = { id: 'current', snapshot: { id: 'r2' }, created_at: 1000, status: 'failed' };
  assert.equal(projectWorkflowJobs(project, [creative], [old, current]).render.id, 'current');
  assert.equal(renderActions(current).retry, true);
});
