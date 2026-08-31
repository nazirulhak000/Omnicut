import React, { useState } from 'react';
import { Lightbulb, Copy, Check, Sparkles, Flame, ShieldAlert, ArrowRight } from 'lucide-react';

export default function ScriptLab({ onApplyHook }) {
  const [copiedIdx, setCopiedIdx] = useState(null);

  const hookFormulas = [
    {
      category: '🚫 เตือนห้ามซื้อ (Stop Scroll)',
      hook: 'อย่าเพิ่งซื้อ {product_name} ถ้าคุณยังไม่รู้สิ่งนี้!',
      desc: 'สร้างความสงสัยและหยุดคนดูทันทีด้วยคำเตือนและข้อควรระวัง',
      color: 'border-red-500/30 bg-red-500/10 text-red-300'
    },
    {
      category: '😫 จี้ Pain Point (Direct Problem)',
      hook: 'ใครที่กำลังเจอปัญหา {pain_point} ดูคลิปนี้ด่วน!',
      desc: 'คัดกรองกลุ่มเป้าหมายที่มีปัญหาโดยตรง ให้รู้สึกว่าคลิปนี้ทำมาเพื่อเขา',
      color: 'border-amber-500/30 bg-amber-500/10 text-amber-300'
    },
    {
      category: '👀 ความลับ / ของแปลก (Social Proof)',
      hook: 'ทุกคนดูนี่! ทำไมคนใน TikTok สั่ง {product_name} ตัวนี้กันเยอะมาก?!',
      desc: 'ใช้พลัง Social Proof กระตุ้นความอยากรู้ว่าทำไมถึงฮิต',
      color: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300'
    },
    {
      category: '⚡ เปรียบเทียบชีวิตเปลี่ยน (Transformation)',
      hook: 'เลิกใช้แบบเดิมๆ ได้แล้ว! พอเปลี่ยนมาใช้ {product_name} ชีวิตดีขึ้นเยอะ',
      desc: 'กระตุ้นให้เกิดการเปรียบเทียบและการตัดสินใจอัปเกรด',
      color: 'border-blue-500/30 bg-blue-500/10 text-blue-300'
    },
    {
      category: '🔥 โปรด่วนจำกัดเวลา (FOMO / Deal)',
      hook: 'ราคาหลุดหรือเปล่าไม่รู้ แต่ตอนนี้ {product_name} จัดโปร {price_deal} จิ้มด่วน!',
      desc: 'สร้างความเร่งด่วน (FOMO) กระตุ้นให้รีบกดซื้อทันทีก่อนหมดโปร',
      color: 'border-purple-500/30 bg-purple-500/10 text-purple-300'
    }
  ];

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="p-5 glass-panel">
        <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
          <Lightbulb className="w-5 h-5 text-[#25F4EE]" />
          คลังไอเดีย & สูตร Hook ไวรัลสไตล์ TikTok
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          สูตรประโยคเปิดคลิป 3 วินาทีแรกที่หยุดนิ้วคนดูได้ผลดีที่สุด สามารถคัดลอกหรือส่งไปใช้ในสตูดิโอได้ทันที
        </p>
      </div>

      {/* Formula Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {hookFormulas.map((formula, idx) => (
          <div key={idx} className="glass-card p-5 space-y-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${formula.color}`}>
                  {formula.category}
                </span>
                <span className="text-[11px] text-slate-400">สูตร #{idx + 1}</span>
              </div>

              <p className="text-sm font-bold text-white font-prompt leading-relaxed mt-2">
                "{formula.hook}"
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {formula.desc}
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-white/5">
              <button
                onClick={() => handleCopy(formula.hook, idx)}
                className="flex-1 py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center justify-center gap-1.5 transition-colors"
              >
                {copiedIdx === idx ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    คัดลอกแล้ว!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    คัดลอกสูตร
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
