import React, { useEffect, useState } from 'react';
import { MAX_TRANSITION_DURATION } from '../../../lib/timelineMath';
import {
  MIN_TRANSITION_DURATION,
  TRANSITION_DURATION_STEP,
  TRANSITION_DURATION_PRESETS,
  boundTransitionDuration,
  clampTransitionDuration,
  formatTransitionDuration,
} from '../../../lib/transitionControls';

/**
 * Transition length for one boundary: quick presets plus a slider over the
 * full range the renderer accepts (0.1-2.0 s). The slider keeps a local draft
 * while dragging and commits once on release, so one drag is one undo step.
 */
export default function TransitionDurationControl({ value, onCommit }) {
  const current = boundTransitionDuration(value);
  const [draft, setDraft] = useState(null);

  useEffect(() => { setDraft(null); }, [current]);

  const shown = draft ?? current;
  const commit = (next, force = false) => {
    const clamped = clampTransitionDuration(next);
    setDraft(null);
    if (force || Math.abs(clamped - current) > 1e-6) onCommit?.(clamped);
  };

  return (
    <div className="pt-2 border-t border-[#363430]">
      <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1.5">
        <span>ความยาวรอยต่อ</span>
        <span className="font-mono font-bold text-[#25F4EE]">{formatTransitionDuration(shown)}</span>
      </div>
      <input
        type="range"
        aria-label="ความยาวรอยต่อ (วินาที)"
        min={MIN_TRANSITION_DURATION}
        max={MAX_TRANSITION_DURATION}
        step={TRANSITION_DURATION_STEP}
        value={shown}
        onChange={(e) => setDraft(Number(e.target.value))}
        onPointerUp={(e) => commit(e.currentTarget.value)}
        onKeyUp={(e) => commit(e.currentTarget.value)}
        onBlur={(e) => { if (draft != null) commit(e.currentTarget.value); }}
        className="w-full accent-[#25F4EE] mb-1.5"
      />
      <div className="grid grid-cols-4 gap-1">
        {TRANSITION_DURATION_PRESETS.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => commit(d, true)}
            className={`py-0.5 rounded text-center font-mono text-xs transition-colors ${
              Math.abs(current - d) < 0.025
                ? 'bg-[#25F4EE]/20 border border-[#25F4EE] text-[#25F4EE] font-bold'
                : 'bg-[#282724] hover:bg-[#363430] text-slate-400'
            }`}
          >
            {d}s
          </button>
        ))}
      </div>
    </div>
  );
}
