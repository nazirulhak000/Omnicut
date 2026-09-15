import React from 'react';
import { Check, Sparkles, AlertCircle } from 'lucide-react';

import { STYLE_PRESET_CATALOG, normalizeStylePreset } from '../../lib/stylePresetCatalog.js';

export default function StylePresetPicker({
  value,
  onChange,
  layout = 'stacked',
  helpText = 'เลือกจังหวะการตัด กล้องเคลื่อน Transition และสี Accent สำหรับทั้งโปรเจกต์',
  usedStyleIds = [],
  usedStyleInfo = {},
}) {
  const activeId = normalizeStylePreset(value);
  const activePreset = STYLE_PRESET_CATALOG.find((p) => p.id === activeId) || STYLE_PRESET_CATALOG[0];
  const isCurrentUsed = usedStyleIds.includes(activePreset?.id);

  return (
    <div className="space-y-2.5">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#25F4EE]" />
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-200">สไตล์การตัดต่อ</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{helpText}</p>
          </div>
        </div>
      </div>

      {/* 1. Compact Style Selector Tabs (Horizontal Segmented Grid) */}
      <div
        className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 p-1 rounded-xl bg-black/40 border border-white/[0.08]"
        role="radiogroup"
        aria-label="สไตล์การตัดต่อของโปรเจกต์"
      >
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
              className={`relative flex items-center gap-2 px-2.5 py-2 rounded-lg text-left transition-all duration-200 cursor-pointer select-none ${
                isActive
                  ? 'bg-white/[0.1] border border-white/[0.18] shadow-sm'
                  : 'hover:bg-white/[0.04] border border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {/* Accent dot indicator */}
              <span
                className="h-2.5 w-2.5 flex-shrink-0 rounded-full transition-transform duration-200"
                style={{
                  backgroundColor: preset.accent,
                  boxShadow: isActive ? `0 0 10px ${preset.accent}80` : 'none',
                  transform: isActive ? 'scale(1.15)' : 'scale(1)',
                }}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 min-w-0">
                  <p className={`text-xs font-bold truncate leading-tight ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {preset.label}
                  </p>
                  {usedStyleIds.includes(preset.id) && (
                    <span
                      title="สไตล์นี้ถูกใช้ในสินค้านี้แล้ว"
                      className="shrink-0 rounded bg-amber-500/20 text-amber-300 text-[8px] font-semibold px-1 py-0.5 border border-amber-500/30 leading-none"
                    >
                      ใช้แล้ว
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 truncate leading-tight mt-0.5">
                  {preset.labelTh}
                </p>
              </div>
              {isActive && (
                <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>

      {/* 2. Active Style Showcase & Mini Hook Preview (Single Compact 2-Col Card) */}
      {activePreset && (
        <div
          className="rounded-xl border p-3 sm:p-3.5 bg-gradient-to-r from-black/60 via-black/40 to-black/60 transition-all duration-300 relative overflow-hidden"
          style={{
            borderColor: `${activePreset.accent}40`,
            boxShadow: `0 0 20px ${activePreset.accent}10`,
          }}
        >
          {/* Subtle Accent Glow on background corner */}
          <div
            className="absolute -right-8 -bottom-8 w-28 h-28 rounded-full blur-3xl pointer-events-none opacity-25"
            style={{ backgroundColor: activePreset.accent }}
          />

          {isCurrentUsed && (
            <div className="mb-2.5 flex items-center gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 px-2.5 py-1.5 text-[11px] text-amber-200/90 relative z-10">
              <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
              <p className="leading-snug">
                สไตล์ <strong className="text-amber-100 font-semibold">{activePreset.label}</strong> {usedStyleInfo[activePreset.id] ? `(${usedStyleInfo[activePreset.id]})` : ''} ถูกใช้สร้างคลิปในสินค้านี้ไปแล้ว — สามารถสร้างซ้ำได้ตามต้องการ
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-4 items-center relative z-10">
            {/* Left Col: Specs & Info (7 cols) */}
            <div className="md:col-span-7 space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-white flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: activePreset.accent }}
                  />
                  {activePreset.label}
                </span>
                <span className="text-xs font-medium text-[#25F4EE]">({activePreset.labelTh})</span>
                {activePreset.recommended && (
                  <span className="rounded-md bg-[#FE2C55]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#FF7895] border border-[#FE2C55]/30">
                    แนะนำ One Click
                  </span>
                )}
              </div>

              <p className="text-[11px] leading-relaxed text-slate-300 line-clamp-2">
                {activePreset.description}
              </p>

              <dl className="grid grid-cols-3 gap-2 pt-1 text-[10px] text-slate-400 border-t border-white/[0.06]">
                <div className="min-w-0">
                  <dt className="text-slate-500 font-semibold mb-0.5">Motion</dt>
                  <dd className="text-slate-300 truncate" title={activePreset.motion}>{activePreset.motion}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-slate-500 font-semibold mb-0.5">Cut</dt>
                  <dd className="text-slate-300 truncate" title={activePreset.transitions}>{activePreset.transitions}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-slate-500 font-semibold mb-0.5">Sound</dt>
                  <dd className="text-slate-300 truncate" title={activePreset.audio}>{activePreset.audio}</dd>
                </div>
              </dl>
            </div>

            {/* Right Col: Mini Hook Preview Box (5 cols) */}
            {activePreset.hookBadge && (
              <div className="md:col-span-5 flex flex-col justify-center">
                <div className="rounded-xl bg-black/75 border border-white/[0.08] p-2.5 shadow-inner relative group">
                  <div className="flex items-center justify-between gap-1 mb-1.5 pb-1 border-b border-white/[0.06]">
                    <span className="text-[10px] font-semibold text-slate-400">ป้ายฮุกคู่ใจ:</span>
                    <span
                      className="px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold border"
                      style={{
                        color: activePreset.hookColor || activePreset.accent,
                        borderColor: `${activePreset.hookColor || activePreset.accent}40`,
                        backgroundColor: `${activePreset.hookColor || activePreset.accent}15`,
                      }}
                    >
                      {activePreset.hookBadge}
                    </span>
                  </div>

                  <div className="flex flex-col items-center justify-center text-center py-1">
                    <span
                      className="font-bold tracking-wider leading-none text-xs"
                      style={{
                        color: activePreset.hookColor || activePreset.accent,
                        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                        fontFamily: 'Kanit, sans-serif',
                      }}
                    >
                      BRAND
                    </span>
                    <span
                      className="font-bold text-white text-[10px] leading-tight mt-0.5"
                      style={{
                        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                        fontFamily: 'Kanit, sans-serif',
                      }}
                    >
                      รุ่นเด่น
                    </span>
                    <span
                      className="text-[#D0D0D0] text-[8.5px] leading-tight"
                      style={{ fontFamily: 'Kanit, sans-serif' }}
                    >
                      คำโปรย
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
