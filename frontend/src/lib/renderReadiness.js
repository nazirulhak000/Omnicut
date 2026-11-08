/**
 * Render Readiness and Save State Machine for OmniCut Pro Studio
 *
 * Enforces a strict 5-state truth table:
 * 1) loading: coverChecking || preflightLoading -> 'loading'
 * 2) unknown / unchecked: (coverStatus === null || coverStatus === undefined) && !preflightReport -> 'unknown'
 * 3) blocked / error: errors.length > 0 || coverStatus === false -> 'error'
 * 4) warnings: warnings.length > 0 && !hasErrors -> 'warning'
 * 5) ready: coverStatus === true && errors.length === 0 && warnings.length === 0 -> 'ready'
 *
 * Guarantees zero false-ready states when checking or when status is unchecked.
 */

export const READINESS_STATES = Object.freeze({
  LOADING: 'loading',
  UNKNOWN: 'unknown',
  ERROR: 'error',
  WARNING: 'warning',
  READY: 'ready',
});

export function getRenderReadinessState({
  coverStatus = null,
  coverChecking = false,
  preflightLoading = false,
  preflightReport = null,
} = {}) {
  // 1) loading: active inspection in progress
  if (coverChecking || preflightLoading) {
    return READINESS_STATES.LOADING;
  }

  const errors = preflightReport?.errors || [];
  const warnings = preflightReport?.warnings || [];

  // 3) blocked / error: structural errors exist or cover is explicitly missing
  const isCoverMissing = coverStatus === false;
  if (errors.length > 0 || isCoverMissing) {
    return READINESS_STATES.ERROR;
  }

  // 2) unknown / unchecked: cover is not confirmed or preflight has not run
  const isCoverUnchecked = coverStatus === null || coverStatus === undefined;
  if (isCoverUnchecked || !preflightReport) {
    return READINESS_STATES.UNKNOWN;
  }

  // 4) warnings: recommendations present with no blockers
  if (warnings.length > 0) {
    return READINESS_STATES.WARNING;
  }

  // 5) ready: cover verified (true) and 0 errors, 0 warnings
  if (coverStatus === true && errors.length === 0 && warnings.length === 0) {
    return READINESS_STATES.READY;
  }

  return READINESS_STATES.UNKNOWN;
}

export function normalizeSaveStatus(saveStatus) {
  if (saveStatus === 'saving') return 'saving';
  if (saveStatus === 'error') return 'error';
  if (saveStatus === 'dirty' || saveStatus === 'unsaved') return 'unsaved';
  return 'saved';
}
