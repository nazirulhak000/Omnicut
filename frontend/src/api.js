import axios from 'axios';
import { sanitizeText, sanitizeScript } from './lib/sanitize';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // 60 seconds default
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

export const deleteFile = (filePath) => api.post('/delete-file', { file_path: filePath }).then(r => r.data);

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
export const updateAngleStatus = (productId, angleId, status, videoUrl = null, projectName = null) =>
  api.patch(`/products/${productId}/angles/${angleId}`, { status, video_url: videoUrl, project_name: projectName }).then(r => r.data);
export const updateAngleVideos = (productId, angleId, selectedVideos) => api.post(`/products/${productId}/angles/${angleId}/videos`, { selected_videos: selectedVideos }).then(r => r.data);
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

export default api;

