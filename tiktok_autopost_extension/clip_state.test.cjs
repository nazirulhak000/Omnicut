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
