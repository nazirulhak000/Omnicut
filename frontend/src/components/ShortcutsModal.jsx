import React from 'react';
import { Sparkles } from 'lucide-react';
import { Modal, Badge } from './ui';
import { SHORTCUT_GROUPS } from '../lib/editorShortcutKeys.js';

export default function ShortcutsModal({ isOpen, onClose }) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="คีย์ลัดด่วน"
      subtitle="เพิ่มความเร็วในการตัดต่อคอนเทนต์ระดับ Power-User"
      maxWidth="max-w-xl"
    >
      <div className="space-y-5">
        {SHORTCUT_GROUPS.map((group, gIdx) => (
          <div key={gIdx} className="space-y-2.5">
            <h4 className="text-xs font-bold text-[#25F4EE] uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{group.category}</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {group.shortcuts.map((sc, sIdx) => (
                <div
                  key={sIdx}
                  className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-between gap-3 text-xs"
                >
                  <span className="text-slate-300 truncate font-medium" title={sc.desc}>{sc.desc}</span>
                  <kbd className="px-2 py-1 rounded-lg bg-white/[0.08] border border-white/[0.15] text-[#25F4EE] font-mono font-bold text-sm shadow-inner flex-shrink-0 min-w-[28px] text-center">
                    {sc.keys}
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
