import React, { useState, useEffect, useMemo } from 'react';
import { Sparkles, Check, Copy, RefreshCw, Volume2, AlertCircle, Eye, Tag } from 'lucide-react';
import { Modal, Badge } from './ui';
import { generateHookVariations, applyAngleHook } from '../api';
import { guessBrandModel } from '../lib/overlayModel';

const STYLE_COLORS = {
  curiosity: 'text-amber-300 border-amber-500/30 bg-amber-500/10',
  warning: 'text-rose-300 border-rose-500/30 bg-rose-500/10',
  social_proof: 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10',
  deal_promo: 'text-cyan-300 border-cyan-500/30 bg-cyan-500/10',
  pain_point: 'text-purple-300 border-purple-500/30 bg-purple-500/10',
};

export default function HookVariationModal({
  isOpen,
  onClose,
  product,
  angle,
  angles = [],
  currentAngleIndex = 0,
  onHookApplied,
  onSaveHookHeader,
  initialTab = 'variations',
  showToast,
}) {
  const [activeTab, setActiveTab] = useState(initialTab || 'variations');
  const [variations, setVariations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [updateFirstLine, setUpdateFirstLine] = useState(true);
  const [applying, setApplying] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);

  // Hook Header Overlay State
  const currentAngle = angle || (angles && angles[currentAngleIndex]) || {};
  const guessed = useMemo(() => {
    return guessBrandModel(currentAngle.product_name || product?.name || product?.title || '');
  }, [currentAngle.product_name, product?.name, product?.title]);

  const [brand, setBrand] = useState('');
  const [model, setModel] = useState('');
  const [label, setLabel] = useState('');
  const [scope, setScope] = useState('all');
  const [syncScriptText, setSyncScriptText] = useState(false);
  const [savingHeader, setSavingHeader] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab(initialTab || 'variations');
    const initialBrand = currentAngle.hook_brand ?? product?.hook_brand ?? guessed.brand ?? '';
    const initialModel = currentAngle.hook_model ?? product?.hook_model ?? guessed.model ?? '';
    const initialLabel = currentAngle.hook_label ?? product?.hook_label ?? '';

    setBrand(initialBrand);
    setModel(initialModel);
    setLabel(initialLabel);
    setScope('all');
    setSyncScriptText(false);
  }, [isOpen, initialTab, currentAngle, product, guessed]);

  const handleResetToGuessed = () => {
    setBrand(guessed.brand || '');
    setModel(guessed.model || '');
  };

  const handleSaveHeader = async () => {
    if (savingHeader) return;
    setSavingHeader(true);
    try {
      if (onSaveHookHeader) {
        await onSaveHookHeader({
          hookBrand: brand.trim(),
          hookModel: model.trim(),
          hookLabel: label.trim(),
          scope,
          syncScriptText,
          angleIndex: currentAngleIndex,
        });
      }
      showToast?.('บันทึกป้ายพาดหัวเรียบร้อยแล้ว');
      onClose();
    } catch (err) {
      console.error('Failed to save hook header:', err);
      showToast?.(err.response?.data?.detail || err.message || 'บันทึกไม่สำเร็จ', 'error');
    } finally {
      setSavingHeader(false);
    }
  };

  const loadVariations = async () => {
    if (!product && !currentAngle) return;
    setLoading(true);
    try {
      const pName = currentAngle?.product_name || product?.title || product?.name || 'สินค้า';
      const pBrand = currentAngle?.hook_brand || brand || '';
      const pModel = currentAngle?.hook_model || model || '';
      const pDesc = product?.description || currentAngle?.key_features || '';
      const pPain = currentAngle?.pain_point || '';

      const res = await generateHookVariations({
        product_name: pName,
        brand: pBrand,
        model: pModel,
        description: pDesc,
        pain_point: pPain,
        angle_name: currentAngle?.angle_name || '',
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
    if (isOpen && activeTab === 'variations' && variations.length === 0) {
      loadVariations();
    }
  }, [isOpen, activeTab, currentAngle?.angle_id]);

  const handleApply = async (variant) => {
    if (!variant) return;
    setApplying(true);
    try {
      if (product?.id && currentAngle?.angle_id) {
        const res = await applyAngleHook({
          product_id: String(product.id),
          angle_id: String(currentAngle.angle_id),
          hook_variant: variant,
          update_script_first_line: updateFirstLine,
        });
        showToast?.('ใช้ Hook ใหม่กับสคริปต์นี้เรียบร้อยแล้ว');
        onHookApplied?.(res.angle || variant);
      } else {
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
      title="Hook & Header Studio"
      subtitle="ปรับแต่งคำพาดหัวและป้ายแบนเนอร์ 3-5 วินาทีแรกของวิดีโอ 9:16 แบบรวมศูนย์"
      maxWidth="max-w-4xl"
    >
      <div className="space-y-3.5">
        {/* Unified Tab Switcher (Consolidated Modals) */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/40 border border-white/[0.08]">
          <button
            type="button"
            onClick={() => setActiveTab('variations')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === 'variations'
                ? 'bg-[#25F4EE] text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>ตัวเลือก Hook AI (5 สไตล์)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('header')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeTab === 'header'
                ? 'bg-[#25F4EE] text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Tag className="w-3.5 h-3.5" />
            <span>พาดหัวปก & แบรนด์ (Header Overlay)</span>
          </button>
        </div>

        {activeTab === 'variations' ? (
          <div className="space-y-3.5">
            {/* Top Controls */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-2xl bg-[#0D111A] border border-white/[0.08]">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-bold text-slate-300">สินค้า:</span>
                <span className="text-xs font-black text-[#25F4EE] truncate max-w-xs">
                  {currentAngle?.product_name || product?.title || 'สินค้า'}
                </span>
                {currentAngle?.angle_name && (
                  <span className="text-[11px] text-slate-400 bg-white/[0.06] px-2 py-0.5 rounded-md border border-white/[0.06] truncate">
                    {currentAngle.angle_name}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3 flex-shrink-0">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={updateFirstLine}
                    onChange={(e) => setUpdateFirstLine(e.target.checked)}
                    className="w-4 h-4 rounded border-white/[0.1] bg-black/40 text-[#25F4EE] accent-[#25F4EE] focus:ring-0 focus:ring-offset-0 cursor-pointer"
                  />
                  <span className="text-xs text-slate-300 font-medium">อัปเดตประโยคแรกในสคริปต์ด้วย</span>
                </label>

                <button
                  type="button"
                  disabled={loading}
                  onClick={loadVariations}
                  className="px-3 py-1.5 rounded-xl border border-[#25F4EE]/30 bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 text-[#25F4EE] text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  สร้างใหม่
                </button>
              </div>
            </div>

            {loading ? (
              <div className="py-16 text-center space-y-3">
                <div className="w-8 h-8 mx-auto rounded-full border-2 border-[#25F4EE] border-t-transparent animate-spin" />
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
                <div className="lg:col-span-7 space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
                  {variations.map((item, idx) => {
                    const isSelected = idx === selectedIdx;
                    const styleClass = STYLE_COLORS[item.style_id] || STYLE_COLORS.curiosity;

                    return (
                      <div
                        key={item.style_id || idx}
                        onClick={() => setSelectedIdx(idx)}
                        className={`p-3.5 rounded-2xl border transition-all cursor-pointer text-left ${
                          isSelected
                            ? 'border-[#25F4EE]/50 bg-[#25F4EE]/[0.06]'
                            : 'border-white/[0.08] bg-[#0D111A] hover:border-white/[0.15] hover:bg-white/[0.02]'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded-lg border text-[10px] font-black ${styleClass}`}>
                              {item.style_name}
                            </span>
                            <span className="text-[10px] text-slate-400 font-bold bg-white/[0.05] px-2 py-0.5 rounded-md border border-white/[0.06]">
                              {item.tag}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              onClick={() => handleCopy(item, idx)}
                              className="p-1 rounded-lg border border-white/[0.08] bg-white/[0.02] text-slate-400 hover:text-white hover:border-white/[0.15] transition-colors cursor-pointer"
                              title="คัดลอกข้อความ"
                              aria-label="คัดลอกข้อความ"
                            >
                              {copiedIdx === idx ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              type="button"
                              disabled={applying}
                              onClick={() => handleApply(item)}
                              className="px-2.5 py-1 rounded-lg bg-[#25F4EE] hover:bg-[#20ded8] text-slate-950 text-[11px] font-black flex items-center gap-1 transition-colors cursor-pointer disabled:opacity-50"
                            >
                              <Check className="w-3 h-3" />
                              ใช้ Hook นี้
                            </button>
                          </div>
                        </div>

                        <h4 className="text-xs sm:text-sm font-black text-white leading-snug mb-2">
                          {item.hook_title}
                        </h4>

                        {item.opening_line && (
                          <div className="flex items-start gap-1.5 text-[11px] text-slate-300 bg-black/40 rounded-xl p-2 border border-white/[0.08]">
                            <Volume2 className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0 mt-0.5" />
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
                <div className="lg:col-span-5 flex flex-col items-center justify-center p-4 rounded-2xl border border-white/[0.08] bg-[#0D111A]">
                  <div className="w-full flex items-center justify-between mb-2 px-1">
                    <span className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                      <Eye className="w-3.5 h-3.5 text-[#25F4EE]" />
                      จำลองบนหน้าจอ 9:16
                    </span>
                    <span className="text-[10px] text-slate-500">Safe Zone บน-ล่าง</span>
                  </div>

                  <div className="relative w-[190px] h-[338px] rounded-2xl border border-white/[0.15] bg-[#0A0D14] overflow-hidden flex flex-col justify-between p-3 select-none">
                    <div className="text-[8px] text-slate-600 text-center border-b border-dashed border-white/10 pb-1">
                      TikTok Safe Zone
                    </div>

                    <div className="space-y-1.5 mt-2">
                      <div className="p-2.5 rounded-xl bg-[#0D111A]/95 border border-[#25F4EE]/40 backdrop-blur-md text-center">
                        {selectedVariant?.hook_brand && (
                          <div className="text-[8px] font-black uppercase tracking-widest text-[#25F4EE] truncate">
                            {selectedVariant.hook_brand}
                          </div>
                        )}
                        {selectedVariant?.hook_model && (
                          <div className="text-[10px] font-black text-white truncate">
                            {selectedVariant.hook_model}
                          </div>
                        )}
                        {selectedVariant?.hook_label && (
                          <div className="mt-1 px-2 py-0.5 rounded-full bg-[#25F4EE] text-slate-950 text-[8px] font-black inline-block max-w-full truncate">
                            {selectedVariant.hook_label}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex-1 flex items-center justify-center text-slate-700 text-[10px] font-bold">
                      วิดีโอสินค้า (9:16)
                    </div>

                    <div className="space-y-2 mb-2">
                      <div className="bg-black/80 rounded-lg p-1.5 border border-white/[0.08] text-center">
                        <p className="text-[8px] text-amber-300 font-bold leading-tight line-clamp-2">
                          {selectedVariant?.opening_line || selectedVariant?.hook_title}
                        </p>
                      </div>
                      <div className="text-[7px] text-slate-600 text-center border-t border-dashed border-white/10 pt-1">
                        Bottom Safe Zone (420px)
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Tab 2: Header Overlay Setting (Brand / Model / Label) */
          <div className="space-y-4 pt-1">
            {/* Live Visual Preview of Hook Banner */}
            <div className="p-3.5 rounded-2xl bg-black/60 border border-white/[0.1] shadow-inner space-y-2">
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold">
                <span>ตัวอย่างป้ายบนวิดีโอจริง (9:16):</span>
                <button
                  type="button"
                  onClick={handleResetToGuessed}
                  className="text-cyan-400 hover:text-cyan-300 text-[11px] flex items-center gap-1 cursor-pointer"
                  title="ดึงชื่อแบรนด์และรุ่นจากชื่อสินค้าอัตโนมัติ"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>รีเซ็ตตามชื่อสินค้า</span>
                </button>
              </div>

              <div className="relative mx-auto max-w-[280px] p-3 rounded-xl bg-gradient-to-b from-black/80 to-slate-950 border border-white/[0.12] text-center shadow-lg">
                <div className="text-[10px] text-[#25F4EE] font-bold tracking-widest uppercase">
                  {brand.trim() || 'ชื่อแบรนด์'}
                </div>
                <div className="text-sm font-black text-white tracking-tight drop-shadow-md truncate">
                  {model.trim() || 'ชื่อรุ่น / โมเดล'}
                </div>
                {label.trim() && (
                  <div className="inline-block mt-1 px-2 py-0.5 rounded-full bg-white/[0.08] border border-white/[0.1] text-[9px] font-medium text-slate-300">
                    {label.trim()}
                  </div>
                )}
              </div>
            </div>

            {/* Form Inputs */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Header: แบรนด์ (Brand)
                </label>
                <input
                  type="text"
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  placeholder="เช่น Logitech, BCD, Esseger"
                  className="w-full rounded-xl border border-white/[0.1] bg-black/40 px-3.5 py-2 text-xs sm:text-sm text-white focus:border-[#25F4EE] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Header: รุ่น / โมเดล (Model)
                </label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="เช่น Lift, LOOP Smartband, 100W Magnetic"
                  className="w-full rounded-xl border border-white/[0.1] bg-black/40 px-3.5 py-2 text-xs sm:text-sm text-white focus:border-[#25F4EE] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Header: หมวดสินค้า (Category / Label)
                </label>
                <input
                  type="text"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="เช่น เมาส์ไร้สายเพื่อสุขภาพ, สายรัดข้อมืออัจฉริยะ"
                  className="w-full rounded-xl border border-white/[0.1] bg-black/40 px-3.5 py-2 text-xs sm:text-sm text-white focus:border-[#25F4EE] focus:outline-none"
                />
              </div>
            </div>

            {/* Scope Selector */}
            <div className="rounded-2xl border border-[#25F4EE]/30 bg-[#25F4EE]/5 p-3.5 space-y-2.5">
              <span className="text-xs font-bold text-cyan-200 block">
                ขอบเขตการนำไปใช้:
              </span>

              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="radio"
                  name="hookScope"
                  value="all"
                  checked={scope === 'all'}
                  onChange={() => setScope('all')}
                  className="mt-0.5 h-4 w-4 accent-[#25F4EE] cursor-pointer"
                />
                <div className="text-xs">
                  <strong className="text-white block font-semibold">
                    ใช้กับทุกสคริปต์ของสินค้านี้ (แนะนำ)
                  </strong>
                  <span className="text-slate-400 text-[11px] leading-relaxed">
                    อัปเดตสคริปต์ทั้ง {angles.length || 1} มุม และบันทึกเป็นค่าเริ่มต้นหลักของสินค้าตัวนี้
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="radio"
                  name="hookScope"
                  value="current"
                  checked={scope === 'current'}
                  onChange={() => setScope('current')}
                  className="mt-0.5 h-4 w-4 accent-[#25F4EE] cursor-pointer"
                />
                <div className="text-xs">
                  <strong className="text-white block font-semibold">
                    ใช้เฉพาะสคริปต์มุมนี้ (มุมที่ {currentAngleIndex + 1}: {currentAngle.angle_name || 'สคริปต์ปัจจุบัน'})
                  </strong>
                  <span className="text-slate-400 text-[11px] leading-relaxed">
                    ปรับเฉพาะคลิปนี้เท่านั้น ไม่กระทบมุมอื่นของสินค้า
                  </span>
                </div>
              </label>
            </div>

            {/* Optional Find & Replace Sync Toggle */}
            <label className="flex items-center gap-2 p-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] text-xs text-slate-300 hover:text-white cursor-pointer select-none">
              <input
                type="checkbox"
                checked={syncScriptText}
                onChange={(e) => setSyncScriptText(e.target.checked)}
                className="h-4 w-4 rounded accent-[#25F4EE] cursor-pointer"
              />
              <span>ค้นหาและแทนที่คำว่าแบรนด์/รุ่นในเนื้อหาบทพูดพากย์ให้อัตโนมัติด้วย</span>
            </label>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={onClose}
                disabled={savingHeader}
                className="px-3.5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-bold text-slate-300 hover:text-white cursor-pointer transition-all"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={handleSaveHeader}
                disabled={savingHeader}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:from-[#20ded8] hover:to-cyan-300 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md cursor-pointer transition-all disabled:opacity-50"
              >
                {savingHeader ? (
                  <span>กำลังบันทึก...</span>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>บันทึกป้าย Hook</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
