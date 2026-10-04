import React from 'react';
import {
  Type,
  Magnet,
  Clock,
  RotateCcw,
  Target,
  Globe,
  Play,
  Scissors,
} from 'lucide-react';
import { formatShortTime, clampScale } from '../../../lib/inspectorModel';

export const PRESET_STYLES = [
  {
    id: 'classic',
    name: 'ขาวคลาสสิก',
    color: '#FFFFFF',
    desc: 'ขาวขอบดำ คมชัด อ่านง่าย',
  },
  {
    id: 'tiktok',
    name: 'เหลือง TikTok',
    color: '#FFE600',
    desc: 'เหลืองนีออน ไวรัลสะดุดตา',
  },
  {
    id: 'warning',
    name: 'แดงเตือนภัย',
    color: '#FE2C55',
    desc: 'แดงเข้มข้น เตือนใจ ดึงสายตา',
  },
  {
    id: 'cyan',
    name: 'ฟ้านีออน Glow',
    color: '#25F4EE',
    desc: 'ฟ้าไซเบอร์ ล้ำยุค โดดเด่น',
  },
  {
    id: 'orange',
    name: 'ส้มพรีเมียม',
    color: '#FF7A00',
    desc: 'ส้มสดใหม่ ไฮไลต์จุดขาย',
  },
];

export const FONT_OPTIONS = [
  { id: 'Kanit', name: 'Kanit (คานิท - ค่ามาตรฐาน TikTok)' },
  { id: 'IBMPlex', name: 'IBM Plex Sans Thai (โมเดิร์น คมชัด)' },
  { id: 'Prompt', name: 'Prompt (พร้อมท์ - เรียบหรู ทันสมัย)' },
  { id: 'NotoSansThai', name: 'Noto Sans Thai (มาตรฐานทางการ)' },
  { id: 'Mali', name: 'Mali (มะลิ - กลมเป็นมิตร แนวรีวิวแกดเจ็ต)' },
];

/**
 * A labelled on/off switch.
 *
 * The knob is laid out by the flex row rather than pushed across with a fixed
 * translate: the track's padding then bounds it on both sides, so it cannot
 * overhang the way a hand-computed offset did once rounding and the ring came
 * into it.
 */
function CaptionToggle({ label, ariaLabel, checked, onToggle }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs text-slate-400 font-medium">{label}:</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel}
        onClick={onToggle}
        className={`flex w-11 shrink-0 items-center rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-[#25F4EE] ${
          checked ? 'justify-end bg-[#25F4EE]' : 'justify-start bg-white/[0.12]'
        }`}
      >
        <span className="block h-5 w-5 rounded-full bg-white shadow" />
      </button>
    </div>
  );
}

export default function CaptionInspector({
  selectedCaption,
  style = {},
  effectiveApplyToAll = true,
  toggleApplyToAll,
  onStyleChange,
  onPatchAllCaptions,
  onCaptionChange,
  onCloseAllCaptionGaps,
  onResetSubtitleTimings,
  onSeek,
  onSplitCueAtPlayhead,
}) {
  if (!selectedCaption) return null;

  const currentFont = selectedCaption.fontName || style?.fontName || 'Kanit';
  const currentScale = selectedCaption.scale ?? style?.captionScale ?? 1.0;
  const currentColor = selectedCaption.color || style?.captionColor || '#FFFFFF';
  const currentPosition = selectedCaption.position || style?.captionPosition || 'bottom';
  const currentTranslation = selectedCaption.translation;

  const handleFontChange = (fontName) => {
    if (effectiveApplyToAll) {
      onStyleChange?.({ fontName });
      onPatchAllCaptions?.({ fontName: null });
    } else {
      onCaptionChange?.(selectedCaption._uid, { fontName });
    }
  };

  const handleScaleChange = (scale) => {
    const clamped = clampScale(scale);
    if (effectiveApplyToAll) {
      onStyleChange?.({ captionScale: clamped }, { coalesceKey: 'caption:scale:all' });
      onPatchAllCaptions?.({ scale: null }, false, { coalesceKey: 'caption:scale:all' });
    } else {
      onCaptionChange?.(
        selectedCaption._uid,
        { scale: clamped },
        { coalesceKey: `caption:scale:${selectedCaption._uid}` },
      );
    }
  };

  const handleColorChange = (color) => {
    if (effectiveApplyToAll) {
      onStyleChange?.({ captionColor: color });
      onPatchAllCaptions?.({ color: null });
    } else {
      onCaptionChange?.(selectedCaption._uid, { color });
    }
  };

  const handlePositionChange = (position) => {
    if (effectiveApplyToAll) {
      onStyleChange?.({ captionPosition: position, captionX: 0.5 });
      onPatchAllCaptions?.({ position: null, x: null, y: null });
    } else {
      onCaptionChange?.(selectedCaption._uid, { position, x: null, y: null });
    }
  };

  const handleResetFormat = () => {
    if (effectiveApplyToAll) {
      onStyleChange?.({
        captionScale: 1.0,
        fontName: 'Kanit',
        captionColor: '#FFFFFF',
        captionPosition: 'bottom',
        captionX: 0.5,
      });
      onPatchAllCaptions?.({
        scale: null,
        x: null,
        y: null,
        fontName: null,
        color: null,
        position: null,
      });
    } else {
      onCaptionChange?.(selectedCaption._uid, {
        scale: null,
        x: null,
        y: null,
        fontName: null,
        color: null,
        position: null,
      });
    }
  };

  return (
    <div className="space-y-3">
      {/* Header Context Card */}
      <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white flex items-center gap-1.5">
            <Type className="w-4 h-4 text-[#25F4EE]" />
            คุณสมบัติคำบรรยาย
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 border border-white/[0.08]">
            {formatShortTime(selectedCaption.start)} - {formatShortTime(selectedCaption.end)}
          </span>
        </div>
      </div>

      {/* Subtitle Scope Selector & Action Buttons */}
      <div className="p-2 rounded-2xl bg-black/50 border border-white/[0.08] space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-400">ขอบเขตการปรับแต่ง:</span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {onCloseAllCaptionGaps && (
              <button
                type="button"
                onClick={onCloseAllCaptionGaps}
                className="px-2 py-1 rounded-lg bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[11px] font-semibold text-[#25F4EE] hover:text-[#52fffb] flex items-center gap-1 transition-all cursor-pointer"
                title="ดูดกล่องคำบรรยายทุกตัวให้ขยับมาเรียงชิดติดกันต่อเนื่องโดยไม่มีช่องว่าง"
              >
                <Magnet className="w-3 h-3 text-[#25F4EE]" />
                <span>ดูดชิดติดกัน</span>
              </button>
            )}
            {onResetSubtitleTimings && (
              <button
                type="button"
                onClick={onResetSubtitleTimings}
                className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-amber-300 hover:text-amber-200 flex items-center gap-1 transition-all cursor-pointer"
                title="รีเซ็ตเวลาเริ่มต้นและสิ้นสุดของคำบรรยายทุกตัวกลับสู่ค่าตั้งต้นเดิม"
              >
                <Clock className="w-3 h-3 text-amber-400" />
                <span>รีเซ็ตเวลาตั้งต้น</span>
              </button>
            )}
            <button
              type="button"
              onClick={handleResetFormat}
              className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-[11px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 transition-all cursor-pointer"
              title="คืนค่าขนาด 100%, ฟอนต์ Kanit, สีขาว และตำแหน่งกึ่งกลางล่าง"
            >
              <RotateCcw className="w-3 h-3 text-slate-400" />
              <span>รีเซ็ตค่าเริ่มต้น</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-black/60 border border-white/[0.06]">
          <button
            type="button"
            onClick={() => toggleApplyToAll?.(false)}
            className={`py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
              !effectiveApplyToAll
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>ปรับเฉพาะกล่องนี้</span>
          </button>
          <button
            type="button"
            onClick={() => toggleApplyToAll?.(true)}
            className={`py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
              effectiveApplyToAll
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>ปรับทั้งแผง</span>
          </button>
        </div>
      </div>

      {/* Textarea Content Box */}
      <div className="space-y-1.5">
        <textarea
          aria-label="ข้อความคำบรรยาย"
          rows={2}
          value={selectedCaption.text || ''}
          onChange={(e) => onCaptionChange?.(selectedCaption._uid, { text: e.target.value })}
          placeholder="พิมพ์ข้อความคำบรรยาย..."
          className="w-full px-3 py-2 rounded-xl bg-black/60 border border-white/[0.1] text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE] shadow-inner resize-none font-medium leading-relaxed"
        />
        {currentTranslation !== null && currentTranslation !== undefined && (
          <div className="space-y-1 pt-1">
            <span className="text-[11px] text-slate-400 font-medium">คำแปลภาษาอังกฤษ (English Subtitle):</span>
            <input
              type="text"
              aria-label="คำแปลภาษาอังกฤษ"
              value={currentTranslation || ''}
              onChange={(e) => onCaptionChange?.(selectedCaption._uid, { translation: e.target.value })}
              placeholder="English translation..."
              className="w-full px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/[0.08] text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]"
            />
          </div>
        )}
      </div>

      {/* Typography Controls Card */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
        {/* Font dropdown */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-slate-400 font-medium w-14 flex-shrink-0">ฟอนต์:</span>
          <select
            aria-label="ฟอนต์คำบรรยาย"
            value={currentFont}
            onChange={(e) => handleFontChange(e.target.value)}
            className="flex-1 min-w-0 py-1.5 px-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-xs font-semibold text-white focus:outline-none focus:border-[#25F4EE] cursor-pointer"
          >
            {FONT_OPTIONS.map((f) => (
              <option key={f.id} value={f.id} className="bg-[#0A0D14] text-white">
                {f.name}
              </option>
            ))}
          </select>
        </div>

        {/* Progressive Ghost Reveal -- SOP Phase 3 */}
        <CaptionToggle
          label="เด้งสีทีละคำ"
          ariaLabel="เด้งสีคำบรรยายทีละคำตามเสียงพูด"
          checked={!!style.ghostReveal}
          onToggle={() => onStyleChange?.({ ghostReveal: !style.ghostReveal })}
        />

        {/* Stacked English subtitle */}
        <CaptionToggle
          label="ซับอังกฤษ"
          ariaLabel="แสดงคำแปลภาษาอังกฤษใต้คำบรรยาย"
          checked={style.bilingualSubtitles !== false}
          onToggle={() => onStyleChange?.({ bilingualSubtitles: style.bilingualSubtitles === false })}
        />

        {/* Font size slider & number input */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">ขนาดตัวอักษร:</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                aria-label="ขนาดตัวอักษรคำบรรยาย (เปอร์เซ็นต์)"
                min={50}
                max={220}
                step={5}
                value={Math.round(currentScale * 100)}
                onChange={(e) => handleScaleChange(clampScale((parseInt(e.target.value, 10) || 100) / 100))}
                className="w-14 px-1.5 py-0.5 rounded-lg bg-black/60 border border-white/[0.1] text-right font-mono text-xs font-bold text-[#25F4EE] focus:outline-none focus:border-[#25F4EE]"
              />
              <span className="text-xs font-bold text-slate-400">%</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {[0.7, 0.85, 1.0, 1.25, 1.5].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => handleScaleChange(s)}
                className={`flex-1 py-1 rounded-lg text-[10px] sm:text-[11px] font-bold border transition-all cursor-pointer ${
                  Math.abs(currentScale - s) < 0.05
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE] shadow-sm'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {Math.round(s * 100)}%
              </button>
            ))}
          </div>
          <input
            type="range"
            aria-label="ปรับขนาดตัวอักษรคำบรรยาย"
            min="0.5"
            max="1.8"
            step="0.05"
            value={currentScale}
            onChange={(e) => handleScaleChange(parseFloat(e.target.value))}
            className="w-full accent-[#25F4EE] cursor-pointer"
          />
        </div>

        {/* Position on screen */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <span className="text-[11px] text-slate-400 font-medium">ตำแหน่งบนจอ:</span>
          <div className="grid grid-cols-3 gap-1.5">
            {[
              { pos: 'top', label: 'บน (20%)' },
              { pos: 'middle', label: 'กลาง (50%)' },
              { pos: 'bottom', label: 'ล่าง (72%)' },
            ].map(({ pos, label }) => (
              <button
                key={pos}
                type="button"
                onClick={() => handlePositionChange(pos)}
                className={`py-1 rounded-lg text-[11px] font-bold border transition-all cursor-pointer ${
                  currentPosition === pos
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Color picker */}
        <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 font-medium">สีตัวอักษร:</span>
            <div className="flex items-center gap-1.5">
              <input
                type="color"
                aria-label="สีตัวอักษรคำบรรยาย"
                value={currentColor.startsWith('#') ? currentColor : '#FFFFFF'}
                onChange={(e) => handleColorChange(e.target.value)}
                className="h-6 w-6 rounded border border-white/20 bg-transparent cursor-pointer p-0"
              />
              <span className="text-xs font-mono font-bold text-white uppercase">
                {currentColor}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Preset Styles */}
      <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300">สไตล์สำเร็จรูป (Preset Styles)</span>
          <span className="text-[10px] text-slate-500">คลิกเปลี่ยนทันที</span>
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {PRESET_STYLES.map((preset) => {
            const isCurrent = currentColor.toUpperCase() === preset.color.toUpperCase();
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleColorChange(preset.color)}
                className={`flex flex-col items-center justify-center p-1.5 rounded-xl border transition-all cursor-pointer group ${
                  isCurrent
                    ? 'border-[#25F4EE] bg-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40 shadow-sm'
                    : 'border-white/[0.08] bg-black/60 hover:border-white/20'
                }`}
                title={`${preset.name}: ${preset.desc}`}
              >
                <div
                  className="w-full h-8 rounded-lg flex items-center justify-center font-black text-sm border shadow-inner"
                  style={{
                    backgroundColor: '#000000',
                    color: preset.color,
                    borderColor: preset.color + '40',
                    textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                  }}
                >
                  Aa
                </div>
                <span className="text-[10px] font-bold text-slate-300 mt-1 truncate w-full text-center group-hover:text-white">
                  {preset.name}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Quick Actions for Selected Caption */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          type="button"
          onClick={() => onSeek?.(selectedCaption.start)}
          className="py-1.5 px-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
        >
          <Play className="w-3.5 h-3.5 fill-current text-emerald-400" />
          <span>เล่นท่อนนี้</span>
        </button>
        <button
          type="button"
          onClick={() => onSplitCueAtPlayhead?.(selectedCaption._uid)}
          className="py-1.5 px-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
        >
          <Scissors className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span>ตัดที่หัวอ่าน</span>
        </button>
      </div>
    </div>
  );
}
