import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { TransitionIcon } from '../../lib/transitionIcons';
import {
  Eye, EyeOff, Film, MessageSquare, Music, Plus, Scissors, Smile, Sparkles, Type, Volume2, VolumeX, Waves, X
} from 'lucide-react';
import TimelineClip from './TimelineClip';
import TimelineRuler from './timeline/TimelineRuler';
import { beatsWithinSpan } from '../../lib/beatGrid.js';
import TimelinePlayhead from './timeline/TimelinePlayhead';
import TimelineContextMenu from './timeline/TimelineContextMenu';
import { EffectTrackLabel, EffectTrackLane } from './timeline/EffectTrack';
import TimelineIntervalItem from './timeline/TimelineIntervalItem';
import TrackLabel from './timeline/TrackLabel';
import TransitionDurationControl from './timeline/TransitionDurationControl';
import { TRANSITION_POPOVER_OPTIONS } from '../../lib/transitionControls.js';
import { previewOnlyLaneLabel, previewOnlyEyeTitle } from '../../lib/laneVisibilityLabel.js';
import { useTimelineKeyboard } from '../../hooks/useTimelineKeyboard';
import { clampPxPerSec, scrollLeftForAnchor } from '../../lib/timelineZoom.js';
import { useTimelineDrag } from '../../hooks/useTimelineDrag';
import {
  overlayLabel,
  packTextOverlays,
  packStickers,
  tickStep,
  indexFromX,
} from '../../lib/timelineTrackModel';
import { CLIP_DRAG_TYPE, TEXT_TEMPLATE_DRAG_TYPE } from './AssetPanel';
import { getAudioPeaks, MAX_DECODE_SECONDS } from '../../lib/audioPeaks';
import { formatTimecode, FADE_DURATION } from '../../lib/timelineMath';
import { voiceCutMarkers } from '../../lib/rippleUi';
import { resolveBackgroundIsolationConfig, scopedArtifactCoversClip, subjectLayerForOverlay } from '../../lib/backgroundIsolationPreview.js';

const RULER_H = 22;
const WAVE_COLUMNS = 1200;

// Row heights on a 4px scale, with the video track deliberately the tall one:
// it is what the eye lands on first, and everything else supports it.
// The banner's length, clamped in one place. The inspector's slider used to
// allow 1.5-5.0s while this lane's handle allowed 1.0-8.0s, so dragging past
// five seconds left the slider pinned and reading the wrong number.
export const HOOK_MIN_DURATION = 1.0;
export const HOOK_MAX_DURATION = 8.0;

const VIDEO_H = 64;
const HOOK_H = 28;
const CUTOUT_H = 26;
const STICKER_H = 28;
const EFFECT_H = 28;
const CAPTION_H = 28;
const TEXT_OVERLAY_H = 28;
const STEM_H = 24;

// Rhythm. Rows inside a group sit close; the three groups (picture, overlays,
// audio) are pushed apart. One repeated gap made eight rows read as a single
// undifferentiated stack -- the grouping had to be inferred rather than seen.
const ROW_GAP = 2;
const GROUP_GAP = 10;
const TRACK_TOP = 6;
// One lane per stem now that the preview plays them separately: a single
// merged "audio" lane could only ever show the mix, which most projects no
// longer have, and gave nothing to mute or solo.
// Beat markers reuse the project's highlight yellow (the same #FFE600 the
// kinetic captions use) so "the app is pointing at this moment" reads the
// same way everywhere.
const BEAT_MARKER_COLOUR = '#FFE600';

const STEMS = [
  { key: 'voice', label: 'พากย์', colour: '#8FBF9F', ring: '#33463A', bg: '#242A26' },
  { key: 'bgm', label: 'เพลง', colour: '#9FB4D8', ring: '#33405A', bg: '#232833' },
  { key: 'sfx', label: 'SFX', colour: '#D8C39F', ring: '#524731', bg: '#302B22' },
  { key: 'clip', label: 'คลิป', colour: '#C79FD8', ring: '#4A3155', bg: '#2C2333' },
];

// The label gutter and the lanes are two columns describing the same rows, so
// they read their geometry from one list. They used to space themselves
// differently -- `gap-1` on the gutter against per-lane `mt-1` -- and any row
// that forgot its margin slid the labels out from under their lanes for every
// row below it. With four audio lanes that drift reached 12px and the names no
// longer sat beside their own waveforms.
const TRACK_ROWS = [
  { key: 'video', group: 'picture', height: VIDEO_H },
  { key: 'hook', group: 'overlay', height: HOOK_H },
  { key: 'cutout', group: 'picture', height: CUTOUT_H, optional: true },
  { key: 'sticker', group: 'overlay', height: STICKER_H, optional: true },
  { key: 'effect', group: 'overlay', height: EFFECT_H, optional: true },
  { key: 'caption', group: 'overlay', height: CAPTION_H },
  { key: 'text', group: 'overlay', height: TEXT_OVERLAY_H, optional: true },
  ...STEMS.map((s) => ({ key: s.key, group: 'audio', height: STEM_H })),
];

/**
 * Height and top margin for every visible row, in order. `heights` overrides a
 * row whose height depends on content; `present` drops an optional row.
 */
function layoutRows({ heights = {}, present = {}, collapsed = {} } = {}) {
  const rows = [];
  let prevGroup = null;
  for (const row of TRACK_ROWS) {
    if (row.optional && !present[row.key]) continue;
    // A collapsed group keeps its first row as the group's own handle, so the
    // fold is reversible from the same place it was folded.
    if (collapsed[row.group] && prevGroup === row.group) continue;
    const height = heights[row.key] ?? row.height;
    const marginTop = prevGroup === null ? 0 : (row.group === prevGroup ? ROW_GAP : GROUP_GAP);
    rows.push({ ...row, height, marginTop });
    prevGroup = row.group;
  }
  return rows;
}

/**
 * Height the track area needs to show every row without scrolling, chrome
 * included. The dock's own min/default heights are derived from this: they used
 * to be hand-tuned numbers, so adding the four audio lanes left the video track
 * below the fold with vertical overflow hidden -- unreachable, with nothing on
 * screen to say it was there.
 */
export function tracksFitHeight({ textOverlays = false, audioCollapsed = false, sticker = false, effect = false } = {}) {
  const rows = layoutRows({
    present: { text: textOverlays, sticker, effect },
    collapsed: { audio: audioCollapsed },
  });
  const tracks = rows.reduce((sum, r) => sum + r.height + r.marginTop, 0);
  return RULER_H + TRACK_TOP + tracks + TRACK_BOTTOM;
}

// Room under the last lane for the horizontal scrollbar, plus a little air so
// the bottom row is not flush against it.
const TRACK_BOTTOM = 18;
const GUTTER = 144;        // left label column
const GUTTER_DENSE = 120;  // phones: the clips need the width more than the names do

/**
 * A mute/solo chip. The mark stays small because the gutter is narrow, but the
 * hit area is padded out to something a pointer can actually catch.
 */
function MixButton({ active, pressed, activeClass, onClick, title, children }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onClick?.(); }}
      title={title}
      // `active` is how it looks, `pressed` is what it is. A track silenced
      // because another one is soloed reads as silent on screen, but its mute
      // button is not pressed -- announcing it as pressed would tell a screen
      // reader the user muted something they never touched.
      aria-pressed={pressed ?? active}
      className={`grid h-[18px] w-[18px] place-items-center rounded text-[10px] font-semibold leading-none
        transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-1
        focus-visible:outline-[#8FBF9F] ${
        active ? activeClass : 'text-[#6F6A64] hover:bg-[#2C2B27] hover:text-[#EDE9E3]'
      }`}
    >
      {children}
    </button>
  );
}

export default function Timeline({
  segments,
  totalDuration,
  audioDuration,
  cues,
  bgmLabel,
  // { bpm, major: number[], minor: number[] } or null when the track has not
  // been analyzed. Defaulted so a caller that never passes it renders no
  // markers rather than throwing.
  beatGrid = null,
  stemUrls = {},
  trackMix = null,
  onTrackMix,
  audioCollapsed = false,
  onToggleAudioGroup,
  dense = false,
  pxPerSec,
  playhead,
  selection,
  onSeek,
  onSelectClip,
  onSelectCaption,
  onTrim,
  onTrimBegin,
  onTrimEnd,
  onToggleTransition,
  onCaptionShift,
  onReorder,
  onReorderSilent,
  onDropClip,
  onDropTextTemplate,
  // Newer shell prop names. Both sets are accepted so the timeline keeps
  // working whichever shape the shell passes.
  onSelect,
  // Multi-select: every selected clip id (primary included), and the handler for
  // Ctrl/Shift+click -> (clipId, 'toggle' | 'range' | 'focus'). Both optional.
  selectedClipIds = [],
  onSelectClipWithMode,
  // Copy / paste clip settings from the clip context menu (all optional).
  onCopySettings,
  onPasteSettings,
  canPasteSettings = false,
  onClipChange,
  onCaptionChange,
  onBeginDrag,
  onEndDrag,
  onZoom,
  // (px/s) => void. When given, Ctrl+wheel zooms continuously around the cursor.
  onZoomTo,
  viewportRef,
  audioUrl,
  isAudioMuted = false,
  onToggleMuteAudio,
  isCaptionHidden = false,
  onToggleHideCaption,
  onSplit,
  onDuplicate,
  onDelete,
  onToggleMirror,
  onAdjustTrim,
  // Edge/body drags snap to these (clip boundaries, playhead, audio end).
  // Both default to "no snapping" so the timeline still works if a caller
  // doesn't wire them up.
  snapCandidates: snapPoints = [],
  snapFunction = (t) => t,
  snapEnabled = true,
  onCuesChange,
  onCaptionRippleShift,
  overlays = [],
  onUpdateOverlay,
  onSelectOverlay,
  onToggleOverlayKindHidden,
  onEnsureHookOverlay,
  onAddTextOverlay,
  stickerStyle,
  stickers = [],
  onUpdateSticker,
  stickerAssets = [],
  onSelectSticker,
  isStickerHidden = false,
  onToggleHideSticker,
  effects = [],
  effectAssets = [],
  onSelectEffect,
  onUpdateEffect,
  backgroundIsolation = null,
  cutoutIntervals = {},
  cutoutArtifactAvailability = {},
  cutoutProcessingClipIds = [],
  cutoutQueuedClipIds = [],
  isCutoutHidden = false,
  onToggleCutout,
  // Ripple delete: the ACTIVE voice edit (null when none / stale) gets a thin
  // orange marker per cut on the voice lane; `rangeMark` is the I / O pair.
  voiceEdit = null,
  rangeMark = null,
}) {
  // The banner and the text overlays are one array; the two lanes are a view
  // of it, so a trim on either takes the same clamp and the same handler.
  // The banner's own slider used to allow 1.5-5.0s while this lane's handle
  // allowed 1.0-8.0s, and dragging past 5s made the slider read wrong.
  const hookOverlay = (overlays || []).find((o) => o.kind === 'hook') || null;
  const textOverlays = (overlays || []).filter((o) => o.kind === 'text');
  const showHookHeader = !!hookOverlay && !hookOverlay.hidden;
  const isTextOverlayHidden = textOverlays.length > 0 && textOverlays.every((o) => o.hidden);
  const hasCutout = (backgroundIsolation?.enabled === true) || (segments || []).some((s) => s.clip?.background_isolation?.enabled === true);
  const scopedCutoutWindows = backgroundIsolation?.scope_mode === 'behind_text_windows'
    ? (segments || []).flatMap((seg) => {
      const intervals = (overlays || []).filter((overlay) => !overlay?.hidden
        && subjectLayerForOverlay(overlay) === 'behind'
        && ((Array.isArray(overlay.tiers) && overlay.tiers.some((tier) => String(tier?.text || '').trim()))
          || String(overlay.text || '').trim()))
        .map((overlay) => ({ start: Math.max(seg.segStart, Number(overlay.start)),
          end: Math.min(seg.segEnd, Number(overlay.end)) }))
        .filter(({ start, end }) => Number.isFinite(start) && Number.isFinite(end) && end > start)
        .sort((a, b) => a.start - b.start || a.end - b.end);
      const merged = [];
      for (const interval of intervals) {
        const last = merged.at(-1);
        if (last && interval.start <= last.end + 1e-9) last.end = Math.max(last.end, interval.end);
        else merged.push({ ...interval });
      }
      const config = resolveBackgroundIsolationConfig(seg.clip, {
        ...backgroundIsolation,
        active_clip_ids: Object.keys(cutoutIntervals),
        active_intervals_by_clip: cutoutIntervals,
      });
      const id = config?.artifact?.id || config?.artifact?.sequence_id;
      const ready = config?.scope_mode === 'behind_text_windows'
        && config?.artifact?.status === 'ready'
        && JSON.stringify(config?.active_intervals) === JSON.stringify(cutoutIntervals[seg.clip?.id])
        && scopedArtifactCoversClip(config, seg.clip, { sourceDurations: { [seg.clip.id]: seg.srcDur } })
        && cutoutArtifactAvailability[id] === true;
      return merged.map((interval) => ({ ...interval, seg, ready }));
    }) : [];
  const onSelectTextOverlay = (id) => onSelectOverlay?.(id, 'text');
  const onSelectHook = () => (hookOverlay ? onSelectOverlay?.(hookOverlay.id, 'hook') : null);
  const onToggleHookHeader = () => onEnsureHookOverlay?.();
  const onToggleHideTextOverlay = () => onToggleOverlayKindHidden?.('text');
  const onTextOverlayChange = (id, patch, silent) => onUpdateOverlay?.(id, patch, silent);
  const deselectAll = () => {
    if (onSelectClip) onSelectClip(null);
    if (onSelectCaption) onSelectCaption(null);
    if (onSelectTextOverlay) onSelectTextOverlay(null);
    onSelect?.(null);
  };

  const selectClip = (id, mode) => {
    // Ctrl/Shift+click and right-click on a selected clip adjust the set instead
    // of replacing it (the shell seeks and sets the primary itself).
    if (mode && mode !== 'replace' && onSelectClipWithMode) {
      onSelectClipWithMode(id, mode);
      return;
    }
    if (onSelectClip) onSelectClip(id);
    else onSelect?.({ type: 'clip', id });
    const seg = segments.find((sg) => sg.clip?.id === id);
    if (seg && typeof seg.segStart === 'number') {
      const segEnd = typeof seg.segEnd === 'number' ? seg.segEnd : seg.segStart + 2.0;
      if (playhead < seg.segStart - 0.05 || playhead > segEnd + 0.05) {
        onSeek?.(seg.segStart);
      }
    }
  };
  const selectCaption = (uid) => {
    if (onSelectCaption) onSelectCaption(uid);
    else onSelect?.({ type: 'caption', id: uid });
    const cue = cues.find((c) => c._uid === uid || c.id === uid);
    if (cue && typeof cue.start === 'number') {
      const cueEnd = typeof cue.end === 'number' ? cue.end : cue.start + 2.0;
      if (playhead < cue.start - 0.05 || playhead > cueEnd + 0.05) {
        onSeek?.(cue.start);
      }
    }
  };
  const selectTextOverlay = (id) => {
    if (onSelectTextOverlay) onSelectTextOverlay(id);
    else onSelect?.({ type: 'text_overlay', id });
    const item = textOverlays.find((t) => t.id === id);
    if (item && typeof item.start === 'number') {
      const itemEnd = typeof item.end === 'number' ? item.end : item.start + 2.0;
      if (playhead < item.start - 0.05 || playhead > itemEnd + 0.05) {
        onSeek?.(item.start);
      }
    }
  };
  const trimClip = (id, patch) => (onTrim ? onTrim(id, patch) : onClipChange?.(id, patch, true));
  const shiftCaption = (uid, patch) => (onCaptionShift ? onCaptionShift(uid, patch) : onCaptionChange?.(uid, patch, true));
  const shiftTextOverlay = (id, patch) => (onTextOverlayChange ? onTextOverlayChange(id, patch, true) : null);
  const dragBegin = () => (onTrimBegin || onBeginDrag)?.();
  const dragEnd = () => (onTrimEnd || onEndDrag)?.();
  const toggleTransition = (id) => {
    if (onToggleTransition) { onToggleTransition(id); return; }
    const seg = segments.find((sg) => sg.clip.id === id);
    const current = seg?.clip.transition_in || 'cut';
    onClipChange?.(id, { transition_in: current !== 'cut' ? 'cut' : 'fade' });
  };
  const reorder = (id, dir, silent) => {
    if (silent && onReorderSilent) { onReorderSilent(id, dir); return true; }
    if (onReorder) { onReorder(id, dir); return true; }
    return false;
  };
  const laneRef = useRef(null);
  const scrollRef = useRef(null);
  const [dropIndex, setDropIndex] = useState(null);
  const [templateDropAt, setTemplateDropAt] = useState(null);
  const stemCanvasRefs = useRef({});
  const [stemPeaks, setStemPeaks] = useState({});
  const [transitionMenuClipId, setTransitionMenuClipId] = useState(null);
  const [transitionMenuPosition, setTransitionMenuPosition] = useState(null);
  const transitionTriggerRef = useRef(null);
  const closeTransitionMenu = () => {
    setTransitionMenuClipId(null);
    transitionTriggerRef.current?.focus();
  };
  useEffect(() => {
    if (!transitionMenuClipId) return undefined;
    const dismiss = () => setTransitionMenuClipId(null);
    const scroller = scrollRef.current;
    window.addEventListener('resize', dismiss);
    scroller?.addEventListener('scroll', dismiss);
    return () => {
      window.removeEventListener('resize', dismiss);
      scroller?.removeEventListener('scroll', dismiss);
    };
  }, [transitionMenuClipId]);
  const [contextMenu, setContextMenu] = useState(null);
  const [activeSnapGuide, setActiveSnapGuide] = useState(null);
  const [rippleFeedback, setRippleFeedback] = useState(null);
  const rippleTimerRef = useRef(null);

  const handleSnapGuide = (guide) => {
    setActiveSnapGuide(guide);
  };

  const handleRippleTriggered = ({ count, type = 'caption' }) => {
    if (rippleTimerRef.current) clearTimeout(rippleTimerRef.current);
    setRippleFeedback({
      active: true,
      text: `🧲 Magnetic Ripple: จัดเรียง ${count} ${type === 'caption' ? 'ซับไตเติล' : 'คลิป'} ต่อเนื่องไร้ช่องว่าง`,
    });
    rippleTimerRef.current = setTimeout(() => {
      setRippleFeedback(null);
    }, 1800);
  };

  useEffect(() => () => {
    if (rippleTimerRef.current) clearTimeout(rippleTimerRef.current);
  }, []);
  const hasTextOverlays = Boolean(textOverlays && textOverlays.length > 0);
  const effectiveStickers = useMemo(() => {
    if (Array.isArray(stickers) && stickers.length > 0) return stickers;
    if (stickerStyle?.badge) {
      return [{
        id: 'sticker_badge',
        badge: stickerStyle.badge,
        start: stickerStyle.startTime ?? 0.5,
        end: stickerStyle.endTime ?? (totalDuration || 15),
        scale: stickerStyle.scale ?? 1,
        normX: stickerStyle.normX,
        normY: stickerStyle.normY,
      }];
    }
    return [];
  }, [stickers, stickerStyle, totalDuration]);

  const hasSticker = effectiveStickers.length > 0;

  // Effects have no legacy single-slot fallback (unlike stickers' style.stickerBadge
  // back-compat path above) -- this is a new feature with nothing to stay
  // compatible with, so the array is used as-is.
  const effectiveEffects = useMemo(
    () => (Array.isArray(effects) ? effects.filter((fx) => fx && !fx.hidden) : []),
    [effects],
  );
  const hasEffects = effectiveEffects.length > 0;

  // Keep repeated lane derivations out of the render maps. These collections
  // are stable for a given segment list, while playhead/selection updates can
  // re-render the timeline frequently.
  const transitionSegments = useMemo(() => segments.slice(1), [segments]);
  const clipAudioSegments = useMemo(
    () => segments.filter((s) => Number(s.clip.volume) > 0),
    [segments],
  );
  const stickerAssetIndex = useMemo(() => {
    const byName = new Map();
    const byPath = new Map();
    (Array.isArray(stickerAssets) ? stickerAssets : []).forEach((asset) => {
      if (asset?.name && !byName.has(asset.name)) byName.set(asset.name, asset);
      if (asset?.path && !byPath.has(asset.path)) byPath.set(asset.path, asset);
    });
    return { byName, byPath };
  }, [stickerAssets]);

  // Auto-stacking multi-layer calculation for overlapping text overlays
  const { packedTextOverlays, textLaneCount } = useMemo(
    () => packTextOverlays(textOverlays),
    [textOverlays],
  );

  const { packedStickers, stickerLaneCount } = useMemo(
    () => packStickers(effectiveStickers),
    [effectiveStickers],
  );

  // packStickers is a generic start/end interval packer (see
  // lib/timelineTrackModel.js) -- reused as-is rather than duplicating it
  // under an "effect" name.
  const { packedStickers: packedEffects, stickerLaneCount: effectLaneCount } = useMemo(
    () => packStickers(effectiveEffects),
    [effectiveEffects],
  );

  const TEXT_LANE_ROW_H = 26;
  const STICKER_LANE_ROW_H = 26;
  const EFFECT_LANE_ROW_H = 26;
  const textTrackHeight = Math.max(TEXT_OVERLAY_H, textLaneCount * TEXT_LANE_ROW_H + 4);
  const stickerTrackHeight = Math.max(STICKER_H, stickerLaneCount * STICKER_LANE_ROW_H + 4);
  const effectTrackHeight = Math.max(EFFECT_H, effectLaneCount * EFFECT_LANE_ROW_H + 4);

  // Geometry for every row, resolved once. Both the label gutter and the lanes
  // spread the same object, so a row cannot be spaced differently on the two
  // sides -- which is exactly how the labels drifted out from under their lanes.
  const gutterW = dense ? GUTTER_DENSE : GUTTER;

  const rows = useMemo(
    () => layoutRows({
      heights: { text: textTrackHeight, sticker: stickerTrackHeight, effect: effectTrackHeight },
      present: { text: hasTextOverlays, sticker: hasSticker, effect: hasEffects, cutout: hasCutout },
      collapsed: { audio: audioCollapsed },
    }),
    [textTrackHeight, stickerTrackHeight, effectTrackHeight, hasTextOverlays, hasSticker, hasEffects, hasCutout, audioCollapsed],
  );
  const visibleStems = audioCollapsed ? STEMS.slice(0, 1) : STEMS;
  const rowStyleOf = useMemo(() => {
    const byKey = {};
    rows.forEach((r) => { byKey[r.key] = { height: r.height, marginTop: r.marginTop }; });
    return byKey;
  }, [rows]);
  const rowStyle = (key) => rowStyleOf[key] || { height: 0, marginTop: 0 };
  const tracksHeight = rows.reduce((sum, r) => sum + r.height + r.marginTop, 0);

  // Ctrl/Cmd+wheel: continuous zoom that keeps the time under the cursor
  // still. Several wheel events can land before React re-renders, so they
  // accumulate into one pending anchor measured against the DOM as it is
  // (old px/s, old scrollLeft); the layout effect below applies it once the
  // wider/narrower content exists.
  const zoomAnchorRef = useRef(null);
  const skipFollowOnceRef = useRef(false);
  const pxPerSecRef = useRef(pxPerSec);
  pxPerSecRef.current = pxPerSec;
  const handleZoomAt = useCallback((factor, anchorX) => {
    const el = scrollRef.current;
    if (!el || !onZoomTo) return;
    const pending = zoomAnchorRef.current;
    const base = pending || { pxPerSec: pxPerSecRef.current, scrollLeft: el.scrollLeft };
    const from = pending ? pending.nextPxPerSec : pxPerSecRef.current;
    const next = clampPxPerSec(from * factor);
    if (Math.abs(next - from) < 1e-9) return;
    zoomAnchorRef.current = { ...base, nextPxPerSec: next, anchorX };
    onZoomTo(next);
  }, [onZoomTo]);
  useLayoutEffect(() => {
    const anchor = zoomAnchorRef.current;
    const el = scrollRef.current;
    if (!anchor || !el) return;
    if (Math.abs(anchor.nextPxPerSec - pxPerSec) > 1e-9) return; // another zoom source won
    zoomAnchorRef.current = null;
    el.scrollLeft = scrollLeftForAnchor({ ...anchor, gutter: gutterW });
    skipFollowOnceRef.current = true;
  }, [pxPerSec]); // eslint-disable-line react-hooks/exhaustive-deps

  // Global listeners for Escape, click outside, and native Ctrl/Cmd + wheel zoom
  useTimelineKeyboard({
    scrollRef,
    onZoom,
    onZoomAt: onZoomTo ? handleZoomAt : undefined,
    transitionMenuClipId,
    setTransitionMenuClipId,
    contextMenu,
    setContextMenu,
  });

  const handleClipContextMenu = (e, seg) => {
    setTransitionMenuClipId(null);
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      seg,
    });
  };

  // Share the scroll container with the parent so "fit to screen" can
  // measure the real track width instead of guessing a viewport size.
  //
  // Guarded on actual visibility: the mobile and desktop layout trees are
  // hidden from each other with CSS, not unmounted, so both Timelines can be
  // alive at once. An offscreen one has clientWidth 0, and letting it claim
  // the shared ref would make "fit to screen" measure nothing and quietly do
  // nothing at all.
  useEffect(() => {
    const el = scrollRef.current;
    if (viewportRef && el && el.offsetParent !== null) viewportRef.current = el;
  }, [viewportRef, playhead]);

  // Keep the playhead on screen while playing. Past ~12 clips the content is
  // wider than the track, and nothing in here ever touched scrollLeft, so the
  // playhead just walked off the right edge and stayed there.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || el.offsetParent === null) return;
    // A cursor-anchored wheel zoom just placed the view on purpose.
    if (skipFollowOnceRef.current) { skipFollowOnceRef.current = false; return; }
    const x = gutterW + playhead * pxPerSec;
    const left = el.scrollLeft;
    const right = left + el.clientWidth;
    const margin = 80;
    if (x < left + margin) {
      el.scrollLeft = Math.max(0, x - margin);
    } else if (x > right - margin) {
      el.scrollLeft = x - el.clientWidth + margin;
    }
  }, [playhead, pxPerSec]);

  // Peaks per stem, from the stem's own file. The old single waveform decoded
  // the mixed file, which 1-Click no longer writes -- the lane just went blank
  // with nothing to say why.
  useEffect(() => {
    let alive = true;
    const wanted = { voice: stemUrls.voice || null, bgm: stemUrls.bgm || null };
    Object.entries(wanted).forEach(([key, url]) => {
      if (!url) {
        setStemPeaks((prev) => (prev[key] ? { ...prev, [key]: null } : prev));
        return;
      }
      getAudioPeaks(url, WAVE_COLUMNS).then((info) => {
        if (alive) setStemPeaks((prev) => ({ ...prev, [key]: info }));
      });
    });
    return () => { alive = false; };
  }, [stemUrls.voice, stemUrls.bgm]);

  useEffect(() => {
    STEMS.forEach(({ key, colour }) => {
      const canvas = stemCanvasRefs.current[key];
      const info = stemPeaks[key];
      if (!canvas || !info?.peaks) return;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = colour;
      ctx.globalAlpha = 0.55;
      const mid = canvas.height / 2;
      for (let i = 0; i < WAVE_COLUMNS; i++) {
        const min = info.peaks[i * 2];
        const max = info.peaks[i * 2 + 1];
        const top = mid - max * mid;
        const bottom = mid - min * mid;
        ctx.fillRect(i, top, 1, Math.max(1, bottom - top));
      }
      ctx.globalAlpha = 1;
    });
  }, [stemPeaks]);

  // Dropping a clip from the media bin. The insert position is whichever
  // boundary the pointer is nearest, so a drop reads like where it landed.
  // Dragging, trimming, and scrubbing controller
  const {
    timeFromEvent,
    startScrub,
    moveScrub,
    endScrub,
    handleTrackAreaPointerDown,
    onBodyDragStart,
    onBodyDragMove,
    onBodyDragEnd,
    startTrim,
    moveTrim,
    endTrim,
    startCaptionBodyDrag,
    moveCaptionBodyDrag,
    endCaptionBodyDrag,
    startTextTrim,
    moveTextTrim,
    endTextTrim,
    startTextBodyDrag,
    moveTextBodyDrag,
    endTextBodyDrag,
    startHookTrim,
    moveHookTrim,
    endHookTrim,
    startStickerTrim,
    moveStickerTrim,
    endStickerTrim,
    startStickerBodyDrag,
    moveStickerBodyDrag,
    endStickerBodyDrag,
    startEffectTrim,
    moveEffectTrim,
    endEffectTrim,
    startEffectBodyDrag,
    moveEffectBodyDrag,
    endEffectBodyDrag,
  } = useTimelineDrag({
    laneRef,
    pxPerSec,
    totalDuration,
    audioDuration,
    segments,
    cues,
    hookOverlay,
    stickerStyle,
    onUpdateSticker,
    onUpdateEffect,
    snapEnabled,
    snapPoints,
    snapFunction,
    onSeek,
    deselectAll,
    dragBegin,
    dragEnd,
    shiftCaption,
    onCuesChange,
    onCaptionRippleShift,
    shiftTextOverlay,
    onUpdateOverlay,
    reorder,
    playhead,
    onSnapGuide: handleSnapGuide,
    onRippleTriggered: handleRippleTriggered,
  });

  // Dropping a clip from the media bin. The insert position is whichever
  // boundary the pointer is nearest, so a drop reads like where it landed.
  const dragHasClip = (e) => Array.from(e.dataTransfer?.types || []).includes(CLIP_DRAG_TYPE);
  const onDragOverTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDropIndex(indexFromX(e.clientX, laneRef.current?.getBoundingClientRect(), pxPerSec, segments));
  };
  const onDropTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    const at = indexFromX(e.clientX, laneRef.current?.getBoundingClientRect(), pxPerSec, segments);
    setDropIndex(null);
    try {
      onDropClip?.(JSON.parse(e.dataTransfer.getData(CLIP_DRAG_TYPE)), at);
    } catch (err) { /* malformed payload -- nothing to insert */ }
  };

  // A card from the template gallery, dropped where it should start. The
  // gallery has always set this drag type and nothing has ever read it, so
  // dragging a card onto the timeline did nothing at all.
  const dragHasTemplate = (e) =>
    Array.from(e.dataTransfer?.types || []).includes(TEXT_TEMPLATE_DRAG_TYPE);
  const onDragOverContent = (e) => {
    if (!dragHasTemplate(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setTemplateDropAt(Math.max(0, timeFromEvent(e) ?? 0));
  };
  const onDropContent = (e) => {
    if (!dragHasTemplate(e)) return;
    e.preventDefault();
    const at = Math.max(0, timeFromEvent(e) ?? 0);
    setTemplateDropAt(null);
    try {
      onDropTextTemplate?.(JSON.parse(e.dataTransfer.getData(TEXT_TEMPLATE_DRAG_TYPE)), at);
    } catch (err) { /* malformed payload -- nothing to insert */ }
  };

  const contentWidth = Math.max(audioDuration || 0, totalDuration, 1) * pxPerSec + 240;

  // Beats clamped to the music lane's own span. A BGM file is usually longer
  // than the sequence and is looped by the renderer, so drawing every beat in
  // the source would paint markers far past the end of the lane. Guarded
  // against a non-finite or negative timestamp too: one bad value from
  // analysis would otherwise place a marker at a nonsense offset.
  const beatMarkers = useMemo(
    () => beatsWithinSpan(beatGrid, Math.max(audioDuration || 0, totalDuration || 0)),
    [beatGrid, audioDuration, totalDuration],
  );
  const step = tickStep(pxPerSec);
  const ticks = useMemo(() => {
    const span = Math.max(totalDuration, audioDuration || 0);
    const out = [];
    for (let t = 0; t <= span + step; t += step) out.push(t);
    return out;
  }, [totalDuration, audioDuration, step]);

  const sfxMarkers = (cues || []).filter((c) => c.sfx);
  // Where each ripple cut joined the voice, on the program clock.
  const voiceCutMarks = useMemo(() => voiceCutMarkers(voiceEdit), [voiceEdit]);

  return (
    <div className="flex h-full flex-col bg-[#1C1B19]">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <div
          style={{ width: contentWidth, minWidth: '100%' }}
          className="relative"
          onDragOver={onDragOverContent}
          onDragLeave={() => setTemplateDropAt(null)}
          onDrop={onDropContent}
        >
          {templateDropAt !== null && (
            <div
              className="pointer-events-none absolute inset-y-0 z-30 w-0.5 bg-[#25F4EE] shadow-[0_0_8px_rgba(37,244,238,0.8)]"
              style={{ left: templateDropAt * pxPerSec }}
            >
              <span className="absolute -top-0.5 left-1 rounded bg-[#25F4EE] px-1 py-0.5 font-mono text-[9px] font-bold text-black">
                {templateDropAt.toFixed(1)}s
              </span>
            </div>
          )}

          {/* Ruler: click or drag to scrub */}
          <TimelineRuler
            gutterW={gutterW}
            rulerHeight={RULER_H}
            ticks={ticks}
            pxPerSec={pxPerSec}
            onStartScrub={startScrub}
            onMoveScrub={moveScrub}
            onEndScrub={endScrub}
            rangeMark={rangeMark}
          />

          {/* Track lanes */}
          <div className="flex" style={{ paddingTop: TRACK_TOP, paddingBottom: TRACK_BOTTOM }}>
            <div className="flex flex-shrink-0 flex-col">
              <div style={rowStyle('video')} className="flex items-center">
                <TrackLabel icon={Film} width={gutterW} slotWidth={dense ? 14 : 26}>วิดีโอ</TrackLabel>
              </div>
              <div style={rowStyle('hook')} className="flex items-center">
                <TrackLabel
                  width={gutterW}
                  slotWidth={dense ? 14 : 26}
                  icon={Sparkles}
                  action={
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onToggleHookHeader?.(); }}
                      title={showHookHeader ? 'คลิกเพื่อซ่อนป้ายฮุกบนพรีวิว' : 'คลิกเพื่อแสดงป้ายฮุกบนพรีวิว'}
                      className={`p-1 rounded transition-colors ${
                        !showHookHeader
                          ? 'text-amber-400 hover:bg-amber-400/20'
                          : 'text-[#E6C24A] hover:bg-[#E6C24A]/20'
                      }`}
                    >
                      {!showHookHeader ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                    </button>
                  }
                >
                  ป้ายฮุก
                </TrackLabel>
              </div>
              {hasCutout && (
                <div style={rowStyle('cutout')} className="flex items-center transition-all duration-150">
                  <TrackLabel
                    width={gutterW}
                    slotWidth={dense ? 14 : 26}
                    icon={Scissors}
                    labelClass={previewOnlyLaneLabel('สินค้าไดคัท', isCutoutHidden).labelClass}
                    labelTitle={previewOnlyLaneLabel('สินค้าไดคัท', isCutoutHidden).title}
                    action={
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onToggleCutout?.(); }}
                        title={previewOnlyEyeTitle('สินค้าไดคัท', isCutoutHidden)}
                        className={`p-1 rounded transition-colors ${
                          isCutoutHidden
                            ? 'text-amber-400 hover:bg-amber-400/20'
                            : 'text-[#C084FC] hover:bg-[#C084FC]/20'
                        }`}
                      >
                        {isCutoutHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    }
                  >
                    {previewOnlyLaneLabel('สินค้าไดคัท', isCutoutHidden).text}
                  </TrackLabel>
                </div>
              )}
              {hasSticker && (
                <div style={rowStyle('sticker')} className="flex items-center transition-all duration-150">
                  <TrackLabel
                    width={gutterW}
                    slotWidth={dense ? 14 : 26}
                    icon={Smile}
                    labelClass={previewOnlyLaneLabel('สติกเกอร์', isStickerHidden).labelClass}
                    labelTitle={previewOnlyLaneLabel('สติกเกอร์', isStickerHidden).title}
                    action={
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onToggleHideSticker?.(); }}
                        title={previewOnlyEyeTitle('สติกเกอร์', isStickerHidden)}
                        className={`p-1 rounded transition-colors ${
                          isStickerHidden
                            ? 'text-amber-400 hover:bg-amber-400/20'
                            : 'text-[#9C968F] hover:text-[#EDE9E3] hover:bg-[#2C2B27]'
                        }`}
                      >
                        {isStickerHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    }
                  >
                    {previewOnlyLaneLabel('สติกเกอร์', isStickerHidden).text}
                  </TrackLabel>
                </div>
              )}
              {hasEffects && (
                <EffectTrackLabel
                  width={gutterW}
                  slotWidth={dense ? 14 : 26}
                  rowStyleProp={rowStyle('effect')}
                />
              )}
              <div style={rowStyle('caption')} className="flex items-center">
                <TrackLabel
                  width={gutterW}
                  slotWidth={dense ? 14 : 26}
                  icon={MessageSquare}
                  labelClass={previewOnlyLaneLabel('คำบรรยาย', isCaptionHidden).labelClass}
                  labelTitle={previewOnlyLaneLabel('คำบรรยาย', isCaptionHidden).title}
                  action={
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onToggleHideCaption?.(); }}
                      title={previewOnlyEyeTitle('คำบรรยาย', isCaptionHidden)}
                      className={`p-1 rounded transition-colors ${
                        isCaptionHidden
                          ? 'text-amber-400 hover:bg-amber-400/20'
                          : 'text-[#9C968F] hover:text-[#EDE9E3] hover:bg-[#2C2B27]'
                      }`}
                    >
                      {isCaptionHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                    </button>
                  }
                >
                  {previewOnlyLaneLabel('คำบรรยาย', isCaptionHidden).text}
                </TrackLabel>
              </div>
              {hasTextOverlays && (
                <div style={rowStyle('text')} className="flex items-center transition-all duration-150">
                  <TrackLabel
                    width={gutterW}
                  slotWidth={dense ? 14 : 26}
                    icon={Type}
                    action={
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onToggleHideTextOverlay?.(); }}
                        title={isTextOverlayHidden ? 'คลิกเพื่อแสดงข้อความเสริมบนพรีวิว' : 'คลิกเพื่อซ่อนข้อความเสริมบนพรีวิว'}
                        className={`p-1 rounded transition-colors ${
                          isTextOverlayHidden
                            ? 'text-amber-400 hover:bg-amber-400/20'
                            : 'text-[#9C968F] hover:text-[#EDE9E3] hover:bg-[#2C2B27]'
                        }`}
                      >
                        {isTextOverlayHidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    }
                  >
                    {textLaneCount > 1 ? `ข้อความ (${textLaneCount})` : 'ข้อความ'}
                  </TrackLabel>
                </div>
              )}
              {visibleStems.map(({ key, label, colour }, i) => {
                // Folded, the one visible row stands for the whole group, so its
                // chips have to act on the whole group. Leaving them pointed at
                // the voice stem made a row labelled "เสียง" mute one track of
                // four -- it read as a group control and was not one.
                const group = audioCollapsed;
                const mixKey = group ? 'all' : key;
                const soloing = Object.values(trackMix?.solo || {}).some(Boolean);
                const isSolo = group
                  ? STEMS.every((s) => trackMix?.solo?.[s.key])
                  : !!trackMix?.solo?.[key];
                const isMute = group
                  ? STEMS.every((s) => trackMix?.mute?.[s.key])
                  : !!trackMix?.mute?.[key];
                const silent = soloing ? !isSolo : isMute;
                return (
                  <div key={key} style={rowStyle(key)} className="flex items-center">
                    <TrackLabel
                      width={gutterW}
                      slotWidth={dense ? 14 : 26}
                      // The leading slot is where a tree control is looked for,
                      // so the group's fold takes it. Folded, this row stands
                      // for the whole group and unfolds from the same place.
                      fold={i === 0 ? {
                        collapsed: audioCollapsed,
                        onToggle: onToggleAudioGroup,
                        title: audioCollapsed
                          ? 'คลิกเพื่อแสดงแทร็กเสียงทั้ง 4'
                          : 'คลิกเพื่อรวมแทร็กเสียงให้เหลือแถวเดียว',
                      } : undefined}
                      // A dot in the lane's own colour ties the name to its
                      // waveform, and going hollow says "silent" without
                      // relying on colour alone -- so does the struck-through
                      // label next to it.
                      dot={dense ? undefined : { colour, hollow: silent }}
                      labelClass={`text-[11px] ${silent ? 'line-through decoration-[#6F6A64]' : ''}`}
                      action={
                        <span className="flex items-center gap-px">
                          {i === 0 && !dense && !audioCollapsed && (
                            // Master mute is a peer of the per-track chips, not
                            // a decoration on the group icon. It is dropped on a
                            // phone, and whenever the group is folded, because
                            // the row's own M then mutes all four anyway -- and
                            // a third chip is the difference between a name that
                            // fits and one that ends in an ellipsis.
                            <MixButton
                              active={isAudioMuted}
                              activeClass="bg-rose-500/25 text-rose-300"
                              onClick={onToggleMuteAudio}
                              title={isAudioMuted ? 'เปิดเสียงพรีวิวทั้งหมด' : 'ปิดเสียงพรีวิวทั้งหมด'}
                            >
                              {isAudioMuted ? <VolumeX className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
                            </MixButton>
                          )}
                          <MixButton
                            active={silent}
                            pressed={isMute}
                            activeClass="bg-rose-500/25 text-rose-300"
                            onClick={() => onTrackMix?.(mixKey, 'mute')}
                            title={`${isMute ? 'เปิด' : 'ปิด'}เสียง${group ? 'ทุกแทร็ก' : `แทร็ก ${label}`}`}
                          >
                            M
                          </MixButton>
                          <MixButton
                            active={isSolo}
                            activeClass="bg-amber-400/25 text-amber-300"
                            onClick={() => onTrackMix?.(mixKey, 'solo')}
                            title={group ? 'ฟังเฉพาะกลุ่มเสียง' : `ฟังแทร็ก ${label} เดี่ยว`}
                          >
                            S
                          </MixButton>
                        </span>
                      }
                    >
                      {/* Folded, the row stands for the group -- the chevron already says
                          there is more behind it, so the count would only cost the
                          width the name needs. */}
                      {i === 0 && audioCollapsed ? 'เสียง' : label}
                    </TrackLabel>
                  </div>
                );
              })}
            </div>

            <div
              ref={laneRef}
              className="relative flex-1 touch-none select-none"
              onPointerDown={handleTrackAreaPointerDown}
              onPointerMove={moveScrub}
              onPointerUp={endScrub}
              onPointerCancel={endScrub}
            >
              {/* video track */}
              <div
                data-testid="timeline-video-track"
                className="relative rounded bg-[#181716]"
                style={rowStyle('video')}
                onDragOver={onDragOverTrack}
                onDragLeave={() => setDropIndex(null)}
                onDrop={onDropTrack}
              >
                {dropIndex !== null && (
                  <div
                    className="pointer-events-none absolute top-0 z-40 h-full w-0.5 -translate-x-1/2 bg-[#D97757]"
                    style={{
                      left: (dropIndex >= segments.length
                        ? (segments.length ? segments[segments.length - 1].segEnd : 0)
                        : segments[dropIndex].segStart) * pxPerSec,
                    }}
                  />
                )}
                {segments.map((seg) => (
                  <TimelineClip
                    key={seg.clip.id}
                    seg={seg}
                    pxPerSec={pxPerSec}
                    isSelected={selection?.type === 'clip' && selection.id === seg.clip.id}
                    isExtraSelected={!(selection?.type === 'clip' && selection.id === seg.clip.id)
                      && selectedClipIds.includes(seg.clip.id)}
                    onSelect={selectClip}
                    onContextMenu={handleClipContextMenu}
                    onAdjustTrim={onAdjustTrim}
                    onTrim={trimClip}
                    onTrimBegin={dragBegin}
                    onTrimEnd={dragEnd}
                    onSeek={onSeek}
                    onReorder={(id, dir) => reorder(id, dir, false)}
                    onBodyDragStart={onBodyDragStart}
                    onBodyDragMove={onBodyDragMove}
                    onBodyDragEnd={onBodyDragEnd}
                    snapCandidates={snapPoints}
                    snapFunction={snapFunction}
                    playhead={playhead}
                    segments={segments}
                    cues={cues}
                    audioDuration={audioDuration}
                    onSnapGuide={handleSnapGuide}
                  />
                ))}

                {transitionSegments.map((seg) => {
                  const currentTransition = seg.clip.transition_in || 'cut';
                  const isFade = currentTransition !== 'cut';
                  const isOpen = transitionMenuClipId === seg.clip.id;
                  const currentDuration = seg.clip.transition_duration ?? FADE_DURATION;
                  const leftPx = seg.segStart * pxPerSec;

                  return (
                    <div
                      key={`tr-wrap-${seg.clip.id}`}
                      className="absolute top-0 bottom-0 pointer-events-none"
                      style={{ left: leftPx }}
                    >
                      <button
                        key={`tr-${seg.clip.id}`}
                        data-transition-trigger=""
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setContextMenu(null);
                          if (!isOpen) {
                            const rect = e.currentTarget.getBoundingClientRect();
                            const popupWidth = 224;
                            const popupHeight = 390;
                            const above = rect.top - popupHeight - 8;
                            const below = rect.bottom + 8;
                            setTransitionMenuPosition({
                              left: Math.max(8, Math.min(rect.left - popupWidth / 2, window.innerWidth - popupWidth - 8)),
                              top: above >= 8 ? above : Math.max(8, Math.min(below, window.innerHeight - popupHeight - 8)),
                            });
                            transitionTriggerRef.current = e.currentTarget;
                          }
                          setTransitionMenuClipId(isOpen ? null : seg.clip.id);
                        }}
                        aria-haspopup="dialog"
                        aria-expanded={isOpen}
                        title={isFade
                          ? `${currentTransition} ${seg.overlap.toFixed(2)} วิ — คลิกเพื่อเปลี่ยนทรานซิชัน`
                          : 'ตัดตรง — คลิกเพื่อเลือกรอยต่อทรานซิชัน'}
                        className={`pointer-events-auto absolute top-1/2 z-20 flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded border transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                          isFade
                            ? 'border-[#D97757] bg-[#33251F] text-[#E89274]'
                            : 'border-[#4A4742] bg-[#232220] text-[#9C968F] hover:text-[#EDE9E3]'
                        } ${isOpen ? 'ring-2 ring-[#25F4EE] z-30' : ''}`}
                      >
                        <TransitionIcon type={currentTransition} className="h-3 w-3" />
                      </button>

                      {/* Quick Transition Popover */}
                      {isOpen && transitionMenuPosition && typeof document !== 'undefined' && createPortal(
                        <div
                          data-transition-popover=""
                          role="dialog"
                          aria-label="ตั้งค่ารอยต่อคลิป"
                          onClick={(e) => e.stopPropagation()}
                          className="pointer-events-auto fixed z-[100] w-56 rounded-xl border border-[#4A4742] bg-[#1C1B19]/95 p-2.5 shadow-2xl backdrop-blur-md text-xs text-[#EDE9E3] animate-in fade-in zoom-in-95 duration-150"
                          style={{ ...transitionMenuPosition, maxHeight: 'calc(100vh - 16px)', overflowY: 'auto' }}
                        >
                          <div className="flex items-center justify-between pb-1.5 border-b border-[#363430]">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <Waves className="h-3.5 w-3.5 text-[#25F4EE]" /> รอยต่อคลิป
                            </span>
                            <button
                              type="button"
                              onClick={closeTransitionMenu}
                              className="p-0.5 text-slate-400 hover:text-white rounded"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="py-2 space-y-1">
                            <button
                              type="button"
                              onClick={() => {
                                onClipChange?.(seg.clip.id, { transition_in: 'cut' });
                                closeTransitionMenu();
                              }}
                              className={`w-full py-1.5 px-2 rounded-lg text-left font-medium transition-colors flex items-center justify-between ${
                                currentTransition === 'cut'
                                  ? 'bg-[#D97757]/25 text-[#E89274] border border-[#D97757]/50'
                                  : 'hover:bg-[#2C2B27] text-slate-300'
                              }`}
                            >
                              <span>ตัดตรง (ไม่มีรอยต่อ)</span>
                              {currentTransition === 'cut' && <Scissors className="h-3 w-3" />}
                            </button>

                            <div className="grid grid-cols-2 gap-1 pt-1">
                              {TRANSITION_POPOVER_OPTIONS.map((t) => {
                                const active = currentTransition === t.id;
                                return (
                                  <button
                                    key={t.id}
                                    type="button"
                                    onClick={() => {
                                      onClipChange?.(seg.clip.id, {
                                        transition_in: t.id,
                                        transition_duration: currentDuration,
                                      });
                                      closeTransitionMenu();
                                    }}
                                    className={`flex items-center gap-1.5 py-1 px-2 rounded-lg text-left font-medium truncate transition-colors ${
                                      active
                                        ? 'bg-[#D97757] text-white'
                                        : 'bg-[#282724] hover:bg-[#363430] text-slate-300'
                                    }`}
                                  >
                                    <TransitionIcon type={t.id} className="h-3 w-3 flex-shrink-0" />
                                    {t.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {/* Duration: presets + slider over the renderer's 0.1-2.0 s range */}
                          <TransitionDurationControl
                            value={currentDuration}
                            onCommit={(d) => {
                              onClipChange?.(seg.clip.id, {
                                transition_in: currentTransition === 'cut' ? 'fade' : currentTransition,
                                transition_duration: d,
                              });
                            }}
                          />
                        </div>,
                        document.body
                      )}
                    </div>
                  );
                })}
              </div>

              {/* hook header track */}
              <div className="relative rounded bg-[#181716]" style={rowStyle('hook')}>
                {(() => {
                  const tierTexts = (hookOverlay?.tiers || []).map((tier) => tier.text).filter(Boolean);
                  const hookText = tierTexts.join(' · ') || 'ป้ายฮุกพาดหัว (Hook Header)';
                  const isSelected = selection?.type === 'hook';
                  const start = hookOverlay?.start || 0;
                  const dur = hookOverlay ? Math.max(0.1, hookOverlay.end - hookOverlay.start) : 5.0;
                  const w = Math.max(24, dur * pxPerSec);

                  return (
                    <TimelineIntervalItem
                      dataType="hook"
                      onClick={(e) => {
                        e.stopPropagation();
                        const t = timeFromEvent(e);
                        if (onSelectHook) onSelectHook();
                        else onSelect?.({ type: 'hook' });
                        if (typeof t === 'number' && t >= start && t <= start + dur) {
                          onSeek?.(t);
                        } else if (playhead < start || playhead > start + dur + 0.05) {
                          onSeek?.(start);
                        }
                      }}
                      title={`${hookText} (${start.toFixed(1)}s - ${(start + dur).toFixed(1)}s)`}
                      className={`group absolute top-0.5 h-[calc(100%-4px)] touch-none select-none rounded text-left text-xs transition-colors duration-150 flex items-center ${
                        !showHookHeader
                          ? 'opacity-40 bg-[#282724] text-[#9C968F] ring-1 ring-white/10'
                          : isSelected
                            ? 'bg-[#3A3018] text-[#FFE600] ring-2 ring-[#E6C24A] shadow-[0_0_12px_rgba(230,194,74,0.3)]'
                            : 'bg-[#2A2415] text-[#E6C24A] ring-1 ring-[#594B22] hover:ring-[#8C7636]'
                      }`}
                      style={{ left: start * pxPerSec, width: w }}
                      showLeftHandle={false}
                      showRightHandle
                      handleClassName="hover:bg-[#E6C24A]"
                      rightHandleTitle={`ลากเพื่อปรับระยะเวลาแสดงผลป้ายฮุก (${HOOK_MIN_DURATION.toFixed(1)} - ${HOOK_MAX_DURATION.toFixed(1)} วิ)`}
                      onTrimStart={(e) => startHookTrim(e)}
                      onTrimMove={moveHookTrim}
                      onTrimEnd={endHookTrim}
                      bodyClassName="flex-1 min-w-0 h-full flex items-center px-2 gap-1.5 overflow-hidden cursor-pointer"
                    >
                      <Sparkles className="h-3 w-3 flex-shrink-0 text-[#E6C24A]" />
                      <span className="truncate font-semibold text-[11px] tracking-wide">{hookText}</span>
                      <span className="text-[9px] text-[#E6C24A]/80 flex-shrink-0">{subjectLayerForOverlay(hookOverlay) === 'behind' ? 'หลัง' : 'หน้า'}</span>
                      <span className="font-mono text-[10px] text-[#E6C24A]/70 flex-shrink-0 ml-auto">
                        {dur.toFixed(1)}s
                      </span>
                    </TimelineIntervalItem>
                  );
                })()}
              </div>

              {/* cutout track */}
              {hasCutout && (
                <div
                  data-testid="timeline-cutout-track"
                  className="relative rounded bg-[#181716] transition-all duration-150"
                  style={rowStyle('cutout')}
                >
                  {backgroundIsolation?.scope_mode === 'behind_text_windows'
                    ? scopedCutoutWindows.map((window, index) => (
                      <div
                        key={`cutout-window-${window.seg.clip.id}-${index}`}
                        title={`Cutout สินค้า: ช็อต #${window.seg.index + 1} ช่วง ${window.start.toFixed(2)}–${window.end.toFixed(2)} วินาที (${window.ready ? 'พร้อมใช้งาน' : 'ยังไม่พร้อม'})`}
                        onClick={(e) => { e.stopPropagation(); selectClip(window.seg.clip.id); }}
                        className={`absolute top-0.5 h-[calc(100%-4px)] rounded border px-2 text-[10px] font-semibold flex items-center cursor-pointer ${window.ready
                          ? 'bg-[#2E1065]/80 text-[#C084FC] border-[#7C3AED]/60'
                          : 'bg-[#3A2208]/80 text-[#FDBA74] border-[#EA580C]/50'}`}
                        style={{ left: window.start * pxPerSec, width: Math.max(16, (window.end - window.start) * pxPerSec) }}
                      >
                        <span className="truncate">{window.ready ? 'Cutout พร้อม' : 'รอ Cutout'}</span>
                      </div>
                    ))
                    : segments.map((seg) => {
                    const clipIso = resolveBackgroundIsolationConfig(seg.clip, backgroundIsolation);
                    const isIsoOn = clipIso?.enabled === true;
                    const isProcessing = Boolean(cutoutProcessingClipIds?.includes(seg.clip.id));
                    const isQueued = Boolean(cutoutQueuedClipIds?.includes(seg.clip.id));
                    const isReady = !isProcessing && !isQueued && clipIso?.artifact?.status === 'ready';
                    const w = Math.max(16, seg.dur * pxPerSec);
                    return (
                      <div
                        key={`cutout-${seg.clip.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          selectClip(seg.clip.id);
                        }}
                        title={`Cutout สินค้า: ช็อต #${seg.index + 1} (${isProcessing ? 'กำลังประมวลผล' : isQueued ? 'รอคิวตัดในรอบนี้' : isIsoOn ? (isReady ? 'พร้อมใช้งาน' : 'รอคิว Cutout') : 'ปิดใช้งาน'})`}
                        className={`group absolute top-0.5 h-[calc(100%-4px)] rounded text-xs select-none flex items-center px-2 gap-1.5 transition-all cursor-pointer ${
                          isCutoutHidden
                            ? 'opacity-30 bg-[#282724] text-[#9C968F] ring-1 ring-white/10'
                            : isProcessing
                              ? 'bg-[#78350F]/90 text-[#FDE68A] border border-[#F59E0B] shadow-[0_0_12px_rgba(245,158,11,0.4)] animate-pulse'
                              : isIsoOn && isReady
                                ? 'bg-[#2E1065]/80 text-[#C084FC] border border-[#7C3AED]/60 shadow-[0_0_8px_rgba(124,58,237,0.25)] hover:border-[#A855F7]'
                                : isIsoOn
                                  ? 'bg-[#3A2208]/80 text-[#FDBA74] border border-[#EA580C]/50'
                                  : 'bg-[#1C1917]/50 text-[#78716C] border border-white/5 opacity-50 hover:opacity-80'
                        }`}
                        style={{ left: seg.segStart * pxPerSec, width: w }}
                      >
                        <Scissors className={`h-3 w-3 flex-shrink-0 ${isProcessing ? 'text-[#FDE68A] animate-spin' : isIsoOn && isReady ? 'text-[#C084FC]' : 'text-slate-500'}`} />
                        <span className="truncate font-semibold text-[10.5px]">
                          {isProcessing ? '⚡ กำลังตัด...' : isIsoOn && isReady ? 'Cutout สินค้า' : isIsoOn ? '⏳ รอ Cutout' : 'ไม่มี Cutout'}
                        </span>
                        {isIsoOn && isReady && (
                          <span className="ml-auto text-[9.5px] font-mono text-[#C084FC]/70 flex-shrink-0">
                            ✓ {seg.dur.toFixed(1)}s
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* sticker track */}
              {hasSticker && (
                <div
                  className="relative rounded bg-[#181716] transition-all duration-150"
                  style={rowStyle('sticker')}
                >
                  {packedStickers.map((item) => {
                    const start = item.start ?? 0.5;
                    const end = item.end ?? (totalDuration || 15);
                    const dur = Math.max(0.2, end - start);
                    const isSelected = selection?.type === 'sticker' && (selection.id === item.id || (!selection.id && item.id === 'sticker_badge'));
                    const w = Math.max(24, dur * pxPerSec);
                    const activeBadge = stickerAssetIndex.byName.get(item.badge)
                      || stickerAssetIndex.byPath.get(item.badge);
                    const stickerName = activeBadge?.title || activeBadge?.name?.replace(/\.[^.]+$/, '') || item.badge || 'สติกเกอร์ 3D';
                    const topPx = (item.lane || 0) * STICKER_LANE_ROW_H + 2;

                    return (
                      <TimelineIntervalItem
                        key={item.id}
                        dataType="sticker"
                        onClick={(e) => {
                          e.stopPropagation();
                          const t = timeFromEvent(e);
                          if (onSelectSticker) onSelectSticker(item.id);
                          else onSelect?.({ type: 'sticker', id: item.id });
                          if (typeof t === 'number' && t >= start && t <= end) {
                            onSeek?.(t);
                          } else if (playhead < start || playhead > end + 0.05) {
                            onSeek?.(start);
                          }
                        }}
                        title={`${stickerName} (${start.toFixed(1)}s - ${end.toFixed(1)}s)`}
                        className={
                          isStickerHidden || item.hidden
                            ? 'opacity-40 bg-[#282724] text-[#9C968F] ring-1 ring-white/10'
                            : isSelected
                              ? 'bg-[#14323B] text-[#25F4EE] ring-2 ring-[#25F4EE] shadow-[0_0_12px_rgba(37,244,238,0.3)] z-10'
                              : 'bg-[#13272D] text-[#64D8D2] ring-1 ring-[#1E4D54] hover:ring-[#2FA0A8]'
                        }
                        style={{ left: start * pxPerSec, width: w, top: topPx, height: STICKER_LANE_ROW_H - 4 }}
                        handleClassName="hover:bg-[#25F4EE]"
                        leftHandleTitle="ลากเพื่อยืด/หดเวลาเริ่มต้นของสติกเกอร์"
                        rightHandleTitle="ลากเพื่อยืด/หดเวลาสิ้นสุดของสติกเกอร์"
                        onTrimStart={(e, edge) => startStickerTrim(e, edge, item)}
                        onTrimMove={moveStickerTrim}
                        onTrimEnd={endStickerTrim}
                        onBodyStart={(e) => startStickerBodyDrag(e, item)}
                        onBodyMove={moveStickerBodyDrag}
                        onBodyEnd={endStickerBodyDrag}
                        bodyClassName="flex-1 min-w-0 h-full flex items-center px-2 gap-1.5 overflow-hidden cursor-move"
                      >
                        {activeBadge?.url ? (
                          <img src={activeBadge.url} alt="" className="h-4 w-4 object-contain flex-shrink-0" />
                        ) : (
                          <Smile className="h-3 w-3 flex-shrink-0 text-[#25F4EE]" />
                        )}
                        <span className="truncate font-semibold text-[11px] tracking-wide">{stickerName}</span>
                        <span className="font-mono text-[10px] text-[#25F4EE]/70 flex-shrink-0 ml-auto">
                          {dur.toFixed(1)}s
                        </span>
                      </TimelineIntervalItem>
                    );
                  })}
                </div>
              )}

              {/* effect track */}
              {hasEffects && (
                <EffectTrackLane
                  rowStyleProp={rowStyle('effect')}
                  packedEffects={packedEffects}
                  effectAssets={effectAssets}
                  selection={selection}
                  playhead={playhead}
                  totalDuration={totalDuration}
                  pxPerSec={pxPerSec}
                  timeFromEvent={timeFromEvent}
                  onSelectEffect={onSelectEffect}
                  onSeek={onSeek}
                  startEffectTrim={startEffectTrim}
                  moveEffectTrim={moveEffectTrim}
                  endEffectTrim={endEffectTrim}
                  startEffectBodyDrag={startEffectBodyDrag}
                  moveEffectBodyDrag={moveEffectBodyDrag}
                  endEffectBodyDrag={endEffectBodyDrag}
                />
              )}

              {/* caption track */}
              <div className="relative rounded bg-[#181716]" style={rowStyle('caption')}>
                {(cues || []).map((cue) => {
                  const selected = selection?.type === 'caption' && selection.id === cue._uid;
                  const w = Math.max(14, (cue.end - cue.start) * pxPerSec);
                  return (
                    <TimelineIntervalItem
                      key={cue._uid}
                      dataType="caption"
                      onClick={(e) => {
                        e.stopPropagation();
                        selectCaption(cue._uid);
                      }}
                      title={`${cue.text} (${cue.start.toFixed(2)}s - ${cue.end.toFixed(2)}s)`}
                      className={`group absolute top-1 h-[calc(100%-8px)] touch-none select-none rounded text-left text-xs leading-[18px] transition-colors duration-150 flex items-center ${
                        selected
                        ? 'bg-[#33251F] text-[#EDE9E3] ring-2 ring-[#D97757]'
                        : 'bg-[#282724] text-[#C9C3BB] ring-1 ring-[#4A4742] hover:ring-[#6B6660]'
                      }`}
                      style={{ left: cue.start * pxPerSec, width: w }}
                      handleClassName="hover:bg-[#D97757]"
                      leftHandleTitle="ลากเพื่อยืด/หดเวลาเริ่มต้น"
                      rightHandleTitle="ลากเพื่อยืด/หดเวลาสิ้นสุด"
                      onTrimStart={(e, edge) => startTrim(e, cue, edge)}
                      onTrimMove={moveTrim}
                      onTrimEnd={endTrim}
                      onBodyStart={(e) => startCaptionBodyDrag(e, cue)}
                      onBodyMove={(e) => moveCaptionBodyDrag(e, cue)}
                      onBodyEnd={endCaptionBodyDrag}
                      bodyClassName="flex-1 min-w-0 h-full flex items-center px-1 overflow-hidden cursor-grab active:cursor-grabbing"
                    >
                      <span className="truncate">{cue.text}</span>
                    </TimelineIntervalItem>
                  );
                })}
              </div>

              {/* text overlay track (only shown when overlays exist, auto-stacked by lane) */}
              {hasTextOverlays && (
                <div
                  className="relative rounded bg-[#181716] transition-all duration-150"
                  style={rowStyle('text')}
                >
                  {packedTextOverlays.map((item) => {
                    const selected = selection?.type === 'text_overlay' && selection.id === item.id;
                    const w = Math.max(16, (item.end - item.start) * pxPerSec);
                    const topPx = item.lane * TEXT_LANE_ROW_H + 2;
                    return (
                      <TimelineIntervalItem
                        key={item.id}
                        dataType="text_overlay"
                        onClick={(e) => { e.stopPropagation(); selectTextOverlay(item.id); }}
                        title={`${overlayLabel(item)} (${item.start.toFixed(2)}s - ${item.end.toFixed(2)}s)`}
                        className={`leading-[18px] ${selected
                          ? 'bg-[#153434] text-[#25F4EE] ring-2 ring-[#25F4EE] shadow-[0_0_10px_rgba(37,244,238,0.25)] z-10'
                          : 'bg-[#1C2626] text-[#A2CCCC] ring-1 ring-[#2E4848] hover:ring-[#477070]'}`}
                        style={{ left: item.start * pxPerSec, width: w, top: topPx, height: TEXT_LANE_ROW_H - 4 }}
                        handleClassName="hover:bg-[#25F4EE]"
                        leftHandleTitle="ลากเพื่อยืด/หดเวลาเริ่มต้น"
                        rightHandleTitle="ลากเพื่อยืด/หดเวลาสิ้นสุด"
                        onTrimStart={(e, edge) => startTextTrim(e, item, edge)}
                        onTrimMove={moveTextTrim}
                        onTrimEnd={endTextTrim}
                        onBodyStart={(e) => startTextBodyDrag(e, item)}
                        onBodyMove={(e) => moveTextBodyDrag(e, item)}
                        onBodyEnd={endTextBodyDrag}
                        bodyClassName="flex-1 min-w-0 h-full flex items-center px-1.5 overflow-hidden cursor-grab active:cursor-grabbing gap-1"
                      >
                        <Type className="h-3 w-3 flex-shrink-0 text-[#25F4EE]" />
                        <span className="truncate font-medium">{overlayLabel(item)}</span>
                        <span className="text-[9px] opacity-75 flex-shrink-0">{subjectLayerForOverlay(item) === 'behind' ? 'หลัง' : 'หน้า'}</span>
                      </TimelineIntervalItem>
                    );
                  })}
                </div>
              )}

              {/* audio stems: one lane each, so a level, a cue or a clip's own
                  sound can be seen and soloed instead of hidden in one mix.
                  The lane carries no name of its own -- the gutter already
                  says it, and repeating it only wrote over the waveform. */}
              {visibleStems.map(({ key, colour, ring, bg }) => {
                const soloing = Object.values(trackMix?.solo || {}).some(Boolean);
                const silent = soloing ? !trackMix?.solo?.[key] : !!trackMix?.mute?.[key];
                const info = stemPeaks[key];
                const spanSecs = key === 'voice' || key === 'bgm' ? audioDuration : totalDuration;
                const note = key === 'bgm'
                  ? (bgmLabel || 'ค่าเริ่มต้นของช่อง')
                  : (info?.truncated ? `รูปคลื่นแสดง ${MAX_DECODE_SECONDS} วิแรก` : '');
                return (
                  <div
                    key={key}
                    className="relative rounded bg-[#181716] transition-opacity duration-150"
                    style={{ ...rowStyle(key), opacity: silent ? 0.4 : 1 }}
                  >
                    {spanSecs > 0 && (
                      <div
                        className="absolute inset-y-0 flex items-center overflow-hidden rounded"
                        style={{
                          left: 0,
                          width: spanSecs * pxPerSec,
                          background: bg,
                          boxShadow: `inset 0 0 0 1px ${ring}`,
                        }}
                        title={
                          key === 'voice' ? 'เสียงพากย์ (voiceover.wav)'
                            : key === 'bgm' ? `เพลงประกอบ${bgmLabel ? ` · ${bgmLabel}` : ' · ค่าเริ่มต้นของช่อง'} (เปลี่ยนได้ที่แผงขวา)`
                              : key === 'sfx' ? 'เสียงเอฟเฟกต์ตามจังหวะซับ'
                                : 'เสียงในตัวคลิป (ตั้งระดับได้ที่แผงขวา)'
                        }
                      >
                        {info?.peaks && (
                          <canvas
                            ref={(el) => { stemCanvasRefs.current[key] = el; }}
                            width={WAVE_COLUMNS}
                            height={STEM_H}
                            className="pointer-events-none absolute inset-0 h-full w-full"
                          />
                        )}
                        {note && (
                          <span
                            className="relative ml-2 truncate text-[10px] drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]"
                            style={{ color: colour }}
                          >
                            {note}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Beat markers on the music lane. Major beats (bar
                        downbeats) are the strong scene-change points and are
                        drawn taller and brighter than the subdivisions, so a
                        glance separates "cut here" from "accent here".
                        pointer-events-none throughout: these are a reading
                        aid for the drag snapping, never a click target that
                        could swallow a scrub. */}
                    {key === 'bgm' && beatMarkers.major.map((t) => (
                      <div
                        key={`beat-major-${t}`}
                        className="pointer-events-none absolute w-px"
                        style={{
                          left: t * pxPerSec,
                          top: 2,
                          bottom: 2,
                          background: BEAT_MARKER_COLOUR,
                          opacity: 0.9,
                        }}
                        title={`จังหวะหลัก ${t.toFixed(2)}s`}
                      />
                    ))}
                    {key === 'bgm' && beatMarkers.minor.map((t) => (
                      <div
                        key={`beat-minor-${t}`}
                        className="pointer-events-none absolute w-px"
                        style={{
                          left: t * pxPerSec,
                          top: '38%',
                          bottom: 2,
                          background: BEAT_MARKER_COLOUR,
                          opacity: 0.4,
                        }}
                        title={`จังหวะย่อย ${t.toFixed(2)}s`}
                      />
                    ))}

                    {/* Ripple cuts of the voice: a thin orange line where the two
                        sides were joined. Hover says how much was taken out;
                        restoring a cut is not offered yet. A small hit area keeps
                        the tooltip reachable without swallowing a click on the lane. */}
                    {key === 'voice' && voiceCutMarks.map((mark) => (
                      <div
                        key={`voice-cut-${mark.id}`}
                        data-voice-cut-marker={mark.id}
                        className="absolute inset-y-0 z-20 -translate-x-1/2 cursor-help"
                        style={{ left: mark.time * pxPerSec, width: 7 }}
                        title={mark.title}
                      >
                        <span className="absolute inset-y-0.5 left-1/2 w-[2px] -translate-x-1/2 rounded-full bg-[#F08A4B] shadow-[0_0_4px_rgba(240,138,75,0.7)]" />
                      </div>
                    ))}

                    {/* clip lane: a block wherever a clip contributes its own audio.
                        Clip volume defaults to 0, so this lane is empty for most
                        projects -- say so rather than leaving a blank strip. */}
                    {key === 'clip' && !clipAudioSegments.length && (
                      <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[#6F6A64]">
                        ยังไม่ได้เปิดเสียงในคลิป — ตั้งระดับได้ที่แผงขวา
                      </span>
                    )}
                    {key === 'clip' && clipAudioSegments.map((s) => (
                      <div
                        key={`clipaud-${s.clip.id}`}
                        className="absolute inset-y-0 rounded bg-[#C79FD8]/30 ring-1 ring-inset ring-[#C79FD8]/60"
                        style={{ left: s.segStart * pxPerSec, width: Math.max(2, (s.segEnd - s.segStart) * pxPerSec) }}
                        title={`เสียงในคลิปนี้ ${Math.round(Number(s.clip.volume) * 100)}%`}
                      />
                    ))}

                    {/* An SFX hit is a moment, not a span: a tick pinned to the
                        instant, with the name beside it so a run of them stays
                        readable. Centred in the lane -- pinned to the top edge
                        they read as belonging to the row above. */}
                    {key === 'sfx' && sfxMarkers.map((cue) => (
                      <button
                        key={`sfx-${cue._uid}`}
                        data-timeline-item="sfx"
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSeek?.(cue.start);
                          selectCaption(cue._uid);
                        }}
                        title={`SFX: ${cue.sfx} (คลิกเพื่อกระโดดไปที่จังหวะนี้)`}
                        className="group/sfx absolute top-1/2 z-20 flex -translate-y-1/2 cursor-pointer items-center gap-1
                          rounded-full pl-0 pr-1.5 transition-colors hover:z-30
                          focus-visible:outline focus-visible:outline-1 focus-visible:outline-[#25F4EE]"
                        style={{ left: cue.start * pxPerSec }}
                      >
                        <span className="h-3 w-[3px] flex-shrink-0 rounded-full bg-[#D97757] transition-colors group-hover/sfx:bg-[#25F4EE]" />
                        <span className="font-mono text-[9px] font-bold uppercase leading-none text-[#D8C39F] transition-colors group-hover/sfx:text-[#25F4EE]">
                          {cue.sfx}
                        </span>
                      </button>
                    ))}
                  </div>
                );
              })}

              {/* the render is cut at the voiceover length, so show where that is */}
              {audioDuration > 0 && (
                <div
                  className="pointer-events-none absolute bottom-0 top-0 border-l border-dashed border-[#6B6660]"
                  style={{ left: audioDuration * pxPerSec }}
                  title="ความยาวเสียงพากย์ — เรนเดอร์จะตัดที่เส้นนี้"
                />
              )}

              {/* Magnetic Snap Guide Line & Tooltip */}
              {activeSnapGuide && Number.isFinite(activeSnapGuide.time) && (
                <div
                  className="pointer-events-none absolute bottom-0 z-40 flex flex-col items-center"
                  style={{
                    left: `${activeSnapGuide.time * pxPerSec}px`,
                    top: `${-RULER_H - TRACK_TOP}px`,
                    transform: 'translateX(-50%)',
                  }}
                >
                  <div className="sticky top-0 z-50 mb-0.5 flex items-center gap-1 rounded bg-[#FFE600] px-1.5 py-0.5 text-[10px] font-bold text-black shadow-[0_2px_8px_rgba(0,0,0,0.8)] whitespace-nowrap">
                    <span>🧲 {activeSnapGuide.label}</span>
                    <span className="font-mono font-semibold opacity-85">({formatTimecode(activeSnapGuide.time)})</span>
                  </div>
                  <div className="w-[2px] flex-1 bg-[#FFE600] shadow-[0_0_10px_#FFE600,0_0_20px_rgba(255,230,0,0.7)]" />
                </div>
              )}

              {/* playhead */}
              <TimelinePlayhead
                playhead={playhead}
                pxPerSec={pxPerSec}
                topOffset={-RULER_H - TRACK_TOP}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Right-Click Context Menu on Video Clips */}
      <TimelineContextMenu
        contextMenu={contextMenu}
        onClose={() => setContextMenu(null)}
        onSplit={onSplit}
        onDuplicate={onDuplicate}
        onToggleMirror={onToggleMirror}
        onAdjustTrim={() => onAdjustTrim?.(contextMenu.seg)}
        onClipChange={onClipChange}
        onDelete={onDelete}
        selectedCount={selectedClipIds.length}
        onCopySettings={onCopySettings}
        onPasteSettings={onPasteSettings}
        canPasteSettings={canPasteSettings}
      />
    </div>
  );
}
