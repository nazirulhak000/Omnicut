// Pure lifecycle rules shared by the Extension list and its Node regression tests.
(function attachClipState(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.OmniCutClipState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  const ACTIVE_QUEUE_STATUSES = new Set(['planned', 'ready_for_extension', 'awaiting_post', 'failed']);

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
    return item?.angle_status === 'rendered' && item.is_latest !== false && !isPostedClip(item);
  }

  function buildExtensionClipList(exportsItems = [], queueItems = []) {
    const exportsList = Array.isArray(exportsItems) ? exportsItems : [];
    const queueList = Array.isArray(queueItems) ? queueItems : [];
    const postedKeys = new Set(exportsList.filter(isPostedClip).map(clipKey).filter(Boolean));
    const scheduled = queueList
      .filter((item) => ACTIVE_QUEUE_STATUSES.has(item?.status) && !isPostedClip(item) && !postedKeys.has(clipKey(item)))
      .map((item) => ({
        ...item,
        rel_path: item.rel_path || item.video_path,
        name: item.name || item.project_name || item.video_path,
        is_scheduled: true,
      }));
    const scheduledKeys = new Set(scheduled.map(clipKey).filter(Boolean));
    const unscheduled = exportsList
      .filter(isReadyToPost)
      .filter((item) => !scheduledKeys.has(clipKey(item)));
    return [...scheduled, ...unscheduled];
  }

  function getExtensionStatus(item) {
    return item?.is_scheduled
      ? { kind: 'scheduled', label: 'จัดเวลาโพสต์แล้ว' }
      : { kind: 'unscheduled', label: 'ตัดต่อเสร็จแล้ว แต่ยังไม่ได้จัดเวลา' };
  }

  return { buildExtensionClipList, clipKey, getExtensionStatus, isPostedClip, isReadyToPost };
});
