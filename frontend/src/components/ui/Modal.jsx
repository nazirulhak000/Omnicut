import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { useBackToClose } from '../../hooks/useBackToClose';

// Phone (<640px): bottom sheet anchored to the bottom edge with safe-area
// padding. sm and up: the centered dialog the desktop always had.
// Layer: z-[9999] (top of the overlay scale documented in index.css).
export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-2xl',
  showCloseButton = true
}) {
  const dialogRef = useRef(null);

  // Phone back gesture closes the modal instead of leaving the app.
  useBackToClose(isOpen, onClose);

  // Listen for Escape key and lock background scroll
  useEffect(() => {
    if (!isOpen) return;

    const previouslyFocused = document.activeElement;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    // Lock body and html scroll
    const origBodyOverflow = document.body.style.overflow;
    const origHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = origBodyOverflow || 'unset';
      document.documentElement.style.overflow = origHtmlOverflow || 'unset';
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        try { previouslyFocused.focus({ preventScroll: true }); } catch { /* element gone */ }
      }
    };
  }, [isOpen, onClose]);

  // Initial focus goes to the dialog itself (not the first input) so iOS does
  // not pop the keyboard the moment a sheet opens.
  useEffect(() => {
    if (!isOpen) return;
    const node = dialogRef.current;
    if (node && !node.contains(document.activeElement)) {
      try { node.focus({ preventScroll: true }); } catch { /* ignore */ }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center p-0 sm:p-4 md:p-6 w-screen h-dvh max-h-dvh overflow-hidden overscroll-none animate-fadeIn">
      {/* Click outside to close backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md z-0 transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container - bottom sheet on phones, centered dialog from sm */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        tabIndex={-1}
        className={`relative w-full ${maxWidth} bg-[#080B11]/95 backdrop-blur-2xl border border-white/[0.14] shadow-2xl rounded-t-3xl rounded-b-none sm:rounded-3xl z-10 flex flex-col max-h-[90dvh] overflow-hidden animate-scaleUp mt-auto sm:my-auto pb-[env(safe-area-inset-bottom)] sm:pb-0 outline-none`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - Fixed Top */}
        {(title || showCloseButton) && (
          <div className="flex-shrink-0 flex items-center justify-between gap-3 px-4 sm:px-6 py-2.5 sm:py-4 border-b border-white/[0.08] bg-[#0B0F19]/95 backdrop-blur-xl z-20">
            <div className="min-w-0 flex-1">
              {title && (
                <h3 className="text-base md:text-lg font-bold text-white truncate">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs text-slate-400 mt-0.5 line-clamp-2 leading-tight">{subtitle}</p>
              )}
            </div>

            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className="w-11 h-11 sm:w-9 sm:h-9 pointer-coarse:w-11 pointer-coarse:h-11 rounded-xl bg-white/[0.05] hover:bg-white/[0.12] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center flex-shrink-0 border border-white/[0.06]"
                aria-label="ปิดหน้าต่าง"
              >
                <X className="w-5 h-5 sm:w-4 sm:h-4" />
              </button>
            )}
          </div>
        )}

        {/* Content Body - Independent Scroll */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6 min-w-0 no-scrollbar space-y-4">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}

export default Modal;
