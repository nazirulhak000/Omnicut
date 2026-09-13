import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Sparkles, Flame, CheckCircle2, Clock, Play, ArrowRight,
  TrendingUp, AlertTriangle, Lightbulb, Target, Settings,
  Copy, Check, Plus, Trash2, Video, Film, Eye, Share2, ThumbsUp,
  RefreshCw, Clapperboard, ChevronRight, Zap, Scissors
} from 'lucide-react';
import { getProducts, getExports, getTiktokStatsLatest } from '../../api';
import {
  loadTargets,
  saveTargets,
  loadPlaybookNotes,
  savePlaybookNotes,
  calculateProductionStats,
  getDailyActionQueue,
  generateBossGreeting,
  analyzeContentPerformance,
  DEFAULT_TARGETS,
} from '../../lib/producerInsights';

export default function ProducerHub({
  onApplyToStudio,
  onGoToEditor,
  onGoToGallery,
  onGoToFlow,
  onGoToTracker,
  onRefreshAll,
}) {
  const [products, setProducts] = useState([]);
  const [exportsList, setExportsList] = useState([]);
  const [tiktokStats, setTiktokStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Targets state
  const [targets, setTargets] = useState(() => loadTargets());
  const [showTargetsModal, setShowTargetsModal] = useState(false);
  const [editingTargets, setEditingTargets] = useState({ ...targets });

  // Playbook Notes state
  const [playbookNotes, setPlaybookNotes] = useState(() => loadPlaybookNotes());
  const [newNoteText, setNewNoteText] = useState('');
  const [newNoteTag, setNewNoteTag] = useState('Hook');

  // Queue filter
  const [queueFilter, setQueueFilter] = useState('all'); // 'all' | 'post' | 'cut' | 'footage'

  // Clipboard copy state
  const [copiedId, setCopiedId] = useState(null);

  // Load data from APIs
  const fetchData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [prodRes, expRes, statsRes] = await Promise.allSettled([
        getProducts(),
        getExports(),
        getTiktokStatsLatest(),
      ]);

      if (prodRes.status === 'fulfilled') {
        const prodData = prodRes.value;
        setProducts(Array.isArray(prodData) ? prodData : (prodData?.products || []));
      }

      if (expRes.status === 'fulfilled') {
        const expData = expRes.value;
        setExportsList(Array.isArray(expData) ? expData : (expData?.exports || []));
      }

      if (statsRes.status === 'fulfilled') {
        setTiktokStats(statsRes.value);
      }
    } catch (err) {
      console.error('Failed to load producer hub data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Calculations
  const stats = useMemo(() => {
    return calculateProductionStats(products, exportsList, targets);
  }, [products, exportsList, targets]);

  const actionQueue = useMemo(() => {
    return getDailyActionQueue(products, exportsList);
  }, [products, exportsList]);

  const bossGreeting = useMemo(() => {
    return generateBossGreeting({ stats, actionQueue });
  }, [stats, actionQueue]);

  const retrospective = useMemo(() => {
    return analyzeContentPerformance(tiktokStats, products);
  }, [tiktokStats, products]);

  // Handle Save Targets
  const handleSaveTargets = () => {
    const validated = {
      dailyCuts: Math.max(1, Number(editingTargets.dailyCuts) || DEFAULT_TARGETS.dailyCuts),
      weeklyCuts: Math.max(1, Number(editingTargets.weeklyCuts) || DEFAULT_TARGETS.weeklyCuts),
      dailyPosts: Math.max(1, Number(editingTargets.dailyPosts) || DEFAULT_TARGETS.dailyPosts),
    };
    setTargets(validated);
    saveTargets(validated);
    setShowTargetsModal(false);
  };

  // Handle Add Playbook Note
  const handleAddNote = (e) => {
    e.preventDefault();
    if (!newNoteText.trim()) return;
    const newNote = {
      id: `note-${Date.now()}`,
      text: newNoteText.trim(),
      createdAt: new Date().toISOString(),
      tag: newNoteTag,
    };
    const updated = [newNote, ...playbookNotes];
    setPlaybookNotes(updated);
    savePlaybookNotes(updated);
    setNewNoteText('');
  };

  // Handle Delete Playbook Note
  const handleDeleteNote = (id) => {
    const updated = playbookNotes.filter(n => n.id !== id);
    setPlaybookNotes(updated);
    savePlaybookNotes(updated);
  };

  // Handle Copy Caption
  const handleCopyCaption = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filtered queue items
  const displayQueue = useMemo(() => {
    if (queueFilter === 'post') return actionQueue.readyToPost;
    if (queueFilter === 'cut') return actionQueue.readyToCut;
    if (queueFilter === 'footage') return actionQueue.needsFootage;
    return [
      ...actionQueue.readyToPost.map(i => ({ ...i, queueCategory: 'post' })),
      ...actionQueue.readyToCut.map(i => ({ ...i, queueCategory: 'cut' })),
      ...actionQueue.needsFootage.map(i => ({ ...i, queueCategory: 'footage' })),
    ];
  }, [actionQueue, queueFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px] text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin text-amber-500 mr-2" />
        <span>กำลังเตรียมข้อมูลศูนย์บัญชาการโปรดิวเซอร์...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* ── 1. Boss Greeting Banner ── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-amber-950/40 border border-amber-500/20 p-6 md:p-8 shadow-2xl backdrop-blur-xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 -mb-16 w-48 h-48 bg-orange-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-slate-950 font-black shadow-lg shadow-amber-500/25 flex-shrink-0 mt-1">
              <Sparkles className="w-7 h-7 text-slate-950" />
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-gradient-to-r ${bossGreeting.badgeColor} text-white shadow-sm`}>
                  {bossGreeting.badge}
                </span>
                <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  สัปดาห์นี้เป้า {targets.weeklyCuts} คลิป
                </span>
              </div>

              <h1 className="text-xl md:text-2xl font-black text-white tracking-tight">
                {bossGreeting.title}
              </h1>

              <p className="text-sm md:text-base text-slate-300 max-w-3xl leading-relaxed">
                {bossGreeting.message}
              </p>
            </div>
          </div>

          {/* Quick Action & Settings Button */}
          <div className="flex items-center gap-2.5 self-start md:self-auto flex-shrink-0">
            <button
              onClick={() => {
                if (bossGreeting.actionTab === 'post') onGoToGallery?.();
                else if (bossGreeting.actionTab === 'cut') onGoToEditor?.();
                else if (bossGreeting.actionTab === 'gallery') onGoToGallery?.();
                else onGoToFlow?.();
              }}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-amber-500/20 cursor-pointer transition-all"
            >
              <span>{bossGreeting.actionPrompt}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                setEditingTargets({ ...targets });
                setShowTargetsModal(true);
              }}
              className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white cursor-pointer transition-all"
              title="ตั้งค่าเป้าหมายการผลิต (Quota)"
            >
              <Settings className="w-5 h-5" />
            </button>

            <button
              onClick={fetchData}
              disabled={refreshing}
              className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white cursor-pointer transition-all disabled:opacity-50"
              title="รีเฟรชข้อมูล"
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin text-amber-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* ── 2. Production Quota Gauges (KPI Cards) ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Weekly Quota Card */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-5 shadow-lg backdrop-blur-md relative overflow-hidden group hover:border-amber-500/30 transition-all">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold">
              <Target className="w-4 h-4 text-amber-400" />
              <span>เป้าหมายสัปดาห์นี้</span>
            </div>
            <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
              {stats.weeklyCuts.pct}%
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-black text-white">{stats.weeklyCuts.current}</span>
            <span className="text-slate-400 text-sm font-semibold">/ {stats.weeklyCuts.target} คลิป</span>
          </div>

          {/* Neon Progress bar */}
          <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden mb-2.5">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${stats.weeklyCuts.pct}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>เหลืออีก <strong className="text-white font-bold">{stats.weeklyCuts.remaining}</strong> คลิป</span>
            <span>จันทร์ - อาทิตย์นี้</span>
          </div>
        </div>

        {/* Daily Cuts Card */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-5 shadow-lg backdrop-blur-md relative overflow-hidden group hover:border-cyan-500/30 transition-all">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold">
              <Clapperboard className="w-4 h-4 text-cyan-400" />
              <span>เป้าหมายตัดต่อวันนี้</span>
            </div>
            <span className="text-xs font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-md border border-cyan-500/20">
              {stats.dailyCuts.pct}%
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-black text-white">{stats.dailyCuts.current}</span>
            <span className="text-slate-400 text-sm font-semibold">/ {stats.dailyCuts.target} คลิป</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden mb-2.5">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${stats.dailyCuts.pct}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{stats.dailyCuts.remaining === 0 ? '✨ วันนี้ครบเป้าแล้ว' : `ยังต้องตัดอีก ${stats.dailyCuts.remaining} คลิป`}</span>
            <span>โควตาประจำวัน</span>
          </div>
        </div>

        {/* Daily Posts Card */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-5 shadow-lg backdrop-blur-md relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold">
              <Share2 className="w-4 h-4 text-emerald-400" />
              <span>เป้าหมายโพสต์วันนี้</span>
            </div>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
              {stats.dailyPosts.pct}%
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-black text-white">{stats.dailyPosts.current}</span>
            <span className="text-slate-400 text-sm font-semibold">/ {stats.dailyPosts.target} คลิป</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden mb-2.5">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${stats.dailyPosts.pct}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{stats.dailyPosts.remaining === 0 ? '🎉 โพสต์ครบแล้ว' : `ยังไม่ได้โพสต์อีก ${stats.dailyPosts.remaining} คลิป`}</span>
            <span>TikTok Active</span>
          </div>
        </div>
      </div>

      {/* ── 3. Daily Action Queue (สิ่งที่ต้องทำวันนี้) ── */}
      <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">สิ่งที่ต้องทำวันนี้ (Daily Action Queue)</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              จัดลำดับความเร่งด่วน 3 ลำดับ คลิกเดียวทำงานต่อได้ทันที ไม่ต้องค้นหา
            </p>
          </div>

          {/* Queue Filter Tabs */}
          <div className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-xl border border-white/5 self-start sm:self-auto">
            <button
              onClick={() => setQueueFilter('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                queueFilter === 'all'
                  ? 'bg-amber-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              ทั้งหมด ({actionQueue.readyToPost.length + actionQueue.readyToCut.length + actionQueue.needsFootage.length})
            </button>
            <button
              onClick={() => setQueueFilter('post')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                queueFilter === 'post'
                  ? 'bg-rose-500 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              รอโพสต์ ({actionQueue.readyToPost.length})
            </button>
            <button
              onClick={() => setQueueFilter('cut')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                queueFilter === 'cut'
                  ? 'bg-amber-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              รอตัด ({actionQueue.readyToCut.length})
            </button>
            <button
              onClick={() => setQueueFilter('footage')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                queueFilter === 'footage'
                  ? 'bg-cyan-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              รอถ่ายคลิป ({actionQueue.needsFootage.length})
            </button>
          </div>
        </div>

        {/* Queue Items List */}
        {displayQueue.length === 0 ? (
          <div className="py-12 text-center rounded-xl bg-slate-950/40 border border-dashed border-white/10">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2 opacity-80" />
            <p className="text-white font-bold text-sm">เคลียร์คิวเกลี้ยงแล้วครับเจ้านาย!</p>
            <p className="text-slate-400 text-xs mt-1">ไม่มีงานคั่งค้างในหมวดนี้ กดเพิ่มสินค้าใหม่ใน Script Lab ได้เลย</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {displayQueue.slice(0, 10).map((item, idx) => {
              const isPost = item.queueCategory === 'post' || queueFilter === 'post';
              const isCut = item.queueCategory === 'cut' || queueFilter === 'cut';
              const isFootage = item.queueCategory === 'footage' || queueFilter === 'footage';

              return (
                <div
                  key={item.id || idx}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-800/40 hover:bg-slate-800/70 border border-white/5 hover:border-white/10 transition-all group"
                >
                  <div className="flex items-start sm:items-center gap-3 min-w-0">
                    {isPost && (
                      <span className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 flex-shrink-0">
                        <Flame className="w-4 h-4" />
                      </span>
                    )}
                    {isCut && (
                      <span className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
                        <Scissors className="w-4 h-4" />
                      </span>
                    )}
                    {isFootage && (
                      <span className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 flex-shrink-0">
                        <Video className="w-4 h-4" />
                      </span>
                    )}

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        {item.productCode && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-white/10 text-[10px] font-bold text-slate-300">
                            {item.productCode}
                          </span>
                        )}
                        <h3 className="text-sm font-bold text-white truncate group-hover:text-amber-300 transition-colors">
                          {item.title}
                        </h3>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-0.5">
                        {item.productName}
                        {isPost && ' · วิดีโอเรนเดอร์เสร็จแล้ว รอโพสต์ลง TikTok'}
                        {isCut && (item.projectName ? ` · ไทม์ไลน์: ${item.projectName}` : ' · วัตถุดิบพร้อมตัด')}
                        {isFootage && ' · สคริปต์พร้อมแล้ว ขาดคลิปถ่ายจริง'}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0 self-end sm:self-center">
                    {isPost && (
                      <>
                        {item.caption && (
                          <button
                            onClick={() => handleCopyCaption(`${item.caption}\n\n${item.hashtags}`, item.id)}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer transition-all"
                            title="คัดลอกแคปชัน"
                          >
                            {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedId === item.id ? 'ก๊อปปี้แล้ว' : 'แคปชัน'}</span>
                          </button>
                        )}
                        <button
                          onClick={onGoToGallery}
                          className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-rose-500 to-pink-500 hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1 cursor-pointer shadow-sm transition-all"
                        >
                          <span>ส่ง TikTok</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}

                    {isCut && (
                      <button
                        onClick={() => {
                          if (item.parentProduct && item.angle) {
                            onApplyToStudio?.({
                              fullProduct: item.parentProduct,
                              angleIndex: item.parentProduct.angles?.findIndex(a => a.angle_id === item.angle.angle_id) || 0,
                              openExisting: !!item.projectName,
                              openProjectName: item.projectName,
                            });
                          } else {
                            onGoToEditor?.();
                          }
                        }}
                        className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1 cursor-pointer shadow-sm transition-all"
                      >
                        <Clapperboard className="w-3.5 h-3.5" />
                        <span>{item.projectName ? 'เปิดไทม์ไลน์' : 'เริ่มตัดต่อ'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {isFootage && (
                      <button
                        onClick={() => {
                          if (item.parentProduct?.id) onGoToFlow?.(item.parentProduct.id);
                          else onGoToFlow?.();
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-cyan-500/20 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
                      >
                        <span>แนบคลิป / ดูแผน</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 4. AI Content Retrospective & Boss's Playbook ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: AI Retrospective */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-6 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-bold text-white">ถอดรหัสคลิปปัง & สถิติ (AI Retrospective)</h2>
            </div>

            {retrospective.topPerformer && (
              <div className="mb-4 p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-slate-900/80 to-slate-900/80 border border-emerald-500/20">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                    🏆 คลิปยอดวิวสูงสุด
                  </span>
                  <div className="flex items-center gap-3 text-xs text-slate-300">
                    <span className="flex items-center gap-1 font-bold text-emerald-300">
                      <Eye className="w-3.5 h-3.5" /> {retrospective.topPerformer.views.toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1 text-slate-400">
                      <ThumbsUp className="w-3.5 h-3.5" /> {retrospective.topPerformer.likes.toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1 text-slate-400">
                      <Share2 className="w-3.5 h-3.5" /> {retrospective.topPerformer.shares.toLocaleString()}
                    </span>
                  </div>
                </div>
                <h4 className="text-sm font-bold text-white truncate">{retrospective.topPerformer.title}</h4>
              </div>
            )}

            <div className="space-y-2.5 mb-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">💡 จุดเด่นที่ทำให้ยอดพุ่ง</h4>
              {retrospective.topTakeaways.map((point, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-slate-300 bg-slate-800/30 p-2.5 rounded-lg border border-white/5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                  <span className="leading-relaxed">{point}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-200/90 leading-relaxed flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-amber-300 font-bold block mb-0.5">ข้อควรปรับปรุงในคลิปหน้า:</strong>
              {retrospective.improvementAdvice}
            </div>
          </div>
        </div>

        {/* Right Column: Boss's Learning Playbook */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-6 shadow-xl backdrop-blur-md flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-400" />
              <h2 className="text-base font-bold text-white">สมุดจดบทเรียนของเจ้านาย (Boss's Playbook)</h2>
            </div>
            <span className="text-xs text-slate-400 font-medium">บันทึกกันลืม ({playbookNotes.length})</span>
          </div>

          {/* New note input form */}
          <form onSubmit={handleAddNote} className="space-y-2 mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={newNoteText}
                onChange={(e) => setNewNoteText(e.target.value)}
                placeholder="จดบทเรียน / ไอเดียกันลืมสำหรับคลิปหน้า..."
                className="flex-1 bg-slate-950/60 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
              />
              <select
                value={newNoteTag}
                onChange={(e) => setNewNoteTag(e.target.value)}
                className="bg-slate-950/60 border border-white/10 rounded-xl px-2.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-amber-500 cursor-pointer"
              >
                <option value="Hook">Hook</option>
                <option value="Audio">Audio</option>
                <option value="Visual">Visual</option>
                <option value="Script">Script</option>
                <option value="Product">Product</option>
              </select>
              <button
                type="submit"
                disabled={!newNoteText.trim()}
                className="px-3 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 active:scale-95 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-1 cursor-pointer transition-all flex-shrink-0"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>จด</span>
              </button>
            </div>
          </form>

          {/* Notes list */}
          <div className="space-y-2 flex-1 overflow-y-auto max-h-[260px] pr-1">
            {playbookNotes.length === 0 ? (
              <p className="text-center text-xs text-slate-500 py-6">ยังไม่มีโน้ตจดบันทึก พิมพ์ข้อความด้านบนเพื่อจดกันลืมได้เลยครับ</p>
            ) : (
              playbookNotes.map((note) => (
                <div
                  key={note.id}
                  className="p-3 rounded-xl bg-slate-800/40 border border-white/5 hover:border-white/10 flex items-start justify-between gap-3 group transition-all"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px] font-bold">
                        {note.tag}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed break-words">{note.text}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteNote(note.id)}
                    className="text-slate-500 hover:text-rose-400 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                    title="ลบโน้ตนี้"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── 5. Targets Modal ── */}
      {showTargetsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md bg-slate-900 border border-white/15 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">ตั้งเป้าหมายการผลิต (Quotas)</h3>
              </div>
              <button
                onClick={() => setShowTargetsModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">
                  🎯 เป้าหมายรายสัปดาห์ (คลิป/สัปดาห์)
                </label>
                <input
                  type="number"
                  min="1"
                  max="200"
                  value={editingTargets.weeklyCuts}
                  onChange={(e) => setEditingTargets({ ...editingTargets, weeklyCuts: e.target.value })}
                  className="w-full bg-slate-950 border border-white/15 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">ค่าเริ่มต้นมาตรฐานของทีมคือ 35 คลิป/สัปดาห์ (เฉลี่ยวันละ 5 คลิป)</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">
                  🎬 เป้าหมายตัดต่อรายวัน (คลิป/วัน)
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={editingTargets.dailyCuts}
                  onChange={(e) => setEditingTargets({ ...editingTargets, dailyCuts: e.target.value })}
                  className="w-full bg-slate-950 border border-white/15 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">
                  📢 เป้าหมายโพสต์ TikTok รายวัน (คลิป/วัน)
                </label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={editingTargets.dailyPosts}
                  onChange={(e) => setEditingTargets({ ...editingTargets, dailyPosts: e.target.value })}
                  className="w-full bg-slate-950 border border-white/15 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-white/10">
              <button
                type="button"
                onClick={() => setShowTargetsModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 cursor-pointer"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={handleSaveTargets}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold cursor-pointer transition-all shadow-md shadow-amber-500/20"
              >
                บันทึกเป้าหมาย
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
