import React from 'react';
import { Trash2, Smile, Move } from 'lucide-react';
import OverlayTimingControls from './OverlayTimingControls';
import OverlayScaleControl from './OverlayScaleControl';
import OverlayInspectorHeader from './OverlayInspectorHeader';

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
      <OverlayInspectorHeader
        preview={(
          <img
            src={imgUrl}
            alt={title}
            className="max-h-full max-w-full object-contain drop-shadow"
          />
        )}
        icon={Smile}
        kindLabel="สติกเกอร์ 3D"
        title={title}
        duration={duration}
        start={start}
        end={end}
      />

      <OverlayTimingControls
        start={start}
        end={end}
        coalescePrefix={`sticker:${sticker.id}`}
        onStartChange={(value, options) => onUpdateSticker?.(sticker.id, { start: value }, options)}
        onEndChange={(value, options) => onUpdateSticker?.(sticker.id, { end: value }, options)}
      />

      <OverlayScaleControl
        scalePct={scalePct}
        ariaLabel="ขนาดสติกเกอร์"
        coalesceKey={`sticker:${sticker.id}:scale`}
        onChange={(value, options) => onUpdateSticker?.(sticker.id, { scale: value }, options)}
        onReset={() => onUpdateSticker?.(sticker.id, { scale: 1.0 })}
      />

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
