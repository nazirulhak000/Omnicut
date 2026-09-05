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
  const isRunning = !isDone && !isFailed && (statusStr === 'rendering' || statusStr === 'processing' || percent > 0 || statusStr === 'queued');

  const defaultMsg = isDone
    ? 'เรนเดอร์เสร็จสมบูรณ์'
    : isFailed
      ? (statusData.error || 'เกิดข้อผิดพลาดในการเรนเดอร์')
      : `กำลังเรนเดอร์ ${percent}%`;

  const message = statusData.message || statusData.step_label || defaultMsg;

  return {
    percent,
    message,
    isDone,
    isFailed,
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

  const videoUrl = result.video_url
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

export function saveActiveJob(projectName, jobId, storage = globalThis?.sessionStorage) {
  if (!projectName || !jobId || !storage) return;
  try {
    storage.setItem(`${STORAGE_PREFIX}${projectName}`, String(jobId));
  } catch (_) {
    // Ignore storage quota or access errors
  }
}

export function getActiveJob(projectName, storage = globalThis?.sessionStorage) {
  if (!projectName || !storage) return null;
  try {
    return storage.getItem(`${STORAGE_PREFIX}${projectName}`) || null;
  } catch (_) {
    return null;
  }
}

export function clearActiveJob(projectName, storage = globalThis?.sessionStorage) {
  if (!projectName || !storage) return;
  try {
    storage.removeItem(`${STORAGE_PREFIX}${projectName}`);
  } catch (_) {
    // Ignore errors
  }
}
