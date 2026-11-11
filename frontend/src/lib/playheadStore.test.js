import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import { createPlayheadStore } from './playheadStore.js';

const read = (rel) => fs.readFileSync(new URL(rel, import.meta.url), 'utf8');

test('playhead store: get/set and change notifications', () => {
  const store = createPlayheadStore(1.5);
  assert.equal(store.get(), 1.5);

  const seen = [];
  const unsubscribe = store.subscribe(() => seen.push(store.get()));
  store.set(2);
  store.set(2); // unchanged value: no notification
  store.set(2.5);
  assert.deepEqual(seen, [2, 2.5]);

  unsubscribe();
  store.set(9);
  assert.deepEqual(seen, [2, 2.5], 'no notification after unsubscribe');
  assert.equal(store.get(), 9);
});

test('playhead store: every subscriber is told, and each store is independent', () => {
  const a = createPlayheadStore();
  const b = createPlayheadStore();
  let first = 0;
  let second = 0;
  a.subscribe(() => { first += 1; });
  a.subscribe(() => { second += 1; });
  a.set(1);
  b.set(5);
  assert.deepEqual([first, second], [1, 1]);
  assert.equal(a.get(), 1);
  assert.equal(b.get(), 5);
});

test('playback ticks stay out of EditorShell state', () => {
  const shell = read('../components/editor/EditorShell.jsx');
  // ticks go to the store only; seeks/play/end still settle the React state
  assert.match(shell, /const handlePlayheadTick = useCallback\(\(time\) => \{\s*playheadStore\.set\(time\);\s*\}, \[playheadStore\]\);/);
  assert.match(shell, /onPlayheadTick=\{handlePlayheadTick\}/);
  assert.match(shell, /onPlayingChange=\{handlePlayingChange\}/);
  assert.match(shell, /<PlayheadContext\.Provider value=\{playheadStore\}>/);
  // handlers read the time when the user acts, so they do not depend on the settled value
  assert.doesNotMatch(shell, /\}, \[playhead, /);
  assert.equal((shell.match(/onPlayheadTick=\{handlePlayheadTick\}/g) || []).length, 2, 'desktop and mobile players');

  const player = read('../components/SequencePlayer.jsx');
  assert.match(player, /\(onPlayheadTick \|\| onPlayhead\)\?\.\(t\);/);
  assert.match(player, /onPlayingChangeRef\.current\?\.\(isPlaying\);/);
});

test('editor hooks read the playhead at event time', () => {
  for (const name of ['useEditorSelection', 'useEditorCommands', 'useEditorShortcuts']) {
    const source = read(`../hooks/${name}.js`);
    assert.match(source, /getPlayhead = null,/, `${name} accepts getPlayhead`);
    assert.match(source, /const readPlayhead = useCallback\(/, `${name} defines readPlayhead`);
    // no handler may close over the raw `playhead` value any more
    const body = source.slice(source.indexOf('const readPlayhead'));
    assert.doesNotMatch(body.replace(/\/\/.*$/gm, ''), /(?<![.\w])playhead(?!\s*:)\b(?!Fallback)/, `${name} has no stale playhead read`);
  }
});

test('only the parts that follow the playhead subscribe to it', () => {
  assert.match(read('../components/editor/timeline/TimelinePlayhead.jsx'), /useLivePlayhead\(playhead\)/);
  assert.match(read('../components/editor/LiveToolbar.jsx'), /useLivePlayheadSelector\(/);
  assert.match(read('../components/editor/inspector/CuesTranscriptInspector.jsx'), /useLivePlayheadSelector\(/);
  const timeline = read('../components/editor/Timeline.jsx');
  assert.match(timeline, /usePlayheadEffect\(/);
  assert.doesNotMatch(timeline, /useLivePlayhead\(/, 'Timeline itself must not re-render on every tick');
});
