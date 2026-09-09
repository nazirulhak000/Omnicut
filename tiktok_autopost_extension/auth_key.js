// Shared API key handling for the extension's calls to the OmniCut backend.
//
// scripts/auth.py's api_key_gate 401s every request once OMNICUT_API_KEY is
// set in the app's .env. The app's own frontend is proxied through Vite,
// which injects the X-API-Key header server-side for every request
// regardless of how the browser made it (see frontend/vite.config.js) --
// but this extension talks to http://127.0.0.1:8000 directly, with no
// proxy in between, so it has to carry the key itself on every fetch()
// and native <img src> load (the latter can't attach a custom header at
// all, so it uses the query-param fallback the gate also accepts for
// GET/HEAD).
//
// Stored in chrome.storage.local (not .sync -- this is a per-machine
// secret tied to one install of the app, not something to carry across a
// Google account) via the settings field in sidepanel.html/js.

const OMNICUT_API_KEY_STORAGE_KEY = 'omnicutApiKey';

function getStoredApiKey() {
  return new Promise((resolve) => {
    if (typeof chrome === 'undefined' || !chrome.storage?.local) {
      resolve('');
      return;
    }
    chrome.storage.local.get([OMNICUT_API_KEY_STORAGE_KEY], (data) => {
      resolve(data?.[OMNICUT_API_KEY_STORAGE_KEY] || '');
    });
  });
}

function setStoredApiKey(key) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [OMNICUT_API_KEY_STORAGE_KEY]: key || '' }, resolve);
  });
}

// Appends the key as a query param, for URLs a native <img>/<video> tag
// will load -- those cannot carry a custom header at all.
function withApiKeyParam(url, apiKey) {
  if (!apiKey) return url;
  return url + (url.includes('?') ? '&' : '?') + 'api_key=' + encodeURIComponent(apiKey);
}

// fetch() wrapper that attaches X-API-Key when a key is configured --
// preferred over the query-param fallback for anything that can set
// headers, since query params can end up in logs.
function authedFetch(url, apiKey, options = {}) {
  if (!apiKey) return fetch(url, options);
  const headers = new Headers(options.headers || {});
  headers.set('X-API-Key', apiKey);
  return fetch(url, { ...options, headers });
}
