/**
 * Pure decisions for the phone editor's preview / bottom-panel split.
 *
 * Kept free of React and the DOM so EditorShell, usePanelLayout and the tests
 * all read ONE rule. Before this, the shell decided "is the preview enlarged?"
 * with `previewH >= innerHeight * 0.55` while the hook toggled on
 * `previewH >= maxH * 0.75` -- two answers for one question, so "shrink
 * preview" could grow it instead and drop immersive at the same time.
 *
 * Full preview is an explicit mode, not a pixel height: in it the bottom panel
 * collapses to zero and the preview takes the whole column; in normal mode the
 * drag clamp keeps room for the tab row and the timeline so the tracks are
 * never squeezed.
 */

export const MOBILE_PREVIEW_MIN_H = 130;
export const MOBILE_PREVIEW_DEFAULT = 0.32;
// The timeline / assets / inspector tab row: 44px touch targets + `p-1` + 1px border.
export const MOBILE_TAB_ROW_H = 53;
// The drag handle between preview and tab row (`h-3.5`).
export const MOBILE_SEPARATOR_H = 14;
// Keyboard step on the drag handle (Shift = bigger step).
export const MOBILE_PREVIEW_KEY_STEP = 24;

/**
 * The single answer to "is the phone preview showing enlarged?". Immersive
 * counts: the navbars are gone, so the control offers the way back.
 *
 * @param {{ full?: boolean, immersive?: boolean }} mode
 */
export function isPreviewEnlarged({ full = false, immersive = false } = {}) {
  return Boolean(full || immersive);
}

/**
 * What one press of the full-preview toggle does. The flag the button shows and
 * the direction it moves always agree: enlarged -> back to normal with navbars;
 * normal -> full preview with navbars hidden.
 *
 * @param {{ full?: boolean, immersive?: boolean }} mode
 * @returns {{ full: boolean, immersive: boolean }}
 */
export function nextPreviewMode(mode = {}) {
  const enlarged = isPreviewEnlarged(mode);
  return { full: !enlarged, immersive: !enlarged };
}

/**
 * Tallest preview allowed in normal mode: the column minus the drag handle,
 * the tab row and the bottom panel's reserved height (the timeline's real
 * height on the timeline tab).
 *
 * @param {{ boxH?: number, innerHeight?: number, reserve?: number }} opts
 */
export function mobilePreviewMaxH({ boxH, innerHeight = 0, reserve = 0 } = {}) {
  const column = Number.isFinite(boxH) && boxH > 0 ? boxH : Math.round((innerHeight || 0) * 0.9);
  const room = column - MOBILE_SEPARATOR_H - MOBILE_TAB_ROW_H - Math.max(0, Number(reserve) || 0);
  return Math.max(MOBILE_PREVIEW_MIN_H, Math.round(room));
}

/** Clamp a requested normal-mode preview height into [min, max]. */
export function clampMobilePreviewH(px, opts = {}) {
  const max = mobilePreviewMaxH(opts);
  const want = Number.isFinite(px) ? Math.round(px) : max;
  return Math.min(max, Math.max(MOBILE_PREVIEW_MIN_H, want));
}

/**
 * Inline styles for the preview and the bottom panel.
 *
 * Full: the panel is `flex: 0 0 0` (kept mounted so the timeline keeps its
 * scroll and width) and the preview fills the column.
 * Normal: the preview asks for `previewH`; when the column is shorter than
 * preview + panel, the large shrink factor makes the preview give up its
 * height first (down to its minimum) instead of both shrinking in proportion
 * and crushing the tracks.
 *
 * @param {{ full?: boolean, previewH: number, panelH?: number | null }} opts
 *   panelH: fixed height of the bottom panel (timeline tab), or null for the
 *   scrollable assets / inspector panels that take the remaining space.
 */
export function mobilePanelStyles({ full = false, previewH, panelH = null } = {}) {
  if (full) {
    return {
      preview: { flex: '1 1 0%', minHeight: MOBILE_PREVIEW_MIN_H },
      panel: { flex: '0 0 0px', height: 0, minHeight: 0, maxHeight: 0, overflow: 'hidden', visibility: 'hidden' },
    };
  }
  return {
    preview: { flex: '1 1000 auto', height: previewH, minHeight: MOBILE_PREVIEW_MIN_H },
    panel: Number.isFinite(panelH)
      ? { flex: '0 1 auto', height: panelH, maxHeight: panelH }
      : { flex: '1 1 0%', minHeight: 0 },
  };
}
