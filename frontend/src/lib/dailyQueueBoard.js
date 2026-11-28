import { addDays, dateOnly, localParts, parseDateOnly, PROJECT_TIME_ZONE } from './scheduleQueue.js';

export const DAILY_TARGET_CAPACITY = 10;
export const TIKTOK_SCHEDULE_QUOTA_MAX = 30;

/**
 * Format a YYYY-MM-DD key into Thai day header parts in Asia/Bangkok.
 */
export function formatThaiDayHeader(dateKey, todayKey = dateOnly()) {
  const [year, month, day] = String(dateKey || '').split('-').map(Number);
  if (!year || !month || !day) {
    return { title: String(dateKey || ''), subtitle: '', isToday: false, isTomorrow: false, isPast: false };
  }
  const tomorrowKey = addDays(todayKey, 1);
  const isToday = dateKey === todayKey;
  const isTomorrow = dateKey === tomorrowKey;
  const isPast = dateKey < todayKey;
  const utcDate = new Date(Date.UTC(year, month - 1, day, 5));
  const weekday = new Intl.DateTimeFormat('th-TH', { timeZone: PROJECT_TIME_ZONE, weekday: 'long' }).format(utcDate);
  const dayMonth = new Intl.DateTimeFormat('th-TH', { timeZone: PROJECT_TIME_ZONE, day: 'numeric', month: 'short' }).format(utcDate);
  const fullLabel = `${weekday} ${dayMonth}`;

  if (isToday) return { title: `วันนี้ · ${fullLabel}`, subtitle: dateKey, isToday: true, isTomorrow: false, isPast: false };
  if (isTomorrow) return { title: `พรุ่งนี้ · ${fullLabel}`, subtitle: dateKey, isToday: false, isTomorrow: true, isPast: false };
  return { title: fullLabel, subtitle: dateKey, isToday: false, isTomorrow: false, isPast };
}

/**
 * Whether an item can be dragged to another day column.
 */
export function canDragQueueItem(item) {
  return item?.status === 'planned' || item?.status === 'failed';
}

/**
 * Compute stacked status bar counts for a column's items.
 */
export function summarizeColumnStatuses(items = []) {
  const counts = {
    posted: 0,
    scheduled_on_platform: 0,
    ready: 0,
    planned: 0,
    issue: 0,
  };
  for (const item of items) {
    const status = item?.status;
    if (status === 'posted') counts.posted += 1;
    else if (status === 'scheduled_on_platform' || status === 'draft_on_platform') counts.scheduled_on_platform += 1;
    else if (status === 'ready_for_extension' || status === 'awaiting_post') counts.ready += 1;
    else if (status === 'failed' || status === 'confirmation_unknown') counts.issue += 1;
    else counts.planned += 1;
  }
  return counts;
}

/**
 * Build ordered day columns for DailyQueueBoard.
 */
export function buildDayColumns(queue = [], { rangeDays = 7, includeOverdue = false, todayKey = dateOnly() } = {}) {
  const byDate = new Map();
  let maxFutureDate = addDays(todayKey, 6);

  for (const item of queue) {
    if (!item?.scheduled_at) continue;
    const { date } = localParts(item.scheduled_at);
    if (!date) continue;
    if (!byDate.has(date)) byDate.set(date, []);
    byDate.get(date).push(item);
    if (date > maxFutureDate) maxFutureDate = date;
  }

  // Sort each day's items by scheduled_at ascending
  for (const items of byDate.values()) {
    items.sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());
  }

  const dateKeys = [];

  if (includeOverdue) {
    const pastKeys = [...byDate.keys()]
      .filter((key) => key < todayKey && byDate.get(key).some((item) => item.status !== 'posted'))
      .sort();
    dateKeys.push(...pastKeys);
  }

  if (rangeDays === 'all') {
    const startMs = parseDateOnly(todayKey).getTime();
    const endMs = parseDateOnly(maxFutureDate).getTime();
    const spanDays = Math.min(90, Math.max(7, Math.round((endMs - startMs) / 86400000) + 1));
    for (let i = 0; i < spanDays; i += 1) {
      dateKeys.push(addDays(todayKey, i));
    }
  } else {
    const count = Math.max(1, Number(rangeDays) || 7);
    for (let i = 0; i < count; i += 1) {
      dateKeys.push(addDays(todayKey, i));
    }
  }

  return dateKeys.map((dateKey) => {
    const items = byDate.get(dateKey) || [];
    const header = formatThaiDayHeader(dateKey, todayKey);
    const statusCounts = summarizeColumnStatuses(items);
    return {
      dateKey,
      ...header,
      items,
      statusCounts,
    };
  });
}

/**
 * Compute top summary metrics for the Live Sync & Auto-Post bar.
 */
export function computeBoardSummary(queue = [], automationStatus = null, todayKey = dateOnly(), nowMs = Date.now()) {
  const todayItems = [];
  let overdueCount = 0;
  let scheduledQuotaUsed = 0;
  let nextSlotItem = null;
  let nextSlotMs = Infinity;

  for (const item of queue) {
    if (!item?.scheduled_at) continue;
    const { date } = localParts(item.scheduled_at);
    const ms = new Date(item.scheduled_at).getTime();

    if (date === todayKey) todayItems.push(item);
    if (date < todayKey && item.status !== 'posted') overdueCount += 1;
    if (item.status === 'scheduled_on_platform') scheduledQuotaUsed += 1;

    if (item.status !== 'posted' && Number.isFinite(ms) && ms >= nowMs - 60000 && ms < nextSlotMs) {
      nextSlotMs = ms;
      nextSlotItem = item;
    }
  }

  const serverQuota =
    automationStatus?.queue_counts?.scheduled_on_platform ??
    automationStatus?.scheduled_on_platform_count;
  const effectiveQuota = typeof serverQuota === 'number' ? serverQuota : scheduledQuotaUsed;

  return {
    todayCount: todayItems.length,
    nextSlotTime: nextSlotItem ? localParts(nextSlotItem.scheduled_at).time : 'ยังไม่มี',
    scheduledQuotaUsed: effectiveQuota,
    scheduledQuotaMax: automationStatus?.tiktok_schedule_quota_max || TIKTOK_SCHEDULE_QUOTA_MAX,
    overdueCount,
  };
}
