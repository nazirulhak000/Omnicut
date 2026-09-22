import test from 'node:test';
import assert from 'node:assert/strict';

import {
  editorStateToSavePayload,
  manifestToEditorState,
  serializeRenderFeatures,
  serializeClips,
  serializeOverlays,
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


test('Product Callout metadata survives load, save, and autosave-equivalent serialization', () => {
  const callout = {
    id: 'callout-model-1',
    kind: 'text',
    role: 'product_callout',
    callout_type: 'model',
    origin: 'auto',
    source_beat_id: 'beat-02',
    template_id: 'product-model-v1',
    theme_role: 'primary',
    timing: { start: 1.25, end: 3.75 },
    tiers: [{ text: 'Soundcore Boom Go 3i', look: {} }],
    metadata: { future_field: 'keep-me' },
  };

  const loaded = manifestToEditorState({ overlays: [callout] });
  const payload = editorStateToSavePayload({ overlays: loaded.overlays });
  const autosavePayload = editorStateToSavePayload({ overlays: loaded.overlays });

  assert.deepEqual(payload.overlays, autosavePayload.overlays);
  assert.equal(payload.overlays[0].kind, 'text');
  assert.equal(payload.overlays[0].role, 'product_callout');
  assert.equal(payload.overlays[0].callout_type, 'model');
  assert.equal(payload.overlays[0].origin, 'auto');
  assert.equal(payload.overlays[0].source_beat_id, 'beat-02');
  assert.equal(payload.overlays[0].template_id, 'product-model-v1');
  assert.equal(payload.overlays[0].theme_role, 'primary');
  assert.deepEqual(payload.overlays[0].metadata, { future_field: 'keep-me' });
  assert.deepEqual(payload.overlays[0].timing, { start: 1.25, end: 3.75 });
});


test('overlay persistence keeps unknown metadata and legacy overlay shape safe', () => {
  const legacy = { id: 'legacy-text', kind: 'text', text: 'เดิม', custom_flag: true };
  const unknown = { id: 'future-overlay', kind: 'sticker', asset: 'badge.png', future: { version: 2 } };
  const overlays = serializeOverlays([legacy, unknown]);

  assert.deepEqual(overlays, [legacy, unknown]);
  assert.notEqual(overlays[0], legacy);
  assert.notEqual(overlays[1], unknown);
});


test('overlay migration opts decorative baked media into accent recolour only', () => {
  const state = manifestToEditorState({
    stickers: [
      { id: 'arrow', badge: 'arrow_pointer_cyan_3d.png' },
      { id: 'badge', badge: 'badge_pros_review.png' },
      { id: 'off', badge: 'arrow_pointer_cyan_3d.png', recolor: false },
    ],
    effects: [{ id: 'fx', effectId: 'fx_arrow_01' }],
  });

  assert.equal(state.stickers[0].recolor, 'accent');
  assert.equal(state.stickers[0].recolorSourceHue, 180);
  assert.equal(state.stickers[1].recolor, undefined);
  assert.equal(state.stickers[2].recolor, false);
  assert.equal(state.effects[0].recolor, 'accent');
  assert.equal(state.effects[0].recolorSourceHue, 205);
});


test('showWatermark parses from manifest and serializes to save payload', () => {
  const defaultState = manifestToEditorState({});
  assert.equal(defaultState.style.showWatermark, true);

  const disabledState = manifestToEditorState({ show_watermark: false });
  assert.equal(disabledState.style.showWatermark, false);

  const payload = editorStateToSavePayload({ style: { showWatermark: false } });
  assert.equal(payload.style.show_watermark, false);
  assert.equal(payload.style.showWatermark, false);

  const payloadDefault = editorStateToSavePayload({ style: { showWatermark: true } });
  assert.equal(payloadDefault.style.show_watermark, true);
  assert.equal(payloadDefault.style.showWatermark, true);
});


test('SpotlightV1 round-trips through editor state and save payload', () => {
  const spotlight = {
    schema_version: 1,
    enabled: true,
    shape: 'ellipse',
    focus: { x: 0.5, y: 0.48, width: 0.42, height: 0.36 },
    dim_opacity: 0.4,
    feather: 0.03,
  };

  const loaded = manifestToEditorState({ render_params: { spotlight } });
  const payload = editorStateToSavePayload({ spotlight: loaded.spotlight });

  assert.deepEqual(loaded.spotlight, spotlight);
  assert.deepEqual(payload.spotlight, spotlight);
});


test('render feature payload carries Spotlight and Background Isolation to the backend', () => {
  const spotlight = {
    schema_version: 1,
    enabled: true,
    focus: { x: 0.5, y: 0.5, width: 0.4, height: 0.3 },
  };
  const backgroundIsolation = {
    schema_version: 1,
    enabled: true,
    mode: 'cutout',
  };

  const payload = serializeRenderFeatures({
    stickers: [{ id: 'sticker-1' }],
    effects: [{ id: 'effect-1' }],
    spotlight,
    backgroundIsolation,
  });

  assert.deepEqual(payload.spotlight, spotlight);
  assert.deepEqual(payload.background_isolation, backgroundIsolation);
  assert.deepEqual(payload.stickers, [{ id: 'sticker-1' }]);
  assert.deepEqual(payload.effects, [{ id: 'effect-1' }]);
});


test('legacy state keeps background isolation absent without changing the save payload shape', () => {
  const state = manifestToEditorState({ raw_video_path: 'legacy.mp4' });
  const payload = editorStateToSavePayload(state);

  assert.equal(state.backgroundIsolation, null);
  assert.equal(Object.hasOwn(payload, 'background_isolation'), false);
  assert.equal(Object.hasOwn(payload, 'backgroundIsolation'), false);
});


test('BackgroundIsolationV1 ready config round-trips losslessly through editor state', () => {
  const backgroundIsolation = {
    schema_version: 1,
    enabled: true,
    mode: 'cutout',
    engine: 'rembg',
    model: 'u2netp',
    quality: 'balanced',
    fallback: 'original',
    artifact: {
      schema_version: 1,
      id: 'bgseq1-0123456789abcdef',
      status: 'ready',
      source_fingerprint: 'product.mp4:123:456',
      future_metadata: { worker: 'sequence-v2' },
    },
    future_config: { owner: 'editorial' },
  };

  const loaded = manifestToEditorState({ background_isolation: backgroundIsolation });
  const payload = editorStateToSavePayload(loaded);

  assert.deepEqual(loaded.backgroundIsolation, backgroundIsolation);
  assert.deepEqual(payload.background_isolation, backgroundIsolation);
  assert.equal(payload.backgroundIsolation, undefined);
});


test('malformed background isolation config fails closed while disabled config remains safe', () => {
  for (const malformed of [
    [],
    { schema_version: 99, enabled: true },
    { enabled: 'true' },
    { enabled: true, mode: 'unknown' },
    { enabled: true, artifact: { status: 'ready' } },
  ]) {
    assert.equal(manifestToEditorState({ background_isolation: malformed }).backgroundIsolation, null);
  }

  const disabled = { enabled: false, reason: 'user_disabled', future: { keep: true } };
  assert.deepEqual(
    manifestToEditorState({ background_isolation: disabled }).backgroundIsolation,
    disabled,
  );
});


test('background isolation persistence clones nested config and does not mutate input', () => {
  const backgroundIsolation = {
    schema_version: 1,
    enabled: true,
    artifact: {
      id: 'bgseq1-fedcba9876543210',
      status: 'ready',
      future: { keep: true },
    },
  };
  const manifest = { background_isolation: backgroundIsolation };
  const loaded = manifestToEditorState(manifest);
  loaded.backgroundIsolation.artifact.future.keep = false;

  assert.equal(backgroundIsolation.artifact.future.keep, true);
  assert.equal(manifest.background_isolation.artifact.future.keep, true);

  const payload = editorStateToSavePayload({ backgroundIsolation });
  payload.background_isolation.artifact.future.keep = false;
  assert.equal(backgroundIsolation.artifact.future.keep, true);
});
