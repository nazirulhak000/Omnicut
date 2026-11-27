import React, { useState, useRef, useCallback } from 'react';
import { Radio, ChevronDown, Check, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { useChannel } from '../../context/ChannelContext.jsx';
import { PopoverPanel } from '../ui/PopoverPanel';

/**
 * EditorChannelSelector
 * Compact glassmorphism channel selector integrated directly into EditorHeader.
 * Maximizes vertical canvas space by eliminating the redundant standalone top channel bar.
 * Follows Rule 3.8 / 4.8 (action verbs, zero leading symbols/emojis).
 */
export default function EditorChannelSelector() {
  const channelState = useChannel();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  // Graceful fallback if ChannelProvider is absent or loading initial state
  if (!channelState) return null;

  const {
    channelId,
    selected,
    channels = [],
    loading = false,
    switching = false,
    switchChannel,
    error,
    refresh,
    canStart = false,
  } = channelState;

  const currentDisplayName = selected?.display_name || channelId || 'ช่องหลัก';
  const currentHandle = selected?.handle || '';
  const isArchived = selected?.status === 'archived';
  const isDraft = selected?.status === 'draft';

  const handleSelectChannel = (id) => {
    if (id !== channelId && switchChannel) {
      switchChannel(id);
    }
    setOpen(false);
  };

  return (
    <div className="relative flex-shrink-0" data-testid="editor-channel-selector">
      {/* ── Accessible Native Select for automation and screen-reader accessibility ── */}
      <select
        aria-label="เลือกช่อง"
        value={channelId}
        disabled={loading || switching}
        onChange={(e) => handleSelectChannel(e.target.value)}
        className="sr-only"
        tabIndex={-1}
      >
        {!selected && <option value={channelId}>{channelId}</option>}
        {channels.map((item) => (
          <option key={item.id} value={item.id}>
            {item.display_name || item.id}
          </option>
        ))}
      </select>
      {/* ── Compact Channel Pill Button ── */}
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={loading || switching}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`สลับช่องทำงาน ปัจจุบันเลือกช่อง ${currentDisplayName}`}
        title={`ช่อง: ${currentDisplayName} ${currentHandle} (${canStart ? 'พร้อมผลิต' : isDraft ? 'แบบร่าง' : isArchived ? 'เก็บถาวร' : 'พร้อมใช้งาน'})`}
        className={`group flex h-8 sm:h-9 items-center gap-1.5 rounded-lg border px-1.5 sm:px-2.5 text-xs font-semibold active:scale-[0.97] disabled:active:scale-100 motion-press active:duration-100 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A] ${
          open
            ? 'border-[#234739] bg-[#121A18] text-[#F4F4F5]'
            : 'border-[#2B2E36] bg-[#1B1D22] text-[#D4D4D8] hover:border-[#3A3E4A] hover:bg-[#22252C] hover:text-[#F4F4F5]'
        }`}
      >
        {switching ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-[#34D399] flex-shrink-0" />
        ) : (
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 transition-[background-color,box-shadow] duration-150 ease-out ${
              canStart
                ? 'bg-[#34D399]'
                : isDraft
                ? 'bg-[#FBBF24]'
                : 'bg-[#5C6069]'
            }`}
          />
        )}

        <Radio className="w-3.5 h-3.5 text-[#8E929B] flex-shrink-0" />

        <span className="hidden sm:inline-block max-w-[130px] truncate font-bold text-[#F4F4F5] tracking-tight">
          {currentDisplayName}
        </span>

        <ChevronDown
          className={`w-3.5 h-3.5 text-[#8E929B] transition-transform duration-200 flex-shrink-0 ${
            open ? 'rotate-180 text-[#F4F4F5]' : 'group-hover:text-[#D4D4D8]'
          }`}
        />
      </button>

      {/* ── Dropdown Popover ── */}
      {open && (
        <PopoverPanel
          anchorRef={buttonRef}
          onClose={() => setOpen(false)}
          align="start"
          role="listbox"
          aria-label="รายชื่อช่องการทำงาน"
          className="w-72 max-w-[90vw] rounded-xl border border-[#23262D] bg-[#14161A] p-2 space-y-1.5 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-2 py-1 border-b border-[#1E2026]">
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-[#34D399]" />
              <span className="text-xs font-bold text-[#F4F4F5]">ช่องการทำงาน</span>
            </div>
            <span className="text-[10px] text-[#8E929B] font-medium">
              {channels.length} ช่อง
            </span>
          </div>

          {/* Channel list */}
          <div className="max-h-60 overflow-y-auto space-y-1 pr-0.5 custom-scrollbar">
            {channels.map((ch) => {
              const isSelected = ch.id === channelId;
              const chDisplayName = ch.display_name || ch.id;
              const chStatus = ch.status || 'active';

              return (
                <button
                  key={ch.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelectChannel(ch.id)}
                  className={`w-full text-left p-2 rounded-lg flex items-center justify-between gap-2 active:scale-[0.98] motion-press active:duration-100 cursor-pointer ${
                    isSelected
                      ? 'bg-[#121A18] border border-[#234739] text-[#F4F4F5]'
                      : 'hover:bg-[#1B1D22] border border-transparent text-[#D4D4D8] hover:text-[#F4F4F5]'
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          chStatus === 'active'
                            ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]'
                            : chStatus === 'draft'
                            ? 'bg-amber-400'
                            : 'bg-slate-500'
                        }`}
                      />
                      <span className="text-xs font-bold truncate">
                        {chDisplayName}
                      </span>
                    </div>
                    {ch.handle && (
                      <div className="text-[11px] text-slate-400 pl-3 truncate">
                        {ch.handle}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-md font-medium ${
                        chStatus === 'active'
                          ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25'
                          : chStatus === 'draft'
                          ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                          : 'bg-slate-500/15 text-slate-400 border border-slate-500/25'
                      }`}
                    >
                      {chStatus === 'active'
                        ? 'พร้อมผลิต'
                        : chStatus === 'draft'
                        ? 'แบบร่าง'
                        : 'เก็บถาวร'}
                    </span>

                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Footer / Error handling */}
          {error && (
            <div className="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-[11px] text-rose-300">
              <span className="truncate flex items-center gap-1">
                <AlertCircle className="w-3 h-3 flex-shrink-0" />
                {error}
              </span>
              <button
                type="button"
                onClick={refresh}
                className="text-[10px] font-bold underline hover:text-white cursor-pointer"
              >
                โหลดใหม่
              </button>
            </div>
          )}
        </PopoverPanel>
      )}
    </div>
  );
}
