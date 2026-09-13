import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PRODUCT_CALLOUT_ORIGINS,
  PRODUCT_CALLOUT_ROLE,
  PRODUCT_CALLOUT_TYPES,
  createProductCalloutId,
  normalizeProductCallout,
  serializeProductCallout,
  validateProductCallout,
} from './productCallout.js';

test('default product callout is renderer-compatible and valid', () => {
  const callout = normalizeProductCallout({ text: 'กันน้ำ IPX7' });
  assert.equal(callout.kind, 'text');
  assert.equal(callout.role, PRODUCT_CALLOUT_ROLE);
  assert.equal(callout.callout_type, 'feature');
  assert.deepEqual(callout.timing, { start: 0, end: 2.5 });
  assert.deepEqual([callout.x, callout.y], [0.5, 0.5]);
  assert.equal(callout.tiers[0].text, 'กันน้ำ IPX7');
  assert.equal(validateProductCallout(callout).valid, true);
});

test('legacy flat text overlay migrates to semantic callout metadata', () => {
  const callout = normalizeProductCallout({
    id: 'legacy-1',
    text: '20,000mAh',
    start: 1.25,
    end: 3.75,
    position: 'top',
    scale: 1.2,
    fontName: 'Kanit',
    bgStyle: 'badge_yellow',
    anim: 'slide',
  });
  assert.deepEqual({ kind: callout.kind, role: callout.role, callout_type: callout.callout_type, origin: callout.origin }, {
    kind: 'text', role: 'product_callout', callout_type: 'feature', origin: 'imported',
  });
  assert.deepEqual(callout.timing, { start: 1.25, end: 3.75 });
  assert.deepEqual([callout.x, callout.y], [0.5, 0.2]);
  assert.equal(callout.look.font, 'Kanit');
  assert.equal(callout.look.size_pct, 120);
  assert.equal(callout.anim.in, 'rise');
  assert.equal(validateProductCallout(callout).valid, true);
});

test('validator rejects out-of-bounds normalized coordinates', () => {
  const callout = normalizeProductCallout({ text: 'รุ่น X', x: 1.01, y: -0.01 });
  const result = validateProductCallout(callout);
  assert.equal(result.valid, false);
  assert.deepEqual(result.errors, [
    'x must be normalized between 0 and 1',
    'y must be normalized between 0 and 1',
  ]);
});

test('allowed semantic roles, origins, and callout types are explicit', () => {
  assert.deepEqual(PRODUCT_CALLOUT_TYPES, ['brand', 'model', 'feature', 'spec', 'price', 'proof', 'cta']);
  assert.deepEqual(PRODUCT_CALLOUT_ORIGINS, ['auto', 'manual', 'imported']);
  const invalidRole = normalizeProductCallout({ text: 'Model X', role: 'caption' });
  assert.equal(validateProductCallout(invalidRole).valid, false);
  assert.match(validateProductCallout(invalidRole).errors[0], /role/);
});

test('ids and serialization are deterministic regardless of object key order', () => {
  const first = { text: 'Soundcore Boom Go 3i', callout_type: 'model', x: 0.5, y: 0.2 };
  const second = { y: 0.2, x: 0.5, callout_type: 'model', text: 'Soundcore Boom Go 3i' };
  assert.equal(createProductCalloutId(first), createProductCalloutId(second));
  assert.equal(serializeProductCallout(first), serializeProductCallout(second));
  assert.match(serializeProductCallout(first), /"kind":"text"/);
});

test('normalization and validation do not mutate nested input data', () => {
  const input = {
    text: 'USB-C',
    source: { kind: 'beat', beat_id: 'beat-1' },
    tiers: [{ text: 'USB-C', look: { color: '#25F4EE' } }],
    look: { shadow: { dx: 2, dy: 3 } },
    anim: { in: 'rise', loop: 'none', out: 'fade' },
  };
  const before = structuredClone(input);
  const normalized = normalizeProductCallout(input);
  normalized.source.kind = 'changed';
  normalized.tiers[0].look.color = '#FF0000';
  normalized.look.shadow.dx = 99;
  assert.deepEqual(input, before);
});
