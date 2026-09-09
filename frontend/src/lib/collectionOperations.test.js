import test from 'node:test';
import assert from 'node:assert/strict';
import { removeItemById, updateItemById } from './collectionOperations.js';

test('collection operations update and remove only the matching id', () => {
  const items = [{ id: 'a', value: 1 }, { id: 'b', value: 2 }];
  assert.deepEqual(updateItemById(items, 'b', { value: 3 }), [
    { id: 'a', value: 1 }, { id: 'b', value: 3 },
  ]);
  assert.deepEqual(removeItemById(items, 'a'), [{ id: 'b', value: 2 }]);
  assert.deepEqual(items, [{ id: 'a', value: 1 }, { id: 'b', value: 2 }]);
});

test('collection operations preserve no-op behavior for an unknown id', () => {
  const items = [{ id: 'a' }];
  assert.deepEqual(updateItemById(items, 'missing', { value: 1 }), items);
  assert.deepEqual(removeItemById(items, 'missing'), items);
  assert.deepEqual(removeItemById(), []);
});
