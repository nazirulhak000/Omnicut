/** Preview pixels may change; editing coordinates and the timeline never do. */
export const PREVIEW_QUALITY_STORAGE_KEY = 'omnicut.previewQuality';
export const MASTER_PREVIEW = 'master1080';
export const SMOOTH_PREVIEW = 'smooth540';

export function normalizePreviewQuality(value) {
  return value === SMOOTH_PREVIEW ? SMOOTH_PREVIEW : MASTER_PREVIEW;
}

export function readPreviewQuality(storage) {
  try { return normalizePreviewQuality((storage || globalThis.localStorage)?.getItem(PREVIEW_QUALITY_STORAGE_KEY)); }
  catch { return MASTER_PREVIEW; }
}

export function writePreviewQuality(storage, value) {
  try { (storage || globalThis.localStorage)?.setItem(PREVIEW_QUALITY_STORAGE_KEY, normalizePreviewQuality(value)); }
  catch { /* Storage disabled/private mode: keep the current in-memory setting. */ }
}

export function previewBackingScale(quality) {
  return normalizePreviewQuality(quality) === MASTER_PREVIEW ? 2 : 1;
}

export function previewPlaybackUrl(quality, masterUrl, proxyEntry) {
  return normalizePreviewQuality(quality) === MASTER_PREVIEW
    ? masterUrl : (proxyEntry?.url || masterUrl);
}

/** A masterless Cutout stays visibly labelled as preview, never as Master. */
export function cutoutPlaybackSource(quality, resolution) {
  if (normalizePreviewQuality(quality) === MASTER_PREVIEW && resolution?.masterVideoUrl) {
    return { url: resolution.masterVideoUrl, source: 'master' };
  }
  return { url: resolution?.videoUrl || null, source: 'preview' };
}

/** Raw RGBA surfaces only: excludes decoders, browser buffers, JS and GPU overhead. */
export function previewSurfaceBytes(quality, surfaceCount = 1) {
  const scale = previewBackingScale(quality);
  return 540 * 960 * scale * scale * 4 * surfaceCount;
}
