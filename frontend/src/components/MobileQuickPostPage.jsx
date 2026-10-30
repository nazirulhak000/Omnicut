import React, { useState, useEffect, useRef } from 'react';
import {
  Download, Copy, Check, ExternalLink, ShoppingBag, Sparkles,
  Smartphone, CheckCircle2, ArrowRight, Video, AlertCircle,
  Tag, Film, Play, RotateCcw, Home, Lightbulb
} from 'lucide-react';
import { getProducts, markPosted } from '../api';
import { toMediaUrl } from '../lib/mediaUrl.js';
import { activeChannel } from '../lib/channelRuntime.js';
import { ChannelWorkspaceBar } from '../context/ChannelContext.jsx';
import { ConfirmModal } from './ui';
import { isAlreadyPostedError, isNoResponseError } from '../lib/mobileStudioFlow.js';

export default function MobileQuickPostPage({ onExit }) {
  const [owner] = useState(activeChannel);
  const resolveMediaUrl = path => {
    try { return toMediaUrl(String(path || '').replace(/^api\/media\//, '/api/media/'), owner); }
    catch { return ''; }
  };
  const [params, setParams] = useState(() => {
    const p = new URLSearchParams(window.location.search);
    return {
      productId: p.get('pid') || '',
      angleId: p.get('aid') || '',
      exportId: p.get('eid') || '',
      videoUrl: p.get('video') || '',
      coverUrl: p.get('cover') || '',
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
  const [markingPosted, setMarkingPosted] = useState(false);
  const [showPostConfirm, setShowPostConfirm] = useState(false);
  // A mark-posted request that got no reply may still have moved the file;
  // the retry's 404 then means "already done", not "failed".
  const postAttemptLostRef = useRef(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
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
            const foundAngle = foundProd.angles?.find(a => (a.angle_id || a.id) === params.angleId);
            if (foundAngle) {
              setAngleData(foundAngle);
              // If angle already marked as posted
              if (foundAngle.status === 'posted' && params.exportId && foundAngle.export_id === params.exportId) {
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
  // The QR code carries the exact export. Angle-level video_url is only a
  // legacy fallback and must never override that stable identity.
  const effectiveVideo = params.videoUrl || angleData?.video_url || '';
  const effectiveCover9x16 = angleData?.cover_9x16_url || angleData?.cover_url || params.coverUrl || '';
  const effectiveCover3x4 = angleData?.cover_3x4_url || '';
  const mediaScopeInvalid = [effectiveVideo, effectiveCover9x16, effectiveCover3x4].some(path => path && !resolveMediaUrl(path));
  const canMarkPosted = Boolean(effectiveVideo && params.exportId && !mediaScopeInvalid);
  const fullPostText = `${effectiveCaption}\n\n${effectiveHashtags}`.trim();

  // Step 1: Handle Video Download / Save
  const handleDownloadVideo = () => {
    if (!effectiveVideo) {
      showToast('ไม่พบที่อยู่วิดีโอสำหรับดาวน์โหลด');
      return;
    }
    const downloadUrl = resolveMediaUrl(effectiveVideo);
    if (!downloadUrl) { showToast('ลิงก์ไฟล์ไม่ตรงกับช่องนี้ กรุณาเปิดลิงก์จากช่องเจ้าของคลิป'); return; }
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

  const handleDownloadCover = (coverUrl, fileName) => {
    if (!coverUrl) return;
    const downloadUrl = resolveMediaUrl(coverUrl);
    if (!downloadUrl) { showToast('ลิงก์ภาพปกไม่ตรงกับช่องนี้'); return; }
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName || 'cover.jpg';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('กำลังดาวน์โหลดภาพปก...');
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

  // Step 5: Mark as Posted (after an explicit confirm; idempotent on retry)
  const handleMarkAsPosted = async () => {
    if (isPosted || markingPosted) return;
    if (!canMarkPosted) {
      showToast('ต้องมี export_id และไฟล์ของช่องนี้ก่อนบันทึกสถานะโพสต์');
      return;
    }
    setMarkingPosted(true);
    try {
      const res = await markPosted(effectiveVideo, params.productId || null, params.angleId || null, params.exportId);
      postAttemptLostRef.current = false;
      setIsPosted(true);
      setShowPostConfirm(false);
      if (res?.status_warning || res?.post_log_warning) showToast('บันทึกไฟล์โพสต์แล้ว แต่ประวัติหรือสถานะยังมีคำเตือน กรุณาตรวจจากคอมพิวเตอร์');
      else showToast('บันทึกสถานะ "โพสต์แล้ว" ส่งกลับไปที่คอมพิวเตอร์เรียบร้อย');
    } catch (err) {
      if (isAlreadyPostedError(err, { previousAttemptLost: postAttemptLostRef.current })) {
        postAttemptLostRef.current = false;
        setIsPosted(true);
        setShowPostConfirm(false);
        showToast('คลิปนี้ถูกบันทึกว่าโพสต์แล้ว');
        return;
      }
      setShowPostConfirm(false);
      if (isNoResponseError(err)) {
        postAttemptLostRef.current = true;
        showToast('การเชื่อมต่อหลุดระหว่างบันทึก ยังไม่แน่ใจว่าบันทึกแล้วหรือยัง กดมาร์กอีกครั้งเพื่อตรวจ');
      } else {
        showToast('ไม่สามารถอัปเดตสถานะได้: ' + (err?.response?.data?.detail || err.friendlyMessage || err.message));
      }
    } finally {
      setMarkingPosted(false);
    }
  };

  return (
    <div className="min-h-dvh bg-[#070A12] text-white flex flex-col justify-between max-w-lg mx-auto px-4 pt-[calc(env(safe-area-inset-top)+1rem)] pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:p-6 font-prompt">
      <ChannelWorkspaceBar />
      {mediaScopeInvalid && <p role="alert" className="py-3 text-sm text-rose-300">ลิงก์ไฟล์ไม่ตรงกับช่องนี้ กรุณาเปิดลิงก์จากช่องเจ้าของคลิป</p>}
      {!mediaScopeInvalid && !canMarkPosted && !isPosted && <p role="alert" className="py-3 text-sm text-rose-300">ไม่พบ export_id หรือไฟล์คลิป กรุณาเปิดลิงก์จากช่องเจ้าของคลิปอีกครั้ง</p>}
      {/* ── Toast Notification ── */}
      {toastMessage && (
        <div role="status" className="fixed top-[calc(env(safe-area-inset-top)+1rem)] left-4 right-4 z-50 p-3.5 rounded-2xl bg-[#25F4EE] text-slate-950 font-bold text-xs text-center shadow-2xl border border-white/20 animate-slideDown">
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
            className="min-h-11 py-1.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-1 cursor-pointer transition-colors"
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
            <span className="font-bold text-white text-sm truncate">{effectiveProduct}</span>
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
        {effectiveVideo && resolveMediaUrl(effectiveVideo) && (
          <div className="rounded-2xl overflow-hidden bg-black border border-white/[0.1] shadow-2xl relative max-w-[240px] mx-auto">
            <video
              src={resolveMediaUrl(effectiveVideo)}
              controls
              playsInline
              className="w-full aspect-[9/16] object-contain max-h-[280px] mx-auto bg-black"
            />
          </div>
        )}

        {/* ── Step 1: Download Video & Covers ── */}
        <div className="p-4 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-3 shadow-md">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-5 h-5 rounded-full bg-[#25F4EE]/20 border border-[#25F4EE]/40 flex items-center justify-center text-[#25F4EE] text-[10px] font-mono">1</span>
              <span>บันทึกวิดีโอ & ภาพปก (Photos)</span>
            </span>
            {isDownloaded && <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-0.5"><Check className="w-3 h-3" /> ดาวน์โหลดแล้ว</span>}
          </div>

          <button
            type="button"
            onClick={handleDownloadVideo}
            className="w-full min-h-11 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/20 active:scale-95 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>ดาวน์โหลดวิดีโอ MP4</span>
          </button>

          {(effectiveCover9x16 || effectiveCover3x4) && (
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.06]">
              {effectiveCover9x16 && (
                <button
                  type="button"
                  onClick={() => handleDownloadCover(effectiveCover9x16, `${effectiveProduct}_cover_9x16.jpg`)}
                  className="min-h-11 py-2 px-3 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-medium text-slate-200 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-cyan-400" />
                  <span>โหลดปก 9:16</span>
                </button>
              )}
              {effectiveCover3x4 && (
                <button
                  type="button"
                  onClick={() => handleDownloadCover(effectiveCover3x4, `${effectiveProduct}_cover_3x4.jpg`)}
                  className="min-h-11 py-2 px-3 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs font-medium text-slate-200 flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-purple-400" />
                  <span>โหลดปก 3:4</span>
                </button>
              )}
            </div>
          )}

          <p className="text-[10px] text-slate-400 leading-relaxed text-center">
            <Lightbulb className="inline w-3 h-3 mr-1 align-[-2px]" aria-hidden="true" />สำหรับ iPhone: แตะดาวน์โหลด หรือแตะค้างที่วิดีโอด้านบนแล้วเลือก <b>"บันทึกวิดีโอ" (Save Video)</b>
          </p>
        </div>

        {/* ── Step 2: Copy Caption & Hashtags ── */}
        <div className="p-4 rounded-2xl bg-[#0B0F19] border border-white/[0.08] space-y-2.5 shadow-md">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-pink-400">
              <span className="w-5 h-5 rounded-full bg-[#FE2C55]/20 border border-[#FE2C55]/40 flex items-center justify-center text-[#FE2C55] text-[10px] font-mono">2</span>
              <span>แคปชัน & แฮชแท็กไวรัล</span>
            </span>
            <span className="text-[10px] text-slate-500">{fullPostText.length} อักษร</span>
          </div>

          <div className="p-3 rounded-xl bg-black/50 border border-white/[0.06] text-xs text-slate-200 font-mono leading-relaxed line-clamp-4 select-all">
            {fullPostText || 'ยังไม่มีแคปชัน'}
          </div>

          <button
            type="button"
            onClick={handleCopyCaption}
            className={`w-full min-h-11 py-2.5 px-4 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer active:scale-95 ${
              copiedCaption
                ? 'bg-emerald-500 text-slate-950 font-black'
                : 'bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] text-white'
            }`}
          >
            {copiedCaption ? (
              <>
                <Check className="w-4 h-4 text-slate-950 stroke-[3]" />
                <span>คัดลอกแคปชันเรียบร้อยแล้ว</span>
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
              className="min-h-11 py-1 px-3 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1 flex-shrink-0 cursor-pointer active:scale-95 transition-all"
            >
              {copiedProduct ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedProduct ? 'คัดลอกแล้ว' : 'คัดลอก'}</span>
            </button>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            <Lightbulb className="inline w-3 h-3 mr-1 align-[-2px]" aria-hidden="true" />ในหน้าก่อนโพสต์ TikTok ให้แตะ <b>"เพิ่มลิงก์" → "สินค้า"</b> แล้ววางชื่อนี้ในช่องค้นหาเพื่อปักตะกร้าได้ทันที
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
            onClick={() => setShowPostConfirm(true)}
            disabled={isPosted || !canMarkPosted || markingPosted}
            className={`w-full min-h-11 py-3 px-4 rounded-xl disabled:opacity-60 text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer active:scale-95 ${
              isPosted
                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 cursor-default'
                : 'bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-slate-300 hover:text-white'
            }`}
          >
            <CheckCircle2 className={`w-4 h-4 ${isPosted ? 'text-emerald-400' : 'text-slate-400'}`} />
            <span>{isPosted ? 'บันทึกว่าโพสต์ลง TikTok แล้ว' : markingPosted ? 'กำลังบันทึก...' : '5. มาร์กว่า "โพสต์ลง TikTok แล้ว"'}</span>
          </button>
        </div>
        <ConfirmModal
          isOpen={showPostConfirm}
          onClose={() => { if (!markingPosted) setShowPostConfirm(false); }}
          onConfirm={handleMarkAsPosted}
          title="ยืนยันว่าโพสต์บน TikTok แล้ว"
          description="ระบบจะย้ายคลิปเข้าโฟลเดอร์ Posted และเปลี่ยนสถานะเป็นโพสต์แล้ว กดเฉพาะเมื่อคลิปขึ้นบน TikTok จริง"
          dangerNote={null}
          confirmText="ยืนยันว่าโพสต์แล้ว"
          cancelText="ยังไม่ได้โพสต์"
          loading={markingPosted}
          variant="info"
        />
      </div>

      {/* ── Footer ── */}
      <div className="text-center py-2 border-t border-white/[0.06] text-[10px] text-slate-500">
        OmniCut Pro Studio · Semi-Auto Mobile Companion
      </div>
    </div>
  );
}
