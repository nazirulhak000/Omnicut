import { assertChannelId } from './channelId.js';

export const CHANNEL_HEADER = 'X-OmniCut-Channel';
const HEADER_KEY = CHANNEL_HEADER.toLowerCase();
const MEDIA_PATHS = [
  /^\/api\/media\/.+$/,
  /^\/api\/editor\/filmstrip$/,
  /^\/api\/producer\/ref-media\/[^/]+$/,
  /^\/api\/background-isolation\/videos\/[^/]+\/(?:cutout|preview)\.webm$/,
  /^\/api\/background-isolation\/sequences\/[^/]+\/frames\/[^/]+$/,
  /^\/api\/hyperframes\/render-jobs\/[^/]+\/artifact\/[^/]+$/,
];

function fail(code) {
  const error = new TypeError(code);
  error.code = code;
  throw error;
}

/** Capture once when dispatching. Compat without an ID is explicit, never inferred. */
export function createChannelRequestContext({ channelId = null, compat = false } = {}) {
  if (channelId !== null) assertChannelId(channelId);
  else if (!compat) fail('channel_scope_missing');
  return Object.freeze({ channelId, compat });
}

function snapshot(value) {
  if (Array.isArray(value)) return Object.freeze(value.map(snapshot));
  if (isPlainObject(value)) {
    return Object.freeze(Object.fromEntries(Object.entries(value).map(([k, v]) => [k, snapshot(v)])));
  }
  // Opaque transport objects (AbortSignal, Blob) retain their native identity.
  return value;
}

function isPlainObject(value) {
  return value && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function rejectMutableCarriers(options, scopedHeaders) {
  for (const value of [options.data, options.body, options.params]) {
    if ((typeof FormData !== 'undefined' && value instanceof FormData)
      || (typeof URLSearchParams !== 'undefined' && value instanceof URLSearchParams)) {
      fail('channel_request_unsupported');
    }
  }
  if (!scopedHeaders && options.headers && !isPlainObject(options.headers) && !Array.isArray(options.headers)) {
    fail('channel_request_unsupported');
  }
  // These can rewrite validated scope after preparation. Integration must own
  // and review its serializer/adapter, then call this helper on the final config.
  if (options.transformRequest || options.paramsSerializer || options.adapter) fail('channel_request_unsupported');
}

function validateJsonCarrier(value, parents = new Set()) {
  if (value === null || value === undefined || ['string', 'boolean'].includes(typeof value)) return;
  if (typeof value === 'number' && Number.isFinite(value)) return;
  if (typeof value !== 'object') fail('channel_request_unsupported');
  // Native immutable binary data is transport-owned, not a JSON owner carrier.
  if (typeof Blob !== 'undefined' && value instanceof Blob) return;
  // These are rejected below after the scope checks, giving conflicts priority.
  if ((typeof FormData !== 'undefined' && value instanceof FormData)
    || (typeof URLSearchParams !== 'undefined' && value instanceof URLSearchParams)) return;
  if ((!isPlainObject(value) && !Array.isArray(value)) || parents.has(value)) fail('channel_request_unsupported');
  parents.add(value);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key === 'symbol' || descriptor.get || descriptor.set) fail('channel_request_unsupported');
    validateJsonCarrier(descriptor.value, parents);
  }
  parents.delete(value);
}

function headerEntries(headers) {
  if (!headers) return [];
  if (Array.isArray(headers)) return headers;
  if (typeof headers.entries === 'function') return [...headers.entries()];
  if (typeof headers.toJSON === 'function') return Object.entries(headers.toJSON());
  return Object.entries(headers);
}

function scopeValues(entries) {
  return entries.filter(([key]) => key.toLowerCase() === HEADER_KEY)
    .flatMap(([, value]) => Array.isArray(value) ? value : [value]);
}

function queryScopeValues(params) {
  if (!params) return [];
  if (typeof params.getAll === 'function') return params.getAll('channel');
  if (!Object.hasOwn(params, 'channel')) return [];
  return Array.isArray(params.channel) ? params.channel : [params.channel];
}

function checkValues(values, expected) {
  for (const value of values) assertChannelId(value);
  if (values.some(value => value !== (expected ?? values[0]))) fail('channel_scope_conflict');
}

function internalUrl(input, origin) {
  if (typeof input !== 'string' || /[\s\\\u0000-\u001f\u007f]/u.test(input)) fail('channel_url_invalid');
  if (input.startsWith('//')) fail('channel_url_external');
  const relative = input.startsWith('/') && !input.startsWith('//');
  if (!relative && !origin) fail('channel_url_external');
  const base = origin ? new URL(origin).origin : 'https://omnicut.invalid';
  const url = new URL(input, base);
  if (url.origin !== base || url.username || url.password || !/^https?:$/.test(url.protocol)) {
    fail('channel_url_external');
  }
  // Check the original spelling before URL normalizes traversal segments.
  let path;
  try {
    const rawPath = relative ? input.split(/[?#]/)[0] : input.replace(/^https?:\/\/[^/]+/i, '').split(/[?#]/)[0];
    path = decodeURIComponent(rawPath);
  } catch { fail('channel_url_invalid'); }
  if (path.includes('\\') || path.split('/').some(part => part === '.' || part === '..')) fail('channel_url_invalid');
  if (!path.startsWith('/api/')) fail('channel_url_invalid');
  return { url, path };
}

function isRegistry(path) {
  return /^\/api\/channels(?:\/[^/]+(?:\/(?:activate|archive|readiness))?)?$/.test(path);
}

function checkBaseUrl(baseURL, origin) {
  if (baseURL === undefined || baseURL === '') return;
  // Axios joins even root-relative urls to baseURL. Allow only a trusted origin
  // root, never a route prefix that would change the classified endpoint.
  if (typeof baseURL !== 'string' || baseURL.startsWith('//')) fail('channel_url_external');
  const base = origin ? new URL(origin).origin : 'https://omnicut.invalid';
  if (!baseURL.startsWith('/') && !origin) fail('channel_url_external');
  const parsed = new URL(baseURL, base);
  if (parsed.origin !== base || parsed.username || parsed.password) fail('channel_url_external');
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) fail('channel_url_invalid');
}

/**
 * Prepare an immutable transport config; url must include /api. Caller supplies the
 * policy's scope (channel/shared/global), never a guessed route family. No dispatch,
 * defaults mutation, authentication or active-channel lookup occurs here. Adapt
 * this config to axios/fetch at the integration boundary; state owns epoch checks.
 * Mutable FormData/URLSearchParams and custom serializers/adapters are unsupported
 * until integration captures their wire form and validates at dispatch. Native
 * headers normalize to frozen plain headers for scoped requests; unscoped compat
 * accepts plain headers only, preserving option shape instead of coercing it.
 * A configured transport must use the trusted origin root, not a /api base prefix.
 */
export function prepareChannelRequest(context, options, { scope, origin } = {}) {
  if (!isPlainObject(options)) fail('channel_request_unsupported');
  for (const descriptor of Object.values(Object.getOwnPropertyDescriptors(options))) {
    if (descriptor.get || descriptor.set) fail('channel_request_unsupported');
  }
  const { url, path } = internalUrl(options.url, origin);
  checkBaseUrl(options.baseURL, origin);
  for (const carrier of [options.data, options.body, options.params]) validateJsonCarrier(carrier);
  if (isPlainObject(options.headers) || Array.isArray(options.headers)) validateJsonCarrier(options.headers);
  const entries = headerEntries(options.headers);
  const registry = isRegistry(path);
  const captured = registry ? createChannelRequestContext({ compat: true }) : createChannelRequestContext(context);
  if (!registry && !['channel', 'shared', 'global'].includes(scope)) fail('channel_policy_missing');
  const suppliedHeaders = scopeValues(entries);
  if (!registry) checkValues(suppliedHeaders, captured.channelId);
  const effectiveId = registry ? null : (captured.channelId ?? suppliedHeaders[0] ?? null);
  // Axios params and URLSearchParams are query input too, even before serialization.
  const queries = [...url.searchParams.getAll('channel'), ...queryScopeValues(options.params)];
  const method = (options.method ?? 'GET').toUpperCase();
  if (queries.length && (method !== 'GET' || !MEDIA_PATHS.some(pattern => pattern.test(path)))) {
    fail('channel_query_not_allowed');
  }
  checkValues(queries, effectiveId);
  const bodyId = bodyChannelIds(options.data, options.body);
  if (!registry) checkValues(bodyId, effectiveId ?? queries[0] ?? null);
  if (!registry && scope === 'channel' && !effectiveId && !queries.length && !captured.compat) {
    fail('channel_scope_missing');
  }
  rejectMutableCarriers(options, registry || effectiveId);
  // A truly unscoped compat request preserves its original option keys and values.
  let prepared = { ...options };
  if (registry || effectiveId) {
    const headers = Object.fromEntries(entries.filter(([key]) => key.toLowerCase() !== HEADER_KEY));
    if (effectiveId) headers[CHANNEL_HEADER] = effectiveId;
    if (options.headers !== undefined || effectiveId) prepared.headers = headers;
  }
  return snapshot(prepared);
}

function bodyChannelIds(...bodies) {
  return bodies.flatMap(body => {
    if (typeof body === 'string') {
      try { body = JSON.parse(body); } catch { return []; }
    }
    if (body && typeof body.getAll === 'function') return body.getAll('channel_id');
    return body && Object.hasOwn(body, 'channel_id') ? [body.channel_id] : [];
  });
}

/** Only the six policy-approved internal GET src patterns can carry query scope. */
export function scopedMediaUrl(input, context, { origin } = {}) {
  const captured = createChannelRequestContext(context);
  const { url, path } = internalUrl(input, origin);
  if (!MEDIA_PATHS.some(pattern => pattern.test(path))) fail('channel_query_not_allowed');
  checkValues(url.searchParams.getAll('channel'), captured.channelId);
  if (!captured.channelId || url.searchParams.has('channel')) return input;
  const hashIndex = input.indexOf('#');
  const head = hashIndex < 0 ? input : input.slice(0, hashIndex);
  const hash = hashIndex < 0 ? '' : input.slice(hashIndex);
  const separator = head.includes('?') ? (/[?&]$/.test(head) ? '' : '&') : '?';
  return `${head}${separator}channel=${encodeURIComponent(captured.channelId)}${hash}`;
}

/** Check echoed scope before consuming data. Missing echo is legal for compat. */
export function assertChannelResponseScope(context, headers) {
  const captured = createChannelRequestContext(context);
  const values = scopeValues(headerEntries(headers));
  checkValues(values, captured.channelId);
  return true;
}
