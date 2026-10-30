import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const trackerSourcePath = path.resolve(__dirname, '../components/ContentTrackerHub.jsx');

test('ContentTrackerHub defines all 4 core pipeline phases', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // Verify phase definitions
  assert.match(source, /id:\s*['"]scripted['"]/);
  assert.match(source, /id:\s*['"]in_production['"]/);
  assert.match(source, /id:\s*['"]rendered['"]/);
  assert.match(source, /id:\s*['"]posted['"]/);
});

test('ContentTrackerHub mobile sticky phase bar meets Apple HIG min 44px touch targets', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // Must have sticky bar with glass-panel and min-h-11 on mobile buttons
  assert.match(source, /sticky top-0 z-20[^>]*glass-panel/);
  assert.match(source, /min-h-11 px-2\.5 py-1 rounded-xl text-xs font-bold/);
});

test('ContentTrackerHub KanBan columns are configured for iPhone 15 Pro Max thumb-friendly snap scrolling', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // KanBan column width must be 88vw with snap-center for 430pt screen
  assert.match(source, /w-\[88vw\]\s+max-w-\[390px\]\s+xl:w-auto/);
  assert.match(source, /snap-center/);
  assert.match(source, /glass-panel/);
});

test('ContentTrackerHub adheres to Ultra-Realistic Glassmorphism tokens (glass-panel, glass-tile, glass-input)', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // Must use glass architectural tokens rather than opaque dark backgrounds
  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  const glassTileCount = (source.match(/glass-tile/g) || []).length;
  const glassInputCount = (source.match(/glass-input/g) || []).length;

  assert.ok(glassPanelCount >= 4, `Expected at least 4 glass-panel occurrences, found ${glassPanelCount}`);
  assert.ok(glassTileCount >= 4, `Expected at least 4 glass-tile occurrences, found ${glassTileCount}`);
  assert.ok(glassInputCount >= 2, `Expected at least 2 glass-input occurrences, found ${glassInputCount}`);
});

test('ContentTrackerHub ensures timer and event listener memory safety with cleanups', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // Verify clearInterval and removeEventListener calls
  assert.match(source, /clearInterval\(intervalId\)/);
  assert.match(source, /clearInterval\(pollInterval\)/);
  assert.match(source, /removeEventListener\(['"]visibilitychange['"]/);
  assert.match(source, /removeEventListener\(['"]focus['"]/);
  assert.match(source, /removeEventListener\(['"]omnicut:tracker-refresh['"]/);
});

test('ContentTrackerHub buttons comply with Rule 3.8/4.8 button hygiene', () => {
  const source = fs.readFileSync(trackerSourcePath, 'utf8');

  // Ensure no buttons have leading '+' or emojis
  const buttonMatches = source.match(/<button\b[^>]*>([\s\S]*?)<\/button>/g) || [];
  for (const btn of buttonMatches) {
    const textOnly = btn.replace(/<[^>]+>/g, '').replace(/\{[^}]*\}/g, '').trim();
    assert.doesNotMatch(textOnly, /^\+\s+[ก-๙a-zA-Z]/, `Found leading '+' in button: ${textOnly}`);
    assert.doesNotMatch(textOnly, /^[⚡⚠️🎙️✨🔥🚀🎬➕]/, `Found leading emoji in button: ${textOnly}`);
  }
});
