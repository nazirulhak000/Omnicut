import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TIMELINE_SCHEMA_VERSION,
  createDefaultTracks,
  migrateToTimelineV2,
  serializeTimelineV2ToManifest,
  updateTrackProperty,
} from './timelineSchema.js';

test('createDefaultTracks returns complete set of video, overlay, and audio tracks', () => {
  const tracks = createDefaultTracks();
  assert.equal(tracks.length, 7);
  const types = tracks.map((t) => t.type);
  assert.ok(types.includes('video'));
  assert.ok(types.includes('audio'));
  assert.ok(types.includes('overlay'));

  const v1 = tracks.find((t) => t.id === 'track-v1');
  assert.equal(v1.visible, true);
  assert.equal(v1.locked, false);
  assert.equal(v1.muted, false);
});

test('migrateToTimelineV2 migrates legacy v1 manifest into valid v2 in-memory', () => {
  const legacyManifest = {
    cuts: [
      { id: 'c1', source_path: 'v1.mp4', duration: 3.0 },
      { id: 'c2', source_path: 'v2.mp4', duration: 4.5 },
    ],
    overlays: [
      { id: 'o1', type: 'hook_header', start: 0, end: 3 },
    ],
    cues: [
      { id: 1, text: 'สวัสดีครับ', start: 0.0, end: 1.5 },
    ],
    audioStems: {
      voice_muted: false,
      sfx_muted: true,
      bgm_volume: 0.20,
    },
  };

  const v2 = migrateToTimelineV2(legacyManifest);
  assert.equal(v2.schema_version, TIMELINE_SCHEMA_VERSION);
  assert.equal(v2.clips.length, 2);
  assert.equal(v2.clips[0].track_id, 'track-v1');
  assert.equal(v2.clips[0].start, 0);
  assert.equal(v2.clips[1].start, 3.0);
  assert.equal(v2.overlays.length, 1);
  assert.equal(v2.cues.length, 1);

  const sfxTrack = v2.tracks.find((t) => t.id === 'track-a2');
  assert.equal(sfxTrack.muted, true);
  const bgmTrack = v2.tracks.find((t) => t.id === 'track-a3');
  assert.equal(bgmTrack.volume, 0.20);
});

test('serializeTimelineV2ToManifest roundtrips back to legacy cuts, overlays, and audioStems', () => {
  const v2 = {
    schema_version: 2,
    tracks: createDefaultTracks(),
    clips: [
      { id: 'c1', source_path: 'a.mp4', start: 0, duration: 2.0, track_id: 'track-v1', keyframes: [{ time: 0, zoom: 1.0 }] },
    ],
    overlays: [
      { id: 'ov1', text: 'Hook', track_id: 'track-o1' },
    ],
    cues: [{ id: 1, text: 'Hi', track_id: 'track-o2' }],
    audioStems: {},
  };

  // Mutate track property
  v2.tracks = updateTrackProperty(v2.tracks, 'track-a1', 'muted', true);
  v2.tracks = updateTrackProperty(v2.tracks, 'track-a3', 'volume', 0.15);

  const serialized = serializeTimelineV2ToManifest(v2, { title: 'Test Project' });
  assert.equal(serialized.title, 'Test Project');
  assert.equal(serialized.cuts.length, 1);
  assert.equal(serialized.cuts[0].id, 'c1');
  assert.deepEqual(serialized.cuts[0].keyframes, [{ time: 0, zoom: 1.0 }]);
  assert.equal(serialized.audioStems.voice_muted, true);
  assert.equal(serialized.audioStems.bgm_volume, 0.15);
});

test('updateTrackProperty immutably updates single track without side effects', () => {
  const tracks = createDefaultTracks();
  const updated = updateTrackProperty(tracks, 'track-v1', 'locked', true);
  assert.equal(updated.find((t) => t.id === 'track-v1').locked, true);
  assert.equal(tracks.find((t) => t.id === 'track-v1').locked, false, 'original must be unchanged');
});
