// Revisions belong to the editor snapshot loaded by the user. A background
// GET must never silently advance them and authorize a stale snapshot save.
const revisions = new Map();
export function rememberProjectRevision(name, revision) {
  if (typeof revision === 'string' && /^[0-9a-f]{64}$/.test(revision)) revisions.set(name, revision);
  else revisions.delete(name);
}
// Read-only: lets a caller notice that a save or load moved the revision while
// its own request was in flight. It cannot change what a save sends.
export function getProjectRevision(name) {
  return revisions.get(name) ?? null;
}
export function withProjectRevision(name, payload) {
  const revision = revisions.get(name);
  return revision ? { ...payload, base_revision: revision } : payload;
}
