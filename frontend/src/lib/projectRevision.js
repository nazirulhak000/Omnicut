// Revisions belong to the editor snapshot loaded by the user. A background
// GET must never silently advance them and authorize a stale snapshot save.
import { activeChannel } from './channelRuntime.js';
import { channelCacheKey } from './channelState.js';
const revisions = new Map();
export function rememberProjectRevision(name, revision, channelId = activeChannel()) {
  const key = channelCacheKey(channelId, name);
  if (typeof revision === 'string' && /^[0-9a-f]{64}$/.test(revision)) revisions.set(key, revision);
  else revisions.delete(key);
}
// Read-only: lets a caller notice that a save or load moved the revision while
// its own request was in flight. It cannot change what a save sends.
export function getProjectRevision(name, channelId = activeChannel()) {
  return revisions.get(channelCacheKey(channelId, name)) ?? null;
}
export function withProjectRevision(name, payload, channelId = activeChannel()) {
  const revision = getProjectRevision(name, channelId);
  return revision ? { ...payload, base_revision: revision } : payload;
}
