import React, { useState, useEffect, useRef } from 'react';
import {
  Link2, Sparkles, Clapperboard, Loader2, Check, Copy,
  AlertCircle, ArrowRight, Upload, Trash2, RefreshCw, Plus, Film, Video
} from 'lucide-react';
import {
  scrapeAndPlanProduct, getProducts, updateProduct, updateAngleStatus, deleteProduct, uploadFile
} from '../api';
import { Modal, Toast, Button, Badge, Input, Textarea } from './ui';
import { useToast } from '../hooks';

export default function ProductToClip({ status, videos = [], onRefresh, onApplyToStudio }) {
  // Input Mode & Active View
  const [showAddModal, setShowAddModal] = useState(false);
  const [inputMode, setInputMode] = useState('link'); // 'link' | 'text' | 'image'
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
  const { toastMessage, showToast, hideToast } = useToast();

  // History / All Products
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState(null);

  // Uploading Screenshot/Image
  const [uploadingImg, setUploadingImg] = useState(false);
  const fileInputRef = useRef(null);

  // Load History on Mount
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await getProducts();
      if (res.products) {
        setHistoryList(res.products);
        if (res.products.length > 0) {
          const current = res.products.find(p => p.id === selectedHistoryId) || res.products[0];
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
    loadHistory();
  }, []);

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
        image_path: inputMode === 'image' ? selectedImage : undefined
      };

      const res = await scrapeAndPlanProduct(payload);
      if (res.success && res.product) {
        selectProduct(res.product);
        setShowAddModal(false);
        setUrl('');
        setCustomKeyword('');
        setRawText('');
        await loadHistory();
        showToast('AI วิเคราะห์และสร้าง 4 สคริปต์สำเร็จแล้ว');
      } else {
        throw new Error('ไม่ได้รับข้อมูลสินค้ากลับมาจากระบบ');
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

    onApplyToStudio({
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      hookTitle: angle.hook_title || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: selectedImage || (videos.length > 0 ? videos[0].path : ''),
      fullProduct: {
        id: productData?.id,
        title: productData?.title || customKeyword || 'สินค้า',
        description: productData?.description,
        price_note: productData?.price_note,
        images: productData?.images || [],
        angles: angles && angles.length > 0 ? angles : [angle]
      },
      angleIndex: angleIdx
    });
  };

  const totalAngles = angles.length;
  const postedAngles = angles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
  const progressPercent = totalAngles > 0 ? Math.round((postedAngles / totalAngles) * 100) : 0;

  return (
    <div className="space-y-5 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ══════════════════════════════════════════════════════════
          1. CLEAN UNIFIED HEADER & PRODUCT SWITCHER
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-panel p-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Left: Standard Clean Select Dropdown */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="flex-1 min-w-0">
            <div className="text-[11px] font-semibold text-slate-400">
              เลือกสินค้าในระบบ ({historyList.length} รายการ):
            </div>
            <select
              value={selectedHistoryId || ''}
              onChange={(e) => {
                const found = historyList.find(p => p.id === e.target.value);
                if (found) selectProduct(found);
              }}
              className="w-full mt-0.5 py-1.5 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-xs sm:text-sm font-bold text-white focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer shadow-inner"
            >
              {historyList.map(p => {
                const pAngles = p.angles || [];
                const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
                return (
                  <option key={p.id} value={p.id}>
                    {p.name} — ({pDone}/{pAngles.length || 4} สคริปต์เสร็จ)
                  </option>
                );
              })}
              {historyList.length === 0 && <option value="">ยังไม่มีสินค้า</option>}
            </select>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => setShowAddModal(true)}
            className="py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center gap-2 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4 text-white" />
            <span>วิเคราะห์สินค้าใหม่</span>
          </button>

          <button
            onClick={loadHistory}
            className="p-2.5 min-w-[36px] min-h-[36px] rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white border border-white/[0.08] text-xs font-bold cursor-pointer transition-colors flex items-center justify-center"
            title="รีเฟรช"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {productData && (
            <button
              onClick={() => handleDeleteHistory(productData.id)}
              className="p-2.5 min-w-[36px] min-h-[36px] rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-bold cursor-pointer transition-colors flex items-center justify-center"
              title="ลบสินค้านี้"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          2. ADD PRODUCT MODAL (Central Modal)
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
            <button
              onClick={() => setInputMode('link')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                inputMode === 'link' ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              ลิงก์สินค้า
            </button>
            <button
              onClick={() => setInputMode('text')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                inputMode === 'text' ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              ข้อความสเปก
            </button>
            <button
              onClick={() => setInputMode('image')}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                inputMode === 'image' ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              รูปภาพสินค้า
            </button>
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
              <p className="text-[11px] text-slate-500">
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
                        <div className="text-[11px] text-slate-400 font-mono">{selectedImage.split('\\').pop()?.split('/').pop()}</div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedImage(null);
                          }}
                          className="text-xs text-rose-400 hover:underline"
                        >
                          ลบรูปออก
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-1.5 text-slate-400">
                        <Upload className="w-7 h-7 mx-auto text-slate-500" />
                        <div className="text-xs font-bold text-slate-200">คลิกเพื่อเลือกไฟล์รูปภาพ</div>
                        <div className="text-[10px] text-slate-500">รองรับ JPG, PNG, WebP</div>
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
                    onClick={() => {
                      setInputMode('text');
                      setFetchError(null);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.1] hover:bg-white/[0.15] text-white text-[11px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <span>สลับไปใช้วิธีวางข้อความสเปกแทน</span>
                  </button>
                )}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
              <Button
                variant="secondary"
                onClick={() => setShowAddModal(false)}
              >
                ยกเลิก
              </Button>
              <Button
                variant="primary"
                onClick={handleScrapeAndPlan}
                loading={fetching}
                icon={Sparkles}
              >
                วิเคราะห์ & สร้าง 4 สคริปต์
              </Button>
            </div>
          </div>
        </Modal>

      {/* ══════════════════════════════════════════════════════════
          3. ACTIVE PRODUCT MASTER HERO CARD
         ══════════════════════════════════════════════════════════ */}
      {productData ? (
        <div className="glass-card p-5 sm:p-6 space-y-5">
          {/* Header row */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                <span className="px-2.5 py-0.5 rounded-full bg-[#25F4EE]/15 text-[#25F4EE] text-xs font-bold border border-[#25F4EE]/30">
                  สินค้าปัจจุบัน
                </span>
                {productData.price_note && (
                  <span className="text-xs font-bold font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                    {productData.price_note}
                  </span>
                )}
              </div>
              <h1 className="text-lg sm:text-xl font-bold text-white font-kanit mt-1 truncate max-w-2xl">
                {productData.title}
              </h1>
              {productData.description && (
                <p className="text-xs sm:text-sm text-slate-400 truncate mt-0.5 max-w-2xl">
                  {productData.description}
                </p>
              )}
            </div>

            {/* Progress Badge */}
            <div className="flex items-center gap-3 bg-black/40 p-2.5 px-4 rounded-xl border border-white/[0.08] flex-shrink-0">
              <div className="text-xs">
                <span className="text-slate-400">ความคืบหน้า: </span>
                <span className="text-white font-bold font-mono">{postedAngles}/{totalAngles} คลิป ({progressPercent}%)</span>
              </div>
              <div className="w-20 h-2 bg-slate-800 rounded-full overflow-hidden ml-1">
                <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
          </div>

          {/* Attached Media Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pt-1">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
              <Video className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>คลิปดิบ & รูปภาพที่แนบ ({videos.length + (productData.images?.length || 0)} ไฟล์):</span>
            </div>
            <label className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-[#25F4EE] cursor-pointer flex items-center gap-1.5 transition-all w-fit">
              <Upload className="w-3.5 h-3.5" />
              <span>{uploadingImg ? 'กำลังอัปโหลด...' : 'แนบคลิปดิบเพิ่ม'}</span>
              <input type="file" accept="video/*,image/*" onChange={handleImageUpload} disabled={uploadingImg} className="hidden" />
            </label>
          </div>

          {/* Media Items Scroll */}
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
            {videos.map(v => (
              <div key={v.path} className="flex-shrink-0 flex items-center gap-2 p-2 rounded-xl bg-black/40 border border-white/[0.08] text-xs">
                <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span className="font-bold text-slate-200 truncate max-w-[130px]">{v.name}</span>
                <span className="text-[10px] text-slate-400 font-mono">{v.size_mb} MB</span>
              </div>
            ))}
            {(productData.images || []).map((img, idx) => (
              <div key={idx} className="flex-shrink-0 flex items-center gap-1.5 p-1.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <img src={`/api/media/${img.rel_path || img.local_path}`} alt="" className="w-7 h-7 rounded-lg object-cover" />
                <span className="text-xs text-slate-300 max-w-[100px] truncate">{img.name}</span>
              </div>
            ))}
          </div>

          {/* ══════════════════════════════════════════════════════════
              4. THE 4 SCRIPT ANGLE CARDS (CLEAN 2x2 PRO GRID)
             ══════════════════════════════════════════════════════════ */}
          <div className="pt-3 border-t border-white/[0.08] space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white font-kanit">
                4 สคริปต์ป้ายยา & สถานะการผลิต (4-Angle Hub)
              </h2>
              <span className="text-xs text-slate-400 font-mono">
                เลือกมุมมองที่ชอบ แล้วกด "ส่งตัดต่อใน Studio"
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {angles.map((ang, idx) => {
                const lines = Array.isArray(ang.script_lines) ? ang.script_lines : (ang.script_text ? ang.script_text.split('\n') : []);
                const curStatus = ang.status || 'scripted';

                const isScripted = curStatus === 'scripted';
                const isInProduction = curStatus === 'in_production';
                const isRendered = curStatus === 'rendered';
                const isPosted = curStatus === 'posted';

                return (
                  <div
                    key={ang.angle_id || idx}
                    className="p-5 rounded-2xl glass-card border border-white/[0.08] hover:border-[#25F4EE]/40 transition-all flex flex-col justify-between space-y-3.5 shadow-md"
                  >
                    <div className="space-y-3">
                      {/* Header */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-[#25F4EE] to-blue-500 flex items-center justify-center text-xs font-bold text-slate-950 shadow-sm">
                            {idx + 1}
                          </span>
                          <span className="text-xs sm:text-sm font-bold text-white font-kanit">
                            {ang.angle_name}
                          </span>
                        </div>

                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                          isPosted
                            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            : isRendered
                            ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
                            : isInProduction
                            ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                            : 'bg-white/[0.05] text-slate-400 border-white/[0.08]'
                        }`}>
                          {isPosted ? 'โพสต์แล้ว' : isRendered ? 'เรนเดอร์เสร็จ' : isInProduction ? 'กำลังตัดต่อ' : 'สคริปต์พร้อม'}
                        </span>
                      </div>

                      {/* Hook 3s Highlight Banner */}
                      {ang.hook_title && (
                        <div className="p-3 rounded-xl bg-black/50 border-l-4 border-[#25F4EE] text-xs sm:text-sm font-bold text-cyan-200 leading-snug">
                          {ang.hook_title}
                        </div>
                      )}

                      {/* Script Lines */}
                      <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold">
                          <span>บทพูดพากย์ ({lines.length} ท่อน):</span>
                          <button
                            onClick={() => copyScriptText(lines.join('\n'), idx)}
                            className="text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer font-bold"
                          >
                            {copiedIndex === idx ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedIndex === idx ? 'คัดลอกแล้ว' : 'คัดลอก'}</span>
                          </button>
                        </div>
                        <div className="space-y-1 text-xs text-slate-200 font-mono leading-relaxed max-h-32 overflow-y-auto no-scrollbar">
                          {lines.map((line, lIdx) => (
                            <div key={lIdx} className="flex items-start gap-1.5">
                              <span className="text-[#25F4EE] font-bold flex-shrink-0">{lIdx + 1}.</span>
                              <span>{line}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Action Footer */}
                    <div className="pt-2.5 border-t border-white/[0.08] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
                      {/* Step Switcher Buttons */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleAngleStatusChange(ang.angle_id, 'scripted')}
                          className={`flex-1 sm:flex-none px-2.5 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all ${
                            isScripted ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40' : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:text-white'
                          }`}
                        >
                          1. สคริปต์
                        </button>
                        <button
                          onClick={() => handleAngleStatusChange(ang.angle_id, 'in_production')}
                          className={`flex-1 sm:flex-none px-2.5 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all ${
                            isInProduction ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:text-white'
                          }`}
                        >
                          2. ตัดต่อ
                        </button>
                        <button
                          onClick={() => handleAngleStatusChange(ang.angle_id, 'rendered')}
                          className={`flex-1 sm:flex-none px-2.5 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all ${
                            isRendered ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:text-white'
                          }`}
                        >
                          3. เรนเดอร์
                        </button>
                      </div>

                      {/* Send to Studio Button */}
                      <button
                        onClick={() => handleSendToStudio(ang, idx)}
                        className="w-full sm:w-auto py-2 px-3.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
                      >
                        <Clapperboard className="w-3.5 h-3.5 text-white" />
                        <span>ส่งตัดต่อใน Studio</span>
                        <ArrowRight className="w-3 h-3 text-white/80" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="p-16 text-center space-y-4 rounded-2xl glass-card shadow-2xl">
          <div>
            <h3 className="text-lg font-bold text-white font-kanit">ยังไม่มีสินค้าในระบบ</h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-md mx-auto">
              กดปุ่ม "วิเคราะห์สินค้าใหม่" ด้านบนเพื่อวางลิงก์ Shopee หรือพิมพ์รายละเอียด AI จะสร้าง 4 สคริปต์ให้ทันที
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
