/**
 * Single place that decides which Cutout engine + model pair the editor sends.
 *
 * Upgraded with CapCut 7.1 Resolution-Independent Stroke Normalization (DilateErode.lua, E5).
 */

export const CUTOUT_ENGINE_MODELS = Object.freeze({
  rembg: Object.freeze(['u2netp', 'u2net', 'isnet-general-use']),
  sam2: Object.freeze(['sam2.1_hiera_tiny', 'sam2.1_hiera_small', 'sam2.1_hiera_base_plus']),
});

export const DEFAULT_CUTOUT_ENGINE = 'sam2';

export const DEFAULT_CUTOUT_MODEL = Object.freeze({
  rembg: 'u2net',
  sam2: 'sam2.1_hiera_tiny',
});

export function defaultCutoutModel(engine) {
  return DEFAULT_CUTOUT_MODEL[engine] || DEFAULT_CUTOUT_MODEL[DEFAULT_CUTOUT_ENGINE];
}

function engineOwningModel(model) {
  return Object.keys(CUTOUT_ENGINE_MODELS).find((engine) => CUTOUT_ENGINE_MODELS[engine].includes(model)) || null;
}

/**
 * @param {{ engine?: unknown, model?: unknown } | null | undefined} config
 * @returns {{ engine: string, model: string }} a pair the worker can run
 */
export function resolveCutoutEngineModel(config) {
  const requestedEngine = typeof config?.engine === 'string' && CUTOUT_ENGINE_MODELS[config.engine]
    ? config.engine
    : null;
  const requestedModel = typeof config?.model === 'string' ? config.model : null;
  const engine = requestedEngine || engineOwningModel(requestedModel) || DEFAULT_CUTOUT_ENGINE;
  const model = requestedModel && CUTOUT_ENGINE_MODELS[engine].includes(requestedModel)
    ? requestedModel
    : defaultCutoutModel(engine);
  return { engine, model };
}

/**
 * CapCut 7.1 Resolution-Independent Stroke / Feather Normalization (DilateErode.lua, E5)
 * Formula: scaleNorm = min(width, height) / 720.0
 * Effective Stroke = baseStroke * scaleNorm
 */
export const STROKE_NORM_BASE = 720.0;

export function calculateNormalizedStroke(baseStroke = 14, width = 1080, height = 1920) {
  const scaleNorm = Math.min(width, height) / STROKE_NORM_BASE;
  return Math.round(baseStroke * scaleNorm);
}
