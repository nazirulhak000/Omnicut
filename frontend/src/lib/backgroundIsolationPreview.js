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

/** Group timeline clips by the source sequence they can share. */
export function groupBackgroundIsolationClips(clips = []) {
  const groups = [];
  const bySource = new Map();
  for (const clip of Array.isArray(clips) ? clips : []) {
    if (!clip?.source_path) continue;
    const rotation = [0, 90, 180, 270].includes(Number(clip.rotation))
      ? Number(clip.rotation)
      : 0;
    const sourcePath = String(clip.source_path);
    const key = `${sourcePath.toLowerCase()}\u0000${rotation}`;
    let group = bySource.get(key);
    if (!group) {
      group = { sourcePath, rotation, clips: [] };
      bySource.set(key, group);
      groups.push(group);
    }
    group.clips.push(clip);
  }
  return groups;
}

/** Return only completed isolation tasks that belong to the active project. */
export function completedBackgroundIsolationTasks(tasks = [], projectName = '') {
  return (Array.isArray(tasks) ? tasks : []).filter((task) => {
    if (task?.type !== 'background_isolation' || task.status !== 'completed') return false;
    if (!task.result?.artifact?.id || !task.payload?.source_path) return false;
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
} = {}) {
  if (projectConfig?.enabled === false) {
    return { state: 'off', label: 'Cutout ปิดอยู่', readyCount: 0, totalCount: 0 };
  }

  const sourceClips = (Array.isArray(clips) ? clips : []).filter((clip) => clip?.source_path);
  if (!sourceClips.length) {
    return { state: 'missing', label: 'Cutout ยังไม่มีคลิป', readyCount: 0, totalCount: 0 };
  }

  const statuses = sourceClips.map((clip) => clipBackgroundIsolationStatus(clip, projectConfig));
  if (statuses.every((status) => status === 'off')) {
    return { state: 'off', label: 'Cutout ปิดอยู่', readyCount: 0, totalCount: 0 };
  }
  const readyCount = statuses.filter((status) => status === 'ready').length;
  const failedCount = statuses.filter((status) => status === 'quality_failed').length;
  const processingCount = statuses.filter((status) => status === 'processing').length;
  const totalCount = sourceClips.length;
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
      label: failedCount === totalCount
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
    quality_failed: { label: 'Cutout คุณภาพไม่ผ่าน', detail: 'Preview ใช้ภาพต้นฉบับเพื่อความปลอดภัย' },
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
  let baseUrl = artifactBaseUrl;
  try {
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
    frameIndex = mapSourceTimeToFrameIndex({
      sourceTime,
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
