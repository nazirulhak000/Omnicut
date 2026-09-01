import React from 'react';
import {
  Copy, FlipHorizontal2, Gauge, Magnet, Redo2, Scissors, Trash2, Undo2, ZoomIn, ZoomOut,
} from 'lucide-react';

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
      className={`flex h-7 items-center gap-1.5 rounded-lg px-2 text-[11px] font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
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
  hasClipSelected,
  hasSelection,
  selectedClip,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSplit,
  onDuplicate,
  onDelete,
  onToggleMirror,
  onCycleSpeed,
  zoomIndex,
  zoomCount,
  onZoom,
  snapEnabled,
  onToggleSnap,
}) {
  const speed = selectedClip?.speed || 1;
  const nextSpeed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length] || 1;

  return (
    <div className="flex items-center gap-1 border-b border-[#363430] bg-[#232220] px-2 py-1">
      <ToolButton icon={Undo2} label="ย้อน" hint="ย้อนการแก้ล่าสุด" shortcut="Ctrl+Z" onClick={onUndo} disabled={!canUndo} />
      <ToolButton icon={Redo2} label="ไปหน้า" hint="ทำสิ่งที่เพิ่งย้อนไปอีกครั้ง" shortcut="Ctrl+Shift+Z" onClick={onRedo} disabled={!canRedo} />

      <span className="mx-1 h-4 w-px bg-[#363430]" />

      <ToolButton icon={Scissors} label="แยก" hint="ผ่าคลิปที่เลือกตรงหัวอ่าน" shortcut="S" onClick={onSplit} disabled={!hasClipSelected} />
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

      <div className="ml-auto flex items-center gap-1">
        <ToolButton
          icon={Magnet}
          label="ดูดขอบ"
          onClick={onToggleSnap}
          active={snapEnabled}
        />
        <span className="mx-1 h-4 w-px bg-[#363430]" />
        <ToolButton icon={ZoomOut} label="" onClick={() => onZoom(-1)} disabled={zoomIndex <= 0} />
        <span className="w-10 text-center font-mono text-[10px] text-[#9C968F]">
          {zoomIndex + 1}/{zoomCount}
        </span>
        <ToolButton icon={ZoomIn} label="" onClick={() => onZoom(1)} disabled={zoomIndex >= zoomCount - 1} />
      </div>
    </div>
  );
}
