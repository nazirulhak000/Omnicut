import test from 'node:test';
import assert from 'node:assert/strict';

import {
  classifyShortcut,
  isEditableTarget,
  isNonTextInput,
  shouldIgnoreShortcutTarget,
  SHORTCUT_GROUPS,
} from './editorShortcutKeys.js';

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

const input = (type) => ({ tagName: 'INPUT', type });
const TEXT_TYPES = ['text', 'search', 'number', 'email', 'url', 'password', 'tel', 'date', 'time', 'datetime-local', 'month', 'week'];
const NON_TEXT_TYPES = ['range', 'checkbox', 'radio', 'button', 'submit', 'reset', 'color', 'file', 'image', 'hidden'];

test('isEditableTarget: only inputs that take typed characters count', () => {
  for (const type of TEXT_TYPES) assert.equal(isEditableTarget(input(type)), true, type);
  for (const type of NON_TEXT_TYPES) assert.equal(isEditableTarget(input(type)), false, type);
  // The DOM reports an <input> with no/unknown type attribute as "text".
  assert.equal(isEditableTarget({ tagName: 'INPUT' }), true);
  assert.equal(isEditableTarget(input('')), true);
  assert.equal(isEditableTarget(input('TEXT')), true);
  assert.equal(isEditableTarget(input('RANGE')), false);
});

test('isEditableTarget: textarea, select and contenteditable stay text-entry', () => {
  assert.equal(isEditableTarget({ tagName: 'TEXTAREA' }), true);
  assert.equal(isEditableTarget({ tagName: 'SELECT' }), true);
  assert.equal(isEditableTarget({ tagName: 'DIV', isContentEditable: true }), true);
  assert.equal(isEditableTarget({ tagName: 'BUTTON' }), false);
  assert.equal(isEditableTarget({ tagName: 'DIV' }), false);
});

test('isNonTextInput: slider/checkbox/radio/button inputs only', () => {
  for (const type of NON_TEXT_TYPES) assert.equal(isNonTextInput(input(type)), true, type);
  for (const type of TEXT_TYPES) assert.equal(isNonTextInput(input(type)), false, type);
  assert.equal(isNonTextInput({ tagName: 'TEXTAREA' }), false);
  assert.equal(isNonTextInput({ tagName: 'SELECT' }), false);
  assert.equal(isNonTextInput({ tagName: 'BUTTON' }), false);
  assert.equal(isNonTextInput(null), false);
});

const ALL_EVENTS = [
  ['Ctrl+Z', { key: 'z', ctrlKey: true }],
  ['Cmd+Z', { key: 'z', metaKey: true }],
  ['Ctrl+Y', { key: 'y', ctrlKey: true }],
  ['Ctrl+Shift+Z', { key: 'z', ctrlKey: true, shiftKey: true }],
  ['Ctrl+B', { key: 'b', ctrlKey: true }],
  ['Delete', { key: 'Delete' }],
  ['Backspace', { key: 'Backspace' }],
  ['Space', { key: ' ' }],
  ['ArrowLeft', { key: 'ArrowLeft' }],
  ['ArrowRight', { key: 'ArrowRight', shiftKey: true }],
  ['s', { key: 's' }],
  ['j', { key: 'j' }],
  ['+', { key: '+' }],
  ['f', { key: 'f' }],
];

test('slider/checkbox/radio/button focus: undo and redo pass, every other key stays with the control', () => {
  const passing = new Set(['Ctrl+Z', 'Cmd+Z', 'Ctrl+Y', 'Ctrl+Shift+Z']);
  for (const type of ['range', 'checkbox', 'radio', 'button']) {
    for (const [name, ev] of ALL_EVENTS) {
      const { action } = classifyShortcut(ev);
      assert.equal(
        shouldIgnoreShortcutTarget(input(type), action),
        !passing.has(name),
        `${type} + ${name}`,
      );
    }
  }
});

test('slider focus never lets Delete, Backspace, Space or the arrows reach the editor', () => {
  for (const key of ['Delete', 'Backspace', ' ', 'ArrowLeft', 'ArrowRight']) {
    const { action } = classifyShortcut({ key });
    assert.notEqual(action, 'none', key);
    assert.equal(shouldIgnoreShortcutTarget(input('range'), action), true, key);
    assert.equal(shouldIgnoreShortcutTarget(input('checkbox'), action), true, key);
  }
});

test('text fields keep every key, undo and redo included', () => {
  for (const el of [input('text'), input('number'), input('search'), { tagName: 'TEXTAREA' }, { tagName: 'SELECT' }, { tagName: 'DIV', isContentEditable: true }]) {
    for (const [name, ev] of ALL_EVENTS) {
      assert.equal(shouldIgnoreShortcutTarget(el, classifyShortcut(ev).action), true, `${el.tagName}/${el.type} + ${name}`);
    }
  }
});

test('elements that are not form inputs are never ignored', () => {
  for (const el of [null, { tagName: 'DIV' }, { tagName: 'BUTTON' }, { tagName: 'A' }]) {
    for (const [name, ev] of ALL_EVENTS) {
      assert.equal(shouldIgnoreShortcutTarget(el, classifyShortcut(ev).action), false, `${el && el.tagName} + ${name}`);
    }
  }
});

test('SHORTCUT_GROUPS: every probed row is what classifyShortcut really returns', () => {
  let probed = 0;
  for (const group of SHORTCUT_GROUPS) {
    for (const row of group.shortcuts) {
      for (const probe of row.probes || []) {
        const got = classifyShortcut(probe.event, probe.context || {});
        assert.equal(got.action, probe.action, `${row.keys}: ${JSON.stringify(probe.event)}`);
        if ('delta' in probe) assert.equal(got.delta, probe.delta, `${row.keys} delta`);
        probed += 1;
      }
    }
  }
  assert.equal(probed, 19, 'every classifyShortcut-backed row keeps its probes');
});

test('SHORTCUT_GROUPS: rows are well formed, keys are unique, and there is no tab 6', () => {
  const seen = new Set();
  for (const group of SHORTCUT_GROUPS) {
    assert.ok(group.category);
    for (const row of group.shortcuts) {
      assert.ok(row.keys && row.desc, JSON.stringify(row));
      assert.equal(seen.has(row.keys), false, `duplicate ${row.keys}`);
      seen.add(row.keys);
    }
  }
  assert.equal(seen.has('6'), false);
  for (const k of ['1', '2', '3', '4', '5']) assert.equal(seen.has(k), true, k);
});
