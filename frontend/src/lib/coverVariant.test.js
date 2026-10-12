import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyCoverResult, getCoverVariant, mergeCoverMetadata } from './coverVariant.js';

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
    url: '/api/media/05_Covers_Thumbnails/Logitech%20Wave%20Keys_cover_3x4.jpg?channel=main',
    path: '05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg',
  });
});

test('keeps a path-only saved cover visible after applying an editor result', () => {
  const updated = applyCoverResult({}, {
    cover_3x4_path: '05_Covers_Thumbnails/edited_cover_3x4.jpg',
  });

  assert.equal(updated.cover_url, '/api/media/05_Covers_Thumbnails/edited_cover_3x4.jpg?channel=main');
  assert.equal(updated.cover_path, '05_Covers_Thumbnails/edited_cover_3x4.jpg');
});

test('restores missing product cover fields from the matching export', () => {
  const products = [{
    id: 'product-1',
    angles: [{
      angle_id: 'unboxing',
      project_name: 'LOG01-แกะกล่องว้าว_1',
      video_url: '04_Exports/Ready_to_post/logitech_wave_keys_แกะกล่องว้าว_1.mp4',
    }],
  }];
  const merged = mergeCoverMetadata(products, {
    exports: [{
      project_name: 'LOG01-แกะกล่องว้าว_1',
      rel_path: '04_Exports/Ready_to_post/logitech_wave_keys_แกะกล่องว้าว_1.mp4',
      cover_path: '05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg',
      cover_3x4_path: '05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg',
      cover_url: '/api/media/05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg',
      cover_3x4_url: '/api/media/05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg',
    }],
  });

  assert.equal(merged[0].angles[0].cover_3x4_path, '05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg');
  assert.equal(merged[0].angles[0].cover_3x4_url, '/api/media/05_Covers_Thumbnails/LOG01-แกะกล่องว้าว_1_cover_3x4.jpg');
});

test('does not replace an explicit angle cover with export fallback data', () => {
  const merged = mergeCoverMetadata([
    { angles: [{ project_name: 'LOG01', cover_3x4_path: '05_Covers_Thumbnails/manual.jpg' }] },
  ], [{ project_name: 'LOG01', cover_3x4_path: '05_Covers_Thumbnails/export.jpg' }]);

  assert.equal(merged[0].angles[0].cover_3x4_path, '05_Covers_Thumbnails/manual.jpg');
});

test('uses export_id before project or path metadata when versions share an angle', () => {
  const merged = mergeCoverMetadata([
    { angles: [{
      angle_id: 'review',
      export_id: 'exp-new',
      project_name: 'same-project',
      video_url: '04_Exports/Ready_to_post/same-name.mp4',
    }] },
  ], [
    { export_id: 'exp-old', project_name: 'same-project', cover_3x4_path: 'old.jpg' },
    { export_id: 'exp-new', project_name: 'same-project', cover_3x4_path: 'new.jpg' },
  ]);

  assert.equal(merged[0].angles[0].cover_3x4_path, 'new.jpg');
});
