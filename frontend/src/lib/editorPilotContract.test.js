import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

const assetPanelSource = read('../components/editor/AssetPanel.jsx');
const inspectorSource = read('../components/editor/Inspector.jsx');
const timelineSource = read('../components/editor/Timeline.jsx');
const viewToggleGroupSource = read('../components/editor/ViewToggleGroup.jsx');
const toolbarSource = read('../components/editor/Toolbar.jsx');
const contextMenuSource = read('../components/editor/timeline/TimelineContextMenu.jsx');

test('AssetPanel implements Obsidian Pro Dark NLE chrome without neon glow', () => {
  // Root styling
  assert.match(assetPanelSource, /bg-\[#0A0D14\]/);
  assert.doesNotMatch(assetPanelSource, /bg-\[#0C1019\]/);

  // Tab rail without neon glow
  assert.match(assetPanelSource, /bg-\[#080B11\]\s+p-1\s+gap-1/);
  assert.doesNotMatch(assetPanelSource, /shadow-\[0_0_12px_rgba\(37,244,238/);

  // Buttons and cards unslop
  assert.doesNotMatch(assetPanelSource, /shadow-sm shadow-\[#25F4EE\]\/20/);
  assert.doesNotMatch(assetPanelSource, /shadow-lg shadow-\[#25F4EE\]\/20/);
  assert.doesNotMatch(assetPanelSource, /bg-gradient-to-r from-\[#FE2C55\] to-\[#25F4EE\]/);
});

test('Inspector implements Obsidian Pro Dark NLE container and tabs', () => {
  // Root styling
  assert.match(inspectorSource, /bg-\[#0A0D14\]\s+text-slate-200/);
  assert.doesNotMatch(inspectorSource, /bg-\[#0C1019\]/);

  // Top tabs
  assert.match(inspectorSource, /rounded-lg text-\[11px\] sm:text-xs font-bold/);
  assert.match(inspectorSource, /bg-\[#25F4EE\]\/12 text-\[#25F4EE\] border border-\[#25F4EE\]\/25/);

  // Empty state unslop
  assert.match(inspectorSource, /rounded-xl border border-white\/\[0\.08\] bg-\[#080B11\]\/90/);
  assert.match(inspectorSource, /rounded-lg bg-cyan-500\/10 border border-cyan-500\/25/);
});

test('Timeline preserves glass-panel contract while modernizing track rows to Obsidian Pro Dark', () => {
  // Required contract for ergonomics
  assert.match(timelineSource, /<div className="flex h-full flex-col glass-panel">/);

  // Track rows modernized from legacy #181716 to #0D111A
  assert.match(timelineSource, /bg-\[#0D111A\] border border-white\/\[0\.04\]/);
  assert.doesNotMatch(timelineSource, /bg-\[#181716\]/);

  // Popover uses Obsidian Dark
  assert.match(timelineSource, /bg-\[#0D121F\]\/95/);
});

test('ViewToggleGroup applies Obsidian Pro Dark styling without neon shadows', () => {
  // Group container
  assert.match(viewToggleGroupSource, /bg-\[#0A0D14\]\/90 border border-white\/\[0\.08\] p-0\.5 rounded-lg/);

  // Clean active states without outer neon shadows
  assert.doesNotMatch(viewToggleGroupSource, /shadow-sm shadow-\[#25F4EE\]\/10/);
  assert.doesNotMatch(viewToggleGroupSource, /shadow-sm shadow-amber-400\/10/);
  assert.doesNotMatch(viewToggleGroupSource, /shadow-sm shadow-\[#D97757\]\/10/);
});

test('Toolbar and TimelineContextMenu follow Obsidian Pro Dark ergonomics', () => {
  // Toolbar touch targets and glass styling preserved
  assert.match(toolbarSource, /min-h-\[44px\]\s+min-w-\[44px\]/);
  assert.match(toolbarSource, /glass-tile/);

  // Context menu uses Obsidian Dark container
  assert.match(contextMenuSource, /bg-\[#0D121F\]\/95/);
  assert.match(contextMenuSource, /border-white\/\[0\.12\]/);
});
