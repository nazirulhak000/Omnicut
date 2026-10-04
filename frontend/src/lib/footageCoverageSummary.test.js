import test from 'node:test';
import assert from 'node:assert/strict';
import { footageCoverageSummary } from './footageCoverageSummary.js';
import { manifestToEditorState, editorStateToSavePayload } from './editorProjectState.js';

test('coverage notice reports actual automatic holds and ignores manual freeze tails', () => {
  const shortage = { reason: 'source_window_exhausted', missing_seconds: 99 };
  assert.deepEqual(footageCoverageSummary([{ freeze_tail: 2, footage_shortage: shortage },
    { freeze_tail: 1.5, footage_shortage: shortage }, { freeze_tail: 7 }]), { count: 2, seconds: 3.5 });
  assert.deepEqual(footageCoverageSummary([{ freeze_tail: 0, footage_shortage: shortage }]), { count: 0, seconds: 0 });
});

test('source window and shortage metadata survive editor load/save', () => {
  const clip = { source_path: 'raw.mp4', trim_start: 2, trim_end: 4, speed: 1,
    freeze_tail: 6, source_window: { start: 2, end: 4 },
    footage_shortage: { reason: 'source_window_exhausted', missing_seconds: 6 } };
  const state = manifestToEditorState({ clip_list: [clip] });
  const saved = editorStateToSavePayload(state);
  assert.deepEqual(saved.clip_list[0].source_window, clip.source_window);
  assert.deepEqual(saved.clip_list[0].footage_shortage, clip.footage_shortage);
  assert.equal(saved.clip_list[0].freeze_tail, 6);
});
