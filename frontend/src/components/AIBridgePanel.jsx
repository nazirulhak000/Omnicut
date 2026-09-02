import React, { useState } from 'react';
import { Copy, Check, ClipboardPaste, X, AlertTriangle, Sparkles } from 'lucide-react';
import { aiParse } from '../api';

/**
 * Shown when the backend answers a task with mode: 'manual' — no API key, or
 * the quota ran out. The user copies the prompt into their own chat and pastes
 * the answer back, and the flow carries on from the same place.
 */
export default function AIBridgePanel({ task, prompt, warning, onParsed, onCancel }) {
  const [copied, setCopied] = useState(false);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState(null);
  const [parsing, setParsing] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('คัดลอกอัตโนมัติไม่ได้ — เลือกข้อความในกล่องแล้วกด Ctrl+C เอาได้เลย');
    }
  };

  const handleUse = async () => {
    if (!answer.trim()) {
      setError('ยังไม่ได้วางคำตอบ');
      return;
    }
    setParsing(true);
    setError(null);
    try {
      const res = await aiParse(task, answer);
      onParsed(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setParsing(false);
    }
  };

  return (
    <div className="p-4 sm:p-5 space-y-3 glass-card text-slate-100 animate-fadeIn">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 border border-[#25F4EE]/30 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4 text-[#25F4EE]" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">โหมดวางเอง (Manual AI Bridge)</h4>
            <p className="text-sm text-slate-400">
              คัดลอกคำสั่งไปวางใน Antigravity หรือแชทที่ใช้อยู่ แล้วนำคำตอบ JSON มาวางกลับ
            </p>
          </div>
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            className="p-1.5 min-w-[32px] min-h-[32px] rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center flex-shrink-0"
            title="ปิด"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {warning && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-sm text-amber-300">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>{warning}</span>
        </div>
      )}

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-300">1. คัดลอกคำสั่งนี้</span>
          <button
            onClick={handleCopy}
            className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-slate-200 text-sm font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            {copied ? (
              <><Check className="w-3 h-3 text-emerald-400" />คัดลอกแล้ว</>
            ) : (
              <><Copy className="w-3 h-3 text-[#25F4EE]" />คัดลอก</>
            )}
          </button>
        </div>
        <textarea
          readOnly
          value={prompt}
          rows={5}
          onFocus={(e) => e.target.select()}
          className="w-full p-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-sm font-mono text-slate-200 resize-y focus:outline-none focus:border-[#25F4EE]/50"
        />
      </div>

      <div className="space-y-1.5">
        <span className="text-sm font-semibold text-slate-300">2. วางคำตอบ (JSON) ที่ได้กลับมา</span>
        <textarea
          value={answer}
          onChange={(e) => { setAnswer(e.target.value); setError(null); }}
          rows={4}
          placeholder='{ "angles": [ ... ] }'
          className="w-full p-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] focus:border-[#25F4EE]/50 outline-none text-sm font-mono text-slate-100 resize-y placeholder-slate-600"
        />
      </div>

      {error && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-300">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <button
        onClick={handleUse}
        disabled={parsing || !answer.trim()}
        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:opacity-90 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-md transition-all active:scale-95 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ClipboardPaste className="w-4 h-4" />
        {parsing ? 'กำลังอ่านคำตอบ...' : 'ใช้คำตอบนี้'}
      </button>
    </div>
  );
}

