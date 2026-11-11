import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getRenderReadinessState, READINESS_STATES, normalizeSaveStatus } from './renderReadiness.js';

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
  assert.ok(readinessChipSource.includes('<PopoverPanel'), 'Popover must render through PopoverPanel (Escape + outside press)');
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

test('RenderReadinessChip implements 5-state truth table without false ready states', () => {
  // 1) loading: coverChecking || preflightLoading
  assert.equal(
    getRenderReadinessState({ coverChecking: true }),
    READINESS_STATES.LOADING,
    'coverChecking must yield loading'
  );
  assert.equal(
    getRenderReadinessState({ preflightLoading: true }),
    READINESS_STATES.LOADING,
    'preflightLoading must yield loading'
  );
  assert.equal(
    getRenderReadinessState({ coverChecking: true, preflightLoading: true }),
    READINESS_STATES.LOADING,
    'both loading must yield loading'
  );

  // 2) unknown / unchecked: (coverStatus === null || coverStatus === undefined) && !preflightReport
  assert.equal(
    getRenderReadinessState({ coverStatus: null, preflightReport: null }),
    READINESS_STATES.UNKNOWN,
    'null cover and null preflight must yield unknown (not ready!)'
  );
  assert.equal(
    getRenderReadinessState({ coverStatus: undefined, preflightReport: null }),
    READINESS_STATES.UNKNOWN,
    'undefined cover and null preflight must yield unknown'
  );
  assert.equal(
    getRenderReadinessState({ coverStatus: null, preflightReport: { errors: [], warnings: [] } }),
    READINESS_STATES.UNKNOWN,
    'null cover with empty preflight must remain unknown (cannot be ready without cover)'
  );
  assert.equal(
    getRenderReadinessState({ coverStatus: true, preflightReport: null }),
    READINESS_STATES.UNKNOWN,
    'true cover with null preflight must remain unknown (cannot be ready without preflight audit)'
  );

  // 3) blocked / error: errors.length > 0 || coverStatus === false
  assert.equal(
    getRenderReadinessState({ coverStatus: false, preflightReport: null }),
    READINESS_STATES.ERROR,
    'explicit missing cover (false) must yield error / blocker'
  );
  assert.equal(
    getRenderReadinessState({ coverStatus: true, preflightReport: { errors: ['Missing audio source'] } }),
    READINESS_STATES.ERROR,
    'preflight errors must yield error / blocker'
  );
  assert.equal(
    getRenderReadinessState({ coverStatus: false, preflightReport: { errors: ['Timeline empty'] } }),
    READINESS_STATES.ERROR,
    'missing cover and errors must both yield error / blocker'
  );

  // 4) warnings: warnings.length > 0 && !hasErrors
  assert.equal(
    getRenderReadinessState({
      coverStatus: true,
      preflightReport: { errors: [], warnings: ['Pacing slow on shot 2'] },
    }),
    READINESS_STATES.WARNING,
    'warnings without errors when cover is true must yield warning'
  );

  // 5) ready: coverStatus === true && errors.length === 0 && warnings.length === 0
  assert.equal(
    getRenderReadinessState({
      coverStatus: true,
      preflightReport: { errors: [], warnings: [] },
    }),
    READINESS_STATES.READY,
    'ready is only achieved when cover is true AND errors === 0 AND warnings === 0'
  );
});

test('RenderReadinessChip JSX satisfies visual and accessibility contract for all 5 states', () => {
  // State 1: loading
  assert.ok(readinessChipSource.includes('กำลังตรวจ...'), 'Must render "กำลังตรวจ..." text on loading');
  assert.ok(readinessChipSource.includes('กำลังตรวจสอบความพร้อม'), 'Must set accessible aria-label on loading');
  assert.ok(readinessChipSource.includes('Loader2'), 'Must render Loader2 spinner during loading');

  // State 2: unknown
  assert.ok(readinessChipSource.includes('ยังไม่ตรวจ'), 'Must render "ยังไม่ตรวจ" chip text when unchecked');
  assert.ok(readinessChipSource.includes('ยังไม่ได้ตรวจ'), 'Must render "ยังไม่ได้ตรวจ" badge');
  assert.ok(readinessChipSource.includes('ยังไม่ได้ตรวจสอบ'), 'Must set accessible aria-label on unknown');
  assert.ok(readinessChipSource.includes('border-slate-700/60'), 'Must use neutral slate styling for unknown state');

  // State 3: blocked / error
  assert.ok(readinessChipSource.includes('ตรวจแก้'), 'Must render "ตรวจแก้" chip text on error');
  assert.ok(readinessChipSource.includes('แก้ {totalBlockers}'), 'Must render totalBlockers badge on error');
  assert.ok(readinessChipSource.includes('ShieldAlert'), 'Must render ShieldAlert on error');
  assert.ok(readinessChipSource.includes('border-red-500/40'), 'Must use red styling for error state');

  // State 4: warnings
  assert.ok(readinessChipSource.includes('เตือน'), 'Must render "เตือน" chip text on warning');
  assert.ok(readinessChipSource.includes('{warnings.length}'), 'Must render warning count badge');

  // State 5: ready
  assert.ok(readinessChipSource.includes('พร้อม'), 'Must render "พร้อม" text on ready');
  assert.ok(readinessChipSource.includes('พร้อมเรนเดอร์ 100%'), 'Must render 100% ready badge in popover');
  assert.ok(readinessChipSource.includes('border-emerald-500/35'), 'Must use emerald styling for ready state');

  // Popover accessibility & dialog role
  assert.ok(readinessChipSource.includes('role="dialog"'), 'Popover must have role="dialog"');
  assert.ok(readinessChipSource.includes('<PopoverPanel'), 'Popover must render through PopoverPanel (Escape + outside press)');
  assert.ok(readinessChipSource.includes('aria-haspopup="dialog"'), 'Trigger button must declare aria-haspopup="dialog"');
});

test('SaveStatusChip supports saving, saved, unsaved/dirty, and error states without flickering', () => {
  assert.equal(normalizeSaveStatus('saving'), 'saving');
  assert.equal(normalizeSaveStatus('saved'), 'saved');
  assert.equal(normalizeSaveStatus('dirty'), 'unsaved');
  assert.equal(normalizeSaveStatus('unsaved'), 'unsaved');
  assert.equal(normalizeSaveStatus('error'), 'error');
  assert.equal(normalizeSaveStatus(undefined), 'saved');

  // Verify JSX handles 'unsaved' alongside 'dirty'
  assert.ok(saveStatusChipSource.includes("saveStatus === 'unsaved'"), 'Must handle unsaved state prop');

  // Verify no flickering text: container button must NOT have animate-pulse
  const errorButtonPulseRegex = /isError\s*\?[\s\S]*?animate-pulse[\s\S]*?:/;
  assert.ok(!errorButtonPulseRegex.test(saveStatusChipSource), 'Error state must not animate-pulse the entire button (prevents flickering text)');

  // Accessibility checks
  assert.ok(saveStatusChipSource.includes('กำลังบันทึกโปรเจกต์'), 'Must have aria-label for saving');
  assert.ok(saveStatusChipSource.includes('บันทึกไม่สำเร็จ'), 'Must have aria-label for error');
  assert.ok(saveStatusChipSource.includes('บันทึกแล้ว'), 'Must have aria-label for saved');
});
