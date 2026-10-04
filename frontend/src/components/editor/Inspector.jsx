import React, { useState, useEffect, useRef } from 'react';
import {
  Film,
  MessageSquare,
  Settings2,
  Plus,
  Sparkles,
  Type,
  SlidersHorizontal,
  Smile,
  Layers,
  ClipboardPaste,
} from 'lucide-react';

import ClipInspector from './inspector/ClipInspector';
import CaptionInspector from './inspector/CaptionInspector';
import OverlayInspector from './inspector/OverlayInspector';
import StickerInspector from './inspector/StickerInspector';
import EffectInspector from './inspector/EffectInspector';
import CuesTranscriptInspector from './inspector/CuesTranscriptInspector';
import ProjectInspector from './inspector/ProjectInspector';
import CutoutInspector from './inspector/CutoutInspector';
import { resolveSelectedItem } from '../../lib/selectionResolver.js';

/**
 * Render clip fields exposed to Inspector/ClipInspector:
 * bg_blur, brightness, contrast, fit_mode, freeze_tail, mirror,
 * pan_x, pan_y, rotation, saturation, smooth_slowmo, speed, trim_end,
 * trim_start, volume, zoom
 */
export const RENDER_CLIP_FIELDS = [
  'bg_blur', 'brightness', 'contrast', 'fit_mode', 'freeze_tail', 'mirror',
  'pan_x', 'pan_y', 'rotation', 'saturation', 'smooth_slowmo', 'speed',
  'trim_end', 'trim_start', 'volume', 'zoom', 'source_window',
];

export default function Inspector({
  selection,
  // Clips selected on the timeline with Ctrl/Shift+click (primary included).
  multiSelectCount = 0,
  onCopySettings = null,
  onPasteSettings = null,
  canPasteSettings = false,
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
  customHookTemplates = {},
  onSaveCustomHookTemplate = null,
  onDeleteCustomHookTemplate = null,
  fonts = [],
  onToggleHookHeader,
  onAddTextAtPlayhead,
  onStyleChange,
  onClipChange,
  clipList = [],
  onPatchAllClips = null,
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
  stickers = [],
  onUpdateSticker = null,
  onDeleteSticker = null,
  effects = [],
  onUpdateEffect = null,
  onDeleteEffect = null,
  backgroundIsolation = null,
  backgroundIsolationStatus = null,
  onToggleBackgroundIsolation = null,
  cutoutPreviewMode = 'composite',
  onCutoutPreviewModeChange = null,
  subjectPoints = [],
  subjectPickMode = false,
  onToggleSubjectPickMode = null,
  onClearSubjectPoints = null,
}) {
  const textOverlays = (overlays || []).filter((o) => o.kind === 'text');

  const selectedSticker = resolveSelectedItem(selection, 'sticker', stickers, {
    fallback: stickers?.[0] || null,
  });

  const selectedEffect = resolveSelectedItem(selection, 'effect', effects);
  const selectedEffectAsset = selectedEffect
    ? (assets?.effects || []).find((a) => a.id === selectedEffect.effectId) || null
    : null;

  // Top tabs: 'properties' (Contextual Inspector) | 'cues' (Subtitle transcript) | 'overview' (Project settings)
  const [activeTab, setActiveTab] = useState('properties');
  const [localApplyToAll, setLocalApplyToAll] = useState(true);
  const effectiveApplyToAll = onToggleApplyToAll ? applyToAll : localApplyToAll;
  const toggleApplyToAll = onToggleApplyToAll || setLocalApplyToAll;

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

    prevSelectionTypeRef.current = selection?.type;
    prevSelectionIdRef.current = selection?.id;
  }, [selection, activeTab]);

  const selectedTextOverlay = resolveSelectedItem(selection, 'text_overlay', overlays, {
    matches: (item, id) => item.id === id && item.kind === 'text',
  });

  const isOverlaySelected = Boolean(selectedTextOverlay);
  const isCaptionSelected = Boolean(selectedCaption);
  const isTextSelected = isOverlaySelected || isCaptionSelected;

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
            TAB 1: CONTEXTUAL PROPERTIES INSPECTOR
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'properties' && (
          <div className="space-y-3">
            {/* Quick Switcher Chips */}
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
                onClick={() => onSelect?.({ type: 'hook' })}
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

              {selectedSticker && (
                <button
                  type="button"
                  onClick={() => onSelect?.({ type: 'sticker', id: selectedSticker.id })}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border ${
                    selection?.type === 'sticker'
                      ? 'bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE]'
                      : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
                  }`}
                >
                  <Smile className="w-3 h-3" />
                  <span>สติกเกอร์</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => onSelect?.({ type: 'cutout' })}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer border ${
                  selection?.type === 'cutout'
                    ? 'bg-violet-500/20 border-violet-400 text-violet-300'
                    : backgroundIsolation?.enabled
                      ? 'bg-violet-950/40 border-violet-500/30 text-violet-300 hover:text-white'
                      : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                <Layers className="w-3 h-3 text-violet-400" />
                <span>ตัดพื้นหลัง</span>
                {backgroundIsolation?.enabled && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                )}
              </button>
            </div>

            {/* Contextual Sub-views */}
            {isOverlaySelected ? (
              <OverlayInspector
                selection={selection}
                selectedTextOverlay={selectedTextOverlay}
                hookOverlay={hookOverlay}
                hookMotionCatalog={hookMotionCatalog}
                hookMotionDefault={hookMotionDefault}
                hookTemplates={hookTemplates}
                customHookTemplates={customHookTemplates}
                onSaveCustomHookTemplate={onSaveCustomHookTemplate}
                onDeleteCustomHookTemplate={onDeleteCustomHookTemplate}
                assets={assets}
                onToggleHookHeader={onToggleHookHeader}
                onUpdateOverlay={onUpdateOverlay}
                onReplaceOverlay={onReplaceOverlay}
                onDeleteOverlay={onDeleteOverlay}
              />
            ) : isCaptionSelected ? (
              <CaptionInspector
                selectedCaption={selectedCaption}
                style={style}
                effectiveApplyToAll={effectiveApplyToAll}
                toggleApplyToAll={toggleApplyToAll}
                onStyleChange={onStyleChange}
                onPatchAllCaptions={onPatchAllCaptions}
                onCaptionChange={onCaptionChange}
                onCloseAllCaptionGaps={onCloseAllCaptionGaps}
                onResetSubtitleTimings={onResetSubtitleTimings}
                onSeek={onSeek}
                onSplitCueAtPlayhead={onSplitCueAtPlayhead}
              />
            ) : selection?.type === 'hook' ? (
              <OverlayInspector
                selection={selection}
                selectedTextOverlay={null}
                hookOverlay={hookOverlay}
                hookMotionCatalog={hookMotionCatalog}
                hookMotionDefault={hookMotionDefault}
                hookTemplates={hookTemplates}
                customHookTemplates={customHookTemplates}
                onSaveCustomHookTemplate={onSaveCustomHookTemplate}
                onDeleteCustomHookTemplate={onDeleteCustomHookTemplate}
                assets={assets}
                onToggleHookHeader={onToggleHookHeader}
                onUpdateOverlay={onUpdateOverlay}
                onReplaceOverlay={onReplaceOverlay}
                onDeleteOverlay={onDeleteOverlay}
              />
            ) : selection?.type === 'sticker' && selectedSticker ? (
              <StickerInspector
                sticker={selectedSticker}
                onUpdateSticker={onUpdateSticker}
                onDeleteSticker={onDeleteSticker}
                totalDuration={totalDuration}
              />
            ) : selection?.type === 'effect' && selectedEffect ? (
              <EffectInspector
                effect={selectedEffect}
                effectAsset={selectedEffectAsset}
                onUpdateEffect={onUpdateEffect}
                onDeleteEffect={onDeleteEffect}
                totalDuration={totalDuration}
              />
            ) : selection?.type === 'cutout' ? (
              <CutoutInspector
                backgroundIsolation={backgroundIsolation}
                backgroundIsolationStatus={backgroundIsolationStatus}
                onToggleBackgroundIsolation={onToggleBackgroundIsolation}
                cutoutPreviewMode={cutoutPreviewMode}
                onCutoutPreviewModeChange={onCutoutPreviewModeChange}
                subjectPoints={subjectPoints}
                subjectPickMode={subjectPickMode}
                onToggleSubjectPickMode={onToggleSubjectPickMode}
                onClearSubjectPoints={onClearSubjectPoints}
              />
            ) : selectedSeg ? (
              <>
                {multiSelectCount > 1 && (
                  <div
                    data-testid="inspector-multi-select"
                    role="status"
                    className="mb-3 rounded-xl border border-[#D97757]/40 bg-[#D97757]/10 p-2.5 text-xs text-[#E89274]"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold">เลือก {multiSelectCount} คลิป</span>
                      {canPasteSettings && (
                        <button
                          type="button"
                          onClick={onPasteSettings}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#D97757] hover:bg-[#E89274] text-white font-medium transition-colors cursor-pointer text-xs shadow-sm"
                          title="วางการตั้งค่าที่คัดลอกไว้ลงทุกคลิปที่เลือก (Ctrl+Alt+V)"
                        >
                          <ClipboardPaste className="w-3.5 h-3.5" />
                          <span>วางการตั้งค่า ({multiSelectCount})</span>
                        </button>
                      )}
                    </div>
                    <span className="text-[#C9C3BB] block mt-1">
                      · แผงนี้แก้เฉพาะคลิปหลักที่ไฮไลต์เข้ม · กด Delete ลบทั้งหมด · Esc ยกเลิกการเลือก
                    </span>
                  </div>
                )}
                <ClipInspector
                  selectedSeg={selectedSeg}
                  onClipChange={onClipChange}
                  clipList={clipList}
                  onPatchAllClips={onPatchAllClips}
                  onCopySettings={onCopySettings}
                  onPasteSettings={onPasteSettings}
                  canPasteSettings={canPasteSettings}
                />
              </>
            ) : (
              <div className="space-y-3">
                <CutoutInspector
                  backgroundIsolation={backgroundIsolation}
                  backgroundIsolationStatus={backgroundIsolationStatus}
                  onToggleBackgroundIsolation={onToggleBackgroundIsolation}
                  cutoutPreviewMode={cutoutPreviewMode}
                  onCutoutPreviewModeChange={onCutoutPreviewModeChange}
                  subjectPoints={subjectPoints}
                  subjectPickMode={subjectPickMode}
                  onToggleSubjectPickMode={onToggleSubjectPickMode}
                  onClearSubjectPoints={onClearSubjectPoints}
                />
                <div className="py-6 px-4 text-center rounded-2xl border border-white/[0.08] bg-black/40 space-y-3">
                  <div className="w-10 h-10 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center mx-auto text-[#25F4EE]">
                    <SlidersHorizontal className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-white">แผงควบคุมคุณสมบัติ (Inspector)</h4>
                    <p className="text-[11px] text-slate-400 max-w-[260px] mx-auto leading-relaxed">
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
            </div>
          )}
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════
            TAB 2: SUBTITLE TRANSCRIPT LIST
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'cues' && (
          <CuesTranscriptInspector
            cuesList={cuesList}
            playhead={playhead}
            selectedCaption={selectedCaption}
            assets={assets}
            onSelectCue={onSelectCue}
            onSeek={onSeek}
            onCaptionChange={onCaptionChange}
            onSplitCue={onSplitCue}
            onMergeCue={onMergeCue}
            onMergeWithPrevious={onMergeWithPrevious}
            onDeleteCue={onDeleteCue}
            onInsertCueAfter={onInsertCueAfter}
            onReorderCues={onReorderCues}
            onBatchFindAndReplace={onBatchFindAndReplace}
            onBatchFormatClean={onBatchFormatClean}
            onCloseAllCaptionGaps={onCloseAllCaptionGaps}
            onResetSubtitleTimings={onResetSubtitleTimings}
            onAddTextAtPlayhead={onAddTextAtPlayhead}
          />
        )}

        {/* ═════════════════════════════════════════════════════════════════════
            TAB 3: PROJECT OVERVIEW
           ═════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'overview' && (
          <ProjectInspector
            style={style}
            totalDuration={totalDuration}
            audioDuration={audioDuration}
            trackMix={trackMix}
            onTrackMix={onTrackMix}
            onStyleChange={onStyleChange}
          />
        )}
      </div>
    </div>
  );
}
