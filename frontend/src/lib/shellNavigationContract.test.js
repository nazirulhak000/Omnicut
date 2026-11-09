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

test('Sidebar enforces 72px rail and Obsidian Pro Dark NLE chrome', () => {
  // 72px icon rail contract
  assert.ok(sidebarSource.includes('w-[72px]'), 'Sidebar must maintain exactly 72px width');
  assert.ok(sidebarSource.includes('bg-[#0A0D14]'), 'Sidebar must use Obsidian Dark #0A0D14 background');
  assert.ok(sidebarSource.includes('border-r border-white/[0.08]'), 'Sidebar must use clean studio 1px border');

  // Nav accessibility & semantic attributes
  assert.ok(sidebarSource.includes('aria-label="แถบเมนูหลัก"'), 'Sidebar nav must have accessible label');
  assert.ok(sidebarSource.includes("aria-label={item.label}"), 'Nav buttons must carry aria-label matching item label');
  assert.ok(sidebarSource.includes("aria-current={isActive ? 'page' : undefined}"), 'Active nav item must announce aria-current="page"');
  assert.ok(sidebarSource.includes('focus-visible:ring-2'), 'Nav buttons must provide clean focus-visible ring');

  // Clean studio active style (no harsh multi-color gradients)
  assert.ok(
    sidebarSource.includes("bg-white/[0.08] text-[#25F4EE] border border-white/[0.12]"),
    'Active nav item must use clean studio active tokens'
  );
  assert.ok(
    sidebarSource.includes("bg-[#25F4EE] shadow-[0_0_8px_#25F4EE]"),
    'Active nav item must have solid cyan accent indicator'
  );

  // Bottom utility buttons accessibility
  assert.ok(sidebarSource.includes('aria-label="อัปโหลดผ่านมือถือ (QR Code)"'), 'QR modal button must have aria-label');
  assert.ok(sidebarSource.includes('aria-label={isFullscreen ? \'ย่อจอ\' : \'เต็มจอ\'}'), 'Fullscreen button must have aria-label');
});

test('Topbar implements clean workstation header without slop glow', () => {
  assert.ok(topbarSource.includes('bg-[#0A0D14]'), 'Topbar must use Obsidian Dark #0A0D14 background');
  assert.ok(topbarSource.includes('border-b border-white/[0.08]'), 'Topbar must use 1px border-white/[0.08]');
  assert.ok(!topbarSource.includes('shadow-[0_4px_24px_-4px_rgba(0,0,0,0.5)'), 'Topbar must remove harsh slop drop shadows');
  assert.ok(topbarSource.includes('focus-visible:ring-2'), 'Topbar interactive actions must include focus-visible rings');
});

test('PageHeader maintains props contract while standardizing on Obsidian Pro Studio', () => {
  assert.ok(pageHeaderSource.includes('bg-[#0A0D14]'), 'PageHeader must use Obsidian Dark background');
  assert.ok(pageHeaderSource.includes('border-white/[0.08]'), 'PageHeader must use border-white/[0.08]');
  assert.ok(pageHeaderSource.includes('shadow-sm'), 'PageHeader must use subtle shadow-sm instead of shadow-lg');

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
    editorHeaderSource.includes('bg-[#0A0D14]'),
    'EditorHeader must use Obsidian Dark #0A0D14 background'
  );
});
