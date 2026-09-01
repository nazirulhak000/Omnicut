import React, { useState, useRef, useMemo, useCallback } from 'react';
import { 
  Video, Upload, HardDrive, CheckCircle2, FileVideo, 
  AlertCircle, Smartphone, Loader2, Sparkles, FolderUp, 
  Film, Trash2, Play, Pause, AlertTriangle, Eye, Check
} from 'lucide-react';
import { uploadFile, uploadMultipleFiles, deleteFile } from '../api';
import { Modal, Button, Badge } from './ui';

export default function StudioStep1Media({
  videos,
  selectedVideo,
  setSelectedVideo,
  productName,
  activeProductContext,
  onVideoUploaded,
  onVideoDeleted
}) {
  const [sourceMode, setSourceMode] = useState('local');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStats, setUploadStats] = useState({ loadedMB: 0, totalMB: 0 });
  const [uploadError, setUploadError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);

  const pName = productName || activeProductContext?.name || activeProductContext?.title || '';
  const pNameLow = pName.toLowerCase();

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
          setUploadStats({ loadedMB: (loaded / (1024 * 1024)).toFixed(1), totalMB: (total / (1024 * 1024)).toFixed(1) });
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
          setUploadStats({ loadedMB: (loaded / (1024 * 1024)).toFixed(1), totalMB: (total / (1024 * 1024)).toFixed(1) });
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

  const handleInputChange = (e) => { handleFiles(e.target.files); e.target.value = ''; };
  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => { setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      if (videoRef.current) {
        try { videoRef.current.pause(); } catch (e) {}
      }
      await deleteFile(deleteTarget.path);
      if (onVideoDeleted) onVideoDeleted(deleteTarget.path);
      setDeleteTarget(null);
    } catch (err) {
      alert('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message));
    } finally { setDeleting(false); }
  };

  const selectedVideoObj = videos.find(v => v.path === selectedVideo || v.rel_path === selectedVideo);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  return (
    <section className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-xs font-bold text-white shadow-md shadow-[#FE2C55]/20">
            1
          </span>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>วิดีโอสินค้าดิบ (Raw B-Roll)</span>
              <span className="text-[10px] font-mono text-[#25F4EE] bg-[#25F4EE]/10 px-2 py-0.5 rounded-full border border-[#25F4EE]/20 font-bold">
                {videos.length} คลิปในระบบ
              </span>
            </h3>
          </div>
        </div>

        {/* Source Mode Switcher */}
        <div className="flex items-center gap-1 p-1 bg-black/40 rounded-xl border border-white/[0.08]">
          <button
            onClick={() => setSourceMode('local')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              sourceMode === 'local'
                ? 'bg-white/[0.1] text-white shadow-sm border border-white/[0.15]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <HardDrive className="w-3.5 h-3.5 inline mr-1 text-[#25F4EE]" />เลือกจากเครื่อง
          </button>
          <button
            onClick={() => setSourceMode('upload')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              sourceMode === 'upload'
                ? 'bg-white/[0.1] text-white shadow-sm border border-white/[0.15]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Upload className="w-3.5 h-3.5 inline mr-1 text-[#FE2C55]" />อัปโหลดเพิ่ม
          </button>
        </div>
      </div>

      {/* Main Card */}
      <div className="glass-card p-4 space-y-3.5">
        {sourceMode === 'local' ? (
          <div className="space-y-3">
            {videos.length > 0 ? (
              <>
                {/* Select Dropdown with active status */}
                <div className="relative">
                  <select
                    value={selectedVideo || ''}
                    onChange={(e) => {
                      setSelectedVideo(e.target.value);
                      setIsPlaying(false);
                    }}
                    className="w-full py-2.5 pl-3.5 pr-8 bg-black/40 border border-white/[0.1] rounded-xl text-white text-xs sm:text-sm font-bold focus:outline-none focus:border-[#25F4EE] transition-colors"
                  >
                    {videos.map((v) => (
                      <option key={v.path} value={v.path} className="bg-[#080B11] text-white">
                        {v.name} ({v.size_mb} MB)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Horizontal Clip Chips Carousel */}
                <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
                  {videos.map((v) => {
                    const isCur = v.path === selectedVideo || v.rel_path === selectedVideo;
                    return (
                      <button
                        key={v.path}
                        onClick={() => {
                          setSelectedVideo(v.path);
                          setIsPlaying(false);
                        }}
                        className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer border ${
                          isCur
                            ? 'bg-[#25F4EE]/20 border-[#25F4EE]/50 text-[#25F4EE] shadow-sm'
                            : 'bg-white/[0.03] border-white/[0.06] text-slate-400 hover:text-white'
                        }`}
                      >
                        <Film className="w-3.5 h-3.5" />
                        <span className="truncate max-w-[120px]">{v.name}</span>
                        {isCur && <Check className="w-3 h-3 text-[#25F4EE]" />}
                      </button>
                    );
                  })}
                </div>

                {/* Product Media Linking Status / Mismatch Warning */}
                {selectedVideoObj && pName && (
                  (() => {
                    const isMismatch = (
                      (pNameLow.includes('logitech') && selectedVideoObj.name.toLowerCase().includes('esseger')) ||
                      (pNameLow.includes('esseger') && selectedVideoObj.name.toLowerCase().includes('logitech')) ||
                      (pNameLow.includes('wave') && selectedVideoObj.name.toLowerCase().includes('cable')) ||
                      (pNameLow.includes('สายชาร์จ') && selectedVideoObj.name.toLowerCase().includes('keyboard'))
                    );
                    const isMatch = (
                      (pNameLow.includes('logitech') && selectedVideoObj.name.toLowerCase().includes('logitech')) ||
                      (pNameLow.includes('esseger') && selectedVideoObj.name.toLowerCase().includes('esseger')) ||
                      (pNameLow.includes('wave') && selectedVideoObj.name.toLowerCase().includes('wave')) ||
                      (pNameLow.includes('สายชาร์จ') && selectedVideoObj.name.toLowerCase().includes('สายชาร์จ'))
                    );

                    if (isMismatch) {
                      return (
                        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-300 animate-fadeIn">
                          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          <div className="space-y-1 flex-1">
                            <div className="font-bold text-amber-300">
                              ข้อสังเกต: คุณกำลังเลือกคลิป "{selectedVideoObj.name}" แต่สคริปต์ปัจจุบันคือ "{pName}"
                            </div>
                            <p className="text-[11px] text-slate-300">
                              คลิปดิบนี้อาจเป็นของสินค้าตัวอื่น แนะนำให้อัปโหลดคลิปของ {pName} หรือถ่ายใหม่เพื่อให้ภาพตรงกับเนื้อหาสคริปต์
                            </p>
                            <button
                              onClick={() => setSourceMode('upload')}
                              className="px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-bold text-[11px] inline-flex items-center gap-1 mt-1 cursor-pointer transition-colors border border-amber-500/40"
                            >
                              <Upload className="w-3 h-3" /> อัปโหลดคลิปดิบสำหรับ {pName}
                            </button>
                          </div>
                        </div>
                      );
                    }

                    if (isMatch) {
                      return (
                        <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-300 animate-fadeIn">
                          <span className="flex items-center gap-1.5 font-bold">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            คลิปดิบนี้ผูกตรงกับสคริปต์สินค้า: {pName}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                            ผูกตรงกัน 100%
                          </span>
                        </div>
                      );
                    }

                    return (
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] flex items-center justify-between text-xs text-slate-400 font-medium">
                        <span>กำลังตัดต่อสคริปต์สำหรับ: <strong className="text-white font-bold">{pName}</strong></span>
                        <span className="text-slate-400 font-mono text-[11px]">ใช้คลิป: {selectedVideoObj.name}</span>
                      </div>
                    );
                  })()
                )}

                {/* Live Mini Video Preview Player */}
                {selectedVideoObj && (
                  <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] flex flex-col sm:flex-row gap-3 items-center">
                    <div className="relative aspect-[9/16] w-28 sm:w-32 bg-black rounded-xl overflow-hidden flex-shrink-0 border border-white/[0.1] group">
                      <video
                        ref={videoRef}
                        src={`/api/media/${selectedVideoObj.path}`}
                        className="w-full h-full object-cover"
                        playsInline
                        muted
                        loop
                        onEnded={() => setIsPlaying(false)}
                      />
                      <button
                        onClick={togglePlay}
                        className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-80 group-hover:opacity-100 transition-opacity cursor-pointer"
                        title={isPlaying ? 'หยุดเล่น' : 'เล่นตัวอย่าง'}
                      >
                        {isPlaying ? (
                          <div className="w-9 h-9 rounded-full bg-black/70 backdrop-blur-md flex items-center justify-center text-white border border-white/20">
                            <Pause className="w-4 h-4" />
                          </div>
                        ) : (
                          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center shadow-lg shadow-[#FE2C55]/30">
                            <Play className="w-4 h-4 ml-0.5 text-white" />
                          </div>
                        )}
                      </button>
                    </div>

                    <div className="flex-1 min-w-0 space-y-1.5 text-left w-full">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-bold text-white truncate max-w-[200px] sm:max-w-xs font-mono">
                          {selectedVideoObj.name}
                        </div>
                        <button
                          onClick={() => setDeleteTarget(selectedVideoObj)}
                          className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          title="ลบคลิปนี้"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 font-mono">
                        <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                          ขนาด: <span className="text-white font-bold">{selectedVideoObj.size_mb} MB</span>
                        </div>
                        <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                          สถานะ: <span className="text-emerald-400 font-bold">พร้อมตัดต่อ</span>
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        ✦ AI Vision Matcher จะสแกนหาจังหวะที่เหมาะสมในคลิปนี้มาประกอบสคริปต์
                      </p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="py-8 text-center space-y-2">
                <FileVideo className="w-10 h-10 mx-auto text-slate-500" />
                <p className="text-xs text-slate-400 font-bold">ยังไม่มีคลิปในระบบ</p>
                <button
                  onClick={() => setSourceMode('upload')}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] text-white text-xs font-bold shadow-md shadow-[#FE2C55]/25 cursor-pointer hover:brightness-110 transition-all"
                >
                  <Upload className="w-3.5 h-3.5 inline mr-1.5" />อัปโหลดคลิปสินค้าทันที
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Upload Dropzone Mode */
          <div className="space-y-3">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 flex flex-col items-center justify-center cursor-pointer transition-all text-center ${
                isDragging
                  ? 'border-[#25F4EE] bg-[#25F4EE]/10 scale-[1.01]'
                  : 'border-white/[0.12] hover:border-[#25F4EE]/60 bg-black/30 hover:bg-black/50'
              }`}
            >
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 border border-white/[0.1] flex items-center justify-center mb-3 text-[#25F4EE] shadow-md">
                {uploading ? (
                  <Loader2 className="w-6 h-6 text-[#25F4EE] animate-spin" />
                ) : (
                  <FolderUp className="w-6 h-6 text-[#25F4EE]" />
                )}
              </div>
              <span className="text-xs sm:text-sm font-bold text-white mb-1">
                {uploading ? `กำลังอัปโหลด... ${uploadProgress}%` : 'ลากไฟล์คลิปมาวาง หรือ คลิกเพื่อเลือก'}
              </span>
              <span className="text-xs text-slate-400">
                รองรับไฟล์ .MP4, .MOV, .M4V จากมือถือและคอมพิวเตอร์
              </span>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="video/*"
                onChange={handleInputChange}
                disabled={uploading}
                className="hidden"
              />
            </div>

            {uploading && (
              <div className="p-3.5 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2">
                <div className="flex justify-between text-xs font-mono text-white">
                  <span>กำลังถ่ายโอนไฟล์...</span>
                  <span className="text-[#25F4EE] font-bold">{uploadStats.loadedMB} / {uploadStats.totalMB} MB</span>
                </div>
                <div className="w-full h-2 bg-white/[0.1] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {uploadError && (
              <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                <span>{uploadError}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="ยืนยันการลบไฟล์?"
        maxWidth="max-w-sm"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 truncate max-w-[220px] font-mono mt-0.5">{deleteTarget?.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setDeleteTarget(null)}
              disabled={deleting}
              className="flex-1"
            >
              ยกเลิก
            </Button>
            <Button
              variant="danger"
              onClick={confirmDelete}
              loading={deleting}
              icon={Trash2}
              className="flex-1"
            >
              ลบไฟล์
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}
