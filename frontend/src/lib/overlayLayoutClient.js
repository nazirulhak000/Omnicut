import { fetchOverlayLayout } from '../api.js';

const layoutCache = new Map();
const pendingRequests = new Map();
const debounceTimers = new Map();

/**
 * Builds a unique cache key based on text, font, size, and anchor metrics.
 */
export function getLayoutCacheKey({ text, fontName, fontSizePx, normX = 0.5, normY = 0.5 }) {
  return `${text || ''}|${fontName || 'Kanit'}|${fontSizePx || 75}|${normX}|${normY}`;
}

/**
 * Returns cached layout synchronously if available.
 */
export function getCachedOverlayLayout(params) {
  const key = getLayoutCacheKey(params);
  return layoutCache.get(key) || null;
}

/**
 * Requests layout from the backend with debouncing and caching.
 * @param {Object} params - Layout request parameters.
 * @param {Function} onResolved - Callback invoked when layout is ready.
 * @param {number} delayMs - Debounce delay in ms (default 120ms).
 */
export function requestOverlayLayout(params, onResolved, delayMs = 120) {
  if (!params || !params.text) return null;
  const key = getLayoutCacheKey(params);

  if (layoutCache.has(key)) {
    const cached = layoutCache.get(key);
    if (onResolved) onResolved(cached);
    return cached;
  }

  if (debounceTimers.has(key)) {
    clearTimeout(debounceTimers.get(key));
  }

  const timer = setTimeout(async () => {
    debounceTimers.delete(key);
    if (pendingRequests.has(key)) return;

    try {
      const promise = fetchOverlayLayout({
        text: params.text || '',
        font_name: params.fontName || 'Kanit',
        font_size_px: params.fontSizePx || 75,
        norm_x: params.normX ?? 0.5,
        norm_y: params.normY ?? 0.5,
        video_w: 1080,
        video_h: 1920,
      });
      pendingRequests.set(key, promise);
      const data = await promise;
      layoutCache.set(key, data);
      pendingRequests.delete(key);
      if (onResolved) onResolved(data);
    } catch (err) {
      pendingRequests.delete(key);
      console.warn('Failed to fetch overlay layout:', err);
    }
  }, delayMs);

  debounceTimers.set(key, timer);
  return null;
}

export function clearOverlayLayoutCache() {
  layoutCache.clear();
  pendingRequests.clear();
  for (const timer of debounceTimers.values()) {
    clearTimeout(timer);
  }
  debounceTimers.clear();
}
