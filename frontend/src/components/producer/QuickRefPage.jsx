import React, { useState, useEffect, useRef } from 'react';
import {
  Bookmark, Link as LinkIcon, Image as ImageIcon, Sparkles,
  ArrowLeft, Check, Trash2, ExternalLink, X, Smartphone, Tag
} from 'lucide-react';
import {
  loadPlaybookNotes,
  addPlaybookNote,
  deletePlaybookNote,
  detectRefPlatform
} from '../../lib/producerInsights';
import { getProducts, uploadRefMedia } from '../../api';

export default function QuickRefPage({ onExit }) {
  const [notes, setNotes] = useState(() => loadPlaybookNotes());
  const [products, setProducts] = useState([]);
  const [ideaText, setIdeaText] = useState('');
  const [refUrl, setRefUrl] = useState('');
  const [selectedTag, setSelectedTag] = useState('Ref Clip');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [previewImage, setPreviewImage] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [copiedSuccess, setCopiedSuccess] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    getProducts()
      .then(res => {
        const list = Array.isArray(res) ? res : (res?.products || []);
        setProducts(list);
      })
      .catch(() => {});
  }, []);

  const handleImageSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Local instant preview
    const reader = new FileReader();
    reader.onload = () => {
      setPreviewImage(reader.result);
    };
    reader.readAsDataURL(file);

    // Optional server upload
    try {
      setUploadingImage(true);
      const uploadRes = await uploadRefMedia(file);
      if (uploadRes?.url) {
        setPreviewImage(uploadRes.url);
      }
    } catch (err) {
      console.warn('Server image upload failed, using local data URL instead:', err);
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
    setSelectedProductId('');
    setCopiedSuccess(true);
    setTimeout(() => setCopiedSuccess(false), 2000);
  };

  const handleDelete = (id) => {
    const updated = deletePlaybookNote(id, notes);
    setNotes(updated);
  };

  const detectedPlatform = detectRefPlatform(refUrl);

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 flex flex-col max-w-md mx-auto p-4 space-y-4">
      {/* ── Top App Bar (iPhone 15 Pro Max Header) ── */}
      <header className="flex items-center justify-between pt-2 pb-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2.5">
          <button
            onClick={onExit || (() => { window.location.href = window.location.pathname; })}
            className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300 hover:text-white cursor-pointer transition-colors"
            title="กลับหน้าหลัก"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-1.5">
              <Smartphone className="w-4 h-4 text-amber-400" />
              <span>จดไอเดีย & เซฟเรฟด่วน</span>
            </h1>
            <p className="text-[11px] text-slate-400">TikTok · Pinterest · ไอเดียตัดคลิป</p>
          </div>
        </div>

        <button
          onClick={onExit || (() => { window.location.href = window.location.pathname; })}
          className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white transition-colors cursor-pointer"
        >
          เปิดหน้าเต็ม
        </button>
      </header>

      {/* ── Quick Input Card ── */}
      <div className="p-4 rounded-2xl bg-slate-900/90 border border-amber-500/20 shadow-xl space-y-3">
        <div>
          <label className="block text-[11px] font-bold text-slate-300 mb-1">
            ลิงก์คลิปเรฟ (TikTok / Pinterest / YouTube)
          </label>
          <div className="relative">
            <input
              type="url"
              value={refUrl}
              onChange={(e) => setRefUrl(e.target.value)}
              placeholder="แปะลิงก์คลิปต้นฉบับที่นี่..."
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50 pr-20"
            />
            {detectedPlatform && (
              <span className="absolute right-2.5 top-2.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40">
                {detectedPlatform}
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-slate-300 mb-1">
            ไอเดีย / จุดเด่นที่ชอบ / สิ่งที่ต้องทำตาม
          </label>
          <textarea
            value={ideaText}
            onChange={(e) => setIdeaText(e.target.value)}
            placeholder="เช่น ฮุกเปิดคลิปเทน้ำแข็งใส่พัดลม, ทำตามจังหวะเพลงนี้, ขยี้เรื่องมือถือกระตุก..."
            rows={2}
            className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50 resize-none"
          />
        </div>

        {/* Media & Tag Selection */}
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
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingImage}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
            <span>{previewImage ? 'เปลี่ยนรูปเรฟ' : 'แนบภาพ/แคปหน้าจอ'}</span>
          </button>

          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-800 border border-white/10 text-xs text-slate-200 focus:outline-none cursor-pointer"
          >
            <option value="Ref Clip">เรฟคลิป (Ref Clip)</option>
            <option value="Hook">ฮุกเปิดคลิป (Hook)</option>
            <option value="Visual">มุมภาพ (Visual)</option>
            <option value="Audio">เสียง / เพลง (Audio)</option>
            <option value="Promo">โปรโมชั่น (Promo)</option>
          </select>

          {products.length > 0 && (
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 border border-white/10 text-xs text-slate-200 focus:outline-none cursor-pointer max-w-[140px] truncate"
            >
              <option value="">ผูกสินค้า (ไม่บังคับ)</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.product_code || ''} {p.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Preview image if attached */}
        {previewImage && (
          <div className="relative inline-block mt-2">
            <img
              src={previewImage}
              alt="Ref preview"
              className="h-20 w-auto rounded-lg border border-white/10 object-cover"
            />
            <button
              onClick={() => setPreviewImage(null)}
              className="absolute -top-1.5 -right-1.5 p-0.5 rounded-full bg-red-600 text-white cursor-pointer"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={!ideaText.trim() && !refUrl.trim() && !previewImage}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-[0.98] text-slate-950 font-bold text-sm flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-amber-500/20 disabled:opacity-40 transition-all"
        >
          {copiedSuccess ? <Check className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
          <span>{copiedSuccess ? 'บันทึกเรียบร้อย!' : 'บันทึกเข้าคลังไอเดีย'}</span>
        </button>
      </div>

      {/* ── Saved Ideas & Refs List ── */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pb-8">
        <div className="flex items-center justify-between text-xs text-slate-400 font-bold px-1">
          <span>ไอเดียและเรฟที่บันทึกไว้ ({notes.length})</span>
        </div>

        {notes.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            ยังไม่มีไอเดียที่บันทึกไว้ — แปะลิงก์ TikTok หรือรูปเรฟด้านบนได้เลย!
          </div>
        ) : (
          notes.map((item) => {
            const platform = detectRefPlatform(item.url);
            return (
              <div
                key={item.id}
                className="p-3.5 rounded-xl bg-slate-900/70 border border-white/5 space-y-2 group hover:border-amber-500/30 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                      <Tag className="w-2.5 h-2.5" />
                      {item.tag || 'Idea'}
                    </span>
                    {item.productName && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-white/10 truncate max-w-[120px]">
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
                    onClick={() => handleDelete(item.id)}
                    className="p-1 rounded text-slate-500 hover:text-red-400 cursor-pointer transition-colors"
                    title="ลบ"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {item.text && (
                  <p className="text-xs text-slate-200 leading-relaxed font-medium">
                    {item.text}
                  </p>
                )}

                {item.imageUrl && (
                  <img
                    src={item.imageUrl}
                    alt="Ref attachment"
                    className="max-h-32 w-auto rounded-lg border border-white/10 object-cover mt-1"
                  />
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
            );
          })
        )}
      </div>
    </div>
  );
}
