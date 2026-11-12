import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

// Round CLAUDE-AUTOPOST-E2E-FIXES-20261113: an unsharpened clip and a
// partly-failed production chain must never read as a clean success.
const galleryPath = path.resolve(process.cwd(), 'src/components/ExportGallery.jsx');
const taskContextPath = path.resolve(process.cwd(), 'src/context/TaskContext.jsx');

test('gallery shows why the automatic sharpness pass failed', () => {
  const source = fs.readFileSync(galleryPath, 'utf8');
  assert.match(source, /!alreadySharp && video\.tiktok_sharpen_error/);
  assert.match(source, /ยังไม่คมชัดระดับ TikTok: \{video\.tiktok_sharpen_error\}/);
});

test('a partly-failed chain toast says so instead of "เสร็จสมบูรณ์"', () => {
  const source = fs.readFileSync(taskContextPath, 'utf8');
  assert.match(source, /t\.result\?\.partial \? 'งานเสร็จบางส่วน' : 'งานเสร็จสมบูรณ์'/);
});
