/**
 * Single place that decides which Cutout engine + model pair the editor sends.
 *
 * Older projects may carry a `model` without an `engine` (written before SAM 2
 * existed, when rembg was the only engine).  Resolving the two fields
 * independently turned `{ model: 'u2netp' }` into `sam2 + u2net`, which the
 * SAM 2 worker cannot run.  The pair is resolved together here so the model
 * always belongs to the engine.
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
