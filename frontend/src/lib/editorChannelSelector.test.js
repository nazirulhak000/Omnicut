import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const selectorSource = read('../components/editor/EditorChannelSelector.jsx');
const headerSource = read('../components/editor/EditorHeader.jsx');
const popoverPanelSource = read('../components/ui/PopoverPanel.jsx');
const appSource = read('../App.jsx');

test('EditorChannelSelector exists, imports useChannel and renders accessible dropdown', () => {
  assert.ok(selectorSource.includes("useChannel"), 'Must import useChannel');
  assert.ok(selectorSource.includes("data-testid=\"editor-channel-selector\""), 'Must have selector test id');
  assert.ok(selectorSource.includes("aria-haspopup=\"listbox\""), 'Must have aria-haspopup="listbox"');
  assert.ok(selectorSource.includes("role=\"listbox\""), 'Must have role="listbox" on dropdown');
  assert.ok(selectorSource.includes("role=\"option\""), 'Must have role="option" on channel items');
});

test('EditorChannelSelector handles keyboard navigation (Escape to close)', () => {
  // Escape, outside press and focus return are owned by ui/PopoverPanel.
  assert.ok(selectorSource.includes('<PopoverPanel'), 'Dropdown must render through PopoverPanel');
  assert.ok(selectorSource.includes('onClose={() => setOpen(false)}'), 'PopoverPanel must be able to close the dropdown');
  assert.ok(popoverPanelSource.includes("event.key !== 'Escape'"), 'PopoverPanel must handle Escape');
});

test('EditorChannelSelector does not display redundant handle in the button pill', () => {
  // Ensure the main button pill does not render visible currentHandle next to currentDisplayName
  assert.equal(
    selectorSource.includes('>{currentHandle}'),
    false,
    'EditorChannelSelector button pill must not render visible {currentHandle}'
  );
  assert.equal(
    selectorSource.includes('{currentHandle &&'),
    false,
    'EditorChannelSelector button pill must not conditionally render currentHandle'
  );
});

test('EditorChannelSelector buttons follow Rule 3.8/4.8 (no leading +, no emojis)', () => {
  const buttonTags = selectorSource.match(/<button[\s\S]*?<\/button>/g) || [];
  for (const btn of buttonTags) {
    const spanMatches = btn.match(/<span[^>]*>(.*?)<\/span>/g) || [];
    for (const span of spanMatches) {
      const text = span.replace(/<[^>]+>/g, '').trim();
      if (!text) continue;
      assert.ok(!text.startsWith('+'), `Button text must not start with '+': "${text}"`);
      assert.ok(!/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u.test(text), `Button text must not start with emoji: "${text}"`);
    }
  }
});

test('EditorHeader integrates EditorChannelSelector next to ProjectSelector', () => {
  assert.ok(
    headerSource.includes("import EditorChannelSelector from './EditorChannelSelector.jsx'"),
    'EditorHeader must import EditorChannelSelector'
  );
  assert.ok(
    headerSource.includes("<EditorChannelSelector />"),
    'EditorHeader must render <EditorChannelSelector />'
  );
  assert.ok(
    headerSource.indexOf("<EditorChannelSelector />") < headerSource.indexOf("<ProjectSelector"),
    'EditorChannelSelector should be positioned alongside and before ProjectSelector'
  );
});

test('App.jsx removes redundant standalone ChannelWorkspaceBar over the editor', () => {
  assert.equal(
    appSource.includes("{activeTab === 'editor' && <ChannelWorkspaceBar />}"),
    false,
    'App.jsx must not render redundant ChannelWorkspaceBar on activeTab === "editor"'
  );
});

test('EditorChannelSelector provides an accessible native select for automation and combobox queries', () => {
  assert.ok(
    selectorSource.includes('aria-label="เลือกช่อง"'),
    'EditorChannelSelector must provide an accessible select with aria-label="เลือกช่อง"'
  );
  assert.ok(
    selectorSource.includes('className="sr-only"'),
    'Accessible select must be sr-only to keep Obsidian Pro UI clean'
  );
});
