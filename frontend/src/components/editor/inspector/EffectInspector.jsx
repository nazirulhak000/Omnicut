import React from 'react';
import { Trash2, Sparkles } from 'lucide-react';
import OverlayTimingControls from './OverlayTimingControls';
import OverlayScaleControl from './OverlayScaleControl';
import OverlayInspectorHeader from './OverlayInspectorHeader';

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
      <OverlayInspectorHeader
        preview={(
          <video
            src={videoUrl}
            className="max-h-full max-w-full object-contain"
            style={{ mixBlendMode: 'multiply' }}
            autoPlay
            loop
            muted
            playsInline
          />
        )}
        previewClassName="w-14 h-14 rounded-xl bg-white border border-white/[0.08] flex items-center justify-center p-1.5 flex-shrink-0 overflow-hidden"
        icon={Sparkles}
        kindLabel="วิดีโอเอฟเฟกต์"
        accentClass="text-fuchsia-400"
        title={title}
        duration={duration}
        start={start}
        end={end}
      />

      <OverlayTimingControls
        start={start}
        end={end}
        endMax={totalDuration || undefined}
        accentClass="text-fuchsia-400"
        inputFocusClass="focus:border-fuchsia-400"
        onStartChange={(value) => onUpdateEffect?.(effect.id, { start: value })}
        onEndChange={(value) => onUpdateEffect?.(effect.id, { end: value })}
      />

      <OverlayScaleControl
        scalePct={scalePct}
        accentClass="text-fuchsia-400"
        rangeClass="accent-fuchsia-400"
        resetHoverClass="hover:text-fuchsia-400"
        onChange={(value) => onUpdateEffect?.(effect.id, { scale: value })}
        onReset={() => onUpdateEffect?.(effect.id, { scale: 1.0 })}
      />

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
