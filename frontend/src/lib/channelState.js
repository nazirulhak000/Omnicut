import { assertChannelId } from './channelId.js';

const PREFIX = 'omnicut:channel:v1:';
export const ACTIVE_CHANNEL_KEY = 'omnicut:active_channel:v1';

function resourceName(resource) {
  if (typeof resource !== 'string' || !resource.length) {
    throw new TypeError('Cache resource must be a nonempty string');
  }
  return encodeURIComponent(resource);
}

/** Use this for storage keys and in-memory cache keys alike. */
export function channelCacheKey(channelId, resource) {
  return `${PREFIX}${assertChannelId(channelId)}:${resourceName(resource)}`;
}

function owns(data, channelId) {
  return !(data && typeof data === 'object' && 'channel_id' in data)
    || data.channel_id === channelId;
}

function envelope(channelId, data) {
  if (!owns(data, channelId)) {
    const error = new TypeError('Cache payload owner does not match channel');
    error.code = 'channel_scope_conflict';
    throw error;
  }
  const serialized = JSON.stringify({ schema_version: 1, channel_id: channelId, data });
  // Reject undefined/functions and other values that silently lose their payload.
  const persisted = JSON.parse(serialized);
  if (!Object.hasOwn(persisted, 'data')) {
    throw new TypeError('Cache payload must be JSON serializable');
  }
  if (!owns(persisted.data, channelId)) {
    const error = new TypeError('Serialized cache payload owner does not match channel');
    error.code = 'channel_scope_conflict';
    throw error;
  }
  return serialized;
}

function decodeEnvelope(raw, channelId) {
  try {
    const value = JSON.parse(raw);
    if (!value || value.schema_version !== 1 || value.channel_id !== channelId
      || !Object.hasOwn(value, 'data') || !owns(value.data, channelId)) return null;
    return value;
  } catch {
    return null;
  }
}

/** Malformed/foreign entries return null untouched; storage failures propagate. */
export function readChannelCache(storage, channelId, resource) {
  const key = channelCacheKey(channelId, resource);
  const value = decodeEnvelope(storage.getItem(key), channelId);
  return value ? value.data : null;
}

export function writeChannelCache(storage, channelId, resource, data) {
  const key = channelCacheKey(channelId, resource);
  storage.setItem(key, envelope(channelId, data));
}

/**
 * Explicit migration of ONE legacy key to main; never call for another channel.
 * A journal keeps the exact source/destination bytes for interruption recovery.
 * Existing main entries (even malformed) are never overwritten. decodeLegacy
 * defaults to JSON.parse; inject e.g. raw => raw for plain-string legacy keys.
 * Storage exceptions propagate so callers can retry. This is not a cross-tab lock.
 */
export function migrateLegacyMain(storage, channelId, resource, legacyKey, {
  decodeLegacy = JSON.parse,
} = {}) {
  const key = channelCacheKey(channelId, resource);
  if (channelId !== 'main') return { status: 'not_main' };
  if (typeof legacyKey !== 'string' || !legacyKey.length || legacyKey.startsWith(PREFIX)) {
    throw new TypeError('Migration requires an unscoped legacy key');
  }
  const journalKey = `${key}:legacy_migration`;
  let journal;
  const savedJournal = storage.getItem(journalKey);
  if (savedJournal !== null) {
    try { journal = JSON.parse(savedJournal); } catch { return { status: 'invalid_journal' }; }
    if (!journal || journal.legacy_key !== legacyKey || journal.channel_id !== 'main'
      || !['pending', 'done'].includes(journal.status)
      || typeof journal.source !== 'string' || typeof journal.target !== 'string'
      || !decodeEnvelope(journal.target, 'main')) return { status: 'invalid_journal' };
    if (journal.status === 'done') return { status: 'already_migrated' };
  } else {
    if (storage.getItem(key) !== null) return { status: 'existing_main' };
    const source = storage.getItem(legacyKey);
    if (source === null) return { status: 'missing' };
    let target;
    try { target = envelope('main', decodeLegacy(source)); } catch { return { status: 'invalid_legacy' }; }
    journal = { channel_id: 'main', legacy_key: legacyKey, source, target, status: 'pending' };
    storage.setItem(journalKey, JSON.stringify(journal));
  }
  const destination = storage.getItem(key);
  if (destination === null) {
    if (storage.getItem(legacyKey) !== journal.source) return { status: 'source_changed' };
    storage.setItem(key, journal.target);
  } else if (destination !== journal.target) {
    return { status: 'existing_main' };
  }
  // Do not remove a source replaced by another tab, nor a failed target write.
  if (storage.getItem(key) !== journal.target) return { status: 'write_unverified' };
  const sourceNow = storage.getItem(legacyKey);
  if (sourceNow !== null && sourceNow !== journal.source) return { status: 'source_changed' };
  if (sourceNow !== null) storage.removeItem(legacyKey);
  storage.setItem(journalKey, JSON.stringify({ ...journal, status: 'done' }));
  return { status: 'migrated' };
}

/** Inject sessionStorage for per-tab selection. sharedStorage is an optional default only. */
export function readActiveChannel(sessionStorage, { sharedStorage, defaultChannelId = 'main' } = {}) {
  assertChannelId(defaultChannelId);
  for (const storage of [sessionStorage, sharedStorage]) {
    if (!storage) continue;
    const value = storage.getItem(ACTIVE_CHANNEL_KEY);
    if (value === null) continue;
    try { return assertChannelId(value); } catch { /* Ignore invalid persisted selection. */ }
  }
  return defaultChannelId;
}

export function writeActiveChannel(sessionStorage, channelId) {
  sessionStorage.setItem(ACTIVE_CHANNEL_KEY, assertChannelId(channelId));
}

/** Capture at dispatch; check before committing results. activate invalidates all old tokens. */
export function createChannelRequestGuard(initialChannelId) {
  let channelId = assertChannelId(initialChannelId);
  let epoch = 0;
  const issued = new WeakSet();
  return {
    activate(nextChannelId) {
      channelId = assertChannelId(nextChannelId);
      epoch += 1;
    },
    capture() {
      const token = Object.freeze({ channel_id: channelId, epoch });
      issued.add(token);
      return token;
    },
    isCurrent(token) {
      return !!token && issued.has(token) && token.epoch === epoch && token.channel_id === channelId;
    },
  };
}

/** Pure decision only; caller implements confirmation, saving and switching. */
export function decideChannelSwitch(currentChannelId, nextChannelId, {
  hasUnsavedChanges = false, decision = null,
} = {}) {
  assertChannelId(currentChannelId);
  assertChannelId(nextChannelId);
  if (![null, 'save', 'discard', 'cancel'].includes(decision)) {
    throw new TypeError('Unknown unsaved-switch decision');
  }
  let action = 'switch';
  if (currentChannelId === nextChannelId || decision === 'cancel') action = 'stay';
  else if (hasUnsavedChanges) {
    action = decision === 'save' ? 'save_before_switch'
      : decision === 'discard' ? 'switch' : 'confirm';
  }
  return { action, from: currentChannelId, to: nextChannelId };
}
