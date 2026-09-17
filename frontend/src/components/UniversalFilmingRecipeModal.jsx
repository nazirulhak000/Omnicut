import React, { useState, useEffect } from 'react';
import {
  X,
  Clapperboard,
  Clock,
  Camera,
  Sparkles,
  QrCode,
  CheckCircle2,
  Copy,
  Smartphone,
  Info,
  Film,
  Zap,
} from 'lucide-react';
import { getUniversalFilmingRecipe } from '../api';

export default function UniversalFilmingRecipeModal({
  isOpen,
  onClose,
  productData,
  showToast = () => {},
}) {
  const [loading, setLoading] = useState(false);
  const [recipe, setRecipe] = useState(null);
  const [showQr, setShowQr] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (isOpen && productData?.id) {
      setLoading(true);
      getUniversalFilmingRecipe(productData.id)
        .then((res) => {
          setRecipe(res);
        })
        .catch((err) => {
          console.error('Failed to load filming recipe:', err);
          showToast('ไม่สามารถโหลดสูตรถ่ายทำได้: ' + (err.response?.data?.detail || err.message), 'error');
        })
        .finally(() => setLoading(false));
    }
  }, [isOpen, productData?.id]);

  if (!isOpen) return null;

  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(currentUrl)}`;

  const handleCopyLink = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(currentUrl);
      setCopiedLink(true);
      showToast('คัดลอกลิงก์เปิดบนมือถือเรียบร้อยแล้ว!', 'success');
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'hook':
        return 'bg-[#FE2C55]/20 text-[#FE2C55] border-[#FE2C55]/40';
      case 'showcase':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/40';
      case 'macro':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/40';
      case 'action':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'cta':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600/50';
    }
  };

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center p-3 sm:p-5 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#0B0F17] border border-white/[0.12] rounded-2xl shadow-2xl shadow-black/80 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08] bg-[#0E131F]/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/20">
              <Clapperboard className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-black text-white tracking-tight">
                  สูตรถ่ายทำ 5 ช็อตมาตรฐาน
                </h2>
                {recipe?.category_badge && (
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30">
                    {recipe.category_badge}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                ถ่ายคลิปดิบครั้งเดียว 5 สเต็ปนี้ (30–55 วินาที) แล้วนำไปตัดต่อได้กับทุกสคริปต์ทันที
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowQr(!showQr)}
              className={`py-1.5 px-3 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                showQr
                  ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                  : 'bg-black/40 border-white/[0.1] text-slate-300 hover:text-white hover:border-white/30'
              }`}
              title="เปิดดูบนหน้าจอมือถือข้างกล้องถ่ายทำ"
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span>เปิดบนมือถือ</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {/* Quick Companion QR Banner (Toggleable) */}
          {showQr && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-slate-900/40 border border-[#25F4EE]/30 flex flex-col sm:flex-row items-center gap-4 animate-in slide-in-from-top-3 duration-200">
              <div className="p-2 bg-white rounded-xl shadow-lg shadow-black/50 flex-shrink-0">
                <img
                  src={qrCodeUrl}
                  alt="QR Code"
                  className="w-32 h-32 object-contain"
                />
              </div>
              <div className="space-y-2 text-center sm:text-left flex-1">
                <div className="flex items-center justify-center sm:justify-start gap-2 text-white font-bold text-sm">
                  <Smartphone className="w-4 h-4 text-[#25F4EE]" />
                  <span>สแกน QR Code เพื่อเปิดคู่มือนี้บนมือถือ</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  เปิดจอค้างไว้ข้างกล้องขณะกำลังถ่ายสินค้าจริง ช่วยให้จำคิวถ่ายได้แม่นยำ ไม่ต้องสลับหน้าจอคอมไปมา
                </p>
                <div className="pt-1 flex items-center justify-center sm:justify-start gap-2">
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="py-1 px-3 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
                  >
                    {copiedLink ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>คัดลอกลิงก์แล้ว!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-300" />
                        <span>คัดลอกลิงก์หน้าเว็บ</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Product Header Tip */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
              <span>
                สินค้า: <strong className="text-white font-semibold">{productData?.name || productData?.title}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Clock className="w-3.5 h-3.5" />
              <span>ความยาวคลิปรวม: ~45–60 วินาทีใน 1 เทค</span>
            </div>
          </div>

          {/* 5 Shots List */}
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <div className="w-7 h-7 border-2 border-[#25F4EE] border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">กำลังเตรียมสูตรถ่ายทำสำหรับสินค้านี้...</span>
            </div>
          ) : recipe?.shots ? (
            <div className="space-y-3">
              {recipe.shots.map((shot, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[#0D121D] border border-white/[0.08] hover:border-white/[0.16] transition-all flex flex-col sm:flex-row gap-3 sm:gap-4 items-start"
                >
                  {/* Step Badge */}
                  <div className="flex items-center gap-2 sm:flex-col sm:items-center sm:justify-center w-full sm:w-16 flex-shrink-0">
                    <span className="w-7 h-7 rounded-full bg-white/10 text-white font-black text-xs flex items-center justify-center">
                      {shot.shot_number}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider border ${getRoleBadgeColor(
                        shot.role
                      )}`}
                    >
                      {shot.role}
                    </span>
                  </div>

                  {/* Shot Details */}
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                        <Film className="w-4 h-4 text-[#25F4EE]" />
                        <span>{shot.title}</span>
                      </h4>
                      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800 text-[11px] text-slate-300 font-mono">
                        <Clock className="w-3 h-3 text-amber-400" />
                        <span>{shot.duration_hint}</span>
                      </div>
                    </div>

                    <div className="text-xs text-slate-200 leading-relaxed bg-black/30 p-2.5 rounded-lg border border-white/[0.04]">
                      <strong className="text-slate-400 block mb-1">🎬 สิ่งที่ต้องถ่าย / ท่าทาง:</strong>
                      {shot.action}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <Camera className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                        <span>
                          มุมกล้อง: <strong className="text-slate-200">{shot.camera_angle}</strong>
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <Info className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                        <span>
                          เคล็ดลับ: <span className="text-slate-300">{shot.tips}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-500">
              ไม่พบข้อมูลสูตรถ่ายทำ กรุณาลองใหม่อีกครั้ง
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/[0.08] bg-[#0E131F] flex items-center justify-between">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>เมื่อถ่ายครบ 5 ช็อตนี้แล้ว ให้อัปโหลดเข้าคลังคลิปดิบ แล้วกด 'สแกนสารบัญฉาก' ได้ทันที</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="py-1.5 px-4 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-all cursor-pointer"
          >
            เข้าใจแล้ว & ปิด
          </button>
        </div>
      </div>
    </div>
  );
}
