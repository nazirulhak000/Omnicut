import React, { useLayoutEffect, useRef, useState } from 'react';

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
