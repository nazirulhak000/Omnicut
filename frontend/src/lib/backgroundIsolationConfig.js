/**
 * The one place that validates the optional `background_isolation` contract.
 *
 * Shared by editorProjectState.js (editor save/load) and timelineSchema.js
 * (Timeline v2 <-> manifest) so adding an engine, model or field means editing
 * a single file instead of two copies that can drift apart.
 */

import { CUTOUT_ENGINE_MODELS, resolveCutoutEngineModel } from './cutoutEngineModel.js';
import { normalizeSubjectPoints } from './subjectPoints.js';

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map(cloneValue);
  if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]));
  return value;
}

const BACKGROUND_ISOLATION_SCHEMA_VERSION = 1;
const BACKGROUND_ISOLATION_OPTIONS = {
  mode: new Set(['cutout']),
  engine: new Set(Object.keys(CUTOUT_ENGINE_MODELS)),
  model: new Set(Object.values(CUTOUT_ENGINE_MODELS).flat()),
  quality: new Set(['draft', 'balanced', 'quality']),
  fallback: new Set(['spotlight', 'original', 'skip']),
};
const BACKGROUND_ISOLATION_STATUSES = new Set([
  'missing',
  'processing',
  'ready',
  'stale',
  'error',
  'cancelled',
]);

/**
 * Keep the optional isolation contract inert in the editor until a later
 * phase consumes it.  Valid objects are cloned losslessly so new backend
 * metadata survives a save/load round-trip; malformed values fail closed.
 */
export function normalizeBackgroundIsolation(value) {
  if (value === null || value === undefined) return null;
  if (!isRecord(value)) return null;
  if (value.schema_version !== undefined && value.schema_version !== BACKGROUND_ISOLATION_SCHEMA_VERSION) return null;
  if (value.enabled !== undefined && typeof value.enabled !== 'boolean') return null;

  // An explicitly disabled feature is inert. Preserve its metadata without
  // validating options that no consumer will read in this state.
  if (value.enabled !== true) return cloneValue(value);

  for (const [key, choices] of Object.entries(BACKGROUND_ISOLATION_OPTIONS)) {
    if (value[key] !== undefined && (typeof value[key] !== 'string' || !choices.has(value[key]))) return null;
  }
  // Infer old model-only configs without rewriting saved metadata. Explicit
  // mismatched pairs must fail closed instead of preparing another model.
  const { engine } = resolveCutoutEngineModel(value);
  if (value.model !== undefined && !CUTOUT_ENGINE_MODELS[engine].includes(value.model)) return null;

  if (value.artifact !== undefined && value.artifact !== null && !isRecord(value.artifact)) return null;
  if (isRecord(value.artifact)) {
    const artifact = value.artifact;
    if (artifact.schema_version !== undefined && artifact.schema_version !== 1) return null;
    if (artifact.status !== undefined && !BACKGROUND_ISOLATION_STATUSES.has(artifact.status)) return null;
    if (artifact.status === 'ready' && (typeof artifact.id !== 'string' || artifact.id.length === 0)) return null;
  }

  // Points picked on the preview and the auto-prompt switch travel with the
  // project: the backend reads them before it derives the SAM 2 subject point.
  // A non-boolean switch fails closed like the other options, while unusable
  // points are simply dropped.
  if (value.auto_prompt !== undefined && typeof value.auto_prompt !== 'boolean') return null;
  if (value.prompt_reference_start !== undefined && (typeof value.prompt_reference_start !== 'number'
    || !Number.isFinite(value.prompt_reference_start) || value.prompt_reference_start < 0)) return null;
  if (value.prompt_reference_source !== undefined && (typeof value.prompt_reference_source !== 'string'
    || !value.prompt_reference_source.trim() || value.prompt_reference_source.length > 4096
    || value.prompt_reference_source.includes('\0') || value.prompt_reference_start === undefined)) return null;
  const clone = cloneValue(value);
  const subjectPoints = normalizeSubjectPoints(value.subject_points);
  if (subjectPoints.length > 0) {
    clone.subject_points = subjectPoints;
  } else {
    delete clone.subject_points;
  }
  if (value.auto_prompt !== false) delete clone.auto_prompt;

  return clone;
}
