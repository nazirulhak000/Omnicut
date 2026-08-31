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
export const previewVoice = (data) => api.post('/voice/preview', data).then(r => r.data);
export const startRender = (data) => api.post('/render', data).then(r => r.data);
export const getRenderStatus = (jobId) => api.get(`/render/status/${jobId}`).then(r => r.data);
export const openFolder = (target) => api.post('/open-folder', { target }).then(r => r.data);
export const transcribeMedia = (data) => api.post('/sub-srt/transcribe', data).then(r => r.data);
export const openCapCut = () => api.post('/capcut/open').then(r => r.data);
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
export const getAllAssets = () => api.get('/assets/all').then(r => r.data);
export const uploadAsset = (formData) => api.post('/assets/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
}).then(r => r.data);

export default api;
