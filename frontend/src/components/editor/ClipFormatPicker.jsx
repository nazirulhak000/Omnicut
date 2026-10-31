import React from 'react';
import { Check, Timer } from 'lucide-react';
import {
  STORY_FORMAT_OPTIONS,
  TARGET_DURATION_OPTIONS,
  normalizeStoryFormat,
  normalizeTargetDuration,
} from '../../lib/clipFormatOptions.js';

const optionClass = (active) => `relative flex min-w-0 flex-col items-start gap-0.5 rounded-lg border px-2.5 py-2 text-left transition-colors duration-150 cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 ${
  active
    ? 'bg-white/[0.1] border-white/[0.18] text-white shadow-sm'
    : 'border-transparent text-slate-300 hover:bg-white/[0.04] hover:text-white'
}`;

/**
 * Target length + story format for a new clip. Both are plain radio groups:
 * one value each, always visible, so the choice is never hidden behind a menu.
 * `scriptSeconds` is the panel's estimate for an existing script, shown so a
 * target that the script cannot meet is visible before rendering.
 */
export default function ClipFormatPicker({ targetDuration, storyFormat, onChange, scriptSeconds = null }) {
  const activeDuration = normalizeTargetDuration(targetDuration);
  const activeFormat = normalizeStoryFormat(storyFormat);
  const activeFormatOption = STORY_FORMAT_OPTIONS.find((o) => o.id === activeFormat);
  const scriptGap = activeDuration != null && scriptSeconds != null ? scriptSeconds - activeDuration : null;
  const scriptOff = scriptGap != null && Math.abs(scriptGap) > Math.max(5, activeDuration * 0.25);

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2">
        <Timer className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#25F4EE]" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-xs font-bold text-slate-200">ความยาวและรูปแบบการเล่า</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-slate-400">
            ใช้กำกับตอน AI เขียนบท และบันทึกไว้กับคลิปเพื่อเทียบผลในแท็บผลงาน
          </p>
        </div>
      </div>

      <div className="space-y-1.5">
        <span id="clip-format-duration-label" className="block text-[11px] font-semibold text-slate-400">ความยาวเป้าหมาย</span>
        <div
          role="radiogroup"
          aria-labelledby="clip-format-duration-label"
          className="grid grid-cols-3 sm:grid-cols-5 gap-1.5 p-1 rounded-xl bg-black/40 border border-white/[0.08]"
        >
          {TARGET_DURATION_OPTIONS.map((option) => {
            const active = option.value === activeDuration;
            return (
              <button
                key={option.label}
                type="button"
                role="radio"
                aria-checked={active}
                data-target-duration={option.value ?? 'auto'}
                onClick={() => onChange?.({ targetDuration: option.value })}
                className={optionClass(active)}
              >
                <span className="flex w-full items-center justify-between gap-1">
                  <span className="text-xs font-bold tabular-nums">{option.label}</span>
                  {active && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" aria-hidden="true" />}
                </span>
                <span className="text-[10px] leading-tight text-slate-400">{option.hint}</span>
              </button>
            );
          })}
        </div>
        {scriptSeconds != null && (
          <p className={`text-[11px] leading-relaxed ${scriptOff ? 'text-amber-300' : 'text-slate-400'}`}>
            {activeDuration == null
              ? `บทพูดตอนนี้ยาวประมาณ ${scriptSeconds} วินาที คลิปจะยาวตามบท`
              : scriptOff
                ? `บทพูดตอนนี้ยาวประมาณ ${scriptSeconds} วินาที ${scriptGap > 0 ? 'ยาวกว่า' : 'สั้นกว่า'}เป้า ${activeDuration} วินาที บทที่มีอยู่จะถูกใช้ตามที่เขียน`
                : `บทพูดตอนนี้ยาวประมาณ ${scriptSeconds} วินาที ใกล้เคียงเป้า ${activeDuration} วินาที`}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <span id="clip-format-story-label" className="block text-[11px] font-semibold text-slate-400">รูปแบบการเล่า</span>
        <div
          role="radiogroup"
          aria-labelledby="clip-format-story-label"
          className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-1.5 p-1 rounded-xl bg-black/40 border border-white/[0.08]"
        >
          {STORY_FORMAT_OPTIONS.map((option) => {
            const active = option.id === activeFormat;
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={active}
                data-story-format={option.id}
                title={option.hint}
                onClick={() => onChange?.({ storyFormat: option.id })}
                className={optionClass(active)}
              >
                <span className="flex w-full items-center justify-between gap-1">
                  <span className="text-xs font-bold leading-tight">{option.label}</span>
                  {active && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" aria-hidden="true" />}
                </span>
                <span className="text-[10px] leading-tight text-slate-400 xl:hidden">{option.hint}</span>
              </button>
            );
          })}
        </div>
        {activeFormatOption && (
          <p className="hidden xl:block text-[11px] leading-relaxed text-slate-400">{activeFormatOption.hint}</p>
        )}
      </div>
    </div>
  );
}
