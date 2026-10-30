import test from 'node:test';
import assert from 'node:assert/strict';

import {
  normalizeTab, readTabFromSearch, resolveInitialTab, buildTabUrl,
  isSafeNextPath, readSafeNext, stripLoginParams, tabHistoryAction,
  pushTab, replaceTab, OVERLAY_STATE_KEY, TAB_STATE_KEY,
} from './appNav.js';

test('normalizeTab maps legacy ids and rejects unknown values', () => {
  assert.equal(normalizeTab('gallery'), 'gallery');
  assert.equal(normalizeTab('studio'), 'editor');
  assert.equal(normalizeTab('sub_srt'), 'editor');
  assert.equal(normalizeTab('gadget'), 'flow');
  assert.equal(normalizeTab('nope'), null);
  assert.equal(normalizeTab(''), null);
  assert.equal(normalizeTab(null), null);
});

test('initial tab prefers the URL, then storage, then the default', () => {
  assert.equal(resolveInitialTab({ search: '?tab=gallery', stored: 'tracker' }), 'gallery');
  assert.equal(resolveInitialTab({ search: '?tab=bogus', stored: 'tracker' }), 'tracker');
  assert.equal(resolveInitialTab({ search: '', stored: 'producer' }), 'flow');
  assert.equal(resolveInitialTab({ search: '', stored: null }), 'flow');
  assert.equal(readTabFromSearch('?mode=desktop&tab=settings'), 'settings');
});

test('buildTabUrl keeps every other query param, path and hash', () => {
  const url = buildTabUrl('https://studio.example/app?mode=mobile&channel=second&film=1&quick_post=1#x', 'gallery');
  const parsed = new URL(url, 'https://studio.example');
  assert.equal(parsed.pathname, '/app');
  assert.equal(parsed.hash, '#x');
  assert.equal(parsed.searchParams.get('tab'), 'gallery');
  for (const [key, value] of [['mode', 'mobile'], ['channel', 'second'], ['film', '1'], ['quick_post', '1']]) {
    assert.equal(parsed.searchParams.get(key), value);
  }
  assert.equal(new URL(buildTabUrl('/?tab=flow', 'bogus'), 'http://x').searchParams.get('tab'), null);
});

test('post-login redirect accepts only same-origin relative paths', () => {
  for (const ok of ['/agy', '/?tab=gallery', '/agy/terminal?x=1']) assert.equal(isSafeNextPath(ok), true, ok);
  for (const bad of ['//evil.com', '/\\evil.com', 'https://evil.com', 'javascript:alert(1)', 'agy', '', null, '/a\\b', '/a\nb']) {
    assert.equal(isSafeNextPath(bad), false, String(bad));
  }
  assert.equal(readSafeNext('?login=1&next=/agy'), '/agy');
  assert.equal(readSafeNext('?login=1&next=https://evil.com'), null);
  assert.equal(stripLoginParams('/?login=1&next=/agy&channel=main'), '/?channel=main');
});

test('tab history action pushes, replaces closing overlay entries, or does nothing', () => {
  assert.equal(tabHistoryAction({ search: '?tab=flow', state: null, tab: 'flow' }), 'none');
  assert.equal(tabHistoryAction({ search: '?tab=flow', state: null, tab: 'gallery' }), 'push');
  assert.equal(tabHistoryAction({ search: '?tab=flow', state: { [OVERLAY_STATE_KEY]: 'ov1' }, tab: 'assets' }), 'replace');
  assert.equal(tabHistoryAction({ search: '', state: null, tab: 'bogus' }), 'none');
});

function fakeWindow(href, state = null) {
  const entries = [{ url: href, state }];
  let index = 0;
  const location = {};
  const sync = () => {
    const url = new URL(entries[index].url, 'https://studio.example');
    location.href = url.href;
    location.search = url.search;
  };
  sync();
  return {
    location,
    entries: () => entries.map((entry) => entry.url),
    history: {
      get state() { return entries[index].state; },
      pushState(nextState, _title, url) { entries.splice(index + 1); entries.push({ url, state: nextState }); index += 1; sync(); },
      replaceState(nextState, _title, url) { entries[index] = { url, state: nextState }; sync(); },
    },
  };
}

test('pushTab/replaceTab write real history entries without touching other params', () => {
  const win = fakeWindow('/?channel=main&mode=desktop');
  assert.equal(replaceTab('flow', { win }), true);
  assert.equal(win.history.state[TAB_STATE_KEY], 'flow');
  assert.equal(pushTab('flow', { win }), 'none');
  assert.equal(pushTab('gallery', { win }), 'push');
  assert.deepEqual(win.entries(), ['/?channel=main&mode=desktop&tab=flow', '/?channel=main&mode=desktop&tab=gallery']);

  // An overlay entry that is closing is replaced instead of leaving a dead back step.
  win.history.pushState({ [OVERLAY_STATE_KEY]: 'sheet' }, '', '/?channel=main&mode=desktop&tab=gallery');
  assert.equal(pushTab('assets', { win }), 'replace');
  assert.deepEqual(win.entries(), [
    '/?channel=main&mode=desktop&tab=flow',
    '/?channel=main&mode=desktop&tab=gallery',
    '/?channel=main&mode=desktop&tab=assets',
  ]);
  assert.equal(win.history.state[OVERLAY_STATE_KEY], undefined);
});
