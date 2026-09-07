// Backend accepts absolute or BASE_DIR-relative paths at /api/media/{path}
// (scripts/api_server.py's stream_media()) -- encode each segment so Thai
// filenames/spaces survive, but keep the "/" separators the route needs.
//
// A scraped product-page thumbnail (TikTok/Shopee CDN) is already a full
// external URL with nothing on our own disk to serve -- routing it through
// /api/media/ would try to encode the whole URL as a local path segment and
// 404. Serve it directly from its own host instead.
export function toMediaUrl(rawPath) {
  if (!rawPath) return '';
  if (rawPath.startsWith('http://') || rawPath.startsWith('https://')) return rawPath;
  if (rawPath.startsWith('/api/media/')) return rawPath;
  const normalized = rawPath.replace(/\\/g, '/');
  return '/api/media/' + normalized.split('/').map(encodeURIComponent).join('/');
}

/**
 * Compares two video references (can be objects, paths, relative paths, or filenames)
 * to determine if they point to the same video file, regardless of Windows/POSIX slashes.
 *
 * Matches on the full normalized path only. Two same-named files living in
 * different folders (e.g. two products' raw footage both containing a
 * "video.mp4") are NOT the same video, so there is no bare-basename
 * fallback here -- that used to silently attach the wrong raw footage to a
 * render. The only case treated as equal without a full path is when BOTH
 * sides are already bare filenames (no directory separator at all), since
 * then there is no path information to lose by comparing names.
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

  const isBareName1 = !norm1.includes('/');
  const isBareName2 = !norm2.includes('/');

  // Legacy last-resort: only when NEITHER side carries any folder
  // information at all, so a bare-name comparison cannot lose anything a
  // full-path comparison would have caught.
  if (isBareName1 && isBareName2) {
    return norm1 === norm2;
  }

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

