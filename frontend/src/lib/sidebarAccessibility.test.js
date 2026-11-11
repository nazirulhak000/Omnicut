import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync(new URL('../components/Sidebar.jsx', import.meta.url), 'utf8');

test('mobile QR modal exposes dialog semantics and keyboard close/focus restoration', () => {
  // Native modal <dialog> (ui/ModalLayer): Escape, focus containment and
  // focus restoration come from the browser, not hand-written listeners.
  assert.match(source, /<ModalLayer onClose=\{\(\) => setShowMobileModal\(false\)\}/);
  assert.match(source, /aria-labelledby="mobile-qr-title"/);
  assert.match(source, /autoFocus\s+onClick=\{\(\) => setShowMobileModal\(false\)\}/);
  assert.doesNotMatch(source, /mobileModalPreviousFocusRef/);
});
