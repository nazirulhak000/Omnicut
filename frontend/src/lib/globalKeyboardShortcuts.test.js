import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { createGlobalKeyDownHandler } from '../hooks/useKeyboardShortcuts.js';

// EDITOR-CUT-QUALITY-R1 / B2: the App-level handler and the editor's own window
// handlers both fire on Space and Ctrl+S. Listener order between them is not stable
// (EditorShell is lazy-mounted), so the App handler must be a no-op for those keys on
// the editor tab regardless of who runs first.

function fakeEvent(init = {}) {
  const event = {
    key: '',
    code: '',
    ctrlKey: false,
    metaKey: false,
    target: { tagName: 'BODY', isContentEditable: false },
    defaultPrevented: false,
    preventCalls: 0,
    ...init,
    preventDefault() {
      this.defaultPrevented = true;
      this.preventCalls += 1;
    },
  };
  return event;
}

const space = (init = {}) => fakeEvent({ key: ' ', code: 'Space', ...init });
const ctrlS = (init = {}) => fakeEvent({ key: 's', code: 'KeyS', ctrlKey: true, ...init });

function fakeVideo({ paused = true, rect = { left: 10, top: 10, right: 330, bottom: 190, width: 320, height: 180 }, ariaHidden = false } = {}) {
  return {
    paused,
    playCalls: 0,
    pauseCalls: 0,
    getBoundingClientRect: () => rect,
    closest: (selector) => (ariaHidden && selector === '[aria-hidden="true"]' ? {} : null),
    play() {
      this.playCalls += 1;
      this.paused = false;
      return Promise.resolve();
    },
    pause() {
      this.pauseCalls += 1;
      this.paused = true;
    },
  };
}

const fakeDoc = (videos) => ({
  querySelectorAll: (selector) => (selector === 'video' ? videos : []),
  defaultView: { innerWidth: 1280, innerHeight: 720 },
});

const decodeVideo = () => fakeVideo({
  ariaHidden: true,
  rect: { left: -9999, top: 0, right: -9998, bottom: 1, width: 1, height: 1 },
});

function build(overrides = {}) {
  const calls = { save: 0, tab: [], escape: 0, shortcuts: 0 };
  const handler = createGlobalKeyDownHandler({
    onSave: () => { calls.save += 1; },
    onTabChange: (tab) => { calls.tab.push(tab); },
    onEscape: () => { calls.escape += 1; },
    onToggleShortcutsModal: () => { calls.shortcuts += 1; },
    ...overrides,
  });
  return { handler, calls };
}

// What the editor's useEditorShortcuts Space handler does to the event.
const editorSpaceHandler = (player) => (e) => {
  e.preventDefault();
  player.toggles += 1;
};

test('editor tab: Space is left to the editor, no <video> is toggled and nothing is prevented here', () => {
  const video = fakeVideo();
  const { handler } = build({ isEditorActive: true, doc: fakeDoc([video]) });
  const e = space();
  handler(e);
  assert.equal(video.playCalls + video.pauseCalls, 0);
  assert.equal(e.preventCalls, 0);
});

test('editor tab: Space toggles the player exactly once whichever handler runs first', () => {
  for (const appFirst of [true, false]) {
    const decode = decodeVideo();
    const player = { toggles: 0 };
    const { handler } = build({ isEditorActive: true, doc: fakeDoc([decode]) });
    const handlers = appFirst ? [handler, editorSpaceHandler(player)] : [editorSpaceHandler(player), handler];
    const e = space();
    handlers.forEach((h) => h(e));
    assert.equal(player.toggles, 1, `appFirst=${appFirst}`);
    assert.equal(decode.playCalls + decode.pauseCalls, 0, `appFirst=${appFirst}: decode video untouched`);
  }
});

test('other tabs: Space toggles the first on-screen video and prevents page scroll', () => {
  const video = fakeVideo({ paused: true });
  const { handler } = build({ doc: fakeDoc([video]) });
  const e = space();
  handler(e);
  assert.equal(video.playCalls, 1);
  assert.equal(e.preventCalls, 1);

  handler(space());
  assert.equal(video.pauseCalls, 1);
});

test('other tabs: hidden decode videos (aria-hidden, 1px, off-screen) are never driven', () => {
  const decode = decodeVideo();
  const visible = fakeVideo();
  const { handler } = build({ doc: fakeDoc([decode, visible]) });
  handler(space());
  assert.equal(decode.playCalls + decode.pauseCalls, 0);
  assert.equal(visible.playCalls, 1);
});

test('other tabs: an off-screen video that is not aria-hidden is skipped in favour of a visible one', () => {
  const offscreen = fakeVideo({ rect: { left: -5000, top: 0, right: -4680, bottom: 180, width: 320, height: 180 } });
  const visible = fakeVideo();
  const { handler } = build({ doc: fakeDoc([offscreen, visible]) });
  handler(space());
  assert.equal(offscreen.playCalls, 0);
  assert.equal(visible.playCalls, 1);
});

test('other tabs: a gallery modal preview still plays when it is the only video', () => {
  const preview = fakeVideo();
  const { handler } = build({ doc: fakeDoc([preview]) });
  handler(space());
  assert.equal(preview.playCalls, 1);
});

test('Space on an event another handler already prevented is skipped', () => {
  const video = fakeVideo();
  const { handler } = build({ doc: fakeDoc([video]) });
  const e = space({ defaultPrevented: true });
  handler(e);
  assert.equal(video.playCalls + video.pauseCalls, 0);
});

test('Space typed into a text field is ignored', () => {
  const video = fakeVideo();
  const { handler } = build({ doc: fakeDoc([video]) });
  const e = space({ target: { tagName: 'TEXTAREA' } });
  handler(e);
  assert.equal(video.playCalls + video.pauseCalls, 0);
  assert.equal(e.preventCalls, 0);
});

test('Ctrl+S on the editor tab blocks the browser dialog but does not show the form-save toast', () => {
  const { handler, calls } = build({ isEditorActive: true });
  const e = ctrlS();
  handler(e);
  assert.equal(e.preventCalls, 1);
  assert.equal(calls.save, 0);
});

test('Ctrl+S on other tabs still saves the form and blocks the browser dialog', () => {
  const { handler, calls } = build();
  const e = ctrlS();
  handler(e);
  assert.equal(e.preventCalls, 1);
  assert.equal(calls.save, 1);
  const mac = ctrlS({ ctrlKey: false, metaKey: true, key: 'S' });
  handler(mac);
  assert.equal(calls.save, 2);
});

test('Ctrl+S already handled by another listener does not fire the toast a second time', () => {
  const { handler, calls } = build();
  const e = ctrlS({ defaultPrevented: true });
  handler(e);
  assert.equal(calls.save, 0);
  assert.equal(e.defaultPrevented, true);
});

test('Escape, ?, and number tabs keep working on every tab', () => {
  for (const isEditorActive of [true, false]) {
    const { handler, calls } = build({ isEditorActive });
    handler(fakeEvent({ key: 'Escape', code: 'Escape' }));
    handler(fakeEvent({ key: '?', code: 'Slash' }));
    handler(fakeEvent({ key: '4', code: 'Digit4' }));
    assert.equal(calls.escape, 1);
    assert.equal(calls.shortcuts, 1);
    assert.deepEqual(calls.tab, ['gallery']);
  }
});

test('App tells the hook when the editor tab is active', () => {
  const appSource = readFileSync(new URL('../App.jsx', import.meta.url), 'utf8');
  assert.match(appSource, /useKeyboardShortcuts\(\{[\s\S]{0,260}?isEditorActive:\s*activeTab === 'editor'/);
});
