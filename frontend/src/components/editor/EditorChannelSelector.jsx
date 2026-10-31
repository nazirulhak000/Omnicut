import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Radio, ChevronDown, Check, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { useChannel } from '../../context/ChannelContext.jsx';

/**
 * EditorChannelSelector
 * Compact glassmorphism channel selector integrated directly into EditorHeader.
 * Maximizes vertical canvas space by eliminating the redundant standalone top channel bar.
 * Follows Rule 3.8 / 4.8 (action verbs, zero leading symbols/emojis).
 */
export default function EditorChannelSelector() {
  const channelState = useChannel();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

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
    <div ref={containerRef} className="relative flex-shrink-0" data-testid="editor-channel-selector">
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
        className={`group flex h-8 sm:h-9 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-semibold transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-cyan-400/50 ${
          open
            ? 'border-cyan-400/60 bg-cyan-500/15 text-white shadow-lg shadow-cyan-500/10'
            : 'border-white/[0.1] bg-white/[0.04] text-slate-200 hover:border-white/[0.22] hover:bg-white/[0.08] hover:text-white'
        }`}
      >
        {switching ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400 flex-shrink-0" />
        ) : (
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 transition-all ${
              canStart
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                : isDraft
                ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]'
                : 'bg-slate-400'
            }`}
          />
        )}

        <Radio className="w-3.5 h-3.5 text-cyan-400/80 flex-shrink-0" />

        <span className="max-w-[85px] sm:max-w-[130px] truncate font-bold text-white tracking-tight">
          {currentDisplayName}
        </span>

        {currentHandle && (
          <span className="hidden xl:inline text-[11px] font-normal text-slate-400 truncate max-w-[90px]">
            {currentHandle}
          </span>
        )}

        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${
            open ? 'rotate-180 text-cyan-300' : 'group-hover:text-slate-200'
          }`}
        />
      </button>

      {/* ── Dropdown Popover ── */}
      {open && (
        <div
          role="listbox"
          aria-label="รายชื่อช่องการทำงาน"
          className="absolute left-0 top-full mt-1.5 z-50 w-72 max-w-[90vw] rounded-2xl border border-white/[0.12] bg-[#0A101E]/95 backdrop-blur-2xl p-2 shadow-2xl space-y-1.5 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-2 py-1 border-b border-white/[0.08]">
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-bold text-white">ช่องการทำงาน</span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">
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
                  className={`w-full text-left p-2 rounded-xl flex items-center justify-between gap-2 transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/15 border border-cyan-500/40 text-white shadow-sm'
                      : 'hover:bg-white/[0.06] border border-transparent text-slate-300 hover:text-white'
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
        </div>
      )}
    </div>
  );
}
