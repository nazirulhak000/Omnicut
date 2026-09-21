import React from 'react';
import { Check, LockKeyhole } from 'lucide-react';

import { PRODUCT_VIDEO_STAGES } from '../../lib/gadgetMediaProject.js';


const STAGE_STATUS_INDEX = {
  brief: 0,
  sourcing: 1,
  source_ready: 2,
  research_ready: 3,
  script_ready: 4,
  in_production: 4,
  review_required: 5,
  ready_to_render: 5,
  rendered: 5,
  approved: 5,
  published: 5,
};


export default function StageRail({ activeStage, status, onChange }) {
  const currentIndex = PRODUCT_VIDEO_STAGES.findIndex((stage) => stage.id === activeStage);
  const reachedIndex = STAGE_STATUS_INDEX[status] ?? 0;

  return (
    <nav aria-label="ขั้นตอนผลิต Product Video" className="overflow-x-auto rounded-2xl bg-[#090D15] p-1.5 ring-1 ring-white/[0.08]">
      <ol className="flex min-w-[760px] items-stretch gap-1">
        {PRODUCT_VIDEO_STAGES.map((stage, index) => {
          const active = index === currentIndex;
          const completed = index < reachedIndex;
          const available = index <= reachedIndex + 1;
          return (
            <li key={stage.id} className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => onChange(stage.id)}
                disabled={!available}
                aria-current={active ? 'step' : undefined}
                title={available ? stage.hint : 'บันทึกขั้นตอนก่อนหน้าให้พร้อมก่อน'}
                className={stageButtonClasses(active)}
              >
                <span className={stageNumberClasses({ active, completed })}>
                  {completed ? <Check className="h-3.5 w-3.5" /> : available ? index + 1 : <LockKeyhole className="h-3 w-3" />}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-xs font-black">{stage.label}</span>
                  <span className={`block truncate text-[10px] ${active ? 'text-black/60' : 'text-slate-500'}`}>{stage.hint}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}


function stageNumberClasses({ active, completed }) {
  const base = 'grid h-6 w-6 flex-none place-items-center rounded-lg text-[11px] font-black';
  if (active) return `${base} bg-black/15 text-[#061116]`;
  if (completed) return `${base} bg-emerald-500/15 text-emerald-200`;
  return `${base} bg-white/[0.06] text-slate-400`;
}


function stageButtonClasses(active) {
  const base = 'group flex min-h-14 w-full items-center gap-2 rounded-xl px-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:cursor-not-allowed disabled:opacity-45';
  if (active) return `${base} bg-cyan-300 text-[#061116]`;
  return `${base} text-slate-300 hover:bg-white/[0.06]`;
}
