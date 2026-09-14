import React, { useState, useEffect, useMemo } from 'react';
import { Tag, Sparkles, Check, X, Layers, AlertCircle, RefreshCw } from 'lucide-react';
import { Modal } from './ui';
import { guessBrandModel } from '../lib/overlayModel';

export default function HookHeaderModal({
  isOpen,
  onClose,
  product,
  angles = [],
  currentAngleIndex = 0,
  onSaveHookHeader,
}) {
  const currentAngle = angles[currentAngleIndex] || {};
  const guessed = useMemo(() => {
    return guessBrandModel(currentAngle.product_name || product?.name || product?.title || '');
  }, [currentAngle.product_name, product?.name, product?.title]);

  const [brand, setBrand] = useState('');
  const [model, setModel] = useState('');
  const [label, setLabel] = useState('');
  const [scope, setScope] = useState('all'); // 'all' | 'current'
  const [syncScriptText, setSyncScriptText] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const initialBrand = currentAngle.hook_brand ?? product?.hook_brand ?? guessed.brand ?? '';
    const initialModel = currentAngle.hook_model ?? product?.hook_model ?? guessed.model ?? '';
    const initialLabel = currentAngle.hook_label ?? product?.hook_label ?? '';

    setBrand(initialBrand);
    setModel(initialModel);
    setLabel(initialLabel);
    setScope('all');
    setSyncScriptText(false);
  }, [isOpen, currentAngle, product, guessed]);

  const handleResetToGuessed = () => {
    setBrand(guessed.brand || '');
    setModel(guessed.model || '');
  };

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await onSaveHookHeader({
        hookBrand: brand.trim(),
        hookModel: model.trim(),
        hookLabel: label.trim(),
        scope,
        syncScriptText,
        angleIndex: currentAngleIndex,
      });
      onClose();
    } catch (err) {
      console.error('Failed to save hook header:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="ตั้งค่าป้าย Hook Header (แบรนด์ · รุ่น · หมวด)"
      subtitle="ข้อความ 3 บรรทัดบนหัววิดีโอ 9:16 ที่ดึงดูดสายตา 3-5 วินาทีแรก"
      icon={Tag}
      maxWidth="max-w-xl"
    >
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
                อัปเดตสคริปต์ทั้ง {angles.length} มุม และบันทึกเป็นค่าเริ่มต้นหลักของสินค้าตัวนี้
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
            disabled={saving}
            className="px-3.5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-bold text-slate-300 hover:text-white cursor-pointer transition-all"
          >
            ยกเลิก
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:from-[#20ded8] hover:to-cyan-300 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md cursor-pointer transition-all disabled:opacity-50"
          >
            {saving ? (
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
    </Modal>
  );
}
