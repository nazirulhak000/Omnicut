import { useEffect, useRef } from 'react';
import { OVERLAY_STATE_KEY } from '../lib/appNav.js';

// Overlays whose owner unmounted/closed but whose history entry has not been
// popped yet. A new overlay opening in the same tick (StrictMode remount, a
// sheet handing off to a modal) reuses that entry instead of stacking a second
// one, so the user never needs two back presses for one visible overlay.
const pendingClose = new Set();
let tokenCounter = 0;

function currentOverlayToken() {
  const state = window.history.state;
  return state && typeof state === 'object' ? state[OVERLAY_STATE_KEY] || null : null;
}

/**
 * useBackToClose(open, onClose)
 *
 * While `open` is true the overlay owns one browser-history entry, so the
 * phone back gesture / Android back button closes the overlay instead of
 * leaving the app. Closing through the UI removes that entry again (no
 * double-back). Nested overlays each own their own entry; back closes the top
 * one only.
 *
 * Options: `{ enabled = true }` -- pass false to opt out (e.g. desktop-only
 * popovers) without breaking the hook order.
 */
export function useBackToClose(open, onClose, { enabled = true } = {}) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open || !enabled || typeof window === 'undefined' || !window.history) return undefined;

    tokenCounter += 1;
    const token = `ov-${Date.now().toString(36)}-${tokenCounter}`;
    const baseState = window.history.state && typeof window.history.state === 'object' ? window.history.state : {};
    const nextState = { ...baseState, [OVERLAY_STATE_KEY]: token };
    const reusable = currentOverlayToken();
    try {
      if (reusable && pendingClose.has(reusable)) {
        pendingClose.delete(reusable);
        window.history.replaceState(nextState, '');
      } else {
        window.history.pushState(nextState, '');
      }
    } catch {
      return undefined;
    }

    let poppedByBrowser = false;
    const onPopState = () => {
      // Still on our entry (e.g. a nested overlay above us was popped).
      if (currentOverlayToken() === token) return;
      poppedByBrowser = true;
      onCloseRef.current?.();
    };
    window.addEventListener('popstate', onPopState);

    return () => {
      window.removeEventListener('popstate', onPopState);
      if (poppedByBrowser) return;
      // Closed by the UI: drop our entry, unless something else already
      // replaced it (tab navigation, another overlay reusing it).
      pendingClose.add(token);
      setTimeout(() => {
        if (!pendingClose.has(token)) return;
        pendingClose.delete(token);
        if (currentOverlayToken() === token) {
          try { window.history.back(); } catch { /* history unavailable */ }
        }
      }, 0);
    };
  }, [open, enabled]);
}

export default useBackToClose;
