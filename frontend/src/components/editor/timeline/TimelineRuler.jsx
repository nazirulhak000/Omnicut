import React from 'react';
import { formatTimecode } from '../../../lib/timelineMath';

export default function TimelineRuler({
  gutterW,
  rulerHeight = 22,
  ticks = [],
  pxPerSec,
  onStartScrub,
  onMoveScrub,
  onEndScrub,
}) {
  return (
    <div className="sticky top-0 z-20 flex bg-[#1C1B19]">
      <div style={{ width: gutterW }} className="flex-shrink-0" />
      <div
        onPointerDown={onStartScrub}
        onPointerMove={onMoveScrub}
        onPointerUp={onEndScrub}
        onPointerCancel={onEndScrub}
        className="relative flex-1 cursor-text touch-none border-b border-[#363430]"
        style={{ height: rulerHeight }}
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
  );
}
