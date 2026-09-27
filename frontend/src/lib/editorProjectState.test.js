import test from 'node:test';
import assert from 'node:assert/strict';

import {
  editorStateToSavePayload,
  manifestToEditorState,
  serializeRenderFeatures,
  serializeClips,
  serializeRenderClips,
  serializeOverlays,
  serializeTransitions,
} from './editorProjectState.js';

test('text depth and scoped Cutout survive save and reload without changing legacy defaults', () => {
  const input = {
    clipList: [{ id: 'local', source_path: 'a.mp4', trim_start: 0, trim_end: 5,
      background_isolation: { enabled: true, scope_mode: 'behind_text_windows',
        active_intervals: [{ start: 0, end: 2 }],
        artifact: { id: 'bgseq1-0123456789abcdef', status: 'ready' } } }],
    overlays: [{ id: 'text', kind: 'text', subject_layer: 'behind', start: 0, end: 2,
      tiers: [{ text: 'SPEC' }] },
    { id: 'hook', kind: 'hook', start: 0, end: 1, tiers: [{ text: 'HOOK' }] }],
    backgroundIsolation: { schema_version: 1, enabled: true, scope_mode: 'behind_text_windows',
      mode: 'cutout', engine: 'rembg', model: 'u2net', quality: 'balanced',
      artifact: { id: null, status: 'missing' } },
  };
  const payload = editorStateToSavePayload(input);
  const loaded = manifestToEditorState(payload);
  assert.equal(loaded.overlays[0].subject_layer, 'behind');
  assert.equal(Object.hasOwn(loaded.overlays[1], 'subject_layer'), false);
  assert.equal(loaded.clipList[0].background_isolation.active_intervals[0].end, 2);
  assert.equal(loaded.backgroundIsolation.scope_mode, 'behind_text_windows');
});

test('scoped render carries local clip identity while saved and legacy clips stay unchanged', () => {
  const clips = [{ id: 'editor-a', source_path: 'a.mp4', trim_start: 0, trim_end: 5 }];
  assert.equal(serializeRenderClips(clips, 'behind_text_windows')[0].id, 'editor-a');
  assert.equal(Object.hasOwn(serializeRenderClips(clips, 'legacy_clip')[0], 'id'), false);
  assert.equal(Object.hasOwn(editorStateToSavePayload({ clipList: clips }).clip_list[0], 'id'), false);
});


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
  assert.deepEqual(first.audio_mutes, { bgm: true, sfx: true, clip: true });
  assert.equal(first.cues[0]._uid, undefined);
});

test('solo and clip edits survive save/reload without turning derived mutes into user mutes', () => {
  const clip = {
    id: 'camera-clip', source_path: 'camera.mp4', trim_start: 0.5, trim_end: 2.5,
    speed: 1.5, freeze_tail: 0.4, zoom: 1.3, pan_x: 0.2, pan_y: -0.1,
    rotation: 90, mirror: true, fit_mode: 'blur', volume: 0.6,
    keyframes: [{ time: 0, zoom: 1.1 }, { time: 1, zoom: 1.5 }],
  };
  const input = { clipList: [clip], trackMix: { mute: { bgm: true }, solo: { voice: true } } };
  const saved = editorStateToSavePayload(input);
  const loaded = manifestToEditorState(saved);

  for (const field of [
    'trim_start', 'trim_end', 'speed', 'freeze_tail', 'zoom', 'pan_x', 'pan_y',
    'rotation', 'mirror', 'fit_mode', 'volume',
  ]) {
    assert.equal(loaded.clipList[0][field], clip[field], field);
  }
  assert.deepEqual(loaded.clipList[0].keyframes, clip.keyframes);
  assert.deepEqual(saved.audio_mutes, { bgm: true, sfx: true, clip: true });
  assert.deepEqual(loaded.trackMix.mute, { bgm: true });
  assert.deepEqual(loaded.trackMix.solo, { voice: true });
});


test('caption line breaks, timing, and style survive save and reload', () => {
  const input = {
    cuesList: [{
      _uid: 'caption-parity-cue',
      start: 0,
      end: 2,
      text: 'บรรทัดหนึ่ง\nLINE TWO\nราคา 9,990 บาท',
      bilingual: false,
      position: 'bottom',
      fontName: 'IBM Plex Sans Thai',
    }],
    style: {
      fontName: 'IBMPlex',
      captionPosition: 'bottom',
      captionScale: 1,
      captionColor: '#FFFFFF',
    },
  };

  const saved = editorStateToSavePayload(input);
  const reloaded = manifestToEditorState(saved);

  assert.equal(saved.cues[0]._uid, undefined);
  assert.equal(reloaded.cuesList[0].text, input.cuesList[0].text);
  assert.equal(reloaded.cuesList[0].start, 0);
  assert.equal(reloaded.cuesList[0].end, 2);
  assert.equal(reloaded.cuesList[0].position, 'bottom');
  assert.equal(reloaded.cuesList[0].fontName, 'IBM Plex Sans Thai');
  assert.equal(reloaded.style.captionPosition, 'bottom');
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


test('motion text font metrics, line layout, and contracts survive save and reload', () => {
  const motionOverlay = {
    id: 'hook-motion-parity',
    kind: 'hook',
    anchor: 'top',
    x: 0.5,
    y: 260 / 1920,
    base_fs_ratio: 0.065,
    comfortable_lines: 4,
    look: {
      font: 'IBM Plex Sans Thai',
      bold: true,
      outline_px: 3,
      shadow: { color: '#000000', blur: 8, dx: 0, dy: 4 },
    },
    tiers: [
      { text: 'นั่งนิ่งจริงครับ', look: { color: '#FFFFFF' } },
      { text: 'Motion 1,125 🚀', look: { color: '#25F4EE' } },
      { text: 'บรรทัดสาม', look: { color: '#FFFFFF' } },
    ],
    layout: {
      lines: [
        { text: 'นั่งนิ่งจริงครับ', words: [{ text: 'นั่งนิ่งจริงครับ', x: 0.34, w: 0.32 }] },
        { text: 'Motion 1,125 🚀', words: [{ text: 'Motion 1,125 🚀', x: 0.35, w: 0.30 }] },
        { text: 'บรรทัดสาม', words: [{ text: 'บรรทัดสาม', x: 0.41, w: 0.18 }] },
      ],
    },
    anim: { in: 'bounce', loop: 'pulse', out: 'fade', speed: 'smooth', stagger: true },
    motionContract: {
      phases: {
        in: { id: 'hook.in.bounce', role: 'hook', phase: 'in', duration_ms: 450 },
        loop: { id: 'hook.loop.pulse', role: 'hook', phase: 'loop', duration_ms: 700 },
        out: { id: 'hook.out.fade', role: 'hook', phase: 'out', duration_ms: 150 },
      },
    },
    motionMetadata: { role: 'hook', schema_version: 1 },
  };

  const loaded = manifestToEditorState({ overlays: [motionOverlay] });
  const payload = editorStateToSavePayload({ overlays: loaded.overlays });
  const reloaded = manifestToEditorState({ overlays: payload.overlays });
  const saved = reloaded.overlays[0];

  assert.equal(saved.anchor, motionOverlay.anchor);
  assert.equal(saved.x, motionOverlay.x);
  assert.equal(saved.y, motionOverlay.y);
  assert.equal(saved.base_fs_ratio, motionOverlay.base_fs_ratio);
  assert.equal(saved.comfortable_lines, motionOverlay.comfortable_lines);
  assert.deepEqual(saved.look, motionOverlay.look);
  assert.deepEqual(saved.tiers, motionOverlay.tiers);
  assert.deepEqual(saved.layout, motionOverlay.layout);
  assert.deepEqual(saved.anim, motionOverlay.anim);
  assert.deepEqual(saved.motionContract, motionOverlay.motionContract);
  assert.deepEqual(saved.motionMetadata, motionOverlay.motionMetadata);
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


test('sticker, effect, and spotlight timing and geometry survive save and reload', () => {
  const input = {
    stickers: [{
      id: 'sticker-parity',
      badge: 'arrow_pointer_cyan_3d.png',
      start: 0.5,
      end: 2.75,
      normX: 0.72,
      normY: 0.22,
      scale: 1.15,
      hidden: false,
      recolor: 'accent',
      recolorSourceHue: 180,
    }],
    effects: [{
      id: 'effect-parity',
      effectId: 'fx_checkmark_01',
      start: 1.25,
      end: 3.5,
      normX: 0.52,
      normY: 0.34,
      scale: 0.9,
      hidden: false,
      recolor: 'accent',
      recolorSourceHue: 205,
    }],
    spotlight: {
      schema_version: 1,
      enabled: true,
      shape: 'ellipse',
      focus: { x: 0.5, y: 0.45, width: 0.52, height: 0.34 },
      dim_opacity: 0.42,
      feather: 0.02,
      corner_radius: 0.08,
    },
  };

  const saved = editorStateToSavePayload(input);
  const reloaded = manifestToEditorState(saved);

  assert.deepEqual(reloaded.stickers, input.stickers);
  assert.deepEqual(reloaded.effects, input.effects);
  assert.deepEqual(reloaded.spotlight, input.spotlight);
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
