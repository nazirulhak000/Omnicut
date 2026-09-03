import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  AlertTriangle, Film, MessageSquare, Settings2, Scissors,
  Trash2, Plus, Volume2, VolumeX, RotateCw, Play, Check, Search,
  Link2, Clock, Split, Sparkles, ArrowUp, ArrowDown,
  Replace, CheckCheck, RefreshCw, X, ChevronUp, ChevronDown
} from 'lucide-react';
import { TRANSITIONS, FADE_DURATION, MAX_TRANSITION_DURATION } from '../../lib/timelineMath';

const SPEEDS = [0.5, 1, 1.5, 2];

const POPULAR_SFX = [
  { id: 'boom', label: '💥 Boom' },
  { id: 'whoosh', label: '⚡ Whoosh' },
  { id: 'ding', label: '🔔 Ding' },
  { id: 'cash', label: '💰 Cash' },
  { id: 'pop', label: '🎈 Pop' },
];

function formatShortTime(sec) {
  if (sec == null || isNaN(sec)) return '00:00.0';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 10);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
}

function NumberInput(props) {
  return (
    <input
      type="number"
      {...props}
      className="w-full px-2.5 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-white text-xs font-mono focus:outline-none focus:border-[#25F4EE] shadow-inner"
    />
  );
}

export default function Inspector({
  selection,
  selectedSeg,
  selectedCaption,
  cuesList = [],
  playhead = 0,
  style = {},
  totalDuration = 0,
  audioDuration = 0,
  assets = {},
  hookBrand = '',
  onHookBrandChange,
  hookModel = '',
  onHookModelChange,
  hookLabel = '',
  onHookLabelChange,
  hookDuration = 3.0,
  onHookDurationChange,
  hookMotion = {},
  onHookMotionChange,
  hookMotionCatalog = null,
  hookMotionDefault = null,
  hookColors = {},
  onHookColorChange,
  showHookHeader = true,
  onToggleHookHeader,
  onAddTextAtPlayhead,
  onStyleChange,
  onClipChange,
  onCaptionChange,
  onSplitCue,
  onSplitCueAtPlayhead,
  onMergeCue,
  onMergeWithPrevious,
  onDeleteCue,
  onInsertCueAfter,
  onReorderCues,
  onBatchFindAndReplace,
  onBatchFormatClean,
  onSeek,
  onSelectCue,
}) {
  const [activeTab, setActiveTab] = useState('cues'); // 'cues' | 'clip' | 'style'
  const [searchQuery, setSearchQuery] = useState('');
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findWord, setFindWord] = useState('');
  const [replaceWord, setReplaceWord] = useState('');
  const [replaceMessage, setReplaceMessage] = useState(null);

  const inputRefs = useRef({});
  const rowRefs = useRef({});
  const isTypingRef = useRef(false);
  const gap = (audioDuration || 0) - totalDuration;

  const sfxList = assets?.sfx || [];

  // Filter cues by search query
  const filteredCues = cuesList.filter((cue) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (cue.text || '').toLowerCase().includes(q) || (cue.translation || '').toLowerCase().includes(q);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 🎬 PILLAR 3: LIVE KARAOKE PLAYHEAD AUTO-SCROLL SYNC
  // ═══════════════════════════════════════════════════════════════════════
  useEffect(() => {
    if (isTypingRef.current || activeTab !== 'cues') return;
    const activeCue = cuesList.find((c) => playhead >= c.start && playhead < c.end);
    if (activeCue && rowRefs.current[activeCue._uid]) {
      rowRefs.current[activeCue._uid].scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [playhead, cuesList, activeTab]);

  // ═══════════════════════════════════════════════════════════════════════
  // 🎯 PILLAR 1: WORD PROCESSOR ERGONOMICS (Enter, Backspace, Arrow keys)
  // ═══════════════════════════════════════════════════════════════════════
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
        // Focus previous input at join point
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
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-[#0C1019] text-slate-200">
      {/* ── Top View Switcher ── */}
      <div className="flex flex-shrink-0 border-b border-white/[0.08] bg-[#080B11] p-1.5 gap-1">
        <button
          type="button"
          onClick={() => setActiveTab('cues')}
          className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            activeTab === 'cues'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>คำบรรยาย ({cuesList.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('clip')}
          disabled={!selectedSeg}
          className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
            activeTab === 'clip'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Film className="w-3.5 h-3.5" />
          <span>คลิปที่เลือก</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('style')}
          className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            activeTab === 'style'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Settings2 className="w-3.5 h-3.5" />
          <span>ภาพรวม</span>
        </button>
      </div>

      <div className="p-2 sm:p-3 space-y-2.5 flex-1 overflow-y-auto">
        {/* ══════════════════════════════════════════════════════════
            MODE 1: SINGLE-ROW HIGH-VELOCITY SUBTITLE STRIP
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'cues' && (
          <div className="space-y-2.5">
            {/* 1. Header / Hook Banner (3 วิแรก) Control Card */}
            <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#E89274] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#D97757]" />
                  <span>Header พาดหัวบนจอ (3 วิแรก)</span>
                </span>
                <button
                  type="button"
                  onClick={onToggleHookHeader}
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border transition-all cursor-pointer ${
                    showHookHeader
                      ? 'bg-[#D97757]/20 border-[#D97757] text-[#E89274]'
                      : 'bg-white/[0.04] border-white/[0.1] text-slate-500 hover:text-white'
                  }`}
                >
                  {showHookHeader ? '✓ เปิดใช้งาน' : '✕ ซ่อนไว้'}
                </button>
              </div>

              {showHookHeader && (
                <div className="space-y-1.5 pt-0.5">
                  <input
                    type="text"
                    value={hookBrand || ''}
                    onChange={(e) => onHookBrandChange?.(e.target.value)}
                    placeholder="แบรนด์ เช่น Logitech"
                    className="w-full py-1.5 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-sm font-extrabold uppercase tracking-wide text-white focus:outline-none focus:border-[#D97757] placeholder-slate-500 shadow-inner"
                  />
                  <input
                    type="text"
                    value={hookModel || ''}
                    onChange={(e) => onHookModelChange?.(e.target.value)}
                    placeholder="รุ่น/โมเดล เช่น Wave Keys"
                    className="w-full py-1.5 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-bold text-[#E6C24A] focus:outline-none focus:border-[#D97757] placeholder-slate-500 shadow-inner"
                  />
                  <input
                    type="text"
                    value={hookLabel || ''}
                    onChange={(e) => onHookLabelChange?.(e.target.value)}
                    placeholder="หมวดสินค้าสั้นๆ เช่น คีย์บอร์ดไร้สาย"
                    className="w-full py-1 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-[11px] font-semibold text-slate-300 focus:outline-none focus:border-[#D97757] placeholder-slate-500 shadow-inner"
                  />
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                    <span>ระยะเวลาแสดงผล:</span>
                    <div className="flex items-center gap-1">
                      {[2.0, 3.0, 4.0].map((sec) => (
                        <button
                          key={sec}
                          type="button"
                          onClick={() => onHookDurationChange?.(sec)}
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono border transition-all cursor-pointer ${
                            Math.abs((hookDuration || 3.0) - sec) < 0.2
                              ? 'bg-[#D97757]/30 border-[#D97757] text-[#E89274]'
                              : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                        >
                          {sec}s
                        </button>
                      ))}
                      <input
                        type="number"
                        min="1.0"
                        max="8.0"
                        step="0.5"
                        value={hookDuration || 3.0}
                        onChange={(e) => onHookDurationChange?.(parseFloat(e.target.value) || 3.0)}
                        className="w-12 py-0.5 px-1 rounded bg-black/50 border border-white/[0.1] text-right text-[11px] font-mono text-white focus:outline-none focus:border-[#D97757]"
                      />
                      <span>วิ</span>
                    </div>
                  </div>
                  {/* Per-tier text colour. Empty means "renderer default"
                      (white wordmark / accent model / muted label), so a
                      brand with its own colour equity can set just the tier
                      it cares about and leave the rest alone. */}
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-[10px] font-bold text-slate-400">สีตัวอักษร</span>
                    {[
                      { tier: 'brand', label: 'แบรนด์', fallback: '#FFFFFF' },
                      { tier: 'model', label: 'รุ่น', fallback: style?.captionColor || '#FFE600' },
                      { tier: 'label', label: 'หมวด', fallback: '#E0E0E0' },
                    ].map(({ tier, label, fallback }) => (
                      <label key={tier} className="flex items-center gap-1 cursor-pointer" title={label}>
                        <input
                          type="color"
                          value={hookColors?.[tier] || fallback}
                          onChange={(e) => onHookColorChange?.(tier, e.target.value)}
                          className="h-5 w-5 cursor-pointer rounded border border-white/[0.15] bg-transparent p-0"
                        />
                        <span className="text-[10px] text-slate-400">{label}</span>
                      </label>
                    ))}
                  </div>

                  {/* Motion presets -- one pick per category, exactly like
                      CapCut's own In / Loop / Out text-animation tabs. The
                      options come from /api/hook-motion-presets so this list
                      can never drift from what the renderer can actually
                      draw; until it loads, only the stagger toggle shows. */}
                  <div className="space-y-1 pt-1">
                    {[
                      { cat: 'in', label: 'เข้า' },
                      { cat: 'loop', label: 'ค้าง' },
                      { cat: 'out', label: 'ออก' },
                      { cat: 'accent', label: 'ตกแต่ง' },
                    ].map(({ cat, label }) => {
                      const options = hookMotionCatalog?.[cat];
                      if (!options) return null;
                      return (
                        <div key={cat} className="flex items-center gap-1.5">
                          <span className="w-9 flex-shrink-0 text-[10px] font-bold text-slate-400">{label}</span>
                          <select
                            value={hookMotion?.[cat] ?? hookMotionDefault?.[cat] ?? 'none'}
                            onChange={(e) => onHookMotionChange?.(cat, e.target.value)}
                            className="flex-1 min-w-0 rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1 text-[11px] font-semibold text-white shadow-inner focus:border-[#D97757] focus:outline-none"
                          >
                            {Object.entries(options).map(([id, meta]) => (
                              <option key={id} value={id}>{meta.label_th}</option>
                            ))}
                          </select>
                        </div>
                      );
                    })}
                    {(() => {
                      const on = hookMotion?.stagger !== false;
                      return (
                        <button
                          type="button"
                          onClick={() => onHookMotionChange?.('stagger', !on)}
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border transition-all cursor-pointer ${
                            on
                              ? 'bg-[#D97757]/20 border-[#D97757] text-[#E89274]'
                              : 'bg-white/[0.04] border-white/[0.1] text-slate-500 hover:text-white'
                          }`}
                        >
                          {on ? '✓' : '✕'} ทยอยเข้าทีละบรรทัด
                        </button>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>

            {/* 2. Caption Sizing & Position Quick Bar */}
            <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300">ขนาดและตำแหน่งคำบรรยาย</span>
                <span className="font-mono text-xs font-bold text-[#25F4EE]">
                  {Math.round((style?.captionScale ?? 1) * 100)}%
                </span>
              </div>
              <div className="flex items-center gap-1">
                {[
                  { s: 1.0, label: '100% มาตรฐาน' },
                  { s: 0.85, label: '85% เล็ก' },
                  { s: 0.7, label: '70% ย่อ' },
                  { s: 1.25, label: '125% ใหญ่' },
                ].map(({ s, label }) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onStyleChange?.({ captionScale: s })}
                    className={`flex-1 py-1 rounded-lg text-[10px] sm:text-[11px] font-bold border transition-all cursor-pointer ${
                      Math.abs((style?.captionScale ?? 1) - s) < 0.05
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE] shadow-sm shadow-[#25F4EE]/20'
                        : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <input
                type="range"
                min="0.5"
                max="1.6"
                step="0.05"
                value={style?.captionScale ?? 1}
                onChange={(e) => onStyleChange?.({ captionScale: parseFloat(e.target.value) })}
                className="w-full accent-[#25F4EE]"
              />
              <div className="flex items-center justify-between pt-1 border-t border-white/[0.06]">
                <span className="text-[11px] text-slate-400">ตำแหน่งบนจอ:</span>
                <div className="flex items-center gap-1">
                  {[
                    ['bottom', 'ล่าง'],
                    ['middle', 'กลาง'],
                    ['top', 'บน'],
                  ].map(([pos, lbl]) => (
                    <button
                      key={pos}
                      type="button"
                      onClick={() => onStyleChange?.({ captionPosition: pos })}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-all cursor-pointer ${
                        (style?.captionPosition || 'bottom') === pos
                          ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                          : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                      }`}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Header: Quick Search, Find & Replace Toggle, Format Clean, Add Cue */}
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

              {/* Format Clean (จัดวรรคตอนอัตโนมัติ) */}
              <button
                type="button"
                onClick={() => onBatchFormatClean?.()}
                className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-amber-300 cursor-pointer transition-colors"
                title="จัดระเบียบวรรคตอนภาษาไทยและลบช่องว่างส่วนเกิน"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              </button>

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
                <div className="flex items-center justify-between text-sm font-bold text-[#25F4EE]">
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
                    <span className="text-sm text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCheck className="w-3 h-3" />{replaceMessage}
                    </span>
                  ) : <span className="text-sm text-slate-500">กด Enter หรือกดปุ่มแทนที่</span>}
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

            {/* ══════════════════════════════════════════════════════════
                SUBTITLE STRIP ROWS (1 Row per Caption)
               ══════════════════════════════════════════════════════════ */}
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
                    {/* 1. Time Badge (Click to seek video) -- just the time;
                        the row order is already visible, an index number was
                        chrome the line didn't need. */}
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

                    {/* 2. Main Thai Text Input -- the whole point of this
                        panel, so it gets whatever the row has left. It never
                        wraps; drag the panel's left edge wider (or Enter to
                        split into a shorter line) to see more at once. */}
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


                    {/* 3. Quick SFX Selector */}
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

                    {/* 4. Move Up / Down (Reorder Cues) */}
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

                    {/* 5. Split Button (✂️) */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCursorSplit(cue);
                      }}
                      className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/[0.04] hover:bg-[#25F4EE]/20 text-slate-400 hover:text-[#25F4EE] border border-white/[0.06] transition-colors cursor-pointer flex-shrink-0"
                      title="✂️ ตัดแบ่งท่อนคำบรรยาย (หรือกด Enter ในช่องพิมพ์)"
                    >
                      <Scissors className="w-3 h-3" />
                    </button>

                    {/* 6. Merge with Next Button (🔗) */}
                    {!isLast && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onMergeCue?.(cue._uid);
                        }}
                        className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/[0.04] hover:bg-blue-500/20 text-slate-400 hover:text-blue-400 border border-white/[0.06] transition-colors cursor-pointer flex-shrink-0"
                        title="🔗 รวมกับท่อนถัดไป"
                      >
                        <Link2 className="w-3 h-3" />
                      </button>
                    )}

                    {/* 7. Delete Button (🗑️) */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCue?.(cue._uid);
                      }}
                      className="w-7 h-7 flex items-center justify-center rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 transition-colors cursor-pointer flex-shrink-0"
                      title="🗑️ ลบท่อนนี้ออก"
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
        )}

        {/* ══════════════════════════════════════════════════════════
            MODE 2: SELECTED CLIP PROPERTIES
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'clip' && selectedSeg && (
          <div className="space-y-3">
            <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold text-white">
                <span>คลิปที่ {selectedSeg.index + 1}</span>
                <span className="font-mono text-[#25F4EE]">{selectedSeg.dur.toFixed(2)}s</span>
              </div>
              <p className="truncate text-xs text-slate-400 font-mono" title={selectedSeg.clip.source_path}>
                {(selectedSeg.clip.source_path || '').split(/[\\/]/).pop()}
              </p>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <span className="block text-sm text-slate-400 mb-1">Trim เข้า (วิ)</span>
                  <NumberInput
                    step="0.1"
                    min="0"
                    value={selectedSeg.clip.trim_start}
                    onChange={(e) => onClipChange?.({ trim_start: Math.max(0, parseFloat(e.target.value) || 0) })}
                  />
                </div>
                <div>
                  <span className="block text-sm text-slate-400 mb-1">Trim ออก (วิ)</span>
                  <NumberInput
                    step="0.1"
                    min="0"
                    placeholder="สุดคลิป"
                    value={selectedSeg.clip.trim_end ?? ''}
                    onChange={(e) => onClipChange?.({
                      trim_end: e.target.value === '' ? null : parseFloat(e.target.value),
                    })}
                  />
                </div>
              </div>

              <div>
                <span className="block text-sm text-slate-400 mb-1">ความเร็ว (Speed)</span>
                <div className="grid grid-cols-4 gap-1">
                  {SPEEDS.map((s) => {
                    const active = (selectedSeg.clip.speed || 1) === s;
                    return (
                      <button
                        key={s}
                        type="button"
                        onClick={() => onClipChange?.({ speed: s === 1 ? undefined : s })}
                        className={`py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                          active
                            ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                            : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                        }`}
                      >
                        {s}x
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Rotate 0 / 90 / 180 / 270 */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400 flex items-center gap-1.5">
                    <RotateCw className="h-3.5 w-3.5 text-[#25F4EE]" />
                    หมุนภาพ (Rotate)
                  </span>
                  {selectedSeg.clip.rotation ? (
                    <button
                      type="button"
                      onClick={() => onClipChange?.({ rotation: undefined })}
                      className="text-xs text-[#E89274] hover:underline cursor-pointer"
                    >
                      รีเซ็ต 0°
                    </button>
                  ) : null}
                </div>
                <div className="grid grid-cols-4 gap-1">
                  {[0, 90, 180, 270].map((deg) => {
                    const active = (selectedSeg.clip.rotation || 0) === deg;
                    return (
                      <button
                        key={deg}
                        type="button"
                        onClick={() => onClipChange?.({ rotation: deg === 0 ? undefined : deg })}
                        className={`py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                          active
                            ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                            : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                        }`}
                      >
                        {deg}°
                      </button>
                    );
                  })}
                </div>
              </div>

              <button
                type="button"
                onClick={() => onClipChange?.({ mirror: !selectedSeg.clip.mirror })}
                className={`w-full py-1.5 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                  selectedSeg.clip.mirror
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                    : 'bg-black/40 border-white/[0.08] text-slate-300 hover:text-white'
                }`}
              >
                {selectedSeg.clip.mirror ? '✓ กลับด้านซ้าย-ขวาอยู่' : 'กลับด้านซ้าย-ขวา (Mirror)'}
              </button>

              {/* Original Audio Volume (0 - 100%) */}
              <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400 flex items-center gap-1.5">
                    {(selectedSeg.clip.volume || 0) > 0 ? (
                      <Volume2 className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <VolumeX className="h-3.5 w-3.5 text-slate-500" />
                    )}
                    เสียงคลิปต้นฉบับ (Original Audio)
                  </span>
                  <button
                    type="button"
                    onClick={() => onClipChange?.({ volume: (selectedSeg.clip.volume || 0) > 0 ? 0 : 1.0 })}
                    className="text-xs font-mono font-bold text-[#25F4EE] hover:underline cursor-pointer"
                  >
                    {Math.round((selectedSeg.clip.volume || 0) * 100)}%
                  </button>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={selectedSeg.clip.volume || 0}
                  onChange={(e) => onClipChange?.({ volume: parseFloat(e.target.value) })}
                  className="w-full accent-[#25F4EE]"
                />
                <p className="text-[11px] text-slate-500">
                  {(selectedSeg.clip.volume || 0) === 0
                    ? 'ปิดเสียงอยู่ (Muted) — แนะนำสำหรับคลิปที่มีเสียง AI พากย์'
                    : 'เปิดเสียงบรรยากาศคลอ — เหมาะกับคลิปแกะกล่อง Unboxing / ASMR'}
                </p>
              </div>

              {/* Framing. Mirrors frame_geometry() in video_editor.py: zoom
                  1-3x, pan -1..1 across whatever room the zoom leaves. */}
              {(() => {
                const zoom = selectedSeg.clip.zoom ?? 1;
                const panning = zoom > 1.001;
                const FIELDS = [
                  { key: 'pan_x', label: 'เลื่อนซ้าย-ขวา' },
                  { key: 'pan_y', label: 'เลื่อนขึ้น-ลง' },
                ];
                return (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">กรอบภาพ</span>
                      <button
                        type="button"
                        disabled={zoom === 1 && !selectedSeg.clip.pan_x && !selectedSeg.clip.pan_y}
                        onClick={() => onClipChange?.({ zoom: undefined, pan_x: undefined, pan_y: undefined })}
                        className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                      >
                        รีเซ็ต
                      </button>
                    </div>
                    <label className="block">
                      <span className="mb-0.5 flex justify-between text-sm text-slate-400">
                        <span>ซูม</span>
                        <span className="font-mono text-slate-300">{zoom.toFixed(2)}x</span>
                      </span>
                      <input
                        type="range" min={1} max={3} step={0.05} value={zoom}
                        onChange={(e) => onClipChange?.({ zoom: parseFloat(e.target.value) })}
                        className="w-full accent-[#D97757]"
                      />
                    </label>
                    {FIELDS.map((f) => (
                      <label key={f.key} className={`block ${panning ? '' : 'opacity-40'}`}>
                        <span className="mb-0.5 flex justify-between text-sm text-slate-400">
                          <span>{f.label}</span>
                          <span className="font-mono text-slate-300">{(selectedSeg.clip[f.key] ?? 0).toFixed(2)}</span>
                        </span>
                        <input
                          type="range" min={-1} max={1} step={0.05}
                          value={selectedSeg.clip[f.key] ?? 0}
                          disabled={!panning}
                          onChange={(e) => onClipChange?.({ [f.key]: parseFloat(e.target.value) })}
                          className="w-full accent-[#D97757] disabled:cursor-not-allowed"
                        />
                      </label>
                    ))}
                    {!panning && (
                      <p className="text-xs text-slate-500">ซูมเกิน 1x ก่อนถึงจะเลื่อนกรอบได้</p>
                    )}
                  </div>
                );
              })()}

              {/* Per-clip colour. Ranges mirror EQ_LIMITS in video_editor.py. */}
              {(() => {
                const COLOR_FIELDS = [
                  { key: 'brightness', label: 'ความสว่าง', min: -0.3, max: 0.3, step: 0.02, def: 0 },
                  { key: 'contrast', label: 'คอนทราสต์', min: 0.5, max: 2, step: 0.05, def: 1 },
                  { key: 'saturation', label: 'ความสด', min: 0, max: 3, step: 0.05, def: 1 },
                ];
                const touched = COLOR_FIELDS.some(
                  (f) => (selectedSeg.clip[f.key] ?? f.def) !== f.def,
                );
                return (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">สีของคลิปนี้</span>
                      <button
                        type="button"
                        disabled={!touched}
                        onClick={() => onClipChange?.({ brightness: undefined, contrast: undefined, saturation: undefined })}
                        className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                      >
                        รีเซ็ต
                      </button>
                    </div>
                    {COLOR_FIELDS.map((f) => {
                      const value = selectedSeg.clip[f.key] ?? f.def;
                      return (
                        <label key={f.key} className="block">
                          <span className="mb-0.5 flex justify-between text-sm text-slate-400">
                            <span>{f.label}</span>
                            <span className="font-mono text-slate-300">{value.toFixed(2)}</span>
                          </span>
                          <input
                            type="range"
                            min={f.min}
                            max={f.max}
                            step={f.step}
                            value={value}
                            onChange={(e) => onClipChange?.({ [f.key]: parseFloat(e.target.value) })}
                            className="w-full accent-[#D97757]"
                          />
                        </label>
                      );
                    })}
                  </div>
                );
              })()}

              {/* Transitions: the first clip has no boundary before it. */}
              {selectedSeg.index > 0 && (() => {
                const kind = selectedSeg.clip.transition_in || 'cut';
                const dur = selectedSeg.clip.transition_duration ?? FADE_DURATION;
                const isCut = kind === 'cut';
                return (
                  <div className="space-y-1.5">
                    <span className="block text-sm text-slate-400">รอยต่อกับคลิปก่อนหน้า</span>
                    <button
                      type="button"
                      onClick={() => onClipChange?.({ transition_in: 'cut' })}
                      className={`w-full py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                        isCut
                          ? 'bg-[#D97757]/20 border-[#D97757] text-[#E89274]'
                          : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                      }`}
                    >
                      ตัดตรง (ไม่มีรอยต่อ)
                    </button>
                    <div className="grid grid-cols-2 gap-1">
                      {TRANSITIONS.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => onClipChange?.({
                            transition_in: t.id,
                            transition_duration: dur,
                          })}
                          title={t.id}
                          className={`py-1 rounded-lg text-sm font-bold transition-all cursor-pointer border ${
                            kind === t.id
                              ? 'bg-[#D97757]/20 border-[#D97757] text-[#E89274]'
                              : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                    <label className={`block pt-1 ${isCut ? 'opacity-40' : ''}`}>
                      <span className="mb-1 flex justify-between text-sm text-slate-400">
                        <span>ความยาวรอยต่อ</span>
                        <span className="font-mono text-slate-300">{dur.toFixed(1)}s</span>
                      </span>
                      <input
                        type="range"
                        min={0.1}
                        max={MAX_TRANSITION_DURATION}
                        step={0.1}
                        value={dur}
                        disabled={isCut}
                        onChange={(e) => onClipChange?.({ transition_duration: parseFloat(e.target.value) })}
                        className="w-full accent-[#D97757] disabled:cursor-not-allowed"
                      />
                    </label>
                    <p className="text-xs leading-relaxed text-slate-500">
                      พรีวิวแสดงรอยต่อทุกแบบเป็นการจางเข้าหากัน — ลายจริง (ปาด/เลื่อน/วงกลม) เห็นได้หลังกด Apply
                    </p>
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════
            MODE 3: PROJECT STYLE OVERVIEW
           ══════════════════════════════════════════════════════════ */}
        {activeTab === 'style' && (
          <div className="space-y-3">
            <div className="space-y-2 rounded-2xl bg-black/40 border border-white/[0.08] p-3 text-xs">
              <div className="flex justify-between text-slate-300">
                <span>ฟอนต์ซับไตเติล:</span>
                <span className="font-bold text-[#25F4EE]">{style.fontName || 'IBMPlex'}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>เพลงประกอบ:</span>
                <span className="font-mono text-slate-200">{style.bgmName || 'เสียงหลักของช่อง'}</span>
              </div>
              <div className="flex justify-between text-slate-300 border-t border-white/[0.06] pt-2">
                <span>ความยาววิดีโอรวม:</span>
                <span className="font-mono font-bold text-white">{totalDuration.toFixed(2)}s</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>ความยาวเสียงพากย์:</span>
                <span className="font-mono font-bold text-white">{audioDuration.toFixed(2)}s</span>
              </div>
            </div>

            {gap > 0.5 && (
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
                <p>
                  วิดีโอสั้นกว่าเสียงพากย์ {gap.toFixed(1)} วิ — ช่วงท้ายจะค้างภาพเฟรมสุดท้ายไว้จนเสียงจบ
                  เพิ่มคลิปหรือลดความเร็วถ้าไม่อยากให้ภาพนิ่ง
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
