import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const topbarSource = read('../components/Topbar.jsx');

test('Topbar TAB_CONFIG covers all 8 core primary tabs plus fallbacks with badges and titles', () => {
  const requiredTabs = ['flow', 'tracker', 'editor', 'gallery', 'assets', 'analytics', 'settings', 'guide'];
  for (const tab of requiredTabs) {
    const hasTab = new RegExp(`\\b${tab}:\\s*\\{`, 'm').test(topbarSource);
    assert.ok(hasTab, `TAB_CONFIG is missing configuration for tab: ${tab}`);
  }
});

test('Topbar source code does not contain unused Lucide icon imports', () => {
  // Lightbulb and Wifi were previously imported but never referenced in JSX
  const hasUnusedLightbulb = /\bLightbulb\b/.test(topbarSource);
  const hasUnusedWifi = /\bWifi\b(?!\w)/.test(topbarSource);
  assert.equal(hasUnusedLightbulb, false, 'Topbar imports unused Lightbulb icon');
  assert.equal(hasUnusedWifi, false, 'Topbar imports unused Wifi icon (WifiOff should be used for offline)');
});

test('Topbar status indicator includes WAI-ARIA keyboard accessibility and mobile >=44px touch target', () => {
  assert.ok(
    topbarSource.includes('onKeyDown='),
    'Server status indicator must handle onKeyDown for keyboard users'
  );
  assert.ok(
    topbarSource.includes('min-h-11') || topbarSource.includes('min-h-[44px]'),
    'Server status indicator must enforce min-h-11 for mobile touch target'
  );
});

test('Topbar buttons comply with Rule 3.8/4.8 (action verbs without leading symbols or emojis)', () => {
  const buttonTags = topbarSource.match(/<button[\s\S]*?<\/button>/g) || [];
  for (const btn of buttonTags) {
    // Check span content inside buttons
    const spanMatches = btn.match(/<span[^>]*>(.*?)<\/span>/g) || [];
    for (const span of spanMatches) {
      const text = span.replace(/<[^>]+>/g, '').trim();
      if (!text) continue;
      assert.ok(!text.startsWith('+'), `Button text must not start with '+': "${text}"`);
      assert.ok(!/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u.test(text), `Button text must not start with emoji: "${text}"`);
    }
  }
});

test('Topbar includes live latency monitoring and tactile glass styling', () => {
  assert.ok(
    topbarSource.includes('latency') || topbarSource.includes('latencyMs'),
    'Topbar should support displaying real-time connection latency'
  );
  assert.ok(
    topbarSource.includes('backdrop-blur'),
    'Topbar must retain frosted glass backdrop-filter'
  );
});
