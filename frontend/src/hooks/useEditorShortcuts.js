import { useEffect, useRef } from 'react';
import { classifyShortcut, isEditableTarget, shouldIgnoreShortcutTarget } from '../lib/editorShortcutKeys.js';

/**
 * Hook to manage timeline keyboard verbs (Space, B, Z, Y, J-K-L, Arrows, Delete).
 * Handlers are stashed in a ref so the window listener is registered only once.
 */
export function useEditorShortcuts({
  undo,
  redo,
  splitAtPlayhead,
  deleteSelected,
  togglePlayer,
  seekPlayer,
  playhead,
  totalDuration,
  audioDuration,
  setZoomIndex,
  zoomLevelsLength = 5,
  selectedSeg,
  patchClip,
  zen,
  setZen,
  onToggleSnap,
  onCycleCutoutMode,
} = {}) {
  const keyHandlerRef = useRef(null);

  // Stashed rather than subscribed in this effect: no dependency array ensures
  // the handler is never stale, while the listener is registered only once below.
  useEffect(() => {
    keyHandlerRef.current = (e) => {
      // A text field keeps every key. A slider/checkbox/button input keeps
      // everything except undo/redo, decided below once the key is classified.
      if (isEditableTarget(e.target)) return;

      // Do not trigger background editor shortcuts if a modal dialog is open
      if (typeof document !== 'undefined' && document.querySelector('[role="dialog"], [aria-modal="true"]')) {
        return;
      }

      // Modified combos not explicitly claimed (Ctrl+S, Ctrl++, ...) come back
      // as 'none' with preventDefault false, so the browser/app keeps them.
      const { action, preventDefault, delta } = classifyShortcut(e, { zen });
      if (action === 'none') return;
      if (shouldIgnoreShortcutTarget(e.target, action)) return;
      if (preventDefault) e.preventDefault();

      const jump = (d) => {
        const maxTime = Math.max(totalDuration || 0, audioDuration || 0);
        const next = Math.max(0, Math.min(maxTime, (playhead || 0) + d));
        seekPlayer?.(next);
      };

      switch (action) {
        case 'undo': undo?.(); break;
        case 'redo': redo?.(); break;
        case 'split': splitAtPlayhead?.(); break;
        case 'exitZen': setZen?.(false); break;
        case 'togglePlay': togglePlayer?.(); break;
        case 'jump': jump(delta); break;
        case 'delete': deleteSelected?.(); break;
        case 'zoomIn':
          setZoomIndex?.((i) => Math.min(zoomLevelsLength - 1, i + 1));
          break;
        case 'zoomOut':
          setZoomIndex?.((i) => Math.max(0, i - 1));
          break;
        case 'toggleFade':
          if (selectedSeg && selectedSeg.index > 0) {
            e.preventDefault();
            patchClip?.(selectedSeg.clip.id, {
              transition_in: selectedSeg.clip.transition_in && selectedSeg.clip.transition_in !== 'cut' ? 'cut' : 'fade',
            });
          }
          break;
        case 'toggleSnap': onToggleSnap?.(); break;
        case 'cycleCutout': onCycleCutoutMode?.(); break;
        default: break;
      }
    };
  });

  useEffect(() => {
    const listener = (e) => keyHandlerRef.current?.(e);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);
}
