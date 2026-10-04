import React from 'react';
import { footageCoverageSummary } from '../../lib/footageCoverageSummary';

export default function FootageCoverageNotice({ clips }) {
  const { count, seconds } = footageCoverageSummary(clips);
  if (!count) return null;
  return (
    <div role="status" data-footage-coverage-notice className="flex-shrink-0 border-b border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
      ภาพตรงบทไม่พอ {seconds.toFixed(2)} วินาทีใน {count} ช็อต ระบบค้างภาพสุดท้ายไว้เพื่อรักษาเสียงและซับ เพิ่มภาพตรงฟีเจอร์หรือปรับช่วงช็อตหากต้องการภาพเคลื่อนไหวตลอด
    </div>
  );
}
