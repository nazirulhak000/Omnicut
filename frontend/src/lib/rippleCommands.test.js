import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import { useEditorCommands } from '../hooks/useEditorCommands.js';
import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';
import { describeRipplePlan } from './rippleRange.js';

// The ripple commands of useEditorCommands, driven through a real hook call
// (server render) against a real history model: ONE set() per ripple, the
// playhead moves, the selection is cleared, a refusal says why.

const DURATIONS = { a: 10, b: 10, c: 10 };

const initialState = () => ({
  clipList: [
    { id: 'a', source_path: 'a.mp4', trim_start: 0, trim_end: 5 },
    { id: 'b', source_path: 'b.mp4', trim_start: 0, trim_end: 5 },
    { id: 'c', source_path: 'c.mp4', trim_start: 0, trim_end: 5 },
  ],
  cuesList: [
    { start: 1, end: 2, text: 'before', _uid: 'u1' },
    { start: 10, end: 12, text: 'after', _uid: 'u2' },
  ],
  microCuesList: [{ start: 10, end: 11, text: 'micro' }],
  overlays: [],
  stickers: [],
  effects: [],
  spotlight: null,
  backgroundIsolation: null,
  trackMix: { mute: {}, solo: {} },
  style: { bgmName: 'upbeat' },
  voiceEdit: null,
  voiceEditStale: false,
  voiceEditNotice: null,
});

function mountCommands(overrides = {}) {
  const model = createEditorHistoryModel(initialState());
  const calls = { setCount: 0, seek: [], selection: [], notify: [], dirty: 0 };
  const cuesDirtyRef = { get current() { return calls.dirty > 0; }, set current(value) { if (value) calls.dirty += 1; } };
  let ids = 0;
  let api;
  function Probe() {
    api = useEditorCommands({
      set: (updater, options) => { calls.setCount += 1; return model.set(updater, options); },
      newId: () => `new-${++ids}`,
      durations: DURATIONS,
      setSelection: (value) => calls.selection.push(value),
      cuesDirtyRef,
      onNotify: (message) => calls.notify.push(message),
      onSeek: (time) => calls.seek.push(time),
      editorState: model.getState(),
      hasVoice: true,
      audioDuration: 15,
      ...overrides,
    });
    return null;
  }
  renderToStaticMarkup(React.createElement(Probe));
  return { api, model, calls };
}

test('defaultRippleScope follows the voiceover', () => {
  const { api } = mountCommands();
  assert.equal(api.defaultRippleScope(), 'all');
  assert.equal(api.defaultRippleScope(false), 'video');
  const noVoice = mountCommands({ hasVoice: false });
  assert.equal(noVoice.api.defaultRippleScope(), 'video');
});

test('planRipple is a dry run: it changes nothing and carries the dialog numbers', () => {
  const { api, model, calls } = mountCommands();
  const before = model.getState();
  const plan = api.planRipple([{ start: 6, end: 8 }]);
  assert.equal(plan.blocked, null);
  assert.equal(plan.scope, 'all', 'voiceover present -> default scope all');
  assert.equal(model.getState(), before);
  assert.equal(calls.setCount, 0);
  assert.match(describeRipplePlan(plan).summary, /เสียงพากย์สั้นลง 2\.00 วินาที/);
});

test('rippleDeleteRange applies in ONE set(): picture, voice cuts and captions together, one undo', () => {
  const { api, model, calls } = mountCommands();
  const before = model.getState();
  const plan = api.rippleDeleteRange({ t0: 6, t1: 8 });
  assert.equal(calls.setCount, 1, 'exactly one history set()');
  assert.equal(plan.changed, true);
  const after = model.getState();
  assert.equal(after.clipList.length, 4);
  assert.deepEqual(after.voiceEdit.cuts.map((c) => [c.start, c.end]), [[6, 8]]);
  assert.deepEqual(after.voiceEdit.source, { duration: 15 });
  assert.equal(after.cuesList[1].start, 8, 'later caption pulled in by 2 s');
  assert.equal(after.cuesList[0], before.cuesList[0]);
  assert.equal(after.microCuesList[0].start, 8, 'micro cues are part of the same step');
  assert.equal(after.style, before.style, 'BGM / style untouched');
  assert.deepEqual(calls.seek, [6], 'playhead goes to the cut');
  assert.deepEqual(calls.selection, [null], 'selection cleared');
  assert.ok(calls.dirty > 0, 'captions changed -> subtitles are re-rendered');

  assert.equal(model.undo(), true);
  assert.equal(model.getState(), before, 'ONE Ctrl+Z restores everything');
  assert.equal(model.canUndo(), false);
});

test('rippleDeleteRange with scope video touches the clips only and leaves captions and voice alone', () => {
  const { api, model, calls } = mountCommands();
  const before = model.getState();
  api.rippleDeleteRange({ t0: 6, t1: 8, scope: 'video' });
  const after = model.getState();
  assert.equal(after.clipList.length, 4);
  assert.equal(after.cuesList, before.cuesList);
  assert.equal(after.microCuesList, before.microCuesList);
  assert.equal(after.voiceEdit, null);
  assert.equal(calls.dirty, 0);
});

test('rippleRanges: several ranges in one step (the silence button will use this)', () => {
  const { api, model, calls } = mountCommands();
  const plan = api.rippleRanges([{ start: 1, end: 2 }, { start: 8, end: 9 }], 'all', { reason: 'silence' });
  assert.equal(calls.setCount, 1);
  assert.equal(plan.reason, 'silence');
  assert.deepEqual(
    model.getState().voiceEdit.cuts.map((c) => [c.start, c.end, c.reason]),
    [[1, 2, 'silence'], [8, 9, 'silence']],
  );
  assert.deepEqual(calls.seek, [1]);
  assert.equal(model.undo(), true);
  assert.equal(model.canUndo(), false);
});

test('a refused ripple changes nothing, tells the user why and does not move anything', () => {
  const { api, model, calls } = mountCommands();
  const before = model.getState();
  const plan = api.rippleDeleteRange({ t0: 0, t1: 15 });
  assert.equal(plan.blocked, 'ตัดแล้วจะไม่เหลือคลิปเลย');
  assert.equal(model.getState(), before);
  assert.deepEqual(calls.notify, ['ตัดแล้วจะไม่เหลือคลิปเลย']);
  assert.deepEqual(calls.seek, []);
  assert.deepEqual(calls.selection, []);
  assert.equal(model.canUndo(), false);
});

test('the plan is made against the NEWEST state, not the one the dialog saw', () => {
  const { api, model } = mountCommands();
  const dialogPlan = api.planRipple([{ start: 6, end: 8 }]);
  // the user keeps editing while the dialog is open
  model.set((prev) => ({ ...prev, cuesList: [...prev.cuesList, { start: 13, end: 14, text: 'late', _uid: 'u3' }] }));
  api.rippleDeleteRange({ t0: 6, t1: 8 });
  const after = model.getState();
  assert.equal(after.cuesList.find((c) => c._uid === 'u3').start, 11, 'the late caption was shifted too');
  assert.equal(dialogPlan.state.cuesList.find((c) => c._uid === 'u3'), undefined);
});
