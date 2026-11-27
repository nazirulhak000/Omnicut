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
      // Stable hook for E2E tests: the visible label and tooltip change with
      // the save state and the wording gets revised (X-07).
      data-testid="editor-save-button"
      data-save-status={saveStatus}
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
      className={`group inline-flex h-7 sm:h-8 items-center gap-1.5 px-2 sm:px-2.5 rounded-lg border text-xs font-semibold active:scale-[0.96] disabled:active:scale-100 motion-press active:duration-100 select-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 ${
        isSaving
          ? 'border-[#4D3B19] bg-[#241D11] text-[#FBBF24]'
          : isError
            ? 'border-[#52232A] bg-[#271417] text-[#F87171] hover:bg-[#3A1B20]'
            : isDirty
              ? 'border-[#4D3B19] bg-[#241D11] text-[#FBBF24] hover:border-[#6B5223]'
              : 'border-[#2B2E36] bg-[#1B1D22] text-[#D4D4D8] hover:border-[#3A3E4A] hover:bg-[#22252C] hover:text-[#F4F4F5]'
      } ${className}`}
    >
      {isSaving ? (
        <Loader2 className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-spin text-[#FBBF24] flex-shrink-0" />
      ) : isError ? (
        <AlertTriangle className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-[#F87171] flex-shrink-0" />
      ) : isDirty ? (
        <span className="w-2 h-2 rounded-full bg-[#FBBF24] flex-shrink-0" />
      ) : (
        <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-[#34D399] flex-shrink-0" />
      )}

      <span className="hidden lg:inline text-[11px] font-medium tracking-tight">
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
