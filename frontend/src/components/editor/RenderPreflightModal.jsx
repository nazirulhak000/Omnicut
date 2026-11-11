import React from 'react';
import { ModalLayer } from '../ui/ModalLayer';
import { X, ShieldAlert, ShieldCheck, AlertCircle, Info, ExternalLink } from 'lucide-react';
import { formatPreflightTime } from '../../lib/renderPreflight.js';

const SEVERITY_TAG = {
  error: { label: 'ต้องแก้', className: 'bg-red-500/20 text-red-200 border border-red-500/30' },
  warning: { label: 'ข้อสังเกต', className: 'bg-amber-500/20 text-amber-100 border border-amber-500/30' },
  info: { label: 'ข้อมูล', className: 'bg-stone-500/25 text-stone-200 border border-stone-500/30' },
};

const ITEM_TONE = {
  error: 'text-red-300 bg-red-500/[0.06] border-red-500/20',
  warning: 'text-amber-100/90 bg-amber-500/[0.04] border-amber-500/20',
  info: 'text-stone-300 bg-white/[0.02] border-white/[0.06]',
};

export default function RenderPreflightModal({ isOpen, onClose, report, onSeek }) {
  if (!isOpen || !report?.issues?.length) return null;

  const holds = report.issues.filter((issue) => issue.code === 'footage_hold');
  const holdSeconds = holds.reduce((total, issue) => total + issue.holdSeconds, 0);
  const infoCount = report.infos?.length ?? 0;
  const score = Number.isFinite(report.viralScore) ? report.viralScore : null;
  const hasErrors = report.errors?.length > 0;

  return (
    <ModalLayer onClose={onClose}
      className="fixed inset-0 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[85vh] w-full max-w-2xl flex-col rounded-3xl border border-white/[0.12] bg-[#0F1420] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
          <div className="flex items-center gap-2.5">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-2xl ${
                hasErrors ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
              }`}
            >
              {hasErrors ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
            </div>
            <div>
              <h3 className="text-base font-bold text-white">ตรวจแผนก่อนเรนเดอร์ & วิเคราะห์ไวรัล</h3>
              <p className="text-xs text-slate-400">
                Preflight Verification & Retention/Compliance Audit
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
            title="ปิดหน้าต่าง (Esc)"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Score & Summary Metrics Bar */}
        <div className="my-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 text-center">
            <div className="text-[11px] font-medium text-slate-400">คะแนนไวรัล</div>
            <div className="mt-1 font-mono text-2xl font-black text-amber-300">
              {score !== null ? `${score}/100` : '—'}
            </div>
          </div>
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 text-center">
            <div className="text-[11px] font-medium text-slate-400">ต้องแก้ไข</div>
            <div
              className={`mt-1 font-mono text-2xl font-black ${
                hasErrors ? 'text-red-400' : 'text-emerald-400'
              }`}
            >
              {report.errors?.length || 0}
            </div>
          </div>
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 text-center">
            <div className="text-[11px] font-medium text-slate-400">ข้อสังเกต</div>
            <div className="mt-1 font-mono text-2xl font-black text-amber-200">
              {report.warnings?.length || 0}
            </div>
          </div>
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3 text-center">
            <div className="text-[11px] font-medium text-slate-400">ข้อมูลคำแนะนำ</div>
            <div className="mt-1 font-mono text-2xl font-black text-stone-300">{infoCount}</div>
          </div>
        </div>

        {holds.length > 0 && (
          <div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-200">
            ⚠️ ภาพตรงบทไม่พอ {holdSeconds.toFixed(2)} วินาทีใน {holds.length} ช็อต
            ระบบค้างภาพสุดท้ายไว้ให้อัตโนมัติ (ยังคงเรนเดอร์ได้)
          </div>
        )}

        <p className="mb-2 text-xs text-slate-400">
          * ข้อสังเกตด้าน Hook, จังหวะช็อต และเสียง เป็นคำแนะนำเพื่อเพิ่มโอกาสไวรัล
          ไม่บังคับแก้ไขก่อนเรนเดอร์ ส่วนข้อผิดพลาดสีแดง (ถ้ามี) จำเป็นต้องแก้ไขก่อนเรนเดอร์
        </p>

        {/* Scrollable list of all issues */}
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          <ul className="space-y-2">
            {report.issues.map((issue, index) => {
              const tag = SEVERITY_TAG[issue.severity] || SEVERITY_TAG.warning;
              const toneClass = ITEM_TONE[issue.severity] || ITEM_TONE.warning;
              return (
                <li
                  key={`${issue.code}-${issue.clipId}-${index}`}
                  className={`flex items-start justify-between gap-3 rounded-xl border p-2.5 text-xs transition-colors ${toneClass}`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${tag.className}`}>
                        {tag.label}
                      </span>
                      {issue.clipIndex != null && (
                        <span className="font-semibold text-slate-300">
                          ช็อต {issue.clipIndex + 1}
                        </span>
                      )}
                      <span className="font-mono text-[11px] text-slate-400">
                        {issue.start == null && issue.source === 'viral'
                          ? 'ทั้งคลิป'
                          : formatPreflightTime(issue.start)}
                        {issue.end != null && issue.end !== issue.start
                          ? ` – ${formatPreflightTime(issue.end)}`
                          : ''}
                      </span>
                    </div>
                    <p className="mt-1 leading-relaxed text-slate-200">{issue.message}</p>
                  </div>

                  {onSeek && issue.start != null && (
                    <button
                      type="button"
                      onClick={() => {
                        onSeek(issue.start);
                        onClose();
                      }}
                      className="flex-shrink-0 flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-amber-300 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
                    >
                      <span>ดูช่วงนี้</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        {/* Footer */}
        <div className="mt-4 flex items-center justify-end border-t border-white/[0.08] pt-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-[#D97757] hover:bg-[#C2683D] px-5 py-2 text-xs font-bold text-white transition-colors cursor-pointer"
          >
            ปิดหน้าต่าง
          </button>
        </div>
      </div>
    </ModalLayer>
  );
}
