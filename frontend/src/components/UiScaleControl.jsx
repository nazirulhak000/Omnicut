import React from 'react';
import { ALargeSmall } from 'lucide-react';
import { UI_SCALES, applyUiScale, getUiScaleId } from '../lib/uiScale';

/**
 * Interface size switch. Lives in the topbar for most tabs and in the editor's
 * own header, because the editor hides the topbar -- and the editor is exactly
 * where someone stares at small text for an hour.
 */
export default function UiScaleControl({ value, onChange, className = '' }) {
  const current = value || getUiScaleId();
  const handle = (id) => {
    applyUiScale(id);
    onChange?.(id);
  };

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
