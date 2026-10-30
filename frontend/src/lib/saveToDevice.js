/**
 * Chunked Range video prefetcher & synchronous Web Share helper for mobile (Phase 5.2).
 *
 * Solves two mobile browser constraints:
 * 1. Cloudflare Tunnel / cellular drops on large MP4s (17-76 MB): downloads in
 *    4 MiB HTTP Range chunks (`Range: bytes=start-end`), retrying failed chunks
 *    and resuming from the last completed chunk if interrupted (e.g. screen lock).
 * 2. iOS Safari transient user activation: `navigator.share({ files })` must be
 *    called synchronously inside the tap handler with zero `await` before it.
 */

export const DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024; // 4 MiB
export const DEFAULT_MAX_CACHE_ENTRIES = 6;

// LRU cache of fully assembled File objects keyed by normalized URL
const _fileCache = new Map();
// Partial chunk buffer keyed by normalized URL so interrupted downloads resume after screen lock
const _partialCache = new Map();

function _touchCache(key, entry, maxEntries = DEFAULT_MAX_CACHE_ENTRIES) {
  if (_fileCache.has(key)) {
    _fileCache.delete(key);
  }
  _fileCache.set(key, entry);
  while (_fileCache.size > maxEntries) {
    const oldestKey = _fileCache.keys().next().value;
    if (oldestKey === undefined) break;
    _fileCache.delete(oldestKey);
  }
}

/**
 * Resolves a clean `.mp4` filename from an explicit filename or URL.
 */
export function resolveVideoFilename(url, explicitFilename = '') {
  const trimmed = String(explicitFilename || '').trim();
  if (trimmed) {
    return trimmed.toLowerCase().endsWith('.mp4') ? trimmed : `${trimmed}.mp4`;
  }
  try {
    const rawPath = String(url || '').split('?')[0].split('#')[0];
    const base = decodeURIComponent(rawPath.split('/').filter(Boolean).pop() || '');
    if (base) {
      return base.toLowerCase().endsWith('.mp4') ? base : `${base}.mp4`;
    }
  } catch {
    // Fallback below
  }
  return 'omnicut_clip.mp4';
}

/**
 * Appends `download=1` to a media URL so the backend sends `Content-Disposition: attachment`.
 */
export function withDownloadParam(rawUrl) {
  const str = String(rawUrl || '').trim();
  if (!str) return '';
  try {
    const isAbsolute = /^https?:\/\//i.test(str);
    const parsed = new URL(str, 'http://local.invalid');
    parsed.searchParams.set('download', '1');
    if (isAbsolute) return parsed.toString();
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    const sep = str.includes('?') ? '&' : '?';
    return `${str}${sep}download=1`;
  }
}

/**
 * Parses an HTTP `Content-Range` header such as `bytes 0-4194303/31457280`.
 * Returns `{ start, end, total }` or `null` if invalid.
 */
export function parseContentRange(headerValue) {
  if (typeof headerValue !== 'string') return null;
  const match = headerValue.trim().match(/^bytes\s+(\d+)-(\d+)\/(\d+|\*)$/i);
  if (!match) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  const total = match[3] === '*' ? null : Number(match[3]);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return null;
  return { start, end, total: Number.isFinite(total) ? total : null };
}

/**
 * Returns a previously prefetched `File` from the in-memory LRU cache, or `null`.
 */
export function getCachedVideoFile(url, filename = '') {
  const key = String(url || '').trim();
  if (!key || !_fileCache.has(key)) return null;
  const cached = _fileCache.get(key);
  _touchCache(key, cached);
  const desiredName = resolveVideoFilename(url, filename || cached.name);
  if (cached.name === desiredName) return cached;
  return new File([cached], desiredName, { type: 'video/mp4', lastModified: cached.lastModified });
}

/**
 * Clears both completed and partial prefetch caches.
 */
export function clearPrefetchCache() {
  _fileCache.clear();
  _partialCache.clear();
}

function _sleep(ms, signal) {
  if (!ms || ms <= 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      const err = new Error('The operation was aborted');
      err.name = 'AbortError';
      reject(err);
      return;
    }
    const timer = setTimeout(resolve, ms);
    if (signal) {
      signal.addEventListener(
        'abort',
        () => {
          clearTimeout(timer);
          const err = new Error('The operation was aborted');
          err.name = 'AbortError';
          reject(err);
        },
        { once: true },
      );
    }
  });
}

function _getHeader(headers, name) {
  if (!headers) return null;
  if (typeof headers.get === 'function') {
    return headers.get(name) ?? headers.get(name.toLowerCase()) ?? null;
  }
  const lower = name.toLowerCase();
  for (const [k, v] of Object.entries(headers)) {
    if (k.toLowerCase() === lower) return v;
  }
  return null;
}

/**
 * Downloads an MP4 in 4 MiB HTTP Range chunks (resumable from the last completed
 * chunk on network hiccup, falling back to single GET if server returns 200),
 * assembles a `File([blob], filename, { type: 'video/mp4' })`, caches it in an
 * in-memory LRU map, and reports `{ loaded, total, percent }` via `onProgress`.
 */
export async function prefetchVideoFile(
  url,
  {
    filename = '',
    chunkSize = DEFAULT_CHUNK_SIZE,
    onProgress = null,
    signal = undefined,
    fetchImpl = globalThis.fetch,
    maxRetries = 3,
    retryDelayMs = 150,
  } = {},
) {
  const cleanUrl = String(url || '').trim();
  if (!cleanUrl) {
    throw new Error('URL สำหรับดาวน์โหลดวิดีโอไม่ถูกต้อง');
  }
  if (typeof fetchImpl !== 'function') {
    throw new Error('ไม่รองรับ fetch API ในสภาพแวดล้อมนี้');
  }

  const resolvedName = resolveVideoFilename(cleanUrl, filename);
  const cached = getCachedVideoFile(cleanUrl, resolvedName);
  if (cached) {
    onProgress?.({ loaded: cached.size, total: cached.size, percent: 100 });
    return cached;
  }

  const safeChunkSize = Math.max(64 * 1024, Number(chunkSize) || DEFAULT_CHUNK_SIZE);

  // Resume from partial cache if available for the same URL and chunk size
  let state = _partialCache.get(cleanUrl);
  if (!state || state.chunkSize !== safeChunkSize) {
    state = {
      chunkSize: safeChunkSize,
      offset: 0,
      total: null,
      chunks: [],
    };
    _partialCache.set(cleanUrl, state);
  } else if (state.offset > 0 && state.total) {
    const resumePct = Math.min(99, Math.round((state.offset / state.total) * 100));
    onProgress?.({ loaded: state.offset, total: state.total, percent: resumePct });
  }

  while (true) {
    if (signal?.aborted) {
      const err = new Error('การดาวน์โหลดถูกยกเลิก');
      err.name = 'AbortError';
      throw err;
    }

    const start = state.offset;
    const desiredEnd =
      state.total !== null
        ? Math.min(start + safeChunkSize - 1, state.total - 1)
        : start + safeChunkSize - 1;

    let response = null;
    let chunkBytes = null;
    let attempt = 0;

    while (true) {
      try {
        response = await fetchImpl(cleanUrl, {
          method: 'GET',
          headers: {
            Range: `bytes=${start}-${desiredEnd}`,
          },
          credentials: 'include',
          signal,
        });

        if (response.status >= 500 || response.status === 429 || response.status === 408) {
          throw new Error(`HTTP ${response.status}`);
        }
        if (!response.ok && response.status !== 206) {
          const fatalErr = new Error(`ดาวน์โหลดวิดีโอไม่สำเร็จ (HTTP ${response.status})`);
          fatalErr.status = response.status;
          fatalErr.fatal = true;
          throw fatalErr;
        }

        const buffer = await response.arrayBuffer();
        chunkBytes = new Uint8Array(buffer);
        break;
      } catch (err) {
        if (err?.name === 'AbortError' || signal?.aborted || err?.fatal) {
          throw err;
        }
        attempt += 1;
        if (attempt > maxRetries) {
          throw err;
        }
        await _sleep(retryDelayMs * attempt, signal);
      }
    }

    // Fallback: Server ignored Range and returned 200 OK with full file
    if (response.status === 200) {
      const fullSize = chunkBytes.byteLength;
      const blob = new Blob([chunkBytes], { type: 'video/mp4' });
      const file = new File([blob], resolvedName, {
        type: 'video/mp4',
        lastModified: Date.now(),
      });
      _partialCache.delete(cleanUrl);
      _touchCache(cleanUrl, file);
      onProgress?.({ loaded: fullSize, total: fullSize, percent: 100 });
      return file;
    }

    // 206 Partial Content
    const contentRange = parseContentRange(_getHeader(response.headers, 'content-range'));
    if (contentRange && contentRange.total !== null) {
      state.total = contentRange.total;
    } else if (state.total === null) {
      const contentLength = Number(_getHeader(response.headers, 'content-length'));
      if (Number.isFinite(contentLength) && contentLength > 0 && chunkBytes.byteLength < safeChunkSize) {
        state.total = start + chunkBytes.byteLength;
      }
    }

    state.chunks.push(chunkBytes);
    state.offset += chunkBytes.byteLength;

    const reachedEnd =
      chunkBytes.byteLength === 0 ||
      (state.total !== null && state.offset >= state.total) ||
      (state.total === null && chunkBytes.byteLength < safeChunkSize);

    const effectiveTotal = state.total !== null ? state.total : state.offset;
    const percent = reachedEnd
      ? 100
      : effectiveTotal > 0
        ? Math.min(99, Math.round((state.offset / effectiveTotal) * 100))
        : 0;

    onProgress?.({
      loaded: state.offset,
      total: effectiveTotal,
      percent,
    });

    if (reachedEnd) {
      break;
    }
  }

  const blob = new Blob(state.chunks, { type: 'video/mp4' });
  const file = new File([blob], resolvedName, {
    type: 'video/mp4',
    lastModified: Date.now(),
  });
  _partialCache.delete(cleanUrl);
  _touchCache(cleanUrl, file);
  return file;
}

/**
 * Triggers a clean `<a download>` with `?download=1` when Web Share is unavailable.
 */
export function triggerBrowserDownload(
  fallbackDownloadUrl,
  filename = 'omnicut_clip.mp4',
  doc = globalThis.document,
) {
  const downloadUrl = withDownloadParam(fallbackDownloadUrl);
  if (!downloadUrl || !doc || typeof doc.createElement !== 'function') {
    return downloadUrl;
  }
  const anchor = doc.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = resolveVideoFilename(downloadUrl, filename);
  anchor.rel = 'noopener';
  if (doc.body && typeof doc.body.appendChild === 'function') {
    doc.body.appendChild(anchor);
    if (typeof anchor.click === 'function') {
      anchor.click();
    }
    if (typeof doc.body.removeChild === 'function') {
      doc.body.removeChild(anchor);
    }
  } else if (typeof anchor.click === 'function') {
    anchor.click();
  }
  return downloadUrl;
}

/**
 * Calls `nav.share({ files: [preparedFile], title, text })` as the VERY FIRST
 * synchronous statement in the tap handler (zero `await` before `nav.share`!)
 * so iOS Safari never drops transient user activation.
 *
 * If `canShare` / `share` is unsupported, triggers a `<a download>` with `?download=1`.
 */
export function sharePreparedFileSync(
  preparedFile,
  {
    title = '',
    text = '',
    fallbackDownloadUrl = '',
    nav = globalThis.navigator,
    doc = globalThis.document,
  } = {},
) {
  const canShareFiles =
    Boolean(preparedFile) &&
    typeof nav?.share === 'function' &&
    (typeof nav.canShare !== 'function' || nav.canShare({ files: [preparedFile] }));

  if (canShareFiles) {
    const sharePayload = { files: [preparedFile] };
    if (title) sharePayload.title = title;
    if (text) sharePayload.text = text;

    // CRITICAL: Invoke nav.share synchronously BEFORE any await / Promise microtask
    const sharePromise = nav.share(sharePayload);
    return Promise.resolve(sharePromise).then(
      () => ({ shared: true, method: 'share' }),
      (err) => {
        if (err && (err.name === 'AbortError' || err.code === 20)) {
          return { shared: false, cancelled: true, method: 'share' };
        }
        if (fallbackDownloadUrl) {
          const downloadUrl = triggerBrowserDownload(fallbackDownloadUrl, preparedFile?.name, doc);
          return { shared: false, method: 'download', downloadUrl, error: err };
        }
        throw err;
      },
    );
  }

  const downloadUrl = triggerBrowserDownload(
    fallbackDownloadUrl,
    preparedFile?.name || 'omnicut_clip.mp4',
    doc,
  );
  return Promise.resolve({
    shared: false,
    method: 'download',
    downloadUrl,
  });
}
