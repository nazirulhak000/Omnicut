import React, { useState, useEffect, useRef } from 'react';
import {
  Link2, Sparkles, Clapperboard, Loader2, Check, Copy,
  AlertCircle, ArrowRight, Upload, Trash2, RefreshCw, Plus, Film, Video,
  ChevronDown, ChevronRight, Package, Rocket
} from 'lucide-react';
import {
  scrapeAndPlanProduct, scrapeAndPlanProductAsync, getProducts, updateProduct, updateAngleStatus, deleteProduct, uploadFile
} from '../api';
import { Modal, Toast, Button, Badge, Input, Textarea } from './ui';
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
  angle, index, isOpen, onToggle, onCopy, onSendToStudio, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false
}) {
  const lines = Array.isArray(angle.script_lines)
    ? angle.script_lines
    : (angle.script_text ? angle.script_text.split('\n') : []);

  const curStatus = angle.status || 'scripted';
  const statusLabel = curStatus === 'posted' ? 'โพสต์แล้ว'
    : curStatus === 'rendered' ? 'ตัดเสร็จ'
    : curStatus === 'in_production' ? 'กำลังตัดต่อ'
    : 'สคริปต์พร้อม';

  const statusColor = curStatus === 'posted' ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : curStatus === 'rendered' ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
    : curStatus === 'in_production' ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
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
              <span className="text-[11px] font-mono text-slate-500">
                {selectedVideos.length > 0
                  ? `เลือกแล้ว ${selectedVideos.length} คลิป`
                  : 'ใช้คลิปทั้งหมดในระบบ'}
              </span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
              {videos.map(v => {
                const isChosen = selectedVideos.includes(v.path) || selectedVideos.includes(v.rel_path);
                return (
                  <button
                    key={v.path}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleVideoForAngle && onToggleVideoForAngle(index, v.path || v.rel_path);
                    }}
                    className={`flex-shrink-0 flex items-center gap-1.5 py-1.5 px-2.5 rounded-lg border text-xs font-bold transition-all cursor-pointer ${
                      isChosen
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE] shadow-sm shadow-[#25F4EE]/20'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-slate-200'
                    }`}
                    title={isChosen ? 'คลิกเพื่อยกเลิกคลิปนี้' : 'คลิกเพื่อเลือกใช้คลิปนี้กับมุมนี้'}
                  >
                    <Film className={`w-3.5 h-3.5 ${isChosen ? 'text-[#25F4EE]' : 'text-slate-500'}`} />
                    <span className="truncate max-w-[130px]">{v.name}</span>
                    {v.size_mb && <span className="text-[10px] font-mono opacity-60">({v.size_mb}MB)</span>}
                    {isChosen && <Check className="w-3 h-3 text-[#25F4EE] ml-0.5" />}
                  </button>
                );
              })}

              {/* Inline Upload Footage Button */}
              <label
                onClick={(e) => e.stopPropagation()}
                className="flex-shrink-0 flex items-center gap-1.5 py-1.5 px-2.5 rounded-lg border border-dashed border-white/[0.15] hover:border-[#25F4EE]/50 hover:bg-[#25F4EE]/5 text-xs font-bold text-slate-400 hover:text-[#25F4EE] transition-all cursor-pointer"
                title="อัปโหลดไฟล์วิดีโอดิบใหม่เข้าสู่ระบบ"
              >
                <Plus className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>{uploadingImg ? 'กำลังอัปโหลด...' : '+ แนบคลิปเพิ่ม'}</span>
                <input
                  type="file"
                  accept="video/*,image/*"
                  onChange={onUploadVideo}
                  disabled={uploadingImg}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <button
              onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
              className="py-2 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
            >
              <Clapperboard className="w-3.5 h-3.5 text-white" />
              <span>เลือกมุมนี้ & ส่งตัดต่อ</span>
              <ArrowRight className="w-3 h-3 text-white/80" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 🌟 MAIN: ProductToClip Component (Redesigned Guided Workflow)
// ═══════════════════════════════════════════════════════════════════════
export default function ProductToClip({ status, videos = [], onRefresh, onApplyToStudio, selectedProductId }) {
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
  const { toastMessage, showToast, hideToast } = useToast();
  const { refreshTrigger, toggleActivityDrawer } = useTaskManager();

  // History / All Products
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState(selectedProductId || null);

  // Angle Count Selection
  const [angleCount, setAngleCount] = useState(7); // Default: 7 (Sweet Spot)

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
      description: item.selling_points?.join(', ') || item.price_note || '',
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
      alert('ไม่สามารถอัปเดตสถานะได้: ' + err.message);
    }
  };

  const handleDeleteHistory = async (id) => {
    if (!confirm('คุณต้องการลบสินค้านี้และสคริปต์ทั้งหมดออกจากระบบใช่หรือไม่?')) return;
    try {
      await deleteProduct(id);
      showToast('ลบสินค้าเรียบร้อยแล้ว');
      const res = await getProducts();
      const updated = res.products || [];
      setHistoryList(updated);
      if (updated.length > 0) selectProduct(updated[0]);
      else {
        setProductData(null);
        setAngles([]);
      }
    } catch (err) {
      alert('ลบไม่สำเร็จ: ' + err.message);
    }
  };

  const handleScrapeAndPlan = async () => {
    if (inputMode === 'link' && !url.trim()) {
      alert('กรุณากรอกลิงก์สินค้าก่อนครับ');
      return;
    }
    if (inputMode === 'text' && !customKeyword.trim() && !rawText.trim()) {
      alert('กรุณาระบุชื่อสินค้าหรือสเปกก่อนครับ');
      return;
    }
    if (inputMode === 'image' && !selectedImage && !customKeyword.trim()) {
      alert('กรุณาอัปโหลดรูปภาพหรือระบุชื่อสินค้าก่อนครับ');
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

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImg(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_dir', 'inbox');
    try {
      const res = await uploadFile(formData);
      if (res.file) {
        setSelectedImage(res.file.path);
        showToast('อัปโหลดไฟล์เรียบร้อยแล้ว');
      }
    } catch (err) {
      alert('อัปโหลดไม่สำเร็จ: ' + (err.friendlyMessage || err.message));
    } finally {
      setUploadingImg(false);
    }
  };

  const handleToggleVideoForAngle = (angleIdx, videoPath) => {
    setAngles(prev => {
      const next = [...prev];
      const ang = { ...next[angleIdx] };
      const currentVideos = ang.selected_videos || (ang.selected_video ? [ang.selected_video] : []);
      if (currentVideos.includes(videoPath)) {
        ang.selected_videos = currentVideos.filter(p => p !== videoPath);
      } else {
        ang.selected_videos = [...currentVideos, videoPath];
      }
      ang.selected_video = ang.selected_videos[0] || null;
      next[angleIdx] = ang;
      return next;
    });
    showToast('อัปเดตการเลือกคลิปสำหรับมุมนี้เรียบร้อยแล้ว');
  };

  const copyScriptText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    showToast('คัดลอกสคริปต์เรียบร้อยแล้ว');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSendToStudio = (angle, angleIdx = 0) => {
    if (!onApplyToStudio) return;

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');

    const chosenVideos = angle.selected_videos && angle.selected_videos.length > 0
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : (videos.length > 0 ? [videos[0].path] : []));
    const primaryVideo = chosenVideos[0] || selectedImage || (videos.length > 0 ? videos[0].path : '');

    onApplyToStudio({
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      hookTitle: angle.hook_title || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
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
      angleIndex: angleIdx
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
          STEP 1: PRODUCT CARD GALLERY (Horizontal Scroll Strip)
         ══════════════════════════════════════════════════════════ */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Package className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>Step 1 — เลือกสินค้า</span>
            {historyList.length > 0 && (
              <span className="text-sm font-mono text-slate-500 ml-1">({historyList.length} รายการ)</span>
            )}
          </h2>
          <div className="flex items-center gap-1.5">
            <button
              onClick={loadHistory}
              className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/[0.06] cursor-pointer transition-colors"
              title="รีเฟรช"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
            </button>
            {productData && (
              <button
                onClick={() => handleDeleteHistory(productData.id)}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 cursor-pointer transition-colors"
                title="ลบสินค้านี้"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Horizontal Scrollable Product Cards */}
        <div className="flex items-stretch gap-2.5 overflow-x-auto pb-1 no-scrollbar snap-x snap-mandatory scroll-smooth pr-4">
          {historyList.map(p => (
            <ProductCard
              key={p.id}
              product={p}
              isSelected={selectedHistoryId === p.id}
              onSelect={selectProduct}
            />
          ))}

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
                label="ลิงก์สินค้า (Shopee / TikTok Shop):"
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
                label="ชื่อสินค้า หรือหมวดหมู่:"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น สายชาร์จแม่เหล็ก 3-in-1 หรือ เซรั่มหน้าใส"
              />
              <Textarea
                label="รายละเอียดสินค้า / สเปก / จุดขาย / ราคา:"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={5}
                placeholder="ก๊อปปี้รายละเอียดสินค้าจาก Shopee / TikTok Shop มาวางที่นี่ได้เลย..."
              />
            </div>
          )}

          {/* Mode 3: Image / Screenshot */}
          {inputMode === 'image' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ชื่อสินค้า (สำหรับระบุในสคริปต์):"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น Esseger สายชาร์จแม่เหล็ก"
              />
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  แคปหน้าจอหน้าร้าน / รูปสินค้า:
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-white/[0.15] hover:border-[#25F4EE]/50 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-black/30"
                >
                  {uploadingImg ? (
                    <div className="flex flex-col items-center gap-2 text-[#25F4EE]">
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span className="text-xs font-bold">กำลังอัปโหลดรูปภาพ...</span>
                    </div>
                  ) : selectedImage ? (
                    <div className="space-y-2">
                      <div className="text-xs font-bold text-emerald-400">เลือกรูปแล้ว:</div>
                      <div className="text-sm text-slate-400 font-mono">{selectedImage.split('\\').pop()?.split('/').pop()}</div>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setSelectedImage(null); }}
                        className="text-xs text-rose-400 hover:underline"
                      >
                        ลบรูปออก
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-slate-400">
                      <Upload className="w-7 h-7 mx-auto text-slate-500" />
                      <div className="text-xs font-bold text-slate-200">คลิกเพื่อเลือกไฟล์รูปภาพ</div>
                      <div className="text-sm text-slate-500">รองรับ JPG, PNG, WebP</div>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
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
              {productData.description && (
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
              <label className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-[#25F4EE] cursor-pointer flex items-center gap-1 transition-all">
                <Upload className="w-3 h-3" />
                <span>{uploadingImg ? 'อัปโหลด...' : '+ แนบคลิปเข้าคลัง'}</span>
                <input type="file" accept="video/*,image/*" onChange={handleImageUpload} disabled={uploadingImg} className="hidden" />
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
                  copiedIndex={copiedIndex}
                  videos={videos}
                  onToggleVideoForAngle={handleToggleVideoForAngle}
                  onUploadVideo={handleImageUpload}
                  uploadingImg={uploadingImg}
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
    </div>
  );
}
