import { toMediaUrl } from './mediaUrl.js';

/**
 * Keeps the two generated cover crops explicit. TikTok's cover picker uses
 * the 3:4 crop; the 9:16 file remains available as a fallback for older
 * exports and other destinations.
 */
export function getCoverVariant(item = {}, preferred = '3:4') {
  const threeByFour = {
    // Older API responses persisted the path but omitted its derived URL.
    // Resolve it here so the posting modal can still render and edit that
    // saved cover without requiring another server-side migration.
    url: item.cover_3x4_url || item.media_url_3x4 || toMediaUrl(item.cover_3x4_path),
    path: item.cover_3x4_path || '',
  };
  const nineBySixteen = {
    url: item.cover_9x16_url || item.media_url || item.cover_url || toMediaUrl(item.cover_9x16_path || item.cover_path),
    path: item.cover_9x16_path || item.cover_path || '',
  };
  const ordered = preferred === '3:4'
    ? [threeByFour, nineBySixteen]
    : [nineBySixteen, threeByFour];
  return ordered.find(({ url, path }) => url || path) || { url: '', path: '' };
}

export function applyCoverResult(item = {}, result = {}) {
  const threeByFour = {
    url: result.media_url_3x4 || result.cover_3x4_url || toMediaUrl(result.cover_3x4_path),
    path: result.cover_3x4_path || '',
  };
  const nineBySixteen = {
    url: result.media_url || result.cover_url || toMediaUrl(result.cover_path),
    path: result.cover_path || '',
  };
  const selected = getCoverVariant({
    ...item,
    cover_3x4_url: threeByFour.url || item.cover_3x4_url,
    cover_3x4_path: threeByFour.path || item.cover_3x4_path,
    cover_9x16_url: nineBySixteen.url || item.cover_9x16_url,
    cover_9x16_path: nineBySixteen.path || item.cover_9x16_path,
    cover_url: nineBySixteen.url || item.cover_url,
    cover_path: nineBySixteen.path || item.cover_path,
  });
  return {
    ...item,
    cover_url: selected.url,
    cover_path: selected.path,
    cover_3x4_url: threeByFour.url || item.cover_3x4_url || null,
    cover_3x4_path: threeByFour.path || item.cover_3x4_path || null,
    cover_9x16_url: nineBySixteen.url || item.cover_9x16_url || null,
    cover_9x16_path: nineBySixteen.path || item.cover_9x16_path || null,
  };
}

function normalizeReference(value) {
  return String(value || '').replace(/\\/g, '/').replace(/^\/+/, '').toLowerCase();
}

function sameReference(left, right) {
  const a = normalizeReference(left);
  const b = normalizeReference(right);
  if (!a || !b) return false;
  return a === b || a.endsWith(`/${b}`) || b.endsWith(`/${a}`);
}

/**
 * Product responses from older backend workers can omit hydrated cover
 * fields even though the matching export already exposes them. Merge only
 * missing fields from the export so an explicit angle cover always wins.
 */
export function mergeCoverMetadata(products = [], exports = []) {
  const exportItems = Array.isArray(exports) ? exports : (exports?.exports || []);
  return products.map((product) => ({
    ...product,
    angles: (product.angles || []).map((angle) => {
      const match = (angle.export_id && exportItems.find((item) => item.export_id === angle.export_id))
        || exportItems.find((item) => {
          // Once either side has a stable identity, never fall back to a
          // project/path match that can select a sibling version.
          if (angle.export_id || item.export_id) return false;
          return (angle.project_name && item.project_name && normalizeReference(angle.project_name) === normalizeReference(item.project_name))
            || sameReference(angle.video_url, item.rel_path || item.path);
        });
      if (!match) return angle;
      return {
        ...angle,
        export_id: angle.export_id || match.export_id || null,
        cover_path: angle.cover_path || match.cover_path || null,
        cover_3x4_path: angle.cover_3x4_path || match.cover_3x4_path || null,
        cover_9x16_path: angle.cover_9x16_path || match.cover_9x16_path || null,
        cover_url: angle.cover_url || match.cover_url || null,
        cover_3x4_url: angle.cover_3x4_url || match.cover_3x4_url || null,
        cover_9x16_url: angle.cover_9x16_url || match.cover_9x16_url || null,
        media_url: angle.media_url || match.media_url || null,
        media_url_3x4: angle.media_url_3x4 || match.media_url_3x4 || null,
      };
    }),
  }));
}
