import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toMediaUrl } from './mediaUrl.js';

test('media URLs stay relative and do not carry an API key by default', () => {
  assert.equal(
    toMediaUrl('01_Raw/สินค้า ทดลอง/clip one.mp4'),
    '/api/media/01_Raw/%E0%B8%AA%E0%B8%B4%E0%B8%99%E0%B8%84%E0%B9%89%E0%B8%B2%20%E0%B8%97%E0%B8%94%E0%B8%A5%E0%B8%AD%E0%B8%87/clip%20one.mp4',
  );
  assert.equal(toMediaUrl('/api/media/04_Exports/clip.mp4'), '/api/media/04_Exports/clip.mp4?channel=main');
});

test('external media URLs are not rewritten through the local API', () => {
  assert.equal(toMediaUrl('https://cdn.example.test/cover.jpg'), 'https://cdn.example.test/cover.jpg');
});

test('legacy and absolute native media still carry explicit scope in strict mode', () => {
  assert.equal(toMediaUrl('/api/media/legacy.mp4', 'main'), '/api/media/legacy.mp4?channel=main');
  assert.equal(toMediaUrl('06_Archive/Posted/clip.mp4', 'main'), '/api/media/06_Archive/Posted/clip.mp4?channel=main');
  assert.equal(toMediaUrl('C:/CapCutDrafts/clip.mp4', 'second'), '/api/media/C%3A/CapCutDrafts/clip.mp4?channel=second');
});

test('absolute same-origin generated media carries scope and rejects a foreign carrier', () => {
  const original = globalThis.location;
  try {
    globalThis.location = { origin: 'https://studio.example.test' };
    assert.equal(toMediaUrl('https://studio.example.test/api/media/04_Exports/clip.mp4#t=1', 'second'),
      'https://studio.example.test/api/media/04_Exports/clip.mp4?channel=second#t=1');
    assert.throws(() => toMediaUrl('https://studio.example.test/api/media/04_Exports/clip.mp4?channel=main', 'second'), /channel_scope_conflict/);
    assert.equal(toMediaUrl('https://cdn.example.test/cover.jpg', 'second'), 'https://cdn.example.test/cover.jpg');
  } finally {
    if (original === undefined) delete globalThis.location;
    else globalThis.location = original;
  }
});
