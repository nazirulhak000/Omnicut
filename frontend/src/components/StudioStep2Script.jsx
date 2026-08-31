import React, { useState, useEffect } from 'react';
import { PenTool, Sparkles, Volume2, Sliders, Check } from 'lucide-react';
import { generateScript } from '../api';

export default function StudioStep2Script({
  productName,
  setProductName,
  hookTitle,
  setHookTitle,
  painPoint,
  setPainPoint,
  priceDeal,
  setPriceDeal,
  keyFeatures,
  setKeyFeatures,
  customScript,
  setCustomScript,
  useCustomScript,
  setUseCustomScript
}) {
  const [previewLines, setPreviewLines] = useState([]);

  // Auto-generate preview lines when inputs change
  useEffect(() => {
    if (!useCustomScript && productName) {
      generateScript({
        product_name: productName,
        key_features: keyFeatures,
        pain_point: painPoint,
        price_deal: priceDeal,
      }).then(res => {
        if (res.script?.lines) {
          setPreviewLines(res.script.lines);
        }
      }).catch(() => {});
    }
  }, [productName, keyFeatures, painPoint, priceDeal, useCustomScript]);

  return (
    <div className="glass-card p-5 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs font-black tracking-wider text-white uppercase rounded-full bg-gradient-to-r from-[#FE2C55] to-[#FF0050] shadow-md shadow-[#FE2C55]/30">
            STEP 2
          </span>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <PenTool className="w-5 h-5 text-[#25F4EE]" />
            สคริปต์รีวิว & การป้ายยา (Copywriting)
          </h2>
        </div>
      </div>

      <div className="space-y-4">
        {/* Row 1: Product Name & Hook Title */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              📦 ชื่อสินค้า:
            </label>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="เช่น Esseger สายชาร์จแม่เหล็ก"
              className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55] transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              🔥 พาดหัว Hook ด้านบนจอ:
            </label>
            <input
              type="text"
              value={hookTitle}
              onChange={(e) => setHookTitle(e.target.value)}
              placeholder="เช่น 🔥 อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก"
              className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55] transition-colors"
            />
          </div>
        </div>

        {/* Row 2: Pain Point & Deal */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              😫 ปัญหาของคนดู (Pain Point):
            </label>
            <input
              type="text"
              value={painPoint}
              onChange={(e) => setPainPoint(e.target.value)}
              placeholder="เช่น สายชาร์จพังง่าย เสียบยากในที่มืด"
              className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55] transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              🏷️ โปรโมชั่น / CTA (Deal):
            </label>
            <input
              type="text"
              value={priceDeal}
              onChange={(e) => setPriceDeal(e.target.value)}
              placeholder="เช่น ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง"
              className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55] transition-colors"
            />
          </div>
        </div>

        {/* Row 3: Key Features */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            ✨ จุดเด่นสินค้า (Key Features):
          </label>
          <textarea
            value={keyFeatures}
            onChange={(e) => setKeyFeatures(e.target.value)}
            rows={2}
            placeholder="เช่น แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก"
            className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55] transition-colors"
          />
        </div>

        {/* Pro Editor Toggle */}
        <div className="pt-2 border-t border-white/5">
          <label className="flex items-center gap-2.5 cursor-pointer text-xs font-semibold text-slate-300 select-none">
            <input
              type="checkbox"
              checked={useCustomScript}
              onChange={(e) => setUseCustomScript(e.target.checked)}
              className="w-4 h-4 rounded text-[#FE2C55] bg-slate-900 border-white/20 focus:ring-0"
            />
            <span className="flex items-center gap-1.5 text-slate-200">
              <Sliders className="w-3.5 h-3.5 text-[#25F4EE]" />
              เปิดโหมดปรับแต่งสคริปต์ละเอียดรายบรรทัด (Pro Script Editor)
            </span>
          </label>

          {useCustomScript ? (
            <div className="mt-3">
              <textarea
                value={customScript}
                onChange={(e) => setCustomScript(e.target.value)}
                rows={5}
                placeholder={`1 บรรทัด = 1 ท่อนซับ + ซอยคัตภาพ 1 ช็อต\n${hookTitle}\n${productName} ตัวเดียวจบ\n${keyFeatures}\n${priceDeal}`}
                className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-[#25F4EE]/30 text-slate-100 text-sm font-mono focus:outline-none focus:border-[#25F4EE] transition-colors"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                💡 คำแนะนำ: แต่ละบรรทัดควรมีความยาวสั้นๆ 1-2 วินาทีเพื่อให้จังหวะคลิปเร็วและน่าติดตาม
              </p>
            </div>
          ) : (
            /* Live Script Breakdown Preview */
            previewLines.length > 0 && (
              <div className="mt-3 space-y-2">
                <div className="text-xs font-semibold text-slate-400">
                  👀 ตัวอย่างสคริปต์อัตโนมัติ & ไทม์ไลน์ SFX ({previewLines.length} ท่อน):
                </div>
                <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
                  {previewLines.map((line, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2.5 p-2 rounded-lg bg-black/40 border border-white/5 text-xs"
                    >
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#232A3B] text-[#25F4EE] border border-[#25F4EE]/30">
                        🔊 {(line.sfx || 'pop').toUpperCase()}
                      </span>
                      <span className="text-slate-200 truncate">{line.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
