import React from 'react';
import { Keyboard, Command, Sparkles } from 'lucide-react';
import { Modal, Badge } from './ui';

export default function ShortcutsModal({ isOpen, onClose }) {
  const shortcutGroups = [
    {
      category: 'การสลับแท็บเมนูหลัก (Navigation)',
      shortcuts: [
        { key: '1', desc: '1. สินค้า ➔ คลิป (AI Product-to-Clip)' },
        { key: '2', desc: '2. คลังสินค้า & แทร็กเกอร์ (Content Tracker)' },
        { key: '3', desc: '3. 1-Click Studio (สตูดิโอตัดต่อด่วน)' },
        { key: '4', desc: '4. ตัดต่อมือ & ซับไตเติล (Manual Editor + SRT)' },
        { key: '5', desc: '5. คลังคลิปตัดเสร็จ (Export Gallery)' },
        { key: '6', desc: '6. คลังทรัพยากร (System & Assets)' },
      ]
    },
    {
      category: 'การควบคุมมีเดีย & ระบบ (Player & Actions)',
      shortcuts: [
        { key: 'Space', desc: 'สลับ เล่น / หยุด วิดีโอพรีวิว (Play / Pause)' },
        { key: 'Esc', desc: 'ปิดหน้าต่างป๊อปอัป / Modal ทั้งหมด' },
        { key: 'Ctrl + S', desc: 'บันทึกสถานะโปรเจกต์ / ฟอร์ม (Auto-Save)' },
        { key: '?', desc: 'เปิด / ปิด หน้าต่างคีย์ลัดนี้' },
      ]
    }
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="คีย์ลัดด่วน (Keyboard Shortcuts)"
      subtitle="เพิ่มความเร็วในการตัดต่อคอนเทนต์ระดับ Power-User"
      maxWidth="max-w-xl"
    >
      <div className="space-y-5">
        {shortcutGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-2.5">
            <h4 className="text-xs font-bold font-kanit text-[#25F4EE] uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{group.category}</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {group.shortcuts.map((sc, sIdx) => (
                <div
                  key={sIdx}
                  className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-between gap-3 text-xs"
                >
                  <span className="text-slate-300 truncate font-medium">{sc.desc}</span>
                  <kbd className="px-2 py-1 rounded-lg bg-white/[0.08] border border-white/[0.15] text-[#25F4EE] font-mono font-bold text-[11px] shadow-inner flex-shrink-0 min-w-[28px] text-center">
                    {sc.key}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div className="p-3 rounded-2xl bg-gradient-to-r from-[#FE2C55]/10 to-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-between text-xs text-slate-300">
          <span>กด <kbd className="px-1.5 py-0.5 rounded bg-black/60 font-mono text-[#25F4EE] font-bold">?</kbd> บนคีย์บอร์ดเพื่อเปิดดูหน้านี้ได้ตลอดเวลา</span>
          <Badge variant="cyan" size="sm">
            Desktop Ready
          </Badge>
        </div>
      </div>
    </Modal>
  );
}
