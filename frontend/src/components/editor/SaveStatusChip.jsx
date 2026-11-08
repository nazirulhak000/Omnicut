import React from 'react';
import { Check, Loader2, AlertTriangle } from 'lucide-react';

/**
 * SaveStatusChip
 * Merges save-state display and manual-save trigger into one compact pill next to the project name.
 * Clickable anytime (Ctrl+S equivalent), with distinct visual states for saved / dirty (unsaved) / saving / error.
 * Enforces clean icons, accessible aria-labels, and no flickering text (no whole-container pulse animation).
 */
export default function SaveStatusChip({
  saveStatus = 'saved',
  onSave,
  disabled = false,
  className = '',
}) {
  const isSaving = saveStatus === 'saving';
  const isError = saveStatus === 'error';
  const isDirty = saveStatus === 'dirty' || saveStatus === 'unsaved';

  const handleClick = (e) => {
    e.preventDefault();
    if (disabled || isSaving) return;
    onSave?.();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isSaving}
      aria-label={
        isSaving
          ? 'กำลังบันทึกโปรเจกต์'
          : isError
            ? 'บันทึกไม่สำเร็จ คลิกเพื่อลองใหม่ (Ctrl+S)'
            : isDirty
              ? 'มีการแก้ไขที่ยังไม่ได้บันทึก คลิกเพื่อบันทึกทันที (Ctrl+S)'
              : 'บันทึกแล้ว คลิกเพื่อบันทึกซ้ำ (Ctrl+S)'
      }
      title={
        isSaving
          ? 'กำลังบันทึกข้อมูล...'
          : isError
            ? 'บันทึกไม่สำเร็จ — คลิกเพื่อลองบันทึกใหม่ (Ctrl+S)'
            : isDirty
              ? 'มีการแก้ไขที่ยังไม่ได้บันทึก — คลิกเพื่อบันทึกลงโปรเจกต์ (Ctrl+S)'
              : 'บันทึกล่าสุดเรียบร้อย — คลิกเพื่อบันทึกซ้ำ (Ctrl+S)'
      }
      className={`group inline-flex h-7 sm:h-8 items-center gap-1.5 px-2 sm:px-2.5 rounded-lg border text-xs font-semibold transition-all select-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 ${
        isSaving
          ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
          : isError
            ? 'border-red-500/50 bg-red-500/15 text-red-300 hover:bg-red-500/25'
            : isDirty
              ? 'border-amber-500/30 bg-amber-500/10 text-amber-300 hover:border-amber-500/50 hover:bg-amber-500/20'
              : 'border-white/[0.08] bg-white/[0.03] text-slate-300 hover:border-white/[0.18] hover:bg-white/[0.08] hover:text-white'
      } ${className}`}
    >
      {isSaving ? (
        <Loader2 className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-spin text-amber-400 flex-shrink-0" />
      ) : isError ? (
        <AlertTriangle className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-red-400 flex-shrink-0" />
      ) : isDirty ? (
        <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0 shadow-[0_0_6px_rgba(251,191,36,0.6)]" />
      ) : (
        <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-400 flex-shrink-0" />
      )}

      <span className="hidden sm:inline text-[11px] font-medium tracking-tight">
        {isSaving
          ? 'กำลังบันทึก...'
          : isError
            ? 'บันทึกไม่สำเร็จ'
            : isDirty
              ? 'มีการแก้ไข'
              : 'บันทึกแล้ว'}
      </span>
    </button>
  );
}
