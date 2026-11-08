import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const mediaHubPath = path.resolve(__dirname, '../components/MediaAssetsHub.jsx');
const analyticsHubPath = path.resolve(__dirname, '../components/analytics/AnalyticsHub.jsx');
const metricCardPath = path.resolve(__dirname, '../components/analytics/MetricKpiCard.jsx');
const metricCardCompPath = path.resolve(__dirname, '../components/analytics/components/MetricKpiCard.jsx');

test('MediaAssetsHub adheres to Obsidian Pro Dark NLE tokens and audio standards', () => {
  const source = fs.readFileSync(mediaHubPath, 'utf8');

  // Obsidian Pro Dark tokens
  assert.match(source, /border-white\/\[0\.08\]/);

  // AI Voice Cast and Personas (Rules 4.5 & 20)
  assert.match(source, /Fenrir/);
  assert.match(source, /Aoede/);
  assert.match(source, /Puck/);

  // Audio mix standards
  assert.match(source, /0\.28/); // SFX 28%
  assert.match(source, /0\.12/); // BGM 12%

  // MPC Drum Pads and Sticky Player
  assert.match(source, /w-11\s+h-11\s+sm:w-9\s+sm:h-9/);
  assert.match(source, /fixed\s+bottom-\[calc\(var\(--nav-h[^>]*glass-panel/);
  assert.match(source, /<span>หยุดเล่น<\/span>/);

  // Glass tokens
  const glassPanelCount = (source.match(/glass-panel/g) || []).length;
  const glassTileCount = (source.match(/glass-tile/g) || []).length;
  assert.ok(glassPanelCount >= 3, `Expected at least 3 glass-panel, found ${glassPanelCount}`);
  assert.ok(glassTileCount >= 1, `Expected at least 1 glass-tile, found ${glassTileCount}`);
});

test('AnalyticsHub integrates PageHeader and 5 Obsidian Pro Dark tabs', () => {
  const source = fs.readFileSync(analyticsHubPath, 'utf8');

  // PageHeader integration
  assert.match(source, /import\s+.*PageHeader.*from\s+['"]\.\.\/ui['"]/);
  assert.match(source, /<PageHeader/);

  // 5 Primary tabs
  assert.match(source, /id:\s*['"]production['"]/);
  assert.match(source, /id:\s*['"]performance['"]/);
  assert.match(source, /id:\s*['"]tokens['"]/);
  assert.match(source, /id:\s*['"]storage['"]/);
  assert.match(source, /id:\s*['"]inventory['"]/);

  // Obsidian Pro Dark styling
  assert.match(source, /border-white\/\[0\.0[68]\]/);
});

test('MetricKpiCard is available at canonical and components paths with pro typography', () => {
  assert.ok(fs.existsSync(metricCardPath), 'MetricKpiCard.jsx must exist at frontend/src/components/analytics/MetricKpiCard.jsx');
  assert.ok(fs.existsSync(metricCardCompPath), 'MetricKpiCard.jsx must exist at frontend/src/components/analytics/components/MetricKpiCard.jsx');

  const source = fs.readFileSync(metricCardPath, 'utf8');
  assert.match(source, /text-2xl\s+font-black/);
  assert.match(source, /font-mono/);
  assert.match(source, /border-white\/\[0\.08\]/);
});

test('MediaAssetsHub and AnalyticsHub comply with button hygiene (Rules 3.8/4.8)', () => {
  for (const filePath of [mediaHubPath, analyticsHubPath]) {
    const source = fs.readFileSync(filePath, 'utf8');
    const buttonMatches = source.match(/<button\b[^>]*>([\s\S]*?)<\/button>/g) || [];
    for (const btn of buttonMatches) {
      const textOnly = btn.replace(/<[^>]+>/g, '').replace(/\{[^}]*\}/g, '').trim();
      assert.doesNotMatch(textOnly, /^\+\s+[ก-๙a-zA-Z]/, `Found leading '+' in button: ${textOnly}`);
      assert.doesNotMatch(textOnly, /^[⚡⚠️🎙️✨🔥🚀🎬➕]/, `Found leading emoji in button: ${textOnly}`);
    }
  }
});
