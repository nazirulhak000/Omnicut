import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export function Toast({
  message,
  type = 'success', // 'success' | 'error' | 'warning' | 'info'
  onClose,
  duration = 3000
}) {
  const managedDuration = Number.isFinite(Number(duration)) ? Number(duration) : 3000;

  useEffect(() => {
    if (!message || managedDuration <= 0) return undefined;
    const timer = setTimeout(() => {
      onClose?.();
    }, managedDuration);
    return () => clearTimeout(timer);
  }, [message, managedDuration, onClose]);

  // popover="manual" puts the toast in the top layer, above any modal <dialog>
  // that is already open (a fixed z-index cannot beat the top layer). Engines
  // without the Popover API ignore the attribute and keep the fixed position.
  //
  // A modal dialog makes everything outside it inert -- not clickable, not
  // reachable by assistive tech. So while one is open the toast is portalled
  // into the topmost modal dialog: it stays on top AND its close button works.
  const layerRef = useRef(null);
  const [modalHost, setModalHost] = useState(null);
  useLayoutEffect(() => {
    if (!message || typeof document === 'undefined') { setModalHost(null); return; }
    const open = [...document.querySelectorAll('dialog[open]')].filter((d) => {
      try { return d.matches(':modal'); } catch { return false; }
    });
    setModalHost(open.length ? open[open.length - 1] : null);
  }, [message]);

  useLayoutEffect(() => {
    const el = layerRef.current;
    if (!el || !message || typeof el.showPopover !== 'function') return undefined;
    try { el.showPopover(); } catch { /* already shown */ }
    return () => {
      try { el.hidePopover(); } catch { /* already hidden or detached */ }
    };
  }, [message, modalHost]);

  // Announce through ariaNotify() where it exists; the live-region role below
  // is the fallback for engines without it (never both, or it is read twice).
  const canNotify = typeof document !== 'undefined' && typeof document.ariaNotify === 'function';
  useEffect(() => {
    if (!message || !canNotify) return;
    try {
      document.ariaNotify(String(message), { priority: type === 'error' ? 'high' : 'normal' });
    } catch { /* announcement is best-effort */ }
  }, [message, type, canNotify]);

  if (!message) return null;

  const typeConfig = {
    success: {
      icon: CheckCircle2,
      style: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 shadow-emerald-500/10',
      iconColor: 'text-emerald-400'
    },
    error: {
      icon: AlertCircle,
      style: 'bg-rose-500/15 border-rose-500/30 text-rose-300 shadow-rose-500/10',
      iconColor: 'text-rose-400'
    },
    warning: {
      icon: AlertTriangle,
      style: 'bg-amber-500/15 border-amber-500/30 text-amber-300 shadow-amber-500/10',
      iconColor: 'text-amber-400'
    },
    info: {
      icon: Info,
      style: 'bg-[#25F4EE]/15 border-[#25F4EE]/30 text-cyan-200 shadow-[#25F4EE]/10',
      iconColor: 'text-[#25F4EE]'
    }
  };

  const config = typeConfig[type] || typeConfig.info;
  const Icon = config.icon;

  const node = (
    <div
      ref={layerRef}
      popover="manual"
      role={canNotify ? undefined : (type === 'error' ? 'alert' : 'status')}
      aria-live={canNotify ? undefined : (type === 'error' ? 'assertive' : 'polite')}
      aria-atomic="true"
      className="toast-layer fixed inset-x-3 top-[calc(env(safe-area-inset-top,0px)+8px)] md:top-auto md:inset-x-auto md:bottom-6 md:right-6 z-[9999] flex justify-center md:block animate-slideDown select-none pointer-events-none"
    >
      <div
        className={`flex items-center gap-2.5 py-2.5 px-4 rounded-full border backdrop-blur-2xl shadow-2xl text-xs sm:text-sm font-semibold w-full md:w-auto max-w-md min-w-0 pointer-events-auto ${config.style}`}
      >
        <Icon className={`w-4 h-4 flex-shrink-0 ${config.iconColor}`} />
        <span className="flex-1 min-w-0 break-words">{message}</span>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="ปิดการแจ้งเตือน"
            className="p-1 max-md:min-h-11 max-md:min-w-11 pointer-coarse:min-h-11 pointer-coarse:min-w-11 flex items-center justify-center flex-shrink-0 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
  return modalHost ? createPortal(node, modalHost) : node;
}

export default Toast;
