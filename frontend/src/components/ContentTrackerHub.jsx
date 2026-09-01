import React, { useState, useEffect, useMemo, useCallback, memo } from 'react';
import {
  Layers, Clapperboard, Check, Trash2, ArrowRight, Play,
  Smartphone, RefreshCw, Search, QrCode, ArrowLeft, Copy
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import {
  getProducts, updateAngleStatus, deleteProduct, updateProduct
} from '../api';
import { Modal, Toast, Button, Badge, Input } from './ui';
import { useDebounce, useToast } from '../hooks';

// 5 Granular Pipeline Phases (Clean Typography)
const PIPELINE_PHASES = [
  { id: 'scripted', label: '1. สคริปต์พร้อม', color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10', desc: 'AI แต่งบท & แคปชันเสร็จแล้ว' },
  { id: 'in_production', label: '2. กำลังตัดต่อ', color: 'text-amber-400 border-amber-500/30 bg-amber-500/10', desc: 'โหลดเข้าห้องตัดต่อ 1-Click Studio' },
  { id: 'rendered', label: '3. ตัดต่อเสร็จ', color: 'text-blue-400 border-blue-500/30 bg-blue-500/10', desc: 'เรนเดอร์ 9:16 สำเร็จ พร้อมตรวจ QC' },
  { id: 'mobile_ready', label: '4. ส่งเข้ามือถือ', color: 'text-purple-400 border-purple-500/30 bg-purple-500/10', desc: 'ส่งไฟล์เข้าสมาร์ตโฟนแล้ว รอโพสต์' },
  { id: 'posted', label: '5. โพสต์แล้ว', color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10', desc: 'คลิปออนไลน์บน TikTok สำเร็จ' },
];

// Memoized Individual Kanban Card for high-speed rendering
const KanbanCard = memo(function KanbanCard({
  ang,
  phaseId,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onCopyCaption,
  copiedAngleId
}) {
  const captionText = `${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`.trim();

  return (
    <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] hover:border-[#25F4EE]/40 transition-all space-y-3 shadow-md">
      {/* Product Title & Badge */}
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-bold text-white truncate flex-1 min-w-0" title={ang.parentProduct?.name}>
          {ang.parentProduct?.name}
        </span>
        {ang.badge && (
          <Badge variant="cyan" size="sm">
            {ang.badge}
          </Badge>
        )}
      </div>

      {/* Hook Title */}
      <div className="p-2 rounded-lg bg-black/50 border-l-4 border-[#25F4EE] text-xs font-bold text-cyan-200 leading-snug">
        {ang.hook_title}
      </div>

      {/* Phase-specific actions */}
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
        <div className="space-y-2">
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
            className="w-full py-1.5 px-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-colors"
          >
            <Check className="w-3 h-3 text-emerald-400" />
            <span>ทำเครื่องหมายว่าตัดเสร็จแล้ว</span>
          </button>
        </div>
      )}

      {phaseId === 'rendered' && (
        <div className="space-y-2">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center text-xs font-bold text-emerald-300">
            วิดีโอเรนเดอร์เสร็จแล้ว
          </div>
          <div className="flex items-center gap-1.5">
            {ang.video_url && (
              <button
                onClick={() => onPreviewVideo(ang.video_url)}
                className="flex-1 py-1.5 px-2 rounded-lg bg-white/[0.05] border border-white/[0.08] text-slate-200 hover:bg-white/[0.1] text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                <span>พรีวิว</span>
              </button>
            )}
            <button
              onClick={() => onOpenQrModal(ang)}
              className="flex-1 py-1.5 px-2 rounded-lg bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] hover:bg-[#25F4EE]/20 text-[11px] font-bold flex items-center justify-center gap-1 cursor-pointer"
            >
              <QrCode className="w-3 h-3" />
              <span>ส่งเข้ามือถือ</span>
            </button>
          </div>
        </div>
      )}

      {phaseId === 'mobile_ready' && (
        <div className="space-y-2">
          <div className="text-[11px] text-slate-400 font-semibold text-center">
            ไฟล์อยู่ในมือถือแล้ว รอเวลาโพสต์
          </div>
          <Button
            onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'posted')}
            variant="neon"
            size="sm"
            className="w-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 shadow-none"
          >
            โพสต์ลง TikTok แล้ว
          </Button>
        </div>
      )}

      {phaseId === 'posted' && (
        <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center text-xs text-emerald-300 font-bold">
          คลิปออนไลน์สำเร็จ
        </div>
      )}

      {/* Caption Copy Helper */}
      {captionText && (phaseId === 'rendered' || phaseId === 'mobile_ready' || phaseId === 'posted') && (
        <button
          onClick={() => onCopyCaption(captionText, ang.angle_id)}
          className="w-full py-1.5 px-2 rounded-lg bg-black/30 hover:bg-black/50 border border-white/[0.05] text-[11px] text-slate-400 hover:text-white flex items-center justify-between cursor-pointer transition-colors"
        >
          <span className="truncate max-w-[170px] font-mono">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
          <span className="text-[#25F4EE] font-bold flex items-center gap-1 flex-shrink-0">
            {copiedAngleId === ang.angle_id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copiedAngleId === ang.angle_id ? 'คัดลอกแล้ว' : 'คัดลอก'}
          </span>
        </button>
      )}
    </div>
  );
});

export default function ContentTrackerHub({ onApplyToStudio, onRefresh, onGoToGallery }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [selectedPhaseFilter, setSelectedPhaseFilter] = useState('all');
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' | 'grouped' | 'table'
  const [copiedAngleId, setCopiedAngleId] = useState(null);
  const [previewVideoUrl, setPreviewVideoUrl] = useState(null);
  const [qrModalItem, setQrModalItem] = useState(null);
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
    } catch (err) {
      alert('ไม่สามารถอัปเดตสถานะได้: ' + err.message);
    }
  }, []);

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
    setTimeout(() => setCopiedAngleId(null), 2000);
  }, []);

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
      const matchesPhase = selectedPhaseFilter === 'all' || a.status === selectedPhaseFilter;
      return matchesSearch && matchesProduct && matchesPhase;
    });
  }, [allAnglesList, debouncedSearch, selectedProductFilter, selectedPhaseFilter]);

  const mobileUrl = typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '';

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
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
              className="w-full rounded-xl bg-black aspect-[9/16] object-contain max-h-[70vh] shadow-2xl border border-white/[0.08]"
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
          1. HEADER & OVERVIEW BAR
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-panel p-5 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-md flex-shrink-0">
              <Layers className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold font-kanit text-white">
              Content Pipeline & Campaign Tracker (แดชบอร์ดติดตามงาน)
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            ระบบติดตามสถานะการผลิตคอนเทนต์ครบ 5 ขั้นตอน (สคริปต์ ➔ ตัดต่อ ➔ เรนเดอร์ ➔ เข้ามือถือ ➔ โพสต์แล้ว)
          </p>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
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

      {/* ══════════════════════════════════════════════════════════
          2. FILTER & SEARCH TOOLBAR
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-card p-4 space-y-3">
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
          </div>
        </div>

        {/* Phase Filter Quick Badges */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          <button
            onClick={() => setSelectedPhaseFilter('all')}
            className={`py-1.5 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap border ${
              selectedPhaseFilter === 'all'
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border-[#25F4EE]/40 shadow-sm'
                : 'bg-white/[0.03] text-slate-400 border-white/[0.06] hover:text-white'
            }`}
          >
            ทั้งหมด ({allAnglesList.length})
          </button>
          {PIPELINE_PHASES.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedPhaseFilter(p.id)}
              className={`py-1.5 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap border ${
                selectedPhaseFilter === p.id
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border-[#25F4EE]/40 shadow-sm'
                  : 'bg-white/[0.03] text-slate-400 border-white/[0.06] hover:text-white'
              }`}
            >
              {p.label} ({phaseCounts[p.id] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          VIEW 1: 5-PHASE KANBAN BOARD
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'kanban' && (
        <div className="w-full overflow-x-auto pb-4 pt-1 no-scrollbar">
          <div className="flex xl:grid xl:grid-cols-5 gap-4 items-start min-w-[1300px] xl:min-w-0">
            {PIPELINE_PHASES.map((phase) => {
              const phaseAngles = filteredAngles.filter(a => a.status === phase.id);

              return (
                <div
                  key={phase.id}
                  className="w-[280px] min-w-[280px] xl:w-auto xl:min-w-0 p-4 border border-white/[0.08] space-y-3.5 rounded-2xl glass-card flex-shrink-0"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.08]">
                    <div className="text-xs sm:text-sm font-bold text-white font-kanit">
                      {phase.label}
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-black/40 border border-white/[0.08] text-slate-400">
                      {phaseAngles.length}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {phaseAngles.length === 0 ? (
                      <div className="py-10 text-center text-xs text-slate-500">
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
    </div>
  );
}
