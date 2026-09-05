import { migrateToOverlays } from './overlayModel.js';
import { FADE_DURATION } from './timelineMath.js';

export const EMPTY_TRACK_MIX = Object.freeze({ mute: {}, solo: {} });

function firstPresent(...values) {
  return values.find((value) => value !== null && value !== undefined);
}

function firstNonEmptyArray(...values) {
  return values.find((value) => Array.isArray(value) && value.length > 0) || [];
}

export function manifestToEditorState(data, options = {}) {
  const manifest = data || {};
  const params = manifest.render_params || {};
  const savedStyle = manifest.style || {};
  const createClipId = options.createClipId || ((index) => `clip-${index}`);
  const createCueId = options.createCueId || ((index) => `cue-${index}`);

  const fallbackPath = params.raw_video_path || manifest.raw_video_path;
  const rawClips = firstNonEmptyArray(manifest.clip_list, params.clip_list);
  const sourceClips = rawClips.length > 0
    ? rawClips
    : (fallbackPath ? [{ source_path: fallbackPath, trim_start: 0, trim_end: null }] : []);
  const savedTransitions = firstNonEmptyArray(manifest.transitions, params.transitions);

  const clipList = sourceClips.map((clip, index) => {
    const rawBoundary = index > 0 ? savedTransitions[index - 1] : null;
    const boundary = typeof rawBoundary === 'string'
      ? { type: rawBoundary }
      : (rawBoundary || {});
    return {
      ...clip,
      id: createClipId(index, clip),
      source_path: clip.source_path || clip.path || '',
      trim_start: Number(clip.trim_start) || 0,
      trim_end: clip.trim_end !== null && clip.trim_end !== undefined ? Number(clip.trim_end) : null,
      duration: Number(clip.duration) || 0,
      speed: Number(clip.speed) || 1,
      transition_in: clip.transition_in || boundary.type || 'cut',
      transition_duration: clip.transition_duration ?? boundary.duration ?? undefined,
      mirror: !!clip.mirror,
      track_id: clip.track_id || 'video-1',
      keyframes: Array.isArray(clip.keyframes) ? clip.keyframes : [],
    };
  });

  const rawCues = firstNonEmptyArray(manifest.cues, manifest.micro_cues);
  const cuesList = rawCues.map((cue, index) => ({
    start: Number(cue.start) || 0,
    end: Number(cue.end) || 0,
    text: cue.text || '',
    translation: cue.translation || '',
    sfx: cue.sfx || null,
    _uid: createCueId(index, cue),
  }));

  const rawCaptionScale = Number(firstPresent(
    manifest.caption_scale, params.caption_scale,
    savedStyle.caption_scale, savedStyle.captionScale, 1,
  ));
  const captionScale = rawCaptionScale >= 0.95 ? rawCaptionScale : 1.0;
  const style = {
    fontName: firstPresent(manifest.font_name, params.font_name, savedStyle.font_name, savedStyle.fontName, 'IBMPlex'),
    bgmName: firstPresent(manifest.bgm_name, params.bgm_name, savedStyle.bgm_name, savedStyle.bgmName, null),
    lutName: firstPresent(manifest.lut_name, params.lut_name, savedStyle.lut_name, savedStyle.lutName, null),
    lutIntensity: Number(firstPresent(manifest.lut_intensity, params.lut_intensity, savedStyle.lut_intensity, savedStyle.lutIntensity, 1)),
    stickerBadge: firstPresent(manifest.sticker_badge, params.sticker_badge, savedStyle.sticker_badge, savedStyle.stickerBadge, null),
    bgmVolume: Number(firstPresent(manifest.bgm_volume, params.bgm_volume, savedStyle.bgm_volume, savedStyle.bgmVolume, 0.12)),
    bgmDucking: !!firstPresent(manifest.bgm_ducking, params.bgm_ducking, savedStyle.bgm_ducking, savedStyle.bgmDucking, false),
    captionPosition: firstPresent(manifest.caption_position, params.caption_position, savedStyle.caption_position, savedStyle.captionPosition, 'bottom'),
    captionColor: firstPresent(manifest.caption_color, params.caption_color, savedStyle.caption_color, savedStyle.captionColor, '#FFFFFF'),
    captionScale,
    stickerPosition: firstPresent(manifest.sticker_position, params.sticker_position, savedStyle.sticker_position, savedStyle.stickerPosition, 'top_right'),
    stickerScale: Number(firstPresent(manifest.sticker_scale, params.sticker_scale, savedStyle.sticker_scale, savedStyle.stickerScale, 1)),
  };

  const storedMix = firstPresent(manifest.track_mix, params.track_mix, EMPTY_TRACK_MIX) || EMPTY_TRACK_MIX;
  const storedMutes = firstPresent(manifest.audio_mutes, params.audio_mutes, storedMix.mute, {}) || {};
  const trackMix = {
    ...storedMix,
    mute: { ...(storedMix.mute || {}), ...storedMutes },
    solo: { ...(storedMix.solo || {}) },
  };

  return {
    clipList,
    cuesList,
    microCuesList: Array.isArray(manifest.micro_cues) ? manifest.micro_cues : [],
    overlays: migrateToOverlays(manifest),
    style,
    trackMix,
    audioDuration: Number(manifest.audio_duration || manifest.total_duration) || 0,
    adTone: manifest.ad_tone || params.ad_tone || null,
    productName: manifest.product_name || params.product_name || '',
    mixedAudioPath: manifest.artifacts?.mixed_audio?.path || null,
    voiceAudioPath: manifest.artifacts?.voice_audio?.path || null,
  };
}

export function serializeClips(clipList = []) {
  return clipList.map(({ id, transition_in, transition_duration, ...clip }) => clip);
}

export function serializeTransitions(clipList = []) {
  return clipList.slice(1).map((clip) => ({
    type: clip.transition_in || 'cut',
    duration: clip.transition_duration ?? FADE_DURATION,
  }));
}

export function serializeCues(cuesList = []) {
  return cuesList.map(({ _uid, ...cue }) => cue);
}

export function serializeStyle(style = {}) {
  return {
    caption_scale: style.captionScale ?? 1,
    caption_position: style.captionPosition || 'bottom',
    caption_color: style.captionColor || '#FFFFFF',
    font_name: style.fontName || 'IBMPlex',
    bgm_name: style.bgmName || null,
    bgm_volume: style.bgmVolume ?? 0.12,
    bgm_ducking: !!style.bgmDucking,
    lut_name: style.lutName || null,
    lut_intensity: style.lutIntensity ?? 1,
    sticker_badge: style.stickerBadge || null,
    sticker_position: style.stickerPosition || 'top_right',
    sticker_scale: style.stickerScale ?? 1,
    captionScale: style.captionScale ?? 1,
    captionPosition: style.captionPosition || 'bottom',
    captionColor: style.captionColor || '#FFFFFF',
    fontName: style.fontName || 'IBMPlex',
  };
}

export function editorStateToSavePayload({ clipList, cuesList, style, overlays, trackMix } = {}) {
  const cues = serializeCues(cuesList);
  const mix = trackMix || EMPTY_TRACK_MIX;
  return {
    cues,
    micro_cues: cues,
    clip_list: serializeClips(clipList),
    transitions: serializeTransitions(clipList),
    style: serializeStyle(style),
    overlays: Array.isArray(overlays) ? overlays : [],
    track_mix: mix,
    audio_mutes: mix.mute || {},
  };
}
