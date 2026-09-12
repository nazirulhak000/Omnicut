const { test } = require('node:test');
const assert = require('node:assert/strict');

// Generic mini fake DOM (dependency-free per testing_standard): supports
// compound selectors with tag / .class / [attr="v"] / [attr^="v"] /
// [attr*="v"] plus comma lists and deep querySelector(All). The <table>
// fixtures keep bespoke overrides for the thead/tbody shape selectors.
function matchCompound(node, part) {
  const tokens = part.match(/(\.[\w-]+|\[[^\]]+\]|[a-zA-Z][\w-]*)/g);
  if (!tokens) return false;
  for (const t of tokens) {
    if (t.charAt(0) === '.') {
      const cls = String(node.className || '').split(/\s+/).filter(Boolean);
      if (!cls.includes(t.slice(1))) return false;
    } else if (t.charAt(0) === '[') {
      const m = t.match(/^\[([^\]^*=]+)(\*=|\^=|=)"([^"]*)"\]$/);
      if (!m) return false;
      const val = String((node._attrs || {})[m[1]] ?? '');
      if (m[2] === '=') { if (val !== m[3]) return false; }
      else if (m[2] === '^=') { if (!val.startsWith(m[3])) return false; }
      else if (!val.includes(m[3])) return false;
    } else if ((node.tagName || '') !== t.toUpperCase()) {
      return false;
    }
  }
  return true;
}
function queryAllDeep(node, sel) {
  const out = [];
  const walk = (n) => {
    for (const c of n.children || []) {
      if (matchCompound(c, sel)) out.push(c);
      walk(c);
    }
  };
  walk(node);
  return out;
}
function el(tag, text, children = [], attrs = {}) {
  return {
    tagName: String(tag).toUpperCase(),
    textContent: text || '',
    children: children.filter(Boolean),
    className: (attrs && attrs.class) || '',
    _attrs: attrs || {},
    href: (attrs && attrs.href) || '',
    src: (attrs && attrs.src) || '',
    querySelector(sel) { return queryAllDeep(this, sel)[0] || null; },
    querySelectorAll(sel) { return queryAllDeep(this, sel); },
  };
}
function fakeDoc(table) {
  return {
    querySelectorAll(sel) {
      if (sel === 'table') return [table];
      return queryAllDeep(table, sel);
    },
  };
}
function buildTable(headerTexts, bodyRowCells) {
  // bodyRowCells: array of rows, each row = array of { text, link?, img? }
  const headCells = headerTexts.map((t) => el('TH', t));
  const headRow = { tagName: 'TR', textContent: '', children: headCells, querySelectorAll: (s) => (s === 'td, th' ? headCells : []) };
  const bodyRows = bodyRowCells.map((cells) => {
    const tds = cells.map((c) => {
      const kids = [];
      if (c.img) kids.push(el('IMG', '', [], { src: c.img }));
      if (c.link) kids.push(el('A', c.text || '', [], { href: c.link }));
      const td = el('TD', c.text || '', kids);
      return td;
    });
    const tr = el('TR', cells.map((c) => c.text || '').join(' '), tds);
    tr.querySelectorAll = (s) => (s === 'td, th' ? tds : []);
    return tr;
  });
  const thead = { tagName: 'THEAD', textContent: '', children: [headRow], querySelectorAll: () => headCells };
  const tbody = { tagName: 'TBODY', textContent: '', children: bodyRows, querySelectorAll: (s) => (s === 'tbody tr' ? bodyRows : []) };
  const table = el('TABLE', '', [thead, tbody]);
  table.querySelectorAll = (sel) => {
    if (sel === 'thead th, thead td, tr:first-child th') return headCells;
    if (sel === 'tbody tr') return bodyRows;
    return queryAllDeep(table, sel);
  };
  return table;
}

// ── Div-grid fixture mirroring the REAL Studio DOM (user-saved page):
// div[data-tt="components_RowLayout_FlexRow"] rows; numeric cells are
// div[width="100px"][data-tt^="components_RowLayout_FlexRow_"] in column
// order; header cells are span[data-tt="components_PostTableHeader_TUXText"].
function buildDivGrid(headerLabels, rows) {
  const headerRow = el('DIV', headerLabels.join(' '),
    headerLabels.map((t) => el('SPAN', t, [], { 'data-tt': 'components_PostTableHeader_TUXText' })),
    { 'data-tt': 'components_RowLayout_FlexRow' });
  const numericOrder = headerLabels
    .map((t) => parser.headerKind(t))
    .filter((k) => ['views', 'likes', 'comments', 'shares'].includes(k));
  const dataRows = rows.map((r) => {
    const kids = [];
    const contentKids = [];
    if (r.duration) contentKids.push(el('SPAN', r.duration, [], { 'data-tt': 'VideoCover_index_TUXText' }));
    if (r.img) contentKids.push(el('IMG', '', [], { 'data-tt': 'VideoCover_index_Image', src: r.img }));
    contentKids.push(el('A', r.title, [], { 'data-tt': 'components_PostInfoCell_a', href: r.href }));
    if (r.date) contentKids.push(el('SPAN', r.date, [], { 'data-tt': 'components_PublishStageLabel_TUXText' }));
    kids.push(el('DIV', r.title, contentKids, { 'data-tt': 'components_RowLayout_FlexRow_2', width: '308px' }));
    if (r.privacy != null) {
      kids.push(el('DIV', r.privacy,
        [el('BUTTON', r.privacy,
          [el('DIV', r.privacy, [], { class: 'TUXButton-label' })],
          { 'data-tt': 'components_PrivacyCell_TUXButton' })],
        { 'data-tt': 'components_RowLayout_FlexRow_4', width: '116px' }));
    }
    numericOrder.forEach((k, idx) => {
      const v = r[k];
      if (v === undefined) return;
      kids.push(el('DIV', String(v), [el('SPAN', String(v), [], { 'data-tt': 'components_ItemRow_TUXText' })],
        { 'data-tt': 'components_RowLayout_FlexRow_' + (6 + idx), width: '100px' }));
    });
    return el('DIV', '', kids, { 'data-tt': 'components_RowLayout_FlexRow' });
  });
  return el('DIV', '', [headerRow, ...dataRows]);
}
function gridDoc(root) {
  return { querySelectorAll: (sel) => queryAllDeep(root, sel) };
}

const parser = require('./stats_parser.js');

test('header lookup finds Thai columns regardless of order', () => {
  const table = buildTable(['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ถูกใจ', 'ความคิดเห็น', 'การดำเนินการ'], []);
  const found = parser.locatePostsTable(fakeDoc(table));
  assert.ok(found);
  assert.equal(found.colIndex.views, 2);
  assert.equal(found.colIndex.likes, 3);
  assert.equal(found.colIndex.comments, 4);
});

test('missing views table returns a Thai action error, not empty silence', () => {
  const table = buildTable(['ชื่อ', 'ราคา', 'สต็อก'], []);
  const res = parser.parsePostsTable(fakeDoc(table));
  assert.equal(res.rows.length, 0);
  assert.match(res.error, /โพสต์/);
});

test('row parses counts, duration, video id and thumbnail', () => {
  const table = buildTable(
    ['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ถูกใจ', 'ความคิดเห็น'],
    [[
      { text: 'สเปกเทพ Logitech Lift 00:26 11 ก.ย. 7:00 PM', link: 'https://www.tiktok.com/@rizanntry/video/7684239800701816081', img: 'https://thumb/x.jpg' },
      { text: 'ทุกคน' },
      { text: '51' },
      { text: '3' },
      { text: '0' },
    ]],
  );
  const res = parser.parsePostsTable(fakeDoc(table));
  assert.equal(res.error, null);
  assert.equal(res.rows.length, 1);
  const r = res.rows[0];
  assert.equal(r.views, 51);
  assert.equal(r.likes, 3);
  assert.equal(r.comments, 0);
  assert.equal(r.duration_sec, 26);
  assert.equal(r.video_id, '7684239800701816081');
  assert.equal(r.thumbnail, 'https://thumb/x.jpg');
});

test('counts accept K/M suffixes, commas and dashes', () => {
  assert.equal(parser.parseCount('268'), 268);
  assert.equal(parser.parseCount('1,239'), 1239);
  assert.equal(parser.parseCount('12.5K'), 12500);
  assert.equal(parser.parseCount('2.3M'), 2300000);
  assert.equal(parser.parseCount('-'), null);
  assert.equal(parser.parseCount('—'), null);
});

test('video id extraction only accepts real /video/ links', () => {
  assert.equal(parser.videoIdFromUrl('https://www.tiktok.com/@u/video/1234567890123456789'), '1234567890123456789');
  assert.equal(parser.videoIdFromUrl('https://www.tiktok.com/upload'), null);
  assert.equal(parser.videoIdFromUrl(''), null);
});

test('views header accepts both "ยอดการดู" (real DOM wording) and "ยอดวิว"', () => {
  // Exact header row from the live tiktok.com/tiktokstudio/content page.
  const table = buildTable(
    ['เนื้อหา (สถานะ)', 'ความเป็นส่วนตัว', 'ยอดวิว', 'ถูกใจ', 'ความคิดเห็น', 'การอ้างอิงการซื้อ'],
    [[
      { text: 'แท็กติดตัวไว้ ESSEAGER ครอบจักรแม่เหล็กเหนียวดึงสุด 00:25 11 ส.ค. 9:30 PM', link: 'https://www.tiktok.com/@u/video/7684239800701816081' },
      { text: 'ทุกคน' },
      { text: '2' },
      { text: '1' },
      { text: '0' },
      { text: '-' },
    ]],
  );
  const found = parser.locatePostsTable(fakeDoc(table));
  assert.ok(found, 'posts table must be located by the real Thai header row');
  assert.equal(found.colIndex.views, 2);
  const res = parser.parsePostsTable(fakeDoc(table));
  assert.equal(res.error, null);
  assert.equal(res.rows.length, 1);
  assert.equal(res.rows[0].views, 2);
  assert.equal(res.rows[0].likes, 1);
  assert.equal(res.rows[0].comments, 0);
  assert.equal(res.rows[0].title, 'แท็กติดตัวไว้ ESSEAGER ครอบจักรแม่เหล็กเหนียวดึงสุด');
});

test('title cleanup strips duration + Thai abbreviated dates incl. ส.ค./เม.ย. (old regex missed them)', () => {
  assert.equal(parser.cleanTitle('หนมชูชั้น BlueWow X110 Ultra 27W บางเฉียบ 00:29 10 ส.ค. 7:00 PM'), 'หนมชูชั้น BlueWow X110 Ultra 27W บางเฉียบ');
  assert.equal(parser.cleanTitle('คีย์บอร์ด Logitech Wave Keys 00:24 10 เม.ย. 12:30 PM'), 'คีย์บอร์ด Logitech Wave Keys');
  assert.equal(parser.cleanTitle('สเปกเทพ Logitech Lift 00:26 11 ก.ย. 7:00 PM'), 'สเปกเทพ Logitech Lift');
  assert.equal(parser.cleanTitle('สเปกเทพ Logitech Lift 00:26 11 ก.ย. 7:00'), 'สเปกเทพ Logitech Lift');
  assert.equal(parser.cleanTitle('คลิปจบ 01:05'), 'คลิปจบ');
  assert.equal(parser.cleanTitle(''), '');
  // "27W"/"X110" model names must survive: no colon, so never treated as time.
  assert.equal(parser.cleanTitle('แอมป์ 27W รุ่น X110 12:30 2 ส.ค. 8:00 PM'), 'แอมป์ 27W รุ่น X110');
});

test('real Studio div-grid (no <table>) parses full rows via data-tt components', () => {
  const grid = buildDivGrid(
    ['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ถูกใจ', 'ความคิดเห็น'],
    [
      { title: 'แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก', href: '/@rizanntry/video/7684239800701816081', duration: '00:25', date: '11 ก.ย. 9:30 PM', privacy: 'ทุกคน', img: 'https://thumb/a.webp', views: 2, likes: 1, comments: 0 },
      { title: 'อปเดตเวอร์ชั่นใหม่จากโลจิเทค Logitech Lift เมาส์ไร้เสียงคลิก', href: 'https://www.tiktok.com/@rizanntry/video/7684123456789012345', duration: '00:26', date: '11 ก.ย. 7:00 PM', privacy: 'ทุกคน', views: 51, likes: 3, comments: 0 },
    ],
  );
  const res = parser.parsePostsTable(gridDoc(grid));
  assert.equal(res.error, null);
  assert.equal(res.rows.length, 2);
  const r0 = res.rows[0];
  assert.equal(r0.views, 2);
  assert.equal(r0.likes, 1);
  assert.equal(r0.comments, 0);
  assert.equal(r0.duration_sec, 25);
  assert.equal(r0.video_id, '7684239800701816081');
  assert.equal(r0.video_url, 'https://www.tiktok.com/@rizanntry/video/7684239800701816081');
  assert.equal(r0.privacy, 'ทุกคน');
  assert.equal(r0.posted_text, '11 ก.ย. 9:30 PM');
  assert.equal(r0.thumbnail, 'https://thumb/a.webp');
  assert.ok(r0.title.includes('ESSAGER'));
  assert.equal(res.rows[1].views, 51);
  assert.equal(res.rows[1].duration_sec, 26);
});

test('div-grid maps number columns by header order, not fixed index', () => {
  const grid = buildDivGrid(
    ['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ความคิดเห็น', 'ถูกใจ'],
    [{ title: 'สลับคอลัมน์ถูกใจคอมเมนต์', href: '/@u/video/7684000000000000001', views: 10, likes: 30, comments: 20 }],
  );
  const res = parser.parsePostsTable(gridDoc(grid));
  assert.equal(res.error, null);
  assert.equal(res.rows[0].views, 10);
  assert.equal(res.rows[0].comments, 20);
  assert.equal(res.rows[0].likes, 30);
});

test('div-grid with header but zero rendered rows asks the user to scroll (virtual list)', () => {
  const grid = buildDivGrid(['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ถูกใจ', 'ความคิดเห็น'], []);
  const res = parser.parsePostsTable(gridDoc(grid));
  assert.equal(res.rows.length, 0);
  assert.match(res.error, /เลื่อน/);
});

test('div-grid duplicate rows (overlay copies) are deduped by video id', () => {
  const row = { title: 'คลิปซ้ำ', href: '/@u/video/7684000000000000009', views: 5, likes: 1, comments: 0 };
  const grid = buildDivGrid(
    ['เนื้อหา (สร้างเมื่อ)', 'ความเป็นส่วนตัว', 'ยอดการดู', 'ถูกใจ', 'ความคิดเห็น'],
    [row, { ...row }],
  );
  const res = parser.parsePostsTable(gridDoc(grid));
  assert.equal(res.rows.length, 1);
  assert.equal(res.rows[0].views, 5);
});
