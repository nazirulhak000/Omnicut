import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  AlertTriangle, Film, MessageSquare, Settings2, Scissors,
  Trash2, Plus, Volume2, VolumeX, RotateCw, Play, Check, Search,
  Link2, Clock, Split, Sparkles, ArrowUp, ArrowDown,
  Replace, CheckCheck, RefreshCw, X, ChevronUp, ChevronDown, Type,
  SlidersHorizontal, AlignLeft, AlignCenter, AlignRight, Bold, Italic, Underline,
  Music, Layers, Palette, Target, Globe, RotateCcw
} from 'lucide-react';
import { TransitionIcon } from '../../lib/transitionIcons';
import { TRANSITIONS, FADE_DURATION, MAX_TRANSITION_DURATION } from '../../lib/timelineMath';
import { resolveHookStyle } from '../../lib/hookStyles';

// The three lines of the banner, in the order they are drawn.
const HOOK_TIERS = [
  { tier: 'brand', label: 'แบรนด์' },
  { tier: 'model', label: 'รุ่น' },
  { tier: 'label', label: 'หมวด' },
];

const SPEEDS = [0.5, 1, 1.5, 2];

const POPULAR_SFX = [
  { id: 'boom', label: 'Boom' },
  { id: 'whoosh', label: 'Whoosh' },
  { id: 'ding', label: 'Ding' },
  { id: 'cash', label: 'Cash' },
  { id: 'pop', label: 'Pop' },
];

const PRESET_STYLES = [
  {
    id: 'classic',
    name: 'ขาวคลาสสิก',
    color: '#FFFFFF',
    desc: 'ขาวขอบดำ คมชัด อ่านง่าย',
  },
  {
    id: 'tiktok',
    name: 'เหลือง TikTok',
    color: '#FFE600',
    desc: 'เหลืองนีออน ไวรัลสะดุดตา',
  },
  {
    id: 'warning',
    name: 'แดงเตือนภัย',
    color: '#FE2C55',
    desc: 'แดงเข้มข้น เตือนใจ ดึงสายตา',
  },
  {
    id: 'cyan',
    name: 'ฟ้านีออน Glow',
    color: '#25F4EE',
    desc: 'ฟ้าไซเบอร์ ล้ำยุค โดดเด่น',
  },
  {
    id: 'orange',
    name: 'ส้มพรีเมียม',
    color: '#FF7A00',
    desc: 'ส้มสดใหม่ ไฮไลต์จุดขาย',
  },
];

const FONT_OPTIONS = [
  { id: 'Kanit', name: 'Kanit (คานิท - ค่ามาตรฐาน TikTok)' },
  { id: 'IBMPlex', name: 'IBM Plex Sans Thai (โมเดิร์น คมชัด)' },
  { id: 'Prompt', name: 'Prompt (พร้อมท์ - เรียบหรู ทันสมัย)' },
  { id: 'NotoSansThai', name: 'Noto Sans Thai (มาตรฐานทางการ)' },
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
  hookStyle = null,
  hookTemplates = null,
  onHookTemplate,
  onHookStyleChange,
  onHookStyleReset,
  fonts = [],
  onHookColorChange,
  showHookHeader = true,
  onToggleHookHeader,
  onAddTextAtPlayhead,
  onStyleChange,
  onClipChange,
  onCaptionChange,
  applyToAll = true,
  onToggleApplyToAll = null,
  onPatchAllCaptions = null,
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
  textOverlays = [],
  onAddTextOverlay,
  onUpdateTextOverlay,
  onDeleteTextOverlay,
  onSelectTextOverlay,
  onSelectHook,
  onSelect,
  trackMix = { mute: {}, solo: {} },
  onTrackMix,
}) {
  const resolvedHook = resolveHookStyle(hookStyle?.template, hookStyle, hookColors);
  const hasHookOverrides = Boolean(
    hookStyle?.font || Object.keys(hookStyle?.tiers || {}).length,
  );

  // Top tabs: 'properties' (Contextual Inspector) | 'cues' (Subtitle transcript) | 'overview' (Project settings)
  const [activeTab, setActiveTab] = useState('properties');
  const [localApplyToAll, setLocalApplyToAll] = useState(true);
  const effectiveApplyToAll = onToggleApplyToAll ? applyToAll : localApplyToAll;
  const toggleApplyToAll = onToggleApplyToAll || setLocalApplyToAll;
  const [textPattern, setTextPattern] = useState({ bold: true, italic: false, underline: false });
  const [textAlign, setTextAlign] = useState('center');

  const [searchQuery, setSearchQuery] = useState('');
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findWord, setFindWord] = useState('');
  const [replaceWord, setReplaceWord] = useState('');
  const [replaceMessage, setReplaceMessage] = useState(null);

  const inputRefs = useRef({});
  const rowRefs = useRef({});
  const hookHeaderCardRef = useRef(null);
  const textOverlayCardRef = useRef(null);
  const hookBrandInputRef = useRef(null);
  const isTypingRef = useRef(false);
  const gap = (audioDuration || 0) - totalDuration;

  const sfxList = assets?.sfx || [];

  const selectedTextOverlay = selection?.type === 'text_overlay'
    ? textOverlays.find((item) => item.id === selection.id)
    : null;

  // Track selection transitions to contextually open the Properties tab
  const prevSelectionTypeRef = useRef(selection?.type);
  const prevSelectionIdRef = useRef(selection?.id);

  useEffect(() => {
    const typeChanged = selection?.type !== prevSelectionTypeRef.current;
    const idChanged = selection?.id !== prevSelectionIdRef.current;

    // Switch to properties tab when a new element is selected from timeline
    // (except when navigating inside cues tab with keyboard/focus)
    if (selection && (typeChanged || (idChanged && activeTab !== 'cues'))) {
      setActiveTab('properties');
    }

    if (selection?.type === 'hook') {
      setTimeout(() => {
        hookHeaderCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        hookBrandInputRef.current?.focus();
      }, 50);
    }

    prevSelectionTypeRef.current = selection?.type;
    prevSelectionIdRef.current = selection?.id;
  }, [selection, activeTab]);

  // Filter cues by search query
  const filteredCues = cuesList.filter((cue) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (cue.text || '').toLowerCase().includes(q) || (cue.translation || '').toLowerCase().includes(q);
  });

  // Karaoke playhead auto-scroll sync (only active in cues tab)
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

  // ─────────────────────────────────────────────────────────────────────────────
  // Text Property Handlers (CapCut Style: Scoped vs Global)
  // ─────────────────────────────────────────────────────────────────────────────
  const isOverlaySelected = Boolean(selectedTextOverlay);
  const isCaptionSelected = Boolean(selectedCaption);
  const isTextSelected = isOverlaySelected || isCaptionSelected;

  const currentText = isOverlaySelected
    ? (selectedTextOverlay.text || '')
    : isCaptionSelected
    ? (selectedCaption.text || '')
    : '';

  const currentTranslation = isCaptionSelected ? selectedCaption.translation : null;

  const currentFont = isOverlaySelected
    ? (selectedTextOverlay.fontName || style?.fontName || 'Kanit')
    : isCaptionSelected
    ? (selectedCaption.fontName || style?.fontName || 'Kanit')
    : (style?.fontName || 'Kanit');

  const currentScale = isOverlaySelected
    ? (selectedTextOverlay.scale ?? 1.0)
    : isCaptionSelected
    ? (selectedCaption.scale ?? style?.captionScale ?? 1.0)
    : (style?.captionScale ?? 1.0);

  const currentColor = isOverlaySelected
    ? (selectedTextOverlay.color || '#FFE600')
    : isCaptionSelected
    ? (selectedCaption.color || style?.captionColor || '#FFFFFF')
    : (style?.captionColor || '#FFFFFF');

  const currentPosition = isOverlaySelected
    ? (selectedTextOverlay.position || 'middle')
    : isCaptionSelected
    ? (selectedCaption.position || style?.captionPosition || 'bottom')
    : (style?.captionPosition || 'bottom');

  const handleFontChange = (fontName) => {
    if (isOverlaySelected) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, { fontName });
    } else if (isCaptionSelected) {
      if (effectiveApplyToAll) {
        onStyleChange?.({ fontName });
        onPatchAllCaptions?.({ fontName: null });
      } else {
        onCaptionChange?.(selectedCaption._uid, { fontName });
      }
    } else {
      onStyleChange?.({ fontName });
    }
  };

  const handleScaleChange = (scale) => {
    const clamped = Math.max(0.4, Math.min(2.2, parseFloat(scale) || 1.0));
    if (isOverlaySelected) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, { scale: clamped });
    } else if (isCaptionSelected) {
      if (effectiveApplyToAll) {
        onStyleChange?.({ captionScale: clamped });
        onPatchAllCaptions?.({ scale: null });
      } else {
        onCaptionChange?.(selectedCaption._uid, { scale: clamped });
      }
    } else {
      onStyleChange?.({ captionScale: clamped });
    }
  };

  const handleColorChange = (color) => {
    if (isOverlaySelected) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, { color });
    } else if (isCaptionSelected) {
      if (effectiveApplyToAll) {
        onStyleChange?.({ captionColor: color });
        onPatchAllCaptions?.({ color: null });
      } else {
        onCaptionChange?.(selectedCaption._uid, { color });
      }
    } else {
      onStyleChange?.({ captionColor: color });
    }
  };

  const handlePositionChange = (position) => {
    if (isOverlaySelected) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, { position, x: null, y: null });
    } else if (isCaptionSelected) {
      if (effectiveApplyToAll) {
        onStyleChange?.({ captionPosition: position, captionX: 0.5 });
        onPatchAllCaptions?.({ position: null, x: null, y: null });
      } else {
        onCaptionChange?.(selectedCaption._uid, { position, x: null, y: null });
      }
    } else {
      onStyleChange?.({ captionPosition: position });
    }
  };

  const handleResetFormat = () => {
    if (isOverlaySelected && selectedTextOverlay) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, {
        scale: 1.0,
        x: 0.5,
        y: 0.5,
        fontName: 'Kanit',
        color: '#FFE600',
        position: 'middle',
      });
    } else if (isCaptionSelected && selectedCaption) {
      if (effectiveApplyToAll) {
        onStyleChange?.({
          captionScale: 1.0,
          fontName: 'Kanit',
          captionColor: '#FFFFFF',
          captionPosition: 'bottom',
          captionX: 0.5,
        });
        onPatchAllCaptions?.({
          scale: null,
          x: null,
          y: null,
          fontName: null,
          color: null,
          position: null,
        });
      } else {
        onCaptionChange?.(selectedCaption._uid, {
          scale: null,
          x: null,
          y: null,
          fontName: null,
          color: null,
          position: null,
        });
      }
      setTextPattern({ bold: true, italic: false, underline: false });
      setTextAlign('center');
    }
  };

  const handleApplyPreset = (preset) => {
    handleColorChange(preset.color);
  };

  const handleTextContentChange = (val) => {
    if (isOverlaySelected) {
      onUpdateTextOverlay?.(selectedTextOverlay.id, { text: val });
    } else if (isCaptionSelected) {
      onCaptionChange?.(selectedCaption._uid, { text: val });
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-[#0C1019] text-slate-200">
      {/* ═════════════════════════════════════════════════════════════════════
          TOP VIEW SWITCHER (3 Pro Tabs: คุณสมบัติ | บทพูด | ภาพรวม)
         ═════════════════════════════════════════════════════════════════════ */}
      <div className="flex flex-shrink-0 border-b border-white/[0.08] bg-[#080B11] p-1.5 gap-1">
        <button
          type="button"
          onClick={() => setActiveTab('properties')}
          className={`flex-1 py-1.5 px-2 rounded-xl text-[11px] sm:text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            activeTab === 'properties'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white border border-transparent'
          }`}
          title="ปรับแต่งคุณสมบัติของชิ้นส่วนที่กำลังเลือกบนไทม์ไลน์"
        >
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span>คุณสมบัติ</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('cues')}
          className={`flex-1 py-1.5 px-2 rounded-xl text-[11px] sm:text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            activeTab === 'cues'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white border border-transparent'
          }`}
          title="ตารางบทพูดและคำบรรยายทั้งหมด (สไตล์ Word Processor)"
        >
          <MessageSquare className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span>บทพูด ({cuesList.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`flex-1 py-1.5 px-2 rounded-xl text-[11px] sm:text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            activeTab === 'overview'
              ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
              : 'text-slate-400 hover:text-white border border-transparent'
          }`}
          title="ภาพรวมโปรเจกต์ (LUT สี, เพลง BGM รวม, ป้ายสติกเกอร์)"
        >
          <Settings2 className="w-3.5 h-3.5" />
          <span>ภาพรวม</span>
        </button>
      </div>

      <div className="p-2 sm:p-3 space-y-3 flex-1 overflow-y-auto">
        {/* ═════════════════════════════════════════════════════════════════════
            TAB 1: CONTEXTUAL PROPERTIES INSPECTOR (สลับตามชิ้นส่วนที่เลือก)
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'properties' && (
          <div className="space-y-3">
            {/* Quick Switcher Chips when text/captions exist */}
            <div className="flex items-center gap-1 pb-1 overflow-x-auto no-scrollbar">
              <button
                type="button"
                onClick={() => {
                  const firstCue = cuesList[0];
                  if (firstCue) onSelectCue?.(firstCue._uid);
                }}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border ${
                  isCaptionSelected
                    ? 'bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                <Type className="w-3 h-3" />
                <span>คำบรรยาย</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (textOverlays.length > 0) {
                    onSelectTextOverlay?.(textOverlays[0].id);
                  } else {
                    onAddTextOverlay?.();
                  }
                }}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border ${
                  isOverlaySelected
                    ? 'bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                <Sparkles className="w-3 h-3" />
                <span>ข้อความเสริม ({textOverlays.length})</span>
              </button>

              <button
                type="button"
                onClick={() => onSelectHook ? onSelectHook() : onSelect?.({ type: 'hook' })}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border ${
                  selection?.type === 'hook'
                    ? 'bg-[#E6C24A]/20 border-[#E6C24A] text-[#E6C24A]'
                    : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                <span>ฮุค 3 วิ</span>
              </button>

              {selectedSeg && (
                <button
                  type="button"
                  onClick={() => onSelect?.({ type: 'clip', id: selectedSeg.clip.id })}
                  className="px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE]"
                >
                  <Film className="w-3 h-3" />
                  <span>คลิปที่ {selectedSeg.index + 1}</span>
                </button>
              )}
            </div>

            {/* ──────────────────────────────────────────────────────────
                SUB-VIEW A: TEXT / SUBTITLE / OVERLAY PROPERTIES (CapCut Look)
               ────────────────────────────────────────────────────────── */}
            {isTextSelected ? (
              <div className="space-y-3">
                {/* Header Context Card */}
                <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <Type className="w-4 h-4 text-[#25F4EE]" />
                      {isOverlaySelected ? 'ข้อความเสริมบนจอ' : 'คุณสมบัติคำบรรยาย'}
                    </span>
                    {isCaptionSelected && selectedCaption && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 border border-white/[0.08]">
                        {formatShortTime(selectedCaption.start)} - {formatShortTime(selectedCaption.end)}
                      </span>
                    )}
                  </div>

                  {isOverlaySelected && selectedTextOverlay && (
                    <button
                      type="button"
                      onClick={() => onDeleteTextOverlay?.(selectedTextOverlay.id)}
                      className="text-rose-400 hover:text-rose-300 text-[11px] font-bold flex items-center gap-1 px-2 py-0.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 cursor-pointer transition-colors"
                      title="ลบข้อความเสริมนี้"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>ลบ</span>
                    </button>
                  )}
                </div>

                {/* Subtitle Scope Selector & Reset Button (CapCut Style) */}
                {isCaptionSelected && (
                  <div className="p-2 rounded-2xl bg-black/50 border border-white/[0.08] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-400">ขอบเขตการปรับแต่ง:</span>
                      <button
                        type="button"
                        onClick={handleResetFormat}
                        className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 transition-all cursor-pointer"
                        title="คืนค่าขนาด 100%, ฟอนต์ Kanit, สีขาว และตำแหน่งกึ่งกลางล่าง"
                      >
                        <RotateCcw className="w-3 h-3 text-slate-400" />
                        <span>รีเซ็ตค่าเริ่มต้น</span>
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-black/60 border border-white/[0.06]">
                      <button
                        type="button"
                        onClick={() => toggleApplyToAll(false)}
                        className={`py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                          !effectiveApplyToAll
                            ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                            : 'text-slate-400 hover:text-white border border-transparent'
                        }`}
                      >
                        <Target className="w-3.5 h-3.5" />
                        <span>ปรับเฉพาะกล่องนี้</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleApplyToAll(true)}
                        className={`py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                          effectiveApplyToAll
                            ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                            : 'text-slate-400 hover:text-white border border-transparent'
                        }`}
                      >
                        <Globe className="w-3.5 h-3.5" />
                        <span>ปรับทั้งแผง</span>
                      </button>
                    </div>
                  </div>
                )}

                {isOverlaySelected && (
                  <div className="flex items-center justify-end">
                    <button
                      type="button"
                      onClick={handleResetFormat}
                      className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 transition-all cursor-pointer"
                      title="คืนค่าตำแหน่งและขนาดเริ่มต้น"
                    >
                      <RotateCcw className="w-3 h-3 text-slate-400" />
                      <span>รีเซ็ตค่าเริ่มต้น</span>
                    </button>
                  </div>
                )}

                {/* Textarea Content Box */}
                <div className="space-y-1.5">
                  <textarea
                    rows={2}
                    value={currentText}
                    onChange={(e) => handleTextContentChange(e.target.value)}
                    placeholder="พิมพ์ข้อความที่นี่..."
                    className="w-full px-3 py-2 rounded-xl bg-black/60 border border-white/[0.1] text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE] shadow-inner resize-none font-medium leading-relaxed"
                  />
                  {currentTranslation !== null && currentTranslation !== undefined && (
                    <div className="space-y-1 pt-1">
                      <span className="text-[11px] text-slate-400 font-medium">คำแปลภาษาอังกฤษ (English Subtitle):</span>
                      <input
                        type="text"
                        value={currentTranslation || ''}
                        onChange={(e) => onCaptionChange?.(selectedCaption._uid, { translation: e.target.value })}
                        placeholder="English translation..."
                        className="w-full px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/[0.08] text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]"
                      />
                    </div>
                  )}
                </div>

                {/* Timing Fine-tune for Text Overlay */}
                {isOverlaySelected && selectedTextOverlay && (
                  <div className="grid grid-cols-2 gap-2 text-xs p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
                    <div className="space-y-1">
                      <span className="text-slate-400">เริ่ม (วินาที):</span>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={selectedTextOverlay.start ?? 0}
                        onChange={(e) => onUpdateTextOverlay?.(selectedTextOverlay.id, { start: Math.max(0, parseFloat(e.target.value) || 0) })}
                        className="w-full px-2.5 py-1 rounded-lg bg-black/60 border border-white/[0.1] text-xs font-mono text-white focus:outline-none focus:border-[#25F4EE]"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-slate-400">สิ้นสุด (วินาที):</span>
                      <input
                        type="number"
                        step="0.1"
                        min="0.1"
                        value={selectedTextOverlay.end ?? 2.5}
                        onChange={(e) => onUpdateTextOverlay?.(selectedTextOverlay.id, { end: Math.max((selectedTextOverlay.start || 0) + 0.1, parseFloat(e.target.value) || 0.1) })}
                        className="w-full px-2.5 py-1 rounded-lg bg-black/60 border border-white/[0.1] text-xs font-mono text-white focus:outline-none focus:border-[#25F4EE]"
                      />
                    </div>
                  </div>
                )}

                {/* Typography Controls Card */}
                <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                  {/* Font dropdown */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-slate-400 font-medium w-14 flex-shrink-0">ฟอนต์:</span>
                    <select
                      value={currentFont}
                      onChange={(e) => handleFontChange(e.target.value)}
                      className="flex-1 min-w-0 py-1.5 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-semibold text-white focus:outline-none focus:border-[#25F4EE] cursor-pointer"
                    >
                      {FONT_OPTIONS.map((f) => (
                        <option key={f.id} value={f.id} className="bg-[#0A0D14] text-white">
                          {f.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Font size slider & number input */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400 font-medium">ขนาดตัวอักษร:</span>
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          min={50}
                          max={220}
                          step={5}
                          value={Math.round(currentScale * 100)}
                          onChange={(e) => handleScaleChange(Math.max(0.5, Math.min(2.2, (parseInt(e.target.value, 10) || 100) / 100)))}
                          className="w-14 px-1.5 py-0.5 rounded-lg bg-black/60 border border-white/[0.1] text-right font-mono text-xs font-bold text-[#25F4EE] focus:outline-none focus:border-[#25F4EE]"
                        />
                        <span className="text-xs font-bold text-slate-400">%</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {[0.7, 0.85, 1.0, 1.25, 1.5].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => handleScaleChange(s)}
                          className={`flex-1 py-1 rounded-lg text-[10px] sm:text-[11px] font-bold border transition-all cursor-pointer ${
                            Math.abs(currentScale - s) < 0.05
                              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE] shadow-sm'
                              : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                        >
                          {Math.round(s * 100)}%
                        </button>
                      ))}
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="1.8"
                      step="0.05"
                      value={currentScale}
                      onChange={(e) => handleScaleChange(parseFloat(e.target.value))}
                      className="w-full accent-[#25F4EE] cursor-pointer"
                    />
                  </div>

                  {/* Pattern (B / I / U) and Alignment */}
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.06]">
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 font-medium">รูปแบบ:</span>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setTextPattern((p) => ({ ...p, bold: !p.bold }))}
                          className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                            textPattern.bold
                              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                              : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                          title="ตัวหนา"
                        >
                          B
                        </button>
                        <button
                          type="button"
                          onClick={() => setTextPattern((p) => ({ ...p, italic: !p.italic }))}
                          className={`flex-1 py-1 rounded-lg text-xs font-bold italic border transition-all cursor-pointer ${
                            textPattern.italic
                              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                              : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                          title="ตัวเอียง"
                        >
                          I
                        </button>
                        <button
                          type="button"
                          onClick={() => setTextPattern((p) => ({ ...p, underline: !p.underline }))}
                          className={`flex-1 py-1 rounded-lg text-xs font-bold underline border transition-all cursor-pointer ${
                            textPattern.underline
                              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                              : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                          title="ขีดเส้นใต้"
                        >
                          U
                        </button>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 font-medium">จัดแนว:</span>
                      <div className="flex items-center gap-1">
                        {[
                          { id: 'left', icon: AlignLeft, title: 'ชิดซ้าย' },
                          { id: 'center', icon: AlignCenter, title: 'กึ่งกลาง' },
                          { id: 'right', icon: AlignRight, title: 'ชิดขวา' },
                        ].map(({ id, icon: Icon, title }) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => setTextAlign(id)}
                            className={`flex-1 py-1 rounded-lg text-xs font-bold border transition-all flex items-center justify-center cursor-pointer ${
                              textAlign === id
                                ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                                : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                            title={title}
                          >
                            <Icon className="w-3.5 h-3.5" />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Position on screen */}
                  <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                    <span className="text-[11px] text-slate-400 font-medium">ตำแหน่งบนจอ:</span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[
                        { pos: 'top', label: 'บน (20%)' },
                        { pos: 'middle', label: 'กลาง (50%)' },
                        { pos: 'bottom', label: 'ล่าง (72%)' },
                      ].map(({ pos, label }) => (
                        <button
                          key={pos}
                          type="button"
                          onClick={() => handlePositionChange(pos)}
                          className={`py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer ${
                            currentPosition === pos
                              ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                              : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Color picker */}
                  <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-slate-400 font-medium">สีตัวอักษร:</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="color"
                          value={currentColor.startsWith('#') ? currentColor : '#FFFFFF'}
                          onChange={(e) => handleColorChange(e.target.value)}
                          className="h-6 w-6 rounded border border-white/20 bg-transparent cursor-pointer p-0"
                        />
                        <span className="text-xs font-mono font-bold text-white uppercase">
                          {currentColor}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 5 Preset Styles Card (CapCut Pro Aesthetic) */}
                <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300">สไตล์สำเร็จรูป (Preset Styles)</span>
                    <span className="text-[10px] text-slate-500">คลิกเปลี่ยนทันที</span>
                  </div>
                  <div className="grid grid-cols-5 gap-1.5">
                    {PRESET_STYLES.map((preset) => {
                      const isCurrent = (currentColor.toUpperCase() === preset.color.toUpperCase());
                      return (
                        <button
                          key={preset.id}
                          type="button"
                          onClick={() => handleApplyPreset(preset)}
                          className={`flex flex-col items-center justify-center p-1.5 rounded-xl border transition-all cursor-pointer group ${
                            isCurrent
                              ? 'border-[#25F4EE] bg-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40 shadow-sm'
                              : 'border-white/[0.08] bg-black/60 hover:border-white/20'
                          }`}
                          title={`${preset.name}: ${preset.desc}`}
                        >
                          <div
                            className="w-full h-8 rounded-lg flex items-center justify-center font-black text-sm border shadow-inner"
                            style={{
                              backgroundColor: '#000000',
                              color: preset.color,
                              borderColor: preset.color + '40',
                              textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                            }}
                          >
                            Aa
                          </div>
                          <span className="text-[10px] font-bold text-slate-300 mt-1 truncate w-full text-center group-hover:text-white">
                            {preset.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Text Overlay Specific: Animation & Background */}
                {isOverlaySelected && selectedTextOverlay && (
                  <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
                    <span className="text-xs font-bold text-slate-300 block">แอนิเมชันและกรอบข้อความ</span>
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400">แอนิเมชันตอนเข้า:</span>
                      <div className="grid grid-cols-3 gap-1">
                        {[
                          { id: 'pop', label: 'Pop เด้งเข้า' },
                          { id: 'fade', label: 'Fade ค่อยๆ โผล่' },
                          { id: 'slide', label: 'Slide เลื่อนขึ้น' },
                        ].map((a) => (
                          <button
                            key={a.id}
                            type="button"
                            onClick={() => onUpdateTextOverlay?.(selectedTextOverlay.id, { anim: a.id })}
                            className={`py-1 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                              (selectedTextOverlay.anim || 'pop') === a.id
                                ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                                : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                          >
                            {a.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Quick Actions for Selected Caption */}
                {isCaptionSelected && selectedCaption && (
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => onSeek?.(selectedCaption.start)}
                      className="py-1.5 px-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <Play className="w-3.5 h-3.5 fill-current text-emerald-400" />
                      <span>เล่นท่อนนี้</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onSplitCueAtPlayhead?.(selectedCaption._uid)}
                      className="py-1.5 px-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <Scissors className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>ตัดที่หัวอ่าน</span>
                    </button>
                  </div>
                )}
              </div>
            ) : selection?.type === 'hook' ? (
              /* ──────────────────────────────────────────────────────────
                  SUB-VIEW B: HOOK HEADER PROPERTIES
                 ────────────────────────────────────────────────────────── */
              <div
                ref={hookHeaderCardRef}
                className="rounded-2xl border border-white/[0.08] bg-black/40 p-3 space-y-3"
              >
                <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
                  <span className="text-xs font-bold text-[#E6C24A] flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-[#E6C24A]" />
                    <span>Header ฮุค (3 วินาทีแรก)</span>
                  </span>
                  <button
                    type="button"
                    onClick={onToggleHookHeader}
                    className={`text-xs font-bold px-2 py-0.5 rounded-lg border transition-all cursor-pointer ${
                      showHookHeader
                        ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                        : 'bg-white/[0.04] border-white/[0.1] text-slate-400'
                    }`}
                  >
                    {showHookHeader ? 'เปิดใช้งาน' : 'ปิดอยู่'}
                  </button>
                </div>

                {/* 3-Tier Text Inputs */}
                <div className="space-y-2">
                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 font-bold">1. แบรนด์ (Tier 1 - ตัวใหญ่):</span>
                    <input
                      ref={hookBrandInputRef}
                      type="text"
                      value={hookBrand}
                      onChange={(e) => onHookBrandChange?.(e.target.value)}
                      placeholder="เช่น Logitech, Sony, Apple..."
                      className="w-full px-3 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-bold text-white placeholder-slate-500 focus:outline-none focus:border-[#E6C24A]"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 font-bold">2. รุ่น / จุดเด่น (Tier 2 - สีเน้น):</span>
                    <input
                      type="text"
                      value={hookModel}
                      onChange={(e) => onHookModelChange?.(e.target.value)}
                      placeholder="เช่น Wave Keys, WH-1000XM5..."
                      className="w-full px-3 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-bold text-[#FFE600] placeholder-slate-500 focus:outline-none focus:border-[#FFE600]"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 font-bold">3. หมวดหมู่ / คำโปรย (Tier 3):</span>
                    <input
                      type="text"
                      value={hookLabel}
                      onChange={(e) => onHookLabelChange?.(e.target.value)}
                      placeholder="เช่น คีย์บอร์ดไร้สายเพื่อสุขภาพ..."
                      className="w-full px-3 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-medium text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#E6C24A]"
                    />
                  </div>
                </div>

                {/* Duration Slider */}
                <div className="space-y-1 pt-1 border-t border-white/[0.06]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">ระยะเวลาแสดงฮุค:</span>
                    <span className="font-mono font-bold text-[#E6C24A]">{hookDuration.toFixed(1)} วิ</span>
                  </div>
                  <input
                    type="range"
                    min="1.5"
                    max="5.0"
                    step="0.5"
                    value={hookDuration}
                    onChange={(e) => onHookDurationChange?.(parseFloat(e.target.value))}
                    className="w-full accent-[#E6C24A] cursor-pointer"
                  />
                </div>

                {/* Templates Selection */}
                {hookTemplates && (
                  <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-400">สไตล์เทมเพลตฮุค:</span>
                      {hasHookOverrides && (
                        <button
                          type="button"
                          onClick={onHookStyleReset}
                          className="rounded px-1.5 py-0.5 text-[10px] font-semibold text-amber-300 hover:bg-amber-400/20 cursor-pointer"
                        >
                          รีเซ็ตเป็นค่าเริ่มต้น
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      {Object.entries(hookTemplates).map(([key, tpl]) => {
                        const active = (hookStyle?.template || 'tech') === key;
                        return (
                          <button
                            key={key}
                            type="button"
                            onClick={() => onHookTemplate?.(key)}
                            className={`truncate rounded-lg px-2 py-1.5 text-left text-xs font-semibold transition-colors cursor-pointer border ${
                              active
                                ? 'bg-[#D97757]/20 border-[#D97757] text-[#E89274]'
                                : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                          >
                            {tpl.label_th}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Motion presets */}
                <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                  <span className="text-xs font-bold text-slate-400">แอนิเมชันพาดหัว:</span>
                  {[
                    { cat: 'in', label: 'เข้า' },
                    { cat: 'loop', label: 'ค้าง' },
                    { cat: 'out', label: 'ออก' },
                    { cat: 'accent', label: 'ตกแต่ง' },
                  ].map(({ cat, label }) => {
                    const options = hookMotionCatalog?.[cat];
                    if (!options) return null;
                    return (
                      <div key={cat} className="flex items-center gap-2">
                        <span className="w-12 flex-shrink-0 text-xs font-bold text-slate-400">{label}</span>
                        <select
                          value={hookMotion?.[cat] ?? hookMotionDefault?.[cat] ?? 'none'}
                          onChange={(e) => onHookMotionChange?.(cat, e.target.value)}
                          className="flex-1 min-w-0 rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1 text-xs font-semibold text-white shadow-inner focus:border-[#E6C24A] focus:outline-none cursor-pointer"
                        >
                          {Object.entries(options).map(([id, meta]) => (
                            <option key={id} value={id}>{meta.label_th}</option>
                          ))}
                        </select>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : selectedSeg ? (
              /* ──────────────────────────────────────────────────────────
                  SUB-VIEW C: VIDEO CLIP PROPERTIES
                 ────────────────────────────────────────────────────────── */
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
                      <span className="block text-xs text-slate-400 mb-1">Trim เข้า (วิ)</span>
                      <NumberInput
                        step="0.1"
                        min="0"
                        value={selectedSeg.clip.trim_start}
                        onChange={(e) => onClipChange?.({ trim_start: Math.max(0, parseFloat(e.target.value) || 0) })}
                      />
                    </div>
                    <div>
                      <span className="block text-xs text-slate-400 mb-1">Trim ออก (วิ)</span>
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
                    <span className="block text-xs text-slate-400 mb-1">ความเร็ว (Speed)</span>
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
                      <span className="text-xs text-slate-400 flex items-center gap-1.5">
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
                      <span className="text-xs text-slate-400 flex items-center gap-1.5">
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
                    const bgBlur = !!selectedSeg.clip.bg_blur || selectedSeg.clip.fit_mode === 'blur';
                    const freezeTail = Number(selectedSeg.clip.freeze_tail) || 0;
                    return (
                      <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400">กรอบภาพ</span>
                          <button
                            type="button"
                            disabled={zoom === 1 && !selectedSeg.clip.pan_x && !selectedSeg.clip.pan_y}
                            onClick={() => onClipChange?.({ zoom: undefined, pan_x: undefined, pan_y: undefined })}
                            className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                          >
                            รีเซ็ต
                          </button>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onClipChange?.({ bg_blur: bgBlur ? undefined : true, fit_mode: bgBlur ? undefined : 'blur' })}
                            className={`flex-1 rounded-xl border px-2 py-1 text-xs font-bold transition-all cursor-pointer ${
                              bgBlur
                                ? 'border-[#25F4EE] bg-[#25F4EE]/15 text-[#25F4EE]'
                                : 'border-white/[0.1] bg-black/40 text-slate-400 hover:text-white'
                            }`}
                          >
                            {bgBlur ? '✓ พื้นหลังเบลอ' : 'พื้นหลังเบลอ'}
                          </button>
                          <label className="flex items-center gap-1 text-xs text-slate-400">
                            <span>ค้างท้าย</span>
                            <input
                              type="number" min="0" max="10" step="0.5"
                              value={freezeTail}
                              onChange={(e) => {
                                const v = Math.min(10, Math.max(0, parseFloat(e.target.value) || 0));
                                onClipChange?.({ freeze_tail: v === 0 ? undefined : v });
                              }}
                              className="w-14 rounded bg-black/50 border border-white/[0.1] px-1 py-0.5 text-right font-mono text-xs text-white focus:outline-none focus:border-[#25F4EE]"
                            />
                            <span>วิ</span>
                          </label>
                        </div>
                        <label className="block">
                          <span className="mb-0.5 flex justify-between text-xs text-slate-400">
                            <span>ซูม</span>
                            <span className="font-mono text-slate-300">{zoom.toFixed(2)}x</span>
                          </span>
                          <input
                            type="range" min={1} max={3} step={0.05} value={zoom}
                            onChange={(e) => onClipChange?.({ zoom: parseFloat(e.target.value) })}
                            className="w-full accent-[#25F4EE]"
                          />
                        </label>
                        {FIELDS.map((f) => (
                          <label key={f.key} className={`block ${panning ? '' : 'opacity-40'}`}>
                            <span className="mb-0.5 flex justify-between text-xs text-slate-400">
                              <span>{f.label}</span>
                              <span className="font-mono text-slate-300">{(selectedSeg.clip[f.key] ?? 0).toFixed(2)}</span>
                            </span>
                            <input
                              type="range" min={-1} max={1} step={0.05}
                              value={selectedSeg.clip[f.key] ?? 0}
                              disabled={!panning}
                              onChange={(e) => onClipChange?.({ [f.key]: parseFloat(e.target.value) })}
                              className="w-full accent-[#25F4EE] disabled:cursor-not-allowed"
                            />
                          </label>
                        ))}
                        {!panning && (
                          <p className="text-[11px] text-slate-500">ซูมเกิน 1x ก่อนถึงจะเลื่อนกรอบได้</p>
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
                      <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400">สีของคลิปนี้</span>
                          <button
                            type="button"
                            disabled={!touched}
                            onClick={() => onClipChange?.({ brightness: undefined, contrast: undefined, saturation: undefined })}
                            className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                          >
                            รีเซ็ต
                          </button>
                        </div>
                        {COLOR_FIELDS.map((f) => {
                          const value = selectedSeg.clip[f.key] ?? f.def;
                          return (
                            <label key={f.key} className="block">
                              <span className="mb-0.5 flex justify-between text-xs text-slate-400">
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
                                className="w-full accent-[#25F4EE]"
                              />
                            </label>
                          );
                        })}
                      </div>
                    );
                  })()}

                  {/* Transitions */}
                  {selectedSeg.index > 0 && (() => {
                    const kind = selectedSeg.clip.transition_in || 'cut';
                    const dur = selectedSeg.clip.transition_duration ?? FADE_DURATION;
                    const isCut = kind === 'cut';
                    return (
                      <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
                        <span className="block text-xs text-slate-400">รอยต่อกับคลิปก่อนหน้า</span>
                        <div className="grid grid-cols-2 gap-1">
                          {TRANSITIONS.map((t) => (
                            <button
                              key={t.id}
                              type="button"
                              onClick={() => onClipChange?.({
                                transition_in: t.id,
                                transition_duration: dur,
                              })}
                              className={`flex items-center justify-center gap-1.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                                kind === t.id
                                  ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                                  : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                              }`}
                            >
                              <TransitionIcon type={t.id} className="h-3.5 w-3.5 flex-shrink-0" />
                              {t.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            ) : (
              /* ──────────────────────────────────────────────────────────
                  SUB-VIEW D: EMPTY CONTEXT STATE (GUIDANCE)
                 ────────────────────────────────────────────────────────── */
              <div className="py-8 px-4 text-center rounded-2xl border border-white/[0.08] bg-black/40 space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center mx-auto text-[#25F4EE]">
                  <SlidersHorizontal className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-white">แผงควบคุมคุณสมบัติ (Inspector)</h4>
                  <p className="text-xs text-slate-400 max-w-[280px] mx-auto leading-relaxed">
                    คลิกเลือกคำบรรยาย, ข้อความ, คลิป หรือเสียง บนไทม์ไลน์เพื่อปรับแต่งคุณสมบัติเฉพาะตัว
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 max-w-[280px] mx-auto pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      if (cuesList.length > 0) {
                        onSelectCue?.(cuesList[0]._uid);
                      } else {
                        setActiveTab('cues');
                      }
                    }}
                    className="py-2 px-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-bold text-slate-200 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Type className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>เลือกคำบรรยาย</span>
                  </button>

                  <button
                    type="button"
                    onClick={onAddTextOverlay}
                    className="py-2 px-2.5 rounded-xl bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/30 text-xs font-bold text-[#25F4EE] transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>เพิ่มข้อความ</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════
            TAB 2: SUBTITLE TRANSCRIPT LIST (สไตล์ Word Processor)
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'cues' && (
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
        )}

        {/* ═════════════════════════════════════════════════════════════════════
            TAB 3: PROJECT OVERVIEW (ภาพรวมโปรเจกต์)
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'overview' && (
          <div className="space-y-3">
            <div className="space-y-2 rounded-2xl bg-black/40 border border-white/[0.08] p-3 text-xs">
              <div className="flex justify-between text-slate-300">
                <span>ฟอนต์มาตรฐานของโปรเจกต์:</span>
                <span className="font-bold text-[#25F4EE]">{style.fontName || 'Kanit'}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>เพลงประกอบ BGM:</span>
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
