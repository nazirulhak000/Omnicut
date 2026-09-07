/**
 * Keeps the two generated cover crops explicit. TikTok's cover picker uses
 * the 3:4 crop; the 9:16 file remains available as a fallback for older
 * exports and other destinations.
 */
export function getCoverVariant(item = {}, preferred = '3:4') {
  const threeByFour = {
    url: item.cover_3x4_url || item.media_url_3x4 || '',
    path: item.cover_3x4_path || '',
  };
  const nineBySixteen = {
    url: item.cover_9x16_url || item.media_url || item.cover_url || '',
    path: item.cover_9x16_path || item.cover_path || '',
  };
  const ordered = preferred === '3:4'
    ? [threeByFour, nineBySixteen]
    : [nineBySixteen, threeByFour];
  return ordered.find(({ url, path }) => url || path) || { url: '', path: '' };
}

export function applyCoverResult(item = {}, result = {}) {
  const threeByFour = {
    url: result.media_url_3x4 || result.cover_3x4_url || '',
    path: result.cover_3x4_path || '',
  };
  const nineBySixteen = {
    url: result.media_url || result.cover_url || '',
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
