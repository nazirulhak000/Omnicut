import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  findSpecNumber,
  highlightBurstLines,
  highlightTh,
  hookHighlightKeywords,
  KINETIC_KEYWORDS_TH,
  projectHighlightKeywords,
  resolveHookKeywordSource,
} from './kineticHighlight.js';

// Shared with tests/test_preview_render_parity.py, which runs the same bursts
// through scripts/subtitle/translation_service.py.
const CASES = JSON.parse(
  readFileSync(new URL('../../../tests/fixtures/sfx_highlight_parity_cases.json', import.meta.url), 'utf-8'),
);

const lines = (ls) => ls.map((l) => l.map((s) => [s.text, s.ass]));

for (const c of CASES.highlight) {
  test(`highlight parity: ${c.name}`, () => {
    const r = highlightBurstLines(c.th_lines, c.en_lines || [], { customKeywords: c.custom_keywords || null });
    assert.deepEqual({ th: lines(r.th), en: lines(r.en) }, c.expected);
  });
}

for (const c of CASES.highlight_keywords) {
  test(`custom keyword parity: ${c.name}`, () => {
    assert.deepEqual(projectHighlightKeywords(resolveHookKeywordSource(c.hook, c.product_name)), c.expected);
  });
}

const hookOverlay = (brand, model, label) => ({
  id: 'ovl_hook',
  kind: 'hook',
  tiers: [{ text: brand, look: {} }, { text: model, look: {} }, { text: label, look: {} }],
});

test('preview keywords come from the hook overlay tiers', () => {
  const overlays = [{ id: 'ovl_text', kind: 'text', tiers: [{ text: 'ไม่ใช่ Hook' }] }, hookOverlay('Anker', 'Nano 3', '')];
  assert.deepEqual(hookHighlightKeywords(overlays, 'ชื่ออื่น'), ['Anker Nano 3', 'Anker', 'Nano']);
});

test('preview keywords fall back to the product name when the banner is blank or missing', () => {
  assert.deepEqual(hookHighlightKeywords([hookOverlay('', ' ', '')], 'Logitech Wave Keys'), ['Logitech Wave Keys', 'Logitech', 'Wave', 'Keys']);
  assert.deepEqual(hookHighlightKeywords([], 'Baseus'), ['Baseus']);
  assert.deepEqual(hookHighlightKeywords(null, ''), []);
});

test('brand from the banner and a spec number in one burst: the brand is highlighted', () => {
  const customKeywords = hookHighlightKeywords([hookOverlay('Anker', 'Nano 3', '')], '');
  const r = highlightBurstLines(['Anker ชาร์จ 65W'], [], { customKeywords });
  assert.deepEqual(lines(r.th), [[['Anker', '&H00FFE600&'], [' ชาร์จ 65W', null]]]);
});

// Same table as tests/test_spec_highlight.py::test_spec_regex_*.
test('spec regex matches number + unit', () => {
  for (const [text, want] of [
    ['แบต 5000mAh อึดมาก', '5000mAh'],
    ['ชาร์จไว 65W', '65W'],
    ['จอ 120 Hz ลื่น', '120 Hz'],
    ['ใช้ได้ 30 ชั่วโมง', '30 ชั่วโมง'],
    ['เล่นได้ 8 ชม. เต็ม', '8 ชม.'],
    ['ความจุ 1.5 TB', '1.5 TB'],
    ['หน้าจอ 6.7 นิ้ว', '6.7 นิ้ว'],
    ['ดีเลย์ 40ms', '40ms'],
  ]) {
    assert.equal(findSpecNumber(text), want, text);
  }
});

test('spec regex ignores prices, model numbers, words, years and percentages', () => {
  for (const text of ['ราคา 199 บาท', 'USB3 ก็ได้', '10 Watts', 'ปี 2026', 'ลดไป 20%']) {
    assert.equal(findSpecNumber(text), null, text);
  }
});

test('a colour hint recolours the spec tier', () => {
  const segs = highlightTh('แบต 5000mAh', { colorHint: '&H0000E6FF&' });
  assert.deepEqual(segs.find((s) => s.ass), { text: '5000mAh', ass: '&H0000E6FF&' });
});

test('dictionary has the English tech terms, not Thai transliterations', () => {
  const all = Object.values(KINETIC_KEYWORDS_TH).flat();
  assert.ok(!all.includes('บลูทูธ') && !all.includes('ฟาสชาร์จ'));
  assert.ok(all.includes('Bluetooth') && all.includes('Fast Charge'));
});

test('a burst keeps one highlight across its wrapped lines', () => {
  const r = highlightBurstLines(['ปวดหลัง', 'ปวดคอ'], []);
  assert.equal(r.th.flat().filter((s) => s.ass).length, 1);
});
