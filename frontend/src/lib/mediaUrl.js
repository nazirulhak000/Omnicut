// Backend accepts absolute or BASE_DIR-relative paths at /api/media/{path}
// (scripts/api_server.py's stream_media()) -- encode each segment so Thai
// filenames/spaces survive, but keep the "/" separators the route needs.
export function toMediaUrl(rawPath) {
  if (!rawPath) return '';
  if (rawPath.startsWith('/api/media/')) return rawPath;
  const normalized = rawPath.replace(/\\/g, '/');
  return '/api/media/' + normalized.split('/').map(encodeURIComponent).join('/');
}

/**
 * Compares two video references (can be objects, paths, relative paths, or filenames)
 * to determine if they point to the same video file, regardless of Windows/POSIX slashes.
 */
export function isSameVideo(v1, v2) {
  if (!v1 || !v2) return false;
  if (v1 === v2) return true;

  const p1 = typeof v1 === 'string' ? v1 : (v1.path || v1.rel_path || v1.name || '');
  const p2 = typeof v2 === 'string' ? v2 : (v2.path || v2.rel_path || v2.name || '');
  if (!p1 || !p2) return false;
  if (p1 === p2) return true;

  const norm1 = p1.replace(/\\/g, '/').toLowerCase().trim();
  const norm2 = p2.replace(/\\/g, '/').toLowerCase().trim();
  if (norm1 === norm2) return true;

  const name1 = norm1.split('/').pop();
  const name2 = norm2.split('/').pop();
  if (name1 && name2 && name1 === name2) return true;

  if (norm1.endsWith('/' + name2) || norm2.endsWith('/' + name1)) return true;

  return false;
}

/**
 * Returns clean filename from video path or object.
 */
export function getMediaName(v) {
  if (!v) return '';
  if (typeof v === 'object' && v.name) return v.name;
  const str = typeof v === 'string' ? v : (v.path || v.rel_path || '');
  return str.split(/[/\\]/).pop() || '';
}

