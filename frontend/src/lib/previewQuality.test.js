import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  MASTER_PREVIEW, SMOOTH_PREVIEW, PREVIEW_QUALITY_STORAGE_KEY,
  normalizePreviewQuality, readPreviewQuality, writePreviewQuality,
  previewBackingScale, previewPlaybackUrl, cutoutPlaybackSource, previewSurfaceBytes,
} from './previewQuality.js';

describe('device preview quality', () => {
  it('defaults to Master1080 without breaking denied storage', () => {
    assert.equal(readPreviewQuality(), MASTER_PREVIEW);
    assert.equal(readPreviewQuality({ getItem: () => { throw new Error('denied'); } }), MASTER_PREVIEW);
    assert.doesNotThrow(() => writePreviewQuality({ setItem: () => { throw new Error('denied'); } }, SMOOTH_PREVIEW));
    assert.equal(normalizePreviewQuality('unknown'), MASTER_PREVIEW);
  });
  it('remembers an explicit smooth choice independently of saved projects', () => {
    const entries = new Map();
    const storage = { getItem: (key) => entries.get(key), setItem: (key, value) => entries.set(key, value) };
    writePreviewQuality(storage, SMOOTH_PREVIEW);
    assert.equal(entries.get(PREVIEW_QUALITY_STORAGE_KEY), SMOOTH_PREVIEW);
    assert.equal(readPreviewQuality(storage), SMOOTH_PREVIEW);
    assert.equal(previewBackingScale(SMOOTH_PREVIEW), 1);
    assert.equal(previewBackingScale(MASTER_PREVIEW), 2);
  });
  it('never uses a ready proxy for Master mode', () => {
    const proxy = { url: '/proxy540.mp4', isProxy: true, status: 'ready' };
    assert.equal(previewPlaybackUrl(MASTER_PREVIEW, '/master4k.mp4', proxy), '/master4k.mp4');
    assert.equal(previewPlaybackUrl(SMOOTH_PREVIEW, '/master4k.mp4', proxy), '/proxy540.mp4');
    assert.equal(previewPlaybackUrl(SMOOTH_PREVIEW, '/master4k.mp4'), '/master4k.mp4');
  });
  it('selects Cutout master and reports missing-master fallback honestly', () => {
    const resolution = { masterVideoUrl: '/rgba1080.webm', videoUrl: '/rgba540.webm' };
    assert.deepEqual(cutoutPlaybackSource(MASTER_PREVIEW, resolution), { url: '/rgba1080.webm', source: 'master' });
    assert.deepEqual(cutoutPlaybackSource(SMOOTH_PREVIEW, resolution), { url: '/rgba540.webm', source: 'preview' });
    assert.deepEqual(cutoutPlaybackSource(MASTER_PREVIEW, { videoUrl: '/rgba540.webm' }), { url: '/rgba540.webm', source: 'preview' });
  });
  it('accounts for backing RGBA surfaces without claiming total RAM', () => {
    assert.equal(previewSurfaceBytes(MASTER_PREVIEW), 8294400);
    assert.equal(previewSurfaceBytes(SMOOTH_PREVIEW, 2), 4147200);
  });
});
