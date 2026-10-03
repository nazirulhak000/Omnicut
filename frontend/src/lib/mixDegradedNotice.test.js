import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { mixDegradedNotice, MIX_DEGRADED_FALLBACK_MESSAGE } from './mixDegradedNotice.js';

test('a healthy or unknown result shows no notice', () => {
  assert.equal(mixDegradedNotice(null), null);
  assert.equal(mixDegradedNotice(undefined), null);
  assert.equal(mixDegradedNotice({}), null);
  assert.equal(mixDegradedNotice({ mix_degraded: false, mix_degraded_reason: 'x' }), null);
  assert.equal(mixDegradedNotice({ mix_degraded: 'true' }), null, 'only a real boolean true counts');
});

test('a degraded mix shows the backend reason', () => {
  const notice = mixDegradedNotice({ mix_degraded: true, mix_degraded_reason: '  ไม่มีเพลง  ' });
  assert.deepEqual(notice, { title: 'มิกซ์เสียงไม่สมบูรณ์', message: 'ไม่มีเพลง' });
});

test('a degraded mix without a reason still says what is missing', () => {
  for (const result of [{ mix_degraded: true }, { mix_degraded: true, mix_degraded_reason: '   ' }, { mix_degraded: true, mix_degraded_reason: null }]) {
    assert.equal(mixDegradedNotice(result).message, MIX_DEGRADED_FALLBACK_MESSAGE);
  }
  assert.match(MIX_DEGRADED_FALLBACK_MESSAGE, /เพลง/);
  assert.match(MIX_DEGRADED_FALLBACK_MESSAGE, /SFX/);
});

test('the editor shows the notice in both render-finished cards', () => {
  const shell = readFileSync(new URL('../components/editor/EditorShell.jsx', import.meta.url), 'utf8');
  assert.match(shell, /import MixDegradedNotice from '\.\/MixDegradedNotice'/);
  assert.equal((shell.match(/<MixDegradedNotice result=\{applyResult\} \/>/g) || []).length, 2);
  const component = readFileSync(new URL('../components/editor/MixDegradedNotice.jsx', import.meta.url), 'utf8');
  assert.match(component, /role="alert"/);
});
