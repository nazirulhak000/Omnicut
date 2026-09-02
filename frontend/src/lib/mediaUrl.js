// Backend accepts absolute or BASE_DIR-relative paths at /api/media/{path}
// (scripts/api_server.py's stream_media()) -- encode each segment so Thai
// filenames/spaces survive, but keep the "/" separators the route needs.
export function toMediaUrl(rawPath) {
  if (!rawPath) return '';
  if (rawPath.startsWith('/api/media/')) return rawPath;
  const normalized = rawPath.replace(/\\/g, '/');
  return '/api/media/' + normalized.split('/').map(encodeURIComponent).join('/');
}
