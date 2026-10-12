import { activeChannel } from './channelRuntime.js';
import { channelCacheKey, migrateLegacyMain, readChannelCache, writeChannelCache } from './channelState.js';

// The owner is captured when the workspace mounts. Delayed callbacks from A
// can only write A's cache, even after the visible workspace switches to B.
export function channelStorage(storage, channelId = activeChannel()) {
  if (!storage) return null;
  return {
    getItem(key) {
      migrateLegacyMain(storage, channelId, key, key, { decodeLegacy: raw => raw });
      return readChannelCache(storage, channelId, key);
    },
    setItem(key, value) { writeChannelCache(storage, channelId, key, String(value)); },
    removeItem(key) { storage.removeItem(channelCacheKey(channelId, key)); },
    keyFor(key) { return channelCacheKey(channelId, key); },
  };
}

export function channelLocalStorage(channelId = activeChannel()) {
  return channelStorage(globalThis.localStorage, channelId);
}

export function channelSessionStorage(channelId = activeChannel()) {
  return channelStorage(globalThis.sessionStorage, channelId);
}
