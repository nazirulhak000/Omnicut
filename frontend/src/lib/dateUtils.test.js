import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDate, getRelativeTime, formatFullDateTime } from './dateUtils.js';

test('parseDate returns null for empty or invalid values', () => {
  assert.equal(parseDate(null), null);
  assert.equal(parseDate(undefined), null);
  assert.equal(parseDate(''), null);
  assert.equal(parseDate('not-a-date'), null);
});

test('parseDate parses Date instances and numbers', () => {
  const now = new Date();
  assert.equal(parseDate(now)?.getTime(), now.getTime());
  assert.equal(parseDate(1726200000)?.getTime(), 1726200000000);
  assert.equal(parseDate(1726200000000)?.getTime(), 1726200000000);
});

test('parseDate parses ISO strings and space-separated date-time strings', () => {
  const iso = parseDate('2026-09-13T06:20:00');
  assert.notEqual(iso, null);
  assert.equal(iso?.getFullYear(), 2026);

  const space = parseDate('2026-09-13 06:20:00');
  assert.notEqual(space, null);
  assert.equal(space?.getFullYear(), 2026);
});

test('getRelativeTime returns empty string for invalid dates', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  assert.equal(getRelativeTime('', fixedNow), '');
  assert.equal(getRelativeTime(null, fixedNow), '');
});

test('getRelativeTime returns เมื่อสักครู่ for less than 60 seconds', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date(fixedNow - 30 * 1000);
  assert.equal(getRelativeTime(date, fixedNow), 'เมื่อสักครู่');
});

test('getRelativeTime returns นาทีที่แล้ว for less than 1 hour', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date(fixedNow - 15 * 60 * 1000);
  assert.equal(getRelativeTime(date, fixedNow), '15 นาทีที่แล้ว');
});

test('getRelativeTime returns ชม. ที่แล้ว for less than 24 hours', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date(fixedNow - 3 * 3600 * 1000);
  assert.equal(getRelativeTime(date, fixedNow), '3 ชม. ที่แล้ว');
});

test('getRelativeTime returns เมื่อวาน for 1 to 2 days', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date(fixedNow - 30 * 3600 * 1000);
  assert.equal(getRelativeTime(date, fixedNow), 'เมื่อวาน');
});

test('getRelativeTime returns วันที่แล้ว for 2 to 7 days', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date(fixedNow - 4 * 86400 * 1000);
  assert.equal(getRelativeTime(date, fixedNow), '4 วันที่แล้ว');
});

test('getRelativeTime returns short date for older than 7 days', () => {
  const fixedNow = new Date('2026-09-13T12:00:00Z').getTime();
  const date = new Date('2026-09-01T12:00:00Z');
  const result = getRelativeTime(date, fixedNow);
  assert.ok(result.includes('ก.ย.'));
});

test('formatFullDateTime returns empty string for invalid inputs', () => {
  assert.equal(formatFullDateTime(null), '');
  assert.equal(formatFullDateTime('invalid'), '');
});

test('formatFullDateTime returns formatted string with Thai month and hours', () => {
  const date = new Date('2026-09-13T06:20:15');
  const formatted = formatFullDateTime(date);
  assert.ok(formatted.includes('13 ก.ย. 2026'));
  assert.ok(formatted.includes('06:20:15 น.'));
});
