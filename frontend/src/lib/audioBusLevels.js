// Per-project voice/SFX bus levels set in the Track Mix inspector (L4-05).
//
// The defaults are scripts/config.py VOICE_VOLUME / SFX_VOLUME, and the
// [0, 1] range is the same ceiling the render clamps to
// (sfx_manager._clamp_gain, then loudnorm TP=-1 on the sum), so the slider can
// never ask for a gain the export would quietly cut back.
// tests/test_preview_render_parity.py keeps these numbers equal to config.py.
//
// Upgraded with CapCut 7.1 Target Loudness (-14 LUFS, targetLoudnessIndex = 2, E2).

export const VOICE_VOLUME_DEFAULT = 1.0;
export const SFX_VOLUME_DEFAULT = 0.28;
export const BUS_VOLUME_MIN = 0;
export const BUS_VOLUME_MAX = 1;

/**
 * CapCut 7.1 Target Loudness Specification (audio_metrics, E2)
 * targetLoudnessIndex = 2 -> -14 LUFS (EBU R128 / ITU-R BS.1770-4 for mobile/social video)
 */
export const TARGET_LUFS_SOCIAL = -14.0;
export const TARGET_LUFS = TARGET_LUFS_SOCIAL;
export const TRUE_PEAK_MAX_DB = -1.0;

/**
 * Approximates LUFS from linear amplitude (RMS/Peak) using K-weighting offset (~ -0.691 dB).
 * LUFS ≈ 20 * log10(amplitude) - 0.691
 */
export function amplitudeToLufs(amplitude) {
  const amp = Math.max(1e-5, Number(amplitude) || 0);
  return Math.round((20 * Math.log10(amp) - 0.691) * 10) / 10;
}

/**
 * Returns required gain adjustment (dB and linear ratio) to hit target LUFS.
 */
export function calculateLoudnessGain(currentLufs, targetLufs = TARGET_LUFS_SOCIAL) {
  const gainDb = targetLufs - currentLufs;
  const linearGain = Math.pow(10, gainDb / 20);
  return { gainDb: Math.round(gainDb * 10) / 10, linearGain };
}

/** A finite gain in [0, 1] rounded to 3 places; anything unusable -> fallback. */
export function clampBusVolume(value, fallback) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return fallback;
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.round(Math.min(BUS_VOLUME_MAX, Math.max(BUS_VOLUME_MIN, n)) * 1000) / 1000;
}

function firstDefined(...values) {
  return values.find((v) => v !== undefined && v !== null);
}

/**
 * Voice/SFX levels stored on a project. Old manifests have neither field and
 * get the defaults, which is exactly the mix they were rendered with.
 */
export function busVolumesFromManifest(manifest = {}, savedStyle = {}) {
  const m = manifest || {};
  const params = m.render_params || {};
  const s = savedStyle || {};
  return {
    voiceVolume: clampBusVolume(
      firstDefined(m.voice_volume, params.voice_volume, s.voice_volume, s.voiceVolume),
      VOICE_VOLUME_DEFAULT,
    ),
    sfxVolume: clampBusVolume(
      firstDefined(m.sfx_volume, params.sfx_volume, s.sfx_volume, s.sfxVolume),
      SFX_VOLUME_DEFAULT,
    ),
  };
}
