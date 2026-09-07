import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyCoverResult, getCoverVariant } from './coverVariant.js';

test('prefers the 3:4 crop while retaining the 9:16 fallback', () => {
  const item = {
    cover_url: '/api/media/clip_cover.jpg',
    cover_path: '05_Covers_Thumbnails/clip_cover.jpg',
  };
  const updated = applyCoverResult(item, {
    media_url: '/api/media/clip_cover.jpg',
    cover_path: '05_Covers_Thumbnails/clip_cover.jpg',
    media_url_3x4: '/api/media/clip_cover_3x4.jpg',
    cover_3x4_path: '05_Covers_Thumbnails/clip_cover_3x4.jpg',
  });

  assert.deepEqual(getCoverVariant(updated), {
    url: '/api/media/clip_cover_3x4.jpg',
    path: '05_Covers_Thumbnails/clip_cover_3x4.jpg',
  });
  assert.equal(updated.cover_9x16_path, '05_Covers_Thumbnails/clip_cover.jpg');
});

test('falls back to the existing cover when a 3:4 crop is unavailable', () => {
  assert.deepEqual(getCoverVariant({
    cover_url: '/api/media/legacy_cover.jpg',
    cover_path: '05_Covers_Thumbnails/legacy_cover.jpg',
  }), {
    url: '/api/media/legacy_cover.jpg',
    path: '05_Covers_Thumbnails/legacy_cover.jpg',
  });
});

test('derives a media URL when a saved 3:4 path has no URL field', () => {
  assert.deepEqual(getCoverVariant({
    cover_3x4_path: '05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg',
  }), {
    url: '/api/media/05_Covers_Thumbnails/Logitech%20Wave%20Keys_cover_3x4.jpg',
    path: '05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg',
  });
});

test('keeps a path-only saved cover visible after applying an editor result', () => {
  const updated = applyCoverResult({}, {
    cover_3x4_path: '05_Covers_Thumbnails/edited_cover_3x4.jpg',
  });

  assert.equal(updated.cover_url, '/api/media/05_Covers_Thumbnails/edited_cover_3x4.jpg');
  assert.equal(updated.cover_path, '05_Covers_Thumbnails/edited_cover_3x4.jpg');
});
