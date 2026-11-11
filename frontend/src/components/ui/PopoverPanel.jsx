import React, { useEffect, useLayoutEffect, useRef } from 'react';

const GAP = 6;
const EDGE = 8;

const supportsPopover = () =>
  typeof HTMLElement !== 'undefined' && typeof HTMLElement.prototype.showPopover === 'function';

/**
 * PopoverPanel -- a dropdown panel tethered to its trigger.
 *
 * Mount it only while open: `{open && <PopoverPanel anchorRef={btn} onClose=...>}`.
 *
 * With the Popover API the panel is `popover="auto"`: it renders in the top
 * layer (never clipped by an overflow:hidden header, no z-index), and the
 * browser closes it on an outside press or Escape. It is placed with fixed
 * coordinates from the anchor's rect, flipped above the anchor when it would
 * run off the bottom and clamped to the viewport edges.
 *
 * Without the Popover API it falls back to the previous behaviour: an
 * absolutely positioned panel under the anchor (the anchor's parent must be
 * `relative`) closed by a document-level outside press.
 *
 * align: 'end' (right edges line up) | 'start' (left edges line up).
 * matchAnchorWidth: panel is at least as wide as the anchor.
 */
export function PopoverPanel({
  anchorRef,
  onClose,
  align = 'end',
  matchAnchorWidth = false,
  className = '',
  children,
  ...rest
}) {
  const panelRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  // A press on the trigger light-dismisses the popover AND fires the trigger's
  // own click (which toggles the owner's state). Only one of the two may
  // report the close, or the panel would close and immediately reopen.
  const pressOnAnchorRef = useRef(false);
  const native = supportsPopover();

  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!panel || !native) return undefined;

    const place = () => {
      const anchor = anchorRef?.current;
      if (!anchor) return;
      const rect = anchor.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      if (matchAnchorWidth) {
        panel.style.minWidth = '';
        const own = parseFloat(getComputedStyle(panel).minWidth) || 0;
        panel.style.minWidth = `${Math.round(Math.max(rect.width, own))}px`;
      }
      const width = panel.offsetWidth;
      const height = panel.offsetHeight;
      let left = align === 'start' ? rect.left : rect.right - width;
      left = Math.max(EDGE, Math.min(left, vw - width - EDGE));
      let top = rect.bottom + GAP;
      if (top + height > vh - EDGE && rect.top - GAP - height >= EDGE) {
        top = rect.top - GAP - height;
      }
      panel.style.left = `${Math.round(left)}px`;
      panel.style.top = `${Math.round(top)}px`;
    };

    try { panel.showPopover(); } catch { /* already open */ }
    place();
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('resize', place);
      try { panel.hidePopover(); } catch { /* already hidden or detached */ }
    };
  }, [native, anchorRef, align, matchAnchorWidth]);

  useEffect(() => {
    // The panel is a DOM descendant of some anchors (a wrapper passed for its
    // width), so a press inside the panel is not a press on the trigger.
    const isOnAnchor = (target) =>
      Boolean(anchorRef?.current?.contains(target)) && !panelRef.current?.contains(target);

    const onPointerDown = (event) => {
      pressOnAnchorRef.current = isOnAnchor(event.target);
      // Fallback only: the browser is not doing light dismiss for us.
      if (!native && !pressOnAnchorRef.current && !panelRef.current?.contains(event.target)) {
        onCloseRef.current?.();
      }
    };
    const onKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      // The editor also binds Escape (exit zen mode, clear selection): this
      // press belongs to the panel only.
      event.stopPropagation();
      onCloseRef.current?.();
      anchorRef?.current?.focus?.();
    };
    document.addEventListener('pointerdown', onPointerDown, true);
    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown, true);
      document.removeEventListener('keydown', onKeyDown, true);
    };
  }, [native, anchorRef]);

  const handleToggle = (event) => {
    if (event.target !== panelRef.current || event.newState !== 'closed') return;
    if (pressOnAnchorRef.current) {
      // The trigger's click handler owns this close.
      pressOnAnchorRef.current = false;
      return;
    }
    onCloseRef.current?.();
  };

  if (native) {
    return (
      <div
        ref={panelRef}
        popover="auto"
        onToggle={handleToggle}
        className={`popover-menu ${className}`}
        {...rest}
      >
        {children}
      </div>
    );
  }

  const fallbackPosition = align === 'start' ? 'left-0' : 'right-0';
  return (
    <div
      ref={panelRef}
      className={`absolute ${fallbackPosition} top-full z-50 mt-1.5 ${matchAnchorWidth ? 'min-w-full' : ''} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export default PopoverPanel;
