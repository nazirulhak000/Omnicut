import React from 'react';
import { Trash2, Smile, Clock, Maximize2, Move } from 'lucide-react';

const STICKER_TITLES = {
  accent_sparkle_star_3d: 'ดาวเปล่งประกาย 3D',
  arrow_pointer_cyan_3d: 'ลูกศรชี้สีฟ้า 3D',
  arrow_pointer_yellow_3d: 'ลูกศรชี้สีเหลือง 3D',
  badge_exclamation_alert_3d: 'ป้ายเตือนเครื่องหมายตกใจ 3D',
  frame_tech_callout_3d: 'กรอบเน้นสเปก 3D',
  frame_tech_callout_hollow_3d: 'กรอบโปร่งเน้นจุดขาย 3D',
  icon_fire_hot_deal_3d: 'ไอคอนไฟฮอตดีล 3D',
  plate_banner_coral_3d: 'ป้ายริบบิ้นสีคอรัล 3D',
  plate_banner_cyan_3d: 'ป้ายริบบิ้นสีฟ้า 3D',
  plate_banner_yellow_3d: 'ป้ายริบบิ้นสีเหลือง 3D',
};

export default function StickerInspector({
  sticker,
  onUpdateSticker,
  onDeleteSticker,
  totalDuration = 30,
}) {
  if (!sticker) return null;

  const baseName = (sticker.badge || '').replace(/\.[^.]+$/, '');
  const title = STICKER_TITLES[baseName] || baseName || 'สติกเกอร์ 3D';
  const imgUrl = `/api/media/02_Assets/Stickers_Memes/${sticker.badge}`;

  const start = typeof sticker.start === 'number' ? sticker.start : 0;
  const end = typeof sticker.end === 'number' ? sticker.end : (start + 3.0);
  const duration = Math.max(0.1, Math.round((end - start) * 10) / 10);
  const scale = typeof sticker.scale === 'number' ? sticker.scale : 1.0;
  const scalePct = Math.round(scale * 100);
  const normX = typeof sticker.normX === 'number' ? sticker.normX : 0.5;
  const normY = typeof sticker.normY === 'number' ? sticker.normY : 0.5;

  return (
    <div className="flex flex-col gap-4 p-4 text-slate-200">
      {/* ─── Header: Sticker Preview & Info ─── */}
      <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.04] border border-white/[0.08]">
        <div className="w-14 h-14 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-center p-1.5 flex-shrink-0">
          <img
            src={imgUrl}
            alt={title}
            className="max-h-full max-w-full object-contain drop-shadow"
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-xs text-[#25F4EE] font-semibold">
            <Smile className="w-3.5 h-3.5" />
            <span>สติกเกอร์ 3D</span>
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
          <Clock className="w-3.5 h-3.5 text-[#25F4EE]" />
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
                onUpdateSticker?.(sticker.id, { start: Math.max(0, val) });
              }}
              className="mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white focus:border-[#25F4EE] focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-[11px] text-slate-400">จบที่ (วินาที)</span>
            <input
              type="number"
              step="0.1"
              min={start + 0.1}
              value={end}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || (start + 0.1);
                onUpdateSticker?.(sticker.id, { end: Math.max(start + 0.1, val) });
              }}
              className="mt-1 w-full rounded-lg bg-black/40 border border-white/[0.1] px-2.5 py-1.5 text-xs font-mono text-white focus:border-[#25F4EE] focus:outline-none"
            />
          </label>
        </div>
      </div>

      {/* ─── Scale / Size Controls ─── */}
      <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
          <div className="flex items-center gap-2">
            <Maximize2 className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>ขนาด (Scale)</span>
          </div>
          <span className="text-xs font-mono font-bold text-[#25F4EE]">{scalePct}%</span>
        </div>
        <input
          type="range"
          min="30"
          max="300"
          step="5"
          value={scalePct}
          onChange={(e) => {
            const pct = parseInt(e.target.value, 10) || 100;
            onUpdateSticker?.(sticker.id, { scale: Math.round((pct / 100) * 100) / 100 });
          }}
          className="w-full accent-[#25F4EE] cursor-pointer"
        />
        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>30%</span>
          <button
            type="button"
            onClick={() => onUpdateSticker?.(sticker.id, { scale: 1.0 })}
            className="text-[11px] text-slate-400 hover:text-[#25F4EE] underline cursor-pointer"
          >
            คืนค่า 100%
          </button>
          <span>300%</span>
        </div>
      </div>

      {/* ─── Position Info ─── */}
      <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
          <div className="flex items-center gap-2">
            <Move className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>ตำแหน่งกึ่งกลาง</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            X: {Math.round(normX * 100)}% · Y: {Math.round(normY * 100)}%
          </span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          สามารถคลิกลากย้ายตำแหน่งและดึงขอบปรับขนาดบนหน้าจอวิดีโอได้อย่างอิสระ
        </p>
        <button
          type="button"
          onClick={() => onUpdateSticker?.(sticker.id, { normX: 0.5, normY: 0.5 })}
          className="w-full py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-medium border border-white/[0.06] transition-colors cursor-pointer"
        >
          จัดกึ่งกลางจอ
        </button>
      </div>

      {/* ─── Delete Sticker Action ─── */}
      <div className="pt-2">
        <button
          type="button"
          onClick={() => onDeleteSticker?.(sticker.id)}
          className="w-full py-2.5 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 border border-red-500/20 flex items-center justify-center gap-2 font-bold text-xs cursor-pointer transition-all active:scale-[0.98] shadow-sm"
          title="ลบสติกเกอร์นี้ออกจากไทม์ไลน์"
        >
          <Trash2 className="w-4 h-4" />
          <span>ลบสติกเกอร์</span>
        </button>
      </div>
    </div>
  );
}
