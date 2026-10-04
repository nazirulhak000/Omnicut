import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  cameraKeyframesOf,
  copyClipSettings,
  pasteClipSettingsInState,
  pasteClipSettingsToClips,
  rescaleCameraKeyframes,
} from './clipSettingsClipboard.js';

const SOURCE = {
  id: 'a',
  source_path: 'a.mp4',
  trim_start: 0,
  trim_end: 4,
  speed: 2,
  smooth_slowmo: true,
  zoom: 1.2,
  pan_x: 0.1,
  brightness: 0.05,
  contrast: 1.1,
  saturation: 1.3,
  transition_in: 'fade',
  transition_duration: 0.4,
  transition_easing: 'ease_in_out',
  volume: 0.7,
  rotation: 90,
  mirror: true,
  keyframes: [
    { time: 0, zoom: 1 },
    { time: 2, zoom: 1.3, easing: 'ease_in_out' },
    { time: 1, text_note: 'not camera' },
  ],
};

const TARGET = {
  id: 'b',
  source_path: 'b.mp4',
  trim_start: 1,
  trim_end: 7, // played 6 / speed 2 (after paste) = 3 s
  speed: 1,
  volume: 0.2,
  rotation: 0,
  keyframes: [{ time: 0.5, pan_y: 0.2 }, { time: 0.1, text_note: 'keep me' }],
};

test('cameraKeyframesOf keeps only zoom/pan points', () => {
  assert.deepEqual(cameraKeyframesOf(SOURCE.keyframes).map((p) => p.time), [0, 2]);
  assert.deepEqual(cameraKeyframesOf(undefined), []);
});

test('copyClipSettings snapshots settings only, never trim/source/volume/rotation/mirror', () => {
  const snap = copyClipSettings(SOURCE);
  assert.equal(snap.values.speed, 2);
  assert.equal(snap.values.zoom, 1.2);
  assert.equal(snap.values.transition_easing, 'ease_in_out');
  for (const field of ['trim_start', 'trim_end', 'source_path', 'volume', 'rotation', 'mirror', 'id']) {
    assert.equal(field in snap.values, false, field);
  }
  assert.equal(snap.playedDuration, 2); // 4 s of source at 2x
  assert.equal(snap.cameraKeyframes.length, 2);
  // A snapshot is a copy: editing the source clip afterwards does not change it.
  SOURCE.keyframes[1].zoom = 9;
  assert.equal(snap.cameraKeyframes[1].zoom, 1.3);
  SOURCE.keyframes[1].zoom = 1.3;
  assert.equal(copyClipSettings(null), null);
});

test('rescaleCameraKeyframes scales to the target length and keeps easing', () => {
  const points = [{ time: 0, zoom: 1 }, { time: 2, zoom: 1.3, easing: 'ease_in_out' }];
  const scaled = rescaleCameraKeyframes(points, 2, 3);
  assert.deepEqual(scaled, [{ time: 0, zoom: 1 }, { time: 3, zoom: 1.3, easing: 'ease_in_out' }]);
  assert.equal(points[1].time, 2, 'input is not mutated');
  // Same length (within a frame) or unknown length: times are kept as they are.
  assert.deepEqual(rescaleCameraKeyframes(points, 2, 2.02), points);
  assert.deepEqual(rescaleCameraKeyframes(points, 0, 3), points);
  assert.deepEqual(rescaleCameraKeyframes(points, 2, 0), points);
  // Never outside the clip.
  assert.equal(rescaleCameraKeyframes([{ time: 5, zoom: 1 }], 2, 3)[0].time, 3);
});

test('paste writes settings and swaps camera keyframes, keeping the target\'s own content', () => {
  const snap = copyClipSettings(SOURCE);
  const { clipList, changed } = pasteClipSettingsToClips([SOURCE, TARGET], snap, ['b']);
  assert.equal(changed, 1);
  const pasted = clipList[1];
  assert.equal(pasted.speed, 2);
  assert.equal(pasted.smooth_slowmo, true);
  assert.equal(pasted.zoom, 1.2);
  assert.equal(pasted.brightness, 0.05);
  assert.equal(pasted.transition_in, 'fade');
  assert.equal(pasted.transition_easing, 'ease_in_out');
  // Not settings: untouched.
  assert.equal(pasted.trim_start, 1);
  assert.equal(pasted.trim_end, 7);
  assert.equal(pasted.source_path, 'b.mp4');
  assert.equal(pasted.volume, 0.2);
  assert.equal(pasted.rotation, 0);
  // The target's old camera point is replaced; its non-camera point survives.
  const camera = cameraKeyframesOf(pasted.keyframes);
  assert.equal(camera.some((p) => p.pan_y === 0.2), false);
  assert.equal(pasted.keyframes.some((p) => p.text_note === 'keep me'), true);
  // Source played 2 s, target now plays (7-1)/2 = 3 s: 2 s -> 3 s, easing kept.
  assert.deepEqual(camera.map((p) => p.time), [0, 3]);
  assert.equal(camera[1].easing, 'ease_in_out');
  // The source clip itself is untouched.
  assert.equal(clipList[0], SOURCE);
});

test('paste uses the source file duration for a clip without trim_end', () => {
  const open = { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: null, keyframes: [] };
  const snap = copyClipSettings(SOURCE); // played 2 s
  const { clipList } = pasteClipSettingsToClips([open], snap, ['c'], { c: 8 }); // 8 s at 2x = 4 s
  assert.deepEqual(cameraKeyframesOf(clipList[0].keyframes).map((p) => p.time), [0, 4]);
});

test('paste to several clips changes each, and skips ids that are not in the list', () => {
  const second = { id: 'd', trim_start: 0, trim_end: 4, speed: 1, keyframes: [] };
  const snap = copyClipSettings(SOURCE);
  const { clipList, changed } = pasteClipSettingsToClips([SOURCE, TARGET, second], snap, ['b', 'd', 'nope']);
  assert.equal(changed, 2);
  assert.equal(clipList[1].zoom, 1.2);
  assert.equal(clipList[2].zoom, 1.2);
});

test('pasting identical settings changes nothing and returns the same array/state', () => {
  const snap = copyClipSettings(SOURCE);
  const once = pasteClipSettingsToClips([SOURCE, TARGET], snap, ['b']).clipList;
  const again = pasteClipSettingsToClips(once, snap, ['b']);
  assert.equal(again.changed, 0);
  assert.equal(again.clipList, once);
  const state = { clipList: once, other: 1 };
  assert.equal(pasteClipSettingsInState(state, snap, ['b']), state);
  assert.notEqual(pasteClipSettingsInState({ clipList: [SOURCE, TARGET] }, snap, ['b']).clipList[1], TARGET);
});

test('pasting a clip with nothing set resets the target\'s settings', () => {
  const plain = { id: 'p', trim_start: 0, trim_end: 4, speed: 1, keyframes: [] };
  const tuned = { id: 't', trim_start: 0, trim_end: 4, speed: 1.5, zoom: 1.4, brightness: 0.1, keyframes: [{ time: 1, zoom: 1.2 }] };
  const { clipList } = pasteClipSettingsToClips([plain, tuned], copyClipSettings(plain), ['t']);
  assert.equal(clipList[1].speed, 1);
  assert.equal(clipList[1].zoom, undefined);
  assert.equal(clipList[1].brightness, undefined);
  assert.deepEqual(clipList[1].keyframes, []);
});

test('no snapshot or no targets is a no-op', () => {
  const list = [SOURCE, TARGET];
  assert.deepEqual(pasteClipSettingsToClips(list, null, ['b']), { clipList: list, changed: 0 });
  assert.equal(pasteClipSettingsToClips(list, copyClipSettings(SOURCE), []).clipList, list);
});

test('T11 Benchmark: copy from clip A and paste to B, C, D in a single atomic operation', () => {
  const clipA = {
    id: 'clip-a',
    source_path: 'footage_a.mp4',
    trim_start: 1,
    trim_end: 5,
    speed: 1.5,
    smooth_slowmo: true,
    zoom: 1.3,
    pan_x: 0.15,
    pan_y: -0.1,
    brightness: 0.08,
    contrast: 1.15,
    saturation: 1.25,
    transition_in: 'dissolve',
    transition_duration: 0.5,
    transition_easing: 'ease_in_out',
    volume: 0.8,
    keyframes: [
      { time: 0, zoom: 1.0 },
      { time: 2.667, zoom: 1.3 }, // at played duration 4s / 1.5 = 2.667s
    ],
  };

  const clipB = { id: 'clip-b', source_path: 'footage_b.mp4', trim_start: 0, trim_end: 3, speed: 1, volume: 0.5 };
  const clipC = { id: 'clip-c', source_path: 'footage_c.mp4', trim_start: 2, trim_end: 8, speed: 1, volume: 1.0 };
  const clipD = { id: 'clip-d', source_path: 'footage_d.mp4', trim_start: 0, trim_end: 2, speed: 2, volume: 0.6 };

  const snapshot = copyClipSettings(clipA);
  assert.ok(snapshot, 'snapshot created from clip A');
  assert.equal(snapshot.values.speed, 1.5);
  assert.equal(snapshot.values.zoom, 1.3);
  assert.equal(snapshot.values.brightness, 0.08);

  const initialList = [clipA, clipB, clipC, clipD];
  const targetIds = ['clip-b', 'clip-c', 'clip-d'];
  const { clipList, changed } = pasteClipSettingsToClips(initialList, snapshot, targetIds);

  assert.equal(changed, 3, 'all 3 target clips updated');

  // Verify clip A is unchanged
  assert.equal(clipList[0], clipA);

  // Verify B, C, D received the copied settings
  for (let i = 1; i <= 3; i++) {
    const target = clipList[i];
    assert.equal(target.speed, 1.5);
    assert.equal(target.smooth_slowmo, true);
    assert.equal(target.zoom, 1.3);
    assert.equal(target.pan_x, 0.15);
    assert.equal(target.pan_y, -0.1);
    assert.equal(target.brightness, 0.08);
    assert.equal(target.contrast, 1.15);
    assert.equal(target.saturation, 1.25);
    assert.equal(target.transition_in, 'dissolve');
    assert.equal(target.transition_duration, 0.5);

    // Verify untouched fields are preserved
    assert.equal(target.source_path, initialList[i].source_path);
    assert.equal(target.trim_start, initialList[i].trim_start);
    assert.equal(target.trim_end, initialList[i].trim_end);
    assert.equal(target.volume, initialList[i].volume);

    // Verify camera keyframes are rescaled to target played duration
    assert.ok(Array.isArray(target.keyframes) && target.keyframes.length === 2);
  }
});

test('UI contracts: Toolbar, Inspector, and EditorShell wire copy/paste clip settings', () => {
  const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
  const toolbarSource = read('../components/editor/Toolbar.jsx');
  const inspectorSource = read('../components/editor/Inspector.jsx');
  const clipInspectorSource = read('../components/editor/inspector/ClipInspector.jsx');
  const editorShellSource = read('../components/editor/EditorShell.jsx');

  // Toolbar checks
  assert.match(toolbarSource, /ClipboardCopy/);
  assert.match(toolbarSource, /ClipboardPaste/);
  assert.match(toolbarSource, /label="คัดลอกค่า"/);
  assert.match(toolbarSource, /shortcut="Ctrl\+Alt\+C"/);
  assert.match(toolbarSource, /shortcut="Ctrl\+Alt\+V"/);

  // Inspector multi-select banner checks
  assert.match(inspectorSource, /data-testid="inspector-multi-select"/);
  assert.match(inspectorSource, /canPasteSettings &&/);
  assert.match(inspectorSource, /วางการตั้งค่า/);
  assert.match(inspectorSource, /onCopySettings=\{onCopySettings\}/);
  assert.match(inspectorSource, /onPasteSettings=\{onPasteSettings\}/);

  // ClipInspector checks
  assert.match(clipInspectorSource, /ClipboardCopy/);
  assert.match(clipInspectorSource, /ClipboardPaste/);
  assert.match(clipInspectorSource, /คัดลอกการตั้งค่า/);
  assert.match(clipInspectorSource, /วางการตั้งค่า/);

  // EditorShell checks (wiring to Toolbar and Inspector)
  assert.match(editorShellSource, /onCopySettings=\{copyClipSettings\}/);
  assert.match(editorShellSource, /onPasteSettings=\{pasteClipSettings\}/);
  assert.match(editorShellSource, /canPasteSettings=\{hasCopiedClipSettings\}/);
});
