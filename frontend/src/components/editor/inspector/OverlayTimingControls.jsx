import React from 'react';
import { Clock } from 'lucide-react';

export default function OverlayTimingControls({
  start,
  end,
  onStartChange,
  onEndChange,
  accentClass = 'text-[#25F4EE]',
  inputFocusClass = 'focus:border-[#25F4EE]',
  endMax,
}) {
  return (
    <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
        <Clock className={`w-3.5 h-3.5 ${accentClass}`} />
        <span>ช่วงเวลาแสดงผล</span>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <label className="block">
          <span className="text-[11px] text-slate-400">เริ่มที่ (วินาที)</span>
          <input
            type="number"
            step="0.1"
            min="0"
            max={Math.max(0, end - 0.1)}
            value={start}
            onChange={(e) => {
              const value = parseFloat(e.target.value) || 0;
              onStartChange?.(Math.max(0, value));
            }}
            className={`mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white ${inputFocusClass} focus:outline-none`}
          />
        </label>
        <label className="block">
          <span className="text-[11px] text-slate-400">จบที่ (วินาที)</span>
          <input
            type="number"
            step="0.1"
            min={start + 0.1}
            max={endMax}
            value={end}
            onChange={(e) => {
              const value = parseFloat(e.target.value) || (start + 0.1);
              onEndChange?.(Math.max(start + 0.1, value));
            }}
            className={`mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white ${inputFocusClass} focus:outline-none`}
          />
        </label>
      </div>
    </div>
  );
}
