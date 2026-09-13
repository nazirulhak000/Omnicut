import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Sparkles, Flame, CheckCircle2, Clock, Play, ArrowRight,
  TrendingUp, AlertTriangle, Lightbulb, Target, Settings,
  Copy, Check, Plus, Trash2, Video, Film, Eye, Share2, ThumbsUp,
  RefreshCw, Clapperboard, ChevronRight, Zap, Scissors, Compass,
  BookOpen, FileText, ExternalLink, X, Bookmark, Image as ImageIcon,
  Link as LinkIcon, Smartphone, Filter, Tag, Loader2, Clipboard
} from 'lucide-react';
import {
  getProducts, getExports, getTiktokStatsLatest,
  uploadRefMedia, aiIdeaToAngle, addProductAngle
} from '../../api';
import {
  loadTargets,
  saveTargets,
  loadPlaybookNotes,
  savePlaybookNotes,
  addPlaybookNote,
  deletePlaybookNote,
  detectRefPlatform,
  calculateProductionStats,
  getDailyActionQueue,
  generateBossGreeting,
  analyzeContentPerformance,
  calculateWeeklyPacing,
  autoSuggestPlaybookNotes,
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

  // Playbook & Idea/Ref Vault state
  const [playbookNotes, setPlaybookNotes] = useState(() => loadPlaybookNotes());
  const [ideaText, setIdeaText] = useState('');
  const [ideaUrl, setIdeaUrl] = useState('');
  const [ideaImage, setIdeaImage] = useState(null);
  const [ideaTag, setIdeaTag] = useState('Hook');
  const [ideaProduct, setIdeaProduct] = useState('');
  const [uploadingRefImage, setUploadingRefImage] = useState(false);
  const [refSaveSuccess, setRefSaveSuccess] = useState(false);
  const fileInputRef = useRef(null);

  // AI Idea-to-Script state
  const [aiSynthesizingId, setAiSynthesizingId] = useState(null);
  const [aiProposal, setAiProposal] = useState(null);
  const [addingAngle, setAddingAngle] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Queue filter
  const [queueFilter, setQueueFilter] = useState('all'); // 'all' | 'post' | 'cut' | 'footage'
  const [productFilter, setProductFilter] = useState('all'); // 'all' | productId

  // Clipboard copy state
  const [copiedId, setCopiedId] = useState(null);

  // Quick Preview Modal state
  const [previewItem, setPreviewItem] = useState(null);

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

  const weeklyPacing = useMemo(() => {
    return calculateWeeklyPacing(stats);
  }, [stats]);

  const bossGreeting = useMemo(() => {
    return generateBossGreeting({ stats, actionQueue });
  }, [stats, actionQueue]);

  const retrospective = useMemo(() => {
    return analyzeContentPerformance(tiktokStats, products);
  }, [tiktokStats, products]);

  const playbookSuggestions = useMemo(() => {
    return autoSuggestPlaybookNotes(retrospective, playbookNotes);
  }, [retrospective, playbookNotes]);

  // Next Mission Spotlight: pick the single most urgent task
  const nextMission = useMemo(() => {
    if (actionQueue.readyToPost.length > 0) {
      return {
        type: 'post',
        item: actionQueue.readyToPost[0],
        badge: '🚨 เร่งด่วนอันดับ 1',
        title: 'ปล่อยคลิปนี้ลง TikTok ด่วนเพื่อดันยอดขาย!',
        description: 'วิดีโอเรนเดอร์เสร็จแล้ว รอโพสต์ลง TikTok',
      };
    }
    if (actionQueue.readyToCut.length > 0) {
      return {
        type: 'cut',
        item: actionQueue.readyToCut[0],
        badge: '🎬 ภารกิจถัดไป',
        title: 'ตัดต่อคลิปนี้ทันที วัตถุดิบพร้อมแล้ว!',
        description: actionQueue.readyToCut[0].projectName ? `ไทม์ไลน์: ${actionQueue.readyToCut[0].projectName}` : 'วัตถุดิบและสคริปต์พร้อมตัดต่อทันที',
      };
    }
    if (actionQueue.needsFootage.length > 0) {
      return {
        type: 'footage',
        item: actionQueue.needsFootage[0],
        badge: '📝 ถ่ายคลิปเพิ่ม',
        title: 'เตรียมวัตถุดิบและดู Shot List สินค้านี้',
        description: 'สคริปต์พร้อมแล้ว ขาดคลิปถ่ายจริง',
      };
    }
    return null;
  }, [actionQueue]);

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

  const [pastedImageToast, setPastedImageToast] = useState(false);

  // Reusable Image Processor for Producer Hub
  const processRefImageFile = async (file) => {
    if (!file) return;

    // Instant local preview
    const reader = new FileReader();
    reader.onload = () => {
      setIdeaImage(reader.result);
      setPastedImageToast(true);
      setTimeout(() => setPastedImageToast(false), 2500);
    };
    reader.readAsDataURL(file);

    // Upload to server if available
    try {
      setUploadingRefImage(true);
      const res = await uploadRefMedia(file);
      if (res?.url) {
        setIdeaImage(res.url);
      }
    } catch (err) {
      console.warn('Upload ref media to server failed, using local base64:', err);
    } finally {
      setUploadingRefImage(false);
    }
  };

  // Handle Image Selection from File Picker
  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) processRefImageFile(file);
  };

  // Intercept Ctrl+V or right-click Paste of images
  const handlePasteImageAnywhere = (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        const file = items[i].getAsFile();
        if (file) {
          e.preventDefault();
          processRefImageFile(file);
          return;
        }
      }
    }
  };

  // Drag & drop image support
  const handleDropImage = (e) => {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (file && file.type.startsWith('image/')) {
      processRefImageFile(file);
    }
  };

  // 1-Tap Read Image directly from Clipboard
  const handlePasteImageFromClipboard = async () => {
    try {
      if (!navigator.clipboard?.read) {
        alert('เบราว์เซอร์นี้ไม่อนุญาตให้อ่านรูปภาพผ่านปุ่มโดยตรง\nทริก: เจ้านายสามารถกดในช่องข้อความแล้วกด Ctrl+V เพื่อวางรูปภาพได้ทันทีครับ!');
        return;
      }
      setUploadingRefImage(true);
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            const blob = await item.getType(type);
            const file = new File([blob], `pasted_ref_${Date.now()}.png`, { type });
            processRefImageFile(file);
            return;
          }
        }
      }
      alert('ไม่พบรูปภาพในคลิปบอร์ด\n(กรุณากดแคปหน้าจอ เช่น Win+Shift+S หรือคัดลอกรูปภาพมาก่อน แล้วกดใหม่อีกครั้งครับ)');
    } catch (err) {
      console.warn('Clipboard read error:', err);
      alert('ไม่สามารถอ่านรูปจากคลิปบอร์ดได้: ' + (err.message || 'Permission denied') + '\nทริก: เจ้านายสามารถกดในช่องข้อความแล้วกด Ctrl+V ได้ทันทีครับ!');
    } finally {
      setUploadingRefImage(false);
    }
  };

  // Handle Add Idea / Ref Note
  const handleSaveIdea = (e) => {
    if (e) e.preventDefault();
    if (!ideaText.trim() && !ideaUrl.trim() && !ideaImage) return;

    const matchedProd = products.find(p => p.id === ideaProduct);
    const newNote = {
      text: ideaText.trim(),
      url: ideaUrl.trim() || undefined,
      imageUrl: ideaImage || undefined,
      tag: ideaTag || 'Hook',
      productId: ideaProduct || undefined,
      productName: matchedProd?.name || undefined,
      productCode: matchedProd?.product_code || undefined,
    };

    const updated = addPlaybookNote(newNote, playbookNotes);
    setPlaybookNotes(updated);
    setIdeaText('');
    setIdeaUrl('');
    setIdeaImage(null);
    setRefSaveSuccess(true);
    setTimeout(() => setRefSaveSuccess(false), 2500);
  };

  // Handle Delete Note
  const handleDeleteNote = (id) => {
    const updated = deletePlaybookNote(id, playbookNotes);
    setPlaybookNotes(updated);
  };

  // Handle Trigger AI Idea-to-Script
  const handleRunAiIdeaToScript = async (note) => {
    try {
      setAiSynthesizingId(note.id);
      const res = await aiIdeaToAngle({
        idea_text: note.text,
        ref_url: note.url,
        ref_image: note.imageUrl,
        product_id: note.productId || (products[0]?.id || null),
      });

      if (res?.success && res.proposal) {
        setAiProposal({
          ...res.proposal,
          product_id: note.productId || (products[0]?.id || ''),
          originNoteId: note.id,
        });
      }
    } catch (err) {
      console.error('Failed to synthesize idea with AI:', err);
      alert('ไม่สามารถประมวลผลไอเดียด้วย AI ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAiSynthesizingId(null);
    }
  };

  // Handle Confirm Adding Proposed Angle to Product
  const handleConfirmAddAngle = async () => {
    if (!aiProposal) return;
    const targetProdId = aiProposal.product_id;
    if (!targetProdId) {
      alert('กรุณาเลือกสินค้าที่ต้องการผูกมุมมองนี้');
      return;
    }

    try {
      setAddingAngle(true);
      const newAngleData = {
        angle_id: `angle_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        angle_name: aiProposal.angle_name,
        hook_title: aiProposal.hook_title,
        target_audience: aiProposal.target_audience,
        pain_point: aiProposal.pain_point,
        shoot_brief: aiProposal.shoot_angle_brief,
        script: aiProposal.script_brief,
        status: 'scripted',
        created_at: new Date().toISOString(),
      };

      await addProductAngle(targetProdId, newAngleData);
      await fetchData(); // Refresh data to immediately show in daily queue
      setAiProposal(null);
      setToastMessage('เพิ่มมุมมองใหม่เข้าสินค้าเรียบร้อยแล้ว!');
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err) {
      console.error('Failed to add angle:', err);
      alert('บันทึกมุมมองไม่สำเร็จ: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAddingAngle(false);
    }
  };

  // Handle Copy Caption
  const handleCopyCaption = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filtered queue items with product filter support
  const displayQueue = useMemo(() => {
    let base = [];
    if (queueFilter === 'post') {
      base = actionQueue.readyToPost.map(i => ({ ...i, queueCategory: 'post' }));
    } else if (queueFilter === 'cut') {
      base = actionQueue.readyToCut.map(i => ({ ...i, queueCategory: 'cut' }));
    } else if (queueFilter === 'footage') {
      base = actionQueue.needsFootage.map(i => ({ ...i, queueCategory: 'footage' }));
    } else {
      base = [
        ...actionQueue.readyToPost.map(i => ({ ...i, queueCategory: 'post' })),
        ...actionQueue.readyToCut.map(i => ({ ...i, queueCategory: 'cut' })),
        ...actionQueue.needsFootage.map(i => ({ ...i, queueCategory: 'footage' })),
      ];
    }

    if (productFilter !== 'all') {
      base = base.filter(i => (
        i.parentProduct?.id === productFilter ||
        i.productCode === productFilter ||
        i.productName === productFilter
      ));
    }

    return base;
  }, [actionQueue, queueFilter, productFilter]);

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

          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>เหลืออีก <strong className="text-white font-bold">{stats.weeklyCuts.remaining}</strong> คลิป</span>
            <span>จันทร์ - อาทิตย์นี้</span>
          </div>

          {/* Weekly Pacing Advice Badge */}
          <div className={`mt-2 pt-2 border-t border-white/5 text-[11px] font-semibold flex items-center gap-1.5 ${weeklyPacing.badgeColor} px-2 py-1 rounded-lg`}>
            <Clock className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{weeklyPacing.paceAdvice}</span>
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

      {/* ── 2.5 Spotlight: ภารกิจอันดับ 1 ที่ต้องทำตอนนี้ (Next Action Spotlight) ── */}
      {nextMission && (
        <div className={`relative overflow-hidden rounded-2xl p-5 border shadow-2xl backdrop-blur-md transition-all ${
          nextMission.type === 'post'
            ? 'bg-gradient-to-r from-rose-950/70 via-slate-900/90 to-slate-900/90 border-rose-500/30'
            : nextMission.type === 'cut'
            ? 'bg-gradient-to-r from-amber-950/70 via-slate-900/90 to-slate-900/90 border-amber-500/30'
            : 'bg-gradient-to-r from-cyan-950/70 via-slate-900/90 to-slate-900/90 border-cyan-500/30'
        }`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5 min-w-0">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
                nextMission.type === 'post' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                nextMission.type === 'cut' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              }`}>
                <Compass className="w-6 h-6 animate-pulse" />
              </div>

              <div className="space-y-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black tracking-wider uppercase ${
                    nextMission.type === 'post' ? 'bg-rose-500 text-white' :
                    nextMission.type === 'cut' ? 'bg-amber-500 text-slate-950' :
                    'bg-cyan-500 text-slate-950'
                  }`}>
                    {nextMission.badge}
                  </span>
                  <span className="text-xs text-slate-400 font-semibold">สิ่งที่เจ้านายควรทำตอนนี้ (ลดภาระสมอง มองแวบเดียวลุยเลย)</span>
                </div>

                <h3 className="text-base font-bold text-white tracking-tight truncate">
                  {nextMission.item.title}
                </h3>

                <p className="text-xs text-slate-300 truncate">
                  สินค้า: <strong className="text-white">{nextMission.item.productName}</strong>
                  {nextMission.item.productCode && ` [${nextMission.item.productCode}]`}
                  <span className="text-slate-400 ml-1.5">· {nextMission.description}</span>
                </p>
              </div>
            </div>

            {/* Spotlight Action Buttons */}
            <div className="flex items-center gap-2.5 flex-shrink-0 self-end md:self-center">
              <button
                onClick={() => setPreviewItem(nextMission.item)}
                className="px-3.5 py-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 border border-white/10 text-xs font-bold text-slate-300 hover:text-white flex items-center gap-1.5 cursor-pointer transition-all"
              >
                <FileText className="w-4 h-4" />
                <span>ดูบท & สเปก</span>
              </button>

              {nextMission.type === 'post' && (
                <button
                  onClick={onGoToGallery}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-rose-500/25 transition-all"
                >
                  <Flame className="w-4 h-4" />
                  <span>ส่ง TikTok ตอนนี้เลย</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {nextMission.type === 'cut' && (
                <button
                  onClick={() => {
                    if (nextMission.item.parentProduct && nextMission.item.angle) {
                      onApplyToStudio?.({
                        fullProduct: nextMission.item.parentProduct,
                        angleIndex: nextMission.item.parentProduct.angles?.findIndex(a => a.angle_id === nextMission.item.angle.angle_id) || 0,
                        openExisting: !!nextMission.item.projectName,
                        openProjectName: nextMission.item.projectName,
                      });
                    } else {
                      onGoToEditor?.();
                    }
                  }}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-amber-500/25 transition-all"
                >
                  <Clapperboard className="w-4 h-4" />
                  <span>เริ่มตัดต่อคลิปนี้ทันที</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {nextMission.type === 'footage' && (
                <button
                  onClick={() => {
                    if (nextMission.item.parentProduct?.id) onGoToFlow?.(nextMission.item.parentProduct.id);
                    else onGoToFlow?.();
                  }}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-cyan-500/25 transition-all"
                >
                  <Video className="w-4 h-4" />
                  <span>ดูแผนถ่ายทำ Shot List</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 2.8 Idea & Ref Vault (สมุดจดไอเดียและคลังเรฟ TikTok / Pinterest) ── */}
      <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-5 shadow-xl backdrop-blur-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3.5">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
              <Lightbulb className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-tight">คลังไอเดีย & เรฟ TikTok / Pinterest (Idea & Ref Vault)</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  {playbookNotes.length} รายการ
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                จดไอเดียสด แปะลิงก์คลิปเรฟ หรือแนบภาพแคปหน้าจอ เพื่อให้ AI ช่วยคิดมุมมองและสคริปต์ต่อยอดได้ทันที
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <a
              href="?view=quick-ref"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-300 hover:text-white border border-cyan-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
              title="เปิดหน้า Quick-Capture ขนาดมือถือ iPhone 15 Pro Max เพื่อ Add to Home Screen"
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span>โหมดมือถือ (iPhone)</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          </div>
        </div>

        {/* Quick Input Bar */}
        <form
          onSubmit={handleSaveIdea}
          onPaste={handlePasteImageAnywhere}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropImage}
          className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5 space-y-3"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-bold text-slate-300 flex items-center gap-1">
                  <LinkIcon className="w-3 h-3 text-cyan-400" />
                  <span>ลิงก์คลิปเรฟ (TikTok / Pinterest / YouTube)</span>
                </label>
                {ideaUrl && detectRefPlatform(ideaUrl) && (
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300 bg-amber-500/15 px-1.5 py-0.5 rounded border border-amber-500/30">
                    {detectRefPlatform(ideaUrl)}
                  </span>
                )}
              </div>
              <input
                type="url"
                value={ideaUrl}
                onChange={(e) => setIdeaUrl(e.target.value)}
                placeholder="แปะลิงก์คลิปเรฟที่ชอบ เช่น https://vt.tiktok.com/..."
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-bold text-slate-300">
                  ไอเดีย / ประเด็นที่อยากให้ AI หรือตัวเองทำตาม
                </label>
                <span className="text-[10px] text-amber-400/90 font-medium">
                  กด Ctrl+V วางรูปภาพได้เลย
                </span>
              </div>
              <input
                type="text"
                value={ideaText}
                onChange={(e) => setIdeaText(e.target.value)}
                onPaste={handlePasteImageAnywhere}
                placeholder="เช่น เปิดด้วยภาพแช่แข็งมือถือ... (แคปหน้าจอแล้วกด Ctrl+V วางรูปภาพได้ทันที)"
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*"
                onChange={handleImageSelect}
                className="hidden"
              />

              <button
                type="button"
                onClick={handlePasteImageFromClipboard}
                disabled={uploadingRefImage}
                className="px-2.5 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                title="อ่านรูปภาพจากคลิปบอร์ดที่เพิ่งแคปหน้าจอมา"
              >
                <Clipboard className="w-3.5 h-3.5" />
                <span>วางรูปภาพ</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingRefImage}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-all"
              >
                <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>{ideaImage ? 'เปลี่ยนรูปเรฟ' : 'แนบไฟล์ภาพ'}</span>
              </button>

              {pastedImageToast && (
                <span className="text-[11px] font-bold text-emerald-400 animate-pulse">
                  วางรูปภาพเรียบร้อย!
                </span>
              )}

              <select
                value={ideaTag}
                onChange={(e) => setIdeaTag(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 border border-white/10 text-xs text-slate-200 focus:outline-none cursor-pointer"
              >
                <option value="Hook">Hook (ฮุกเปิดคลิป)</option>
                <option value="Ref Clip">Ref Clip (เรฟคลิป)</option>
                <option value="Visual">Visual (มุมกล้อง)</option>
                <option value="Audio">Audio (เสียง/เพลง)</option>
                <option value="Promo">Promo (โปรโมชั่น)</option>
              </select>

              {products.length > 0 && (
                <select
                  value={ideaProduct}
                  onChange={(e) => setIdeaProduct(e.target.value)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-800 border border-white/10 text-xs text-slate-200 focus:outline-none cursor-pointer max-w-[170px] truncate"
                >
                  <option value="">ผูกสินค้า (ไม่บังคับ)</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.product_code ? `[${p.product_code}] ` : ''}{p.name}
                    </option>
                  ))}
                </select>
              )}

              {ideaImage && (
                <div className="relative inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 border border-white/10 text-[11px] text-cyan-300">
                  <span>มีรูปเรฟแนบอยู่</span>
                  <button
                    type="button"
                    onClick={() => setIdeaImage(null)}
                    className="text-slate-400 hover:text-rose-400 cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={!ideaText.trim() && !ideaUrl.trim() && !ideaImage}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer shadow-md shadow-amber-500/20 disabled:opacity-40 transition-all"
            >
              {refSaveSuccess ? <Check className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
              <span>{refSaveSuccess ? 'บันทึกเรียบร้อย' : 'บันทึกไอเดีย'}</span>
            </button>
          </div>
        </form>

        {/* Saved Ideas / Refs List */}
        {playbookNotes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[360px] overflow-y-auto pr-1">
            {playbookNotes.map((item) => {
              const platform = detectRefPlatform(item.url);
              const isSynthesizing = aiSynthesizingId === item.id;

              return (
                <div
                  key={item.id}
                  className="p-3.5 rounded-xl bg-slate-800/40 border border-white/5 hover:border-amber-500/30 transition-all flex flex-col justify-between gap-2.5 group"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                          <Tag className="w-2.5 h-2.5" />
                          {item.tag || 'Idea'}
                        </span>
                        {item.productName && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-900/80 text-slate-300 border border-white/10 truncate max-w-[110px]">
                            {item.productCode || item.productName}
                          </span>
                        )}
                        {platform && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                            {platform}
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => handleDeleteNote(item.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                        title="ลบรายการนี้"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {item.text && (
                      <p className="text-xs text-slate-200 leading-relaxed font-medium line-clamp-3">
                        {item.text}
                      </p>
                    )}

                    {item.imageUrl && (
                      <div className="relative rounded-lg overflow-hidden border border-white/10 max-h-28 bg-black/40">
                        <img
                          src={item.imageUrl}
                          alt="Ref media"
                          className="w-full h-28 object-cover group-hover:scale-105 transition-transform"
                        />
                      </div>
                    )}

                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-semibold underline truncate max-w-full"
                      >
                        <LinkIcon className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate">{item.url}</span>
                        <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                      </a>
                    )}
                  </div>

                  {/* AI Idea-to-Script Button */}
                  <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500">
                      {item.createdAt ? new Date(item.createdAt).toLocaleDateString('th-TH') : ''}
                    </span>

                    <button
                      onClick={() => handleRunAiIdeaToScript(item)}
                      disabled={isSynthesizing}
                      className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-bold flex items-center gap-1 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                      title="ให้ AI วิเคราะห์เรฟนี้แล้วแปลงเป็นมุมมองและสคริปต์สำหรับสินค้า"
                    >
                      {isSynthesizing ? <Loader2 className="w-3 h-3 animate-spin text-amber-400" /> : <Sparkles className="w-3 h-3" />}
                      <span>{isSynthesizing ? 'AI กำลังคิด...' : 'คิดสคริปต์จากเรฟ'}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 3. Daily Action Queue (สิ่งที่ต้องทำวันนี้) ── */}
      <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-6 shadow-xl backdrop-blur-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">สิ่งที่ต้องทำวันนี้ (Daily Action Queue)</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              จัดสรรสินค้าแบบกระจายคละสินค้า (Round-Robin) คลิกเดียวทำงานต่อได้ทันที ไม่ผูกขาดสินค้าเดียว
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

        {/* Product Filter Chips */}
        {actionQueue.productsInQueue && actionQueue.productsInQueue.length > 1 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-[11px] text-slate-500 font-bold flex items-center gap-1 flex-shrink-0">
              <Filter className="w-3 h-3 text-amber-400" /> กรองสินค้า:
            </span>
            <button
              onClick={() => setProductFilter('all')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex-shrink-0 ${
                productFilter === 'all'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-sm'
                  : 'bg-slate-800 text-slate-300 hover:text-white border border-white/5'
              }`}
            >
              ทั้งหมด
            </button>
            {actionQueue.productsInQueue.map(p => (
              <button
                key={p.id || p.code}
                onClick={() => setProductFilter(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex-shrink-0 max-w-[200px] truncate ${
                  productFilter === p.id
                    ? 'bg-amber-500/25 text-amber-300 border border-amber-500/40 font-bold'
                    : 'bg-slate-800/80 text-slate-400 hover:text-white border border-white/5'
                }`}
              >
                {p.code ? `[${p.code}] ` : ''}{p.name} ({p.count})
              </button>
            ))}
          </div>
        )}

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

                  <div className="flex items-center gap-2 flex-shrink-0 self-end sm:self-auto">
                    <button
                      onClick={() => setPreviewItem(item)}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1 cursor-pointer transition-all"
                      title="ดูบทและรายละเอียด"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span className="hidden md:inline">ดูบท</span>
                    </button>

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
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>💡 จุดเด่นที่ทำให้ยอดพุ่ง</span>
                <span className="text-[10px] text-amber-400 lowercase font-normal">คลิกเพื่อจดลง Playbook ได้ทันที</span>
              </h4>
              {playbookSuggestions.map((item, i) => (
                <div key={item.id || i} className="flex items-center justify-between gap-3 text-xs text-slate-300 bg-slate-800/30 p-2.5 rounded-lg border border-white/5 group hover:border-amber-500/30 transition-all">
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                    <span className="leading-relaxed">{item.text}</span>
                  </div>
                  <button
                    onClick={() => {
                      if (!item.alreadySaved) {
                        const newNote = {
                          id: `note-${Date.now()}-${i}`,
                          text: item.text,
                          createdAt: new Date().toISOString(),
                          tag: item.tag,
                        };
                        const updated = [newNote, ...playbookNotes];
                        setPlaybookNotes(updated);
                        savePlaybookNotes(updated);
                      }
                    }}
                    disabled={item.alreadySaved}
                    className={`px-2 py-1 rounded text-[11px] font-bold flex items-center gap-1 flex-shrink-0 transition-all ${
                      item.alreadySaved
                        ? 'text-emerald-400 bg-emerald-500/10 cursor-default'
                        : 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 cursor-pointer active:scale-95'
                    }`}
                  >
                    {item.alreadySaved ? <Check className="w-3 h-3 text-emerald-400" /> : <Plus className="w-3 h-3" />}
                    <span>{item.alreadySaved ? 'จดแล้ว' : 'จดบทเรียน'}</span>
                  </button>
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

        {/* Right Column: Studio Rules & Guidelines */}
        <div className="rounded-2xl bg-slate-900/70 border border-white/[0.08] p-6 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-5 h-5 text-amber-400" />
              <h2 className="text-base font-bold text-white">คู่มือกฎเหล็กการผลิตคลิปปัง (Studio Rules)</h2>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5 space-y-1">
                <span className="font-bold text-amber-300 block">⚡ กฎ Hook 0.5 วินาทีแรก</span>
                <p className="text-slate-300 leading-relaxed">
                  อย่าเกริ่นทักทายเวิ่นเว้อ ให้เปิดด้วยภาพกระแทกตา ป้ายเตือน หรือปัญหาตรงๆ เพื่อหยุดนิ้วคนดูทันที
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5 space-y-1">
                <span className="font-bold text-cyan-300 block">✂️ จังหวะตัดต่อ J-Cut (180ms)</span>
                <p className="text-slate-300 leading-relaxed">
                  เสียงพากย์หรือ SFX ของช็อตถัดไปจะดังขึ้นก่อนภาพตัดเปลี่ยน 180ms เพื่อสร้างความลื่นไหลและเร่ง Retention
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5 space-y-1">
                <span className="font-bold text-emerald-300 block">📱 Safe Zone 9:16 มาตรฐาน TikTok</span>
                <p className="text-slate-300 leading-relaxed">
                  ข้อความซับไตเติลและป้ายราคายกสูงจากขอบล่าง 420px เสมอ เพื่อไม่ให้ปุ่ม Like / แชร์ และชื่อเพลงบดบัง
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
            <span>ไอเดียทั้งหมดถูกซิงก์เข้า <strong>คลังเรฟด้านบน</strong></span>
            <button
              onClick={() => window.scrollTo({ top: 400, behavior: 'smooth' })}
              className="text-amber-400 hover:text-amber-300 font-semibold cursor-pointer"
            >
              ขึ้นไปดูคลังเรฟ ↑
            </button>
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

      {/* ── 6. Quick Preview Modal (ดูสคริปต์และสเปกก่อนตัด) ── */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg bg-slate-900 border border-white/15 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <h3 className="text-base font-bold text-white truncate">
                  รายละเอียด: {previewItem.title}
                </h3>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1.5">
                <div className="text-slate-400 font-medium">ชื่อสินค้า:</div>
                <div className="text-white font-bold text-sm">{previewItem.productName}</div>
                {previewItem.productCode && (
                  <span className="inline-block px-2 py-0.5 rounded bg-slate-800 border border-white/10 text-slate-300 text-[10px] font-bold">
                    รหัส: {previewItem.productCode}
                  </span>
                )}
              </div>

              {previewItem.angle?.hook_title && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-1">
                  <div className="text-amber-400 font-bold">Hook Title (หัวข้อเปิดคลิป):</div>
                  <div className="text-white font-semibold text-sm leading-relaxed">{previewItem.angle.hook_title}</div>
                </div>
              )}

              {previewItem.angle?.script_text && (
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1.5">
                  <div className="text-slate-400 font-medium">บทพูดสคริปต์ (Script):</div>
                  <div className="text-slate-200 leading-relaxed max-h-40 overflow-y-auto p-2 rounded bg-black/40 whitespace-pre-wrap font-sans">
                    {previewItem.angle.script_text}
                  </div>
                </div>
              )}

              {previewItem.angle?.key_features && (
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1">
                  <div className="text-slate-400 font-medium">จุดเด่นสินค้า:</div>
                  <div className="text-slate-200">{previewItem.angle.key_features}</div>
                </div>
              )}

              {previewItem.caption && (
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 space-y-1">
                  <div className="text-slate-400 font-medium">แคปชัน & แฮชแท็ก:</div>
                  <div className="text-slate-200 font-sans">{previewItem.caption}</div>
                  {previewItem.hashtags && <div className="text-cyan-400 mt-1">{previewItem.hashtags}</div>}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/10">
              <button
                type="button"
                onClick={() => setPreviewItem(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 cursor-pointer"
              >
                ปิดหน้าต่าง
              </button>

              {previewItem.parentProduct && previewItem.angle && (
                <button
                  type="button"
                  onClick={() => {
                    const itemToOpen = previewItem;
                    setPreviewItem(null);
                    onApplyToStudio?.({
                      fullProduct: itemToOpen.parentProduct,
                      angleIndex: itemToOpen.parentProduct.angles?.findIndex(a => a.angle_id === itemToOpen.angle.angle_id) || 0,
                      openExisting: !!itemToOpen.projectName,
                      openProjectName: itemToOpen.projectName,
                    });
                  }}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-md shadow-amber-500/25"
                >
                  <Clapperboard className="w-3.5 h-3.5" />
                  <span>เริ่มตัดต่อคลิปนี้ทันที</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── AI Angle Proposal Modal (AI Idea-to-Script) ── */}
      {aiProposal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn"
          onClick={() => setAiProposal(null)}
        >
          <div
            className="w-full max-w-lg rounded-2xl bg-[#0F1420] border border-amber-500/30 p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <span className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Sparkles className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">AI สังเคราะห์สคริปต์จากเรฟ</h3>
                  <p className="text-xs text-slate-400">แปลงไอเดียเป็นมุมมองวิดีโอขายดีพร้อมนำไปตัดต่อ</p>
                </div>
              </div>
              <button
                onClick={() => setAiProposal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 text-xs">
              <div>
                <label className="block text-[11px] font-bold text-slate-400 mb-1">ชื่อมุมมอง (Angle Name)</label>
                <input
                  type="text"
                  value={aiProposal.angle_name}
                  onChange={(e) => setAiProposal({ ...aiProposal, angle_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs font-bold text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-amber-400 mb-1">หัวข้อฮุกเปิดคลิป (Hook Title)</label>
                <input
                  type="text"
                  value={aiProposal.hook_title}
                  onChange={(e) => setAiProposal({ ...aiProposal, hook_title: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-amber-500/30 text-xs font-bold text-amber-300 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 mb-1">กลุ่มเป้าหมาย</label>
                  <p className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 text-slate-300 text-[11px]">
                    {aiProposal.target_audience}
                  </p>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 mb-1">Pain Point ปัญหาที่เน้น</label>
                  <p className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 text-slate-300 text-[11px]">
                    {aiProposal.pain_point}
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-cyan-400 mb-1">คำแนะนำมุมกล้องและการถ่าย (Shoot Brief)</label>
                <div className="p-3 rounded-xl bg-cyan-950/20 border border-cyan-500/20 text-slate-200 text-xs leading-relaxed whitespace-pre-line">
                  {aiProposal.shoot_angle_brief}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">บทพูดพากย์ย่อ (Voiceover Script)</label>
                <textarea
                  rows={3}
                  value={aiProposal.script_brief}
                  onChange={(e) => setAiProposal({ ...aiProposal, script_brief: e.target.value })}
                  className="w-full p-3 rounded-xl bg-slate-900 border border-white/10 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-amber-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">ผูกเข้ากับสินค้าเป้าหมาย</label>
                <select
                  value={aiProposal.product_id}
                  onChange={(e) => setAiProposal({ ...aiProposal, product_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-amber-500 cursor-pointer"
                >
                  {products.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.product_code ? `[${p.product_code}] ` : ''}{p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex items-center justify-between">
              <button
                onClick={() => setAiProposal(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer transition-colors"
              >
                ยกเลิก
              </button>
              <button
                onClick={handleConfirmAddAngle}
                disabled={addingAngle}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all"
              >
                {addingAngle ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>{addingAngle ? 'กำลังบันทึก...' : 'เพิ่มเป็นมุมมองสินค้า (Add to Angles)'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast Notification ── */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs shadow-2xl flex items-center gap-2 animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
