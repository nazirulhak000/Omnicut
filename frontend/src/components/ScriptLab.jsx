import React, { useState } from 'react';
import {
  Lightbulb, Copy, Check, Sparkles, Send, RefreshCw, Wand2, Edit3, Clock, Hash, MessageSquareText, Clapperboard, ArrowRight
} from 'lucide-react';
import { generateAiScripts } from '../api';
import { Input, Textarea, Button, Badge } from './ui';

export default function ScriptLab({
  initialProductName = 'Esseger สายชาร์จแม่เหล็ก 3-in-1',
  initialKeyFeatures = 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว 66W หมุนได้ 540 องศา สายถักไนลอนทนทาน',
  initialPainPoint = 'สายชาร์จพังง่ายตรงคอ เสียบยากในที่มืด เล่นเกมแล้วสายเกะกะมือ',
  initialPriceDeal = 'ลดพิเศษวันนี้เหลือ 149 บาท',
  onApplyScript
}) {
  const defaultScripts = [
    {
      angle_id: 'pain_point',
      angle_name: 'เตือนภัย / จี้จุดเจ็บ (Stop Scroll)',
      badge: 'แก้ปัญหา',
      hook_title: 'ถ้ายังไม่เห็นสิ่งนี้ อย่าเพิ่งซื้อสายชาร์จธรรมดา!',
      estimated_sec: 28,
      script_text: `ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
ใครที่เบื่อกับสายชาร์จพังตรงคอ เสียบยากในที่มืด บอกเลยว่าตัวนี้จบ
Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!`,
      caption: 'สายชาร์จพังบ่อย เสียบยาก เล่นเกมเกะกะ? จบทุกปัญหาด้วย Esseger!',
      hashtags: ['#สายชาร์จพังบ่อย', '#สายชาร์จแม่เหล็ก', '#esseger', '#ของดีบอกต่อ', '#tiktokshop']
    },
    {
      angle_id: 'tech_hype',
      angle_name: 'โชว์ฟังก์ชันสุดล้ำ / ว้าว (Tech Hype)',
      badge: 'ไวรัล TikTok',
      hook_title: 'นี่แหละ สายชาร์จแห่งอนาคต! หมุน 540 องศา!',
      estimated_sec: 29,
      script_text: `ทุกคนดูนี่! ทำไมคนใน TikTok สั่งสายชาร์จตัวนี้กันเยอะมาก?!
นี่คือ Esseger สายชาร์จแม่เหล็ก 3-in-1 แค่เอาเข้าใกล้ก็ดูดปึ้ก
ข้อต่อหมุนได้ 540 องศารอบทิศ จะนอนเล่นเกมหรือดูหนังก็ไม่เกะกะมือ
ชาร์จไวถึง 66W วัสดุสายถักไนลอนแข็งแรงทนทานสุดๆ
คุ้มขนาดนี้วันนี้แค่ 149 บาท พิกัดในตะกร้าซ้ายล่าง กดสั่งตรงนี้ได้เลยครับ!`,
      caption: 'ล้ำไปอีกขั้น! สายชาร์จแม่เหล็ก 540 องศา ชาร์จไว 66W! ต้องมี!',
      hashtags: ['#สายชาร์จสุดล้ำ', '#เทคโนโลยีใหม่', '#esseger', '#ของมันต้องมี', '#tiktokshop']
    },
    {
      angle_id: 'fomo_deal',
      angle_name: 'โปรเดือด / ความคุ้มค่า (FOMO & Deal)',
      badge: 'Flash Sale',
      hook_title: 'โปรนี้หมดแล้วหมดเลย! สายชาร์จเทพแค่ 149 บาท!',
      estimated_sec: 28,
      script_text: `ทุกคน! รีบเลยครับ ใครกำลังหาสายชาร์จเทพๆ ราคาคุ้มๆ ต้องโปรนี้เลย
Esseger สายชาร์จแม่เหล็ก 3-in-1 จัดโปรพิเศษวันนี้แค่ 149 บาทเท่านั้น
ได้ทั้งหัวแม่เหล็กดูดแน่น หมุนได้ 540 องศา ชาร์จไว 66W สายถักพรีเมียม
ของดีมีจำนวนจำกัดนะครับ รีบกดใส่ตะกร้าซ้ายล่างด่วนเลยก่อนหมดโปร!`,
      caption: 'โปรเดือด! Esseger สายชาร์จแม่เหล็ก 3-in-1 แค่ 149 บาท! ของมีจำกัดนะ!',
      hashtags: ['#โปรโมชั่น', '#ราคาถูกและดี', '#คุ้มค่า', '#esseger', '#ลดราคา']
    },
    {
      angle_id: 'transformation',
      angle_name: 'ชีวิตดีขึ้น / เปรียบเทียบ (Transformation)',
      badge: 'รีวิวเจาะลึก',
      hook_title: 'เลิกใช้แบบเดิมๆ! พอเปลี่ยนมาใช้ตัวนี้ชีวิตดีขึ้นเยอะ!',
      estimated_sec: 29,
      script_text: `ชีวิตผมเปลี่ยนไปเยอะมากครับ! จากเมื่อก่อนที่ต้องทนกับสายชาร์จพังง่ายๆ
พอเปลี่ยนมาใช้ Esseger สายชาร์จแม่เหล็ก 3-in-1 ตัวนี้คือจบเลยครับ
เสียบง่ายในที่มืด หมุนได้ 540 องศา นอนเล่นเกมสบายมือ ชาร์จไว 66W
ใครอยากชีวิตดีขึ้นแบบผม กดเลยครับ 149 บาท ในตะกร้าซ้ายล่าง!`,
      caption: 'ก่อนมี vsหลังมี Esseger! ชีวิตดีขึ้นเยอะจริงๆ! #รีวิวชีวิตจริง',
      hashtags: ['#ชีวิตดีขึ้น', '#รีวิวชีวิตจริง', '#สายชาร์จแม่เหล็ก', '#tiktokshop']
    }
  ];

  const savedLab = (() => {
    try {
      const raw = localStorage.getItem('capcut_script_lab');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  const [productName, setProductName] = useState(() => savedLab?.productName || initialProductName);
  const [keyFeatures, setKeyFeatures] = useState(() => savedLab?.keyFeatures || initialKeyFeatures);
  const [painPoint, setPainPoint] = useState(() => savedLab?.painPoint || initialPainPoint);
  const [priceDeal, setPriceDeal] = useState(() => savedLab?.priceDeal || initialPriceDeal);

  const [loading, setLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [appliedIdx, setAppliedIdx] = useState(null);
  const [activeAngleTab, setActiveAngleTab] = useState(() => savedLab?.activeAngleTab || 0);

  const [scripts, setScripts] = useState(() => (savedLab?.scripts && savedLab.scripts.length > 0) ? savedLab.scripts : defaultScripts);

  // Auto-save ScriptLab state to localStorage
  React.useEffect(() => {
    try {
      const data = {
        productName,
        keyFeatures,
        painPoint,
        priceDeal,
        activeAngleTab,
        scripts
      };
      localStorage.setItem('capcut_script_lab', JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save script lab state:', e);
    }
  }, [productName, keyFeatures, painPoint, priceDeal, activeAngleTab, scripts]);

  const handleGenerate = async () => {
    if (!productName.trim()) {
      alert('กรุณากรอกชื่อสินค้าก่อนครับ!');
      return;
    }
    setLoading(true);
    try {
      const res = await generateAiScripts({
        product_name: productName,
        key_features: keyFeatures,
        pain_point: painPoint,
        price_deal: priceDeal
      });
      if (res && res.angles && res.angles.length > 0) {
        setScripts(res.angles);
        setActiveAngleTab(0);
      }
    } catch (err) {
      console.error('Error generating AI scripts:', err);
      alert('เกิดข้อผิดพลาดในการสร้างสคริปต์ AI: ' + (err.friendlyMessage || err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCopyScript = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleApplyToStudio = (item, idx) => {
    if (onApplyScript) {
      onApplyScript({
        productName,
        hookTitle: item.hook_title,
        customScript: item.script_text,
        keyFeatures,
        painPoint,
        priceDeal,
        adTone: item.angle_id === 'tech_hype' ? 'commercial_hype' :
                item.angle_id === 'fomo_deal' ? 'commercial_hype' :
                item.angle_id === 'transformation' ? 'commercial_aesthetic' : 'commercial_premium'
      });
      setAppliedIdx(idx);
      setTimeout(() => setAppliedIdx(null), 2500);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Top Banner */}
      <div className="glass-panel p-5 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-md flex-shrink-0">
              <Wand2 className="w-5 h-5" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold font-kanit text-white">
              AI Script Lab (ห้องแล็บแต่งสคริปต์ไวรัล TikTok)
            </h2>
            <Badge variant="cyan" size="sm">
              Gemini 2.5 Engine
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
            ให้ AI แต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมองจิตวิทยาการขาย (Hook ➔ Pain Point ➔ Feature ➔ Benefit ➔ CTA) พร้อมกดส่งตรงเข้า Studio เพื่อตัดต่อทันที
          </p>
        </div>
      </div>

      {/* Product Input Card */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <div className="flex items-center gap-2 font-bold text-white text-sm">
            <Sparkles className="w-4 h-4 text-[#25F4EE]" />
            <span>1. ระบุข้อมูลสินค้าเพื่อแต่งบทรีวิว</span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">ปรับแก้ข้อมูลได้ตลอดเวลา</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="ชื่อสินค้า (Product Name)"
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="เช่น Esseger สายชาร์จแม่เหล็ก 3-in-1"
          />

          <Input
            label="ราคา / โปรโมชั่น (Price & Deal)"
            type="text"
            value={priceDeal}
            onChange={(e) => setPriceDeal(e.target.value)}
            placeholder="เช่น ลดพิเศษวันนี้เหลือ 149 บาท จิ้มตะกร้าซ้ายล่าง"
          />

          <Textarea
            label="จุดเด่น / สเปกสำคัญ (Key Features)"
            rows={2}
            value={keyFeatures}
            onChange={(e) => setKeyFeatures(e.target.value)}
            placeholder="เช่น แม่เหล็กแรงดูดสูง หมุนได้ 540 องศา ชาร์จเร็ว 66W สายถักทนทาน"
            className="resize-none"
          />

          <Textarea
            label="ปัญหาที่แก้ / Pain Point (ที่คนเจอจริง)"
            rows={2}
            value={painPoint}
            onChange={(e) => setPainPoint(e.target.value)}
            placeholder="เช่น สายชาร์จพังง่าย เสียบยากในที่มืด เล่นเกมแล้วสายเกะกะมือ"
            className="resize-none"
          />
        </div>

        {/* Action Button */}
        <Button
          onClick={handleGenerate}
          loading={loading}
          icon={Sparkles}
          size="lg"
          className="w-full"
        >
          {loading ? 'AI กำลังแต่งสคริปต์ 4 มุมมอง...' : 'แต่งสคริปต์ 4 มุมมองด้วย AI'}
        </Button>
      </div>

      {/* Generated Scripts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-white text-sm md:text-base font-kanit">
            <MessageSquareText className="w-5 h-5 text-[#25F4EE]" />
            <span>2. สคริปต์ที่ AI แต่งให้ (เลือกสไตล์ที่ชอบไปใช้ตัดต่อได้เลย):</span>
          </div>
        </div>

        {/* Angle Tabs */}
        <div className="flex flex-wrap gap-2 pb-1">
          {scripts.map((item, idx) => (
            <button
              key={idx}
              onClick={() => setActiveAngleTab(idx)}
              className={`px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm flex items-center gap-2 transition-all cursor-pointer border ${
                activeAngleTab === idx
                  ? 'bg-gradient-to-r from-[#FE2C55]/20 to-[#25F4EE]/20 text-white border-[#25F4EE]/40 shadow-md shadow-[#25F4EE]/10'
                  : 'bg-white/[0.03] text-slate-400 border-white/[0.06] hover:border-white/[0.12] hover:text-white'
              }`}
            >
              <span>{item.angle_name}</span>
            </button>
          ))}
        </div>

        {/* Active Script Card Display */}
        {scripts[activeAngleTab] && (
          <div className="glass-card p-5 md:p-6 space-y-5 animate-fadeIn">
            {/* Header & Meta */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/[0.08]">
              <div className="flex items-center gap-2.5">
                <Badge variant="cyan">
                  {scripts[activeAngleTab].badge || scripts[activeAngleTab].angle_name}
                </Badge>
                <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                  <Clock className="w-3.5 h-3.5 text-[#25F4EE]" />
                  ความยาวคลิปประมาณ ~{scripts[activeAngleTab].estimated_sec || 28} วินาที
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={() => handleCopyScript(scripts[activeAngleTab].script_text, activeAngleTab)}
                  variant="secondary"
                  size="sm"
                  icon={copiedIdx === activeAngleTab ? Check : Copy}
                >
                  {copiedIdx === activeAngleTab ? 'คัดลอกบทแล้ว' : 'คัดลอกบท'}
                </Button>
              </div>
            </div>

            {/* Hook 3s Highlight Banner */}
            {scripts[activeAngleTab].hook_title && (
              <div className="p-3.5 rounded-2xl bg-black/50 border-l-4 border-[#25F4EE] text-sm md:text-base font-bold text-cyan-200 leading-snug">
                {scripts[activeAngleTab].hook_title}
              </div>
            )}

            {/* Full Script Body */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300">
                เนื้อหาสคริปต์พากย์เสียง (Voiceover Script):
              </label>
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.06] text-xs sm:text-sm text-slate-200 font-mono whitespace-pre-line leading-relaxed select-all">
                {scripts[activeAngleTab].script_text}
              </div>
            </div>

            {/* Ready-to-use Caption & Hashtags */}
            {(scripts[activeAngleTab].caption || scripts[activeAngleTab].hashtags) && (
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.06] space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>แคปชัน & แฮชแท็กสำหรับโพสต์ TikTok:</span>
                  </span>
                  <button
                    onClick={() => {
                      const text = `${scripts[activeAngleTab].caption || ''}\n\n${(scripts[activeAngleTab].hashtags || []).join(' ')}`;
                      navigator.clipboard.writeText(text);
                      alert('คัดลอกแคปชันและแฮชแท็กแล้ว');
                    }}
                    className="text-[#25F4EE] hover:underline text-xs cursor-pointer font-semibold"
                  >
                    คัดลอกทั้งหมด
                  </button>
                </div>
                <div className="text-xs text-slate-300 font-mono select-all bg-black/30 p-2.5 rounded-xl border border-white/[0.04]">
                  {scripts[activeAngleTab].caption}
                  <div className="mt-1.5 text-[#25F4EE] font-semibold">
                    {(scripts[activeAngleTab].hashtags || []).join(' ')}
                  </div>
                </div>
              </div>
            )}

            {/* Direct 1-Click Apply to Studio */}
            <div className="pt-2">
              <Button
                onClick={() => handleApplyToStudio(scripts[activeAngleTab], activeAngleTab)}
                variant="tiktok"
                size="lg"
                icon={appliedIdx === activeAngleTab ? Check : Clapperboard}
                iconRight={appliedIdx === activeAngleTab ? null : ArrowRight}
                className="w-full"
              >
                {appliedIdx === activeAngleTab ? 'ส่งข้อมูลเข้า Studio เรียบร้อยแล้ว' : 'ส่งสคริปต์นี้เข้า 1-Click Studio'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
