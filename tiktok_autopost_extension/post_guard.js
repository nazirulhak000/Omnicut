// Shared guards for unattended posting. Loaded by the service worker (importScripts), the side panel
// (<script>) and the Node conductor (require) -- one source of truth for what may be posted and how
// a finished post is recognised on TikTok Studio > Content.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniPostGuard = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  // Channel rule: never publish price / discount text (breaks TikTok rules).
  const PRICE_RE = /฿|\bTHB\b|\d[\d,]*\s*บาท|ราคา|ลดราคา|ส่วนลด|ลด\s*\d+\s*%|\d+\s*%\s*off|\$\s*\d/i;
  // A template placeholder that was never filled in, e.g. {product_name}.
  const PLACEHOLDER_RE = /\{[a-z][a-z0-9_]*\}/i;
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
    if (PLACEHOLDER_RE.test(`${caption} ${hashtags}`)) return 'placeholder_in_caption';
    if (!allowPriceCaption && PRICE_RE.test(`${caption} ${hashtags}`)) return 'price_in_caption';
    // a clip without a publish time in a scheduled run would be posted LIVE (the worker skips the schedule step)
    if (requireSchedule && !(clip.schedule_date && clip.schedule_time)) return 'no_schedule';
    if (!ignoreSlot && clip.schedule_date && clip.schedule_time) {
      const slot = new Date(`${clip.schedule_date}T${clip.schedule_time}:00`).getTime();
      if (!Number.isFinite(slot) || slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
    }
    return '';
  }

  return { PRICE_RE, PLACEHOLDER_RE, MIN_LEAD_MS, rowMatchesClip, clipCaptionText, clipSkipReason };
});
