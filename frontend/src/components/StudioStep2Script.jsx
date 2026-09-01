import React, { useState } from 'react';
import { Clock, Edit3, Copy, Check } from 'lucide-react';
import { Input, Textarea, Badge } from './ui';

export default function StudioStep2Script({
  productName, setProductName,
  hookTitle, setHookTitle,
  painPoint, setPainPoint,
  priceDeal, setPriceDeal,
  keyFeatures, setKeyFeatures,
  customScript, setCustomScript,
  useCustomScript, setUseCustomScript
}) {
  const [copiedAll, setCopiedAll] = useState(false);

  // Approximate duration calculation (Thai reading speed ~4-5 syllables per sec)
  const fullText = useCustomScript && customScript
    ? customScript
    : `${hookTitle || ''} ${productName || ''} ${painPoint || ''} ${keyFeatures || ''} ${priceDeal || ''}`;
  
  const charCount = fullText.replace(/\s+/g, '').length;
  const estimatedSeconds = Math.max(12, Math.round(charCount / 12));

  const previewLines = useCustomScript && customScript
    ? customScript.split('\n').filter(line => line.trim().length > 0)
    : [
        hookTitle || 'อย่าเพิ่งเลื่อนผ่าน!',
        `ใครเจอปัญหา ${painPoint || 'แบบนี้อยู่'} ต้องดูตัวนี้`,
        `${productName || 'สินค้าตัวนี้'} ${keyFeatures || 'คุณภาพดีมาก'}`,
        `${priceDeal || 'รีบกดในตะกร้าซ้ายล่างได้เลยครับ'}`
      ];

  const handleCopyAll = () => {
    const textToCopy = previewLines.join('\n');
    navigator.clipboard.writeText(textToCopy);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  return (
    <section className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-[#25F4EE] to-blue-500 flex items-center justify-center text-[12px] font-bold text-slate-950 shadow-md shadow-[#25F4EE]/20">
            2
          </span>
          <h3 className="text-sm font-bold text-white font-kanit">
            สคริปต์ & คำบรรยาย
          </h3>
        </div>

        {/* Estimated Duration Badge */}
        <Badge variant="cyan" size="sm" icon={Clock}>
          ~{estimatedSeconds}s (ความยาวแนะนำ)
        </Badge>
      </div>

      <div className="glass-card p-4 sm:p-5 space-y-4">
        {/* Row 1: Product Name & Hook Title */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <Input
            label="ชื่อสินค้า (Product Name)"
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="เช่น Esseger สายชาร์จแม่เหล็ก 3-in-1"
          />

          <Input
            label="พาดหัว Hook ดึงดูด (3 วินาทีแรก)"
            type="text"
            value={hookTitle}
            onChange={(e) => setHookTitle(e.target.value)}
            placeholder="เช่น อย่าเพิ่งเลื่อนผ่าน! สายชาร์จตัวจบ"
          />
        </div>

        {/* Row 2: Pain Point & Promo CTA */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <Input
            label="ปัญหาที่ลูกค้าเจอ (Pain Point)"
            type="text"
            value={painPoint}
            onChange={(e) => setPainPoint(e.target.value)}
            placeholder="เช่น สายชาร์จพังง่าย เสียบยากในที่มืด"
          />

          <Input
            label="โปรโมชั่น & Call-To-Action (CTA)"
            type="text"
            value={priceDeal}
            onChange={(e) => setPriceDeal(e.target.value)}
            placeholder="เช่น ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง"
          />
        </div>

        {/* Key Features */}
        <Textarea
          label="จุดเด่นและฟีเจอร์สำคัญ (Key Selling Points)"
          value={keyFeatures}
          onChange={(e) => setKeyFeatures(e.target.value)}
          rows={2}
          placeholder="เช่น แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก"
          className="resize-none"
        />

        {/* Pro Script Editor Toggle & View */}
        <div className="pt-3 border-t border-white/[0.08]">
          <div className="flex items-center justify-between">
            <label
              onClick={() => setUseCustomScript(!useCustomScript)}
              className="flex items-center gap-2.5 cursor-pointer select-none group"
            >
              <div className={`w-8 h-[18px] rounded-full transition-colors relative p-0.5 ${
                useCustomScript ? 'bg-[#25F4EE]' : 'bg-slate-700'
              }`}>
                <div className={`w-3.5 h-3.5 rounded-full bg-slate-950 transition-transform shadow-sm ${
                  useCustomScript ? 'translate-x-3.5' : 'translate-x-0'
                }`} />
              </div>
              <span className="text-xs font-bold text-slate-200 group-hover:text-white transition-colors flex items-center gap-1.5">
                <Edit3 className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>โหมดแก้ไขสคริปต์รายบรรทัด (1 บรรทัด = 1 ซับ)</span>
              </span>
            </label>

            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
              {useCustomScript ? 'กำลังใช้สคริปต์กำหนดเอง' : 'โหมดอัตโนมัติ'}
            </span>
          </div>

          {useCustomScript ? (
            <div className="mt-3 space-y-2 animate-fadeIn">
              <Textarea
                value={customScript}
                onChange={(e) => setCustomScript(e.target.value)}
                rows={6}
                placeholder={`1 บรรทัด = 1 ประโยคซับไตเติลบนจอ เช่น:\n${hookTitle || 'อย่าเพิ่งเลื่อนผ่าน!'}\n${productName || 'สายชาร์จแม่เหล็กตัวนี้คือที่สุด'}\n${keyFeatures || 'แม่เหล็กแรงดูดสูง เสียบปึ้งติดทันที'}\n${priceDeal || 'รีบกดในตะกร้าซ้ายล่างได้เลยครับ'}`}
                className="font-mono leading-relaxed"
              />
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span className="text-[#25F4EE]">แต่ละบรรทัดจะถูกแปลงเป็นเสียงพากย์และซับไตเติลพอดีคำ</span>
                <Badge variant="slate" size="sm">
                  {customScript ? customScript.split('\n').filter(Boolean).length : 0} ท่อนประโยค
                </Badge>
              </div>
            </div>
          ) : (
            previewLines.length > 0 && (
              <div className="mt-3 space-y-1.5 animate-fadeIn">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
                  <span>ตัวอย่างท่อนเสียงและซับไตเติล ({previewLines.length} ท่อน):</span>
                  <button
                    onClick={handleCopyAll}
                    className="text-[11px] font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    {copiedAll ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedAll ? 'คัดลอกแล้ว' : 'คัดลอกบททั้งหมด'}</span>
                  </button>
                </div>
                <div className="max-h-[140px] overflow-y-auto space-y-1.5 pr-1">
                  {previewLines.map((line, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-xl bg-black/40 border border-white/[0.05] text-xs text-slate-300 flex items-center gap-2 font-mono"
                    >
                      <span className="w-4 h-4 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] text-[10px] flex items-center justify-center flex-shrink-0 font-bold">
                        {idx + 1}
                      </span>
                      <span className="truncate">{line}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </section>
  );
}
