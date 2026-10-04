import test from 'node:test';
import assert from 'node:assert/strict';

import {
  editorStateToSavePayload,
  manifestToEditorState,
  normalizeVoiceEdit,
  serializeVoiceEdit,
} from './editorProjectState.js';
import { applyRipplePlan, planRippleRanges } from './rippleRange.js';

const STORED = {
  schema_version: 1,
  source: { path: 'projects/p1/voiceover.wav', size: 123456, mtime_ns: 1700000000000000000, duration: 31.2 },
  cuts: [
    { id: 'cut-1a', start: 4.0, end: 4.6, reason: 'manual' },
    { id: 'cut-2b', start: 10, end: 11, reason: 'silence' },
  ],
};

const manifest = (extra = {}) => ({
  clip_list: [{ source_path: 'a.mp4', trim_start: 0, trim_end: 5 }],
  cues: [{ start: 0, end: 2, text: 'ทดสอบ' }],
  micro_cues: [{ start: 0, end: 1, text: 'ทด' }],
  total_duration: 29.6,
  artifacts: { voice_audio: { path: 'projects/p1/voiceover.wav' } },
  ...extra,
});

test('loading: voice_edit becomes voiceEdit and the timeline voice is the post-cut length', () => {
  const loaded = manifestToEditorState(manifest({ voice_edit: STORED, voice_edit_stale: false }));
  assert.deepEqual(loaded.voiceEdit.source, STORED.source);
  assert.deepEqual(loaded.voiceEdit.cuts.map((c) => [c.id, c.start, c.end, c.reason]), [
    ['cut-1a', 4, 4.6, 'manual'],
    ['cut-2b', 10, 11, 'silence'],
  ]);
  assert.equal(loaded.voiceEditStale, false);
  assert.equal(loaded.voiceEditNotice, null);
  assert.ok(Math.abs(loaded.audioDuration - 29.6) < 1e-6, '31.2 - 0.6 - 1');
});

test('loading: no voice_edit -> null, nothing stale, audioDuration exactly as before', () => {
  const loaded = manifestToEditorState(manifest());
  assert.equal(loaded.voiceEdit, null);
  assert.equal(loaded.voiceEditStale, false);
  assert.equal(loaded.voiceEditNotice, null);
  assert.equal(loaded.audioDuration, 29.6);
  const withAudioDuration = manifestToEditorState(manifest({ audio_duration: 31.2 }));
  assert.equal(withAudioDuration.audioDuration, 31.2);
});

test('loading: a stale edit is kept for display but never shortens the voice; the notice is carried', () => {
  const notice = { kind: 'stale', reason: 'สร้างเสียงพากย์ใหม่แล้ว จุดตัดเสียงเดิมใช้ไม่ได้' };
  const loaded = manifestToEditorState(manifest({
    voice_edit: STORED, voice_edit_stale: true, voice_edit_notice: notice, total_duration: 31.2,
  }));
  assert.equal(loaded.voiceEditStale, true);
  assert.deepEqual(loaded.voiceEditNotice, notice);
  assert.equal(loaded.audioDuration, 31.2, 'cuts are not applied while stale');
  assert.ok(loaded.voiceEdit, 'the stored edit is still there');
});

test('loading: a dropped edit (server cleared it) shows its notice with no edit', () => {
  const loaded = manifestToEditorState(manifest({
    voice_edit_notice: { kind: 'dropped', reason: 'ล้างจุดตัด 2 จุด' },
  }));
  assert.equal(loaded.voiceEdit, null);
  assert.equal(loaded.voiceEditNotice.kind, 'dropped');
});

test('normalizeVoiceEdit: unusable shapes give null; ids and reasons are filled; cuts are normalized', () => {
  assert.equal(normalizeVoiceEdit(null), null);
  assert.equal(normalizeVoiceEdit('x'), null);
  assert.equal(normalizeVoiceEdit({ source: {}, cuts: [{ start: 1, end: 2 }] }), null, 'no duration');
  assert.equal(normalizeVoiceEdit({ source: { duration: 10 }, cuts: [] }), null, 'no cuts');
  assert.equal(normalizeVoiceEdit({ source: { duration: 10 }, cuts: [{ start: 1, end: 1.01 }] }), null, 'empty after snapping');
  const edit = normalizeVoiceEdit({
    schema_version: 7,
    source: { duration: '10' },
    cuts: [{ start: 3, end: 4 }, { id: 'dup', start: 1, end: 2 }, { id: 'dup', start: 2, end: 2.5 }, { id: '', start: 6, end: 7 }],
  });
  assert.equal(edit.schema_version, 1);
  assert.equal(edit.source.duration, 10);
  assert.deepEqual(edit.cuts.map((c) => [c.start, c.end]), [[1, 2.5], [3, 4], [6, 7]]);
  assert.equal(new Set(edit.cuts.map((c) => c.id)).size, edit.cuts.length, 'ids are unique');
  assert.ok(edit.cuts.every((c) => typeof c.id === 'string' && c.id && c.reason === 'manual'));
});

test('saving: voiceEdit omitted -> no key (server keeps what it has); null -> null (clears); object -> cuts + source', () => {
  const base = { clipList: [], cuesList: [], style: {} };
  assert.equal(Object.hasOwn(editorStateToSavePayload(base), 'voice_edit'), false);
  assert.equal(editorStateToSavePayload({ ...base, voiceEdit: null }).voice_edit, null);
  assert.equal(editorStateToSavePayload({ ...base, voiceEdit: { source: { duration: 5 }, cuts: [] } }).voice_edit, null);

  const loaded = manifestToEditorState(manifest({ voice_edit: STORED }));
  const payload = editorStateToSavePayload({ ...base, voiceEdit: loaded.voiceEdit });
  assert.deepEqual(payload.voice_edit, {
    schema_version: 1,
    source: STORED.source,
    cuts: STORED.cuts,
  });
});

test('saving: a brand-new edit sends only source.duration, never an invented path/size/mtime', () => {
  const payload = editorStateToSavePayload({
    clipList: [],
    cuesList: [],
    style: {},
    voiceEdit: { schema_version: 1, source: { duration: 31.2 }, cuts: [{ id: 'c1', start: 4, end: 4.6, reason: 'manual' }] },
  });
  assert.deepEqual(payload.voice_edit.source, { duration: 31.2 });
  assert.deepEqual(Object.keys(payload.voice_edit).sort(), ['cuts', 'schema_version', 'source']);
  assert.deepEqual(payload.voice_edit.cuts, [{ id: 'c1', start: 4, end: 4.6, reason: 'manual' }]);
});

test('round trip: manifest -> editor state -> save payload -> manifest gives the same voiceEdit', () => {
  const first = manifestToEditorState(manifest({ voice_edit: STORED }));
  const payload = editorStateToSavePayload({
    clipList: first.clipList,
    cuesList: first.cuesList,
    microCuesList: first.microCuesList,
    style: first.style,
    voiceEdit: first.voiceEdit,
  });
  const second = manifestToEditorState({ ...manifest(), voice_edit: payload.voice_edit });
  assert.deepEqual(second.voiceEdit, first.voiceEdit);
  assert.equal(second.audioDuration, first.audioDuration);
  assert.deepEqual(serializeVoiceEdit(second.voiceEdit), payload.voice_edit);
});

test('microCuesList stays as it was: saved as micro_cues, falling back to cues only when not passed', () => {
  const loaded = manifestToEditorState(manifest());
  assert.deepEqual(loaded.microCuesList, [{ start: 0, end: 1, text: 'ทด' }]);
  const saved = editorStateToSavePayload({
    clipList: loaded.clipList, cuesList: loaded.cuesList, microCuesList: loaded.microCuesList, style: loaded.style,
  });
  assert.deepEqual(saved.micro_cues, loaded.microCuesList);
  const fallback = editorStateToSavePayload({ clipList: loaded.clipList, cuesList: loaded.cuesList, style: loaded.style });
  assert.equal(fallback.micro_cues.length, loaded.cuesList.length);
});

test('a ripple survives save and load: cut cues, ripple_text_cut and word tracks come back as saved', () => {
  const loaded = manifestToEditorState({
    clip_list: [
      { source_path: 'a.mp4', trim_start: 0, trim_end: 5 },
      { source_path: 'b.mp4', trim_start: 0, trim_end: 5 },
    ],
    cues: [{
      start: 1,
      end: 9,
      text: 'one two three four',
      word_reveal: [
        { text: 'one', start: 1, end: 3 },
        { text: 'two', start: 3, end: 5 },
        { text: 'three', start: 5, end: 7 },
        { text: 'four', start: 7, end: 9 },
      ],
    }],
    micro_cues: [],
    total_duration: 10,
  }, { createClipId: (index) => `c${index}` });
  const durations = { c0: 5, c1: 5 };
  const plan = planRippleRanges(
    {
      clipList: loaded.clipList,
      cuesList: loaded.cuesList,
      microCuesList: loaded.microCuesList,
      overlays: loaded.overlays,
      stickers: loaded.stickers,
      effects: loaded.effects,
      voiceEdit: loaded.voiceEdit,
      voiceEditStale: loaded.voiceEditStale,
    },
    [{ start: 4, end: 6 }],
    { durations, hasVoice: true, audioDuration: loaded.audioDuration, newCutId: () => 'cut-r1' },
  );
  assert.equal(plan.blocked, null);
  const next = applyRipplePlan({ ...loaded }, plan);
  const payload = editorStateToSavePayload({ ...next, microCuesList: next.microCuesList });
  assert.equal(payload.voice_edit.cuts[0].start, 4);
  assert.equal(payload.voice_edit.cuts[0].end, 6);
  assert.equal(payload.cues[0].ripple_text_cut, true);

  const reloaded = manifestToEditorState({
    clip_list: payload.clip_list,
    transitions: payload.transitions,
    cues: payload.cues,
    micro_cues: payload.micro_cues,
    voice_edit: payload.voice_edit,
    total_duration: 8,
  });
  assert.equal(reloaded.cuesList[0].ripple_text_cut, true);
  assert.equal(reloaded.cuesList[0].end, 7);
  assert.deepEqual(reloaded.cuesList[0].word_reveal.map((w) => [w.text, w.start, w.end]), [
    ['one', 1, 3], ['two', 3, 4], ['three', 4, 5], ['four', 5, 7],
  ]);
  assert.equal(reloaded.voiceEdit.cuts[0].start, 4);
  assert.ok(Math.abs(reloaded.audioDuration - 8) < 1e-9, 'the timeline voice is now 2 s shorter');
});
