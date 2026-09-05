import React from 'react';
import { RotateCcw } from 'lucide-react';

export default function SliderControl({
  label,
  value,
  min = 0,
  max = 100,
  step = 1,
  displayValue,
  onChange,
  onReset,
  unit = '',
  disabled = false,
}) {
  const formatted = displayValue !== undefined ? displayValue : `${value}${unit}`;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400 font-medium">{label}</span>
        <div className="flex items-center gap-1.5 font-mono text-slate-200">
          <span>{formatted}</span>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              disabled={disabled}
              title="รีเซ็ตเป็นค่าเริ่มต้น"
              className="p-0.5 text-slate-500 hover:text-white rounded transition-colors disabled:opacity-30"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange?.(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-[#2C2B27] rounded-lg appearance-none cursor-pointer accent-[#25F4EE] disabled:opacity-40"
      />
    </div>
  );
}
