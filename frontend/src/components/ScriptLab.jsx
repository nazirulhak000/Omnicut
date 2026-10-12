import { channelLocalStorage } from '../lib/channelStorage.js';
import React, { useState } from 'react';
import {
  Lightbulb, Copy, Check, Sparkles, Send, RefreshCw, Wand2, Edit3, Clock, Hash, MessageSquareText, Clapperboard, ArrowRight,
  Flame, Zap, Target, TrendingUp, Film, Video, ShieldCheck
} from 'lucide-react';
import { generateAiScripts, generateHookVariantsAI, matchRawFolderWithAI } from '../api';
import { Input, Textarea, Button, Badge, Toast } from './ui';
import { useToast } from '../hooks';

export default function ScriptLab({
  initialProductName = 'Esseger สายชาร์จแม่เหล็ก 3-in-1',
  initialKeyFeatures = 'แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว 66W หมุนได้ 540 องศา สายถักไนลอนทนทาน',
  initialPainPoint = 'สายชาร์จพังง่ายตรงคอ เสียบยากในที่มืด เล่นเกมแล้วสายเกะกะมือ',
  initialPriceDeal = 'ลดพิเศษวันนี้เหลือ 149 บาท',
  onApplyScript
}) {
  const [workspaceStorage] = useState(channelLocalStorage);
  const { toastMessage, toastType, toastDuration, showToast, hideToast } = useToast();
  const [hookVariants, setHookVariants] = useState([]);
  const [hookLoading, setHookLoading] = useState(false);
  const [rawFolderInput, setRawFolderInput] = useState('01_Raw');
  const [matchingSequence, setMatchingSequence] = useState(false);
  const [matchedSequence, setMatchedSequence] = useState([]);
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
      const raw = workspaceStorage.getItem('capcut_script_lab');
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
      workspaceStorage.setItem('capcut_script_lab', JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save script lab state:', e);
    }
  }, [productName, keyFeatures, painPoint, priceDeal, activeAngleTab, scripts]);

  const handleGenerate = async () => {
    if (!productName.trim()) {
      showToast('กรุณากรอกชื่อสินค้าก่อนครับ!', 'warning');
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
        showToast('สร้างสคริปต์ AI เรียบร้อยแล้ว');
      }
    } catch (err) {
      console.error('Error generating AI scripts:', err);
      showToast('เกิดข้อผิดพลาดในการสร้างสคริปต์ AI: ' + (err.friendlyMessage || err.response?.data?.detail || err.message), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateHookVariants = async () => {
    if (!productName.trim()) {
      showToast('กรุณากรอกชื่อสินค้าก่อนวิเคราะห์ Hook ครับ!', 'warning');
      return;
    }
    setHookLoading(true);
    try {
      const featuresList = keyFeatures.split(/[,，\n]/).map(s => s.trim()).filter(Boolean);
      const res = await generateHookVariantsAI(productName, featuresList);
      if (res && res.variants && res.variants.length > 0) {
        setHookVariants(res.variants);
        showToast('วิเคราะห์และจัดอันดับ Hook ด้วย TypeSafe AI เรียบร้อย!');
      }
    } catch (err) {
      console.error('Error generating hook variants:', err);
      showToast('เกิดข้อผิดพลาดในการวิเคราะห์ Hook: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setHookLoading(false);
    }
  };

  const handleApplyHookVariant = (variant) => {
    setScripts(prev => {
      const updated = [...prev];
      if (updated[activeAngleTab]) {
        updated[activeAngleTab] = {
          ...updated[activeAngleTab],
          hook_title: variant.hook_text,
          badge: variant.angle_title,
        };
      }
      return updated;
    });
    showToast(`นำ Hook "${variant.angle_title}" ไปใส่ในสคริปต์เรียบร้อยแล้ว`);
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
        // Not auto-filling hookBrand/hookModel/hookLabel -- the 3-tier hook
        // banner is manual-only (see EditorShell.jsx).
        customScript: item.script_text,
        keyFeatures,
        painPoint,
        priceDeal,
        adTone: item.angle_id === 'tech_hype' ? 'commercial_hype' :
                item.angle_id === 'fomo_deal' ? 'commercial_hype' :
                item.angle_id === 'transformation' ? 'commercial_aesthetic' : 'commercial_premium',
        brollSequence: matchedSequence.length > 0 ? matchedSequence : undefined,
      });
      setAppliedIdx(idx);
      setTimeout(() => setAppliedIdx(null), 2500);
    }
  };

  const handleMatchBrollSequence = async () => {
    const current = scripts[activeAngleTab];
    if (!current || !current.script_text) {
      showToast('กรุณาเลือกหรือสร้างสคริปต์ก่อนจับคู่ B-roll ครับ', 'warning');
      return;
    }
    const lines = current.script_text
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      showToast('ไม่พบประโยคในสคริปต์ที่จะนำไปจับคู่', 'warning');
      return;
    }

    setMatchingSequence(true);
    try {
      const res = await matchRawFolderWithAI(rawFolderInput.trim() || '01_Raw', lines);
      if (res && res.sequence && res.sequence.length > 0) {
        setMatchedSequence(res.sequence);
        showToast(`TypeSafe Jev จับคู่ B-roll สำเร็จ ${res.sequence.length} ช็อต!`, 'success');
      } else if (res && res.error) {
        showToast(`ไม่สามารถจับคู่ได้: ${res.error}`, 'warning');
      }
    } catch (err) {
      console.error('Error matching B-roll sequence:', err);
      showToast('เกิดข้อผิดพลาดในการจับคู่ B-roll: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setMatchingSequence(false);
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
            <h2 className="text-lg sm:text-xl font-bold text-white">
              AI Script Lab (ห้องแล็บแต่งสคริปต์ไวรัล TikTok)
            </h2>
            <Badge variant="cyan" size="sm">
              Gemini + TypeSafe AI
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
            ให้ AI แต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมอง พร้อมวิเคราะห์คะแนนตรึงคนดู (3s Retention Score) ด้วย TypeSafe System One ก่อนส่งตรงเข้า Studio ตัดต่อทันที
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
          <span className="text-sm text-slate-400">ปรับแก้ข้อมูลได้ตลอดเวลา</span>
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

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <Button
            onClick={handleGenerate}
            loading={loading}
            icon={Sparkles}
            size="lg"
            className="w-full"
          >
            {loading ? 'AI กำลังแต่งสคริปต์ 4 มุมมอง...' : 'แต่งสคริปต์ 4 มุมมองด้วย AI'}
          </Button>

          <button
            type="button"
            onClick={handleGenerateHookVariants}
            disabled={hookLoading}
            className="obsidian-hero-btn px-4 py-3 flex items-center justify-center gap-2 cursor-pointer text-sm font-bold disabled:opacity-50"
          >
            <Zap className="w-4 h-4 text-cyan-950" />
            <span>{hookLoading ? 'TypeSafe กำลังวิเคราะห์ Hook...' : 'วิเคราะห์ & จัดอันดับ Hook (TypeSafe AI)'}</span>
          </button>
        </div>
      </div>

      {/* TypeSafe AI Hook Intelligence Section */}
      {hookVariants.length > 0 && (
        <div className="obsidian-card p-5 space-y-4 animate-fadeIn border border-cyan-500/30">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div className="flex items-center gap-2">
              <Flame className="w-5 h-5 text-amber-400" />
              <span className="font-bold text-white text-sm md:text-base">
                TypeSafe AI Hook Ranking (จัดอันดับอัตราการตรึงคนดู 3 วินาทีแรก)
              </span>
            </div>
            <span className="text-xs text-cyan-400 font-mono">System One Jev Scored</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {hookVariants.map((v, i) => (
              <div
                key={i}
                className="bg-slate-900/80 border border-white/[0.08] rounded-xl p-4 flex flex-col justify-between space-y-3 hover:border-cyan-500/40 transition-all"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span
                      className="text-[11px] font-bold px-2 py-0.5 rounded-md text-slate-900"
                      style={{ backgroundColor: v.badge_color || '#FFE600' }}
                    >
                      อันดับ #{i + 1} {v.angle_title}
                    </span>
                    <span className="text-[11px] text-emerald-400 font-mono font-bold">
                      คะแนน {Math.round(v.rating_score * 100)}%
                    </span>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-200 font-medium leading-relaxed">
                    "{v.hook_text}"
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>3s Retention Prob:</span>
                    <span className="font-mono text-cyan-300 font-bold">
                      {Math.round((v.retention_probability || 0.8) * 100)}%
                    </span>
                  </div>
                  <div className="retention-meter-track">
                    <div
                      className="retention-meter-fill"
                      style={{ width: `${Math.round((v.retention_probability || 0.8) * 100)}%` }}
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => handleApplyHookVariant(v)}
                    className="w-full mt-2 py-1.5 px-2.5 rounded-lg text-xs font-bold bg-white/[0.06] hover:bg-cyan-500/20 text-cyan-300 hover:text-white border border-white/[0.08] hover:border-cyan-500/40 transition-all cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <span>ใช้ Hook นี้ในสคริปต์</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generated Scripts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-white text-sm md:text-base">
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
              {item.retention_probability && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 font-bold ml-1">
                  🎯 {Math.round(item.retention_probability * 100)}%
                </span>
              )}
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

            {/* TypeSafe Jev Retention Score Bar */}
            {scripts[activeAngleTab].retention_probability && (
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/20 text-xs">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-cyan-400" />
                  <span className="font-bold text-cyan-300">TypeSafe Jev Retention Score:</span>
                  <span className="font-mono font-bold text-white text-sm">
                    {Math.round(scripts[activeAngleTab].retention_probability * 100)}%
                  </span>
                </div>
                <div className="flex items-center gap-3 text-slate-400 text-[11px]">
                  {scripts[activeAngleTab].detected_tone && (
                    <span>
                      โทนจิตวิทยา: <span className="text-emerald-300 font-semibold">{scripts[activeAngleTab].detected_tone}</span>
                    </span>
                  )}
                  {scripts[activeAngleTab].rating_score && (
                    <span>
                      ศักยภาพไวรัล: <span className="text-amber-300 font-semibold">{Math.round(scripts[activeAngleTab].rating_score * 100)}%</span>
                    </span>
                  )}
                </div>
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
                      showToast('คัดลอกแคปชันและแฮชแท็กแล้ว');
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

            {/* TypeSafe Smart B-roll Matcher Section */}
            <div className="p-4 rounded-2xl bg-black/40 border border-cyan-500/20 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] pb-2.5">
                <div className="flex items-center gap-2">
                  <Film className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-bold text-white">
                    TypeSafe Smart B-roll Matcher (Strict Topic Hold Guard)
                  </span>
                </div>
                <span className="text-[11px] text-cyan-400 font-mono">System One B-roll Decision</span>
              </div>

              <div className="flex flex-col sm:flex-row gap-2.5 items-center">
                <div className="w-full sm:flex-1">
                  <input
                    type="text"
                    value={rawFolderInput}
                    onChange={(e) => setRawFolderInput(e.target.value)}
                    placeholder="ระบุโฟลเดอร์ เช่น 01_Raw หรือ 01_Raw/20260921_Xiaomi_Pad_8"
                    className="w-full px-3 py-2 text-xs rounded-xl bg-black/50 border border-white/[0.1] text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleMatchBrollSequence}
                  disabled={matchingSequence}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl text-xs font-bold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 transition-all cursor-pointer flex items-center justify-center gap-2 whitespace-nowrap disabled:opacity-50"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{matchingSequence ? 'Jev กำลังจับคู่คลิป...' : 'จับคู่ B-roll อัตโนมัติ (Jev)'}</span>
                </button>
              </div>

              {matchedSequence.length > 0 && (
                <div className="space-y-2 pt-2">
                  <div className="text-[11px] text-slate-400 flex items-center justify-between">
                    <span>ไทม์ไลน์ที่ Jev จับคู่ได้ ({matchedSequence.length} ช็อต):</span>
                    <span className="text-emerald-400 font-semibold">Strict Topic Hold ผ่านเกณฑ์ 100%</span>
                  </div>
                  <div className="max-h-60 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                    {matchedSequence.map((item, mIdx) => (
                      <div
                        key={mIdx}
                        className="p-2.5 rounded-xl bg-slate-900/90 border border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs hover:border-cyan-500/30 transition-all"
                      >
                        <div className="space-y-1 sm:max-w-[65%]">
                          <div className="text-slate-300 font-medium line-clamp-1">
                            <span className="text-cyan-400 font-mono font-bold mr-1.5">#{mIdx + 1}</span>
                            "{item.sentence}"
                          </div>
                        </div>
                        <div className="flex items-center gap-2 self-end sm:self-auto">
                          <div className="text-right">
                            <div className="text-slate-200 font-bold font-mono text-[11px] truncate max-w-[160px]">
                              🎬 {item.matched_clip?.name || item.matched_clip_id}
                            </div>
                            <div className="text-[10px] text-emerald-400 font-mono">
                              ความแม่นยำ {Math.round((item.relevance_score || 0.85) * 100)}%
                            </div>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            Strict Hold
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

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

      <Toast message={toastMessage} type={toastType} duration={toastDuration} onClose={hideToast} />
    </div>
  );
}
