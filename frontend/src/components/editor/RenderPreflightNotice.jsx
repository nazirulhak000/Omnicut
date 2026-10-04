import React from 'react';
import { formatPreflightTime } from '../../lib/renderPreflight.js';

export default function RenderPreflightNotice({ report, onSeek }) {
  if (!report?.issues?.length) return null;
  const holds = report.issues.filter((issue) => issue.code === 'footage_hold');
  const holdSeconds = holds.reduce((total, issue) => total + issue.holdSeconds, 0);
  return (
    <details open={report.errors.length > 0} data-render-preflight data-footage-coverage-notice={holds.length ? '' : undefined} className="flex-shrink-0 border-b border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
      <summary className="cursor-pointer">ตรวจแผนก่อนเรนเดอร์: ต้องแก้ {report.errors.length} รายการ · ข้อสังเกต {report.warnings.length} รายการ{holds.length > 0 ? ` · ภาพตรงบทไม่พอ ${holdSeconds.toFixed(2)} วินาทีใน ${holds.length} ช็อต ระบบค้างภาพสุดท้ายไว้` : ''}</summary>
      <p className="mt-2">ตรวจจากข้อมูลไทม์ไลน์ ยังไม่ได้ตรวจการเปิดไฟล์หรือเฟรมดำจริง ภาพค้างตามแผนที่อนุญาตยังเรนเดอร์ได้</p>
      <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto">
        {report.issues.map((issue, index) => (
          <li key={`${issue.code}-${issue.clipId}-${index}`} className={issue.severity === 'error' ? 'text-red-300' : ''}>
            <span>{issue.clipIndex == null ? '' : `ช็อต ${issue.clipIndex + 1} · `}{formatPreflightTime(issue.start)}{issue.end != null && issue.end !== issue.start ? ` – ${formatPreflightTime(issue.end)}` : ''} · {issue.message}</span>
            {onSeek && issue.start != null && <button type="button" onClick={() => onSeek(issue.start)} className="ml-2 inline-flex items-center underline">ดูช่วงนี้</button>}
          </li>
        ))}
      </ul>
    </details>
  );
}
