import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles, Play, Video, ExternalLink, RefreshCw, Clock,
  Flame, Swords, MessageSquare, BarChart3, CheckCircle2,
  AlertCircle, Film, Plus, Send, Download
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
        getProducts().catch(() => [])
      ]);
      setStatus(statusRes);
      setStyles(stylesRes);
      setCompositions(compsRes);
      setProducts(prodsRes);
      if (prodsRes.length > 0 && !selectedProduct) {
        setSelectedProduct(prodsRes[0].id || prodsRes[0].code || 'hat01');
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

  const handleOpenStudio = async () => {
    try {
      setActionError(null);
      setActionSuccess('กำลังเปิด HyperFrames Studio บนเบราว์เซอร์...');
      await openHyperFramesStudio(3100);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err) {
      setActionError('ไม่สามารถเปิด Studio ได้: ' + (err.friendlyMessage || err.message));
    }
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

          <button
            type="button"
            onClick={handleOpenStudio}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-sm"
          >
            <ExternalLink className="w-4 h-4" />
            เปิด HyperFrames Studio
          </button>

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
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-sm text-slate-300">
            <span className="font-semibold text-white">⭐ กฎเหล็กของช่อง:</span> วิดีโอทุกสไตล์ถูกคราฟต์ภายใต้แนวคิด
            <span className="text-amber-400 font-medium"> "เหมือนคนตัด ไม่ใช่ AI ตัด"</span> ห้ามใช้การ์ดมืดๆ, ห้าม pill ฟ้า,
            ห้ามพื้นหลังสีดำโล่ง และห้ามไอคอนเวกเตอร์วาดเอง — ใช้ฉลากจริง มีมจริง Motion มีฟิสิกส์หลอดแตก และจังหวะ Meme Pause
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {styles.map((st) => (
              <div
                key={st.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60">
                        {getStyleIcon(st.id)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-white text-base">{st.name}</h3>
                        <p className="text-xs text-slate-400">{st.tagline}</p>
                      </div>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      {st.badge}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs text-slate-300 leading-relaxed">
                    <span className="text-slate-400 font-medium block mb-1">สูตรจังหวะการตัด:</span>
                    {st.formula}
                  </div>

                  <div className="text-xs text-slate-400 space-y-1">
                    <div>
                      <span className="text-slate-500">คลิปตัวอย่างอ้างอิง:</span>{' '}
                      <span className="text-indigo-400 font-mono">{st.reference}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">ความยาวที่เหมาะสม:</span> ~{st.recommended_duration_sec} วินาที
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-xs text-emerald-400">{st.pros}</span>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedStyle(st.id);
                      setActiveTab('create');
                    }}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
                  >
                    ใช้สไตล์นี้
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Content: Tab 2 (Compositions Gallery) ── */}
      {activeTab === 'compositions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              พบ {compositions.length} รายการในสตูดิโอ (จัดเก็บที่ <code className="text-slate-300">03_Projects/_HyperFrames_Studio/compositions/</code>)
            </p>
            <button
              type="button"
              onClick={handleOpenStudio}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
            >
              เปิดหน้าต่าง HyperFrames Studio Live Preview ↗
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {compositions.map((comp) => {
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
                  {products.map((p) => (
                    <option key={p.id || p.code} value={(p.id || p.code).toLowerCase()}>
                      {p.name ? `${p.id || p.code} - ${p.name}` : (p.id || p.code)}
                    </option>
                  ))}
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
    </div>
  );
}
