// OmniCut TikTok Studio stats parser — reads the Creator-Center/Studio
// "Posts" table (the table in the user's screenshot) from a live DOM and
// returns plain rows the backend can import. Pure + dependency-free so the
// same file runs in the real sidepanel AND in Node regression tests.
//
// Tolerant by design: columns are located by header text (Thai), never by
// fixed index, so a TikTok DOM reshuffle degrades to "unmatched column"
// instead of silently shifting numbers into the wrong fields.
(function attachStatsParser(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.OmniCutStatsParser = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  const HEADER_ALIASES = {
    title: ['เนื้อหา', 'content', 'video', 'โพสต์'],
    privacy: ['ความเป็นส่วนตัว', 'privacy'],
    views: ['ยอดวิว', 'ยอดการดู', 'ยอดดู', 'views', 'view'],
    likes: ['ถูกใจ', 'likes', 'like'],
    comments: ['ความคิดเห็น', 'comments', 'comment'],
    shares: ['แชร์', 'การแชร์', 'shares', 'share'],
  };

  function norm(s) {
    return String(s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  function headerKind(text) {
    const t = norm(text);
    if (!t) return null;
    for (const [kind, aliases] of Object.entries(HEADER_ALIASES)) {
      if (aliases.some((a) => t.includes(norm(a)))) return kind;
    }
    return null;
  }

  function parseCount(raw) {
    if (raw == null) return null;
    let s = String(raw).trim().replace(/,/g, '');
    if (!s || s === '-' || s === '—') return null;
    const m = s.match(/^([\d.]+)\s*([KMBก-ฮ]?)/i);
    if (!m) return null;
    let n = parseFloat(m[1]);
    if (Number.isNaN(n)) return null;
    const suffix = (m[2] || '').toUpperCase();
    if (suffix === 'K') n *= 1000;
    else if (suffix === 'M' || suffix === 'B') n *= 1000000;
    return Math.round(n);
  }

  function parseDuration(raw) {
    const m = String(raw || '').match(/(\d{1,3}):(\d{2})/);
    if (!m) return null;
    return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
  }

  function videoIdFromUrl(url) {
    const m = String(url || '').match(/\/video\/(\d{10,25})/);
    return m ? m[1] : null;
  }

  // Studio title cells end with "00:25 11 ส.ค. 9:30 PM" (duration + day +
  // Thai abbreviated month + clock). Month abbreviations may start with any
  // Thai letter incl. leading vowels ("เม.ย.", "มี.ค."), so the token class is
  // [ก-๙] -- the old [ก-ฮ]-only pattern silently left "ส.ค." fragments inside
  // the title and polluted clip matching.
  function cleanTitle(raw) {
    let s = String(raw || '').replace(/\s+/g, ' ').trim();
    // Full suffix: "<duration> <day> <thai-month> <clock> <AM|PM>"
    s = s.replace(/\s*\d{1,3}:\d{2}\s+\d{1,2}\s+[ก-๙][^\s]*\s+\d{1,2}:\d{2}(?:\s*(?:AM|PM))?$/i, '');
    // Date + clock only (layouts that skip the duration)
    s = s.replace(/\s*\d{1,2}\s+[ก-๙][^\s]*\s+\d{1,2}:\d{2}(?:\s*(?:AM|PM))?$/i, '');
    // Trailing duration only
    s = s.replace(/\s*\d{1,3}:\d{2}$/, '');
    return s.trim().slice(0, 200);
  }

  // Locate the posts table: the table whose header row mentions views/likes
  // in any supported language. Returns { table, colIndex } or null.
  function locatePostsTable(doc) {
    const tables = Array.from(doc.querySelectorAll('table'));
    for (const table of tables) {
      const headers = Array.from(table.querySelectorAll('thead th, thead td, tr:first-child th'));
      if (!headers.length) continue;
      const kinds = headers.map((h) => headerKind(h.textContent));
      if (kinds.includes('views') && (kinds.includes('likes') || kinds.includes('comments'))) {
        const colIndex = {};
        kinds.forEach((k, i) => { if (k && !(k in colIndex)) colIndex[k] = i; });
        return { table, colIndex };
      }
    }
    return null;
  }

  function parsePostsTable(doc) {
    const found = locatePostsTable(doc);
    if (!found) return { rows: [], error: 'ไม่พบตารางโพสต์ในหน้านี้ — เปิดหน้า TikTok Studio แท็บ โพสต์ ก่อนกดซิงก์' };
    const { table, colIndex } = found;
    const bodyRows = Array.from(table.querySelectorAll('tbody tr'));
    const rows = [];
    for (const tr of bodyRows) {
      const cells = Array.from(tr.querySelectorAll('td, th'));
      if (!cells.length) continue;
      const cellText = (kind) => {
        const i = colIndex[kind];
        return i == null || !cells[i] ? '' : cells[i].textContent.trim();
      };
      const titleCell = colIndex.title != null ? cells[colIndex.title] : cells[0];
      const link = titleCell ? titleCell.querySelector('a[href*="/video/"]') : null;
      const url = link ? link.href : null;
      const title = cleanTitle(titleCell ? titleCell.textContent : '');
      if (!title && !url) continue;
      const thumb = titleCell ? titleCell.querySelector('img') : null;
      rows.push({
        title,
        posted_text: cellText('title'),
        privacy: cellText('privacy'),
        views: parseCount(cellText('views')),
        likes: parseCount(cellText('likes')),
        comments: parseCount(cellText('comments')),
        shares: 'shares' in colIndex ? parseCount(cellText('shares')) : null,
        duration_sec: parseDuration(titleCell ? titleCell.textContent : ''),
        thumbnail: thumb ? thumb.src : null,
        video_url: url,
        video_id: videoIdFromUrl(url),
      });
    }
    return { rows, error: null };
  }

  return { headerKind, parseCount, parseDuration, cleanTitle, videoIdFromUrl, locatePostsTable, parsePostsTable, HEADER_ALIASES };
});