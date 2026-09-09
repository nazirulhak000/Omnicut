import React from 'react';
import { Sparkles } from 'lucide-react';

/**
 * Video overlay effects (checkmark/warning/arrow/etc, see 02_Assets/Effects)
 * track for the Timeline. Split out from Timeline.jsx because the label
 * gutter and the content lane are two separate render sites sharing the same
 * row geometry (`rowStyle('effect')`) -- mirroring how TrackLabel/TrackHeader
 * are their own files rather than adding more inline JSX to an already very
 * large component.
 *
 * Drag-to-move and drag-to-trim mirror the sticker track's markup exactly
 * (see the sticker block in Timeline.jsx) -- same left/middle/right handle
 * layout, same pointer-capture pattern -- via the matching
 * startEffectTrim/startEffectBodyDrag handlers added to useTimelineDrag.js.
 */

function labelFor(item, effectAssets) {
  const asset = (effectAssets || []).find((a) => a.id === item.effectId);
  return asset?.label_th || asset?.label || item.effectId || 'เอฟเฟกต์';
}

export function EffectTrackLabel({ width, slotWidth, rowStyleProp, TrackLabel }) {
  return (
    <div style={rowStyleProp} className="flex items-center transition-all duration-150">
      <TrackLabel width={width} slotWidth={slotWidth} icon={Sparkles}>
        เอฟเฟกต์
      </TrackLabel>
    </div>
  );
}

export function EffectTrackLane({
  rowStyleProp,
  packedEffects,
  effectAssets,
  selection,
  playhead,
  totalDuration,
  pxPerSec,
  timeFromEvent,
  onSelectEffect,
  onSeek,
  startEffectTrim,
  moveEffectTrim,
  endEffectTrim,
  startEffectBodyDrag,
  moveEffectBodyDrag,
  endEffectBodyDrag,
}) {
  return (
    <div className="relative rounded bg-[#181716] transition-all duration-150" style={rowStyleProp}>
      {packedEffects.map((item) => {
        const start = item.start ?? 0.5;
        const end = item.end ?? (totalDuration || 15);
        const dur = Math.max(0.2, end - start);
        const isSelected = selection?.type === 'effect' && selection.id === item.id;
        const w = Math.max(24, dur * pxPerSec);
        const label = labelFor(item, effectAssets);
        const topPx = (item.lane || 0) * 26 + 2;

        return (
          <div
            key={item.id}
            data-timeline-item="effect"
            onClick={(e) => {
              e.stopPropagation();
              const t = timeFromEvent(e);
              onSelectEffect?.(item.id);
              if (typeof t === 'number' && t >= start && t <= end) {
                onSeek?.(t);
              } else if (playhead < start || playhead > end + 0.05) {
                onSeek?.(start);
              }
            }}
            title={`${label} (${start.toFixed(1)}s - ${end.toFixed(1)}s)`}
            className={`group absolute touch-none select-none rounded text-left text-xs transition-colors duration-150 flex items-center ${
              item.hidden
                ? 'opacity-40 bg-[#282724] text-[#9C968F] ring-1 ring-white/10'
                : isSelected
                  ? 'bg-[#3A1E3B] text-[#E879F9] ring-2 ring-[#E879F9] shadow-[0_0_12px_rgba(232,121,249,0.3)] z-10'
                  : 'bg-[#2A1730] text-[#C983D6] ring-1 ring-[#4D2E54] hover:ring-[#7A4A84]'
            }`}
            style={{
              left: start * pxPerSec,
              width: w,
              top: topPx,
              height: 22,
            }}
          >
            {/* Left Trim Handle */}
            <div
              onPointerDown={(e) => startEffectTrim?.(e, 'left', item)}
              onPointerMove={moveEffectTrim}
              onPointerUp={endEffectTrim}
              onPointerCancel={endEffectTrim}
              title="ลากเพื่อยืด/หดเวลาเริ่มต้นของเอฟเฟกต์"
              className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-l hover:bg-[#E879F9] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
            >
              <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
            </div>

            {/* Middle Body */}
            <div
              onPointerDown={(e) => startEffectBodyDrag?.(e, item)}
              onPointerMove={moveEffectBodyDrag}
              onPointerUp={endEffectBodyDrag}
              onPointerCancel={endEffectBodyDrag}
              className="flex-1 min-w-0 h-full flex items-center px-2 gap-1.5 overflow-hidden cursor-move"
            >
              <Sparkles className="h-3 w-3 flex-shrink-0" />
              <span className="truncate font-semibold text-[11px] tracking-wide">{label}</span>
              <span className="font-mono text-[10px] text-[#E879F9]/70 flex-shrink-0 ml-auto">
                {dur.toFixed(1)}s
              </span>
            </div>

            {/* Right Trim Handle */}
            <div
              onPointerDown={(e) => startEffectTrim?.(e, 'right', item)}
              onPointerMove={moveEffectTrim}
              onPointerUp={endEffectTrim}
              onPointerCancel={endEffectTrim}
              title="ลากเพื่อยืด/หดเวลาสิ้นสุดของเอฟเฟกต์"
              className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r hover:bg-[#E879F9] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
            >
              <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
