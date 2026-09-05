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
      <div className="absolute bottom-0 left-0 top-0 w-0.5 -translate-x-1/2 bg-[#D97757]" />
      <div className="absolute top-0 h-2.5 w-2.5 -translate-x-1/2 rotate-45 bg-[#D97757]" />
    </div>
  );
}
