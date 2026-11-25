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

test('a clip whose slot passed says it needs a new time (a draft keeps being a draft)', () => {
  const overdueDraft = { is_scheduled: true, is_draft: true, publish_draft: true, needs_reschedule: true };
  const overduePlanned = { is_scheduled: true, needs_reschedule: true };
  assert.deepEqual(getExtensionStatus(overdueDraft), { kind: 'draft_overdue', label: 'แบบร่างเลยเวลา — ต้องจัดเวลาใหม่' });
  assert.deepEqual(getExtensionStatus(overduePlanned), { kind: 'overdue', label: 'เลยเวลา — ต้องจัดเวลาใหม่' });
  assert.equal(getExtensionStatus({ is_scheduled: true, is_draft: true, needs_reschedule: false }).kind, 'draft');
});

test('scheduled_on_platform exports are excluded from unscheduled and never shown in waiting to post', () => {
  const exportsItems = [
    { export_id: 'e-sched', rel_path: '04_Exports/Ready_to_post/sched.mp4', angle_status: 'rendered', is_latest: true },
    { export_id: 'e-flagged', rel_path: '04_Exports/Ready_to_post/flagged.mp4', angle_status: 'rendered', is_latest: true, scheduled_on_platform: true },
    { export_id: 'e-ready', rel_path: '04_Exports/Ready_to_post/ready.mp4', angle_status: 'rendered', is_latest: true },
  ];
  const queueItems = [
    { id: 'q-done', status: 'scheduled_on_platform', export_id: 'e-sched', video_path: '04_Exports/Ready_to_post/sched.mp4' },
    { id: 'q-plan', status: 'planned', export_id: 'e-plan', video_path: '04_Exports/Ready_to_post/plan.mp4' },
  ];
  assert.equal(isReadyToPost(exportsItems[1]), false, 'flagged scheduled_on_platform export is not ready to post');
  assert.equal(isReadyToPost(exportsItems[2]), true, 'normal rendered export is ready to post');

  const clips = buildExtensionClipList(exportsItems, queueItems);
  const byExportId = Object.fromEntries(clips.map((c) => [c.export_id, c]));
  assert.equal(byExportId['e-sched'], undefined, 'scheduled_on_platform queue clip must not leak into unscheduled');
  assert.equal(byExportId['e-flagged'], undefined, 'scheduled_on_platform flagged export must not leak into unscheduled');
  assert.ok(byExportId['e-ready'], 'unposted ready clip is listed');
  assert.ok(byExportId['e-plan'], 'planned queue clip is listed');
});

test('C7: sibling planned/failed rows stay hidden when another row for the same clip is posted or past scheduled_on_platform', () => {
  const pastSlot = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
  const clips = buildExtensionClipList([], [
    { id: 'q-posted', status: 'posted', export_id: 'e-a', video_path: '04_Exports/a.mp4' },
    { id: 'q-sib-plan', status: 'planned', export_id: 'e-a', video_path: '04_Exports/a.mp4' },
    { id: 'q-sib-fail', status: 'failed', export_id: 'e-a', video_path: '04_Exports/a.mp4' },
    { id: 'q-sched-past', status: 'scheduled_on_platform', export_id: 'e-b', video_path: '04_Exports/b.mp4', scheduled_at: pastSlot },
    { id: 'q-sib-b-plan', status: 'planned', export_id: 'e-b', video_path: '04_Exports/b.mp4' },
    { id: 'q-sib-b-fail', status: 'failed', export_id: 'e-b', video_path: '04_Exports/b.mp4' },
    { id: 'q-active', status: 'planned', export_id: 'e-c', video_path: '04_Exports/c.mp4' },
  ]);
  assert.deepEqual(clips.map((c) => c.id), ['q-active']);
});

test('C7: custom { now } still treats past scheduled_on_platform as consumed and sorts remaining clips chronologically', () => {
  const futureNow = Date.parse('2035-01-01T00:00:00+07:00');
  const clips = buildExtensionClipList([], [
    { id: 'q-consumed-past', status: 'scheduled_on_platform', export_id: 'e-old', video_path: 'old.mp4', scheduled_at: '2026-11-01T10:00+07:00' },
    { id: 'q-consumed-sib', status: 'planned', export_id: 'e-old', video_path: 'old.mp4', scheduled_at: '2035-01-02T10:00+07:00' },
    { id: 'q-late', status: 'planned', export_id: 'e-late', video_path: 'late.mp4', scheduled_at: '2035-01-03T12:00+07:00' },
    { id: 'q-early-fields', status: 'planned', export_id: 'e-early', video_path: 'early.mp4', schedule_date: '2035-01-02', schedule_time: '08:00' },
    { id: 'q-unslotted', status: 'planned', export_id: 'e-unslotted', video_path: 'unslotted.mp4' },
  ], { now: futureNow });
  assert.deepEqual(clips.map((c) => c.id), ['q-early-fields', 'q-late', 'q-unslotted']);
});

test('C7: buildExtensionClipList respects now option without resurfacing past scheduled siblings and sorts chronologically', () => {
  const fixedNow = Date.parse('2026-11-25T12:00:00+07:00');
  const clips = buildExtensionClipList(
    [{ export_id: 'e-past', rel_path: '04_Exports/past.mp4', angle_status: 'rendered', is_latest: true }],
    [
      { id: 'q-late', status: 'planned', export_id: 'e-late', video_path: '04_Exports/late.mp4', scheduled_at: '2026-11-26T15:00:00+07:00' },
      { id: 'q-unbounded', status: 'planned', export_id: 'e-unbounded', video_path: '04_Exports/unbounded.mp4' },
      { id: 'q-early', status: 'planned', export_id: 'e-early', video_path: '04_Exports/early.mp4', schedule_date: '2026-11-25', schedule_time: '18:00' },
      { id: 'q-past-sched', status: 'scheduled_on_platform', export_id: 'e-past', video_path: '04_Exports/past.mp4', scheduled_at: '2026-11-25T09:00:00+07:00' },
      { id: 'q-past-sib', status: 'planned', export_id: 'e-past', video_path: '04_Exports/past.mp4', scheduled_at: '2026-11-25T10:00:00+07:00' },
    ],
    { now: fixedNow }
  );
  assert.deepEqual(clips.map((c) => c.id), ['q-early', 'q-late', 'q-unbounded']);
});
