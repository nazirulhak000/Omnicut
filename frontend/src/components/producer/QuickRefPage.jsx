import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bookmark, Link as LinkIcon, Image as ImageIcon, Sparkles,
  ArrowLeft, Check, Trash2, ExternalLink, X, Smartphone, Tag,
  Clipboard, Search, Loader2, PlayCircle, Eye, Volume2, Flame,
  Share2, Copy, Filter, Film, PlusCircle, RefreshCw, Maximize2, Download,
  Upload
} from 'lucide-react';
import {
  loadPlaybookNotes,
  savePlaybookNotes,
  addPlaybookNote,
  deletePlaybookNote,
  formatNoteForSharing,
  detectRefPlatform
} from '../../lib/producerInsights';
import {
  getProducts,
  uploadRefMedia,
  aiIdeaToAngle,
  addProductAngle,
  getProducerNotes,
  saveProducerNotes,
  deleteProducerNote
} from '../../api';

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
  const [previewImages, setPreviewImages] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [pasteSuccess, setPasteSuccess] = useState(false);
  const [pastedImageToast, setPastedImageToast] = useState(false);
  const [clipboardHelpToast, setClipboardHelpToast] = useState(false);
  const [clipboardErrorMsg, setClipboardErrorMsg] = useState('');
  const [deleteToast, setDeleteToast] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [copyShareToast, setCopyShareToast] = useState(false);
  const [activeZoomImage, setActiveZoomImage] = useState(null);
  const [activeDetailsNote, setActiveDetailsNote] = useState(null);

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
  const lastPasteTimeRef = useRef(0);

  // Sync Notes with Server (Makes notes accessible on PC & Mobile simultaneously)
  const fetchNotes = useCallback(async () => {
    try {
      setIsSyncing(true);
      const res = await getProducerNotes();
      if (res?.success && Array.isArray(res.notes)) {
        setNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
    } catch (err) {
      console.warn('Failed to sync notes from server, using local:', err);
    } finally {
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    getProducts()
      .then(res => {
        const list = Array.isArray(res) ? res : (res?.products || []);
        setProducts(list);
      })
      .catch(() => {});

    fetchNotes();
    // Auto-sync every 20 seconds
    const interval = setInterval(fetchNotes, 20000);
    return () => clearInterval(interval);
  }, [fetchNotes]);

  // Global Paste Listener: Press Ctrl+V (or Cmd+V) ANYWHERE on the page to paste images instantly!
  useEffect(() => {
    const handleGlobalWindowPaste = (e) => {
      // If already handled locally or triggered within debounce window (600ms), ignore to prevent duplicate images
      if (e.defaultPrevented || Date.now() - lastPasteTimeRef.current < 600) {
        return;
      }

      const activeEl = document.activeElement;
      const isTextInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');

      const cd = e.clipboardData;
      if (!cd) return;

      // Check if clipboard contains image files or image items
      const hasImageFile = Array.from(cd.files || []).some(f => f.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|heic|heif|bmp)$/i.test(f.name || ''));
      const hasImageItem = Array.from(cd.items || []).some(i => i.type.startsWith('image/'));

      if (hasImageFile || hasImageItem) {
        // Intercept image paste globally, adding images to the list
        e.preventDefault();
        lastPasteTimeRef.current = Date.now();
        handlePasteAnywhere(e);
        setPastedImageToast(true);
        setTimeout(() => setPastedImageToast(false), 3000);
        return;
      }

      // If user is not in a text input, and pastes text that is an image URL or TikTok/YT link
      if (!isTextInput) {
        const text = cd.getData('text/plain')?.trim();
        if (text) {
          if (text.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(text)) {
            e.preventDefault();
            lastPasteTimeRef.current = Date.now();
            appendImageUrl(text);
            setPastedImageToast(true);
            setTimeout(() => setPastedImageToast(false), 3000);
          } else if (/^(https?:\/\/)?(www\.)?(tiktok\.com|youtube\.com|youtu\.be|pin\.it|pinterest\.com)/i.test(text)) {
            e.preventDefault();
            setRefUrl(text);
            setPasteSuccess(true);
            setTimeout(() => setPasteSuccess(false), 2000);
          }
        }
      }
    };

    window.addEventListener('paste', handleGlobalWindowPaste);
    return () => window.removeEventListener('paste', handleGlobalWindowPaste);
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

  // Helper to detect duplicate images (exact match or binary data URL match) with 100% crash-proof safety
  const isDuplicateImage = (list, newImg) => {
    try {
      if (!newImg || typeof newImg !== 'string' || !Array.isArray(list) || list.length === 0) {
        return false;
      }
      if (list.includes(newImg)) return true;
      const newLen = newImg.length;
      const newPrefix = newImg.slice(0, 80);
      const newSuffix = newImg.slice(-80);
      return list.some(existing => (
        typeof existing === 'string' &&
        existing.length === newLen &&
        existing.slice(0, 80) === newPrefix &&
        existing.slice(-80) === newSuffix
      ));
    } catch (_) {
      return false;
    }
  };

  // Helper to append a single image URL with deduplication
  const appendImageUrl = (url) => {
    try {
      if (!url || typeof url !== 'string') return;
      setPreviewImages(prev => {
        try {
          if (isDuplicateImage(prev, url)) return prev;
          return [...prev, url];
        } catch (_) {
          return prev;
        }
      });
      setPastedImageToast(true);
      setTimeout(() => setPastedImageToast(false), 2500);
    } catch (err) {
      console.warn('appendImageUrl error:', err);
    }
  };

  // Multi-Image Processor with Deduplication and Safe Exception Isolation
  const processImageFiles = async (files) => {
    try {
      if (!files || files.length === 0) return;
      const fileList = Array.from(files);

      for (const file of fileList) {
        if (!file) continue;

        // Local preview reader
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const localData = reader.result;
            if (!localData || typeof localData !== 'string') return;
            setPreviewImages(prev => {
              try {
                if (isDuplicateImage(prev, localData)) return prev;
                return [...prev, localData];
              } catch (_) {
                return prev;
              }
            });
            setPastedImageToast(true);
            setTimeout(() => setPastedImageToast(false), 2500);
          } catch (err) {
            console.warn('Error displaying image preview:', err);
          }
        };
        reader.onerror = () => {
          console.warn('FileReader error');
        };

        try {
          reader.readAsDataURL(file);
        } catch (readErr) {
          console.warn('Failed to read file as DataURL:', readErr);
        }

        // Upload to server in background
        try {
          setUploadingImage(true);
          const uploadRes = await uploadRefMedia(file);
          if (uploadRes?.url && typeof uploadRes.url === 'string') {
            setPreviewImages(prev => {
              try {
                if (isDuplicateImage(prev, uploadRes.url)) {
                  return prev.filter(img => img !== reader.result);
                }
                return prev.map(img => (img === reader.result ? uploadRes.url : img));
              } catch (_) {
                return prev;
              }
            });
          }
        } catch (err) {
          console.warn('Server image upload failed, using local preview:', err);
        } finally {
          setUploadingImage(false);
        }
      }
    } catch (err) {
      console.warn('processImageFiles error:', err);
    }
  };

  const handleImageSelect = (e) => {
    try {
      const files = e.target.files;
      if (files && files.length > 0) processImageFiles(files);
    } catch (err) {
      console.warn('handleImageSelect error:', err);
    }
  };

  const removePreviewImage = (indexToRemove) => {
    try {
      setPreviewImages(prev => prev.filter((_, idx) => idx !== indexToRemove));
    } catch (err) {
      console.warn('removePreviewImage error:', err);
    }
  };

  // Intercept Ctrl+V or right-click Paste in textarea, contenteditable, or card
  const handlePasteAnywhere = (e) => {
    try {
      const cd = e.clipboardData;
      if (!cd) return;

      // Debounce guard: if paste was processed in the last 500ms, ignore secondary bubbling/events
      const now = Date.now();
      if (now - lastPasteTimeRef.current < 500) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }

      // 1. Check cd.files FIRST (iOS Safari & desktop multiple file pastes)
      if (cd.files && cd.files.length > 0) {
        const validFiles = [];
        for (let i = 0; i < cd.files.length; i++) {
          const file = cd.files[i];
          if (file && (file.type?.startsWith('image/') || /\.(png|jpe?g|webp|gif|heic|heif|bmp)$/i.test(file.name || ''))) {
            validFiles.push(file);
          }
        }
        if (validFiles.length > 0) {
          e.preventDefault();
          e.stopPropagation();
          lastPasteTimeRef.current = Date.now();
          processImageFiles(validFiles);
          return;
        }
      }

      // 2. Check cd.items (Chrome / Android / Chromium-based browsers)
      if (cd.items && cd.items.length > 0) {
        const validFiles = [];
        for (let i = 0; i < cd.items.length; i++) {
          const item = cd.items[i];
          if (item.type && item.type.startsWith('image/')) {
            const file = item.getAsFile();
            if (file) validFiles.push(file);
          }
        }
        if (validFiles.length > 0) {
          e.preventDefault();
          e.stopPropagation();
          lastPasteTimeRef.current = Date.now();
          processImageFiles(validFiles);
          return;
        }
      }

      // 3. Check HTML content for <img> tags (when user copies images from Pinterest or web)
      try {
        const html = cd.getData('text/html');
        if (html) {
          const matches = [...html.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)];
          const urls = matches.map(m => m[1]).filter(src => src && typeof src === 'string' && !src.startsWith('webkit-fake-url:'));
          if (urls.length > 0) {
            e.preventDefault();
            e.stopPropagation();
            lastPasteTimeRef.current = Date.now();
            urls.forEach(appendImageUrl);
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
            e.stopPropagation();
            lastPasteTimeRef.current = Date.now();
            appendImageUrl(trimmed);
            return;
          }
        }
      } catch (_) {}
    } catch (err) {
      console.warn('handlePasteAnywhere error:', err);
    }
  };

  // ContentEditable input catcher (Failsafe for iOS Safari native image paste/insertion)
  const handleContentEditableInput = (e) => {
    try {
      const container = e.currentTarget;
      if (!container) return;

      // Clean up DOM safely in setTimeout to avoid React 19 reconciliation removeChild crashes!
      const safeClean = () => {
        setTimeout(() => {
          if (container) {
            try {
              container.textContent = '';
            } catch (_) {}
          }
        }, 50);
      };

      // Failsafe debounce: If handlePasteAnywhere already caught the paste in the last 700ms,
      // just clean up safely without duplicating or crashing React
      const now = Date.now();
      if (now - lastPasteTimeRef.current < 700) {
        safeClean();
        return;
      }

      let foundAny = false;
      const imgs = container.querySelectorAll('img');
      imgs.forEach(img => {
        if (img.src && typeof img.src === 'string' && !img.src.startsWith('webkit-fake-url:')) {
          appendImageUrl(img.src);
          foundAny = true;
        }
      });
      const text = container.innerText?.trim();
      if (text && typeof text === 'string' && (text.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(text))) {
        appendImageUrl(text);
        foundAny = true;
      }

      if (foundAny) {
        lastPasteTimeRef.current = Date.now();
      }
      safeClean();
    } catch (err) {
      console.warn('handleContentEditableInput error:', err);
    }
  };

  // Drag & drop image support
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      processImageFiles(files);
      setPastedImageToast(true);
      setTimeout(() => setPastedImageToast(false), 3000);
    }
  };

  // 1-Tap Read Image from Clipboard with full type detection
  const handlePasteImageFromClipboard = async () => {
    if (!navigator.clipboard?.read) {
      setClipboardErrorMsg('เบราว์เซอร์จำกัดสิทธิ์เข้าถึงคลิปบอร์ดผ่านปุ่มนี้ กรุณากด Ctrl+V บนคีย์บอร์ด หรือแตะ "เลือกจากคลังภาพ"');
      setTimeout(() => setClipboardErrorMsg(''), 5000);
      return;
    }

    try {
      setUploadingImage(true);
      const items = await navigator.clipboard.read();
      const filesToAdd = [];
      let foundAnyImage = false;

      for (const item of items) {
        // A. Image blob (Snipping tool / copied image)
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            const blob = await item.getType(type);
            const ext = type.split('/')[1] || 'png';
            const file = new File([blob], `pasted_ref_${Date.now()}_${Math.random().toString(36).slice(2, 6)}.${ext}`, { type });
            filesToAdd.push(file);
            foundAnyImage = true;
          }
        }

        // B. HTML content from website
        if (item.types.includes('text/html')) {
          try {
            const blob = await item.getType('text/html');
            const html = await blob.text();
            const matches = [...html.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)];
            const urls = matches.map(m => m[1]).filter(src => src && !src.startsWith('webkit-fake-url:'));
            if (urls.length > 0) {
              urls.forEach(appendImageUrl);
              foundAnyImage = true;
            }
          } catch (_) {}
        }

        // C. Plain text image link or base64
        if (item.types.includes('text/plain')) {
          try {
            const blob = await item.getType('text/plain');
            const text = (await blob.text()).trim();
            if (text.startsWith('data:image/') || /\.(png|jpe?g|webp|gif|heic)(\?.*)?$/i.test(text)) {
              appendImageUrl(text);
              foundAnyImage = true;
            }
          } catch (_) {}
        }
      }

      if (filesToAdd.length > 0) {
        processImageFiles(filesToAdd);
        setPastedImageToast(true);
        setTimeout(() => setPastedImageToast(false), 3000);
        return;
      }

      if (foundAnyImage) {
        setPastedImageToast(true);
        setTimeout(() => setPastedImageToast(false), 3000);
        return;
      }

      setClipboardErrorMsg('ไม่พบรูปภาพในคลิปบอร์ด กรุณาแคปหน้าจอแล้วกด Ctrl+V หรือเลือกจากคลังภาพ');
      setTimeout(() => setClipboardErrorMsg(''), 4500);
    } catch (err) {
      console.warn('Clipboard read error:', err);
      setClipboardErrorMsg('เบราว์เซอร์จำกัดสิทธิ์เข้าถึงคลิปบอร์ดผ่านปุ่มนี้ กรุณากด Ctrl+V บนคีย์บอร์ด หรือเลือกจากคลังภาพ');
      setTimeout(() => setClipboardErrorMsg(''), 5000);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSave = async () => {
    if (!ideaText.trim() && !refUrl.trim() && previewImages.length === 0) return;

    const matchedProduct = products.find(p => p.id === selectedProductId);
    const newNote = {
      text: ideaText.trim(),
      url: refUrl.trim() || undefined,
      images: previewImages,
      imageUrl: previewImages[0] || undefined,
      tag: selectedTag,
      productId: selectedProductId || undefined,
      productName: matchedProduct?.name || undefined,
      productCode: matchedProduct?.product_code || undefined,
      createdAt: new Date().toISOString(),
    };

    const updated = addPlaybookNote(newNote, notes);
    setNotes(updated);
    setIdeaText('');
    setRefUrl('');
    setPreviewImages([]);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);

    // Sync to backend so PC and other clients have it immediately
    try {
      await saveProducerNotes(updated);
    } catch (err) {
      console.warn('Failed to save to server:', err);
    }
  };

  const handleDelete = async (id) => {
    const updated = deletePlaybookNote(id, notes);
    setNotes(updated);
    setDeleteToast(true);
    setTimeout(() => setDeleteToast(false), 3000);
    try {
      await deleteProducerNote(id);
    } catch (err) {
      console.warn('Failed to delete on server:', err);
    }
  };

  // One-click Copy/Share note for Boss or Team
  const handleCopyNoteForBoss = (item) => {
    const text = formatNoteForSharing(item);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setCopyShareToast(true);
      setTimeout(() => setCopyShareToast(false), 3000);
    } else {
      alert(text);
    }
  };

  // Run AI Idea-to-Script on saved note
  const handleRunAi = async (item) => {
    try {
      setAiSynthesizingId(item.id);
      const itemImages = Array.isArray(item.images) && item.images.length > 0
        ? item.images
        : (item.imageUrl ? [item.imageUrl] : []);

      const res = await aiIdeaToAngle({
        idea_text: item.text,
        ref_url: item.url,
        ref_image: itemImages[0] || '',
        ref_images: itemImages,
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

              {/* 5. Image Drop / Pick Zone (Multiple Images Support) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-300 flex items-center gap-1">
                    <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ภาพเรฟ / แคปหน้าจอ (แนบได้หลายรูป)</span>
                  </label>
                  {pastedImageToast && (
                    <span className="text-[10px] font-bold text-emerald-400 animate-pulse">
                      เพิ่มรูปภาพเรียบร้อย!
                    </span>
                  )}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,video/*"
                  multiple
                  onChange={handleImageSelect}
                  className="hidden"
                />

                {previewImages.length > 0 ? (
                  <div className="space-y-2.5">
                    <div className="p-3 rounded-2xl border border-amber-500/30 bg-slate-950/80 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-200">
                            แนบภาพเรฟ ({previewImages.length} รูป)
                          </span>
                          <span className="text-[10px] text-amber-300 font-semibold bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded">
                            พร้อมบันทึก
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setPreviewImages([])}
                          className="text-[11px] text-rose-400 hover:text-rose-300 font-semibold cursor-pointer"
                        >
                          ล้างรูปทั้งหมด
                        </button>
                      </div>

                      {/* Thumbnail Strip */}
                      <div className="flex items-center gap-2.5 overflow-x-auto pb-1.5 scrollbar-none">
                        {previewImages.map((img, idx) => (
                          <div
                            key={idx}
                            className="relative flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden border border-white/15 bg-black/40 group"
                          >
                            <img
                              src={img}
                              alt={`Thumbnail ${idx + 1}`}
                              className="w-full h-full object-cover cursor-zoom-in"
                              onClick={() => setActiveZoomImage(img)}
                            />
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                removePreviewImage(idx);
                              }}
                              className="absolute top-1 right-1 p-0.5 rounded-md bg-black/75 text-rose-300 hover:bg-rose-500 hover:text-white transition-colors"
                              title="ลบรูปนี้"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                            <span className="absolute bottom-0.5 left-1 text-[9px] font-bold text-white/80 bg-black/60 px-1 rounded">
                              #{idx + 1}
                            </span>
                          </div>
                        ))}

                        {/* Button to add more images */}
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="flex-shrink-0 w-16 h-16 rounded-xl border-2 border-dashed border-amber-500/40 bg-amber-500/5 hover:bg-amber-500/15 text-amber-300 flex flex-col items-center justify-center gap-0.5 cursor-pointer transition-all active:scale-95"
                          title="เลือกรูปภาพเพิ่มจากคลัง"
                        >
                          <PlusCircle className="w-4 h-4 text-amber-400" />
                          <span className="text-[9px] font-bold">เพิ่มรูป</span>
                        </button>
                      </div>
                    </div>

                    {/* Secondary Quick Paste Bar to add more (2-Layer zero highlight) */}
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1 min-h-[44px] rounded-xl border border-dashed border-amber-500/30 bg-amber-500/[0.03] hover:bg-amber-500/[0.08] focus-within:border-amber-400 transition-all overflow-hidden">
                        <div
                          contentEditable="true"
                          suppressContentEditableWarning
                          onPaste={handlePasteAnywhere}
                          onInput={handleContentEditableInput}
                          tabIndex={0}
                          className="w-full min-h-[44px] px-3 py-2 outline-none cursor-pointer caret-amber-400 text-transparent"
                          style={{ WebkitUserSelect: 'text', userSelect: 'text' }}
                        />
                        <div className="absolute inset-0 pointer-events-none select-none flex items-center justify-between px-3 py-2">
                          <span className="text-[11px] text-amber-200/90 font-medium truncate">
                            แตะแล้วกด "วาง" (Paste) เพื่อเพิ่มรูปอีก
                          </span>
                          <Clipboard className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 ml-1" />
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-2.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1 cursor-pointer flex-shrink-0"
                      >
                        <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                        <span>เลือกเพิ่ม</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {/* 2-Layer iOS & Desktop Direct Paste Box (ZERO text highlighting, 100% native Paste menu) */}
                    <div className="relative w-full min-h-[64px] rounded-2xl border-2 border-dashed border-amber-500/40 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] focus-within:border-amber-400 focus-within:bg-amber-500/[0.08] transition-all overflow-hidden group">
                      {/* Layer 1: Empty ContentEditable Surface (User taps here -> Apple iOS native [วาง / Paste] pops up!) */}
                      <div
                        contentEditable="true"
                        suppressContentEditableWarning
                        onPaste={handlePasteAnywhere}
                        onInput={handleContentEditableInput}
                        tabIndex={0}
                        className="w-full min-h-[64px] px-4 py-3.5 outline-none cursor-pointer caret-amber-400 text-transparent"
                        style={{ WebkitUserSelect: 'text', userSelect: 'text' }}
                        aria-label="แตะเพื่อวางรูปภาพ"
                      />

                      {/* Layer 2: Non-Selectable Visual Overlay (pointer-events-none so tap hits Layer 1 directly, impossible to highlight text!) */}
                      <div className="absolute inset-0 pointer-events-none select-none flex items-center justify-between px-4 py-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 flex-shrink-0">
                            <Clipboard className="w-5 h-5" />
                          </div>
                          <div className="text-left min-w-0">
                            <p className="text-xs font-bold text-amber-200 truncate">
                              แตะที่นี่แล้วกด "วาง" (Paste)
                            </p>
                            <p className="text-[11px] text-slate-400 truncate">
                              แตะ 1 ครั้ง เมนู [วาง] จะเด้งขึ้นมาทันที วางรูปจาก iPhone ได้เลย
                            </p>
                          </div>
                        </div>
                        <span className="text-[10px] font-bold text-amber-300 bg-amber-500/20 border border-amber-500/30 px-3 py-1.5 rounded-xl whitespace-nowrap flex-shrink-0">
                          แตะแล้วกดวาง
                        </span>
                      </div>
                    </div>

                    {/* Action Bar: Direct 1-Tap Photo Library & Paste Button */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploadingImage}
                        className="w-full py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-amber-500/20 via-orange-500/20 to-amber-500/10 hover:from-amber-500/30 hover:to-orange-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer active:scale-95 transition-all shadow-md shadow-amber-500/10"
                        title="เปิดคลังภาพ (รูปที่เพิ่งแคปหน้าจอจะอยู่มุมบนสุดซ้ายมือ)"
                      >
                        <ImageIcon className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span className="truncate">เลือกจากคลังภาพ (แคปล่าสุดอยู่บนสุด)</span>
                      </button>

                      <button
                        type="button"
                        onClick={handlePasteImageFromClipboard}
                        disabled={uploadingImage}
                        className="w-full py-2.5 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-white/10 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all"
                        title="อ่านรูปภาพจากคลิปบอร์ดเครื่อง"
                      >
                        <Clipboard className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                        <span className="truncate">วางรูปภาพ</span>
                      </button>
                    </div>

                    {clipboardErrorMsg && (
                      <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-[11px] text-amber-300 flex items-center justify-between animate-fadeIn">
                        <span>{clipboardErrorMsg}</span>
                        <button
                          type="button"
                          onClick={() => setClipboardErrorMsg('')}
                          className="text-amber-400 hover:text-white ml-2 cursor-pointer"
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
                disabled={!ideaText.trim() && !refUrl.trim() && previewImages.length === 0}
                className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 hover:brightness-110 active:scale-[0.98] text-slate-950 font-black text-sm flex items-center justify-center gap-2 cursor-pointer shadow-xl shadow-amber-500/25 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {saveSuccess ? <Check className="w-5 h-5" /> : <Bookmark className="w-5 h-5" />}
                <span>{saveSuccess ? 'บันทึกเข้าคลังเรียบร้อย!' : 'บันทึกเข้าคลังไอเดีย'}</span>
              </button>

              {deleteToast && (
                <div className="p-2.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-xs font-bold text-rose-300 text-center animate-fadeIn">
                  ลบโน้ตออกจากคลังเรียบร้อยแล้ว
                </div>
              )}
            </div>

            {/* Mobile Recent Saved Notes Strip (See and delete without switching tabs!) */}
            {notes.length > 0 && (
              <div className="lg:hidden p-4 rounded-3xl bg-slate-900/80 border border-white/10 space-y-3 shadow-xl backdrop-blur-xl">
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <div className="flex items-center gap-1.5">
                    <Film className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-bold text-slate-200">
                      โน้ตที่บันทึกแล้ว ({notes.length})
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMobileTab('vault')}
                    className="text-xs font-bold text-amber-400 hover:text-amber-300 flex items-center gap-1 cursor-pointer"
                  >
                    <span>ดูทั้งหมดในคลัง</span>
                    <ArrowLeft className="w-3 h-3 rotate-180" />
                  </button>
                </div>

                <div className="space-y-2">
                  {notes.slice(0, 3).map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-2xl bg-slate-950/80 border border-white/10 flex items-center justify-between gap-3"
                    >
                      <div
                        className="min-w-0 flex-1 cursor-pointer"
                        onClick={() => setActiveDetailsNote(item)}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            {item.tag || 'Idea'}
                          </span>
                          {item.images?.length > 0 && (
                            <span className="text-[10px] text-cyan-300 font-semibold bg-cyan-500/10 border border-cyan-500/20 px-1 rounded">
                              {item.images.length} รูป
                            </span>
                          )}
                          {item.productName && (
                            <span className="text-[10px] text-slate-400 truncate max-w-[100px]">
                              {item.productName}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-200 truncate font-medium">
                          {item.text || item.url || 'โน้ตเรฟ (ไม่มีข้อความ)'}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDelete(item.id)}
                        className="px-3 py-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-bold flex items-center gap-1 cursor-pointer active:scale-95 transition-all flex-shrink-0"
                        title="ลบโน้ตนี้"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                        <span>ลบ</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
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

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  {/* Sync from Server Button */}
                  <button
                    type="button"
                    onClick={fetchNotes}
                    disabled={isSyncing}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-white/10 text-xs font-semibold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all flex-shrink-0"
                    title="ซิงก์ข้อมูลล่าสุดจากเซิร์ฟเวอร์ (คอมพิวเตอร์/มือถือ)"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isSyncing ? 'animate-spin' : ''}`} />
                    <span className="hidden xs:inline">{isSyncing ? 'กำลังซิงก์...' : 'ซิงก์ข้อมูล'}</span>
                  </button>

                  {/* Search Bar */}
                  <div className="relative w-full sm:w-52">
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
                    const itemImages = Array.isArray(item.images) && item.images.length > 0
                      ? item.images
                      : (item.imageUrl ? [item.imageUrl] : []);

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
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(item.id);
                              }}
                              className="px-2.5 py-1 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-bold flex items-center gap-1 cursor-pointer active:scale-95 transition-all shadow-sm"
                              title="ลบโน้ตนี้"
                            >
                              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                              <span>ลบ</span>
                            </button>
                          </div>

                          {/* Note Text */}
                          {item.text && (
                            <p className="text-xs text-slate-200 leading-relaxed font-medium">
                              {item.text}
                            </p>
                          )}

                          {/* Multi-Image Gallery */}
                          {itemImages.length === 1 && (
                            <div
                              onClick={() => setActiveZoomImage(itemImages[0])}
                              className="relative rounded-xl overflow-hidden border border-white/10 max-h-44 bg-black/40 cursor-zoom-in group/img"
                              title="แตะเพื่อดูรูปขยายใหญ่"
                            >
                              <img
                                src={itemImages[0]}
                                alt="Ref attachment"
                                className="w-full h-full max-h-44 object-cover group-hover/img:scale-105 transition-transform duration-300"
                              />
                              <div className="absolute top-2 right-2 px-2 py-0.5 rounded-lg bg-black/60 backdrop-blur-md text-[10px] text-white font-medium flex items-center gap-1 opacity-0 group-hover/img:opacity-100 transition-opacity">
                                <Maximize2 className="w-3 h-3" />
                                <span>ดูภาพเต็ม</span>
                              </div>
                            </div>
                          )}

                          {itemImages.length > 1 && (
                            <div className="space-y-1.5">
                              <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                                <span className="flex items-center gap-1 text-amber-300 font-bold">
                                  <ImageIcon className="w-3 h-3" />
                                  <span>แนบ {itemImages.length} รูป</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setActiveDetailsNote(item)}
                                  className="text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 cursor-pointer"
                                >
                                  <span>ดูอัลบั้มเต็ม</span>
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </button>
                              </div>
                              <div className={`grid gap-1.5 ${itemImages.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}`}>
                                {itemImages.slice(0, 3).map((imgUrl, imgIdx) => {
                                  const isLastAndMore = imgIdx === 2 && itemImages.length > 3;
                                  const remaining = itemImages.length - 3;
                                  return (
                                    <div
                                      key={imgIdx}
                                      onClick={() => isLastAndMore ? setActiveDetailsNote(item) : setActiveZoomImage(imgUrl)}
                                      className="relative h-20 rounded-xl overflow-hidden border border-white/10 bg-black/40 cursor-pointer group/thumb hover:border-amber-500/40 transition-all"
                                    >
                                      <img
                                        src={imgUrl}
                                        alt={`Ref ${imgIdx + 1}`}
                                        className="w-full h-full object-cover group-hover/thumb:scale-110 transition-transform duration-300"
                                      />
                                      {isLastAndMore ? (
                                        <div className="absolute inset-0 bg-black/75 backdrop-blur-[2px] flex items-center justify-center font-bold text-white text-xs">
                                          +{remaining} รูป
                                        </div>
                                      ) : (
                                        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover/thumb:opacity-100 transition-opacity flex items-center justify-center">
                                          <Maximize2 className="w-3.5 h-3.5 text-white drop-shadow" />
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
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

                        {/* Bottom Actions: Share/Copy + AI Button */}
                        <div className="pt-2.5 border-t border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleCopyNoteForBoss(item)}
                              className="px-2.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-slate-200 hover:text-white border border-white/10 text-xs font-semibold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
                              title="คัดลอกสรุปข้อความและรูปภาพทั้งหมดสำหรับส่งไลน์ให้นายหรือทีมงาน"
                            >
                              <Copy className="w-3.5 h-3.5 text-cyan-400" />
                              <span>คัดลอกส่งงาน</span>
                            </button>
                            {itemImages.length > 0 && (
                              <button
                                type="button"
                                onClick={() => setActiveDetailsNote(item)}
                                className="p-1.5 rounded-xl bg-slate-800/40 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-white/5 text-xs transition-colors"
                                title="เปิดดูรายละเอียดและอัลบั้มรูปเต็ม"
                              >
                                <Maximize2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={() => handleRunAi(item)}
                            disabled={isSynthesizing}
                            className="px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
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
      {/* ── 1-Click Copy Toast Notification ── */}
      {copyShareToast && (
        <div className="fixed bottom-6 right-6 z-50 p-3.5 px-4 rounded-2xl bg-emerald-950/95 border border-emerald-500/40 text-emerald-200 text-xs font-bold shadow-2xl backdrop-blur-xl flex items-center gap-2.5 animate-bounce">
          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>คัดลอกข้อความและรูปภาพทั้งหมดลงคลิปบอร์ดแล้ว พร้อมส่งต่อให้นายหรือทีมงาน!</span>
        </div>
      )}

      {/* ── Lightbox Image Modal ── */}
      {activeZoomImage && (
        <div
          onClick={() => setActiveZoomImage(null)}
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-zoom-out animate-fadeIn"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-4xl max-h-[90vh] flex flex-col items-center gap-3 cursor-default"
          >
            <button
              type="button"
              onClick={() => setActiveZoomImage(null)}
              className="absolute -top-11 right-0 p-2 rounded-full bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white cursor-pointer transition-colors shadow-lg"
              title="ปิดรูปขยาย"
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
                    setCopyShareToast(true);
                    setTimeout(() => setCopyShareToast(false), 2000);
                  }
                }}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-white/10 flex items-center gap-1.5 transition-colors"
              >
                <Copy className="w-3.5 h-3.5 text-amber-400" />
                <span>คัดลอกลิงก์รูป</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Note Details & Full Album Modal ── */}
      {activeDetailsNote && (() => {
        const detailImages = Array.isArray(activeDetailsNote.images) && activeDetailsNote.images.length > 0
          ? activeDetailsNote.images
          : (activeDetailsNote.imageUrl ? [activeDetailsNote.imageUrl] : []);

        return (
          <div
            onClick={() => setActiveDetailsNote(null)}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-fadeIn"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl rounded-3xl bg-slate-900 border border-white/10 p-5 sm:p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto my-auto"
            >
              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-white/10">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-1 rounded-xl text-xs font-black uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    {activeDetailsNote.tag || 'Idea'}
                  </span>
                  {activeDetailsNote.productName && (
                    <span className="px-2.5 py-1 rounded-xl text-xs font-medium bg-slate-800 text-slate-300 border border-white/10">
                      {activeDetailsNote.productCode ? `[${activeDetailsNote.productCode}] ` : ''}{activeDetailsNote.productName}
                    </span>
                  )}
                  <span className="text-xs text-slate-400">
                    {activeDetailsNote.createdAt ? new Date(activeDetailsNote.createdAt).toLocaleString('th-TH') : ''}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveDetailsNote(null)}
                  className="p-1.5 rounded-xl text-slate-400 hover:text-white bg-slate-800 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Text Note */}
              {activeDetailsNote.text && (
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-white/5 space-y-1">
                  <p className="text-sm text-slate-200 leading-relaxed font-medium whitespace-pre-wrap">
                    {activeDetailsNote.text}
                  </p>
                </div>
              )}

              {/* URL */}
              {activeDetailsNote.url && (
                <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/20 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs text-cyan-300 min-w-0">
                    <LinkIcon className="w-4 h-4 flex-shrink-0 text-cyan-400" />
                    <span className="truncate">{activeDetailsNote.url}</span>
                  </div>
                  <a
                    href={activeDetailsNote.url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 hover:text-white flex-shrink-0"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}

              {/* Images Album Grid */}
              {detailImages.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                    <span className="flex items-center gap-1.5 text-amber-300">
                      <ImageIcon className="w-4 h-4" />
                      <span>รูปภาพที่แนบทั้งหมด ({detailImages.length} รูป)</span>
                    </span>
                    <span className="text-[11px] text-slate-500">แตะเพื่อขยายใหญ่</span>
                  </div>
                  <div className={`grid gap-2.5 ${detailImages.length === 1 ? 'grid-cols-1' : detailImages.length === 2 ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-3'}`}>
                    {detailImages.map((img, i) => (
                      <div
                        key={i}
                        onClick={() => setActiveZoomImage(img)}
                        className="relative rounded-2xl overflow-hidden border border-white/10 bg-black/40 cursor-zoom-in group hover:border-amber-500/50 transition-all aspect-video sm:aspect-square"
                      >
                        <img
                          src={img}
                          alt={`Album item ${i + 1}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/60 text-[10px] text-white font-bold backdrop-blur-sm">
                          #{i + 1}
                        </div>
                        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <Maximize2 className="w-4 h-4 text-white drop-shadow" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Bottom Actions */}
              <div className="pt-3 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => handleCopyNoteForBoss(activeDetailsNote)}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-white/10 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer active:scale-95 transition-all shadow-md"
                >
                  <Copy className="w-4 h-4 text-cyan-400" />
                  <span>คัดลอกส่งงาน (พร้อมข้อความและรูปทั้งหมด)</span>
                </button>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      handleDelete(activeDetailsNote.id);
                      setActiveDetailsNote(null);
                    }}
                    className="px-3.5 py-2.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all shadow-sm"
                    title="ลบโน้ตนี้"
                  >
                    <Trash2 className="w-4 h-4 text-rose-400" />
                    <span>ลบโน้ตนี้</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const itemToRun = activeDetailsNote;
                      setActiveDetailsNote(null);
                      handleRunAi(itemToRun);
                    }}
                    className="px-4 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
                  >
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>คิดสคริปต์จากเรฟนี้</span>
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
