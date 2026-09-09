import React from 'react';
import { Trash2, Sparkles, Clock, Maximize2 } from 'lucide-react';

export default function EffectInspector({
  effect,
  effectAsset,
  onUpdateEffect,
  onDeleteEffect,
  totalDuration = 30,
}) {
  if (!effect) return null;

  const title = effectAsset?.label || effectAsset?.label_th || effect.effectId;
  const videoUrl = effectAsset?.video_url || `/api/media/02_Assets/Effects/${effect.effectId}.webm`;

  const start = typeof effect.start === 'number' ? effect.start : 0;
  const end = typeof effect.end === 'number' ? effect.end : (start + 3.0);
  const duration = Math.max(0.1, Math.round((end - start) * 10) / 10);
  const scale = typeof effect.scale === 'number' ? effect.scale : 1.0;
  const scalePct = Math.round(scale * 100);
  const normX = typeof effect.normX === 'number' ? effect.normX : 0.5;
  const normY = typeof effect.normY === 'number' ? effect.normY : 0.35;

  return (
    <div className="flex flex-col gap-4 p-4 text-slate-200">
      {/* ─── Header: Effect Preview & Info ─── */}
      <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.04] border border-white/[0.08]">
        <div className="w-14 h-14 rounded-xl bg-white border border-white/[0.08] flex items-center justify-center p-1.5 flex-shrink-0 overflow-hidden">
          <video
            src={videoUrl}
            className="max-h-full max-w-full object-contain"
            style={{ mixBlendMode: 'multiply' }}
            autoPlay
            loop
            muted
            playsInline
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-xs text-fuchsia-400 font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>วิดีโอเอฟเฟกต์</span>
          </div>
          <h3 className="text-sm font-bold text-white truncate mt-0.5">{title}</h3>
          <p className="text-[11px] text-slate-400 font-mono mt-0.5">
            {duration.toFixed(1)}s ({start.toFixed(1)}s – {end.toFixed(1)}s)
          </p>
        </div>
      </div>

      {/* ─── Timing Controls ─── */}
      <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
          <Clock className="w-3.5 h-3.5 text-fuchsia-400" />
          <span>ช่วงเวลาแสดงผล</span>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <label className="block">
            <span className="text-[11px] text-slate-400">เริ่มที่ (วินาที)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max={Math.max(0, end - 0.1)}
              value={start}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || 0;
                onUpdateEffect?.(effect.id, { start: Math.max(0, val) });
              }}
              className="mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white focus:border-fuchsia-400 focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-[11px] text-slate-400">จบที่ (วินาที)</span>
            <input
              type="number"
              step="0.1"
              min={start + 0.1}
              max={totalDuration || undefined}
              value={end}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || (start + 0.1);
                onUpdateEffect?.(effect.id, { end: Math.max(start + 0.1, val) });
              }}
              className="mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white focus:border-fuchsia-400 focus:outline-none"
            />
          </label>
        </div>
      </div>

      {/* ─── Scale / Size Controls ─── */}
      <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
          <div className="flex items-center gap-2">
            <Maximize2 className="w-3.5 h-3.5 text-fuchsia-400" />
            <span>ขนาด (Scale)</span>
          </div>
          <span className="text-xs font-mono font-bold text-fuchsia-400">{scalePct}%</span>
        </div>
        <input
          type="range"
          min="30"
          max="300"
          step="5"
          value={scalePct}
          onChange={(e) => {
            const pct = parseInt(e.target.value, 10) || 100;
            onUpdateEffect?.(effect.id, { scale: Math.round((pct / 100) * 100) / 100 });
          }}
          className="w-full accent-fuchsia-400 cursor-pointer"
        />
        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>30%</span>
          <button
            type="button"
            onClick={() => onUpdateEffect?.(effect.id, { scale: 1.0 })}
            className="text-[11px] text-slate-400 hover:text-fuchsia-400 underline cursor-pointer"
          >
            คืนค่า 100%
          </button>
          <span>300%</span>
        </div>
      </div>

      {/* ─── Position (numeric only -- no canvas drag yet for effects) ─── */}
      <div className="space-y-2 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
          <span>ตำแหน่งกึ่งกลาง</span>
          <span className="text-[11px] font-mono text-slate-400">
            X: {Math.round(normX * 100)}% · Y: {Math.round(normY * 100)}%
          </span>
        </div>
        <button
          type="button"
          onClick={() => onUpdateEffect?.(effect.id, { normX: 0.5, normY: 0.5 })}
          className="w-full py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-medium border border-white/[0.06] transition-colors cursor-pointer"
        >
          จัดกึ่งกลางจอ
        </button>
      </div>

      {/* ─── Delete Effect Action ─── */}
      <div className="pt-2">
        <button
          type="button"
          onClick={() => onDeleteEffect?.(effect.id)}
          className="w-full py-2.5 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 border border-red-500/20 flex items-center justify-center gap-2 font-bold text-xs cursor-pointer transition-all active:scale-[0.98] shadow-sm"
          title="ลบเอฟเฟกต์นี้ออกจากไทม์ไลน์"
        >
          <Trash2 className="w-4 h-4" />
          <span>ลบเอฟเฟกต์</span>
        </button>
      </div>
    </div>
  );
}
