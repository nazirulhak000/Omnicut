import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { MIN_CLIP_DURATION, buildSegments, snapSeekTime, snapToFrame } from './timelineMath.js';
import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';
import { patchClipInState } from './inspectorModel.js';
import { classifyShortcut } from './editorShortcutKeys.js';
import {
  TRIM_MESSAGES,
  collectEditPoints,
  editNavigationTarget,
  freezePlayheadCandidate,
  prevNextEditPoint,
  resolveTrimHead,
  resolveTrimTail,
  trimDragSeekTime,
  withoutPlayheadCandidate,
} from './timelineTrimOps.js';

const FRAME = 1 / 30;
const clip = (id, extra = {}) => ({ id, source_path: `${id}.mp4`, trim_start: 0, trim_end: null, speed: 1, transition_in: 'cut', ...extra });
// Three 4s / 3s / 2s clips back to back (no transitions): 0-4, 4-7, 7-9.
const layout = (clips = [clip('a'), clip('b'), clip('c')], durations = { a: 4, b: 3, c: 2 }) => buildSegments(clips, durations);
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-9, `${msg || ''} ${a} !== ${b}`);

// ---- Q: trim head to the playhead ----------------------------------------

test('Q trims the head of the clip under the playhead to the frame-snapped playhead', () => {
  const segs = layout();
  const r = resolveTrimHead(segs, null, 5.0);
  assert.equal(r.seg.clip.id, 'b');
  near(r.patch.trim_start, snapToFrame(1.0));
  assert.deepEqual(Object.keys(r.patch), ['trim_start']);
  // The kept part slides back to the clip's own start, so the preview stays on the same frame.
  assert.equal(r.seekTo, 4);
});

test('Q snaps an off-grid playhead to a whole frame', () => {
  const r = resolveTrimHead(layout(), null, 5.04); // 151.2 frames -> frame 151
  near(r.patch.trim_start, 31 / 30);
  assert.equal(Math.round(r.patch.trim_start * 30 * 1e6) / 1e6 % 1, 0, 'a whole frame');
});

test('Q prefers the selected clip when the playhead is on it, else the clip under the playhead', () => {
  const segs = layout();
  assert.equal(resolveTrimHead(segs, segs[0], 2).seg.clip.id, 'a');
  // Selected clip is elsewhere: fall back to the one under the playhead.
  assert.equal(resolveTrimHead(segs, segs[0], 5).seg.clip.id, 'b');
});

test('Q respects speed: the cut is a source time, speed times the sequence time', () => {
  const segs = layout([clip('a', { speed: 2, trim_end: 8 })], { a: 8 }); // 8s source at 2x -> 4s on the timeline
  near(segs[0].dur, 4);
  const r = resolveTrimHead(segs, null, 1);
  near(r.patch.trim_start, 2); // 1s of timeline = 2s of source
});

test('Q keeps MIN_CLIP_DURATION and says why when it cannot', () => {
  const segs = layout();
  const tooClose = resolveTrimHead(segs, null, 3.9); // only 0.1s would remain of clip a
  assert.equal(tooClose.seg, null);
  assert.equal(tooClose.message, TRIM_MESSAGES.headTooShort);
  assert.match(tooClose.message, new RegExp(String(MIN_CLIP_DURATION)));
});

test('Q at the head edge, off the clips, with no clips, or in a freeze tail refuses with a reason', () => {
  const segs = layout();
  assert.equal(resolveTrimHead(segs, null, 4).message, TRIM_MESSAGES.headAtEdge); // exact boundary a|b
  assert.equal(resolveTrimHead(segs, null, 0).message, TRIM_MESSAGES.headAtEdge);
  assert.equal(resolveTrimHead(segs, null, 20).message, TRIM_MESSAGES.outside);
  assert.equal(resolveTrimHead([], null, 1).message, TRIM_MESSAGES.noClips);
  const frozen = layout([clip('a', { trim_end: 2, freeze_tail: 2 })], { a: 4 }); // plays 0-2, holds 2-4
  assert.equal(resolveTrimHead(frozen, null, 3).message, TRIM_MESSAGES.freeze);
});

test('Q does nothing (and stays honest) on a clip whose source length is unknown', () => {
  const segs = layout([clip('a')], { a: 0 });
  assert.equal(resolveTrimHead(segs, null, 0.1).seg, null);
});

// ---- W: trim tail to the playhead ----------------------------------------

test('W trims the tail to the frame-snapped playhead and leaves the head alone', () => {
  const segs = layout();
  const r = resolveTrimTail(segs, null, 5.5);
  assert.equal(r.seg.clip.id, 'b');
  near(r.patch.trim_end, snapToFrame(1.5));
  assert.deepEqual(Object.keys(r.patch), ['trim_end']);
  assert.equal(r.seekTo, null);
});

test('W refuses at the tail edge, near the head, and on the boundary', () => {
  const segs = layout();
  const onBoundary = resolveTrimTail(segs, null, 7); // exactly b|c: neither clip has anything sensible to cut
  assert.equal(onBoundary.seg, null);
  assert.ok(onBoundary.message);
  assert.equal(resolveTrimTail(segs, null, 4.1).message, TRIM_MESSAGES.tailTooShort); // only 0.1s of b would stay
  assert.equal(resolveTrimTail(segs, null, 9).message, TRIM_MESSAGES.tailAtEdge); // end of the last clip
  assert.equal(resolveTrimTail(segs, null, 30).message, TRIM_MESSAGES.outside);
});

test('W respects an already-trimmed window and speed', () => {
  const segs = layout([clip('a', { trim_start: 1, trim_end: 5, speed: 2 })], { a: 8 }); // 2s on the timeline
  near(segs[0].dur, 2);
  const r = resolveTrimTail(segs, null, 1);
  near(r.patch.trim_end, 3); // 1 + 1s*2x
  assert.ok(r.patch.trim_end >= 1 + MIN_CLIP_DURATION * 2);
});

test('W never trims inside a freeze tail (the held frame is not source footage)', () => {
  const frozen = layout([clip('a', { trim_end: 2, freeze_tail: 2 })], { a: 4 });
  assert.equal(resolveTrimTail(frozen, null, 3).message, TRIM_MESSAGES.freeze);
  const r = resolveTrimTail(frozen, null, 1);
  near(r.patch.trim_end, 1);
});

test('W on a transition overlap resolves to the incoming clip (the one on screen)', () => {
  const clips = [clip('a'), clip('b', { transition_in: 'fade', transition_duration: 0.5 })];
  const segs = buildSegments(clips, { a: 4, b: 4 });
  assert.ok(segs[1].segStart < segs[0].segEnd, 'clips overlap');
  const inOverlap = segs[1].segStart + 0.25;
  assert.equal(resolveTrimHead(segs, null, snapToFrame(inOverlap)).seg.clip.id, 'b');
});

// ---- one undo step, via the real history model ----------------------------

test('a Q trim is exactly one undo step, and undo restores the previous trim', () => {
  const state0 = { clipList: [clip('a', { trim_end: 4 }), clip('b', { trim_end: 3 })] };
  const model = createEditorHistoryModel(state0);
  const segs = layout([clip('a', { trim_end: 4 }), clip('b', { trim_end: 3 })], { a: 4, b: 3 });
  const r = resolveTrimHead(segs, null, 5);
  assert.ok(r.seg);
  assert.equal(model.set((prev) => patchClipInState(prev, r.seg.clip.id, r.patch)), true);
  assert.equal(model.getState().clipList[1].trim_start, snapToFrame(1));
  assert.equal(model.getState().clipList[0].trim_start, 0, 'other clips untouched');
  assert.equal(model.undo(), true);
  assert.equal(model.getState().clipList[1].trim_start, 0);
  assert.equal(model.undo(), false, 'one trim made exactly one step');
});

// ---- edit points ------------------------------------------------------------

test('collectEditPoints gathers sequence start, clip edges and cue edges, sorted', () => {
  const pts = collectEditPoints(layout(), [{ start: 1.5, end: 2.5 }, { start: 'x', end: 6 }, null]);
  assert.deepEqual(pts, [0, 0, 1.5, 2.5, 4, 4, 6, 7, 7, 9]);
});

test('prevNextEditPoint walks forward and back through the points, stopping at the ends', () => {
  const pts = [0, 4, 7, 9];
  assert.equal(prevNextEditPoint(pts, 0, 1), 4);
  assert.equal(prevNextEditPoint(pts, 4, 1), 7);
  assert.equal(prevNextEditPoint(pts, 5, 1), 7);
  assert.equal(prevNextEditPoint(pts, 9, 1), null);
  assert.equal(prevNextEditPoint(pts, 9, -1), 7);
  assert.equal(prevNextEditPoint(pts, 4, -1), 0);
  assert.equal(prevNextEditPoint(pts, 0, -1), null);
  assert.equal(prevNextEditPoint([], 3, 1), null);
});

test('prevNextEditPoint never returns the point the playhead already sits on', () => {
  // A clip start between frames lands on the next frame; pressing the key again must move on.
  const segs = buildSegments([clip('a', { trim_end: 1.2345 }), clip('b'), clip('c')], { a: 1.2345, b: 2, c: 2 });
  const points = collectEditPoints(segs, []);
  const land = (t) => snapSeekTime(t, segs);
  let here = 0;
  const visited = [];
  for (let i = 0; i < 10; i += 1) {
    const next = prevNextEditPoint(points, here, 1, { land });
    if (next === null) break;
    assert.ok(next > here, `moves forward from ${here} to ${next}`);
    visited.push(next);
    here = next;
  }
  assert.equal(visited.length, 3, 'a/b, b/c boundaries and the end');
  // ...and back again without getting stuck either.
  for (let i = 0; i < 10; i += 1) {
    const prev = prevNextEditPoint(points, here, -1, { land });
    if (prev === null) break;
    assert.ok(prev < here, `moves back from ${here} to ${prev}`);
    here = prev;
  }
  assert.equal(here, 0);
});

test('editNavigationTarget: Home / End go to the sequence start / end of the clips', () => {
  const ctx = { segments: layout(), cues: [], playhead: 5, totalDuration: 9 };
  assert.equal(editNavigationTarget('seekStart', ctx), 0);
  assert.equal(editNavigationTarget('seekEnd', ctx), 9);
  assert.equal(editNavigationTarget('seekEnd', { ...ctx, totalDuration: 0 }), 0);
  assert.equal(editNavigationTarget('togglePlay', ctx), null);
});

test('key -> action -> target: Up/Down/Home/End on a three-clip timeline', () => {
  const segs = layout();
  const cues = [{ start: 1, end: 2 }];
  const press = (key, playhead) => editNavigationTarget(classifyShortcut({ key }).action, { segments: segs, cues, playhead, totalDuration: 9 });
  assert.equal(press('ArrowDown', 0), 1, 'cue start comes before the first clip boundary');
  assert.equal(press('ArrowDown', 2), 4);
  assert.equal(press('ArrowUp', 5), 4);
  assert.equal(press('ArrowUp', 4), 2, 'back over the cue end');
  assert.equal(press('ArrowUp', 0), null);
  assert.equal(press('ArrowDown', 9), null);
  assert.equal(press('Home', 5), 0);
  assert.equal(press('End', 5), 9);
});

test('Q / W / arrows / Home / End are claimed only without Ctrl/Meta/Alt', () => {
  for (const [key, action] of [['q', 'trimHead'], ['W', 'trimTail'], ['ArrowUp', 'prevEdit'], ['ArrowDown', 'nextEdit'], ['Home', 'seekStart'], ['End', 'seekEnd']]) {
    assert.equal(classifyShortcut({ key }).action, action, key);
    assert.equal(classifyShortcut({ key }).preventDefault, true, key);
    assert.equal(classifyShortcut({ key, ctrlKey: true }).action, 'none', `Ctrl+${key} stays with the browser`);
    assert.equal(classifyShortcut({ key, metaKey: true }).action, 'none', `Meta+${key}`);
    assert.equal(classifyShortcut({ key, altKey: true }).action, 'none', `Alt+${key}`);
  }
});

// ---- snap-target helpers ----------------------------------------------------

test('withoutPlayheadCandidate drops only the playhead entry, keeping an edge at the same time', () => {
  // [0, playhead, ...extra, segStart/segEnd...] as snapCandidates() builds it.
  assert.deepEqual(withoutPlayheadCandidate([0, 5, 9, 0, 4, 4, 7], 5), [0, 9, 0, 4, 4, 7]);
  // Playhead sitting on a clip edge: one 4 goes, the edge's own 4 stays.
  assert.deepEqual(withoutPlayheadCandidate([0, 4, 0, 4, 7], 4), [0, 0, 4, 7]);
  assert.deepEqual(withoutPlayheadCandidate([0, 4], 3), [0, 4]);
  assert.deepEqual(withoutPlayheadCandidate(undefined, 3), []);
});

test('freezePlayheadCandidate pins the playhead target to where the drag began', () => {
  assert.deepEqual(freezePlayheadCandidate([0, 8.9, 4, 9], 8.9, 2), [0, 2, 4, 9]);
  const same = [0, 2, 4];
  assert.equal(freezePlayheadCandidate(same, 2, 2), same, 'unchanged when the playhead has not moved');
  assert.equal(freezePlayheadCandidate(same, 3, 2), same, 'no live entry: nothing to swap');
  assert.equal(freezePlayheadCandidate(same, 2, undefined), same);
});

test('trimDragSeekTime: head shows the clip start, tail shows the last kept frame', () => {
  assert.equal(trimDragSeekTime('start', 4, 2.5), 4);
  near(trimDragSeekTime('end', 4, 2.5), 4 + 2.5 - FRAME);
  assert.equal(trimDragSeekTime('end', 4, 0), 4, 'never before the clip start');
});

// ---- wiring contracts (source) -----------------------------------------------

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

test('the shortcut hook maps the new actions to the trim commands and the navigation helper', () => {
  const hook = read('../hooks/useEditorShortcuts.js');
  assert.match(hook, /case 'trimHead': trimHeadAtPlayhead\?\.\(\)/);
  assert.match(hook, /case 'trimTail': trimTailAtPlayhead\?\.\(\)/);
  for (const action of ['prevEdit', 'nextEdit', 'seekStart', 'seekEnd']) assert.match(hook, new RegExp(`case '${action}'`));
  assert.match(hook, /editNavigationTarget\(/);
  // Typing in a field still wins: the editable-target guard runs before any action.
  assert.ok(hook.indexOf('isEditableTarget(e.target)') < hook.indexOf("case 'trimHead'"));
});

test('EditorShell hands the trim commands, segments and cues to the shortcut hook and onSeek to the commands', () => {
  const shell = read('../components/editor/EditorShell.jsx');
  assert.match(shell, /useEditorShortcuts\(\{[\s\S]*?trimHeadAtPlayhead,[\s\S]*?trimTailAtPlayhead,[\s\S]*?segments,[\s\S]*?cues: cuesList,/);
  assert.match(shell, /useEditorCommands\(\{[\s\S]*?onSeek: seekPlayer,/);
});

test('the trim commands are one set() call, notify on refusal and never touch history directly', () => {
  const commands = read('../hooks/useEditorCommands.js');
  const body = commands.match(/const trimEdgeAtPlayhead = useCallback\(([\s\S]*?)\n  \}, \[/);
  assert.ok(body, 'trimEdgeAtPlayhead exists');
  assert.equal((body[1].match(/\bset\(/g) || []).length, 1, 'one set() = one undo step');
  assert.match(body[1], /onNotify\?\.\(target\.message\)/);
  assert.doesNotMatch(body[1], /setSilent|beginDrag|endDrag/);
});

test('TimelineClip: trim drag shows the edge frame without adding undo entries or moving the snap target', () => {
  const src = read('../components/editor/TimelineClip.jsx');
  assert.match(src, /onSeek\?\.\(trimDragSeekTime\('start'/);
  assert.match(src, /onSeek\?\.\(trimDragSeekTime\('end'/);
  assert.match(src, /startPlayhead: playhead/);
  assert.match(src, /freezePlayheadCandidate\(snapCandidates, playhead, dragPlayhead\)/);
  // Up/Down no longer reorder (they are the editor-wide edit-point keys now); [ and ] still do.
  assert.doesNotMatch(src, /e\.key === 'ArrowUp'|e\.key === 'ArrowDown'/);
  assert.match(src, /e\.key === '\['/);
  assert.match(src, /e\.key === '\]'/);
});

test('TimelineClip: handles show on hover through a named group, absolutely positioned (no layout shift)', () => {
  const src = read('../components/editor/TimelineClip.jsx');
  assert.match(src, /group\/clip absolute/);
  assert.match(src, /group-hover\/clip:opacity-80/);
  assert.match(src, /group-hover\/clip:pointer-events-auto/);
  assert.match(src, /isSelected \|\| width >= HOVER_HANDLE_MIN_WIDTH/);
});

test('scrub snapping: same snap function/targets as trimming, Shift bypasses, playhead target excluded', () => {
  const src = read('../hooks/useTimelineDrag.js');
  const body = src.match(/const scrubTimeFromEvent = \(e\) => \{([\s\S]*?)\n  \};/);
  assert.ok(body, 'scrubTimeFromEvent exists');
  assert.match(body[1], /!snapEnabled \|\| e\.shiftKey/);
  assert.match(body[1], /snapFunction\(rawT, withoutPlayheadCandidate\(snapPoints, playhead\)\)/);
  // Every scrub entry point (ruler + track area) goes through it; none seeks with the raw time.
  assert.equal((src.match(/onSeek\?\.\(timeFromEvent\(e\)\)/g) || []).length, 0);
  assert.equal((src.match(/onSeek\?\.\(scrubTimeFromEvent\(e\)\)/g) || []).length, 3);
});
