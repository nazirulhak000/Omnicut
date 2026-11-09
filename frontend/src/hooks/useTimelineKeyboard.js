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
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        // Continuous zoom around the cursor when the timeline supports it;
        // otherwise the old one-preset step.
        if (onZoomAt) {
          const rect = el.getBoundingClientRect();
          onZoomAt(wheelZoomFactor(e.deltaY, e.deltaMode), e.clientX - rect.left);
          return;
        }
        onZoom?.(e.deltaY < 0 ? 1 : -1);
        return;
      }

      // Horizontal scroll: Shift + vertical wheel, or native horizontal gesture
      if (e.shiftKey && e.deltaY !== 0) {
        e.preventDefault();
        const delta = e.deltaMode === 1 ? e.deltaY * 32 : e.deltaY;
        el.scrollLeft += delta;
        return;
      }

      // Normal vertical wheel (e.deltaY !== 0, without Shift/Ctrl/Meta):
      // If the timeline has vertical overflow (more tracks than fit in viewport),
      // allow smooth natural vertical scrolling up and down through all tracks.
      if (e.deltaY !== 0 && e.deltaX === 0) {
        const canScrollVertically = el.scrollHeight > el.clientHeight;
        if (canScrollVertically) {
          // Allow natural vertical scroll through all tracks
          return;
        }
        // If all tracks fit vertically, allow horizontal timeline pan
        e.preventDefault();
        const delta = e.deltaMode === 1 ? e.deltaY * 32 : e.deltaY;
        el.scrollLeft += delta;
      }
    };
    el.addEventListener('wheel', onWheelNative, { passive: false });
    return () => el.removeEventListener('wheel', onWheelNative);
  }, [scrollRef, onZoom, onZoomAt]);
}
