import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const clipInspectorSource = read('../components/editor/inspector/ClipInspector.jsx');
const overlayInspectorSource = read('../components/editor/inspector/OverlayInspector.jsx');

test('ClipInspector has continuous speed range slider alongside presets and typed input', () => {
  assert.match(clipInspectorSource, /แถบเลื่อนความเร็ว/);
  assert.match(clipInspectorSource, /min=\{MIN_CLIP_SPEED\}/);
  assert.match(clipInspectorSource, /max=\{MAX_CLIP_SPEED\}/);
  assert.match(clipInspectorSource, /step="0\.05"/);
  assert.match(clipInspectorSource, /sliderChange\('speed',\s*\{\s*speed:/);
});

test('ClipInspector embeds TransitionDurationControl for transition duration editing', () => {
  assert.match(clipInspectorSource, /import TransitionDurationControl from '\.\.\/timeline\/TransitionDurationControl'/);
  assert.match(clipInspectorSource, /<TransitionDurationControl/);
  assert.match(clipInspectorSource, /transition_duration:\s*d/);
});

test('OverlayInspector has Outline/Stroke styling controls for text overlays', () => {
  assert.match(overlayInspectorSource, /เส้นขอบ \(Outline \/ Stroke\)/);
  assert.match(overlayInspectorSource, /outline_color:/);
  assert.match(overlayInspectorSource, /outline_px:/);
  assert.match(overlayInspectorSource, /ความหนา/);
});

test('OverlayInspector has Drop Shadow controls for text overlays', () => {
  assert.match(overlayInspectorSource, /เงาตัวอักษร \(Drop Shadow\)/);
  assert.match(overlayInspectorSource, /selectedLook\.shadow/);
  assert.match(overlayInspectorSource, /DEFAULT_SHADOW/);
});

test('OverlayInspector supports custom background pill/box fill color', () => {
  assert.match(overlayInspectorSource, /สีพื้นหลังกรอบ \(กำหนดเอง\)/);
  assert.match(overlayInspectorSource, /selectedLook\.pill\.fill/);
});

test('OverlayInspector handleResetFormat restores outline, shadow, pill and skew to defaults', () => {
  assert.match(overlayInspectorSource, /outline_color:\s*DEFAULT_TEXT_LOOK\.outline_color/);
  assert.match(overlayInspectorSource, /outline_px:\s*DEFAULT_TEXT_LOOK\.outline_px/);
  assert.match(overlayInspectorSource, /shadow:\s*DEFAULT_SHADOW/);
  assert.match(overlayInspectorSource, /pill:\s*null/);
  assert.match(overlayInspectorSource, /skew:\s*0\.0/);
});
