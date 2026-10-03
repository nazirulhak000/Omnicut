// Decides what the editor does with the server's project revision after a
// render. The render pipeline rewrites the manifest (clip list, artifacts,
// fingerprints), so the server revision moves while the browser still holds
// the one it loaded. projectRevision.js guards saves with that revision so a
// stale editor can never overwrite newer work; this module only decides when
// the editor may legitimately catch up, and never loosens that guard.

const REVISION_PATTERN = /^[0-9a-f]{64}$/;

export function isProjectRevision(value) {
  return typeof value === 'string' && REVISION_PATTERN.test(value);
}

// JSON with object keys sorted, so two payloads built from the same data but
// in a different key order compare equal. Arrays keep their order.
export function stableStringify(value) {
  return JSON.stringify(sortKeys(value));
}

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((out, key) => {
      if (value[key] !== undefined) out[key] = sortKeys(value[key]);
      return out;
    }, {});
  }
  return value;
}

export const POST_RENDER_ACTIONS = Object.freeze({
  SKIP: 'skip', // nothing trustworthy to act on; keep the remembered revision
  NOOP: 'noop', // already in sync
  REMEMBER: 'remember', // adopt the server revision; editor content is identical
  RELOAD: 'reload', // server changed editor-owned fields; load them into the editor
  NOTIFY: 'notify', // the user has unsaved edits; ask before anything is replaced
});

/**
 * @param {object} input
 * @param {boolean} input.fetchOk         the project GET succeeded
 * @param {object} input.manifest         the manifest the GET returned
 * @param {string} input.projectName      project the editor shows now
 * @param {string} input.targetProject    project the render belonged to
 * @param {string|null} input.revisionAtStart remembered revision when the GET started
 * @param {string|null} input.revisionNow     remembered revision now
 * @param {boolean} input.editorClean     no unsaved, queued or in-flight edits
 * @param {object} input.currentPayload   the editor's save payload now
 * @param {Function} input.toPayload      manifest -> save payload (same shape)
 * @param {boolean} [input.allowReload=true] false turns RELOAD into NOTIFY
 */
export function decidePostRenderSync({
  fetchOk,
  manifest,
  projectName,
  targetProject,
  revisionAtStart,
  revisionNow,
  editorClean,
  currentPayload,
  toPayload,
  allowReload = true,
} = {}) {
  const { SKIP, NOOP, REMEMBER, RELOAD, NOTIFY } = POST_RENDER_ACTIONS;
  if (!fetchOk || !manifest || typeof manifest !== 'object') return { action: SKIP, reason: 'fetch_failed' };
  if (!projectName || projectName !== targetProject) return { action: SKIP, reason: 'project_switched' };
  const fetched = manifest._editor_revision;
  if (!isProjectRevision(fetched)) return { action: SKIP, reason: 'invalid_revision' };
  // A save or a load landed while the GET was in flight. Its revision is newer
  // than (or unrelated to) this response, so this response must not replace it.
  if ((revisionAtStart ?? null) !== (revisionNow ?? null)) return { action: SKIP, reason: 'stale_response' };
  if (fetched === revisionNow) return { action: NOOP, reason: 'in_sync' };
  if (!editorClean) return { action: NOTIFY, reason: 'unsaved_edits' };

  let serverKey;
  let currentKey;
  try {
    serverKey = stableStringify(toPayload(manifest));
    currentKey = stableStringify(currentPayload);
  } catch {
    return { action: SKIP, reason: 'payload_unreadable' };
  }
  if (serverKey === currentKey) return { action: REMEMBER, reason: 'content_unchanged', revision: fetched };
  return allowReload
    ? { action: RELOAD, reason: 'content_changed', revision: fetched }
    : { action: NOTIFY, reason: 'content_changed' };
}

/**
 * The job is reported done a moment before its last manifest write, so one
 * read can see a revision that is about to change. Read until two reads in a
 * row agree. Returns the manifest, or null when no stable read was seen.
 */
export async function fetchSettledProject(fetchProject, { attempts = 4, delayMs = 1200, wait } = {}) {
  const pause = wait || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  let previous = null;
  for (let i = 0; i < attempts; i += 1) {
    if (i > 0) await pause(delayMs);
    let manifest;
    try {
      manifest = await fetchProject();
    } catch {
      return null;
    }
    const revision = manifest?._editor_revision;
    if (!isProjectRevision(revision)) return null;
    if (previous && previous._editor_revision === revision) return manifest;
    previous = manifest;
  }
  return null;
}
