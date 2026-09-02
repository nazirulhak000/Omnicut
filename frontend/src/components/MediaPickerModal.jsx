import React, { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Film, Search, Check, X, Upload, CheckSquare, Square,
  Loader2, Play, Pause, Sparkles, FolderOpen, AlertCircle, Trash2, Unlink, CheckCircle2, Edit3, Tag
} from 'lucide-react';
import { getRawVideos, uploadFile, deleteFile, removeVideoFromProduct, renameVideo } from '../api';
import { Button, ConfirmModal, Modal } from './ui';

export default function MediaPickerModal({
  isOpen = false,
  onClose,
  title = 'เลือกคลิปวิดีโอ',
  subtitle = null,
  productId = null,
  productName = null,
  selectedVideos = [],
  onConfirm,
  isMultiSelect = true,
  onVideoUploaded
}) {
  const [activeTab, setActiveTab] = useState(productId ? 'product' : 'all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [allVideos, setAllVideos] = useState([]);
  const [productVideos, setProductVideos] = useState([]);
  const [selectedList, setSelectedList] = useState([]);
  const [previewVideoPath, setPreviewVideoPath] = useState(null);

  // Uploading state & Custom Clip Name
  const [customClipName, setCustomClipName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState(null);
  const fileInputRef = useRef(null);

  // Delete & Unlink States
  const [pendingUnlinkVideo, setPendingUnlinkVideo] = useState(null);
  const [pendingDeleteVideo, setPendingDeleteVideo] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Rename States
  const [pendingRenameVideo, setPendingRenameVideo] = useState(null);
  const [renameInputText, setRenameInputText] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameError, setRenameError] = useState(null);

  // Initialize selected list only on modal open transition
  const hasInitializedRef = useRef(false);

  useEffect(() => {
    if (!isOpen) {
      hasInitializedRef.current = false;
      return;
    }

    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      setSelectedList(Array.isArray(selectedVideos) ? [...selectedVideos] : (selectedVideos ? [selectedVideos] : []));
      setSearchQuery('');
      setPreviewVideoPath(null);
      setUploadSuccessMessage(null);
      setUploadError(null);
      setActiveTab(productId ? 'product' : 'all');
      loadVideos();
    }

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    const origBodyOverflow = document.body.style.overflow;
    const origHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = origBodyOverflow || 'unset';
      document.documentElement.style.overflow = origHtmlOverflow || 'unset';
    };
  }, [isOpen]);

  const loadVideos = async () => {
    setLoading(true);
    try {
      const res = await getRawVideos(productId);
      if (res) {
        setAllVideos(res.videos || []);
        setProductVideos(res.product_videos || []);
      }
    } catch (err) {
      console.error('Failed to load videos for picker:', err);
    } finally {
      setLoading(false);
    }
  };

  // Switchable source list
  const currentSourceList = activeTab === 'product' ? productVideos : allVideos;

  // Filtered list by search query
  const filteredVideos = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return currentSourceList;
    return currentSourceList.filter(v =>
      (v.name || '').toLowerCase().includes(q) ||
      (v.path || '').toLowerCase().includes(q) ||
      (v.rel_path || '').toLowerCase().includes(q)
    );
  }, [currentSourceList, searchQuery]);

  const toggleSelect = (videoPath) => {
    if (!isMultiSelect) {
      setSelectedList([videoPath]);
      return;
    }

    setSelectedList(prev => {
      if (prev.includes(videoPath)) {
        return prev.filter(p => p !== videoPath);
      } else {
        return [...prev, videoPath];
      }
    });
  };

  const handleSelectAll = () => {
    const allPaths = filteredVideos.map(v => v.path || v.rel_path);
    setSelectedList(prev => Array.from(new Set([...prev, ...allPaths])));
  };

  const handleClearSelection = () => {
    setSelectedList([]);
  };

  const handleUpload = async (e) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (!files.length) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    setUploadSuccessMessage(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_dir', 'raw');
        if (productId) {
          formData.append('product_id', productId);
        }
        if (customClipName && customClipName.trim()) {
          const suffixIndex = files.length > 1 ? `_${i + 1}` : '';
          formData.append('custom_name', `${customClipName.trim()}${suffixIndex}`);
        }

        const res = await uploadFile(formData, (pct) => {
          const overall = Math.round(((i + (pct / 100)) / files.length) * 100);
          setUploadProgress(overall);
        });

        if (res && res.file) {
          const newPath = res.file.path || res.file.rel_path;
          if (isMultiSelect) {
            setSelectedList(prev => Array.from(new Set([...prev, newPath])));
          } else {
            setSelectedList([newPath]);
          }
          if (onVideoUploaded) onVideoUploaded(res.file);
        }
      }
      await loadVideos();
      const clipLabel = customClipName.trim() ? ` "${customClipName.trim()}"` : '';
      setUploadSuccessMessage(`อัปโหลดสำเร็จ ${files.length} ไฟล์${clipLabel}! คลิปถูกจัดเก็บและผูกเข้ากับสินค้า "${productName || 'นี้'}" เรียบร้อยแล้ว`);
      setCustomClipName(''); // Reset input for next upload
    } catch (err) {
      console.error('Upload error in picker:', err);
      setUploadError(err.friendlyMessage || err.message || 'อัปโหลดไม่สำเร็จ');
    } finally {
      setUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleStartRename = (video) => {
    setPendingRenameVideo(video);
    setRenameInputText((video.name || '').replace(/\.[^/.]+$/, ''));
    setRenameError(null);
  };

  const handleConfirmRename = async (e) => {
    e?.preventDefault();
    if (!pendingRenameVideo || !renameInputText.trim()) return;
    setIsRenaming(true);
    setRenameError(null);
    try {
      const vPath = pendingRenameVideo.path || pendingRenameVideo.rel_path;
      const res = await renameVideo(vPath, renameInputText.trim(), productId);
      if (res && res.file) {
        const newPath = res.file.path || res.file.rel_path;
        setSelectedList(prev => prev.map(p => (p === vPath || p === pendingRenameVideo.path || p === pendingRenameVideo.rel_path) ? newPath : p));
      }
      setPendingRenameVideo(null);
      await loadVideos();
    } catch (err) {
      console.error('Rename error:', err);
      setRenameError(err.friendlyMessage || err.response?.data?.detail || err.message || 'เปลี่ยนชื่อไม่สำเร็จ');
    } finally {
      setIsRenaming(false);
    }
  };

  const confirmUnlink = async () => {
    if (!pendingUnlinkVideo || !productId) return;
    setIsDeleting(true);
    try {
      const vPath = pendingUnlinkVideo.path || pendingUnlinkVideo.rel_path;
      await removeVideoFromProduct(productId, vPath);
      setProductVideos(prev => prev.filter(v => (v.path || v.rel_path) !== vPath));
      setSelectedList(prev => prev.filter(p => p !== vPath && p !== pendingUnlinkVideo.path && p !== pendingUnlinkVideo.rel_path));
      setPendingUnlinkVideo(null);
      await loadVideos();
    } catch (err) {
      console.error('Failed to unlink video:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDeleteVideo) return;
    setIsDeleting(true);
    try {
      const vPath = pendingDeleteVideo.path || pendingDeleteVideo.rel_path;
      await deleteFile(vPath);
      setAllVideos(prev => prev.filter(v => (v.path || v.rel_path) !== vPath));
      setProductVideos(prev => prev.filter(v => (v.path || v.rel_path) !== vPath));
      setSelectedList(prev => prev.filter(p => p !== vPath && p !== pendingDeleteVideo.path && p !== pendingDeleteVideo.rel_path));
      setPendingDeleteVideo(null);
      await loadVideos();
    } catch (err) {
      console.error('Failed to delete file:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm(selectedList);
    }
    if (onClose) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-4 md:p-6 w-screen h-[100dvh] max-h-[100dvh] overflow-hidden overscroll-none animate-fadeIn">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md z-0 transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog Card - True Center & Mobile Safe Height */}
      <div className="relative w-full max-w-4xl bg-[#080B11]/95 backdrop-blur-2xl border border-white/[0.14] rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[85dvh] sm:max-h-[90dvh] z-10 overflow-hidden animate-scaleUp my-auto">
        {/* ── Modal Header (Fixed Top) ── */}
        <div className="flex-shrink-0 p-3.5 sm:p-4 md:p-5 border-b border-white/[0.08] flex items-center justify-between bg-[#0B0F19]/95 z-20">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center text-[#25F4EE] shadow-sm">
              <Film className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-kanit flex items-center gap-2">
                <span>{title}</span>
                {productName && (
                  <span className="text-xs font-normal text-slate-400 truncate max-w-[200px]">
                    ({productName})
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400">
                {subtitle || (isMultiSelect ? 'เลือก 1 หรือหลายคลิปดิบสำหรับนำไปตัดต่อ' : 'เลือกคลิปดิบหลักสำหรับฉากนี้')}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-white/[0.08] rounded-xl transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Scope Tabs & Instant Search Bar ── */}
        <div className="p-3 sm:px-5 border-b border-white/[0.06] bg-black/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Scope Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {productId && (
              <button
                type="button"
                onClick={() => setActiveTab('product')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'product'
                    ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>คลิปของสินค้านี้ ({productVideos.length})</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'all'
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>คลังรวมทั้งหมด ({allVideos.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'upload'
                  ? 'bg-[#FE2C55]/15 text-[#FE2C55] border border-[#FE2C55]/40 ring-1 ring-[#FE2C55]/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>+ อัปโหลดคลิปใหม่</span>
            </button>
          </div>

          {/* Instant Search Bar */}
          {activeTab !== 'upload' && (
            <div className="relative flex-1 sm:max-w-xs">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="ค้นหาชื่อไฟล์คลิป..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-black/50 border border-white/[0.1] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl pl-8 pr-7 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* ── Action Toolbar (Select All / Counter) ── */}
        {activeTab !== 'upload' && (
          <div className="px-4 py-2 bg-black/40 border-b border-white/[0.04] flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span>แสดง <strong>{filteredVideos.length}</strong> ไฟล์</span>
              {selectedList.length > 0 && (
                <span className="px-2 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE] font-bold font-mono">
                  เลือกแล้ว {selectedList.length} คลิป
                </span>
              )}
            </div>

            {isMultiSelect && filteredVideos.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-slate-400 hover:text-[#25F4EE] transition-colors cursor-pointer font-semibold"
                >
                  เลือกทั้งหมด
                </button>
                <span className="text-slate-600">|</span>
                <button
                  type="button"
                  onClick={handleClearSelection}
                  className="text-slate-400 hover:text-rose-400 transition-colors cursor-pointer font-semibold"
                >
                  ล้างการเลือก
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Content Grid / Upload View ── */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-3 sm:p-5 no-scrollbar min-h-0">
          {loading ? (
            <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-3">
              <Loader2 className="w-7 h-7 animate-spin text-[#25F4EE]" />
              <p className="text-xs">กำลังโหลดรายการคลิป...</p>
            </div>
          ) : activeTab === 'upload' ? (
            /* Upload Dropzone Tab (iOS Safari & Android & Desktop Optimized) */
            <div className="max-w-md mx-auto py-4 sm:py-6 space-y-4">
              {/* Optional Custom Clip Name Input */}
              <div className="space-y-1.5 text-left bg-black/40 p-3.5 rounded-2xl border border-white/[0.08]">
                <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>ตั้งชื่อคลิป (ตัวเลือก):</span>
                </label>
                <input
                  type="text"
                  placeholder="เช่น มุมแกะกล่อง, รีวิวสวิตช์ (เว้นว่างไว้จะใช้ชื่อไฟล์เดิม)"
                  value={customClipName}
                  onChange={(e) => setCustomClipName(e.target.value)}
                  className="w-full bg-black/60 border border-white/[0.12] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
                />
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  ตั้งชื่อคลิปก่อนเลือกไฟล์ เพื่อให้ค้นหาและหยิบไปตัดต่อง่าย
                </p>
              </div>

              {/* Native Label-based iOS/Desktop Dropzone */}
              <label
                htmlFor="media-picker-file-input"
                className="relative block p-6 sm:p-8 rounded-2xl border-2 border-dashed border-[#25F4EE]/40 hover:border-[#25F4EE] bg-[#25F4EE]/[0.02] hover:bg-[#25F4EE]/[0.05] active:bg-[#25F4EE]/[0.08] transition-all text-center space-y-3 cursor-pointer select-none"
              >
                <input
                  id="media-picker-file-input"
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  multiple={isMultiSelect}
                  onChange={handleUpload}
                  disabled={uploading}
                  className="sr-only"
                />
                <div className="w-14 h-14 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center mx-auto text-[#25F4EE] shadow-lg shadow-[#25F4EE]/10">
                  <Upload className="w-7 h-7 stroke-[2.2]" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-white font-kanit">เลือกวิดีโอจากอุปกรณ์</h4>
                  <p className="text-xs text-slate-400 mt-1">เปิดคลังรูปภาพหรือไฟล์ในเครื่อง รองรับ MOV, MP4, 4K HDR</p>
                </div>
                <div className="inline-flex items-center justify-center font-bold px-4 py-2 rounded-xl text-xs gap-2 bg-[#25F4EE] text-slate-950 shadow-md">
                  <Upload className="w-4 h-4" />
                  <span>เปิดคลังวิดีโอหรือเลือกไฟล์</span>
                </div>
              </label>

              {uploading && (
                <div className="space-y-1.5 p-3 rounded-xl bg-black/40 border border-white/[0.08]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-cyan-300 font-bold">กำลังอัปโหลด...</span>
                    <span className="text-white font-mono">{uploadProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold">อัปโหลดไม่สำเร็จ</div>
                    <div className="text-[11px] text-rose-400/90 mt-0.5">{uploadError}</div>
                  </div>
                </div>
              )}

              {uploadSuccessMessage && (
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs space-y-3">
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400 mt-0.5" />
                    <div>
                      <div className="font-bold text-sm text-white">อัปโหลดคลิปสำเร็จ!</div>
                      <div className="text-xs text-emerald-300/90 mt-0.5">{uploadSuccessMessage}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="primary"
                      size="sm"
                      icon={Sparkles}
                      onClick={() => setActiveTab('product')}
                      className="w-full justify-center"
                    >
                      ไปดูและเลือกคลิปในแท็บ "คลิปของสินค้านี้" ({productVideos.length})
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : filteredVideos.length === 0 ? (
            /* Empty Search/List State */
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-3">
              <Film className="w-10 h-10 opacity-30 text-slate-400" />
              <div>
                <p className="text-sm font-bold text-slate-300">ไม่พบคลิปดิบที่ตรงกับเงื่อนไข</p>
                <p className="text-xs text-slate-500 mt-1">
                  {searchQuery ? `ลองค้นหาด้วยคำอื่น หรือสลับไปดูแท็บคลังรวม` : `ยังไม่มีคลิปดิบในหมวดนี้ — สามารถกดแท็บ "อัปโหลดคลิปใหม่" ได้ทันที`}
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                icon={Upload}
                onClick={() => setActiveTab('upload')}
              >
                + อัปโหลดคลิปเข้าสู่ระบบ
              </Button>
            </div>
          ) : (
            /* Video Grid Cards */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {filteredVideos.map((video) => {
                const videoPath = video.path || video.rel_path;
                const isSelected = selectedList.includes(videoPath) || selectedList.includes(video.path) || selectedList.includes(video.rel_path);
                const isPlaying = previewVideoPath === videoPath;
                const videoUrl = `/api/media/${video.rel_path || video.path}`;

                return (
                  <div
                    key={videoPath}
                    onClick={() => toggleSelect(videoPath)}
                    className={`group relative rounded-xl border p-3 transition-all cursor-pointer flex flex-col justify-between space-y-2.5 ${
                      isSelected
                        ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE] shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
                        : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.25] hover:bg-white/[0.02]'
                    }`}
                  >
                    {/* Video Player / Thumbnail Preview Area */}
                    <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-black border border-white/[0.06] flex items-center justify-center group-hover:shadow-md transition-all">
                      {isPlaying ? (
                        <video
                          src={videoUrl}
                          autoPlay
                          controls
                          className="w-full h-full object-cover"
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-tr from-slate-950 to-slate-900">
                          <Film className="w-8 h-8 text-slate-700 group-hover:text-[#25F4EE] transition-colors" />

                          {/* Quick Preview Play Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewVideoPath(isPlaying ? null : videoPath);
                            }}
                            className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-black/60 hover:bg-[#25F4EE] text-white hover:text-slate-950 flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-lg cursor-pointer"
                            title="ดูตัวอย่างวิดีโอ"
                          >
                            <Play className="w-4 h-4 ml-0.5" />
                          </button>
                        </div>
                      )}

                      {/* Checkbox Overlay Top-Right */}
                      <div className="absolute top-2 right-2 pointer-events-none">
                        <div className={`w-6 h-6 rounded-lg flex items-center justify-center transition-all ${
                          isSelected
                            ? 'bg-[#25F4EE] text-slate-950 shadow-md ring-2 ring-black'
                            : 'bg-black/60 border border-white/[0.3] text-transparent'
                        }`}>
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </div>
                      </div>

                      {/* Size Badge Bottom-Left */}
                      {video.size_mb && (
                        <div className="absolute bottom-2 left-2 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-mono text-slate-300 border border-white/[0.1]">
                          {video.size_mb} MB
                        </div>
                      )}
                    </div>

                    {/* Meta Info & Actions Bar */}
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center justify-between gap-1.5">
                        <h4 className={`text-xs font-bold truncate leading-snug flex-1 ${isSelected ? 'text-[#25F4EE]' : 'text-white'}`} title={video.name}>
                          {video.name}
                        </h4>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartRename(video);
                          }}
                          className="p-1 rounded-md text-slate-400 hover:text-[#25F4EE] hover:bg-white/[0.08] transition-colors cursor-pointer flex-shrink-0"
                          title="แก้ไขชื่อคลิปนี้"
                        >
                          <Edit3 className="w-3 h-3" />
                        </button>
                      </div>

                      <p className="text-[10px] text-slate-500 font-mono truncate">
                        {video.rel_path || video.path}
                      </p>

                      {/* Card Action Buttons (Unlink & Delete) */}
                      <div className="flex items-center justify-between pt-1.5 mt-1 border-t border-white/[0.06]">
                        {activeTab === 'product' && productId ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPendingUnlinkVideo(video);
                            }}
                            className="px-2 py-0.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
                            title="ปลดคลิปออกจากสินค้านี้"
                          >
                            <Unlink className="w-2.5 h-2.5" />
                            <span>ปลดออกจากสินค้านี้</span>
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-500">คลิปในคลัง</span>
                        )}

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingDeleteVideo(video);
                          }}
                          className="p-1 rounded-md hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                          title="ลบไฟล์คลิปนี้ถาวร"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Modal Footer Action Bar (Fixed Bottom) ── */}
        <div className="flex-shrink-0 p-3.5 sm:px-5 border-t border-white/[0.08] bg-[#0B0F19]/95 backdrop-blur-xl flex items-center justify-between gap-3 z-20">
          <div className="text-xs text-slate-400 truncate">
            {selectedList.length > 0 ? (
              <span>เลือกแล้ว <strong className="text-[#25F4EE] font-mono font-bold">{selectedList.length}</strong> คลิป</span>
            ) : (
              <span className="text-slate-500">ยังไม่ได้เลือกคลิป</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={onClose}>
              ยกเลิก
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirm}
              icon={Check}
            >
              {selectedList.length > 0 ? `ยืนยัน (${selectedList.length} คลิป)` : 'ยืนยัน'}
            </Button>
          </div>
        </div>
      </div>

      {/* ── Rename Video Modal ── */}
      {pendingRenameVideo && (
        <Modal
          isOpen={!!pendingRenameVideo}
          onClose={() => setPendingRenameVideo(null)}
          title="เปลี่ยนชื่อเรียกคลิป"
          subtitle="ตั้งชื่อภาษาไทยหรืออังกฤษเพื่อง่ายต่อการจำและค้นหา"
          maxWidth="max-w-md"
        >
          <form onSubmit={handleConfirmRename} className="space-y-4 pt-1">
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-bold text-slate-300">
                ชื่อใหม่ของคลิป:
              </label>
              <input
                type="text"
                value={renameInputText}
                onChange={(e) => setRenameInputText(e.target.value)}
                placeholder="เช่น มุมแกะกล่อง, รีวิวสวิตช์ปุ่มพิมพ์"
                autoFocus
                className="w-full bg-black/60 border border-white/[0.15] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
              />
              <p className="text-[11px] text-slate-400 font-mono">
                ชื่อไฟล์เดิม: <span className="text-slate-300">{pendingRenameVideo.name}</span>
              </p>
            </div>

            {renameError && (
              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {renameError}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
              <Button
                variant="secondary"
                type="button"
                onClick={() => setPendingRenameVideo(null)}
                disabled={isRenaming}
              >
                ยกเลิก
              </Button>
              <Button
                variant="primary"
                type="submit"
                loading={isRenaming}
                icon={Check}
              >
                บันทึกชื่อใหม่
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Unlink Video Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!pendingUnlinkVideo}
        onClose={() => setPendingUnlinkVideo(null)}
        onConfirm={confirmUnlink}
        title="ปลดคลิปนี้ออกจากสินค้า?"
        description="คลิปนี้จะไม่แสดงในสินค้านี้ แต่ไฟล์จะถูกเก็บไว้ในคลิปอิสระอย่างปลอดภัย"
        itemName={pendingUnlinkVideo?.name}
        dangerNote="สามารถเพิ่มกลับเข้ามาใหม่จากแท็บคลังรวมได้ตลอดเวลา"
        confirmText="ปลดออกจากสินค้า"
        loading={isDeleting}
        variant="warning"
      />

      {/* ── Delete File Permanent Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!pendingDeleteVideo}
        onClose={() => setPendingDeleteVideo(null)}
        onConfirm={confirmDelete}
        title="ลบไฟล์คลิปดิบนี้ถาวร?"
        description="ไฟล์วิดีโอนี้จะถูกลบออกจากโฟลเดอร์ 01_Raw ในเครื่องอย่างถาวร"
        itemName={pendingDeleteVideo?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบไฟล์ถาวร"
        loading={isDeleting}
        variant="danger"
      />
    </div>,
    document.body
  );
}
