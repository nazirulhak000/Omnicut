import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export function Toast({
  message,
  type = 'success', // 'success' | 'error' | 'warning' | 'info'
  onClose,
  duration = 3000
}) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      onClose?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

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
    <div className="fixed bottom-6 right-6 z-50 animate-fadeIn select-none pointer-events-auto">
      <div
        className={`flex items-center gap-3 py-3 px-4 rounded-2xl border backdrop-blur-md shadow-xl text-xs sm:text-sm font-semibold max-w-md ${config.style}`}
      >
        <Icon className={`w-4 h-4 flex-shrink-0 ${config.iconColor}`} />
        <span className="flex-1">{message}</span>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

export default Toast;
