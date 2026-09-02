import React from 'react';
import { ALargeSmall } from 'lucide-react';
import { UI_SCALES, applyUiScale, getUiScaleId } from '../lib/uiScale';

/**
 * Interface size switch. Lives in the topbar for most tabs and in the editor's
 * own header, because the editor hides the topbar -- and the editor is exactly
 * where someone stares at small text for an hour.
 */
export default function UiScaleControl({ value, onChange, className = '', variant = 'bar' }) {
  const current = value || getUiScaleId();
  const handle = (id) => {
    applyUiScale(id);
    onChange?.(id);
  };

  // Inside the overflow menu it is one row among others, so it drops the
  // pill chrome and spans the width instead.
  if (variant === 'menu') {
    return (
      <div className={`flex gap-1 ${className}`}>
        {UI_SCALES.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => handle(s.id)}
            className={`h-9 flex-1 cursor-pointer rounded-lg border text-xs font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
              current === s.id
                ? 'border-[#D97757] bg-[#D97757]/20 text-[#E89274]'
                : 'border-white/[0.08] bg-black/40 text-slate-300 hover:text-white'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`flex min-w-0 items-center gap-1.5 rounded-xl border border-white/[0.08] bg-black/40 px-2 ${className}`}>
      <ALargeSmall className="h-4 w-4 flex-shrink-0 text-[#D97757]" />
      <select
        value={current}
        onChange={(e) => handle(e.target.value)}
        title="ขนาดตัวอักษรและหน้าจอทั้งระบบ"
        aria-label="ขนาดตัวอักษรทั้งระบบ"
        className="h-9 cursor-pointer bg-transparent text-sm font-medium text-slate-200 focus:outline-none"
      >
        {UI_SCALES.map((s) => (
          <option key={s.id} value={s.id} className="bg-[#080B11] text-white">{s.label}</option>
        ))}
      </select>
    </div>
  );
}
