import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles, Play, Video, ExternalLink, RefreshCw, Clock,
  Flame, Swords, MessageSquare, BarChart3, CheckCircle2,
  AlertCircle, Film, Plus, Send, Download, Info, X, ChevronRight,
  Volume2, Music, Check, ArrowRight
} from 'lucide-react';
import {
  getHyperFramesStatus,
  getHyperFramesStyles,
  getHyperFramesCompositions,
  createHyperFramesClip,
  renderHyperFramesComposition,
  openHyperFramesStudio,
  getProducts
} from '../../api';
import StylePosterMockup from './StylePosterMockup';

// ── Rich Editorial Metas for the 4 Approved Styles ──
const STYLE_EXTRAS = {
  vs_battle: {
    accentBorder: 'hover:border-rose-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(244,63,94,0.18)]',
    tagColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) + Upbeat BGM (0.14) + SFX ชก/ดาบ',
    rhythm: [
      { time: '0-3s', label: 'เปิดศึก VS', desc: 'ตัดภาพแบ่ง 2 ฝั่ง ซาวด์เปิดศึก', color: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
      { time: '3-10s', label: 'ยก 1: สปีด', desc: 'ชาร์จเทียบกัน HP บาร์ฝั่งเก่าลด', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
      { time: '10-17s', label: 'ยก 2: อุณหภูมิ', desc: 'วัดความร้อน 58°C vs 34°C', color: 'bg-red-500/20 text-red-300 border-red-500/30' },
      { time: '17-22s', label: 'ยก 3: ราคา', desc: 'เทียบราคาโปรโมชั่นหลักร้อย', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
      { time: '22-25s', label: 'K.O. ตะกร้า', desc: 'K.O. จบศึก ปักตะกร้าเหลือง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  tech_explainer: {
    accentBorder: 'hover:border-cyan-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(6,182,212,0.18)]',
    tagColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) สุขุม + Ambient Tech BGM (0.12)',
    rhythm: [
      { time: '0-4s', label: 'ตั้งคำถาม', desc: 'เปิดข้อสงสัย ทำไมหัวชาร์จแรงไม่ร้อน', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
      { time: '4-15s', label: 'ผ่าโครงสร้าง', desc: 'Exploded View ชิป GaN III', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
      { time: '15-28s', label: 'เจาะสเปก', desc: 'เกจวัตต์และระบบระบายความร้อน', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
      { time: '28-35s', label: 'เทสจริง', desc: 'เสียบชาร์จจริง กราฟนิ่งอุณหภูมิต่ำ', color: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
      { time: '35-40s', label: 'สรุปคุ้มค่า', desc: 'เหมาะกับคนใช้หลายอุปกรณ์ ปักตะกร้า', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  meme_pas: {
    accentBorder: 'hover:border-amber-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(245,158,11,0.18)]',
    tagColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) + มีม SFX แตรลม/Vine Boom + BGM (0.14)',
    rhythm: [
      { time: '0-4s', label: 'ฮุกปัญหาจริง', desc: 'ค่าไฟพุ่ง ปรอทแตก เตือนแล้วนะ', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
      { time: '4-10s', label: 'มีมตกใจ + Pause', desc: 'มีมเหงื่อตก ค้าง 0.8s ดึงสายตา', color: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
      { time: '10-14s', label: 'หักมุมแตรลม', desc: 'ซาวด์แตรลมเปิดตัวสินค้าแก้ปัญหา', color: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
      { time: '14-38s', label: 'จุดขายคู่มีม', desc: 'ฟีเจอร์เด่น สลับ 1 มีม 1 SFX', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
      { time: '38-45s', label: 'ปักตะกร้าเหลือง', desc: 'CTA ชี้ตะกร้าเหลืองซ้ายล่าง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  pov_chat: {
    accentBorder: 'hover:border-emerald-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(16,185,129,0.18)]',
    tagColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    audioDetail: 'ไม่มีเสียงพากย์ (ดนตรีสดใส + Sound Effect แชท LINE เด้ง)',
    rhythm: [
      { time: '0-4s', label: 'แชทเด้งเตือน', desc: 'เสียงแชท LINE แฟนบ่นร้อน/แบตหมด', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
      { time: '4-12s', label: 'บทสนทนาดราม่า', desc: 'คนดูอ่านตาม 100% สลับพิมพ์ตอบ', color: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
      { time: '12-20s', label: 'ส่งของแก้ปัญหา', desc: 'ส่งรูป/ลิงก์แกดเจ็ตตัวช่วยเข้าแชท', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
      { time: '20-25s', label: 'แฟนปลื้มรอดตาย', desc: 'ตอบกลับว่ารอดแล้ว แบตเต็ม/เย็นเจี๊ยบ', color: 'bg-green-500/20 text-green-300 border-green-500/30' },
      { time: '25-28s', label: 'แจกพิกัดในแชท', desc: 'ส่งสติกเกอร์ชี้ตะกร้าเหลืองซ้ายล่าง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  }
};

export default function HyperFramesHub({ onNavigateToGallery }) {
  const [activeTab, setActiveTab] = useState('styles'); // 'styles' | 'compositions' | 'create'
  const [status, setStatus] = useState(null);
  const [styles, setStyles] = useState([]);
  const [compositions, setCompositions] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [selectedStyleDetail, setSelectedStyleDetail] = useState(null); // Modal state for style deep dive

  // Form State for creating a new clip
  const [newClipId, setNewClipId] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('meme_pas');
  const [scriptText, setScriptText] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Render state tracking
  const [renderingCompId, setRenderingCompId] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setRefreshing(true);
      setActionError(null);
      const [statusRes, stylesRes, compsRes, prodsRes] = await Promise.all([
        getHyperFramesStatus().catch(() => null),
        getHyperFramesStyles().catch(() => []),
        getHyperFramesCompositions().catch(() => []),
        getProducts().catch(() => ({ products: [] }))
      ]);
      setStatus(statusRes);
      setStyles(Array.isArray(stylesRes) ? stylesRes : (stylesRes?.styles || []));
      setCompositions(Array.isArray(compsRes) ? compsRes : (compsRes?.compositions || []));
      const prodsList = Array.isArray(prodsRes) ? prodsRes : (prodsRes?.products || []);
      setProducts(prodsList);
      if (prodsList.length > 0 && !selectedProduct) {
        const first = prodsList[0];
        const initialVal = (first.id || first.code || first.product_code || 'hat01').toLowerCase();
        setSelectedProduct(initialVal);
      }
    } catch (err) {
      setActionError('ไม่สามารถโหลดข้อมูล HyperFrames ได้ กรุณาลองใหม่อีกครั้ง');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedProduct]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenStudio = () => {
    setActionSuccess('กำลังเปิด HyperFrames Studio ในแท็บใหม่...');
    openHyperFramesStudio(3002).catch(() => {});
    setTimeout(() => setActionSuccess(null), 4000);
  };

  const handleCreateClip = async (e) => {
    e.preventDefault();
    if (!newClipId.trim()) {
      setActionError('กรุณาระบุรหัสคลิป (เช่น hat01-review-30s)');
      return;
    }
    try {
      setIsCreating(true);
      setActionError(null);
      setActionSuccess(null);
      const res = await createHyperFramesClip({
        clip_id: newClipId.trim(),
        product: selectedProduct.toLowerCase(),
        script: scriptText.trim() || undefined,
        style: selectedStyle
      });
      setActionSuccess(`สร้างดราฟต์สำเร็จ: ${res.clip_id} เปิดแต่งต่อใน Compositions ได้ทันที`);
      setNewClipId('');
      setScriptText('');
      await loadData();
      setActiveTab('compositions');
    } catch (err) {
      setActionError('สร้างคลิปไม่สำเร็จ: ' + (err.friendlyMessage || err.message));
    } finally {
      setIsCreating(false);
    }
  };

  const handleRenderComposition = async (comp, isTest = false) => {
    try {
      setRenderingCompId(comp.id);
      setActionError(null);
      setActionSuccess(`กำลังเรนเดอร์ ${comp.id} ผ่าน Chrome Headless (ประมาณ 1-2 นาที)...`);
      const res = await renderHyperFramesComposition({
        composition_id: comp.id,
        product_id: comp.product?.toUpperCase(),
        is_test: isTest
      });
      if (isTest) {
        setActionSuccess(`เรนเดอร์ทดสอบสำเร็จในโฟลเดอร์ชั่วคราว: ${res.output_path}`);
      } else {
        setActionSuccess(`เรนเดอร์และลงทะเบียนสำเร็จ! บันทึกลง Export Gallery เรียบร้อย`);
        if (onNavigateToGallery) {
          setTimeout(() => onNavigateToGallery(), 2500);
        }
      }
    } catch (err) {
      setActionError('การเรนเดอร์ล้มเหลว: ' + (err.friendlyMessage || err.message));
    } finally {
      setRenderingCompId(null);
    }
  };

  const getStyleIcon = (styleId) => {
    switch (styleId) {
      case 'meme_pas': return <Flame className="w-5 h-5 text-amber-400" />;
      case 'tech_explainer': return <BarChart3 className="w-5 h-5 text-cyan-400" />;
      case 'vs_battle': return <Swords className="w-5 h-5 text-rose-400" />;
      case 'pov_chat': return <MessageSquare className="w-5 h-5 text-emerald-400" />;
      default: return <Sparkles className="w-5 h-5 text-indigo-400" />;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* ── Header & Status Bar ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-rose-500/20 border border-indigo-500/30">
              <Sparkles className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                HyperFrames Creative Studio
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-medium">
                  Web-Animation 9:16
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                สตูดิโอผลิตคลิปแนวตั้งอัตโนมัติด้วย Web Animation และ 4 สไตล์ไวรัลคุณภาพสูง (เหมือนคนตัด ไม่ใช่ AI)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Health Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <span className={`w-2 h-2 rounded-full ${status?.ready ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span>{status?.ready ? `Engine v${status.hyperframes_version} พร้อมใช้งาน` : 'กำลังตรวจสอบเอนจิน...'}</span>
          </div>

          <a
            href="http://127.0.0.1:3002/#project/_HyperFrames_Studio"
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleOpenStudio}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-sm"
          >
            <ExternalLink className="w-4 h-4" />
            เปิด HyperFrames Studio
          </a>

          <button
            type="button"
            onClick={loadData}
            disabled={refreshing}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-colors"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Toast Messages ── */}
      {actionError && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-sm animate-in fade-in">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span className="flex-1">{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}
      {actionSuccess && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-200 text-sm animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="flex-1">{actionSuccess}</span>
          <button type="button" onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* ── Tab Switcher ── */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('styles')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'styles'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Flame className="w-4 h-4" />
          4 สไตล์ที่อนุมัติ (Approved Styles)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('compositions')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'compositions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Film className="w-4 h-4" />
          คลังคลิป Compositions ({compositions.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('create')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'create'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Plus className="w-4 h-4" />
          เริ่มคลิปดราฟต์ใหม่
        </button>
      </div>

      {/* ── Content: Tab 1 (Approved Styles) ── */}
      {activeTab === 'styles' && (
        <div className="space-y-5">
          {/* Channel Golden Rule Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-indigo-950/40 border border-slate-800/90 text-sm text-slate-300 flex items-start gap-3 shadow-md">
            <span className="text-xl">⭐</span>
            <div>
              <span className="font-semibold text-white">กฎเหล็ก 4 สไตล์ไวรัลคุณภาพสูง:</span> ทุกสไตล์คราฟต์ภายใต้แนวคิด
              <span className="text-amber-400 font-medium"> "เหมือนคนตัด ไม่ใช่ AI ตัด"</span> — ห้ามใช้การ์ดมืดๆ ห้าม pill สีฟ้า ห้ามพื้นหลังดำโล่ง และห้ามไอคอนเวกเตอร์วาดเอง ใช้ฉลากจริง วิดีโอจริง มีมจริง จังหวะ Meme Pause 0.8s และ HUD เกมต่อสู้แบบมีชีวิต
            </div>
          </div>

          {/* 4 Approved Styles Showcase Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {(Array.isArray(styles) ? styles : []).map((st) => {
              const extras = STYLE_EXTRAS[st.id] || {
                accentBorder: 'hover:border-slate-700',
                accentShadow: '',
                tagColor: 'bg-slate-800 text-slate-300 border-slate-700',
                audioDetail: st.has_voiceover ? 'มีเสียงพากย์ Fenrir (1.0)' : 'ดนตรีล้วน',
                rhythm: []
              };

              return (
                <div
                  key={st.id}
                  className={`p-5 rounded-2xl bg-slate-900/90 border border-slate-800/80 transition-all duration-300 flex flex-col sm:flex-row gap-5 shadow-lg group ${extras.accentBorder} ${extras.accentShadow}`}
                >
                  {/* Left Column: 9:16 Visual Poster Frame */}
                  <div className="w-full sm:w-44 md:w-48 shrink-0 flex flex-col items-center gap-2">
                    <StylePosterMockup
                      styleId={st.id}
                      onPreviewClick={() => setSelectedStyleDetail(st)}
                    />
                    <button
                      type="button"
                      onClick={() => setSelectedStyleDetail(st)}
                      className="text-[11px] text-slate-400 hover:text-indigo-300 font-medium transition-colors"
                    >
                      เปิดดูตัวอย่างและโครงสร้าง
                    </button>
                  </div>

                  {/* Right Column: Editorial Intelligence & Rhythm */}
                  <div className="flex-1 flex flex-col justify-between space-y-3.5 min-w-0">
                    <div className="space-y-3">
                      {/* Header: Title + Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-lg bg-slate-800/90 border border-slate-700/60 shrink-0">
                            {getStyleIcon(st.id)}
                          </div>
                          <div>
                            <h3 className="font-semibold text-white text-base tracking-tight">{st.name}</h3>
                            <p className="text-xs text-slate-400">{st.tagline}</p>
                          </div>
                        </div>
                        <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium shrink-0 ${extras.tagColor}`}>
                          {st.badge}
                        </span>
                      </div>

                      {/* Visual Beat-by-Beat Timeline Rhythm */}
                      <div className="space-y-1.5">
                        <span className="text-[11px] text-slate-400 font-medium block">
                          สูตรจังหวะการตัด (Beat-by-Beat Timeline):
                        </span>
                        <div className="flex flex-wrap items-center gap-1.5 py-1">
                          {extras.rhythm.map((step, idx) => (
                            <React.Fragment key={idx}>
                              <span
                                className={`px-2 py-0.5 rounded-md text-[11px] font-mono border font-medium cursor-help transition-transform hover:scale-105 ${step.color}`}
                                title={step.desc}
                              >
                                {step.time} {step.label}
                              </span>
                              {idx < extras.rhythm.length - 1 && (
                                <span className="text-slate-600 text-xs">➔</span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>

                      {/* Formula Detail Summary */}
                      <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/60 text-xs text-slate-300 leading-relaxed">
                        {st.formula}
                      </div>

                      {/* Specs DNA Bar */}
                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                        <div>
                          <span className="text-slate-500">ความยาว:</span> ~{st.recommended_duration_sec} วินาที
                        </div>
                        <div className="truncate" title={extras.audioDetail}>
                          <span className="text-slate-500">ระบบเสียง:</span> {st.has_voiceover ? 'พากย์ Fenrir (1.0)' : 'ดนตรีล้วน'}
                        </div>
                        <div className="col-span-2 truncate">
                          <span className="text-slate-500">คลิปตัวอย่าง:</span>{' '}
                          <span className="text-indigo-400 font-mono text-[11px]">{st.reference}</span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                      <span className="text-xs text-emerald-400 font-medium truncate" title={st.pros}>
                        {st.pros}
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => setSelectedStyleDetail(st)}
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition-colors"
                        >
                          ดูรายละเอียด
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedStyle(st.id);
                            setActiveTab('create');
                          }}
                          className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-sm transition-colors"
                        >
                          เลือกใช้สไตล์นี้
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Content: Tab 2 (Compositions Gallery) ── */}
      {activeTab === 'compositions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              พบ {(Array.isArray(compositions) ? compositions : []).length} รายการในสตูดิโอ (จัดเก็บที่ <code className="text-slate-300">03_Projects/_HyperFrames_Studio/compositions/</code>)
            </p>
            <a
              href="http://127.0.0.1:3002/#project/_HyperFrames_Studio"
              target="_blank"
              rel="noopener noreferrer"
              onClick={handleOpenStudio}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
            >
              เปิดหน้าต่าง HyperFrames Studio Live Preview ↗
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(Array.isArray(compositions) ? compositions : []).map((comp) => {
              const isRendering = renderingCompId === comp.id;
              return (
                <div
                  key={comp.id}
                  className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-white text-sm truncate" title={comp.id}>
                        {comp.id}
                      </h3>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {comp.duration}s
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 truncate">
                      สินค้า: <span className="text-slate-300 uppercase font-medium">{comp.product}</span>
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-slate-500">
                      <span>อัปเดต: {comp.updated_at?.split('T')[0]}</span>
                      {comp.has_vo && <span className="text-indigo-400">• มีเสียงพากย์</span>}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleRenderComposition(comp, false)}
                      disabled={isRendering}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-medium text-white transition-colors"
                    >
                      {isRendering ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          กำลังเรนเดอร์...
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          เรนเดอร์ Final (MP4)
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => handleRenderComposition(comp, true)}
                      disabled={isRendering}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs text-slate-300 transition-colors"
                      title="เรนเดอร์ทดสอบลง .tmp/"
                    >
                      เทส
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Content: Tab 3 (Create New Clip Draft) ── */}
      {activeTab === 'create' && (
        <div className="max-w-2xl bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Plus className="w-5 h-5 text-indigo-400" />
              สร้างดราฟต์คลิป HyperFrames ใหม่
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              ระบบจะเชื่อมต่อ Faster-Whisper สกัด Timestamps คำต่อคำ และสร้างไฟล์โครงสร้าง Composition พร้อมโมชั่นอัตโนมัติ
            </p>
          </div>

          <form onSubmit={handleCreateClip} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                รหัสคลิป (Clip ID) *
              </label>
              <input
                type="text"
                value={newClipId}
                onChange={(e) => setNewClipId(e.target.value)}
                placeholder="เช่น hat01-review-30s หรือ ess02-trick-21s"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:border-indigo-500 focus:outline-none"
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  สินค้าเป้าหมาย *
                </label>
                <select
                  value={selectedProduct}
                  onChange={(e) => setSelectedProduct(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="hat01">HAT01 (Hatari T16M1)</option>
                  <option value="ess02">ESS02 (Essager 30W/65W)</option>
                  <option value="goc01">GOC01 (Gocomma Fan)</option>
                  {(Array.isArray(products) ? products : []).map((p) => {
                    const code = (p.id || p.code || p.product_code || '').toLowerCase();
                    if (!code || ['hat01', 'ess02', 'goc01'].includes(code)) return null;
                    const displayName = p.name || p.title || p.product_name || code.toUpperCase();
                    return (
                      <option key={p.id || p.code || code} value={code}>
                        {code.toUpperCase()} ({displayName})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  สไตล์ที่ต้องการ
                </label>
                <select
                  value={selectedStyle}
                  onChange={(e) => setSelectedStyle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="meme_pas">Meme-PAS (รีวิวสายมีม)</option>
                  <option value="tech_explainer">Tech Explainer (สาย Vox)</option>
                  <option value="vs_battle">VS Battle (สายเกมต่อสู้)</option>
                  <option value="pov_chat">POV Chat Story (ไม่มีเสียงพากย์)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                บทสคริปต์ (Script Prompt สำหรับ Whisper)
              </label>
              <textarea
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                placeholder="วางบทสคริปต์ภาษาไทยที่นี่ เพื่อช่วยให้ Whisper สะกดคำไทยและคำเฉพาะได้อย่างแม่นยำ 100%..."
                rows={4}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:border-indigo-500 focus:outline-none resize-none"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={isCreating}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-colors shadow-sm"
              >
                {isCreating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    กำลังประมวลผล Whisper...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    สร้างดราฟต์คลิป
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Style Detail & Breakdown Modal ── */}
      {selectedStyleDetail && (() => {
        const modalExtras = STYLE_EXTRAS[selectedStyleDetail.id] || {
          tagColor: 'bg-slate-800 text-slate-300 border-slate-700',
          audioDetail: selectedStyleDetail.has_voiceover ? 'มีเสียงพากย์ Fenrir (1.0)' : 'ดนตรีล้วน',
          rhythm: []
        };

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl p-6 flex flex-col md:flex-row gap-6">
              {/* Close Button */}
              <button
                type="button"
                onClick={() => setSelectedStyleDetail(null)}
                className="absolute top-4 right-4 p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                title="ปิดหน้าต่าง"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Left Column: 9:16 Mockup Frame */}
              <div className="w-full md:w-64 shrink-0 flex flex-col items-center gap-3">
                <StylePosterMockup styleId={selectedStyleDetail.id} />
                <span className="text-xs text-slate-400 font-mono">
                  ภาพจำลองหน้าปก & HUD 9:16
                </span>
              </div>

              {/* Right Column: Editorial Intelligence */}
              <div className="flex-1 flex flex-col justify-between space-y-4">
                <div className="space-y-4">
                  {/* Title & Badge */}
                  <div className="flex items-start justify-between gap-3 pr-8">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        {getStyleIcon(selectedStyleDetail.id)}
                        <h2 className="text-xl font-bold text-white tracking-tight">
                          {selectedStyleDetail.name}
                        </h2>
                      </div>
                      <p className="text-sm text-slate-400">
                        {selectedStyleDetail.tagline}
                      </p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-full border font-medium shrink-0 ${modalExtras.tagColor}`}>
                      {selectedStyleDetail.badge}
                    </span>
                  </div>

                  {/* Beat-by-Beat Timeline Breakdown */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-400" />
                      สูตรจังหวะการตัดไทม์ไลน์ (Rhythm Blueprint):
                    </h4>
                    <div className="space-y-1.5 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                      {modalExtras.rhythm.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-2.5 text-xs">
                          <span className={`px-2 py-0.5 rounded font-mono font-medium text-[11px] shrink-0 border ${step.color}`}>
                            {step.time}
                          </span>
                          <div>
                            <span className="font-semibold text-white">{step.label}: </span>
                            <span className="text-slate-300">{step.desc}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Formula Description */}
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      แนวทางการเล่าเรื่อง (Narrative Formula):
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                      {selectedStyleDetail.formula}
                    </p>
                  </div>

                  {/* Technical DNA & Guidelines */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                    <div>
                      <span className="text-slate-500 block mb-0.5">ความยาวที่แนะนำ:</span>
                      <span className="font-semibold text-white font-mono">
                        ~{selectedStyleDetail.recommended_duration_sec} วินาที
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-0.5">ระบบเสียง & พากย์:</span>
                      <span className="font-semibold text-indigo-300">
                        {modalExtras.audioDetail}
                      </span>
                    </div>
                    <div className="sm:col-span-2">
                      <span className="text-slate-500 block mb-0.5">คลิปต้นแบบอ้างอิง:</span>
                      <span className="text-slate-200 font-mono text-[11px]">
                        {selectedStyleDetail.reference}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Modal Footer Actions */}
                <div className="pt-4 border-t border-slate-800/80 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedStyle(selectedStyleDetail.id);
                      setSelectedStyleDetail(null);
                      setActiveTab('create');
                    }}
                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-colors shadow-md text-center"
                  >
                    เลือกใช้สไตล์นี้เพื่อเริ่มดราฟต์
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedStyleDetail(null)}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition-colors"
                  >
                    ปิดหน้าต่าง
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
