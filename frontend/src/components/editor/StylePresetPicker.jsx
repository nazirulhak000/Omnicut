import React from 'react';
import { Check, Sparkles } from 'lucide-react';

import { STYLE_PRESET_CATALOG, normalizeStylePreset } from '../../lib/stylePresetCatalog.js';

export default function StylePresetPicker({
  value,
  onChange,
  layout = 'stacked',
  helpText = 'เลือกจังหวะการตัด กล้องเคลื่อน Transition และสี Accent สำหรับทั้งโปรเจกต์',
}) {
  const activeId = normalizeStylePreset(value);
  const gridClass = layout === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 gap-2.5' : 'space-y-2';

  return (
    <div className="space-y-2.5">
      <div className="flex items-start gap-2">
        <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#25F4EE]" />
        <div className="min-w-0">
          <p className="text-xs font-bold text-slate-200">สไตล์การตัดต่อ</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{helpText}</p>
        </div>
      </div>

      <div className={gridClass} role="radiogroup" aria-label="สไตล์การตัดต่อของโปรเจกต์">
        {STYLE_PRESET_CATALOG.map((preset) => {
          const isActive = activeId === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              data-style-preset={preset.id}
              onClick={() => onChange?.(preset.id)}
              className={`min-w-0 rounded-xl border p-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-[#25F4EE]/60 cursor-pointer ${
                isActive
                  ? 'border-[#25F4EE]/70 bg-[#25F4EE]/[0.08]'
                  : 'border-white/[0.08] bg-black/30 hover:border-white/[0.22] hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex min-w-0 items-start justify-between gap-2">
                <div className="flex min-w-0 items-start gap-2">
                  <span
                    className="mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full ring-2 ring-black/30"
                    style={{ backgroundColor: preset.accent }}
                    aria-hidden="true"
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <p className="text-sm font-bold text-white">{preset.label}</p>
                      {preset.recommended && (
                        <span className="rounded-md bg-[#FE2C55]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#FF7895]">
                          แนะนำ One Click
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs font-medium text-[#25F4EE]">{preset.labelTh}</p>
                  </div>
                </div>
                {isActive && <Check className="h-4 w-4 flex-shrink-0 text-[#25F4EE]" aria-hidden="true" />}
              </div>

              <p className="mt-2 text-[11px] leading-relaxed text-slate-300">{preset.description}</p>
              <dl className="mt-2 space-y-1 text-[10px] leading-relaxed text-slate-400">
                <div className="flex gap-1.5"><dt className="w-12 flex-shrink-0 text-slate-500">Motion</dt><dd>{preset.motion}</dd></div>
                <div className="flex gap-1.5"><dt className="w-12 flex-shrink-0 text-slate-500">Cut</dt><dd>{preset.transitions}</dd></div>
                <div className="flex gap-1.5"><dt className="w-12 flex-shrink-0 text-slate-500">Sound</dt><dd>{preset.audio}</dd></div>
              </dl>
            </button>
          );
        })}
      </div>
    </div>
  );
}
