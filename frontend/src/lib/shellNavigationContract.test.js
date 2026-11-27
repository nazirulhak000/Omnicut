import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

const sidebarSource = read('../components/Sidebar.jsx');
const topbarSource = read('../components/Topbar.jsx');
const pageHeaderSource = read('../components/ui/PageHeader.jsx');
const editorChannelSelectorSource = read('../components/editor/EditorChannelSelector.jsx');
const projectSelectorSource = read('../components/editor/ProjectSelector.jsx');
const editorHeaderSource = read('../components/editor/EditorHeader.jsx');

test('Sidebar enforces 72px rail and Matte-Dark Desktop Utility chrome', () => {
  // 72px icon rail contract
  assert.ok(sidebarSource.includes('w-[72px]'), 'Sidebar must maintain exactly 72px width');
  assert.ok(sidebarSource.includes('bg-[#101114]'), 'Sidebar must use Matte-Dark #101114 chrome background');
  assert.ok(sidebarSource.includes('border-r border-[#1E2026]'), 'Sidebar must use clean studio 1px #1E2026 border');

  // Nav accessibility & semantic attributes
  assert.ok(sidebarSource.includes('aria-label="แถบเมนูหลัก"'), 'Sidebar nav must have accessible label');
  assert.ok(sidebarSource.includes("aria-label={item.label}"), 'Nav buttons must carry aria-label matching item label');
  assert.ok(sidebarSource.includes("aria-current={isActive ? 'page' : undefined}"), 'Active nav item must announce aria-current="page"');
  assert.ok(sidebarSource.includes('focus-visible:ring-2'), 'Nav buttons must provide clean focus-visible ring');

  // Clean studio active style (no harsh multi-color gradients or cyan glow blur)
  assert.ok(
    sidebarSource.includes("bg-[#1B1D22] text-[#F4F4F5] border border-[#2B2E36]"),
    'Active nav item must use Matte-Dark active tokens'
  );
  assert.ok(
    sidebarSource.includes("bg-[#34D399]"),
    'Active nav item must have solid #34D399 accent indicator without glow blur'
  );
  assert.ok(
    !sidebarSource.includes('shadow-[0_0_12px_rgba(37,244,238,0.25)]'),
    'Active nav item must not have cyan glow blur'
  );

  // Bottom utility buttons accessibility
  assert.ok(sidebarSource.includes('aria-label="อัปโหลดผ่านมือถือ (QR Code)"'), 'QR modal button must have aria-label');
  assert.ok(sidebarSource.includes('aria-label={isFullscreen ? \'ย่อจอ\' : \'เต็มจอ\'}'), 'Fullscreen button must have aria-label');
});

test('Topbar implements clean workstation header without slop glow or backdrop blur', () => {
  assert.ok(topbarSource.includes('bg-[#101114]'), 'Topbar must use Matte-Dark #101114 background');
  assert.ok(topbarSource.includes('border-b border-[#1E2026]'), 'Topbar must use 1px border-[#1E2026]');
  assert.ok(!topbarSource.includes('backdrop-blur'), 'Topbar must not use backdrop-blur');
  assert.ok(!topbarSource.includes('shadow-[0_4px_24px_-4px_rgba(0,0,0,0.5)'), 'Topbar must remove harsh slop drop shadows');
  assert.ok(topbarSource.includes('focus-visible:ring-2'), 'Topbar interactive actions must include focus-visible rings');
});

test('PageHeader maintains props contract while standardizing on Matte-Dark Desktop Utility', () => {
  assert.ok(pageHeaderSource.includes('bg-[#14161A]'), 'PageHeader must use Matte-Dark #14161A card background');
  assert.ok(pageHeaderSource.includes('border-[#23262D]'), 'PageHeader must use 1px border-[#23262D]');

  // Interface contract
  const props = ['icon', 'iconGradient', 'iconColor', 'eyebrow', 'title', 'titlePrefix', 'badges', 'quickSwitcher', 'actions', 'secondRow'];
  for (const prop of props) {
    assert.ok(pageHeaderSource.includes(prop), `PageHeader must preserve prop: ${prop}`);
  }
});

test('Mobile collision guard: EditorChannelSelector, ProjectSelector, and EditorHeader', () => {
  // EditorChannelSelector collapses currentDisplayName text on small screens (< 640px)
  assert.ok(
    editorChannelSelectorSource.includes('hidden sm:inline-block max-w-[130px] truncate'),
    'EditorChannelSelector must hide text label on mobile to reduce width to ~42px'
  );
  assert.ok(
    editorChannelSelectorSource.includes('px-1.5 sm:px-2.5'),
    'EditorChannelSelector must use compact mobile padding'
  );

  // ProjectSelector min-width scales down to 100px on narrow viewports and
  // only ever grows with the viewport (640-767px was wider than 768px+).
  assert.ok(
    projectSelectorSource.includes('min-w-[100px] sm:min-w-[160px] lg:min-w-[180px]'),
    'ProjectSelector must use min-w-[100px] on mobile and a non-shrinking min-width ladder'
  );
  assert.ok(!projectSelectorSource.includes('md:min-w-[110px]'), 'no breakpoint may shrink the selector');

  // EditorHeader AI Agent text is hidden on small screens
  assert.ok(
    editorHeaderSource.includes('<span className="hidden sm:inline">AI Agent</span>'),
    'EditorHeader AI Agent button must hide text on mobile'
  );
  assert.ok(
    editorHeaderSource.includes('bg-[#101114]'),
    'EditorHeader must use Matte-Dark #101114 background'
  );
});
