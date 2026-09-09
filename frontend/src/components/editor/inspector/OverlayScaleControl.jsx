import React from 'react';
import { Maximize2 } from 'lucide-react';

export default function OverlayScaleControl({
  scalePct,
  onChange,
  onReset,
  accentClass = 'text-[#25F4EE]',
  rangeClass = 'accent-[#25F4EE]',
  resetHoverClass = 'hover:text-[#25F4EE]',
}) {
  return (
    <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
        <div className="flex items-center gap-2">
          <Maximize2 className={`w-3.5 h-3.5 ${accentClass}`} />
          <span>ขนาด (Scale)</span>
        </div>
        <span className={`text-xs font-mono font-bold ${accentClass}`}>{scalePct}%</span>
      </div>
      <input
        type="range"
        min="30"
        max="300"
        step="5"
        value={scalePct}
        onChange={(e) => {
          const pct = parseInt(e.target.value, 10) || 100;
          onChange?.(Math.round((pct / 100) * 100) / 100);
        }}
        className={`w-full ${rangeClass} cursor-pointer`}
      />
      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <span>30%</span>
        <button
          type="button"
          onClick={onReset}
          className={`text-[11px] text-slate-400 ${resetHoverClass} underline cursor-pointer`}
        >
          คืนค่า 100%
        </button>
        <span>300%</span>
      </div>
    </div>
  );
}
