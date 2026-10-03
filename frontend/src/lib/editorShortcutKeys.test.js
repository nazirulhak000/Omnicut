import test from 'node:test';
import assert from 'node:assert/strict';

import { classifyShortcut, isEditableTarget } from './editorShortcutKeys.js';

const key = (k, mods = {}) => classifyShortcut({ key: k, ...mods });

test('Ctrl/Meta+S is left alone (no split, no preventDefault)', () => {
  for (const mods of [{ ctrlKey: true }, { metaKey: true }, { ctrlKey: true, shiftKey: true }]) {
    const r = key('s', mods);
    assert.equal(r.action, 'none');
    assert.equal(r.preventDefault, false);
    assert.equal(key('S', mods).action, 'none');
  }
});

test('Ctrl/Meta + plus/minus/equals do not hijack editor zoom', () => {
  for (const k of ['+', '=', '-', '_']) {
    assert.equal(key(k, { ctrlKey: true }).action, 'none');
    assert.equal(key(k, { metaKey: true }).preventDefault, false);
  }
});

test('plain s splits and plain +/- zoom', () => {
  assert.equal(key('s').action, 'split');
  assert.equal(key('S', { shiftKey: true }).action, 'split');
  assert.equal(key('+').action, 'zoomIn');
  assert.equal(key('=').action, 'zoomIn');
  assert.equal(key('-').action, 'zoomOut');
  assert.equal(key('_').action, 'zoomOut');
  assert.equal(key('s').preventDefault, true);
});

test('explicit modifier combos: Ctrl+B split, Ctrl+Z undo, Ctrl+Y / Shift+Ctrl+Z redo', () => {
  assert.equal(key('b', { ctrlKey: true }).action, 'split');
  assert.equal(key('B', { metaKey: true }).action, 'split');
  assert.equal(key('z', { ctrlKey: true }).action, 'undo');
  assert.equal(key('Z', { metaKey: true }).action, 'undo');
  assert.equal(key('Z', { ctrlKey: true, shiftKey: true }).action, 'redo');
  assert.equal(key('y', { ctrlKey: true }).action, 'redo');
  assert.equal(key('z', { ctrlKey: true }).preventDefault, true);
});

test('plain b and other unmodified keys keep their behavior', () => {
  assert.equal(key('b').action, 'none');
  assert.equal(key(' ').action, 'togglePlay');
  assert.equal(key('k').action, 'togglePlay');
  assert.deepEqual(key('j'), { action: 'jump', preventDefault: true, delta: -1 });
  assert.deepEqual(key('l'), { action: 'jump', preventDefault: true, delta: 1 });
  assert.equal(key('ArrowLeft').delta, -1 / 30);
  assert.equal(key('ArrowRight').delta, 1 / 30);
  assert.equal(key('ArrowLeft', { shiftKey: true }).delta, -1);
  assert.equal(key('ArrowRight', { shiftKey: true }).delta, 1);
  assert.equal(key('Delete').action, 'delete');
  assert.equal(key('Backspace').action, 'delete');
  assert.equal(key('n').action, 'toggleSnap');
  assert.equal(key('m').action, 'cycleCutout');
  assert.deepEqual(key('f'), { action: 'toggleFade', preventDefault: false });
  assert.equal(key('x').action, 'none');
});

test('Escape only acts in zen mode', () => {
  assert.equal(classifyShortcut({ key: 'Escape' }, { zen: true }).action, 'exitZen');
  assert.equal(classifyShortcut({ key: 'Escape' }, { zen: false }).action, 'none');
  assert.equal(classifyShortcut({ key: 'Escape' }).action, 'none');
});

test('Alt-modified keys are ignored', () => {
  assert.equal(key('s', { altKey: true }).action, 'none');
  assert.equal(key('ArrowLeft', { altKey: true }).action, 'none');
  assert.equal(key('z', { ctrlKey: true, altKey: true }).action, 'none');
});

test('events without a key are ignored safely', () => {
  assert.equal(classifyShortcut({}).action, 'none');
  assert.equal(classifyShortcut(null).action, 'none');
});

test('isEditableTarget detects text-entry controls', () => {
  assert.equal(isEditableTarget({ tagName: 'INPUT' }), true);
  assert.equal(isEditableTarget({ tagName: 'TEXTAREA' }), true);
  assert.equal(isEditableTarget({ tagName: 'SELECT' }), true);
  assert.equal(isEditableTarget({ tagName: 'DIV', isContentEditable: true }), true);
  assert.equal(isEditableTarget({ tagName: 'DIV' }), false);
  assert.equal(isEditableTarget(null), false);
});
