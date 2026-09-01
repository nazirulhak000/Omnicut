import React, { useEffect } from 'react';
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
  // Listen for Escape key to close modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    // Lock body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
      {/* Click outside to close backdrop */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Modal Container */}
      <div
        role="dialog"
        aria-modal="true"
        className={`relative w-full ${maxWidth} glass-panel border border-white/[0.12] shadow-2xl rounded-2xl sm:rounded-3xl p-4 sm:p-6 md:p-7 z-10 space-y-4 sm:space-y-5 max-h-[90dvh] overflow-y-auto no-scrollbar`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-start justify-between gap-3 border-b border-white/[0.08] pb-3 sm:pb-4">
            <div className="min-w-0 flex-1">
              {title && (
                <h3 className="text-sm sm:text-base md:text-lg font-bold font-kanit text-white truncate">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{subtitle}</p>
              )}
            </div>

            {showCloseButton && (
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center flex-shrink-0"
                aria-label="ปิดหน้าต่าง"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        {/* Content Body */}
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
