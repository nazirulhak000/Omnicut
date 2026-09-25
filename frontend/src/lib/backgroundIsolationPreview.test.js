import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LEGACY_FRAME_PATTERN,
  SEQUENCE_FRAME_PATTERN,
  buildBackgroundIsolationFrameUrl,
  backgroundIsolationWindowContainsClip,
  backgroundIsolationPrefetchTimes,
  completedBackgroundIsolationTasks,
  groupBackgroundIsolationClips,
  mapSourceTimeToFrameIndex,
  resolveBackgroundIsolationConfig,
  resolveBackgroundIsolationPreview,
  splitBackgroundIsolationOverlays,
  summarizeBackgroundIsolationPlan,
  summarizeBackgroundIsolationStatus,
  findBackgroundIsolationConflicts,
  clearBackgroundIsolationConflicts,
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

test('completed isolation task projection ignores another project and malformed tasks', () => {
  const tasks = [
    { type: 'background_isolation', status: 'completed', payload: { project_name: 'active', source_path: 'a.mp4' }, result: { artifact: { id: 'a' } } },
    { type: 'background_isolation', status: 'completed', payload: { project_name: 'other', source_path: 'a.mp4' }, result: { artifact: { id: 'b' } } },
    { type: 'background_isolation', status: 'processing', payload: { project_name: 'active', source_path: 'a.mp4' }, result: { artifact: { id: 'c' } } },
    { type: 'background_isolation', status: 'completed', payload: { project_name: 'active' }, result: { artifact: { id: 'd' } } },
  ];

  assert.deepEqual(completedBackgroundIsolationTasks(tasks, 'active'), [tasks[0]]);
});

test('explicit project disable overrides a ready clip artifact', () => {
  const clip = { background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } } };
  const project = { enabled: false, fallback: 'original' };

  assert.deepEqual(resolveBackgroundIsolationConfig(clip, project), project);
});

test('status summary stays off when project isolation is disabled, even if clips retain ready artifacts', () => {
  const result = summarizeBackgroundIsolationStatus({
    projectConfig: { enabled: false, fallback: 'original' },
    clips: [{
      source_path: 'D:/clips/product.mp4',
      background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } },
    }],
  });

  assert.equal(result.state, 'off');
  assert.equal(result.label, 'Cutout ปิดอยู่');
});

test('status summary treats an absent isolation config as off', () => {
  const result = summarizeBackgroundIsolationStatus({
    clips: [{ source_path: 'D:/clips/product.mp4' }],
  });

  assert.equal(result.state, 'off');
  assert.equal(result.label, 'Cutout ปิดอยู่');
});

test('status summary exposes failed artifacts instead of downgrading them to missing', () => {
  const result = summarizeBackgroundIsolationStatus({
    projectConfig: { enabled: true },
    clips: [{
      source_path: 'D:/clips/product.mp4',
      background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'stale' } },
    }],
  });

  assert.equal(result.state, 'quality_failed');
  assert.equal(result.label, 'Cutout คุณภาพไม่ผ่าน');
});

test('status summary reports processing before ready and ready only after every clip is ready', () => {
  const clips = [
    { source_path: 'D:/clips/a.mp4', background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } } },
    { source_path: 'D:/clips/b.mp4', background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'processing' } } },
  ];

  assert.equal(summarizeBackgroundIsolationStatus({ clips, projectConfig: { enabled: true } }).state, 'processing');
  assert.equal(summarizeBackgroundIsolationStatus({
    clips: clips.map((clip) => ({ ...clip, background_isolation: { ...clip.background_isolation, artifact: { ...clip.background_isolation.artifact, status: 'ready' } } })),
    projectConfig: { enabled: true },
  }).state, 'ready');
});

test('project processing marker prevents stale ready clips from reporting ready after reload', () => {
  const clips = [
    { source_path: 'D:/clips/a.mp4', background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } } },
    { source_path: 'D:/clips/b.mp4', background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } } },
  ];

  const result = summarizeBackgroundIsolationStatus({
    clips,
    projectConfig: { enabled: true, artifact: { id: null, status: 'processing' } },
  });

  assert.equal(result.state, 'processing');
  assert.equal(result.readyCount, 2);
  assert.equal(result.totalCount, 2);
});

test('project failure marker prevents stale ready clips from masking a failed prepare', () => {
  const result = summarizeBackgroundIsolationStatus({
    clips: [{
      source_path: 'D:/clips/a.mp4',
      background_isolation: { enabled: true, artifact: { id: ARTIFACT_ID, status: 'ready' } },
    }],
    projectConfig: { enabled: true, artifact: { id: null, status: 'error' } },
  });

  assert.equal(result.state, 'quality_failed');
  assert.equal(result.readyCount, 1);
  assert.equal(result.totalCount, 1);
});

test('splits disjoint trim windows while merging overlapping windows from one source', () => {
  const source = 'D:/clips/esseger.mov';
  const groups = groupBackgroundIsolationClips([
    { source_path: source, trim_start: 0, trim_end: 2 },
    { source_path: source, trim_start: 1.5, trim_end: 4 },
    { source_path: source.toUpperCase(), trim_start: 8, trim_end: 10 },
    { source_path: source, rotation: 90, trim_start: 12, trim_end: 14 },
  ]);

  assert.equal(groups.length, 3);
  assert.deepEqual(
    groups.map(({ rotation, start, duration, clips }) => ({ rotation, start, duration, clips: clips.length })),
    [
      { rotation: 0, start: 0, duration: 4, clips: 2 },
      { rotation: 0, start: 8, duration: 2, clips: 1 },
      { rotation: 90, start: 12, duration: 2, clips: 1 },
    ],
  );
});

test('uses loaded source duration for an open-ended clip and reports unresolved windows', () => {
  const source = 'D:/clips/product.mov';
  const resolved = groupBackgroundIsolationClips(
    [{ id: 'clip-1', source_path: source, trim_start: 3, trim_end: null }],
    { sourceDurations: { 'clip-1': 8.5 } },
  );
  const unresolved = groupBackgroundIsolationClips([
    { id: 'clip-2', source_path: source, trim_start: 3, trim_end: null },
  ]);

  assert.equal(resolved[0].start, 3);
  assert.equal(resolved[0].duration, 5.5);
  assert.equal(resolved[0].unresolved, false);
  assert.equal(unresolved[0].duration, null);
  assert.equal(unresolved[0].unresolved, true);
});

test('task window binds only clips covered by that source range', () => {
  const clip = { id: 'clip-1', source_path: 'D:/clips/product.mov', trim_start: 8, trim_end: 10 };
  assert.equal(backgroundIsolationWindowContainsClip({
    source_path: clip.source_path,
    rotation: 0,
    start: 8,
    duration: 2,
  }, clip), true);
  assert.equal(backgroundIsolationWindowContainsClip({
    source_path: clip.source_path,
    rotation: 0,
    start: 0,
    duration: 2,
  }, clip), false);
});

test('preflight summary reports exact jobs, seconds, frames, and unresolved windows', () => {
  const plan = summarizeBackgroundIsolationPlan([
    { duration: 2, clips: [{}, {}], unresolved: false },
    { duration: 1.5, clips: [{}], unresolved: false },
  ], { fps: 30 });
  const blocked = summarizeBackgroundIsolationPlan([
    { duration: null, clips: [{}], unresolved: true },
  ]);

  assert.deepEqual(plan, {
    jobCount: 2,
    clipCount: 3,
    unresolvedCount: 0,
    totalDuration: 3.5,
    frameCount: 105,
    fps: 30,
    ready: true,
  });
  assert.equal(blocked.ready, false);
  assert.equal(blocked.unresolvedCount, 1);
});

test('prefetch times follow rational FPS and stop at the artifact boundary', () => {
  assert.deepEqual(
    backgroundIsolationPrefetchTimes({
      sourceTime: 9.95,
      fps: '30/1',
      count: 4,
      sourceStart: 8,
      sourceDuration: 2,
    }).map((value) => Number(value.toFixed(6))),
    [9.95, 9.983333],
  );
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
    source_start: 0,
    source_duration: null,
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

test('windowed sequence subtracts source_start before selecting a frame', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig(),
    manifest: readyManifest({ source_start: 8, source_duration: 2, frame_count: 60 }),
    artifactBaseUrl: BASE_URL,
    sourceTime: 8 + (3 / 30),
  });

  assert.equal(result.ok, true);
  assert.equal(result.frameIndex, 3);
  assert.equal(result.sourceStart, 8);
  assert.equal(result.sourceDuration, 2);
});

test('windowed sequence fails closed when a clip asks for source time outside its artifact', () => {
  for (const sourceTime of [7.99, 10.01]) {
    const result = resolveBackgroundIsolationPreview({
      config: readyConfig(),
      manifest: readyManifest({ source_start: 8, source_duration: 2, frame_count: 60 }),
      artifactBaseUrl: BASE_URL,
      sourceTime,
    });
    assert.equal(result.useArtifact, false);
    assert.equal(result.reason, 'source_time_outside_artifact');
  }
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

test('ready artifact fails closed when the manifest quality does not match the requested quality', () => {
  const result = resolveBackgroundIsolationPreview({
    config: readyConfig({ quality: 'quality' }),
    manifest: readyManifest({ quality: 'balanced' }),
    artifactBaseUrl: BASE_URL,
  });

  assert.equal(result.useArtifact, false);
  assert.equal(result.reason, 'manifest_invalid');
  assert.equal(result.status, 'error');
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

test('findBackgroundIsolationConflicts correctly identifies clips with bg_blur or blur fit_mode', () => {
  const clips = [
    { id: 'c1', bg_blur: true, label: 'Intro' },
    { id: 'c2', fit_mode: 'contain', label: 'Feature' },
    { id: 'c3', fit_mode: 'blur', label: 'Demo' },
    { id: 'c4', label: 'Outro' },
  ];

  const conflicts = findBackgroundIsolationConflicts(clips);
  assert.equal(conflicts.length, 2);
  assert.deepEqual(conflicts.map((c) => c.idx), [0, 2]);
  assert.deepEqual(conflicts.map((c) => c.clip.id), ['c1', 'c3']);

  assert.deepEqual(findBackgroundIsolationConflicts([]), []);
  assert.deepEqual(findBackgroundIsolationConflicts(null), []);
});

test('clearBackgroundIsolationConflicts immutably removes bg_blur and blur fit_mode without mutating original clips', () => {
  const clips = [
    { id: 'c1', bg_blur: true, fit_mode: 'blur', speed: 1.2 },
    { id: 'c2', fit_mode: 'cover', speed: 1.0 },
  ];

  const cleared = clearBackgroundIsolationConflicts(clips);
  assert.equal(cleared.length, 2);
  assert.equal(cleared[0].bg_blur, undefined);
  assert.equal(cleared[0].fit_mode, undefined);
  assert.equal(cleared[0].speed, 1.2);
  assert.equal(cleared[1].fit_mode, 'cover');

  // Verify immutability
  assert.equal(clips[0].bg_blur, true);
  assert.equal(clips[0].fit_mode, 'blur');
  assert.deepEqual(clearBackgroundIsolationConflicts([]), []);
});
