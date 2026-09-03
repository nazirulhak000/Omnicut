import React, { useState, useEffect, useMemo } from 'react';
import {
  Film, Search, RefreshCw, Upload, Folder, Trash2, Edit3, Link2,
  Unlink, Play, Pause, ChevronDown, ChevronRight, HardDrive,
  Sparkles, Check, AlertCircle, Eye, Box, Tag, Layers, CheckSquare, Square
} from 'lucide-react';
import { getRawVault, reassignRawVideo, renameVideo, deleteFile, batchDeleteRawVideos, getProducts } from '../api';
import { Button, ConfirmModal, Modal, Toast } from './ui';
import { useToast } from '../hooks';
import MediaPickerModal from './MediaPickerModal';

export default function RawVaultPanel() {
  const { toastMessage, toastType, showToast, hideToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [vaultData, setVaultData] = useState({ products: [], unassigned: [], total_clips: 0, total_size_mb: 0 });
  const [productList, setProductList] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'products', 'unassigned', 'large'
  const [collapsedGroups, setCollapsedGroups] = useState({});

  // Video Preview Player
  const [activePreviewPath, setActivePreviewPath] = useState(null);

  // Modals
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadTargetProductId, setUploadTargetProductId] = useState(null);
  const [uploadTargetProductName, setUploadTargetProductName] = useState(null);

  // Rename State
  const [pendingRenameVideo, setPendingRenameVideo] = useState(null);
  const [renameInputText, setRenameInputText] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameError, setRenameError] = useState(null);

  // Reassign / Bind Product State
  const [pendingReassignVideo, setPendingReassignVideo] = useState(null);
  const [targetProductId, setTargetProductId] = useState('');
  const [isReassigning, setIsReassigning] = useState(false);

  // Delete State
  const [pendingDeleteVideo, setPendingDeleteVideo] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Batch Selection
  const [selectedPaths, setSelectedPaths] = useState([]);
  const [pendingBatchDelete, setPendingBatchDelete] = useState(false);

  const fetchVault = async () => {
    setLoading(true);
    try {
      const [vaultRes, prodRes] = await Promise.all([
        getRawVault(),
        getProducts()
      ]);
      if (vaultRes) setVaultData(vaultRes);
      if (prodRes && prodRes.products) setProductList(prodRes.products);
    } catch (err) {
      console.error('Failed to load raw vault data:', err);
      showToast('ไม่สามารถโหลดข้อมูลคลังคลิปดิบได้', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVault();
  }, []);

  const toggleGroup = (groupId) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };

  // Filtered Products and Unassigned Clips
  const filteredProducts = useMemo(() => {
    if (activeFilter === 'unassigned') return [];
    const q = searchQuery.trim().toLowerCase();

    return (vaultData.products || []).map(p => {
      let vids = p.videos || [];
      if (activeFilter === 'large') {
        vids = vids.filter(v => (v.size_mb || 0) >= 50);
      }
      if (q) {
        vids = vids.filter(v =>
          (v.name || '').toLowerCase().includes(q) ||
          (p.product_title || '').toLowerCase().includes(q) ||
          (v.rel_path || '').toLowerCase().includes(q)
        );
      }
      return { ...p, filteredVideos: vids };
    }).filter(p => p.filteredVideos.length > 0 || (searchQuery && (p.product_title || '').toLowerCase().includes(q)));
  }, [vaultData.products, searchQuery, activeFilter]);

  const filteredUnassigned = useMemo(() => {
    if (activeFilter === 'products') return [];
    let list = vaultData.unassigned || [];
    const q = searchQuery.trim().toLowerCase();

    if (activeFilter === 'large') {
      list = list.filter(v => (v.size_mb || 0) >= 50);
    }
    if (q) {
      list = list.filter(v =>
        (v.name || '').toLowerCase().includes(q) ||
        (v.rel_path || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [vaultData.unassigned, searchQuery, activeFilter]);

  // Rename Actions
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
      await renameVideo(vPath, renameInputText.trim(), pendingRenameVideo.product_id);
      showToast('เปลี่ยนชื่อคลิปสำเร็จ', 'success');
      setPendingRenameVideo(null);
      await fetchVault();
    } catch (err) {
      console.error('Rename error:', err);
      setRenameError(err.response?.data?.detail || err.message || 'เปลี่ยนชื่อไม่สำเร็จ');
    } finally {
      setIsRenaming(false);
    }
  };

  // Reassign / Move Actions
  const handleStartReassign = (video) => {
    setPendingReassignVideo(video);
    setTargetProductId(video.product_id || '');
  };

  const handleConfirmReassign = async (e) => {
    e?.preventDefault();
    if (!pendingReassignVideo) return;
    setIsReassigning(true);
    try {
      const vPath = pendingReassignVideo.path || pendingReassignVideo.rel_path;
      await reassignRawVideo({
        video_path: vPath,
        target_product_id: targetProductId || null,
        source_product_id: pendingReassignVideo.product_id || null
      });
      showToast(targetProductId ? 'ผูกคลิปเข้ากับสินค้าเรียบร้อย' : 'ปลดคลิปออกเป็นคลิปอิสระแล้ว', 'success');
      setPendingReassignVideo(null);
      await fetchVault();
    } catch (err) {
      console.error('Reassign error:', err);
      showToast(err.response?.data?.detail || 'จัดการผูกสินค้าไม่สำเร็จ', 'error');
    } finally {
      setIsReassigning(false);
    }
  };

  // Delete Single Action
  const handleConfirmDelete = async () => {
    if (!pendingDeleteVideo) return;
    setIsDeleting(true);
    try {
      const vPath = pendingDeleteVideo.path || pendingDeleteVideo.rel_path;
      await deleteFile(vPath);
      showToast('ลบไฟล์คลิปดิบเรียบร้อยแล้ว', 'success');
      setPendingDeleteVideo(null);
      await fetchVault();
    } catch (err) {
      console.error('Delete error:', err);
      showToast(err.response?.data?.detail || 'ลบไฟล์ไม่สำเร็จ', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Batch Delete
  const handleConfirmBatchDelete = async () => {
    if (!selectedPaths.length) return;
    setIsDeleting(true);
    try {
      const res = await batchDeleteRawVideos(selectedPaths);
      showToast(`ลบไฟล์คลิปสำเร็จ ${res.deleted_count || selectedPaths.length} ไฟล์`, 'success');
      setSelectedPaths([]);
      setPendingBatchDelete(false);
      await fetchVault();
    } catch (err) {
      console.error('Batch delete error:', err);
      showToast('ลบไฟล์กลุ่มไม่สำเร็จ', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const toggleSelectVideo = (path) => {
    setSelectedPaths(prev =>
      prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
    );
  };

  const renderVideoCard = (video, sourceProductId) => {
    const videoPath = video.path || video.rel_path;
    const isSelected = selectedPaths.includes(videoPath);
    const isPlaying = activePreviewPath === videoPath;
    const videoUrl = `/api/media/${video.rel_path || video.path}`;

    return (
      <div
        key={videoPath}
        className={`group relative rounded-2xl border p-3 transition-all flex flex-col justify-between space-y-3 ${
          isSelected
            ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE] shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
            : 'bg-black/40 border-white/[0.08] hover:border-white/[0.25] hover:bg-white/[0.02]'
        }`}
      >
        {/* Video Player Preview Area */}
        <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-black border border-white/[0.06] flex items-center justify-center">
          {isPlaying ? (
            <video
              src={videoUrl}
              autoPlay
              controls
              playsInline
              webkit-playsinline="true"
              className="w-full h-full object-cover"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-tr from-slate-950 to-slate-900 relative">
              <Film className="w-8 h-8 text-slate-700 group-hover:text-[#25F4EE] transition-colors" />

              {/* Play Button Overlay (Visible on mobile touch & hover on desktop) */}
              <button
                type="button"
                onClick={() => setActivePreviewPath(isPlaying ? null : videoPath)}
                className="absolute inset-0 m-auto w-11 h-11 rounded-full bg-black/70 hover:bg-[#25F4EE] text-white hover:text-slate-950 flex items-center justify-center transition-all opacity-90 sm:opacity-0 sm:group-hover:opacity-100 shadow-xl border border-white/20 hover:border-transparent active:scale-90 cursor-pointer"
                title="เล่นตัวอย่างวิดีโอ"
              >
                <Play className="w-4 h-4 ml-0.5 fill-current" />
              </button>
            </div>
          )}

          {/* Checkbox Select Touch Target (Apple HIG >= 44x44px hit-box) */}
          <button
            type="button"
            onClick={() => toggleSelectVideo(videoPath)}
            className="absolute top-1.5 right-1.5 w-11 h-11 flex items-center justify-center z-10 cursor-pointer group/chk"
            title={isSelected ? 'ยกเลิกการเลือก' : 'เลือกคลิปนี้'}
          >
            <div
              className={`w-6 h-6 rounded-lg flex items-center justify-center transition-all ${
                isSelected
                  ? 'bg-[#25F4EE] text-slate-950 shadow-md ring-2 ring-black'
                  : 'bg-black/70 border border-white/[0.3] text-transparent group-hover/chk:border-[#25F4EE]'
              }`}
            >
              <Check className="w-3.5 h-3.5 stroke-[3]" />
            </div>
          </button>

          {/* Size Badge Bottom-Left */}
          {video.size_mb && (
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-black/80 backdrop-blur-sm text-[10px] font-mono text-slate-300 border border-white/[0.1] shadow-sm">
              {video.size_mb} MB
            </div>
          )}
        </div>

        {/* Video Info & Controls */}
        <div className="space-y-2 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-xs sm:text-sm font-bold text-white truncate flex-1 leading-snug" title={video.name}>
              {video.name}
            </h4>
            {/* Rename Icon (Touch-Friendly >= 36x36px on mobile) */}
            <button
              type="button"
              onClick={() => handleStartRename(video)}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-[#25F4EE] hover:bg-white/[0.08] active:bg-white/[0.15] transition-colors cursor-pointer flex-shrink-0"
              title="เปลี่ยนชื่อคลิป"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
          </div>

          <p className="text-[10px] text-slate-500 font-mono truncate select-all">
            {video.rel_path || video.path}
          </p>

          {/* Bottom Actions Toolbar (Touch-Friendly Ergonomics) */}
          <div className="flex items-center justify-between pt-2.5 border-t border-white/[0.06] gap-2">
            <button
              type="button"
              onClick={() => handleStartReassign(video)}
              className="flex-1 py-2 px-3 rounded-xl bg-white/[0.04] hover:bg-[#25F4EE]/15 active:bg-[#25F4EE]/25 text-slate-300 hover:text-[#25F4EE] border border-white/[0.08] text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-98"
              title={sourceProductId ? "ย้าย/สลับสินค้า" : "ผูกคลิปเข้ากับสินค้า"}
            >
              <Link2 className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">{sourceProductId ? "ย้ายสินค้า" : "ผูกสินค้า"}</span>
            </button>

            <button
              type="button"
              onClick={() => setPendingDeleteVideo(video)}
              className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/[0.02] hover:bg-rose-500/20 active:bg-rose-500/30 text-slate-500 hover:text-rose-400 border border-white/[0.04] hover:border-rose-500/30 transition-all cursor-pointer flex-shrink-0"
              title="ลบไฟล์คลิปดิบนี้ถาวร"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300 relative pb-10">
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ── Top Header & Storage Summary ── */}
      <div className="rounded-3xl border border-white/[0.08] bg-[#0B0F19]/80 backdrop-blur-xl p-5 sm:p-7 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#25F4EE]/10 to-[#FE2C55]/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 relative z-10">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold tracking-wide uppercase">
              <Film className="w-3.5 h-3.5" />
              <span>คลังคลิปดิบ</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-kanit">
              คลังคลิปดิบ
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
              จัดการคลิปวิดีโอต้นฉบับ แยกตามสินค้าหรือคลิปอิสระ
            </p>
          </div>

          {/* Storage Metrics Cards */}
          <div className="flex items-center flex-wrap gap-2.5 sm:gap-3">
            <div className="flex-1 sm:flex-initial px-4 py-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-3 shadow-inner min-w-[130px]">
              <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0">
                <Film className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400 font-medium">คลิปดิบทั้งหมด</div>
                <div className="text-base font-black text-white font-mono">{vaultData.total_clips || 0} <span className="text-xs font-normal text-slate-400">ไฟล์</span></div>
              </div>
            </div>

            <div className="flex-1 sm:flex-initial px-4 py-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-3 shadow-inner min-w-[130px]">
              <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 flex-shrink-0">
                <HardDrive className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400 font-medium">ความจุรวม</div>
                <div className="text-base font-black text-white font-mono">{vaultData.total_size_mb || 0} <span className="text-xs font-normal text-slate-400">MB</span></div>
              </div>
            </div>

            <Button
              variant="primary"
              icon={Upload}
              onClick={() => {
                setUploadTargetProductId(null);
                setUploadTargetProductName(null);
                setUploadModalOpen(true);
              }}
              className="w-full sm:w-auto shadow-lg shadow-[#25F4EE]/20 justify-center"
            >
              อัปโหลดคลิปใหม่
            </Button>
          </div>
        </div>

        {/* ── Search & Filter Tool Bar with Clear Button ── */}
        <div className="mt-6 pt-5 border-t border-white/[0.06] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3.5 relative z-10">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="ค้นหาชื่อคลิป, สินค้า, หรือโฟลเดอร์..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/50 border border-white/[0.1] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl pl-10 pr-9 py-2.5 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white flex items-center justify-center text-xs transition-colors cursor-pointer"
                title="ล้างคำค้นหา"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 sm:pb-0 touch-pan-x">
            <button
              type="button"
              onClick={() => setActiveFilter('all')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap active:scale-95 ${
                activeFilter === 'all'
                  ? 'bg-white/15 text-white border border-white/30 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              ทั้งหมด ({vaultData.total_clips || 0})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('products')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 active:scale-95 ${
                activeFilter === 'products'
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                  : 'text-slate-400 hover:text-[#25F4EE] hover:bg-white/[0.04]'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span>ผูกสินค้า ({vaultData.products?.reduce((acc, p) => acc + (p.video_count || 0), 0) || 0})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('unassigned')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 active:scale-95 ${
                activeFilter === 'unassigned'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-amber-300 hover:bg-white/[0.04]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>คลิปอิสระ ({vaultData.unassigned?.length || 0})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('large')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 active:scale-95 ${
                activeFilter === 'large'
                  ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-rose-300 hover:bg-white/[0.04]'
              }`}
            >
              <span>ไฟล์ใหญ่</span>
            </button>

            <button
              type="button"
              onClick={fetchVault}
              disabled={loading}
              className="p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/[0.08] transition-all cursor-pointer ml-1 active:scale-95 flex-shrink-0"
              title="รีเฟรชข้อมูล"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#25F4EE]' : ''}`} />
            </button>
          </div>
        </div>

        {/* Batch Selection Action Bar */}
        {selectedPaths.length > 0 && (
          <div className="mt-4 p-3.5 rounded-2xl bg-[#FE2C55]/10 border border-[#FE2C55]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in slide-in-from-top-2 duration-200">
            <span className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-[#FE2C55] flex-shrink-0" />
              <span>เลือกคลิปดิบอยู่ <strong className="font-mono text-[#25F4EE]">{selectedPaths.length}</strong> คลิป</span>
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSelectedPaths([])}
                className="flex-1 sm:flex-initial px-3.5 py-2 rounded-xl text-xs text-slate-400 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] transition-all cursor-pointer text-center"
              >
                ยกเลิก
              </button>
              <Button
                variant="danger"
                size="sm"
                icon={Trash2}
                onClick={() => setPendingBatchDelete(true)}
                className="flex-1 sm:flex-initial justify-center"
              >
                ลบ {selectedPaths.length} คลิป
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* ── Products & Unassigned Footage Accordion ── */}
      {loading ? (
        <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-[#25F4EE]" />
          <p className="text-sm font-medium">กำลังโหลดคลังคลิปดิบ...</p>
        </div>
      ) : filteredProducts.length === 0 && filteredUnassigned.length === 0 ? (
        <div className="p-12 rounded-3xl border border-white/[0.08] bg-[#0B0F19]/60 text-center space-y-4">
          <Film className="w-12 h-12 text-slate-600 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white">ไม่พบคลิปดิบที่ตรงกับเงื่อนไข</h3>
            <p className="text-xs text-slate-400">ลองเปลี่ยนคำค้นหา หรือกดปุ่มอัปโหลดคลิปใหม่เข้าสู่ระบบ</p>
          </div>
          <Button
            variant="primary"
            icon={Upload}
            onClick={() => setUploadModalOpen(true)}
          >
            อัปโหลดคลิปดิบเข้าคลัง
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Product-Scoped Video Groups */}
          {filteredProducts.map((product) => {
            const isCollapsed = collapsedGroups[product.product_id];
            const videos = product.filteredVideos || [];

            return (
              <div
                key={product.product_id}
                className="rounded-3xl border border-white/[0.08] bg-[#0B0F19]/70 backdrop-blur-md overflow-hidden transition-all shadow-xl hover:border-white/[0.15]"
              >
                {/* Group Header */}
                <div
                  onClick={() => toggleGroup(product.product_id)}
                  className="p-4 sm:p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors select-none"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <button
                      type="button"
                      className="w-7 h-7 rounded-lg bg-white/[0.04] text-slate-400 hover:text-white flex items-center justify-center transition-colors flex-shrink-0"
                    >
                      {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>

                    {product.product_cover ? (
                      <img
                        src={product.product_cover}
                        alt={product.product_title}
                        className="w-10 h-10 rounded-xl object-cover border border-white/[0.1] flex-shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 flex-shrink-0">
                        <Box className="w-5 h-5" />
                      </div>
                    )}

                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm sm:text-base font-black text-white truncate font-kanit">
                          {product.product_title}
                        </h3>
                        {product.category && (
                          <span className="px-2 py-0.5 rounded-md bg-white/[0.06] text-[10px] text-slate-300 font-medium">
                            {product.category}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        ID: {product.product_id}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                    <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
                      <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] font-mono font-bold text-white">
                        {videos.length} คลิป
                      </span>
                      <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] font-mono text-cyan-300">
                        {product.total_size_mb} MB
                      </span>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      icon={Upload}
                      onClick={() => {
                        setUploadTargetProductId(product.product_id);
                        setUploadTargetProductName(product.product_title);
                        setUploadModalOpen(true);
                      }}
                      className="px-2.5 py-1.5 sm:px-3 sm:py-2 text-xs"
                    >
                      <span className="hidden xs:inline sm:inline">เพิ่มคลิป</span>
                      <span className="inline xs:hidden sm:hidden">เพิ่ม</span>
                    </Button>
                  </div>
                </div>

                {/* Group Body (Video Grid) */}
                {!isCollapsed && (
                  <div className="p-4 sm:p-5 pt-0 border-t border-white/[0.04]">
                    {videos.length === 0 ? (
                      <div className="py-8 text-center text-slate-500 text-xs">
                        ยังไม่มีคลิปดิบในสินค้านี้ — กดปุ่ม "เพิ่มคลิป" เพื่ออัปโหลด
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5 mt-3">
                        {videos.map((video) => renderVideoCard(video, product.product_id))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Unassigned / B-Roll Footage Shelf */}
          {filteredUnassigned.length > 0 && (
            <div className="rounded-3xl border border-amber-500/20 bg-[#0B0F19]/70 backdrop-blur-md overflow-hidden transition-all shadow-xl">
              <div
                onClick={() => toggleGroup('unassigned_group')}
                className="p-4 sm:p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors select-none"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <button
                    type="button"
                    className="w-7 h-7 rounded-lg bg-white/[0.04] text-slate-400 hover:text-white flex items-center justify-center transition-colors flex-shrink-0"
                  >
                    {collapsedGroups['unassigned_group'] ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
                    <Layers className="w-5 h-5" />
                  </div>

                  <div className="min-w-0">
                    <h3 className="text-sm sm:text-base font-black text-amber-300 truncate font-kanit flex items-center gap-2">
                      <span>คลิปอิสระ (ยังไม่ผูกสินค้า)</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      คลิปที่ยังไม่ได้ผูกกับสินค้า สามารถเลือกผูกเข้าสินค้าใดก็ได้ทันที
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                  <span className="px-2.5 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 font-mono font-bold text-amber-300 text-xs">
                    {filteredUnassigned.length} คลิป
                  </span>
                </div>
              </div>

              {!collapsedGroups['unassigned_group'] && (
                <div className="p-4 sm:p-5 pt-0 border-t border-white/[0.04]">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5 mt-3">
                    {filteredUnassigned.map((video) => renderVideoCard(video, null))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

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
                className="w-full bg-black/60 border border-white/[0.15] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl px-3.5 py-2.5 text-[16px] sm:text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
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

      {/* ── Reassign / Bind Product Modal ── */}
      {pendingReassignVideo && (
        <Modal
          isOpen={!!pendingReassignVideo}
          onClose={() => setPendingReassignVideo(null)}
          title="ผูกหรือย้ายคลิปเข้ากับสินค้า"
          subtitle={`กำหนดสินค้าปลายทางสำหรับคลิป "${pendingReassignVideo.name}"`}
          maxWidth="max-w-lg"
        >
          <form onSubmit={handleConfirmReassign} className="space-y-4 pt-1">
            <div className="space-y-2 text-left">
              <label className="text-xs font-bold text-slate-300">
                เลือกสินค้าที่ต้องการผูกคลิปนี้:
              </label>
              <select
                value={targetProductId}
                onChange={(e) => setTargetProductId(e.target.value)}
                className="w-full bg-black/60 border border-white/[0.15] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE] rounded-xl px-3.5 py-2.5 text-[16px] sm:text-xs text-white focus:outline-none transition-all"
              >
                <option value="">-- ปลดเป็นคลิปอิสระ --</option>
                {productList.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} (ID: {p.id})
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-400">
                เมื่อเลือกสินค้า คลิปจะถูกย้ายเข้าโฟลเดอร์ของสินค้านั้น และพร้อมให้หยิบไปตัดต่อทันที
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
              <Button
                variant="secondary"
                type="button"
                onClick={() => setPendingReassignVideo(null)}
                disabled={isReassigning}
              >
                ยกเลิก
              </Button>
              <Button
                variant="primary"
                type="submit"
                loading={isReassigning}
                icon={Check}
              >
                ยืนยันการผูกสินค้า
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Single Delete Confirm Modal ── */}
      <ConfirmModal
        isOpen={!!pendingDeleteVideo}
        onClose={() => setPendingDeleteVideo(null)}
        onConfirm={handleConfirmDelete}
        title="ลบไฟล์คลิปดิบนี้ถาวร?"
        description="ไฟล์วิดีโอนี้จะถูกลบออกจากดิสก์ในเครื่องอย่างถาวร"
        itemName={pendingDeleteVideo?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบไฟล์ถาวร"
        loading={isDeleting}
        variant="danger"
      />

      {/* ── Batch Delete Confirm Modal ── */}
      <ConfirmModal
        isOpen={pendingBatchDelete}
        onClose={() => setPendingBatchDelete(false)}
        onConfirm={handleConfirmBatchDelete}
        title={`ลบไฟล์คลิปดิบ ${selectedPaths.length} รายการถาวร?`}
        description="ไฟล์วิดีโอที่เลือกทั้งหมดจะถูกลบออกจากเครื่องอย่างถาวร"
        itemName={`${selectedPaths.length} ไฟล์คลิปดิบ`}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText={`ลบ ${selectedPaths.length} ไฟล์ถาวร`}
        loading={isDeleting}
        variant="danger"
      />

      {/* ── Quick Upload Media Picker Modal ── */}
      <MediaPickerModal
        isOpen={uploadModalOpen}
        onClose={() => {
          setUploadModalOpen(false);
          fetchVault();
        }}
        productId={uploadTargetProductId}
        productName={uploadTargetProductName}
        title={uploadTargetProductName ? `อัปโหลดคลิปเข้า: ${uploadTargetProductName}` : 'อัปโหลดคลิปดิบเข้าคลัง'}
        onConfirm={() => {
          setUploadModalOpen(false);
          fetchVault();
        }}
        onVideoUploaded={() => {
          fetchVault();
        }}
      />
    </div>
  );
}
