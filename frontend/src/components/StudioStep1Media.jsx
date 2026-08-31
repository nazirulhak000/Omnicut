import React, { useState, useRef } from 'react';
import { 
  Video, Upload, HardDrive, CheckCircle2, FileVideo, 
  AlertCircle, Smartphone, Loader2, Sparkles, FolderUp, 
  Film, Trash2, Play, AlertTriangle
} from 'lucide-react';
import { uploadFile, uploadMultipleFiles, deleteFile } from '../api';

export default function StudioStep1Media({
  videos,
  selectedVideo,
  setSelectedVideo,
  onVideoUploaded,
  onVideoDeleted
}) {
  const [sourceMode, setSourceMode] = useState('local'); // 'local' | 'upload'
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStats, setUploadStats] = useState({ loadedMB: 0, totalMB: 0 });
  const [uploadError, setUploadError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  const handleFiles = async (filesList) => {
    if (!filesList || filesList.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    const files = Array.from(filesList);

    try {
      if (files.length === 1) {
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('target_dir', 'inbox');

        const res = await uploadFile(formData, (percent, loaded, total) => {
          setUploadProgress(percent);
          setUploadStats({
            loadedMB: (loaded / (1024 * 1024)).toFixed(1),
            totalMB: (total / (1024 * 1024)).toFixed(1)
          });
        });

        if (res.file) {
          onVideoUploaded(res.file);
          setSelectedVideo(res.file.path);
        }
      } else {
        const formData = new FormData();
        files.forEach(f => formData.append('files', f));
        formData.append('target_dir', 'inbox');

        const res = await uploadMultipleFiles(formData, (percent, loaded, total) => {
          setUploadProgress(percent);
          setUploadStats({
            loadedMB: (loaded / (1024 * 1024)).toFixed(1),
            totalMB: (total / (1024 * 1024)).toFixed(1)
          });
        });

        if (res.files && res.files.length > 0) {
          res.files.forEach(f => onVideoUploaded(f));
          setSelectedVideo(res.files[0].path);
        }
      }
    } catch (err) {
      setUploadError(err.response?.data?.detail || err.message || 'การอัปโหลดไฟล์ล้มเหลว');
    } finally {
      setUploading(false);
    }
  };

  const handleInputChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = ''; // Reset input
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const videoEls = document.querySelectorAll('video');
      videoEls.forEach(v => {
        try {
          v.pause();
        } catch (e) {}
      });

      await deleteFile(deleteTarget.path);
      if (onVideoDeleted) onVideoDeleted(deleteTarget.path);
      setDeleteTarget(null);
    } catch (err) {
      alert('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const selectedVideoObj = videos.find(v => v.path === selectedVideo || v.rel_path === selectedVideo);

  return (
    <div className="glass-card p-4 sm:p-5 mb-6">
      {/* Card Header */}
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs font-black tracking-wider text-white uppercase rounded-full bg-gradient-to-r from-[#FE2C55] to-[#FF0050] shadow-md shadow-[#FE2C55]/30">
            STEP 1
          </span>
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <Video className="w-5 h-5 text-[#25F4EE]" />
            วัตถุดิบวิดีโอสินค้า (Raw Footage)
          </h2>
        </div>
        <span className="text-xs text-slate-400 font-mono hidden sm:inline">
          {videos.length} คลิปในระบบ
        </span>
      </div>

      {/* Source Switcher */}
      <div className="grid grid-cols-2 gap-2 mb-4 p-1 bg-black/40 rounded-xl border border-white/5">
        <button
          onClick={() => setSourceMode('local')}
          className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            sourceMode === 'local'
              ? 'bg-[#232A3B] text-white shadow-md border border-white/10'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <HardDrive className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span>เลือกจากเครื่อง ({videos.length})</span>
        </button>
        <button
          onClick={() => setSourceMode('upload')}
          className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            sourceMode === 'upload'
              ? 'bg-[#232A3B] text-white shadow-md border border-white/10'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Upload className="w-3.5 h-3.5 text-[#FE2C55]" />
          <span>อัปโหลดใหม่ / มือถือ</span>
        </button>
      </div>

      {/* Local Video Select Mode */}
      {sourceMode === 'local' ? (
        <div className="space-y-3">
          {videos.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  เลือกคลิปวิดีโอสินค้าที่ต้องการตัดต่อ:
                </label>
                {selectedVideoObj && (
                  <button
                    onClick={() => setDeleteTarget(selectedVideoObj)}
                    className="text-[11px] font-semibold text-red-400 hover:text-red-300 flex items-center gap-1 cursor-pointer transition-colors"
                    title="ลบคลิปที่เลือกอยู่นี้ออกจากเครื่อง"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>ลบคลิปนี้</span>
                  </button>
                )}
              </div>
              <select
                value={selectedVideo || ''}
                onChange={(e) => setSelectedVideo(e.target.value)}
                className="w-full py-3 px-3.5 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm font-medium focus:outline-none focus:border-[#FE2C55] transition-colors"
              >
                {videos.map((v) => (
                  <option key={v.path} value={v.path}>
                    📹 {v.name} ({v.size_mb} MB - {v.modified_time})
                  </option>
                ))}
              </select>

              {/* Quick Visual Clip Carousel/Chips */}
              <div className="mt-3 flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
                {videos.slice(0, 8).map((v) => {
                  const isCur = v.path === selectedVideo || v.rel_path === selectedVideo;
                  return (
                    <div
                      key={v.path}
                      className={`flex-shrink-0 flex items-center gap-1.5 p-2 rounded-xl border text-xs transition-all ${
                        isCur
                          ? 'bg-[#FE2C55]/15 border-[#FE2C55] text-white ring-1 ring-[#FE2C55]'
                          : 'bg-black/30 border-white/5 text-slate-400 hover:text-slate-200 hover:bg-black/50'
                      }`}
                    >
                      <button
                        onClick={() => setSelectedVideo(v.path)}
                        className="text-left cursor-pointer flex-1 min-w-0"
                      >
                        <div className="flex items-center gap-1.5 font-bold truncate max-w-[120px]">
                          <Film className="w-3 h-3 flex-shrink-0 text-[#25F4EE]" />
                          <span className="truncate">{v.name}</span>
                        </div>
                        <div className="text-[10px] opacity-70 mt-0.5">{v.size_mb} MB</div>
                      </button>
                      <button
                        onClick={() => setDeleteTarget(v)}
                        className="p-1 text-slate-500 hover:text-red-400 transition-colors cursor-pointer"
                        title={`ลบ ${v.name}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex flex-col sm:flex-row items-center gap-3">
              <AlertCircle className="w-6 h-6 flex-shrink-0" />
              <div className="text-center sm:text-left">
                <div className="font-bold">ยังไม่พบไฟล์วิดีโอในโฟลเดอร์ 00_Inbox หรือ 01_Raw</div>
                <div className="text-slate-400 mt-0.5">กดแท็บ "อัปโหลดใหม่ / มือถือ" ด้านบนเพื่อส่งไฟล์ได้ทันทีครับ</div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Upload Area (Mobile & Desktop Drag/Drop) */
        <div className="space-y-3">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 flex flex-col items-center justify-center cursor-pointer transition-all group text-center ${
              isDragging
                ? 'border-[#25F4EE] bg-[#25F4EE]/10 scale-[1.01]'
                : 'border-white/20 hover:border-[#FE2C55]/60 bg-black/25 hover:bg-black/45'
            }`}
          >
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              {uploading ? (
                <Loader2 className="w-7 h-7 text-[#25F4EE] animate-spin" />
              ) : (
                <FolderUp className="w-7 h-7 text-slate-300 group-hover:text-[#FE2C55] transition-colors" />
              )}
            </div>

            <span className="text-sm sm:text-base font-bold text-slate-200 group-hover:text-white">
              {uploading 
                ? `กำลังอัปโหลด... ${uploadProgress}% (${uploadStats.loadedMB} / ${uploadStats.totalMB} MB)` 
                : 'แตะเพื่อเลือกวิดีโอจากมือถือ / ลากไฟล์มาวางที่นี่'}
            </span>
            <span className="text-xs text-slate-400 mt-1">
              รองรับไฟล์ .MP4, .MOV, .M4V จากมือถือ iPhone / Android (เลือกพร้อมกันหลายคลิปได้)
            </span>

            {/* Live Upload Progress Bar */}
            {uploading && (
              <div className="w-full max-w-xs mt-4 space-y-1.5">
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-200 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {uploadProgress}% • {uploadStats.loadedMB} MB จาก {uploadStats.totalMB} MB
                </div>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="video/*,video/mp4,video/quicktime,video/x-m4v"
              onChange={handleInputChange}
              disabled={uploading}
              className="hidden"
            />
          </div>

          {uploadError && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>
      )}

      {/* Video Preview Player & Info */}
      {selectedVideo && (
        <div className="mt-4 p-3.5 rounded-2xl bg-black/50 border border-white/10 space-y-2.5">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span className="font-bold text-[#25F4EE] flex items-center gap-1.5 truncate max-w-[280px]">
              <FileVideo className="w-4 h-4 flex-shrink-0" />
              {selectedVideoObj?.name || selectedVideo.split('\\').pop()?.split('/').pop()}
            </span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-slate-400">
                {selectedVideoObj?.size_mb ? `${selectedVideoObj.size_mb} MB` : ''}
              </span>
              <button
                onClick={() => setDeleteTarget(selectedVideoObj || { name: selectedVideo, path: selectedVideo })}
                className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-600 text-red-400 hover:text-white transition-all cursor-pointer"
                title="ลบวิดีโอนี้"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="rounded-xl overflow-hidden border border-white/10 bg-black max-h-[360px] sm:max-h-[420px] flex items-center justify-center relative group">
            <video
              key={selectedVideo}
              controls
              playsInline
              preload="metadata"
              className="w-full max-h-[360px] sm:max-h-[420px] object-contain"
              src={`/api/media/${selectedVideoObj?.rel_path || selectedVideo}`}
            >
              Your browser does not support video playback.
            </video>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-6 glass-panel border border-red-500/40 shadow-2xl rounded-3xl text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/20 text-red-400 flex items-center justify-center mx-auto border border-red-500/30">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">ยืนยันการลบไฟล์วิดีโอ?</h3>
              <p className="text-xs text-slate-300 font-mono break-all bg-black/40 p-2.5 rounded-xl border border-white/5 mt-2">
                {deleteTarget.name}
              </p>
              <p className="text-[11px] text-slate-400 pt-1">
                ไฟล์จะถูกลบออกจากเครื่องอย่างถาวร
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-colors cursor-pointer"
              >
                ยกเลิก
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-600/30 transition-all cursor-pointer"
              >
                {deleting ? 'กำลังลบ...' : 'ยืนยันลบไฟล์'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
