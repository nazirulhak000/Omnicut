/**
 * Pure Preview adapter for Background Isolation sequence artifacts.
 *
 * This module deliberately has no browser I/O: it does not fetch, inspect a
 * URL, import rembg, or mutate a cache.  The caller supplies either a base
 * URL or a pure lookup function and decides how to render the returned URL.
 */

export const BACKGROUND_ISOLATION_SCHEMA_VERSION = 1;
export const SEQUENCE_SCHEMA_VERSION = 1;
export const SEQUENCE_ARTIFACT_ID_PATTERN = /^bgseq1-[0-9a-f]{16}$/;
export const SEQUENCE_FRAME_PATTERN = 'frames/frame_%06d.png';
export const LEGACY_FRAME_PATTERN = 'frame_%06d.png';
export const SUPPORTED_MODES = Object.freeze(['cutout']);
export const SUPPORTED_ENGINES = Object.freeze(['rembg']);
export const SUPPORTED_MODELS = Object.freeze(['u2netp', 'u2net', 'isnet-general-use']);
export const SUPPORTED_QUALITIES = Object.freeze(['draft', 'balanced', 'quality']);
export const SEQUENCE_STATUSES = Object.freeze([
  'missing',
  'processing',
  'ready',
  'stale',
  'error',
  'cancelled',
]);
export const FALLBACKS = Object.freeze(['spotlight', 'original', 'skip']);
export const BACKGROUND_ISOLATION_UI_STATES = Object.freeze([
  'off',
  'missing',
  'processing',
  'ready',
  'partial',
  'quality_failed',
]);

const DEFAULT_FALLBACK = 'spotlight';
const RATIONAL_PATTERN = /^(\d+)\/(\d+)$/;
const FRAME_PATTERN_PATTERN = /^(?:(frames)\/)?frame_%06d\.png$/;
const EPSILON = 1e-9;

function finiteNonNegative(value) {
  const candidate = Number(value);
  return Number.isFinite(candidate) && candidate >= 0 ? candidate : null;
}

function clipSourceWindow(clip, sourceDurations = {}) {
  const start = finiteNonNegative(clip?.trim_start) ?? 0;
  const candidates = [
    clip?.trim_end,
    clip?.source_duration,
    clip?.sourceDuration,
    clip?.id != null ? sourceDurations?.[clip.id] : null,
  ];
  const end = candidates
    .map(finiteNonNegative)
    .find((candidate) => candidate != null && candidate > start + EPSILON);
  return {
    start,
    end: end ?? null,
    duration: end == null ? null : end - start,
    unresolved: end == null,
  };
}

/**
 * Group clips into the smallest reusable source windows.
 *
 * Overlapping windows share one job. Disjoint windows remain separate so a
 * short edit never runs rembg across unused minutes between two trims.
 */
export function groupBackgroundIsolationClips(clips = [], { sourceDurations = {} } = {}) {
  const buckets = new Map();
  for (const clip of Array.isArray(clips) ? clips : []) {
    if (!clip?.source_path) continue;
    const rotation = [0, 90, 180, 270].includes(Number(clip.rotation))
      ? Number(clip.rotation)
      : 0;
    const sourcePath = String(clip.source_path);
    const key = `${sourcePath.toLowerCase()}\u0000${rotation}`;
    if (!buckets.has(key)) buckets.set(key, { sourcePath, rotation, windows: [] });
    buckets.get(key).windows.push({ clip, ...clipSourceWindow(clip, sourceDurations) });
  }

  const groups = [];
  buckets.forEach(({ sourcePath, rotation, windows }) => {
    const sorted = windows.sort((a, b) => a.start - b.start || (a.end ?? Infinity) - (b.end ?? Infinity));
    for (const window of sorted) {
      const previous = groups.at(-1);
      const canMerge = previous
        && previous.sourcePath.toLowerCase() === sourcePath.toLowerCase()
        && previous.rotation === rotation
        && !previous.unresolved
        && !window.unresolved
        && window.start <= previous.end + EPSILON;
      if (canMerge) {
        previous.end = Math.max(previous.end, window.end);
        previous.duration = previous.end - previous.start;
        previous.clips.push(window.clip);
        continue;
      }
      groups.push({
        sourcePath,
        rotation,
        start: window.start,
        end: window.end,
        duration: window.duration,
        unresolved: window.unresolved,
        clips: [window.clip],
      });
    }
  });
  return groups;
}

/** Match a persisted task window back to the clips it actually covers. */
export function backgroundIsolationWindowContainsClip(window, clip, { sourceDurations = {} } = {}) {
  if (!window || !clip?.source_path) return false;
  const rotation = [0, 90, 180, 270].includes(Number(clip.rotation)) ? Number(clip.rotation) : 0;
  const windowRotation = [0, 90, 180, 270].includes(Number(window.rotation)) ? Number(window.rotation) : 0;
  if (
    String(clip.source_path).toLowerCase() !== String(window.sourcePath ?? window.source_path ?? '').toLowerCase()
    || rotation !== windowRotation
  ) return false;

  const clipWindow = clipSourceWindow(clip, sourceDurations);
  const start = finiteNonNegative(window.start) ?? 0;
  const duration = window.duration == null ? null : finiteNonNegative(window.duration);
  if (clipWindow.unresolved || duration === 0) return false;
  const end = duration == null ? Infinity : start + duration;
  return clipWindow.start >= start - EPSILON && clipWindow.end <= end + EPSILON;
}

/** Build a deterministic preflight summary before any expensive work starts. */
export function summarizeBackgroundIsolationPlan(groups = [], { fps = 30 } = {}) {
  const safeFps = Number.isFinite(Number(fps)) && Number(fps) > 0 ? Number(fps) : 30;
  const list = Array.isArray(groups) ? groups : [];
  const unresolvedCount = list.filter((group) => group?.unresolved || group?.duration == null).length;
  const totalDuration = list.reduce((sum, group) => {
    const duration = Number(group?.duration);
    return sum + (Number.isFinite(duration) && duration > 0 ? duration : 0);
  }, 0);
  const frameCount = list.reduce((sum, group) => {
    const duration = Number(group?.duration);
    return sum + (Number.isFinite(duration) && duration > 0 ? Math.ceil(duration * safeFps - EPSILON) : 0);
  }, 0);
  return {
    jobCount: list.length,
    clipCount: list.reduce((sum, group) => sum + (Array.isArray(group?.clips) ? group.clips.length : 0), 0),
    unresolvedCount,
    totalDuration,
    frameCount,
    fps: safeFps,
    ready: list.length > 0 && unresolvedCount === 0 && frameCount > 0,
  };
}

/** Find clips that conflict with background isolation (e.g. background blur enabled). */
export function findBackgroundIsolationConflicts(clipList = []) {
  if (!Array.isArray(clipList)) return [];
  return clipList
    .map((clip, idx) => ({ clip, idx }))
    .filter(({ clip }) => Boolean(clip?.bg_blur || clip?.fit_mode === 'blur'));
}

/** Clear conflicting background blur properties from clip list immutably. */
export function clearBackgroundIsolationConflicts(clipList = []) {
  if (!Array.isArray(clipList)) return [];
  return clipList.map((clip) => {
    if (!clip?.bg_blur && clip?.fit_mode !== 'blur') return clip;
    const next = { ...clip };
    delete next.bg_blur;
    if (next.fit_mode === 'blur') {
      delete next.fit_mode;
    }
    return next;
  });
}

export function backgroundIsolationPrefetchTimes({
  sourceTime,
  fps,
  count = 3,
  sourceStart = 0,
  sourceDuration = null,
} = {}) {
  const start = parseNonNegativeTime(sourceTime);
  const ratio = parsePositiveRational(fps, 'fps');
  const frameStep = ratio.denominator / ratio.numerator;
  const limit = sourceDuration == null ? Infinity : sourceStart + sourceDuration;
  const total = Math.max(1, Math.min(8, Math.floor(Number(count) || 1)));
  return Array.from({ length: total }, (_, index) => start + index * frameStep)
    .filter((time) => time <= limit + EPSILON);
}

/** Return only completed isolation tasks that belong to the active project. */
export function completedBackgroundIsolationTasks(tasks = [], projectName = '', requestId = null) {
  return (Array.isArray(tasks) ? tasks : []).filter((task) => {
    if (task?.type !== 'background_isolation' || task.status !== 'completed') return false;
    if (!task.result?.artifact?.id || !task.payload?.source_path) return false;
    if (requestId != null && task.payload?.config?.request_id !== requestId) return false;
    return !task.payload.project_name || task.payload.project_name === projectName;
  });
}

function fallbackMode(value) {
  return FALLBACKS.includes(value) ? value : DEFAULT_FALLBACK;
}

function normalizedChoice(value, choices, defaultValue) {
  if (value === undefined || value === null) return defaultValue;
  if (typeof value !== 'string') return null;
  const candidate = value.trim().toLowerCase();
  return choices.includes(candidate) ? candidate : null;
}

function parsePositiveRational(value, label) {
  let numerator;
  let denominator;

  if (typeof value === 'number') {
    if (!Number.isFinite(value) || value <= 0) {
      throw new TypeError(`${label} must be positive`);
    }
    numerator = value;
    denominator = 1;
  } else if (typeof value === 'string') {
    const match = RATIONAL_PATTERN.exec(value.trim());
    if (!match) throw new TypeError(`${label} must be a rational`);
    numerator = Number(match[1]);
    denominator = Number(match[2]);
  } else if (Array.isArray(value) && value.length === 2) {
    numerator = Number(value[0]);
    denominator = Number(value[1]);
  } else {
    throw new TypeError(`${label} must be a rational`);
  }

  if (
    !Number.isSafeInteger(numerator) ||
    !Number.isSafeInteger(denominator) ||
    numerator <= 0 ||
    denominator <= 0
  ) {
    throw new TypeError(`${label} must contain positive safe integers`);
  }

  return { numerator, denominator };
}

function parseNonNegativeTime(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    throw new TypeError('source time must be a non-negative finite number');
  }
  return value;
}

function parseFramePattern(value) {
  if (typeof value !== 'string') throw new TypeError('frame pattern is required');
  const match = FRAME_PATTERN_PATTERN.exec(value);
  if (!match) throw new TypeError('unsupported frame pattern');
  return {
    value,
    directory: match[1] ? 'frames' : '',
  };
}

function parseRotation(value) {
  if (![0, 90, 180, 270].includes(value)) {
    throw new TypeError('rotation must be 0, 90, 180, or 270');
  }
  return value;
}

function parsePositiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new TypeError(`${label} must be a positive integer`);
  }
  return value;
}

function normalizedConfig(value) {
  if (value === undefined || value === null) {
    return {
      absent: true,
      enabled: false,
      fallback: 'legacy',
      artifactId: null,
      artifactStatus: 'missing',
    };
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {
      absent: false,
      enabled: false,
      fallback: DEFAULT_FALLBACK,
      artifactId: null,
      artifactStatus: 'missing',
    };
  }

  if (value.schema_version !== undefined && value.schema_version !== BACKGROUND_ISOLATION_SCHEMA_VERSION) {
    return {
      absent: false,
      invalid: true,
      enabled: false,
      fallback: DEFAULT_FALLBACK,
      artifactId: null,
      artifactStatus: 'error',
    };
  }

  if (value.enabled !== undefined && typeof value.enabled !== 'boolean') {
    return {
      absent: false,
      invalid: true,
      enabled: false,
      fallback: DEFAULT_FALLBACK,
      artifactId: null,
      artifactStatus: 'error',
    };
  }

  const artifact = value.artifact && typeof value.artifact === 'object'
    ? value.artifact
    : {};
  const artifactId = artifact.sequence_id ?? artifact.sequenceId ?? artifact.id ?? null;
  const choices = [
    normalizedChoice(value.mode, SUPPORTED_MODES, 'cutout'),
    normalizedChoice(value.engine, SUPPORTED_ENGINES, 'rembg'),
    normalizedChoice(value.model, SUPPORTED_MODELS, 'u2net'),
    normalizedChoice(value.quality, SUPPORTED_QUALITIES, 'balanced'),
    normalizedChoice(value.fallback, FALLBACKS, DEFAULT_FALLBACK),
  ];
  const artifactIsObject = value.artifact === undefined || value.artifact === null || (
    value.artifact && typeof value.artifact === 'object' && !Array.isArray(value.artifact)
  );
  const artifactSchemaIsValid = artifact.schema_version === undefined || artifact.schema_version === 1;
  const artifactStatusIsValid = artifact.status === undefined || SEQUENCE_STATUSES.includes(artifact.status);
  const invalid = choices.some(choice => choice === null) || !artifactIsObject || !artifactSchemaIsValid || !artifactStatusIsValid;

  return {
    absent: false,
    invalid,
    enabled: value.enabled === true && !invalid,
    fallback: choices[4] ?? DEFAULT_FALLBACK,
    quality: choices[3] ?? 'balanced',
    artifactId,
    artifactStatus: artifact.status ?? 'missing',
  };
}

function fallbackResult(config, reason, status = config.artifactStatus) {
  return {
    ok: false,
    kind: 'fallback',
    useArtifact: false,
    fallback: config.absent ? 'legacy' : config.fallback,
    reason,
    status,
    artifactId: null,
    frameIndex: null,
    frameUrl: null,
    rotation: 0,
  };
}

/**
 * Resolve clip/project isolation config with an explicit project disable as
 * the master switch. Prepared clip artifacts can outlive a later toggle.
 */
export function resolveBackgroundIsolationConfig(clip, projectConfig) {
  if (projectConfig && typeof projectConfig === 'object' && !Array.isArray(projectConfig)
    && projectConfig.enabled === false) {
    return projectConfig;
  }
  if (clip && typeof clip === 'object' && !Array.isArray(clip)) {
    if (clip.background_isolation !== undefined && clip.background_isolation !== null) {
      return clip.background_isolation;
    }
    if (clip.backgroundIsolation !== undefined && clip.backgroundIsolation !== null) {
      return clip.backgroundIsolation;
    }
  }
  return projectConfig;
}

function clipBackgroundIsolationStatus(clip, projectConfig) {
  const config = resolveBackgroundIsolationConfig(clip, projectConfig);
  if (config === undefined || config === null) return 'off';

  const preview = resolveBackgroundIsolationPreview({ config });
  if (preview.reason === 'invalid_config') return 'quality_failed';
  if (config.enabled !== true) return 'off';
  const artifactStatus = config.artifact?.status ?? 'missing';
  if (artifactStatus === 'processing') return 'processing';
  if (artifactStatus === 'ready') return 'ready';
  if (['stale', 'error', 'cancelled'].includes(artifactStatus)) return 'quality_failed';
  return 'missing';
}

/**
 * Summarise the safe state of all timeline clips for editor chrome.
 *
 * This intentionally treats an explicit project disable as authoritative and
 * treats any failed/stale artifact as a quality failure.  The summary is only
 * a user-facing hint; frame/manifest validation still happens per frame in
 * resolveBackgroundIsolationPreview.
 */
export function summarizeBackgroundIsolationStatus({
  clips = [],
  projectConfig = null,
  preparing = false,
  artifactAvailability = null,
} = {}) {
  if (projectConfig?.enabled === false) {
    return { state: 'off', label: 'Cutout ปิดอยู่', readyCount: 0, totalCount: 0 };
  }

  const sourceClips = (Array.isArray(clips) ? clips : []).filter((clip) => clip?.source_path);
  if (!sourceClips.length) {
    return { state: 'missing', label: 'Cutout ยังไม่มีคลิป', readyCount: 0, totalCount: 0 };
  }

  const statuses = sourceClips.map((clip) => {
    const status = clipBackgroundIsolationStatus(clip, projectConfig);
    if (status !== 'ready' || artifactAvailability == null) return status;
    const artifact = resolveBackgroundIsolationConfig(clip, projectConfig)?.artifact;
    const id = artifact?.id || artifact?.sequence_id;
    if (!id || artifactAvailability[id] === false) return 'quality_failed';
    return artifactAvailability[id] === true ? 'ready' : 'processing';
  });
  if (statuses.every((status) => status === 'off')) {
    return { state: 'off', label: 'Cutout ปิดอยู่', readyCount: 0, totalCount: 0 };
  }
  const readyCount = statuses.filter((status) => status === 'ready').length;
  const failedCount = statuses.filter((status) => status === 'quality_failed').length;
  const processingCount = statuses.filter((status) => status === 'processing').length;
  const totalCount = sourceClips.length;
  const missingCacheCount = artifactAvailability == null ? 0 : sourceClips.filter((clip) => {
    if (clipBackgroundIsolationStatus(clip, projectConfig) !== 'ready') return false;
    const artifact = resolveBackgroundIsolationConfig(clip, projectConfig)?.artifact;
    return artifactAvailability[artifact?.id || artifact?.sequence_id] === false;
  }).length;
  // During a reload, old per-clip configs can still say `ready` while the
  // project-level job is being resumed or has just failed. Keep the marker
  // authoritative for the aggregate state, while retaining readyCount for
  // progress display.
  const projectArtifactStatus = projectConfig?.enabled === true
    ? projectConfig?.artifact?.status
    : null;
  const projectProcessing = projectArtifactStatus === 'processing';
  const projectFailed = ['stale', 'error', 'cancelled'].includes(projectArtifactStatus);

  if (preparing || projectProcessing || processingCount > 0) {
    return {
      state: 'processing',
      label: `กำลังเตรียม Cutout (${readyCount}/${totalCount})`,
      readyCount,
      totalCount,
    };
  }
  if (projectFailed || failedCount > 0) {
    return {
      state: 'quality_failed',
      label: missingCacheCount > 0
        ? 'ไฟล์ Cutout หาย กรุณาเตรียมใหม่'
        : failedCount === totalCount
          ? 'Cutout คุณภาพไม่ผ่าน'
          : `Cutout คุณภาพไม่ผ่านบางส่วน (${readyCount}/${totalCount})`,
      readyCount,
      totalCount,
    };
  }
  if (readyCount === totalCount) {
    return { state: 'ready', label: `Cutout พร้อมใช้ (${readyCount}/${totalCount})`, readyCount, totalCount };
  }
  if (readyCount > 0) {
    return { state: 'partial', label: `Cutout พร้อมบางส่วน (${readyCount}/${totalCount})`, readyCount, totalCount };
  }
  return { state: 'missing', label: 'Cutout ยังไม่พร้อม', readyCount, totalCount };
}

export function backgroundIsolationStatusMeta(status = 'off') {
  const meta = {
    off: { label: 'Cutout ปิดอยู่', detail: 'Preview ใช้ภาพต้นฉบับ' },
    missing: { label: 'Cutout ยังไม่พร้อม', detail: 'Preview ใช้ภาพต้นฉบับจนกว่า artifact จะพร้อม' },
    processing: { label: 'กำลังเตรียม Cutout', detail: 'Preview ใช้ภาพต้นฉบับชั่วคราว' },
    ready: { label: 'Cutout พร้อมใช้', detail: 'Preview ใช้ artifact ที่ตรวจสอบแล้ว' },
    partial: { label: 'Cutout พร้อมบางส่วน', detail: 'บางคลิปยังใช้ภาพต้นฉบับ' },
    quality_failed: { label: 'Cutout ใช้งานไม่ได้', detail: 'ตรวจไฟล์ Cutout และเตรียมใหม่ก่อน Render' },
  };
  return meta[BACKGROUND_ISOLATION_UI_STATES.includes(status) ? status : 'missing'];
}

function resolveLookupBase(artifactLookup, artifactId, manifest) {
  if (typeof artifactLookup === 'function') {
    const result = artifactLookup(artifactId, manifest);
    if (typeof result === 'string') return result;
    if (result && typeof result === 'object') {
      return result.baseUrl ?? result.baseURL ?? null;
    }
    return null;
  }

  if (artifactLookup instanceof Map) {
    const result = artifactLookup.get(artifactId);
    return typeof result === 'string'
      ? result
      : result?.baseUrl ?? result?.baseURL ?? null;
  }

  if (artifactLookup && typeof artifactLookup === 'object') {
    const result = artifactLookup[artifactId];
    return typeof result === 'string'
      ? result
      : result?.baseUrl ?? result?.baseURL ?? null;
  }

  return null;
}

function appendPath(baseUrl, segments) {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) return null;
  const trimmed = baseUrl.trim();
  const hashIndex = trimmed.indexOf('#');
  const queryIndex = trimmed.indexOf('?');
  const suffixIndex = [hashIndex, queryIndex].filter(index => index >= 0).sort((a, b) => a - b)[0];
  const path = suffixIndex === undefined ? trimmed : trimmed.slice(0, suffixIndex);
  const suffix = suffixIndex === undefined ? '' : trimmed.slice(suffixIndex);
  return `${path.replace(/\/+$/, '')}/${segments.map(encodeURIComponent).join('/')}${suffix}`;
}

export function buildBackgroundIsolationFrameUrl({
  artifactBaseUrl,
  artifactId,
  framePattern = SEQUENCE_FRAME_PATTERN,
  frameIndex,
}) {
  if (typeof artifactId !== 'string' || !SEQUENCE_ARTIFACT_ID_PATTERN.test(artifactId)) {
    return null;
  }
  if (!Number.isSafeInteger(frameIndex) || frameIndex < 0) return null;

  let pattern;
  try {
    pattern = parseFramePattern(framePattern);
  } catch {
    return null;
  }

  const frameName = `frame_${String(frameIndex).padStart(6, '0')}.png`;
  const segments = pattern.directory ? [artifactId, pattern.directory, frameName] : [artifactId, frameName];
  return appendPath(artifactBaseUrl, segments);
}

/**
 * Convert source-local seconds to the backend's zero-based frame index.
 *
 * The calculation first quantizes the timestamp to the manifest timebase,
 * then converts those ticks using the manifest FPS.  This keeps 1/90000 plus
 * 30000/1001 deterministic and avoids using a clip index as a frame index.
 */
export function mapSourceTimeToFrameIndex({ sourceTime, fps, timebase, frameCount }) {
  const seconds = parseNonNegativeTime(sourceTime);
  const fpsRatio = parsePositiveRational(fps, 'fps');
  const timebaseRatio = parsePositiveRational(timebase, 'timebase');
  const count = parsePositiveInteger(frameCount, 'frame count');

  const ticks = Math.floor(
    (seconds * timebaseRatio.denominator) / timebaseRatio.numerator + EPSILON,
  );
  const rawIndex = Math.floor(
    (ticks * timebaseRatio.numerator * fpsRatio.numerator) /
      (timebaseRatio.denominator * fpsRatio.denominator) + EPSILON,
  );
  return Math.min(Math.max(rawIndex, 0), count - 1);
}

/**
 * Resolve one Preview frame without performing any I/O.
 *
 * `artifactLookup` is intentionally a caller-owned pure lookup.  It may be a
 * function, Map, or object keyed by sequence artifact id.  A function is
 * called as `(artifactId, manifest)` and must return a base URL or
 * `{ baseUrl }`.
 */
export function resolveBackgroundIsolationPreview({
  config,
  manifest,
  artifactBaseUrl,
  artifactLookup,
  sourceTime = 0,
} = {}) {
  const normalized = normalizedConfig(config);

  if (normalized.absent) return fallbackResult(normalized, 'config_absent', 'legacy');
  if (normalized.invalid) return fallbackResult(normalized, 'invalid_config', 'disabled');
  if (!normalized.enabled) return fallbackResult(normalized, 'disabled', 'disabled');
  if (!SEQUENCE_STATUSES.includes(normalized.artifactStatus)) {
    return fallbackResult(normalized, 'invalid_artifact_status', 'error');
  }
  if (normalized.artifactStatus !== 'ready') {
    return fallbackResult(normalized, `artifact_${normalized.artifactStatus}`, normalized.artifactStatus);
  }
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    return fallbackResult(normalized, 'manifest_missing', 'missing');
  }

  let framePattern;
  let frameIndex;
  let sourceStart;
  let sourceDuration;
  let baseUrl = artifactBaseUrl;
  try {
    if (manifest.schema_version === 2) {
      if (manifest.status !== 'ready' || manifest.artifact_id !== normalized.artifactId
          || !SEQUENCE_ARTIFACT_ID_PATTERN.test(manifest.artifact_id)
          || manifest.video_file !== 'cutout.webm' || manifest.codec !== 'vp9-alpha'
          || typeof manifest.source_fingerprint !== 'string' || !manifest.source_fingerprint.trim()
          || manifest.quality !== normalized.quality) throw new TypeError('video artifact');
      parsePositiveInteger(manifest.frame_count, 'frame count');
      parsePositiveInteger(manifest.width, 'width');
      parsePositiveInteger(manifest.height, 'height');
      const videoFps = parsePositiveRational(manifest.fps, 'fps');
      parseRotation(manifest.rotation);
      sourceStart = parseNonNegativeTime(manifest.source_start);
      sourceDuration = parseNonNegativeTime(manifest.source_duration);
      const absoluteSourceTime = parseNonNegativeTime(sourceTime);
      if (sourceDuration <= 0 || absoluteSourceTime < sourceStart - EPSILON
          || absoluteSourceTime > sourceStart + sourceDuration + EPSILON) {
        return fallbackResult(normalized, 'source_time_outside_artifact', 'error');
      }
      const videoTime = Math.min(
        Math.max(0, absoluteSourceTime - sourceStart),
        Math.max(0, (manifest.frame_count - 1) * videoFps.denominator / videoFps.numerator),
      );
      const videoBase = String(artifactBaseUrl || '').replace(/\/sequences\/?$/, '/videos');
      if (!videoBase.startsWith('/api/background-isolation/videos')) throw new TypeError('video URL');
      const proxy = manifest.preview;
      const useProxy = proxy?.video_file === 'preview.webm' && proxy.codec === 'vp9-alpha'
        && proxy.derived_from === 'cutout.webm' && proxy.frame_mapping === 'identity'
        && typeof manifest.sha256 === 'string' && /^[0-9a-f]{64}$/.test(manifest.sha256)
        && proxy.master_sha256 === manifest.sha256
        && proxy.frame_count === manifest.frame_count && proxy.fps === manifest.fps
        && Number.isInteger(proxy.width) && proxy.width > 0 && proxy.width <= manifest.width
        && Number.isInteger(proxy.height) && proxy.height > 0 && proxy.height <= manifest.height
        && Math.abs(proxy.width / proxy.height - manifest.width / manifest.height) < 0.005;
      return {
        ok: true, kind: 'artifact', useArtifact: true, fallback: null,
        reason: null, status: 'ready', artifactId: manifest.artifact_id,
        videoUrl: `${videoBase}/${manifest.artifact_id}/${useProxy ? 'preview.webm' : 'cutout.webm'}`, videoTime,
        masterVideoUrl: `${videoBase}/${manifest.artifact_id}/cutout.webm`, usesProxy: useProxy,
        rotation: manifest.rotation, fps: manifest.fps, width: manifest.width,
        height: manifest.height, sourceStart, sourceDuration,
      };
    }
    if (manifest.schema_version !== SEQUENCE_SCHEMA_VERSION) throw new TypeError('schema');
    if (manifest.status !== 'ready') {
      const status = SEQUENCE_STATUSES.includes(manifest.status) ? manifest.status : 'error';
      return fallbackResult(normalized, `manifest_${manifest.status ?? 'missing'}`, status);
    }
    if (manifest.artifact_id !== normalized.artifactId) throw new TypeError('artifact id');
    if (!SEQUENCE_ARTIFACT_ID_PATTERN.test(manifest.artifact_id)) throw new TypeError('artifact id');
    if (typeof manifest.source_fingerprint !== 'string' || !manifest.source_fingerprint.trim()) throw new TypeError('source fingerprint');
    if (typeof manifest.algorithm !== 'string' || !manifest.algorithm.trim()) throw new TypeError('algorithm');
    if (!SUPPORTED_ENGINES.includes(manifest.engine)) throw new TypeError('engine');
    if (!SUPPORTED_MODELS.includes(manifest.model)) throw new TypeError('model');
    if (!SUPPORTED_QUALITIES.includes(manifest.quality)) throw new TypeError('quality');
    if (manifest.quality !== normalized.quality) throw new TypeError('quality mismatch');
    if (typeof manifest.worker_version !== 'string' || !manifest.worker_version.trim()) throw new TypeError('worker version');
    framePattern = parseFramePattern(manifest.frame_pattern);
    parseRotation(manifest.rotation);
    parsePositiveInteger(manifest.width, 'width');
    parsePositiveInteger(manifest.height, 'height');
    sourceStart = parseNonNegativeTime(manifest.source_start ?? 0);
    sourceDuration = manifest.source_duration == null
      ? null
      : parseNonNegativeTime(manifest.source_duration);
    if (sourceDuration === 0) throw new TypeError('source duration');
    const absoluteSourceTime = parseNonNegativeTime(sourceTime);
    if (
      absoluteSourceTime < sourceStart - EPSILON
      || (sourceDuration != null && absoluteSourceTime > sourceStart + sourceDuration + EPSILON)
    ) {
      return fallbackResult(normalized, 'source_time_outside_artifact', 'error');
    }
    frameIndex = mapSourceTimeToFrameIndex({
      sourceTime: Math.max(0, absoluteSourceTime - sourceStart),
      fps: manifest.fps,
      timebase: manifest.timebase,
      frameCount: manifest.frame_count,
    });
    if (artifactLookup !== undefined) {
      baseUrl = resolveLookupBase(artifactLookup, manifest.artifact_id, manifest);
    }
  } catch {
    return fallbackResult(normalized, 'manifest_invalid', 'error');
  }

  const frameUrl = buildBackgroundIsolationFrameUrl({
    artifactBaseUrl: baseUrl,
    artifactId: manifest.artifact_id,
    framePattern: framePattern.value,
    frameIndex,
  });
  if (!frameUrl) return fallbackResult(normalized, 'artifact_url_missing', 'missing');

  return {
    ok: true,
    kind: 'artifact',
    useArtifact: true,
    fallback: null,
    reason: null,
    status: 'ready',
    artifactId: manifest.artifact_id,
    frameIndex,
    frameUrl,
    rotation: manifest.rotation,
    framePattern: framePattern.value,
    fps: manifest.fps,
    timebase: manifest.timebase,
    width: manifest.width,
    height: manifest.height,
    sourceStart,
    sourceDuration,
  };
}

/**
 * Subject isolation adds one intentional z-order exception: the product Hook
 * is painted before the isolated subject, while captions and other overlays
 * remain in the foreground.  Keep this classification pure so Preview and
 * any editor surface can share the same rule.
 */
export function splitBackgroundIsolationOverlays(overlays = []) {
  const list = Array.isArray(overlays) ? overlays : [];
  const behindSubject = [];
  const foreground = [];
  list.forEach((overlay) => {
    const isHook = overlay?.kind === 'hook' || overlay?.type === 'hook_header';
    (isHook ? behindSubject : foreground).push(overlay);
  });
  return { behindSubject, foreground };
}

export default resolveBackgroundIsolationPreview;
