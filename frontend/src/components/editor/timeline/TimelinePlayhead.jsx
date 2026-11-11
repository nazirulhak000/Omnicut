import React, { memo } from 'react';
import { useLivePlayhead } from '../../../hooks/usePlayhead';

function TimelinePlayhead({
  playhead = 0,
  pxPerSec = 50,
  topOffset = -28,
}) {
  // Subscribes to the live playhead so only this needle re-renders while a
  // clip plays; the `playhead` prop is the fallback outside the editor.
  const livePlayhead = useLivePlayhead(playhead);
  const x = Math.round(livePlayhead * pxPerSec);
  return (
    <div
      className="pointer-events-none absolute left-0 z-30"
      style={{
        transform: `translate3d(${x}px, 0, 0)`,
        willChange: 'transform',
        top: topOffset,
        bottom: 0,
      }}
    >
      <div className="absolute bottom-0 left-0 top-0 w-[3.5px] -translate-x-1/2 bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)]" />
      <div className="absolute top-0 h-4 w-4 sm:h-3 sm:w-3 -translate-x-1/2 rotate-45 bg-white border border-[#D97757] shadow-[0_0_10px_rgba(255,255,255,0.9)]" />
    </div>
  );
}

export default memo(TimelinePlayhead);
