import { migrateToOverlays } from './overlayModel.js';
import { getOverlayRecolorMetadata } from './overlayRecolor.js';
import {
  normalizeProductCallout,
  PRODUCT_CALLOUT_ROLE,
} from './productCallout.js';
import { FADE_DURATION } from './timelineMath.js';

export const EMPTY_TRACK_MIX = Object.freeze({ mute: {}, solo: {} });

function firstPresent(...values) {
  return values.find((value) => value !== null && value !== undefined);
}

function firstNonEmptyArray(...values) {
  return values.find((value) => Array.isArray(value) && value.length > 0) || [];
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map(cloneValue);
  if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]));
  return value;
}

/** Merge normalized fields while retaining unknown nested metadata for future schema versions. */
function mergeLossless(raw, normalized) {
  if (Array.isArray(normalized)) {
    return normalized.map((item, index) => mergeLossless(Array.isArray(raw) ? raw[index] : undefined, item));
  }
  if (isRecord(normalized)) {
    const source = isRecord(raw) ? raw : {};
    const merged = Object.fromEntries(Object.entries(source).map(([key, value]) => [key, cloneValue(value)]));
    for (const [key, value] of Object.entries(normalized)) {
      merged[key] = mergeLossless(source[key], value);
    }
    return merged;
  }
  return cloneValue(normalized);
}

/**
 * Keep the editor's overlay contract lossless while adding defaults only to
 * canonical Product Callouts. Legacy overlays must remain byte-for-byte
 * compatible at the field level, including unknown metadata.
 */
function normalizeOverlayForPersistence(overlay) {
  if (!overlay || typeof overlay !== 'object' || Array.isArray(overlay)) return overlay;
  if (overlay.role !== PRODUCT_CALLOUT_ROLE) return { ...overlay };
  return mergeLossless(overlay, normalizeProductCallout(overlay));
}

export function serializeOverlays(overlays = []) {
  return Array.isArray(overlays) ? overlays.map(normalizeOverlayForPersistence) : [];
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
  // serializeTransitions appends clip 0's own entry transition (e.g. a fade-in) as a
  // trailing extra element on top of the normal N-1 clip-boundary entries, but only
  // when clip 0 actually carries one -- detect that shape here so it round-trips
  // instead of silently defaulting clip 0 back to 'cut'.
  const hasOpeningTransition = sourceClips.length > 0 && savedTransitions.length === sourceClips.length;
  const openingBoundary = hasOpeningTransition ? savedTransitions[savedTransitions.length - 1] : null;
  const clipBoundaries = hasOpeningTransition ? savedTransitions.slice(0, -1) : savedTransitions;

  const clipList = sourceClips.map((clip, index) => {
    const rawBoundary = index > 0 ? clipBoundaries[index - 1] : openingBoundary;
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
    scale: cue.scale !== null && cue.scale !== undefined ? Number(cue.scale) : null,
    x: cue.x !== null && cue.x !== undefined ? Number(cue.x) : null,
    y: cue.y !== null && cue.y !== undefined ? Number(cue.y) : null,
    position: cue.position || null,
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
    stickerStartTime: firstPresent(manifest.sticker_start_time, params.sticker_start_time, savedStyle.sticker_start_time, savedStyle.stickerStartTime, null),
    stickerEndTime: firstPresent(manifest.sticker_end_time, params.sticker_end_time, savedStyle.sticker_end_time, savedStyle.stickerEndTime, null),
    stickerNormX: firstPresent(manifest.sticker_norm_x, params.sticker_norm_x, savedStyle.sticker_norm_x, savedStyle.stickerNormX, null),
    stickerNormY: firstPresent(manifest.sticker_norm_y, params.sticker_norm_y, savedStyle.sticker_norm_y, savedStyle.stickerNormY, null),
    showWatermark: firstPresent(manifest.show_watermark, params.show_watermark, savedStyle.show_watermark, savedStyle.showWatermark, true),
  };

  const storedMix = firstPresent(manifest.track_mix, params.track_mix, EMPTY_TRACK_MIX) || EMPTY_TRACK_MIX;
  const storedMutes = firstPresent(manifest.audio_mutes, params.audio_mutes, storedMix.mute, {}) || {};
  const trackMix = {
    ...storedMix,
    mute: { ...(storedMix.mute || {}), ...storedMutes },
    solo: { ...(storedMix.solo || {}) },
  };

  const rawStickers = firstNonEmptyArray(manifest.stickers, params.stickers, savedStyle.stickers);
  let stickers = [];
  if (rawStickers.length > 0) {
    stickers = rawStickers.map((stk, idx) => {
      const badge = stk.badge || stk.path || '';
      const recolorMeta = getOverlayRecolorMetadata('sticker', badge);
      const requestedRecolor = stk.recolor ?? stk.tint;
      return {
        id: stk.id || `sticker-${idx}-${Date.now()}`,
        badge,
        start: Number(firstPresent(stk.start, stk.start_time, stk.startTime, 0.5)),
        end: stk.end != null ? Number(stk.end) : (stk.end_time != null ? Number(stk.end_time) : (stk.endTime != null ? Number(stk.endTime) : 3.5)),
        normX: Number(firstPresent(stk.normX, stk.norm_x, 0.8)),
        normY: Number(firstPresent(stk.normY, stk.norm_y, 0.2)),
        scale: Number(firstPresent(stk.scale, 1.0)),
        hidden: !!stk.hidden,
        ...(requestedRecolor !== undefined ? {
          recolor: requestedRecolor,
          ...(stk.recolorSourceHue != null || stk.recolor_source_hue != null ? {
            recolorSourceHue: Number(firstPresent(stk.recolorSourceHue, stk.recolor_source_hue)),
          } : {}),
        } : recolorMeta.recolorable ? {
          recolor: 'accent',
          recolorSourceHue: recolorMeta.recolor_source_hue,
        } : {}),
      };
    });
  } else if (savedStyle.stickerBadge || manifest.sticker_badge) {
    stickers = [{
      id: 'sticker-legacy-1',
      badge: savedStyle.stickerBadge || manifest.sticker_badge,
      start: Number(firstPresent(savedStyle.stickerStartTime, manifest.sticker_start_time, 0.5)),
      end: Number(firstPresent(savedStyle.stickerEndTime, manifest.sticker_end_time, 3.5)),
      normX: Number(firstPresent(savedStyle.stickerNormX, manifest.sticker_norm_x, 0.8)),
      normY: Number(firstPresent(savedStyle.stickerNormY, manifest.sticker_norm_y, 0.2)),
      scale: Number(firstPresent(savedStyle.stickerScale, manifest.sticker_scale, 1.0)),
      hidden: false,
    }];
  }

  const rawEffects = firstNonEmptyArray(manifest.effects, params.effects, []);
  const effects = rawEffects.map((fx, idx) => {
    const effectId = fx.effectId || fx.effect_id || '';
    const recolorMeta = getOverlayRecolorMetadata('effect', effectId);
    const requestedRecolor = fx.recolor ?? fx.tint;
    return {
      id: fx.id || `effect-${idx}-${Date.now()}`,
      effectId,
      start: Number(firstPresent(fx.start, fx.start_time, fx.startTime, 0.5)),
      end: fx.end != null ? Number(fx.end) : (fx.end_time != null ? Number(fx.end_time) : (fx.endTime != null ? Number(fx.endTime) : 3.5)),
      normX: Number(firstPresent(fx.normX, fx.norm_x, 0.5)),
      normY: Number(firstPresent(fx.normY, fx.norm_y, 0.35)),
      scale: Number(firstPresent(fx.scale, 1.0)),
      hidden: !!fx.hidden,
      ...(requestedRecolor !== undefined ? {
        recolor: requestedRecolor,
        ...(fx.recolorSourceHue != null || fx.recolor_source_hue != null ? {
          recolorSourceHue: Number(firstPresent(fx.recolorSourceHue, fx.recolor_source_hue)),
        } : {}),
      } : recolorMeta.recolorable ? {
        recolor: 'accent',
        recolorSourceHue: recolorMeta.recolor_source_hue,
      } : {}),
    };
  });

  return {
    clipList,
    cuesList,
    microCuesList: Array.isArray(manifest.micro_cues) ? manifest.micro_cues : [],
    overlays: serializeOverlays(migrateToOverlays(manifest)),
    stickers,
    effects,
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
  const boundaries = clipList.slice(1).map((clip) => ({
    type: clip.transition_in || 'cut',
    duration: clip.transition_duration ?? FADE_DURATION,
  }));
  // Clip 0 has no preceding clip, so it's never a "boundary" -- but it can still
  // carry its own entry transition (e.g. a fade-in on the very start of the video).
  // Append it as a trailing extra element only when it's meaningfully set, so files
  // with no opening transition keep the exact N-1-length shape they always had.
  const openingClip = clipList[0];
  if (openingClip && openingClip.transition_in && openingClip.transition_in !== 'cut') {
    boundaries.push({
      type: openingClip.transition_in,
      duration: openingClip.transition_duration ?? FADE_DURATION,
    });
  }
  return boundaries;
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
    sticker_start_time: style.stickerStartTime ?? null,
    sticker_end_time: style.stickerEndTime ?? null,
    sticker_norm_x: style.stickerNormX ?? null,
    sticker_norm_y: style.stickerNormY ?? null,
    stickerStartTime: style.stickerStartTime ?? null,
    stickerEndTime: style.stickerEndTime ?? null,
    stickerNormX: style.stickerNormX ?? null,
    stickerNormY: style.stickerNormY ?? null,
    captionScale: style.captionScale ?? 1,
    captionPosition: style.captionPosition || 'bottom',
    captionColor: style.captionColor || '#FFFFFF',
    fontName: style.fontName || 'IBMPlex',
    show_watermark: style.showWatermark !== false,
    showWatermark: style.showWatermark !== false,
  };
}

export function editorStateToSavePayload({ clipList, cuesList, microCuesList, style, overlays, trackMix, stickers, effects } = {}) {
  const cues = serializeCues(cuesList);
  // Fall back to `cues` when the caller hasn't been updated to pass microCuesList yet,
  // so this stays backward compatible instead of breaking the save outright.
  const microCues = Array.isArray(microCuesList) ? serializeCues(microCuesList) : cues;
  const mix = trackMix || EMPTY_TRACK_MIX;
  return {
    cues,
    micro_cues: microCues,
    clip_list: serializeClips(clipList),
    transitions: serializeTransitions(clipList),
    style: serializeStyle(style),
    stickers: Array.isArray(stickers) ? stickers : [],
    effects: Array.isArray(effects) ? effects : [],
    overlays: serializeOverlays(overlays),
    track_mix: mix,
    audio_mutes: mix.mute || {},
  };
}
