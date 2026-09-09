import test from 'node:test';
import assert from 'node:assert/strict';
import {
  linkClipAudio,
  unlinkClipAudio,
  computeRippleClipMove,
  packTimedLanes,
  packTextOverlays,
  packStickers,
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

test('packTimedLanes assigns deterministic lanes without mutating the input', () => {
  const items = [
    { id: 'late', start: 1.0, end: 2.0 },
    { id: 'overlap', start: 0.25, end: 1.25 },
    { id: 'first', start: 0.0, end: 0.5 },
    { id: 'epsilon', start: 1.20, end: 1.5 },
  ];
  const original = items.map((item) => ({ ...item }));

  const packed = packTimedLanes(items);

  assert.deepEqual(packed.packedItems, [
    { id: 'first', start: 0.0, end: 0.5, lane: 0 },
    { id: 'overlap', start: 0.25, end: 1.25, lane: 1 },
    { id: 'late', start: 1.0, end: 2.0, lane: 0 },
    { id: 'epsilon', start: 1.20, end: 1.5, lane: 1 },
  ]);
  assert.equal(packed.laneCount, 2);
  assert.deepEqual(items, original, 'packing does not mutate or reorder the source array');
});

test('packTimedLanes preserves the existing wrapper result contracts', () => {
  const items = [
    { id: 'a', start: 0, end: 1 },
    { id: 'b', start: 0.5, end: 1.5 },
  ];

  assert.deepEqual(packTextOverlays(items), {
    packedTextOverlays: [
      { id: 'a', start: 0, end: 1, lane: 0 },
      { id: 'b', start: 0.5, end: 1.5, lane: 1 },
    ],
    textLaneCount: 2,
  });
  assert.deepEqual(packStickers(items), {
    packedStickers: [
      { id: 'a', start: 0, end: 1, lane: 0 },
      { id: 'b', start: 0.5, end: 1.5, lane: 1 },
    ],
    stickerLaneCount: 2,
  });
});

test('packTimedLanes returns the empty contract for missing or empty input', () => {
  assert.deepEqual(packTimedLanes(), { packedItems: [], laneCount: 0 });
  assert.deepEqual(packTimedLanes([]), { packedItems: [], laneCount: 0 });
});
