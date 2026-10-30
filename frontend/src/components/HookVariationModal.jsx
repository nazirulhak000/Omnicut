import React, { useState, useEffect } from 'react';
import { Sparkles, Check, Copy, RefreshCw, Volume2, AlertCircle, Eye } from 'lucide-react';
import { Modal, Badge } from './ui';
import { generateHookVariations, applyAngleHook } from '../api';

const STYLE_COLORS = {
  curiosity: 'text-amber-300 border-amber-500/30 bg-amber-500/10',
  warning: 'text-red-300 border-red-500/30 bg-red-500/10',
  social_proof: 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10',
  deal_promo: 'text-cyan-300 border-cyan-500/30 bg-cyan-500/10',
  pain_point: 'text-purple-300 border-purple-500/30 bg-purple-500/10',
};

export default function HookVariationModal({
  isOpen,
  onClose,
  product,
  angle,
  onHookApplied,
  showToast,
}) {
  const [variations, setVariations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [updateFirstLine, setUpdateFirstLine] = useState(true);
  const [applying, setApplying] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);

  const loadVariations = async () => {
    if (!product && !angle) return;
    setLoading(true);
    try {
      const pName = angle?.product_name || product?.title || product?.name || 'สินค้า';
      const pBrand = angle?.hook_brand || '';
      const pModel = angle?.hook_model || '';
      const pDesc = product?.description || angle?.key_features || '';
      const pPain = angle?.pain_point || '';

      const res = await generateHookVariations({
        product_name: pName,
        brand: pBrand,
        model: pModel,
        description: pDesc,
        pain_point: pPain,
        angle_name: angle?.angle_name || '',
      });

      if (res?.variations?.length) {
        setVariations(res.variations);
        setSelectedIdx(0);
      }
    } catch (err) {
      showToast?.(err.response?.data?.detail || err.message || 'สร้าง Hook ไม่สำเร็จ', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadVariations();
    } else {
      setVariations([]);
      setSelectedIdx(0);
    }
  }, [isOpen, angle?.angle_id]);

  const handleApply = async (variant) => {
    if (!variant) return;
    setApplying(true);
    try {
      if (product?.id && angle?.angle_id) {
        const res = await applyAngleHook({
          product_id: String(product.id),
          angle_id: String(angle.angle_id),
          hook_variant: variant,
          update_script_first_line: updateFirstLine,
        });
        showToast?.('ใช้ Hook ใหม่กับสคริปต์นี้เรียบร้อยแล้ว');
        onHookApplied?.(res.angle || variant);
      } else {
        // Direct local callback if standalone
        onHookApplied?.(variant);
        showToast?.('ปรับใช้ Hook เรียบร้อยแล้ว');
      }
      onClose();
    } catch (err) {
      showToast?.(err.response?.data?.detail || err.message || 'ปรับใช้ Hook ไม่สำเร็จ', 'error');
    } finally {
      setApplying(false);
    }
  };

  const handleCopy = (variant, index) => {
    const textToCopy = `พาดหัว: ${variant.hook_title}\nป้ายแบนเนอร์: ${variant.hook_brand} | ${variant.hook_model} | ${variant.hook_label}\nประโยคเปิด: ${variant.opening_line}`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedIdx(index);
    setTimeout(() => setCopiedIdx(null), 2000);
    showToast?.('คัดลอกข้อความ Hook แล้ว');
  };

  const selectedVariant = variations[selectedIdx] || variations[0];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Hook Variation & A/B Generator"
      subtitle="สร้างประโยคเปิดคลิปและป้ายพาดหัว 5 สไตล์การตลาด เพื่อทดสอบ A/B และเพิ่มยอดคลิกดูจนจบ"
      maxWidth="max-w-4xl"
    >
      <div className="space-y-4">
        {/* Top Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-300">สินค้า:</span>
            <span className="text-xs font-black text-cyan-200 truncate max-w-xs">
              {angle?.product_name || product?.title || 'สินค้า'}
            </span>
            {angle?.angle_name && (
              <span className="text-[11px] text-slate-400 bg-white/[0.06] px-2 py-0.5 rounded-md">
                {angle.angle_name}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={updateFirstLine}
                onChange={(e) => setUpdateFirstLine(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-black/40 text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
              />
              <span className="text-xs text-slate-300 font-medium">อัปเดตประโยคแรกในสคริปต์ด้วย</span>
            </label>

            <button
              type="button"
              disabled={loading}
              onClick={loadVariations}
              className="px-3 py-1.5 rounded-xl border border-cyan-400/30 bg-cyan-400/[0.08] hover:bg-cyan-400/[0.15] text-cyan-300 text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              สร้างใหม่
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-8 h-8 mx-auto rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
            <p className="text-sm font-bold text-slate-300">กำลังคิด Hook โดนๆ 5 สไตล์...</p>
            <p className="text-xs text-slate-500">วิเคราะห์ตามจิตวิทยาหยุดสายตาคนดู 3 วินาทีแรก</p>
          </div>
        ) : variations.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            ไม่พบข้อมูล Hook กรุณากดปุ่มสร้างใหม่
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left: 5 Variant Cards (7 cols) */}
            <div className="lg:col-span-7 space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
              {variations.map((item, idx) => {
                const isSelected = idx === selectedIdx;
                const styleClass = STYLE_COLORS[item.style_id] || STYLE_COLORS.curiosity;

                return (
                  <div
                    key={item.style_id || idx}
                    onClick={() => setSelectedIdx(idx)}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer text-left ${
                      isSelected
                        ? 'border-cyan-400/60 bg-cyan-500/[0.08] shadow-[0_0_20px_rgba(37,244,238,0.08)]'
                        : 'border-white/[0.08] bg-black/25 hover:border-white/[0.2] hover:bg-white/[0.02]'
                    }`}
                  >
                    {/* Header: Style + Tag + Actions */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-lg border text-[10px] font-black ${styleClass}`}>
                          {item.style_name}
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold bg-white/[0.05] px-2 py-0.5 rounded-md">
                          {item.tag}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => handleCopy(item, idx)}
                          className="p-1 rounded-lg border border-white/[0.1] text-slate-400 hover:text-white"
                          title="คัดลอกข้อความ"
                          aria-label="คัดลอกข้อความ"
                        >
                          {copiedIdx === idx ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          type="button"
                          disabled={applying}
                          onClick={() => handleApply(item)}
                          className="px-2.5 py-1 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 text-[11px] font-black flex items-center gap-1 transition-colors"
                        >
                          <Check className="w-3 h-3" />
                          ใช้ Hook นี้
                        </button>
                      </div>
                    </div>

                    {/* Hook Title */}
                    <h4 className="text-xs sm:text-sm font-black text-white leading-snug mb-2">
                      {item.hook_title}
                    </h4>

                    {/* Opening Voice Line */}
                    {item.opening_line && (
                      <div className="flex items-start gap-1.5 text-[11px] text-slate-300 bg-black/40 rounded-xl p-2 border border-white/[0.05]">
                        <Volume2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                        <span className="line-clamp-2 leading-relaxed">
                          "{item.opening_line}"
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Right: Live 9:16 Mock Preview (5 cols) */}
            <div className="lg:col-span-5 flex flex-col items-center justify-center p-4 rounded-2xl border border-white/[0.08] bg-black/40">
              <div className="w-full flex items-center justify-between mb-3 px-1">
                <span className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-cyan-400" />
                  จำลองบนหน้าจอ 9:16
                </span>
                <span className="text-[10px] text-slate-500">Safe Zone บน-ล่าง</span>
              </div>

              {/* 9:16 Frame */}
              <div className="relative w-[210px] h-[373px] rounded-2xl border-2 border-white/20 bg-slate-950 overflow-hidden shadow-2xl flex flex-col justify-between p-3 select-none">
                {/* Safe Zone Header Guide */}
                <div className="text-[8px] text-slate-600 text-center border-b border-dashed border-white/10 pb-1">
                  TikTok Safe Zone
                </div>

                {/* Top Hook Banner Mock */}
                <div className="space-y-1.5 mt-2">
                  <div className="p-2.5 rounded-xl bg-gradient-to-b from-slate-900/90 to-slate-900/70 border border-cyan-400/40 backdrop-blur-md shadow-lg text-center">
                    {/* Tier 1: Brand */}
                    {selectedVariant?.hook_brand && (
                      <div className="text-[8px] font-black uppercase tracking-widest text-cyan-300 truncate">
                        {selectedVariant.hook_brand}
                      </div>
                    )}
                    {/* Tier 2: Model */}
                    {selectedVariant?.hook_model && (
                      <div className="text-[10px] font-black text-white truncate">
                        {selectedVariant.hook_model}
                      </div>
                    )}
                    {/* Tier 3: Label */}
                    {selectedVariant?.hook_label && (
                      <div className="mt-1 px-2 py-0.5 rounded-full bg-cyan-400 text-slate-950 text-[8px] font-black inline-block max-w-full truncate">
                        {selectedVariant.hook_label}
                      </div>
                    )}
                  </div>
                </div>

                {/* Center Content Placeholder */}
                <div className="flex-1 flex items-center justify-center text-slate-700 text-[10px] font-bold">
                  วิดีโอสินค้า (9:16)
                </div>

                {/* Spoken subtitle preview at bottom */}
                <div className="space-y-2 mb-2">
                  <div className="bg-black/80 rounded-lg p-1.5 border border-white/10 text-center">
                    <p className="text-[8px] text-amber-300 font-bold leading-tight line-clamp-2">
                      {selectedVariant?.opening_line || selectedVariant?.hook_title}
                    </p>
                  </div>
                  <div className="text-[7px] text-slate-600 text-center border-t border-dashed border-white/10 pt-1">
                    Bottom Safe Zone (420px)
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 text-center mt-3 leading-relaxed">
                คลิกเลือก Hook ที่ชอบ แล้วกด <strong>ใช้ Hook นี้</strong> เพื่ออัปเดตสคริปต์และป้ายแบนเนอร์ทันที
              </p>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
