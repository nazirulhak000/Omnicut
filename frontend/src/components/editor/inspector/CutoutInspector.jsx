import React from 'react';
import { Layers, Check, Loader2, Sparkles, Crosshair } from 'lucide-react';

export default function CutoutInspector({
  backgroundIsolation,
  backgroundIsolationStatus,
  onToggleBackgroundIsolation,
  cutoutPreviewMode = 'composite',
  onCutoutPreviewModeChange,
  subjectPoints = [],
  subjectPickMode = false,
  onToggleSubjectPickMode,
  onClearSubjectPoints,
}) {
  const isEnabled = backgroundIsolation?.enabled === true;
  const statusState = backgroundIsolationStatus?.state || (isEnabled ? 'ready' : 'off');
  const posPoints = subjectPoints.filter((p) => p.label === 1);
  const negPoints = subjectPoints.filter((p) => p.label === 0);

  return (
    <div className="space-y-3 rounded-xl border border-white/[0.08] bg-[#0E131E] p-3 shadow-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/[0.04] text-slate-300 border border-white/[0.08]">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>ตัดพื้นหลัง / แยกวัตถุ</span>
              <span className="text-[10px] font-mono text-slate-400 font-semibold px-1.5 py-0.2 rounded bg-white/[0.04] border border-white/[0.06]">SAM 2</span>
            </h4>
            <p className="text-[10px] text-slate-400">วางข้อความ/ซับไตเติลไว้ด้านหลังวัตถุ</p>
          </div>
        </div>

        {/* Status Pill */}
        <div className="flex items-center gap-1.5">
          {statusState === 'ready' ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
              <Check className="h-3 w-3" />
              <span>พร้อมใช้งาน</span>
            </span>
          ) : statusState === 'generating' ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-400 animate-pulse">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>กำลังประมวลผล</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              ปิดอยู่
            </span>
          )}
        </div>
      </div>

      {/* Main Toggle Button */}
      <button
        type="button"
        onClick={() => onToggleBackgroundIsolation?.(!isEnabled)}
        className={`w-full py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer border ${
          isEnabled
            ? 'bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border-[#25F4EE]/40 text-[#25F4EE]'
            : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.08] text-slate-300'
        }`}
      >
        <Layers className="h-3.5 w-3.5" />
        <span>{isEnabled ? 'เปิดใช้งาน Cutout อยู่ (คลิกเพื่อปิด)' : 'เปิดใช้งานระบบตัดพื้นหลัง (Cutout)'}</span>
      </button>

      {isEnabled && (
        <>
          {/* Display Mode Switcher */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] font-semibold text-slate-300 block">โหมดการแสดงผลเพื่อตรวจเช็ค:</span>
            <div className="grid grid-cols-3 gap-1 rounded-xl bg-black/60 p-1 border border-white/10">
              <button
                type="button"
                onClick={() => onCutoutPreviewModeChange?.('composite')}
                title="แสดงคลิปแยกพื้นหลังปกติ พร้อมข้อความด้านหลัง"
                className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center cursor-pointer ${
                  cutoutPreviewMode === 'composite'
                    ? 'bg-white/[0.12] text-white border border-white/[0.16] shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                ปกติ
              </button>
              <button
                type="button"
                onClick={() => onCutoutPreviewModeChange?.('checkerboard')}
                title="แสดงพื้นหลังตารางหมากรุก เพื่อตรวจเช็กความโปร่งใสและขอบไดคัท"
                className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center cursor-pointer ${
                  cutoutPreviewMode === 'checkerboard'
                    ? 'bg-white/[0.12] text-white border border-white/[0.16] shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                หมากรุก
              </button>
              <button
                type="button"
                onClick={() => onCutoutPreviewModeChange?.('matte')}
                title="แสดงมาสก์ขาวดำ (Alpha Matte) เพื่อตรวจเช็กรอยรั่วและรูโหว่"
                className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center cursor-pointer ${
                  cutoutPreviewMode === 'matte'
                    ? 'bg-white/[0.12] text-white border border-white/[0.16] shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                มาสก์
              </button>
            </div>
            <p className="text-[10px] text-slate-500 italic">
              {cutoutPreviewMode === 'composite' && '• โหมดปกติ: วางข้อความและเอฟเฟกต์ซ้อนหลังสินค้า'}
              {cutoutPreviewMode === 'checkerboard' && '• โหมดหมากรุก: ตรวจดูความเนียนของขอบไดคัทและเงา'}
              {cutoutPreviewMode === 'matte' && '• โหมดมาสก์: ตรวจเช็กพื้นที่สีขาว (เก็บ) และสีดำ (ลบออก)'}
            </p>
          </div>

          {/* Interactive Subject Points */}
          <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-slate-300">จุดนำทางวัตถุ (Subject Points):</span>
              <span className="font-mono text-[10px] text-slate-400">
                + {posPoints.length} | - {negPoints.length}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onToggleSubjectPickMode}
                className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer border ${
                  subjectPickMode
                    ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.3)] animate-pulse'
                    : 'bg-white/5 border-white/10 text-slate-300 hover:text-white hover:bg-white/10'
                }`}
              >
                <Crosshair className="w-3.5 h-3.5" />
                <span>{subjectPickMode ? 'กำลังจิ้มจุดบนจอ...' : 'จิ้มจุดวัตถุบนจอ'}</span>
              </button>
              {subjectPoints.length > 0 && onClearSubjectPoints && (
                <button
                  type="button"
                  onClick={onClearSubjectPoints}
                  title="ล้างจุดที่เลือกทั้งหมด"
                  className="px-2.5 py-1.5 rounded-xl border border-white/10 bg-white/5 text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 cursor-pointer transition-all"
                >
                  ล้างจุด
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
