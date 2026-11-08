import React, { useState, useRef, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Check,
  Loader2,
  Image as ImageIcon,
  BookOpen,
  ChevronDown,
  X,
  ExternalLink,
} from 'lucide-react';

/**
 * RenderReadinessChip
 * Unifies Cover Status, Preflight Audit & Viral Score, and Boss Playbook Tips into
 * one high-signal chip with an interactive Popover checklist.
 */
export default function RenderReadinessChip({
  coverStatus = null,
  coverChecking = false,
  onOpenCoverStudio,
  preflightReport = null,
  onOpenPreflightModal,
  playbookNotes = [],
  onOpenPlaybookModal,
  disabled = false,
  className = '',
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);

  // Close on outside click and Escape
  useEffect(() => {
    if (!open) return;
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  const errors = preflightReport?.errors || [];
  const warnings = preflightReport?.warnings || [];
  const viralScore = Number.isFinite(preflightReport?.viralScore) ? preflightReport.viralScore : null;

  const isCoverMissing = coverStatus === false;
  const hasErrors = errors.length > 0 || isCoverMissing;
  const hasWarnings = warnings.length > 0 && !hasErrors;
  const isReady = !hasErrors && !hasWarnings;

  const totalBlockers = errors.length + (isCoverMissing ? 1 : 0);

  return (
    <div ref={containerRef} className={`relative flex-shrink-0 ${className}`}>
      {/* ── Main Readiness Trigger Chip ── */}
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`สถานะความพร้อมเรนเดอร์: ${hasErrors ? 'ต้องแก้ไข' : hasWarnings ? 'มีคำเตือน' : 'พร้อม'}`}
        title="ตรวจเช็กความพร้อมก่อนเรนเดอร์ (ปก, ตรวจแผน, ข้อเตือนใจ)"
        className={`flex h-8 sm:h-9 items-center gap-1.5 rounded-xl border px-2 sm:px-2.5 text-xs font-bold transition-all cursor-pointer select-none disabled:opacity-40 disabled:cursor-not-allowed ${
          open
            ? 'ring-2 ring-white/20'
            : ''
        } ${
          hasErrors
            ? 'border-red-500/40 bg-red-500/15 text-red-300 hover:bg-red-500/25 shadow-sm shadow-red-500/10'
            : hasWarnings
              ? 'border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 shadow-sm shadow-amber-500/10'
              : 'border-emerald-500/35 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 shadow-sm shadow-emerald-500/10'
        }`}
      >
        {hasErrors ? (
          <ShieldAlert className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
        ) : hasWarnings ? (
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
        ) : (
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        )}

        <span className="hidden xl:inline tracking-tight">
          {hasErrors ? 'ตรวจแก้' : hasWarnings ? 'เตือน' : 'พร้อม'}
        </span>

        {viralScore !== null && (
          <span className="font-mono text-[11px] font-semibold text-white/90">
            {viralScore}
          </span>
        )}

        {totalBlockers > 0 ? (
          <span className="rounded bg-red-500/30 px-1 py-0.2 text-[10px] font-bold text-red-200">
            แก้ {totalBlockers}
          </span>
        ) : warnings.length > 0 ? (
          <span className="rounded bg-amber-500/25 px-1 py-0.2 text-[10px] font-bold text-amber-200">
            {warnings.length}
          </span>
        ) : null}

        <ChevronDown
          className={`w-3 h-3 text-white/60 transition-transform duration-200 ${
            open ? 'rotate-180 text-white' : ''
          }`}
        />
      </button>

      {/* ── Readiness Checklist Popover ── */}
      {open && (
        <div
          role="dialog"
          aria-label="รายการตรวจสอบความพร้อมก่อนเรนเดอร์"
          className="absolute right-0 top-full mt-2 z-50 w-80 max-w-[92vw] rounded-2xl border border-white/[0.12] bg-[#0A101E]/95 backdrop-blur-2xl p-3 shadow-2xl space-y-2.5 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-white">ความพร้อมก่อนเรนเดอร์</span>
            </div>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                hasErrors
                  ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                  : hasWarnings
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              }`}
            >
              {hasErrors ? 'ต้องแก้ไขก่อนเรนเดอร์' : hasWarnings ? 'มีข้อแนะนำ' : 'พร้อมเรนเดอร์ 100%'}
            </span>
          </div>

          {/* Checklist Items */}
          <div className="space-y-2">
            {/* Item 1: Cover Status */}
            <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    coverStatus === true
                      ? 'bg-emerald-500/15 text-emerald-400'
                      : isCoverMissing
                        ? 'bg-red-500/15 text-red-400'
                        : 'bg-white/[0.06] text-slate-400'
                  }`}
                >
                  <ImageIcon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold text-white truncate">ภาพปก 9:16</div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {coverChecking ? (
                      <span className="text-amber-300 flex items-center gap-1">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" /> กำลังตรวจสอบ...
                      </span>
                    ) : coverStatus === true ? (
                      <span className="text-emerald-400 font-medium">มีภาพปกแล้ว พร้อมเรนเดอร์</span>
                    ) : isCoverMissing ? (
                      <span className="text-red-400 font-semibold">ยังไม่มีภาพปก (จำเป็น)</span>
                    ) : (
                      'ยังไม่ได้ตรวจสอบ'
                    )}
                  </div>
                </div>
              </div>

              {onOpenCoverStudio && (
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    onOpenCoverStudio();
                  }}
                  className={`px-2 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer flex-shrink-0 ${
                    coverStatus === true
                      ? 'bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 hover:text-white'
                      : 'bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 shadow-sm'
                  }`}
                >
                  {coverStatus === true ? 'แก้ไขปก' : 'สร้างปก'}
                </button>
              )}
            </div>

            {/* Item 2: Preflight Audit & Viral Score */}
            <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    errors.length > 0
                      ? 'bg-red-500/15 text-red-400'
                      : warnings.length > 0
                        ? 'bg-amber-500/15 text-amber-400'
                        : 'bg-emerald-500/15 text-emerald-400'
                  }`}
                >
                  {errors.length > 0 ? (
                    <ShieldAlert className="w-3.5 h-3.5" />
                  ) : (
                    <ShieldCheck className="w-3.5 h-3.5" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>ตรวจแผน & คะแนนไวรัล</span>
                    {viralScore !== null && (
                      <span className="text-[10px] font-mono px-1 rounded bg-white/[0.08] text-cyan-300">
                        {viralScore}/100
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {errors.length > 0 ? (
                      <span className="text-red-400 font-semibold">พบข้อผิดพลาด {errors.length} จุด</span>
                    ) : warnings.length > 0 ? (
                      <span className="text-amber-300 font-medium">มีข้อแนะนำ {warnings.length} จุด</span>
                    ) : (
                      <span className="text-emerald-400 font-medium">ผ่านเกณฑ์สมบูรณ์</span>
                    )}
                  </div>
                </div>
              </div>

              {onOpenPreflightModal && (
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    onOpenPreflightModal();
                  }}
                  className="px-2 py-1 rounded-lg text-xs font-bold bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 hover:text-white transition-all cursor-pointer flex-shrink-0"
                >
                  ดูรายละเอียด
                </button>
              )}
            </div>

            {/* Item 3: Boss Playbook Tips */}
            <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 text-amber-400 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold text-white truncate">ข้อเตือนใจเจ้านาย</div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {playbookNotes.length > 0
                      ? `${playbookNotes.length} ข้อเตือนใจคุมคุณภาพ`
                      : 'เทคนิคและข้อควรระวัง'}
                  </div>
                </div>
              </div>

              {onOpenPlaybookModal && (
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    onOpenPlaybookModal();
                  }}
                  className="px-2 py-1 rounded-lg text-xs font-bold bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 hover:text-white transition-all cursor-pointer flex-shrink-0"
                >
                  เปิดดู
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
