import React, { useRef } from 'react';
import { FlipHorizontal2, Gauge } from 'lucide-react';
import { MIN_CLIP_DURATION } from '../../lib/timelineMath';

const CLIP_RADIUS = 6;

/**
 * One video clip on the timeline: filmstrip texture, selection, drag-to-trim
 * on either edge, and drag-the-body to reorder. Trim edits trim_start /
 * trim_end on the source, so the visible filmstrip window shifts with it.
 */
export default function TimelineClip({
  seg,
  pxPerSec,
  isSelected,
  filmstrip,          // { url, frames } | null
  onSelect,
  onTrim,             // (clipId, patch) during drag -- no undo step
  onTrimBegin,
  onTrimEnd,
  onReorder,          // (clipId, direction) -- keyboard/click reorder fallback
}) {
  const dragRef = useRef(null);
  const { clip } = seg;
  const speed = clip.speed || 1;

  const width = Math.max(14, seg.dur * pxPerSec);
  const left = seg.segStart * pxPerSec;

  // Map the sprite (which spans the whole source file) onto just the trimmed
  // window, so the frames shown are the frames that will actually render.
  const filmstripStyle = (() => {
    if (!filmstrip?.url || !seg.srcDur) return {};
    const spanSource = Math.max(MIN_CLIP_DURATION, seg.dur * speed);
    const scaleFactor = seg.srcDur / spanSource;
    return {
      backgroundImage: `linear-gradient(rgba(24,23,22,0.55), rgba(24,23,22,0.55)), url("${filmstrip.url}")`,
      backgroundSize: `100% 100%, ${width * scaleFactor}px 100%`,
      backgroundPositionX: `0px, ${-(clip.trim_start / seg.srcDur) * width * scaleFactor}px`,
      backgroundRepeat: 'no-repeat, no-repeat',
    };
  })();

  const startEdgeDrag = (edge) => (e) => {
    e.stopPropagation();
    e.preventDefault();
    // Capture keeps the drag alive if the cursor leaves the handle. It throws
    // for a pointer id the browser no longer tracks (cancelled pointer,
    // synthetic event) -- that must not abort the drag setup below.
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
    dragRef.current = { edge, startX: e.clientX, startTrimStart: clip.trim_start, startTrimEnd: clip.trim_end ?? seg.srcDur };
    onTrimBegin?.();
  };

  const moveEdgeDrag = (e) => {
    const d = dragRef.current;
    if (!d) return;
    // Timeline pixels are sequence seconds; source seconds move `speed` times faster.
    const deltaSource = ((e.clientX - d.startX) / pxPerSec) * speed;

    if (d.edge === 'start') {
      const next = Math.min(
        Math.max(0, d.startTrimStart + deltaSource),
        d.startTrimEnd - MIN_CLIP_DURATION * speed,
      );
      onTrim(clip.id, { trim_start: Math.round(next * 100) / 100 });
    } else {
      const next = Math.max(
        Math.min(seg.srcDur || d.startTrimEnd, d.startTrimEnd + deltaSource),
        d.startTrimStart + MIN_CLIP_DURATION * speed,
      );
      const atSourceEnd = seg.srcDur && next >= seg.srcDur - 0.05;
      onTrim(clip.id, { trim_end: atSourceEnd ? null : Math.round(next * 100) / 100 });
    }
  };

  const endEdgeDrag = (e) => {
    if (!dragRef.current) return;
    dragRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* already released */ }
    onTrimEnd?.();
  };

  const fileName = (clip.source_path || '').split(/[\\/]/).pop();

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`คลิป ${fileName}`}
      aria-pressed={isSelected}
      onClick={() => onSelect(clip.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(clip.id); }
        if (e.key === '[') { e.preventDefault(); onReorder?.(clip.id, -1); }
        if (e.key === ']') { e.preventDefault(); onReorder?.(clip.id, 1); }
      }}
      className={`absolute top-0 h-full overflow-hidden cursor-pointer transition-shadow duration-150
        focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
        isSelected
          ? 'ring-2 ring-[#D97757] shadow-[0_0_0_1px_rgba(217,119,87,0.6)] z-10'
          : 'ring-1 ring-[#4A4742] hover:ring-[#6B6660]'
      }`}
      style={{ left, width, borderRadius: CLIP_RADIUS, backgroundColor: '#282724', ...filmstripStyle }}
    >
      <div className="absolute inset-x-0 top-0 flex items-center gap-1 px-1.5 py-0.5 pointer-events-none">
        <span className="text-[9px] font-medium text-[#EDE9E3] truncate drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]">
          {fileName}
        </span>
      </div>

      {(speed !== 1 || clip.mirror) && (
        <div className="absolute bottom-0.5 left-1.5 flex items-center gap-1 pointer-events-none">
          {speed !== 1 && (
            <span className="flex items-center gap-0.5 rounded bg-[#181716]/80 px-1 text-[8px] font-semibold text-[#E89274]">
              <Gauge className="h-2.5 w-2.5" />{speed}x
            </span>
          )}
          {clip.mirror && (
            <span className="rounded bg-[#181716]/80 p-0.5 text-[#E89274]">
              <FlipHorizontal2 className="h-2.5 w-2.5" />
            </span>
          )}
        </div>
      )}

      {/* Trim handles -- only interactive on the selected clip so a click on a
          neighbour selects it instead of accidentally trimming it. */}
      {isSelected && ['start', 'end'].map((edge) => (
        <div
          key={edge}
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
    </div>
  );
}
