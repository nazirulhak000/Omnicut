import React from 'react';
import { Smartphone, Home, Sparkles, Flame, ShoppingBag, ArrowRight, Check, Zap, Layers, X, RotateCcw } from 'lucide-react';

export default function PresetsBar({
  activeProductContext,
  selectedAngleIndex,
  onSelectAngle,
  onSelectPreset,
  onGoToProductFlow,
  onClearProductContext,
  onResetForm
}) {
  const defaultPresets = [
    {
      id: 'gadget',
      name: 'อุปกรณ์ไอที',
      icon: Smartphone,
      data: {
        productName: 'Esseger สายชาร์จแม่เหล็ก',
        hookBrand: 'Esseger',
        hookModel: 'สายชาร์จแม่เหล็ก',
        hookLabel: 'ชาร์จไว ไม่ทำร้ายแบต',
        painPoint: 'สายชาร์จพังง่าย เสียบยากในที่มืด',
        priceDeal: 'ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง',
        keyFeatures: 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก'
      }
    },
    {
      id: 'home',
      name: 'ของใช้ในบ้าน',
      icon: Home,
      data: {
        productName: 'เครื่องดูดฝุ่นไร้สายมินิมอล',
        hookBrand: '',
        hookModel: 'เครื่องดูดฝุ่นไร้สาย',
        hookLabel: 'มินิมอล พลังดูดแรง',
        painPoint: 'ฝุ่นตามซอกทำความสะอาดยาก เครื่องใหญ่หนักมือ',
        priceDeal: 'ลด 50% วันนี้ ส่งฟรีถึงบ้าน',
        keyFeatures: 'พลังดูดแรงสูง ไร้สาย น้ำหนักเบา แบตอึด ดีไซน์สวยเข้ากับบ้าน'
      }
    },
    {
      id: 'beauty',
      name: 'สกินแคร์',
      icon: Sparkles,
      data: {
        productName: 'เซรั่มไฮยาหน้าฉ่ำโกลว์',
        hookBrand: '',
        hookModel: 'เซรั่มไฮยาลูรอน',
        hookLabel: 'หน้าฉ่ำโกลว์ ชุ่มชื้น 72 ชม.',
        painPoint: 'หน้าแห้ง แต่งหน้าไม่ติด ผิวโทรมดูหมองคล้ำ',
        priceDeal: 'โปร 1 แถม 1 จัดในตะกร้าด่วน',
        keyFeatures: 'ซึมไวไม่เหนียวเหนอะ ล็อคความชุ่มชื้น 72 ชม. หน้าฉ่ำใส รูขุมขนกระชับ'
      }
    },
    {
      id: 'flash_sale',
      name: 'Flash Sale',
      icon: Flame,
      data: {
        productName: 'พาวเวอร์แบงค์ชาร์จไว 20000mAh',
        hookBrand: '',
        hookModel: 'พาวเวอร์แบงค์ 20000mAh',
        hookLabel: 'ชาร์จเร็ว 22.5W',
        painPoint: 'แบตมือถือหมดระหว่างวัน พกพาวเวอร์แบงค์หนักๆ',
        priceDeal: 'Flash Sale 199.- วันนี้วันเดียวเท่านั้น',
        keyFeatures: 'บางเบาพกง่าย ชาร์จเร็ว 22.5W มีสายในตัวไม่ต้องพกสายเพิ่ม'
      }
    }
  ];

  // MODE A: An active product was imported from Menu 1 (ProductToClip)
  if (activeProductContext && activeProductContext.angles && activeProductContext.angles.length > 0) {
    const { title, angles } = activeProductContext;

    return (
      <div className="glass-panel p-3.5 sm:p-4 mb-3 space-y-3 animate-fadeIn">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center flex-shrink-0 text-white shadow-md">
              <ShoppingBag className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  ✓ โหลดจากเมนูที่ 1 แล้ว
                </span>
                <span className="text-xs text-slate-400 hidden sm:inline">
                  (เลือกสลับสคริปต์ได้ 4 สไตล์)
                </span>
              </div>
              <h4 className="text-xs sm:text-sm font-bold text-white font-kanit truncate max-w-xs sm:max-w-md md:max-w-xl mt-0.5">
                {title || 'สินค้าปัจจุบัน'}
              </h4>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onGoToProductFlow}
              className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>เปลี่ยนสินค้า / สแกนใหม่</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#25F4EE]" />
            </button>
            {onResetForm && (
              <button
                onClick={onResetForm}
                className="px-2.5 py-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1 border border-transparent hover:border-rose-500/20"
                title="รีเซ็ตฟอร์มทั้งหมดกลับเป็นค่าเริ่มต้น"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>รีเซ็ตฟอร์ม</span>
              </button>
            )}
            <button
              onClick={onClearProductContext}
              className="px-2.5 py-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.05] text-xs font-bold transition-colors cursor-pointer"
              title="ยกเลิกการผูกสินค้าปัจจุบัน"
            >
              ✕ ปิดสินค้านี้
            </button>
          </div>
        </div>

        {/* 4 Angle Pills Switcher */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-0.5">
          <span className="text-xs font-bold text-slate-400 flex-shrink-0 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-[#25F4EE]" />
            สลับมุมมอง:
          </span>

          {angles.map((ang, idx) => {
            const isSelected = selectedAngleIndex === idx;
            return (
              <button
                key={ang.angle_id || idx}
                onClick={() => onSelectAngle && onSelectAngle(idx)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs transition-all whitespace-nowrap cursor-pointer flex-shrink-0 font-bold ${
                  isSelected
                    ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] text-white shadow-lg shadow-[#FE2C55]/25 border border-transparent'
                    : 'bg-black/40 hover:bg-white/[0.05] text-slate-300 border border-white/[0.08]'
                }`}
              >
                {isSelected ? <Check className="w-3.5 h-3.5 text-white" /> : <span className="opacity-60">{idx + 1}.</span>}
                <span>{ang.angle_name || `มุมที่ ${idx + 1}`}</span>
                {ang.badge && (
                  <span className={`text-sm px-1.5 py-0.2 rounded-full font-bold ${
                    isSelected ? 'bg-black/30 text-white' : 'bg-[#25F4EE]/10 text-[#25F4EE]'
                  }`}>
                    {ang.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // MODE B: Default Quick Presets Bar
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
      {/* MODE B: Default Quick Demo Presets */}
      <div className="flex flex-wrap items-center gap-2 bg-black/40 p-2.5 rounded-2xl border border-white/[0.08] text-xs">
        <span className="font-bold text-slate-400 px-1 hidden sm:inline">
          พรีเซ็ตตัวอย่าง (คลิกเพื่อโหลดข้อมูลเร็ว):
        </span>
        <div className="w-px h-4 bg-white/[0.1] flex-shrink-0" />
        {defaultPresets.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.id}
              onClick={() => onSelectPreset(p.data)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-black/40 border border-white/[0.08] hover:bg-white/[0.08] hover:border-white/[0.2] text-slate-200 transition-all text-xs font-bold whitespace-nowrap flex-shrink-0 cursor-pointer group shadow-sm"
            >
              <Icon className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#25F4EE] transition-colors" />
              <span>{p.name}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        {onResetForm && (
          <button
            onClick={onResetForm}
            className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/30 border border-white/[0.08] text-slate-400 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap shadow-sm"
            title="รีเซ็ตฟอร์มและล้างข้อมูลทั้งหมดกลับเป็นค่าเริ่มต้น"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>รีเซ็ตฟอร์ม</span>
          </button>
        )}
        <button
          onClick={onGoToProductFlow}
          className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#25F4EE]/20 to-blue-500/20 hover:bg-[#25F4EE]/30 border border-[#25F4EE]/40 text-[#25F4EE] text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span>สแกนสินค้าใหม่ด้วย AI (เมนู 1)</span>
        </button>
      </div>
    </div>
  );
}
