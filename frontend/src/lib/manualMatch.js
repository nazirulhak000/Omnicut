// Manual matching helpers for unplaced TikTok Studio rows (see
// PerformanceAnalyticsTab's "แถวที่ยังไม่ได้จับคู่" section and the
// /api/tiktok-stats/attach contract). Pure functions so they are testable
// without any backend.

export function buildCandidateOptions(candidates) {
  const list = Array.isArray(candidates) ? candidates : [];
  return list
    .map((c) => ({
      key: `${c.clip_file || 'clip.mp4'}::${c.hook_title || ''}`,
      label: [c.hook_title, c.product_name].filter(Boolean).join(' — ') || c.clip_file || 'คลิป',
      candidate: c,
    }))
    .sort((a, b) => a.label.localeCompare(b.label, 'th'));
}

export function findOptionKey(options, candidate) {
  if (!candidate) return '';
  return (options.find((o) => o.candidate === candidate) || {}).key || '';
}

export function buildAttachPayload(pendingRow, option) {
  if (!pendingRow || !pendingRow.id) return null;
  if (!option || !option.candidate) return null;
  return { pending_id: pendingRow.id, candidate: option.candidate };
}

export function metricSummary(row) {
  const parts = [];
  for (const [field, label] of [['views', 'วิว'], ['likes', 'ถูกใจ'], ['comments', 'คอมเมนต์']]) {
    const v = Number(row?.[field]);
    if (Number.isFinite(v) && v > 0) parts.push(`${label} ${v}`);
  }
  return parts.length ? parts.join(' · ') : 'ยังไม่มีตัวเลข';
}
