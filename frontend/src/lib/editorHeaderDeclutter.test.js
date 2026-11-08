import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

const headerSource = read('../components/editor/EditorHeader.jsx');
const saveStatusChipSource = read('../components/editor/SaveStatusChip.jsx');
const viewToggleGroupSource = read('../components/editor/ViewToggleGroup.jsx');
const readinessChipSource = read('../components/editor/RenderReadinessChip.jsx');
const preflightNoticeSource = read('../components/editor/RenderPreflightNotice.jsx');
const headerMenuSource = read('../components/editor/HeaderMenu.jsx');
const projectSelectorSource = read('../components/editor/ProjectSelector.jsx');

test('EditorHeader integrates 3 clear zones with decluttered navbar', () => {
  // Zone 1: Project Identity & Quick Save
  assert.ok(headerSource.includes("<EditorChannelSelector />"), 'Zone 1 must contain EditorChannelSelector');
  assert.ok(headerSource.includes("<ProjectSelector"), 'Zone 1 must contain ProjectSelector');
  assert.ok(headerSource.includes("onNewProject="), 'ProjectSelector must receive onNewProject callback');
  assert.ok(headerSource.includes("<SaveStatusChip"), 'Zone 1 must contain SaveStatusChip');

  // Zone 2: Viewport Controller
  assert.ok(headerSource.includes("<ViewToggleGroup"), 'Zone 2 must contain ViewToggleGroup');

  // Zone 3: AI Tools & Render Flow
  assert.ok(headerSource.includes('data-testid="toggle-ai-agent-btn"'), 'Zone 3 must preserve AI Agent toggle button');
  assert.ok(headerSource.includes("<ActivityIndicatorButton"), 'Zone 3 must contain ActivityIndicatorButton');
  assert.ok(headerSource.includes("<HeaderMenu"), 'Zone 3 must contain HeaderMenu');
  assert.ok(headerSource.includes("<RenderReadinessChip"), 'Zone 3 must contain RenderReadinessChip');
  assert.ok(headerSource.includes("<RenderButton"), 'Zone 3 must contain RenderButton');

  // Ordering check: Zone 1 < Zone 2 < Zone 3
  const z1 = headerSource.indexOf('Zone 1');
  const z2 = headerSource.indexOf('Zone 2');
  const z3 = headerSource.indexOf('Zone 3');
  assert.ok(z1 < z2 && z2 < z3, 'Header must follow 3-zone layout order: Left -> Center -> Right');

  // Verify removed clutter
  assert.ok(!headerSource.includes("<Scissors"), 'Decorative scissors icon should be removed');
  assert.ok(!headerSource.includes("formatTimecode(playhead"), 'Redundant timecode in navbar should be removed (lives in SequencePlayer)');
});

test('SaveStatusChip merges display and manual save trigger with accessibility', () => {
  assert.ok(saveStatusChipSource.includes('saveStatus === \'saving\''), 'Must handle saving state');
  assert.ok(saveStatusChipSource.includes('saveStatus === \'error\''), 'Must handle error state');
  assert.ok(saveStatusChipSource.includes('saveStatus === \'dirty\''), 'Must handle dirty state');
  assert.ok(saveStatusChipSource.includes('onSave?.()'), 'Must call onSave on click');
  assert.ok(saveStatusChipSource.includes('aria-label='), 'Must have aria-label');
  assert.ok(saveStatusChipSource.includes('title='), 'Must have tooltip title');
});

test('ViewToggleGroup renders segmented view controls with aria-labels', () => {
  assert.ok(viewToggleGroupSource.includes('toggleLeftSidebar'), 'Must handle toggleLeftSidebar');
  assert.ok(viewToggleGroupSource.includes('toggleFocusMode'), 'Must handle toggleFocusMode');
  assert.ok(viewToggleGroupSource.includes('toggleRightSidebar'), 'Must handle toggleRightSidebar');
  assert.ok(viewToggleGroupSource.includes('role="group"'), 'Must have role="group"');
  assert.ok(viewToggleGroupSource.includes('aria-pressed='), 'Must indicate toggle state with aria-pressed');
});

test('RenderReadinessChip combines cover, preflight, and playbook into interactive popover', () => {
  assert.ok(readinessChipSource.includes('coverStatus'), 'Must inspect coverStatus');
  assert.ok(readinessChipSource.includes('preflightReport'), 'Must inspect preflightReport');
  assert.ok(readinessChipSource.includes('playbookNotes'), 'Must inspect playbookNotes');
  assert.ok(readinessChipSource.includes('role="dialog"'), 'Popover must have role="dialog"');
  assert.ok(readinessChipSource.includes("e.key === 'Escape'"), 'Popover must close on Escape key');
  assert.ok(readinessChipSource.includes('ShieldCheck'), 'Must render ShieldCheck icon');
  assert.ok(readinessChipSource.includes('ShieldAlert'), 'Must render ShieldAlert icon');
});

test('HeaderMenu supports sections, dividers, and toggle switches', () => {
  assert.ok(headerMenuSource.includes("item.type === 'section'"), 'HeaderMenu must support section headers');
  assert.ok(headerMenuSource.includes("item.type === 'divider'"), 'HeaderMenu must support dividers');
  assert.ok(headerMenuSource.includes("item.type === 'toggle'"), 'HeaderMenu must support toggle checkboxes');
  assert.ok(headerMenuSource.includes("item.badge"), 'HeaderMenu must support badges');
});

test('ProjectSelector includes New Clip button inside dropdown when onNewProject is passed', () => {
  assert.ok(projectSelectorSource.includes('onNewProject'), 'ProjectSelector must accept onNewProject prop');
  assert.ok(projectSelectorSource.includes('สร้างคลิปใหม่'), 'Must display "สร้างคลิปใหม่" action');
  assert.ok(projectSelectorSource.includes('<Plus'), 'Must render Plus icon');
});

test('RenderPreflightNotice is hidden in normal editing to prevent intrusive top banner', () => {
  assert.ok(
    preflightNoticeSource.includes('if (!isAuditMode)'),
    'RenderPreflightNotice must return null unless explicitly in audit mode'
  );
});
