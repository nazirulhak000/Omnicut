import { prepareChannelRequest, assertChannelResponseScope, scopedMediaUrl } from './channelRequest.js';

function failure(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}

function multipartCopy(data, channelId) {
  const copy = new FormData();
  for (const [key, value] of data.entries()) {
    if (key === 'channel_id' && value !== channelId) throw failure('channel_scope_conflict');
    if (typeof File !== 'undefined' && value instanceof File) copy.append(key, value, value.name);
    else copy.append(key, value);
  }
  return copy;
}

export function channelMediaData(value, context) {
  if (typeof value === 'string' && value.startsWith('/api/')) {
    try { return scopedMediaUrl(value, context); }
    catch (error) { if (error.code === 'channel_query_not_allowed') return value; throw error; }
  }
  if (Array.isArray(value)) return value.map(item => channelMediaData(item, context));
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, channelMediaData(item, context)]));
  }
  return value;
}

/** Capture before dispatch, validate before transport and before consuming data. */
export function createChannelTransport({ send, capture, isCurrent }) {
  return async function request(options) {
    const token = options.channelToken || capture();
    const { channelToken: _token, ...transportOptions } = options;
    const context = { channelId: token.channel_id };
    const multipart = typeof FormData !== 'undefined' && transportOptions.data instanceof FormData;
    const copiedBody = multipart ? multipartCopy(transportOptions.data, token.channel_id) : null;
    const prepared = prepareChannelRequest(context,
      multipart ? { ...transportOptions, data: undefined } : transportOptions, { scope: 'channel' });
    let response;
    try { response = await send(multipart ? { ...prepared, data: copiedBody } : prepared); }
    catch (error) {
      if (!isCurrent(token)) throw failure('channel_response_stale');
      throw error;
    }
    assertChannelResponseScope(context, response.headers);
    if (!isCurrent(token)) throw failure('channel_response_stale');
    return { ...response, data: channelMediaData(response.data, context) };
  };
}

export function projectApiPath(projectName) {
  const parts = String(projectName).replaceAll('\\', '/').split('/');
  if (parts.some(part => !part || part === '.' || part === '..') || parts.length > 2) {
    throw failure('project_name_invalid');
  }
  return parts.length === 1 ? `/projects/${encodeURIComponent(parts[0])}`
    : `/channel-projects/${encodeURIComponent(parts[0])}/${encodeURIComponent(parts[1])}`;
}
