import React, { useState } from 'react';
import { Check, X, Scissors, Volume2, Type, AlertCircle } from 'lucide-react';

export default function ActionApprovalCard({
  action,
  onApply,
  onDiscard,
}) {
  const [status, setStatus] = useState('pending'); // 'pending' | 'applying' | 'applied' | 'discarded' | 'error'
  const [errorMessage, setErrorMessage] = useState('');

  if (!action) return null;

  const { action_type, title, description, payload } = action;

  const handleApplyClick = async () => {
    setStatus('applying');
    setErrorMessage('');
    try {
      if (typeof onApply === 'function') {
        await onApply(action);
      }
      setStatus('applied');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err?.message || 'ไม่สามารถใช้งานคำสั่งนี้ได้');
    }
  };

  const handleDiscardClick = () => {
    setStatus('discarded');
    if (typeof onDiscard === 'function') {
      onDiscard(action);
    }
  };

  const getActionIcon = () => {
    switch (action_type) {
      case 'split_clip':
        return <Scissors className="h-4 w-4 text-emerald-400" />;
      case 'audio_mix':
        return <Volume2 className="h-4 w-4 text-cyan-400" />;
      case 'subtitle_style':
        return <Type className="h-4 w-4 text-amber-400" />;
      default:
        return <Scissors className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <div className="mt-2.5 mb-1.5 rounded-xl border border-white/10 bg-slate-900/90 p-3 shadow-lg backdrop-blur-md transition-all">
      {/* ── Header Badge & Title ── */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          {getActionIcon()}
          <span className="text-xs font-bold text-white tracking-wide">{title}</span>
        </div>
        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 border border-white/[0.05]">
          {action_type}
        </span>
      </div>

      {/* ── Description ── */}
      <p className="text-xs text-slate-300 leading-relaxed mb-3">
        {description}
      </p>

      {/* ── Status or Action Buttons ── */}
      {status === 'pending' && (
        <div className="flex items-center justify-end gap-2 pt-1 border-t border-white/[0.06]">
          <button
            type="button"
            onClick={handleDiscardClick}
            className="flex h-7 items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 text-xs font-bold text-slate-300 transition-colors hover:bg-white/[0.08] hover:text-white cursor-pointer"
          >
            <X className="h-3 w-3" />
            <span>ยกเลิก</span>
          </button>
          <button
            type="button"
            onClick={handleApplyClick}
            className="flex h-7 items-center gap-1 rounded-lg border border-emerald-500/40 bg-emerald-500/20 px-3 text-xs font-bold text-emerald-300 transition-all hover:bg-emerald-500/30 hover:shadow-[0_0_8px_rgba(16,185,129,0.3)] cursor-pointer"
          >
            <Check className="h-3 w-3" />
            <span>อนุมัติคำสั่ง</span>
          </button>
        </div>
      )}

      {status === 'applying' && (
        <div className="flex items-center justify-end gap-1.5 text-xs font-bold text-amber-400 pt-1 border-t border-white/[0.06]">
          <div className="h-3 w-3 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />
          <span>กำลังปรับใช้...</span>
        </div>
      )}

      {status === 'applied' && (
        <div className="flex items-center justify-end gap-1 text-xs font-bold text-emerald-400 pt-1 border-t border-white/[0.06]">
          <Check className="h-3.5 w-3.5" />
          <span>อนุมัติและปรับใช้สำเร็จ</span>
        </div>
      )}

      {status === 'discarded' && (
        <div className="flex items-center justify-end text-xs font-bold text-slate-500 pt-1 border-t border-white/[0.06]">
          <span>ยกเลิกคำสั่งแล้ว</span>
        </div>
      )}

      {status === 'error' && (
        <div className="flex items-center gap-1.5 text-xs font-bold text-rose-400 pt-1 border-t border-white/[0.06]">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
