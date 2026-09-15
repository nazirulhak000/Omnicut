import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const sequencePlayerSource = readFileSync(
  new URL('../components/SequencePlayer.jsx', import.meta.url),
  'utf8',
);

const tickStart = sequencePlayerSource.indexOf('const tick = () => {');
const tickEnd = sequencePlayerSource.indexOf(
  'rafRef.current = requestAnimationFrame(tick);',
  tickStart,
);
const playbackTickSource = sequencePlayerSource.slice(tickStart, tickEnd);

test('playback publishes the UI playhead through the throttled scheduler', () => {
  assert.notEqual(tickStart, -1, 'playback tick should remain present');
  assert.notEqual(tickEnd, -1, 'playback RAF should remain scheduled');
  assert.match(sequencePlayerSource, /const PLAYHEAD_UI_INTERVAL_MS = 1000 \/ 30;/);
  assert.match(sequencePlayerSource, /const publishPlayhead = \(t, force = false, now = performance\.now\(\)\) =>/);
  assert.match(playbackTickSource, /publishPlayhead\(t(?:, false, now)?\);/);
  assert.doesNotMatch(playbackTickSource, /setPlayhead\(t\);/);
});

test('playback preserves frame scheduling and avoids a repeated previous-segment scan', () => {
  assert.equal(
    (sequencePlayerSource.match(/requestAnimationFrame\(tick\)/g) || []).length,
    2,
    'playback should schedule its initial and subsequent RAF callbacks',
  );
  assert.match(sequencePlayerSource, /const segmentsByClipId = useMemo\(\(\) =>/);
  assert.match(playbackTickSource, /segmentsByClipId\.get\(prevActiveClipIdRef\.current\)/);
  assert.doesNotMatch(
    playbackTickSource,
    /segments\.find\(s => s\.clip\.id === prevActiveClipIdRef\.current\)/,
  );
});

test('frame scheduling keeps the audio clock, drift correction, and selection-box contract', () => {
  assert.match(playbackTickSource, /audio\.currentTime/);
  assert.match(playbackTickSource, /clockRef\.current\.startT/);
  assert.match(playbackTickSource, /RESYNC\.AUDIO/);
  assert.match(playbackTickSource, /pumpSfx\(t\)/);
  assert.match(playbackTickSource, /applyBgmEnvelope\(t\)/);
  assert.match(sequencePlayerSource, /selection, overlays, cues, playhead,/);
});

test('background isolation frame errors have bounded deterministic retry backoff', () => {
  assert.match(
    sequencePlayerSource,
    /const BACKGROUND_FRAME_RETRY_DELAYS_MS = Object\.freeze\(\[250, 1000, 4000\]\);/,
  );
  assert.match(sequencePlayerSource, /function backgroundFrameRetryDelay\(retryCount\)/);
  assert.match(sequencePlayerSource, /const retryDelay = backgroundFrameRetryDelay\(entry\.retryCount\);/);
  assert.match(sequencePlayerSource, /entry\.retryTimer = setTimeout\(\(\) => \{/);
  assert.match(sequencePlayerSource, /entry\.status = 'loading';/);
  assert.match(
    sequencePlayerSource,
    /if \(cache\.get\(resolution\.frameUrl\) !== entry\) return;/,
  );
});

test('background isolation preview cache has a bounded eviction policy', () => {
  assert.match(sequencePlayerSource, /const BACKGROUND_FRAME_CACHE_LIMIT = 120;/);
  assert.match(sequencePlayerSource, /function evictBackgroundIsolationFrameCache\(cache, keepKey\)/);
  assert.match(sequencePlayerSource, /evictBackgroundIsolationFrameCache\(cache, resolution\.frameUrl\);/);
  assert.match(sequencePlayerSource, /cache\.delete\(oldest\);/);
});
