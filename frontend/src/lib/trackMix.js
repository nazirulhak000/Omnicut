export const AUDIO_TRACKS = Object.freeze(['voice', 'bgm', 'sfx', 'clip']);

/** Resolve the audible buses once for Preview, persistence, and Export. */
export function effectiveAudioMutes(trackMix = {}) {
  const solo = trackMix?.solo || {};
  const mute = trackMix?.mute || {};
  const hasSolo = AUDIO_TRACKS.some((track) => !!solo[track]);
  return Object.fromEntries(AUDIO_TRACKS
    .filter((track) => (hasSolo ? !solo[track] : !!mute[track]))
    .map((track) => [track, true]));
}
