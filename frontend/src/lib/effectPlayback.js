// Timeline-locked playback policy for looping video overlays/effects.
// The effect video is a media decoder, not a second clock. It must follow the
// editor timeline so a frame overlay starts at its configured start time and
// does not slowly drift away from the composition during preview.

export const EFFECT_PLAYBACK = Object.freeze({
  HARD_DRIFT_SECONDS: 0.14,
  SLEW_DRIFT_SECONDS: 0.018,
  START_DRIFT_SECONDS: 0.06,
  SLEW_FAST_RATE: 1.04,
  SLEW_SLOW_RATE: 0.96,
});

export function wrapEffectTime(timelineTime, effectStart, mediaDuration) {
  const duration = Number(mediaDuration);
  if (!Number.isFinite(duration) || duration <= 0) return 0;

  const elapsed = Math.max(0, (Number(timelineTime) || 0) - (Number(effectStart) || 0));
  const wrapped = elapsed % duration;
  return wrapped < 0 ? wrapped + duration : wrapped;
}

/**
 * Decide how a media element should follow the effect's timeline position.
 * This is pure so the drift policy can be tested without a browser or video.
 */
export function reconcileEffectPlayback({
  timelineTime = 0,
  effectStart = 0,
  mediaTime = 0,
  mediaDuration = 0,
  paused = false,
} = {}) {
  const start = Number(effectStart) || 0;
  if ((Number(timelineTime) || 0) < start) {
    return { action: 'idle', targetTime: 0, playbackRate: 1 };
  }

  const targetTime = wrapEffectTime(timelineTime, start, mediaDuration);
  const currentTime = Number(mediaTime) || 0;
  const drift = currentTime - targetTime;

  if (paused) {
    return {
      action: Math.abs(drift) > EFFECT_PLAYBACK.START_DRIFT_SECONDS ? 'seek-and-play' : 'play',
      targetTime,
      playbackRate: 1,
    };
  }

  if (Math.abs(drift) > EFFECT_PLAYBACK.HARD_DRIFT_SECONDS) {
    return { action: 'seek', targetTime, playbackRate: 1 };
  }
  if (drift < -EFFECT_PLAYBACK.SLEW_DRIFT_SECONDS) {
    return { action: 'slew', targetTime: null, playbackRate: EFFECT_PLAYBACK.SLEW_FAST_RATE };
  }
  if (drift > EFFECT_PLAYBACK.SLEW_DRIFT_SECONDS) {
    return { action: 'slew', targetTime: null, playbackRate: EFFECT_PLAYBACK.SLEW_SLOW_RATE };
  }
  return { action: 'hold', targetTime: null, playbackRate: 1 };
}
