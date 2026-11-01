import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LINKAGE_ENABLE_TYPES,
  isLinkageType,
  findOverlappingItems,
  shiftLinkedItems,
  groupTimelineItems,
  ungroupTimelineItems,
  findGroupMembers,
} from './timelineTrackModel.js';

test('LINKAGE_ENABLE_TYPES includes all standard CapCut 7.1 types', () => {
  const expected = ['text', 'effect', 'sticker', 'filter', 'adjust', 'sound', 'tts'];
  for (const t of expected) {
    assert.equal(isLinkageType(t), true, `Expected ${t} to be linkage type`);
    assert.equal(isLinkageType(t.toUpperCase()), true, `Expected ${t.toUpperCase()} to be linkage type`);
  }
  assert.equal(isLinkageType('unknown_type'), false);
  assert.equal(isLinkageType(null), false);
});

test('findOverlappingItems identifies items inside target window', () => {
  const items = [
    { id: 'item1', start: 0.0, end: 2.0 },
    { id: 'item2', start: 1.5, end: 3.5 },
    { id: 'item3', start: 4.0, end: 6.0 },
  ];

  // Clip window [1.0, 3.0] overlaps with item1 (0-2) and item2 (1.5-3.5), but not item3 (4-6)
  const overlapping = findOverlappingItems(items, 1.0, 3.0);
  assert.equal(overlapping.length, 2);
  assert.deepEqual(overlapping.map((i) => i.id), ['item1', 'item2']);

  // Non-overlapping window [6.0, 8.0]
  const empty = findOverlappingItems(items, 6.0, 8.0);
  assert.equal(empty.length, 0);
});

test('shiftLinkedItems adjusts only target items by deltaSec', () => {
  const items = [
    { id: 'c1', start: 1.0, end: 2.5 },
    { id: 'c2', start: 3.0, end: 4.0 },
    { id: 'c3', start: 5.0, end: 6.0 },
  ];

  const linked = new Set(['c1', 'c2']);
  const delta = 0.5;

  const shifted = shiftLinkedItems(items, linked, delta);
  assert.equal(shifted[0].start, 1.5);
  assert.equal(shifted[0].end, 3.0);
  assert.equal(shifted[1].start, 3.5);
  assert.equal(shifted[1].end, 4.5);
  // c3 is untouched
  assert.equal(shifted[2].start, 5.0);
  assert.equal(shifted[2].end, 6.0);
});

test('groupTimelineItems and ungroupTimelineItems handle sub-track groups', () => {
  const items = [
    { id: 'clipA' },
    { id: 'clipB' },
    { id: 'clipC' },
  ];

  // Group clipA and clipB
  const grouped = groupTimelineItems(items, ['clipA', 'clipB'], 'grp_123');
  assert.equal(grouped[0].groupId, 'grp_123');
  assert.equal(grouped[1].groupId, 'grp_123');
  assert.equal(grouped[2].groupId, undefined);

  // findGroupMembers
  const members = findGroupMembers(grouped, 'grp_123');
  assert.deepEqual(members.map((m) => m.id), ['clipA', 'clipB']);

  // Ungroup clipA (should ungroup all members of grp_123)
  const ungrouped = ungroupTimelineItems(grouped, 'clipA');
  assert.equal(ungrouped[0].groupId, undefined);
  assert.equal(ungrouped[1].groupId, undefined);
  assert.equal(ungrouped[2].groupId, undefined);
});
