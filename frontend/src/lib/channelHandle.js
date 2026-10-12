// TikTok handle normalization -- ONE rule shared with scripts/channel_store.py
// (normalize_handle). Parity is enforced by tests in both languages that read
// tests/fixtures/channel_handle_cases.json.
//
// Order: type -> trim (explicit char set) -> empty -> TikTok URL extraction ->
// strip one leading "@" -> empty -> charset [A-Za-z0-9._] -> ASCII lowercase ->
// length 2..24 -> consecutive dots -> trailing dot. Result: "@" + handle.

export const HANDLE_MIN_LEN = 2;
export const HANDLE_MAX_LEN = 24;

// Same characters as HANDLE_TRIM_CHARS in scripts/channel_store.py. Explicit on
// purpose: String.prototype.trim and Python str.strip disagree on U+FEFF/U+0085.
const TRIM_CLASS =
  ' \\t\\n\\r\\f\\v\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff\\u200b';
const TRIM_RE = new RegExp(`^[${TRIM_CLASS}]+|[${TRIM_CLASS}]+$`, 'g');
const URL_SCHEME_RE = /^[a-z][a-z0-9+.-]*:\/\//i;
const TIKTOK_HOST_PREFIX_RE = /^(?:[a-z0-9-]+\.)*tiktok\.com(?:[:/]|$)/i;
const TIKTOK_URL_RE = /^(?:https?:\/\/)?(?:[a-z0-9-]+\.)*tiktok\.com(?::\d+)?(?:\/([\s\S]*))?$/i;
const HANDLE_CHARS_RE = /^[A-Za-z0-9._]+$/;

export const HANDLE_ERROR_MESSAGES = Object.freeze({
  invalid_type: 'handle ต้องเป็นข้อความ',
  empty: 'กรุณาระบุ handle ของช่อง เช่น @rizanntry',
  not_tiktok_url: 'ลิงก์นี้ไม่ใช่ลิงก์โปรไฟล์ TikTok',
  url_without_handle: 'ลิงก์ TikTok นี้ไม่มี @handle ให้ใช้ลิงก์โปรไฟล์ เช่น tiktok.com/@ชื่อช่อง',
  invalid_chars: 'handle ใช้ได้เฉพาะ a-z, 0-9, จุด และขีดล่าง',
  too_short: `handle ต้องยาวอย่างน้อย ${HANDLE_MIN_LEN} ตัวอักษร`,
  too_long: `handle ยาวได้ไม่เกิน ${HANDLE_MAX_LEN} ตัวอักษร`,
  consecutive_dots: 'handle มีจุดติดกันไม่ได้',
  trailing_dot: 'handle ลงท้ายด้วยจุดไม่ได้',
});

const fail = (code) => ({ ok: false, code, message: HANDLE_ERROR_MESSAGES[code] });

function asciiLower(text) {
  return text.replace(/[A-Z]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) + 32));
}

/**
 * Normalize a TikTok handle or profile URL to "@lowercase".
 * @returns {{ok: true, value: string} | {ok: false, code: string, message: string}}
 */
export function normalizeHandle(raw) {
  if (raw === null || raw === undefined) return fail('empty');
  if (typeof raw !== 'string') return fail('invalid_type');
  let text = raw.replace(TRIM_RE, '');
  if (!text) return fail('empty');
  if (URL_SCHEME_RE.test(text) || TIKTOK_HOST_PREFIX_RE.test(text)) {
    const match = TIKTOK_URL_RE.exec(text);
    if (!match) return fail('not_tiktok_url');
    const rest = (match[1] || '').split(/[?#]/, 1)[0];
    const segment = rest.split('/', 1)[0];
    if (!segment.startsWith('@') || segment === '@') return fail('url_without_handle');
    text = segment;
  }
  if (text.startsWith('@')) text = text.slice(1);
  if (!text) return fail('empty');
  if (!HANDLE_CHARS_RE.test(text)) return fail('invalid_chars');
  text = asciiLower(text);
  if (text.length < HANDLE_MIN_LEN) return fail('too_short');
  if (text.length > HANDLE_MAX_LEN) return fail('too_long');
  if (text.includes('..')) return fail('consecutive_dots');
  if (text.endsWith('.')) return fail('trailing_dot');
  return { ok: true, value: `@${text}` };
}
