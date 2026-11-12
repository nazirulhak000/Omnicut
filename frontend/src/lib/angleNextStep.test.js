import test from 'node:test';
import assert from 'node:assert/strict';
import { angleNextStep, angleActionLabel, STAGE_LABEL, STAGE_HINT } from './angleNextStep.js';

const voiced = { has_shot_list: true, is_edge_tts: false };

test('a script without clips asks for clips first', () => {
  const step = angleNextStep({ status: 'scripted' }, { selectedCount: 0, shotListInfo: voiced });
  assert.deepEqual(step, { stage: 'needs_clips', primary: 'pick_clips', secondary: ['tracker'] });
});

test('clips without a usable voice ask for the voice; Edge-TTS counts as no voice', () => {
  assert.equal(angleNextStep({}, { selectedCount: 2 }).primary, 'voice');
  const edge = angleNextStep({}, { selectedCount: 2, shotListInfo: { has_shot_list: true, is_edge_tts: true } });
  assert.equal(edge.stage, 'needs_voice');
  assert.equal(angleActionLabel('voice', edge.stage, { edgeTts: true }), 'อัปเกรดเสียง');
});

test('clips and voice lead to a draft; the tracker stays secondary', () => {
  const step = angleNextStep({ status: 'scripted' }, { selectedCount: 1, shotListInfo: voiced });
  assert.equal(step.primary, 'draft');
  assert.deepEqual(step.secondary, ['tracker', 'studio']);
});

test('a draft opens in the editor whatever the clips are', () => {
  const step = angleNextStep({ status: 'in_production' }, { selectedCount: 0 });
  assert.equal(step.stage, 'drafted');
  assert.equal(angleActionLabel(step.primary, step.stage), 'เปิดทำต่อใน Editor');
  assert.equal(angleActionLabel('tracker', step.stage), 'ดูใน Tracker');
});

test('a rendered clip is watched first; without a file it is not rendered', () => {
  assert.equal(angleNextStep({ status: 'rendered', video_url: '/x.mp4' }).primary, 'watch');
  assert.equal(angleNextStep({ status: 'rendered' }, { selectedCount: 0 }).stage, 'needs_clips');
});

test('posted wins over everything and falls back to the gallery without a file', () => {
  assert.deepEqual(angleNextStep({ status: 'scripted', posted_at: 'x', video_url: '/v.mp4' }),
    { stage: 'posted', primary: 'watch', secondary: ['gallery', 'clone'] });
  assert.deepEqual(angleNextStep({ status: 'posted' }), { stage: 'posted', primary: 'gallery', secondary: ['clone'] });
});

test('every stage has a label and a hint, every action a verb-first label', () => {
  for (const stage of ['posted', 'rendered', 'drafted', 'needs_clips', 'needs_voice', 'ready_to_draft']) {
    assert.ok(STAGE_LABEL[stage] && STAGE_HINT[stage], stage);
  }
  for (const action of ['watch', 'gallery', 'clone', 'timeline', 'recut', 'tracker', 'pick_clips', 'voice', 'draft', 'studio']) {
    assert.notEqual(angleActionLabel(action, 'needs_clips'), action);
  }
});
