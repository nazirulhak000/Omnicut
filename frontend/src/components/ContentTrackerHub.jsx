import React, { useState, useEffect, useMemo, useCallback, useRef, memo } from 'react';
import {
  Layers, Clapperboard, Check, Trash2, ArrowRight, Play,
  Smartphone, RefreshCw, Search, QrCode, ArrowLeft, Copy,
  Kanban, Table, Sparkles, CheckCircle2, Clock,
  ExternalLink, ChevronRight, ChevronLeft, Filter, AlertCircle,
  Video, Eye, Flame, TrendingUp, Plus, X, FileText, Scissors,
  FolderDown, Info
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import {
  getProducts, updateAngleStatus, deleteProduct, updateProduct
} from '../api';
import { Modal, Toast, Button, Badge, Input } from './ui';
import { useDebounce, useToast } from '../hooks';

// 5 Granular Pipeline Phases (Original Vibrant & Readable Palette)
const PIPELINE_PHASES = [
  { id: 'scripted', label: 'สคริปต์พร้อม', short: 'สคริปต์', icon: FileText, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10 active:bg-cyan-500/20', dot: 'bg-cyan-400' },
  { id: 'in_production', label: 'กำลังตัดต่อ', short: 'ตัดต่อ', icon: Clapperboard, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10 active:bg-amber-500/20', dot: 'bg-amber-400' },
  { id: 'rendered', label: 'ตัดต่อเสร็จ', short: 'ตรวจ QC', icon: Video, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10 active:bg-blue-500/20', dot: 'bg-blue-400' },
  { id: 'mobile_ready', label: 'ส่งเข้ามือถือ', short: 'ส่งมือถือ', icon: Smartphone, color: 'text-purple-400 border-purple-500/30 bg-purple-500/10 active:bg-purple-500/20', dot: 'bg-purple-400' },
  { id: 'posted', label: 'โพสต์แล้ว', short: 'โพสต์แล้ว', icon: CheckCircle2, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10 active:bg-emerald-500/20', dot: 'bg-emerald-400' },
];

const PHASE_ORDER = ['scripted', 'in_production', 'rendered', 'mobile_ready', 'posted'];

// ═══════════════════════════════════════════════════════════════════════
// 🎬 HOVER VIDEO PREVIEW THUMBNAIL (Memory Safe & Fast)
// ═══════════════════════════════════════════════════════════════════════
const HoverVideoThumb = memo(function HoverVideoThumb({ videoUrl, onClick }) {
  const [isHovered, setIsHovered] = useState(false);
  const videoRef = useRef(null);

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch(() => {});
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (videoRef.current) {
      videoRef.current.pause();
    }
  };

  if (!videoUrl) return null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative w-full aspect-[9/16] rounded-lg overflow-hidden bg-black/70 border border-white/[0.1] hover:border-[#25F4EE] transition-all cursor-pointer group shadow-sm"
    >
      <video
        ref={videoRef}
        src={`/api/media/${videoUrl}`}
        muted
        playsInline
        loop
        className="w-full h-full object-cover"
      />
      {!isHovered && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/10 transition-colors">
          <div className="w-7 h-7 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center text-white border border-white/[0.2] shadow-md group-hover:scale-110 transition-transform">
            <Play className="w-3 h-3 fill-current text-[#25F4EE] ml-0.5" />
          </div>
        </div>
      )}
      <div className="absolute bottom-1 right-1 px-1.5 py-0.2 rounded bg-black/80 backdrop-blur-sm text-[8px] font-mono text-slate-300 border border-white/[0.08]">
        พรีวิว
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📌 MEMOIZED KANBAN CARD (Ultra High-Density & Deep-Dive Trigger)
// ═══════════════════════════════════════════════════════════════════════
const KanbanCard = memo(function KanbanCard({
  ang,
  phaseId,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onInspectAngle,
  onCopyCaption,
  copiedAngleId
}) {
  const captionText = `${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`.trim();
  const curIdx = PHASE_ORDER.indexOf(phaseId);
  const prevPhase = curIdx > 0 ? PHASE_ORDER[curIdx - 1] : null;
  const nextPhase = curIdx < PHASE_ORDER.length - 1 ? PHASE_ORDER[curIdx + 1] : null;

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', JSON.stringify({
          productId: ang.parentProduct?.id,
          angleId: ang.angle_id,
          fromPhase: phaseId
        }));
      }}
      className="p-2.5 rounded-xl bg-[#0B0F19] border border-white/[0.08] hover:border-[#25F4EE]/40 transition-all space-y-2 relative group shadow-sm"
    >
      {/* 1. Header: Product Name + Badge + Detail Inspect Icon */}
      <div className="flex items-center justify-between gap-1.5 text-xs">
        <span
          onClick={() => onInspectAngle(ang)}
          className="font-bold text-white truncate flex-1 min-w-0 font-kanit text-[11px] hover:text-[#25F4EE] cursor-pointer"
          title={`คลิกเพื่อดูรายละเอียดเชิงลึกของ: ${ang.parentProduct?.name}`}
        >
          {ang.parentProduct?.name}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {ang.badge && (
            <span className="text-[9px] px-1.5 py-0.2 font-mono font-bold rounded bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 whitespace-nowrap">
              {ang.badge}
            </span>
          )}
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-0.5 rounded text-slate-500 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="ดูรายละเอียดจริงเชิงลึก (Deep Dive)"
          >
            <Info className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* 2. Hook Title: Crisp 2-line with thin accent bar (Clickable to inspect) */}
      <div
        onClick={() => onInspectAngle(ang)}
        className="pl-2 border-l-2 border-[#25F4EE] text-xs font-bold text-cyan-200 line-clamp-2 leading-snug cursor-pointer hover:underline"
        title="คลิกเพื่อดูบทพูดและรายละเอียดเต็ม"
      >
        {ang.hook_title}
      </div>

      {/* Video Hover Thumbnail (if rendered) */}
      {ang.video_url && (
        <div className="w-full max-w-[100px] mx-auto pt-0.5">
          <HoverVideoThumb
            videoUrl={ang.video_url}
            onClick={() => onPreviewVideo(ang.video_url)}
          />
        </div>
      )}

      {/* 3. Merged Bottom Action & Stepper Row (ยุบบรรทัดเดียวกัน - Ultra High Density!) */}
      <div className="flex items-center justify-between gap-1.5 pt-1.5 border-t border-white/[0.06]">
        {/* Left: Direct Primary Action */}
        <div className="flex items-center gap-1 min-w-0 flex-1">
          {phaseId === 'scripted' && (
            <button
              onClick={() => onSendToStudio(ang.parentProduct, ang)}
              className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1 cursor-pointer shadow-sm flex-shrink-0"
              title="ส่งตัดต่อใน 1-Click Studio"
            >
              <Clapperboard className="w-3.5 h-3.5" />
              <span>ส่ง Studio</span>
            </button>
          )}

          {phaseId === 'in_production' && (
            <>
              <button
                onClick={() => onSendToStudio(ang.parentProduct, ang)}
                className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1 cursor-pointer shadow-sm flex-shrink-0"
                title="เปิดทำต่อใน 1-Click Studio"
              >
                <span>Studio</span>
                <ArrowRight className="w-3 h-3" />
              </button>
              <button
                onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'rendered')}
                className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-emerald-400 cursor-pointer"
                title="ทำเครื่องหมายว่าตัดเสร็จแล้ว"
              >
                <Check className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {phaseId === 'rendered' && (
            <>
              {ang.video_url && (
                <button
                  onClick={() => onPreviewVideo(ang.video_url)}
                  className="px-2 py-1.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-slate-200 hover:bg-white/[0.12] text-xs font-bold flex items-center gap-1 cursor-pointer"
                  title="พรีวิวตรวจ QC"
                >
                  <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                  <span>QC</span>
                </button>
              )}
              <button
                onClick={() => onOpenQrModal(ang)}
                className="px-2 py-1.5 rounded-lg bg-[#25F4EE]/15 border border-[#25F4EE]/30 text-[#25F4EE] hover:bg-[#25F4EE]/25 text-xs font-bold flex items-center gap-1 cursor-pointer"
                title="ส่งเข้ามือถือ"
              >
                <QrCode className="w-3 h-3" />
                <span>มือถือ</span>
              </button>
            </>
          )}

          {phaseId === 'mobile_ready' && (
            <>
              <button
                onClick={() => onOpenQrModal(ang)}
                className="px-2 py-1.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 hover:bg-purple-500/25 text-xs font-bold flex items-center gap-1 cursor-pointer"
                title="เปิด QR Code"
              >
                <QrCode className="w-3 h-3" />
                <span>QR</span>
              </button>
              <button
                onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'posted')}
                className="px-2 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 text-xs font-bold flex items-center gap-1 cursor-pointer"
                title="มาร์กว่าโพสต์แล้ว"
              >
                <Check className="w-3 h-3" />
                <span>โพสต์แล้ว</span>
              </button>
            </>
          )}

          {phaseId === 'posted' && (
            <div
              onClick={() => onInspectAngle(ang)}
              className="px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-[11px] text-emerald-300 font-bold flex items-center gap-1 cursor-pointer hover:bg-emerald-500/20"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>ออนไลน์แล้ว</span>
            </div>
          )}
        </div>

        {/* Right: Caption Quick Copy & Steppers */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {captionText && (
            <button
              onClick={() => onCopyCaption(captionText, ang.angle_id)}
              className="p-1.5 rounded-lg bg-black/40 hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-white cursor-pointer transition-colors"
              title="คัดลอกแคปชัน & แฮชแท็ก"
            >
              {copiedAngleId === ang.angle_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-[#25F4EE]" />}
            </button>
          )}

          {prevPhase && (
            <button
              onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, prevPhase)}
              className="p-1 rounded text-slate-500 hover:text-white cursor-pointer"
              title={`ย้อนกลับไป: ${PIPELINE_PHASES.find(p => p.id === prevPhase)?.short}`}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          )}

          {nextPhase && (
            <button
              onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, nextPhase)}
              className="px-1.5 py-1 rounded bg-white/[0.04] hover:bg-[#25F4EE]/20 text-[#25F4EE] text-[10px] font-bold flex items-center gap-0.5 cursor-pointer border border-white/[0.06] hover:border-[#25F4EE]/30"
              title={`เลื่อนไป: ${PIPELINE_PHASES.find(p => p.id === nextPhase)?.label}`}
            >
              <span>{PIPELINE_PHASES.find(p => p.id === nextPhase)?.short}</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📋 TABLE VIEW COMPONENT (High-Density True Table Style)
// ═══════════════════════════════════════════════════════════════════════
const TableRow = memo(function TableRow({
  ang,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onInspectAngle,
  onCopyCaption,
  copiedAngleId
}) {
  const currentPhase = PIPELINE_PHASES.find(p => p.id === ang.status) || PIPELINE_PHASES[0];

  return (
    <tr className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
      {/* 1. Media Preview */}
      <td className="py-2 px-3 w-14">
        {ang.video_url ? (
          <button
            onClick={() => onPreviewVideo(ang.video_url)}
            className="w-9 h-12 rounded-lg overflow-hidden bg-black relative border border-white/[0.1] hover:border-[#25F4EE] flex-shrink-0 group cursor-pointer"
          >
            <video src={`/api/media/${ang.video_url}`} className="w-full h-full object-cover" muted />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/10">
              <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
            </div>
          </button>
        ) : (
          <div className="w-9 h-12 rounded-lg bg-black/40 border border-white/[0.06] flex items-center justify-center text-[10px] text-slate-600 font-mono">
            -
          </div>
        )}
      </td>

      {/* 2. Product & Hook Title */}
      <td className="py-2 px-3">
        <div className="space-y-0.5 max-w-xs sm:max-w-md">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              onClick={() => onInspectAngle(ang)}
              className="font-bold text-white text-xs font-kanit hover:text-[#25F4EE] cursor-pointer"
            >
              {ang.parentProduct?.name}
            </span>
            {ang.badge && (
              <span className="flex-shrink-0 whitespace-nowrap">
                <Badge variant="cyan" size="sm">{ang.badge}</Badge>
              </span>
            )}
          </div>
          <p
            onClick={() => onInspectAngle(ang)}
            className="text-xs text-cyan-200 font-bold line-clamp-1 cursor-pointer hover:underline"
          >
            {ang.hook_title}
          </p>
        </div>
      </td>

      {/* 3. Status Phase Selector */}
      <td className="py-2 px-3">
        <select
          value={ang.status}
          onChange={(e) => onStatusChange(ang.parentProduct.id, ang.angle_id, e.target.value)}
          className={`py-1 px-2 rounded-lg text-xs font-bold border focus:outline-none cursor-pointer ${currentPhase.color}`}
        >
          {PIPELINE_PHASES.map((p) => (
            <option key={p.id} value={p.id} className="bg-[#080B11] text-white">
              {p.label}
            </option>
          ))}
        </select>
      </td>

      {/* 4. Caption Preview & Copy */}
      <td className="py-2 px-3">
        <button
          onClick={() => onCopyCaption(`${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`, ang.angle_id)}
          className="text-left py-1 px-2 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.06] text-slate-300 text-xs flex items-center justify-between gap-2 max-w-[180px] cursor-pointer"
        >
          <span className="truncate text-[11px] font-mono">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
          <span className="text-[#25F4EE] flex-shrink-0">
            {copiedAngleId === ang.angle_id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          </span>
        </button>
      </td>

      {/* 5. Direct Action Buttons */}
      <td className="py-2 px-3 text-right">
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-slate-400 hover:text-white cursor-pointer"
            title="ดูรายละเอียดจริงเชิงลึก"
          >
            <Info className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => onSendToStudio(ang.parentProduct, ang)}
            className="py-1 px-2.5 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center gap-1 cursor-pointer"
            title="ส่งเข้า 1-Click Studio"
          >
            <Clapperboard className="w-3 h-3" />
            <span>Studio</span>
          </button>

          <button
            onClick={() => onOpenQrModal(ang)}
            className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 cursor-pointer"
            title="สแกน QR Code เข้ามือถือ"
          >
            <QrCode className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 🌟 MAIN CONTENT TRACKER HUB COMPONENT (True Deep-Dive Tracking)
// ═══════════════════════════════════════════════════════════════════════
export default function ContentTrackerHub({ onApplyToStudio, onRefresh, onGoToGallery, onGoToEditor, onGoToFlow }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [activePhase, setActivePhase] = useState('all'); // 'all' | 'scripted' | 'in_production' | ...
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('capcut_tracker_view_mode') || 'kanban';
    } catch {
      return 'kanban';
    }
  });
  const [copiedAngleId, setCopiedAngleId] = useState(null);
  const [previewVideoUrl, setPreviewVideoUrl] = useState(null);
  const [qrModalItem, setQrModalItem] = useState(null);
  const [inspectAngle, setInspectAngle] = useState(null); // Deep-Dive Inspection state
  const colRefs = useRef({});
  const { toastMessage, showToast, hideToast } = useToast();

  const handleSwitchViewMode = (mode) => {
    setViewMode(mode);
    try {
      localStorage.setItem('capcut_tracker_view_mode', mode);
    } catch {
      // ignore
    }
  };

  const scrollToPhaseColumn = (phaseId) => {
    setActivePhase(phaseId);
    if (viewMode === 'kanban' && phaseId !== 'all' && colRefs.current[phaseId]) {
      colRefs.current[phaseId].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  };

  const fetchProductsData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getProducts();
      if (res.products) {
        setProducts(res.products);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProductsData();
  }, [fetchProductsData]);

  const handleAngleStatusChange = useCallback(async (productId, angleId, nextStatus, videoUrl = null) => {
    try {
      await updateAngleStatus(productId, angleId, nextStatus, videoUrl);
      setProducts(prev => prev.map(p => {
        if (p.id === productId) {
          const updatedAngles = p.angles?.map(a => a.angle_id === angleId ? { ...a, status: nextStatus, ...(videoUrl ? { video_url: videoUrl } : {}) } : a) || [];
          return { ...p, angles: updatedAngles };
        }
        return p;
      }));
      // Also update inspectAngle state if it's currently open
      if (inspectAngle && inspectAngle.angle_id === angleId) {
        setInspectAngle(prev => prev ? { ...prev, status: nextStatus, ...(videoUrl ? { video_url: videoUrl } : {}) } : null);
      }
      showToast('อัปเดตสถานะสำเร็จ');
    } catch (err) {
      alert('ไม่สามารถอัปเดตสถานะได้: ' + err.message);
    }
  }, [inspectAngle, showToast]);

  const handleSendToStudio = useCallback((product, angle, angleIdx = 0) => {
    if (!onApplyToStudio) return;

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');

    // Move to Phase 2: in_production
    handleAngleStatusChange(product.id, angle.angle_id, 'in_production');

    onApplyToStudio({
      productId: product.id,
      angleId: angle.angle_id,
      productName: angle.product_name || product.name || 'สินค้า',
      hookTitle: angle.hook_title || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || product.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || product.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: product.images?.[0]?.local_path || product.images?.[0]?.rel_path || '',
      fullProduct: {
        id: product.id,
        title: product.name,
        description: product.description,
        price_note: product.price_note,
        images: product.images || [],
        angles: product.angles || [angle]
      },
      angleIndex: angleIdx
    });
  }, [onApplyToStudio, handleAngleStatusChange]);

  const handleCopyCaption = useCallback((text, angleId) => {
    navigator.clipboard.writeText(text);
    setCopiedAngleId(angleId);
    showToast('คัดลอกแคปชัน & แฮชแท็กแล้ว!');
    setTimeout(() => setCopiedAngleId(null), 2000);
  }, [showToast]);

  // Flatten all angles with useMemo
  const allAnglesList = useMemo(() => {
    const list = [];
    products.forEach(p => {
      (p.angles || []).forEach(a => {
        list.push({
          ...a,
          parentProduct: p,
          status: a.status || 'scripted'
        });
      });
    });
    return list;
  }, [products]);

  // Phase Stats with useMemo
  const phaseCounts = useMemo(() => ({
    scripted: allAnglesList.filter(a => a.status === 'scripted').length,
    in_production: allAnglesList.filter(a => a.status === 'in_production').length,
    rendered: allAnglesList.filter(a => a.status === 'rendered').length,
    mobile_ready: allAnglesList.filter(a => a.status === 'mobile_ready').length,
    posted: allAnglesList.filter(a => a.status === 'posted').length,
  }), [allAnglesList]);

  // Filtered angles with useMemo and Debounced Search
  const filteredAngles = useMemo(() => {
    const q = (debouncedSearch || '').toLowerCase().trim();
    return allAnglesList.filter(a => {
      const matchesSearch = !q ||
        a.parentProduct?.name?.toLowerCase().includes(q) ||
        a.hook_title?.toLowerCase().includes(q) ||
        a.angle_name?.toLowerCase().includes(q);

      const matchesProduct = selectedProductFilter === 'all' || a.parentProduct?.id === selectedProductFilter;
      const matchesPhase = activePhase === 'all' || a.status === activePhase;

      return matchesSearch && matchesProduct && matchesPhase;
    });
  }, [allAnglesList, debouncedSearch, selectedProductFilter, activePhase]);

  const mobileUrl = typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '';

  // Drag & Drop Handler (Desktop)
  const handleDropOnColumn = (targetPhaseId, e) => {
    e.preventDefault();
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      if (data && data.productId && data.angleId && data.fromPhase !== targetPhaseId) {
        handleAngleStatusChange(data.productId, data.angleId, targetPhaseId);
      }
    } catch (err) {
      console.error('Drop parse error', err);
    }
  };

  return (
    <div className="space-y-3 animate-fadeIn pb-16">
      {/* Central Toast */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ══════════════════════════════════════════════════════════
          🎯 DEEP-DIVE JOB INSPECTOR MODAL (ติดตามงานจริงเชิงลึก)
         ══════════════════════════════════════════════════════════ */}
      <Modal
        isOpen={!!inspectAngle}
        onClose={() => setInspectAngle(null)}
        title="รายละเอียดงานจริงเชิงลึก (Deep-Dive Pipeline Inspector)"
        subtitle={inspectAngle?.parentProduct?.name}
        maxWidth="max-w-2xl"
      >
        {inspectAngle && (() => {
          const currentPhaseInfo = PIPELINE_PHASES.find(p => p.id === inspectAngle.status) || PIPELINE_PHASES[0];
          const scriptLines = Array.isArray(inspectAngle.script_lines)
            ? inspectAngle.script_lines
            : (inspectAngle.script_text ? inspectAngle.script_text.split('\n') : []);
          const captionText = `${inspectAngle.tiktok_caption || ''}\n\n${inspectAngle.tiktok_hashtags || ''}`.trim();

          return (
            <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
              {/* 1. Status Stepper Ribbon inside Modal */}
              <div className="p-3 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${currentPhaseInfo.color}`}>
                    <currentPhaseInfo.icon className="w-3.5 h-3.5" />
                    <span>สถานะปัจจุบัน: {currentPhaseInfo.label}</span>
                  </span>
                  {inspectAngle.badge && (
                    <Badge variant="cyan" size="sm">{inspectAngle.badge}</Badge>
                  )}
                </div>

                {/* Quick Switcher dropdown in Modal */}
                <select
                  value={inspectAngle.status}
                  onChange={(e) => handleAngleStatusChange(inspectAngle.parentProduct.id, inspectAngle.angle_id, e.target.value)}
                  className="py-1 px-2.5 rounded-lg bg-black/70 border border-white/[0.1] text-xs font-bold text-slate-200 focus:outline-none cursor-pointer"
                >
                  {PIPELINE_PHASES.map(p => (
                    <option key={p.id} value={p.id} className="bg-[#080B11] text-white">
                      เปลี่ยนเป็น: {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 2. Hook Title 3s */}
              <div className="space-y-1">
                <div className="text-[11px] font-semibold text-slate-400">Hook 3 วินาทีแรก (จุดหยุดคนดู):</div>
                <div className="p-3 rounded-xl bg-[#080B11] border-l-4 border-[#25F4EE] text-xs sm:text-sm font-bold text-cyan-200 leading-snug">
                  {inspectAngle.hook_title || 'ไม่มี Hook'}
                </div>
              </div>

              {/* 3. Script Breakdown Section */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span>บทพูดพากย์ทั้งหมด ({scriptLines.length} ท่อน):</span>
                  {scriptLines.length > 0 && (
                    <button
                      onClick={() => handleCopyCaption(scriptLines.join('\n'), 'script_modal')}
                      className="text-[#25F4EE] hover:underline flex items-center gap-1 text-[11px] font-bold cursor-pointer"
                    >
                      {copiedAngleId === 'script_modal' ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอกสคริปต์</>}
                    </button>
                  )}
                </div>
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs text-slate-200">
                  {scriptLines.length === 0 ? (
                    <div className="text-slate-500 text-center py-4">ไม่มีบทพูด</div>
                  ) : (
                    scriptLines.map((line, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-[#25F4EE] font-bold flex-shrink-0">{idx + 1}.</span>
                        <span>{line}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* 4. Video QC Player (If Rendered) */}
              {inspectAngle.video_url && (
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-slate-300">วิดีโอที่ตัดต่อเสร็จแล้ว (QC Player):</div>
                  <video
                    src={`/api/media/${inspectAngle.video_url}`}
                    controls
                    className="w-full max-h-64 rounded-xl bg-black object-contain border border-white/[0.08]"
                  />
                </div>
              )}

              {/* 5. TikTok Caption & Hashtags */}
              {captionText && (
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                    <span>แคปชัน & แฮชแท็ก TikTok:</span>
                    <button
                      onClick={() => handleCopyCaption(captionText, 'cap_modal')}
                      className="text-[#25F4EE] hover:underline flex items-center gap-1 text-[11px] font-bold cursor-pointer"
                    >
                      {copiedAngleId === 'cap_modal' ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอกแคปชัน</>}
                    </button>
                  </div>
                  <p className="text-xs text-slate-300 font-mono line-clamp-3 select-all">
                    {inspectAngle.tiktok_caption} {inspectAngle.tiktok_hashtags}
                  </p>
                </div>
              )}

              {/* 6. True Deep-Dive Navigation Action Grid */}
              <div className="pt-2 border-t border-white/[0.08] grid grid-cols-1 sm:grid-cols-2 gap-2">
                {/* Button 1: Go to Script Lab (Menu 1) */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    onGoToFlow?.(inspectAngle.parentProduct?.id);
                  }}
                  className="py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <FileText className="w-4 h-4 text-indigo-400" />
                  <span>ดูสคริปต์ใน Lab สินค้า</span>
                </button>

                {/* Button 2: Go to 1-Click Studio (Menu 3) */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    handleSendToStudio(inspectAngle.parentProduct, inspectAngle);
                  }}
                  className="py-2.5 px-3 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-[#FE2C55]/20 active:scale-95 transition-all"
                >
                  <Clapperboard className="w-4 h-4 text-white" />
                  <span>เปิดทำใน 1-Click Studio</span>
                </button>

                {/* Button 3: Go to Video Editor (Menu 4) */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    onGoToEditor?.();
                  }}
                  className="py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <Scissors className="w-4 h-4 text-purple-400" />
                  <span>เปิดไทม์ไลน์ใน Video Editor</span>
                </button>

                {/* Button 4: Mobile QR / Gallery */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    setQrModalItem(inspectAngle);
                  }}
                  className="py-2.5 px-3 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <QrCode className="w-4 h-4 text-[#25F4EE]" />
                  <span>สแกน QR ส่งเข้ามือถือ</span>
                </button>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* Video Modal Preview */}
      <Modal
        isOpen={!!previewVideoUrl}
        onClose={() => setPreviewVideoUrl(null)}
        title="พรีวิววิดีโอ (ตรวจ QC ก่อนโพสต์)"
        maxWidth="max-w-md"
      >
        {previewVideoUrl && (
          <div className="space-y-3">
            <video
              src={`/api/media/${previewVideoUrl}`}
              controls
              autoPlay
              className="w-full rounded-2xl bg-black aspect-[9/16] object-contain max-h-[70vh] shadow-2xl border border-white/[0.08]"
            />
          </div>
        )}
      </Modal>

      {/* QR Code Modal for Mobile Transfer */}
      <Modal
        isOpen={!!qrModalItem}
        onClose={() => setQrModalItem(null)}
        title="สแกน QR เพื่อส่งคลิปเข้ามือถือ"
        subtitle={qrModalItem?.hook_title}
        maxWidth="max-w-sm"
      >
        {qrModalItem && (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] flex items-center justify-center mx-auto shadow-md">
              <Smartphone className="w-6 h-6" />
            </div>

            <div className="bg-white p-3 rounded-2xl inline-block shadow-xl">
              <QRCodeSVG value={mobileUrl} size={180} />
            </div>

            {/* Caption Preview & Copy inside Modal */}
            <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-left space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                <span>แคปชัน & แฮชแท็กพร้อมโพสต์:</span>
                <button
                  onClick={() => handleCopyCaption(`${qrModalItem.tiktok_caption || ''}\n\n${qrModalItem.tiktok_hashtags || ''}`, 'modal')}
                  className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  {copiedAngleId === 'modal' ? <><Check className="w-3.5 h-3.5 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3.5 h-3.5" /> คัดลอก</>}
                </button>
              </div>
              <p className="text-xs text-slate-300 line-clamp-3 font-mono leading-relaxed select-all">
                {qrModalItem.tiktok_caption} {qrModalItem.tiktok_hashtags}
              </p>
            </div>

            <Button
              onClick={() => {
                handleAngleStatusChange(qrModalItem.parentProduct.id, qrModalItem.angle_id, 'mobile_ready');
                setQrModalItem(null);
                showToast('อัปเดตสถานะเป็น "ส่งเข้ามือถือแล้ว"');
              }}
              variant="tiktok"
              size="md"
              icon={Check}
              className="w-full"
            >
              มาร์กว่า "ส่งเข้ามือถือแล้ว"
            </Button>
          </div>
        )}
      </Modal>

      {/* ══════════════════════════════════════════════════════════
          1. COMPACT METRIC CHIPS RIBBON (TAP TO SWITCH/FILTER)
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-panel p-2 rounded-xl border border-white/[0.08] bg-[#0B0E17]">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 no-scrollbar pr-4">
          {/* Card 0: All */}
          <button
            type="button"
            onClick={() => scrollToPhaseColumn('all')}
            className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 border ${
              activePhase === 'all'
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border-[#25F4EE]/50 shadow-sm'
                : 'bg-black/40 text-slate-400 border-white/[0.08] hover:text-white hover:border-white/[0.15]'
            }`}
          >
            <span>ทั้งหมด</span>
            <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-black/60">{allAnglesList.length}</span>
          </button>

          {/* Cards 1..5 */}
          {PIPELINE_PHASES.map((p) => {
            const count = phaseCounts[p.id] || 0;
            const isActive = activePhase === p.id;
            const Icon = p.icon;

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => scrollToPhaseColumn(isActive && activePhase !== 'all' ? 'all' : p.id)}
                className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 border ${
                  isActive
                    ? `${p.color} ring-1 ring-[#25F4EE]/40 shadow-sm font-bold`
                    : 'bg-black/40 text-slate-400 border-white/[0.08] hover:text-white hover:border-white/[0.15]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{p.short}</span>
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-black/60 font-bold">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          2. STREAMLINED SEARCH & VIEW CONTROLS (MERGED ROW)
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-card p-2 rounded-xl border border-white/[0.08] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-2">
        {/* Search Box */}
        <div className="relative flex-1 min-w-0">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ค้นหาชื่อสินค้า, สคริปต์, หรือ Hook..."
            className="w-full pl-8 pr-7 py-1.5 rounded-lg bg-[#080B11] border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Product Filter Dropdown & View Mode Switcher (Merged Row) */}
        <div className="flex items-center gap-1.5 justify-between md:justify-end flex-shrink-0">
          <select
            value={selectedProductFilter}
            onChange={(e) => setSelectedProductFilter(e.target.value)}
            className="py-1.5 px-2 rounded-lg bg-[#080B11] border border-white/[0.1] text-xs font-bold text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer max-w-[150px] sm:max-w-[200px] truncate"
          >
            <option value="all">สินค้าทั้งหมด ({products.length})</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} ({(p.angles || []).length})
              </option>
            ))}
          </select>

          {/* Multi-View Switcher */}
          <div className="flex items-center p-0.5 rounded-lg bg-black/60 border border-white/[0.1] flex-shrink-0">
            <button
              type="button"
              onClick={() => handleSwitchViewMode('kanban')}
              className={`py-1 px-2 rounded-md text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                viewMode === 'kanban'
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองบอร์ด (Kanban)"
            >
              <Kanban className="w-3 h-3" />
              <span>บอร์ด</span>
            </button>

            <button
              type="button"
              onClick={() => handleSwitchViewMode('table')}
              className={`py-1 px-2 rounded-md text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองตาราง (Table)"
            >
              <Table className="w-3 h-3" />
              <span>ตาราง</span>
            </button>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          3. REAL HORIZONTAL KANBAN BOARD (SWIPEABLE COLUMNS)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'kanban' && (
        <div className="space-y-1.5">
          {/* Mobile Swipe Hint */}
          <div className="flex xl:hidden items-center justify-between text-[10px] text-slate-400 px-1">
            <span className="flex items-center gap-1 text-slate-400">
              <ChevronLeft className="w-3 h-3 text-[#25F4EE]" />
              <span>เลื่อนซ้าย-ขวาเพื่อดูหัวข้อถัดไป</span>
              <ChevronRight className="w-3 h-3 text-[#25F4EE]" />
            </span>
            <span className="text-[#25F4EE] font-bold font-mono">5 คอลัมน์</span>
          </div>

          {/* Real Horizontal Kanban Board with Snap-Scroll */}
          <div className="flex overflow-x-auto snap-x snap-mandatory gap-2.5 pb-3 no-scrollbar scroll-smooth items-start xl:grid xl:grid-cols-5 xl:overflow-x-visible xl:snap-none">
            {PIPELINE_PHASES.map((phase) => {
              const phaseAngles = filteredAngles.filter(a => a.status === phase.id);

              return (
                <div
                  key={phase.id}
                  ref={(el) => (colRefs.current[phase.id] = el)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDropOnColumn(phase.id, e)}
                  className="w-[82vw] max-w-[320px] xl:w-auto xl:max-w-none flex-shrink-0 snap-center p-2.5 border border-white/[0.08] space-y-2 rounded-2xl glass-card transition-colors hover:border-white/[0.15] bg-[#070A12] flex flex-col"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-1.5 border-b border-white/[0.08]">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-white font-kanit">
                      <phase.icon className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>{phase.label}</span>
                    </div>
                    <span className="text-[11px] font-mono font-bold px-1.5 py-0.2 rounded-full bg-black/60 border border-white/[0.08] text-slate-300">
                      {phaseAngles.length}
                    </span>
                  </div>

                  {/* Cards inside column (Vertical Scrollable within column) */}
                  <div className="space-y-2 max-h-[68vh] overflow-y-auto pr-0.5 min-h-[120px]">
                    {phaseAngles.length === 0 ? (
                      <div className="py-8 text-center text-[11px] text-slate-500 border border-dashed border-white/[0.06] rounded-xl">
                        ไม่มีคลิปในขั้นตอนนี้
                      </div>
                    ) : (
                      phaseAngles.map((ang, idx) => (
                        <KanbanCard
                          key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                          ang={ang}
                          phaseId={phase.id}
                          onSendToStudio={handleSendToStudio}
                          onStatusChange={handleAngleStatusChange}
                          onPreviewVideo={setPreviewVideoUrl}
                          onOpenQrModal={setQrModalItem}
                          onInspectAngle={setInspectAngle}
                          onCopyCaption={handleCopyCaption}
                          copiedAngleId={copiedAngleId}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          4. CLEAN HIGH-DENSITY REAL TABLE VIEW
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'table' && (
        <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden bg-[#070A12] shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[620px]">
              <thead>
                <tr className="border-b border-white/[0.08] bg-black/70 text-slate-400 font-bold text-[11px]">
                  <th className="py-2.5 px-3 w-14 text-center">วิดีโอ</th>
                  <th className="py-2.5 px-3 min-w-[180px]">สินค้า & มุมขาย (Hook Title)</th>
                  <th className="py-2.5 px-3 w-32">สถานะขั้นตอน</th>
                  <th className="py-2.5 px-3 w-44">แคปชัน TikTok</th>
                  <th className="py-2.5 px-3 text-right w-24">ปุ่มลัด</th>
                </tr>
              </thead>
              <tbody>
                {filteredAngles.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-xs text-slate-500">
                      ไม่พบข้อมูลคลิปตามเงื่อนไขที่ค้นหา
                    </td>
                  </tr>
                ) : (
                  filteredAngles.map((ang, idx) => (
                    <TableRow
                      key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                      ang={ang}
                      onSendToStudio={handleSendToStudio}
                      onStatusChange={handleAngleStatusChange}
                      onPreviewVideo={setPreviewVideoUrl}
                      onOpenQrModal={setQrModalItem}
                      onInspectAngle={setInspectAngle}
                      onCopyCaption={handleCopyCaption}
                      copiedAngleId={copiedAngleId}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
