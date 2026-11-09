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

  // App unsets bottom padding on mobile when in immersive mode
  assert.ok(
    appSource.includes("activeTab === 'editor' && isEditorImmersive ? 'pb-0' : 'pb-[var(--nav-h)]'"),
    'App.jsx must set pb-0 when editor is in immersive mode'
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

  // Keyboard shortcut Esc / F for immersive toggle
  assert.ok(
    editorShellSource.includes("e.key === 'Escape' && isImmersive"),
    'EditorShell must handle Escape key to exit immersive mode'
  );
});
