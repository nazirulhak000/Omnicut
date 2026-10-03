/** One decoder following source time. No independent timeline or image sequence. */
export function createCutoutVideoPlayback(video, refresh = () => {}) {
  let disposed = false;
  let frameCallback = null;
  let target = 0;
  let playing = false;
  let fps = 30;
  let presented = null;
  let waiting = true;
  let lastTarget = null;
  let lastNow = null;
  let playPending = false;
  const metrics = { seeks: 0, frames: 0, rejectedFrames: 0 };
  const tolerance = () => 1.5 / fps;
  const publish = () => {
    video._cutoutTargetTime = target;
    video._cutoutPresentedTime = presented;
    video._cutoutWaitingForFrame = waiting;
  };
  const play = () => {
    if (disposed || !video.paused || playPending || video.readyState < 2) return;
    playPending = true;
    Promise.resolve(video.play()).catch(() => {}).finally(() => { playPending = false; });
  };
  const ready = () => !disposed && !video.error && video.readyState >= 2
    && !video.seeking && presented != null && Math.abs(presented - target) <= tolerance();
  const onFrame = (_now, metadata) => {
    if (disposed) return;
    metrics.frames += 1;
    // A queued callback can belong to a seek that has already been superseded.
    if (!video.seeking && Math.abs(metadata.mediaTime - target) <= tolerance()) {
      presented = metadata.mediaTime;
      const wasWaiting = waiting;
      waiting = false;
      publish();
      if (!playing) video.pause();
      if (wasWaiting) refresh();
    } else {
      presented = metadata.mediaTime;
      metrics.rejectedFrames += 1;
      publish();
    }
    frameCallback = video.requestVideoFrameCallback(onFrame);
  };
  const onLoaded = () => { play(); refresh(); };
  const onSeeked = () => {
    // Browsers without rVFC expose the decoded paused frame after seeked.
    if (!video.requestVideoFrameCallback) {
      presented = video.currentTime;
      waiting = false;
      publish();
    } else if (!ready()) play();
    refresh();
  };
  const onError = () => refresh();
  video.addEventListener('loadeddata', onLoaded);
  video.addEventListener('seeked', onSeeked);
  video.addEventListener('error', onError);
  if (video.requestVideoFrameCallback) frameCallback = video.requestVideoFrameCallback(onFrame);
  publish();
  return {
    metrics,
    ready,
    sync({ time, isPlaying = false, rate = 1, frameRate = 30, now = performance.now() }) {
      if (disposed) return false;
      fps = Number.isFinite(frameRate) && frameRate > 0 ? frameRate : 30;
      target = Math.max(0, Number(time) || 0);
      if (Number.isFinite(video.duration)) target = Math.min(target, Math.max(0, video.duration - 1 / fps));
      publish();
      playing = isPlaying;
      const baseRate = Math.max(0.0625, Math.min(16, Number(rate) || 1));
      const elapsed = lastNow == null ? 0 : Math.max(0, (now - lastNow) / 1000);
      const discontinuity = lastTarget != null
        && Math.abs(target - lastTarget - (playing ? elapsed * baseRate : 0)) > 0.15;
      lastTarget = target;
      lastNow = now;
      const drift = video.currentTime - target;
      const pausedMismatch = !playing && (presented == null || Math.abs(presented - target) > 0.75 / fps);
      // Source loading can start this decoder early, and a busy compositor can
      // leave it behind. Beyond the drawable frame window, rate-only recovery
      // would hide the subject for hundreds of milliseconds. Resynchronise the
      // decoder while retaining the stricter paused frame selection.
      const needsSeek = discontinuity || Math.abs(drift) > (playing ? tolerance() : 0.75 / fps);
      if (needsSeek && (!video.seeking || discontinuity)) {
        presented = null;
        waiting = true;
        publish();
        video.currentTime = target;
        metrics.seeks += 1;
      }
      // Follow the frame that Canvas will draw, rather than only currentTime:
      // Chromium can present an upcoming frame ahead of its playback clock.
      // Bounded rate corrections keep small phase drift out of the strict frame
      // readiness window without repeatedly flushing the decoder with seeks.
      const presentationDrift = presented == null ? drift : presented - target;
      const correction = playing && !needsSeek ? Math.max(-0.1, Math.min(0.1, -presentationDrift * 6)) : 0;
      video.playbackRate = Math.max(0.0625, Math.min(16, baseRate * (1 + correction)));
      if (!video.requestVideoFrameCallback && !video.seeking && video.readyState >= 2) {
        presented = video.currentTime;
        publish();
      }
      if (playing || pausedMismatch || waiting) play();
      else if (!video.paused) video.pause();
      return ready();
    },
    deactivate() { playing = false; video.pause(); lastTarget = lastNow = null; },
    dispose() {
      disposed = true;
      if (frameCallback != null && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(frameCallback);
      video.removeEventListener('loadeddata', onLoaded);
      video.removeEventListener('seeked', onSeeked);
      video.removeEventListener('error', onError);
      video.pause();
      video.removeAttribute('src');
      video.load();
    },
  };
}
