import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MOTION_UI_PHASE_ORDER,
  getMotionUiModel,
  getMotionUiPreset,
  getMotionUiPresets,
  formatMotionDuration,
} from './motionUiModel.js';

test('groups hook presets in UI order while preserving contract loop as hold', () => {
  const model = getMotionUiModel({ role: 'hook' });

  assert.deepEqual(model.phaseOrder, ['in', 'hold', 'out']);
  assert.deepEqual(model.contractPhaseOrder, ['in', 'loop', 'out']);
  assert.deepEqual(model.groups.map((group) => group.id), ['in', 'hold', 'out']);
  assert.equal(model.groups[1].contractPhase, 'loop');
  assert.ok(model.groups[1].presets.some((preset) => preset.id === 'pulse'));
});

test('keeps legacy ids and exposes the full contract id', () => {
  const preset = getMotionUiPreset('hook', 'in', 'bounce');

  assert.equal(preset.id, 'bounce');
  assert.equal(preset.legacyId, 'bounce');
  assert.equal(preset.contractId, 'hook.in.bounce');
  assert.equal(preset.phase, 'in');
  assert.equal(preset.uiPhase, 'in');
});

test('provides Thai labels, duration metadata, role recommendation, and preview order', () => {
  const preset = getMotionUiPreset('hook', 'hold', 'pulse');

  assert.equal(preset.label, 'เต้นเบา');
  assert.equal(preset.durationMs, 700);
  assert.equal(preset.durationLabel, '700 มิลลิวินาที/รอบ');
  assert.equal(preset.recommendedRole, 'hook');
  assert.equal(preset.recommendedRoleLabel, 'Hook');
  assert.deepEqual(preset.preview.phaseOrder, MOTION_UI_PHASE_ORDER);
  assert.equal(preset.preview.activePhase, 'hold');
});

test('exposes truthful capability metadata without inventing renderer behavior', () => {
  const preset = getMotionUiPreset('text', 'in', 'snap');

  assert.equal(preset.capabilities.intensity.supported, false);
  assert.equal(preset.capabilities.speed.supported, false);
  assert.match(preset.capabilities.speed.reason, /Renderer/);
});

test('provides DOM-ready aria metadata and selected state', () => {
  const model = getMotionUiModel({ role: 'hook', selectedByPhase: { in: 'pop' } });
  const selected = model.groups[0].presets.find((preset) => preset.id === 'pop');
  const unselected = model.groups[0].presets.find((preset) => preset.id === 'bounce');

  assert.equal(model.aria.role, 'group');
  assert.equal(model.groups[0].aria.role, 'radiogroup');
  assert.equal(selected.aria.role, 'radio');
  assert.equal(selected.aria['aria-checked'], true);
  assert.equal(unselected.aria['aria-checked'], false);
  assert.match(selected.aria['aria-label'], /ป๊อปเข้า/);
});

test('filters by role and returns an empty caption catalog without inventing presets', () => {
  const textIn = getMotionUiPresets('text', 'in');
  const captionModel = getMotionUiModel({ role: 'caption' });

  assert.ok(textIn.some((preset) => preset.id === 'snap'));
  assert.equal(textIn.some((preset) => preset.id === 'bounce'), false);
  assert.deepEqual(captionModel.groups.map((group) => group.presets.length), [0, 0, 0]);
});

test('accepts the legacy loop phase alias and formats edge durations', () => {
  const preset = getMotionUiPreset('hook', 'loop', 'wave');

  assert.equal(preset.uiPhase, 'hold');
  assert.equal(formatMotionDuration(0), 'ทันที');
  assert.equal(formatMotionDuration(1), 'ตัดทันที');
  assert.equal(formatMotionDuration(450), '450 มิลลิวินาที');
  assert.equal(formatMotionDuration(1200, { repeat: true }), '1.2 วินาที/รอบ');
});
