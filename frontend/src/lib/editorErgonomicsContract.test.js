import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const playerPath = path.resolve(__dirname, '../components/SequencePlayer.jsx');
const timelinePath = path.resolve(__dirname, '../components/editor/Timeline.jsx');
const toolbarPath = path.resolve(__dirname, '../components/editor/Toolbar.jsx');
const playheadPath = path.resolve(__dirname, '../components/editor/timeline/TimelinePlayhead.jsx');
const editorShellPath = path.resolve(__dirname, '../components/editor/EditorShell.jsx');

test('SequencePlayer has 9:16 vertical stage with Double-Tap ripple and glass player bar', () => {
  const source = fs.readFileSync(playerPath, 'utf8');

  // Double-tap ripple
  assert.match(source, /doubleTapRipple/);
  assert.match(source, /Double-Tap Visual Ripple Feedback/);

  // Studio Player Control Bar with glass-panel and fixed tabular-nums timecode
  assert.match(source, /rounded-full\s+glass-panel\s+px-3\s+py-1\s+shadow-lg/);
  assert.match(source, /tabular-nums\s+w-\[140px\]/);
});

test('Timeline enforces touch-action none for drag scrubbing and glass-panel layout', () => {
  const source = fs.readFileSync(timelinePath, 'utf8');

  // touch-none must be applied for mobile scrubber stability
  const touchNoneCount = (source.match(/touch-none/g) || []).length;
  assert.ok(touchNoneCount >= 2, `Expected at least 2 touch-none occurrences, found ${touchNoneCount}`);

  // Root container must use glass-panel
  assert.match(source, /<div className="flex h-full flex-col glass-panel">/);
});

test('Toolbar enforces >= 44px mobile touch targets, Q/W trims, and glass styling', () => {
  const source = fs.readFileSync(toolbarPath, 'utf8');

  // Minimum 44px touch target on buttons
  assert.match(source, /min-h-\[44px\]\s+min-w-\[44px\]/);

  // Q and W trim tools
  assert.match(source, /shortcut="Q"/);
  assert.match(source, /shortcut="W"/);
  assert.match(source, /label="ตัดหัว"/);
  assert.match(source, /label="ตัดท้าย"/);

  // Glass-tile toolbar container
  assert.match(source, /glass-tile/);
});

test('TimelinePlayhead has high-visibility 3.5px line and glow', () => {
  const source = fs.readFileSync(playheadPath, 'utf8');

  assert.match(source, /w-\[3\.5px\]/);
  assert.match(source, /shadow-\[0_0_8px_rgba\(255,255,255,0\.9\)\]/);
});

test('EditorShell provides >=44px mobile tabs, wake lock, and glass panels', () => {
  const source = fs.readFileSync(editorShellPath, 'utf8');

  // Mobile tabs >= 44px
  assert.match(source, /min-h-\[44px\]/);

  // Screen wake lock
  assert.match(source, /useWakeLock/);

  // Glassmorphism classes
  assert.match(source, /glass-panel/);
});
