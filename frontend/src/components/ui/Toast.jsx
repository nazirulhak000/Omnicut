import React, { useEffect } from 'react';
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

  return (
    <div
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
      aria-atomic="true"
      className="fixed inset-x-3 bottom-[calc(var(--nav-h)+0.75rem)] md:inset-x-auto md:bottom-6 md:right-6 z-[60] flex justify-center md:block animate-fadeIn select-none pointer-events-none"
    >
      <div
        className={`flex items-center gap-3 py-3 px-4 rounded-2xl border backdrop-blur-md shadow-xl text-sm font-semibold w-full md:w-auto max-w-md min-w-0 pointer-events-auto ${config.style}`}
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
}

export default Toast;
