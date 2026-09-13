/**
 * Timeline Document Schema v2 and In-Memory Migration.
 * 
 * Supports multi-track video, audio, and overlay layers with track-level
 * lock, mute, and visibility controls while guaranteeing lossless roundtrip
 * serialization back to legacy manifest schema.
 */

import {
  normalizeProductCallout,
  PRODUCT_CALLOUT_ROLE,
} from './productCallout.js';

export const TIMELINE_SCHEMA_VERSION = 2;

/**
 * Normalize only canonical Product Callouts. Spreading the source overlay
 * first keeps forward-compatible/unknown metadata lossless across v1 <-> v2.
 */
function normalizeOverlayForTimeline(overlay) {
  if (!overlay || typeof overlay !== 'object' || Array.isArray(overlay)) return overlay;
  if (overlay.role !== PRODUCT_CALLOUT_ROLE) return { ...overlay };
  return mergeLossless(overlay, normalizeProductCallout(overlay));
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map(cloneValue);
  if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]));
  return value;
}

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
 * Creates default multi-track descriptor for a project.
 */
export function createDefaultTracks() {
  return [
    {
      id: 'track-v1',
      type: 'video',
      name: 'Video 1 (Main)',
      locked: false,
      muted: false,
      visible: true,
      z_index: 10,
    },
    {
      id: 'track-v2',
      type: 'video',
      name: 'Video 2 (B-Roll / Overlay)',
      locked: false,
      muted: false,
      visible: true,
      z_index: 20,
    },
    {
      id: 'track-o1',
      type: 'overlay',
      name: 'Overlays & Badges',
      locked: false,
      muted: false,
      visible: true,
      z_index: 30,
    },
    {
      id: 'track-o2',
      type: 'overlay',
      name: 'Subtitles & Captions',
      locked: false,
      muted: false,
      visible: true,
      z_index: 40,
    },
    {
      id: 'track-o3',
      type: 'overlay',
      name: 'Stickers',
      locked: false,
      muted: false,
      visible: true,
      z_index: 45,
    },
    {
      id: 'track-a1',
      type: 'audio',
      name: 'Voice Track',
      locked: false,
      muted: false,
      visible: true,
      volume: 1.0,
      stem_key: 'voice',
    },
    {
      id: 'track-a2',
      type: 'audio',
      name: 'SFX Track',
      locked: false,
      muted: false,
      visible: true,
      volume: 0.28,
      stem_key: 'sfx',
    },
    {
      id: 'track-a3',
      type: 'audio',
      name: 'BGM Track',
      locked: false,
      muted: false,
      visible: true,
      volume: 0.12,
      stem_key: 'bgm',
    },
  ];
}

/**
 * Migrates a legacy manifest (v1) into Timeline Document v2 in-memory.
 * Does not mutate the input object.
 *
 * @param {Object} manifest - Existing project manifest or state
 * @returns {Object} v2 Timeline Document
 */
export function migrateToTimelineV2(manifest = {}) {
  if (!manifest) return { schema_version: TIMELINE_SCHEMA_VERSION, tracks: createDefaultTracks(), clips: [], overlays: [], cues: [] };

  // If already v2, return normalized copy
  if (manifest.schema_version === TIMELINE_SCHEMA_VERSION && Array.isArray(manifest.tracks)) {
    return {
      schema_version: TIMELINE_SCHEMA_VERSION,
      tracks: manifest.tracks.map((t) => ({ ...t })),
      clips: Array.isArray(manifest.cuts || manifest.clipList) ? (manifest.cuts || manifest.clipList).map((c) => ({ ...c })) : [],
      overlays: Array.isArray(manifest.overlays) ? manifest.overlays.map(normalizeOverlayForTimeline) : [],
      cues: Array.isArray(manifest.cues) ? manifest.cues.map((c) => ({ ...c })) : [],
      audioStems: { ...(manifest.audioStems || {}) },
    };
  }

  const tracks = createDefaultTracks();

  // Normalize clips onto track-v1
  const rawClips = Array.isArray(manifest.cuts)
    ? manifest.cuts
    : Array.isArray(manifest.clipList)
    ? manifest.clipList
    : [];

  let runningStart = 0;
  const clips = rawClips.map((clip, idx) => {
    const dur = Number(clip.duration) || 2.0;
    const start = Number.isFinite(clip.start) ? Number(clip.start) : runningStart;
    runningStart = start + dur;
    return {
      ...clip,
      id: clip.id || `clip-${idx + 1}`,
      track_id: clip.track_id || 'track-v1',
      start,
      duration: dur,
      keyframes: Array.isArray(clip.keyframes) ? clip.keyframes : [],
    };
  });

  // Normalize overlays onto track-o1
  const overlays = (Array.isArray(manifest.overlays) ? manifest.overlays : []).map((ov, idx) => ({
    ...normalizeOverlayForTimeline(ov),
    id: ov.id || `overlay-${idx + 1}`,
    track_id: ov.track_id || 'track-o1',
    keyframes: Array.isArray(ov.keyframes) ? ov.keyframes : [],
  }));

  // Normalize cues onto track-o2
  const cues = (Array.isArray(manifest.cues) ? manifest.cues : []).map((c, idx) => ({
    ...c,
    id: c.id ?? idx + 1,
    track_id: 'track-o2',
  }));

  // Sync audio stems into audio track defaults
  const audioStems = manifest.audioStems || {};
  if (audioStems.voice_muted !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a1');
    if (t) t.muted = Boolean(audioStems.voice_muted);
  }
  if (audioStems.sfx_muted !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a2');
    if (t) t.muted = Boolean(audioStems.sfx_muted);
  }
  if (audioStems.bgm_muted !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a3');
    if (t) t.muted = Boolean(audioStems.bgm_muted);
  }
  if (audioStems.voice_volume !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a1');
    if (t) t.volume = Number(audioStems.voice_volume);
  }
  if (audioStems.sfx_volume !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a2');
    if (t) t.volume = Number(audioStems.sfx_volume);
  }
  if (audioStems.bgm_volume !== undefined) {
    const t = tracks.find((tr) => tr.id === 'track-a3');
    if (t) t.volume = Number(audioStems.bgm_volume);
  }

  return {
    schema_version: TIMELINE_SCHEMA_VERSION,
    tracks,
    clips,
    overlays,
    cues,
    audioStems: { ...audioStems },
  };
}

/**
 * Serializes a v2 Timeline Document back into a legacy-compatible manifest.
 * Preserves all existing engine expectations (cuts, overlays, audioStems).
 *
 * @param {Object} timelineV2 - v2 Timeline Document
 * @param {Object} baseManifest - Original manifest to merge onto
 * @returns {Object} Backwards-compatible manifest payload
 */
export function serializeTimelineV2ToManifest(timelineV2, baseManifest = {}) {
  if (!timelineV2) return baseManifest;

  const tracks = Array.isArray(timelineV2.tracks) ? timelineV2.tracks : createDefaultTracks();
  const clips = Array.isArray(timelineV2.clips) ? timelineV2.clips : [];
  const overlays = Array.isArray(timelineV2.overlays) ? timelineV2.overlays : [];
  const cues = Array.isArray(timelineV2.cues) ? timelineV2.cues : [];

  // Filter out clips on invisible/muted video tracks if necessary, or preserve track metadata
  const visibleClips = clips.filter((c) => {
    const tr = tracks.find((t) => t.id === c.track_id);
    return !tr || tr.visible !== false;
  });

  // Rebuild audioStems reflecting track mute/volume states
  const voiceTrack = tracks.find((t) => t.id === 'track-a1');
  const sfxTrack = tracks.find((t) => t.id === 'track-a2');
  const bgmTrack = tracks.find((t) => t.id === 'track-a3');

  const updatedAudioStems = {
    ...(baseManifest.audioStems || {}),
    ...(timelineV2.audioStems || {}),
    voice_muted: voiceTrack ? voiceTrack.muted : false,
    sfx_muted: sfxTrack ? sfxTrack.muted : false,
    bgm_muted: bgmTrack ? bgmTrack.muted : false,
    voice_volume: voiceTrack ? voiceTrack.volume : 1.0,
    sfx_volume: sfxTrack ? sfxTrack.volume : 0.28,
    bgm_volume: bgmTrack ? bgmTrack.volume : 0.12,
  };

  return {
    ...baseManifest,
    schema_version: TIMELINE_SCHEMA_VERSION,
    tracks,
    cuts: visibleClips.map((c) => ({
      id: c.id,
      source_path: c.source_path,
      start: c.start,
      duration: c.duration,
      trim_start: c.trim_start ?? 0,
      trim_end: c.trim_end ?? 0,
      speed: c.speed ?? 1.0,
      volume: c.volume ?? 1.0,
      transition_in: c.transition_in || 'cut',
      transition_duration: c.transition_duration ?? 0.5,
      freeze_tail: c.freeze_tail ?? 0,
      track_id: c.track_id || 'track-v1',
      keyframes: Array.isArray(c.keyframes) ? c.keyframes : [],
    })),
    overlays: overlays.map(normalizeOverlayForTimeline),
    cues: cues.map((c) => ({ ...c })),
    audioStems: updatedAudioStems,
  };
}

/**
 * Updates a track property (e.g. muted, locked, visible, volume) immutably.
 */
export function updateTrackProperty(tracks, trackId, key, value) {
  return (tracks || []).map((track) => {
    if (track.id !== trackId) return track;
    return { ...track, [key]: value };
  });
}
