const MANUAL_SUFFIX = '_tiktok_sharp';

/**
 * True when a gallery clip already went through the TikTok sharpness pass:
 * the backend sharpened it in place right after the render
 * (`tiktok_enhanced`), or it is the copy the manual button writes
 * (`<name>_tiktok_sharp.mp4`).
 */
export function isTiktokSharp(item) {
  if (!item) return false;
  if (item.tiktok_enhanced === true) return true;
  return String(item.name || '').includes(MANUAL_SUFFIX)
    || String(item.rel_path || '').includes(MANUAL_SUFFIX);
}
