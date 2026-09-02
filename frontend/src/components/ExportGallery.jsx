import React, { useState, useMemo, useEffect, useCallback, memo } from 'react';
import {
  Film, Download, Folder, RefreshCw, Trash2,
  AlertTriangle, Check, Play, Search, Filter, ArrowUpDown,
  Smartphone, CheckSquare, Square, Share2, Copy, FileText, QrCode
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { openFolder, deleteFile } from '../api';
import { Modal, Toast, Button, Badge } from './ui';
import { useDebounce, useToast } from '../hooks';

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

        {/* Product Tag Badge (Top Right) */}
        <div className="absolute top-3 right-3 z-20">
          {isLogitech ? (
            <Badge variant="slate" size="sm">Logitech</Badge>
          ) : isEsseger ? (
            <Badge variant="cyan" size="sm">Esseger</Badge>
          ) : (
            <Badge variant="slate" size="sm">9:16</Badge>
          )}
        </div>

        {/* Video Player Preview (9:16 Vertical) */}
        <div
          onClick={() => onOpenDetail(item)}
          className="bg-black aspect-[9/16] w-full flex items-center justify-center relative overflow-hidden cursor-pointer"
        >
          <video
            src={`/api/media/${item.path}`}
            className="w-full h-full object-cover"
            playsInline
            muted
            loop
            onMouseOver={e => e.target.play().catch(() => {})}
            onMouseOut={e => { e.target.pause(); e.target.currentTime = 0; }}
          />

          {/* Play Button Overlay on Hover */}
          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-all flex flex-col items-center justify-center gap-2">
            <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
              <Play className="w-4 h-4 fill-current ml-0.5 text-white" />
            </div>
            <span className="text-sm font-bold text-white bg-black/80 px-2.5 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
              คลิกดูรายละเอียด
            </span>
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

export default function ExportGallery({ exportsList, onRefresh }) {
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'oldest' | 'size_desc' | 'name'
  const [selectedDetailVideo, setSelectedDetailVideo] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const { toastMessage, toastType, showToast, hideToast } = useToast();
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [copiedCaption, setCopiedCaption] = useState(false);

  const handleOpenExportsFolder = useCallback(() => {
    openFolder('exports');
  }, []);

  const handleCopyCaption = useCallback((text) => {
    navigator.clipboard.writeText(text);
    setCopiedCaption(true);
    showToast('คัดลอกแคปชัน & แฮชแท็กเรียบร้อยแล้ว');
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
      alert('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, selectedDetailVideo, onRefresh, showToast]);

  const handleBatchDelete = useCallback(async () => {
    if (selectedVideos.length === 0) return;
    if (!confirm(`คุณต้องการลบวิดีโอที่เลือกทั้ง ${selectedVideos.length} คลิปใช่หรือไม่?`)) return;

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
      if (onRefresh) onRefresh();
    } finally {
      setDeleting(false);
    }
  }, [selectedVideos, onRefresh, showToast]);

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

      return matchesSearch && matchesProduct;
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
  }, [exportsList, debouncedSearch, selectedProductFilter, sortBy]);

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

      {/* DETAILED VIDEO QC & METADATA POPUP MODAL */}
      <Modal
        isOpen={!!selectedDetailVideo}
        onClose={() => setSelectedDetailVideo(null)}
        title="รายละเอียดวิดีโอ & QC TikTok"
        subtitle={selectedDetailVideo?.hook_title || selectedDetailVideo?.name}
        maxWidth="max-w-4xl"
      >
        {selectedDetailVideo && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            {/* Left: 9:16 Video Player */}
            <div className="space-y-3">
              <div className="bg-black rounded-2xl overflow-hidden aspect-[9/16] w-full max-h-[520px] mx-auto border border-white/[0.08] shadow-2xl relative flex items-center justify-center">
                <video
                  src={`/api/media/${selectedDetailVideo.path}`}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              </div>
            </div>

            {/* Right: Meta & QR Mobile Transfer */}
            <div className="space-y-4 text-left">
              {/* Size & Format info */}
              <div className="p-3.5 rounded-2xl bg-black/40 border border-white/[0.08] space-y-1.5 text-xs font-mono">
                <div className="flex justify-between text-slate-300">
                  <span>ขนาดไฟล์:</span>
                  <span className="font-bold text-[#25F4EE]">{selectedDetailVideo.size_mb} MB</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>วันที่สร้าง:</span>
                  <span>{selectedDetailVideo.modified}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>ฟอร์แมต:</span>
                  <span className="text-emerald-400 font-bold">1080x1920 (9:16 H.264)</span>
                </div>
              </div>

              {/* QR Mobile Download Section */}
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] text-center space-y-3">
                <div className="flex items-center justify-center gap-2 text-xs font-bold text-white">
                  <Smartphone className="w-4 h-4 text-[#25F4EE]" />
                  <span>สแกน QR เพื่อดาวน์โหลดลงมือถือ</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl inline-block shadow-md">
                  <QRCodeSVG
                    value={`${mobileBaseUrl}/api/media/${selectedDetailVideo.path}`}
                    size={130}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2">
                <a
                  href={`/api/media/${selectedDetailVideo.path}`}
                  download={selectedDetailVideo.name}
                  className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg cursor-pointer"
                >
                  <Download className="w-4 h-4" />
                  <span>ดาวน์โหลดไฟล์</span>
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

      {/* ── Top Header Bar & Stats Overview ── */}
      <div className="p-6 border border-white/[0.08] glass-panel rounded-3xl shadow-xl space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/20 flex-shrink-0 text-white">
              <Film className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight font-kanit">
                คลังวิดีโอที่ตัดเสร็จแล้ว (Export Gallery)
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                คลิกที่คลิปเพื่อดูรายละเอียด: สคริปต์, แคปชัน, แฮชแท็ก, และสแกน QR โหลดเข้ามือถือ
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              onClick={onRefresh}
              variant="secondary"
              size="sm"
              icon={RefreshCw}
            >
              รีเฟรช
            </Button>
            <Button
              onClick={handleOpenExportsFolder}
              variant="secondary"
              size="sm"
              icon={Folder}
            >
              เปิดโฟลเดอร์ในเครื่อง
            </Button>
          </div>
        </div>

        {/* ── 3 Metric Summary Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-slate-400">คลิปที่ตัดสำเร็จทั้งหมด</div>
              <div className="text-2xl sm:text-3xl font-bold text-white font-mono mt-1">
                {exportsList?.length || 0} <span className="text-xs font-normal text-slate-400">คลิป</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-slate-400">พื้นที่จัดเก็บรวม</div>
              <div className="text-2xl sm:text-3xl font-bold text-[#25F4EE] font-mono mt-1">
                {totalMB} <span className="text-xs font-normal text-slate-400">MB</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-emerald-400">ความพร้อมสำหรับ TikTok</div>
              <div className="text-2xl sm:text-3xl font-bold text-emerald-300 font-mono mt-1">
                100% <span className="text-xs font-normal text-emerald-400/70">อัตราส่วน 9:16</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Search, Product Filter, Sort & Batch Actions ── */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pt-4 border-t border-white/[0.08]">
          <div className="flex flex-wrap items-center gap-2.5 flex-1">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64 min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ค้นหาชื่อคลิป หรือสินค้า..."
                className="w-full py-2 pl-10 pr-3 rounded-xl bg-black/40 border border-white/[0.1] text-white text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE] transition-colors"
              />
            </div>

            {/* Product Filter Dropdown */}
            <div className="flex items-center gap-1.5">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={selectedProductFilter}
                onChange={(e) => setSelectedProductFilter(e.target.value)}
                className="py-2 px-3 rounded-xl bg-black/40 border border-white/[0.1] text-white text-xs sm:text-sm font-bold focus:outline-none focus:border-[#25F4EE] transition-colors"
              >
                <option value="all" className="bg-[#080B11]">สินค้าทั้งหมด ({exportsList?.length || 0})</option>
                {productTags.map(t => (
                  <option key={t} value={t} className="bg-[#080B11]">{t}</option>
                ))}
              </select>
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5">
              <ArrowUpDown className="w-4 h-4 text-slate-400" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="py-2 px-3 rounded-xl bg-black/40 border border-white/[0.1] text-white text-xs sm:text-sm font-bold focus:outline-none focus:border-[#25F4EE] transition-colors"
              >
                <option value="newest" className="bg-[#080B11]">ใหม่ล่าสุด</option>
                <option value="oldest" className="bg-[#080B11]">เก่าที่สุด</option>
                <option value="size_desc" className="bg-[#080B11]">ขนาดใหญ่สุด</option>
                <option value="name" className="bg-[#080B11]">เรียงตามชื่อ</option>
              </select>
            </div>
          </div>

          {/* Batch Actions & Select All */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleSelectAll}
              className="py-2 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              {selectedVideos.length === filteredExports.length && filteredExports.length > 0 ? (
                <CheckSquare className="w-3.5 h-3.5 text-[#25F4EE]" />
              ) : (
                <Square className="w-3.5 h-3.5 text-slate-400" />
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
    </div>
  );
}
