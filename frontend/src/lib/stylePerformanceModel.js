// View model for GET /api/tiktok-stats/style-performance.
//
// The endpoint (PostLog.style_performance_report in scripts/post_log.py)
// returns `{ measured, by_style_preset, by_hook_style, by_story_format }`;
// every group row is `{ <field>: id, count, median_views, avg_watch_time_sec,
// completion_rate }`, with null where no post in the group has that metric.
// Only metrics from posts at least 48h old are counted.
//
// A group with fewer than MIN_RELIABLE_SAMPLE measured posts is flagged
// `lowSample`, and never gets the "highest median" marker: five posts is too
// few to call one style better than another.

import { STYLE_PRESET_CATALOG } from './stylePresetCatalog.js';
import { storyFormatLabel } from './clipFormatOptions.js';

export const MIN_RELIABLE_SAMPLE = 5;

export const STYLE_GROUPS = Object.freeze([
  Object.freeze({ id: 'style_preset', label: 'สไตล์ตัดต่อ' }),
  Object.freeze({ id: 'hook_style', label: 'แนว Hook' }),
  Object.freeze({ id: 'story_format', label: 'รูปแบบการเล่า' }),
]);

// == HOOK_STYLES[].style_name in scripts/hook_generator.py.
export const HOOK_STYLE_LABELS = Object.freeze({
  curiosity: 'กระตุ้นความสงสัย',
  warning: 'เตือนภัย / หยุดก่อน',
  social_proof: 'ผลลัพธ์จริง / สถิติ',
  deal_promo: 'ห้ามพลาด / ของมันต้องมี',
  pain_point: 'แทงใจดำ / ขยี้ปัญหา',
});

const UNSPECIFIED = 'unspecified';

/** `{ label, sublabel }` for one group id. Unknown ids are shown as they are. */
export function styleGroupLabel(groupBy, id) {
  const key = String(id ?? '').trim();
  if (!key || key === UNSPECIFIED) return { label: 'ไม่ระบุ', sublabel: 'คลิปที่ไม่ได้บันทึกค่านี้' };
  if (groupBy === 'style_preset') {
    const preset = STYLE_PRESET_CATALOG.find((p) => p.id === key.toLowerCase());
    return preset ? { label: preset.labelTh, sublabel: preset.label } : { label: key, sublabel: '' };
  }
  if (groupBy === 'hook_style') {
    return { label: HOOK_STYLE_LABELS[key] || key, sublabel: HOOK_STYLE_LABELS[key] ? key : '' };
  }
  if (groupBy === 'story_format') {
    const label = storyFormatLabel(key);
    return { label, sublabel: label !== key ? key : '' };
  }
  return { label: key, sublabel: '' };
}

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/**
 * Rows for one grouping, in the server's order (median views, highest first).
 * `isTop` marks the reliable group with the highest median views, and only
 * when at least two groups are reliable -- otherwise there is nothing to beat.
 */
export function buildStylePerformanceRows(report, groupBy) {
  const raw = Array.isArray(report?.[`by_${groupBy}`]) ? report[`by_${groupBy}`] : [];
  const rows = raw
    .filter((g) => g && typeof g === 'object')
    .map((g) => {
      const id = g[groupBy] ?? UNSPECIFIED;
      const count = Math.max(0, Math.round(Number(g.count) || 0));
      return {
        id: String(id),
        ...styleGroupLabel(groupBy, id),
        count,
        medianViews: num(g.median_views),
        avgWatchTimeSec: num(g.avg_watch_time_sec),
        completionRate: num(g.completion_rate),
        lowSample: count < MIN_RELIABLE_SAMPLE,
        isTop: false,
      };
    });
  const reliable = rows.filter((r) => !r.lowSample && r.medianViews != null);
  if (reliable.length >= 2) {
    const best = reliable.reduce((a, b) => (b.medianViews > a.medianViews ? b : a));
    const tied = reliable.filter((r) => r.medianViews === best.medianViews);
    if (tied.length === 1) best.isTop = true;
  }
  return rows;
}

/** Largest median views among the rows (bar scale), or 0. */
export function maxMedianViews(rows) {
  return rows.reduce((m, r) => (r.medianViews != null && r.medianViews > m ? r.medianViews : m), 0);
}

export function formatWatchTime(sec) {
  return sec == null ? null : `${sec.toFixed(1)} วิ`;
}

export function formatCompletionRate(rate) {
  // PostLog stores the rate as a 0..1 fraction (parse_completion_rate).
  return rate == null ? null : `${(rate * 100).toFixed(1)}%`;
}
