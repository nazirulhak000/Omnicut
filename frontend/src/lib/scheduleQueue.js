export const PROJECT_TIME_ZONE = 'Asia/Bangkok';

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
