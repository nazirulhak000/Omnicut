/**
 * Shared date and relative time formatting utilities.
 */

const THAI_MONTHS_SHORT = [
  'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
  'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'
];

/**
 * Parse a timestamp or date string into a Date object.
 * Handles ISO strings, strings with space instead of 'T', and unix timestamps.
 */
export function parseDate(val) {
  if (!val) return null;
  if (val instanceof Date) return isNaN(val.getTime()) ? null : val;
  if (typeof val === 'number') {
    // If it's in seconds (e.g. 10 digits), convert to ms
    const ms = val < 1e11 ? val * 1000 : val;
    const d = new Date(ms);
    return isNaN(d.getTime()) ? null : d;
  }
  if (typeof val === 'string') {
    const s = val.trim();
    if (!s) return null;
    // Normalize "2026-09-12 23:39:28" to ISO "2026-09-12T23:39:28"
    const normalized = s.includes('T') ? s : s.replace(' ', 'T');
    const d = new Date(normalized);
    return isNaN(d.getTime()) ? null : d;
  }
  return null;
}

/**
 * Returns human-readable relative time in Thai.
 * e.g. "เมื่อสักครู่", "5 นาทีที่แล้ว", "2 ชม. ที่แล้ว", "เมื่อวาน", "3 วันที่แล้ว"
 * Falls back to short date like "13 ก.ย." if older than 7 days.
 */
export function getRelativeTime(val, nowMs = Date.now()) {
  const d = parseDate(val);
  if (!d) return '';

  const diffSec = Math.floor((nowMs - d.getTime()) / 1000);

  // If the date is in the slight future (e.g. client/server clock skew), treat as just now
  if (diffSec < 60) {
    return 'เมื่อสักครู่';
  }
  if (diffSec < 3600) {
    const mins = Math.floor(diffSec / 60);
    return `${mins} นาทีที่แล้ว`;
  }
  if (diffSec < 86400) {
    const hours = Math.floor(diffSec / 3600);
    return `${hours} ชม. ที่แล้ว`;
  }
  if (diffSec < 86400 * 2) {
    return 'เมื่อวาน';
  }
  if (diffSec < 86400 * 7) {
    const days = Math.floor(diffSec / 86400);
    return `${days} วันที่แล้ว`;
  }

  // Older than 7 days -> show short date "D MMM"
  const day = d.getDate();
  const month = THAI_MONTHS_SHORT[d.getMonth()] || '';
  return `${day} ${month}`;
}

/**
 * Returns full date and time string in Thai.
 * e.g. "13 ก.ย. 2026 06:20:15"
 */
export function formatFullDateTime(val) {
  const d = parseDate(val);
  if (!d) return '';

  const day = d.getDate();
  const month = THAI_MONTHS_SHORT[d.getMonth()] || '';
  const year = d.getFullYear();
  const pad = (n) => String(n).padStart(2, '0');
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  const seconds = pad(d.getSeconds());

  return `${day} ${month} ${year} ${hours}:${minutes}:${seconds} น.`;
}
