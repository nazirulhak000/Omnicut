/**
 * Playback-source resolution for timeline clips.
 *
 * The editor plays 540p proxies so scrubbing a 4K master stays responsive,
 * while Render always reads the master. This module owns the bookkeeping for
 * that swap, kept out of the player so it can be tested without a DOM.
 *
 * Two invariants:
 *
 * 1. **The master is always a valid answer.** A proxy that is missing, still
 *    encoding, or failed outright costs smoothness, never the ability to
 *    edit, so every lookup falls back rather than erroring.
 * 2. **Proxies are pixels, never a clock.** A proxy is re-encoded and its
 *    duration can differ from the master's by a frame. Trim, in/out and speed
 *    are always computed from the master, so nothing here exposes a duration.
 */

/** Status the backend reports for one clip's proxy. */
export const PROXY_READY = 'ready';
export const PROXY_BUILDING = 'building';
export const PROXY_MASTER = 'master';

/**
 * How long to wait before asking again about a proxy that was still encoding.
 * Long enough that a timeline full of clips does not hammer the API, short
 * enough that a finished proxy is picked up within a few seconds.
 */
export const PROXY_POLL_MS = 3000;

/**
 * Normalise one `/api/proxy/for-clip` response.
 *
 * A malformed or empty payload resolves to the master URL the caller already
 * had: the player must always end up with something to play.
 */
export function readProxyResponse(payload, masterUrl) {
  const fallback = { url: masterUrl, isProxy: false, status: PROXY_MASTER };
  if (!payload || typeof payload !== 'object') return fallback;

  const url = typeof payload.url === 'string' && payload.url ? payload.url : masterUrl;
  const status = payload.status === PROXY_READY || payload.status === PROXY_BUILDING
    ? payload.status
    : PROXY_MASTER;

  return {
    url,
    // Trust the flag only when the status agrees: a payload claiming
    // is_proxy on a master URL would make the render-side guard the only
    // thing standing between a 540p file and an export.
    isProxy: status === PROXY_READY && payload.is_proxy === true && url !== masterUrl,
    status,
  };
}

/**
 * True when a clip should be asked about again.
 *
 * Only a clip whose proxy was still encoding is worth re-checking: `ready` is
 * terminal, and `master` means nothing is being built.
 */
export function shouldPoll(entry) {
  return entry?.status === PROXY_BUILDING;
}

/**
 * Merge one resolved clip into the source map without disturbing the rest.
 *
 * Returns the original map when nothing changed, so React state updates can
 * bail out instead of re-rendering the whole player on every poll that
 * reports the same thing.
 */
export function mergeProxyEntry(current, clipId, entry) {
  const existing = current?.[clipId];
  if (existing
    && existing.url === entry.url
    && existing.status === entry.status
    && existing.isProxy === entry.isProxy) {
    return current;
  }
  return { ...(current || {}), [clipId]: entry };
}

/**
 * The URL to play for `clip`, given what has been resolved so far.
 *
 * Falls back to the master whenever the clip has not been resolved yet, so
 * the first paint shows real footage instead of an empty player while the
 * proxy lookup is in flight.
 */
export function playbackUrlFor(clip, sources, toMediaUrl) {
  const master = toMediaUrl(clip?.source_path);
  const entry = sources?.[clip?.id];
  return entry?.url || master;
}

/**
 * Clip ids whose proxies are still encoding, for a "preparing previews" hint.
 */
export function buildingClipIds(sources) {
  return Object.entries(sources || {})
    .filter(([, entry]) => shouldPoll(entry))
    .map(([id]) => id);
}
