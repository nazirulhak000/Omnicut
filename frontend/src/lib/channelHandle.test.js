import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { HANDLE_ERROR_MESSAGES, normalizeHandle } from './channelHandle.js';

// Same vectors as tests/test_channel_registry.py (Python normalize_handle).
const fixture = JSON.parse(
  readFileSync(new URL('../../../tests/fixtures/channel_handle_cases.json', import.meta.url), 'utf-8'),
);

test('shared handle fixture is non-trivial', () => {
  assert.ok(fixture.cases.length >= 40);
  assert.ok(fixture.cases.some((c) => 'expected' in c));
  assert.ok(fixture.cases.some((c) => 'error' in c));
});

for (const [index, testCase] of fixture.cases.entries()) {
  test(`handle case ${index}: ${JSON.stringify(testCase.input)}`, () => {
    const result = normalizeHandle(testCase.input);
    if ('expected' in testCase) {
      assert.deepEqual(result, { ok: true, value: testCase.expected });
    } else {
      assert.equal(result.ok, false);
      assert.equal(result.code, testCase.error);
      assert.equal(result.message, HANDLE_ERROR_MESSAGES[testCase.error]);
      assert.ok(result.message.length > 0);
    }
  });
}

test('normalization is idempotent for every accepted value', () => {
  for (const testCase of fixture.cases) {
    if (!('expected' in testCase)) continue;
    assert.deepEqual(normalizeHandle(testCase.expected), { ok: true, value: testCase.expected });
  }
});

test('every fixture error code has a Thai message', () => {
  for (const testCase of fixture.cases) {
    if ('error' in testCase) assert.ok(HANDLE_ERROR_MESSAGES[testCase.error], testCase.error);
  }
});
