import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import {
  createFilmstripCache,
  filmstripKey,
  filmstripRequestCount,
  filmstripSlotCount,
  filmstripTileStyles,
  filmstripUrl,
  filmstripWindow,
} from '../../../lib/timelineFilmstrip';

// One registry and one small queue for the whole page: two clips cut from the
// same window share a sprite, and at most two sprites are fetched at a time
// (each one is several ffmpeg seeks on the backend).
const cache = createFilmstripCache();
const MAX_PARALLEL = 2;
const queue = [];
const inflight = new Map(); // url -> Promise<entry|null>
let running = 0;

function pump() {
  while (running < MAX_PARALLEL && queue.length) {
    const job = queue.shift();
    running += 1;
    const img = new Image();
    img.decoding = 'async';
    const done = (entry) => {
      running -= 1;
      inflight.delete(job.url);
      job.resolve(entry);
      pump();
    };
    img.onload = () => {
      if (img.naturalWidth > 0 && img.naturalHeight > 0) {
        done(cache.store(job.key, { url: job.url, count: job.count, naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight }));
        return;
      }
      // An empty image is as useless as an error: remember it so it is not asked for again.
      cache.fail(job.url);
      done(null);
    };
    img.onerror = () => { cache.fail(job.url); done(null); };
    img.src = job.url;
  }
}

function loadSprite(key, url, count) {
  if (inflight.has(url)) return inflight.get(url);
  const promise = new Promise((resolve) => { queue.push({ key, url, count, resolve }); });
  inflight.set(url, promise);
  pump();
  return promise;
}

const DEBOUNCE_MS = 350;

/**
 * Thumbnails behind a timeline clip. Loads only once the clip has been on
 * screen, waits for trim/zoom to settle before asking for a new sprite, keeps
 * showing the previous sprite meanwhile, and renders nothing if the endpoint
 * fails -- the clip then looks exactly as it did without thumbnails.
 */
function ClipFilmstrip({ sourcePath, trimStart = 0, trimEnd = null, width }) {
  const rootRef = useRef(null);
  const [visible, setVisible] = useState(false);
  const [height, setHeight] = useState(0);
  const [, setLoadedTick] = useState(0);
  const lastShownRef = useRef(null);

  const win = useMemo(
    () => filmstripWindow({ source_path: sourcePath, trim_start: trimStart, trim_end: trimEnd }),
    [sourcePath, trimStart, trimEnd],
  );
  const key = filmstripKey(win);
  const slots = filmstripSlotCount(width);
  const wantCount = filmstripRequestCount(slots);

  // Settled request: trim drags and zoom bursts change `key`/`wantCount` on
  // every pointer move; only the value that holds still for DEBOUNCE_MS is
  // fetched.
  const [settled, setSettled] = useState({ key, wantCount });
  useEffect(() => {
    if (settled.key === key && settled.wantCount === wantCount) return undefined;
    const t = setTimeout(() => setSettled({ key, wantCount }), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [key, wantCount, settled.key, settled.wantCount]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return undefined;
    if (typeof IntersectionObserver === 'undefined') { setVisible(true); return undefined; }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setVisible(true);
        io.disconnect();
      }
    }, { rootMargin: '0px 300px' });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return undefined;
    setHeight(el.clientHeight);
    if (typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(() => setHeight(el.clientHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!visible || !win || settled.key !== key) return undefined;
    if (!cache.needs(key, settled.wantCount)) return undefined;
    const url = filmstripUrl(win, settled.wantCount);
    if (cache.hasFailed(url)) return undefined;
    let alive = true;
    loadSprite(key, url, settled.wantCount).then((entry) => {
      if (alive && entry) setLoadedTick((n) => n + 1);
    });
    return () => { alive = false; };
  }, [visible, win, key, settled.key, settled.wantCount]);

  const current = key ? cache.best(key) : null;
  if (current) lastShownRef.current = current;
  const sprite = current || lastShownRef.current;

  const styles = useMemo(() => (sprite ? filmstripTileStyles({
    slots,
    count: sprite.count,
    naturalWidth: sprite.naturalWidth,
    naturalHeight: sprite.naturalHeight,
    slotWidth: slots ? width / slots : 0,
    slotHeight: height,
  }) : []), [sprite, slots, width, height]);

  return (
    <div
      ref={rootRef}
      aria-hidden="true"
      data-filmstrip={sprite ? 'loaded' : 'empty'}
      data-filmstrip-count={sprite?.count || 0}
      className="pointer-events-none absolute inset-0 flex overflow-hidden opacity-80"
    >
      {styles.map((style, i) => (
        <div
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          className="h-full flex-1 bg-no-repeat"
          style={{ ...style, backgroundImage: `url("${sprite.url}")` }}
        />
      ))}
    </div>
  );
}

export default memo(ClipFilmstrip);
