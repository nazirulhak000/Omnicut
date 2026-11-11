import React, { useLayoutEffect, useRef, useState } from 'react';

// The browser returns focus to the invoker when a modal dialog closes, but
// WebKit loses it in two cases: Safari does not focus a <button> on click or
// tap (so there is no invoker to return to), and focus is dropped to <body>
// when the dialog node is removed right after close(). Remember the invoker
// and put focus back only when it ended up on <body>; whenever the native
// return worked, this does nothing.
const PRESSABLE = 'button, a[href], summary, [role="button"], [role="menuitem"], [role="tab"], [tabindex]';
let lastPressed = null;
if (typeof document !== 'undefined') {
  document.addEventListener('pointerdown', (event) => {
    lastPressed = event.target instanceof Element ? event.target.closest(PRESSABLE) : null;
  }, true);
}

/**
 * ModalLayer -- the one place the app opens a blocking overlay.
 *
 * Renders a native <dialog> opened with showModal(), so the browser supplies
 * the top layer (no z-index races), an inert page behind it, focus
 * containment, Escape handling and focus return to the invoker. The dialog
 * itself is stretched over the viewport and stays visually transparent: the
 * caller's className / children draw the scrim and the panel exactly as the
 * old `<div className="fixed inset-0 ...">` wrappers did.
 *
 * Children mount only after the dialog is open. A closed <dialog> is
 * display:none, and focus() / autoFocus on a hidden element is a no-op, so
 * mounting them earlier would silently drop every initial-focus request.
 *
 * `onClose` is called for Escape (and platform close requests). Omit it for
 * an overlay the user must not dismiss; Escape is then swallowed.
 */
export function ModalLayer({ onClose, className = '', children, ...rest }) {
  const ref = useRef(null);
  const [ready, setReady] = useState(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const unmountingRef = useRef(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    unmountingRef.current = false;
    const active = document.activeElement;
    const invoker = active && active !== document.body ? active : lastPressed;
    if (!el.open) {
      try {
        el.showModal();
      } catch {
        // No modal-dialog support (old engines, test DOMs): still show it.
        el.setAttribute('open', '');
      }
    }
    setReady(true);
    return () => {
      unmountingRef.current = true;
      try { if (el.open) el.close(); } catch { /* already detached */ }
      const restoreFocus = () => {
        const now = document.activeElement;
        if (!invoker || !invoker.isConnected) return;
        if (now && now !== document.body && now.isConnected) return;
        try { invoker.focus({ preventScroll: true }); } catch { /* not focusable any more */ }
      };
      restoreFocus();
      // Again once React has removed the dialog node (WebKit drops focus then).
      setTimeout(restoreFocus, 0);
    };
  }, []);

  const handleCancel = (event) => {
    if (event.target !== ref.current) return;
    // React owns the open state: keep the dialog open and let the owner decide.
    event.preventDefault();
    onCloseRef.current?.();
  };

  // A second Escape without user activation closes the dialog natively even
  // when `cancel` was prevented. Tell the owner, and if it chose to stay open
  // (unsaved-changes guard) put the dialog back in the top layer.
  const handleNativeClose = (event) => {
    const el = ref.current;
    if (event.target !== el || unmountingRef.current) return;
    onCloseRef.current?.();
    setTimeout(() => {
      if (unmountingRef.current || !el.isConnected || el.open) return;
      try { el.showModal(); } catch { el.setAttribute('open', ''); }
    }, 0);
  };

  return (
    <dialog
      ref={ref}
      className={`modal-layer ${className}`}
      onCancel={handleCancel}
      onClose={handleNativeClose}
      {...rest}
    >
      {ready ? children : null}
    </dialog>
  );
}

export default ModalLayer;
