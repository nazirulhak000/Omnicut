/**
 * Pure functions and storage helpers for OmniCut render jobs and polling.
 */

const STORAGE_PREFIX = 'omnicut_active_render_';

export function calculateJobProgress(statusData) {
  if (!statusData) {
    return {
      percent: 0,
      message: '',
      isDone: false,
      isFailed: false,
      isCancelled: false,
      isCancelling: false,
      isRunning: false,
    };
  }

  const rawProgress = typeof statusData.progress === 'number'
    ? statusData.progress
    : (statusData.status === 'completed' || statusData.status === 'done' ? 1.0 : 0);

  const percent = Math.max(0, Math.min(100, Math.round(rawProgress * 100)));
  const statusStr = String(statusData.status || '').toLowerCase();
  const isDone = statusStr === 'done' || statusStr === 'completed';
  const isFailed = statusStr === 'failed' || statusStr === 'error';
  // "cancelling" is the transient state between a cancel request and the
  // worker thread actually unwinding -- still in flight, so it counts as
  // running (the poller keeps polling). "cancelled" is the real terminal
  // state once the worker has stopped -- distinct from isFailed so callers
  // can show "cancelled by you" instead of an error message.
  const isCancelling = statusStr === 'cancelling';
  const isCancelled = statusStr === 'cancelled';
  const isRunning = !isDone && !isFailed && !isCancelled
    && (statusStr === 'rendering' || statusStr === 'processing' || statusStr === 'queued' || isCancelling || percent > 0);

  const defaultMsg = isDone
    ? 'เรนเดอร์เสร็จสมบูรณ์'
    : isCancelled
      ? 'ยกเลิกงานแล้ว'
      : isCancelling
        ? 'กำลังยกเลิกงาน...'
        : isFailed
          ? (statusData.error || 'เกิดข้อผิดพลาดในการเรนเดอร์')
          : `กำลังเรนเดอร์ ${percent}%`;

  const message = statusData.message || statusData.step_label || defaultMsg;

  return {
    percent,
    message,
    isDone,
    isFailed,
    isCancelled,
    isCancelling,
    isRunning,
  };
}

export function normalizeJobResult(result) {
  if (!result || typeof result !== 'object') {
    return {
      videoUrl: null,
      videoPath: null,
      raw: {},
    };
  }

  const videoPath = result.mp4
    || result.final_video_path
    || result.video_path
    || result.mp4_video
    || null;

  // mp4_url is the servable "/api/media/..." URL that render_jobs.py's
  // complete_job() actually populates on the backend; video_url and the
  // "starts with http" check on videoPath are kept as fallbacks for older
  // or differently-shaped job results that don't carry mp4_url.
  const videoUrl = result.mp4_url
    || result.video_url
    || (videoPath && typeof videoPath === 'string' && videoPath.startsWith('http') ? videoPath : null);

  return {
    videoUrl,
    videoPath,
    raw: result,
  };
}

export function formatJobError(err) {
  if (!err) return 'เกิดข้อผิดพลาดในการประมวลผล';
  if (typeof err === 'string') return err;
  const detail = err.response?.data?.detail ?? err.detail ?? err.message ?? err.error;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === 'object' ? (d.msg || JSON.stringify(d)) : String(d))).join(', ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(err.message || 'เกิดข้อผิดพลาดในการประมวลผล');
}

// A render job is tracked by the backend's job_id (a stable uuid4, known at
// saveActiveJob time), not by the project's display name/label. The label
// (project name / product name, built from a caller-supplied fallback chain
// that can even collapse to the literal 'วิดีโอ' when nothing else is given)
// is only ever a UI string -- it can be computed differently by different
// callers, or differ between when a render starts and when the user
// navigates back to check on it. Keying storage by that string meant a
// mismatch silently orphaned the entry (lookup finds nothing, render looks
// "gone" though it is still running server-side), or -- when two renders
// both fell back to the same label ('วิดีโอ') -- clobbered each other.
//
// There is at most one active render per browser tab (EditorShell's
// useRenderJob and NewClipPanel's are never mounted at the same time --
// NewClipPanel only renders in place of the editor before a project exists),
// so the job entry lives under a single well-known key, not one keyed per
// project. The project label is stored as a payload field on that entry for
// display/diagnostics (and back-compat filtering, see getActiveJob), never
// as part of the storage key -- exactly the mismatch that caused the bug.
//
// Storage shape: `${STORAGE_PREFIX}job` -> JSON { jobId, projectKey }
//
// Entries written by the old per-project scheme
// (`${STORAGE_PREFIX}${projectName}` -> raw jobId string) live under a key
// shape this code never writes or reads, so they are simply invisible to
// the new code -- never a parse/read crash, just an inert leftover.
//
// Backing store: localStorage, not sessionStorage. sessionStorage is scoped
// per-tab, so a render started in one tab was invisible to a second tab on
// the same project, and closing (not just navigating away from) the tab
// that started a still-running render wiped the entry entirely -- the
// render would keep going server-side with zero UI trace of it. localStorage
// is shared across tabs of the same origin and survives tab close, so both
// gaps close without changing the key name or JSON shape.
const JOB_ENTRY_KEY = `${STORAGE_PREFIX}job`;

function readJobEntry(storage) {
  try {
    const raw = storage.getItem(JOB_ENTRY_KEY);
    if (!raw) return null;
    // JSON.parse throwing (a foreign value, or a stale entry from before
    // this field existed) is caught by the same handler below -- ignore
    // rather than throw or return garbage.
    const entry = JSON.parse(raw);
    if (!entry || typeof entry !== 'object' || !entry.jobId) return null;
    return entry;
  } catch (_) {
    return null;
  }
}

/**
 * Persist the currently in-flight render job for this tab.
 * @param {string|null} projectKey Display label of the project the job belongs
 *   to, stored alongside the job purely so a later getActiveJob(projectKey)
 *   call can tell whether the stored job is for that project. Not part of
 *   the storage key.
 * @param {string} jobId Stable backend job id (uuid4).
 */
export function saveActiveJob(projectKey, jobId, storage = globalThis?.localStorage) {
  if (!jobId || !storage) return;
  try {
    storage.setItem(JOB_ENTRY_KEY, JSON.stringify({ jobId: String(jobId), projectKey: projectKey || null }));
  } catch (_) {
    // Ignore storage quota or access errors
  }
}

/**
 * Look up the in-flight render job for this tab, if any.
 *
 * `projectKey` is accepted for call-site symmetry with saveActiveJob (and so
 * existing callers/tests that pass a project label keep working), but it is
 * intentionally NOT used to reject a match: since a tab has at most one
 * active render job, and the label a job was saved under can legitimately
 * differ from the label the project is looked up by later (a display string
 * recomputed by a different caller, or the project simply shown under its
 * canonical name once it exists on disk), gating on label equality is
 * exactly the bug this rewrite fixes. If the stored job's own projectKey is
 * known, it is returned on the side (see getActiveJobEntry) for callers that
 * want to double check or display it, but getActiveJob itself always
 * surfaces whatever job this tab has in flight.
 */
export function getActiveJob(_projectKey, storage = globalThis?.localStorage) {
  if (!storage) return null;
  const entry = readJobEntry(storage);
  return entry ? entry.jobId : null;
}

/**
 * Like getActiveJob, but returns the full stored entry ({ jobId, projectKey })
 * instead of just the job id, for callers that want the saved label too.
 */
export function getActiveJobEntry(storage = globalThis?.localStorage) {
  if (!storage) return null;
  return readJobEntry(storage);
}

export function clearActiveJob(projectKey, storage = globalThis?.localStorage) {
  if (!storage) return;
  try {
    storage.removeItem(JOB_ENTRY_KEY);
  } catch (_) {
    // Ignore errors
  }
}
