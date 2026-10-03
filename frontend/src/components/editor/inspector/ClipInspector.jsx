import React, { useState } from 'react';
import { RotateCw, Volume2, VolumeX } from 'lucide-react';
import { TransitionIcon } from '../../../lib/transitionIcons';
import { TRANSITIONS, FADE_DURATION } from '../../../lib/timelineMath';
import {
  MIN_CLIP_SPEED,
  MAX_CLIP_SPEED,
  SLOW_ZOOM_PRESETS,
  cameraKeyframeSummary,
  clampFreezeTail,
  clampRotation,
  clampSpeed,
  clampTrimStart,
  clampTrimEnd,
  clampVolume,
  clampZoom,
  clampPan,
  clearCameraMotionPatch,
  clipSliderCoalesceKey,
  countOtherCameraKeyframeClips,
  framingResetPatch,
  normalizeSpeed,
  pickApplyAllPatch,
  slowZoomPatch,
  summarizeApplyToAll,
} from '../../../lib/inspectorModel';

const SPEEDS = [0.25, 0.5, 1, 1.25, 1.5, 2, 3, 4];

const COLOR_FIELDS = [
  { key: 'brightness', label: 'ความสว่าง', min: -0.3, max: 0.3, step: 0.02, def: 0 },
  { key: 'contrast', label: 'คอนทราสต์', min: 0.5, max: 2, step: 0.05, def: 1 },
  { key: 'saturation', label: 'ความสด', min: 0, max: 3, step: 0.05, def: 1 },
];

const APPLY_ALL_LABELS = { color: 'สี', framing: 'ซูม/เลื่อน', speed: 'ความเร็ว' };

function NumberInput(props) {
  return (
    <input
      type="number"
      {...props}
      className="w-full px-2.5 py-1.5 rounded-xl bg-black/60 border border-white/[0.1] text-white text-xs font-mono focus:outline-none focus:border-[#25F4EE] shadow-inner"
    />
  );
}

/**
 * Typed speed. The value is held as text until Enter/blur: clamping on every
 * keystroke would jump "0.5" to 0.25 the moment the first "0" is typed.
 */
function SpeedInput({ speed, onCommit }) {
  const [draft, setDraft] = useState(null);
  const commit = () => {
    if (draft === null) return;
    const parsed = parseFloat(draft);
    setDraft(null);
    if (Number.isFinite(parsed)) onCommit(normalizeSpeed(parsed));
  };
  return (
    <input
      type="text"
      inputMode="decimal"
      aria-label="ความเร็วที่กำหนดเอง (เท่า)"
      value={draft ?? String(speed)}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') commit();
        else if (e.key === 'Escape') setDraft(null);
      }}
      className="w-16 rounded bg-black/50 border border-white/[0.1] px-1.5 py-0.5 text-right font-mono text-xs text-white focus:outline-none focus:border-[#25F4EE]"
    />
  );
}

function ApplyAllButton({ onClick, disabled = false, title }) {
  return (
    <button
      type="button"
      disabled={disabled}
      title={title}
      onClick={onClick}
      className="text-xs text-[#25F4EE] hover:underline disabled:opacity-30 disabled:no-underline disabled:cursor-not-allowed cursor-pointer"
    >
      ใช้กับทุกคลิป
    </button>
  );
}

export default function ClipInspector({
  selectedSeg,
  onClipChange,
  clipList = [],
  onPatchAllClips = null,
}) {
  const [applyNote, setApplyNote] = useState(null);

  if (!selectedSeg?.clip) return null;

  const { clip, index, dur, srcDur } = selectedSeg;
  const zoom = clip.zoom ?? 1;
  const panning = zoom > 1.001;
  const bgBlur = !!clip.bg_blur || clip.fit_mode === 'blur';
  const freezeTail = Number(clip.freeze_tail) || 0;

  const colorTouched = COLOR_FIELDS.some(
    (f) => (clip[f.key] ?? f.def) !== f.def,
  );

  // Camera keyframes (written by the pipeline, or by the slow-zoom presets)
  // win over the static zoom/pan sliders in both preview and render.
  const cam = cameraKeyframeSummary(clip);
  const overriddenLabel = cam.zoom && cam.pan ? 'ซูม/เลื่อน' : cam.zoom ? 'ซูม' : 'เลื่อน';

  // Slider drags share one undo step per clip and field.
  const sliderChange = (field, patch) => onClipChange?.(
    patch,
    { coalesceKey: clipSliderCoalesceKey(clip.id, field) },
  );

  const canApplyAll = typeof onPatchAllClips === 'function' && clipList.length > 1;
  const otherCameraClips = canApplyAll ? countOtherCameraKeyframeClips(clipList, clip.id) : 0;
  const applyToAll = (group) => {
    const patch = pickApplyAllPatch(clip, group);
    if (!patch || !canApplyAll) return;
    const { changed, cameraKeyframeClips } = summarizeApplyToAll(clipList, patch);
    onPatchAllClips(patch);
    const label = APPLY_ALL_LABELS[group];
    let text = changed === 0
      ? `ค่า${label}ตรงกันทุกคลิปอยู่แล้ว`
      : `ใช้ค่า${label}กับอีก ${changed} คลิปแล้ว (Ctrl+Z ย้อนกลับได้ในครั้งเดียว)`;
    if (cameraKeyframeClips > 0) {
      text += ` · ${cameraKeyframeClips} คลิปมีการเคลื่อนกล้องของตัวเอง ค่าซูม/เลื่อนไม่มีผลกับคลิปเหล่านั้น`;
    }
    setApplyNote({ clipId: clip.id, group, text });
  };
  const applyNoteFor = (group) => (
    applyNote && applyNote.clipId === clip.id && applyNote.group === group
      ? <p role="status" className="text-[11px] leading-relaxed text-emerald-300/90">{applyNote.text}</p>
      : null
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
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs text-slate-400">ความเร็ว (Speed)</span>
            {canApplyAll && (
              <ApplyAllButton onClick={() => applyToAll('speed')} title="ใช้ความเร็วของคลิปนี้กับทุกคลิป" />
            )}
          </div>
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
          <label className="mt-1.5 flex items-center gap-2 text-xs text-slate-400">
            <span>กำหนดเอง</span>
            <SpeedInput
              key={clip.id}
              speed={clip.speed || 1}
              onCommit={(next) => onClipChange?.({ speed: next === 1 ? undefined : next })}
            />
            <span>เท่า (ช่วง {MIN_CLIP_SPEED} ถึง {MAX_CLIP_SPEED})</span>
          </label>
          {applyNoteFor('speed')}
          {/* Only offered where it changes anything: above 0.7x the stepping
              is not visible enough to be worth the render time. The note is
              the UI disclosure required for this approximation -- Preview
              plays the browser's own interpolation, not the rendered frames,
              so the two are close but not identical. */}
          {(clip.speed || 1) < 0.7 && (
            <label className="mt-2 flex items-start gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={!!clip.smooth_slowmo}
                onChange={(e) => onClipChange?.({ smooth_slowmo: e.target.checked || undefined })}
                className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 accent-[#25F4EE]"
              />
              <span>
                สโลว์โมชันนุ่มขึ้น (สร้างเฟรมเพิ่ม)
                <span className="block text-[11px] text-slate-500">
                  ค่า Preview เป็นค่าประมาณ ผลจริงดูที่ Render · ใช้เวลาเรนเดอร์นานขึ้นหลายเท่า
                </span>
              </span>
            </label>
          )}
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
            onChange={(e) => sliderChange('volume', { volume: clampVolume(parseFloat(e.target.value)) })}
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
            <div className="flex items-center gap-3">
              {canApplyAll && (
                <ApplyAllButton
                  onClick={() => applyToAll('framing')}
                  disabled={cam.points > 0}
                  title={cam.points > 0
                    ? 'คลิปนี้มีการเคลื่อนกล้อง ค่าซูม/เลื่อนที่ตั้งไว้ไม่ใช่ค่าที่เห็นในภาพ ล้างการเคลื่อนกล้องก่อนจึงจะใช้กับทุกคลิปได้'
                    : 'ใช้ซูมและเลื่อนของคลิปนี้กับทุกคลิป (ไม่คัดลอกการเคลื่อนกล้อง)'}
                />
              )}
              <button
                type="button"
                disabled={zoom === 1 && !clip.pan_x && !clip.pan_y && cam.points === 0}
                onClick={() => onClipChange?.(framingResetPatch(clip))}
                className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                รีเซ็ต
              </button>
            </div>
          </div>
          {cam.points > 0 && (
            <div role="status" className="space-y-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-2">
              <p className="text-[11px] leading-relaxed text-amber-200">
                คลิปนี้มีการเคลื่อนกล้องอัตโนมัติ {cam.points} จุด ตัวเลื่อน{overriddenLabel}ไม่มีผลจนกว่าจะล้าง
              </p>
              <button
                type="button"
                onClick={() => onClipChange?.(clearCameraMotionPatch(clip))}
                className="rounded-lg border border-amber-500/40 bg-amber-500/15 px-2 py-1 text-xs font-bold text-amber-200 hover:bg-amber-500/25 cursor-pointer"
              >
                ล้างการเคลื่อนกล้อง
              </button>
            </div>
          )}
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
          <label className={`block ${cam.zoom ? 'opacity-50' : ''}`}>
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
              onChange={(e) => sliderChange('zoom', { zoom: clampZoom(parseFloat(e.target.value)) })}
              className="w-full accent-[#25F4EE]"
            />
          </label>
          {[
            { key: 'pan_x', label: 'เลื่อนซ้าย-ขวา' },
            { key: 'pan_y', label: 'เลื่อนขึ้น-ลง' },
          ].map((f) => (
            <label key={f.key} className={`block ${!panning ? 'opacity-40' : cam.pan ? 'opacity-50' : ''}`}>
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
                onChange={(e) => sliderChange(f.key, { [f.key]: clampPan(parseFloat(e.target.value)) })}
                className="w-full accent-[#25F4EE] disabled:cursor-not-allowed"
              />
            </label>
          ))}
          {!panning && (
            <p className="text-[11px] text-slate-500">ซูมเกิน 1x ก่อนถึงจะเลื่อนกรอบได้</p>
          )}
          {applyNoteFor('framing')}
          {canApplyAll && otherCameraClips > 0 && (
            <p className="text-[11px] leading-relaxed text-amber-200/80">
              คลิปอื่น {otherCameraClips} คลิปมีการเคลื่อนกล้องของตัวเอง ค่าซูม/เลื่อนที่ใช้กับทุกคลิปจะไม่มีผลกับคลิปเหล่านั้น
            </p>
          )}

          {/* Slow zoom across the whole played clip (2-point keyframes) */}
          <div className="space-y-1 pt-1">
            <span className="block text-xs text-slate-400">ซูมช้าๆ ตลอดคลิป</span>
            <div className="grid grid-cols-2 gap-1">
              {SLOW_ZOOM_PRESETS.map((preset) => {
                const patch = slowZoomPatch(clip, srcDur, preset);
                return (
                  <button
                    key={preset.id}
                    type="button"
                    disabled={!patch}
                    title={patch ? undefined : 'ซูมปัจจุบันสูงสุดแล้ว หรือคลิปสั้นเกินไป'}
                    onClick={() => patch && onClipChange?.(patch)}
                    className="rounded-lg border border-white/[0.08] bg-black/40 py-1 text-xs font-bold text-slate-300 transition-all hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {preset.label}
                  </button>
                );
              })}
              <button
                type="button"
                disabled={cam.points === 0}
                onClick={() => onClipChange?.(clearCameraMotionPatch(clip))}
                className="rounded-lg border border-white/[0.08] bg-black/40 py-1 text-xs font-bold text-slate-300 transition-all hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                ล้าง
              </button>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500">
              เริ่มจากค่าซูมปัจจุบัน และแทนที่การเคลื่อนกล้องเดิมของคลิปนี้
            </p>
          </div>
        </div>

        {/* Colour EQ */}
        <div className="space-y-1.5 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">สีของคลิปนี้</span>
            <div className="flex items-center gap-3">
              {canApplyAll && (
                <ApplyAllButton onClick={() => applyToAll('color')} title="ใช้ค่าสีของคลิปนี้กับทุกคลิป" />
              )}
              <button
                type="button"
                disabled={!colorTouched}
                onClick={() => onClipChange?.({ brightness: undefined, contrast: undefined, saturation: undefined })}
                className="text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
              >
                รีเซ็ต
              </button>
            </div>
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
                  onChange={(e) => sliderChange(f.key, { [f.key]: parseFloat(e.target.value) })}
                  className="w-full accent-[#25F4EE]"
                />
              </label>
            );
          })}
          {applyNoteFor('color')}
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
