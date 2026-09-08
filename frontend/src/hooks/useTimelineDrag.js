import { useRef } from 'react';
import { applyCaptionMagneticRipple } from '../lib/timelineTrackModel';
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
}) {
  const scrubbing = useRef(false);
  const captionDrag = useRef(null);
  const captionTrim = useRef(null);
  const textDrag = useRef(null);
  const textTrim = useRef(null);
  const hookTrim = useRef(null);
  const stickerTrim = useRef(null);
  const stickerDrag = useRef(null);
  const bodyDrag = useRef(null);

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

  const moveScrub = (e) => {
    if (scrubbing.current) onSeek?.(timeFromEvent(e));
  };

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

    deselectAll?.();
    scrubbing.current = true;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* scrub still works */ }
    onSeek?.(timeFromEvent(e));
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
    if (!d.moved) { d.moved = true; dragBegin?.(); }

    if (d.edge === 'left') {
      const targetIdx = (d.initialCues || []).findIndex((c) => c._uid === d.uid || c.id === d.uid);
      const minStart = (snapEnabled && targetIdx > 0) ? d.initialCues[targetIdx - 1].end : 0;
      const rawStart = Math.max(minStart, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      const finalStart = Math.max(minStart, Math.round(snapped * 100) / 100);
      shiftCaption?.(d.uid, { start: finalStart });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      const newEnd = Math.round(Math.max(d.start + 0.2, snapped) * 100) / 100;

      if (snapEnabled && (onCuesChange || onCaptionRippleShift)) {
        const nextCues = applyCaptionMagneticRipple(d.initialCues, d.uid, d.start, newEnd);
        (onCuesChange || onCaptionRippleShift)(nextCues, true);
      } else {
        shiftCaption?.(d.uid, { end: newEnd });
      }
    }
  };

  const endTrim = (e) => {
    const d = captionTrim.current;
    captionTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Caption body drag
  const startCaptionBodyDrag = (e, cue) => {
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
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
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin?.(); }

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
      shiftCaption?.(cue._uid, {
        start: finalStart,
        end: finalEnd,
      });
    }
  };

  const endCaptionBodyDrag = (e) => {
    const d = captionDrag.current;
    captionDrag.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Text overlay trim
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
    if (!d.moved) { d.moved = true; dragBegin?.(); }

    if (d.edge === 'left') {
      const rawStart = Math.max(0, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      shiftTextOverlay?.(d.id, { start: Math.round(snapped * 100) / 100 });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      shiftTextOverlay?.(d.id, { end: Math.round(snapped * 100) / 100 });
    }
  };

  const endTextTrim = (e) => {
    const d = textTrim.current;
    textTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Text overlay body drag
  const startTextBodyDrag = (e, item) => {
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
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
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin?.(); }
    const shift = Math.max(-d.start, delta);
    const rawStart = d.start + shift;
    const snappedStart = snapFunction(rawStart, snapPoints);
    const correction = snappedStart - rawStart;
    shiftTextOverlay?.(item.id, {
      start: Math.round((d.start + shift + correction) * 100) / 100,
      end: Math.round((d.end + shift + correction) * 100) / 100,
    });
  };

  const endTextBodyDrag = (e) => {
    const d = textDrag.current;
    textDrag.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Hook duration trim
  const startHookTrim = (e) => {
    e.stopPropagation();
    if (!hookOverlay) return;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
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
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin?.(); }
    const rawEnd = d.startEnd + delta;
    const snapped = snapFunction(rawEnd, snapPoints);
    const minEnd = d.start + HOOK_MIN_DURATION;
    const maxEnd = d.start + HOOK_MAX_DURATION;
    const clamped = Math.max(minEnd, Math.min(maxEnd, Math.round(snapped * 10) / 10));
    onUpdateOverlay?.(hookOverlay.id, { end: clamped }, true);
  };

  const endHookTrim = (e) => {
    const d = hookTrim.current;
    hookTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Sticker duration trim
  const startStickerTrim = (e, edgeOrItem, maybeEdge) => {
    let edge = edgeOrItem;
    let item = null;
    if (typeof edgeOrItem === 'object' && edgeOrItem !== null) {
      item = edgeOrItem;
      edge = maybeEdge;
    } else if (typeof maybeEdge === 'object' && maybeEdge !== null) {
      item = maybeEdge;
    }
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    const start = item?.start ?? stickerStyle?.startTime ?? 0.5;
    const end = item?.end ?? stickerStyle?.endTime ?? (totalDuration || 15);
    stickerTrim.current = {
      edge,
      startX: e.clientX,
      start,
      end,
      id: item?.id,
      moved: false,
    };
  };

  const moveStickerTrim = (e) => {
    const d = stickerTrim.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin?.(); }

    if (d.edge === 'left') {
      const rawStart = Math.max(0, Math.min(d.end - 0.3, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      const rounded = Math.round(snapped * 10) / 10;
      onUpdateSticker?.({ id: d.id, start: rounded, startTime: rounded });
    } else {
      const maxEnd = Math.max(totalDuration, audioDuration || 0) || 999;
      const rawEnd = Math.max(d.start + 0.3, Math.min(maxEnd, d.end + delta));
      const snapped = snapFunction(rawEnd, snapPoints);
      const rounded = Math.round(snapped * 10) / 10;
      onUpdateSticker?.({ id: d.id, end: rounded, endTime: rounded });
    }
  };

  const endStickerTrim = (e) => {
    const d = stickerTrim.current;
    stickerTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

  // Sticker time window body drag
  const startStickerBodyDrag = (e, item) => {
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    const start = item?.start ?? stickerStyle?.startTime ?? 0.5;
    const end = item?.end ?? stickerStyle?.endTime ?? (totalDuration || 15);
    stickerDrag.current = {
      startX: e.clientX,
      start,
      end,
      id: item?.id,
      duration: Math.max(0.3, end - start),
      moved: false,
    };
  };

  const moveStickerBodyDrag = (e) => {
    const d = stickerDrag.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin?.(); }
    const maxT = Math.max(totalDuration, audioDuration || 0) || 999;
    const minStart = 0;
    const maxStart = Math.max(0, maxT - d.duration);
    const rawStart = Math.max(minStart, Math.min(maxStart, d.start + delta));
    const snappedStart = snapFunction(rawStart, snapPoints);
    const finalStart = Math.round(snappedStart * 10) / 10;
    const finalEnd = Math.round((finalStart + d.duration) * 10) / 10;
    onUpdateSticker?.({
      id: d.id,
      start: finalStart,
      end: finalEnd,
      startTime: finalStart,
      endTime: finalEnd,
    });
  };

  const endStickerBodyDrag = (e) => {
    const d = stickerDrag.current;
    stickerDrag.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd?.();
  };

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
  };
}
