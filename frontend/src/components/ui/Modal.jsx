import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-2xl',
  showCloseButton = true
}) {
  // Listen for Escape key and lock background scroll
  useEffect(() => {
    if (!isOpen) return;

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
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-4 md:p-6 w-screen h-[100dvh] max-h-[100dvh] overflow-hidden overscroll-none animate-fadeIn">
      {/* Click outside to close backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md z-0 transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container - Fixed Center & Safe Max Height */}
      <div
        role="dialog"
        aria-modal="true"
        className={`relative w-full ${maxWidth} bg-[#080B11]/95 backdrop-blur-2xl border border-white/[0.14] shadow-2xl rounded-2xl sm:rounded-3xl z-10 flex flex-col max-h-[85dvh] sm:max-h-[90dvh] overflow-hidden animate-scaleUp my-auto`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - Fixed Top */}
        {(title || showCloseButton) && (
          <div className="flex-shrink-0 flex items-center justify-between gap-3 px-4 sm:px-6 py-3.5 sm:py-4 border-b border-white/[0.08] bg-[#0B0F19]/95 backdrop-blur-xl z-20">
            <div className="min-w-0 flex-1">
              {title && (
                <h3 className="text-sm sm:text-base md:text-lg font-bold text-white truncate">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs text-slate-400 mt-0.5 line-clamp-2 leading-tight">{subtitle}</p>
              )}
            </div>

            {showCloseButton && (
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-xl bg-white/[0.05] hover:bg-white/[0.12] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center flex-shrink-0 border border-white/[0.06]"
                aria-label="ปิดหน้าต่าง"
              >
                <X className="w-4 h-4" />
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
