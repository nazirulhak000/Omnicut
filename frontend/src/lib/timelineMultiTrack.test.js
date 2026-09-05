import test from 'node:test';
import assert from 'node:assert/strict';
import {
  linkClipAudio,
  unlinkClipAudio,
  computeRippleClipMove,
} from './timelineTrackModel.js';

test('linkClipAudio and unlinkClipAudio update audio linking attributes cleanly', () => {
  const clip = { id: 'c1', source_path: 'test.mp4', duration: 3.0 };
  const linked = linkClipAudio(clip, 'track-a1');
  assert.equal(linked.audio_linked, true);
  assert.equal(linked.linked_audio_track, 'track-a1');

  const unlinked = unlinkClipAudio(linked);
  assert.equal(unlinked.audio_linked, false);
  assert.equal(unlinked.linked_audio_track, undefined);
});

test('computeRippleClipMove shifts subsequent clips on same track deterministically', () => {
  const clips = [
    { id: 'c1', track_id: 'track-v1', start: 0.0, duration: 2.0 },
    { id: 'c2', track_id: 'track-v1', start: 2.0, duration: 3.0 },
    { id: 'c3', track_id: 'track-v1', start: 5.0, duration: 2.0 },
    { id: 'c_other', track_id: 'track-v2', start: 0.0, duration: 5.0 },
  ];

  // Move c2 from 2.0 to 3.5 (delta +1.5)
  const moved = computeRippleClipMove(clips, 'c2', 3.5);
  assert.equal(moved[0].start, 0.0, 'c1 untouched');
  assert.equal(moved[1].start, 3.5, 'c2 shifted to 3.5');
  assert.equal(moved[2].start, 6.5, 'c3 pushed from 5.0 to 6.5 (+1.5)');
  assert.equal(moved[3].start, 0.0, 'c_other on track-v2 untouched');
});
