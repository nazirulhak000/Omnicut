import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const headerSource = readFileSync(
  new URL('../components/editor/inspector/OverlayInspectorHeader.jsx', import.meta.url),
  'utf8',
);
const stickerSource = readFileSync(
  new URL('../components/editor/inspector/StickerInspector.jsx', import.meta.url),
  'utf8',
);
const effectSource = readFileSync(
  new URL('../components/editor/inspector/EffectInspector.jsx', import.meta.url),
  'utf8',
);

test('overlay inspector header owns shared identity and timing layout', () => {
  assert.match(headerSource, /preview,\s*icon: Icon,\s*kindLabel,\s*title,\s*duration,\s*start,\s*end/);
  assert.match(headerSource, /duration\.toFixed\(1\).*start\.toFixed\(1\).*end\.toFixed\(1\)/s);
  assert.match(headerSource, /previewClassName/);
});

test('sticker and effect inspectors provide media-specific header config', () => {
  assert.match(stickerSource, /import OverlayInspectorHeader from '\.\/OverlayInspectorHeader'/);
  assert.match(stickerSource, /icon=\{Smile\}/);
  assert.match(stickerSource, /kindLabel="สติกเกอร์ 3D"/);
  assert.match(effectSource, /import OverlayInspectorHeader from '\.\/OverlayInspectorHeader'/);
  assert.match(effectSource, /icon=\{Sparkles\}/);
  assert.match(effectSource, /accentClass="text-fuchsia-400"/);
  assert.match(effectSource, /<video/);
});
