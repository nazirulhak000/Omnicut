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
  const LIMITS = (typeof module === 'object' && module.exports) ? require('./limits.js') : globalThis.OmniLimits;
  const MAX_TEXT_CHARS = LIMITS.MAX_TEXT_CHARS;
  const MAX_HASHTAGS = LIMITS.MAX_HASHTAGS;
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
  const MIN_LEAD_MS = LIMITS.MIN_LEAD_MS;
  const MAX_LEAD_MS = LIMITS.MAX_LEAD_MS;
  const SLOT_STEP_MINUTES = LIMITS.SLOT_STEP_MINUTES;
  const SLOT_TZ_OFFSET = LIMITS.SLOT_TZ_OFFSET;

  // Epoch ms of a slot given as Bangkok wall time (YYYY-MM-DD + HH:MM). NaN when malformed.
  // Never parsed in the PC's local zone: a PC set to another timezone would shift every slot.
  function slotMs(date, time) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date || '')) || !/^\d{2}:\d{2}$/.test(String(time || ''))) return NaN;
    return new Date(`${date}T${time}:00${SLOT_TZ_OFFSET}`).getTime();
  }

  // '' = TikTok will accept this slot at `now`, otherwise why not.
  function slotProblem(date, time, now = Date.now()) {
    const slot = slotMs(date, time);
    if (!Number.isFinite(slot)) return 'slot_invalid';
    if (Number(String(time).slice(3, 5)) % SLOT_STEP_MINUTES !== 0) return 'slot_not_on_step';
    if (slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
    if (slot - now > MAX_LEAD_MS) return 'slot_too_far';
    return '';
  }

  const alnum = text => String(text || '').toLowerCase().replace(/[^a-z0-9ก-๙]/g, '');

  // Does one Content-page row (its visible text) belong to this clip? Needs the start of the caption;
  // a scheduled clip must also show its day number and time (12h or 24h).
  // The episode number a row carries as a hashtag (#EP1731). 'match' = this clip's number, 'other' = another clip's number,
  // 'none' = no tag visible (a long caption is truncated in Studio's lists, and clips posted before EP numbers have none).
  const EP_TAG_RE = /#EP0*(\d{1,9})(?!\d)/gi;
  function episodeMatch(rowText, episodeNo) {
    const wanted = Number(episodeNo);
    if (!Number.isFinite(wanted) || wanted <= 0) return 'none';
    const found = [];
    for (const m of String(rowText || '').matchAll(EP_TAG_RE)) found.push(Number(m[1]));
    if (!found.length) return 'none';
    return found.includes(wanted) ? 'match' : 'other';
  }

  function rowMatchesClip(rowText, clip) {
    const row = alnum(rowText);
    const key = alnum(clip.caption).slice(0, 20);
    // With an EP number the tag decides when it is visible: same number = this clip (even if the caption is cut short),
    // another number = never this clip. Without a visible tag the caption key is the fallback, exactly as before.
    const episode = episodeMatch(rowText, clip.episode_no);
    if (episode === 'other') return { ok: false, reason: 'caption_not_found' };
    if (episode !== 'match' && (key.length < 8 || !row.includes(key))) return { ok: false, reason: 'caption_not_found' };
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
      const problem = slotProblem(clip.schedule_date, clip.schedule_time, now);
      if (problem) return problem === 'slot_invalid' ? 'slot_passed_or_too_close' : problem;
    }
    return '';
  }

  const captionKey = (caption) => alnum(caption).slice(0, 20);

  // Content-page linkage of a scheduled job that has gone live (B2). The same rule the backend checks: the first 40
  // characters of the caption with all whitespace removed must appear in the row, and a visible #EP tag must be this
  // clip's. Two clips of one product often share 20 characters, rarely 40.
  const LINKAGE_KEY_CHARS = 40;
  const linkageKey = (caption) => String(caption || '').normalize('NFC').replace(/\s+/g, '').slice(0, LINKAGE_KEY_CHARS);
  function linkageEpisode(job) {
    if (Number(job && job.episode_no) > 0) return Number(job.episode_no);
    const tags = [...String((job && job.hashtags) || '').matchAll(/#EP0*(\d+)(?!\d)/gi)];
    return tags.length === 1 ? Number(tags[0][1]) : null;
  }
  // rows: [{videoId, text}] read from Studio > Content. {row} when exactly one row belongs to the job, else {reason}.
  function matchLinkageRow(rows, job) {
    const key = linkageKey(job && job.caption);
    if (key.length < 12) return {reason: 'caption_too_short'};
    const episode = linkageEpisode(job);
    const hits = (rows || []).filter((row) => {
      if (!row || !/^[0-9]{8,32}$/.test(String(row.videoId || ''))) return false;
      const flat = String(row.text || '').normalize('NFC').replace(/\s+/g, '');
      if (!flat.includes(key)) return false;
      return episodeMatch(row.text, episode) !== 'other';
    });
    if (hits.length === 1) return {row: hits[0]};
    return {reason: hits.length ? 'ambiguous' : 'not_found', count: hits.length};
  }

  // After a 409 "already prepared": may the panel clear the job GET /pending returned? Only a never-claimed job of
  // THIS clip's export. /pending returns the channel's oldest job, which can belong to another clip; clearing that
  // would cancel the other clip's job and reset its queue row.
  function clearableStaleJob(pending, exportId) {
    return Boolean(pending && pending.job_id && pending.status === 'prepared' && exportId && pending.export_id === exportId);
  }

  return { episodeMatch, captionKey, clearableStaleJob, linkageKey, linkageEpisode, matchLinkageRow, PRICE_RE, PLACEHOLDER_RE, MAX_TEXT_CHARS, MAX_HASHTAGS, normalizeText, contentReason, MIN_LEAD_MS, MAX_LEAD_MS, slotMs, slotProblem, rowMatchesClip, clipCaptionText, clipSkipReason };
});
