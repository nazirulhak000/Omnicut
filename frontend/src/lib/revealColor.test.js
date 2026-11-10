import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  REVEAL_FALLBACK_COLOR,
  legibleRevealHex,
  pickRevealHex,
  resolveRevealColor,
} from './revealColor.js';

// Shared with tests/test_reveal_color.py, which runs the same overlays through
// scripts/subtitle/reveal_color.py.
const CASES = JSON.parse(
  readFileSync(new URL('../../../tests/fixtures/reveal_color_parity_cases.json', import.meta.url), 'utf-8'),
);

for (const c of CASES.cases) {
  test(`reveal colour parity: ${c.name}`, () => {
    assert.equal(pickRevealHex(c.overlays), c.expected);
  });
}

test('resolveRevealColor follows the hook by default', () => {
  const overlays = [{ kind: 'hook', tiers: [{ look: { color: '#FE2C55' } }] }];
  assert.equal(resolveRevealColor(overlays), '#FE2C55');
  assert.equal(resolveRevealColor(overlays, true), '#FE2C55');
});

test('resolveRevealColor keeps the SOP green when sync is off or the hook has no accent', () => {
  const overlays = [{ kind: 'hook', tiers: [{ look: { color: '#FE2C55' } }] }];
  assert.equal(resolveRevealColor(overlays, false), REVEAL_FALLBACK_COLOR);
  assert.equal(resolveRevealColor([], true), REVEAL_FALLBACK_COLOR);
  assert.equal(REVEAL_FALLBACK_COLOR, '#66FF00');
});

test('legibleRevealHex leaves a readable colour alone', () => {
  assert.equal(legibleRevealHex('#fe2c55'), '#FE2C55');
});
