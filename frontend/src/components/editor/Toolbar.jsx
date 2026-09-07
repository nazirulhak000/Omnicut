import React from 'react';
import {
  Copy, FlipHorizontal2, Gauge, Magnet, Maximize2, Redo2, RotateCcw, Scissors, Shield, Sparkles, Trash2, Undo2, ZoomIn, ZoomOut, Type,
} from 'lucide-react';
import { formatTimecode } from '../../lib/timelineMath';

const SPEEDS = [0.5, 1, 1.5, 2];

function ToolButton({ icon: Icon, label, hint, shortcut, onClick, disabled, active }) {
  const tip = [hint || label, shortcut && `(${shortcut})`].filter(Boolean).join(' ');
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={tip}
      aria-label={label}
      className={`flex h-9 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
        disabled
          ? 'cursor-not-allowed text-[#5A554F]'
          : active
            ? 'cursor-pointer bg-[#33251F] text-[#E89274]'
            : 'cursor-pointer text-[#C9C3BB] hover:bg-[#2C2B27] hover:text-[#EDE9E3]'
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

export default function Toolbar({
  playhead = 0,
  totalDuration = 0,
  hasClipSelected,
  hasSelection,
  selectedClip,
  canSplit = hasClipSelected,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSplit,
  onAddText,
  onDuplicate,
  onDelete,
  onToggleMirror,
  onCycleSpeed,
  onResetClipTransform,
  hasTransformOverride = false,
  currentHookTemplate = 'tech',
  customHookTemplates = {},
  onApplyHookTemplate,
  showSafeZone = false,
  onToggleSafeZone,
  zoomIndex,
  zoomCount,
  onZoom,
  onZoomToFit,
  snapEnabled,
  onToggleSnap,
}) {
  const speed = selectedClip?.speed || 1;
  const nextSpeed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length] || 1;

  return (
    <div className="flex items-center gap-1 border-b border-[#363430] bg-[#232220] px-2 py-1 overflow-x-auto no-scrollbar min-w-0">
      <ToolButton icon={Undo2} label="ย้อน" hint="ย้อนการแก้ล่าสุด" shortcut="Ctrl+Z" onClick={onUndo} disabled={!canUndo} />
      <ToolButton icon={Redo2} label="ไปหน้า" hint="ทำสิ่งที่เพิ่งย้อนไปอีกครั้ง" shortcut="Ctrl+Shift+Z" onClick={onRedo} disabled={!canRedo} />

      {/* Digital Timecode Display */}
      <div
        className="mx-1 flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#161514] border border-[#3A3833] font-mono text-xs font-semibold shadow-inner select-none"
        title="เวลาปัจจุบัน / เวลาทั้งหมดของคลิป"
      >
        <span className="text-[#25F4EE]">{formatTimecode(playhead)}</span>
        <span className="text-[#6B6660]">/</span>
        <span className="text-[#9C968F]">{formatTimecode(totalDuration)}</span>
      </div>

      <span className="mx-1 h-4 w-px bg-[#363430]" />

      <ToolButton icon={Scissors} label="แยก" hint="ผ่าคลิปตรงหัวอ่าน" shortcut="S / Ctrl+B" onClick={onSplit} disabled={!canSplit} />
      <ToolButton icon={Type} label="เพิ่มข้อความ" hint="แทรกข้อความใหม่ตรงหัวอ่าน" onClick={onAddText} />
      <ToolButton icon={Copy} label="ทำสำเนา" hint="ก๊อบคลิปที่เลือกต่อท้ายตัวเอง" onClick={onDuplicate} disabled={!hasClipSelected} />
      <ToolButton icon={Trash2} label="ลบ" shortcut="Del" onClick={onDelete} disabled={!hasSelection} />

      <span className="mx-1 h-4 w-px bg-[#363430]" />

      <ToolButton
        icon={FlipHorizontal2}
        label="กลับด้าน"
        onClick={onToggleMirror}
        disabled={!hasClipSelected}
        active={!!selectedClip?.mirror}
      />
      <ToolButton
        icon={Gauge}
        label={`${speed}x`}
        shortcut={`คลิกเป็น ${nextSpeed}x`}
        onClick={onCycleSpeed}
        disabled={!hasClipSelected}
        active={speed !== 1}
      />
      <ToolButton
        icon={RotateCcw}
        label="รีเซ็ตซูม"
        hint="คืนค่าซูมและตำแหน่งช็อตเป็น 100%"
        onClick={onResetClipTransform}
        disabled={!hasClipSelected || !hasTransformOverride}
        active={hasTransformOverride}
      />

      {/* Quick Hook Style Preset Selector */}
      <span className="mx-1 h-4 w-px bg-[#363430]" />
      <div
        className="flex items-center gap-1.5 rounded-lg bg-[#1C1B19] border border-[#3A3833] px-2 py-1 text-xs flex-shrink-0"
        title="เลือกสไตล์ป้ายฮุกพาดหัวคลิป (สร้างหรือเปลี่ยนทันที)"
      >
        <Sparkles className="h-3.5 w-3.5 text-[#FFE600] flex-shrink-0" />
        <span className="text-[#A8A29E] font-medium hidden md:inline">ฮุก:</span>
        <select
          value={currentHookTemplate || 'tech'}
          onChange={(e) => onApplyHookTemplate?.(e.target.value)}
          className="bg-transparent text-xs font-semibold text-[#EDE9E3] focus:outline-none cursor-pointer pr-1"
        >
          {Object.keys(customHookTemplates || {}).length > 0 && (
            <optgroup label="🌟 แม่แบบของฉัน">
              {Object.entries(customHookTemplates).map(([id, tpl]) => (
                <option key={id} value={id} className="bg-[#232220] text-[#25F4EE]">
                  {tpl.label_th || tpl.name || id}
                </option>
              ))}
            </optgroup>
          )}
          <optgroup label="⚡ แม่แบบมาตรฐาน">
            <option value="tech" className="bg-[#232220] text-[#EDE9E3]">เทค (Tech)</option>
            <option value="cute" className="bg-[#232220] text-[#EDE9E3]">คิ้วท์ (Cute)</option>
            <option value="bold_pop" className="bg-[#232220] text-[#EDE9E3]">ป็อปตัวหนา (Bold Pop)</option>
            <option value="plain" className="bg-[#232220] text-[#EDE9E3]">เรียบ (Plain)</option>
            <option value="clean" className="bg-[#232220] text-[#EDE9E3]">คลีน (Clean)</option>
            <option value="flash_sale" className="bg-[#232220] text-[#EDE9E3]">โปรไฟลุก (Flash Sale)</option>
            <option value="neon_cyber" className="bg-[#232220] text-[#EDE9E3]">นีออน (Neon)</option>
            <option value="minimal_luxury" className="bg-[#232220] text-[#EDE9E3]">ลักชัวรี (Luxury)</option>
          </optgroup>
        </select>
      </div>

      <div className="ml-auto flex items-center gap-1">
        <ToolButton
          icon={Shield}
          label="Safe Zone"
          hint="เปิด/ปิดเส้นไกด์ TikTok Safe Zone 420px"
          onClick={onToggleSafeZone}
          active={showSafeZone}
        />
        <ToolButton
          icon={Magnet}
          label="ดูดขอบ"
          onClick={onToggleSnap}
          active={snapEnabled}
        />
        <span className="mx-1 h-4 w-px bg-[#363430]" />
        <ToolButton icon={ZoomOut} label="" onClick={() => onZoom(-1)} disabled={zoomIndex <= 0} />
        <span className="w-10 text-center font-mono text-sm text-[#9C968F]">
          {zoomIndex + 1}/{zoomCount}
        </span>
        <ToolButton icon={ZoomIn} label="" onClick={() => onZoom(1)} disabled={zoomIndex >= zoomCount - 1} />
        <ToolButton icon={Maximize2} label="" hint="ซูมให้เห็นทั้งคลิปพอดีจอ" onClick={onZoomToFit} disabled={!onZoomToFit} />
      </div>
    </div>
  );
}
