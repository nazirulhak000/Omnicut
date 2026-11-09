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
      const hasDay = new RegExp(`(^|[^0-9])${day}([^0-9]|$)`).test(String(rowText).replace(/\d{1,2}:\d{2}/g, ' '));
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
    const { exportsKnown = true, allowPriceCaption = false } = options;
    if (exportsKnown && clip.export_id) {
      if (!exportRecord) return 'export_missing';
      if (exportRecord.is_posted || exportRecord.export_status === 'posted') return 'export_already_posted';
      if (exportRecord.is_qc_rejected) return 'export_qc_rejected';
    }
    const { caption, hashtags } = clipCaptionText(clip);
    if (!allowPriceCaption && PRICE_RE.test(`${caption} ${hashtags}`)) return 'price_in_caption';
    if (clip.schedule_date && clip.schedule_time) {
      const slot = new Date(`${clip.schedule_date}T${clip.schedule_time}:00`).getTime();
      if (!Number.isFinite(slot) || slot - now < MIN_LEAD_MS) return 'slot_passed_or_too_close';
    }
    return '';
  }

  return { PRICE_RE, MIN_LEAD_MS, rowMatchesClip, clipCaptionText, clipSkipReason };
});
