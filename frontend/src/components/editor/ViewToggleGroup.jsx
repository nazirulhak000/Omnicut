import React from 'react';
import { PanelLeftOpen, PanelLeftClose, PanelRightOpen, PanelRightClose, Columns3 } from 'lucide-react';

/**
 * ViewToggleGroup
 * Compact segmented viewport controller for EditorHeader Zone 2 (Center).
 * Icon-only presentation with comprehensive aria-labels and tooltips.
 */
export default function ViewToggleGroup({
  projectName,
  zen = false,
  leftSidebarCollapsed = false,
  toggleLeftSidebar,
  rightSidebarCollapsed = false,
  toggleRightSidebar,
  isFocusMode,
  toggleFocusMode,
  className = '',
}) {
  const disabled = !projectName || zen;
  const activeFocus = isFocusMode ?? (leftSidebarCollapsed && rightSidebarCollapsed);

  return (
    <div
      role="group"
      aria-label="ตัวควบคุมมุมมองพาเนล"
      className={`inline-flex items-center gap-0.5 bg-[#0A0D14]/90 border border-white/[0.08] p-0.5 rounded-lg ${className}`}
    >
      {/* Left panel toggle */}
      <button
        type="button"
        onClick={toggleLeftSidebar}
        disabled={disabled}
        aria-label={leftSidebarCollapsed ? 'เปิดแถบซ้าย (คลังสื่อ)' : 'ซ่อนแถบซ้าย (คลังสื่อ)'}
        aria-pressed={!leftSidebarCollapsed}
        title={
          zen
            ? 'ปิดโหมดเต็มจอก่อน (Esc)'
            : leftSidebarCollapsed
              ? 'เปิดแถบซ้าย (คลังสื่อ)'
              : 'ซ่อนแถบซ้าย'
        }
        className={`h-7 w-7 sm:h-8 sm:w-8 rounded-md flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
          !leftSidebarCollapsed
            ? 'bg-[#25F4EE]/12 text-[#25F4EE] border border-[#25F4EE]/30'
            : 'text-slate-400 hover:text-white hover:bg-white/[0.06] border border-transparent'
        }`}
      >
        {leftSidebarCollapsed ? (
          <PanelLeftOpen className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        ) : (
          <PanelLeftClose className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        )}
      </button>

      {/* Focus mode toggle */}
      <button
        type="button"
        onClick={toggleFocusMode}
        disabled={disabled}
        aria-label={activeFocus ? 'ออกจากโหมดโฟกัส' : 'เข้าโหมดโฟกัส (ซ่อนพาเนลข้างทั้งหมด)'}
        aria-pressed={Boolean(activeFocus)}
        title={
          zen
            ? 'ปิดโหมดเต็มจอก่อน (Esc)'
            : activeFocus
              ? 'ออกจากโหมดโฟกัส (เปิดพาเนลข้าง)'
              : 'เข้าโหมดโฟกัส (ซ่อนพาเนลข้างทั้งหมด)'
        }
        className={`h-7 w-7 sm:h-8 sm:w-8 rounded-md flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
          activeFocus
            ? 'bg-amber-400/15 text-amber-300 border border-amber-400/30'
            : 'text-slate-400 hover:text-white hover:bg-white/[0.06] border border-transparent'
        }`}
      >
        <Columns3 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
      </button>

      {/* Right panel toggle */}
      <button
        type="button"
        onClick={toggleRightSidebar}
        disabled={disabled}
        aria-label={rightSidebarCollapsed ? 'เปิดแถบขวา (คำบรรยาย/สารบัญ)' : 'ซ่อนแถบขวา (คำบรรยาย/สารบัญ)'}
        aria-pressed={!rightSidebarCollapsed}
        title={
          zen
            ? 'ปิดโหมดเต็มจอก่อน (Esc)'
            : rightSidebarCollapsed
              ? 'เปิดแถบขวา (คำบรรยาย)'
              : 'ซ่อนแถบขวา'
        }
        className={`h-7 w-7 sm:h-8 sm:w-8 rounded-md flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
          !rightSidebarCollapsed
            ? 'bg-[#D97757]/15 text-[#E08A6D] border border-[#D97757]/30'
            : 'text-slate-400 hover:text-white hover:bg-white/[0.06] border border-transparent'
        }`}
      >
        {rightSidebarCollapsed ? (
          <PanelRightOpen className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        ) : (
          <PanelRightClose className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        )}
      </button>
    </div>
  );
}
