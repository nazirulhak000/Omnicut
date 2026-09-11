import axios from 'axios';
import { sanitizeText, sanitizeScript } from './lib/sanitize.js';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // 60 seconds default
});

// ── Request Interceptor: attach shared-secret API key when configured ──
// Mirrors scripts/auth.py's OMNICUT_API_KEY gate (checked via X-API-Key).
// The gate is permissive when the backend has no key configured, so we only
// send the header when a value is present -- that keeps today's unset-key
// setup working unchanged. See frontend/.env.example for the env var and
// the bundle-visibility caveat (this value ships inside the built JS).
// `import.meta.env` only exists under Vite; the lib tests import modules
// that reach this file through plain `node --test`, where it is undefined.
const API_KEY = import.meta.env?.VITE_API_KEY;
api.interceptors.request.use((config) => {
  if (API_KEY) {
    config.headers['X-API-Key'] = API_KEY;
  }
  return config;
});

// ── Response Error Interceptor for Clean, Actionable Error Messages ──
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let friendlyMessage = 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์';

    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      friendlyMessage = 'การเชื่อมต่อใช้เวลานานเกินกำหนด (Network Timeout) กรุณาตรวจสอบและลองใหม่อีกครั้ง';
    } else if (error.code === 'ERR_NETWORK' || !error.response) {
      friendlyMessage = 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ CapCut Backend ได้ กรุณาตรวจสอบว่าเซิร์ฟเวอร์ทำงานอยู่';
    } else if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || error.response.data?.message;

      if (status === 413) {
        friendlyMessage = 'ไฟล์ที่อัปโหลดมีขนาดใหญ่เกินกว่าที่เซิร์ฟเวอร์รองรับ';
      } else if (status === 404) {
        friendlyMessage = detail || 'ไม่พบข้อมูลที่ร้องขอในระบบ';
      } else if (status === 422) {
        friendlyMessage = detail || 'ข้อมูลที่ส่งไปไม่ถูกต้องตามรูปแบบที่กำหนด';
      } else if (status >= 500) {
        friendlyMessage = `เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์ (${status}): ${detail || 'Internal Server Error'}`;
      } else if (detail) {
        friendlyMessage = detail;
      }
    }

    // Attach friendly message to the error object for easy display in components
    error.friendlyMessage = friendlyMessage;
    return Promise.reject(error);
  }
);

export const getSystemStatus = () => api.get('/status').then(r => r.data);
export const getRawVideos = (productId = null) => api.get('/videos', { params: productId ? { product_id: productId } : {} }).then(r => r.data);
export const attachVideoToProduct = (productId, videoPath) => api.post(`/products/${productId}/videos`, { video_path: videoPath }).then(r => r.data);
export const removeVideoFromProduct = (productId, videoPath) => api.delete(`/products/${productId}/videos`, { params: { video_path: videoPath } }).then(r => r.data);
export const renameVideo = (videoPath, newName, productId = null) => api.post('/videos/rename', { video_path: videoPath, new_name: newName, product_id: productId }).then(r => r.data);
export const getRawVault = () => api.get('/raw-vault').then(r => r.data);
export const reassignRawVideo = (payload) => api.post('/raw-vault/reassign', payload).then(r => r.data);
export const batchDeleteRawVideos = (videoPaths) => api.post('/raw-vault/batch-delete', { video_paths: videoPaths }).then(r => r.data);
export const getExports = () => api.get('/exports').then(r => r.data);
export const getExportMediaInfo = (path) => api.get('/exports/media-info', { params: { path } }).then(r => r.data);
export const linkExportToAngle = (videoPath, productId, angleId, exportId = null) =>
  api.post('/exports/link-angle', {
    video_path: videoPath, export_id: exportId, product_id: productId, angle_id: angleId,
  }).then(r => r.data);
export const getSfxList = () => api.get('/sfx').then(r => r.data);

export const generateScript = (data) => api.post('/script/generate', {
  ...data,
  product_name: sanitizeText(data.product_name),
  key_features: sanitizeText(data.key_features),
  pain_point: sanitizeText(data.pain_point),
  price_deal: sanitizeText(data.price_deal)
}).then(r => r.data);

export const generateAiScripts = (data) => api.post('/script/ai-generate', {
  ...data,
  product_name: sanitizeText(data.product_name),
  key_features: sanitizeText(data.key_features),
  pain_point: sanitizeText(data.pain_point),
  price_deal: sanitizeText(data.price_deal)
}, { timeout: 120000 }).then(r => r.data);

export const previewVoice = (data) => api.post('/voice/preview', {
  ...data,
  text: sanitizeText(data.text)
}, { timeout: 45000 }).then(r => r.data);

export const startRender = (data) => api.post('/render', {
  ...data,
  product_name: sanitizeText(data.product_name),
  hook_title: sanitizeText(data.hook_title),
  key_features: sanitizeText(data.key_features),
  pain_point: sanitizeText(data.pain_point),
  price_deal: sanitizeText(data.price_deal),
  custom_script: data.custom_script ? sanitizeScript(data.custom_script) : null
}, { timeout: 120000 }).then(r => r.data);

export const getRenderStatus = (jobId) => api.get(`/render/status/${jobId}`, { timeout: 15000 }).then(r => r.data);
export const openFolder = (target) => api.post('/open-folder', { target }).then(r => r.data);

// Round POST-1: desktop "post to TikTok" flow -- reveal a single file
// pre-selected in Explorer (instead of just opening its folder), generate a
// real jpg cover (TikTok's uploader rejects the gallery's .webp poster), and
// close the Ready_to_post -> Posted lifecycle that never had a second half.
export const revealFile = (filePath) => api.post('/reveal-file', { file_path: filePath }).then(r => r.data);

export const generateCover = (videoPath, atSeconds, brand = '', model = '', label = '', template = null) =>
  api.post('/covers/generate', {
    video_path: videoPath, at_seconds: atSeconds, brand, model, label, template,
  }).then(r => r.data);

export const getCoverBadges = () => api.get('/covers/badges').then(r => r.data);

export const getCoverHighlights = (videoPath) =>
  api.post('/covers/highlights', { video_path: videoPath }).then(r => r.data);

export const generateCoverHooks = (productName, angleTitle = '', scriptContent = '') =>
  api.post('/covers/generate-hooks', {
    product_name: productName,
    angle_title: angleTitle,
    script_content: scriptContent,
  }).then(r => r.data);

export const renderProCover = (payload) =>
  api.post('/covers/render-pro', payload).then(r => r.data);

export const getCoverRawSources = (videoPath) =>
  api.post('/covers/raw-sources', { video_path: videoPath }).then(r => r.data);

export const markPosted = (filePath, productId = null, angleId = null, exportId = null) =>
  api.post('/exports/mark-posted', {
    file_path: filePath, export_id: exportId, product_id: productId, angle_id: angleId,
  }).then(r => r.data);

// Round POST-2: hands a prepared job (abs paths + caption) to the
// tiktok_autopost_extension/ Chrome extension, which polls
// GET /api/tiktok-autopost/pending itself -- see that endpoint's docstring
// for why the app can't message the extension directly.
export const prepareTiktokAutopost = (videoPath, coverPath, caption, hashtags, productId = null, angleId = null, tiktokProductId = null, scheduleTime = null, exportId = null) =>
  api.post('/tiktok-autopost/prepare', {
    video_path: videoPath, cover_path: coverPath, caption, hashtags,
    product_id: productId, angle_id: angleId, tiktok_product_id: tiktokProductId,
    export_id: exportId,
    schedule_time: scheduleTime,
  }).then(r => r.data);

export const getScheduleQueue = (params = {}) => api.get('/schedule-queue', { params }).then(r => r.data);
export const createScheduleQueue = (payload) => api.post('/schedule-queue', payload).then(r => r.data);
export const updateScheduleQueue = (id, payload) => api.patch(`/schedule-queue/${id}`, payload).then(r => r.data);
export const removeScheduleQueue = (id) => api.delete(`/schedule-queue/${id}`).then(r => r.data);
export const prepareScheduleQueue = (id) => api.post(`/schedule-queue/${id}/prepare`).then(r => r.data);
export const getScheduleTemplate = (weekStart = null) => api.get('/schedule-queue/template', { params: weekStart ? { week_start: weekStart } : {} }).then(r => r.data);
export const saveScheduleTemplate = (payload) => api.put('/schedule-queue/template', payload).then(r => r.data);
export const copyScheduleTemplate = (payload) => api.post('/schedule-queue/template/copy', payload).then(r => r.data);
export const resetScheduleTemplate = (weekStart) => api.delete(`/schedule-queue/template/${weekStart}`).then(r => r.data);
export const previewScheduleAutofill = (payload) => api.post('/schedule-queue/auto-fill/preview', payload).then(r => r.data);
export const commitScheduleAutofill = (payload) => api.post('/schedule-queue/auto-fill', payload).then(r => r.data);

export const transcribeMedia = (data) => api.post('/sub-srt/transcribe', data, { timeout: 180000 }).then(r => r.data);

// Uploads with extended 5-minute timeout for large HD/4K videos
export const uploadFile = (formData, onProgress) => api.post('/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 300000,
  onUploadProgress: (progressEvent) => {
    if (onProgress && progressEvent.total) {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent, progressEvent.loaded, progressEvent.total);
    }
  }
}).then(r => r.data);

export const uploadMultipleFiles = (formData, onProgress) => api.post('/upload-multiple', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 300000,
  onUploadProgress: (progressEvent) => {
    if (onProgress && progressEvent.total) {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent, progressEvent.loaded, progressEvent.total);
    }
  }
}).then(r => r.data);

export const deleteFile = (filePath, productId = null, angleId = null, exportId = null) => api.post('/delete-file', {
  file_path: filePath,
  export_id: exportId || null,
  product_id: productId || null,
  angle_id: angleId || null,
}).then(r => r.data);

// --- Phase 1: product -> clip flow ---
export const aiRun = (task, context) => api.post('/ai/prompt', { task, context }, { timeout: 90000 }).then(r => r.data);
export const aiParse = (task, rawText) => api.post('/ai/parse', { task, raw_text: rawText }, { timeout: 90000 }).then(r => r.data);
export const getAiStatus = () => api.get('/ai/status').then(r => r.data);

export const getAngles = (params) => api.get('/angles', { params }).then(r => r.data);

export const scrapeAndPlanProduct = (payload) => {
  const data = typeof payload === 'string' ? { url: payload } : payload;
  return api.post('/products/scrape-and-plan', {
    ...data,
    custom_keyword: data.custom_keyword ? sanitizeText(data.custom_keyword) : undefined,
    raw_text: data.raw_text ? sanitizeScript(data.raw_text) : undefined
  }, { timeout: 120000 }).then(r => r.data);
};

export const getProducts = (status) => api.get('/products', { params: status ? { status } : {} }).then(r => r.data);
export const createProduct = (data) => api.post('/products', data).then(r => r.data);
export const updateProduct = (id, data) => api.patch(`/products/${id}`, data).then(r => r.data);
export const previewProductSource = (id, data = {}) =>
  api.post(`/products/${id}/preview-source`, data, { timeout: 120000 }).then(r => r.data);
export const previewProductImageMetadata = (id) =>
  api.post(`/products/${id}/preview-image-metadata`, {}, { timeout: 120000 }).then(r => r.data);
export const previewProductImageMetadataAsync = (id) =>
  api.post(`/products/${id}/preview-image-metadata-async`).then(r => r.data);
export const refreshProductSource = (id, data = {}) =>
  api.post(`/products/${id}/refresh-source`, data, { timeout: 120000 }).then(r => r.data);
export const resolveTiktokProductId = (urlOrId) =>
  api.post('/products/resolve-tiktok-id', { url_or_id: urlOrId }).then(r => r.data);
export const updateAngleStatus = (productId, angleId, status, videoUrl = null, projectName = null, qcNote = null, clearQcNote = false, clearConflictNote = false, exportId = null, markQcPassed = false) =>
  api.patch(`/products/${productId}/angles/${angleId}`, {
    status,
    video_url: videoUrl,
    project_name: projectName,
    export_id: exportId || null,
    ...(qcNote !== null ? { qc_note: qcNote } : {}),
    ...(clearQcNote ? { clear_qc_note: true } : {}),
    ...(clearConflictNote ? { clear_conflict_note: true } : {}),
    ...(markQcPassed ? { mark_qc_passed: true } : {}),
  }).then(r => r.data);

export const updateAngleCover = (productId, angleId, cover) =>
  api.patch(`/products/${productId}/angles/${angleId}/cover`, cover).then(r => r.data);

export const updateAngleVideos = (productId, angleId, selectedVideos) => api.post(`/products/${productId}/angles/${angleId}/videos`, { selected_videos: selectedVideos }).then(r => r.data);
export const setDefaultVideosForProduct = (productId, selectedVideos) => api.post(`/products/${productId}/default-videos`, { selected_videos: selectedVideos }).then(r => r.data);
export const deleteProduct = (id) => api.delete(`/products/${id}`).then(r => r.data);

export const getProjects = () => api.get('/projects').then(r => r.data);
export const getProject = (name) => api.get(`/projects/${encodeURIComponent(name)}`).then(r => r.data);
export const getProjectOrigin = (name) => api.get(`/projects/${encodeURIComponent(name)}/origin`).then(r => r.data);
export const deleteProject = (name, scope = 'project') =>
  api.delete(`/projects/${encodeURIComponent(name)}`, { params: { scope } }).then(r => r.data);
export const updateProjectCues = (name, data) => api.patch(`/projects/${encodeURIComponent(name)}/cues`, data).then(r => r.data);
export const updateProjectClips = (name, data) => api.patch(`/projects/${encodeURIComponent(name)}/clips`, data).then(r => r.data);
export const updateProjectState = (name, data) => api.patch(`/projects/${encodeURIComponent(name)}/state`, data).then(r => r.data);

export const startReroll = (data) => api.post('/reroll', data, { timeout: 120000 }).then(r => r.data);

export const getPosts = () => api.get('/posts').then(r => r.data);
export const createPost = (data) => api.post('/posts', data).then(r => r.data);
export const setPostMetrics = (id, metrics) => api.post(`/posts/${id}/metrics`, metrics).then(r => r.data);
export const getPerformance = () => api.get('/posts/performance').then(r => r.data);

export const getAllAssets = () => api.get('/assets/all').then(r => r.data);
export const starAsset = (id, starred) => api.post('/assets/star', { id, starred }).then(r => r.data);
export const getHookMotionPresets = () => api.get('/hook-motion-presets').then(r => r.data);
export const uploadAsset = (formData) => api.post('/assets/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 300000
}).then(r => r.data);

// ═══════════════════════════════════════════════════════════════════════
// 📋 GLOBAL TASK & ACTIVITY MANAGEMENT APIS
// ═══════════════════════════════════════════════════════════════════════
export const scrapeAndPlanProductAsync = (payload) => {
  const data = typeof payload === 'string' ? { url: payload } : payload;
  return api.post('/products/scrape-and-plan-async', {
    ...data,
    custom_keyword: data.custom_keyword ? sanitizeText(data.custom_keyword) : undefined,
    raw_text: data.raw_text ? sanitizeScript(data.raw_text) : undefined
  }).then(r => r.data);
};

// Round: per-angle AI script reroll (duration + extra_beats), independent of
// the video-render reroll system (startReroll above) -- this one overwrites
// an angle's script content before any video work happens, and is async like
// scrape-and-plan-async (returns a task_id polled via the same TaskContext).
export const rerollAngleScript = (productId, angleId, payload = {}) =>
  api.post(`/products/${productId}/angles/${angleId}/reroll-script`, payload).then(r => r.data);

// Shot-list generation: per-beat filming plan built from the angle's real
// TTS voice timing (not a text-length estimate), so footage can later be
// mapped onto the script without AI vision matching. Async like
// reroll-script above (task_id polled via TaskContext's refreshTrigger).
export const generateShotList = (productId, angleId, voiceOverrides = {}) =>
  api.post(`/products/${productId}/angles/${angleId}/shot-list`, voiceOverrides).then(r => r.data);

export const getShotList = (productId, angleId) =>
  api.get(`/products/${productId}/angles/${angleId}/shot-list`).then(r => r.data);

// Guided-take recording sessions (scripts/api_recording.py): pairs the
// mobile filming page (MobileFilmingPage.jsx) with a product/angle's shot
// list, one uploaded segment per beat, strict order + retake-last-only
// enforced server-side.
export const createRecordingSession = (productId, angleId) =>
  api.post('/recording-sessions', { product_id: productId, angle_id: angleId }).then(r => r.data);

export const getRecordingSession = (sessionId) =>
  api.get(`/recording-sessions/${sessionId}`).then(r => r.data);

export const uploadRecordingSegment = (sessionId, beatIndex, blob, filename, onProgress) => {
  const formData = new FormData();
  formData.append('beat_index', String(beatIndex));
  formData.append('file', blob, filename);
  return api.post(`/recording-sessions/${sessionId}/segments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
    onUploadProgress: onProgress
      ? (e) => onProgress(e.total ? Math.round((e.loaded / e.total) * 100) : 0)
      : undefined,
  }).then(r => r.data);
};

export const deleteRecordingSegment = (sessionId, beatIndex) =>
  api.delete(`/recording-sessions/${sessionId}/segments/${beatIndex}`).then(r => r.data);

export const finalizeRecordingSession = (sessionId) =>
  api.post(`/recording-sessions/${sessionId}/finalize`).then(r => r.data);

export const getActiveTasks = () => api.get('/tasks/active').then(r => r.data);
export const getTaskStatus = (taskId) => api.get(`/tasks/${taskId}`).then(r => r.data);
export const cancelTaskApi = (taskId) => api.post(`/tasks/${taskId}/cancel`).then(r => r.data);
export const deleteTaskApi = (taskId) => api.delete(`/tasks/${taskId}`).then(r => r.data);
export const clearCompletedTasksApi = () => api.post('/tasks/clear-completed').then(r => r.data);

// ═══════════════════════════════════════════════════════════════════════
// 📊 AI TOKEN ANALYTICS APIS
// ═══════════════════════════════════════════════════════════════════════
export const getTokenSummary = () => api.get('/tokens/summary').then(r => r.data);
export const getTokenHistory = (limit = 50) => api.get('/tokens/history', { params: { limit } }).then(r => r.data);
export const resetTokenAnalytics = () => api.post('/tokens/reset').then(r => r.data);

export const fetchOverlayLayout = (payload) => api.post('/editor/overlay/layout', payload).then(r => r.data);

// True ffprobe duration of a raw source file -- see api_editor.py's
// /media-info docstring for why TrimAdjustModal needs this instead of the
// per-clip `durations` state the rest of the editor uses.
export const getMediaInfo = (path) => api.get('/editor/media-info', { params: { path } }).then(r => r.data);

export const filmstripUrlFor = (path, count, start, end) => {
  const params = new URLSearchParams({ path, count: String(count) });
  if (start != null) params.set('start', start.toFixed(2));
  if (end != null) params.set('end', end.toFixed(2));
  return `/api/editor/filmstrip?${params.toString()}`;
};

export const getHookTemplates = () => api.get('/editor/hook-templates').then(r => r.data);
export const saveCustomHookTemplate = (payload) => api.post('/editor/hook-templates', payload).then(r => r.data);
export const deleteCustomHookTemplate = (id) => api.delete(`/editor/hook-templates/${encodeURIComponent(id)}`).then(r => r.data);

export default api;
