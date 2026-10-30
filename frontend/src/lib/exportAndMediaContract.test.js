import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const galleryPath = path.resolve(__dirname, '../components/ExportGallery.jsx');
const mediaPath = path.resolve(__dirname, '../components/MediaAssetsHub.jsx');

test('ExportGallery enforces 9:16 vertical video cards, 15ms haptic copy, and Web Share API', () => {
  const source = fs.readFileSync(galleryPath, 'utf8');

  // 9:16 aspect ratio
  assert.match(source, /aspect-\[9\/16\]/);

  // 15ms haptic feedback on copy
  assert.match(source, /navigator\.vibrate\?\.?\s*\(\s*15\s*\)/);

  // Web Share API support
  assert.match(source, /navigator\.share/);
});

test('ExportGallery utilizes Ultra-Realistic Glassmorphism tokens (glass-panel, glass-tile)', () => {
  const source = fs.readFileSync(galleryPath, 'utf8');

  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  const glassTileCount = (source.match(/glass-tile/g) || []).length;

  assert.ok(glassPanelCount >= 3, `Expected at least 3 glass-panel occurrences, found ${glassPanelCount}`);
  assert.ok(glassTileCount >= 2, `Expected at least 2 glass-tile occurrences, found ${glassTileCount}`);
});

test('MediaAssetsHub provides MPC-style pads and sticky mobile mini audio bar', () => {
  const source = fs.readFileSync(mediaPath, 'utf8');

  // MPC-style drum pads (44px on mobile)
  assert.match(source, /w-11\s+h-11\s+sm:w-9\s+sm:h-9/);

  // Sticky audio mini bar with glass-panel and stop button
  assert.match(source, /fixed\s+bottom-\[calc\(var\(--nav-h[^>]*glass-panel/);
  assert.match(source, /<span>หยุดเล่น<\/span>/);
});

test('MediaAssetsHub utilizes Ultra-Realistic Glassmorphism tokens (glass-panel, glass-tile)', () => {
  const source = fs.readFileSync(mediaPath, 'utf8');

  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  const glassTileCount = (source.match(/glass-tile/g) || []).length;

  assert.ok(glassPanelCount >= 3, `Expected at least 3 glass-panel occurrences, found ${glassPanelCount}`);
  assert.ok(glassTileCount >= 1, `Expected at least 1 glass-tile occurrences, found ${glassTileCount}`);
});

test('ExportGallery and MediaAssetsHub buttons comply with Rule 3.8/4.8 button hygiene', () => {
  for (const filePath of [galleryPath, mediaPath]) {
    const source = fs.readFileSync(filePath, 'utf8');
    const buttonMatches = source.match(/<button\b[^>]*>([\s\S]*?)<\/button>/g) || [];
    for (const btn of buttonMatches) {
      const textOnly = btn.replace(/<[^>]+>/g, '').replace(/\{[^}]*\}/g, '').trim();
      assert.doesNotMatch(textOnly, /^\+\s+[ก-๙a-zA-Z]/, `Found leading '+' in button: ${textOnly}`);
      assert.doesNotMatch(textOnly, /^[⚡⚠️🎙️✨🔥🚀🎬➕]/, `Found leading emoji in button: ${textOnly}`);
    }
  }
});
