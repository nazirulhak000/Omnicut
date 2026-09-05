import test from 'node:test';
import assert from 'node:assert/strict';
import { formatAppError, DEFAULT_ERROR_SUGGESTIONS } from './errorMapping.js';

test('formatAppError handles null and string errors gracefully', () => {
  const nullErr = formatAppError(null);
  assert.equal(nullErr.category, 'internal');
  assert.ok(nullErr.message.includes('ไม่ทราบสาเหตุ'));

  const strErr = formatAppError('Network connection lost');
  assert.equal(strErr.message, 'Network connection lost');
  assert.equal(strErr.category, 'internal');
});

test('formatAppError extracts structured backend fields and Thai suggestions', () => {
  const payload = {
    error: 'ไม่พบไฟล์มีเดียต้นฉบับ',
    error_category: 'user_correctable',
    error_code: 'FILE_NOT_FOUND',
    suggestion_th: 'กรุณาอัปโหลดไฟล์วิดีโอใหม่',
  };

  const formatted = formatAppError(payload);
  assert.equal(formatted.message, 'ไม่พบไฟล์มีเดียต้นฉบับ');
  assert.equal(formatted.category, 'user_correctable');
  assert.equal(formatted.code, 'FILE_NOT_FOUND');
  assert.equal(formatted.suggestion, 'กรุณาอัปโหลดไฟล์วิดีโอใหม่');
});

test('formatAppError falls back to category defaults when suggestion is omitted', () => {
  const payload = {
    error: 'FFmpeg execution timed out',
    error_category: 'ffmpeg',
    error_code: 'FFMPEG_TIMEOUT',
  };

  const formatted = formatAppError(payload);
  assert.equal(formatted.suggestion, DEFAULT_ERROR_SUGGESTIONS.ffmpeg);
});
