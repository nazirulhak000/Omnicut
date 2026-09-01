// Peak envelope for the timeline's audio track.
//
// The mixed audio of a project is decoded once in the browser and reduced to a
// fixed number of min/max buckets. Decoding is the expensive part (a 28s wav
// is a few MB), so results are cached per url+bucket count for the life of the
// page -- switching zoom levels or re-rendering the timeline never decodes
// again.

const CACHE = new Map();

// A long file would decode into hundreds of MB of Float32 samples for a
// picture a few hundred pixels tall. Past this we read the head and say so.
export const MAX_DECODE_SECONDS = 180;

/**
 * @returns {Promise<{peaks: Float32Array, duration: number, truncated: boolean}>}
 *          peaks holds `buckets * 2` values: min, max, min, max, ...
 */
export function getAudioPeaks(url, buckets = 1200) {
  if (!url) return Promise.resolve(null);
  const key = `${url}|${buckets}`;
  if (CACHE.has(key)) return CACHE.get(key);

  const job = (async () => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`audio ${res.status}`);
    const bytes = await res.arrayBuffer();

    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    const ctx = new Ctx();
    let buffer;
    try {
      buffer = await ctx.decodeAudioData(bytes);
    } finally {
      // Chromium caps how many AudioContexts a page may hold open.
      if (ctx.state !== 'closed') ctx.close();
    }

    const rate = buffer.sampleRate;
    const truncated = buffer.duration > MAX_DECODE_SECONDS;
    const usable = Math.min(buffer.length, Math.floor(MAX_DECODE_SECONDS * rate));
    const channel = buffer.getChannelData(0);

    const peaks = new Float32Array(buckets * 2);
    const step = Math.max(1, Math.floor(usable / buckets));
    for (let b = 0; b < buckets; b++) {
      const start = b * step;
      const end = Math.min(usable, start + step);
      let min = 0;
      let max = 0;
      for (let i = start; i < end; i++) {
        const v = channel[i];
        if (v < min) min = v;
        if (v > max) max = v;
      }
      peaks[b * 2] = min;
      peaks[b * 2 + 1] = max;
    }
    return { peaks, duration: buffer.duration, truncated };
  })().catch(() => null);   // a missing or undecodable file just means no waveform

  CACHE.set(key, job);
  return job;
}

export default getAudioPeaks;
