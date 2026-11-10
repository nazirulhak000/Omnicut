const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildExtensionClipList,
  getExtensionStatus,
  isPostedClip,
  isReadyToPost,
} = require('./clip_state.js');

test('includes rendered exports without a schedule and explains the missing schedule', () => {
  const clips = buildExtensionClipList([
    {
      name: 'unscheduled.mp4',
      rel_path: '04_Exports/Ready_to_post/unscheduled.mp4',
      angle_status: 'rendered',
      is_latest: true,
    },
  ], []);

  assert.equal(clips.length, 1);
  assert.deepEqual(getExtensionStatus(clips[0]), {
    kind: 'unscheduled',
    label: 'ตัดต่อเสร็จแล้ว แต่ยังไม่ได้จัดเวลา',
  });
});

test('never exposes a posted export, including stale queue rows', () => {
  const posted = {
    name: 'posted.mp4',
    rel_path: '04_Exports/Posted/posted.mp4',
    angle_status: 'rendered',
    is_posted: true,
    is_latest: true,
  };
  assert.equal(isPostedClip(posted), true);
  assert.equal(isReadyToPost(posted), false);

  const clips = buildExtensionClipList([posted], [{
    id: 'queue-1',
    video_path: '04_Exports/Ready_to_post/posted.mp4',
    video_key: '04_exports/posted.mp4',
    status: 'ready_for_extension',
  }]);
  assert.deepEqual(clips, []);
});

test('keeps a scheduled clip once and labels its committed schedule', () => {
  const clips = buildExtensionClipList([
    {
      name: 'scheduled.mp4',
      rel_path: '04_Exports/Ready_to_post/scheduled.mp4',
      angle_status: 'rendered',
      is_latest: true,
    },
  ], [{
    id: 'queue-1',
    video_path: '04_Exports/Ready_to_post/scheduled.mp4',
    scheduled_at: '2026-09-08T21:30:00+07:00',
    status: 'planned',
  }]);

  assert.equal(clips.length, 1);
  assert.equal(clips[0].is_scheduled, true);
  assert.equal(getExtensionStatus(clips[0]).kind, 'scheduled');
});

test('uses export_id so same filenames from different exports do not collapse', () => {
  const clips = buildExtensionClipList(
    [{
      export_id: 'exp-posted',
      rel_path: '04_Exports/Posted/shared.mp4',
      is_posted: true,
    }],
    [{
      export_id: 'exp-ready',
      video_path: '04_Exports/Ready_to_post/shared.mp4',
      status: 'planned',
    }],
  );

  assert.equal(clips.length, 1);
  assert.equal(clips[0].export_id, 'exp-ready');
});

test('R1 pickBatchCandidates: ticked clips mean "exactly these", even when none is usable; never the whole queue', () => {
  const { pickBatchCandidates } = require('./clip_state.js');
  const allClips = [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }, { id: 'c', name: 'C' }];
  const keyOf = (clip) => clip.id;
  const none = pickBatchCandidates({ allClips, selectedKeys: new Set(), keyOf });
  assert.equal(none.usingPicked, false);
  assert.equal(none.candidates.length, 3);
  const filtered = pickBatchCandidates({ allClips, selectedKeys: new Set(), keyOf, matchesQuery: (clip) => clip.name === 'B' });
  assert.deepEqual(filtered.candidates.map(keyOf), ['b']);
  const two = pickBatchCandidates({ allClips, selectedKeys: new Set(['c', 'a']), keyOf });
  assert.equal(two.usingPicked, true);
  assert.deepEqual(two.candidates.map(keyOf), ['a', 'c']);                // list order, not tick order
  // the search box does not widen a ticked selection
  const withQuery = pickBatchCandidates({ allClips, selectedKeys: new Set(['a']), keyOf, matchesQuery: () => true });
  assert.deepEqual(withQuery.candidates.map(keyOf), ['a']);
  // a tick for a clip that is gone selects nothing, so the run is NOT "ticked" and the caller sees the plain list
  const gone = pickBatchCandidates({ allClips, selectedKeys: new Set(['zzz']), keyOf });
  assert.equal(gone.usingPicked, false);
});

test('a queue row saved as a draft on TikTok becomes a draft clip (publish_draft, schedule slot, own status label)', () => {
  const clips = buildExtensionClipList([], [
    { id: 'q-draft', status: 'draft_on_platform', export_id: 'e1', video_path: 'a.mp4', scheduled_at: '2030-01-02T09:00+07:00' },
    { id: 'q-plan', status: 'planned', export_id: 'e2', video_path: 'b.mp4' },
    { id: 'q-done', status: 'scheduled_on_platform', export_id: 'e3', video_path: 'c.mp4' },
  ]);
  const byId = Object.fromEntries(clips.map((c) => [c.id, c]));
  assert.ok(byId['q-draft'].is_draft && byId['q-draft'].publish_draft);
  assert.equal(byId['q-draft'].force_mode, 'schedule');
  assert.deepEqual(getExtensionStatus(byId['q-draft']), { kind: 'draft', label: 'แบบร่างบน TikTok รอเผยแพร่' });
  assert.ok(!byId['q-plan'].is_draft && !byId['q-plan'].publish_draft);
  assert.equal(byId['q-done'], undefined, 'rows TikTok already scheduled are not listed');
});
