import React, { useRef, useState } from 'react';
import { FlipHorizontal2, Gauge, RotateCw, Volume2 } from 'lucide-react';
import { MIN_CLIP_DURATION, resolveSnapCandidateLabel, snapToFrame } from '../../lib/timelineMath';

const CLIP_RADIUS = 6;

/**
 * One video clip on the timeline: selection, drag-to-trim on either edge,
 * and drag-the-body to reorder. To shift/resize the trim window against the
 * raw source file (rather than just resizing on the timeline's own grid),
 * see TrimAdjustModal (opened via the clip's right-click context menu).
 */
export default function TimelineClip({
  seg,
  pxPerSec,
  isSelected,
  onSelect,
  onContextMenu,
  onAdjustTrim,       // double-click shortcut for the same modal the right-click menu opens
  onTrim,             // (clipId, patch) during drag -- no undo step
  onTrimBegin,
  onTrimEnd,
  onReorder,          // (clipId, direction) -- keyboard reorder ([ and ])
  onBodyDragStart,    // dragging the clip body reorders it
  onBodyDragMove,
  onBodyDragEnd,
  snapCandidates = [],
  snapFunction = (t) => t,
  playhead,
  segments = [],
  cues = [],
  audioDuration = 0,
  onSnapGuide,
}) {
  const dragRef = useRef(null);
  const bodyRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [dragDx, setDragDx] = useState(0);
  const [trimHud, setTrimHud] = useState(null);
  const { clip } = seg;
  const speed = clip.speed || 1;

  const width = Math.max(14, seg.dur * pxPerSec);
  const left = seg.segStart * pxPerSec;

  const startBodyDrag = (e) => {
    // the trim handles have their own drag; their event bubbles up here
    if (e.target.closest('[data-trim-handle]')) return;
    bodyRef.current = { startX: e.clientX, moved: false };
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
  };

  const moveBodyDrag = (e) => {
    const d = bodyRef.current;
    if (!d) return;
    if (!d.moved) {
      if (Math.abs(e.clientX - d.startX) < 6) return;
      d.moved = true;
      setDragging(true);
      onBodyDragStart?.(clip.id);
    }
    // A swap moves the clip's own `left`, so the ghost offset has to rebase
    // or the clip would jump by its neighbour's width twice.
    const swapped = onBodyDragMove?.(clip.id, e.clientX);
    if (swapped) {
      d.startX = e.clientX;
      setDragDx(0);
    } else {
      setDragDx(e.clientX - d.startX);
    }
  };

  const endBodyDrag = (e) => {
    const d = bodyRef.current;
    bodyRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
    if (!d?.moved) return;
    setDragging(false);
    setDragDx(0);
    onBodyDragEnd?.();
  };

  const startEdgeDrag = (edge) => (e) => {
    e.stopPropagation();
    e.preventDefault();
    // Capture keeps the drag alive if the cursor leaves the handle. It throws
    // for a pointer id the browser no longer tracks (cancelled pointer,
    // synthetic event) -- that must not abort the drag setup below.
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
    const startTrimEnd = clip.trim_end ?? seg.srcDur;
    const initialSpan = startTrimEnd - clip.trim_start;
    dragRef.current = {
      edge,
      startX: e.clientX,
      startTrimStart: clip.trim_start,
      startTrimEnd,
      initialDur: Math.max(MIN_CLIP_DURATION, initialSpan / speed),
    };
    setTrimHud({ edge, dur: seg.dur, delta: 0 });
    onTrimBegin?.();
  };

  // Trimming either edge changes this clip's duration, and because the
  // timeline packs clips with no gaps, that duration change always shows up
  // at the SAME on-screen edge -- this clip's own end (segStart + dur). The
  // start handle's own left position never moves (segStart comes only from
  // clips before it); only how far the box's right edge retreats does. So
  // snapping is applied to that shared edge for both handles, converted back
  // into the trim value that produces it.
  const snapToEdge = (rawNext, sourceOtherBound) => {
    if (!snapCandidates.length) return rawNext;
    // rawNext/sourceOtherBound are source-domain trim values; the edge that
    // actually moves on screen is measured in sequence seconds, `speed` times
    // slower, so convert to that domain to snap and back to trim to apply it.
    const dur = Math.abs(rawNext - sourceOtherBound) / speed;
    const virtualEnd = seg.segStart + dur;
    const snappedEnd = snapFunction(virtualEnd, snapCandidates);
    const snappedDur = snappedEnd - seg.segStart;
    if (snappedDur < MIN_CLIP_DURATION) return rawNext; // snap would collapse the clip -- ignore it
    if (Math.abs(snappedEnd - virtualEnd) > 0.001) {
      const label = resolveSnapCandidateLabel(snappedEnd, {
        playhead,
        segments,
        cues,
        audioDuration,
      });
      onSnapGuide?.({ time: snappedEnd, label });
    } else {
      onSnapGuide?.(null);
    }
    return sourceOtherBound + (rawNext > sourceOtherBound ? 1 : -1) * snappedDur * speed;
  };

  const moveEdgeDrag = (e) => {
    const d = dragRef.current;
    if (!d) return;
    // Timeline pixels are sequence seconds; source seconds move `speed` times faster.
    const deltaSource = ((e.clientX - d.startX) / pxPerSec) * speed;

    if (d.edge === 'start') {
      let next = Math.min(
        Math.max(0, d.startTrimStart + deltaSource),
        d.startTrimEnd - MIN_CLIP_DURATION * speed,
      );
      const snapped = snapToEdge(next, d.startTrimEnd);
      if (snapped >= 0 && snapped <= d.startTrimEnd - MIN_CLIP_DURATION * speed) next = snapped;
      // Whole 30 fps frame (still stored in seconds); clamped back inside the
      // same bounds so rounding can never shrink the clip under its minimum.
      const finalVal = Math.min(Math.max(snapToFrame(next), 0), d.startTrimEnd - MIN_CLIP_DURATION * speed);
      onTrim(clip.id, { trim_start: finalVal });
      const curDur = Math.max(MIN_CLIP_DURATION, (d.startTrimEnd - finalVal) / speed);
      setTrimHud({ edge: 'start', dur: curDur, delta: curDur - d.initialDur });
    } else {
      let next = Math.max(
        Math.min(seg.srcDur || d.startTrimEnd, d.startTrimEnd + deltaSource),
        d.startTrimStart + MIN_CLIP_DURATION * speed,
      );
      const maxNext = seg.srcDur || d.startTrimEnd;
      const snapped = snapToEdge(next, d.startTrimStart);
      if (snapped >= d.startTrimStart + MIN_CLIP_DURATION * speed && snapped <= maxNext) next = snapped;
      const atSourceEnd = seg.srcDur && next >= seg.srcDur - 0.05;
      const finalVal = atSourceEnd
        ? null
        : Math.max(Math.min(snapToFrame(next), maxNext), d.startTrimStart + MIN_CLIP_DURATION * speed);
      onTrim(clip.id, { trim_end: finalVal });
      const curDur = Math.max(MIN_CLIP_DURATION, ((atSourceEnd ? seg.srcDur : finalVal) - d.startTrimStart) / speed);
      setTrimHud({ edge: 'end', dur: curDur, delta: curDur - d.initialDur });
    }
  };

  const endEdgeDrag = (e) => {
    if (!dragRef.current) return;
    dragRef.current = null;
    setTrimHud(null);
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* already released */ }
    onTrimEnd?.();
  };

  const fileName = (clip.source_path || '').split(/[\\/]/).pop();

  return (
    <div
      data-timeline-item="clip"
      role="button"
      tabIndex={0}
      aria-label={`คลิป ${fileName}`}
      aria-pressed={isSelected}
      onClick={(e) => { e.stopPropagation(); if (!dragging) onSelect(clip.id); }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        onSelect(clip.id);
        onAdjustTrim?.(seg);
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onSelect(clip.id);
        onContextMenu?.(e, seg);
      }}
      onPointerDown={startBodyDrag}
      onPointerMove={moveBodyDrag}
      onPointerUp={endBodyDrag}
      onPointerCancel={endBodyDrag}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(clip.id); }
        if (e.key === '[' || e.key === 'ArrowUp') { e.preventDefault(); onReorder?.(clip.id, -1); }
        if (e.key === ']' || e.key === 'ArrowDown') { e.preventDefault(); onReorder?.(clip.id, 1); }
      }}
      title="ลากตัวคลิปเพื่อสลับลำดับ · ลากขอบเพื่อตัด · ดับเบิลคลิกเพื่อปรับช่วงตัด"
      className={`absolute top-0 h-full touch-none overflow-hidden transition-shadow duration-150
        focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
        dragging ? 'cursor-grabbing' : 'cursor-grab'
      } ${
        isSelected
          ? 'ring-2 ring-[#D97757] shadow-[0_0_0_1px_rgba(217,119,87,0.6)] z-10'
          : 'ring-1 ring-[#4A4742] hover:ring-[#6B6660]'
      }`}
      style={{
        left,
        width,
        borderRadius: CLIP_RADIUS,
        backgroundColor: '#282724',
        ...(dragging
          ? { transform: `translateX(${dragDx}px)`, opacity: 0.85, zIndex: 30 }
          : null),
      }}
    >
      <div className="absolute inset-x-0 top-0 flex items-center justify-between gap-1 px-1.5 py-0.5 pointer-events-none">
        <span className="text-xs font-medium text-[#EDE9E3] truncate drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]">
          {fileName}
        </span>
        {clip.background_isolation?.enabled && (
          <span
            className="flex-shrink-0 flex items-center gap-0.5 rounded bg-violet-600/90 border border-violet-400/40 px-1 py-0.5 text-[9px] font-bold text-violet-100 shadow-sm"
            title="แยกพื้นหลังสินค้า (Cutout Active)"
          >
            ✂️ Cutout
          </span>
        )}
        {(clip.bg_blur || clip.fit_mode === 'blur') && (
          <span
            className="flex-shrink-0 flex items-center gap-0.5 rounded bg-[#25F4EE]/20 border border-[#25F4EE]/40 px-1 py-0.5 text-[9px] font-bold text-[#25F4EE] shadow-sm"
            title="เปิดพื้นหลังเบลอ (ขัดแย้งกับ Cutout)"
          >
            Blur BG
          </span>
        )}
      </div>

      {(speed !== 1 || clip.mirror || clip.rotation || (clip.volume || 0) > 0) && (
        <div className="absolute bottom-0.5 left-1.5 flex items-center gap-1 pointer-events-none">
          {speed !== 1 && (
            <span className="flex items-center gap-0.5 rounded bg-[#181716]/80 px-1 text-xs font-semibold text-[#E89274]">
              <Gauge className="h-2.5 w-2.5" />{speed}x
            </span>
          )}
          {clip.mirror && (
            <span className="rounded bg-[#181716]/80 p-0.5 text-[#E89274]">
              <FlipHorizontal2 className="h-2.5 w-2.5" />
            </span>
          )}
          {!!clip.rotation && (
            <span className="flex items-center gap-0.5 rounded bg-[#181716]/80 px-1 text-xs font-semibold text-[#25F4EE]">
              <RotateCw className="h-2.5 w-2.5" />{clip.rotation}°
            </span>
          )}
          {(clip.volume || 0) > 0 && (
            <span className="flex items-center gap-0.5 rounded bg-[#181716]/80 px-1 text-xs font-semibold text-emerald-400">
              <Volume2 className="h-2.5 w-2.5" />{Math.round(clip.volume * 100)}%
            </span>
          )}
        </div>
      )}

      {/* Trim handles -- only interactive on the selected clip so a click on a
          neighbour selects it instead of accidentally trimming it. */}
      {isSelected && ['start', 'end'].map((edge) => (
        <div
          key={edge}
          data-trim-handle=""
          onPointerDown={startEdgeDrag(edge)}
          onPointerMove={moveEdgeDrag}
          onPointerUp={endEdgeDrag}
          onPointerCancel={endEdgeDrag}
          title={edge === 'start' ? 'ลากปรับจุดเริ่ม' : 'ลากปรับจุดจบ'}
          className={`absolute top-0 h-full w-2.5 cursor-ew-resize touch-none bg-[#D97757]
            flex items-center justify-center ${edge === 'start' ? 'left-0' : 'right-0'}`}
          style={{
            borderTopLeftRadius: edge === 'start' ? CLIP_RADIUS : 0,
            borderBottomLeftRadius: edge === 'start' ? CLIP_RADIUS : 0,
            borderTopRightRadius: edge === 'end' ? CLIP_RADIUS : 0,
            borderBottomRightRadius: edge === 'end' ? CLIP_RADIUS : 0,
          }}
        >
          <span className="h-3.5 w-0.5 rounded-full bg-[#181716]/70" />
        </div>
      ))}

      {/* Live Trim HUD Tooltip */}
      {trimHud && (
        <div
          className={`pointer-events-none absolute -top-8 z-50 flex items-center gap-1.5 rounded-lg border border-[#D97757]/80 bg-[#0F1420]/95 px-2 py-0.5 shadow-2xl backdrop-blur-md text-[11px] font-mono font-bold text-white whitespace-nowrap animate-in fade-in zoom-in-95 duration-100 ${
            trimHud.edge === 'start' ? 'left-0' : 'right-0'
          }`}
        >
          <span className="text-[#25F4EE]">{trimHud.dur.toFixed(2)}s</span>
          <span className={trimHud.delta > 0.001 ? 'text-emerald-400' : trimHud.delta < -0.001 ? 'text-rose-400' : 'text-slate-400'}>
            ({trimHud.delta >= 0 ? `+${trimHud.delta.toFixed(2)}s` : `${trimHud.delta.toFixed(2)}s`})
          </span>
        </div>
      )}
    </div>
  );
}
