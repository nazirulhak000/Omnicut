/**
 * Render Readiness and Save State Machine for OmniCut Pro Studio
 *
 * Enforces a strict 5-state truth table:
 * 1) loading: coverChecking || preflightLoading -> 'loading'
 * 2) unknown / unchecked: (coverStatus === null || coverStatus === undefined) || !preflightReport -> 'unknown'
 * 3) blocked / error: errors.length > 0 -> 'error'
 * 4) warnings: warnings.length > 0 && !hasErrors -> 'warning'
 * 5) ready: cover checked (true or false) && errors.length === 0 && warnings.length === 0 -> 'ready'
 *
 * A missing cover (coverStatus === false) is not a blocker: the renderer
 * creates a default cover after the clip is exported (scripts/auto_cover.py).
 * An unchecked cover (null / undefined) still is -- it means the project's
 * product angle has not been found yet.
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

  // 3) blocked / error: structural errors exist
  if (errors.length > 0) {
    return READINESS_STATES.ERROR;
  }

  // 2) unknown / unchecked: cover is not checked or preflight has not run
  if (isRenderBlockedByCover(coverStatus) || !preflightReport) {
    return READINESS_STATES.UNKNOWN;
  }

  // 4) warnings: recommendations present with no blockers
  if (warnings.length > 0) {
    return READINESS_STATES.WARNING;
  }

  // 5) ready: cover checked (saved, or to be created after render), 0 errors, 0 warnings
  return READINESS_STATES.READY;
}

/** Only an unchecked cover keeps Render disabled; a missing one does not. */
export function isRenderBlockedByCover(coverStatus) {
  return coverStatus === null || coverStatus === undefined;
}

/** Tooltip text for the Render button about the cover; '' when a cover is saved. */
export function getRenderCoverNote(coverStatus) {
  if (isRenderBlockedByCover(coverStatus)) return 'ยังไม่พบข้อมูลสินค้าของโปรเจกต์นี้ จึงยังเรนเดอร์ไม่ได้';
  if (coverStatus === false) return 'ยังไม่มีปก ระบบจะสร้างปกอัตโนมัติหลังเรนเดอร์';
  return '';
}

export function normalizeSaveStatus(saveStatus) {
  if (saveStatus === 'saving') return 'saving';
  if (saveStatus === 'error') return 'error';
  if (saveStatus === 'dirty' || saveStatus === 'unsaved') return 'unsaved';
  return 'saved';
}
