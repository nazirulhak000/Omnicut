import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync(new URL('../components/Sidebar.jsx', import.meta.url), 'utf8');

test('mobile QR modal exposes dialog semantics and keyboard close/focus restoration', () => {
  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /aria-labelledby="mobile-qr-title"/);
  assert.match(source, /onKeyDown/);
  assert.match(source, /event\.key !== 'Escape'/);
  assert.match(source, /closeMobileModalRef\.current\?\.focus\(\)/);
  assert.match(source, /mobileModalPreviousFocusRef\.current/);
});
