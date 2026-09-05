import test from 'node:test';
import assert from 'node:assert/strict';

import {
  editorStateToSavePayload,
  manifestToEditorState,
  serializeClips,
  serializeTransitions,
} from './editorProjectState.js';


test('legacy manifest fields migrate without losing clip render data', () => {
  const state = manifestToEditorState({
    raw_video_path: 'legacy.mp4',
    transitions: ['fade'],
    cues: [{ start: '0', end: '1.2', text: 'เดิม' }],
    hook_brand: 'Brand',
    hook_model: 'Model',
    hook_label: 'Label',
    style: { captionScale: 0.8, fontName: 'Kanit' },
    audio_mutes: { bgm: true },
  }, {
    createClipId: () => 'clip-id',
    createCueId: () => 'cue-id',
  });

  assert.equal(state.clipList[0].source_path, 'legacy.mp4');
  assert.equal(state.clipList[0].track_id, 'video-1');
  assert.equal(state.cuesList[0]._uid, 'cue-id');
  assert.equal(state.style.captionScale, 1, 'legacy undersized captions migrate to the current minimum');
  assert.equal(state.style.fontName, 'Kanit');
  assert.equal(state.overlays[0].kind, 'hook');
  assert.equal(state.trackMix.mute.bgm, true);
});


test('clip serialization removes editor-only fields and preserves keyframes', () => {
  const clips = serializeClips([{
    id: 'local-only',
    source_path: 'a.mp4',
    transition_in: 'wipeleft',
    transition_duration: 0.6,
    track_id: 'video-2',
    keyframes: [{ time: 0, scale: 1 }, { time: 1, scale: 1.2 }],
    zoom: 1.1,
  }]);

  assert.deepEqual(clips, [{
    source_path: 'a.mp4',
    track_id: 'video-2',
    keyframes: [{ time: 0, scale: 1 }, { time: 1, scale: 1.2 }],
    zoom: 1.1,
  }]);
});


test('transition serialization follows clip boundaries', () => {
  assert.deepEqual(serializeTransitions([
    { id: 'a' },
    { id: 'b', transition_in: 'dissolve', transition_duration: 0.7 },
    { id: 'c' },
  ]), [
    { type: 'dissolve', duration: 0.7 },
    { type: 'cut', duration: 0.4 },
  ]);
});


test('one save serializer carries overlays, keyframes, and audio controls', () => {
  const input = {
    clipList: [{ id: 'a', source_path: 'a.mp4', track_id: 'video-1', keyframes: [{ time: 0, x: 0.5 }] }],
    cuesList: [{ _uid: 'cue-a', start: 0, end: 1, text: 'หนึ่ง' }],
    style: { fontName: 'IBMPlex', bgmVolume: 0.2, captionScale: 1 },
    overlays: [{ id: 'overlay-a', kind: 'text', tiers: [{ text: 'ข้อความ' }] }],
    trackMix: { mute: { bgm: true }, solo: { voice: true } },
  };

  const first = editorStateToSavePayload(input);
  const second = editorStateToSavePayload(input);

  assert.deepEqual(first, second, 'manual save and autosave can share one deterministic payload');
  assert.deepEqual(first.clip_list[0].keyframes, input.clipList[0].keyframes);
  assert.deepEqual(first.overlays, input.overlays);
  assert.deepEqual(first.track_mix, input.trackMix);
  assert.deepEqual(first.audio_mutes, { bgm: true });
  assert.equal(first.cues[0]._uid, undefined);
});
