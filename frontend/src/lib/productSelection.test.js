import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveHistoryTargetId, resolveSelectedProduct } from './productSelection.js';

test('keeps the requested product even when it is not the first history item', () => {
  const products = [{ id: 'first' }, { id: 'selected' }];

  assert.equal(resolveSelectedProduct(products, 'selected')?.id, 'selected');
});

test('does not silently replace a missing selected product with the first item', () => {
  const products = [{ id: 'first' }, { id: 'other' }];

  assert.equal(resolveSelectedProduct(products, 'deleted-or-stale'), null);
});

test('uses the first item only when there is no requested selection', () => {
  assert.equal(resolveSelectedProduct([{ id: 'first' }], null)?.id, 'first');
});

test('keeps the local selection when the parent prop is an unchanged stale id', () => {
  assert.equal(resolveHistoryTargetId('parent-old', 'parent-old', 'local-selected'), 'local-selected');
});

test('honours a newly changed parent selection', () => {
  assert.equal(resolveHistoryTargetId('parent-new', 'parent-old', 'local-selected'), 'parent-new');
});

test('uses fallback id when both external and local ids are null', () => {
  assert.equal(resolveHistoryTargetId(null, null, null, 'persisted-fallback'), 'persisted-fallback');
});
