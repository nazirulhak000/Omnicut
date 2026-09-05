import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  AlertTriangle, Film, MessageSquare, Settings2, Scissors,
  Trash2, Plus, Volume2, VolumeX, RotateCw, Play, Check, Search,
  Link2, Clock, Split, Sparkles, ArrowUp, ArrowDown,
  Replace, CheckCheck, RefreshCw, X, ChevronUp, ChevronDown, Type,
  SlidersHorizontal, AlignLeft, AlignCenter, AlignRight, Bold, Italic, Underline,
  Music, Layers, Palette, Target, Globe, RotateCcw, Magnet
} from 'lucide-react';
import { TransitionIcon } from '../../lib/transitionIcons';
import { TRANSITIONS, FADE_DURATION, MAX_TRANSITION_DURATION } from '../../lib/timelineMath';
import { HOOK_MAX_DURATION, HOOK_MIN_DURATION } from './Timeline';
import {
  ACCENT_COLOR,
  DEFAULT_TEXT_LOOK,
  LEGACY_BG_STYLES,
  PILL_PAD_X_EM,
  PILL_PAD_Y_EM,
  overriddenTierFields,
  resolveLook,
  withHookTemplate,
  withHookTemplateReset,
  withTierLook,
  withTierText,
} from '../../lib/overlayModel';
import { toMediaUrl } from '../../lib/mediaUrl';

const LEGACY_SFX_ALIASES = {
  whoosh: 'sfx_whoosh_fast',
  pop: 'sfx_pop_bubble',
  ding: 'sfx_bell_ding',
  cash: 'sfx_cash_register',
  boom: 'sfx_vine_boom',
};

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

const HOOK_TIER_LABELS = ['แบรนด์', 'รุ่น / จุดเด่น', 'หมวดหมู่ / คำโปรย'];

/**
 * The five background chips are shorthand for a pill, which is what the look
 * actually carries. bgStyle and badgeColor used to be their own fields, and a
 * banner's pill was a third spelling of the same idea.
 */
function pillForBgStyle(id) {
  const preset = LEGACY_BG_STYLES[id];
  if (!preset) return null;
  return { ...preset, pad_x_em: PILL_PAD_X_EM, pad_y_em: PILL_PAD_Y_EM };
}

function bgStyleOf(pill) {
  if (!pill) return 'none';
  for (const [id, preset] of Object.entries(LEGACY_BG_STYLES)) {
    if (preset && preset.fill === pill.fill && preset.border === pill.border) return id;
  }
  return 'none';
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
  hookOverlay = null,
  hookMotionCatalog = null,
  hookMotionDefault = null,
  hookTemplates = null,
  fonts = [],
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
  overlays = [],
  onAddTextOverlay,
  onUpdateOverlay,
  onReplaceOverlay,
  onDeleteOverlay,
  onSelectOverlay,
  onSelect,
  trackMix = { mute: {}, solo: {} },
  onTrackMix,
  onCloseAllCaptionGaps,
  onResetSubtitleTimings,
}) {
  const textOverlays = (overlays || []).filter((o) => o.kind === 'text');
  const showHookHeader = !!hookOverlay && !hookOverlay.hidden;
  // Which tier fields the user has moved off the template, so each row can
  // say so and offer to put it back.
  const hookOverrides = hookOverlay ? overriddenTierFields(hookOverlay) : [];
  const hasHookOverrides = hookOverrides.some((fields) => fields.length > 0);
  const hookDuration = hookOverlay ? Math.max(0.1, hookOverlay.end - hookOverlay.start) : 3.0;
  const hookMotion = hookOverlay?.anim || {};

  const patchHookTier = (tierIdx, patch) => {
    if (!hookOverlay) return;
    onReplaceOverlay?.(hookOverlay.id, withTierLook(hookOverlay, tierIdx, patch));
  };
  const setHookTierText = (tierIdx, text) => {
    if (!hookOverlay) return;
    onReplaceOverlay?.(hookOverlay.id, withTierText(hookOverlay, tierIdx, text));
  };
  const onHookTemplate = (template) => {
    if (!hookOverlay) return;
    onReplaceOverlay?.(hookOverlay.id, withHookTemplate(hookOverlay, template));
  };
  const onHookStyleReset = () => {
    if (!hookOverlay) return;
    onReplaceOverlay?.(hookOverlay.id, withHookTemplateReset(hookOverlay));
  };
  const onHookDurationChange = (seconds) => {
    if (!hookOverlay) return;
    onUpdateOverlay?.(hookOverlay.id, { end: Math.round((hookOverlay.start + seconds) * 100) / 100 });
  };
  const onHookMotionChange = (key, value) => {
    if (!hookOverlay) return;
    onUpdateOverlay?.(hookOverlay.id, { anim: { ...(hookOverlay.anim || {}), [key]: value } });
  };

  // Top tabs: 'properties' (Contextual Inspector) | 'cues' (Subtitle transcript) | 'overview' (Project settings)
  const [activeTab, setActiveTab] = useState('properties');
  const [localApplyToAll, setLocalApplyToAll] = useState(true);
  const effectiveApplyToAll = onToggleApplyToAll ? applyToAll : localApplyToAll;
  const toggleApplyToAll = onToggleApplyToAll || setLocalApplyToAll;
  const [textPattern, setTextPattern] = useState({ bold: true, italic: false, underline: false });
  // Which banner row is expanded. One at a time keeps the panel scannable --
  // three rows of five controls each is a wall.
  const [openTier, setOpenTier] = useState(0);
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
  const textAreaRef = useRef(null);
  const isTypingRef = useRef(false);
  const gap = (audioDuration || 0) - totalDuration;

  const sfxList = assets?.sfx || [];

  const playSfxAudio = (sfxKey) => {
    if (!sfxKey) return;
    const canonical = LEGACY_SFX_ALIASES[sfxKey] || sfxKey;
    const item = sfxList.find(s => s.id === canonical || s.name === canonical || s.id === sfxKey || s.name === sfxKey)
      || sfxList.find(s => s.name?.toLowerCase().includes(sfxKey.toLowerCase()));
    if (!item?.path) return;
    try {
      const audio = new Audio(toMediaUrl(item.path));
      audio.volume = 0.28;
      audio.play().catch(() => {});
    } catch (_) {}
  };

  // The shared text controls below drive a single-tier overlay. A banner has
  // three and gets its own editor, so it is deliberately not selected here.
  const selectedTextOverlay = selection?.type === 'text_overlay'
    ? (overlays || []).find((item) => item.id === selection.id && item.kind === 'text')
    : null;
  const selectedLook = selectedTextOverlay
    ? resolveLook(selectedTextOverlay.look, (selectedTextOverlay.tiers || [{}])[0].look)
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

    if (selection?.type === 'text_overlay' && selection?.focusText) {
      setTimeout(() => {
        if (textAreaRef.current) {
          textAreaRef.current.focus();
          textAreaRef.current.select();
        }
      }, 60);
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

  const patchOverlayLook = (patch) => {
    if (!selectedTextOverlay) return;
    onReplaceOverlay?.(selectedTextOverlay.id, withTierLook(selectedTextOverlay, 0, patch));
  };

  const currentText = isOverlaySelected
    ? ((selectedTextOverlay.tiers || [{}])[0].text || '')
    : isCaptionSelected
    ? (selectedCaption.text || '')
    : '';

  const currentTranslation = isCaptionSelected ? selectedCaption.translation : null;

  const currentFont = isOverlaySelected
    ? (selectedLook.font || style?.fontName || 'Kanit')
    : isCaptionSelected
    ? (selectedCaption.fontName || style?.fontName || 'Kanit')
    : (style?.fontName || 'Kanit');

  const currentScale = isOverlaySelected
    ? (selectedLook.size_pct ?? 100) / 100
    : isCaptionSelected
    ? (selectedCaption.scale ?? style?.captionScale ?? 1.0)
    : (style?.captionScale ?? 1.0);

  const currentColor = isOverlaySelected
    ? (selectedLook.color === ACCENT_COLOR ? '#FFE600' : selectedLook.color)
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
      patchOverlayLook({ font: fontName });
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
      patchOverlayLook({ size_pct: Math.round(clamped * 100) });
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
      patchOverlayLook({ color });
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
      onUpdateOverlay?.(selectedTextOverlay.id, { position, x: null, y: null });
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
      onUpdateOverlay?.(selectedTextOverlay.id, { x: 0.5, y: 0.5, position: 'middle' });
      patchOverlayLook({
        size_pct: DEFAULT_TEXT_LOOK.size_pct,
        font: 'Kanit',
        color: '#FFE600',
        outline_color: DEFAULT_TEXT_LOOK.outline_color,
        outline_px: DEFAULT_TEXT_LOOK.outline_px,
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
      onReplaceOverlay?.(selectedTextOverlay.id, withTierText(selectedTextOverlay, 0, val));
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
                    onSelectOverlay?.(textOverlays[0].id, 'text');
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
                      onClick={() => onDeleteOverlay?.(selectedTextOverlay.id)}
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
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {onCloseAllCaptionGaps && (
                          <button
                            type="button"
                            onClick={onCloseAllCaptionGaps}
                            className="px-2 py-1 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[11px] font-semibold text-[#25F4EE] hover:text-[#52fffb] flex items-center gap-1 transition-all cursor-pointer"
                            title="ดูดกล่องคำบรรยายทุกตัวให้ขยับมาเรียงชิดติดกันต่อเนื่องโดยไม่มีช่องว่าง"
                          >
                            <Magnet className="w-3 h-3 text-[#25F4EE]" />
                            <span>ดูดชิดติดกัน</span>
                          </button>
                        )}
                        {onResetSubtitleTimings && (
                          <button
                            type="button"
                            onClick={onResetSubtitleTimings}
                            className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-amber-300 hover:text-amber-200 flex items-center gap-1 transition-all cursor-pointer"
                            title="รีเซ็ตเวลาเริ่มต้นและสิ้นสุดของคำบรรยายทุกตัวกลับสู่ค่าตั้งต้นเดิม"
                          >
                            <Clock className="w-3 h-3 text-amber-400" />
                            <span>รีเซ็ตเวลาตั้งต้น</span>
                          </button>
                        )}
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
                    ref={textAreaRef}
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
                        onChange={(e) => onUpdateOverlay?.(selectedTextOverlay.id, { start: Math.max(0, parseFloat(e.target.value) || 0) })}
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
                        onChange={(e) => onUpdateOverlay?.(selectedTextOverlay.id, { end: Math.max((selectedTextOverlay.start || 0) + 0.1, parseFloat(e.target.value) || 0.1) })}
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

                {/* Text Overlay Specific: Animation, Badge Style & Linked SFX */}
                {isOverlaySelected && selectedTextOverlay && (
                  <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                    <div className="flex items-center justify-between pb-1 border-b border-white/[0.06]">
                      <span className="text-xs font-bold text-slate-200">แอนิเมชัน กรอบ และเสียงป็อปอัพ</span>
                    </div>

                    {/* 1. In-Animation selector */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] text-slate-400 font-medium">แอนิเมชันตอนเปิดตัว (In-Animation):</span>
                      <div className="grid grid-cols-3 gap-1">
                        {[
                          { id: 'snap', label: 'Pop เด้งเข้า' },
                          { id: 'pop_zoom', label: 'Zoom พุ่งเข้า' },
                          { id: 'stamp', label: 'Stamp กระแทก' },
                          { id: 'rise', label: 'Slide เลื่อนขึ้น' },
                          { id: 'quick_fade', label: 'Fade ค่อยๆ โผล่' },
                          { id: 'none', label: 'None นิ่ง' },
                        ].map((a) => (
                          <button
                            key={a.id}
                            type="button"
                            onClick={() => onUpdateOverlay?.(selectedTextOverlay.id, { anim: { ...(selectedTextOverlay.anim || {}), in: a.id } })}
                            className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                              (selectedTextOverlay.anim?.in || 'snap') === a.id
                                ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                                : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                          >
                            {a.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* 2. Badge Background Style */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] text-slate-400 font-medium">สไตล์กรอบ/ป้ายพื้นหลัง:</span>
                      <div className="grid grid-cols-3 gap-1">
                        {[
                          { id: 'none', label: 'ไม่มีกรอบ' },
                          { id: 'pill', label: 'Dark Glass' },
                          { id: 'badge_red', label: 'Sale แดง' },
                          { id: 'badge_yellow', label: 'ดีล เหลือง' },
                          { id: 'badge_cyan', label: 'Cyber นีออน' },
                        ].map((bg) => (
                          <button
                            key={bg.id}
                            type="button"
                            onClick={() => patchOverlayLook({ pill: pillForBgStyle(bg.id) })}
                            className={`py-1 px-1 rounded-lg text-xs font-bold border transition-all cursor-pointer truncate text-center ${
                              bgStyleOf(selectedLook.pill) === bg.id
                                ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                                : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                          >
                            {bg.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* 3. Linked Sound FX */}
                    <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                          <Volume2 className="w-3.5 h-3.5 text-amber-400" />
                          <span>เสียงเอฟเฟกต์ (SFX):</span>
                        </span>
                        {selectedTextOverlay.sfx && (
                          <button
                            type="button"
                            onClick={() => playSfxAudio(selectedTextOverlay.sfx)}
                            className="px-2 py-0.5 rounded-md bg-amber-400/20 hover:bg-amber-400/30 text-amber-300 text-[10px] font-bold flex items-center gap-1 border border-amber-400/40 cursor-pointer transition-all"
                            title="ทดลองฟังเสียงสด"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            <span>ลองฟัง</span>
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-1.5">
                        <select
                          value={selectedTextOverlay.sfx || 'none'}
                          onChange={(e) => {
                            const val = e.target.value === 'none' ? null : e.target.value;
                            onUpdateOverlay?.(selectedTextOverlay.id, { sfx: val });
                            if (val) playSfxAudio(val);
                          }}
                          className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-semibold text-white focus:outline-none focus:border-[#25F4EE] cursor-pointer"
                        >
                          <option value="none" className="bg-[#0A0D14] text-slate-400">ปิดเสียง (None)</option>
                          <option value="pop" className="bg-[#0A0D14] text-white">Pop บับเบิล</option>
                          <option value="ding" className="bg-[#0A0D14] text-white">Ding กระดิ่ง</option>
                          <option value="cash" className="bg-[#0A0D14] text-white">Cash เปิดกล่องเงิน</option>
                          <option value="sfx_coin_drop" className="bg-[#0A0D14] text-white">Coin เหรียญทอง</option>
                          <option value="sfx_whoosh_fast" className="bg-[#0A0D14] text-white">Whoosh พุ่งเร็ว</option>
                          <option value="boom" className="bg-[#0A0D14] text-white">Boom กระแทก</option>
                          <option value="sfx_camera_shutter" className="bg-[#0A0D14] text-white">Shutter ถ่ายรูป</option>
                          <option value="sfx_sub_drop" className="bg-[#0A0D14] text-white">Sub Drop ทุ้มลึก</option>
                          <option value="sfx_bell_ding" className="bg-[#0A0D14] text-white">Bell Ding แจ้งเตือน</option>
                          <option value="sfx_mouse_click" className="bg-[#0A0D14] text-white">Click คลิกเบา</option>
                        </select>

                        <div className="flex items-center text-[10px] text-slate-400 px-1">
                          {selectedTextOverlay.sfx ? (
                            <span className="text-emerald-400">✓ ผูกเสียงแล้ว (ลบตาม)</span>
                          ) : (
                            <span className="text-slate-500">ไม่มีเสียงประกอบ</span>
                          )}
                        </div>
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
                    <span>ป้ายฮุก</span>
                    <span className="font-mono text-[10px] text-[#E6C24A]/60">
                      {(hookOverlay?.start ?? 0).toFixed(1)}–{(hookOverlay?.end ?? 3).toFixed(1)}s
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => onToggleHookHeader?.()}
                    className={`px-2 py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer ${
                      showHookHeader
                        ? 'bg-[#E6C24A]/15 border-[#E6C24A]/50 text-[#E6C24A]'
                        : 'bg-black/40 border-white/[0.1] text-slate-400 hover:text-white'
                    }`}
                  >
                    {showHookHeader ? 'เปิดใช้งาน' : 'ปิดอยู่'}
                  </button>
                </div>

                {!hookOverlay ? (
                  <p className="py-4 text-center text-xs text-slate-500">
                    ยังไม่มีป้ายฮุก — กด “ปิดอยู่” ด้านบนเพื่อสร้าง
                  </p>
                ) : (
                  <>
                    {/* Template row */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-medium text-slate-400">สไตล์</span>
                        <button
                          type="button"
                          onClick={() => onHookStyleReset?.()}
                          disabled={!hasHookOverrides}
                          title="คืนทุกแถวกลับเป็นค่าของสไตล์นี้"
                          className={`flex items-center gap-1 rounded-lg px-2 py-0.5 text-[10px] font-bold transition-all ${
                            hasHookOverrides
                              ? 'text-[#E6C24A] hover:bg-[#E6C24A]/10 cursor-pointer'
                              : 'text-slate-600 cursor-not-allowed'
                          }`}
                        >
                          <RotateCcw className="h-3 w-3" />
                          รีเซ็ต
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-1">
                        {Object.entries(hookTemplates || {}).map(([key, tpl]) => (
                          <button
                            key={key}
                            type="button"
                            onClick={() => onHookTemplate?.(key)}
                            title={tpl.label_th}
                            className={`truncate rounded-lg border px-2 py-1 text-left text-[11px] font-bold transition-all cursor-pointer ${
                              hookOverlay.template === key
                                ? 'bg-[#E6C24A]/15 border-[#E6C24A] text-[#E6C24A]'
                                : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                            }`}
                          >
                            {tpl.label_th}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Duration */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-medium text-slate-400">ระยะเวลาแสดง</span>
                        <span className="font-mono font-bold text-[#E6C24A]">{hookDuration.toFixed(1)} วิ</span>
                      </div>
                      <input
                        type="range"
                        min={HOOK_MIN_DURATION}
                        max={HOOK_MAX_DURATION}
                        step={0.1}
                        value={hookDuration}
                        onChange={(e) => onHookDurationChange?.(parseFloat(e.target.value))}
                        className="w-full accent-[#E6C24A] cursor-pointer"
                      />
                    </div>

                    {/* One row per tier: text, size, colours, outline, caps. */}
                    <div className="space-y-1.5">
                      {HOOK_TIER_LABELS.map((tierLabel, idx) => {
                        const tier = (hookOverlay.tiers || [])[idx];
                        if (!tier) return null;
                        const look = resolveLook(hookOverlay.look, tier.look);
                        const overridden = hookOverrides[idx] || [];
                        const open = openTier === idx;
                        const swatch = look.color === ACCENT_COLOR ? '#FFE600' : look.color;
                        return (
                          <div
                            key={tierLabel}
                            className={`rounded-xl border transition-colors ${
                              open ? 'border-[#E6C24A]/40 bg-black/50' : 'border-white/[0.07] bg-black/25'
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => setOpenTier(open ? -1 : idx)}
                              className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left cursor-pointer"
                            >
                              <span className="w-4 flex-shrink-0 font-mono text-[10px] text-slate-500">{idx + 1}</span>
                              <span className="min-w-0 flex-1 truncate text-[11px] font-bold text-slate-300">
                                {tier.text?.trim() || tierLabel}
                              </span>
                              <span className="flex-shrink-0 font-mono text-[10px] text-slate-500">
                                {look.size_pct}%
                              </span>
                              <span
                                className="h-3 w-3 flex-shrink-0 rounded-full border border-white/20"
                                style={{ background: swatch }}
                              />
                              <span
                                title={overridden.length ? `แก้จากสไตล์แล้ว: ${overridden.length} ค่า` : 'ค่าเดิมของสไตล์'}
                                className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                                  overridden.length ? 'bg-[#E6C24A]' : 'bg-transparent ring-1 ring-slate-600'
                                }`}
                              />
                              <ChevronDown
                                className={`h-3 w-3 flex-shrink-0 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}
                              />
                            </button>

                            {open && (
                              <div className="space-y-2 border-t border-white/[0.06] px-2.5 pb-2.5 pt-2">
                                <input
                                  ref={idx === 0 ? hookBrandInputRef : undefined}
                                  value={tier.text || ''}
                                  onChange={(e) => setHookTierText(idx, e.target.value)}
                                  placeholder={tierLabel}
                                  className="w-full rounded-lg border border-white/[0.1] bg-black/60 px-2 py-1.5 text-xs font-semibold text-white shadow-inner focus:border-[#E6C24A] focus:outline-none"
                                />

                                <div className="flex items-center gap-2">
                                  <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขนาด</span>
                                  <input
                                    type="range"
                                    min={40}
                                    max={220}
                                    step={1}
                                    value={look.size_pct}
                                    onChange={(e) => patchHookTier(idx, { size_pct: parseInt(e.target.value, 10) })}
                                    className="min-w-0 flex-1 accent-[#E6C24A] cursor-pointer"
                                  />
                                  <span className="w-9 flex-shrink-0 text-right font-mono text-[10px] text-[#E6C24A]">
                                    {look.size_pct}%
                                  </span>
                                </div>

                                <div className="flex items-center gap-2">
                                  <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">สี</span>
                                  <input
                                    type="color"
                                    value={swatch}
                                    onChange={(e) => patchHookTier(idx, { color: e.target.value })}
                                    className="h-6 w-8 flex-shrink-0 cursor-pointer rounded border border-white/[0.1] bg-transparent"
                                  />
                                  <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขอบ</span>
                                  <input
                                    type="color"
                                    value={look.outline_color}
                                    onChange={(e) => patchHookTier(idx, { outline_color: e.target.value })}
                                    className="h-6 w-8 flex-shrink-0 cursor-pointer rounded border border-white/[0.1] bg-transparent"
                                  />
                                  <button
                                    type="button"
                                    onClick={() => patchHookTier(idx, { upper: !look.upper })}
                                    title="พิมพ์ใหญ่ทั้งบรรทัด"
                                    className={`ml-auto flex-shrink-0 rounded-lg border px-2 py-0.5 text-[10px] font-black transition-all cursor-pointer ${
                                      look.upper
                                        ? 'border-[#E6C24A] bg-[#E6C24A]/15 text-[#E6C24A]'
                                        : 'border-white/[0.08] bg-black/30 text-slate-500 hover:text-white'
                                    }`}
                                  >
                                    AA
                                  </button>
                                </div>

                                <div className="flex items-center gap-2">
                                  <span className="w-11 flex-shrink-0 text-[10px] font-medium text-slate-400">ขอบหนา</span>
                                  <input
                                    type="range"
                                    min={0}
                                    max={20}
                                    step={0.5}
                                    value={look.outline_px}
                                    onChange={(e) => patchHookTier(idx, { outline_px: parseFloat(e.target.value) })}
                                    className="min-w-0 flex-1 accent-[#E6C24A] cursor-pointer"
                                  />
                                  <span className="w-9 flex-shrink-0 text-right font-mono text-[10px] text-[#E6C24A]">
                                    {look.outline_px}px
                                  </span>
                                </div>

                                {look.color === ACCENT_COLOR && (
                                  <p className="text-[10px] text-slate-500">
                                    แถวนี้ใช้สีเดียวกับคำบรรยายอยู่ — เลือกสีเพื่อกำหนดเอง
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

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
                  </>
                )}
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

              {/* Close All Caption Gaps (ดูดชิดติดกัน) */}
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
