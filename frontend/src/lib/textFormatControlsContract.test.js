import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Buttons that look like formatting but change nothing in the render are worse
// than no button: the user cannot read code, so a lit "B" reads as "bold on".
// These checks pin which of them exist, per what the render really honours.

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const captionSource = read('../components/editor/inspector/CaptionInspector.jsx');
const overlaySource = read('../components/editor/inspector/OverlayInspector.jsx');

test('caption inspector has no bold/italic/underline or alignment buttons (they never reached the render)', () => {
  assert.doesNotMatch(captionSource, /setTextPattern|textPattern/);
  assert.doesNotMatch(captionSource, /setTextAlign|textAlign/);
  assert.doesNotMatch(captionSource, /AlignLeft|AlignCenter|AlignRight/);
  assert.doesNotMatch(captionSource, /title="ตัวหนา"|title="ตัวเอียง"|title="ขีดเส้นใต้"/);
  assert.doesNotMatch(captionSource, /title="ชิดซ้าย"|title="กึ่งกลาง"|title="ชิดขวา"|จัดแนว:/);
});

test('caption inspector still has the controls that do reach the render', () => {
  assert.match(captionSource, /ปรับขนาดตัวอักษรคำบรรยาย/);
  assert.match(captionSource, /handlePositionChange/);
  assert.match(captionSource, /handleColorChange/);
  assert.match(captionSource, /handleFontChange/);
});

test('free-text overlay has no local-only bold, underline or alignment buttons', () => {
  assert.doesNotMatch(overlaySource, /setTextPattern|textPattern/);
  assert.doesNotMatch(overlaySource, /setTextAlign|textAlign/);
  assert.doesNotMatch(overlaySource, /AlignLeft|AlignCenter|AlignRight/);
  assert.doesNotMatch(overlaySource, /จัดแนว:/);
});

test('free-text overlay keeps italic (skew is the fax tag in _text_overlay_events) and the hook tiers keep B/I/U', () => {
  assert.match(overlaySource, /patchOverlayLook\(\{ skew: isItalic \? 0\.0 : -0\.25 \}\)/);
  for (const field of ['bold', 'italic', 'underline']) {
    assert.ok(overlaySource.includes(`patchHookTier(idx, { ${field}: !look.${field} })`), field);
  }
});
