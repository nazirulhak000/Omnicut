import test from 'node:test';
import assert from 'node:assert/strict';
import { saveStatusDot } from './saveStatusIndicator.js';

// S4-08: the immersive capsule's dot was always a pulsing green.
test('capsule save dot follows the real save status', () => {
  assert.equal(saveStatusDot('saved').tone, 'saved');
  assert.match(saveStatusDot('saved').className, /emerald/);
  assert.doesNotMatch(saveStatusDot('saved').className, /pulse/, 'a settled state does not blink');
  assert.match(saveStatusDot('dirty').className, /amber/);
  assert.match(saveStatusDot('unsaved').className, /amber/);
  assert.match(saveStatusDot('saving').className, /animate-pulse/);
  assert.match(saveStatusDot('error').className, /red/);
  for (const s of ['saved', 'dirty', 'saving', 'error']) assert.ok(saveStatusDot(s).label.length > 0, s);
});

test('anything that is not a confirmed save never shows green', () => {
  for (const s of ['dirty', 'unsaved', 'saving', 'error', undefined, null, '', 'conflict']) {
    assert.doesNotMatch(saveStatusDot(s).className, /emerald/, String(s));
  }
});
