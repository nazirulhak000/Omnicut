import React from 'react';
import { AlertTriangle, CheckCircle2, Gauge, ShieldCheck } from 'lucide-react';

import { formatDuration, projectBlockers, projectDuration, STATUS_LABELS } from '../../lib/gadgetMediaProject.js';


export default function QualityInspector({ project, timeline }) {
  const report = project?.quality_report || {};
  const blockers = projectBlockers(project);
  const duration = projectDuration(project, timeline);

  return (
    <aside className="space-y-4 xl:sticky xl:top-4">
      <section className="rounded-2xl bg-[#0B0F19] p-4 ring-1 ring-white/[0.08]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold text-slate-400">สถานะงาน</p>
            <p className="mt-1 text-sm font-black text-white">{STATUS_LABELS[project?.status] || project?.status}</p>
          </div>
          <span className={`rounded-lg px-2 py-1 text-[10px] font-black ${report.passed ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-200'}`}>
            {report.passed ? 'ผ่าน Hard Gate' : 'ยังมี Blocker'}
          </span>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-white/[0.035] p-3">
            <dt className="flex items-center gap-1.5 text-[10px] text-slate-500"><Gauge className="h-3.5 w-3.5" />Editorial</dt>
            <dd className="mt-1 text-xl font-black text-white">{report.editorial_score || 0}<span className="text-xs text-slate-500">/100</span></dd>
          </div>
          <div className="rounded-xl bg-white/[0.035] p-3">
            <dt className="text-[10px] text-slate-500">Master duration</dt>
            <dd className={`mt-1 text-xl font-black ${duration >= 45 && duration <= 60 ? 'text-emerald-300' : 'text-amber-200'}`}>{formatDuration(duration)}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-2xl bg-[#0B0F19] p-4 ring-1 ring-white/[0.08]">
        <h3 className="flex items-center gap-2 text-sm font-black text-white">
          <ShieldCheck className="h-4 w-4 text-cyan-300" /> Quality Gate
        </h3>
        {report.gates?.length ? (
          <ul className="mt-3 space-y-2">
            {report.gates.map((gate) => (
              <li key={gate.id} className="flex items-start gap-2 text-xs leading-5">
                {gate.passed
                  ? <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-emerald-300" />
                  : <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-amber-300" />}
                <span className={gate.passed ? 'text-slate-300' : 'text-amber-100'}>{gate.message}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs leading-5 text-slate-400">กด “ตรวจ Quality” ในขั้น Review เพื่อดูผลครบทุก Gate</p>
        )}
      </section>

      {blockers.length > 0 && (
        <section className="rounded-2xl bg-amber-500/[0.07] p-4 ring-1 ring-amber-400/25">
          <h3 className="text-xs font-black text-amber-100">ต้องแก้ก่อน Render {blockers.length} รายการ</h3>
          <ul className="mt-2 space-y-1.5 text-[11px] leading-5 text-amber-100/80">
            {blockers.map((item) => <li key={item.id}>• {item.message}</li>)}
          </ul>
        </section>
      )}
    </aside>
  );
}

