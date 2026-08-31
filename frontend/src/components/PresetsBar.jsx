import React from 'react';
import { Smartphone, Home, Sparkles, Flame } from 'lucide-react';

export default function PresetsBar({ onSelectPreset }) {
  const presets = [
    {
      id: 'gadget',
      name: 'อุปกรณ์ไอที / แกดเจ็ต',
      icon: Smartphone,
      color: 'from-blue-600/20 to-cyan-600/20 border-cyan-500/30 text-cyan-300',
      data: {
        productName: 'Esseger สายชาร์จแม่เหล็ก',
        hookTitle: '🔥 อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก',
        painPoint: 'สายชาร์จพังง่าย เสียบยากในที่มืด',
        priceDeal: 'ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง',
        keyFeatures: 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก'
      }
    },
    {
      id: 'home',
      name: 'ของใช้ในบ้าน / มินิมอล',
      icon: Home,
      color: 'from-amber-600/20 to-orange-600/20 border-orange-500/30 text-orange-300',
      data: {
        productName: 'เครื่องดูดฝุ่นไร้สายมินิมอล',
        hookTitle: '🏠 ของใช้ในบ้านที่ต้องมี! เครื่องดูดฝุ่นไร้สาย',
        painPoint: 'ฝุ่นตามซอกทำความสะอาดยาก เครื่องใหญ่หนักมือ',
        priceDeal: 'ลด 50% วันนี้ ส่งฟรีถึงบ้าน',
        keyFeatures: 'พลังดูดแรงสูง ไร้สาย น้ำหนักเบา แบตอึด ดีไซน์สวยเข้ากับบ้าน'
      }
    },
    {
      id: 'beauty',
      name: 'สกินแคร์ / ความงาม',
      icon: Sparkles,
      color: 'from-pink-600/20 to-rose-600/20 border-pink-500/30 text-pink-300',
      data: {
        productName: 'เซรั่มไฮยาหน้าฉ่ำโกลว์',
        hookTitle: '✨ กู้ผิวโทรมด่วน! เซรั่มหน้าฉ่ำโกลว์',
        painPoint: 'หน้าแห้ง แต่งหน้าไม่ติด ผิวโทรมดูหมองคล้ำ',
        priceDeal: 'โปร 1 แถม 1 จัดในตะกร้าด่วน',
        keyFeatures: 'ซึมไวไม่เหนียวเหนอะ ล็อคความชุ่มชื้น 72 ชม. หน้าฉ่ำใส รูขุมขนกระชับ'
      }
    },
    {
      id: 'flash_sale',
      name: 'Flash Sale / ลดแหลก',
      icon: Flame,
      color: 'from-red-600/20 to-rose-600/20 border-red-500/30 text-red-300',
      data: {
        productName: 'พาวเวอร์แบงค์ชาร์จไว 20000mAh',
        hookTitle: '⚡ Flash Sale วันเดียว! พาวเวอร์แบงค์ชาร์จไว',
        painPoint: 'แบตมือถือหมดระหว่างวัน พกพาวเวอร์แบงค์หนักๆ',
        priceDeal: 'Flash Sale 199.- วันนี้วันเดียวเท่านั้น',
        keyFeatures: 'บางเบาพกง่าย ชาร์จเร็ว 22.5W มีสายในตัวไม่ต้องพกสายเพิ่ม'
      }
    }
  ];

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2.5">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-prompt">
          ⚡ Quick Presets (เลือกหมวดหมู่สินค้าเพื่อกรอกข้อมูลด่วน)
        </h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {presets.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.id}
              onClick={() => onSelectPreset(p.data)}
              className={`flex items-center gap-2.5 p-3 rounded-xl border bg-gradient-to-r ${p.color} hover:scale-[1.02] active:scale-[0.98] transition-all text-left group`}
            >
              <div className="p-2 rounded-lg bg-black/30 group-hover:bg-black/50 transition-colors">
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-bold text-white leading-tight">{p.name}</div>
                <div className="text-[11px] opacity-70 truncate max-w-[120px]">{p.data.productName}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
