// "Check against TikTok": what became of each draft the queue believes is still on TikTok. Pure, so it is unit-testable;
// the worker only collects the two lists (Drafts tab, Studio > Content) and the panel acts on the verdicts.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniDraftSync = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const DAY_MS = 24 * 60 * 60 * 1000;
  const DRAFT_LIFETIME_DAYS = 60;          // TikTok deletes a draft after 60 days: nothing older can matter
  const SAFETY_MARGIN_MS = DAY_MS;         // look back one day further than the oldest draft was saved
  const OLDER_ROWS_TO_STOP = 5;            // consecutive Content rows older than the cutoff (a pinned old video is not the end of the list)
  const BLOCKING_STATES = new Set(['deleted', 'posted_outside', 'duplicate_risk']);

  // How far back Studio > Content has to be read: from the oldest unresolved draft's save time (a post made from that draft cannot be
  // older), never beyond a draft's 60-day lifetime. Unknown save time = the whole lifetime.
  function lookbackCutoff(drafts, now = Date.now()) {
    const floor = now - DRAFT_LIFETIME_DAYS * DAY_MS;
    const saved = (drafts || []).map((d) => Number(d.savedAtMs)).filter((t) => Number.isFinite(t) && t > 0);
    if (!saved.length || saved.length < (drafts || []).length) return floor;     // one unknown save time -> the safe, full window
    return Math.max(floor, Math.min(...saved) - SAFETY_MARGIN_MS);
  }

  // present: the caption is still listed on TikTok's Drafts tab; match: a Content row (scheduled or posted) carries the same caption;
  // complete: the Content scan reached the cutoff / the end (not stopped by its row cap), so "no match" really means none.
  function classifyDraft({ present, match, complete, draftComplete = true }) {
    if (!present && !draftComplete) return {state:'unknown',label:'อ่านรายการ Drafts ไม่ครบ — ยังสรุปว่าแบบร่างหายไม่ได้'};
    if (present && !match) return { state: 'ok', label: 'แบบร่างยังอยู่บน TikTok' };
    if (present && match) return { state: 'duplicate_risk', label: 'มีแถวคำบรรยายเดียวกันใน Content แล้ว — เสี่ยงโพสต์ซ้ำ' };
    if (!present && match) return { state: 'posted_outside', label: 'แบบร่างหายไปและมีโพสต์เดียวกันใน Content — โพสต์เองบน TikTok?' };
    if (complete) return { state: 'deleted', label: 'แบบร่างไม่อยู่บน TikTok แล้ว (ถูกลบ?)' };
    return { state: 'unknown', label: 'ไม่พบแบบร่างและยังตรวจ Content ไม่ครบ — ตรวจเองบน TikTok' };
  }

  const isBlocking = (state) => BLOCKING_STATES.has(state);

  // A successful transport is not a successful scan: every requested id needs exactly one known verdict.
  function validateResults(drafts, reply) {
    const ids = new Set(drafts.map((d) => d.id));
    const rows = reply?.results;
    const valid = reply?.success === true && Array.isArray(rows) && rows.length === ids.size
      && ids.size === drafts.length && rows.every((r) => r && ids.has(r.id)
        && ['ok', 'deleted', 'posted_outside', 'duplicate_risk', 'unknown'].includes(r.state))
      && new Set(rows.map((r) => r.id)).size === ids.size;
    if (!valid) {
      const results = drafts.map((d) => ({ id: d.id, state: 'unknown', label: 'ตรวจแบบร่างไม่ครบ — กรุณาตรวจใหม่ก่อนเริ่มรัน' }));
      return { ok: false, error: 'draft_sync_incomplete', results, problems: results };
    }
    return { ...summarize(rows), results: rows };
  }

  function summarize(results) {
    const counts = {};
    for (const r of results || []) counts[r.state] = (counts[r.state] || 0) + 1;
    const problems = (results || []).filter((r) => r.state !== 'ok');
    return { counts, problems, ok: problems.length === 0 };
  }

  return { DAY_MS, DRAFT_LIFETIME_DAYS, OLDER_ROWS_TO_STOP, lookbackCutoff, classifyDraft, isBlocking, summarize, validateResults };
});
