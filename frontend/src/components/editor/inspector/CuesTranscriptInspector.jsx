import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  Replace,
  Sparkles,
  Magnet,
  Clock,
  Plus,
  X,
  CheckCheck,
  Scissors,
  Link2,
  Trash2,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { formatShortTime } from '../../../lib/inspectorModel';

export default function CuesTranscriptInspector({
  cuesList = [],
  playhead = 0,
  selectedCaption = null,
  assets = {},
  onSelectCue,
  onSeek,
  onCaptionChange,
  onSplitCue,
  onMergeCue,
  onMergeWithPrevious,
  onDeleteCue,
  onInsertCueAfter,
  onReorderCues,
  onBatchFindAndReplace,
  onBatchFormatClean,
  onCloseAllCaptionGaps,
  onResetSubtitleTimings,
  onAddTextAtPlayhead,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findWord, setFindWord] = useState('');
  const [replaceWord, setReplaceWord] = useState('');
  const [replaceMessage, setReplaceMessage] = useState(null);

  const inputRefs = useRef({});
  const rowRefs = useRef({});
  const isTypingRef = useRef(false);

  // Only starred SFX show up here -- with 1800+ total SFX, rendering every
  // one as an <option> per cue row (one <select> per row) froze the browser
  // on transcripts with many lines. Falls back to the full list if nothing
  // is starred yet, so the picker isn't empty before anyone has starred one.
  const allSfx = assets?.sfx || [];
  const starredSfx = allSfx.filter((s) => s.starred);
  const sfxList = starredSfx.length > 0 ? starredSfx : allSfx;

  // Filter cues by search query
  const filteredCues = cuesList.filter((cue) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (cue.text || '').toLowerCase().includes(q) || (cue.translation || '').toLowerCase().includes(q);
  });

  // Karaoke playhead auto-scroll sync
  useEffect(() => {
    if (isTypingRef.current) return;
    const activeCue = cuesList.find((c) => playhead >= c.start && playhead < c.end);
    if (activeCue && rowRefs.current[activeCue._uid]) {
      rowRefs.current[activeCue._uid].scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [playhead, cuesList]);

  // Word Processor keyboard ergonomics
  const handleCursorSplit = (cue, forcedCursorIdx) => {
    const el = inputRefs.current[cue._uid];
    const cursorIdx = forcedCursorIdx ?? el?.selectionStart ?? Math.floor((cue.text || '').length / 2);
    onSplitCue?.(cue._uid, cursorIdx);
  };

  const handleKeyDown = (e, cue, index) => {
    const el = e.target;
    const cursorStart = el.selectionStart;
    const cursorEnd = el.selectionEnd;
    const textLen = (cue.text || '').length;

    // 1. Enter key -> Split line at cursor
    if (e.key === 'Enter') {
      e.preventDefault();
      handleCursorSplit(cue, cursorStart);
      return;
    }

    // 2. Backspace at index 0 -> Merge with previous line
    if (e.key === 'Backspace' && cursorStart === 0 && cursorEnd === 0 && index > 0) {
      e.preventDefault();
      const prevCue = cuesList[index - 1];
      if (prevCue) {
        const prevTextLen = (prevCue.text || '').length;
        onMergeWithPrevious?.(cue._uid);
        setTimeout(() => {
          const prevEl = inputRefs.current[prevCue._uid];
          if (prevEl) {
            prevEl.focus();
            prevEl.setSelectionRange(prevTextLen, prevTextLen);
          }
        }, 30);
      }
      return;
    }

    // 3. Arrow Up (↑) -> Navigate to previous cue line
    if (e.key === 'ArrowUp' && cursorStart === 0 && index > 0) {
      e.preventDefault();
      const prevCue = cuesList[index - 1];
      if (prevCue) {
        onSelectCue?.(prevCue._uid);
        onSeek?.(prevCue.start);
        if (inputRefs.current[prevCue._uid]) {
          inputRefs.current[prevCue._uid].focus();
        }
      }
      return;
    }

    // 4. Arrow Down (↓) -> Navigate to next cue line
    if (e.key === 'ArrowDown' && cursorStart === textLen && index < cuesList.length - 1) {
      e.preventDefault();
      const nextCue = cuesList[index + 1];
      if (nextCue) {
        onSelectCue?.(nextCue._uid);
        onSeek?.(nextCue.start);
        if (inputRefs.current[nextCue._uid]) {
          inputRefs.current[nextCue._uid].focus();
        }
      }
      return;
    }
  };

  // Find and Replace Handler
  const handleExecuteReplace = () => {
    if (!findWord.trim()) return;
    const count = onBatchFindAndReplace?.(findWord.trim(), replaceWord.trim());
    setReplaceMessage(`แทนที่คำสำเร็จ ${count || 0} จุด`);
    setTimeout(() => setReplaceMessage(null), 3000);
  };

  return (
    <div className="space-y-2.5">
      {/* Header Toolbar: Search, Find & Replace, Auto-Clean, Add Cue */}
      <div className="flex items-center gap-1.5 pb-1">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ค้นหาข้อความ..."
            className="w-full py-1 pl-8 pr-2.5 rounded-lg bg-black/50 border border-white/[0.08] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]"
          />
        </div>

        {/* Find & Replace Toggle */}
        <button
          type="button"
          onClick={() => setShowFindReplace((v) => !v)}
          className={`p-1.5 rounded-lg border text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
            showFindReplace
              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
              : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.08] text-slate-400 hover:text-white'
          }`}
          title="ค้นหาและแทนที่คำผิดทั้งเรื่อง (Find & Replace All)"
        >
          <Replace className="w-3.5 h-3.5" />
        </button>

        {/* Format Clean */}
        <button
          type="button"
          onClick={() => onBatchFormatClean?.()}
          className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-amber-300 cursor-pointer transition-colors"
          title="จัดระเบียบวรรคตอนภาษาไทยและลบช่องว่างส่วนเกิน"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
        </button>

        {/* Close All Caption Gaps */}
        {onCloseAllCaptionGaps && (
          <button
            type="button"
            onClick={onCloseAllCaptionGaps}
            className="p-1.5 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] hover:text-[#52fffb] text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors flex-shrink-0"
            title="ดูดคำบรรยายทุกกล่องให้เรียงต่อกันชิดสนิทโดยไม่มีช่องว่าง"
          >
            <Magnet className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span className="hidden sm:inline">ดูดชิดติดกัน</span>
          </button>
        )}

        {/* Reset Subtitle Timings */}
        {onResetSubtitleTimings && (
          <button
            type="button"
            onClick={onResetSubtitleTimings}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-amber-300 hover:text-amber-200 text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors flex-shrink-0"
            title="รีเซ็ตเวลาคำบรรยายทั้งหมดกลับสู่ค่าต้นฉบับ"
          >
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">รีเซ็ตเวลา</span>
          </button>
        )}

        {/* Add New Text at Playhead */}
        <button
          type="button"
          onClick={onAddTextAtPlayhead}
          className="py-1 px-2 rounded-lg bg-[#D97757]/20 hover:bg-[#D97757]/30 border border-[#D97757]/40 text-[#E89274] text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors flex-shrink-0"
          title="แทรกข้อความใหม่ ณ จุดที่หัวอ่าน (Playhead) กำลังวางอยู่"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>ที่หัวอ่าน</span>
        </button>

        {/* Add New Cue at Tail */}
        <button
          type="button"
          onClick={() => onInsertCueAfter?.(cuesList[cuesList.length - 1]?._uid)}
          className="py-1 px-2 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors flex-shrink-0"
          title="เพิ่มท่อนคำบรรยายใหม่ต่อท้าย"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>ต่อท้าย</span>
        </button>
      </div>

      {/* Expandable Find & Replace Bar */}
      {showFindReplace && (
        <div className="p-2.5 rounded-xl bg-[#080B11] border border-[#25F4EE]/30 space-y-2 shadow-lg animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="flex items-center justify-between text-xs font-bold text-[#25F4EE]">
            <span className="flex items-center gap-1">
              <Replace className="w-3.5 h-3.5" />
              <span>ค้นหาและแทนที่คำผิดทั้งเรื่อง</span>
            </span>
            <button
              type="button"
              onClick={() => setShowFindReplace(false)}
              className="text-slate-500 hover:text-white cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <input
              type="text"
              value={findWord}
              onChange={(e) => setFindWord(e.target.value)}
              placeholder="คำที่ต้องการหา..."
              className="py-1 px-2 rounded-lg bg-black/60 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]"
            />
            <input
              type="text"
              value={replaceWord}
              onChange={(e) => setReplaceWord(e.target.value)}
              placeholder="แทนที่ด้วยคำนี้..."
              className="py-1 px-2 rounded-lg bg-black/60 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]"
            />
          </div>
          <div className="flex items-center justify-between">
            {replaceMessage ? (
              <span className="text-xs text-emerald-400 font-bold flex items-center gap-1">
                <CheckCheck className="w-3 h-3" />{replaceMessage}
              </span>
            ) : <span className="text-[11px] text-slate-500">กด Enter หรือกดปุ่มแทนที่</span>}
            <button
              type="button"
              onClick={handleExecuteReplace}
              disabled={!findWord.trim()}
              className="py-1 px-3 rounded-lg bg-[#25F4EE] hover:bg-[#25F4EE]/90 text-black font-bold text-xs cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              แทนที่ทั้งหมด
            </button>
          </div>
        </div>
      )}

      {/* Subtitle Rows List */}
      <div className="space-y-1">
        {filteredCues.map((cue, idx) => {
          const isSelected = selectedCaption?._uid === cue._uid;
          const isPlaying = playhead >= cue.start && playhead < cue.end;
          const isLast = idx === cuesList.length - 1;
          const isFirst = idx === 0;

          return (
            <div
              key={cue._uid}
              ref={(el) => (rowRefs.current[cue._uid] = el)}
              onClick={() => {
                onSelectCue?.(cue._uid);
                onSeek?.(cue.start);
              }}
              className={`flex items-center gap-1 p-1 rounded-xl border transition-all group cursor-pointer ${
                isSelected
                  ? 'border-[#25F4EE] bg-[#25F4EE]/15 shadow-md ring-1 ring-[#25F4EE]/40'
                  : isPlaying
                  ? 'border-emerald-500/60 bg-emerald-500/15 shadow-sm ring-1 ring-emerald-500/30'
                  : 'border-white/[0.06] bg-black/40 hover:border-white/[0.15] hover:bg-black/60'
              }`}
            >
              {/* Time Badge */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCue?.(cue._uid);
                  onSeek?.(cue.start);
                }}
                className={`px-1 py-1 rounded-lg text-xs font-mono font-bold cursor-pointer transition-colors flex-shrink-0 border ${
                  isPlaying
                    ? 'bg-emerald-500/30 text-emerald-300 border-emerald-500/50'
                    : 'bg-black/60 text-slate-400 border-white/[0.08] hover:text-[#25F4EE] hover:border-[#25F4EE]/40'
                }`}
                title={`ท่อนที่ ${idx + 1} · คลิกกระโดดไป ${formatShortTime(cue.start)}`}
              >
                {formatShortTime(cue.start)}
              </button>

              {/* Thai Text Input */}
              <div className="flex-1 min-w-0">
                <input
                  ref={(el) => (inputRefs.current[cue._uid] = el)}
                  type="text"
                  value={cue.text || ''}
                  onFocus={() => {
                    isTypingRef.current = true;
                    onSelectCue?.(cue._uid);
                    onSeek?.(cue.start);
                  }}
                  onBlur={() => { isTypingRef.current = false; }}
                  onChange={(e) => onCaptionChange?.(cue._uid, { text: e.target.value })}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectCue?.(cue._uid);
                    onSeek?.(cue.start);
                  }}
                  onKeyDown={(e) => handleKeyDown(e, cue, idx)}
                  placeholder="พิมพ์ข้อความ (Enter เพื่อแยกท่อน, Backspace เพื่อรวมท่อน)..."
                  className="w-full py-1 px-2 rounded-lg bg-black/40 border border-transparent focus:border-[#25F4EE] focus:bg-black/80 text-white text-xs placeholder-slate-600 focus:outline-none transition-colors cursor-text"
                />
                {(cue.translation !== undefined && cue.translation !== null) && (
                  <input
                    type="text"
                    value={cue.translation || ''}
                    onChange={(e) => onCaptionChange?.(cue._uid, { translation: e.target.value })}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCue?.(cue._uid);
                      onSeek?.(cue.start);
                    }}
                    placeholder="คำแปลภาษาอังกฤษ (English Translation)..."
                    className="w-full py-0.5 px-2 mt-0.5 rounded bg-black/20 border border-transparent focus:border-cyan-500/50 text-slate-300 text-[11px] focus:text-white placeholder-slate-600 focus:outline-none transition-colors"
                  />
                )}
              </div>

              {/* Quick SFX Selector */}
              <select
                value={cue.sfx || ''}
                onChange={(e) => onCaptionChange?.(cue._uid, { sfx: e.target.value || null })}
                onClick={(e) => e.stopPropagation()}
                className="py-1 px-1 rounded-lg bg-black/60 border border-white/[0.08] text-xs text-slate-400 focus:text-[#25F4EE] focus:outline-none cursor-pointer w-[46px] truncate flex-shrink-0"
                title="เสียงเอฟเฟกต์ (SFX)"
              >
                <option value="">SFX</option>
                {sfxList.map((s) => (
                  <option key={s.id} value={s.id} className="bg-[#080B11]">
                    {s.label_th || s.name}
                  </option>
                ))}
              </select>

              {/* Move Up / Down */}
              <div className="flex items-center opacity-60 group-hover:opacity-100 transition-opacity flex-shrink-0">
                {!isFirst && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReorderCues?.(idx, idx - 1);
                    }}
                    className="w-5 h-5 flex items-center justify-center rounded-md hover:bg-white/[0.1] text-slate-400 hover:text-white cursor-pointer"
                    title="เลื่อนท่อนนี้ขึ้น"
                  >
                    <ChevronUp className="w-3 h-3" />
                  </button>
                )}
                {!isLast && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReorderCues?.(idx, idx + 1);
                    }}
                    className="w-5 h-5 flex items-center justify-center rounded-md hover:bg-white/[0.1] text-slate-400 hover:text-white cursor-pointer"
                    title="เลื่อนท่อนนี้ลง"
                  >
                    <ChevronDown className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Split Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCursorSplit(cue);
                }}
                className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/[0.04] hover:bg-[#25F4EE]/20 text-slate-400 hover:text-[#25F4EE] border border-white/[0.06] transition-colors cursor-pointer flex-shrink-0"
                title="ตัดแบ่งท่อนคำบรรยาย (หรือกด Enter ในช่องพิมพ์)"
              >
                <Scissors className="w-3 h-3" />
              </button>

              {/* Merge with Next Button */}
              {!isLast && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onMergeCue?.(cue._uid);
                  }}
                  className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/[0.04] hover:bg-blue-500/20 text-slate-400 hover:text-blue-400 border border-white/[0.06] transition-colors cursor-pointer flex-shrink-0"
                  title="รวมกับท่อนถัดไป"
                >
                  <Link2 className="w-3 h-3" />
                </button>
              )}

              {/* Delete Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteCue?.(cue._uid);
                }}
                className="w-7 h-7 flex items-center justify-center rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 transition-colors cursor-pointer flex-shrink-0"
                title="ลบท่อนนี้ออก"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          );
        })}

        {filteredCues.length === 0 && (
          <div className="py-8 text-center text-xs text-slate-500 space-y-2">
            <p>ไม่พบรายการคำบรรยาย</p>
            <button
              type="button"
              onClick={() => onInsertCueAfter?.(null)}
              className="px-3 py-1.5 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold inline-flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>สร้างท่อนแรก</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
