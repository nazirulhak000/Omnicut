// Pure row identity and creation evidence shared by save, verify and reconciliation.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniDraftEvidence = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const norm = (s) => String(s || '').normalize('NFC').toLowerCase().replace(/[^a-z0-9\u0e00-\u0e7f]/g, '');
  function episodeOf(job) {
    const tags = [...String(job.hashtags || '').matchAll(/#EP0*(\d+)(?!\d)/gi)];
    return Number(job.episode_no || (tags.length === 1 ? tags[0][1] : 0)) || null;
  }
  function matches(raw, job) {
    const text = String(raw || '');
    const ep = episodeOf(job);
    const tags = [...text.matchAll(/#EP0*(\d+)(?!\d)/gi)].map((m) => Number(m[1]));
    if (ep && tags.length) return tags.every((n) => n === ep);
    const caption = norm(String(job.caption || '').split('#')[0]);
    // Truncated captions and a prefix spanning the rest of the page are not an identity.
    return caption.length >= 8 && text.split(/\r?\n/).some((line) => norm(line.split('#')[0]) === caption);
  }
  function evaluate(page, job, baseline = null) {
    const onDrafts = /\/tiktokstudio\/content/.test(String(page.url || '')) && /[?&]tab=draft/.test(page.url || '');
    const rows = Array.isArray(page.rows) ? page.rows : [];
    const hits = rows.filter((r) => matches(r, job));
    const unique = onDrafts && hits.length === 1;
    const fresh = baseline?.complete === true && Array.isArray(baseline.rows)
      && (!baseline.jobId || baseline.jobId === job.job_id) && (!baseline.channelId || baseline.channelId === job.channel_id)
      && !hasPriorCandidate(baseline.rows, job);
    return { url: page.url || '', onDrafts, draftCount: page.draftCount ?? null,
      rowVisible: unique, matchCount: hits.length, created: unique && fresh,
      reason: !onDrafts ? 'not_drafts' : hits.length > 1 ? 'ambiguous' : !unique ? 'row_not_found' : !fresh ? 'creation_not_proven' : 'new_unique_row' };
  }
  function hasPriorCandidate(rows, job) {
    return rows.some((raw) => {
      if (matches(raw, job)) return true;
      const tags = [...String(raw).matchAll(/#EP0*(\d+)(?!\d)/gi)].map(m => Number(m[1]));
      const ep = episodeOf(job);
      if (ep && tags.length && tags.every(n => n !== ep)) return false;
      const caption = norm(String(job.caption || '').split('#')[0]);
      return !caption || String(raw).split(/\r?\n/).some(line => {
        const key = norm(line.split('#')[0]);
        return key.length >= 8 && caption.startsWith(key);
      });
    });
  }
  return { matches, evaluate, episodeOf, hasPriorCandidate };
});
