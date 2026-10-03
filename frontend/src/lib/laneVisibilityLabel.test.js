import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  PREVIEW_ONLY_HIDDEN_TEXT,
  previewOnlyLaneLabel,
  previewOnlyEyeTitle,
} from './laneVisibilityLabel.js';

test('a visible lane keeps its own name and gets no tooltip or colour', () => {
  assert.deepEqual(previewOnlyLaneLabel('คำบรรยาย', false), {
    text: 'คำบรรยาย',
    title: undefined,
    labelClass: '',
  });
});

test('a lane hidden in the preview shows the status and says what the render still does', () => {
  const label = previewOnlyLaneLabel('คำบรรยาย', true);
  assert.equal(label.text, PREVIEW_ONLY_HIDDEN_TEXT);
  assert.equal(PREVIEW_ONLY_HIDDEN_TEXT, 'ซ่อนเฉพาะพรีวิว');
  assert.match(label.title, /คำบรรยาย/);
  assert.match(label.title, /render ยังมี/);
  assert.match(label.labelClass, /amber/);
});

test('eye tooltip: closed eye states the preview-only scope, open eye keeps the old wording', () => {
  assert.equal(previewOnlyEyeTitle('สติกเกอร์', false), 'คลิกเพื่อซ่อนสติกเกอร์บนพรีวิว');
  const closed = previewOnlyEyeTitle('สติกเกอร์', true);
  assert.match(closed, /^ซ่อนเฉพาะพรีวิว/);
  assert.match(closed, /คลิกเพื่อแสดงสติกเกอร์บนพรีวิว/);
});

// Only the three eyes backed by local useState in EditorShell are preview-only.
// The text-overlay and hook eyes write `hidden` into the project and
// subtitle_engine drops hidden overlays, so labelling them "preview only"
// would be a lie in the other direction.
const timelineSource = readFileSync(new URL('../components/editor/Timeline.jsx', import.meta.url), 'utf8');

test('Timeline marks the caption, sticker and cutout lanes, and only those', () => {
  for (const [name, flag] of [['คำบรรยาย', 'isCaptionHidden'], ['สติกเกอร์', 'isStickerHidden'], ['สินค้าไดคัท', 'isCutoutHidden']]) {
    assert.ok(timelineSource.includes(`previewOnlyLaneLabel('${name}', ${flag}).text`), `${name} label`);
    assert.ok(timelineSource.includes(`previewOnlyEyeTitle('${name}', ${flag})`), `${name} eye title`);
  }
  assert.doesNotMatch(timelineSource, /previewOnlyLaneLabel\('ข้อความ/);
  assert.doesNotMatch(timelineSource, /previewOnlyLaneLabel\('ป้ายฮุก/);
});

test('the hide flags behind those three lanes really are local, unsaved state', () => {
  const shell = readFileSync(new URL('../components/editor/EditorShell.jsx', import.meta.url), 'utf8');
  assert.match(shell, /const \[isCaptionHidden, setIsCaptionHidden\] = useState\(false\)/);
  assert.match(shell, /const \[isCutoutHidden, setIsCutoutHidden\] = useState\(false\)/);
  assert.match(shell, /const \[isStickerHidden, setIsStickerHidden\] = useState\(false\)/);
});
