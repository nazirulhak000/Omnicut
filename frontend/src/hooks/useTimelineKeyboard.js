import { useEffect } from 'react';
import { wheelZoomFactor } from '../lib/timelineZoom.js';

/**
 * Handles global keyboard and wheel listeners for the Timeline:
 * - Escape key closes active menus/popovers
 * - Click outside closes active menus/popovers
 * - Native non-passive wheel zoom for Ctrl/Cmd + wheel (anchored at the cursor via onZoomAt)
 */
export function useTimelineKeyboard({
  scrollRef,
  onZoom,
  onZoomAt,
  transitionMenuClipId,
  setTransitionMenuClipId,
  contextMenu,
  setContextMenu,
}) {
  // Close context menu & transition popover on outside pointer click or Escape
  useEffect(() => {
    const handleGlobalPointer = (e) => {
      if (
        transitionMenuClipId &&
        !e.target.closest('[data-transition-popover]') &&
        !e.target.closest('[data-transition-trigger]')
      ) {
        setTransitionMenuClipId(null);
      }
      if (contextMenu && !e.target.closest('[data-context-menu]')) {
        setContextMenu(null);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setTransitionMenuClipId(null);
        setContextMenu(null);
      }
    };

    window.addEventListener('pointerdown', handleGlobalPointer);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('pointerdown', handleGlobalPointer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [transitionMenuClipId, contextMenu, setTransitionMenuClipId, setContextMenu]);

  // Ctrl/Cmd+wheel has to be bound natively with { passive: false }: React
  // registers its own root `wheel` listener as passive, so preventDefault()
  // inside an onWheel prop is ignored and the browser page-zooms instead of
  // the timeline.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheelNative = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      // Continuous zoom around the cursor when the timeline supports it;
      // otherwise the old one-preset step.
      if (onZoomAt) {
        const rect = el.getBoundingClientRect();
        onZoomAt(wheelZoomFactor(e.deltaY, e.deltaMode), e.clientX - rect.left);
        return;
      }
      onZoom?.(e.deltaY < 0 ? 1 : -1);
    };
    el.addEventListener('wheel', onWheelNative, { passive: false });
    return () => el.removeEventListener('wheel', onWheelNative);
  }, [scrollRef, onZoom, onZoomAt]);
}
