// Shared guards for unattended posting. Loaded by the service worker (importScripts), the side panel
// (<script>) and the Node conductor (require) -- one source of truth for what may be posted and how
// a finished post is recognised on TikTok Studio > Content.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniPostGuard = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  // Channel rule: never publish price / discount text (breaks TikTok rules).
  // Twin of scripts/content_guard.py (same cases in tests/fixtures/content_guard_cases.json, tested on both sides).
  // ฟรี / โปร / ถูก on their own are NOT price text; a number with a currency, a percentage, a discount word or ราคา is.
  const PRICE_RE_STRICT = new RegExp(
    '฿|[$€£¥]\\s*\\d|\\d\\s*[$€£¥]'
    + '|\\b(?:thb|usd|baht)\\b'
    + '|\\d[\\d,.]*\\s*(?:บาท|บ\\.|baht|฿|k\\s*บาท)'
    + '|\\d+\\.-'
    + '|ราคา|ลดราคา|ส่วนลด|ร้อยละ'
    + '|ลด\\s*\\d+\\s*(?:%|บาท|฿|\\.-)|ลดเหลือ|ลด\\s*\\d+\\s*เหลือ'
    + '|\\d+\\s*%'
    + '|\\d+\\s*%?\\s*off\\b|\\boff\\s*\\d'
    + '|(?:เหลือ|เพียง|เริ่มต้น|เริ่มที่|แค่)\\s*\\d+\\s*(?:บาท|฿|\\.-)?(?=\\s|$|[^\\d%a-z])', 'i');
  // A template placeholder that was never filled in, e.g. {product_name}.
  const PLACEHOLDER_RE_STRICT = new RegExp(
    '\\{[a-z][a-z0-9_]*\\}|\\{\\{[^}]*\\}\\}|\\$\\{[^}]*\\}|\\[[a-z]+_[a-z_]+\\]|<[a-z]+_[a-z_]+>|%[sd]\\b'
    + '|\\b(?:undefined|null|nan)\\b|\\btodo\\b|\\blorem ipsum\\b', 'i');
  const MAX_TEXT_CHARS = 4000;
  const MAX_HASHTAGS = 30;
  const INVISIBLE_RE = new RegExp('[\\u00ad\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u2064\\ufeff]', 'g');
  const DIGIT_BLOCKS = [0x0E50, 0x0660, 0x06F0];   // Thai, Arabic-Indic, Extended Arabic-Indic zero

  // NFKC, no zero-width/format characters, Thai/Arabic digits -> ASCII, single spaces, lower case.
  function normalizeText(text) {
    let value = String(text == null ? '' : text);
    if (value.normalize) value = value.normalize('NFKC');
    value = value.replace(INVISIBLE_RE, '').replace(/٪/g, '%').replace(/[٠-٩۰-۹๐-๙]/g, ch => {
      const code = ch.charCodeAt(0);
      for (const zero of DIGIT_BLOCKS) if (code >= zero && code < zero + 10) return String(code - zero);
      return ch;
    });
    return value.replace(/\s+/g, ' ').trim().toLowerCase();
  }

  // '' = fine, else why this caption/hashtag text may not be typed or posted (twin: content_guard.content_reason).
  function contentReason(caption, hashtags, options = {}) {
    const raw = `${caption || ''}\n\n${hashtags || ''}`;
    const text = normalizeText(raw);
    if (!text) return 'empty_caption';
    if (PLACEHOLDER_RE_STRICT.test(text)) return 'placeholder_in_caption';
    if (!options.allowPrice && PRICE_RE_STRICT.test(text)) return 'price_in_caption';
    if (raw.length > MAX_TEXT_CHARS) return 'caption_too_long';
    if ((raw.match(/#[^\s#]+/g) || []).length > MAX_HASHTAGS) return 'too_many_hashtags';
    return '';
  }
  const PRICE_RE = PRICE_RE_STRICT;
  const PLACEHOLDER_RE = PLACEHOLDER_RE_STRICT;
  const MIN_LEAD_MS = 15 * 60 * 1000;

  const alnum = text => String(text || '').toLowerCase().replace(/[^a-z0-9ก-๙]/g, '');

  // Does one Content-page row (its visible text) belong to this clip? Needs the start of the caption;
  // a scheduled clip must also show its day number and time (12h or 24h).
  function rowMatchesClip(rowText, clip) {
    const row = alnum(rowText);
    const key = alnum(clip.caption).slice(0, 20);
    if (key.length < 8 || !row.includes(key)) return { ok: false, reason: 'caption_not_found' };
    if (clip.schedule_date && clip.schedule_time) {
      const [hh, mm] = clip.schedule_time.split(':').map(Number);
      const h12 = hh % 12 === 0 ? 12 : hh % 12;
      const time12 = `${h12}:${String(mm).padStart(2, '0')}${hh >= 12 ? 'pm' : 'am'}`;
      const flat = String(rowText).toLowerCase().replace(/\s+/g, '');
      const day = Number(clip.schedule_date.slice(8, 10));
      const hasTime = flat.includes(time12) || flat.includes(clip.schedule_time);
      // the day number must sit next to a month name ("Nov 10" / "10 พ.ย."); a bare number equal to the day (views,
      // likes, comments) is not a date
      const months = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ม\\.ค\\.|ก\\.พ\\.|มี\\.ค\\.|เม\\.ย\\.|พ\\.ค\\.|มิ\\.ย\\.|ก\\.ค\\.|ส\\.ค\\.|ก\\.ย\\.|ต\\.ค\\.|พ\\.ย\\.|ธ\\.ค\\.';
      const hasDay = new RegExp(`(?:(?:${months})[a-z]*\\.?\\s*${day}(?![0-9:])|(?:^|[^0-9])${day}\\s*(?:${months}))`, 'i').test(String(rowText).replace(/\s+/g, ' '));
      if (!hasTime || !hasDay) return { ok: false, reason: 'schedule_badge_mismatch' };
    }
    return { ok: true };
  }

  // The post text exactly as the side panel / conductor will type it.
  function clipCaptionText(clip) {
    const caption = clip.tiktok_caption || clip.caption || clip.hook_title || clip.name || '';
    const hashtags = clip.tiktok_hashtags || clip.hashtags || '';
    return { caption, hashtags };
  }

  // '' = may be posted, otherwise a short reason to skip it.
  //   exportRecord: the /api/exports row of clip.export_id (undefined = missing)
  //   options.exportsKnown: false when the registry could not be read (then do not guess)
  function clipSkipReason(clip, exportRecord, now = Date.now(), options = {}) {
    const { exportsKnown = true, allowPriceCaption = false, ignoreSlot = false, requireSchedule = false } = options;
    if (exportsKnown && clip.export_id) {
      if (!exportRecord) return 'export_missing';
      if (exportRecord.is_posted || exportRecord.export_status === 'posted') return 'export_already_posted';
      if (exportRecord.is_qc_rejected) return 'export_qc_rejected';
    }
    const { caption, hashtags } = clipCaptionText(clip);
    const content = contentReason(caption, hashtags, {allowPrice: allowPriceCaption});
    if (content) return content;
    // a clip without a publish time in a scheduled run would be posted LIVE (the worker skips the schedule step)
    if (requireSchedule && !(clip.schedule_date && clip.schedule_time)) return 'no_schedule';
    if (!ignoreSlot && clip.schedule_date && clip.schedule_time) {
      const slot = new Date(`${clip.schedule_date}T${clip.schedule_time}:00`).getTime();
      if (!Number.isFinite(slot) || slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
    }
    return '';
  }

  return { PRICE_RE, PLACEHOLDER_RE, MAX_TEXT_CHARS, MAX_HASHTAGS, normalizeText, contentReason, MIN_LEAD_MS, rowMatchesClip, clipCaptionText, clipSkipReason };
});
