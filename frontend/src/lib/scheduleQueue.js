export const PROJECT_TIME_ZONE = 'Asia/Bangkok';
export const DEFAULT_PRIMARY_TIMES = ['09:00', '12:30', '16:00', '19:00', '21:30'];
export const WEEKDAY_LABELS = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'];

export function pad2(value) {
  return String(value).padStart(2, '0');
}

export function toLocalDateTime(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: PROJECT_TIME_ZONE,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).reduce((out, part) => ({ ...out, [part.type]: part.value }), {});
  return { date: `${parts.year}-${parts.month}-${parts.day}`, time: `${parts.hour}:${parts.minute}` };
}

export function snapTimeToFiveMinutes(time) {
  const [hour, minute] = String(time || '00:00').split(':').map(Number);
  const total = Math.max(0, Math.min(1439, (hour || 0) * 60 + (minute || 0)));
  const snapped = Math.round(total / 5) * 5;
  const bounded = Math.min(1435, snapped);
  return `${pad2(Math.floor(bounded / 60))}:${pad2(bounded % 60)}`;
}

export function buildScheduleIso(date, time) {
  return `${date}T${snapTimeToFiveMinutes(time)}:00+07:00`;
}

export function mergeScheduleDraft(current, field, value) {
  return {
    date: field === 'date' ? String(value || '') : String(current?.date || ''),
    time: field === 'time' ? String(value || '') : String(current?.time || ''),
  };
}

export function scheduleTimeOptions() {
  return Array.from({ length: 288 }, (_, index) => `${pad2(Math.floor(index / 12))}:${pad2((index % 12) * 5)}`);
}

export function primaryTimeOptions() {
  return scheduleTimeOptions();
}

export function dateOnly(value = new Date()) {
  return toLocalDateTime(value).date;
}

export function parseDateOnly(value) {
  const [year, month, day] = String(value || '').split('-').map(Number);
  return new Date(Date.UTC(year || 1970, (month || 1) - 1, day || 1, 5));
}

export function weekStartForDate(value) {
  const date = parseDateOnly(value);
  const weekday = (date.getUTCDay() + 6) % 7;
  date.setUTCDate(date.getUTCDate() - weekday);
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

export function addDays(value, days) {
  const date = parseDateOnly(value);
  date.setUTCDate(date.getUTCDate() + Number(days || 0));
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

export function templateForWeek(template, weekStart = null) {
  const days = template?.days || {};
  return {
    id: template?.id || 'default',
    week_start: weekStart || template?.week_start || null,
    timezone: PROJECT_TIME_ZONE,
    days: Object.fromEntries(Array.from({ length: 7 }, (_, index) => {
      const day = days[String(index)] || {};
      const times = Array.isArray(day.times) && day.times.length > 0
        ? [...new Set(day.times)]
        : DEFAULT_PRIMARY_TIMES;
      return [String(index), { enabled: day.enabled !== false, times: [...times].sort() }];
    })),
  };
}

export function templateSlots(startDate, endDate, templateByWeek = {}, now = new Date(), latestScheduledAt = null) {
  const start = parseDateOnly(startDate);
  const end = parseDateOnly(endDate);
  const latestMs = latestScheduledAt ? new Date(latestScheduledAt).getTime() : 0;
  const latestDate = latestMs ? parseDateOnly(toLocalDateTime(new Date(latestMs)).date) : null;
  const latestWithinRange = latestDate && latestDate >= start && latestDate <= end ? latestMs : 0;
  const cursorDate = new Date(Math.max(now.getTime(), latestWithinRange));
  const slots = [];
  for (let offset = 0; offset < 366 && slots.length < 10000; offset += 1) {
    const date = new Date(start.getTime());
    date.setUTCDate(date.getUTCDate() + offset);
    if (date > end) break;
    const dateKey = `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
    const week = weekStartForDate(dateKey);
    const template = templateForWeek(templateByWeek[week] || templateByWeek.default, week);
    const config = template.days[String((date.getUTCDay() + 6) % 7)];
    if (config?.enabled !== false) {
      config.times.forEach((time) => {
        const iso = buildScheduleIso(dateKey, time);
        if (new Date(iso).getTime() > cursorDate.getTime() && (!latestWithinRange || new Date(iso).getTime() > latestWithinRange)) {
          slots.push({ date: dateKey, time, scheduledAt: iso });
        }
      });
    }
  }
  return slots;
}

export function estimateQueueCoverage({ readyCount = 0, template, startDate, now = new Date(), latestScheduledAt = null, horizonDays = 366 } = {}) {
  const count = Math.max(0, Number(readyCount) || 0);
  const start = startDate || dateOnly(now);
  const week = weekStartForDate(start);
  const normalizedTemplate = templateForWeek(template, week);
  const slots = templateSlots(
    start,
    addDays(start, Math.max(1, Number(horizonDays) || 366) - 1),
    { default: normalizedTemplate },
    now,
    latestScheduledAt,
  ).slice(0, count);
  const coveredDates = [...new Set(slots.map((slot) => slot.date))];
  const weeklyCapacity = Object.values(normalizedTemplate.days)
    .filter((day) => day.enabled !== false)
    .reduce((total, day) => total + day.times.length, 0);
  const lastSlot = slots[slots.length - 1] || null;
  return {
    readyCount: count,
    slotCount: slots.length,
    coveredDays: coveredDates.length,
    endDate: lastSlot?.date || '',
    endWeekStart: lastSlot ? weekStartForDate(lastSlot.date) : '',
    weeklyCapacity,
    firstDate: coveredDates[0] || '',
  };
}

export function seededRandom(seed = 1) {
  let value = (Number(seed) >>> 0) || 1;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

export function addMinutes(date, minutes) {
  const value = new Date(`${date.date}T${date.time}:00+07:00`);
  value.setMinutes(value.getMinutes() + minutes);
  return localParts(value.toISOString());
}

export function nextTemplateSlotAfterLatest(items = [], templatesByWeek = {}, now = new Date()) {
  const latestMs = items
    .filter((item) => item?.status !== 'posted')
    .map((item) => new Date(item?.scheduled_at || '').getTime())
    .filter(Number.isFinite)
    .reduce((latest, value) => Math.max(latest, value), 0);
  const cursorMs = Math.max(now.getTime(), latestMs);
  const cursorDate = parseDateOnly(toLocalDateTime(new Date(cursorMs)).date);
  const occupied = new Set(items
    .filter((item) => item?.status !== 'posted')
    .map((item) => {
      const timestamp = new Date(item?.scheduled_at || '');
      if (Number.isNaN(timestamp.getTime())) return null;
      const parts = localParts(timestamp.toISOString());
      return buildScheduleIso(parts.date, parts.time);
    })
    .filter(Boolean));

  for (let offset = 0; offset < 366; offset += 1) {
    const date = new Date(cursorDate.getTime());
    date.setUTCDate(date.getUTCDate() + offset);
    const dateKey = `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
    const week = weekStartForDate(dateKey);
    const rawTemplate = templatesByWeek[week] || templatesByWeek.default;
    if (!rawTemplate) continue;
    const template = templateForWeek(rawTemplate, week);
    const dayConfig = template.days[String((date.getUTCDay() + 6) % 7)];
    if (dayConfig?.enabled === false) continue;
    for (const time of dayConfig?.times || []) {
      const iso = buildScheduleIso(dateKey, time);
      const timestamp = new Date(iso).getTime();
      if (timestamp > cursorMs && !occupied.has(iso)) return { date: dateKey, time };
    }
  }
  return null;
}

export function sortScheduleItems(items = []) {
  return [...items].sort((a, b) => String(a.scheduled_at || '').localeCompare(String(b.scheduled_at || '')) || String(a.id || '').localeCompare(String(b.id || '')));
}

export function groupScheduleItems(items = []) {
  return sortScheduleItems(items).reduce((groups, item) => {
    const date = String(item.scheduled_at || '').slice(0, 10) || 'ไม่ระบุวันที่';
    (groups[date] ||= []).push(item);
    return groups;
  }, {});
}

export function localParts(iso) {
  const date = new Date(iso);
  return toLocalDateTime(Number.isNaN(date.getTime()) ? new Date() : date);
}
