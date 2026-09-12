const { test } = require('node:test');
const assert = require('node:assert/strict');

// Minimal fake DOM: enough for stats_parser (querySelectorAll on document +
// per-element textContent/querySelector). No jsdom dependency — keeps the
// extension folder dependency-free per testing_standard.
function el(tag, text, children = [], attrs = {}) {
  const node = {
    tagName: tag.toUpperCase(), textContent: text || '', children,
    href: attrs.href || '', src: attrs.src || '',
    querySelector(sel) {
      if (sel === 'a[href*="/video/"]') {
        return findDeep(this, (n) => n.tagName === 'A' && (n.href || '').includes('/video/'));
      }
      if (sel === 'img') return findDeep(this, (n) => n.tagName === 'IMG');
      return null;
    },
    querySelectorAll(sel) {
      const out = [];
      walk(this, (n) => {
        if (sel === 'td, th' && (n.tagName === 'TD' || n.tagName === 'TH')) out.push(n);
        if ((sel === 'thead th, thead td, tr:first-child th') && n.tagName === 'TH') out.push(n);
        if (sel === 'tbody tr' && n.tagName === 'TR' && n._inBody) out.push(n);
      });
      return out;
    },
  };
  return node;
}
function findDeep(node, pred) {
  if (pred(node)) return node;
  for (const c of node.children || []) { const hit = findDeep(c, pred); if (hit) return hit; }
  return null;
}
function walk(node, fn) {
  fn(node);
  for (const c of node.children || []) walk(c, fn);
}
function fakeDoc(table) {
  return {
    querySelectorAll(sel) {
      if (sel === 'table') return [table];
      return [];
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
    tr._inBody = true;
    tr.querySelectorAll = (s) => (s === 'td, th' ? tds : []);
    return tr;
  });
  const thead = { tagName: 'THEAD', textContent: '', children: [headRow], querySelectorAll: () => headCells };
  const tbody = { tagName: 'TBODY', textContent: '', children: bodyRows, querySelectorAll: (s) => (s === 'tbody tr' ? [] : bodyRows) };
  const table = el('TABLE', '', [thead, tbody]);
  table.querySelectorAll = (sel) => {
    if (sel === 'thead th, thead td, tr:first-child th') return headCells;
    if (sel === 'tbody tr') return bodyRows;
    return [];
  };
  return table;
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

test('real Thai Studio header "ยอดวิว" is recognized as the views column', () => {
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
