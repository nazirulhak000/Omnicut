// Pure lifecycle rules shared by the Extension list and its Node regression tests.
(function attachClipState(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.OmniCutClipState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  // draft_on_platform: saved as a draft on TikTok, waiting to be published from there (never re-uploaded)
  const ACTIVE_QUEUE_STATUSES = new Set(['planned', 'ready_for_extension', 'awaiting_post', 'failed', 'draft_on_platform']);

  function normalisePath(value) {
    return String(value || '').replace(/\\/g, '/').replace(/^\/+/, '').toLowerCase();
  }

  function clipKey(item) {
    if (item?.export_id) return `export:${String(item.export_id)}`;
    const explicit = normalisePath(item?.video_key);
    const path = explicit || normalisePath(item?.rel_path || item?.video_path || item?.path || item?.name);
    return path.split('/').pop() || '';
  }

  function isPostedClip(item) {
    // API exports include an explicit per-file boolean. It must win over the
    // angle-level status because one angle can have old and posted versions.
    if (typeof item?.is_posted === 'boolean') return item.is_posted;
    return item?.status === 'posted' || item?.angle_status === 'posted' || Boolean(item?.posted_at);
  }

  function isReadyToPost(item) {
    return (
      item?.angle_status === 'rendered' &&
      item.is_latest !== false &&
      !isPostedClip(item) &&
      !item?.scheduled_on_platform &&
      !item?.is_scheduled_on_platform
    );
  }

  function buildExtensionClipList(exportsItems = [], queueItems = []) {
    const exportsList = Array.isArray(exportsItems) ? exportsItems : [];
    const queueList = Array.isArray(queueItems) ? queueItems : [];
    const postedKeys = new Set(exportsList.filter(isPostedClip).map(clipKey).filter(Boolean));
    const consumedKeys = new Set([
      ...postedKeys,
      ...queueList
        .filter((item) => item?.status === 'scheduled_on_platform' || item?.status === 'posted')
        .map(clipKey)
        .filter(Boolean),
    ]);
    const scheduled = queueList
      .filter((item) => ACTIVE_QUEUE_STATUSES.has(item?.status) && !isPostedClip(item) && !consumedKeys.has(clipKey(item)))
      .map((item) => ({
        ...item,
        rel_path: item.rel_path || item.video_path,
        name: item.name || item.project_name || item.video_path,
        is_scheduled: true,
        ...(item.status === 'draft_on_platform' ? { is_draft: true, publish_draft: true, force_mode: 'schedule' } : {}),
      }));
    const scheduledKeys = new Set(scheduled.map(clipKey).filter(Boolean));
    const unscheduled = exportsList
      .filter(isReadyToPost)
      .filter((item) => !scheduledKeys.has(clipKey(item)) && !consumedKeys.has(clipKey(item)));
    return [...scheduled, ...unscheduled];
  }

  function getExtensionStatus(item) {
    // the slot passed (or is < 15 min away): the clip needs a new time before it can run; a draft stays a draft meanwhile
    if (item?.is_draft && item.needs_reschedule) return { kind: 'draft_overdue', label: 'แบบร่างเลยเวลา — ต้องจัดเวลาใหม่' };
    if (item?.needs_reschedule) return { kind: 'overdue', label: 'เลยเวลา — ต้องจัดเวลาใหม่' };
    if (item?.is_draft) return { kind: 'draft', label: 'แบบร่างบน TikTok รอเผยแพร่' };
    return item?.is_scheduled
      ? { kind: 'scheduled', label: 'จัดเวลาโพสต์แล้ว' }
      : { kind: 'unscheduled', label: 'ตัดต่อเสร็จแล้ว แต่ยังไม่ได้จัดเวลา' };
  }

  // Which clips a batch run starts from. If the operator ticked anything the run is "exactly these", even when none of
  // them is usable any more (a slot passed, the mode changed): the caller then stops. It must never fall back to the
  // whole queue, which used to post clips nobody picked.
  function pickBatchCandidates({ allClips = [], selectedKeys = new Set(), keyOf = clipKey, matchesQuery = () => true } = {}) {
    const ticked = allClips.filter((clip) => selectedKeys.has(keyOf(clip)));
    if (ticked.length) return { usingPicked: true, candidates: ticked };
    return { usingPicked: false, candidates: allClips.filter(matchesQuery) };
  }

  return { buildExtensionClipList, clipKey, getExtensionStatus, isPostedClip, isReadyToPost, pickBatchCandidates };
});
