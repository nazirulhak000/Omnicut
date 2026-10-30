import React from 'react';

export default function TimelinePlayhead({
  playhead = 0,
  pxPerSec = 50,
  topOffset = -28,
}) {
  return (
    <div
      className="pointer-events-none absolute z-30"
      style={{ left: playhead * pxPerSec, top: topOffset, bottom: 0 }}
    >
      <div className="absolute bottom-0 left-0 top-0 w-[3.5px] -translate-x-1/2 bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)]" />
      <div className="absolute top-0 h-4 w-4 sm:h-3 sm:w-3 -translate-x-1/2 rotate-45 bg-white border border-[#D97757] shadow-[0_0_10px_rgba(255,255,255,0.9)]" />
    </div>
  );
}
