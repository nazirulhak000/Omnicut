import test from 'node:test';
import assert from 'node:assert/strict';

import {
  PROXY_BUILDING,
  PROXY_MASTER,
  PROXY_READY,
  buildingClipIds,
  isProxyableSource,
  mergeProxyEntry,
  playbackUrlFor,
  readProxyResponse,
  shouldPoll,
} from './clipProxy.js';

const MASTER = '/api/media/01_Raw/clip.mp4';
const PROXY = '/api/media/03_Projects/.cache/editing-proxies/abc.mp4';

// ---------------------------------------------------------------------------
// readProxyResponse
// ---------------------------------------------------------------------------

test('readProxyResponse takes the proxy when one is ready', () => {
  const entry = readProxyResponse(
    { status: PROXY_READY, url: PROXY, master_url: MASTER, is_proxy: true },
    MASTER,
  );
  assert.equal(entry.url, PROXY);
  assert.equal(entry.isProxy, true);
  assert.equal(entry.status, PROXY_READY);
});

test('readProxyResponse plays the master while a proxy encodes', () => {
  const entry = readProxyResponse(
    { status: PROXY_BUILDING, url: MASTER, master_url: MASTER, is_proxy: false },
    MASTER,
  );
  assert.equal(entry.url, MASTER, 'editing must not wait on an encode');
  assert.equal(entry.isProxy, false);
  assert.equal(entry.status, PROXY_BUILDING);
});

test('readProxyResponse falls back to the master on a malformed payload', () => {
  // The player must always end up with something to play.
  for (const bad of [null, undefined, 'nope', 42, {}]) {
    const entry = readProxyResponse(bad, MASTER);
    assert.equal(entry.url, MASTER);
    assert.equal(entry.isProxy, false);
    assert.equal(entry.status, PROXY_MASTER);
  }
});

test('readProxyResponse ignores an unknown status', () => {
  const entry = readProxyResponse({ status: 'weird', url: PROXY, is_proxy: true }, MASTER);
  assert.equal(entry.status, PROXY_MASTER);
  assert.equal(entry.isProxy, false, 'an unrecognised status must not be trusted as a proxy');
});

test('readProxyResponse refuses to flag the master URL as a proxy', () => {
  // A payload claiming is_proxy while handing back the master would leave the
  // render-side guard as the only thing between a 540p file and an export.
  const entry = readProxyResponse(
    { status: PROXY_READY, url: MASTER, master_url: MASTER, is_proxy: true },
    MASTER,
  );
  assert.equal(entry.isProxy, false);
});

test('readProxyResponse ignores is_proxy while still building', () => {
  const entry = readProxyResponse(
    { status: PROXY_BUILDING, url: PROXY, is_proxy: true },
    MASTER,
  );
  assert.equal(entry.isProxy, false, 'only a ready proxy counts as a proxy');
});

test('readProxyResponse substitutes the master for an empty url', () => {
  const entry = readProxyResponse({ status: PROXY_READY, url: '', is_proxy: true }, MASTER);
  assert.equal(entry.url, MASTER);
});

// ---------------------------------------------------------------------------
// shouldPoll
// ---------------------------------------------------------------------------

test('shouldPoll re-checks only clips whose proxy is encoding', () => {
  assert.equal(shouldPoll({ status: PROXY_BUILDING }), true);
  assert.equal(shouldPoll({ status: PROXY_READY }), false, 'ready is terminal');
  assert.equal(shouldPoll({ status: PROXY_MASTER }), false, 'nothing is being built');
  assert.equal(shouldPoll(null), false);
  assert.equal(shouldPoll(undefined), false);
});

// ---------------------------------------------------------------------------
// mergeProxyEntry
// ---------------------------------------------------------------------------

test('mergeProxyEntry adds a clip without disturbing the others', () => {
  const before = { a: { url: MASTER, status: PROXY_MASTER, isProxy: false } };
  const after = mergeProxyEntry(before, 'b', { url: PROXY, status: PROXY_READY, isProxy: true });
  assert.equal(after.a, before.a, 'untouched entries should keep their identity');
  assert.equal(after.b.url, PROXY);
});

test('mergeProxyEntry returns the same object when nothing changed', () => {
  // Identity is the signal React uses to skip a re-render; a poll that
  // reports the same thing must not repaint the whole player.
  const entry = { url: MASTER, status: PROXY_BUILDING, isProxy: false };
  const before = { a: entry };
  assert.equal(mergeProxyEntry(before, 'a', { ...entry }), before);
});

test('mergeProxyEntry replaces an entry once the proxy is ready', () => {
  const before = { a: { url: MASTER, status: PROXY_BUILDING, isProxy: false } };
  const after = mergeProxyEntry(before, 'a', { url: PROXY, status: PROXY_READY, isProxy: true });
  assert.notEqual(after, before);
  assert.equal(after.a.url, PROXY);
});

test('mergeProxyEntry tolerates a missing map', () => {
  const after = mergeProxyEntry(null, 'a', { url: PROXY, status: PROXY_READY, isProxy: true });
  assert.equal(after.a.url, PROXY);
});

// ---------------------------------------------------------------------------
// playbackUrlFor
// ---------------------------------------------------------------------------

const toMediaUrl = (p) => (p ? `/api/media/${p}` : '');

test('playbackUrlFor uses the master until a clip is resolved', () => {
  // The first paint must show real footage, not an empty player.
  const clip = { id: 'c1', source_path: '01_Raw/clip.mp4' };
  assert.equal(playbackUrlFor(clip, {}, toMediaUrl), '/api/media/01_Raw/clip.mp4');
});

test('playbackUrlFor uses the proxy once resolved', () => {
  const clip = { id: 'c1', source_path: '01_Raw/clip.mp4' };
  const sources = { c1: { url: PROXY, status: PROXY_READY, isProxy: true } };
  assert.equal(playbackUrlFor(clip, sources, toMediaUrl), PROXY);
});

test('playbackUrlFor keeps clips independent', () => {
  const sources = { c1: { url: PROXY, status: PROXY_READY, isProxy: true } };
  const other = { id: 'c2', source_path: '01_Raw/other.mp4' };
  assert.equal(playbackUrlFor(other, sources, toMediaUrl), '/api/media/01_Raw/other.mp4');
});

test('playbackUrlFor survives a missing clip or sources', () => {
  assert.equal(playbackUrlFor(null, null, toMediaUrl), '');
  assert.equal(playbackUrlFor({ id: 'x' }, null, toMediaUrl), '');
});

// ---------------------------------------------------------------------------
// buildingClipIds
// ---------------------------------------------------------------------------

test('buildingClipIds lists only the clips still encoding', () => {
  const sources = {
    a: { status: PROXY_READY },
    b: { status: PROXY_BUILDING },
    c: { status: PROXY_MASTER },
    d: { status: PROXY_BUILDING },
  };
  assert.deepEqual(buildingClipIds(sources).sort(), ['b', 'd']);
});

test('buildingClipIds is empty for an empty or missing map', () => {
  assert.deepEqual(buildingClipIds({}), []);
  assert.deepEqual(buildingClipIds(null), []);
});


// ---------------------------------------------------------------------------
// isProxyableSource
// ---------------------------------------------------------------------------

test('isProxyableSource accepts project-relative media files', () => {
  for (const path of [
    '01_Raw/clip.mp4', '01_Raw/a.MOV', '02_Assets/b.webm',
    '01_Raw/c.mkv', '01_Raw/d.m4v', '01_Raw/e.avi',
  ]) {
    assert.equal(isProxyableSource(path), true, path);
  }
});

test('isProxyableSource rejects a served page or asset URL', () => {
  // The motion-capture fixture hands SequencePlayer its own page URL. Asking
  // the backend to proxy that produces a 403, and the browser logs the
  // rejection to the console whether or not the JS catches it -- which fails
  // every capture-based parity test in the suite.
  assert.equal(isProxyableSource('https://127.0.0.1:5173/motion_capture.html'), false);
  assert.equal(isProxyableSource('http://localhost:5173/clip.mp4'), false);
});

test('isProxyableSource rejects in-memory sources', () => {
  // A blob or data URI has no master on disk to build a proxy from.
  assert.equal(isProxyableSource('blob:http://localhost/abc-123'), false);
  assert.equal(isProxyableSource('data:video/mp4;base64,AAAA'), false);
});

test('isProxyableSource rejects the Vite filesystem escape hatch', () => {
  assert.equal(isProxyableSource('/@fs/D:/tmp/fixture.mp4'), false);
});

test('isProxyableSource rejects non-video files', () => {
  for (const path of ['notes.txt', '02_Assets/song.wav', 'cover.png', 'a.json']) {
    assert.equal(isProxyableSource(path), false, path);
  }
});

test('isProxyableSource rejects empty and non-string input', () => {
  for (const bad of ['', '   ', null, undefined, 42, {}]) {
    assert.equal(isProxyableSource(bad), false);
  }
});

test('isProxyableSource ignores a query string or fragment', () => {
  assert.equal(isProxyableSource('01_Raw/clip.mp4?v=2'), true);
  assert.equal(isProxyableSource('01_Raw/clip.mp4#t=3'), true);
  assert.equal(isProxyableSource('01_Raw/page.html?x=.mp4'), false);
});
