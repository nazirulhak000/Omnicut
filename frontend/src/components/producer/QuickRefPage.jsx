import React, { useState, useEffect, useRef } from 'react';
import {
  Bookmark, Link as LinkIcon, Image as ImageIcon, Sparkles,
  ArrowLeft, Check, Trash2, ExternalLink, X, Smartphone, Tag,
  Clipboard, Search, Loader2, PlayCircle, Eye, Volume2, Flame,
  Share2, Copy, Filter, Film, PlusCircle
} from 'lucide-react';
import {
  loadPlaybookNotes,
  addPlaybookNote,
  deletePlaybookNote,
  detectRefPlatform
} from '../../lib/producerInsights';
import { getProducts, uploadRefMedia, aiIdeaToAngle, addProductAngle } from '../../api';

// Predefined Ref Categories with ergonomic pills
const CATEGORIES = [
  { id: 'Ref Clip', label: 'เรฟคลิป', icon: Film, desc: 'ตัวอย่างสไตล์การตัดต่อหรือมู้ดคลิป' },
  { id: 'Hook', label: 'Hook เปิดคลิป', icon: Flame, desc: 'ประเด็นสะดุดตา 3 วินาทีแรก' },
  { id: 'Visual', label: 'มุมกล้อง / Visual', icon: Eye, desc: 'มุมถ่ายสวยๆ หรือเทคนิคโชว์สินค้า' },
  { id: 'Audio', label: 'เสียง / เพลง', icon: Volume2, desc: 'ซาวด์แทร็ก เพลงฮิต หรือแนวเสียงพากย์' },
  { id: 'Promo', label: 'โปรโมชั่น', icon: Tag, desc: 'เทคนิคปิดการขาย การแจกโค้ด' },
];

export default function QuickRefPage({ onExit }) {
  const [notes, setNotes] = useState(() => loadPlaybookNotes());
  const [products, setProducts] = useState([]);
  const [ideaText, setIdeaText] = useState('');
  const [refUrl, setRefUrl] = useState('');
  const [selectedTag, setSelectedTag] = useState('Ref Clip');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [previewImage, setPreviewImage] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [pasteSuccess, setPasteSuccess] = useState(false);
  const [pastedImageToast, setPastedImageToast] = useState(false);
  const [clipboardHelpToast, setClipboardHelpToast] = useState(false);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTag, setFilterTag] = useState('all');

  // AI Idea-to-Script State
  const [aiSynthesizingId, setAiSynthesizingId] = useState(null);
  const [aiProposal, setAiProposal] = useState(null);
  const [addingAngle, setAddingAngle] = useState(false);
  const [angleAddedSuccess, setAngleAddedSuccess] = useState(false);

  // Mobile Tab State: 'capture' (จดใหม่) or 'vault' (คลังที่เซฟ)
  const [mobileTab, setMobileTab] = useState('capture');

  const fileInputRef = useRef(null);

  useEffect(() => {
    getProducts()
      .then(res => {
        const list = Array.isArray(res) ? res : (res?.products || []);
        setProducts(list);
      })
      .catch(() => {});
  }, []);

  // 1-Tap Paste URL from Clipboard
  const handlePasteClipboard = async () => {
    try {
      if (!navigator.clipboard?.readText) {
        alert('เบราว์เซอร์ไม่อนุญาตให้อ่านคลิปบอร์ดอัตโนมัติ กรุณากดแปะในช่องด้วยตัวเอง');
        return;
      }
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        setRefUrl(text.trim());
        setPasteSuccess(true);
        setTimeout(() => setPasteSuccess(false), 1500);
      }
    } catch (err) {
      console.warn('Clipboard read error:', err);
    }
  };

  // Reusable Image Processor (Used by File Picker, Ctrl+V Paste, and Clipboard Button)
  const processImageFile = async (file) => {
    if (!file) return;

    // Instant local preview
    const reader = new FileReader();
    reader.onload = () => {
      setPreviewImage(reader.result);
      setPastedImageToast(true);
      setTimeout(() => setPastedImageToast(false), 2500);
    };
    reader.readAsDataURL(file);

    // Upload to server 02_Assets/Refs/
    try {
      setUploadingImage(true);
      const uploadRes = await uploadRefMedia(file);
      if (uploadRes?.url) {
        setPreviewImage(uploadRes.url);
      }
    } catch (err) {
      console.warn('Server image upload failed, using local preview:', err);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) processImageFile(file);
  };

  // Intercept Ctrl+V or right-click Paste in textarea, contenteditable, or card
  const handlePasteAnywhere = (e) => {
    const cd = e.clipboardData;
    if (!cd) return;

    // 1. Check cd.files FIRST (This is where iOS Safari and desktop file pastes put copied photos!)
    if (cd.files && cd.files.length > 0) {
      for (let i = 0; i < cd.files.length; i++) {
        const file = cd.files[i];
        if (file && (file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|heic|heif|bmp)$/i.test(file.name || ''))) {
          e.preventDefault();
          processImageFile(file);
          return;
        }
      }
    }

    // 2. Check cd.items (Chrome / Android / Chromium-based browsers)
    if (cd.items && cd.items.length > 0) {
      for (let i = 0; i < cd.items.length; i++) {
        const item = cd.items[i];
        if (item.type && item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            processImageFile(file);
            return;
          }
        }
      }
    }

    // 3. Check HTML content for <img> tag (when user copies image from Pinterest or web page)
    try {
      const html = cd.getData('text/html');
      if (html) {
        const match = html.match(/<img[^>]+src=["']([^"']+)["']/i);
        if (match && match[1] && !match[1].startsWith('webkit-fake-url:')) {
          e.preventDefault();
          setPreviewImage(match[1]);
          setPastedImageToast(true);
          setTimeout(() => setPastedImageToast(false), 2500);
          return;
        }
      }
    } catch (_) {}

    // 4. Check plain text for direct image link or base64 data URL
    try {
      const text = cd.getData('text/plain');
      if (text) {
        const trimmed = text.trim();
        if (trimmed.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(trimmed)) {
          e.preventDefault();
          setPreviewImage(trimmed);
          setPastedImageToast(true);
          setTimeout(() => setPastedImageToast(false), 2500);
          return;
        }
      }
    } catch (_) {}
  };

  // ContentEditable input catcher (Failsafe for iOS Safari native image insertion)
  const handleContentEditableInput = (e) => {
    const container = e.currentTarget;
    const img = container.querySelector('img');
    if (img && img.src) {
      if (!img.src.startsWith('webkit-fake-url:')) {
        setPreviewImage(img.src);
        setPastedImageToast(true);
        setTimeout(() => setPastedImageToast(false), 2500);
      }
    }
    const text = container.innerText?.trim();
    if (text && (text.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(text))) {
      setPreviewImage(text);
      setPastedImageToast(true);
      setTimeout(() => setPastedImageToast(false), 2500);
    }
    container.innerHTML = '';
  };

  // Drag & drop image support
  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (file && file.type.startsWith('image/')) {
      processImageFile(file);
    }
  };

  // 1-Tap Read Image from Clipboard with seamless guidance
  const handlePasteImageFromClipboard = async () => {
    // If clipboard.read is not supported (e.g. mobile Safari default or non-HTTPS),
    // trigger file picker immediately & synchronously so Safari does not block it!
    if (!navigator.clipboard?.read) {
      fileInputRef.current?.click();
      return;
    }

    try {
      setUploadingImage(true);
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            const blob = await item.getType(type);
            const file = new File([blob], `pasted_ref_${Date.now()}.png`, { type });
            processImageFile(file);
            return;
          }
          if (type === 'text/plain') {
            const blob = await item.getType(type);
            const text = await blob.text();
            const trimmed = text.trim();
            if (trimmed.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(trimmed)) {
              setPreviewImage(trimmed);
              setPastedImageToast(true);
              setTimeout(() => setPastedImageToast(false), 2500);
              return;
            }
          }
        }
      }
      setClipboardHelpToast(true);
      setTimeout(() => setClipboardHelpToast(false), 4000);
    } catch (err) {
      console.warn('Clipboard read error (iOS Safari permission):', err);
      setClipboardHelpToast(true);
      setTimeout(() => setClipboardHelpToast(false), 4000);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSave = () => {
    if (!ideaText.trim() && !refUrl.trim() && !previewImage) return;

    const matchedProduct = products.find(p => p.id === selectedProductId);
    const newNote = {
      text: ideaText.trim(),
      url: refUrl.trim() || undefined,
      imageUrl: previewImage || undefined,
      tag: selectedTag,
      productId: selectedProductId || undefined,
      productName: matchedProduct?.name || undefined,
      productCode: matchedProduct?.product_code || undefined,
    };

    const updated = addPlaybookNote(newNote, notes);
    setNotes(updated);
    setIdeaText('');
    setRefUrl('');
    setPreviewImage(null);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  const handleDelete = (id) => {
    const updated = deletePlaybookNote(id, notes);
    setNotes(updated);
  };

  // Run AI Idea-to-Script on saved note
  const handleRunAi = async (item) => {
    try {
      setAiSynthesizingId(item.id);
      const res = await aiIdeaToAngle({
        idea_text: item.text,
        ref_url: item.url,
        ref_image: item.imageUrl,
        product_id: item.productId || (products[0]?.id || null),
      });

      if (res?.success && res.proposal) {
        setAiProposal({
          ...res.proposal,
          product_id: item.productId || (products[0]?.id || ''),
          originNoteId: item.id,
        });
      }
    } catch (err) {
      alert('ไม่สามารถประมวลผลด้วย AI ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAiSynthesizingId(null);
    }
  };

  // Confirm adding proposed angle to target product
  const handleConfirmAddAngle = async () => {
    if (!aiProposal) return;
    try {
      setAddingAngle(true);
      const targetProdId = aiProposal.product_id || products[0]?.id;
      if (!targetProdId) {
        alert('กรุณาเลือกสินค้าที่ต้องการเพิ่มมุมมอง');
        return;
      }

      const newAngleData = {
        name: aiProposal.name,
        hook: aiProposal.hook,
        hook_category: aiProposal.hook_category || 'curiosity',
        shoot_brief: aiProposal.shoot_brief,
        script: aiProposal.script,
        tags: [aiProposal.hook_category, 'ref-inspired'].filter(Boolean),
      };

      await addProductAngle(targetProdId, newAngleData);
      setAngleAddedSuccess(true);
      setTimeout(() => {
        setAngleAddedSuccess(false);
        setAiProposal(null);
      }, 1500);
    } catch (err) {
      alert('เพิ่มมุมมองไม่สำเร็จ: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAddingAngle(false);
    }
  };

  const detectedPlatform = detectRefPlatform(refUrl);

  // Filtered notes
  const filteredNotes = notes.filter(n => {
    const matchTag = filterTag === 'all' || n.tag === filterTag;
    const q = searchQuery.trim().toLowerCase();
    const matchSearch = !q ||
      (n.text && n.text.toLowerCase().includes(q)) ||
      (n.url && n.url.toLowerCase().includes(q)) ||
      (n.productName && n.productName.toLowerCase().includes(q)) ||
      (n.productCode && n.productCode.toLowerCase().includes(q));
    return matchTag && matchSearch;
  });

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 flex flex-col relative selection:bg-amber-500/30 selection:text-amber-200">
      {/* ── Ambient Background Glows ── */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />

      {/* ── Sticky Top Header ── */}
      <header className="sticky top-0 z-30 bg-[#07090E]/90 backdrop-blur-xl border-b border-white/[0.08] px-4 py-3 sm:px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onExit || (() => { window.location.href = window.location.pathname; })}
              className="w-10 h-10 rounded-xl bg-slate-800/80 hover:bg-slate-700 active:scale-95 flex items-center justify-center text-slate-300 hover:text-white cursor-pointer transition-all border border-white/5"
              title="กลับหน้าหลัก"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <span className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-black">✦</span>
                  <span>คลังไอเดีย & เซฟเรฟด่วน</span>
                </h1>
                <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  {notes.length} รายการ
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                TikTok · Pinterest · YouTube · เก็บไอเดียสดพร้อมส่ง AI แตกสคริปต์
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mobile View Switcher (Visible on small screens) */}
            <div className="flex lg:hidden bg-slate-900/90 p-1 rounded-xl border border-white/10">
              <button
                onClick={() => setMobileTab('capture')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  mobileTab === 'capture'
                    ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                จดไอเดีย
              </button>
              <button
                onClick={() => setMobileTab('vault')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  mobileTab === 'vault'
                    ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <span>คลังเรฟ</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  mobileTab === 'vault' ? 'bg-slate-950/30 text-slate-950 font-black' : 'bg-slate-800 text-slate-300'
                }`}>
                  {notes.length}
                </span>
              </button>
            </div>

            <button
              onClick={onExit || (() => { window.location.href = window.location.pathname; })}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 hover:text-white transition-all border border-white/10 hidden sm:flex items-center gap-1.5"
            >
              <span>เปิดหน้าเต็มในแอป</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content Area ── */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

          {/* ══════════════════════════════════════════════════════════════
              LEFT / TOP: QUICK CAPTURE STUDIO
              ══════════════════════════════════════════════════════════════ */}
          <div className={`lg:col-span-5 space-y-4 ${
            mobileTab === 'vault' ? 'hidden lg:block' : 'block'
          }`}>
            <div className="p-4 sm:p-5 rounded-3xl bg-slate-900/80 border border-amber-500/20 shadow-2xl backdrop-blur-xl space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-amber-500/15 text-amber-400">
                    <Bookmark className="w-4 h-4" />
                  </span>
                  <h2 className="text-sm font-bold text-white">บันทึกไอเดียใหม่</h2>
                </div>
                <span className="text-[11px] text-slate-400">พิมพ์หรือแปะลิงก์</span>
              </div>

              {/* 1. URL Input with 1-Tap Paste Button */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ลิงก์คลิปเรฟ (TikTok / Pinterest / YouTube)</span>
                  </label>
                  <button
                    type="button"
                    onClick={handlePasteClipboard}
                    className="text-[11px] font-bold text-amber-400 hover:text-amber-300 flex items-center gap-1 cursor-pointer bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20 active:scale-95 transition-all"
                  >
                    {pasteSuccess ? <Check className="w-3 h-3" /> : <Clipboard className="w-3 h-3" />}
                    <span>{pasteSuccess ? 'วางเรียบร้อย!' : 'วางลิงก์ล่าสุด'}</span>
                  </button>
                </div>

                <div className="relative">
                  <input
                    type="url"
                    value={refUrl}
                    onChange={(e) => setRefUrl(e.target.value)}
                    placeholder="https://vt.tiktok.com/... หรือ pin.it/..."
                    /* text-base (16px) is critical to prevent iOS Safari auto-zoom */
                    className="w-full px-3.5 py-3 rounded-2xl bg-slate-950/80 border border-white/10 text-base text-white placeholder:text-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-500/20 pr-24 transition-all min-h-[48px]"
                  />
                  {detectedPlatform ? (
                    <span className="absolute right-3 top-2.5 px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      {detectedPlatform}
                    </span>
                  ) : refUrl ? (
                    <button
                      type="button"
                      onClick={() => setRefUrl('')}
                      className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  ) : null}
                </div>
              </div>

              {/* 2. Idea / Notes Textarea with Direct Image Paste & Drag-Drop */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-300">
                    ไอเดีย / จุดเด่นที่ชอบ / สิ่งที่ต้องทำตาม
                  </label>
                  <span className="text-[10px] text-amber-400/90 font-medium">
                    กด Ctrl+V วางรูปในช่องนี้ได้เลย
                  </span>
                </div>
                <textarea
                  value={ideaText}
                  onChange={(e) => setIdeaText(e.target.value)}
                  onPaste={handlePasteAnywhere}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  placeholder="เช่น ฮุกเปิดคลิปเทน้ำแข็งใส่พัดลม, ขยี้เรื่องเล่นเกมแล้วกระตุก... (แคปหน้าจอแล้วกด Ctrl+V วางรูปภาพในช่องนี้ได้ทันที)"
                  rows={3}
                  /* text-base (16px) is critical to prevent iOS Safari auto-zoom */
                  className="w-full px-3.5 py-2.5 rounded-2xl bg-slate-950/80 border border-white/10 text-base text-white placeholder:text-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-500/20 resize-none transition-all"
                />
              </div>

              {/* 3. Category Segmented Pills */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">ประเภทเรฟ</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {CATEGORIES.map((cat) => {
                    const Icon = cat.icon;
                    const active = selectedTag === cat.id;
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setSelectedTag(cat.id)}
                        className={`p-2 rounded-xl text-xs font-bold flex items-center gap-2 border transition-all cursor-pointer text-left ${
                          active
                            ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md shadow-amber-500/10'
                            : 'bg-slate-950/60 border-white/5 text-slate-400 hover:text-slate-200 hover:border-white/15'
                        }`}
                      >
                        <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${active ? 'text-amber-400' : 'text-slate-400'}`} />
                        <span className="truncate">{cat.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 4. Product Link Selector */}
              {products.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-300">ผูกสินค้า (ไม่บังคับ)</label>
                    {selectedProductId && (
                      <button
                        type="button"
                        onClick={() => setSelectedProductId('')}
                        className="text-[11px] text-slate-400 hover:text-rose-400"
                      >
                        ล้างค่า
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full scrollbar-none">
                    <button
                      type="button"
                      onClick={() => setSelectedProductId('')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap border cursor-pointer transition-all ${
                        !selectedProductId
                          ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                          : 'bg-slate-950/60 border-white/5 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      ทั่วไป (ไม่ระบุ)
                    </button>
                    {products.map((p) => {
                      const active = selectedProductId === p.id;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => setSelectedProductId(p.id)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap border cursor-pointer transition-all ${
                            active
                              ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-sm'
                              : 'bg-slate-950/60 border-white/5 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {p.product_code ? `[${p.product_code}] ` : ''}{p.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 5. Image Drop / Pick Zone */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-300 flex items-center gap-1">
                    <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ภาพเรฟ / แคปหน้าจอ</span>
                  </label>
                  {pastedImageToast && (
                    <span className="text-[10px] font-bold text-emerald-400 animate-pulse">
                      วางรูปภาพเรียบร้อย!
                    </span>
                  )}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,video/*"
                  onChange={handleImageSelect}
                  className="hidden"
                />

                {previewImage ? (
                  <div className="relative rounded-2xl overflow-hidden border border-amber-500/30 bg-slate-950 p-2 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <img
                        src={previewImage}
                        alt="Ref preview"
                        className="h-14 w-14 rounded-xl object-cover border border-white/10"
                      />
                      <div>
                        <p className="text-xs font-bold text-slate-200">แนบภาพเรฟเรียบร้อย</p>
                        <p className="text-[10px] text-slate-400">พร้อมวิเคราะห์ด้วย AI</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 text-[11px] font-semibold text-slate-300 hover:text-white"
                      >
                        เปลี่ยนรูป
                      </button>
                      <button
                        type="button"
                        onClick={() => setPreviewImage(null)}
                        className="p-1.5 rounded-lg bg-rose-500/20 text-rose-300 hover:bg-rose-500/30"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {/* Rich ContentEditable Paste Target for Mobile (iOS Safari & Android) & Desktop */}
                    <div
                      contentEditable
                      suppressContentEditableWarning
                      onPaste={handlePasteAnywhere}
                      onInput={handleContentEditableInput}
                      onKeyDown={(e) => {
                        if (!e.ctrlKey && !e.metaKey && e.key !== 'v') {
                          e.preventDefault();
                        }
                      }}
                      tabIndex={0}
                      className="w-full py-3 px-3.5 rounded-2xl border-2 border-dashed border-amber-500/40 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] focus:border-amber-400 focus:bg-amber-500/[0.08] focus:outline-none flex items-center justify-between cursor-pointer transition-all active:scale-[0.99]"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="p-1.5 rounded-xl bg-amber-500/20 text-amber-400 flex-shrink-0">
                          <Clipboard className="w-4 h-4" />
                        </div>
                        <div className="text-left min-w-0">
                          <p className="text-xs font-bold text-amber-200 truncate">
                            แตะที่นี่แล้วกด วาง (Paste)
                          </p>
                          <p className="text-[10px] text-slate-400 truncate">
                            สำหรับมือถือ แตะ 1 ที แล้วเลือก "วาง" ในเมนูด้านบน
                          </p>
                        </div>
                      </div>
                      <span className="text-[10px] font-bold text-amber-300 bg-amber-500/20 border border-amber-500/30 px-2 py-1 rounded-lg pointer-events-none whitespace-nowrap flex-shrink-0">
                        แตะค้างแล้วกดวาง
                      </span>
                    </div>

                    {/* Secondary Action Bar: Direct 1-Tap Photo Library & Paste Button */}
                    <div
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={handleDrop}
                      className="w-full p-2.5 rounded-2xl border border-white/10 bg-slate-950/40 flex items-center justify-between gap-2 transition-all"
                    >
                      <div className="flex items-center gap-2 text-slate-400 min-w-0">
                        <ImageIcon className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        <span className="text-xs truncate">
                          {uploadingImage ? 'กำลังอัปโหลดรูป...' : 'หรือเลือกจากมือถือ:'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploadingImage}
                          className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
                          title="เปิดคลังภาพเพื่อเลือกรูปที่เพิ่งแคปหน้าจอไว้ได้ทันที"
                        >
                          <ImageIcon className="w-3.5 h-3.5" />
                          <span>เลือกจากคลังภาพ</span>
                        </button>
                        <button
                          type="button"
                          onClick={handlePasteImageFromClipboard}
                          disabled={uploadingImage}
                          className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10 text-xs font-semibold flex items-center gap-1 cursor-pointer active:scale-95 transition-all"
                          title="อ่านภาพจากคลิปบอร์ดเครื่อง"
                        >
                          <Clipboard className="w-3.5 h-3.5" />
                          <span>วางรูปภาพ</span>
                        </button>
                      </div>
                    </div>

                    {clipboardHelpToast && (
                      <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300 flex items-center justify-between animate-fadeIn">
                        <span>มือถือจำกัดการเข้าถึงคลิปบอร์ด กรุณาแตะกล่องด้านบนเพื่อกดวาง หรือแตะ "เลือกจากคลังภาพ"</span>
                        <button
                          type="button"
                          onClick={() => setClipboardHelpToast(false)}
                          className="text-amber-400 hover:text-white ml-2"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 6. Big Thumb-Friendly Save Button */}
              <button
                type="button"
                onClick={handleSave}
                disabled={!ideaText.trim() && !refUrl.trim() && !previewImage}
                className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 hover:brightness-110 active:scale-[0.98] text-slate-950 font-black text-sm flex items-center justify-center gap-2 cursor-pointer shadow-xl shadow-amber-500/25 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {saveSuccess ? <Check className="w-5 h-5" /> : <Bookmark className="w-5 h-5" />}
                <span>{saveSuccess ? 'บันทึกเข้าคลังเรียบร้อย!' : 'บันทึกเข้าคลังไอเดีย'}</span>
              </button>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════════
              RIGHT / BOTTOM: INTERACTIVE IDEA VAULT & REFS LIST
              ══════════════════════════════════════════════════════════════ */}
          <div className={`lg:col-span-7 space-y-4 ${
            mobileTab === 'capture' ? 'hidden lg:block' : 'block'
          }`}>
            <div className="p-4 sm:p-5 rounded-3xl bg-slate-900/80 border border-white/[0.08] shadow-2xl backdrop-blur-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-cyan-500/15 text-cyan-400">
                    <Film className="w-4 h-4" />
                  </span>
                  <div>
                    <h2 className="text-sm font-bold text-white">คลังไอเดียทั้งหมด</h2>
                    <p className="text-[11px] text-slate-400">รวม {notes.length} รายการที่บันทึกไว้</p>
                  </div>
                </div>

                {/* Search Bar */}
                <div className="relative w-full sm:w-56">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="ค้นหาไอเดีย / สินค้า..."
                    className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-950/80 border border-white/10 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-amber-400 transition-all"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-2 text-slate-500 hover:text-slate-300"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Tag Filter Tabs */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                <button
                  onClick={() => setFilterTag('all')}
                  className={`px-3 py-1 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                    filterTag === 'all'
                      ? 'bg-amber-500 text-slate-950 shadow-sm'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-white/5'
                  }`}
                >
                  ทั้งหมด ({notes.length})
                </button>
                {CATEGORIES.map((cat) => {
                  const count = notes.filter(n => n.tag === cat.id).length;
                  const active = filterTag === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setFilterTag(cat.id)}
                      className={`px-3 py-1 rounded-xl text-xs font-semibold whitespace-nowrap border transition-all ${
                        active
                          ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                          : 'bg-slate-950/60 border-white/5 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {cat.label} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Cards Grid */}
              {filteredNotes.length === 0 ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-white/10 flex items-center justify-center mx-auto text-slate-500">
                    <Bookmark className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-300">ยังไม่พบไอเดียในหมวดนี้</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {searchQuery ? 'ลองเปลี่ยนคำค้นหา หรือล้างตัวกรอง' : 'บันทึกไอเดียแรกจากแบบฟอร์มด้านซ้ายได้เลย'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[640px] overflow-y-auto pr-1">
                  {filteredNotes.map((item) => {
                    const platform = detectRefPlatform(item.url);
                    const isSynthesizing = aiSynthesizingId === item.id;
                    return (
                      <div
                        key={item.id}
                        className="p-4 rounded-2xl bg-slate-950/70 border border-white/[0.08] hover:border-amber-500/40 space-y-3 transition-all flex flex-col justify-between group"
                      >
                        <div className="space-y-2.5">
                          {/* Tags & Product Header */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                {item.tag || 'Idea'}
                              </span>
                              {platform && (
                                <span className="px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                                  {platform}
                                </span>
                              )}
                              {item.productName && (
                                <span className="px-2 py-0.5 rounded-lg text-[10px] font-medium bg-slate-800 text-slate-300 border border-white/10 truncate max-w-[130px]">
                                  {item.productCode ? `[${item.productCode}] ` : ''}{item.productName}
                                </span>
                              )}
                            </div>

                            <button
                              onClick={() => handleDelete(item.id)}
                              className="p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="ลบโน้ตนี้"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          {/* Note Text */}
                          {item.text && (
                            <p className="text-xs text-slate-200 leading-relaxed font-medium">
                              {item.text}
                            </p>
                          )}

                          {/* Image Attachment */}
                          {item.imageUrl && (
                            <div className="rounded-xl overflow-hidden border border-white/10 max-h-40 bg-black/40">
                              <img
                                src={item.imageUrl}
                                alt="Ref attachment"
                                className="w-full h-full object-cover"
                              />
                            </div>
                          )}

                          {/* URL Link */}
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold bg-cyan-950/40 border border-cyan-500/20 px-2.5 py-1 rounded-xl truncate max-w-full"
                            >
                              <LinkIcon className="w-3.5 h-3.5 flex-shrink-0" />
                              <span className="truncate">{item.url}</span>
                              <ExternalLink className="w-3 h-3 flex-shrink-0 ml-auto" />
                            </a>
                          )}
                        </div>

                        {/* Bottom Actions: AI Button */}
                        <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                          <span className="text-[10px] text-slate-500">
                            {item.createdAt ? new Date(item.createdAt).toLocaleDateString('th-TH') : ''}
                          </span>

                          <button
                            type="button"
                            onClick={() => handleRunAi(item)}
                            disabled={isSynthesizing}
                            className="px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                            title="วิเคราะห์ไอเดียนี้ด้วย AI"
                          >
                            {isSynthesizing ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                            ) : (
                              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                            )}
                            <span>{isSynthesizing ? 'กำลังคิดสคริปต์...' : 'คิดสคริปต์จากเรฟ'}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* ── AI Idea-to-Script Modal ── */}
      {aiProposal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-3xl bg-slate-900 border border-amber-500/30 p-5 sm:p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-amber-500/20 text-amber-400">
                  <Sparkles className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-white">AI สกัดไอเดียเป็นมุมมองสินค้า</h3>
                  <p className="text-xs text-slate-400">Hook + แผนถ่าย + สคริปต์ย่อ พร้อมเริ่มผลิต</p>
                </div>
              </div>
              <button
                onClick={() => setAiProposal(null)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Target Product Selection */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-300">ผูกกับสินค้า</label>
              <select
                value={aiProposal.product_id || ''}
                onChange={(e) => setAiProposal({ ...aiProposal, product_id: e.target.value })}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-amber-400"
              >
                {products.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.product_code ? `[${p.product_code}] ` : ''}{p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Hook Proposed */}
            <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-amber-500/20 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-amber-300">
                  HOOK เปิดคลิป 3 วินาทีแรก
                </span>
                <span className="text-[10px] text-slate-400">
                  หมวด: {aiProposal.hook_category || 'curiosity'}
                </span>
              </div>
              <p className="text-sm font-bold text-amber-200 leading-snug">
                "{aiProposal.hook}"
              </p>
            </div>

            {/* Shoot Brief */}
            {aiProposal.shoot_brief && (
              <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-white/5 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">
                  แผนถ่ายทำ (Shoot Brief)
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {aiProposal.shoot_brief}
                </p>
              </div>
            )}

            {/* Script */}
            {aiProposal.script && (
              <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-white/5 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  บทพากย์ย่อ (Voiceover Script)
                </span>
                <p className="text-xs text-slate-200 leading-relaxed">
                  {aiProposal.script}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setAiProposal(null)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={handleConfirmAddAngle}
                disabled={addingAngle || angleAddedSuccess}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-slate-950 font-black text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all"
              >
                {addingAngle ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : angleAddedSuccess ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <PlusCircle className="w-4 h-4" />
                )}
                <span>{angleAddedSuccess ? 'เพิ่มสำเร็จแล้ว!' : 'เพิ่มเป็นมุมมองสินค้า'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
