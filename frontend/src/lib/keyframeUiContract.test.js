import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

test('ClipInspector contract: diamond keyframe button and navigation controls exist', () => {
  const src = read('../components/editor/inspector/ClipInspector.jsx');
  assert.match(src, /data-testid="diamond-keyframe-button"/);
  assert.match(src, /handleToggleKeyframe/);
  assert.match(src, /handleSeekToKeyframe/);
  assert.match(src, /prevKf/);
  assert.match(src, /nextKf/);
  assert.match(src, /hasKeyframeAtPlayhead/);
  assert.match(src, /motionTimeAt\(selectedSeg, playhead\)/);
  assert.match(src, /keyframes\.length > 0/);
});

test('TimelineClip contract: visual keyframe diamond markers are rendered on clip body', () => {
  const src = read('../components/editor/TimelineClip.jsx');
  assert.match(src, /data-testid="timeline-keyframe-marker"/);
  assert.match(src, /Array\.isArray\(clip\.keyframes\)/);
  assert.match(src, /rotate-45/);
  assert.match(src, /kfTime \* pxPerSec/);
});

test('Inspector contract: passes playhead and onSeek to ClipInspector', () => {
  const src = read('../components/editor/Inspector.jsx');
  assert.match(src, /<ClipInspector[\s\S]*?playhead=\{playhead\}[\s\S]*?onSeek=\{onSeek\}/);
});
