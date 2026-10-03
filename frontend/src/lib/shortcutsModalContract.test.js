import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { SHORTCUT_GROUPS } from './editorShortcutKeys.js';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const sidebarSource = read('../components/Sidebar.jsx');
const keyboardHookSource = read('../hooks/useKeyboardShortcuts.js');
const modalSource = read('../components/ShortcutsModal.jsx');
const editorHeaderSource = read('../components/editor/EditorHeader.jsx');
const editorShellSource = read('../components/editor/EditorShell.jsx');
const appSource = read('../App.jsx');

// '1' -> 'flow' from the object literal the global hook switches tabs with.
function tabMapFromHook() {
  const body = keyboardHookSource.match(/const tabMap = \{([\s\S]*?)\};/);
  assert.ok(body, 'useKeyboardShortcuts.js no longer has a tabMap');
  const map = {};
  for (const m of body[1].matchAll(/'(\d)':\s*'(\w+)'/g)) map[m[1]] = m[2];
  return map;
}

// 'flow' -> '1. ...' (the label the Sidebar button actually shows).
function sidebarLabels() {
  const labels = {};
  for (const m of sidebarSource.matchAll(/\{\s*id:\s*'(\w+)',[^}]*?label:\s*'([^']+)'/g)) {
    if (!(m[1] in labels)) labels[m[1]] = m[2];
  }
  return labels;
}

const tabRows = () => SHORTCUT_GROUPS[0].shortcuts;

test('shortcut dialog tab rows are exactly the keys the global hook maps, nothing extra', () => {
  const tabMap = tabMapFromHook();
  assert.deepEqual(tabRows().map((r) => r.keys), Object.keys(tabMap).sort());
  assert.equal(tabRows().some((r) => r.keys === '6'), false);
});

test('shortcut dialog tab rows carry the same label the Sidebar shows for that tab', () => {
  const tabMap = tabMapFromHook();
  const labels = sidebarLabels();
  for (const row of tabRows()) {
    const tabId = tabMap[row.keys];
    assert.ok(labels[tabId], `Sidebar has no button for ${tabId}`);
    assert.equal(row.desc, labels[tabId], `key ${row.keys}`);
    assert.ok(labels[tabId].startsWith(`${row.keys}.`), `Sidebar numbers ${tabId} differently from key ${row.keys}`);
  }
});

test('ShortcutsModal reads the shared table instead of its own copy', () => {
  assert.match(modalSource, /import \{ SHORTCUT_GROUPS \} from '\.\.\/lib\/editorShortcutKeys\.js'/);
  assert.match(modalSource, /SHORTCUT_GROUPS\.map/);
  assert.doesNotMatch(modalSource, /category:/);
});

test('the editor header menu can open the shortcuts dialog (Topbar is hidden in the editor)', () => {
  assert.match(editorHeaderSource, /id: 'shortcuts',\s*label: 'ดูคีย์ลัด'/);
  assert.match(editorHeaderSource, /onSelect: onOpenShortcuts/);
  assert.match(editorShellSource, /onOpenShortcuts=\{onOpenShortcuts\}/);
  assert.match(appSource, /onOpenShortcuts=\{\(\) => setShowShortcutsModal\(true\)\}/);
});
