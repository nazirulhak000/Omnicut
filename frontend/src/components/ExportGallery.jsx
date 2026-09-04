import React, { useState, useMemo, useEffect, useCallback, memo } from 'react';
import {
  Film, Download, Folder, RefreshCw, Trash2,
  AlertTriangle, Check, Play, Search, Filter, ArrowUpDown,
  Smartphone, CheckSquare, Square, Share2, Copy, FileText, QrCode, Sparkles, HardDrive,
  ShieldAlert, XCircle, CheckCircle2, History, FileQuestion, Link2
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { openFolder, deleteFile, getProducts, linkExportToAngle } from '../api';
import { Modal, Toast, Button, Badge, ConfirmModal } from './ui';
import { useDebounce, useToast } from '../hooks';
import RawVaultPanel from './RawVaultPanel';

// Memoized Export Video Item Card
const ExportCard = memo(function ExportCard({
  item,
  isSelected,
  onToggleSelect,
  onOpenDetail,
  onOpenDelete
}) {
  const nameLow = (item.name || '').toLowerCase();
  const isEsseger = nameLow.includes('esseger') || nameLow.includes('สายชาร์จ');
  const isLogitech = nameLow.includes('logitech') || nameLow.includes('wave');

  return (
    <div
      className={`overflow-hidden transition-all duration-200 flex flex-col justify-between group relative rounded-2xl sm:rounded-3xl border glass-card shadow-lg ${
        isSelected
          ? 'border-[#25F4EE] ring-1 ring-[#25F4EE] bg-[#25F4EE]/5'
          : item.is_qc_rejected
          ? 'border-red-500/50 hover:border-red-400 bg-red-950/10 hover:shadow-red-950/40 ring-1 ring-red-500/20'
          : item.is_previous_version
          ? 'opacity-80 hover:opacity-100 border-amber-500/30 hover:border-amber-400/60 bg-amber-950/10 hover:shadow-amber-950/30 ring-1 ring-amber-500/20'
          : item.is_unlinked
          ? 'border-slate-700/60 hover:border-slate-500/60 bg-slate-900/40'
          : 'border-emerald-500/30 hover:border-emerald-400/70 bg-emerald-950/5 hover:shadow-2xl ring-1 ring-emerald-500/20'
      }`}
    >
      {/* Card Top / Video Thumbnail Area */}
      <div>
        {/* Select Checkbox (Top Left) */}
        <button
          onClick={() => onToggleSelect(item.path)}
          className="absolute top-2.5 left-2.5 sm:top-3 sm:left-3 z-20 w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-black/75 backdrop-blur-md flex items-center justify-center border border-white/20 text-white cursor-pointer hover:border-[#25F4EE] shadow-sm transition-transform active:scale-95"
        >
          {isSelected ? <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#25F4EE]" /> : <Square className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-400" />}
        </button>

        {/* Product Tag Badge + Status Badge (Top Right) */}
        <div className="absolute top-2.5 right-2.5 sm:top-3 sm:right-3 z-20 flex items-center gap-1 sm:gap-1.5 flex-wrap justify-end">
          {item.is_qc_rejected ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-red-600/90 text-white font-black text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-red-400/50">
              <ShieldAlert className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>QC ปัดตก</span>
            </span>
          ) : item.is_previous_version ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-amber-600/90 text-white font-bold text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-amber-400/50">
              <History className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>เวอร์ชันเก่า</span>
            </span>
          ) : item.is_unlinked ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-slate-700/90 text-slate-200 font-bold text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-slate-600/50">
              <FileQuestion className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-slate-300" />
              <span>ภายนอก</span>
            </span>
          ) : item.is_latest ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-emerald-600/90 text-white font-black text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-emerald-400/50">
              <CheckCircle2 className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>ล่าสุด</span>
            </span>
          ) : null}

          {isLogitech ? (
            <Badge variant="slate" size="xs">Logitech</Badge>
          ) : isEsseger ? (
            <Badge variant="cyan" size="xs">Esseger</Badge>
          ) : null}
        </div>

        {/* Video / Poster Preview (9:16 Vertical) */}
        <div
          onClick={() => onOpenDetail(item)}
          className="bg-black aspect-[9/16] w-full flex items-center justify-center relative overflow-hidden cursor-pointer"
        >
          {item.thumbnail_url ? (
            <img
              src={item.thumbnail_url}
              alt={item.name}
              loading="lazy"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <video
              src={`/api/media/${item.rel_path || item.path}#t=1.0`}
              preload="metadata"
              className="w-full h-full object-cover"
              playsInline
              muted
              loop
              onLoadedMetadata={e => {
                try { e.target.currentTime = 1.0; } catch {}
              }}
              onMouseOver={e => e.target.play().catch(() => {})}
              onMouseOut={e => { e.target.pause(); try { e.target.currentTime = 1.0; } catch {} }}
            />
          )}

          {/* Centered Play Button Overlay */}
          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-all flex flex-col items-center justify-center gap-1.5 sm:gap-2 pointer-events-none">
            {item.is_qc_rejected ? (
              <>
                <div className="w-10 h-10 sm:w-13 sm:h-13 rounded-full bg-gradient-to-tr from-red-600 to-rose-600 text-white flex items-center justify-center shadow-xl shadow-red-600/50 ring-2 ring-red-400 ring-offset-2 ring-offset-black/50 transform group-hover:scale-110 transition-all">
                  <Play className="w-4 h-4 sm:w-5 sm:h-5 fill-current ml-0.5 text-white" />
                </div>
                <div className="px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-red-600/90 backdrop-blur-md text-white font-black text-[9px] sm:text-[11px] shadow-lg border border-red-400/60 tracking-wide flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-white" />
                  <span>QC ไม่ผ่าน</span>
                </div>
                {item.qc_note && (
                  <div className="max-w-[85%] text-center text-[9px] sm:text-[10px] text-red-100 font-mono leading-snug px-1.5 sm:px-2 py-0.5 rounded-md bg-black/70 border border-red-500/40 truncate">
                    {item.qc_note}
                  </div>
                )}
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  ดูรายละเอียด (ตรวจ QC)
                </span>
              </>
            ) : item.is_previous_version ? (
              <>
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-tr from-amber-600 to-orange-500 text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
                  <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4 fill-current ml-0.5 text-white" />
                </div>
                <div className="px-2 py-0.5 rounded-full bg-amber-600/80 backdrop-blur-md text-white font-bold text-[9px] sm:text-[10px] shadow-md border border-amber-400/40 tracking-wide flex items-center gap-1">
                  <History className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
                  <span>เวอร์ชันเก่า</span>
                </div>
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด
                </span>
              </>
            ) : (
              <>
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
                  <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4 fill-current ml-0.5 text-white" />
                </div>
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2.5 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด
                </span>
              </>
            )}
          </div>
        </div>

        {/* Video Metadata */}
        <div className="p-2.5 sm:p-4 space-y-1 sm:space-y-1.5 text-left">
          <h4
            onClick={() => onOpenDetail(item)}
            className="text-xs sm:text-sm font-bold text-white truncate cursor-pointer hover:text-[#25F4EE] transition-colors"
            title={item.hook_title || item.name}
          >
            {item.hook_title || item.name}
          </h4>

          {item.product_name && (
            <p className="text-[10px] sm:text-[11px] text-slate-400 truncate" title={item.product_name}>
              {item.product_name}
            </p>
          )}

          <div className="flex items-center justify-between text-[10px] sm:text-xs text-slate-400 font-mono pt-0.5">
            <span className="flex items-center gap-1 text-[#25F4EE] font-bold">
              {item.size_mb} MB
            </span>
            <span className="text-[10px] sm:text-xs text-slate-400">
              {item.modified?.split(' ')?.[0] || item.modified}
            </span>
          </div>
        </div>
      </div>

      {/* Card Action Buttons */}
      <div className="p-2 sm:p-3 pt-0 flex items-center gap-1 sm:gap-1.5 border-t border-white/[0.08] mt-1 sm:mt-2">
        <button
          onClick={() => onOpenDetail(item)}
          className="flex-1 py-1.5 sm:py-2 px-1.5 sm:px-2.5 rounded-lg sm:rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-[11px] sm:text-xs font-bold flex items-center justify-center cursor-pointer transition-colors"
        >
          ดูรายละเอียด
        </button>

        <a
          href={`/api/media/${item.path}`}
          download={item.name}
          className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold transition-colors cursor-pointer flex-shrink-0"
          title="ดาวน์โหลด .MP4"
        >
          <Download className="w-3.5 h-3.5" />
        </a>

        <button
          onClick={() => onOpenDelete(item)}
          className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-bold transition-colors cursor-pointer flex-shrink-0"
          title="ลบวิดีโอ"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
});

export default function ExportGallery({ exportsList, onRefresh, initialHighlightVideo, onClearHighlightVideo }) {
  const [activeMediaTab, setActiveMediaTab] = useState('exports');
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'latest' | 'previous' | 'unlinked' | 'qc_rejected'
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'oldest' | 'size_desc' | 'name'
  const [selectedDetailVideo, setSelectedDetailVideo] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [showBatchDeleteModal, setShowBatchDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { toastMessage, toastType, showToast, hideToast } = useToast();
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [copiedCaption, setCopiedCaption] = useState(false);

  // Link to script/product modal state
  const [linkingVideo, setLinkingVideo] = useState(null);
  const [availableProducts, setAvailableProducts] = useState([]);
  const [selectedLinkProductId, setSelectedLinkProductId] = useState('');
  const [selectedLinkAngleId, setSelectedLinkAngleId] = useState('');
  const [isLinking, setIsLinking] = useState(false);

  const handleSwapToLatest = useCallback((currentVideo) => {
    if (!currentVideo || !exportsList) return;
    const latest = exportsList.find(v => {
      if (currentVideo.latest_video_name && v.name === currentVideo.latest_video_name) return true;
      if (currentVideo.latest_video_path && (v.path === currentVideo.latest_video_path || v.rel_path === currentVideo.latest_video_rel)) return true;
      if (currentVideo.product_id && currentVideo.angle_id && v.product_id === currentVideo.product_id && v.angle_id === currentVideo.angle_id && v.is_latest) return true;
      if (currentVideo.project_name && v.project_name === currentVideo.project_name && v.is_latest) return true;
      return false;
    });
    if (latest) {
      setSelectedDetailVideo(latest);
      showToast(`สลับไปยังเวอร์ชันล่าสุด: ${latest.hook_title || latest.name}`);
    } else {
      showToast('ไม่พบไฟล์เวอร์ชันล่าสุดในรายการ หรืออาจถูกลบไปแล้ว', 'warning');
    }
  }, [exportsList, showToast]);

  const handleOpenLinkModal = useCallback(async (video) => {
    setLinkingVideo(video);
    try {
      const res = await getProducts();
      const prods = Array.isArray(res) ? res : (res?.products || []);
      setAvailableProducts(prods);
      if (prods.length > 0) {
        setSelectedLinkProductId(prods[0].id);
        if (prods[0].angles?.length > 0) {
          setSelectedLinkAngleId(prods[0].angles[0].angle_id);
        } else {
          setSelectedLinkAngleId('');
        }
      }
    } catch (err) {
      showToast('ไม่สามารถโหลดรายชื่อสินค้าได้: ' + err.message, 'error');
    }
  }, [showToast]);

  const handleLinkProductChange = useCallback((e) => {
    const pid = e.target.value;
    setSelectedLinkProductId(pid);
    const prod = availableProducts.find(p => p.id === pid);
    if (prod?.angles?.length > 0) {
      setSelectedLinkAngleId(prod.angles[0].angle_id);
    } else {
      setSelectedLinkAngleId('');
    }
  }, [availableProducts]);

  const selectedProductAngles = useMemo(() => {
    if (!selectedLinkProductId || !availableProducts) return [];
    const prod = availableProducts.find(p => p.id === selectedLinkProductId);
    return prod?.angles || [];
  }, [selectedLinkProductId, availableProducts]);

  const handleConfirmLink = useCallback(async () => {
    if (!linkingVideo || !selectedLinkProductId || !selectedLinkAngleId) {
      showToast('กรุณาเลือกสินค้าและมุมสคริปต์ที่ต้องการผูก', 'error');
      return;
    }
    setIsLinking(true);
    try {
      await linkExportToAngle(linkingVideo.path, selectedLinkProductId, selectedLinkAngleId);
      showToast('ผูกคลิปกับสคริปต์เรียบร้อยแล้ว');
      setLinkingVideo(null);
      if (selectedDetailVideo?.path === linkingVideo.path) {
        setSelectedDetailVideo(null);
      }
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('ผูกคลิปไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsLinking(false);
    }
  }, [linkingVideo, selectedLinkProductId, selectedLinkAngleId, selectedDetailVideo, onRefresh, showToast]);

  // Auto-open video detail modal if user navigated from a completed render task
  useEffect(() => {
    if (!initialHighlightVideo || !exportsList || exportsList.length === 0) return;
    const targetStr = String(initialHighlightVideo).toLowerCase().trim();
    const matched = exportsList.find((item) => {
      const name = (item.name || '').toLowerCase();
      const path = (item.path || '').toLowerCase();
      const relPath = (item.rel_path || '').toLowerCase();
      const prodId = (item.product_id || '').toLowerCase();
      return name.includes(targetStr) || targetStr.includes(name) ||
             path.includes(targetStr) || relPath.includes(targetStr) ||
             (prodId && targetStr.includes(prodId));
    });

    if (matched) {
      setSelectedDetailVideo(matched);
      onClearHighlightVideo?.();
    } else if (exportsList.length > 0) {
      // Fallback: pick the latest rendered video if name slightly varied
      setSelectedDetailVideo(exportsList[0]);
      onClearHighlightVideo?.();
    }
  }, [initialHighlightVideo, exportsList, onClearHighlightVideo]);

  const handleOpenExportsFolder = useCallback(() => {
    openFolder('exports');
  }, []);

  const handleCopyCaption = useCallback((text) => {
    navigator.clipboard.writeText(text);
    setCopiedCaption(true);
    showToast('คัดลอกแคปชันเรียบร้อยแล้ว');
    setTimeout(() => setCopiedCaption(false), 2000);
  }, [showToast]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteFile(deleteTarget.path);
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อยแล้ว`);
      setDeleteTarget(null);
      if (selectedDetailVideo?.path === deleteTarget.path) setSelectedDetailVideo(null);
      setSelectedVideos(prev => prev.filter(p => p !== deleteTarget.path));
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, selectedDetailVideo, onRefresh, showToast]);

  const confirmBatchDelete = useCallback(async () => {
    if (selectedVideos.length === 0) return;

    setDeleting(true);
    try {
      for (const p of selectedVideos) {
        try {
          await deleteFile(p);
        } catch (e) {
          console.error(e);
        }
      }
      showToast(`ลบวิดีโอ ${selectedVideos.length} คลิปเรียบร้อยแล้ว`);
      setSelectedVideos([]);
      setShowBatchDeleteModal(false);
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('เกิดข้อผิดพลาดในการลบไฟล์: ' + err.message, 'error');
    } finally {
      setDeleting(false);
    }
  }, [selectedVideos, onRefresh, showToast]);

  const handleBatchDelete = useCallback(() => {
    if (selectedVideos.length === 0) return;
    setShowBatchDeleteModal(true);
  }, [selectedVideos]);

  const toggleSelectVideo = useCallback((path) => {
    setSelectedVideos(prev =>
      prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
    );
  }, []);

  // Compute Total Storage with useMemo
  const totalMB = useMemo(() => {
    if (!exportsList || exportsList.length === 0) return '0.0';
    const sum = exportsList.reduce((acc, curr) => acc + (parseFloat(curr.size_mb) || 0), 0);
    return sum.toFixed(1);
  }, [exportsList]);

  // Extract unique product tags from filenames with useMemo
  const productTags = useMemo(() => {
    if (!exportsList) return [];
    const tags = new Set();
    exportsList.forEach(v => {
      if (v.product_name) tags.add(v.product_name);
      else {
        const nameLow = v.name.toLowerCase();
        if (nameLow.includes('logitech') || nameLow.includes('wave')) tags.add('Logitech Wave Keys');
        else if (nameLow.includes('esseger') || nameLow.includes('สายชาร์จ')) tags.add('Esseger สายชาร์จ 66W');
        else tags.add('คลิปอื่นๆ');
      }
    });
    return Array.from(tags);
  }, [exportsList]);

  // Filter & Sort with useMemo and Debounced Search
  const filteredExports = useMemo(() => {
    if (!exportsList) return [];
    const q = (debouncedSearch || '').toLowerCase().trim();

    let list = exportsList.filter(item => {
      const matchesSearch = !q ||
        item.name.toLowerCase().includes(q) ||
        item.hook_title?.toLowerCase().includes(q) ||
        item.product_name?.toLowerCase().includes(q);

      let matchesProduct = true;
      if (selectedProductFilter !== 'all') {
        matchesProduct = item.product_name === selectedProductFilter ||
          (selectedProductFilter.includes('Logitech') && item.name.toLowerCase().includes('logitech')) ||
          (selectedProductFilter.includes('Esseger') && item.name.toLowerCase().includes('esseger'));
      }

      let matchesStatus = true;
      if (statusFilter === 'latest')      matchesStatus = !!item.is_latest;
      if (statusFilter === 'previous')    matchesStatus = !!item.is_previous_version;
      if (statusFilter === 'unlinked')    matchesStatus = !!item.is_unlinked;
      if (statusFilter === 'qc_rejected') matchesStatus = !!item.is_qc_rejected;

      return matchesSearch && matchesProduct && matchesStatus;
    });

    // Sorting
    list = [...list].sort((a, b) => {
      if (sortBy === 'newest') return (b.modified_raw || 0) - (a.modified_raw || 0);
      if (sortBy === 'oldest') return (a.modified_raw || 0) - (b.modified_raw || 0);
      if (sortBy === 'size_desc') return (parseFloat(b.size_mb) || 0) - (parseFloat(a.size_mb) || 0);
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      return 0;
    });

    return list;
  }, [exportsList, debouncedSearch, selectedProductFilter, statusFilter, sortBy]);

  // Quick counts for filter chips
  const counts = useMemo(() => {
    if (!exportsList) return { all: 0, latest: 0, previous: 0, unlinked: 0, qc_rejected: 0 };
    return {
      all:         exportsList.length,
      latest:      exportsList.filter(v => !!v.is_latest).length,
      previous:    exportsList.filter(v => !!v.is_previous_version).length,
      unlinked:    exportsList.filter(v => !!v.is_unlinked).length,
      qc_rejected: exportsList.filter(v => !!v.is_qc_rejected).length,
    };
  }, [exportsList]);

  const toggleSelectAll = useCallback(() => {
    if (selectedVideos.length === filteredExports.length) {
      setSelectedVideos([]);
    } else {
      setSelectedVideos(filteredExports.map(v => v.path));
    }
  }, [selectedVideos.length, filteredExports]);

  const mobileBaseUrl = typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '';

  return (
    <div className="space-y-6 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />

      {/* ── High-Level Media Center Switcher (Exports vs Raw Vault) ── */}
      <div className="flex items-center justify-between gap-3 p-1.5 rounded-3xl bg-[#0B0F19]/90 border border-white/[0.08] backdrop-blur-xl shadow-xl">
        <div className="flex items-center gap-2 flex-1">
          <button
            type="button"
            onClick={() => setActiveMediaTab('exports')}
            className={`flex-1 sm:flex-initial px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
              activeMediaTab === 'exports'
                ? 'bg-gradient-to-r from-[#FE2C55]/20 to-[#FE2C55]/10 text-[#FE2C55] border border-[#FE2C55]/40 shadow-lg shadow-[#FE2C55]/10'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>คลิปตัดเสร็จ ({exportsList?.length || 0})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveMediaTab('raw_vault')}
            className={`flex-1 sm:flex-initial px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
              activeMediaTab === 'raw_vault'
                ? 'bg-gradient-to-r from-[#25F4EE]/20 to-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/40 shadow-lg shadow-[#25F4EE]/10'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Film className="w-4 h-4" />
            <span>คลิปดิบ</span>
          </button>
        </div>
      </div>

      {activeMediaTab === 'raw_vault' ? (
        <RawVaultPanel />
      ) : (
        <>
      {/* ── DETAILED VIDEO QC, FULL PREVIEW & METADATA MODAL ── */}
      <Modal
        isOpen={!!selectedDetailVideo}
        onClose={() => setSelectedDetailVideo(null)}
        title={selectedDetailVideo?.hook_title || selectedDetailVideo?.name || 'พรีวิววิดีโอ'}
        subtitle={selectedDetailVideo?.hook_title ? selectedDetailVideo.name : 'พรีวิวคลิปขนาดเต็ม สแกน QR โหลดเข้ามือถือ'}
        maxWidth="max-w-xl"
      >
        {selectedDetailVideo && (
          <div className="space-y-4 max-h-[80vh] overflow-y-auto pr-1 no-scrollbar">
            {/* 1. Large 9:16 Video Player Preview (เต็มขนาดหน้าจอ) */}
            <div className="w-full max-w-[340px] sm:max-w-[380px] aspect-[9/16] max-h-[68vh] mx-auto rounded-2xl overflow-hidden bg-black border border-white/[0.12] shadow-2xl relative flex items-center justify-center ring-1 ring-white/[0.05]">
              <video
                key={selectedDetailVideo.rel_path || selectedDetailVideo.path}
                src={`/api/media/${selectedDetailVideo.rel_path || selectedDetailVideo.path}`}
                controls
                autoPlay
                playsInline
                preload="auto"
                className="w-full h-full object-contain"
              />
            </div>

            {/* Version / QC Status Banners */}
            {selectedDetailVideo.is_previous_version && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
                    <History className="w-4 h-4 text-amber-400" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-amber-300 mb-0.5">คลิปนี้เป็นเวอร์ชันก่อนหน้า (มีเวอร์ชันใหม่กว่าแทนที่แล้ว)</div>
                    {selectedDetailVideo.latest_video_name && (
                      <div className="text-[11px] text-amber-200/80">
                        เวอร์ชันล่าสุด: <span className="font-mono text-white">{selectedDetailVideo.latest_video_name}</span>
                      </div>
                    )}
                    <div className="text-[10px] text-slate-400 mt-0.5">สามารถสลับไปดูตัวล่าสุด หรือลบไฟล์นี้เพื่อประหยัดพื้นที่ดิสก์</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleSwapToLatest(selectedDetailVideo)}
                  className="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer flex-shrink-0 shadow-sm"
                  title="เปิดดูคลิปเวอร์ชันล่าสุด"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>สลับไปดูตัวล่าสุด</span>
                </button>
              </div>
            )}

            {selectedDetailVideo.is_unlinked && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-700/40 border border-slate-600/40 flex items-center justify-center flex-shrink-0">
                    <FileQuestion className="w-4 h-4 text-slate-300" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-200 mb-0.5">คลิปภายนอก (ยังไม่ได้ผูกกับสคริปต์สินค้า)</div>
                    <div className="text-[11px] text-slate-400">
                      ไฟล์นี้ยังไม่มีข้อมูลสคริปต์ในระบบ สามารถเลือกผูกกับสินค้าเพื่อดึงสคริปต์และแคปชันมาใช้ได้
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleOpenLinkModal(selectedDetailVideo)}
                  className="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/40 text-[#25F4EE] hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer flex-shrink-0 shadow-sm"
                >
                  <Link2 className="w-3.5 h-3.5" />
                  <span>ผูกกับสคริปต์</span>
                </button>
              </div>
            )}

            {selectedDetailVideo.is_latest && !selectedDetailVideo.is_qc_rejected && (
              <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>คลิปเวอร์ชันล่าสุด (พร้อมใช้งานและโพสต์ลง TikTok)</span>
              </div>
            )}

            {/* QC Rejected Banner — show if this file was superseded by a newer render */}
            {selectedDetailVideo.is_qc_rejected && (
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-red-500/10 border border-red-500/30">
                <div className="w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                  <ShieldAlert className="w-4 h-4 text-red-400" />
                </div>
                <div>
                  <div className="text-xs font-bold text-red-300 mb-0.5">คลิปนี้ถูกปัดตก QC — ถูกแทนที่แล้ว</div>
                  {selectedDetailVideo.qc_note && (
                    <div className="text-xs text-red-200/80 font-mono">{selectedDetailVideo.qc_note}</div>
                  )}
                  <div className="text-[10px] text-slate-400 mt-1">สามารถลบไฟล์นี้ได้อย่างปลอดภัย เวอร์ชันใหม่ถูก render แล้ว</div>
                </div>
              </div>
            )}

            {/* 2. Caption & Hashtag Box */}
            <div className="p-3.5 rounded-2xl bg-black/50 border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>แคปชัน & แฮชแท็กสำหรับโพสต์</span>
                </span>
                <button
                  onClick={() => handleCopyCaption(`${selectedDetailVideo.tiktok_caption || 'รีวิวตัวเด็ด! สินค้าคุณภาพดีบอกต่อ'}\n\n${selectedDetailVideo.tiktok_hashtags || '#รีวิวของใช้ #ของดีบอกต่อ #tiktokshop'}`)}
                  className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[#25F4EE] hover:text-white text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copiedCaption ? 'คัดลอกแล้ว!' : 'คัดลอก'}</span>
                </button>
              </div>
              <p className="text-xs text-slate-300 bg-black/40 p-2.5 rounded-xl border border-white/[0.04] select-all leading-relaxed font-mono">
                {selectedDetailVideo.tiktok_caption || 'รีวิวตัวเด็ด! สินค้าคุณภาพดีบอกต่อ'}&nbsp;
                {selectedDetailVideo.tiktok_hashtags || '#รีวิวของใช้ #ของดีบอกต่อ #tiktokshop'}
              </p>
            </div>

            {/* 3. Size & Format info chips */}
            <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <div className="text-[10px] text-slate-400">ขนาดไฟล์</div>
                <div className="font-bold text-[#25F4EE] mt-0.5">{selectedDetailVideo.size_mb} MB</div>
              </div>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <div className="text-[10px] text-slate-400">ความละเอียด</div>
                <div className="font-bold text-emerald-400 mt-0.5">1080x1920 (9:16)</div>
              </div>
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <div className="text-[10px] text-slate-400">วันที่สร้าง</div>
                <div className="text-slate-300 truncate mt-0.5">{selectedDetailVideo.modified?.split(' ')?.[0] || 'ล่าสุด'}</div>
              </div>
            </div>

            {/* 4. QR Mobile Download Section */}
            <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] text-center space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center text-[#25F4EE] mx-auto">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">สแกน QR โหลดคลิปเข้ามือถือ</h4>
                <p className="text-xs text-slate-400 mt-0.5">เปิดกล้องมือถือสแกนเพื่อดาวน์โหลดไฟล์ MP4 เข้าเครื่อง</p>
              </div>
              <div className="p-3 bg-white rounded-2xl inline-block shadow-xl">
                <QRCodeSVG
                  value={`${mobileBaseUrl}/api/media/${encodeURIComponent(selectedDetailVideo.rel_path || selectedDetailVideo.path)}`}
                  size={150}
                  level="M"
                />
              </div>
            </div>

            {/* 5. Modal Footer Action Buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-white/[0.08]">
              <a
                href={`/api/media/${selectedDetailVideo.rel_path || selectedDetailVideo.path}`}
                download={selectedDetailVideo.name}
                className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg cursor-pointer active:scale-95 transition-all"
              >
                <Download className="w-4 h-4" />
                <span>ดาวน์โหลด MP4</span>
              </a>
              <Button
                onClick={() => {
                  setDeleteTarget(selectedDetailVideo);
                  setSelectedDetailVideo(null);
                }}
                variant="danger"
                size="md"
                icon={Trash2}
              >
                {selectedDetailVideo.is_previous_version ? 'ลบไฟล์เวอร์ชันนี้' : 'ลบไฟล์'}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* DELETE CONFIRMATION MODAL */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="ยืนยันการลบวิดีโอนี้?"
        maxWidth="max-w-sm"
      >
        <div className="text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto border border-rose-500/20">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <p className="text-xs text-slate-300 font-mono break-all bg-black/40 p-2.5 rounded-xl border border-white/[0.08]">
            {deleteTarget?.name}
          </p>
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
              className="flex-1"
            >
              {deleting ? 'กำลังลบ...' : 'ยืนยันลบ'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── LINK EXTERNAL VIDEO TO PRODUCT/ANGLE MODAL ── */}
      <Modal
        isOpen={!!linkingVideo}
        onClose={() => setLinkingVideo(null)}
        title="ผูกวิดีโอนี้กับสินค้าและสคริปต์"
        subtitle={linkingVideo?.name}
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-xs text-slate-300">
            เลือกสินค้าและมุมมองสคริปต์ (Angle) ที่ต้องการเชื่อมโยงเข้ากับคลิปนี้ เมื่อเชื่อมแล้วคลิปจะถูกนำไปแสดงข้อมูลสคริปต์ แคปชัน และแท็กสินค้า
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-300">เลือกสินค้า</label>
            <select
              value={selectedLinkProductId}
              onChange={handleLinkProductChange}
              className="w-full py-2.5 px-3 rounded-xl bg-black/60 border border-white/[0.12] text-white text-xs font-bold focus:outline-none focus:border-[#25F4EE]"
            >
              {availableProducts.map(p => (
                <option key={p.id} value={p.id} className="bg-[#080B11]">
                  {p.name || p.title || p.id}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-300">เลือกมุมสคริปต์ (Angle)</label>
            {selectedProductAngles.length > 0 ? (
              <select
                value={selectedLinkAngleId}
                onChange={(e) => setSelectedLinkAngleId(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-black/60 border border-white/[0.12] text-white text-xs font-bold focus:outline-none focus:border-[#25F4EE]"
              >
                {selectedProductAngles.map(a => (
                  <option key={a.angle_id} value={a.angle_id} className="bg-[#080B11]">
                    {a.angle_name || a.angle_id} {a.hook_title ? `— "${a.hook_title.slice(0, 30)}..."` : ''}
                  </option>
                ))}
              </select>
            ) : (
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                สินค้านี้ยังไม่มีมุมสคริปต์ที่สร้างไว้
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 pt-2 border-t border-white/[0.08]">
            <Button
              variant="secondary"
              onClick={() => setLinkingVideo(null)}
              disabled={isLinking}
              className="flex-1"
            >
              ยกเลิก
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirmLink}
              loading={isLinking}
              disabled={!selectedLinkProductId || !selectedLinkAngleId}
              icon={Check}
              className="flex-1"
            >
              {isLinking ? 'กำลังผูกคลิป...' : 'ยืนยันการผูกคลิป'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Top Header Bar & Stats Overview (Cyber-Dark Glassmorphic) ── */}
      <div className="rounded-2xl sm:rounded-3xl border border-white/[0.08] bg-[#0B0F19]/80 backdrop-blur-xl p-4 sm:p-7 shadow-2xl relative overflow-hidden space-y-4 sm:space-y-6">
        {/* Ambient Glow Aura */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#FE2C55]/10 via-[#25F4EE]/5 to-transparent rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Top section: Title & Actions */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 sm:gap-5 relative z-10">
          <div className="space-y-1.5 sm:space-y-2">
            <div className="inline-flex items-center gap-2 px-2.5 sm:px-3 py-1 rounded-full bg-[#FE2C55]/10 border border-[#FE2C55]/30 text-[#FE2C55] text-[11px] sm:text-xs font-bold tracking-wide uppercase">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Exported Master Gallery</span>
            </div>
            <h1 className="text-xl sm:text-3xl font-black text-white tracking-tight font-kanit">
              คลังคลิปตัดเสร็จ
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
              คลิปวิดีโอ 9:16 คุณภาพสูง พร้อมสคริปต์ แคปชัน แฮชแท็ก และ QR สแกนโหลดลงมือถือ
            </p>
          </div>

          {/* Quick Metrics & Actions Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
            {/* Metrics Shelf: 3 compact columns on mobile, clean inline pills on desktop */}
            <div className="grid grid-cols-3 sm:flex sm:items-center gap-2 sm:gap-2.5">
              {/* Metric 1 */}
              <div className="px-2.5 sm:px-4 py-2 sm:py-2.5 rounded-xl sm:rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-center sm:text-left shadow-inner">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-[#FE2C55]/10 border border-[#FE2C55]/20 flex items-center justify-center text-[#FE2C55] mx-auto sm:mx-0 flex-shrink-0">
                  <Film className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <div>
                  <div className="text-[10px] sm:text-[11px] text-slate-400 font-medium">คลิปตัดเสร็จ</div>
                  <div className="text-xs sm:text-base font-black text-white font-mono">
                    {exportsList?.length || 0} <span className="text-[10px] sm:text-xs font-normal text-slate-400">ไฟล์</span>
                  </div>
                </div>
              </div>

              {/* Metric 2 */}
              <div className="px-2.5 sm:px-4 py-2 sm:py-2.5 rounded-xl sm:rounded-2xl bg-white/[0.03] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-center sm:text-left shadow-inner">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] mx-auto sm:mx-0 flex-shrink-0">
                  <HardDrive className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <div>
                  <div className="text-[10px] sm:text-[11px] text-slate-400 font-medium">ความจุรวม</div>
                  <div className="text-xs sm:text-base font-black text-white font-mono">
                    {totalMB} <span className="text-[10px] sm:text-xs font-normal text-slate-400">MB</span>
                  </div>
                </div>
              </div>

              {/* Metric 3 */}
              <div className="px-2.5 sm:px-4 py-2 sm:py-2.5 rounded-xl sm:rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-center sm:text-left shadow-inner">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-300 mx-auto sm:mx-0 flex-shrink-0">
                  <Smartphone className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <div>
                  <div className="text-[10px] sm:text-[11px] text-emerald-400/90 font-medium">สเปกคลิป</div>
                  <div className="text-xs sm:text-base font-black text-emerald-300 font-mono">
                    9:16 <span className="text-[10px] sm:text-xs font-normal text-emerald-400/80">FHD</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full sm:w-auto">
              <Button
                onClick={onRefresh}
                variant="secondary"
                size="sm"
                icon={RefreshCw}
                className="justify-center"
              >
                รีเฟรช
              </Button>
              <Button
                onClick={handleOpenExportsFolder}
                variant="secondary"
                size="sm"
                icon={Folder}
                className="justify-center"
              >
                เปิดโฟลเดอร์
              </Button>
            </div>
          </div>
        </div>

        {/* ── Tier 1: Search & Filter Dropdowns (Search + Product + Sort) ── */}
        <div className="pt-4 border-t border-white/[0.06] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 relative z-10">
          {/* Search Input with Clear Button */}
          <div className="relative flex-1 md:max-w-md lg:max-w-lg">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ค้นหาชื่อคลิป, แคปชัน, หรือสินค้า..."
              className="w-full bg-black/50 border border-white/[0.1] focus:border-[#FE2C55] focus:ring-1 focus:ring-[#FE2C55] rounded-xl pl-10 pr-9 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
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

          {/* Product Filter & Sort Dropdowns (Side-by-side on both mobile & desktop) */}
          <div className="grid grid-cols-2 sm:flex sm:items-center gap-2.5 w-full md:w-auto">
            {/* Product Filter Dropdown */}
            <div className="relative flex-1 sm:w-48">
              <select
                value={selectedProductFilter}
                onChange={(e) => setSelectedProductFilter(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer truncate"
              >
                <option value="all" className="bg-[#080B11]">สินค้าทั้งหมด ({exportsList?.length || 0})</option>
                {productTags.map(t => (
                  <option key={t} value={t} className="bg-[#080B11]">{t}</option>
                ))}
              </select>
            </div>

            {/* Sort Dropdown */}
            <div className="relative flex-1 sm:w-36">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer"
              >
                <option value="newest" className="bg-[#080B11]">ใหม่ล่าสุด</option>
                <option value="oldest" className="bg-[#080B11]">เก่าที่สุด</option>
                <option value="size_desc" className="bg-[#080B11]">ขนาดใหญ่สุด</option>
                <option value="name" className="bg-[#080B11]">เรียงตามชื่อ</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── Tier 2: Status Filter Chips & Batch Actions ── */}
        <div className="pt-3.5 border-t border-white/[0.06] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 relative z-10">
          {/* Status Filter Chips (Smooth horizontal scroll on mobile) */}
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 sm:pb-0 no-scrollbar touch-pan-x -mx-1 px-1 sm:mx-0 sm:px-0 flex-nowrap">
            {[
              { id: 'all',         label: 'ทั้งหมด',              count: counts.all,          color: 'text-slate-300 border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08]',   active: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/40 shadow-sm shadow-[#25F4EE]/10' },
              { id: 'latest',      label: 'เวอร์ชันล่าสุด',        count: counts.latest,       color: 'text-emerald-300 border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10', active: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10' },
              { id: 'previous',    label: 'เวอร์ชันก่อนหน้า',       count: counts.previous,     color: 'text-amber-300 border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10',   active: 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm shadow-amber-500/10' },
              { id: 'unlinked',    label: 'คลิปภายนอก',          count: counts.unlinked,     color: 'text-slate-400 border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06]',  active: 'bg-slate-500/20 text-slate-200 border-slate-500/40' },
              { id: 'qc_rejected', label: 'QC ปัดตก',            count: counts.qc_rejected,  color: 'text-red-300 border-red-500/20 bg-red-500/5 hover:bg-red-500/10',         active: 'bg-red-500/20 text-red-300 border-red-500/40 shadow-sm shadow-red-500/10' },
            ].map(chip => (
              <button
                key={chip.id}
                type="button"
                onClick={() => setStatusFilter(chip.id)}
                className={`py-1.5 px-3 rounded-xl text-xs font-bold border flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 ${
                  statusFilter === chip.id ? chip.active : chip.color
                }`}
              >
                {chip.id === 'latest' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                {chip.id === 'previous' && <History className="w-3.5 h-3.5 text-amber-400" />}
                {chip.id === 'unlinked' && <FileQuestion className="w-3.5 h-3.5 text-slate-400" />}
                {chip.id === 'qc_rejected' && <ShieldAlert className="w-3.5 h-3.5 text-red-400" />}
                <span>{chip.label}</span>
                <span className="font-mono text-[11px] opacity-75">({chip.count})</span>
              </button>
            ))}
          </div>

          {/* Batch Actions & Select All */}
          <div className="flex items-center gap-2 justify-between sm:justify-end flex-shrink-0">
            <button
              type="button"
              onClick={toggleSelectAll}
              className="py-1.5 sm:py-2 px-3 sm:px-3.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-2 cursor-pointer transition-colors active:scale-95"
            >
              {selectedVideos.length === filteredExports.length && filteredExports.length > 0 ? (
                <CheckSquare className="w-4 h-4 text-[#FE2C55]" />
              ) : (
                <Square className="w-4 h-4 text-slate-400" />
              )}
              <span>เลือกทั้งหมด ({filteredExports.length})</span>
            </button>

            {selectedVideos.length > 0 && (
              <Button
                onClick={handleBatchDelete}
                loading={deleting}
                variant="danger"
                size="sm"
                icon={Trash2}
                className="active:scale-95"
              >
                ลบที่เลือก ({selectedVideos.length})
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ── 9:16 Video Grid Showcase (2 columns on mobile, up to 6 on 2xl) ── */}
      {filteredExports.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3 sm:gap-4 lg:gap-5">
          {filteredExports.map((item, idx) => (
            <ExportCard
              key={item.rel_path || item.path || idx}
              item={item}
              isSelected={selectedVideos.includes(item.path)}
              onToggleSelect={toggleSelectVideo}
              onOpenDetail={setSelectedDetailVideo}
              onOpenDelete={setDeleteTarget}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="p-16 text-center space-y-4 rounded-3xl border border-white/[0.08] glass-panel shadow-xl">
          <div>
            <h3 className="text-lg font-bold text-white">
              {searchQuery ? 'ไม่พบคลิปวิดีโอที่ค้นหา' : 'ยังไม่มีคลิปวิดีโอที่ตัดเสร็จในคลัง'}
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-md mx-auto">
              {searchQuery
                ? 'ลองพิมพ์คำค้นหาอื่น หรือเปลี่ยนตัวกรองสินค้า'
                : 'ไปที่เมนู 1-Click Studio แล้วกดเริ่มตัดต่อวิดีโอ คลิปที่ตัดเสร็จจะมาปรากฏในคลังนี้โดยอัตโนมัติ'}
            </p>
          </div>
        </div>
      )}

      {/* ── Floating Batch Action Bar (Mobile & Desktop) ── */}
      {selectedVideos.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-md w-[calc(100%-2rem)] p-3 rounded-2xl bg-[#0B0F19]/95 border border-[#25F4EE]/40 backdrop-blur-2xl shadow-2xl flex items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2.5 text-xs font-bold text-white">
            <span className="w-6 h-6 rounded-lg bg-[#25F4EE]/20 text-[#25F4EE] flex items-center justify-center font-mono text-xs">
              {selectedVideos.length}
            </span>
            <span>เลือกไว้ {selectedVideos.length} คลิป</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSelectedVideos([])}
              className="py-1.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-xs font-bold text-slate-300 transition-colors cursor-pointer"
            >
              ยกเลิก
            </button>
            <button
              type="button"
              onClick={handleBatchDelete}
              className="py-1.5 px-3.5 rounded-xl bg-rose-500 hover:bg-rose-600 text-xs font-bold text-white flex items-center gap-1.5 shadow-lg shadow-rose-500/20 transition-all active:scale-95 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>ลบที่เลือก</span>
            </button>
          </div>
        </div>
      )}

      {/* ── Single Video Delete Confirm Modal ── */}
      <ConfirmModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="ลบคลิปวิดีโอนี้ถาวร?"
        description="ไฟล์วิดีโอ MP4 ในโฟลเดอร์ Exports จะถูกลบออกจากเครื่อง"
        itemName={deleteTarget?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบไฟล์ถาวร"
        loading={deleting}
        variant="danger"
      />

      {/* ── Batch Delete Confirm Modal ── */}
      <ConfirmModal
        isOpen={showBatchDeleteModal}
        onClose={() => setShowBatchDeleteModal(false)}
        onConfirm={confirmBatchDelete}
        title={`ลบคลิปวิดีโอที่เลือกทั้งหมด (${selectedVideos.length} รายการ)?`}
        description={`ไฟล์วิดีโอทั้งหมด ${selectedVideos.length} ไฟล์จะถูกลบออกจากเครื่องอย่างถาวร`}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText={`ลบทั้งหมด ${selectedVideos.length} ไฟล์`}
        loading={deleting}
        variant="danger"
      />

      </>
      )}
    </div>
  );
}
