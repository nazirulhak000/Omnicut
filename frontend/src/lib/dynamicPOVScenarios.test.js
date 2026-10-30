import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getProductCategoryType,
  getCategoryDisplayName,
  getDynamicPOVScenarios,
  convertAngleToPOVDialogue
} from './dynamicPOVScenarios.js';

test('getProductCategoryType identifies product categories correctly', () => {
  assert.equal(getProductCategoryType({ product_code: 'EAR01', name: 'หูฟัง Earphone Synmax' }), 'audio');
  assert.equal(getProductCategoryType({ product_code: 'JBL01', name: 'JBL Tune 310C In-Ear' }), 'audio');
  assert.equal(getProductCategoryType({ product_code: 'HAT01', name: 'Hatari พัดลมตั้งโต๊ะ 16 นิ้ว' }), 'cooling');
  assert.equal(getProductCategoryType({ product_code: 'HOY01', name: 'HOYAUP พัดลมมือถือ' }), 'cooling');
  assert.equal(getProductCategoryType({ product_code: 'ESS02', name: 'ที่ชาร์จเร็ว Essager PD 30W' }), 'power');
  assert.equal(getProductCategoryType({ product_code: 'TOS01', name: 'ปลั๊กไฟ TOSHINO 3 ตา' }), 'power');
  assert.equal(getProductCategoryType({ product_code: 'GOC01', name: 'GoChek ไมค์ไร้สาย' }), 'microphone');
  assert.equal(getProductCategoryType({ product_code: 'LOG01', name: 'LOGITECH WAVE KEYS คีย์บอร์ด' }), 'desk_setup');
  assert.equal(getProductCategoryType({ product_code: 'LOG02', name: 'Logitech Lift เมาส์' }), 'desk_setup');
  assert.equal(getProductCategoryType({ product_code: 'MAG01', name: 'Magnetic Tripod ขาตั้งมือถือ' }), 'generic');
  assert.equal(getProductCategoryType(null), 'generic');
});

test('getCategoryDisplayName returns Thai human readable names', () => {
  assert.equal(getCategoryDisplayName('audio'), 'หูฟัง / เครื่องเสียง');
  assert.equal(getCategoryDisplayName('cooling'), 'พัดลม / ความเย็น');
  assert.equal(getCategoryDisplayName('power'), 'หัวชาร์จ / แบตเตอรี่ / ปลั๊กไฟ');
  assert.equal(getCategoryDisplayName('microphone'), 'ไมโครโฟน / สตรีมมิ่ง');
  assert.equal(getCategoryDisplayName('desk_setup'), 'อุปกรณ์โต๊ะทำงาน / เมาส์ / คีย์บอร์ด');
  assert.equal(getCategoryDisplayName('generic'), 'แกดเจ็ตและสินค้าทั่วไป');
});

test('getDynamicPOVScenarios returns 4 tailored scenarios for audio (EAR01)', () => {
  const earProduct = { product_code: 'EAR01', name: 'หูฟัง Earphone Synmax' };
  const scenarios = getDynamicPOVScenarios(earProduct);

  assert.equal(scenarios.length, 4);
  assert.ok(scenarios[0].title.includes('หูฟังไร้สาย'));
  assert.ok(scenarios[0].script.includes('Synmax'));
  assert.ok(scenarios[0].script.includes('แฟน:'));
  assert.ok(scenarios[0].script.includes('ฉัน:'));
  assert.equal(scenarios[0].id, 'audio_battery_dead');
  assert.equal(scenarios[1].id, 'audio_meeting_mic');
  assert.equal(scenarios[2].id, 'audio_gaming_lag');
  assert.equal(scenarios[3].id, 'audio_lost_backup');
});

test('getDynamicPOVScenarios returns 4 tailored scenarios for cooling (HAT01)', () => {
  const hatProduct = { product_code: 'HAT01', name: 'Hatari T16M1' };
  const scenarios = getDynamicPOVScenarios(hatProduct);

  assert.equal(scenarios.length, 4);
  assert.ok(scenarios[0].title.includes('ห้องร้อน'));
  assert.ok(scenarios[0].script.includes('Hatari'));
  assert.equal(scenarios[0].id, 'cooling_hot_room');
});

test('getDynamicPOVScenarios returns 4 tailored scenarios for power (ESS02)', () => {
  const essProduct = { product_code: 'ESS02', name: 'Essager 30W' };
  const scenarios = getDynamicPOVScenarios(essProduct);

  assert.equal(scenarios.length, 4);
  assert.ok(scenarios[0].title.includes('แบตหมด'));
  assert.ok(scenarios[0].script.includes('Essager'));
  assert.equal(scenarios[0].id, 'power_battery_2pct');
});

test('getDynamicPOVScenarios gracefully handles generic products with angles', () => {
  const genericProduct = {
    product_code: 'XYZ99',
    name: 'Gadget XYZ',
    angles: [
      {
        angle_name: 'Pain Point',
        pain_point: 'ของเดิมเปราะหักง่ายมาก',
        key_features: 'ทำจากไทเทเนียม ทนทาน 10 เท่า',
        price_deal: 'ลด 50% วันนี้'
      }
    ]
  };
  const scenarios = getDynamicPOVScenarios(genericProduct);

  assert.equal(scenarios.length, 4);
  assert.ok(scenarios[0].script.includes('ของเดิมเปราะหักง่ายมาก'));
  assert.ok(scenarios[0].script.includes('Gadget XYZ'));
  assert.ok(scenarios[0].script.includes('ไทเทเนียม'));
  // price_deal is product data only -- it never reaches the POV chat script.
  for (const s of scenarios) {
    assert.ok(!s.script.includes('ลด 50%'), s.id);
    assert.ok(!/ราคา|บาท|โปรโมชั่น|ส่วนลด|ส่งฟรี/.test(s.script), s.id);
  }
});

test('convertAngleToPOVDialogue adapts an angle into a 2-person LINE dialogue', () => {
  const angle = {
    angle_name: 'สายเกมเมอร์',
    pain_point: 'คุยงานแล้วเสียงอู้อี้ เล่นเกมดีเลย์จับทิศทางเสียงไม่ได้',
    key_features: 'ไมค์คมชัด ตัดเสียงรบกวน ดีเลย์ 0ms',
    price_deal: '159 บาท ส่งฟรี'
  };
  const dialogue = convertAngleToPOVDialogue(angle, 'หูฟัง Earphone Synmax');

  assert.ok(dialogue.includes('แฟน: "เธอออ'));
  assert.ok(dialogue.includes('เสียงอู้อี้'));
  assert.ok(dialogue.includes('ฉัน: "ใจเย็น! ในกระเป๋ามี หูฟัง Earphone Synmax'));
  assert.ok(dialogue.includes('ไมค์คมชัด'));
  // No price/promo in the clip dialogue even when the angle carries one.
  assert.ok(!dialogue.includes('159 บาท'));
  assert.ok(!dialogue.includes('ส่งฟรี'));
  assert.ok(dialogue.includes('แฟน: "เห้ยยย จริงด้วย รอดตายแล้ว ขอบคุณน้าาา 🥰"'));
});
