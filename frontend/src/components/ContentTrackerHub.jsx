import React, { useState, useEffect, useMemo, useCallback, useRef, memo } from 'react';
import {
  Layers, Clapperboard, Check, Trash2, ArrowRight, Play,
  Smartphone, RefreshCw, Search, QrCode, ArrowLeft, Copy,
  Kanban, Table, Calendar, Sparkles, CheckCircle2, Clock,
  ExternalLink, ChevronRight, ChevronLeft, Filter, AlertCircle,
  Video, Eye, Flame, TrendingUp, Plus
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import {
  getProducts, updateAngleStatus, deleteProduct, updateProduct
} from '../api';
import { Modal, Toast, Button, Badge, Input } from './ui';
import { useDebounce, useToast } from '../hooks';

// 5 Granular Pipeline Phases with distinctive neon badges & icons
const PIPELINE_PHASES = [
  { id: 'scripted', label: '1. สคริปต์พร้อม', icon: Sparkles, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10', glow: 'shadow-cyan-500/20', desc: 'AI แต่งบท & แคปชันเสร็จแล้ว' },
  { id: 'in_production', label: '2. กำลังตัดต่อ', icon: Clapperboard, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10', glow: 'shadow-amber-500/20', desc: 'โหลดเข้าห้องตัดต่อ 1-Click Studio' },
  { id: 'rendered', label: '3. ตัดต่อเสร็จ', icon: Video, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10', glow: 'shadow-blue-500/20', desc: 'เรนเดอร์ 9:16 สำเร็จ พร้อมตรวจ QC' },
  { id: 'mobile_ready', label: '4. ส่งเข้ามือถือ', icon: Smartphone, color: 'text-purple-400 border-purple-500/30 bg-purple-500/10', glow: 'shadow-purple-500/20', desc: 'สแกน QR โหลดคลิปเข้ามือถือแล้ว' },
  { id: 'posted', label: '5. โพสต์แล้ว', icon: CheckCircle2, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10', glow: 'shadow-emerald-500/20', desc: 'คลิปออนไลน์บน TikTok เรียบร้อย' },
];

const PHASE_ORDER = ['scripted', 'in_production', 'rendered', 'mobile_ready', 'posted'];

// ═══════════════════════════════════════════════════════════════════════
// 🎬 HOVER VIDEO PREVIEW THUMBNAIL COMPONENT
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
      className="relative w-full aspect-[9/16] rounded-xl overflow-hidden bg-black/60 border border-white/[0.1] hover:border-[#25F4EE] transition-all cursor-pointer group shadow-inner"
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
          <div className="w-8 h-8 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center text-white border border-white/[0.2] shadow-md group-hover:scale-110 transition-transform">
            <Play className="w-3.5 h-3.5 fill-current text-[#25F4EE] ml-0.5" />
          </div>
        </div>
      )}
      <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 backdrop-blur-sm text-[9px] font-mono text-slate-300 border border-white/[0.08]">
        พรีวิว
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📌 MEMOIZED KANBAN CARD (Drag & Drop + Quick Actions)
// ═══════════════════════════════════════════════════════════════════════
const KanbanCard = memo(function KanbanCard({
  ang,
  phaseId,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onCopyCaption,
  onGoToEditor,
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
      className="p-3.5 rounded-2xl bg-[#0E131F]/90 border border-white/[0.08] hover:border-[#25F4EE]/50 hover:shadow-lg hover:shadow-[#25F4EE]/10 transition-all space-y-3 relative group"
    >
      {/* Product Title & Badge */}
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-bold text-white truncate flex-1 min-w-0 font-kanit" title={ang.parentProduct?.name}>
          {ang.parentProduct?.name}
        </span>
        {ang.badge && (
          <Badge variant="cyan" size="sm">
            {ang.badge}
          </Badge>
        )}
      </div>

      {/* Hook Title */}
      <div className="p-2 rounded-xl bg-black/60 border-l-4 border-[#25F4EE] text-xs font-bold text-cyan-200 leading-snug">
        {ang.hook_title}
      </div>

      {/* Video Hover Thumbnail (for rendered / mobile_ready / posted) */}
      {ang.video_url && (
        <div className="w-full max-w-[140px] mx-auto pt-1">
          <HoverVideoThumb
            videoUrl={ang.video_url}
            onClick={() => onPreviewVideo(ang.video_url)}
          />
        </div>
      )}

      {/* Phase-specific Primary Action */}
      {phaseId === 'scripted' && (
        <Button
          onClick={() => onSendToStudio(ang.parentProduct, ang)}
          variant="tiktok"
          size="sm"
          icon={Clapperboard}
          className="w-full"
        >
          ส่งตัดต่อใน Studio
        </Button>
      )}

      {phaseId === 'in_production' && (
        <div className="space-y-1.5">
          <Button
            onClick={() => onSendToStudio(ang.parentProduct, ang)}
            variant="tiktok"
            size="sm"
            iconRight={ArrowRight}
            className="w-full"
          >
            เปิดทำต่อใน Studio
          </Button>
          <button
            onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'rendered')}
            className="w-full py-1.5 px-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-colors"
          >
            <Check className="w-3 h-3 text-emerald-400" />
            <span>มาร์กว่าตัดเสร็จแล้ว</span>
          </button>
        </div>
      )}

      {phaseId === 'rendered' && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            {ang.video_url && (
              <button
                onClick={() => onPreviewVideo(ang.video_url)}
                className="flex-1 py-1.5 px-2 rounded-xl bg-white/[0.05] border border-white/[0.08] text-slate-200 hover:bg-white/[0.1] text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                <span>พรีวิว</span>
              </button>
            )}
            <button
              onClick={() => onOpenQrModal(ang)}
              className="flex-1 py-1.5 px-2 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] hover:bg-[#25F4EE]/20 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
            >
              <QrCode className="w-3 h-3" />
              <span>ส่งมือถือ</span>
            </button>
          </div>
        </div>
      )}

      {phaseId === 'mobile_ready' && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onOpenQrModal(ang)}
              className="flex-1 py-1.5 px-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 hover:bg-purple-500/20 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
            >
              <QrCode className="w-3 h-3" />
              <span>เปิด QR ซ้ำ</span>
            </button>
            <button
              onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'posted')}
              className="flex-1 py-1.5 px-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
            >
              <Check className="w-3 h-3" />
              <span>โพสต์แล้ว</span>
            </button>
          </div>
        </div>
      )}

      {phaseId === 'posted' && (
        <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center text-xs text-emerald-300 font-bold flex items-center justify-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>คลิปออนไลน์สำเร็จ</span>
        </div>
      )}

      {/* Caption Copy Helper */}
      {captionText && (
        <button
          onClick={() => onCopyCaption(captionText, ang.angle_id)}
          className="w-full py-1.5 px-2 rounded-xl bg-black/40 hover:bg-black/60 border border-white/[0.06] text-[11px] text-slate-400 hover:text-white flex items-center justify-between cursor-pointer transition-colors"
        >
          <span className="truncate max-w-[170px] font-mono text-[10px]">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
          <span className="text-[#25F4EE] font-bold flex items-center gap-1 flex-shrink-0 text-[10px]">
            {copiedAngleId === ang.angle_id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copiedAngleId === ang.angle_id ? 'คัดลอกแล้ว' : 'แคปชัน'}
          </span>
        </button>
      )}

      {/* Quick Phase Shifter Arrows */}
      <div className="flex items-center justify-between pt-1 border-t border-white/[0.06] text-[10px] text-slate-400">
        {prevPhase ? (
          <button
            onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, prevPhase)}
            className="flex items-center gap-0.5 hover:text-[#25F4EE] cursor-pointer transition-colors"
            title="ถอยกลับเฟสก่อนหน้า"
          >
            <ChevronLeft className="w-3 h-3" />
            <span>ถอยเฟส</span>
          </button>
        ) : <div />}

        {nextPhase && (
          <button
            onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, nextPhase)}
            className="flex items-center gap-0.5 text-[#25F4EE] hover:underline font-bold cursor-pointer transition-colors ml-auto"
            title="เลื่อนไปเฟสถัดไป"
          >
            <span>เลื่อนเฟส</span>
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📋 TABLE VIEW COMPONENT (Clean High-Density List)
// ═══════════════════════════════════════════════════════════════════════
const TableRow = memo(function TableRow({
  ang,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onCopyCaption,
  copiedAngleId
}) {
  const currentPhase = PIPELINE_PHASES.find(p => p.id === ang.status) || PIPELINE_PHASES[0];

  return (
    <tr className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
      {/* 1. Media Preview */}
      <td className="py-3 px-3 w-16">
        {ang.video_url ? (
          <button
            onClick={() => onPreviewVideo(ang.video_url)}
            className="w-10 h-14 rounded-lg overflow-hidden bg-black relative border border-white/[0.1] hover:border-[#25F4EE] flex-shrink-0 group cursor-pointer"
          >
            <video src={`/api/media/${ang.video_url}`} className="w-full h-full object-cover" muted />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/10">
              <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
            </div>
          </button>
        ) : (
          <div className="w-10 h-14 rounded-lg bg-black/40 border border-white/[0.06] flex items-center justify-center text-[10px] text-slate-600 font-mono">
            -
          </div>
        )}
      </td>

      {/* 2. Product & Hook Title */}
      <td className="py-3 px-3">
        <div className="space-y-0.5 max-w-xs sm:max-w-md">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-white text-xs">{ang.parentProduct?.name}</span>
            {ang.badge && <Badge variant="cyan" size="sm">{ang.badge}</Badge>}
          </div>
          <p className="text-xs text-cyan-200 font-bold line-clamp-1">{ang.hook_title}</p>
        </div>
      </td>

      {/* 3. Status Phase Selector */}
      <td className="py-3 px-3">
        <select
          value={ang.status}
          onChange={(e) => onStatusChange(ang.parentProduct.id, ang.angle_id, e.target.value)}
          className={`py-1.5 px-2.5 rounded-xl text-xs font-bold border focus:outline-none cursor-pointer ${currentPhase.color}`}
        >
          {PIPELINE_PHASES.map((p) => (
            <option key={p.id} value={p.id} className="bg-[#080B11] text-white">
              {p.label}
            </option>
          ))}
        </select>
      </td>

      {/* 4. Caption Preview & Copy */}
      <td className="py-3 px-3">
        <button
          onClick={() => onCopyCaption(`${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`, ang.angle_id)}
          className="text-left py-1 px-2 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.06] text-slate-300 text-xs flex items-center justify-between gap-2 max-w-[200px] cursor-pointer"
        >
          <span className="truncate text-[11px] font-mono">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
          <span className="text-[#25F4EE] flex-shrink-0">
            {copiedAngleId === ang.angle_id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          </span>
        </button>
      </td>

      {/* 5. Direct Action Buttons */}
      <td className="py-3 px-3 text-right">
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => onSendToStudio(ang.parentProduct, ang)}
            className="py-1 px-2.5 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center gap-1 cursor-pointer"
            title="ส่งเข้า 1-Click Studio"
          >
            <Clapperboard className="w-3 h-3" />
            <span>Studio</span>
          </button>

          <button
            onClick={() => onOpenQrModal(ang)}
            className="p-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 cursor-pointer"
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
// 🌟 MAIN CONTENT TRACKER HUB COMPONENT
// ═══════════════════════════════════════════════════════════════════════
export default function ContentTrackerHub({ onApplyToStudio, onRefresh, onGoToGallery, onGoToEditor, onGoToFlow }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [selectedPhaseFilter, setSelectedPhaseFilter] = useState('all');
  const [publicationFilter, setPublicationFilter] = useState('all'); // 'all' | 'pending' | 'published'
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' | 'table'
  const [copiedAngleId, setCopiedAngleId] = useState(null);
  const [previewVideoUrl, setPreviewVideoUrl] = useState(null);
  const [qrModalItem, setQrModalItem] = useState(null);
  const [mobileActivePhase, setMobileActivePhase] = useState('scripted');
  const { toastMessage, showToast, hideToast } = useToast();

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
      showToast('อัปเดตสถานะสำเร็จ');
    } catch (err) {
      alert('ไม่สามารถอัปเดตสถานะได้: ' + err.message);
    }
  }, [showToast]);

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

  // Completion Percentage
  const completionRate = useMemo(() => {
    if (allAnglesList.length === 0) return 0;
    return Math.round((phaseCounts.posted / allAnglesList.length) * 100);
  }, [allAnglesList.length, phaseCounts.posted]);

  // Filtered angles with useMemo and Debounced Search
  const filteredAngles = useMemo(() => {
    const q = (debouncedSearch || '').toLowerCase().trim();
    return allAnglesList.filter(a => {
      const matchesSearch = !q ||
        a.parentProduct?.name?.toLowerCase().includes(q) ||
        a.hook_title?.toLowerCase().includes(q) ||
        a.angle_name?.toLowerCase().includes(q);

      const matchesProduct = selectedProductFilter === 'all' || a.parentProduct?.id === selectedProductFilter;
      const matchesPhase = selectedPhaseFilter === 'all' || a.status === selectedPhaseFilter;
      const matchesPub =
        publicationFilter === 'all' ? true :
        publicationFilter === 'published' ? a.status === 'posted' :
        a.status !== 'posted';

      return matchesSearch && matchesProduct && matchesPhase && matchesPub;
    });
  }, [allAnglesList, debouncedSearch, selectedProductFilter, selectedPhaseFilter, publicationFilter]);

  const mobileUrl = typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '';

  // Drag & Drop Handler
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
    <div className="space-y-5 animate-fadeIn pb-16">
      {/* Central Toast */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* Video Modal Preview with memory-safe video tag */}
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
          1. PIPELINE ANALYTICS & METRICS DASHBOARD (TOP HERO)
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-panel p-5 sm:p-6 rounded-3xl border border-white/[0.08] bg-gradient-to-br from-[#0D121E] via-[#090C14] to-[#0D121E] space-y-5 shadow-2xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-lg shadow-[#25F4EE]/15 flex-shrink-0">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg sm:text-xl font-bold font-kanit text-white flex items-center gap-2">
                  <span>Content Pipeline & Production Tracker</span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 font-mono font-bold">
                    {allAnglesList.length} คลิปในระบบ
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  ระบบติดตามและบริหารงานผลิตวิดีโอ 5 ขั้นตอน สไตล์ Notion & ClickUp
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full lg:w-auto justify-end">
            <Button
              onClick={fetchProductsData}
              loading={loading}
              variant="secondary"
              size="sm"
              icon={RefreshCw}
            >
              รีเฟรชข้อมูล
            </Button>
          </div>
        </div>

        {/* 6 Interactive Stat & Filter Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {/* Card 0: All Angles */}
          <div
            onClick={() => setSelectedPhaseFilter('all')}
            className={`p-3 rounded-2xl border transition-all cursor-pointer space-y-1.5 ${
              selectedPhaseFilter === 'all'
                ? 'bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE] ring-2 ring-[#25F4EE]/40 shadow-lg shadow-[#25F4EE]/10'
                : 'bg-black/40 border-white/[0.08] hover:border-white/[0.2] hover:bg-black/60'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold flex items-center gap-1.5 text-white">
                <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>ทั้งหมด</span>
              </span>
              <span className="font-mono text-base font-bold text-white">{allAnglesList.length}</span>
            </div>
            <div className="text-[10px] text-slate-500 truncate">คลิปทั้งหมดในระบบ</div>
          </div>

          {/* Cards 1..5: Pipeline Phases */}
          {PIPELINE_PHASES.map((p) => {
            const Icon = p.icon;
            const count = phaseCounts[p.id] || 0;
            const isSelected = selectedPhaseFilter === p.id;

            return (
              <div
                key={p.id}
                onClick={() => setSelectedPhaseFilter(isSelected ? 'all' : p.id)}
                className={`p-3 rounded-2xl border transition-all cursor-pointer space-y-1.5 ${
                  isSelected
                    ? `${p.color} ring-2 ring-[#25F4EE]/50 shadow-lg`
                    : 'bg-black/40 border-white/[0.08] hover:border-white/[0.2] hover:bg-black/60'
                }`}
              >
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold flex items-center gap-1.5">
                    <Icon className="w-3.5 h-3.5" />
                    <span>{p.label.split('.')[1]}</span>
                  </span>
                  <span className="font-mono text-base font-bold text-white">{count}</span>
                </div>
                <div className="text-[10px] text-slate-500 truncate">{p.desc}</div>
              </div>
            );
          })}
        </div>

        {/* Overall Completion Progress Bar */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>ความคืบหน้าการเผยแพร่แคมเปญ (Published Rate)</span>
            </span>
            <span className="font-mono font-bold text-[#25F4EE]">{completionRate}% สำเร็จ</span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-900 overflow-hidden border border-white/[0.06]">
            <div
              className="h-full bg-gradient-to-r from-[#25F4EE] via-[#FE2C55] to-emerald-400 transition-all duration-500 rounded-full"
              style={{ width: `${Math.max(5, completionRate)}%` }}
            />
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          2. MULTI-VIEW & SEARCH TOOLBAR
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-card p-4 rounded-2xl border border-white/[0.08]">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ค้นหาชื่อสินค้า, สคริปต์, หรือ Hook..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#080B11] border border-white/[0.1] text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50 shadow-inner"
            />
          </div>

          {/* Product Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedProductFilter}
              onChange={(e) => setSelectedProductFilter(e.target.value)}
              className="py-2 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-xs font-bold text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer"
            >
              <option value="all">สินค้าทั้งหมด ({products.length})</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} ({(p.angles || []).length} คลิป)
                </option>
              ))}
            </select>

            {/* Publication Filter */}
            <select
              value={publicationFilter}
              onChange={(e) => setPublicationFilter(e.target.value)}
              className="py-2 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-xs font-bold text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer"
            >
              <option value="all">ทุกสถานะ</option>
              <option value="pending">รอโพสต์ ({allAnglesList.length - phaseCounts.posted})</option>
              <option value="published">โพสต์แล้ว ({phaseCounts.posted})</option>
            </select>

            {/* Multi-View Switcher (Kanban vs Table) */}
            <div className="flex items-center p-1 rounded-xl bg-black/60 border border-white/[0.1]">
              <button
                type="button"
                onClick={() => setViewMode('kanban')}
                className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'kanban'
                    ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="มุมมอง Kanban Board"
              >
                <Kanban className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">บอร์ด</span>
              </button>

              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'table'
                    ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="มุมมอง Table ตาราง"
              >
                <Table className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">ตาราง</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          MOBILE PHASE SWITCHER TABS (ON SMALL SCREENS)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'kanban' && (
        <div className="xl:hidden flex items-center gap-1.5 overflow-x-auto pb-2 no-scrollbar">
          {PIPELINE_PHASES.map((p) => {
            const count = phaseCounts[p.id] || 0;
            const isActive = mobileActivePhase === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => setMobileActivePhase(p.id)}
                className={`py-2 px-3 rounded-2xl text-xs font-bold flex items-center gap-1.5 whitespace-nowrap border transition-all cursor-pointer flex-shrink-0 ${
                  isActive
                    ? 'bg-[#25F4EE]/20 text-[#25F4EE] border-[#25F4EE]/50 shadow-md'
                    : 'bg-black/40 text-slate-400 border-white/[0.08]'
                }`}
              >
                <span>{p.label}</span>
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-black/60">{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          VIEW 1: 5-PHASE KANBAN BOARD (DRAG & DROP READY)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'kanban' && (
        <>
          {/* Desktop Full 5-Column Grid */}
          <div className="hidden xl:grid xl:grid-cols-5 gap-4 items-start">
            {PIPELINE_PHASES.map((phase) => {
              const phaseAngles = filteredAngles.filter(a => a.status === phase.id);

              return (
                <div
                  key={phase.id}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDropOnColumn(phase.id, e)}
                  className="p-4 border border-white/[0.08] space-y-3.5 rounded-3xl glass-card transition-colors hover:border-white/[0.15]"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.08]">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-white font-kanit">
                      <phase.icon className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>{phase.label}</span>
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-black/60 border border-white/[0.08] text-slate-300">
                      {phaseAngles.length}
                    </span>
                  </div>

                  <div className="space-y-3 min-h-[160px]">
                    {phaseAngles.length === 0 ? (
                      <div className="py-12 text-center text-xs text-slate-500 border border-dashed border-white/[0.06] rounded-2xl">
                        ลากการ์ดมาวางที่นี่
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
                          onCopyCaption={handleCopyCaption}
                          onGoToEditor={onGoToEditor}
                          copiedAngleId={copiedAngleId}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Mobile Single-Column Active Phase View */}
          <div className="xl:hidden">
            {(() => {
              const curPhase = PIPELINE_PHASES.find(p => p.id === mobileActivePhase) || PIPELINE_PHASES[0];
              const phaseAngles = filteredAngles.filter(a => a.status === curPhase.id);

              return (
                <div className="p-4 border border-white/[0.08] space-y-3.5 rounded-3xl glass-card">
                  <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
                    <div className="flex items-center gap-2 text-sm font-bold text-white font-kanit">
                      <curPhase.icon className="w-4 h-4 text-[#25F4EE]" />
                      <span>{curPhase.label}</span>
                    </div>
                    <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-black/60 border border-white/[0.1] text-slate-300">
                      {phaseAngles.length} รายการ
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {phaseAngles.length === 0 ? (
                      <div className="py-16 text-center text-xs text-slate-500 col-span-full">
                        ไม่มีคลิปในขั้นตอนนี้
                      </div>
                    ) : (
                      phaseAngles.map((ang, idx) => (
                        <KanbanCard
                          key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                          ang={ang}
                          phaseId={curPhase.id}
                          onSendToStudio={handleSendToStudio}
                          onStatusChange={handleAngleStatusChange}
                          onPreviewVideo={setPreviewVideoUrl}
                          onOpenQrModal={setQrModalItem}
                          onCopyCaption={handleCopyCaption}
                          onGoToEditor={onGoToEditor}
                          copiedAngleId={copiedAngleId}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════
          VIEW 2: CLEAN HIGH-DENSITY TABLE VIEW
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'table' && (
        <div className="glass-card rounded-3xl border border-white/[0.08] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/[0.08] bg-black/60 text-slate-400 font-bold text-[11px]">
                  <th className="py-3 px-3">วิดีโอ</th>
                  <th className="py-3 px-3">สินค้า & มุมขาย (Hook Title)</th>
                  <th className="py-3 px-3">สถานะขั้นตอน</th>
                  <th className="py-3 px-3">แคปชัน TikTok</th>
                  <th className="py-3 px-3 text-right">ปุ่มลัด</th>
                </tr>
              </thead>
              <tbody>
                {filteredAngles.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
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
