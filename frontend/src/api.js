import axios from 'axios';
import { rememberProjectRevision, withProjectRevision } from './lib/projectRevision.js';
import { sanitizeText, sanitizeScript } from './lib/sanitize.js';
import { createChannelTransport, projectApiPath } from './lib/channelTransport.js';
import { captureChannel, isCurrentChannel, channelSelectionError } from './lib/channelRuntime.js';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // 60 seconds default
  // Same-origin today; keeps the HttpOnly session cookie (omnicut_session)
  // attached even if the API is ever served from a sibling origin.
  withCredentials: true,
});

// ── App login (session cookie) ──
// The API answers protected calls with 401 {login_required: true} once the
// session cookie is missing/expired. One window event lets AuthGate show the
// login screen without every caller knowing about auth. /api/auth/* never
// fires it (the login form handles its own 401), so there is no loop.
export const LOGIN_REQUIRED_EVENT = 'omnicut:login-required';
export const AUTH_RESTORED_EVENT = 'omnicut:auth-restored';

function isAuthEndpoint(url = '') {
  return /(?:^|\/)api\/auth(?:\/|$)|^\/?auth(?:\/|$)/.test(String(url));
}

export function notifyLoginRequired(url, data) {
  if (typeof window === 'undefined' || isAuthEndpoint(url)) return false;
  if (!data || data.login_required !== true) return false;
  try {
    window.dispatchEvent(new CustomEvent(LOGIN_REQUIRED_EVENT, { detail: { url: String(url || '') } }));
  } catch { /* CustomEvent unavailable */ }
  return true;
}

const authClient = axios.create({ baseURL: '/', timeout: 15000, withCredentials: true });

/** GET /api/auth/me -> {authenticated, auth_required, method, password_configured} */
export const getAuthMe = () => authClient.get('/api/auth/me').then(r => r.data);
/** POST /api/auth/login -> sets the HttpOnly cookie on 200; 401 wrong password; 429 throttled; 503 not configured. */
export const loginWithPassword = (password) => authClient.post('/api/auth/login', { password }).then(r => r.data);
export const logout = () => authClient.post('/api/auth/logout').then(r => r.data);

/**
 * Many components call fetch('/api/...') directly. Watch those responses for
 * the same 401 {login_required} contract. Idempotent; call once at startup.
 */
export function installAuthFetchWatcher() {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') return;
  if (window.fetch.__omnicutAuthWatcher) return;
  const nativeFetch = window.fetch.bind(window);
  const watchedFetch = async (input, init) => {
    const response = await nativeFetch(input, init);
    if (response.status === 401) {
      try {
        const rawUrl = typeof input === 'string' ? input : (input?.url || String(input));
        const url = new URL(rawUrl, window.location.href);
        if (url.origin === window.location.origin && url.pathname.startsWith('/api/') && !isAuthEndpoint(url.pathname)) {
          response.clone().json().then(data => notifyLoginRequired(url.pathname, data)).catch(() => {});
        }
      } catch { /* non-URL input */ }
    }
    return response;
  };
  watchedFetch.__omnicutAuthWatcher = true;
  window.fetch = watchedFetch;
}

const originalRequest = api.request.bind(api);
const scopedRequest = createChannelTransport({ send: originalRequest,
  capture: captureChannel, isCurrent: isCurrentChannel });
api.request = options => {
  if (channelSelectionError() && !/^\/(?:api\/)?channels(?:\/|$)/.test(options.url)) {
    const error = new Error(channelSelectionError());
    error.code = 'channel_scope_invalid';
    return Promise.reject(error);
  }
  return scopedRequest({ ...options, baseURL: '/',
    url: options.url.startsWith('/api/') ? options.url : `/api${options.url}` });
};
for (const method of ['get', 'delete', 'head', 'options']) {
  api[method] = (url, options = {}) => api.request({ ...options, method, url });
}
for (const method of ['post', 'put', 'patch']) {
  api[method] = (url, data, options = {}) => api.request({ ...options, method, url, data });
}

export const getChannels = () => api.get('/channels').then(response => response.data);
export const createChannel = payload => api.post('/channels', payload).then(response => response.data);
export const updateChannel = (id, payload) => api.patch(`/channels/${encodeURIComponent(id)}`, payload).then(response => response.data);
export const activateChannelProfile = (id, expectedRevision) => api.post(`/channels/${encodeURIComponent(id)}/activate`, { expected_revision: expectedRevision }).then(response => response.data);
export const archiveChannelProfile = (id, expectedRevision) => api.post(`/channels/${encodeURIComponent(id)}/archive`, { expected_revision: expectedRevision }).then(response => response.data);
export const getChannelReadiness = id => api.get(`/channels/${encodeURIComponent(id)}/readiness`).then(response => response.data);

// Authentication is injected by the same-origin Vite proxy/server boundary;
// the browser code never carries the backend shared secret.

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

      if (status === 401) {
        notifyLoginRequired(error.config?.url, error.response.data);
        friendlyMessage = detail || 'ต้องเข้าสู่ระบบก่อน';
      } else if (status === 413) {
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
export const enhanceExportForTiktok = (payload) => api.post('/exports/enhance-tiktok', payload).then(r => r.data);
export const linkExportToAngle = (videoPath, productId, angleId, exportId = null) =>
  api.post('/exports/link-angle', {
    video_path: videoPath, export_id: exportId, product_id: productId, angle_id: angleId,
  }).then(r => r.data);
export const getSfxList = () => api.get('/sfx').then(r => r.data);

// Beat grid for a BGM track: the same beats scripts/pipeline.py snaps
// generated cuts to, so a hand-placed cut lands on the same music. Analysis
// is optional server-side (librosa may be absent), so an empty grid means
// "no snap targets", not a failure -- callers render no markers and carry on.
export const getBgmBeats = (bgmName) =>
  api.get('/audio/beats', { params: { bgm_name: bgmName } }).then(r => r.data);

// Dead-air spans for one media file, plus the ranges a ripple delete would
// keep. Read-only: nothing is cut until the user confirms the preview.
export const getMediaSilences = (mediaPath, options = {}) =>
  api.get('/audio/silences', { params: { media_path: mediaPath, ...options } }).then(r => r.data);

// Playback URL for one clip: the 540p editing proxy when it exists, otherwise
// the master while the proxy encodes in the background. Never blocks -- the
// master is always a valid answer, so a failed or slow encode costs
// smoothness, not the ability to edit.
export const getClipProxy = (sourcePath, { build = true } = {}) =>
  api.get('/proxy/for-clip', { params: { source_path: sourcePath, build } }).then(r => r.data);

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
export const getVoicePresets = () => api.get('/voice/presets').then(r => r.data);

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
export const startBatchRender = (payload) => api.post('/render/batch', payload).then(r => r.data);
export const startBatchDraft = (payload) => api.post('/render/batch', { ...payload, export_mp4: false }).then(r => r.data);
export const getBatchRenderStatus = (batchId) => api.get(`/render/batch/${batchId}`).then(r => r.data);
export const startBackgroundIsolation = (payload) =>
  api.post('/background-isolation/process', payload, { timeout: 120000 }).then(r => r.data);
export const getBackgroundIsolationManifest = (artifactId) =>
  api.get(`/background-isolation/sequences/${encodeURIComponent(artifactId)}/manifest`).then(r => r.data);
export const preflightBackgroundIsolation = (payload) =>
  api.post('/background-isolation/preflight', payload, { timeout: 30000 }).then(r => r.data);
export const interactiveSegment = (payload) =>
  api.post('/background-isolation/interactive-segment', payload, { timeout: 15000 }).then(r => r.data);
export const cancelBatchRender = (batchId) => api.post(`/render/batch/${batchId}/cancel`).then(r => r.data);
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

export const renderProCover = (payload, channelToken = captureChannel()) =>
  api.post('/covers/render-pro', payload, { channelToken }).then(r => r.data);

export const getCoverRawSources = (videoPath) =>
  api.post('/covers/raw-sources', { video_path: videoPath }).then(r => r.data);

export const getCoverProductRefImages = (params) =>
  api.post('/covers/product-ref-images', params).then(r => r.data);

export const generateAiCoverImage = (payload) =>
  api.post('/covers/ai-generate-image', payload).then(r => r.data);

export const grabCoverFrame = (videoPath, atSeconds) =>
  api.post('/covers/grab-frame', { video_path: videoPath, at_seconds: atSeconds }).then(r => r.data);

export const markPosted = (filePath, productId = null, angleId = null, exportId = null) =>
  api.post('/exports/mark-posted', {
    file_path: filePath, export_id: exportId, product_id: productId, angle_id: angleId,
  }).then(r => r.data);

// Round POST-2: hands a prepared job (abs paths + caption) to the
// tiktok_autopost_extension/ Chrome extension, which polls
// GET /api/tiktok-autopost/pending itself -- see that endpoint's docstring
// for why the app can't message the extension directly.
export const prepareTiktokAutopost = (videoPath, coverPath, caption, hashtags, productId = null, angleId = null, tiktokProductId = null, scheduleDate = null, scheduleTime = null, exportId = null) =>
  api.post('/tiktok-autopost/prepare', {
    video_path: videoPath, cover_path: coverPath, caption, hashtags,
    product_id: productId, angle_id: angleId, tiktok_product_id: tiktokProductId,
    export_id: exportId,
    schedule_date: scheduleDate,
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

// Non-commerce Gadget Media campaign workflow.
export const listGadgetMediaCampaigns = () => api.get('/gadget-media/campaigns').then(r => r.data);
export const createGadgetMediaCampaign = (payload = {}) => api.post('/gadget-media/campaigns', payload).then(r => r.data);
export const getGadgetMediaCampaignReadiness = (campaignId) =>
  api.get(`/gadget-media/campaigns/${encodeURIComponent(campaignId)}/readiness`).then(r => r.data);
export const getGadgetMediaCampaignAnalytics = (campaignId) =>
  api.get(`/gadget-media/campaigns/${encodeURIComponent(campaignId)}/analytics`).then(r => r.data);
export const getGadgetMediaPresetSources = () => api.get('/gadget-media/preset-sources').then(r => r.data);
export const updateGadgetMediaSlot = (campaignId, slotId, payload) =>
  api.patch(`/gadget-media/campaigns/${encodeURIComponent(campaignId)}/slots/${encodeURIComponent(slotId)}`, payload).then(r => r.data);
export const listGadgetMediaProjects = () => api.get('/gadget-media/projects').then(r => r.data);
export const createGadgetMediaProject = (payload) => api.post('/gadget-media/projects', payload).then(r => r.data);
export const getGadgetMediaProject = (projectId) =>
  api.get(`/gadget-media/projects/${encodeURIComponent(projectId)}`).then(r => r.data);
export const updateGadgetMediaProject = (projectId, payload) =>
  api.patch(`/gadget-media/projects/${encodeURIComponent(projectId)}`, payload).then(r => r.data);
export const probeGadgetMediaSource = (projectId, payload) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/sources/probe`, payload).then(r => r.data);
export const buildGadgetMediaTimeline = (projectId) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/timeline/build`).then(r => r.data);
export const getGadgetMediaTimeline = (projectId) =>
  api.get(`/gadget-media/projects/${encodeURIComponent(projectId)}/timeline`).then(r => r.data);
export const saveGadgetMediaTimeline = (projectId, timeline) =>
  api.put(`/gadget-media/projects/${encodeURIComponent(projectId)}/timeline`, { timeline }).then(r => r.data);
export const validateGadgetMediaProject = (projectId) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/quality/validate`).then(r => r.data);
export const generateGadgetMediaNarration = (projectId, payload = {}) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/audio/generate`, payload).then(r => r.data);
export const renderGadgetMediaProject = (projectId, payload = { export_preset: 'post' }) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/renders`, payload).then(r => r.data);
export const approveGadgetMediaRender = (projectId, artifactId) =>
  api.post(`/gadget-media/projects/${encodeURIComponent(projectId)}/renders/${encodeURIComponent(artifactId)}/approve`).then(r => r.data);
export const createGadgetMediaProjectFromSlot = (campaignId, slotId, payload) =>
  api.post(`/gadget-media/campaigns/${encodeURIComponent(campaignId)}/slots/${encodeURIComponent(slotId)}/project`, payload).then(r => r.data);

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

export const getProducts = (status, lite = null, reconcile = true) => {
  const params = {};
  if (status) params.status = status;
  if (lite) params.lite = lite;
  if (reconcile === false) params.reconcile = 0;
  return api.get('/products', { params }).then(r => r.data);
};
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
export const updateAngleStatus = (productId, angleId, status, videoUrl = null, projectName = null, qcNote = null, clearQcNote = false, clearConflictNote = false, exportId = null, markQcPassed = false, batch = null) =>
  api.patch(`/products/${productId}/angles/${angleId}`, {
    status,
    video_url: videoUrl,
    project_name: projectName,
    export_id: exportId || null,
    ...(batch !== null ? { batch } : {}),
    ...(qcNote !== null ? { qc_note: qcNote } : {}),
    ...(clearQcNote ? { clear_qc_note: true } : {}),
    ...(clearConflictNote ? { clear_conflict_note: true } : {}),
    ...(markQcPassed ? { mark_qc_passed: true } : {}),
  }).then(r => r.data);

export const updateAngleCover = (productId, angleId, cover, batch = null, channelToken = captureChannel()) =>
  api.patch(`/products/${productId}/angles/${angleId}/cover`, { ...cover, ...(batch !== null ? { batch } : {}) }, { channelToken }).then(r => r.data);

export const updateAngleVideos = (productId, angleId, selectedVideos, batch = null) =>
  api.post(`/products/${productId}/angles/${angleId}/videos`, { selected_videos: selectedVideos, ...(batch !== null ? { batch } : {}) }).then(r => r.data);
export const setDefaultVideosForProduct = (productId, selectedVideos) => api.post(`/products/${productId}/default-videos`, { selected_videos: selectedVideos }).then(r => r.data);
export const getSceneCatalogs = (productId, videoPath) =>
  api.get(`/products/${productId}/scene-catalogs`, { params: videoPath ? { video_path: videoPath } : {} }).then(r => r.data);
export const indexSceneCatalogs = (productId, payload = {}) =>
  api.post(`/products/${productId}/index-scenes`, payload, { timeout: 180000 }).then(r => r.data);
export const getRawVaultSceneCatalogs = (videoPath) =>
  api.get('/raw-vault/scene-catalogs', { params: videoPath ? { video_path: videoPath } : {} }).then(r => r.data);
export const indexRawVaultScenes = (payload = {}) =>
  api.post('/raw-vault/index-scenes', payload, { timeout: 180000 }).then(r => r.data);
export const generateProductBatch = (productId, payload) => api.post(`/products/${productId}/generate-batch`, payload).then(r => r.data);
export const addProductAngle = (productId, payload) => api.post(`/products/${productId}/angles`, payload).then(r => r.data);
export const deleteProductAngle = (productId, angleId, batch = null) =>
  api.delete(`/products/${productId}/angles/${angleId}`, { params: batch !== null ? { batch } : {} }).then(r => r.data);
export const deleteProduct = (id, force = false) => api.delete(`/products/${id}`, { params: { force } }).then(r => r.data);

export const getProjects = () => api.get('/projects').then(r => r.data);
export const getProject = (name) => api.get(projectApiPath(name)).then(r => r.data);
export const getProjectOrigin = (name) => api.get(`${projectApiPath(name)}/origin`).then(r => r.data);
export const deleteProject = (name, scope = 'project') =>
  api.delete(projectApiPath(name), { params: { scope } }).then(r => r.data);
export const updateProjectCues = (name, data) => api.patch(`${projectApiPath(name)}/cues`, data).then(r => r.data);
export const updateProjectClips = (name, data) => api.patch(`${projectApiPath(name)}/clips`, data).then(r => r.data);
export const updateProjectState = (name, data, channelToken = captureChannel()) =>
  api.patch(`${projectApiPath(name)}/state`, withProjectRevision(name, data, channelToken.channel_id), { channelToken }).then(r => {
    rememberProjectRevision(name, r.data?._editor_revision, channelToken.channel_id);
    return r.data;
  });

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
export const generateShotList = (productId, angleId, voiceOverrides = {}, batch = null) => {
  const payload = { ...voiceOverrides };
  if (batch !== null && batch !== undefined) {
    payload.batch = batch;
  }
  return api.post(`/products/${productId}/angles/${angleId}/shot-list`, payload).then(r => r.data);
};

export const getShotList = (productId, angleId, batch = null) =>
  api.get(`/products/${productId}/angles/${angleId}/shot-list`, { params: batch ? { batch } : {} }).then(r => r.data);

export const getShotListStatus = (productId) =>
  api.get(`/products/${productId}/shot-list-status`).then(r => r.data);

export const batchGenerateAudio = (productId, payload = {}) =>
  api.post(`/products/${productId}/batch-generate-audio`, payload).then(r => r.data);

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
// 📊 AI TOKEN & ANALYTICS HUB APIS
// ═══════════════════════════════════════════════════════════════════════
export const getTokenSummary = () => api.get('/tokens/summary').then(r => r.data);
export const getTokenHistory = (options = {}) => {
  const params = typeof options === 'number' ? { limit: options } : options;
  return api.get('/tokens/history', { params }).then(r => r.data);
};
export const resetTokenAnalytics = () => api.post('/tokens/reset').then(r => r.data);
export const clearTokenAlerts = () => api.post('/tokens/alerts/clear').then(r => r.data);

export const getProductionAnalytics = () => api.get('/analytics/production').then(r => r.data);
export const getStorageAnalytics = (forceScan = false) => api.get('/analytics/storage', { params: forceScan ? { force_scan: true } : {} }).then(r => r.data);
export const purgeSafeStorageCache = () => api.post('/analytics/storage/purge-safe-cache').then(r => r.data);
export const getCutoutCacheStatus = () => api.get('/analytics/storage/cutout-cache').then(r => r.data);
export const purgeCutoutCache = () => api.post('/analytics/storage/purge-cutout-cache').then(r => r.data);

export const getInventoryHealth = () => api.get('/analytics/inventory').then(r => r.data);
export const getTiktokStatsLatest = () => api.get('/tiktok-stats/latest').then(r => r.data);
export const getTiktokMilestones = (threshold = 1000) => api.get('/tiktok-stats/milestones', { params: { threshold } }).then(r => r.data);
export const getTiktokPending = () => api.get('/tiktok-stats/pending').then(r => r.data);
export const getTiktokClipCandidates = () => api.get('/tiktok-stats/clip-candidates').then(r => r.data);
export const attachTiktokPending = (payload) => api.post('/tiktok-stats/attach', payload).then(r => r.data);
export const ignoreTiktokPending = (pendingId) => api.post('/tiktok-stats/pending/ignore', { pending_id: pendingId }).then(r => r.data);
export const ignoreAllTiktokPending = () => api.post('/tiktok-stats/pending/ignore-all').then(r => r.data);
export const getTiktokIgnored = () => api.get('/tiktok-stats/ignored').then(r => r.data);
export const restoreTiktokIgnored = (ignoredId) => api.post('/tiktok-stats/ignored/restore', { ignored_id: ignoredId }).then(r => r.data);

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

// ═══════════════════════════════════════════════════════════════════════
// 💾 ONE-CLICK BACKUP & ASSET DEDUPLICATION APIS
// ═══════════════════════════════════════════════════════════════════════
export const createSystemBackup = () => api.post('/backup/create').then(r => r.data);
export const getSystemBackups = () => api.get('/backup/list').then(r => r.data);
export const verifySystemBackup = (filename) => api.get(`/backup/verify/${encodeURIComponent(filename)}`).then(r => r.data);
export const deleteSystemBackup = (filename) => api.delete(`/backup/${encodeURIComponent(filename)}`).then(r => r.data);

export const scanAssetDuplicates = (minSizeKb = 10) =>
  api.get('/assets/duplicates/scan', { params: { min_size_kb: minSizeKb } }).then(r => r.data);
export const cleanAssetDuplicates = (duplicatePaths, moveToTrash = true) =>
  api.post('/assets/duplicates/clean', { duplicate_paths: duplicatePaths, move_to_trash: moveToTrash }).then(r => r.data);
// ═══════════════════════════════════════════════════════════════════════
// 🎯 AI HOOK VARIATION & A/B APIS
// ═══════════════════════════════════════════════════════════════════════
export const getHookStyles = () => api.get('/hooks/styles').then(r => r.data);
export const generateHookVariations = (payload) => api.post('/hooks/generate', payload).then(r => r.data);
export const applyAngleHook = (payload) => api.post('/hooks/apply-angle', payload).then(r => r.data);
export const applyProjectHook = (payload) => api.post('/hooks/apply-project', payload).then(r => r.data);

// ═══════════════════════════════════════════════════════════════════════
// 💡 AI PRODUCER HUB — IDEA & REF VAULT APIS
// ═══════════════════════════════════════════════════════════════════════
export const uploadRefMedia = (file, channelToken = captureChannel()) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/producer/upload-ref-media', formData, {
    channelToken,
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

export const aiIdeaToAngle = (payload) =>
  api.post('/producer/ai-idea-to-angle', payload).then(r => r.data);

export const getProducerNotes = (channelToken = captureChannel()) =>
  api.get('/producer/notes', { channelToken }).then(r => r.data);

export const saveProducerNotes = (notes, baseRevision = null) =>
  api.post('/producer/notes', { notes, ...(baseRevision ? { base_revision: baseRevision } : {}) }).then(r => r.data);

export const addProducerNote = (note, channelToken = captureChannel()) =>
  api.post('/producer/notes/add', { note }, { channelToken }).then(r => r.data);

export const updateProducerNote = (noteId, patch, baseRevision = null, channelToken = captureChannel()) =>
  api.put(`/producer/notes/${encodeURIComponent(noteId)}`, { ...patch, ...(baseRevision ? { base_revision: baseRevision } : {}) }, { channelToken }).then(r => r.data);

export const deleteProducerNote = (noteId, channelToken = captureChannel()) =>
  api.delete(`/producer/notes/${encodeURIComponent(noteId)}`, { channelToken }).then(r => r.data);

export const getManualShotMap = (productId, angleId, batch = null) =>
  api.get(`/products/${productId}/angles/${angleId}/manual-shot-map`, { params: batch ? { batch } : {} }).then(r => r.data);

export const saveManualShotMap = (productId, angleId, shotMap, batch = null) =>
  api.patch(`/products/${productId}/angles/${angleId}/manual-shot-map`, { shot_map: shotMap, batch }).then(r => r.data);

export const syncManualShotMap = (productId, sourceAngleId, payload = {}) =>
  api.post(`/products/${productId}/angles/${sourceAngleId}/sync-manual-shot-map`, payload).then(r => r.data);

export const getUniversalFilmingRecipe = (productId) =>
  api.get(`/products/${productId}/filming-recipe`).then(r => r.data);

// ── TypeSafe Studio API (System One / Jev Integration) ──
export const getTypeSafeStatus = () =>
  api.get('/typesafe-studio/status').then(r => r.data);

export const matchBrollWithAI = (sentence, candidateClips) =>
  api.post('/typesafe-studio/match-broll', { sentence, candidate_clips: candidateClips }).then(r => r.data);

export const generateHookVariantsAI = (productName, keyFeatures = null) =>
  api.post('/typesafe-studio/generate-hooks', { product_name: productName, key_features: keyFeatures }).then(r => r.data);

export const evaluateHookAI = (hookText) =>
  api.post('/typesafe-studio/evaluate-hook', { hook_text: hookText }).then(r => r.data);

export const matchBrollSequenceWithAI = (sentences, candidateClips, ensureDiversity = true) =>
  api.post('/typesafe-studio/match-sequence', {
    sentences,
    candidate_clips: candidateClips,
    ensure_diversity: ensureDiversity,
  }).then(r => r.data);

export const matchRawFolderWithAI = (rawFolder, sentences) =>
  api.post('/typesafe-studio/match-raw-folder', {
    raw_folder: rawFolder,
    sentences,
  }).then(r => r.data);

// ── Mobile Quick Studio API ──
export const fetchMobileCatalog = (params) =>
  api.get('/mobile-studio/catalog', { params }).then(r => r.data);

export const createMobileSession = (productId, angleId) =>
  api.post('/mobile-studio/session', { product_id: productId, angle_id: angleId }, { timeout: 300000 }).then(r => r.data);

export const triggerMobileAssemble = (productId, angleId, sessionId = null, customRawVideo = null, bgmEnabled = true) =>
  api.post('/mobile-studio/assemble', {
    product_id: productId,
    angle_id: angleId,
    session_id: sessionId,
    custom_raw_video: customRawVideo,
    bgm_enabled: bgmEnabled,
  }).then(r => r.data);

export const fetchMobileTask = (taskId) =>
  api.get(`/mobile-studio/task/${taskId}`).then(r => r.data);

export const cancelMobileTask = (taskId) =>
  api.post(`/mobile-studio/cancel/${taskId}`).then(r => r.data);

export const createMobileQuickAngle = (productId, title = null, script = null) =>
  api.post('/mobile-studio/quick-angle', { product_id: productId, title, script }).then(r => r.data);

export const uploadMobileVideo = (productId, angleId, file, onProgress = null) => {
  const formData = new FormData();
  formData.append('product_id', productId);
  formData.append('angle_id', angleId);
  formData.append('file', file);
  return api.post('/mobile-studio/upload-video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress ? (e) => {
      const pct = Math.round((e.loaded * 100) / (e.total || e.loaded));
      onProgress(pct);
    } : undefined,
  }).then(r => r.data);
};

export const quickAddMobileProduct = (nameOrUrl) =>
  api.post('/mobile-studio/products/quick-add', { name_or_url: nameOrUrl }).then(r => r.data);

export const previewMobileVoice = (text, voice = 'gemini_fenrir_male_strong') =>
  api.post('/mobile-studio/preview-voice', { text, voice }).then(r => r.data);

// ── HyperFrames Creative Studio APIs ──
export const getHyperFramesStatus = () => api.get('/hyperframes/status').then(r => r.data);
export const getHyperFramesStyles = () => api.get('/hyperframes/styles').then(r => r.data);
export const getHyperFramesCompositions = () => api.get('/hyperframes/compositions').then(r => r.data);
export const createHyperFramesClip = (payload) => api.post('/hyperframes/create-clip', payload).then(r => r.data);
export const renderHyperFramesComposition = (payload) => api.post('/hyperframes/render', payload).then(r => r.data);
export const openHyperFramesStudio = (port = 3100) => api.post('/hyperframes/open-studio', { port }).then(r => r.data);

// The existing transport freezes request scope and discards late channel replies.
export const hyperframesWorkflowApi = {
  aiCapabilities: () => api.get('/hyperframes/ai/capabilities').then(r => r.data),
  inspectOverlay: payload => api.post('/hyperframes/overlay/inspect', payload).then(r => r.data),
  createOverlay: payload => api.post('/hyperframes/overlay/projects', payload).then(r => r.data),
  generateAI: (id, payload) => api.post(`/hyperframes/authoring-jobs/${encodeURIComponent(id)}/generate`, payload).then(r => r.data),
  cancelAI: id => api.post(`/hyperframes/authoring-jobs/${encodeURIComponent(id)}/generate/cancel`).then(r => r.data),
  listGadgetProjects: () => listGadgetMediaProjects(),
  listProjects: () => api.get('/hyperframes/projects').then(r => r.data),
  createProject: payload => api.post('/hyperframes/projects', payload).then(r => r.data),
  getProject: id => api.get(`/hyperframes/projects/${encodeURIComponent(id)}`).then(r => r.data),
  updateProject: (id, payload) => api.patch(`/hyperframes/projects/${encodeURIComponent(id)}`, payload).then(r => r.data),
  createAuthoringJob: (id, payload) => api.post(`/hyperframes/projects/${encodeURIComponent(id)}/authoring-jobs`, payload).then(r => r.data),
  getAuthoringJob: id => api.get(`/hyperframes/authoring-jobs/${encodeURIComponent(id)}`).then(r => r.data),
  getHandoff: id => api.get(`/hyperframes/authoring-jobs/${encodeURIComponent(id)}/handoff`).then(r => r.data),
  acceptRevision: (id, payload) => api.post(`/hyperframes/projects/${encodeURIComponent(id)}/accept-revision`, payload).then(r => r.data),
  createRenderJob: (id, payload) => api.post(`/hyperframes/projects/${encodeURIComponent(id)}/render-jobs`, payload).then(r => r.data),
  getRenderJob: id => api.get(`/hyperframes/render-jobs/${encodeURIComponent(id)}`).then(r => r.data),
  cancelRender: id => api.post(`/hyperframes/render-jobs/${encodeURIComponent(id)}/cancel`).then(r => r.data),
  retryRender: id => api.post(`/hyperframes/render-jobs/${encodeURIComponent(id)}/retry`).then(r => r.data),
  finalizeRender: (id, payload) => api.post(`/hyperframes/render-jobs/${encodeURIComponent(id)}/finalize`, payload).then(r => r.data),
  repairRender: id => api.post(`/hyperframes/render-jobs/${encodeURIComponent(id)}/repair`).then(r => r.data),
  artifactUrl: (id, kind = 'video') => `/api/hyperframes/render-jobs/${encodeURIComponent(id)}/artifact/${encodeURIComponent(kind)}?channel=${encodeURIComponent(captureChannel().channel_id)}`,
};

export const getPostingJobForPublication = (id, options = {}) => api.get(`/tiktok-autopost/jobs/${encodeURIComponent(id)}`, options).then(r => ({ job: r.data }));
export const getPublicationObservations = (id, options = {}) => api.get(`/tiktok-autopost/jobs/${encodeURIComponent(id)}/publication-observations`, options).then(r => r.data);
export const recordPublicationObservation = (id, payload, options = {}) => api.post(`/tiktok-autopost/jobs/${encodeURIComponent(id)}/publication-observations`, payload, options).then(r => r.data);

// ── AI Production Co-Pilot APIs ──
export const createCopilotSession = (productId, initialPrompt = '') =>
  api.post('/copilot/sessions', { product_id: productId, initial_prompt: initialPrompt }).then(r => r.data);

export const getCopilotSession = (sessionId) =>
  api.get(`/copilot/sessions/${encodeURIComponent(sessionId)}`).then(r => r.data);

export const sendCopilotChatMessage = (sessionId, message) =>
  api.post(`/copilot/sessions/${encodeURIComponent(sessionId)}/chat`, { message }).then(r => r.data);

export const generateCopilotScript = (sessionId, style = 'couple_paper_chat') =>
  api.post(`/copilot/sessions/${encodeURIComponent(sessionId)}/generate-script`, { style }).then(r => r.data);

export const buildCopilotDraft = (sessionId, clipSlug = null, dryRunAudio = false) =>
  api.post(`/copilot/sessions/${encodeURIComponent(sessionId)}/build-draft`, { clip_slug: clipSlug, dry_run_audio: dryRunAudio }).then(r => r.data);

export const renderCopilotSession = (sessionId) =>
  api.post(`/copilot/sessions/${encodeURIComponent(sessionId)}/render`).then(r => r.data);

export default api;
