import { useEffect, useRef } from 'react';

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
} = {}) {
  const keyHandlerRef = useRef(null);

  // Stashed rather than subscribed in this effect: no dependency array ensures
  // the handler is never stale, while the listener is registered only once below.
  useEffect(() => {
    keyHandlerRef.current = (e) => {
      const el = e.target;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)) {
        return;
      }

      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo?.(); else undo?.();
        return;
      }
      if (mod && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo?.();
        return;
      }
      if (mod && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        splitAtPlayhead?.();
        return;
      }
      if (e.key === 'Escape' && zen) {
        e.preventDefault();
        setZen?.(false);
        return;
      }

      const jump = (delta) => {
        const maxTime = Math.max(totalDuration || 0, audioDuration || 0);
        const next = Math.max(0, Math.min(maxTime, (playhead || 0) + delta));
        seekPlayer?.(next);
      };

      switch (e.key) {
        case ' ':
          e.preventDefault();
          togglePlayer?.();
          break;
        case 's': case 'S':
          e.preventDefault();
          splitAtPlayhead?.();
          break;
        case 'j': case 'J':
          e.preventDefault();
          jump(-1.0);
          break;
        case 'k': case 'K':
          e.preventDefault();
          togglePlayer?.();
          break;
        case 'l': case 'L':
          e.preventDefault();
          jump(1.0);
          break;
        case 'Delete': case 'Backspace':
          e.preventDefault();
          deleteSelected?.();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          jump(-(e.shiftKey ? 1 : 1 / 30));
          break;
        case 'ArrowRight':
          e.preventDefault();
          jump(e.shiftKey ? 1 : 1 / 30);
          break;
        case '+': case '=':
          e.preventDefault();
          setZoomIndex?.((i) => Math.min(zoomLevelsLength - 1, i + 1));
          break;
        case '-': case '_':
          e.preventDefault();
          setZoomIndex?.((i) => Math.max(0, i - 1));
          break;
        case 'f': case 'F':
          if (selectedSeg && selectedSeg.index > 0) {
            e.preventDefault();
            patchClip?.(selectedSeg.clip.id, {
              transition_in: selectedSeg.clip.transition_in && selectedSeg.clip.transition_in !== 'cut' ? 'cut' : 'fade',
            });
          }
          break;
        default:
          break;
      }
    };
  });

  useEffect(() => {
    const listener = (e) => keyHandlerRef.current?.(e);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);
}
