/**
 * Pure state transitions for the Cutout "pick the product" points.
 *
 * Kept out of EditorShell so the two rules that matter can be tested without
 * rendering the editor:
 *   1. a point edit must never leave a ready artifact looking current, because
 *      the artifact was built from the old points;
 *   2. the prepare request must carry the picked points even when the project
 *      marker was not enabled yet.
 */
import { defaultCutoutModel, resolveCutoutEngineModel } from './cutoutEngineModel.js';
import { normalizeSubjectPoints, withSubjectPoint } from './subjectPoints.js';

function sameJson(left, right) {
  return JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
}

function hasReadyArtifact(config, hasReadyClipArtifact) {
  return hasReadyClipArtifact === true || config?.artifact?.status === 'ready';
}

/**
 * Replace the picked points on a Cutout config.
 *
 * Returns the SAME object when nothing changed so callers can skip a write.
 * When the cutout is enabled and an artifact was already built, the project
 * marker becomes `stale`: the aggregate status then reads as needing a new
 * prepare, and the prepare run resets it.
 */
export function setSubjectPointsOnConfig(config, points, { hasReadyClipArtifact = false } = {}) {
  const base = config && typeof config === 'object' && !Array.isArray(config) ? config : null;
  const next = normalizeSubjectPoints(points);
  if (sameJson(next, normalizeSubjectPoints(base?.subject_points))) return config ?? null;
  // Points are only meaningful for an enabled cutout. A disabled one can
  // still be cleared, but never gains points, so picking cannot silently
  // create a half-configured project marker.
  if (!base) return config ?? null;
  if (base.enabled !== true && next.length > 0) return config;

  const updated = { ...base };
  if (next.length > 0) updated.subject_points = next;
  else delete updated.subject_points;
  if (base.enabled === true && hasReadyArtifact(base, hasReadyClipArtifact)) {
    updated.artifact = { ...(base.artifact || {}), schema_version: 1, id: null, status: 'stale' };
  }
  return updated;
}

/** Append one picked point (deduplicated and capped by withSubjectPoint). */
export function addSubjectPointToConfig(config, point, options) {
  return setSubjectPointsOnConfig(config, withSubjectPoint(config?.subject_points, point), options);
}

/** Drop every picked point. */
export function clearSubjectPointsOnConfig(config, options) {
  return setSubjectPointsOnConfig(config, [], options);
}

/**
 * The project-level config the prepare request is built from. A fresh config
 * (cutout not enabled yet) still keeps points picked beforehand.
 */
export function buildPrepareBaseConfig(backgroundIsolation, requestId) {
  const { engine, model } = resolveCutoutEngineModel(backgroundIsolation);
  const points = normalizeSubjectPoints(backgroundIsolation?.subject_points);
  return {
    ...(backgroundIsolation?.enabled === true
      ? backgroundIsolation
      : {
        schema_version: 1,
        enabled: true,
        mode: 'cutout',
        engine,
        model: defaultCutoutModel(engine),
        quality: 'balanced',
        fallback: 'spotlight',
        artifact: { schema_version: 1, id: null, status: 'missing' },
        ...(points.length > 0 ? { subject_points: points } : {}),
      }),
    engine,
    model: model === 'u2netp' ? 'u2net' : model,
    request_id: requestId,
    artifact: { schema_version: 1, id: null, status: 'missing' },
  };
}
