import { useRef } from 'react';
import { applyCaptionMagneticRipple } from '../lib/timelineTrackModel';
import { resolveSnapCandidateLabel } from '../lib/timelineMath';
import { withoutPlayheadCandidate } from '../lib/timelineTrimOps';
import { beginDragAfterThreshold, capturePointer, releasePointer } from '../lib/timelineDragLifecycle';
import { HOOK_MIN_DURATION, HOOK_MAX_DURATION } from '../components/editor/Timeline';

export function useTimelineDrag({
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
  onSnapGuide,
  onRippleTriggered,
}) {
  const scrubbing = useRef(false);
  const captionDrag = useRef(null);
  const captionTrim = useRef(null);
  const textDrag = useRef(null);
  const textTrim = useRef(null);
  const hookTrim = useRef(null);
  const stickerTrim = useRef(null);
  const stickerDragRef = useRef(null);
  const effectTrim = useRef(null);
  const effectDragRef = useRef(null);
  const bodyDrag = useRef(null);

  const notifySnap = (rawTime, snappedTime) => {
    if (!snapEnabled) {
      onSnapGuide?.(null);
      return;
    }
    if (Math.abs(snappedTime - rawTime) > 0.001) {
      const label = resolveSnapCandidateLabel(snappedTime, {
        playhead,
        segments,
        cues,
        audioDuration,
      });
      onSnapGuide?.({ time: snappedTime, label });
    } else {
      onSnapGuide?.(null);
    }
  };

  const timeFromEvent = (e) => {
    const lane = laneRef.current;
    if (!lane) return 0;
    const rect = lane.getBoundingClientRect();
    const maxT = Math.max(totalDuration, audioDuration || 0);
    const rawT = (e.clientX - rect.left) / pxPerSec;
    return Math.max(0, maxT > 0 ? Math.min(maxT, rawT) : rawT);
  };

  // Scrubbing snaps to the same targets as clip trimming (clip edges, cue
  // edges, beats, audio end) while magnetic snap is on; holding Shift bypasses
  // it. The playhead's own target is left out: it is wherever the pointer just
  // was, so snapping to it would freeze a slow scrub in place.
  const scrubTimeFromEvent = (e) => {
    const rawT = timeFromEvent(e);
    if (!snapEnabled || e.shiftKey || !snapFunction) {
      onSnapGuide?.(null);
      return rawT;
    }
    const snapped = snapFunction(rawT, withoutPlayheadCandidate(snapPoints, playhead));
    notifySnap(rawT, snapped);
    const maxT = Math.max(totalDuration, audioDuration || 0);
    return Math.max(0, maxT > 0 ? Math.min(maxT, snapped) : snapped);
  };

  const startScrub = (e) => {
    scrubbing.current = true;
    capturePointer(e);
    onSeek?.(scrubTimeFromEvent(e));
  };

  const moveScrub = (e) => {
    if (scrubbing.current) onSeek?.(scrubTimeFromEvent(e));
  };

  const endScrub = (e) => {
    const wasScrubbing = scrubbing.current;
    scrubbing.current = false;
    releasePointer(e);
    if (wasScrubbing) onSnapGuide?.(null);
  };

  const handleTrackAreaPointerDown = (e) => {
    if (e.button !== 0) return;
    const isInteractive = e.target.closest(
      'button, [role="button"], [data-trim-handle], [data-transition-trigger], [data-transition-popover], [data-timeline-item]'
    );
    if (isInteractive) return;

    deselectAll?.();
    scrubbing.current = true;
    capturePointer(e);
    onSeek?.(scrubTimeFromEvent(e));
  };

  // Body drag reorders clips
  const onBodyDragStart = () => {
    bodyDrag.current = true;
    dragBegin?.();
  };

  const onBodyDragMove = (clipId, clientX) => {
    if (!bodyDrag.current || !laneRef.current) return false;
    const t = (clientX - laneRef.current.getBoundingClientRect().left) / pxPerSec;
    const myIdx = segments.findIndex((s) => s.clip.id === clipId);
    const overIdx = segments.findIndex((s) => t >= s.segStart && t < s.segEnd);
    if (myIdx === -1 || overIdx === -1 || overIdx === myIdx) return false;
    return reorder?.(clipId, overIdx > myIdx ? 1 : -1, true);
  };

  const onBodyDragEnd = () => {
    if (!bodyDrag.current) return;
    bodyDrag.current = false;
    dragEnd?.();
  };

  // Caption trim
  const startTrim = (e, cue, edge) => {
    e.stopPropagation();
    capturePointer(e);
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
    if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;

    if (d.edge === 'left') {
      const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
      const minStart = (snapEnabled && targetIdx > 0) ? d.initialCues[targetIdx - 1].end : 0;
      const rawStart = Math.max(minStart, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      notifySnap(rawStart, snapped);
      const finalStart = Math.max(minStart, Math.round(snapped * 100) / 100);
      shiftCaption?.(d.uid, { start: finalStart });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      notifySnap(rawEnd, snapped);
      const newEnd = Math.round(Math.max(d.start + 0.2, snapped) * 100) / 100;

      if (snapEnabled && (onCuesChange || onCaptionRippleShift)) {
        const nextCues = applyCaptionMagneticRipple(d.initialCues, d.uid, d.start, newEnd);
        (onCuesChange || onCaptionRippleShift)(nextCues, true);
        const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
        const rippleCount = (d.initialCues?.length || 0) - 1 - targetIdx;
        if (rippleCount > 0) {
          onRippleTriggered?.({ count: rippleCount, time: newEnd, type: 'caption' });
        }
      } else {
        shiftCaption?.(d.uid, { end: newEnd });
      }
    }
  };

  const endTrim = (e) => {
    const d = captionTrim.current;
    captionTrim.current = null;
    releasePointer(e);
    onSnapGuide?.(null);
    if (d?.moved) dragEnd?.();
  };

  // Caption body drag
  const startCaptionBodyDrag = (e, cue) => {
    capturePointer(e);
    captionDrag.current = {
      uid: cue._uid,
      startX: e.clientX,
      start: cue.start,
      end: cue.end,
      initialCues: (cues || []).map((c) => ({ ...c })),
      moved: false,
    };
  };

  const moveCaptionBodyDrag = (e, cue) => {
    const d = captionDrag.current;
    if (!d || d.uid !== cue._uid) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;

    const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
    const dur = Math.round((d.end - d.start) * 100) / 100;
    const minStart = (snapEnabled && targetIdx > 0) ? d.initialCues[targetIdx - 1].end : 0;

    const rawStart = Math.max(minStart, d.start + delta);
    const snappedStart = snapFunction(rawStart, snapPoints);
    notifySnap(rawStart, snappedStart);
    const finalStart = Math.max(minStart, Math.round(snappedStart * 100) / 100);
    const finalEnd = Math.round((finalStart + dur) * 100) / 100;

    if (snapEnabled && (onCuesChange || onCaptionRippleShift)) {
      const nextCues = applyCaptionMagneticRipple(d.initialCues, d.uid, finalStart, finalEnd);
      (onCuesChange || onCaptionRippleShift)(nextCues, true);
      const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
      const rippleCount = (d.initialCues?.length || 0) - 1 - targetIdx;
      if (rippleCount > 0) {
        onRippleTriggered?.({ count: rippleCount, time: finalStart, type: 'caption' });
      }
    } else {
      shiftCaption?.(cue._uid, {
        start: finalStart,
        end: finalEnd,
      });
    }
  };

  const endCaptionBodyDrag = (e) => {
    const d = captionDrag.current;
    captionDrag.current = null;
    releasePointer(e);
    onSnapGuide?.(null);
    if (d?.moved) dragEnd?.();
  };

  // Text overlay trim
  const startTextTrim = (e, item, edge) => {
    e.stopPropagation();
    capturePointer(e);
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
    if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;

    if (d.edge === 'left') {
      const rawStart = Math.max(0, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      notifySnap(rawStart, snapped);
      shiftTextOverlay?.(d.id, { start: Math.round(snapped * 100) / 100 });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      notifySnap(rawEnd, snapped);
      shiftTextOverlay?.(d.id, { end: Math.round(snapped * 100) / 100 });
    }
  };

  const endTextTrim = (e) => {
    const d = textTrim.current;
    textTrim.current = null;
    releasePointer(e);
    onSnapGuide?.(null);
    if (d?.moved) dragEnd?.();
  };

  // Text overlay body drag
  const startTextBodyDrag = (e, item) => {
    capturePointer(e);
    textDrag.current = {
      id: item.id,
      startX: e.clientX,
      start: item.start,
      end: item.end,
      moved: false,
    };
  };

  const moveTextBodyDrag = (e, item) => {
    const d = textDrag.current;
    if (!d || d.id !== item.id) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;
    const shift = Math.max(-d.start, delta);
    const rawStart = d.start + shift;
    const snappedStart = snapFunction(rawStart, snapPoints);
    notifySnap(rawStart, snappedStart);
    const correction = snappedStart - rawStart;
    shiftTextOverlay?.(item.id, {
      start: Math.round((d.start + shift + correction) * 100) / 100,
      end: Math.round((d.end + shift + correction) * 100) / 100,
    });
  };

  const endTextBodyDrag = (e) => {
    const d = textDrag.current;
    textDrag.current = null;
    releasePointer(e);
    onSnapGuide?.(null);
    if (d?.moved) dragEnd?.();
  };

  // Hook duration trim
  const startHookTrim = (e) => {
    e.stopPropagation();
    if (!hookOverlay) return;
    capturePointer(e);
    hookTrim.current = {
      startX: e.clientX,
      startEnd: hookOverlay.end,
      start: hookOverlay.start,
      moved: false,
    };
  };

  const moveHookTrim = (e) => {
    const d = hookTrim.current;
    if (!d || !hookOverlay) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;
    const rawEnd = d.startEnd + delta;
    const snapped = snapFunction(rawEnd, snapPoints);
    notifySnap(rawEnd, snapped);
    const minEnd = d.start + HOOK_MIN_DURATION;
    const maxEnd = d.start + HOOK_MAX_DURATION;
    const clamped = Math.max(minEnd, Math.min(maxEnd, Math.round(snapped * 10) / 10));
    onUpdateOverlay?.(hookOverlay.id, { end: clamped }, true);
  };

  const endHookTrim = (e) => {
    const d = hookTrim.current;
    hookTrim.current = null;
    releasePointer(e);
    onSnapGuide?.(null);
    if (d?.moved) dragEnd?.();
  };

  // Sticker and Effect share one interval-drag lifecycle. Their adapters below
  // retain the different persistence fields and the sticker legacy fallback.
  const createTimedIntervalDrag = ({ trimRef, bodyRef, readWindow, onTrimUpdate, onBodyUpdate }) => {
    const startTrim = (e, edge, item) => {
      capturePointer(e);
      const { start, end } = readWindow(item);
      trimRef.current = { edge, startX: e.clientX, start, end, id: item?.id, moved: false };
    };

    const moveTrim = (e) => {
      const d = trimRef.current;
      if (!d) return;
      const delta = (e.clientX - d.startX) / pxPerSec;
      if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;

      if (d.edge === 'left') {
        const rawStart = Math.max(0, Math.min(d.end - 0.3, d.start + delta));
        const snapped = snapFunction(rawStart, snapPoints);
        notifySnap(rawStart, snapped);
        onTrimUpdate({ id: d.id, edge: 'left', value: Math.round(snapped * 10) / 10 });
      } else {
        const maxEnd = Math.max(totalDuration, audioDuration || 0) || 999;
        const rawEnd = Math.max(d.start + 0.3, Math.min(maxEnd, d.end + delta));
        const snapped = snapFunction(rawEnd, snapPoints);
        notifySnap(rawEnd, snapped);
        onTrimUpdate({ id: d.id, edge: 'right', value: Math.round(snapped * 10) / 10 });
      }
    };

    const endTrim = (e) => {
      const d = trimRef.current;
      trimRef.current = null;
      releasePointer(e);
      onSnapGuide?.(null);
      if (d?.moved) dragEnd?.();
    };

    const startBodyDrag = (e, item) => {
      capturePointer(e);
      const { start, end } = readWindow(item);
      bodyRef.current = {
        startX: e.clientX,
        start,
        end,
        id: item?.id,
        duration: Math.max(0.3, end - start),
        moved: false,
      };
    };

    const moveBodyDrag = (e) => {
      const d = bodyRef.current;
      if (!d) return;
      const delta = (e.clientX - d.startX) / pxPerSec;
      if (!beginDragAfterThreshold(d, e.clientX, dragBegin)) return;
      const maxT = Math.max(totalDuration, audioDuration || 0) || 999;
      const maxStart = Math.max(0, maxT - d.duration);
      const rawStart = Math.max(0, Math.min(maxStart, d.start + delta));
      const snappedStart = snapFunction(rawStart, snapPoints);
      notifySnap(rawStart, snappedStart);
      const finalStart = Math.round(snappedStart * 10) / 10;
      const finalEnd = Math.round((finalStart + d.duration) * 10) / 10;
      onBodyUpdate({ id: d.id, start: finalStart, end: finalEnd });
    };

    const endBodyDrag = (e) => {
      const d = bodyRef.current;
      bodyRef.current = null;
      releasePointer(e);
      onSnapGuide?.(null);
      if (d?.moved) dragEnd?.();
    };

    return { startTrim, moveTrim, endTrim, startBodyDrag, moveBodyDrag, endBodyDrag };
  };

  const stickerIntervalDrag = createTimedIntervalDrag({
    trimRef: stickerTrim,
    bodyRef: stickerDragRef,
    readWindow: (item) => ({
      start: item?.start ?? stickerStyle?.startTime ?? 0.5,
      end: item?.end ?? stickerStyle?.endTime ?? (totalDuration || 15),
    }),
    onTrimUpdate: ({ id, edge, value }) => onUpdateSticker?.(
      edge === 'left'
        ? { id, start: value, startTime: value }
        : { id, end: value, endTime: value }
    ),
    onBodyUpdate: ({ id, start, end }) => onUpdateSticker?.({
      id, start, end, startTime: start, endTime: end,
    }),
  });

  // Sticker keeps its historical `(event, edge, item)` and
  // `(event, item, edge)` call forms for callers outside the current Timeline.
  const startStickerTrim = (e, edgeOrItem, maybeEdge) => {
    let edge = edgeOrItem;
    let item = null;
    if (typeof edgeOrItem === 'object' && edgeOrItem !== null) {
      item = edgeOrItem;
      edge = maybeEdge;
    } else if (typeof maybeEdge === 'object' && maybeEdge !== null) {
      item = maybeEdge;
    }
    stickerIntervalDrag.startTrim(e, edge, item);
  };
  const moveStickerTrim = stickerIntervalDrag.moveTrim;
  const endStickerTrim = stickerIntervalDrag.endTrim;
  const startStickerBodyDrag = stickerIntervalDrag.startBodyDrag;
  const moveStickerBodyDrag = stickerIntervalDrag.moveBodyDrag;
  const endStickerBodyDrag = stickerIntervalDrag.endBodyDrag;

  const effectIntervalDrag = createTimedIntervalDrag({
    trimRef: effectTrim,
    bodyRef: effectDragRef,
    readWindow: (item) => ({
      start: item?.start ?? 0.5,
      end: item?.end ?? (totalDuration || 15),
    }),
    onTrimUpdate: ({ id, edge, value }) => onUpdateEffect?.(
      edge === 'left' ? { id, start: value } : { id, end: value }
    ),
    onBodyUpdate: ({ id, start, end }) => onUpdateEffect?.({ id, start, end }),
  });

  const startEffectTrim = (e, edge, item) => effectIntervalDrag.startTrim(e, edge, item);
  const moveEffectTrim = effectIntervalDrag.moveTrim;
  const endEffectTrim = effectIntervalDrag.endTrim;
  const startEffectBodyDrag = effectIntervalDrag.startBodyDrag;
  const moveEffectBodyDrag = effectIntervalDrag.moveBodyDrag;
  const endEffectBodyDrag = effectIntervalDrag.endBodyDrag;

  return {
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
  };
}
