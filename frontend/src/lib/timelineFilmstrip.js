/**
 * Pure helpers for the thumbnail strip drawn behind each timeline clip.
 *
 * The backend (`GET /api/editor/filmstrip`, scripts/api_editor.py) renders one
 * horizontal JPEG sprite of `count` equal tiles sampled evenly across a source
 * window. A clip asks for its own trim window, so every tile is a frame the
 * clip really plays. Requests are keyed by source + window, and the tile count
 * is bucketed so zooming does not ask the server for a new sprite per pixel:
 * a sprite with more tiles than needed is reused by picking every n-th tile.
 */

/** On-screen width of one thumbnail slot, in px (cover-cropped). */
export const FILMSTRIP_SLOT_PX = 48;
/** Never draw more slots than this on one clip, however far it is zoomed. */
export const FILMSTRIP_MAX_SLOTS = 120;
/** Tile counts the client asks for; the server clamps to 2..40. */
export const FILMSTRIP_COUNT_BUCKETS = Object.freeze([2, 4, 6, 8, 12, 16, 24, 32, 40]);
/** Trim windows are rounded to this many seconds for the cache key. */
export const FILMSTRIP_WINDOW_STEP = 0.1;

const roundTo = (value, step) => Math.round(value / step) * step;
const fixed = (value) => Number(value.toFixed(2));

/** How many thumbnail slots fit across a clip `widthPx` wide. */
export function filmstripSlotCount(widthPx, slotPx = FILMSTRIP_SLOT_PX, maxSlots = FILMSTRIP_MAX_SLOTS) {
  const width = Number(widthPx);
  if (!Number.isFinite(width) || width <= 0) return 0;
  return Math.max(1, Math.min(maxSlots, Math.round(width / slotPx)));
}

/** Smallest bucketed tile count that covers `slots` (capped at the largest bucket). */
export function filmstripRequestCount(slots) {
  const wanted = Math.max(1, Math.ceil(Number(slots) || 0));
  return FILMSTRIP_COUNT_BUCKETS.find((n) => n >= wanted) ?? FILMSTRIP_COUNT_BUCKETS.at(-1);
}

/**
 * The source window a clip shows, rounded for caching, or null when the clip
 * has no source file. `start` is null from the file's start and `end` is null
 * to the file's end (trim_end unset); the server clamps `end` to the file, so
 * the window never depends on the probed duration arriving later.
 */
export function filmstripWindow(clip) {
  const path = clip?.source_path;
  if (!path) return null;
  const rawStart = Math.max(0, Number(clip.trim_start) || 0);
  const rawEnd = clip.trim_end ?? null;
  let start = fixed(roundTo(rawStart, FILMSTRIP_WINDOW_STEP));
  let end = rawEnd === null || rawEnd === undefined || !Number.isFinite(Number(rawEnd))
    ? null
    : fixed(roundTo(Number(rawEnd), FILMSTRIP_WINDOW_STEP));
  if (end !== null && end <= start) end = fixed(start + FILMSTRIP_WINDOW_STEP);
  if (start <= 0) start = null;
  return { path, start, end };
}

/** Cache key for one source window (tile count is not part of it). */
export function filmstripKey(win) {
  if (!win) return '';
  return `${win.path}|${win.start ?? ''}|${win.end ?? ''}`;
}

/** Same query shape as api.js filmstripUrlFor(). */
export function filmstripUrl(win, count) {
  const params = new URLSearchParams({ path: win.path, count: String(count) });
  if (win.start !== null && win.start !== undefined) params.set('start', win.start.toFixed(2));
  if (win.end !== null && win.end !== undefined) params.set('end', win.end.toFixed(2));
  return `/api/editor/filmstrip?${params.toString()}`;
}

/** Which sprite tile slot `i` of `slots` shows when the sprite has `count` tiles. */
export function filmstripTileIndex(i, slots, count) {
  if (slots <= 0 || count <= 0) return 0;
  return Math.min(count - 1, Math.floor(((i + 0.5) * count) / slots));
}

/**
 * Background styles that cover-crop tile k of the sprite into each slot. The
 * sprite is `naturalWidth` x `naturalHeight` and holds `count` equal tiles
 * side by side. Returns [] when anything needed is missing.
 */
export function filmstripTileStyles({ slots, count, naturalWidth, naturalHeight, slotWidth, slotHeight }) {
  if (!(slots > 0 && count > 0 && naturalWidth > 0 && naturalHeight > 0 && slotWidth > 0 && slotHeight > 0)) {
    return [];
  }
  const tileW = naturalWidth / count;
  const scale = Math.max(slotWidth / tileW, slotHeight / naturalHeight);
  const spriteW = naturalWidth * scale;
  const spriteH = naturalHeight * scale;
  const offsetX = (tileW * scale - slotWidth) / 2;
  const offsetY = (spriteH - slotHeight) / 2;
  const px = (n) => `${Number(n.toFixed(2))}px`;
  const styles = [];
  for (let i = 0; i < slots; i++) {
    const k = filmstripTileIndex(i, slots, count);
    styles.push({
      backgroundSize: `${px(spriteW)} ${px(spriteH)}`,
      backgroundPosition: `${px(-(k * tileW * scale + offsetX))} ${px(-offsetY)}`,
    });
  }
  return styles;
}

/**
 * In-memory registry of loaded sprites, shared by every clip on the page.
 * `best(key)` is the loaded sprite with the most tiles for that window;
 * a failed URL is remembered so re-renders never retry it.
 */
export function createFilmstripCache() {
  const loaded = new Map(); // key -> { url, count, naturalWidth, naturalHeight }
  const failed = new Set(); // url
  return {
    best: (key) => loaded.get(key) || null,
    store(key, entry) {
      const prev = loaded.get(key);
      if (!prev || entry.count >= prev.count) loaded.set(key, entry);
      return loaded.get(key);
    },
    fail: (url) => { failed.add(url); },
    hasFailed: (url) => failed.has(url),
    /** True when a sprite with at least `count` tiles is not loaded yet. */
    needs(key, count) {
      const prev = loaded.get(key);
      return !prev || prev.count < count;
    },
    clear() { loaded.clear(); failed.clear(); },
  };
}
