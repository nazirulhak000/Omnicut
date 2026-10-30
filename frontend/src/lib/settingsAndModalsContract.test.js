import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const modalPath = path.resolve(__dirname, '../components/ui/Modal.jsx');
const toastPath = path.resolve(__dirname, '../components/ui/Toast.jsx');
const settingsPath = path.resolve(__dirname, '../components/SystemSettings.jsx');
const guidePath = path.resolve(__dirname, '../components/UserGuide.jsx');
const analyticsPath = path.resolve(__dirname, '../components/analytics/AnalyticsHub.jsx');

test('Modal enforces iOS Bottom Sheet with grab handle, 80px swipe-down, 10ms haptic, and glass-panel', () => {
  const source = fs.readFileSync(modalPath, 'utf8');

  // Bottom sheet styling
  assert.match(source, /rounded-t-3xl\s+rounded-b-none\s+sm:rounded-3xl/);
  assert.match(source, /glass-panel/);

  // Swipe-down mechanics
  assert.match(source, /onTouchStart=\{handleTouchStart\}/);
  assert.match(source, /onTouchMove=\{handleTouchMove\}/);
  assert.match(source, /onTouchEnd=\{handleTouchEnd\}/);
  assert.match(source, /dragY\s*>\s*80/);
  assert.match(source, /navigator\.vibrate\?\.?\s*\(\s*10\s*\)/);

  // Accessible 44px close button
  assert.match(source, /w-11\s+h-11\s+sm:w-9\s+sm:h-9/);
});

test('Toast provides Dynamic Island top capsule with 44px touch targets', () => {
  const source = fs.readFileSync(toastPath, 'utf8');

  // Dynamic Island top anchoring
  assert.match(source, /top-\[calc\(env\(safe-area-inset-top,0px\)\+8px\)\]/);
  assert.match(source, /rounded-full/);

  // 44px mobile touch target
  assert.match(source, /pointer-coarse:min-h-11/);
});

test('SystemSettings provides >=48px section carousel pills and glass tokens', () => {
  const source = fs.readFileSync(settingsPath, 'utf8');

  assert.match(source, /min-h-\[48px\]/);
  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  assert.ok(glassPanelCount >= 5, `Expected at least 5 glass-panel in settings, found ${glassPanelCount}`);
});

test('UserGuide provides >=48px FAQ accordion with haptic feedback and glass tokens', () => {
  const source = fs.readFileSync(guidePath, 'utf8');

  assert.match(source, /min-h-\[48px\]/);
  assert.match(source, /navigator\.vibrate\?\.?\s*\(\s*10\s*\)/);
  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  assert.ok(glassPanelCount >= 3, `Expected at least 3 glass-panel in guide, found ${glassPanelCount}`);
});

test('AnalyticsHub provides >=44px tab navigation and ambient refraction', () => {
  const source = fs.readFileSync(analyticsPath, 'utf8');

  assert.match(source, /min-h-\[44px\]/);
  assert.match(source, /bg-transparent\s+relative\s+z-10/);
});

test('Settings and Guide buttons comply with Rule 3.8/4.8 button hygiene', () => {
  for (const filePath of [settingsPath, guidePath, modalPath, toastPath]) {
    const source = fs.readFileSync(filePath, 'utf8');
    const buttonMatches = source.match(/<button\b[^>]*>([\s\S]*?)<\/button>/g) || [];
    for (const btn of buttonMatches) {
      const textOnly = btn.replace(/<[^>]+>/g, '').replace(/\{[^}]*\}/g, '').trim();
      assert.doesNotMatch(textOnly, /^\+\s+[ก-๙a-zA-Z]/, `Found leading '+' in button: ${textOnly}`);
      assert.doesNotMatch(textOnly, /^[⚡⚠️🎙️✨🔥🚀🎬➕]/, `Found leading emoji in button: ${textOnly}`);
    }
  }
});
