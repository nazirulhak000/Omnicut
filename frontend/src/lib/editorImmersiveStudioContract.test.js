import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

const appSource = read('../App.jsx');
const sidebarSource = read('../components/Sidebar.jsx');
const editorHeaderSource = read('../components/editor/EditorHeader.jsx');
const editorShellSource = read('../components/editor/EditorShell.jsx');

test('App wires isEditorImmersive state to Sidebar, EditorShell, and main container', () => {
  // App manages isEditorImmersive state
  assert.ok(
    appSource.includes('isEditorImmersive'),
    'App.jsx must manage isEditorImmersive state'
  );
  assert.ok(
    appSource.includes('handleToggleEditorImmersive'),
    'App.jsx must provide handleToggleEditorImmersive callback'
  );

  // App connects isImmersive to Sidebar
  assert.ok(
    appSource.includes("isImmersive={activeTab === 'editor' && isEditorImmersive}"),
    'App.jsx must pass isImmersive to Sidebar'
  );

  // App connects isImmersive to EditorShell
  assert.ok(
    appSource.includes('isImmersive={isEditorImmersive}'),
    'App.jsx must pass isImmersive to EditorShell'
  );

  // Immersive drops the nav-bar padding but keeps the home-indicator inset
  // (S4-10): --nav-h was the only place that carried safe-area-inset-bottom.
  assert.ok(
    appSource.includes("activeTab === 'editor' && isEditorImmersive ? 'pb-[env(safe-area-inset-bottom)]' : 'pb-[var(--nav-h)]'"),
    'App.jsx must keep the bottom safe-area inset in immersive mode'
  );
});

test('Sidebar mobile navigation translates down smoothly when isImmersive is active', () => {
  assert.ok(
    sidebarSource.includes('isImmersive = false'),
    'Sidebar must accept isImmersive prop with default false'
  );
  assert.ok(
    sidebarSource.includes("isImmersive ? 'translate-y-full opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'"),
    'Sidebar mobile nav must transition down when isImmersive is true'
  );
  // S4-09: hidden off-screen must also mean out of the Tab order.
  assert.ok(sidebarSource.includes('inert={isImmersive || undefined}'), 'hidden bottom nav is inert');
  assert.ok(sidebarSource.includes('aria-hidden={isImmersive || undefined}'), 'hidden bottom nav is aria-hidden');
});

test('EditorHeader integrates Immersive Studio toggle in Zone 3 and overflow menu', () => {
  assert.ok(
    editorHeaderSource.includes('isImmersive = false'),
    'EditorHeader must accept isImmersive prop'
  );
  assert.ok(
    editorHeaderSource.includes('data-testid="toggle-immersive-studio-btn"'),
    'EditorHeader Zone 3 must render toggle-immersive-studio-btn'
  );
  assert.ok(
    editorHeaderSource.includes("id: 'immersive'"),
    'EditorHeader overflow menu must contain immersive toggle item'
  );
});

test('EditorShell provides Floating Studio Capsule and mobile mode toggle button', () => {
  assert.ok(
    editorShellSource.includes('isImmersive = false'),
    'EditorShell must accept isImmersive prop'
  );

  // Floating Studio Capsule when in immersive mode
  assert.ok(
    editorShellSource.includes('aria-label="แถบควบคุมสตูดิโอเต็มจอ"'),
    'EditorShell must render Floating Studio Capsule toolbar in immersive mode'
  );
  assert.ok(
    editorShellSource.includes('แสดงแถบ'),
    'Floating Studio Capsule must provide restore button'
  );

  // Mobile mode tab bar includes quick toggle button with >= 44px touch target
  assert.ok(
    editorShellSource.includes('min-h-[44px] min-w-[44px]'),
    'Mobile immersive toggle button must meet >=44px touch target standard'
  );

  // D12 / S4-06: no private F / Escape listener in the shell any more. The
  // immersive keys go through useEditorShortcuts (classifyShortcut), which
  // owns the editable-target, dialog and Escape-priority guards.
  assert.ok(!editorShellSource.includes("e.key === 'Escape' && isImmersive"), 'no Escape handler that bypasses the priority order');
  assert.ok(!/e\.key === 'f' \|\| e\.key === 'F'/.test(editorShellSource), 'no F handler beside toggleFade');
  assert.ok(editorShellSource.includes('onExitImmersive: exitImmersiveFromKeys'), 'Esc reaches immersive via the shortcut hook');
  assert.ok(editorShellSource.includes('onToggleImmersive: toggleImmersiveFromKeys'), 'Shift+F reaches immersive via the shortcut hook');
});

test('useEditorShortcuts keeps Escape for a context menu or a handler that already consumed it', () => {
  const hookSource = read('../hooks/useEditorShortcuts.js');
  assert.match(hookSource, /action === 'exitImmersive'\)\s*&& document\.querySelector\('\[data-context-menu\]'\)/);
  assert.match(hookSource, /\(action === 'exitImmersive' \|\| action === 'toggleImmersive'\) && e\.defaultPrevented/);
  assert.match(hookSource, /\[role="dialog"\], \[aria-modal="true"\]/, 'dialogs block every editor shortcut');
});

test('capsule save dot is bound to saveStatus, not a hardcoded green pulse (S4-08)', () => {
  assert.ok(!editorShellSource.includes('rounded-full bg-emerald-400 flex-shrink-0 animate-pulse'), 'no hardcoded green dot');
  assert.ok(editorShellSource.includes('const saveDot = saveStatusDot(saveStatus);'));
  assert.ok(editorShellSource.includes('aria-label={`ขยายแถบควบคุมสตูดิโอ · ${saveDot.label}`}'), 'mini capsule announces the save state');
});

test('mobile preview separator: no duplicate props, keyboard + value semantics (S4-12)', () => {
  const start = editorShellSource.indexOf('aria-label="ปรับขนาดพรีวิว 9:16"');
  assert.ok(start > 0);
  const tagStart = editorShellSource.lastIndexOf('<div', start);
  const tagEnd = editorShellSource.indexOf('className=', start);
  const tag = editorShellSource.slice(tagStart, tagEnd);
  for (const prop of ['title=', 'aria-label=', 'onKeyDown=', 'aria-valuenow=']) {
    assert.equal(tag.split(prop).length - 1, 1, `${prop} appears exactly once`);
  }
  assert.ok(tag.includes("setActiveSplitter('mobilePreview')"), 'drag highlights the handle');
  assert.ok(tag.includes('setActiveSplitter(null)'), 'drag end clears the highlight');
});

test('channel watermark alert is readable Thai, not ? placeholders (S4-11)', () => {
  assert.ok(!/\?{8,}/.test(editorShellSource), 'no run of ? left in EditorShell');
  assert.ok(editorShellSource.includes('โปรเจกต์นี้ยังไม่มีลายน้ำของช่องที่บันทึกไว้'));
});
