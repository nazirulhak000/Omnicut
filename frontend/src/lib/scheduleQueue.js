export const PROJECT_TIME_ZONE = 'Asia/Bangkok';
export const DEFAULT_PRIMARY_TIMES = ['12:30', '19:00', '21:30'];
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
      const times = Array.isArray(day.times) && day.times.length === 3 ? day.times : DEFAULT_PRIMARY_TIMES;
      return [String(index), { enabled: day.enabled !== false, times: [...times].sort() }];
    })),
  };
}

export function templateSlots(startDate, endDate, templateByWeek = {}, now = new Date(), latestScheduledAt = null) {
  const start = parseDateOnly(startDate);
  const end = parseDateOnly(endDate);
  const cursorDate = new Date(Math.max(now.getTime(), latestScheduledAt ? new Date(latestScheduledAt).getTime() : 0));
  const slots = [];
  for (let offset = 0; offset < 366 && slots.length < 10000; offset += 1) {
    const date = new Date(start.getTime());
    date.setUTCDate(date.getUTCDate() + offset);
    const dateKey = `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
    const week = weekStartForDate(dateKey);
    const template = templateForWeek(templateByWeek[week] || templateByWeek.default, week);
    const config = template.days[String((date.getUTCDay() + 6) % 7)];
    if (config?.enabled !== false) {
      config.times.forEach((time) => {
        const iso = buildScheduleIso(dateKey, time);
        if (new Date(iso).getTime() > cursorDate.getTime() && (!latestScheduledAt || new Date(iso).getTime() > new Date(latestScheduledAt).getTime())) {
          slots.push({ date: dateKey, time, scheduledAt: iso });
        }
      });
    }
    if (date >= end && slots.length) break;
  }
  return slots;
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
