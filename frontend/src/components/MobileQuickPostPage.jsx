import React, { useState, useEffect, useCallback } from 'react';
import {
  Download, Copy, Check, ExternalLink, ShoppingBag, Sparkles,
  Smartphone, CheckCircle2, ArrowRight, Video, AlertCircle,
  Tag, Film, Play, RotateCcw, Home
} from 'lucide-react';
import { updateAngleStatus, getProducts } from '../api';

export default function MobileQuickPostPage({ onExit }) {
  const [params, setParams] = useState(() => {
    const p = new URLSearchParams(window.location.search);
    return {
      productId: p.get('pid') || '',
      angleId: p.get('aid') || '',
      videoUrl: p.get('video') || '',
      productName: p.get('product') || '',
      hookTitle: p.get('hook') || '',
      caption: p.get('caption') || '',
      hashtags: p.get('hashtags') || '',
    };
  });

  const [productData, setProductData] = useState(null);
  const [angleData, setAngleData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copiedCaption, setCopiedCaption] = useState(false);
  const [copiedProduct, setCopiedProduct] = useState(false);
  const [isDownloaded, setIsDownloaded] = useState(false);
  const [isPosted, setIsPosted] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Fetch live product & angle details if pid/aid are available
  useEffect(() => {
    if (!params.productId && !params.angleId) return;

    let isMounted = true;
    setLoading(true);

    getProducts()
      .then((res) => {
        if (!isMounted) return;
        if (res.products) {
          const foundProd = res.products.find(p => p.id === params.productId);
          if (foundProd) {
            setProductData(foundProd);
            const foundAngle = foundProd.angles?.find(a => a.angle_id === params.angleId);
            if (foundAngle) {
              setAngleData(foundAngle);
              // If angle already marked as posted
              if (foundAngle.status === 'posted') {
                setIsPosted(true);
              }
            }
          }
        }
      })
      .catch((err) => {
        console.error('Error loading quick post data:', err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [params.productId, params.angleId]);

  // Resolved Display Values
  const effectiveProduct = angleData?.parentProduct?.name || productData?.name || params.productName || 'สินค้า TikTok Shop';
  const effectiveHook = angleData?.hook_title || params.hookTitle || 'คลิปรีวิวสินค้า';
  const effectiveCaption = angleData?.tiktok_caption || params.caption || '';
  const effectiveHashtags = angleData?.tiktok_hashtags || params.hashtags || '';
  const effectiveVideo = angleData?.video_url || params.videoUrl || '';
  const fullPostText = `${effectiveCaption}\n\n${effectiveHashtags}`.trim();

  // Step 1: Handle Video Download / Save
  const handleDownloadVideo = () => {
    if (!effectiveVideo) {
      showToast('ไม่พบที่อยู่วิดีโอสำหรับดาวน์โหลด');
      return;
    }
    const downloadUrl = `/api/media/${effectiveVideo}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = effectiveVideo.split(/[\\/]/).pop() || 'tiktok_video.mp4';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setIsDownloaded(true);
    showToast('กำลังดาวน์โหลดวิดีโอ...');
  };

  // Step 2: Copy Caption & Hashtags
  const handleCopyCaption = () => {
    if (!fullPostText) {
      showToast('ไม่มีข้อความแคปชัน');
      return;
    }
    navigator.clipboard.writeText(fullPostText).then(() => {
      setCopiedCaption(true);
      showToast('คัดลอกแคปชัน & แฮชแท็กเรียบร้อย!');
      setTimeout(() => setCopiedCaption(false), 2500);
    }).catch(() => {
      showToast('ไม่สามารถคัดลอกได้อัตโนมัติ กรุณากดเลือกข้อความด้วยตนเอง');
    });
  };

  // Step 3: Copy Product Name for TikTok Shop Tagging
  const handleCopyProductName = () => {
    if (!effectiveProduct) return;
    navigator.clipboard.writeText(effectiveProduct).then(() => {
      setCopiedProduct(true);
      showToast(`คัดลอก "${effectiveProduct}" สำหรับค้นหาปักตะกร้าแล้ว!`);
      setTimeout(() => setCopiedProduct(false), 2500);
    }).catch(() => {
      showToast('ไม่สามารถคัดลอกได้');
    });
  };

  // Step 4: Open TikTok App
  const handleLaunchTikTok = () => {
    // Attempt TikTok URL scheme, fallback to web
    const tiktokScheme = 'snssdk1180://feed';
    const fallbackUrl = 'https://www.tiktok.com/';

    const start = Date.now();
    window.location.href = tiktokScheme;

    setTimeout(() => {
      if (Date.now() - start < 1500) {
        window.location.href = fallbackUrl;
      }
    }, 1000);
  };

  // Step 5: Mark as Posted
  const handleMarkAsPosted = async () => {
    if (params.productId && params.angleId) {
      try {
        await updateAngleStatus(params.productId, params.angleId, 'posted', effectiveVideo, null, null, true);
        setIsPosted(true);
        showToast('🎉 บันทึกสถานะ "โพสต์แล้ว" ส่งกลับไปที่คอมพิวเตอร์เรียบร้อย!');
      } catch (err) {
        showToast('ไม่สามารถอัปเดตสถานะได้: ' + err.message);
      }
    } else {
      setIsPosted(true);
      showToast('🎉 มาร์กว่าโพสต์เรียบร้อยแล้ว!');
    }
  };

  return (
    <div className="min-h-screen bg-[#070A12] text-white flex flex-col justify-between max-w-lg mx-auto p-4 sm:p-6 font-prompt">
      {/* ── Toast Notification ── */}
      {toastMessage && (
        <div className="fixed top-4 left-4 right-4 z-50 p-3.5 rounded-2xl bg-[#25F4EE] text-slate-950 font-bold text-xs text-center shadow-2xl border border-white/20 animate-slideDown">
          {toastMessage}
        </div>
      )}

      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-md">
            <Smartphone className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-black uppercase tracking-wider text-[#25F4EE] font-mono">
              Quick Post Companion
            </h1>
            <p className="text-[11px] text-slate-400">ผู้ช่วยโพสต์คลิป TikTok</p>
          </div>
        </div>

        {onExit && (
          <button
            onClick={onExit}
            className="py-1.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-1 cursor-pointer transition-colors"
          >
            <Home className="w-3.5 h-3.5" />
            <span>หน้าหลัก</span>
          </button>
        )}
      </div>

      {/* ── Main Content Body ── */}
      <div className="space-y-4 py-4 flex-1">
        {/* Product & Hook Banner */}
        <div className="p-3.5 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-1.5 shadow-lg">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-white text-sm font-kanit truncate">{effectiveProduct}</span>
            {isPosted ? (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <Check className="w-3 h-3" /> โพสต์แล้ว
              </span>
            ) : (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                พร้อมโพสต์
              </span>
            )}
          </div>
          <div className="p-2 rounded-xl bg-black/40 border-l-3 border-[#25F4EE] text-xs font-bold text-cyan-200 leading-snug">
            {effectiveHook}
          </div>
        </div>

        {/* Video Preview (if video exists) */}
        {effectiveVideo && (
          <div className="rounded-2xl overflow-hidden bg-black border border-white/[0.1] shadow-2xl relative max-w-[240px] mx-auto">
            <video
              src={`/api/media/${effectiveVideo}`}
              controls
              playsInline
              className="w-full aspect-[9/16] object-contain max-h-[280px] mx-auto bg-black"
            />
          </div>
        )}

        {/* ── Step 1: Download Video ── */}
        <div className="p-4 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-2.5 shadow-md">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-5 h-5 rounded-full bg-[#25F4EE]/20 border border-[#25F4EE]/40 flex items-center justify-center text-[#25F4EE] text-[10px] font-mono">1</span>
              <span>บันทึกวิดีโอเข้าม้วนฟิล์ม (Photos)</span>
            </span>
            {isDownloaded && <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-0.5"><Check className="w-3 h-3" /> ดาวน์โหลดแล้ว</span>}
          </div>

          <button
            type="button"
            onClick={handleDownloadVideo}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/20 active:scale-95 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>ดาวน์โหลดวิดีโอ MP4</span>
          </button>
          <p className="text-[10px] text-slate-400 leading-relaxed text-center">
            💡 สำหรับ iPhone: แตะดาวน์โหลด หรือแตะค้างที่วิดีโอด้านบนแล้วเลือก <b>"บันทึกวิดีโอ" (Save Video)</b>
          </p>
        </div>

        {/* ── Step 2: Copy Caption & Hashtags ── */}
        <div className="p-4 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-2.5 shadow-md">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-pink-400">
              <span className="w-5 h-5 rounded-full bg-[#FE2C55]/20 border border-[#FE2C55]/40 flex items-center justify-center text-[#FE2C55] text-[10px] font-mono">2</span>
              <span>แคปชัน & แฮชแท็กไวรัล</span>
            </span>
            <span className="text-[10px] text-slate-500 font-mono">{fullPostText.length} อักษร</span>
          </div>

          <div className="p-3 rounded-xl bg-black/50 border border-white/[0.06] text-xs text-slate-200 font-mono leading-relaxed line-clamp-4 select-all">
            {fullPostText || 'ยังไม่มีแคปชัน'}
          </div>

          <button
            type="button"
            onClick={handleCopyCaption}
            className={`w-full py-2.5 px-4 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer active:scale-95 ${
              copiedCaption
                ? 'bg-emerald-500 text-slate-950 font-black'
                : 'bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] text-white'
            }`}
          >
            {copiedCaption ? (
              <>
                <Check className="w-4 h-4 text-slate-950 stroke-[3]" />
                <span>คัดลอกแคปชันเรียบร้อยแล้ว!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-[#25F4EE]" />
                <span>คัดลอกแคปชัน & แฮชแท็ก</span>
              </>
            )}
          </button>
        </div>

        {/* ── Step 3: Copy Product Name for Tagging ── */}
        <div className="p-4 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-2.5 shadow-md">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-amber-400">
              <span className="w-5 h-5 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 text-[10px] font-mono">3</span>
              <span>คีย์เวิร์ดสำหรับ "ปักตะกร้า" (TikTok Shop)</span>
            </span>
          </div>

          <div className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-black/50 border border-white/[0.06]">
            <div className="flex items-center gap-2 min-w-0">
              <ShoppingBag className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span className="text-xs font-bold text-amber-200 truncate">{effectiveProduct}</span>
            </div>
            <button
              type="button"
              onClick={handleCopyProductName}
              className="py-1 px-2.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1 flex-shrink-0 cursor-pointer active:scale-95 transition-all"
            >
              {copiedProduct ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedProduct ? 'คัดลอกแล้ว' : 'คัดลอก'}</span>
            </button>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            💡 ในหน้าก่อนโพสต์ TikTok ให้แตะ <b>"เพิ่มลิงก์" → "สินค้า"</b> แล้ววางชื่อนี้ในช่องค้นหาเพื่อปักตะกร้าได้ทันที
          </p>
        </div>

        {/* ── Step 4: Open TikTok App ── */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleLaunchTikTok}
            className="w-full py-3.5 px-4 rounded-2xl bg-gradient-to-r from-[#FE2C55] via-pink-600 to-[#25F4EE] hover:brightness-110 text-white text-sm sm:text-base font-black flex items-center justify-center gap-2 shadow-xl shadow-[#FE2C55]/25 active:scale-95 transition-all cursor-pointer"
          >
            <ExternalLink className="w-5 h-5 flex-shrink-0" />
            <span>4. เปิดแอป TikTok ทันที</span>
          </button>
        </div>

        {/* ── Step 5: Mark as Posted ── */}
        <div className="pt-1">
          <button
            type="button"
            onClick={handleMarkAsPosted}
            disabled={isPosted}
            className={`w-full py-3 px-4 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer active:scale-95 ${
              isPosted
                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 cursor-default'
                : 'bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-slate-300 hover:text-white'
            }`}
          >
            <CheckCircle2 className={`w-4 h-4 ${isPosted ? 'text-emerald-400' : 'text-slate-400'}`} />
            <span>{isPosted ? '✓ โพสต์ลง TikTok เรียบร้อยแล้ว' : '5. มาร์กว่า "โพสต์ลง TikTok แล้ว"'}</span>
          </button>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="text-center py-2 border-t border-white/[0.06] text-[10px] text-slate-500">
        OmniCut Pro Studio · Semi-Auto Mobile Companion
      </div>
    </div>
  );
}
