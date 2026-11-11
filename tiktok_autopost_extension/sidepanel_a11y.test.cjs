// Static contract for the side panel's accessibility and overlay markup.
// The behaviour itself (focus, Escape, axe) is checked in a real browser by
// tools/extension_panel_check.py; this keeps the markup from drifting back.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
const js = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');

test('page has a header and one main landmark around the panel content', () => {
  assert.match(html, /<header class="app-header/);
  assert.equal((html.match(/<main\b/g) || []).length, 1);
  assert.ok(html.indexOf('<main') < html.indexOf('id="panelList"'));
  assert.ok(html.indexOf('</main>') > html.indexOf('id="panelTools"'));
  assert.ok(html.indexOf('</main>') < html.indexOf('id="videoPreviewModal"'), 'dialogs live outside <main>');
});

test('tabs expose the tab pattern and keep one tab in the Tab order', () => {
  assert.match(html, /class="segmented-switch" role="tablist"/);
  for (const [tab, panel] of [['tabBtnList', 'panelList'], ['tabBtnChecklist', 'panelChecklist'], ['tabBtnTools', 'panelTools']]) {
    assert.match(html, new RegExp(`id="${tab}"[^>]*role="tab"[^>]*aria-controls="${panel}"`));
    assert.match(html, new RegExp(`id="${panel}"[^>]*role="tabpanel"[^>]*aria-labelledby="${tab}"`));
  }
  assert.match(js, /btn\.setAttribute\('aria-selected', selected \? 'true' : 'false'\);/);
  assert.match(js, /btn\.tabIndex = selected \? 0 : -1;/);
  assert.match(js, /e\.key === 'ArrowRight'/);
  assert.match(js, /e\.key === 'ArrowLeft'/);
});

test('confirm and video preview are native modal dialogs', () => {
  assert.match(html, /<dialog id="confirmOverlay" class="app-dialog" aria-labelledby="confirmText">/);
  assert.match(html, /<dialog id="videoPreviewModal" class="preview-modal app-dialog" aria-labelledby="previewModalTitle">/);
  assert.match(js, /confirmOverlay\.showModal\(\)/);
  assert.match(js, /videoPreviewModal\.showModal\(\)/);
  // Escape (the dialog's cancel event) is always "no" / "close", never "yes"
  assert.match(js, /const onEscape = \(e\) => \{ e\.preventDefault\(\); cleanup\(false\); \};/);
  assert.match(js, /videoPreviewModal\?\.addEventListener\('cancel', \(e\) => \{\s*e\.preventDefault\(\);\s*closeVideoPreview\(\);/);
});

test('the safe answer comes first in the confirm dialog, so it takes initial focus', () => {
  assert.ok(html.indexOf('id="confirmCancelBtn"') < html.indexOf('id="confirmOkBtn"'));
  assert.ok(html.indexOf('id="confirmCancelBtn"') > html.indexOf('<dialog id="confirmOverlay"'));
});

test('icon-only controls and bare fields have accessible names', () => {
  for (const id of ['apiKeySettingsBtn', 'refreshBtn', 'previewCloseBtn', 'themeToggleBtn', 'apiKeyInput', 'batchLimitSelect']) {
    assert.match(html, new RegExp(`id="${id}"[^>]*aria-label="[^"]+"|aria-label="[^"]+"[^>]*id="${id}"`), `${id} needs aria-label`);
  }
  assert.match(html, /<select id="batchModeSelect"[^>]*aria-labelledby="batchModeLabel"/);
  assert.match(html, /<span id="batchModeLabel">/);
});

test('clip thumbnails are keyboard controls that load a small lazy preview', () => {
  assert.match(js, /thumbWrap\.setAttribute\('role', 'button'\);/);
  assert.match(js, /thumbWrap\.tabIndex = 0;/);
  assert.match(js, /if \(e\.key !== 'Enter' && e\.key !== ' '\) return;/);
  assert.match(js, /thumb\.loading = 'lazy';/);
  assert.match(js, /\$\{thumbUrl\.includes\('\?'\) \? '&' : '\?'\}w=160/);
});

test('motion, scrollbar and blocked-card styles follow the standards', () => {
  assert.match(html, /scrollbar-color: var\(--scrollbar-thumb\) var\(--scrollbar-track\);/);
  assert.match(html, /@supports not \(scrollbar-color: auto\)/);
  // reduced motion keeps colour feedback instead of killing every transition
  assert.doesNotMatch(html, /transition: none !important;/);
  assert.match(html, /transition-property: color, background-color, border-color, opacity, box-shadow !important;/);
  // a blocked card is never dimmed as a whole (that dimmed the reason text too)
  assert.doesNotMatch(html, /\.card\.blocked \{ opacity: 0\.55; \}/);
});

test('the export list and the schedule queue are requested together', () => {
  const start = js.indexOf('async function loadExports()');
  const body = js.slice(start, js.indexOf('filterAndRenderClips();', start));
  assert.ok(body.indexOf('queuePromise = scopedPanelFetch(`${BACKEND}/api/schedule-queue`)') < body.indexOf('await scopedPanelFetch(`${BACKEND}/api/exports`)'),
    'the queue request must start before the export request is awaited');
  assert.match(body, /const queueRes = await queuePromise;/);
});
