import test from 'node:test';
import assert from 'node:assert/strict';
import { listFieldFromText, listFieldText, listItemText, listLineCount } from './productListFields.js';

// The three shapes found in the product store.
const KEY_SPECS = [{ key: 'ความจุ', value: '30,000mAh' }, { key: 'กำลังไฟ', value: '22.5W' }];
const NAME_SPECS = [{ name: 'ความจุแบตเตอรี่', value: '5000mAh' }];
const TEXT_SPECS = ['ความถี่: 50Hz - 18 KHz', 'Bluetooth 5.3'];

test('labelled objects read as "label: value", never as [object Object]', () => {
  assert.equal(listFieldText(KEY_SPECS), 'ความจุ: 30,000mAh\nกำลังไฟ: 22.5W');
  assert.equal(listFieldText(NAME_SPECS), 'ความจุแบตเตอรี่: 5000mAh');
  assert.equal(listFieldText(TEXT_SPECS), 'ความถี่: 50Hz - 18 KHz\nBluetooth 5.3');
  assert.equal(listItemText({ label: 'น้ำหนัก', value: 180 }), 'น้ำหนัก: 180');
  assert.equal(listItemText({ value: 'ไม่มีชื่อ' }), 'ไม่มีชื่อ');
  assert.equal(listItemText({ other: 1 }), '{"other":1}');
  assert.ok(!listFieldText([...KEY_SPECS, ...NAME_SPECS]).includes('[object Object]'));
});

test('missing and single values read as empty or one line', () => {
  assert.equal(listFieldText(null), '');
  assert.equal(listFieldText(undefined), '');
  assert.equal(listFieldText([]), '');
  assert.equal(listFieldText('ข้อความเดียว'), 'ข้อความเดียว');
  assert.equal(listFieldText([' a ', '', null]), 'a');
});

test('untouched text saves the stored field itself', () => {
  for (const original of [KEY_SPECS, NAME_SPECS, TEXT_SPECS]) {
    assert.equal(listFieldFromText(listFieldText(original), original), original);
    // trailing spaces and blank lines are not an edit
    assert.equal(listFieldFromText(`\n${listFieldText(original)}  \n\n`, original), original);
  }
});

test('edited labelled objects keep their shape and label key', () => {
  assert.deepEqual(
    listFieldFromText('ความจุ: 30,000mAh\nกำลังไฟ: 15W\nสี: ดำ: ด้าน', KEY_SPECS),
    [{ key: 'ความจุ', value: '30,000mAh' }, { key: 'กำลังไฟ', value: '15W' }, { key: 'สี', value: 'ดำ: ด้าน' }],
  );
  assert.deepEqual(listFieldFromText('ความจุแบตเตอรี่: 6000mAh', NAME_SPECS),
    [{ name: 'ความจุแบตเตอรี่', value: '6000mAh' }]);
  // a line without a label still keeps the object shape readers expect
  assert.deepEqual(listFieldFromText('มีไฟฉาย', KEY_SPECS), [{ key: '', value: 'มีไฟฉาย' }]);
});

test('edited text lists stay strings, and an empty field stays a list', () => {
  assert.deepEqual(listFieldFromText('Bluetooth 5.4\nกันน้ำ IPX5', TEXT_SPECS), ['Bluetooth 5.4', 'กันน้ำ IPX5']);
  assert.deepEqual(listFieldFromText('จุดขายใหม่', []), ['จุดขายใหม่']);
  assert.deepEqual(listFieldFromText('', KEY_SPECS), []);
  assert.deepEqual(listFieldFromText('a\nb', 'ข้อความเดิม'), ['a', 'b']);
});

test('line count ignores blank lines', () => {
  assert.equal(listLineCount('a\n\n b \n'), 2);
  assert.equal(listLineCount(''), 0);
});
