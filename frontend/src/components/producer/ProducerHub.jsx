import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Sparkles, Flame, CheckCircle2, Clock, Play, ArrowRight,
  TrendingUp, AlertTriangle, Lightbulb, Target, Settings,
  Copy, Check, Plus, Trash2, Video, Film, Eye, Share2, ThumbsUp,
  RefreshCw, Clapperboard, ChevronRight, Zap, Scissors, Compass,
  BookOpen, FileText, ExternalLink, X, Bookmark, Image as ImageIcon,
  Link as LinkIcon, Smartphone, Filter, Tag, Loader2, Clipboard, Search
} from 'lucide-react';
import {
  getProducts, getExports, getTiktokStatsLatest,
  uploadRefMedia, aiIdeaToAngle, addProductAngle,
  getProducerNotes, addProducerNote, deleteProducerNote
} from '../../api';
import {
  loadTargets,
  saveTargets,
  loadPlaybookNotes,
  savePlaybookNotes,
  addPlaybookNote,
  deletePlaybookNote,
  formatNoteForSharing,
  detectRefPlatform,
  calculateProductionStats,
  getDailyActionQueue,
  getNextAction,
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
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const [partialFailures, setPartialFailures] = useState([]);

  // Targets state
  const [targets, setTargets] = useState(() => loadTargets());
  const [showTargetsModal, setShowTargetsModal] = useState(false);
  const [editingTargets, setEditingTargets] = useState({ ...targets });

  // Playbook & Idea/Ref Vault state
  const [playbookNotes, setPlaybookNotes] = useState(() => loadPlaybookNotes());
  const [ideaText, setIdeaText] = useState('');
  const [ideaUrl, setIdeaUrl] = useState('');
  const [ideaImages, setIdeaImages] = useState([]);
  const [ideaTag, setIdeaTag] = useState('Hook');
  const [ideaProduct, setIdeaProduct] = useState('');
  const [uploadingRefImage, setUploadingRefImage] = useState(false);
  const [failedRefUploads, setFailedRefUploads] = useState(0);
  const [refSaveSuccess, setRefSaveSuccess] = useState(false);
  const [activeZoomImage, setActiveZoomImage] = useState(null);
  const fileInputRef = useRef(null);

  // AI Idea-to-Script state
  const [aiSynthesizingId, setAiSynthesizingId] = useState(null);
  const [aiProposal, setAiProposal] = useState(null);
  const [addingAngle, setAddingAngle] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Queue filter
  const [queueFilter, setQueueFilter] = useState('all'); // 'all' | 'post' | 'cut' | 'footage'
  const [productFilter, setProductFilter] = useState('all'); // 'all' | productId
  const [queueSearch, setQueueSearch] = useState('');
  const [queueSort, setQueueSort] = useState('priority'); // 'priority' | 'oldest' | 'product'
  const [queueLimit, setQueueLimit] = useState(10);

  // Clipboard copy state
  const [copiedId, setCopiedId] = useState(null);

  // Quick Preview Modal state
  const [previewItem, setPreviewItem] = useState(null);

  useEffect(() => {
    if (!showTargetsModal && !previewItem && !aiProposal && !activeZoomImage) return undefined;
    const handleModalKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      if (activeZoomImage) setActiveZoomImage(null);
      else if (aiProposal) setAiProposal(null);
      else if (previewItem) setPreviewItem(null);
      else setShowTargetsModal(false);
    };
    document.addEventListener('keydown', handleModalKeyDown);
    return () => document.removeEventListener('keydown', handleModalKeyDown);
  }, [activeZoomImage, aiProposal, previewItem, showTargetsModal]);

  // Load data from APIs
  const fetchData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [prodRes, expRes, statsRes, notesRes] = await Promise.allSettled([
        getProducts(),
        getExports(),
        getTiktokStatsLatest(),
        getProducerNotes(),
      ]);

      const sourceResults = [
        ['สินค้า', prodRes],
        ['ไฟล์ Export', expRes],
        ['สถิติ TikTok', statsRes],
        ['Playbook', notesRes],
      ];
      setPartialFailures(sourceResults
        .filter(([, result]) => result.status === 'rejected')
        .map(([label]) => label));
      setLastSyncedAt(new Date().toISOString());

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

      if (notesRes.status === 'fulfilled' && notesRes.value?.success && Array.isArray(notesRes.value?.notes)) {
        setPlaybookNotes(notesRes.value.notes);
        savePlaybookNotes(notesRes.value.notes);
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

  const syncLabel = lastSyncedAt
    ? `ซิงก์ล่าสุด ${new Intl.DateTimeFormat('th-TH', { hour: '2-digit', minute: '2-digit' }).format(new Date(lastSyncedAt))}`
    : 'ยังไม่ได้ซิงก์ข้อมูล';

  const playbookSuggestions = useMemo(() => {
    return autoSuggestPlaybookNotes(retrospective, playbookNotes);
  }, [retrospective, playbookNotes]);

  const handleSaveRetrospective = useCallback(async (item) => {
    if (!item || item.alreadySaved) return;
    const top = retrospective.topPerformer;
    const newNote = {
      id: `note-retro-${Date.now()}`,
      text: item.text,
      createdAt: new Date().toISOString(),
      tag: item.tag,
      provenance: {
        type: 'retrospective',
        source: retrospective.source,
        sourceClipId: top?.sourceId || null,
        sampleSize: retrospective.sampleSize,
        period: retrospective.period,
        confidence: retrospective.confidence,
        metricSnapshot: top?.metricSnapshot || retrospective.metrics,
      },
    };
    const previousNotes = playbookNotes;
    const updated = [newNote, ...previousNotes];
    setPlaybookNotes(updated);
    savePlaybookNotes(updated);
    try {
      const res = await addProducerNote(newNote);
      if (res?.success && Array.isArray(res.notes)) {
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
    } catch (err) {
      setPlaybookNotes(previousNotes);
      savePlaybookNotes(previousNotes);
      setToastMessage('จดบทเรียนในเครื่องแล้ว แต่ซิงก์เซิร์ฟเวอร์ไม่สำเร็จ');
      setTimeout(() => setToastMessage(null), 3500);
      console.warn('Failed to sync retrospective note:', err);
    }
  }, [playbookNotes, retrospective]);

  // Next Mission Spotlight: pick the single most urgent task
  const nextMission = useMemo(() => {
    return getNextAction(actionQueue);
  }, [actionQueue]);

  const handleNextMission = useCallback(() => {
    if (!nextMission) {
      onGoToFlow?.();
      return;
    }

    if (nextMission.type === 'post') {
      onGoToGallery?.({
        targetId: nextMission.item.exportPath || nextMission.item.id,
        exportId: nextMission.item.id,
      });
      return;
    }

    if (nextMission.type === 'cut' && nextMission.item.parentProduct && nextMission.item.angle) {
      onApplyToStudio?.({
        fullProduct: nextMission.item.parentProduct,
        productId: nextMission.item.productId,
        angleId: nextMission.item.angle.angle_id,
        angleIndex: nextMission.item.parentProduct.angles?.findIndex(a => a.angle_id === nextMission.item.angle.angle_id) || 0,
        openExisting: !!nextMission.item.projectName,
        openProjectName: nextMission.item.projectName,
      });
      return;
    }

    if (nextMission.type === 'footage') {
      onGoToFlow?.(nextMission.item.productId || nextMission.item.parentProduct?.id);
      return;
    }

    onGoToEditor?.();
  }, [nextMission, onApplyToStudio, onGoToEditor, onGoToFlow, onGoToGallery]);

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

  // Append single image URL to ideaImages
  const appendIdeaImageUrl = (url) => {
    if (!url) return;
    setIdeaImages(prev => {
      if (prev.includes(url)) return prev;
      return [...prev, url];
    });
    setPastedImageToast(true);
    setTimeout(() => setPastedImageToast(false), 2500);
  };

  // Reusable Multi-Image Processor for Producer Hub
  const processRefImageFiles = async (files) => {
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);

    const pendingEntries = [];
    for (const file of fileList) {
      if (!file?.type?.startsWith('image/')) continue;
      try {
        const localData = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = () => reject(new Error('อ่านไฟล์ภาพไม่สำเร็จ'));
          reader.readAsDataURL(file);
        });
        const pendingUrl = `${localData}#omnicut-pending-${Date.now()}-${pendingEntries.length}`;
        pendingEntries.push({ file, pendingUrl });
        setIdeaImages(prev => [...prev, pendingUrl]);
      } catch (err) {
        console.warn('Failed to prepare reference image:', err);
        setFailedRefUploads(count => count + 1);
      }
    }

    if (pendingEntries.length === 0) return;
    setUploadingRefImage(true);
    setPastedImageToast(true);
    setTimeout(() => setPastedImageToast(false), 2500);

    for (const { file, pendingUrl } of pendingEntries) {
      try {
        const res = await uploadRefMedia(file);
        if (!res?.url) throw new Error('เซิร์ฟเวอร์ไม่คืนลิงก์รูปภาพ');
        setIdeaImages(prev => prev.map(img => (img === pendingUrl ? res.url : img)));
      } catch (err) {
        console.warn('Upload ref media to server failed:', err);
        setIdeaImages(prev => prev.filter(img => img !== pendingUrl));
        setFailedRefUploads(count => count + 1);
      }
    }
    setUploadingRefImage(false);
  };

  const removeIdeaImage = (indexToRemove) => {
    setIdeaImages(prev => prev.filter((_, idx) => idx !== indexToRemove));
  };

  // Handle Image Selection from File Picker (Supports multiple files)
  const handleImageSelect = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) processRefImageFiles(files);
  };

  // Intercept Ctrl+V or right-click Paste of images
  const handlePasteImageAnywhere = (e) => {
    const cd = e.clipboardData;
    if (!cd) return;

    // 1. Check cd.files first (iOS Safari & desktop copied images)
    if (cd.files && cd.files.length > 0) {
      const validFiles = [];
      for (let i = 0; i < cd.files.length; i++) {
        const file = cd.files[i];
        if (file && (file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|heic|heif|bmp)$/i.test(file.name || ''))) {
          validFiles.push(file);
        }
      }
      if (validFiles.length > 0) {
        e.preventDefault();
        processRefImageFiles(validFiles);
        return;
      }
    }

    // 2. Check cd.items
    const items = cd.items;
    if (items && items.length > 0) {
      const validFiles = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].type && items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) validFiles.push(file);
        }
      }
      if (validFiles.length > 0) {
        e.preventDefault();
        processRefImageFiles(validFiles);
        return;
      }
    }

    // 3. Check HTML content for <img> tag
    try {
      const html = cd.getData('text/html');
      if (html) {
        const matches = [...html.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)];
        const urls = matches.map(m => m[1]).filter(src => src && !src.startsWith('webkit-fake-url:'));
        if (urls.length > 0) {
          e.preventDefault();
          urls.forEach(appendIdeaImageUrl);
          return;
        }
      }
    } catch (_) {}

    // 4. Check text/plain for direct image URL or base64
    try {
      const text = cd.getData('text/plain');
      if (text) {
        const trimmed = text.trim();
        if (trimmed.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(trimmed)) {
          e.preventDefault();
          appendIdeaImageUrl(trimmed);
          return;
        }
      }
    } catch (_) {}
  };

  // Drag & drop image support
  const handleDropImage = (e) => {
    e.preventDefault();
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      processRefImageFiles(files);
    }
  };

  // 1-Tap Read Image directly from Clipboard with Photo Picker fallback
  const handlePasteImageFromClipboard = async () => {
    if (!navigator.clipboard?.read) {
      fileInputRef.current?.click();
      return;
    }

    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            const blob = await item.getType(type);
            const file = new File([blob], `pasted_ref_${Date.now()}.png`, { type });
            processRefImageFiles([file]);
            return;
          }
          if (type === 'text/plain') {
            const blob = await item.getType(type);
            const text = await blob.text();
            const trimmed = text.trim();
            if (trimmed.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(trimmed)) {
              appendIdeaImageUrl(trimmed);
              return;
            }
          }
        }
      }
      fileInputRef.current?.click();
    } catch (err) {
      console.warn('Clipboard read error:', err);
      fileInputRef.current?.click();
    }
  };

  // Handle Add Idea / Ref Note
  const handleSaveIdea = async (e) => {
    if (e) e.preventDefault();
    if (!ideaText.trim() && !ideaUrl.trim() && ideaImages.length === 0) return;

    const matchedProd = products.find(p => p.id === ideaProduct);
    if (ideaImages.some(img => img.includes('#omnicut-pending-'))) return;
    const newNote = {
      text: ideaText.trim(),
      url: ideaUrl.trim() || undefined,
      images: ideaImages,
      imageUrl: ideaImages[0] || undefined,
      tag: ideaTag || 'Hook',
      productId: ideaProduct || undefined,
      productName: matchedProd?.name || undefined,
      productCode: matchedProd?.product_code || undefined,
      createdAt: new Date().toISOString(),
    };

    const updated = addPlaybookNote(newNote, playbookNotes);
    const localNote = updated[0];
    setPlaybookNotes(updated);
    setIdeaText('');
    setIdeaUrl('');
    setIdeaImages([]);
    setRefSaveSuccess(true);
    setTimeout(() => setRefSaveSuccess(false), 2500);

    // Sync one item so another device cannot be overwritten by a stale list.
    try {
      const res = await addProducerNote(localNote);
      if (res?.success && Array.isArray(res.notes)) {
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
    } catch (err) {
      setPlaybookNotes(playbookNotes);
      savePlaybookNotes(playbookNotes);
      setToastMessage('บันทึกในเครื่องแล้ว แต่ซิงก์เซิร์ฟเวอร์ไม่สำเร็จ กรุณาลองใหม่');
      setTimeout(() => setToastMessage(null), 3500);
      console.warn('Failed to sync note to server:', err);
    }
  };

  // Handle Delete Note
  const handleDeleteNote = async (id) => {
    const updated = deletePlaybookNote(id, playbookNotes);
    setPlaybookNotes(updated);
    try {
      const res = await deleteProducerNote(id);
      if (res?.success && Array.isArray(res.notes)) {
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
    } catch (err) {
      setPlaybookNotes(playbookNotes);
      savePlaybookNotes(playbookNotes);
      setToastMessage('ลบในเครื่องแล้ว แต่ซิงก์เซิร์ฟเวอร์ไม่สำเร็จ รายการถูกคืนกลับ');
      setTimeout(() => setToastMessage(null), 3500);
      console.warn('Failed to delete note on server:', err);
    }
  };

  // One-click Copy/Share note for Boss or Team
  const handleCopyNoteForBoss = (item) => {
    const text = formatNoteForSharing(item);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setToastMessage('คัดลอกสรุปไอเดียและรูปภาพทั้งหมดลงคลิปบอร์ดแล้ว พร้อมส่งต่อ!');
      setTimeout(() => setToastMessage(null), 3000);
    } else {
      alert(text);
    }
  };

  // Handle Trigger AI Idea-to-Script
  const handleRunAiIdeaToScript = async (note) => {
    try {
      setAiSynthesizingId(note.id);
      const itemImages = Array.isArray(note.images) && note.images.length > 0
        ? note.images
        : (note.imageUrl ? [note.imageUrl] : []);

      const res = await aiIdeaToAngle({
        idea_text: note.text,
        ref_url: note.url,
        ref_image: itemImages[0] || '',
        ref_images: itemImages,
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
        i.productId === productFilter ||
        i.parentProduct?.id === productFilter ||
        i.productCode === productFilter ||
        i.productName === productFilter
      ));
    }

    const normalizedQuery = queueSearch.trim().toLowerCase();
    if (normalizedQuery) {
      base = base.filter(item => [item.title, item.productName, item.productCode, item.projectName]
        .filter(Boolean)
        .some(value => String(value).toLowerCase().includes(normalizedQuery)));
    }

    const categoryRank = { post: 0, cut: 1, footage: 2 };
    base.sort((a, b) => {
      if (queueSort === 'product') {
        return String(a.productName || '').localeCompare(String(b.productName || ''), 'th') || String(a.title || '').localeCompare(String(b.title || ''), 'th');
      }
      const aDate = new Date(a.updatedAt || 0).getTime() || 0;
      const bDate = new Date(b.updatedAt || 0).getTime() || 0;
      if (queueSort === 'oldest') return aDate - bDate;
      return (categoryRank[a.queueCategory] ?? 9) - (categoryRank[b.queueCategory] ?? 9) || aDate - bDate;
    });

    return base;
  }, [actionQueue, queueFilter, productFilter, queueSearch, queueSort]);

  useEffect(() => {
    setQueueLimit(10);
  }, [queueFilter, productFilter, queueSearch, queueSort]);

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
                  {syncLabel} · เป้าสัปดาห์นี้ {targets.weeklyCuts} คลิป
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
              onClick={handleNextMission}
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

      {partialFailures.length > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-100 flex items-start gap-2" role="status" aria-live="polite">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <strong className="text-amber-300">ข้อมูลบางส่วนยังไม่พร้อม</strong>
            <p className="mt-0.5 text-amber-100/80">{partialFailures.join(', ')} โหลดไม่สำเร็จ กดรีเฟรชเพื่อลองใหม่ได้</p>
          </div>
        </div>
      )}

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
                  <span className="text-slate-400 ml-1.5">· {nextMission.description} · {nextMission.priorityReason}</span>
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
                  onClick={handleNextMission}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-rose-500/25 transition-all"
                >
                  <Flame className="w-4 h-4" />
                  <span>ส่ง TikTok ตอนนี้เลย</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {nextMission.type === 'cut' && (
                <button
                  onClick={handleNextMission}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-amber-500/25 transition-all"
                >
                  <Clapperboard className="w-4 h-4" />
                  <span>เริ่มตัดต่อคลิปนี้ทันที</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {nextMission.type === 'footage' && (
                <button
                  onClick={handleNextMission}
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
                multiple
                onChange={handleImageSelect}
                className="hidden"
              />

              <button
                type="button"
                onClick={handlePasteImageFromClipboard}
                disabled={uploadingRefImage || ideaImages.some(img => img.includes('#omnicut-pending-'))}
                className="px-2.5 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                title="อ่านรูปภาพจากคลิปบอร์ดที่เพิ่งแคปหน้าจอมา (กด Ctrl+V หรือคลิกวางได้เรื่อยๆ หลายรูป)"
              >
                <Clipboard className="w-3.5 h-3.5" />
                <span>วางรูปภาพ</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingRefImage || ideaImages.some(img => img.includes('#omnicut-pending-'))}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-all"
                title="เลือกรูปภาพจากเครื่อง (เลือกพร้อมกันได้หลายรูป)"
              >
                <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>{ideaImages.length > 0 ? `แนบเพิ่ม (${ideaImages.length} รูป)` : 'แนบไฟล์ภาพ'}</span>
              </button>

              {pastedImageToast && (
                <span className="text-[11px] font-bold text-emerald-400 animate-pulse">
                  วางรูปภาพเรียบร้อย!
                </span>
              )}
              {failedRefUploads > 0 && (
                <span className="text-[11px] font-semibold text-rose-300">
                  อัปโหลดภาพไม่สำเร็จ {failedRefUploads} ไฟล์
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
            </div>

            <button
              type="submit"
              disabled={uploadingRefImage || ideaImages.some(img => img.includes('#omnicut-pending-')) || (!ideaText.trim() && !ideaUrl.trim() && ideaImages.length === 0)}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer shadow-md shadow-amber-500/20 disabled:opacity-40 transition-all"
            >
              {refSaveSuccess ? <Check className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
              <span>{refSaveSuccess ? 'บันทึกเรียบร้อย' : 'บันทึกไอเดีย'}</span>
            </button>
          </div>

          {/* Multi-Image Preview Strip in Form */}
          {ideaImages.length > 0 && (
            <div className="pt-2 border-t border-white/5 space-y-1.5">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-bold text-amber-300">รูปภาพที่แนบ ({ideaImages.length} รูป)</span>
                <span className="text-[10px]">กดปุ่ม X เพื่อลบรูปที่ไม่ต้องการ</span>
              </div>
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {ideaImages.map((img, idx) => (
                  <div key={idx} className="relative group/thumb flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden border border-white/15 bg-black/50">
                    <img src={img} alt={`Preview ${idx + 1}`} className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={() => removeIdeaImage(idx)}
                      className="absolute top-1 right-1 p-0.5 rounded-md bg-rose-600/90 text-white opacity-90 group-hover/thumb:opacity-100 hover:bg-rose-700 transition-all cursor-pointer"
                      title="ลบรูปนี้"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    <span className="absolute bottom-1 left-1 px-1 py-0.2 rounded bg-black/60 text-[9px] text-slate-300 font-bold">
                      #{idx + 1}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </form>

        {/* Saved Ideas / Refs List */}
        {playbookNotes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto pr-1">
            {playbookNotes.map((item) => {
              const platform = detectRefPlatform(item.url);
              const isSynthesizing = aiSynthesizingId === item.id;
              const itemImages = Array.isArray(item.images) && item.images.length > 0
                ? item.images
                : (item.imageUrl ? [item.imageUrl] : []);

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
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteNote(item.id);
                        }}
                        className="px-2 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 text-xs font-semibold flex items-center gap-1 cursor-pointer active:scale-95 transition-all shadow-sm"
                        title="ลบรายการนี้"
                      >
                        <Trash2 className="w-3 h-3 text-rose-400" />
                        <span>ลบ</span>
                      </button>
                    </div>

                    {item.text && (
                      <p className="text-xs text-slate-200 leading-relaxed font-medium line-clamp-3">
                        {item.text}
                      </p>
                    )}

                    {/* Multi-Image Gallery */}
                    {itemImages.length === 1 && (
                      <div
                        onClick={() => setActiveZoomImage(itemImages[0])}
                        className="relative rounded-lg overflow-hidden border border-white/10 max-h-28 bg-black/40 cursor-zoom-in group/img"
                        title="คลิกเพื่อดูรูปขยายใหญ่"
                      >
                        <img
                          src={itemImages[0]}
                          alt="Ref media"
                          className="w-full h-28 object-cover group-hover/img:scale-105 transition-transform"
                        />
                      </div>
                    )}

                    {itemImages.length > 1 && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-amber-300 font-bold">
                          <span className="flex items-center gap-1">
                            <ImageIcon className="w-3 h-3" />
                            <span>{itemImages.length} รูป</span>
                          </span>
                          <span className="text-[9px] text-slate-500 font-normal">คลิกเพื่อดูรูป</span>
                        </div>
                        <div className={`grid gap-1 ${itemImages.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}`}>
                          {itemImages.slice(0, 3).map((imgUrl, imgIdx) => {
                            const isLastAndMore = imgIdx === 2 && itemImages.length > 3;
                            return (
                              <div
                                key={imgIdx}
                                onClick={() => setActiveZoomImage(imgUrl)}
                                className="relative h-16 rounded-lg overflow-hidden border border-white/10 bg-black/40 cursor-pointer group/thumb hover:border-amber-500/40 transition-all"
                              >
                                <img
                                  src={imgUrl}
                                  alt={`Ref ${imgIdx + 1}`}
                                  className="w-full h-full object-cover group-hover/thumb:scale-110 transition-transform"
                                />
                                {isLastAndMore && (
                                  <div className="absolute inset-0 bg-black/70 flex items-center justify-center font-bold text-white text-[10px]">
                                    +{itemImages.length - 2}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
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

                  {/* Actions: Copy for Boss + AI Idea-to-Script Button */}
                  <div className="pt-2 border-t border-white/5 flex items-center justify-between gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleCopyNoteForBoss(item)}
                      className="px-2 py-1 rounded-lg bg-slate-700/70 hover:bg-slate-700 text-slate-200 hover:text-white border border-white/5 text-[11px] font-semibold flex items-center gap-1 cursor-pointer active:scale-95 transition-all"
                      title="คัดลอกสรุปไอเดียและรูปภาพทั้งหมดสำหรับส่งไลน์ให้นายหรือทีมงาน"
                    >
                      <Copy className="w-3 h-3 text-cyan-400" />
                      <span>คัดลอกส่งงาน</span>
                    </button>

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

        <div className="flex flex-col sm:flex-row gap-2.5">
          <label className="relative flex-1 min-w-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            <span className="sr-only">ค้นหางานในคิว</span>
            <input
              type="search"
              value={queueSearch}
              onChange={(e) => setQueueSearch(e.target.value)}
              placeholder="ค้นหาชื่อฮุก สินค้า รหัส หรือไทม์ไลน์"
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950/70 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <span className="sr-only">เรียงลำดับคิว</span>
            <select
              value={queueSort}
              onChange={(e) => setQueueSort(e.target.value)}
              className="px-3 py-2 rounded-xl bg-slate-950/70 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-amber-500 cursor-pointer"
            >
              <option value="priority">เรียงตามความเร่งด่วน</option>
              <option value="oldest">งานเก่าที่สุดก่อน</option>
              <option value="product">เรียงตามสินค้า</option>
            </select>
          </label>
          <span className="flex items-center text-[11px] text-slate-500 whitespace-nowrap">
            แสดง {Math.min(queueLimit, displayQueue.length)} จาก {displayQueue.length} งาน
          </span>
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
            {displayQueue.slice(0, queueLimit).map((item, idx) => {
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
                          onClick={() => onGoToGallery?.({
                            targetId: item.exportPath || item.id,
                            exportId: item.id,
                          })}
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
            {displayQueue.length > queueLimit && (
              <button
                type="button"
                onClick={() => setQueueLimit(limit => limit + 10)}
                className="w-full py-2.5 rounded-xl bg-slate-800/70 hover:bg-slate-700/80 border border-white/10 text-xs font-bold text-slate-300 hover:text-white cursor-pointer transition-colors"
              >
                แสดงงานเพิ่มอีก {Math.min(10, displayQueue.length - queueLimit)} งาน
              </button>
            )}
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
              <h2 className="text-base font-bold text-white">ถอดรหัสคลิปปัง & สถิติ (Automatic Retrospective)</h2>
              <span className="text-[10px] font-semibold text-slate-500 border border-white/10 rounded px-1.5 py-0.5">
                {retrospective.method === 'heuristic' ? 'ข้อเสนอจาก heuristic' : 'จากข้อมูลจริง'}
              </span>
            </div>

            <div className="mb-3 text-[11px] text-slate-500">
              แหล่งข้อมูล: {retrospective.source === 'tiktok_stats_latest' ? 'TikTok Studio ล่าสุด' : 'ยังไม่มีสถิติ TikTok Studio'} · ตัวอย่าง {retrospective.sampleSize} คลิป · ความมั่นใจ {retrospective.confidence}
            </div>
            <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-slate-400">
              <div className="rounded-lg bg-slate-800/50 border border-white/5 px-2.5 py-2">
                <span className="block text-slate-500">ค่าเฉลี่ยวิว</span>
                <strong className="text-white">{retrospective.metrics.averageViews.toLocaleString()}</strong>
              </div>
              <div className="rounded-lg bg-slate-800/50 border border-white/5 px-2.5 py-2">
                <span className="block text-slate-500">ค่ากลางวิว</span>
                <strong className="text-white">{retrospective.metrics.medianViews.toLocaleString()}</strong>
              </div>
              <div className="rounded-lg bg-slate-800/50 border border-white/5 px-2.5 py-2">
                <span className="block text-slate-500">Engagement</span>
                <strong className="text-white">{retrospective.metrics.engagementRate.toFixed(2)}%</strong>
              </div>
              <div className="rounded-lg bg-slate-800/50 border border-white/5 px-2.5 py-2">
                <span className="block text-slate-500">ช่วงข้อมูล</span>
                <strong className="text-white">{retrospective.period.from ? new Intl.DateTimeFormat('th-TH', { day: 'numeric', month: 'short' }).format(new Date(retrospective.period.from)) : 'ไม่มีวันที่'}</strong>
              </div>
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
                <p className="mt-1 text-[10px] text-slate-500 truncate">Source clip: {retrospective.topPerformer.sourceId}</p>
              </div>
            )}

            <div className="space-y-2.5 mb-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>💡 จุดเด่นที่ทำให้ยอดพุ่ง</span>
                <span className="text-[10px] text-amber-400 lowercase font-normal">คลิกเพื่อจดลง Playbook ได้ทันที</span>
              </h4>
              {playbookSuggestions.map((item) => (
                <div key={item.id || i} className="flex items-center justify-between gap-3 text-xs text-slate-300 bg-slate-800/30 p-2.5 rounded-lg border border-white/5 group hover:border-amber-500/30 transition-all">
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                    <span className="leading-relaxed">{item.text}</span>
                  </div>
                  <button
                    onClick={() => handleSaveRetrospective(item)}
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
          <div role="dialog" aria-modal="true" aria-labelledby="producer-targets-title" className="w-full max-w-md bg-slate-900 border border-white/15 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-amber-400" />
                <h3 id="producer-targets-title" className="text-base font-bold text-white">ตั้งเป้าหมายการผลิต (Quotas)</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowTargetsModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
                aria-label="ปิดหน้าต่างตั้งเป้าหมาย"
              >
                <X className="w-5 h-5" />
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
          <div role="dialog" aria-modal="true" aria-labelledby="producer-preview-title" className="w-full max-w-lg bg-slate-900 border border-white/15 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <h3 id="producer-preview-title" className="text-base font-bold text-white truncate">
                  รายละเอียด: {previewItem.title}
                </h3>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg cursor-pointer"
                aria-label="ปิดรายละเอียด"
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
            role="dialog"
            aria-modal="true"
            aria-labelledby="producer-ai-proposal-title"
            className="w-full max-w-lg rounded-2xl bg-[#0F1420] border border-amber-500/30 p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <span className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Sparkles className="w-5 h-5" />
                </span>
                <div>
                  <h3 id="producer-ai-proposal-title" className="text-base font-bold text-white">AI สังเคราะห์สคริปต์จากเรฟ</h3>
                  <p className="text-xs text-slate-400">แปลงไอเดียเป็นมุมมองวิดีโอขายดีพร้อมนำไปตัดต่อ</p>
                </div>
              </div>
              <button
                onClick={() => setAiProposal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="ปิดข้อเสนอจาก AI"
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

      {/* ── Lightbox Image Modal ── */}
      {activeZoomImage && (
        <div
          onClick={() => setActiveZoomImage(null)}
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-zoom-out animate-fadeIn"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="ดูภาพเรฟขนาดใหญ่"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="ดูภาพเรฟขนาดใหญ่"
            className="relative max-w-4xl max-h-[90vh] flex flex-col items-center gap-3 cursor-default"
          >
            <button
              type="button"
              onClick={() => setActiveZoomImage(null)}
              className="absolute -top-11 right-0 p-2 rounded-full bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white cursor-pointer transition-colors shadow-lg"
              title="ปิดรูปขยาย"
              aria-label="ปิดรูปขยาย"
              aria-label="ปิดรูปขยาย"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={activeZoomImage}
              alt="Zoomed Reference"
              className="max-h-[80vh] max-w-full rounded-2xl object-contain shadow-2xl border border-white/10"
            />
            <div className="flex items-center gap-3">
              <a
                href={activeZoomImage}
                target="_blank"
                rel="noreferrer"
                className="px-3.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-xs font-semibold text-cyan-300 border border-white/10 flex items-center gap-1.5 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>เปิดรูปขนาดเต็มในแท็บใหม่</span>
              </a>
              <button
                type="button"
                onClick={() => {
                  if (navigator.clipboard?.writeText) {
                    navigator.clipboard.writeText(activeZoomImage);
                    setToastMessage('คัดลอกลิงก์รูปภาพแล้ว!');
                    setTimeout(() => setToastMessage(null), 2000);
                  }
                }}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-white/10 flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Copy className="w-3.5 h-3.5 text-amber-400" />
                <span>คัดลอกลิงก์รูป</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast Notification ── */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs shadow-2xl flex items-center gap-2 animate-bounce" role="status" aria-live="polite">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
