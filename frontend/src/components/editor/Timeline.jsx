import React, { useEffect, useMemo, useRef, useState } from 'react';
import { TransitionIcon } from '../../lib/transitionIcons';
import {
  ChevronDown, ChevronRight,
  Copy, Eye, EyeOff, Film, FlipHorizontal2, Gauge, MessageSquare, Music, Plus, Scissors, Sparkles, Trash2, Type, Volume2, VolumeX, Waves, X
} from 'lucide-react';
import TimelineClip from './TimelineClip';
import { CLIP_DRAG_TYPE } from './AssetPanel';
import { getAudioPeaks, MAX_DECODE_SECONDS } from '../../lib/audioPeaks';
import { formatTimecode, TRANSITIONS, FADE_DURATION } from '../../lib/timelineMath';

const RULER_H = 22;
const WAVE_COLUMNS = 1200;

// Row heights on a 4px scale, with the video track deliberately the tall one:
// it is what the eye lands on first, and everything else supports it.
const VIDEO_H = 64;
const HOOK_H = 28;
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
export function tracksFitHeight({ textOverlays = false, audioCollapsed = false } = {}) {
  const rows = layoutRows({
    present: { text: textOverlays },
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

/** Tick spacing that keeps labels readable at any zoom. */
function tickStep(pxPerSec) {
  for (const step of [1, 2, 5, 10, 15, 30, 60]) {
    if (step * pxPerSec >= 56) return step;
  }
  return 120;
}

/**
 * Computes deterministic magnetic ripple on cues when a cue is trimmed or dragged.
 * Extends -> pushes subsequent cues forward.
 * Shrinks -> magnetically pulls subsequent cues backward (Magnetic Pull) without leaving gaps.
 * Cues never overlap and maintain relative order with zero cumulative drift.
 */
function applyCaptionMagneticRipple(initialCues, targetUid, newStart, newEnd) {
  if (!initialCues || !initialCues.length) return [];
  const list = initialCues.map((c) => ({ ...c }));
  const targetIdx = list.findIndex((c) => c._uid === targetUid || c.id === targetUid);
  if (targetIdx === -1) return list;

  const validStart = Math.max(0, Math.round(newStart * 100) / 100);
  const validEnd = Math.max(validStart + 0.2, Math.round(newEnd * 100) / 100);

  const initTarget = initialCues[targetIdx];
  list[targetIdx] = {
    ...list[targetIdx],
    start: validStart,
    end: validEnd,
  };

  const deltaEnd = Math.round((validEnd - initTarget.end) * 100) / 100;
  const deltaStart = Math.round((validStart - initTarget.start) * 100) / 100;
  // If end changed (e.g. right trim), use deltaEnd. Otherwise (e.g. body drag or left trim), use deltaStart
  const shiftDelta = Math.abs(deltaEnd) > 0.001 ? deltaEnd : deltaStart;

  for (let i = targetIdx + 1; i < list.length; i++) {
    const prevCue = list[i - 1];
    const initCur = initialCues[i];
    const curDur = Math.max(0.2, Math.round((initCur.end - initCur.start) * 100) / 100);

    const wantedStart = Math.round((initCur.start + shiftDelta) * 100) / 100;
    const shiftedStart = Math.max(prevCue.end, wantedStart);
    const shiftedEnd = Math.round((shiftedStart + curDur) * 100) / 100;

    list[i] = {
      ...list[i],
      start: shiftedStart,
      end: shiftedEnd,
    };
  }

  return list;
}

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

function TrackLabel({ icon: Icon, children, action, iconTitle, iconClass, onIconClick, dot, labelClass, fold, width, slotWidth = 26 }) {
  return (
    <div
      className="flex items-center gap-1 px-2 text-xs font-medium text-[#9C968F]"
      style={{ width: width ?? GUTTER }}
    >
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        <span className="flex flex-shrink-0 items-center gap-1.5" style={{ width: slotWidth }}>
        {fold && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); fold.onToggle?.(); }}
            title={fold.title}
            aria-expanded={!fold.collapsed}
            className="-m-0.5 flex-shrink-0 rounded p-0.5 text-[#6F6A64] transition-colors hover:bg-[#2C2B27] hover:text-[#EDE9E3]"
          >
            {fold.collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
        {Icon && onIconClick ? (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onIconClick(); }}
            title={iconTitle}
            className="-m-0.5 flex-shrink-0 rounded p-0.5 transition-colors hover:bg-[#2C2B27] hover:text-[#EDE9E3]"
          >
            <Icon className={`h-3 w-3 ${iconClass || ''}`} />
          </button>
        ) : Icon ? (
          <Icon className="h-3 w-3 flex-shrink-0" />
        ) : null}
        {dot && (
          <span
            className="h-[7px] w-[7px] flex-shrink-0 rounded-full"
            style={dot.hollow
              ? { boxShadow: `inset 0 0 0 1.5px ${dot.colour}`, opacity: 0.5 }
              : { background: dot.colour }}
          />
        )}
        </span>
        <span className={`truncate ${labelClass || ''}`} title={typeof children === 'string' ? children : undefined}>
          {children}
        </span>
      </div>
      {action}
    </div>
  );
}

export default function Timeline({
  segments,
  totalDuration,
  audioDuration,
  cues,
  bgmLabel,
  stemUrls = {},
  trackMix = null,
  onTrackMix,
  audioCollapsed = false,
  onToggleAudioGroup,
  dense = false,
  filmstrips,
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
  // Newer shell prop names. Both sets are accepted so the timeline keeps
  // working whichever shape the shell passes.
  onSelect,
  onClipChange,
  onCaptionChange,
  onBeginDrag,
  onEndDrag,
  onZoom,
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
  // Edge/body drags snap to these (clip boundaries, playhead, audio end).
  // Both default to "no snapping" so the timeline still works if a caller
  // doesn't wire them up.
  snapCandidates: snapPoints = [],
  snapFunction = (t) => t,
  snapEnabled = true,
  onCuesChange,
  onCaptionRippleShift,
  showHookHeader = true,
  hookBrand = '',
  hookModel = '',
  hookLabel = '',
  hookDuration = 3.0,
  onHookDurationChange,
  onToggleHookHeader,
  onSelectHook,
  textOverlays = [],
  onAddTextOverlay,
  onTextOverlayChange,
  onSelectTextOverlay,
  isTextOverlayHidden = false,
  onToggleHideTextOverlay,
}) {
  const deselectAll = () => {
    if (onSelectClip) onSelectClip(null);
    if (onSelectCaption) onSelectCaption(null);
    if (onSelectTextOverlay) onSelectTextOverlay(null);
    onSelect?.(null);
  };

  const selectClip = (id) => {
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
  const scrubbing = useRef(false);
  const captionDrag = useRef(null);
  const captionTrim = useRef(null);
  const textDrag = useRef(null);
  const textTrim = useRef(null);
  const bodyDrag = useRef(null);
  const [dropIndex, setDropIndex] = useState(null);
  const stemCanvasRefs = useRef({});
  const [stemPeaks, setStemPeaks] = useState({});
  const [transitionMenuClipId, setTransitionMenuClipId] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const hasTextOverlays = Boolean(textOverlays && textOverlays.length > 0);

  // Auto-stacking multi-layer calculation for overlapping text overlays
  const { packedTextOverlays, textLaneCount } = useMemo(() => {
    if (!textOverlays || textOverlays.length === 0) {
      return { packedTextOverlays: [], textLaneCount: 0 };
    }
    const sorted = [...textOverlays].sort((a, b) => a.start - b.start);
    const laneEndTimes = [];
    const packed = sorted.map((item) => {
      let assignedLane = -1;
      for (let i = 0; i < laneEndTimes.length; i++) {
        if (item.start >= laneEndTimes[i] - 0.05) {
          assignedLane = i;
          laneEndTimes[i] = item.end;
          break;
        }
      }
      if (assignedLane === -1) {
        assignedLane = laneEndTimes.length;
        laneEndTimes.push(item.end);
      }
      return { ...item, lane: assignedLane };
    });
    return { packedTextOverlays: packed, textLaneCount: Math.max(1, laneEndTimes.length) };
  }, [textOverlays]);

  const TEXT_LANE_ROW_H = 26;
  const textTrackHeight = Math.max(TEXT_OVERLAY_H, textLaneCount * TEXT_LANE_ROW_H + 4);

  // Geometry for every row, resolved once. Both the label gutter and the lanes
  // spread the same object, so a row cannot be spaced differently on the two
  // sides -- which is exactly how the labels drifted out from under their lanes.
  const gutterW = dense ? GUTTER_DENSE : GUTTER;

  const rows = useMemo(
    () => layoutRows({
      heights: { text: textTrackHeight },
      present: { text: hasTextOverlays },
      collapsed: { audio: audioCollapsed },
    }),
    [textTrackHeight, hasTextOverlays, audioCollapsed],
  );
  const visibleStems = audioCollapsed ? STEMS.slice(0, 1) : STEMS;
  const rowStyleOf = useMemo(() => {
    const byKey = {};
    rows.forEach((r) => { byKey[r.key] = { height: r.height, marginTop: r.marginTop }; });
    return byKey;
  }, [rows]);
  const rowStyle = (key) => rowStyleOf[key] || { height: 0, marginTop: 0 };
  const tracksHeight = rows.reduce((sum, r) => sum + r.height + r.marginTop, 0);

  // Close context menu & transition popover on outside pointer click or Escape
  useEffect(() => {
    const handleGlobalPointer = (e) => {
      if (transitionMenuClipId && !e.target.closest('[data-transition-popover]') && !e.target.closest('[data-transition-trigger]')) {
        setTransitionMenuClipId(null);
      }
      if (contextMenu && !e.target.closest('[data-context-menu]')) {
        setContextMenu(null);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setTransitionMenuClipId(null);
        setContextMenu(null);
      }
    };
    window.addEventListener('pointerdown', handleGlobalPointer);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('pointerdown', handleGlobalPointer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [transitionMenuClipId, contextMenu]);

  const handleClipContextMenu = (e, seg) => {
    setTransitionMenuClipId(null);
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      seg,
    });
  };

  // Ctrl/Cmd+wheel has to be bound natively with { passive: false }: React
  // registers its own root `wheel` listener as passive, so preventDefault()
  // inside an onWheel prop is ignored and the browser page-zooms instead of
  // the timeline.
  const scrollRef = useRef(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheelNative = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      onZoom?.(e.deltaY < 0 ? 1 : -1);
    };
    el.addEventListener('wheel', onWheelNative, { passive: false });
    return () => el.removeEventListener('wheel', onWheelNative);
  }, [onZoom]);

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
  const indexFromX = (clientX) => {
    if (!laneRef.current) return segments.length;
    const t = (clientX - laneRef.current.getBoundingClientRect().left) / pxPerSec;
    let i = 0;
    while (i < segments.length && t > (segments[i].segStart + segments[i].segEnd) / 2) i += 1;
    return i;
  };
  const dragHasClip = (e) => Array.from(e.dataTransfer?.types || []).includes(CLIP_DRAG_TYPE);
  const onDragOverTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDropIndex(indexFromX(e.clientX));
  };
  const onDropTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    const at = indexFromX(e.clientX);
    setDropIndex(null);
    try {
      onDropClip?.(JSON.parse(e.dataTransfer.getData(CLIP_DRAG_TYPE)), at);
    } catch (err) { /* malformed payload -- nothing to insert */ }
  };

  // Dragging a clip body reorders it. The clip reports pointer positions; the
  // decision lives here because only the timeline knows where the other clips
  // are. Each crossing is one swap, and the whole gesture is one undo step.
  const onBodyDragStart = () => { bodyDrag.current = true; dragBegin(); };
  const onBodyDragMove = (clipId, clientX) => {
    if (!bodyDrag.current || !laneRef.current) return false;
    const t = (clientX - laneRef.current.getBoundingClientRect().left) / pxPerSec;
    const myIdx = segments.findIndex((s) => s.clip.id === clipId);
    const overIdx = segments.findIndex((s) => t >= s.segStart && t < s.segEnd);
    if (myIdx === -1 || overIdx === -1 || overIdx === myIdx) return false;
    return reorder(clipId, overIdx > myIdx ? 1 : -1, true);
  };
  const onBodyDragEnd = () => {
    if (!bodyDrag.current) return;
    bodyDrag.current = false;
    dragEnd();
  };

  const contentWidth = Math.max(audioDuration || 0, totalDuration, 1) * pxPerSec + 240;
  const step = tickStep(pxPerSec);
  const ticks = useMemo(() => {
    const span = Math.max(totalDuration, audioDuration || 0);
    const out = [];
    for (let t = 0; t <= span + step; t += step) out.push(t);
    return out;
  }, [totalDuration, audioDuration, step]);

  const timeFromEvent = (e) => {
    const lane = laneRef.current;
    if (!lane) return 0;
    const rect = lane.getBoundingClientRect();
    const maxT = Math.max(totalDuration, audioDuration || 0);
    const rawT = (e.clientX - rect.left) / pxPerSec;
    return Math.max(0, maxT > 0 ? Math.min(maxT, rawT) : rawT);
  };

  const startScrub = (e) => {
    scrubbing.current = true;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* scrub still works */ }
    onSeek?.(timeFromEvent(e));
  };
  const moveScrub = (e) => { if (scrubbing.current) onSeek?.(timeFromEvent(e)); };
  const endScrub = (e) => {
    scrubbing.current = false;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
  };

  const handleTrackAreaPointerDown = (e) => {
    if (e.button !== 0) return;
    const isInteractive = e.target.closest(
      'button, [role="button"], [data-trim-handle], [data-transition-trigger], [data-transition-popover], [data-timeline-item]'
    );
    if (isInteractive) return;

    deselectAll();
    scrubbing.current = true;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* scrub still works */ }
    onSeek?.(timeFromEvent(e));
  };

  const startTrim = (e, cue, edge) => {
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    captionTrim.current = {
      uid: cue._uid,
      edge,
      startX: e.clientX,
      start: cue.start,
      end: cue.end,
      initialCues: (cues || []).map((c) => ({ ...c })),
      moved: false,
    };
  };

  const moveTrim = (e) => {
    const d = captionTrim.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin(); }

    if (d.edge === 'left') {
      const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
      const minStart = (snapEnabled && targetIdx > 0) ? d.initialCues[targetIdx - 1].end : 0;
      const rawStart = Math.max(minStart, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      const finalStart = Math.max(minStart, Math.round(snapped * 100) / 100);
      shiftCaption(d.uid, { start: finalStart });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      const newEnd = Math.round(Math.max(d.start + 0.2, snapped) * 100) / 100;

      if (snapEnabled && (onCuesChange || onCaptionRippleShift)) {
        const nextCues = applyCaptionMagneticRipple(d.initialCues, d.uid, d.start, newEnd);
        (onCuesChange || onCaptionRippleShift)(nextCues, true);
      } else {
        shiftCaption(d.uid, { end: newEnd });
      }
    }
  };

  const endTrim = (e) => {
    const d = captionTrim.current;
    captionTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd();
  };

  const startTextTrim = (e, item, edge) => {
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    textTrim.current = {
      id: item.id,
      edge,
      startX: e.clientX,
      start: item.start,
      end: item.end,
      moved: false,
    };
  };

  const moveTextTrim = (e) => {
    const d = textTrim.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin(); }

    if (d.edge === 'left') {
      const rawStart = Math.max(0, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      shiftTextOverlay(d.id, { start: Math.round(snapped * 100) / 100 });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      shiftTextOverlay(d.id, { end: Math.round(snapped * 100) / 100 });
    }
  };

  const endTextTrim = (e) => {
    const d = textTrim.current;
    textTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd();
  };

  const hookTrim = useRef(null);

  const startHookTrim = (e) => {
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    hookTrim.current = {
      startX: e.clientX,
      startDuration: hookDuration || 3.0,
      moved: false,
    };
  };

  const moveHookTrim = (e) => {
    const d = hookTrim.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin(); }
    const rawDur = Math.max(1.0, Math.min(8.0, d.startDuration + delta));
    const snapped = snapFunction(rawDur, snapPoints);
    const clamped = Math.max(1.0, Math.min(8.0, Math.round(snapped * 10) / 10));
    onHookDurationChange?.(clamped);
  };

  const endHookTrim = (e) => {
    const d = hookTrim.current;
    hookTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd();
  };

  const sfxMarkers = (cues || []).filter((c) => c.sfx);

  return (
    <div className="flex h-full flex-col bg-[#1C1B19]">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <div style={{ width: contentWidth, minWidth: '100%' }} className="relative">

          {/* Ruler: click or drag to scrub */}
          <div className="sticky top-0 z-20 flex bg-[#1C1B19]">
            <div style={{ width: gutterW }} className="flex-shrink-0" />
            <div
              onPointerDown={startScrub}
              onPointerMove={moveScrub}
              onPointerUp={endScrub}
              onPointerCancel={endScrub}
              className="relative flex-1 cursor-text touch-none border-b border-[#363430]"
              style={{ height: RULER_H }}
              title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"
            >
              {ticks.map((t) => (
                <div key={t} className="pointer-events-none absolute top-0 h-full" style={{ left: t * pxPerSec }}>
                  <span className="absolute top-0 h-2 w-px bg-[#4A4742]" />
                  <span className="absolute top-2 -translate-x-1/2 font-mono text-xs text-[#9C968F]">
                    {formatTimecode(t)}
                  </span>
                </div>
              ))}
            </div>
          </div>

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
              <div style={rowStyle('caption')} className="flex items-center">
                <TrackLabel
                  width={gutterW}
                  slotWidth={dense ? 14 : 26}
                  icon={MessageSquare}
                  action={
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onToggleHideCaption?.(); }}
                      title={isCaptionHidden ? 'คลิกเพื่อแสดงคำบรรยายบนพรีวิว' : 'คลิกเพื่อซ่อนคำบรรยายบนพรีวิว'}
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
                  คำบรรยาย
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
              className="relative flex-1"
              onPointerDown={handleTrackAreaPointerDown}
              onPointerMove={moveScrub}
              onPointerUp={endScrub}
              onPointerCancel={endScrub}
            >
              {/* video track */}
              <div
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
                    filmstrip={filmstrips?.[seg.clip.id]}
                    onSelect={selectClip}
                    onContextMenu={handleClipContextMenu}
                    onTrim={trimClip}
                    onTrimBegin={dragBegin}
                    onTrimEnd={dragEnd}
                    onReorder={(id, dir) => reorder(id, dir, false)}
                    onBodyDragStart={onBodyDragStart}
                    onBodyDragMove={onBodyDragMove}
                    onBodyDragEnd={onBodyDragEnd}
                    snapCandidates={snapPoints}
                    snapFunction={snapFunction}
                  />
                ))}

                {segments.slice(1).map((seg) => {
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
                          setTransitionMenuClipId(isOpen ? null : seg.clip.id);
                        }}
                        title={isFade
                          ? `${currentTransition} ${seg.overlap.toFixed(1)} วิ — คลิกเพื่อเปลี่ยนทรานซิชัน`
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
                      {isOpen && (
                        <div
                          data-transition-popover=""
                          onClick={(e) => e.stopPropagation()}
                          className={`pointer-events-auto absolute bottom-full mb-2 z-50 w-56 rounded-xl border border-[#4A4742] bg-[#1C1B19]/95 p-2.5 shadow-2xl backdrop-blur-md text-xs text-[#EDE9E3] animate-in fade-in zoom-in-95 duration-150 ${
                            leftPx < 120 ? 'left-0' : '-translate-x-1/2'
                          }`}
                        >
                          <div className="flex items-center justify-between pb-1.5 border-b border-[#363430]">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <Waves className="h-3.5 w-3.5 text-[#25F4EE]" /> รอยต่อคลิป
                            </span>
                            <button
                              type="button"
                              onClick={() => setTransitionMenuClipId(null)}
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
                                setTransitionMenuClipId(null);
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
                              {TRANSITIONS.slice(0, 8).map((t) => {
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
                                      setTransitionMenuClipId(null);
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

                          {/* Duration presets */}
                          <div className="pt-2 border-t border-[#363430]">
                            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1.5">
                              <span>ความยาวรอยต่อ:</span>
                              <span className="font-mono font-bold text-[#25F4EE]">{currentDuration.toFixed(1)}s</span>
                            </div>
                            <div className="grid grid-cols-4 gap-1">
                              {[0.3, 0.5, 0.8, 1.0].map((d) => (
                                <button
                                  key={d}
                                  type="button"
                                  onClick={() => {
                                    onClipChange?.(seg.clip.id, {
                                      transition_in: currentTransition === 'cut' ? 'fade' : currentTransition,
                                      transition_duration: d,
                                    });
                                  }}
                                  className={`py-0.5 rounded text-center font-mono text-xs transition-colors ${
                                    Math.abs(currentDuration - d) < 0.05
                                      ? 'bg-[#25F4EE]/20 border border-[#25F4EE] text-[#25F4EE] font-bold'
                                      : 'bg-[#282724] hover:bg-[#363430] text-slate-400'
                                  }`}
                                >
                                  {d}s
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* hook header track */}
              <div className="relative rounded bg-[#181716]" style={rowStyle('hook')}>
                {(() => {
                  const hookText = [hookBrand, hookModel, hookLabel].filter(Boolean).join(' · ') || 'ป้ายฮุกพาดหัว (Hook Header)';
                  const isSelected = selection?.type === 'hook';
                  const dur = hookDuration || 3.0;
                  const w = Math.max(24, dur * pxPerSec);

                  return (
                    <div
                      data-timeline-item="hook"
                      onClick={(e) => {
                        e.stopPropagation();
                        const t = timeFromEvent(e);
                        if (onSelectHook) onSelectHook();
                        else onSelect?.({ type: 'hook' });
                        if (typeof t === 'number' && t >= 0 && t <= dur) {
                          onSeek?.(t);
                        } else if (playhead < 0 || playhead > dur + 0.05) {
                          onSeek?.(0);
                        }
                      }}
                      title={`${hookText} (0.0s - ${dur.toFixed(1)}s)`}
                      className={`group absolute top-0.5 h-[calc(100%-4px)] touch-none select-none rounded text-left text-xs transition-colors duration-150 flex items-center ${
                        !showHookHeader
                          ? 'opacity-40 bg-[#282724] text-[#9C968F] ring-1 ring-white/10'
                          : isSelected
                            ? 'bg-[#3A3018] text-[#FFE600] ring-2 ring-[#E6C24A] shadow-[0_0_12px_rgba(230,194,74,0.3)]'
                            : 'bg-[#2A2415] text-[#E6C24A] ring-1 ring-[#594B22] hover:ring-[#8C7636]'
                      }`}
                      style={{ left: 0, width: w }}
                    >
                      {/* Body */}
                      <div className="flex-1 min-w-0 h-full flex items-center px-2 gap-1.5 overflow-hidden cursor-pointer">
                        <Sparkles className="h-3 w-3 flex-shrink-0 text-[#E6C24A]" />
                        <span className="truncate font-semibold text-[11px] tracking-wide">
                          {hookText}
                        </span>
                        <span className="font-mono text-[10px] text-[#E6C24A]/70 flex-shrink-0 ml-auto">
                          {dur.toFixed(1)}s
                        </span>
                      </div>

                      {/* Right Trim Handle for Hook Duration */}
                      <div
                        onPointerDown={startHookTrim}
                        onPointerMove={moveHookTrim}
                        onPointerUp={endHookTrim}
                        onPointerCancel={endHookTrim}
                        title="ลากเพื่อปรับระยะเวลาแสดงผลป้ายฮุก (1.0 - 8.0 วิ)"
                        className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r hover:bg-[#E6C24A] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                      >
                        <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* caption track */}
              <div className="relative rounded bg-[#181716]" style={rowStyle('caption')}>
                {(cues || []).map((cue) => {
                  const selected = selection?.type === 'caption' && selection.id === cue._uid;
                  const w = Math.max(14, (cue.end - cue.start) * pxPerSec);
                  return (
                    <div
                      key={cue._uid}
                      data-timeline-item="caption"
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
                    >
                      {/* Left Trim Handle */}
                      <div
                        onPointerDown={(e) => startTrim(e, cue, 'left')}
                        onPointerMove={moveTrim}
                        onPointerUp={endTrim}
                        onPointerCancel={endTrim}
                        title="ลากเพื่อยืด/หดเวลาเริ่มต้น"
                        className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-l hover:bg-[#D97757] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                      >
                        <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                      </div>

                      {/* Middle Body (Drag to shift entire cue) */}
                      <div
                        onPointerDown={(e) => {
                          try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
                          captionDrag.current = {
                            uid: cue._uid,
                            startX: e.clientX,
                            start: cue.start,
                            end: cue.end,
                            initialCues: (cues || []).map((c) => ({ ...c })),
                            moved: false,
                          };
                        }}
                        onPointerMove={(e) => {
                          const d = captionDrag.current;
                          if (!d || d.uid !== cue._uid) return;
                          const delta = (e.clientX - d.startX) / pxPerSec;
                          if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
                          if (!d.moved) { d.moved = true; dragBegin(); }

                          const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
                          const dur = Math.round((d.end - d.start) * 100) / 100;
                          const minStart = (snapEnabled && targetIdx > 0) ? d.initialCues[targetIdx - 1].end : 0;

                          const rawStart = Math.max(minStart, d.start + delta);
                          const snappedStart = snapFunction(rawStart, snapPoints);
                          const finalStart = Math.max(minStart, Math.round(snappedStart * 100) / 100);
                          const finalEnd = Math.round((finalStart + dur) * 100) / 100;

                          if (snapEnabled && (onCuesChange || onCaptionRippleShift)) {
                            const nextCues = applyCaptionMagneticRipple(d.initialCues, d.uid, finalStart, finalEnd);
                            (onCuesChange || onCaptionRippleShift)(nextCues, true);
                          } else {
                            shiftCaption(cue._uid, {
                              start: finalStart,
                              end: finalEnd,
                            });
                          }
                        }}
                        onPointerUp={(e) => {
                          const d = captionDrag.current;
                          captionDrag.current = null;
                          try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                          if (d?.moved) dragEnd();
                        }}
                        onPointerCancel={(e) => {
                          const d = captionDrag.current;
                          captionDrag.current = null;
                          try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                          if (d?.moved) dragEnd();
                        }}
                        className="flex-1 min-w-0 h-full flex items-center px-1 overflow-hidden cursor-grab active:cursor-grabbing"
                      >
                        <span className="truncate">{cue.text}</span>
                      </div>

                      {/* Right Trim Handle */}
                      <div
                        onPointerDown={(e) => startTrim(e, cue, 'right')}
                        onPointerMove={moveTrim}
                        onPointerUp={endTrim}
                        onPointerCancel={endTrim}
                        title="ลากเพื่อยืด/หดเวลาสิ้นสุด"
                        className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r hover:bg-[#D97757] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                      >
                        <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                      </div>
                    </div>
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
                      <div
                        key={item.id}
                        data-timeline-item="text_overlay"
                        onClick={(e) => { e.stopPropagation(); selectTextOverlay(item.id); }}
                        title={`${item.text || 'ข้อความเสริม'} (${item.start.toFixed(2)}s - ${item.end.toFixed(2)}s)`}
                        className={`group absolute touch-none select-none rounded text-left text-xs leading-[18px] transition-colors duration-150 flex items-center ${
                          selected
                            ? 'bg-[#153434] text-[#25F4EE] ring-2 ring-[#25F4EE] shadow-[0_0_10px_rgba(37,244,238,0.25)] z-10'
                            : 'bg-[#1C2626] text-[#A2CCCC] ring-1 ring-[#2E4848] hover:ring-[#477070]'
                        }`}
                        style={{
                          left: item.start * pxPerSec,
                          width: w,
                          top: topPx,
                          height: TEXT_LANE_ROW_H - 4,
                        }}
                      >
                        {/* Left Trim Handle */}
                        <div
                          onPointerDown={(e) => startTextTrim(e, item, 'left')}
                          onPointerMove={moveTextTrim}
                          onPointerUp={endTextTrim}
                          onPointerCancel={endTextTrim}
                          title="ลากเพื่อยืด/หดเวลาเริ่มต้น"
                          className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-l hover:bg-[#25F4EE] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                        >
                          <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                        </div>

                        {/* Middle Body (Drag to shift entire text overlay) */}
                        <div
                          onPointerDown={(e) => {
                            try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
                            textDrag.current = {
                              id: item.id, startX: e.clientX, start: item.start, end: item.end, moved: false,
                            };
                          }}
                          onPointerMove={(e) => {
                            const d = textDrag.current;
                            if (!d || d.id !== item.id) return;
                            const delta = (e.clientX - d.startX) / pxPerSec;
                            if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
                            if (!d.moved) { d.moved = true; dragBegin(); }
                            const shift = Math.max(-d.start, delta);
                            const rawStart = d.start + shift;
                            const snappedStart = snapFunction(rawStart, snapPoints);
                            const correction = snappedStart - rawStart;
                            shiftTextOverlay(item.id, {
                              start: Math.round((d.start + shift + correction) * 100) / 100,
                              end: Math.round((d.end + shift + correction) * 100) / 100,
                            });
                          }}
                          onPointerUp={(e) => {
                            const d = textDrag.current;
                            textDrag.current = null;
                            try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                            if (d?.moved) dragEnd();
                          }}
                          onPointerCancel={(e) => {
                            const d = textDrag.current;
                            textDrag.current = null;
                            try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                            if (d?.moved) dragEnd();
                          }}
                          className="flex-1 min-w-0 h-full flex items-center px-1.5 overflow-hidden cursor-grab active:cursor-grabbing gap-1"
                        >
                          <Type className="h-3 w-3 flex-shrink-0 text-[#25F4EE]" />
                          <span className="truncate font-medium">{item.text || 'ข้อความเสริม'}</span>
                        </div>

                        {/* Right Trim Handle */}
                        <div
                          onPointerDown={(e) => startTextTrim(e, item, 'right')}
                          onPointerMove={moveTextTrim}
                          onPointerUp={endTextTrim}
                          onPointerCancel={endTextTrim}
                          title="ลากเพื่อยืด/หดเวลาสิ้นสุด"
                          className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r hover:bg-[#25F4EE] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                        >
                          <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                        </div>
                      </div>
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

                    {/* clip lane: a block wherever a clip contributes its own audio.
                        Clip volume defaults to 0, so this lane is empty for most
                        projects -- say so rather than leaving a blank strip. */}
                    {key === 'clip' && !segments.some((s) => Number(s.clip.volume) > 0) && (
                      <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[#6F6A64]">
                        ยังไม่ได้เปิดเสียงในคลิป — ตั้งระดับได้ที่แผงขวา
                      </span>
                    )}
                    {key === 'clip' && segments.filter((s) => Number(s.clip.volume) > 0).map((s) => (
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

              {/* playhead */}
              <div
                className="pointer-events-none absolute z-30"
                style={{ left: playhead * pxPerSec, top: -RULER_H - TRACK_TOP, bottom: 0 }}
              >
                <div className="absolute bottom-0 left-0 top-0 w-0.5 -translate-x-1/2 bg-[#D97757]" />
                <div className="absolute top-0 h-2.5 w-2.5 -translate-x-1/2 rotate-45 bg-[#D97757]" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right-Click Context Menu on Video Clips */}
      {contextMenu && (
        <div
          data-context-menu=""
          onClick={(e) => e.stopPropagation()}
          className="fixed z-50 min-w-[190px] rounded-xl border border-[#4A4742] bg-[#1E1D1A]/95 p-1.5 shadow-2xl backdrop-blur-md text-xs text-[#EDE9E3] animate-in fade-in zoom-in-95 duration-100"
          style={{
            left: Math.max(10, Math.min(window.innerWidth - 200, contextMenu.x)),
            top: Math.max(10, Math.min(window.innerHeight - 230, contextMenu.y)),
          }}
        >
          <div className="px-2 py-1 font-mono text-[10px] font-semibold text-[#9C968F] border-b border-[#363430] truncate">
            {contextMenu.seg.clip.source_path?.split(/[\\/]/).pop()}
          </div>
          <div className="py-1 space-y-0.5">
            <button
              type="button"
              onClick={() => {
                onSplit?.();
                setContextMenu(null);
              }}
              className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[#D97757]/20 hover:text-[#E89274] transition-colors"
            >
              <span className="flex items-center gap-2">
                <Scissors className="h-3.5 w-3.5" />
                <span>ผ่าคลิปตรงหัวอ่าน</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">S / Ctrl+B</span>
            </button>
            <button
              type="button"
              onClick={() => {
                onDuplicate?.();
                setContextMenu(null);
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#2C2B27] transition-colors"
            >
              <Copy className="h-3.5 w-3.5" />
              <span>ทำสำเนาคลิป</span>
            </button>
            <button
              type="button"
              onClick={() => {
                onToggleMirror?.();
                setContextMenu(null);
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#2C2B27] transition-colors"
            >
              <FlipHorizontal2 className="h-3.5 w-3.5" />
              <span>กลับด้านภาพ (Mirror)</span>
            </button>
          </div>

          <div className="my-1 border-t border-[#363430]" />
          <div className="px-2 py-1 text-[10px] text-[#9C968F] flex items-center gap-1">
            <Gauge className="h-3 w-3" />
            <span>ปรับความเร็ว:</span>
          </div>
          <div className="grid grid-cols-4 gap-1 px-1">
            {[0.5, 1, 1.5, 2].map((sp) => {
              const cur = contextMenu.seg.clip.speed || 1;
              return (
                <button
                  key={sp}
                  type="button"
                  onClick={() => {
                    onClipChange?.(contextMenu.seg.clip.id, { speed: sp === 1 ? undefined : sp });
                    setContextMenu(null);
                  }}
                  className={`py-1 rounded text-center font-semibold transition-colors ${
                    cur === sp
                      ? 'bg-[#D97757] text-white'
                      : 'bg-[#282724] hover:bg-[#363430] text-[#C9C3BB]'
                  }`}
                >
                  {sp}x
                </button>
              );
            })}
          </div>

          <div className="my-1 border-t border-[#363430]" />
          <button
            type="button"
            onClick={() => {
              onDelete?.();
              setContextMenu(null);
            }}
            className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-rose-400 hover:bg-rose-500/20 transition-colors"
          >
            <span className="flex items-center gap-2">
              <Trash2 className="h-3.5 w-3.5" />
              <span>ลบคลิป</span>
            </span>
            <span className="text-[10px] text-rose-400/60 font-mono">Del</span>
          </button>
        </div>
      )}
    </div>
  );
}
