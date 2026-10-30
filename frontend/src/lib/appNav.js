// App navigation <-> browser history.
//
// The shell used to keep the active tab only in localStorage, so the phone's
// back gesture (iOS swipe / Android back) left the app instead of returning to
// the previous screen. These helpers put the tab in `?tab=` and create real
// history entries, while every other query parameter (mode, channel, film,
// quick_post, ...) is preserved untouched.
//
// Pure helpers take explicit inputs so they run under `node --test`; the thin
// `push*/replace*` wrappers touch window.history.

export const TAB_PARAM = 'tab';
export const TAB_STORAGE_KEY = 'capcut_active_tab';
export const DEFAULT_TAB = 'flow';

export const APP_TABS = Object.freeze([
  'flow', 'tracker', 'editor', 'gallery', 'assets', 'analytics', 'settings', 'dashboard', 'guide',
]);

// Tabs that were folded into others. Old links / stored values must land on a
// screen that still renders something.
const LEGACY_TAB_MAP = Object.freeze({
  sub_srt: 'editor',
  studio: 'editor',
  script_lab: 'flow',
  creative: 'flow',
  gadget: 'flow',
  producer: 'flow',
});

/** Map any raw value (URL, storage, legacy id) to a renderable tab id, or null. */
export function normalizeTab(raw) {
  if (typeof raw !== 'string') return null;
  const value = raw.trim();
  if (!value) return null;
  const mapped = LEGACY_TAB_MAP[value] || value;
  return APP_TABS.includes(mapped) ? mapped : null;
}

/** Tab named in a query string (`?tab=gallery`), normalized, or null. */
export function readTabFromSearch(search) {
  try {
    return normalizeTab(new URLSearchParams(search || '').get(TAB_PARAM));
  } catch {
    return null;
  }
}

/** URL wins (a shared link / back-forward entry), then the stored tab, then the default. */
export function resolveInitialTab({ search = '', stored = null, fallback = DEFAULT_TAB } = {}) {
  return readTabFromSearch(search) || normalizeTab(stored) || fallback;
}

/**
 * Same URL with `?tab=` set to `tab`; all other params, path and hash kept.
 * Returns a relative URL string (path + search + hash) suitable for pushState.
 */
export function buildTabUrl(href, tab) {
  const url = new URL(href, 'http://local.invalid');
  const normalized = normalizeTab(tab);
  if (normalized) url.searchParams.set(TAB_PARAM, normalized);
  else url.searchParams.delete(TAB_PARAM);
  return `${url.pathname}${url.search}${url.hash}`;
}

/**
 * Only same-origin relative paths are allowed as a post-login redirect:
 * "/agy" and "/?tab=gallery" pass; "//evil.com", "https://...", "javascript:",
 * and backslash tricks do not.
 */
export function isSafeNextPath(next) {
  if (typeof next !== 'string') return false;
  const value = next.trim();
  if (!value.startsWith('/')) return false;
  if (value.startsWith('//') || value.startsWith('/\\')) return false;
  if (/[\\\u0000-\u001f]/.test(value)) return false;
  try {
    const base = 'http://local.invalid';
    const url = new URL(value, base);
    return url.origin === base;
  } catch {
    return false;
  }
}

/** `next` from a query string when it is a safe relative path, else null. */
export function readSafeNext(search) {
  try {
    const next = new URLSearchParams(search || '').get('next');
    return isSafeNextPath(next) ? next.trim() : null;
  } catch {
    return null;
  }
}

/** Query string without the login handshake params (`login`, `next`). */
export function stripLoginParams(href) {
  const url = new URL(href, 'http://local.invalid');
  url.searchParams.delete('login');
  url.searchParams.delete('next');
  return `${url.pathname}${url.search}${url.hash}`;
}

/** History state marker used by useBackToClose for overlay entries. */
export const OVERLAY_STATE_KEY = 'omnicutOverlay';
export const TAB_STATE_KEY = 'omnicutTab';

/** True when a history state object belongs to an open overlay entry. */
export function isOverlayState(state) {
  return Boolean(state && typeof state === 'object' && state[OVERLAY_STATE_KEY]);
}

/**
 * Decide how to record a tab change. Returns 'none' when the URL already shows
 * the tab, 'replace' when the current entry is an overlay that is closing (so
 * the overlay entry becomes the tab entry instead of leaving a dead back step),
 * otherwise 'push'.
 */
export function tabHistoryAction({ search = '', state = null, tab }) {
  const normalized = normalizeTab(tab);
  if (!normalized) return 'none';
  if (readTabFromSearch(search) === normalized) return 'none';
  return isOverlayState(state) ? 'replace' : 'push';
}

function browserWindow(win) {
  if (win) return win;
  return typeof window === 'undefined' ? null : window;
}

/** Record a tab change as a history entry. Returns the action taken. */
export function pushTab(tab, { win } = {}) {
  const w = browserWindow(win);
  if (!w?.history || !w.location) return 'none';
  const action = tabHistoryAction({ search: w.location.search, state: w.history.state, tab });
  if (action === 'none') return action;
  const url = buildTabUrl(w.location.href, tab);
  const state = { [TAB_STATE_KEY]: normalizeTab(tab) };
  try {
    if (action === 'replace') w.history.replaceState(state, '', url);
    else w.history.pushState(state, '', url);
  } catch {
    return 'none';
  }
  return action;
}

/** Put the tab in the URL without adding a history entry (boot, redirects). */
export function replaceTab(tab, { win } = {}) {
  const w = browserWindow(win);
  if (!w?.history || !w.location) return false;
  const normalized = normalizeTab(tab);
  if (!normalized) return false;
  try {
    const current = w.history.state && typeof w.history.state === 'object' ? w.history.state : {};
    w.history.replaceState({ ...current, [TAB_STATE_KEY]: normalized }, '', buildTabUrl(w.location.href, normalized));
    return true;
  } catch {
    return false;
  }
}
