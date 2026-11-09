const { test } = require('node:test');
const assert = require('node:assert/strict');
const { PRICE_RE, rowMatchesClip, clipSkipReason, clipCaptionText } = require('./post_guard.js');

const NOW = new Date('2026-11-09T12:00:00').getTime();
const clip = (over = {}) => ({ export_id: 'e1', tiktok_caption: 'พัดลมพกพาเย็นจัด พิกัดในตะกร้า', schedule_date: '2026-11-10', schedule_time: '07:00', ...over });

test('price / discount wording is blocked, ordinary copy is not', () => {
  for (const bad of ['ลด 50% วันนี้', 'ราคาถูกมาก', '199 บาท', '฿199', 'SALE 30% off', 'ส่วนลดพิเศษ', 'ลดราคา']) assert.ok(PRICE_RE.test(bad), bad);
  for (const ok of ['พัดลมพกพาเย็นจัด พิกัดในตะกร้า', 'รีวิวใช้จริง 3 เดือน', 'ชาร์จเร็ว 30W']) assert.ok(!PRICE_RE.test(ok), ok);
});

test('clipSkipReason: export problems, price caption, passed slot; and ok', () => {
  const rec = { export_id: 'e1' };
  assert.equal(clipSkipReason(clip(), rec, NOW), '');
  assert.equal(clipSkipReason(clip(), undefined, NOW), 'export_missing');
  assert.equal(clipSkipReason(clip(), undefined, NOW, { exportsKnown: false }), '');
  assert.equal(clipSkipReason(clip(), { is_posted: true }, NOW), 'export_already_posted');
  assert.equal(clipSkipReason(clip(), { export_status: 'posted' }, NOW), 'export_already_posted');
  assert.equal(clipSkipReason(clip(), { is_qc_rejected: true }, NOW), 'export_qc_rejected');
  assert.equal(clipSkipReason(clip({ tiktok_caption: 'ลดราคาวันนี้' }), rec, NOW), 'price_in_caption');
  assert.equal(clipSkipReason(clip({ tiktok_hashtags: '#ลด50%' }), rec, NOW), 'price_in_caption');
  assert.equal(clipSkipReason(clip({ tiktok_caption: 'ลดราคาวันนี้' }), rec, NOW, { allowPriceCaption: true }), '');
  assert.equal(clipSkipReason(clip({ schedule_date: '2026-11-09', schedule_time: '12:10' }), rec, NOW), 'slot_passed_or_too_close');
  assert.equal(clipSkipReason(clip({ schedule_date: '', schedule_time: '' }), rec, NOW), '');
  assert.equal(clipSkipReason({ tiktok_caption: 'พัดลมพกพา' }, undefined, NOW), '', 'an unqueued clip without an export id is not judged by the registry');
});

test('caption text follows the same fallbacks the panel uses to type it', () => {
  assert.equal(clipCaptionText({ hook_title: 'ฮุค' }).caption, 'ฮุค');
  assert.equal(clipCaptionText({ caption: 'c', hook_title: 'h' }).caption, 'c');
  assert.equal(clipCaptionText({ tiktok_caption: 't', caption: 'c' }).caption, 't');
});

test('row matching: caption start + scheduled day/time', () => {
  const c = { caption: 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน! HOYAUP พัดลม', schedule_date: '2026-11-10', schedule_time: '07:00' };
  const nl = String.fromCharCode(10);
  const row = badge => ['00:35', 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน! HOYAUP พัดลมระบายความร้อน', badge, 'Everyone'].join(nl);
  assert.equal(rowMatchesClip(row('Nov 10, 7:00 AM (GMT+7) Bangkok'), c).ok, true);
  assert.equal(rowMatchesClip(row('Nov 10, 8:00 AM (GMT+7) Bangkok'), c).reason, 'schedule_badge_mismatch');
  assert.equal(rowMatchesClip(row('Nov 11, 7:00 AM (GMT+7) Bangkok'), c).reason, 'schedule_badge_mismatch');
  assert.equal(rowMatchesClip('00:25' + nl + 'อย่างอื่น', c).reason, 'caption_not_found');
  assert.equal(rowMatchesClip(row('Nov 10, 9:00 PM (GMT+7) Bangkok'), { ...c, schedule_time: '21:00' }).ok, true);
});
