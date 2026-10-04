// Keep the source's decoded clock distinct from its advancing playback clock.
export function trackPresentedSource(video) {
  let time = null;
  let callback = null;
  let disposed = false;
  const seeking = () => { time = null; };
  const frame = (_now, metadata) => {
    if (disposed) return;
    if (!video.seeking) time = metadata.mediaTime;
    callback = video.requestVideoFrameCallback(frame);
  };
  video.addEventListener('seeking', seeking);
  video.addEventListener('emptied', seeking);
  if (video.requestVideoFrameCallback) callback = video.requestVideoFrameCallback(frame);
  return {
    time: () => video.seeking ? null : (time ?? (video.paused || !video.requestVideoFrameCallback ? video.currentTime : null)),
    dispose() {
      disposed = true;
      if (callback != null) video.cancelVideoFrameCallback?.(callback);
      video.removeEventListener('seeking', seeking);
      video.removeEventListener('emptied', seeking);
    },
  };
}

export function cutoutFramesMatch(sourceTime, maskTime, sourceStart, fps = 30) {
  return [sourceTime, maskTime, sourceStart, fps].every(Number.isFinite) && fps > 0
    && Math.abs(sourceTime - sourceStart - maskTime) <= 0.5 / fps + 1e-6;
}

// One pair per source decoder. Both passes draw the same immutable RGB snapshot.
export function createCutoutFramePair(createCanvas = () => document.createElement('canvas')) {
  let pair = null;
  let key = null;
  let lastRequested = null;
  return {
    resolve({ source, mask, sourceTime, maskTime, sourceStart, fps, requestedTime, artifactKey }) {
      const changed = key !== artifactKey;
      const jumped = lastRequested != null && (requestedTime < lastRequested - 0.05 || requestedTime - lastRequested > 0.25);
      lastRequested = requestedTime;
      key = artifactKey;
      if (changed || jumped || source.seeking) pair = null;
      if (source.readyState >= 2 && (mask.readyState >= 2 || mask.complete) && !source.seeking && !mask.seeking
          && cutoutFramesMatch(sourceTime, maskTime, sourceStart, fps)) {
        if (pair?.sourceTime === sourceTime && pair?.maskTime === maskTime) return pair.subject;
        const width = source.videoWidth;
        const height = source.videoHeight;
        if (!width || !height) return null;
        const rgb = pair?.rgb || createCanvas();
        const subject = pair?.subject || createCanvas();
        for (const canvas of [rgb, subject]) {
          if (canvas.width !== width || canvas.height !== height) {
            canvas.width = width; canvas.height = height;
          }
          canvas.videoWidth = width; canvas.videoHeight = height; canvas.readyState = 4;
        }
        const rgbCtx = rgb.getContext('2d');
        rgbCtx.clearRect(0, 0, width, height);
        rgbCtx.drawImage(source, 0, 0, width, height);
        const ctx = subject.getContext('2d');
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(rgb, 0, 0);
        ctx.globalCompositeOperation = 'destination-in';
        ctx.drawImage(mask, 0, 0, width, height);
        ctx.globalCompositeOperation = 'source-over';
        subject._cutoutSourceFrame = rgb;
        pair = { rgb, subject, sourceTime, maskTime };
      }
      // Hold only within the current playback neighbourhood, never over a seek.
      return pair && Math.abs(requestedTime - pair.sourceTime) <= 0.25 ? pair.subject : null;
    },
  };
}
