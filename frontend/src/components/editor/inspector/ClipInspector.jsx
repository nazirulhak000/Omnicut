import React from 'react';
import { RotateCw, Volume2, VolumeX } from 'lucide-react';
import { TransitionIcon } from '../../../lib/transitionIcons';
import { TRANSITIONS, FADE_DURATION } from '../../../lib/timelineMath';
import {
  clampFreezeTail,
  clampRotation,
  clampSpeed,
  clampTrimStart,
  clampTrimEnd,
  clampVolume,
  clampZoom,
  clampPan,
} from '../../../lib/inspectorModel';

const SPEEDS = [0.5, 1, 1.5, 2];

const COLOR_FIELDS = [
  { key: 'brightness', label: 'ความสว่าง', min: -0.3, max: 0.3, step: 0.02, def: 0 },
  { key: 'contrast', label: 'คอนทราสต์', min: 0.5, max: 2, step: 0.05, def: 1 },
  { key: 'saturation', label: 'ความสด', min: 0, max: 3, step: 0.05, def: 1 },
];

function NumberInput(props) {
  return (
    <input
      type="number"
      {...props}
      className="w-full px-2.5 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-white text-xs font-mono focus:outline-none focus:border-[#25F4EE] shadow-inner"
    />
  );
}

export default function ClipInspector({ selectedSeg, onClipChange }) {
  if (!selectedSeg?.clip) return null;

  const { clip, index, dur, srcDur } = selectedSeg;
  const zoom = clip.zoom ?? 1;
  const panning = zoom > 1.001;
  const bgBlur = !!clip.bg_blur || clip.fit_mode === 'blur';
  const freezeTail = Number(clip.freeze_tail) || 0;

  const colorTouched = COLOR_FIELDS.some(
    (f) => (clip[f.key] ?? f.def) !== f.def,
  );

  return (
    <div className="space-y-3">
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
        <div className="flex items-center justify-between text-xs font-bold text-white">
          <span>คลิปที่ {index + 1}</span>
          <span className="font-mono text-[#25F4EE]">{dur.toFixed(2)}s</span>
        </div>
        <p className="truncate text-xs text-slate-400 font-mono" title={clip.source_path}>
          {(clip.source_path || '').split(/[\\/]/).pop()}
        </p>

        {/* Trimming Controls */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <div>
            <span className="block text-xs text-slate-400 mb-1">Trim เข้า (วิ)</span>
            <NumberInput
              aria-label="Trim เข้า (วิ)"
              step="0.1"
              min="0"
              value={clip.trim_start ?? 0}
              onChange={(e) => onClipChange?.({ trim_start: clampTrimStart(e.target.value, clip, srcDur) })}
            />
          </div>
          <div>
            <span className="block text-xs text-slate-400 mb-1">Trim ออก (วิ)</span>
            <NumberInput
              aria-label="Trim ออก (วิ)"
              step="0.1"
              min="0"
              placeholder="สุดคลิป"
              value={clip.trim_end ?? ''}
              onChange={(e) => onClipChange?.({ trim_end: clampTrimEnd(e.target.value, clip, srcDur) })}
            />
          </div>
        </div>

        {/* Speed Controls */}
        <div>
          <span className="block text-xs text-slate-400 mb-1">ความเร็ว (Speed)</span>
          <div className="grid grid-cols-4 gap-1">
            {SPEEDS.map((s) => {
              const active = (clip.speed || 1) === s;
              return (
                <button
                  key={s}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onClipChange?.({ speed: s === 1 ? undefined : clampSpeed(s) })}
                  className={`py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                    active
                      ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                      : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                  }`}
                >
                  {s}x
                </button>
              );
            })}
          </div>
        </div>

        {/* Rotate 0 / 90 / 180 / 270 */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              <RotateCw className="h-3.5 w-3.5 text-[#25F4EE]" />
              หมุนภาพ (Rotate)
            </span>
            {clip.rotation ? (
              <button
                type="button"
                onClick={() => onClipChange?.({ rotation: undefined })}
                className="text-xs text-[#E89274] hover:underline cursor-pointer"
              >
                รีเซ็ต 0°
              </button>
            ) : null}
          </div>
          <div className="grid grid-cols-4 gap-1">
            {[0, 90, 180, 270].map((deg) => {
              const active = (clip.rotation || 0) === deg;
              return (
                <button
                  key={deg}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onClipChange?.({ rotation: deg === 0 ? undefined : clampRotation(deg) })}
                  className={`py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                    active
                      ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                      : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                  }`}
                >
                  {deg}°
                </button>
              );
            })}
          </div>
        </div>

        {/* Mirror Toggle */}
        <button
          type="button"
          aria-pressed={!!clip.mirror}
          onClick={() => onClipChange?.({ mirror: !clip.mirror })}
          className={`w-full py-1.5 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
            clip.mirror
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
              : 'bg-black/40 border-white/[0.08] text-slate-300 hover:text-white'
          }`}
        >
          {clip.mirror ? '✓ กลับด้านซ้าย-ขวาอยู่' : 'กลับด้านซ้าย-ขวา (Mirror)'}
        </button>

        {/* Original Audio Volume (0 - 100%) */}
        <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              {(clip.volume || 0) > 0 ? (
                <Volume2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <VolumeX className="h-3.5 w-3.5 text-slate-500" />
              )}
              เสียงคลิปต้นฉบับ (Original Audio)
            </span>
            <button
              type="button"
              onClick={() => onClipChange?.({ volume: (clip.volume || 0) > 0 ? 0 : 1.0 })}
              aria-label={(clip.volume || 0) > 0 ? 'ปิดเสียงคลิปต้นฉบับ' : 'เปิดเสียงคลิปต้นฉบับ'}
              className="text-xs font-mono font-bold text-[#25F4EE] hover:underline cursor-pointer"
            >
              {Math.round((clip.volume || 0) * 100)}%
            </button>
          </div>
          <input
            type="range"
            aria-label="ระดับเสียงคลิปต้นฉบับ"
            min={0}
            max={1}
            step={0.05}
            value={clip.volume || 0}
            onChange={(e) => onClipChange?.({ volume: clampVolume(parseFloat(e.target.value)) })}
            className="w-full accent-[#25F4EE]"
          />
          {clip.volume > 0 && (clip.speed || 1) !== 1 && (
            <p className="text-[11px] leading-relaxed text-amber-200/80">
              Preview อาจได้ยิน pitch ต่างจาก Render เมื่อเปลี่ยนความเร็วคลิป
            </p>
          )}
        </div>

        {/* Framing: Zoom, Pan X/Y, Blur background, Freeze tail */}
        <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">กรอบภาพ</span>
            <button
              type="button"
              disabled={zoom === 1 && !clip.pan_x && !clip.pan_y}
              onClick={() => onClipChange?.({ zoom: undefined, pan_x: undefined, pan_y: undefined })}
              className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              รีเซ็ต
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-pressed={bgBlur}
              onClick={() => onClipChange?.({ bg_blur: bgBlur ? undefined : true, fit_mode: bgBlur ? undefined : 'blur' })}
              className={`flex-1 rounded-xl border px-2 py-1 text-xs font-bold transition-all cursor-pointer ${
                bgBlur
                  ? 'border-[#25F4EE] bg-[#25F4EE]/15 text-[#25F4EE]'
                  : 'border-white/[0.1] bg-black/40 text-slate-400 hover:text-white'
              }`}
            >
              {bgBlur ? '✓ พื้นหลังเบลอ' : 'พื้นหลังเบลอ'}
            </button>
            <label className="flex items-center gap-1 text-xs text-slate-400">
              <span>ค้างท้าย</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.5"
                value={freezeTail}
                onChange={(e) => {
                  const v = clampFreezeTail(parseFloat(e.target.value) || 0);
                  onClipChange?.({ freeze_tail: v === 0 ? undefined : v });
                }}
                className="w-14 rounded bg-black/50 border border-white/[0.1] px-1 py-0.5 text-right font-mono text-xs text-white focus:outline-none focus:border-[#25F4EE]"
              />
              <span>วิ</span>
            </label>
          </div>
          <label className="block">
            <span className="mb-0.5 flex justify-between text-xs text-slate-400">
              <span>ซูม</span>
              <span className="font-mono text-slate-300">{zoom.toFixed(2)}x</span>
            </span>
            <input
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              onChange={(e) => onClipChange?.({ zoom: clampZoom(parseFloat(e.target.value)) })}
              className="w-full accent-[#25F4EE]"
            />
          </label>
          {[
            { key: 'pan_x', label: 'เลื่อนซ้าย-ขวา' },
            { key: 'pan_y', label: 'เลื่อนขึ้น-ลง' },
          ].map((f) => (
            <label key={f.key} className={`block ${panning ? '' : 'opacity-40'}`}>
              <span className="mb-0.5 flex justify-between text-xs text-slate-400">
                <span>{f.label}</span>
                <span className="font-mono text-slate-300">{(clip[f.key] ?? 0).toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={-1}
                max={1}
                step={0.05}
                value={clip[f.key] ?? 0}
                disabled={!panning}
                onChange={(e) => onClipChange?.({ [f.key]: clampPan(parseFloat(e.target.value)) })}
                className="w-full accent-[#25F4EE] disabled:cursor-not-allowed"
              />
            </label>
          ))}
          {!panning && (
            <p className="text-[11px] text-slate-500">ซูมเกิน 1x ก่อนถึงจะเลื่อนกรอบได้</p>
          )}
        </div>

        {/* Colour EQ */}
        <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">สีของคลิปนี้</span>
            <button
              type="button"
              disabled={!colorTouched}
              onClick={() => onClipChange?.({ brightness: undefined, contrast: undefined, saturation: undefined })}
              className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              รีเซ็ต
            </button>
          </div>
          {COLOR_FIELDS.map((f) => {
            const value = clip[f.key] ?? f.def;
            return (
              <label key={f.key} className="block">
                <span className="mb-0.5 flex justify-between text-xs text-slate-400">
                  <span>{f.label}</span>
                  <span className="font-mono text-slate-300">{value.toFixed(2)}</span>
                </span>
                <input
                  type="range"
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  value={value}
                  onChange={(e) => onClipChange?.({ [f.key]: parseFloat(e.target.value) })}
                  className="w-full accent-[#25F4EE]"
                />
              </label>
            );
          })}
          {colorTouched && (
            <p className="text-[11px] leading-relaxed text-amber-200/80">
              สีใน Preview เป็นค่าประมาณ โดยเฉพาะความสว่าง; Render เป็นผลลัพธ์อ้างอิง
            </p>
          )}
        </div>

        {/* Boundary Transition with Previous Clip */}
        {index > 0 && (() => {
          const kind = clip.transition_in || 'cut';
          const durTrans = clip.transition_duration ?? FADE_DURATION;
          return (
            <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
              <span className="block text-xs text-slate-400">รอยต่อกับคลิปก่อนหน้า</span>
              <div className="grid grid-cols-2 gap-1">
                {TRANSITIONS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    aria-pressed={kind === t.id}
                    onClick={() => onClipChange?.({
                      transition_in: t.id,
                      transition_duration: durTrans,
                    })}
                    className={`flex items-center justify-center gap-1.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer border ${
                      kind === t.id
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                  >
                    <TransitionIcon type={t.id} className="h-3.5 w-3.5 flex-shrink-0" />
                    {t.label}
                  </button>
                ))}
              </div>
              {['dissolve', 'fadeblack', 'fadewhite'].includes(kind) && (
                <p className="text-[11px] leading-relaxed text-amber-200/80">
                  Preview ของ Transition นี้เป็นค่าประมาณ; ตรวจรอยต่อใน Render อีกครั้ง
                </p>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
