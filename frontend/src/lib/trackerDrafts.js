const cacheKey = 'tracker.manualDrafts';
export function trackerDraftKey(kind, item) {
  return `${kind}:${item?.export_id || `${item?.parentProduct?.id || ''}:${item?.angle_id || item?.id || ''}`}`;
}
function readAll(storage) {
  try { const data = JSON.parse(storage.getItem(cacheKey) || '{}'); return data && Object.getPrototypeOf(data) === Object.prototype ? data : {}; }
  catch { return {}; }
}
export function readTrackerDraft(storage, kind, item) {
  return readAll(storage)[trackerDraftKey(kind, item)] || null;
}
export function writeTrackerDraft(storage, kind, item, draft) {
  storage.setItem(cacheKey, JSON.stringify({ ...readAll(storage), [trackerDraftKey(kind, item)]: draft }));
}
export function clearTrackerDraft(storage, kind, item) {
  const data = readAll(storage); delete data[trackerDraftKey(kind, item)];
  storage.setItem(cacheKey, JSON.stringify(data));
}
