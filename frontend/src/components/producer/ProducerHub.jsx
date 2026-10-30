import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useChannelDraft } from '../../hooks/useChannelDraft.js';
import { channelLocalStorage } from '../../lib/channelStorage.js';
import { captureChannel } from '../../lib/channelRuntime.js';
import { Bookmark, Check, CheckCircle2, Clipboard, Copy, Edit3, ExternalLink, Image as ImageIcon, Lightbulb, Link as LinkIcon, Loader2, Pin, RefreshCw, Smartphone, Sparkles, Tag, Trash2, X } from 'lucide-react';
import { getProducts, uploadRefMedia, aiIdeaToAngle, addProductAngle, getProducerNotes, addProducerNote, deleteProducerNote, updateProducerNote } from '../../api';
import { loadPlaybookNotes as readPlaybookNotes, savePlaybookNotes as writePlaybookNotes, addPlaybookNote, deletePlaybookNote, formatNoteForSharing, detectRefPlatform } from '../../lib/producerInsights';

/** The retained idea/ref vault; producer quota, missions and queues are retired. */
export default function ProducerHub() {
  const channelToken = useMemo(() => captureChannel(), []);
  const storage = useMemo(() => channelLocalStorage(channelToken.channel_id), []);
  const savePlaybookNotes = value => writePlaybookNotes(value, storage);
  const [retained] = useState(() => { try { return JSON.parse(storage.getItem('producer_manual_draft') || 'null') || {}; } catch { return {}; } });
  const notesRevision = useRef(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [playbookNotes, setPlaybookNotes] = useState(() => readPlaybookNotes(storage));
  const [ideaText, setIdeaText] = useState(retained.ideaText || '');
  const [ideaUrl, setIdeaUrl] = useState(retained.ideaUrl || '');
  const [ideaImages, setIdeaImages] = useState(retained.ideaImages || []);
  const [ideaTag, setIdeaTag] = useState(retained.ideaTag || 'Hook');
  const [ideaProduct, setIdeaProduct] = useState(retained.ideaProduct || '');
  const [uploadingRefImage, setUploadingRefImage] = useState(false);
  const [failedRefUploads, setFailedRefUploads] = useState(0);
  const [refSaveSuccess, setRefSaveSuccess] = useState(false);
  const [activeZoomImage, setActiveZoomImage] = useState(null);
  const fileInputRef = useRef(null);
  const [aiSynthesizingId, setAiSynthesizingId] = useState(null);
  const [aiProposal, setAiProposal] = useState(retained.aiProposal || null);
  const [addingAngle, setAddingAngle] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [editingNote, setEditingNote] = useState(retained.editingNote || null);
  const [showPipelineViewer, setShowPipelineViewer] = useState(false);
  const draftValue = { ideaText, ideaUrl, ideaImages, ideaTag, ideaProduct, editingNote, aiProposal };
  const currentDraft = useRef(draftValue);
  currentDraft.current = draftValue;
  const draft = useChannelDraft(draftValue, {
    save: value => {
      if (value.ideaImages.some(img => img.includes('#omnicut-pending-'))) throw new Error('กรุณารอการแนบภาพให้เสร็จก่อนสลับช่อง');
      storage.setItem('producer_manual_draft', JSON.stringify(value));
    },
    reset: value => {
      setIdeaText(value.ideaText); setIdeaUrl(value.ideaUrl); setIdeaImages(value.ideaImages);
      setIdeaTag(value.ideaTag); setIdeaProduct(value.ideaProduct); setEditingNote(value.editingNote); setAiProposal(value.aiProposal);
    },
  });

  const fetchData = useCallback(async () => {
    setLoadError('');
    const [prodRes, notesRes] = await Promise.allSettled([getProducts(), getProducerNotes(channelToken)]);
    if (prodRes.status === 'fulfilled') {
      const data = prodRes.value;
      setProducts(Array.isArray(data) ? data : Array.isArray(data?.products) ? data.products : []);
    }
    if (notesRes.status === 'fulfilled' && notesRes.value?.success && Array.isArray(notesRes.value.notes)) {
      notesRevision.current = notesRes.value.revision;
      setPlaybookNotes(notesRes.value.notes);
      writePlaybookNotes(notesRes.value.notes, storage);
    } else setLoadError('โหลดคลังไอเดียจากเซิร์ฟเวอร์ไม่สำเร็จ ข้อมูลเดิมในเครื่องยังถูกเก็บไว้');
    setLoading(false);
  }, [channelToken, storage]);
  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!aiProposal && !activeZoomImage && !editingNote) return undefined;
    const dialog = document.querySelector('[role="dialog"]');
    const previousFocus = document.activeElement;
    const getFocusable = () => dialog
      ? Array.from(dialog.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      : [];
    getFocusable()[0]?.focus();
    const handleModalKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (activeZoomImage) setActiveZoomImage(null);
        else if (aiProposal) setAiProposal(null);
        else if (editingNote) setEditingNote(null);
        return;
      }
      if (event.key !== 'Tab' || !dialog) return;
      const focusable = getFocusable();
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleModalKeyDown);
    return () => {
      document.removeEventListener('keydown', handleModalKeyDown);
      if (previousFocus instanceof HTMLElement && document.contains(previousFocus)) previousFocus.focus();
    };
  }, [activeZoomImage, aiProposal, editingNote]);

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
  const processRefImageFiles = files => draft.run(() => processRefImageFilesWork(files));
  const processRefImageFilesWork = async (files) => {
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
        const res = await uploadRefMedia(file, channelToken);
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

    // Build the row without publishing a cache entry before the server accepts it.
    const updated = addPlaybookNote(newNote, playbookNotes, null);
    const localNote = updated[0];

    // Sync one item so another device cannot be overwritten by a stale list.
    try {
      await draft.run(async () => {
      const res = await addProducerNote(localNote, channelToken);
      if (!res?.success || !Array.isArray(res.notes)) throw new Error('เซิร์ฟเวอร์ไม่ยืนยันการบันทึก');
      if (res?.success && Array.isArray(res.notes)) {
        notesRevision.current = res.revision;
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
      const unchanged = ['ideaText', 'ideaUrl', 'ideaImages', 'ideaTag', 'ideaProduct'].every(key => JSON.stringify(currentDraft.current[key]) === JSON.stringify(draftValue[key]));
      const nextDraft = unchanged ? { ...currentDraft.current, ideaText: '', ideaUrl: '', ideaImages: [] } : currentDraft.current;
      try {
        storage.setItem('producer_manual_draft', JSON.stringify(nextDraft));
        draft.markSaved(nextDraft);
      } catch { setToastMessage('บันทึกโน้ตแล้ว แต่ยังเก็บร่างอื่นในเครื่องไม่ได้'); }
      if (unchanged) { setIdeaText(''); setIdeaUrl(''); setIdeaImages([]); }
      setRefSaveSuccess(true);
      setTimeout(() => setRefSaveSuccess(false), 2500);
      });
    } catch (err) {
      setToastMessage('บันทึกไม่สำเร็จ ข้อมูลที่พิมพ์ยังอยู่ กรุณาลองใหม่');
      setTimeout(() => setToastMessage(null), 3500);
      console.warn('Failed to sync note to server:', err);
    }
  };

  // Handle Delete Note
  const handleDeleteNote = async (id) => {
    const updated = deletePlaybookNote(id, playbookNotes, storage);
    setPlaybookNotes(updated);
    try {
      const res = await deleteProducerNote(id, channelToken);
      if (res?.success && Array.isArray(res.notes)) {
        notesRevision.current = res.revision;
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

  // Handle Toggle Pin Note
  const handleTogglePinNote = async (item) => {
    const newPinned = !item.isPinned;
    const patched = { ...item, isPinned: newPinned };
    const updated = playbookNotes.map(n => n.id === item.id ? patched : n);
    setPlaybookNotes(updated);
    try {
      const res = await updateProducerNote(item.id, { isPinned: newPinned }, notesRevision.current, channelToken);
      if (res?.success && Array.isArray(res.notes)) {
        notesRevision.current = res.revision;
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
      setToastMessage(newPinned ? 'ปักหมุดโน้ตไว้ด้านบนสุดแล้ว 📌' : 'ยกเลิกการปักหมุดแล้ว');
      setTimeout(() => setToastMessage(null), 2500);
    } catch (err) {
      setPlaybookNotes(playbookNotes);
      savePlaybookNotes(playbookNotes);
      setToastMessage('ไม่สามารถอัปเดตการปักหมุดบนเซิร์ฟเวอร์ได้');
      setTimeout(() => setToastMessage(null), 3000);
      console.warn('Failed to update note pin state:', err);
    }
  };

  // Handle Save Edited Note
  const handleSaveEditedNote = async (updatedFields) => {
    if (!editingNote) return;
    try {
      await draft.run(async () => {
      if (!editingNote.base_revision) throw new Error('ไม่พบรุ่นข้อมูลเดิม กรุณาโหลดโน้ตใหม่ก่อนแก้ไข');
      const res = await updateProducerNote(editingNote.id, updatedFields, editingNote.base_revision, channelToken);
      if (!res?.success || !Array.isArray(res.notes)) throw new Error('เซิร์ฟเวอร์ไม่ยืนยันการบันทึก');
      if (res?.success && Array.isArray(res.notes)) {
        notesRevision.current = res.revision;
        setPlaybookNotes(res.notes);
        savePlaybookNotes(res.notes);
      }
      setToastMessage('บันทึกการแก้ไขโน้ตเรียบร้อยแล้ว');
      setTimeout(() => setToastMessage(null), 2500);
      const unchanged = JSON.stringify(currentDraft.current.editingNote) === JSON.stringify(editingNote);
      const nextNote = unchanged ? null : { ...currentDraft.current.editingNote, base_revision: res.revision };
      setEditingNote(nextNote);
      const nextDraft = { ...currentDraft.current, editingNote: nextNote };
      try {
        storage.setItem('producer_manual_draft', JSON.stringify(nextDraft));
        draft.markSaved(nextDraft);
      } catch { setToastMessage('บันทึกโน้ตแล้ว แต่ยังเก็บร่างอื่นในเครื่องไม่ได้'); }
      });
    } catch (err) {
      setToastMessage('ไม่สามารถบันทึกการแก้ไขได้ กรุณาลองใหม่');
      setTimeout(() => setToastMessage(null), 3500);
      console.warn('Failed to update note:', err);
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

      await draft.run(async () => {
      await addProductAngle(targetProdId, newAngleData);
      await fetchData(); // Refresh data to immediately show in daily queue
      const unchanged = JSON.stringify(currentDraft.current.aiProposal) === JSON.stringify(aiProposal);
      const nextProposal = unchanged ? null : currentDraft.current.aiProposal;
      setAiProposal(nextProposal);
      const nextDraft = { ...currentDraft.current, aiProposal: nextProposal };
      try {
        storage.setItem('producer_manual_draft', JSON.stringify(nextDraft));
        draft.markSaved(nextDraft);
      } catch { setToastMessage('เพิ่มมุมมองแล้ว แต่ยังเก็บร่างอื่นในเครื่องไม่ได้'); }
      setToastMessage('เพิ่มมุมมองใหม่เข้าสินค้าเรียบร้อยแล้ว!');
      setTimeout(() => setToastMessage(null), 3500);
      });
    } catch (err) {
      console.error('Failed to add angle:', err);
      alert('บันทึกมุมมองไม่สำเร็จ: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAddingAngle(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center min-h-[250px] text-slate-400"><RefreshCw className="mr-2 h-6 w-6 animate-spin text-amber-500" />กำลังโหลดคลังไอเดีย...</div>;
  return <div className="space-y-4 pb-12">
    {loadError && <div role="alert" className="space-y-2 text-amber-300"><p>{loadError}</p><button type="button" onClick={fetchData} className="rounded-lg border border-white/15 px-3 py-2 text-slate-200">ลองโหลดไอเดียใหม่</button></div>}
      {/* ── AI Production Pipeline Flow Banner & Interactive Viewer ── */}
      <div className="rounded-2xl bg-gradient-to-r from-cyan-950/40 via-slate-900/80 to-purple-950/40 border border-cyan-500/20 p-4 shadow-xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400/20 to-blue-500/20 border border-cyan-400/30 flex items-center justify-center text-cyan-300 flex-shrink-0 shadow-lg shadow-cyan-500/10">
              <Sparkles className="w-5 h-5 text-cyan-300" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-white tracking-tight">OmniCut AI Production Pipeline Flow</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-400/10 text-cyan-300 border border-cyan-400/25">
                  Interactive SOP & Master Prompts
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-400/10 text-amber-300 border border-amber-400/25">
                  Gemini 3.8 Flash TTS
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                ผังกระบวนการผลิตคลิปแนวตั้ง 9:16 ด้วย AI ครบวงจร (สคริปต์ ➔ เสียงคู่รักใต้ ➔ ดราฟต์ ➔ TikTok Sharpness ➔ Auto ปก CTA ➔ โพสต์)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
            <button
              type="button"
              onClick={() => setShowPipelineViewer(!showPipelineViewer)}
              className="px-3.5 py-1.5 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 text-xs font-semibold text-cyan-300 hover:text-white border border-cyan-500/30 flex items-center gap-1.5 cursor-pointer transition-all shadow-sm"
            >
              <span>{showPipelineViewer ? 'ซ่อนแผนผัง' : 'เปิดดูแผนผัง Interactive'}</span>
            </button>
            <a
              href="/ai_pipeline_flow.html"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-all"
              title="เปิดแผนผังแบบเต็มหน้าต่างในแท็บใหม่"
            >
              <span>เปิดแท็บใหม่</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          </div>
        </div>

        {/* Embedded Interactive Viewer Drawer */}
        {showPipelineViewer && (
          <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 text-cyan-300">
                <span>⚡ แผนผังสถาปัตยกรรมสด (Mermaid Graph Zoom/Pan + คลังคำสั่ง 1-Click Master Prompt)</span>
              </span>
              <a
                href="/ai_pipeline_flow.html#prompts-library"
                target="_blank"
                rel="noreferrer"
                className="text-amber-400 hover:underline flex items-center gap-1"
              >
                <span>ไปยังส่วน Prompts Library</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="w-full h-[700px] rounded-xl overflow-hidden border border-white/10 bg-[#070c18] shadow-inner">
              <iframe
                src="/ai_pipeline_flow.html"
                title="OmniCut AI Production Pipeline Flow"
                className="w-full h-full border-0"
              />
            </div>
          </div>
        )}
      </div>

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
              href="/ai_pipeline_flow.html"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-amber-300 hover:text-white border border-amber-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
              title="เปิดดูแผนผัง AI Production Pipeline Flow"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>ผัง AI Pipeline</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
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
                accept="image/*"
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
                  className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-2.5 group ${
                    item.isPinned
                      ? 'bg-amber-500/[0.05] border-amber-500/40 shadow-sm shadow-amber-500/10'
                      : 'bg-slate-800/40 border-white/5 hover:border-amber-500/30'
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {item.isPinned && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                            <Pin className="w-2.5 h-2.5 fill-amber-400 text-amber-400" />
                            <span>ปักหมุด</span>
                          </span>
                        )}
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

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTogglePinNote(item);
                          }}
                          className={`p-1.5 rounded-lg border text-xs font-semibold flex items-center cursor-pointer transition-all ${
                            item.isPinned
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                              : 'bg-white/5 hover:bg-white/10 text-slate-400 border-white/10'
                          }`}
                          title={item.isPinned ? 'ยกเลิกการปักหมุด' : 'ปักหมุดให้อยู่บนสุด'}
                          aria-label={item.isPinned ? 'ยกเลิกการปักหมุด' : 'ปักหมุดให้อยู่บนสุด'}
                        >
                          <Pin className={`w-3 h-3 ${item.isPinned ? 'fill-amber-400 text-amber-400' : ''}`} />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingNote({ ...item, base_revision: notesRevision.current });
                          }}
                          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 text-xs font-semibold flex items-center cursor-pointer transition-all"
                          title="แก้ไขข้อความโน้ต"
                          aria-label="แก้ไขข้อความโน้ต"
                        >
                          <Edit3 className="w-3 h-3 text-cyan-400" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteNote(item.id);
                          }}
                          className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 text-xs font-semibold flex items-center cursor-pointer transition-all shadow-sm"
                          title="ลบรายการนี้"
                          aria-label="ลบรายการนี้"
                        >
                          <Trash2 className="w-3 h-3 text-rose-400" />
                        </button>
                      </div>
                    </div>

                    {item.text && (
                      <p className="text-xs text-slate-200 leading-relaxed font-medium line-clamp-3">
                        {item.text}
                      </p>
                    )}

                    {/* Multi-Image Gallery */}
                    {itemImages.length === 1 && (
                      <div
                        role="button"
                        tabIndex={0}
                        aria-label="ดูรูปอ้างอิงขนาดใหญ่"
                        onClick={() => setActiveZoomImage(itemImages[0])}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            setActiveZoomImage(itemImages[0]);
                          }
                        }}
                        className="relative rounded-lg overflow-hidden border border-white/10 max-h-28 bg-black/40 cursor-zoom-in group/img focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/80"
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
                                role="button"
                                tabIndex={0}
                                aria-label={`ดูรูปอ้างอิงที่ ${imgIdx + 1} ขนาดใหญ่`}
                                onClick={() => setActiveZoomImage(imgUrl)}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter' || event.key === ' ') {
                                    event.preventDefault();
                                    setActiveZoomImage(imgUrl);
                                  }
                                }}
                                className="relative h-16 rounded-lg overflow-hidden border border-white/10 bg-black/40 cursor-pointer group/thumb hover:border-amber-500/40 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/80"
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
              {aiProposal.visual_insights && (
                <div className="p-3 rounded-xl bg-emerald-950/25 border border-emerald-500/30 text-emerald-200 text-xs flex items-start gap-2.5">
                  <span className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                    <Sparkles className="w-3.5 h-3.5" />
                  </span>
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">
                      ข้อมูลเชิงลึกจากภาพเรฟ (Visual Insights)
                    </span>
                    <p className="text-xs text-emerald-100/90 leading-relaxed">
                      {aiProposal.visual_insights}
                    </p>
                  </div>
                </div>
              )}

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
            className="relative max-w-4xl max-h-[90vh] flex flex-col items-center gap-3 cursor-default"
          >
            <button
              type="button"
              onClick={() => setActiveZoomImage(null)}
              className="absolute -top-11 right-0 p-2 rounded-full bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white cursor-pointer transition-colors shadow-lg"
              title="ปิดรูปขยาย"
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

      {/* ── Edit Note Modal ── */}
      {editingNote && (
        <div
          onClick={() => setEditingNote(null)}
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto animate-fadeIn"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-note-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded-2xl bg-slate-900 border border-white/10 p-5 sm:p-6 shadow-2xl space-y-4 my-auto"
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 id="edit-note-title" className="text-base font-bold text-white flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-cyan-400" />
                <span>แก้ไขข้อความโน้ต</span>
              </h3>
              <button
                type="button"
                onClick={() => setEditingNote(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">ข้อความไอเดีย</label>
                <textarea
                  rows={4}
                  value={editingNote.text || ''}
                  onChange={(e) => setEditingNote({ ...editingNote, text: e.target.value })}
                  placeholder="พิมพ์ข้อความไอเดียหรือสรุปประเด็น..."
                  className="w-full p-3 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-cyan-400 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">หมวดหมู่ (Tag)</label>
                  <input
                    type="text"
                    value={editingNote.tag || ''}
                    onChange={(e) => setEditingNote({ ...editingNote, tag: e.target.value })}
                    placeholder="เช่น Hook, Visual, Promo"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">ชื่อสินค้า (ถ้ามี)</label>
                  <input
                    type="text"
                    value={editingNote.productName || ''}
                    onChange={(e) => setEditingNote({ ...editingNote, productName: e.target.value })}
                    placeholder="ชื่อสินค้า"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">ลิงก์เรฟ (URL)</label>
                <input
                  type="text"
                  value={editingNote.url || ''}
                  onChange={(e) => setEditingNote({ ...editingNote, url: e.target.value })}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-white/10 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingNote(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 cursor-pointer"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={() => handleSaveEditedNote({
                  text: editingNote.text,
                  tag: editingNote.tag,
                  productName: editingNote.productName,
                  url: editingNote.url,
                })}
                className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer shadow-lg shadow-cyan-500/20 active:scale-95 transition-all"
              >
                <Check className="w-3.5 h-3.5" />
                <span>บันทึกการแก้ไข</span>
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
  </div>;
}
