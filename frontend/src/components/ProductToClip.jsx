import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Link2, Sparkles, Clapperboard, Loader2, Check, Copy,
  AlertCircle, ArrowRight, Upload, Trash2, RefreshCw, Plus, Film, Video,
  ChevronDown, ChevronUp, ChevronRight, Package, Rocket, FolderOpen, X,
  Search, LayoutGrid, Filter, Play
} from 'lucide-react';
import {
  scrapeAndPlanProduct, scrapeAndPlanProductAsync, getProducts, updateProduct, updateAngleStatus, updateAngleVideos, deleteProduct, uploadFile
} from '../api';
import { Modal, Toast, Button, Badge, Input, Textarea, ConfirmModal } from './ui';
import MediaPickerModal from './MediaPickerModal';
import { toMediaUrl } from '../lib/mediaUrl';
import { useToast } from '../hooks';
import { useTaskManager } from '../context/TaskContext';

// ═══════════════════════════════════════════════════════════════════════
// 📦 PRODUCT CARD (Horizontal Gallery Item)
// ═══════════════════════════════════════════════════════════════════════
function ProductCard({ product, isSelected, onSelect }) {
  const pAngles = product.angles || [];
  const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
  const total = pAngles.length || 4;
  const pct = Math.round((pDone / total) * 100);
  const thumb = product.images?.[0];
  const thumbSrc = thumb ? `/api/media/${thumb.rel_path || thumb.local_path}` : null;

  return (
    <button
      onClick={() => onSelect(product)}
      className={`flex-shrink-0 w-[130px] sm:w-[150px] rounded-xl border transition-all cursor-pointer group snap-center p-2.5 space-y-2 text-left ${
        isSelected
          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
          : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
      }`}
    >
      {/* Thumbnail or Placeholder */}
      <div className="w-full aspect-square rounded-lg overflow-hidden bg-black/60 border border-white/[0.06] flex items-center justify-center">
        {thumbSrc ? (
          <img src={thumbSrc} alt="" className="w-full h-full object-cover" />
        ) : (
          <Package className={`w-7 h-7 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-600'}`} />
        )}
      </div>

      {/* Name */}
      <div className={`text-xs font-bold truncate leading-tight ${isSelected ? 'text-white' : 'text-slate-300'}`}>
        {product.name}
      </div>

      {/* Progress Mini Bar */}
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={`text-sm font-mono font-bold flex-shrink-0 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-500'}`}>
          {pDone}/{total}
        </span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════
// 📝 ACCORDION SCRIPT ITEM (with Angle-Specific Footage Selector)
// ═══════════════════════════════════════════════════════════════════════
function ScriptAccordionItem({
  angle, index, isOpen, onToggle, onCopy, onSendToStudio, onOpenInTimeline, onPreviewExportVideo, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false,
  onOpenMediaPicker
}) {
  const lines = Array.isArray(angle.script_lines)
    ? angle.script_lines
    : (angle.script_text ? angle.script_text.split('\n') : []);

  const curStatus = angle.status || 'scripted';
  // ONLY rendered if an actual video export URL exists or status is posted!
  const isRendered = (curStatus === 'rendered' || curStatus === 'posted') && (!!angle.video_url);
  const isInProduction = curStatus === 'in_production' || (!!angle.project_name && !isRendered);

  const statusLabel = curStatus === 'posted' ? 'โพสต์แล้ว'
    : isRendered ? 'ตัดเสร็จแล้ว'
    : isInProduction ? 'กำลังตัดต่อ'
    : 'สคริปต์พร้อม';

  const statusColor = curStatus === 'posted' ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isRendered ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isInProduction ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : 'bg-white/[0.05] text-slate-400 border-white/[0.08]';

  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);

  return (
    <div className={`rounded-xl border transition-all ${
      isOpen
        ? 'bg-[#0B0F19] border-[#25F4EE]/30 shadow-md'
        : 'bg-[#080B11] border-white/[0.06] hover:border-white/[0.15]'
    }`}>
      {/* Collapsed Header Row */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left cursor-pointer group"
      >
        {/* Number Badge */}
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 ${
          isOpen
            ? 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950 shadow-sm'
            : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
        }`}>
          {index + 1}
        </span>

        {/* Name + Hook Preview */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-bold truncate ${isOpen ? 'text-white' : 'text-slate-200'}`}>
              {angle.angle_name}
            </span>
          </div>
          {!isOpen && angle.hook_title && (
            <p className="text-sm text-slate-500 truncate mt-0.5 font-kanit">
              "{angle.hook_title}"
            </p>
          )}
        </div>

        {/* Attached Video Count Badge (if any) */}
        {selectedVideos.length > 0 && !isOpen && (
          <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/20 flex-shrink-0">
            <Film className="w-3 h-3" />
            <span>{selectedVideos.length} คลิป</span>
          </span>
        )}

        {/* Status Badge */}
        <span className={`text-sm font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${statusColor}`}>
          {statusLabel}
        </span>

        {/* Quick Preview Button on Header when Exported */}
        {isRendered && angle.video_url && !isOpen && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onPreviewExportVideo && onPreviewExportVideo(angle);
            }}
            className="p-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/30 flex items-center justify-center flex-shrink-0 cursor-pointer transition-all"
            title="กดเพื่อดูคลิปวิดีโอที่ Export แล้ว"
          >
            <Play className="w-3 h-3 fill-cyan-300 text-cyan-300" />
          </button>
        )}

        {/* Chevron */}
        {isOpen
          ? <ChevronDown className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
          : <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white flex-shrink-0" />
        }
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="px-3 pb-3 space-y-3 border-t border-white/[0.06] pt-3 animate-fadeIn">
          {/* Hook Highlight */}
          {angle.hook_title && (
            <div className="p-2.5 rounded-lg bg-black/50 border-l-[3px] border-[#25F4EE] text-xs sm:text-sm font-bold text-cyan-200 leading-snug">
              {angle.hook_title}
            </div>
          )}

          {/* Script Lines */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm text-slate-400 font-semibold">
              <span>บทพูดพากย์ ({lines.length} ท่อน):</span>
              <button
                onClick={(e) => { e.stopPropagation(); onCopy(lines.join('\n'), index); }}
                className="text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer font-bold"
              >
                {copiedIndex === index
                  ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</>
                  : <><Copy className="w-3 h-3" /> คัดลอก</>}
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.06] space-y-1 max-h-40 overflow-y-auto font-mono text-xs text-slate-200 leading-relaxed">
              {lines.map((line, lIdx) => (
                <div key={lIdx} className="flex items-start gap-1.5">
                  <span className="text-[#25F4EE] font-bold flex-shrink-0">{lIdx + 1}.</span>
                  <span>{line}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 🎬 Angle-Specific Footage Selector */}
          <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
            <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
              <span className="flex items-center gap-1.5 text-slate-300">
                <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>คลิปดิบที่แนบกับมุมนี้:</span>
              </span>
              <span className="text-[11px] font-mono">
                {selectedVideos.length > 0
                  ? <span className="text-emerald-400 font-bold">เลือกแล้ว {selectedVideos.length} คลิป</span>
                  : <span className="text-amber-400/90 font-bold flex items-center gap-1">⚠️ ยังไม่ได้เลือกคลิป</span>}
              </span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
              {/* Media Picker Modal Trigger Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenMediaPicker && onOpenMediaPicker(index);
                }}
                className={`flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold transition-all cursor-pointer shadow-sm active:scale-95 ${
                  selectedVideos.length > 0
                    ? 'bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border-[#25F4EE]/40 text-[#25F4EE]'
                    : 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-500/50 text-amber-300 animate-pulse'
                }`}
                title="เปิดคลังเลือกคลิปแบบ Grid พร้อมดูภาพพรีวิวและค้นหา"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                <span>{selectedVideos.length > 0 ? `เปลี่ยน/เลือกคลิป (${videos.length})` : `เลือกคลิป (${videos.length})`}</span>
              </button>

              {/* Show ONLY Selected Footage Tags (with X to remove) */}
              {selectedVideos.map(path => {
                const fileName = path.split(/[/\\]/).pop();
                return (
                  <div
                    key={path}
                    className="flex-shrink-0 flex items-center gap-1.5 py-1 px-2.5 rounded-lg bg-[#25F4EE]/15 border border-[#25F4EE]/40 text-xs font-bold text-[#25F4EE] shadow-sm animate-fadeIn"
                  >
                    <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span className="truncate max-w-[130px]">{fileName}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleVideoForAngle && onToggleVideoForAngle(index, path);
                      }}
                      className="p-0.5 hover:bg-[#25F4EE]/30 rounded text-[#25F4EE] hover:text-white cursor-pointer ml-0.5 transition-colors"
                      title="ยกเลิกการผูกคลิปนี้"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}

              {/* If no video explicitly chosen */}
              {selectedVideos.length === 0 && (
                <span className="text-[11px] text-amber-400/80 italic py-1">
                  (ต้องเลือกคลิปก่อนส่งตัดต่อ)
                </span>
              )}
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.06]">
            {isRendered ? (
              <>
                {angle.video_url && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onPreviewExportVideo && onPreviewExportVideo(angle);
                    }}
                    className="py-2 px-3.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-cyan-500/10 cursor-pointer active:scale-95 transition-all"
                    title="เปิดดูวิดีโอที่ตัดต่อและ Export เสร็จแล้ว (ตรวจ QC)"
                  >
                    <Film className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ดูคลิปที่ Export แล้ว</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onOpenInTimeline) {
                      onOpenInTimeline(angle, index);
                    } else {
                      onSendToStudio(angle, index);
                    }
                  }}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-500/25 cursor-pointer active:scale-95 transition-all"
                  title="เปิดดูวิดีโอที่ตัดเสร็จแล้วในไทม์ไลน์ทันที"
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>เปิดดูในไทม์ไลน์</span>
                  <ArrowRight className="w-3 h-3 text-white/80" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                  className="py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center gap-1 border border-white/[0.1] cursor-pointer"
                  title="ส่งไปปรับแต่งสคริปต์หรือตัดมุมนี้ใหม่"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>ตัดใหม่</span>
                </button>
              </>
            ) : isInProduction ? (
              <>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onOpenInTimeline) {
                      onOpenInTimeline(angle, index);
                    } else {
                      onSendToStudio(angle, index);
                    }
                  }}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-amber-500/25 cursor-pointer active:scale-95 transition-all"
                  title="เปิดตัดต่อในไทม์ไลน์"
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>เปิดทำต่อในไทม์ไลน์</span>
                  <ArrowRight className="w-3 h-3 text-white/80" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                  className="py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center gap-1 border border-white/[0.1] cursor-pointer"
                  title="ส่งไปปรับแต่งสคริปต์หรือตัดมุมนี้ใหม่"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>ตัดใหม่</span>
                </button>
              </>
            ) : selectedVideos.length === 0 ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenMediaPicker && onOpenMediaPicker(index);
                }}
                className="py-2 px-4 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1.5 shadow-md cursor-pointer active:scale-95 transition-all"
                title="คลิกเพื่อเลือกคลิปสำหรับมุมนี้ก่อน"
              >
                <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                <span>เลือกคลิปก่อนส่งตัดต่อ</span>
                <ArrowRight className="w-3 h-3 text-amber-400/80" />
              </button>
            ) : (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                className="py-2 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
              >
                <Clapperboard className="w-3.5 h-3.5 text-white" />
                <span>เลือกมุมนี้ & ส่งตัดต่อ</span>
                <ArrowRight className="w-3 h-3 text-white/80" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 🌟 MAIN: ProductToClip Component (Redesigned Guided Workflow)
// ═══════════════════════════════════════════════════════════════════════
export default function ProductToClip({ status, videos = [], onRefresh, onApplyToStudio, onGoToGallery, selectedProductId }) {
  // Input Mode & Active View
  const [showAddModal, setShowAddModal] = useState(false);
  const [inputMode, setInputMode] = useState('link');
  const [url, setUrl] = useState('');
  const [customKeyword, setCustomKeyword] = useState('');
  const [rawText, setRawText] = useState('');
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  // Active Product & Angles State
  const [productData, setProductData] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [angles, setAngles] = useState([]);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [openAngleIdx, setOpenAngleIdx] = useState(0); // Accordion: which angle is expanded
  const [previewExportAngle, setPreviewExportAngle] = useState(null); // Dialog: preview exported MP4 video
  const { toastMessage, showToast, hideToast } = useToast();
  const { refreshTrigger, toggleActivityDrawer } = useTaskManager();

  // History / All Products & Scalable Catalog
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState(selectedProductId || null);
  const [productSearch, setProductSearch] = useState('');
  const [productFilter, setProductFilter] = useState('all'); // 'all' | 'in_progress' | 'completed'
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [isStep1Collapsed, setIsStep1Collapsed] = useState(false);
  const [deleteTargetProduct, setDeleteTargetProduct] = useState(null);
  const [isDeletingProduct, setIsDeletingProduct] = useState(false);

  // Filtered Products for 100+ items
  const filteredHistory = useMemo(() => {
    let list = historyList || [];
    const q = (productSearch || '').trim().toLowerCase();
    if (q) {
      list = list.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) ||
        (p.price || '').toLowerCase().includes(q)
      );
    }
    if (productFilter === 'in_progress') {
      list = list.filter(p => {
        const done = (p.angles || []).filter(a => a.status === 'posted' || a.status === 'rendered').length;
        return done < (p.angles?.length || 4);
      });
    } else if (productFilter === 'completed') {
      list = list.filter(p => {
        const done = (p.angles || []).filter(a => a.status === 'posted' || a.status === 'rendered').length;
        return done >= (p.angles?.length || 4) && ((p.angles?.length || 0) > 0);
      });
    }
    return list;
  }, [historyList, productSearch, productFilter]);

  // Angle Count Selection
  const [angleCount, setAngleCount] = useState(7); // Default: 7 (Sweet Spot)

  // Media Picker Modal State
  const [pickerModalOpen, setPickerModalOpen] = useState(false);
  const [pickerAngleIndex, setPickerAngleIndex] = useState(0);

  // Uploading Screenshot/Image
  const [uploadingImg, setUploadingImg] = useState(false);
  const fileInputRef = useRef(null);

  // Load History on Mount or when background task finishes
  const loadHistory = async (targetId = null) => {
    setLoadingHistory(true);
    try {
      const res = await getProducts();
      if (res.products) {
        setHistoryList(res.products);
        if (res.products.length > 0) {
          const effectiveId = targetId || selectedProductId || selectedHistoryId;
          const current = res.products.find(p => p.id === effectiveId) || res.products[0];
          selectProduct(current);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory(selectedProductId);
  }, [selectedProductId, refreshTrigger]);

  const selectProduct = (item) => {
    if (!item) return;
    setSelectedHistoryId(item.id);
    setProductData({
      id: item.id,
      title: item.name,
      url: item.url,
      description: item.selling_points?.length ? item.selling_points.join(', ') : '',
      price_note: item.price_note || '',
      status: item.status || 'scripted',
      images: item.images || (item.thumbnail ? [{ rel_path: item.thumbnail, name: 'thumb' }] : []),
    });
    setAngles(item.angles || []);
    setOpenAngleIdx(0); // Reset accordion to first angle
    if (item.images && item.images.length > 0) {
      setSelectedImage(item.images[0].local_path || item.images[0].rel_path);
    }
  };

  const handleAngleStatusChange = async (angleId, nextStatus) => {
    if (!productData?.id) return;
    try {
      await updateAngleStatus(productData.id, angleId, nextStatus);
      setAngles(prev => prev.map(a => a.angle_id === angleId ? { ...a, status: nextStatus } : a));
      const res = await getProducts();
      if (res.products) setHistoryList(res.products);
      showToast(`อัปเดตสถานะสคริปต์เรียบร้อยแล้ว`);
    } catch (err) {
      showToast('ไม่สามารถอัปเดตสถานะได้: ' + err.message, 'error');
    }
  };

  const handleDeleteHistory = (target) => {
    if (!target) return;
    setDeleteTargetProduct(target);
  };

  const confirmDeleteProduct = async () => {
    if (!deleteTargetProduct?.id) return;
    setIsDeletingProduct(true);
    try {
      await deleteProduct(deleteTargetProduct.id);
      showToast('ลบสินค้าและสคริปต์ทั้งหมดเรียบร้อยแล้ว');
      const res = await getProducts();
      const updated = res.products || [];
      setHistoryList(updated);
      if (updated.length > 0) {
        selectProduct(updated[0]);
      } else {
        setProductData(null);
        setAngles([]);
      }
      setDeleteTargetProduct(null);
    } catch (err) {
      showToast('ลบไม่สำเร็จ: ' + err.message, 'error');
    } finally {
      setIsDeletingProduct(false);
    }
  };

  const handleScrapeAndPlan = async () => {
    if (inputMode === 'link' && !url.trim()) {
      showToast('กรุณากรอกลิงก์สินค้าก่อนครับ', 'warning');
      return;
    }
    if (inputMode === 'text' && !customKeyword.trim() && !rawText.trim()) {
      showToast('กรุณาระบุชื่อสินค้าหรือสเปกก่อนครับ', 'warning');
      return;
    }
    if (inputMode === 'image' && !selectedImage && !customKeyword.trim()) {
      showToast('กรุณาอัปโหลดรูปภาพหรือระบุชื่อสินค้าก่อนครับ', 'warning');
      return;
    }

    setFetching(true);
    setFetchError(null);

    try {
      const payload = {
        url: inputMode === 'link' ? url : undefined,
        raw_text: inputMode === 'text' ? `${customKeyword}\n${rawText}` : undefined,
        custom_keyword: customKeyword || undefined,
        image_path: inputMode === 'image' ? selectedImage : undefined,
        angle_count: angleCount
      };

      // Non-blocking async background task execution
      const res = await scrapeAndPlanProductAsync(payload);
      if (res.success && res.task_id) {
        setShowAddModal(false);
        setUrl('');
        setCustomKeyword('');
        setRawText('');
        showToast(`🚀 เริ่มวิเคราะห์สินค้า & สร้าง ${angleCount} สคริปต์ในเบื้องหลังแล้ว — สามารถเปลี่ยนหน้าหรือทำงานต่อได้ทันที`);
      } else {
        // Fallback to sync if async did not return task_id
        const syncRes = await scrapeAndPlanProduct(payload);
        if (syncRes.success && syncRes.product) {
          selectProduct(syncRes.product);
          setShowAddModal(false);
          setUrl('');
          setCustomKeyword('');
          setRawText('');
          await loadHistory();
          showToast(`AI วิเคราะห์และสร้าง ${angleCount} สคริปต์สำเร็จแล้ว`);
        }
      }
    } catch (err) {
      console.error('Scrape and plan error:', err);
      setFetchError(err.friendlyMessage || err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการวิเคราะห์สินค้า');
    } finally {
      setFetching(false);
    }
  };

  const [previewImage, setPreviewImage] = useState(null);

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImg(true);
    try {
      setPreviewImage(URL.createObjectURL(file));
    } catch {
      // ignore
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_dir', 'inbox');
    try {
      const res = await uploadFile(formData);
      if (res.file) {
        setSelectedImage(res.file.path);
        showToast('อัปโหลดไฟล์รูปภาพเรียบร้อยแล้ว');
      }
    } catch (err) {
      showToast('อัปโหลดไม่สำเร็จ: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setUploadingImg(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleOpenMediaPicker = (idx) => {
    setPickerAngleIndex(idx);
    setPickerModalOpen(true);
  };

  const handleConfirmMediaPicker = async (selectedPaths) => {
    const targetAngle = angles[pickerAngleIndex];
    if (!targetAngle) return;

    // Immediate UI update
    setAngles(prev => {
      const next = [...prev];
      if (next[pickerAngleIndex]) {
        const ang = { ...next[pickerAngleIndex] };
        ang.selected_videos = selectedPaths;
        ang.selected_video = selectedPaths[0] || null;
        next[pickerAngleIndex] = ang;
      }
      return next;
    });
    showToast(`เลือกคลิปดิบ ${selectedPaths.length} คลิปสำหรับมุมมองนี้เรียบร้อยแล้ว`);

    // Backend Persistence
    if (productData?.id && targetAngle.angle_id) {
      try {
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, selectedPaths);
        if (res.product) {
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
      } catch (err) {
        console.error('Failed to persist angle videos:', err);
      }
    }
  };

  const handleToggleVideoForAngle = async (angleIdx, videoPath) => {
    const targetAngle = angles[angleIdx];
    if (!targetAngle) return;

    const currentVideos = targetAngle.selected_videos || (targetAngle.selected_video ? [targetAngle.selected_video] : []);
    const newVideos = currentVideos.includes(videoPath)
      ? currentVideos.filter(p => p !== videoPath)
      : [...currentVideos, videoPath];

    // Immediate UI update
    setAngles(prev => {
      const next = [...prev];
      const ang = { ...next[angleIdx] };
      ang.selected_videos = newVideos;
      ang.selected_video = newVideos[0] || null;
      next[angleIdx] = ang;
      return next;
    });
    showToast('อัปเดตการเลือกคลิปสำหรับมุมนี้เรียบร้อยแล้ว');

    // Backend Persistence
    if (productData?.id && targetAngle.angle_id) {
      try {
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, newVideos);
        if (res.product) {
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
      } catch (err) {
        console.error('Failed to persist angle videos:', err);
      }
    }
  };

  const copyScriptText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    showToast('คัดลอกสคริปต์เรียบร้อยแล้ว');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSendToStudio = async (angle, angleIdx = 0) => {
    if (!onApplyToStudio) return;

    const chosenVideos = angle.selected_videos && angle.selected_videos.length > 0
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : []);

    const resolvedIndex = typeof angleIdx === 'number' && angleIdx >= 0
      ? angleIdx
      : angles.findIndex(a => (a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title);

    if (chosenVideos.length === 0) {
      showToast('⚠️ กรุณาเลือกคลิปวิดีโอสำหรับมุมนี้ก่อนส่งตัดต่อ', 'warning');
      handleOpenMediaPicker(resolvedIndex >= 0 ? resolvedIndex : 0);
      return;
    }

    // Do NOT set in_production prematurely when merely sending to studio!
    // Status stays 'scripted' until user actually presses render in timeline.

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');

    const primaryVideo = chosenVideos[0] || '';

    onApplyToStudio({
      productId: productData?.id,
      angleId: angle.angle_id,
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      // Not auto-filling hookBrand/hookModel/hookLabel -- the 3-tier hook
      // banner is manual-only (see EditorShell.jsx).
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
      openProjectName: angle.project_name || '',
      openVideoUrl: angle.video_url || '',
      fullProduct: {
        id: productData?.id,
        title: productData?.title || customKeyword || 'สินค้า',
        description: productData?.description,
        price_note: productData?.price_note,
        selectedVideo: primaryVideo,
        selectedVideos: chosenVideos,
        images: productData?.images || [],
        angles: angles && angles.length > 0 ? angles : [angle]
      },
      angleIndex: resolvedIndex >= 0 ? resolvedIndex : 0
    });
  };

  const handleOpenInTimeline = (angle, index) => {
    const resolvedIndex = typeof index === 'number'
      ? index
      : angles.findIndex(a => (a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title);

    const chosenVideos = (angle.selected_videos && angle.selected_videos.length > 0)
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : (productData?.videos ? productData.videos.map(v => v.path || v.rel_path) : []));

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');
    const primaryVideo = chosenVideos[0] || '';

    onApplyToStudio({
      productId: productData?.id,
      angleId: angle.angle_id,
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      // Not auto-filling hookBrand/hookModel/hookLabel -- the 3-tier hook
      // banner is manual-only (see EditorShell.jsx).
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
      openProjectName: angle.project_name || '',
      openVideoUrl: angle.video_url || '',
      isRendered: true,
      fullProduct: {
        id: productData?.id,
        title: productData?.title || customKeyword || 'สินค้า',
        description: productData?.description,
        price_note: productData?.price_note,
        selectedVideo: primaryVideo,
        selectedVideos: chosenVideos,
        images: productData?.images || [],
        angles: angles && angles.length > 0 ? angles : [angle]
      },
      angleIndex: resolvedIndex >= 0 ? resolvedIndex : 0
    });
  };

  const totalAngles = angles.length;
  const postedAngles = angles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
  const progressPercent = totalAngles > 0 ? Math.round((postedAngles / totalAngles) * 100) : 0;

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="space-y-4 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ══════════════════════════════════════════════════════════
          STEP 1: PRODUCT CARD GALLERY & SEARCH (Handles 100+ items)
         ══════════════════════════════════════════════════════════ */}
      <div className="space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-1">
          <div className="flex items-center gap-2 min-w-0">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 flex-shrink-0">
              <Package className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>Step 1 — เลือกสินค้า</span>
              {historyList.length > 0 && (
                <span className="text-sm font-mono text-slate-500 ml-1">({historyList.length} รายการ)</span>
              )}
            </h2>

            {/* Quick Product Switcher Dropdown (for 100+ items) */}
            {historyList.length > 0 && (
              <div className="relative min-w-0 max-w-[190px] sm:max-w-[240px]">
                <select
                  value={selectedHistoryId || ''}
                  onChange={(e) => {
                    const found = historyList.find(p => p.id === e.target.value);
                    if (found) selectProduct(found);
                  }}
                  className="w-full bg-[#080B11] border border-white/[0.1] hover:border-[#25F4EE]/40 text-slate-200 text-xs font-bold py-1 px-2.5 rounded-lg focus:outline-none focus:border-[#25F4EE] cursor-pointer truncate"
                  title="สลับสินค้าด่วนจากรายการทั้งหมด"
                >
                  <option value="" disabled>-- เลือกสินค้าด่วน ({historyList.length}) --</option>
                  {historyList.map(p => (
                    <option key={p.id} value={p.id} className="bg-[#080B11] text-white">
                      {p.name} ({p.angles?.length || 0} สคริปต์)
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Instant Search Bar */}
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                placeholder="ค้นหาสินค้า..."
                className="bg-[#080B11] border border-white/[0.1] focus:border-[#25F4EE] text-slate-200 text-xs pl-8 pr-7 py-1 rounded-lg w-[120px] sm:w-[150px] focus:w-[180px] transition-all focus:outline-none placeholder-slate-500"
              />
              {productSearch && (
                <button
                  onClick={() => setProductSearch('')}
                  className="absolute right-2 text-slate-400 hover:text-white cursor-pointer"
                  title="ล้างคำค้นหา"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* View All Grid Catalog Button */}
            <button
              onClick={() => setShowCatalogModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold cursor-pointer transition-colors"
              title="เปิดดูคลังสินค้าทั้งหมดแบบตาราง Grid"
            >
              <LayoutGrid className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span className="hidden sm:inline">คลังสินค้า</span>
            </button>

            {/* Toggle Collapse/Expand Strip Button */}
            <button
              onClick={() => setIsStep1Collapsed(!isStep1Collapsed)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold cursor-pointer transition-colors"
              title={isStep1Collapsed ? "ขยายแถบสินค้า" : "ย่อแถบสินค้าเพื่อดูสคริปต์เต็มตา"}
            >
              {isStep1Collapsed ? (
                <>
                  <ChevronDown className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>เปิดแถบ</span>
                </>
              ) : (
                <>
                  <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                  <span>ย่อเก็บ</span>
                </>
              )}
            </button>

            <button
              onClick={loadHistory}
              className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/[0.06] cursor-pointer transition-colors"
              title="รีเฟรช"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
            </button>

            {productData && (
              <button
                onClick={() => handleDeleteHistory(productData)}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 cursor-pointer transition-colors"
                title="ลบสินค้านี้"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Horizontal Scrollable Product Cards (Filtered & Collapsible) */}
        {!isStep1Collapsed && (
          <div className="flex items-stretch gap-2.5 overflow-x-auto pb-1 no-scrollbar snap-x snap-mandatory scroll-smooth pr-4 animate-fadeIn">
            {filteredHistory.map(p => (
              <ProductCard
                key={p.id}
                product={p}
                isSelected={selectedHistoryId === p.id}
                onSelect={selectProduct}
              />
            ))}

            {filteredHistory.length === 0 && productSearch && (
              <div className="flex items-center justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-400 gap-2 flex-shrink-0">
                <Search className="w-4 h-4 text-slate-500" />
                <span>ไม่พบสินค้าที่ตรงกับ "{productSearch}"</span>
                <button
                  onClick={() => setProductSearch('')}
                  className="text-[#25F4EE] hover:underline font-bold ml-1 cursor-pointer"
                >
                  ล้างการค้นหา
                </button>
              </div>
            )}

            {/* + Add New Product Card */}
            <button
              onClick={() => setShowAddModal(true)}
              className="flex-shrink-0 w-[130px] sm:w-[150px] rounded-xl border-2 border-dashed border-white/[0.12] hover:border-[#25F4EE]/50 bg-black/20 hover:bg-[#25F4EE]/[0.05] transition-all cursor-pointer snap-center p-2.5 flex flex-col items-center justify-center gap-2 group"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 border border-white/[0.1] flex items-center justify-center group-hover:scale-110 transition-transform">
                <Plus className="w-5 h-5 text-[#25F4EE]" />
              </div>
              <span className="text-xs font-bold text-slate-400 group-hover:text-white transition-colors text-center">
                วิเคราะห์สินค้าใหม่
              </span>
            </button>
          </div>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════
          ADD PRODUCT MODAL
         ══════════════════════════════════════════════════════════ */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="เพิ่มสินค้าใหม่ ➔ ให้ AI สร้าง 4 สคริปต์"
        subtitle="รองรับทุกลิงก์ Shopee / TikTok Shop หรือพิมพ์สเปกตรงๆ"
        maxWidth="max-w-xl"
      >
        <div className="space-y-4">
          {/* Input Mode Selector */}
          <div className="flex items-center gap-1 p-1 bg-black/40 rounded-xl border border-white/[0.08]">
            {[
              { id: 'link', label: 'ลิงก์สินค้า' },
              { id: 'text', label: 'ข้อความสเปก' },
              { id: 'image', label: 'รูปภาพสินค้า' },
            ].map(m => (
              <button
                key={m.id}
                onClick={() => setInputMode(m.id)}
                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  inputMode === m.id ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Mode 1: URL */}
          {inputMode === 'link' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ลิงก์สินค้า:"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://shopee.co.th/product/... หรือ https://vt.tiktok.com/..."
              />
              <p className="text-sm text-slate-500">
                หากแพลตฟอร์มป้องกันการดึงข้อมูล ระบบจะแนะนำให้วางข้อความสเปกแทน
              </p>
            </div>
          )}

          {/* Mode 2: Raw Text */}
          {inputMode === 'text' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ชื่อสินค้า:"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น สายชาร์จแม่เหล็ก 3-in-1 หรือ เซรั่มหน้าใส"
              />
              <Textarea
                label="รายละเอียดสินค้าและสเปก:"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={5}
                placeholder="ก๊อปปี้รายละเอียดสินค้ามาวางที่นี่ได้เลย..."
              />
            </div>
          )}

          {/* Mode 3: Image / Screenshot */}
          {inputMode === 'image' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ชื่อสินค้า:"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น Esseger สายชาร์จแม่เหล็ก"
              />
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  รูปสินค้าหรือภาพหน้าจอ:
                </label>
                <div
                  className="relative block border-2 border-dashed border-white/[0.15] hover:border-[#25F4EE]/50 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-black/30"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,image/heic,image/heif,image/jpeg,image/png,image/webp,.heic,.HEIC,.heif,.HEIF,.jpg,.jpeg,.png,.webp"
                    onChange={handleImageUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                  />
                  {uploadingImg ? (
                    <div className="flex flex-col items-center gap-2 text-[#25F4EE] pointer-events-none">
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span className="text-xs font-bold">กำลังอัปโหลดรูปภาพ...</span>
                    </div>
                  ) : (selectedImage || previewImage) ? (
                    <div className="space-y-2 relative z-30">
                      {previewImage && (
                        <img
                          src={previewImage}
                          alt="Uploaded Preview"
                          className="h-32 mx-auto rounded-xl object-contain border border-white/[0.1] shadow-md mb-2"
                        />
                      )}
                      <div className="text-xs font-bold text-emerald-400">เลือกรูปแล้ว:</div>
                      <div className="text-sm text-slate-400 font-mono">{(selectedImage || 'image').split('\\').pop()?.split('/').pop()}</div>
                      <button
                        type="button"
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setSelectedImage(null); setPreviewImage(null); }}
                        className="text-xs text-rose-400 hover:underline cursor-pointer"
                      >
                        ลบรูปออก
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-slate-400 pointer-events-none">
                      <Upload className="w-7 h-7 mx-auto text-slate-500" />
                      <div className="text-xs font-bold text-slate-200">แตะเพื่อเลือกรูปสินค้า</div>
                      <div className="text-sm text-slate-500">รองรับ HEIC, JPG, PNG, WebP</div>
                    </div>
                  )}
                </div>

                {/* Native Fallback for 100% iOS Safari support */}
                <div className="mt-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-1 text-left">
                  <span className="text-[11px] font-bold text-slate-400 block">หรือเลือกไฟล์รูปภาพ:</span>
                  <input
                    type="file"
                    accept="image/*,image/heic,image/heif,image/jpeg,image/png,image/webp,.heic,.HEIC,.heif,.HEIF,.jpg,.jpeg,.png,.webp"
                    onChange={handleImageUpload}
                    disabled={uploadingImg}
                    className="block w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-[#25F4EE]/20 file:text-[#25F4EE] hover:file:bg-[#25F4EE]/30 file:cursor-pointer cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}

          {fetchError && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{fetchError}</span>
              </div>
              {inputMode === 'link' && (
                <button
                  type="button"
                  onClick={() => { setInputMode('text'); setFetchError(null); }}
                  className="px-3 py-1.5 rounded-lg bg-white/[0.1] hover:bg-white/[0.15] text-white text-sm font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span>สลับไปใช้วิธีวางข้อความสเปกแทน</span>
                </button>
              )}
            </div>
          )}

          {/* ── Angle Count Selector ── */}
          <div className="flex items-center gap-3 py-2.5">
            <span className="text-xs text-slate-400 font-semibold">จำนวนมุมขาย:</span>
            <div className="flex items-center gap-1.5">
              {[
                { val: 4, label: '4', desc: 'Quick' },
                { val: 7, label: '7', desc: 'แนะนำ' },
                { val: 10, label: '10', desc: 'ครบ' },
              ].map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setAngleCount(opt.val)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                    angleCount === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.05] text-slate-400 border border-white/[0.08] hover:border-white/[0.2] hover:text-white'
                  }`}
                >
                  {opt.label}
                  {opt.desc && <span className="ml-1 text-[10px] opacity-60">({opt.desc})</span>}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
            <Button variant="secondary" onClick={() => setShowAddModal(false)}>
              ยกเลิก
            </Button>
            <Button variant="primary" onClick={handleScrapeAndPlan} loading={fetching} icon={Sparkles}>
              วิเคราะห์ & สร้าง {angleCount} สคริปต์
            </Button>
          </div>
        </div>
      </Modal>

      {/* ══════════════════════════════════════════════════════════
          STEP 2 + 3: PRODUCT DETAIL + SCRIPT ACCORDION + MEDIA
         ══════════════════════════════════════════════════════════ */}
      {productData ? (
        <div className="space-y-4">

          {/* ──── Product Info Compact Header ──── */}
          <div className="glass-card p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-sm sm:text-base font-bold text-white font-kanit truncate max-w-md">
                  {productData.title}
                </h1>
                {productData.price_note && (
                  <span className="text-sm font-bold font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex-shrink-0">
                    {productData.price_note}
                  </span>
                )}
              </div>
              {productData.description && productData.description.trim() !== (productData.price_note || '').trim() && (
                <p className="text-sm sm:text-xs text-slate-400 truncate mt-0.5 max-w-lg">
                  {productData.description}
                </p>
              )}
            </div>

            {/* Progress */}
            <div className="flex items-center gap-2.5 bg-black/40 p-2 px-3 rounded-lg border border-white/[0.08] flex-shrink-0">
              <span className="text-sm text-slate-400">ความคืบหน้า:</span>
              <span className="text-xs text-white font-bold font-mono">{postedAngles}/{totalAngles}</span>
              <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
          </div>

          {/* ──── STEP 2: Script Accordion & Footage Selection ──── */}
          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#FE2C55]" />
                <span>Step 2 — เลือกมุมขาย & คลิปประกอบ ({totalAngles} สคริปต์)</span>
              </h2>
              <label className="relative px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-[#25F4EE] cursor-pointer flex items-center gap-1 transition-all">
                <input
                  type="file"
                  accept="video/*,image/*,image/heic,image/heif,.heic,.HEIC,.heif,.HEIF,.mov,.MOV,.mp4,.MP4"
                  onChange={handleImageUpload}
                  disabled={uploadingImg}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <Upload className="w-3.5 h-3.5 pointer-events-none" />
                <span className="pointer-events-none">{uploadingImg ? 'กำลังอัปโหลด...' : 'แนบคลิป/รูปเข้าคลัง'}</span>
              </label>
            </div>

            <div className="space-y-1.5">
              {angles.map((ang, idx) => (
                <ScriptAccordionItem
                  key={ang.angle_id || idx}
                  angle={ang}
                  index={idx}
                  isOpen={openAngleIdx === idx}
                  onToggle={() => setOpenAngleIdx(openAngleIdx === idx ? -1 : idx)}
                  onCopy={copyScriptText}
                  onSendToStudio={handleSendToStudio}
                  onOpenInTimeline={handleOpenInTimeline}
                  onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                  copiedIndex={copiedIndex}
                  videos={videos}
                  onToggleVideoForAngle={handleToggleVideoForAngle}
                  onUploadVideo={handleImageUpload}
                  uploadingImg={uploadingImg}
                  onOpenMediaPicker={handleOpenMediaPicker}
                />
              ))}
            </div>
          </div>

        </div>
      ) : (
        /* ══════════════════════════════════════════════════════════
           🌟 EMPTY STATE / ONBOARDING (First-Run Experience)
          ══════════════════════════════════════════════════════════ */
        <div className="p-8 sm:p-12 text-center space-y-5 rounded-2xl glass-card shadow-2xl border border-white/[0.08]">
          {/* Hero Icon */}
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 border border-white/[0.1] flex items-center justify-center mx-auto shadow-lg">
            <Rocket className="w-8 h-8 text-[#25F4EE]" />
          </div>

          <div>
            <h3 className="text-lg font-bold text-white font-kanit">เริ่มต้นสร้างคลิปขายจากสินค้าได้เลย!</h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
              วางลิงก์สินค้าจาก Shopee หรือ TikTok Shop → AI จะวิเคราะห์สเปกและสร้าง <strong className="text-white">4 สคริปต์ป้ายยา</strong> จาก 4 มุมขายให้ทันที → เลือกมุมที่ชอบแล้วกด "ส่งตัดต่อ"
            </p>
          </div>

          {/* 3-Step Visual Guide */}
          <div className="flex items-center justify-center gap-3 text-xs text-slate-400 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-[#25F4EE]/20 text-[#25F4EE] font-bold text-sm flex items-center justify-center">1</span>
              <span>วางลิงก์/สเปก</span>
            </div>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-[#FE2C55]/20 text-[#FE2C55] font-bold text-sm flex items-center justify-center">2</span>
              <span>AI สร้าง 4 สคริปต์</span>
            </div>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-sm flex items-center justify-center">3</span>
              <span>ส่งตัดต่อใน Studio</span>
            </div>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="mx-auto py-3 px-6 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-sm font-bold flex items-center gap-2 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4 text-white" />
            <span>วิเคราะห์สินค้าแรกของคุณ</span>
          </button>
        </div>
      )}

      {/* ── Universal Media Picker Modal ── */}
      <MediaPickerModal
        isOpen={pickerModalOpen}
        onClose={() => setPickerModalOpen(false)}
        title={`เลือกคลิปสำหรับมุม: ${angles[pickerAngleIndex]?.angle_name || 'มุมมองขาย'}`}
        productId={productData?.id}
        productName={productData?.title}
        selectedVideos={angles[pickerAngleIndex]?.selected_videos || (angles[pickerAngleIndex]?.selected_video ? [angles[pickerAngleIndex]?.selected_video] : [])}
        onConfirm={handleConfirmMediaPicker}
        isMultiSelect={true}
      />

      {/* ── Product Catalog Modal (Searchable Grid for 100+ items) ── */}
      <Modal
        isOpen={showCatalogModal}
        onClose={() => setShowCatalogModal(false)}
        title={`คลังสินค้าทั้งหมด (${historyList.length} รายการ)`}
        subtitle="ค้นหา กรอง และเลือกสินค้าเพื่อเข้าสู่หน้ามุมมองขายและสคริปต์"
        maxWidth="max-w-4xl"
      >
        <div className="space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-white/[0.08]">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                placeholder="ค้นหาชื่อสินค้า, ราคา, หรือคีย์เวิร์ด..."
                className="w-full bg-[#080B11] border border-white/[0.1] focus:border-[#25F4EE] text-white text-xs pl-9 pr-8 py-2 rounded-xl focus:outline-none placeholder-slate-500"
                autoFocus
              />
              {productSearch && (
                <button
                  onClick={() => setProductSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                  title="ล้างคำค้นหา"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 p-1 bg-black/40 rounded-xl border border-white/[0.08] flex-shrink-0">
              {[
                { id: 'all', label: `ทั้งหมด (${historyList.length})` },
                { id: 'in_progress', label: `กำลังทำ` },
                { id: 'completed', label: `เสร็จแล้ว` },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setProductFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    productFilter === tab.id
                      ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Grid Cards Container */}
          <div className="max-h-[60vh] overflow-y-auto pr-1 no-scrollbar">
            {filteredHistory.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {filteredHistory.map(p => {
                  const pAngles = p.angles || [];
                  const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
                  const total = pAngles.length || 4;
                  const pct = Math.round((pDone / total) * 100);
                  const thumb = p.images?.[0];
                  const thumbSrc = thumb ? `/api/media/${thumb.rel_path || thumb.local_path}` : null;
                  const isSelected = selectedHistoryId === p.id;

                  return (
                    <div
                      key={p.id}
                      onClick={() => {
                        selectProduct(p);
                        setShowCatalogModal(false);
                      }}
                      className={`p-3 rounded-xl border transition-all cursor-pointer group relative flex flex-col justify-between space-y-2.5 ${
                        isSelected
                          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE] shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
                          : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                      }`}
                    >
                      {/* Image Preview */}
                      <div className="w-full aspect-square rounded-lg overflow-hidden bg-black/60 border border-white/[0.06] flex items-center justify-center relative">
                        {thumbSrc ? (
                          <img src={thumbSrc} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                        ) : (
                          <Package className={`w-10 h-10 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-600'}`} />
                        )}
                        {isSelected && (
                          <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-[#25F4EE] text-black flex items-center justify-center shadow-md">
                            <Check className="w-3 h-3 stroke-[3]" />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="space-y-1">
                        <div className={`text-xs font-bold truncate leading-tight ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                          {p.name}
                        </div>
                        {p.price && (
                          <div className="text-xs font-mono font-bold text-amber-400">
                            {p.price}
                          </div>
                        )}
                      </div>

                      {/* Progress Bar & Angle Count */}
                      <div className="space-y-1 pt-1 border-t border-white/[0.06]">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">สคริปต์</span>
                          <span className="font-mono font-bold text-[#25F4EE]">
                            {pDone}/{total} มุม
                          </span>
                        </div>
                        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-12 text-center space-y-3">
                <Package className="w-12 h-12 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400">
                  {productSearch ? `ไม่พบสินค้าที่ตรงกับคำค้นหา "${productSearch}"` : 'ยังไม่มีสินค้าในระบบ'}
                </p>
                {productSearch && (
                  <button
                    onClick={() => setProductSearch('')}
                    className="text-xs text-[#25F4EE] hover:underline font-bold cursor-pointer"
                  >
                    ล้างการค้นหา
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-white/[0.08]">
            <Button
              variant="primary"
              onClick={() => {
                setShowCatalogModal(false);
                setShowAddModal(true);
              }}
              className="flex items-center gap-1.5 text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>วิเคราะห์สินค้าใหม่</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => setShowCatalogModal(false)}
              className="text-xs"
            >
              ปิดหน้าต่าง
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Video Export Preview Modal (Dialog ดูคลิป ณ จุดนั้นทันที) ── */}
      <Modal
        isOpen={!!previewExportAngle}
        onClose={() => setPreviewExportAngle(null)}
        title="🎬 พรีวิววิดีโอที่ตัดต่อเสร็จแล้ว (QC & Export Preview)"
        subtitle={previewExportAngle?.hook_title || productData?.name}
        maxWidth="max-w-md"
      >
        {previewExportAngle && (
          <div className="space-y-3.5">
            <div className="relative rounded-2xl overflow-hidden bg-black aspect-[9/16] max-h-[66vh] mx-auto border border-white/[0.1] shadow-2xl flex items-center justify-center">
              <video
                src={toMediaUrl(previewExportAngle.video_url)}
                controls
                autoPlay
                playsInline
                className="w-full h-full object-contain"
              />
            </div>

            {/* Meta & Quick Details */}
            <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <Check className="w-3.5 h-3.5" />
                  <span>เรนเดอร์เสร็จสมบูรณ์พร้อมโพสต์ (9:16)</span>
                </span>
                {previewExportAngle.badge && (
                  <Badge variant="cyan" size="sm">{previewExportAngle.badge}</Badge>
                )}
              </div>
              {previewExportAngle.tiktok_caption && (
                <p className="text-xs text-slate-300 line-clamp-2 font-mono leading-relaxed select-all">
                  {previewExportAngle.tiktok_caption} {previewExportAngle.tiktok_hashtags}
                </p>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center gap-2 pt-1">
              {onGoToGallery && (
                <button
                  type="button"
                  onClick={() => {
                    setPreviewExportAngle(null);
                    onGoToGallery();
                  }}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                  title="ไปที่หน้าคลัง Export ทั้งหมด"
                >
                  <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
                  <span>เปิดใน Gallery</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  const ang = previewExportAngle;
                  setPreviewExportAngle(null);
                  handleOpenInTimeline(ang, openAngleIdx >= 0 ? openAngleIdx : 0);
                }}
                className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
                title="เปิดดูในไทม์ไลน์"
              >
                <Play className="w-3.5 h-3.5 fill-white text-white" />
                <span>เปิดดูในไทม์ไลน์</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Delete Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!deleteTargetProduct}
        onClose={() => setDeleteTargetProduct(null)}
        onConfirm={confirmDeleteProduct}
        title="ลบสินค้าและสคริปต์ทั้งหมดถาวร?"
        description="ข้อมูลสินค้า สเปก และสคริปต์มุมมองขายทั้งหมดจะถูกลบออกจากระบบ"
        itemName={deleteTargetProduct?.title || deleteTargetProduct?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบข้อมูลถาวร"
        loading={isDeletingProduct}
        variant="danger"
      />
    </div>
  );
}
