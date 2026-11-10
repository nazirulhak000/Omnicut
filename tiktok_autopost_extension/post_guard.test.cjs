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
  assert.equal(clipSkipReason(clip({ tiktok_caption: 'ต้องมี! {product_name} ปลดปล่อยสองมือ' }), rec, NOW), 'placeholder_in_caption');
  assert.equal(clipSkipReason(clip({ tiktok_caption: 'ใช้ {product_name} ดี' }), rec, NOW, { allowPriceCaption: true }), 'placeholder_in_caption');
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

test('clipSkipReason: a draft-only run ignores the publish slot, nothing else', () => {
  const NOW2 = Date.parse('2026-11-10T04:30:00Z');
  const rec = { id: 'exp-1' };
  const past = { export_id: 'exp-1', tiktok_caption: 'ok', schedule_date: '2026-11-09', schedule_time: '12:10' };
  assert.equal(clipSkipReason(past, rec, NOW2), 'slot_passed_or_too_close');
  assert.equal(clipSkipReason(past, rec, NOW2, { ignoreSlot: true }), '');
  // the other guards still apply to drafts: price text, missing export, placeholder
  assert.equal(clipSkipReason({ ...past, tiktok_caption: 'ลดราคาวันนี้' }, rec, NOW2, { ignoreSlot: true }), 'price_in_caption');
  assert.equal(clipSkipReason(past, undefined, NOW2, { ignoreSlot: true }), 'export_missing');
  assert.equal(clipSkipReason({ ...past, tiktok_caption: 'ใช้ {product_name}' }, rec, NOW2, { ignoreSlot: true }), 'placeholder_in_caption');
});

test('R1: a clip with no publish time is blocked in scheduled runs (it would be posted LIVE) but fine as a draft', () => {
  const NOW3 = Date.parse('2026-11-10T04:30:00Z');
  const rec = { id: 'exp-1' };
  const unscheduled = { export_id: 'exp-1', tiktok_caption: 'ใช้จริงดีมาก', tiktok_hashtags: '#a' };
  assert.equal(clipSkipReason(unscheduled, rec, NOW3, { requireSchedule: true }), 'no_schedule');
  assert.equal(clipSkipReason(unscheduled, rec, NOW3, { requireSchedule: true, ignoreSlot: true }), 'no_schedule');
  assert.equal(clipSkipReason(unscheduled, rec, NOW3, { requireSchedule: false, ignoreSlot: true }), '');
  const scheduled = { ...unscheduled, schedule_date: '2026-11-12', schedule_time: '09:00' };
  assert.equal(clipSkipReason(scheduled, rec, NOW3, { requireSchedule: true }), '');
  // only one half of a schedule is not a schedule
  assert.equal(clipSkipReason({ ...unscheduled, schedule_time: '09:00' }, rec, NOW3, { requireSchedule: true }), 'no_schedule');
  assert.equal(clipSkipReason({ ...unscheduled, schedule_date: '2026-11-12' }, rec, NOW3, { requireSchedule: true }), 'no_schedule');
});

test('R1: rowMatchesClip needs the day next to a month name; views/likes equal to the day are not a date', () => {
  const { rowMatchesClip } = require('./post_guard.js');
  const NL = String.fromCharCode(10);
  const clip = { caption: 'ใช้จริงมาแล้วสามเดือนเต็ม พัดลม', schedule_date: '2026-11-10', schedule_time: '18:00' };
  const row = (badge, ...stats) => ['00:28', 'ใช้จริงมาแล้วสามเดือนเต็ม พัดลมตัวนี้', badge, 'Everyone', ...stats].join(NL);
  assert.equal(rowMatchesClip(row('Nov 10, 6:00 PM (GMT+7) Bangkok'), clip).ok, true);
  assert.equal(rowMatchesClip(row('10 พ.ย. 6:00 PM'), clip).ok, true);
  assert.equal(rowMatchesClip(row('10 พ.ย. 18:00'), clip).ok, true);
  assert.equal(rowMatchesClip(row('Nov 11, 6:00 PM', '10', '10', '10'), clip).reason, 'schedule_badge_mismatch'); // 10 views, wrong day
  assert.equal(rowMatchesClip(row('Nov 12, 6:00 PM', '0', '10', '0'), clip).ok, false);
  assert.equal(rowMatchesClip(row('Nov 10, 9:00 AM'), clip).ok, false);   // right day, wrong time
  assert.equal(rowMatchesClip(row('Nov 100, 6:00 PM'), clip).ok, false);  // 100 is not 10
});
