import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const ptcSource = read('../components/ProductToClip.jsx');

test('ProductToClip buttons strictly comply with Rule 3.8/4.8 (no + prefix and no emojis in button spans)', () => {
  const buttons = ptcSource.match(/<button[\s\S]*?<\/button>/g) || [];
  const violations = [];

  for (const b of buttons) {
    const spans = b.match(/<span[^>]*>(.*?)<\/span>/g) || [];
    for (const s of spans) {
      const text = s.replace(/<[^>]+>/g, '').trim();
      if (!text) continue;
      if (text.startsWith('+')) {
        violations.push(`Leading '+': "${text}"`);
      }
      if (/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u.test(text)) {
        violations.push(`Leading emoji: "${text}"`);
      }
    }
  }

  assert.deepEqual(violations, [], `Found Rule 3.8/4.8 button text violations: ${JSON.stringify(violations)}`);
});

test('ProductToClip expands SessionStorage persistence to prevent data loss on mobile', () => {
  assert.ok(
    ptcSource.includes('omnicut_draft_url') &&
    ptcSource.includes('omnicut_draft_keyword') &&
    ptcSource.includes('omnicut_draft_rawtext') &&
    ptcSource.includes('omnicut_draft_tiktok_id'),
    'ProductToClip must persist draft inputs including tiktokProductId in sessionStorage'
  );
});

test('ProductToClip applies visionOS glassmorphism classes to workflow sections', () => {
  assert.ok(
    ptcSource.includes('glass-panel') || ptcSource.includes('glass-card'),
    'ProductToClip must use glassmorphism styling for primary cards'
  );
});

test('ProductToClip mobile 1-tap paste button provides haptic feedback and >=44px touch target', () => {
  assert.ok(
    ptcSource.includes('min-h-[48px]') || ptcSource.includes('min-h-11'),
    'Mobile 1-tap paste button must meet Apple HIG touch target >= 44px'
  );
  assert.ok(
    ptcSource.includes('navigator.vibrate'),
    'Mobile 1-tap paste button must trigger haptic feedback'
  );
});
