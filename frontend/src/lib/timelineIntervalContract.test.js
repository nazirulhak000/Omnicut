import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const shellSource = readFileSync(
  new URL('../components/editor/timeline/TimelineIntervalItem.jsx', import.meta.url),
  'utf8',
);
const timelineSource = readFileSync(
  new URL('../components/editor/Timeline.jsx', import.meta.url),
  'utf8',
);

test('timeline interval shell keeps two handles by default and supports one-sided items', () => {
  assert.match(shellSource, /showLeftHandle = true/);
  assert.match(shellSource, /showRightHandle = true/);
  assert.match(shellSource, /\{showLeftHandle && \(/);
  assert.match(shellSource, /\{showRightHandle && \(/);
});

test('hook uses the shared shell without enabling a left trim handle', () => {
  assert.match(timelineSource, /<TimelineIntervalItem\s+dataType="hook"/);
  assert.match(timelineSource, /showLeftHandle=\{false\}/);
  assert.match(timelineSource, /rightHandleTitle=\{`ลากเพื่อปรับระยะเวลาแสดงผลป้ายฮุก/);
});

test('caption uses the shared shell while retaining caption-specific drag adapters', () => {
  assert.match(timelineSource, /<TimelineIntervalItem\s+key=\{cue\._uid\}\s+dataType="caption"/);
  assert.match(timelineSource, /onTrimStart=\{\(e, edge\) => startTrim\(e, cue, edge\)\}/);
  assert.match(timelineSource, /onBodyMove=\{\(e\) => moveCaptionBodyDrag\(e, cue\)\}/);
  assert.match(timelineSource, /rightHandleTitle="ลากเพื่อยืด\/หดเวลาสิ้นสุด"/);
});
