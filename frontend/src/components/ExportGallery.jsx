import React, { useState, useMemo, useEffect, useCallback, memo } from 'react';
import {
  Film, Download, Folder, RefreshCw, Trash2,
  AlertTriangle, Check, Play, Search, Filter, ArrowUpDown,
  Smartphone, CheckSquare, Square, Share2, Copy, FileText, QrCode, Sparkles, HardDrive,
  ShieldAlert, XCircle
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { openFolder, deleteFile } from '../api';
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
      className={`overflow-hidden transition-all duration-200 flex flex-col justify-between group relative rounded-3xl border glass-card shadow-lg ${
        isSelected
          ? 'border-[#25F4EE] ring-1 ring-[#25F4EE] bg-[#25F4EE]/5'
          : item.is_qc_rejected
          ? 'border-red-500/50 hover:border-red-400 bg-red-950/10 hover:shadow-red-950/40 ring-1 ring-red-500/20'
          : 'border-white/[0.08] hover:border-white/[0.2] hover:shadow-2xl'
      }`}
    >
      {/* Card Top / Video Thumbnail Area */}
      <div>
        {/* Select Checkbox (Top Left) */}
        <button
          onClick={() => onToggleSelect(item.path)}
          className="absolute top-3 left-3 z-20 w-7 h-7 rounded-lg bg-black/70 backdrop-blur-md flex items-center justify-center border border-white/20 text-white cursor-pointer hover:border-[#25F4EE] shadow-sm"
        >
          {isSelected ? <Check className="w-4 h-4 text-[#25F4EE]" /> : <Square className="w-3.5 h-3.5 text-slate-400" />}
        </button>

        {/* Product Tag Badge + QC Status (Top Right) */}
        <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
          {item.is_qc_rejected && (
            <span className="px-2 py-0.5 rounded-md bg-red-600/90 text-white font-black text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-red-400/50">
              <ShieldAlert className="w-3 h-3 text-white" />
              <span>QC ไม่ผ่าน</span>
            </span>
          )}
          {isLogitech ? (
            <Badge variant="slate" size="sm">Logitech</Badge>
          ) : isEsseger ? (
            <Badge variant="cyan" size="sm">Esseger</Badge>
          ) : (
            <Badge variant="slate" size="sm">9:16</Badge>
          )}
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

          {/* Centered Play Button Overlay (Red circle for QC rejected, Cyan/Pink for normal - both fully playable!) */}
          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-all flex flex-col items-center justify-center gap-2 pointer-events-none">
            {item.is_qc_rejected ? (
              <>
                {/* Distinct Red Glowing Play Circle */}
                <div className="w-13 h-13 rounded-full bg-gradient-to-tr from-red-600 to-rose-600 text-white flex items-center justify-center shadow-xl shadow-red-600/50 ring-2 ring-red-400 ring-offset-2 ring-offset-black/50 transform group-hover:scale-110 transition-all">
                  <Play className="w-5 h-5 fill-current ml-0.5 text-white" />
                </div>
                <div className="px-2.5 py-1 rounded-full bg-red-600/90 backdrop-blur-md text-white font-black text-[11px] shadow-lg border border-red-400/60 tracking-wide flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-white" />
                  <span>QC ไม่ผ่าน</span>
                </div>
                {item.qc_note && (
                  <div className="max-w-[85%] text-center text-[10px] text-red-100 font-mono leading-snug px-2 py-0.5 rounded-md bg-black/70 border border-red-500/40 truncate">
                    {item.qc_note}
                  </div>
                )}
                <span className="text-xs font-bold text-white bg-black/80 px-2.5 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด (ตรวจ QC)
                </span>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
                  <Play className="w-4 h-4 fill-current ml-0.5 text-white" />
                </div>
                <span className="text-sm font-bold text-white bg-black/80 px-2.5 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด
                </span>
              </>
            )}
          </div>
        </div>

        {/* Video Metadata */}
        <div className="p-4 space-y-2 text-left">
          <h4
            onClick={() => onOpenDetail(item)}
            className="text-xs sm:text-sm font-bold text-white truncate cursor-pointer hover:text-[#25F4EE] transition-colors"
            title={item.hook_title || item.name}
          >
            {item.hook_title || item.name}
          </h4>

          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1 text-[#25F4EE] font-bold">
              {item.size_mb} MB
            </span>
            <span className="text-sm text-slate-400">
              {item.modified?.split(' ')?.[0] || item.modified}
            </span>
          </div>
        </div>
      </div>

      {/* Card Action Buttons */}
      <div className="p-3 pt-0 flex items-center gap-1.5 border-t border-white/[0.08] mt-2">
        <button
          onClick={() => onOpenDetail(item)}
          className="flex-1 py-2 px-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-bold flex items-center justify-center cursor-pointer transition-colors"
        >
          ดูรายละเอียด
        </button>

        <a
          href={`/api/media/${item.path}`}
          download={item.name}
          className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold transition-colors cursor-pointer"
          title="ดาวน์โหลด .MP4"
        >
          <Download className="w-3.5 h-3.5" />
        </a>

        <button
          onClick={() => onOpenDelete(item)}
          className="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-bold transition-colors cursor-pointer"
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
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'linked' | 'qc_rejected'
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'oldest' | 'size_desc' | 'name'
  const [selectedDetailVideo, setSelectedDetailVideo] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [showBatchDeleteModal, setShowBatchDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { toastMessage, toastType, showToast, hideToast } = useToast();
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [copiedCaption, setCopiedCaption] = useState(false);

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
      if (statusFilter === 'linked')      matchesStatus = !!item.angle_id;
      if (statusFilter === 'qc_rejected') matchesStatus = !!item.is_qc_rejected;
      if (statusFilter === 'unlinked')    matchesStatus = !item.angle_id;

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
    if (!exportsList) return { all: 0, linked: 0, qc_rejected: 0, unlinked: 0 };
    return {
      all:         exportsList.length,
      linked:      exportsList.filter(v => !!v.angle_id).length,
      qc_rejected: exportsList.filter(v => !!v.is_qc_rejected).length,
      unlinked:    exportsList.filter(v => !v.angle_id).length,
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
                src={`/api/media/${selectedDetailVideo.rel_path || selectedDetailVideo.path}`}
                controls
                autoPlay
                playsInline
                preload="auto"
                className="w-full h-full object-contain"
              />
            </div>

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
                ลบไฟล์
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

      {/* ── Top Header Bar & Stats Overview (Cyber-Dark Glassmorphic) ── */}
      <div className="rounded-3xl border border-white/[0.08] bg-[#0B0F19]/80 backdrop-blur-xl p-5 sm:p-7 shadow-2xl relative overflow-hidden space-y-6">
        {/* Ambient Glow Aura */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#FE2C55]/10 via-[#25F4EE]/5 to-transparent rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 relative z-10">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FE2C55]/10 border border-[#FE2C55]/30 text-[#FE2C55] text-xs font-bold tracking-wide uppercase">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Exported Master Gallery</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-kanit">
              คลังคลิปตัดเสร็จ
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
              คลิปวิดีโอ 9:16 คุณภาพสูง พร้อมสคริปต์ แคปชัน แฮชแท็ก และ QR สแกนโหลดลงมือถือ
            </p>
          </div>

          {/* Metrics & Quick Action Shelf */}
          <div className="flex items-center flex-wrap gap-2.5 sm:gap-3">
            {/* Metric 1: Total Exported Clips */}
            <div className="flex-1 sm:flex-initial px-4 py-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-3 shadow-inner min-w-[130px]">
              <div className="w-9 h-9 rounded-xl bg-[#FE2C55]/10 border border-[#FE2C55]/20 flex items-center justify-center text-[#FE2C55] flex-shrink-0">
                <Film className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400 font-medium">คลิปตัดเสร็จ</div>
                <div className="text-base font-black text-white font-mono">
                  {exportsList?.length || 0} <span className="text-xs font-normal text-slate-400">ไฟล์</span>
                </div>
              </div>
            </div>

            {/* Metric 2: Total Storage */}
            <div className="flex-1 sm:flex-initial px-4 py-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-3 shadow-inner min-w-[130px]">
              <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE] flex-shrink-0">
                <HardDrive className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400 font-medium">ความจุรวม</div>
                <div className="text-base font-black text-white font-mono">
                  {totalMB} <span className="text-xs font-normal text-slate-400">MB</span>
                </div>
              </div>
            </div>

            {/* Metric 3: Quality / Aspect Ratio */}
            <div className="hidden sm:flex px-4 py-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 items-center gap-3 shadow-inner">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-300 flex-shrink-0">
                <Smartphone className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-emerald-400/90 font-medium">พร้อมลง TikTok</div>
                <div className="text-base font-black text-emerald-300 font-mono">
                  9:16 <span className="text-xs font-normal text-emerald-400/80">Full HD</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                onClick={onRefresh}
                variant="secondary"
                size="sm"
                icon={RefreshCw}
                className="flex-1 sm:flex-initial justify-center"
              >
                รีเฟรช
              </Button>
              <Button
                onClick={handleOpenExportsFolder}
                variant="secondary"
                size="sm"
                icon={Folder}
                className="flex-1 sm:flex-initial justify-center"
              >
                เปิดโฟลเดอร์
              </Button>
            </div>
          </div>
        </div>

        {/* ── Search, Product Filter, Sort & Batch Actions ── */}
        <div className="pt-5 border-t border-white/[0.06] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3.5 relative z-10">
          <div className="flex flex-wrap items-center gap-2.5 flex-1">
            {/* Search Input with Clear Button */}
            <div className="relative flex-1 sm:w-64 min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ค้นหาชื่อคลิป, แคปชัน, หรือสินค้า..."
                className="w-full bg-black/50 border border-white/[0.1] focus:border-[#FE2C55] focus:ring-1 focus:ring-[#FE2C55] rounded-xl pl-10 pr-9 py-2.5 text-[16px] sm:text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
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

            {/* Product Filter Dropdown */}
            <div className="flex items-center gap-1.5 flex-1 sm:flex-initial">
              <select
                value={selectedProductFilter}
                onChange={(e) => setSelectedProductFilter(e.target.value)}
                className="w-full sm:w-auto py-2.5 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-[16px] sm:text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer"
              >
                <option value="all" className="bg-[#080B11]">สินค้าทั้งหมด ({exportsList?.length || 0})</option>
                {productTags.map(t => (
                  <option key={t} value={t} className="bg-[#080B11]">{t}</option>
                ))}
              </select>
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5 flex-1 sm:flex-initial">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full sm:w-auto py-2.5 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-[16px] sm:text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer"
              >
                <option value="newest" className="bg-[#080B11]">ใหม่ล่าสุด</option>
                <option value="oldest" className="bg-[#080B11]">เก่าที่สุด</option>
                <option value="size_desc" className="bg-[#080B11]">ขนาดใหญ่สุด</option>
                <option value="name" className="bg-[#080B11]">เรียงตามชื่อ</option>
              </select>
            </div>
          </div>

          {/* ── Status Filter Chips ────────────────────────────────────── */}
          <div className="flex flex-wrap items-center gap-1.5 pt-2">
            {[
              { id: 'all',         label: 'ทั้งหมด',              count: counts.all,          color: 'text-slate-300 border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08]',   active: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/40' },
              { id: 'linked',      label: 'มีสคริปต์แม็ป',           count: counts.linked,       color: 'text-emerald-300 border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10', active: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
              { id: 'qc_rejected', label: 'QC ปัดตก',            count: counts.qc_rejected,  color: 'text-red-300 border-red-500/20 bg-red-500/5 hover:bg-red-500/10',         active: 'bg-red-500/20 text-red-300 border-red-500/40' },
              { id: 'unlinked',    label: 'ไม่มีสคริปต์',            count: counts.unlinked,     color: 'text-slate-400 border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06]',  active: 'bg-slate-500/20 text-slate-200 border-slate-500/40' },
            ].map(chip => (
              <button
                key={chip.id}
                type="button"
                onClick={() => setStatusFilter(chip.id)}
                className={`py-1.5 px-3 rounded-xl text-xs font-bold border flex items-center gap-1.5 transition-all cursor-pointer ${
                  statusFilter === chip.id ? chip.active : chip.color
                }`}
              >
                {chip.id === 'qc_rejected' && <ShieldAlert className="w-3 h-3" />}
                {chip.label}
                <span className="font-mono text-[10px] opacity-70">{chip.count}</span>
              </button>
            ))}
          </div>

          {/* Batch Actions & Select All */}
          <div className="flex items-center gap-2 justify-between sm:justify-end pt-2 sm:pt-0">
            <button
              type="button"
              onClick={toggleSelectAll}
              className="py-2.5 px-3.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-2 cursor-pointer transition-colors active:scale-95"
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

      {/* ── 9:16 Video Grid Showcase ── */}
      {filteredExports.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-5">
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
