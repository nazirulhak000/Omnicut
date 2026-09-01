import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

export const getSystemStatus = () => api.get('/status').then(r => r.data);
export const getRawVideos = () => api.get('/videos').then(r => r.data);
export const getExports = () => api.get('/exports').then(r => r.data);
export const getSfxList = () => api.get('/sfx').then(r => r.data);
export const generateScript = (data) => api.post('/script/generate', data).then(r => r.data);
export const generateAiScripts = (data) => api.post('/script/ai-generate', data).then(r => r.data);
export const previewVoice = (data) => api.post('/voice/preview', data).then(r => r.data);
export const startRender = (data) => api.post('/render', data).then(r => r.data);
export const getRenderStatus = (jobId) => api.get(`/render/status/${jobId}`).then(r => r.data);
export const openFolder = (target) => api.post('/open-folder', { target }).then(r => r.data);
export const transcribeMedia = (data) => api.post('/sub-srt/transcribe', data).then(r => r.data);
export const uploadFile = (formData, onProgress) => api.post('/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  onUploadProgress: (progressEvent) => {
    if (onProgress && progressEvent.total) {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent, progressEvent.loaded, progressEvent.total);
    }
  }
}).then(r => r.data);

export const uploadMultipleFiles = (formData, onProgress) => api.post('/upload-multiple', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  onUploadProgress: (progressEvent) => {
    if (onProgress && progressEvent.total) {
      const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress(percent, progressEvent.loaded, progressEvent.total);
    }
  }
}).then(r => r.data);

export const deleteFile = (filePath) => api.post('/delete-file', { file_path: filePath }).then(r => r.data);

// --- Phase 1: product -> clip flow ---

// Returns { mode: 'auto', data } when a key is configured, or
// { mode: 'manual', prompt } for the user to run in their own chat.
export const aiRun = (task, context) => api.post('/ai/prompt', { task, context }).then(r => r.data);
export const aiParse = (task, rawText) => api.post('/ai/parse', { task, raw_text: rawText }).then(r => r.data);
export const getAiStatus = () => api.get('/ai/status').then(r => r.data);

export const getAngles = (params) => api.get('/angles', { params }).then(r => r.data);

export const scrapeAndPlanProduct = (payload) => api.post('/products/scrape-and-plan', typeof payload === 'string' ? { url: payload } : payload).then(r => r.data);
export const getProducts = (status) => api.get('/products', { params: status ? { status } : {} }).then(r => r.data);
export const createProduct = (data) => api.post('/products', data).then(r => r.data);
export const updateProduct = (id, data) => api.patch(`/products/${id}`, data).then(r => r.data);
export const updateAngleStatus = (productId, angleId, status, videoUrl = null) => api.patch(`/products/${productId}/angles/${angleId}`, { status, video_url: videoUrl }).then(r => r.data);
export const deleteProduct = (id) => api.delete(`/products/${id}`).then(r => r.data);

export const getProjects = () => api.get('/projects').then(r => r.data);
export const getProject = (name) => api.get(`/projects/${encodeURIComponent(name)}`).then(r => r.data);
export const updateProjectCues = (name, data) => api.patch(`/projects/${encodeURIComponent(name)}/cues`, data).then(r => r.data);

// Same job shape as startRender, so getRenderStatus polls it too.
export const startReroll = (data) => api.post('/reroll', data).then(r => r.data);

export const getPosts = () => api.get('/posts').then(r => r.data);
export const createPost = (data) => api.post('/posts', data).then(r => r.data);
export const setPostMetrics = (id, metrics) => api.post(`/posts/${id}/metrics`, metrics).then(r => r.data);
export const getPerformance = () => api.get('/posts/performance').then(r => r.data);
export const getAllAssets = () => api.get('/assets/all').then(r => r.data);
export const uploadAsset = (formData) => api.post('/assets/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
}).then(r => r.data);

export default api;
