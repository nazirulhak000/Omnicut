import React, { useState } from 'react';
import { X, ExternalLink } from 'lucide-react';
import { formatPreflightTime } from '../../lib/renderPreflight.js';

// Severity is carried by a word as well as by color, so the list still reads
// for color-blind users and in high-contrast mode.
const SEVERITY_TAG = {
  error: { label: 'ต้องแก้', className: 'bg-red-500/20 text-red-200' },
  warning: { label: 'ข้อสังเกต', className: 'bg-amber-500/20 text-amber-100' },
  info: { label: 'ข้อมูล', className: 'bg-stone-500/25 text-stone-200' },
};
const ITEM_TONE = { error: 'text-red-300', warning: '', info: 'text-amber-200/75' };

export default function RenderPreflightNotice({ report, onSeek, onOpenModal }) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (!report?.issues?.length) return null;
  if (isDismissed) return null;

  const holds = report.issues.filter((issue) => issue.code === 'footage_hold');
  const holdSeconds = holds.reduce((total, issue) => total + issue.holdSeconds, 0);
  const infoCount = report.infos?.length ?? 0;
  const hasViral = report.issues.some((issue) => issue.source === 'viral');
  const score = Number.isFinite(report.viralScore) ? report.viralScore : null;

  const hasErrors = report.errors?.length > 0;
  const hasHolds = holds.length > 0;
  const isAuditMode =
    typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('renderAudit') === '1';

  // If there are no errors and no footage holds (only advisory warnings/viral tips),
  // do not intrude on the top workspace unless explicitly in audit mode.
  if (!hasErrors && !hasHolds && !isAuditMode) {
    return null;
  }

  return (
    <details
      open={hasErrors}
      data-render-preflight
      data-footage-coverage-notice={holds.length ? '' : undefined}
      className="flex-shrink-0 border-b border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-200"
    >
      <summary className="flex cursor-pointer items-center justify-between select-none">
        <div className="flex-1 pr-2">
          ตรวจแผนก่อนเรนเดอร์: ต้องแก้ {report.errors.length} รายการ · ข้อสังเกต {report.warnings.length} รายการ
          {infoCount > 0 ? ` · ข้อมูล ${infoCount} รายการ` : ''}
          {score !== null ? <span data-viral-score className="tabular-nums"> · คะแนนไวรัล {score}/100</span> : null}
          {holds.length > 0 ? ` · ภาพตรงบทไม่พอ ${holdSeconds.toFixed(2)} วินาทีใน ${holds.length} ช็อต ระบบค้างภาพสุดท้ายไว้` : ''}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {onOpenModal && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onOpenModal();
              }}
              className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 text-[11px] font-semibold text-amber-100 hover:bg-amber-500/30 transition-colors"
            >
              <span>เปิดดูทั้งหมด</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDismissed(true);
            }}
            title="ซ่อนแถบนี้"
            className="flex h-5 w-5 items-center justify-center rounded-md text-amber-300/80 hover:bg-amber-500/20 hover:text-white transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </summary>
      <p className="mt-2">ตรวจจากข้อมูลไทม์ไลน์ ยังไม่ได้ตรวจการเปิดไฟล์หรือเฟรมดำจริง ภาพค้างตามแผนที่อนุญาตยังเรนเดอร์ได้</p>
      {hasViral && (
        <p className="mt-1">ข้อสังเกตด้าน hook จังหวะช็อต และเสียง ไม่บังคับแก้ ส่วนราคาหรือคำเคลมเกินจริงต้องแก้ก่อนเรนเดอร์</p>
      )}
      <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto">
        {report.issues.map((issue, index) => {
          const tag = SEVERITY_TAG[issue.severity] || SEVERITY_TAG.warning;
          return (
            <li key={`${issue.code}-${issue.clipId}-${index}`} data-severity={issue.severity} data-source={issue.source || 'timeline'} className={ITEM_TONE[issue.severity] || ''}>
              <span className={`mr-1.5 inline-block rounded px-1 py-px text-[11px] leading-4 ${tag.className}`}>{tag.label}</span>
              <span>{issue.clipIndex == null ? '' : `ช็อต ${issue.clipIndex + 1} · `}{issue.start == null && issue.source === 'viral' ? 'ทั้งคลิป' : formatPreflightTime(issue.start)}{issue.end != null && issue.end !== issue.start ? ` – ${formatPreflightTime(issue.end)}` : ''} · {issue.message}</span>
              {onSeek && issue.start != null && <button type="button" onClick={() => onSeek(issue.start)} className="ml-2 inline-flex items-center rounded-sm underline underline-offset-2 focus-visible:outline focus-visible:outline-1 focus-visible:outline-amber-200">ดูช่วงนี้</button>}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
