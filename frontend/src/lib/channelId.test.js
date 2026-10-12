import test from 'node:test';
import assert from 'node:assert/strict';
import { isValidChannelId, assertChannelId } from './channelId.js';

test('channel IDs preserve the exact P1 slug and length contract', () => {
  for (const id of ['main', 'gen', 'a0', 'a_b-2', 'a'.repeat(32)]) {
    assert.equal(isValidChannelId(id), true);
    assert.equal(assertChannelId(id), id);
  }
});

test('explicit malformed IDs cannot silently become main or another scope', () => {
  for (const id of [null, undefined, 1, {}, [], '', 'a', 'a'.repeat(33), 'Main',
    ' main', 'main ', 'main\n', 'main\r\n', 'main\t', '0a', '-main', '_main',
    '../main', 'main/second', 'ช่อง', 'main%0a', 'main\0']) {
    assert.equal(isValidChannelId(id), false);
    assert.throws(() => assertChannelId(id), (error) => (
      error instanceof TypeError && error.code === 'channel_scope_invalid'
    ));
  }
});
