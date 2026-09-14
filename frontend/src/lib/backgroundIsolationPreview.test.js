import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LEGACY_FRAME_PATTERN,
  SEQUENCE_FRAME_PATTERN,
  buildBackgroundIsolationFrameUrl,
  groupBackgroundIsolationClips,
  mapSourceTimeToFrameIndex,
  resolveBackgroundIsolationPreview,
  splitBackgroundIsolationOverlays,
} from './backgroundIsolationPreview.js';

const ARTIFACT_ID = 'bgseq1-0123456789abcdef';
const BASE_URL = '/api/background-isolation/sequences';

test('splits Hook overlays behind the isolated Subject while keeping captions foregrounded', () => {
  const result = splitBackgroundIsolationOverlays([
    { id: 'hook', kind: 'hook' },
    { id: 'caption', kind: 'text' },
    { id: 'legacy-hook', type: 'hook_header' },
  ]);

  assert.deepEqual(result.behindSubject.map((item) => item.id), ['hook', 'legacy-hook']);
  assert.deepEqual(result.foreground.map((item) => item.id), ['caption']);
});

test('groups multiple trim windows from one source into one isolation job', () => {
  const source = 'D:/clips/esseger.mov';
  const groups = groupBackgroundIsolationClips([
    { source_path: source, trim_start: 0, trim_end: 2 },
    { source_path: source, trim_start: 4, trim_end: 6 },
    { source_path: source.toUpperCase(), trim_start: 8, trim_end: 10 },
    { source_path: source, rotation: 90, trim_start: 12, trim_end: 14 },
  ]);

  assert.equal(groups.length, 2);
  assert.equal(groups[0].clips.length, 3);
  assert.equal(groups[1].rotation, 90);
});

function readyConfig(overrides = {}) {
  return {
    schema_version: 1,
    enabled: true,
    fallback: 'spotlight',
    artifact: {
      id: ARTIFACT_ID,
      status: 'ready',
    },
    ...overrides,
  };
}

function readyManifest(overrides = {}) {
  return {
    schema_version: 1,
    artifact_id: ARTIFACT_ID,
    status: 'ready',
    source_fingerprint: 'source:size=10:mtime=1',
    algorithm: 'background-isolation-v1',
    engine: 'rembg',
    model: 'u2netp',
    quality: 'balanced',
    worker_version: 'sequence-worker-v1',
    frame_count: 4,
    fps: '30/1',
    timebase: '1/30',
    width: 1080,
    height: 1920,
    rotation: 0,
    frame_pattern: SEQUENCE_FRAME_PATTERN,
    ...overrides,
  };
}

test('missing field preserves legacy behavior without producing an artifact URL', () => {
  assert.deepEqual(
    resolveBackgroundIsolationPreview({ sourceTime: 1, artifactBaseUrl: BASE_URL }),
    {
      ok: false,
      kind: 'fallback',
      useArtifact: false,
      fallback: 'legacy',
      reason: 'config_absent',
      status: 'legacy',
      artifactId: null,
      frameIndex: null,
      frameUrl: null,
      rotation: 0,
    },
  );
});

test('disabled config uses its declared deterministic fallback', () => {
  const result = resolveBackgroundIsolationPreview({
    config: { enabled: false, fallback: 'original' },
    manifest: readyManifest(),
    artifactBaseUrl: BASE_URL,
  });
  assert.equal(result.useArtifact, false);
  assert.equal(result.fallback, 'original');
  assert.equal(result.reason, 'disabled');
  assert.equal(result.status, 'disabled');
});

test('invalid config schema or options is disabled like the backend contract', () => {
  for (const config of [
    { schema_version: 99, enabled: true },
    { enabled: true, engine: 'other' },
    { enabled: 'yes' },
  ]) {
    const result = resolveBackgroundIsolationPreview({
      config,
      manifest: readyManifest(),
      artifactBaseUrl: BASE_URL,
    });
    assert.equal(result.useArtifact, false);
    assert.equal(result.fallback, 'spotlight');
    assert.equal(result.reason, 'invalid_config');
    assert.equal(result.status, 'disabled');
  }
});

for (const status of ['missing', 'stale', 'error', 'cancelled']) {
  test(`${status} artifact always falls back without consulting the manifest`, () => {
    let lookupCalls = 0;
    const result = resolveBackgroundIsolationPreview({
      config: readyConfig({ artifact: { id: ARTIFACT_ID, status } }),
      manifest: readyManifest(),
      artifactLookup: () => {
        lookupCalls += 1;
        return BASE_URL;
      },
      sourceTime: 0.2,
    });
    assert.equal(result.useArtifact, false);
    assert.equal(result.fallback, 'spotlight');
    assert.equal(result.status, status);
    assert.equal(result.reason, `artifact_${status}`);
    assert.equal(lookupCalls, 0);
  });
}

test('ready sequence maps source-local time to a zero-based frame and carries rotation', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ rotation: 90 }),
    artifactBaseUrl: BASE_URL,
    sourceTime: 1 / 30,
  });

  assert.equal(result.ok, true);
  assert.equal(result.frameIndex, 1);
  assert.equal(result.frameUrl, `${BASE_URL}/${ARTIFACT_ID}/frames/frame_000001.png`);
  assert.equal(result.rotation, 90);
  assert.equal(result.framePattern, SEQUENCE_FRAME_PATTERN);
});

test('frame boundaries are stable and source time beyond duration clamps to the last frame', () => {
  const manifest = readyManifest({ frame_count: 3 });
  assert.equal(
    mapSourceTimeToFrameIndex({ sourceTime: 0, fps: manifest.fps, timebase: manifest.timebase, frameCount: 3 }),
    0,
  );
  assert.equal(
    mapSourceTimeToFrameIndex({ sourceTime: 1 / 30 - 1e-8, fps: manifest.fps, timebase: manifest.timebase, frameCount: 3 }),
    0,
  );
  assert.equal(
    mapSourceTimeToFrameIndex({ sourceTime: 2 / 30, fps: manifest.fps, timebase: manifest.timebase, frameCount: 3 }),
    2,
  );
  assert.equal(
    mapSourceTimeToFrameIndex({ sourceTime: 999, fps: manifest.fps, timebase: manifest.timebase, frameCount: 3 }),
    2,
  );
});

test('timebase and fractional FPS stay aligned with backend rational timestamps', () => {
  assert.equal(
    mapSourceTimeToFrameIndex({
      sourceTime: 1001 / 30000,
      fps: '30000/1001',
      timebase: '1001/30000',
      frameCount: 10,
    }),
    1,
  );
  assert.equal(
    mapSourceTimeToFrameIndex({
      sourceTime: 3003 / 90000,
      fps: '30000/1001',
      timebase: '1/90000',
      frameCount: 10,
    }),
    1,
  );
});

test('lookup receives the backend artifact id and can supply a base URL', () => {
  const calls = [];
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest(),
    artifactLookup: (artifactId, manifest) => {
      calls.push({ artifactId, manifest });
      return { baseUrl: 'https://cdn.example.test/derived' };
    },
    sourceTime: 0,
  });
  assert.equal(result.frameUrl, `https://cdn.example.test/derived/${ARTIFACT_ID}/frames/frame_000000.png`);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].artifactId, ARTIFACT_ID);
  assert.deepEqual(calls[0].manifest, readyManifest());
});

test('URL joining preserves query/hash and encodes each derived path segment', () => {
  assert.equal(
    buildBackgroundIsolationFrameUrl({
      artifactBaseUrl: '/media/derived?token=a%2Fb#preview',
      artifactId: ARTIFACT_ID,
      frameIndex: 12,
    }),
    `/media/derived/${ARTIFACT_ID}/frames/frame_000012.png?token=a%2Fb#preview`,
  );
  assert.equal(
    buildBackgroundIsolationFrameUrl({
      artifactBaseUrl: '/media/derived',
      artifactId: 'bgseq1-bad/id',
      frameIndex: 0,
    }),
    null,
  );
});

test('legacy frame pattern remains readable but canonical backend pattern is emitted unchanged', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ frame_pattern: LEGACY_FRAME_PATTERN }),
    artifactBaseUrl: BASE_URL,
    sourceTime: 0,
  });
  assert.equal(result.ok, true);
  assert.equal(result.frameUrl, `${BASE_URL}/${ARTIFACT_ID}/frame_000000.png`);
  assert.equal(result.framePattern, LEGACY_FRAME_PATTERN);
});

test('manifest id mismatch, invalid status, and missing URL fail closed', () => {
  const mismatch = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ artifact_id: 'bgseq1-fedcba9876543210' }),
    artifactBaseUrl: BASE_URL,
  });
  assert.equal(mismatch.reason, 'manifest_invalid');
  assert.equal(mismatch.status, 'error');

  const stale = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ status: 'stale' }),
    artifactBaseUrl: BASE_URL,
  });
  assert.equal(stale.reason, 'manifest_stale');
  assert.equal(stale.status, 'stale');

  const noUrl = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest(),
  });
  assert.equal(noUrl.reason, 'artifact_url_missing');
  assert.equal(noUrl.status, 'missing');
});

test('ready manifest requires the metadata enforced by the sequence artifact store', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ worker_version: '' }),
    artifactBaseUrl: BASE_URL,
  });
  assert.equal(result.reason, 'manifest_invalid');
  assert.equal(result.status, 'error');
});

test('sequence_id is accepted for the separate sequence artifact contract', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig({ artifact: { sequence_id: ARTIFACT_ID, status: 'ready' } }),
    manifest: readyManifest(),
    artifactBaseUrl: BASE_URL,
  });
  assert.equal(result.ok, true);
  assert.equal(result.artifactId, ARTIFACT_ID);
});
