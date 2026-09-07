import React from 'react';
import { Copy, Crop, FlipHorizontal2, Gauge, Scissors, Trash2 } from 'lucide-react';

export default function TimelineContextMenu({
  contextMenu,
  onClose,
  onSplit,
  onDuplicate,
  onToggleMirror,
  onAdjustTrim,
  onClipChange,
  onDelete,
}) {
  if (!contextMenu) return null;

  const fileName = contextMenu.seg?.clip?.source_path?.split(/[\\/]/).pop() || 'คลิปวิดีโอ';
  const curSpeed = contextMenu.seg?.clip?.speed || 1;

  return (
    <div
      data-context-menu=""
      onClick={(e) => e.stopPropagation()}
      className="fixed z-50 min-w-[190px] rounded-xl border border-[#4A4742] bg-[#1E1D1A]/95 p-1.5 shadow-2xl backdrop-blur-md text-xs text-[#EDE9E3] animate-in fade-in zoom-in-95 duration-100"
      style={{
        left: Math.max(10, Math.min(typeof window !== 'undefined' ? window.innerWidth - 200 : 1000, contextMenu.x)),
        top: Math.max(10, Math.min(typeof window !== 'undefined' ? window.innerHeight - 230 : 800, contextMenu.y)),
      }}
    >
      <div className="px-2 py-1 font-mono text-[10px] font-semibold text-[#9C968F] border-b border-[#363430] truncate">
        {fileName}
      </div>
      <div className="py-1 space-y-0.5">
        <button
          type="button"
          onClick={() => {
            onSplit?.();
            onClose?.();
          }}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[#D97757]/20 hover:text-[#E89274] transition-colors"
        >
          <span className="flex items-center gap-2">
            <Scissors className="h-3.5 w-3.5" />
            <span>ผ่าคลิปตรงหัวอ่าน</span>
          </span>
          <span className="text-[10px] text-slate-500 font-mono">S / Ctrl+B</span>
        </button>
        <button
          type="button"
          onClick={() => {
            onDuplicate?.();
            onClose?.();
          }}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#2C2B27] transition-colors"
        >
          <Copy className="h-3.5 w-3.5" />
          <span>ทำสำเนาคลิป</span>
        </button>
        <button
          type="button"
          onClick={() => {
            onToggleMirror?.();
            onClose?.();
          }}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#2C2B27] transition-colors"
        >
          <FlipHorizontal2 className="h-3.5 w-3.5" />
          <span>กลับด้านภาพ (Mirror)</span>
        </button>
        <button
          type="button"
          onClick={() => {
            onAdjustTrim?.();
            onClose?.();
          }}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#2C2B27] transition-colors"
        >
          <Crop className="h-3.5 w-3.5" />
          <span>ปรับช่วงตัด</span>
        </button>
      </div>

      <div className="my-1 border-t border-[#363430]" />
      <div className="px-2 py-1 text-[10px] text-[#9C968F] flex items-center gap-1">
        <Gauge className="h-3 w-3" />
        <span>ปรับความเร็ว:</span>
      </div>
      <div className="grid grid-cols-4 gap-1 px-1">
        {[0.5, 1, 1.5, 2].map((sp) => (
          <button
            key={sp}
            type="button"
            onClick={() => {
              onClipChange?.(contextMenu.seg.clip.id, { speed: sp === 1 ? undefined : sp });
              onClose?.();
            }}
            className={`py-1 rounded text-center font-semibold transition-colors ${
              curSpeed === sp
                ? 'bg-[#D97757] text-white'
                : 'bg-[#282724] hover:bg-[#363430] text-[#C9C3BB]'
            }`}
          >
            {sp}x
          </button>
        ))}
      </div>

      <div className="my-1 border-t border-[#363430]" />
      <button
        type="button"
        onClick={() => {
          onDelete?.();
          onClose?.();
        }}
        className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-rose-400 hover:bg-rose-500/20 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Trash2 className="h-3.5 w-3.5" />
          <span>ลบคลิป</span>
        </span>
        <span className="text-[10px] text-rose-400/60 font-mono">Del</span>
      </button>
    </div>
  );
}
