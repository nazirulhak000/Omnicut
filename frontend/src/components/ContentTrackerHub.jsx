import React, { useState, useEffect, useMemo, useCallback, useRef, memo } from 'react';
import {
  Layers, Clapperboard, Check, Trash2, ArrowRight, Play,
  Smartphone, RefreshCw, Search, QrCode, ArrowLeft, Copy,
  Kanban, Table, Sparkles, CheckCircle2, Clock,
  ExternalLink, ChevronRight, ChevronLeft, Filter, AlertCircle,
  Video, Eye, Flame, TrendingUp, Plus, X, FileText, Scissors,
  FolderDown, Info, Film, RotateCcw, ShieldAlert, AlertTriangle,
  Rocket, Calendar, Sun, Moon, Sunrise, Sunset, Shuffle, ChevronDown, ChevronUp,
  Archive, Image as ImageIcon
} from 'lucide-react';
import {
  getProducts, getExports, updateAngleStatus, updateAngleCover, deleteProduct, updateProduct, prepareTiktokAutopost, markPosted
} from '../api';
import CoverStudioModal from './CoverStudioModal';
import ScheduleAgenda from './ScheduleAgenda';
import { Modal, Toast, Button, Badge, Input, Textarea, SafeQRCode } from './ui';
import { useDebounce, useToast } from '../hooks';
import { guessBrandModel } from '../lib/overlayModel';
import { applyCoverResult, getCoverVariant, mergeCoverMetadata } from '../lib/coverVariant';

// 5 Granular Pipeline Phases (Original Vibrant & Readable Palette)
const PIPELINE_PHASES = [
  { id: 'scripted', label: 'สคริปต์พร้อม', short: 'สคริปต์', icon: FileText, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10 active:bg-cyan-500/20', dot: 'bg-cyan-400' },
  { id: 'in_production', label: 'กำลังตัดต่อ', short: 'ตัดต่อ', icon: Clapperboard, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10 active:bg-amber-500/20', dot: 'bg-amber-400' },
  { id: 'rendered', label: 'ตัดต่อเสร็จ', short: 'ตรวจ QC', icon: Video, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10 active:bg-blue-500/20', dot: 'bg-blue-400' },
  { id: 'mobile_ready', label: 'ส่งเข้ามือถือ', short: 'ส่งมือถือ', icon: Smartphone, color: 'text-purple-400 border-purple-500/30 bg-purple-500/10 active:bg-purple-500/20', dot: 'bg-purple-400' },
  { id: 'posted', label: 'โพสต์แล้ว', short: 'โพสต์แล้ว', icon: CheckCircle2, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10 active:bg-emerald-500/20', dot: 'bg-emerald-400' },
];

const PHASE_ORDER = ['scripted', 'in_production', 'rendered', 'mobile_ready', 'posted'];

// ═══════════════════════════════════════════════════════════════════════
// 🎬 HOVER VIDEO PREVIEW THUMBNAIL (Memory Safe & Fast)
// ═══════════════════════════════════════════════════════════════════════
const HoverVideoThumb = memo(function HoverVideoThumb({ videoUrl, onClick }) {
  const [isHovered, setIsHovered] = useState(false);
  const videoRef = useRef(null);

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch(() => {});
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (videoRef.current) {
      videoRef.current.pause();
      try {
        videoRef.current.currentTime = 1.0;
      } catch {}
    }
  };

  if (!videoUrl) return null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative w-full aspect-[9/16] rounded-lg overflow-hidden bg-black/70 border border-white/[0.1] hover:border-[#25F4EE] transition-all cursor-pointer group shadow-sm"
    >
      <video
        ref={videoRef}
        src={`/api/media/${videoUrl}#t=1.0`}
        muted
        playsInline
        loop
        className="w-full h-full object-cover"
        onLoadedMetadata={e => {
          try {
            e.target.currentTime = 1.0;
          } catch {}
        }}
      />
      {!isHovered && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/10 transition-colors">
          <div className="w-7 h-7 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center text-white border border-white/[0.2] shadow-md group-hover:scale-110 transition-transform">
            <Play className="w-3 h-3 fill-current text-[#25F4EE] ml-0.5" />
          </div>
        </div>
      )}
      <div className="absolute bottom-1 right-1 px-1.5 py-0.2 rounded bg-black/80 backdrop-blur-sm text-xs font-mono text-slate-300 border border-white/[0.08]">
        พรีวิว
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📌 MEMOIZED KANBAN CARD (Ultra High-Density & Deep-Dive Trigger)
// ═══════════════════════════════════════════════════════════════════════
const KanbanCard = memo(function KanbanCard({
  ang,
  phaseId,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onOpenTiktokModal,
  onOpenCoverStudio,
  onInspectAngle,
  onCopyCaption,
  onQcFail,
  onQcPass,
  onDismissConflict,
  onUnpickScript,
  copiedAngleId
}) {
  const isSelected = false;
  const currentPhase = PIPELINE_PHASES.find(p => p.id === phaseId) || PIPELINE_PHASES[0];

  const captionText = `${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`.trim();
  const curIdx = PHASE_ORDER.indexOf(phaseId);
  const prevPhase = curIdx > 0 ? PHASE_ORDER[curIdx - 1] : null;
  const nextPhase = curIdx < PHASE_ORDER.length - 1 ? PHASE_ORDER[curIdx + 1] : null;

  const chosenVideos = (ang.selected_videos && ang.selected_videos.length > 0)
    ? ang.selected_videos
    : (ang.selected_video ? [ang.selected_video] : []);
  const hasVideos = chosenVideos.length > 0;

  // ── Round TRK-3: Compact Horizontal Mini Video Card for 'rendered' phase (~95px height) ──
  if (phaseId === 'rendered') {
    return (
      <div className={`p-2 rounded-xl border transition-all relative group shadow-sm flex gap-2.5 items-stretch ${
        ang.qc_note
          ? 'bg-[#120A06] border-red-500/40 hover:border-red-400/60 ring-1 ring-red-500/20'
          : 'bg-[#09111C] border-[#25F4EE]/30 hover:border-[#25F4EE]/60 shadow-[#25F4EE]/5'
      }`}>
        {/* Left: Mini 9:16 Video or Cover Preview (~52px wide) */}
        <div
          onClick={() => ang.video_url && onPreviewVideo(ang.video_url, ang)}
          className="w-[52px] flex-shrink-0 relative rounded-lg overflow-hidden bg-black/80 border border-white/[0.1] hover:border-[#25F4EE] transition-all cursor-pointer group/thumb aspect-[9/16]"
          title={ang.cover_url ? "คลิกเพื่อพรีวิว (มีภาพปก 9:16 แล้ว)" : "คลิกเพื่อพรีวิวคลิปเต็ม"}
        >
          {ang.cover_url ? (
            <img
              src={ang.cover_url}
              alt="Cover 9:16"
              className="w-full h-full object-cover"
            />
          ) : ang.video_url ? (
            <video
              src={`/api/media/${ang.video_url}#t=1.0`}
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-slate-900 text-slate-600">
              <Video className="w-4 h-4" />
            </div>
          )}
          {ang.cover_url && (
            <span className="absolute top-0.5 right-0.5 px-1 py-0.2 rounded bg-amber-500/90 text-slate-950 font-black text-[8px] uppercase tracking-wider z-10 shadow">
              ปก
            </span>
          )}
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover/thumb:bg-black/10 transition-colors">
            <div className="w-5 h-5 rounded-full bg-black/70 backdrop-blur-sm flex items-center justify-center text-white border border-white/[0.2] group-hover/thumb:scale-110 transition-transform">
              <Play className="w-2.5 h-2.5 fill-current text-[#25F4EE] ml-0.5" />
            </div>
          </div>
        </div>

        {/* Right: Info & Actions */}
        <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
          {/* Row 1: Product Name & QC Badge / Conflict */}
          <div>
            <div className="flex items-center justify-between gap-1 text-xs">
              <span
                onClick={() => onInspectAngle(ang)}
                className="font-bold text-white truncate text-xs font-kanit hover:text-[#25F4EE] cursor-pointer flex items-center gap-1 min-w-0"
                title={`คลิกเพื่อดูรายละเอียดเชิงลึกของ: ${ang.project_name || ang.parentProduct?.name}`}
              >
                {ang.parentProduct?.product_code && (
                  <span className="px-1 py-0.1 rounded bg-fuchsia-500/15 border border-fuchsia-500/30 text-fuchsia-300 font-mono text-[9px] flex-shrink-0">
                    {ang.parentProduct.product_code}
                  </span>
                )}
                <span className="truncate">{ang.project_name || ang.parentProduct?.name}</span>
              </span>
              <div className="flex items-center gap-1 flex-shrink-0">
                {ang.qc_note ? (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onQcPass && onQcPass(ang); }}
                    className="px-1.5 py-0.2 rounded bg-red-500/20 border border-red-500/30 text-red-300 font-bold text-[10px] cursor-pointer"
                    title={ang.qc_note}
                  >
                    QC ไม่ผ่าน
                  </button>
                ) : (
                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-0.5">
                    <Check className="w-2.5 h-2.5 text-emerald-400" />
                    <span>QC ผ่าน</span>
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onInspectAngle(ang)}
                  className="p-0.5 rounded text-slate-500 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
                  title="ดูรายละเอียดจริงเชิงลึก"
                >
                  <Info className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* Row 2: 1-line Hook */}
            <div
              onClick={() => onInspectAngle(ang)}
              className="pl-1.5 border-l-2 border-[#25F4EE] text-[11px] font-semibold text-cyan-200 truncate cursor-pointer hover:underline my-1"
              title={ang.hook_title}
            >
              {ang.hook_title}
            </div>
          </div>

          {/* Row 3: Compact Actions Toolbar */}
          <div className="flex items-center gap-1 pt-1 border-t border-white/[0.06] overflow-x-auto no-scrollbar">
            <button
              type="button"
              onClick={() => onOpenTiktokModal && onOpenTiktokModal(ang)}
              className="py-1 px-2 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-[11px] font-bold flex items-center gap-1 shadow-sm cursor-pointer active:scale-95 whitespace-nowrap"
              title="ส่งคลิปไป TikTok Studio"
            >
              <Rocket className="w-3 h-3 flex-shrink-0" />
              <span>ส่ง TikTok</span>
            </button>

            <button
              type="button"
              onClick={() => onOpenCoverStudio && onOpenCoverStudio(ang)}
              className="py-1 px-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-[11px] font-bold flex items-center gap-1 cursor-pointer whitespace-nowrap active:scale-95"
              title="สตูดิโอสร้างปกคลิป 9:16 (Auto Crop + AI Hook + 3D Badge)"
            >
              <ImageIcon className="w-3 h-3 flex-shrink-0" />
              <span>{ang.cover_url ? 'แก้ปก' : 'สร้างปก'}</span>
            </button>

            <button
              type="button"
              onClick={() => onOpenQrModal(ang)}
              className="py-1 px-1.5 rounded-lg bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 text-[11px] font-bold flex items-center gap-1 cursor-pointer whitespace-nowrap active:scale-95"
              title="ส่งเข้ามือถือ"
            >
              <QrCode className="w-3 h-3 flex-shrink-0" />
              <span>มือถือ</span>
            </button>

            {ang.video_url && (
              <button
                type="button"
                onClick={() => onPreviewVideo(ang.video_url, ang)}
                className="py-1 px-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] text-slate-200 text-[11px] font-bold flex items-center gap-1 cursor-pointer whitespace-nowrap"
                title="พรีวิวตรวจคลิปเต็มจอ"
              >
                <Play className="w-2.5 h-2.5 fill-current text-[#25F4EE]" />
                <span>QC</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => onQcFail(ang)}
              className="py-1 px-1.5 rounded-lg bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-[11px] font-bold flex items-center gap-1 cursor-pointer whitespace-nowrap"
              title="QC ไม่ผ่าน ส่งตัดใหม่"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>ตัดใหม่</span>
            </button>

            <button
              type="button"
              onClick={() => onStatusChange(ang.parentProduct?.id, ang.angle_id, 'posted', null, null, true)}
              className="p-1 rounded-lg bg-white/[0.03] hover:bg-emerald-500/20 hover:border-emerald-500/40 border border-white/[0.06] text-slate-400 hover:text-emerald-300 text-[11px] cursor-pointer ml-auto flex-shrink-0"
              title="มาร์กว่าโพสต์แล้ว"
            >
              <Check className="w-3 h-3 text-emerald-400" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`p-2.5 rounded-xl border transition-all space-y-2 relative group shadow-sm ${
        ang.qc_note
          ? 'bg-[#120A06] border-red-500/40 hover:border-red-400/60 ring-1 ring-red-500/20'
          : phaseId === 'rendered'
          ? 'bg-[#09111C] border-[#25F4EE]/30 hover:border-[#25F4EE]/60 shadow-[#25F4EE]/5'
          : 'bg-[#0B0F19] border-white/[0.08] hover:border-[#25F4EE]/40'
      }`}
    >
      {/* Round BUG-3: Data Conflict Banner -- this angle's clip got auto-unlinked
          because another angle already legitimately claimed the same project/video */}
      {ang.data_conflict_note && (
        <div className="flex items-center justify-between gap-1.5 py-1 px-2 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold">
          <div className="flex items-start gap-1.5 min-w-0 flex-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-amber-400" />
            <span className="leading-snug" title={ang.data_conflict_note}>ปลดคลิปอัตโนมัติ: ชนกับ angle อื่น (ต้องผูกคลิปใหม่)</span>
          </div>
          {onDismissConflict && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDismissConflict(ang); }}
              className="px-2 py-0.5 rounded-md bg-white/[0.1] hover:bg-white/[0.18] text-amber-200 font-black text-[10px] cursor-pointer whitespace-nowrap active:scale-95 transition-all"
              title="เข้าใจแล้ว ซ่อนคำเตือนนี้"
            >
              เข้าใจแล้ว
            </button>
          )}
        </div>
      )}

      {/* QC Status Banner: Red if failed (with one-click fix button), Cyan if passed/rendered */}
      {ang.qc_note ? (
        <div className="flex items-center justify-between gap-1.5 py-1 px-2 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs font-bold">
          <div className="flex items-start gap-1.5 min-w-0 flex-1">
            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-red-400" />
            <span className="leading-snug truncate" title={ang.qc_note}>QC ไม่ผ่าน: {ang.qc_note}</span>
          </div>
          {onQcPass && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onQcPass(ang); }}
              className="px-2 py-0.5 rounded-md bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:brightness-110 text-slate-950 font-black text-[10px] cursor-pointer shadow-sm shadow-[#25F4EE]/20 whitespace-nowrap active:scale-95 transition-all"
              title="กดตรงนี้เพื่อแก้ให้เป็น QC ผ่านสีฟ้าทันที"
            >
              แก้เป็นผ่าน
            </button>
          )}
        </div>
      ) : (phaseId === 'rendered' && (
        <div className="flex items-center justify-between py-0.5 px-2 rounded-lg bg-[#25F4EE]/10 border border-[#25F4EE]/25 text-[#25F4EE] text-xs font-bold">
          <span className="flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>QC ผ่าน (พร้อมใช้งาน)</span>
          </span>
        </div>
      ))}
      
      {/* 1. Header: Project Name (falls back to product name pre-editor) + Detail Inspect Icon */}
      <div className="flex items-center justify-between gap-1.5 text-xs">
        <span
          onClick={() => onInspectAngle(ang)}
          className="font-bold text-white truncate flex-1 min-w-0 font-kanit text-sm hover:text-[#25F4EE] cursor-pointer flex items-center gap-1.5"
          title={`คลิกเพื่อดูรายละเอียดเชิงลึกของ: ${ang.project_name || ang.parentProduct?.name}`}
        >
          {ang.parentProduct?.product_code && (
            <span className="px-1.5 py-0.2 rounded bg-fuchsia-500/15 border border-fuchsia-500/30 text-fuchsia-300 font-mono text-[10px] flex-shrink-0">
              {ang.parentProduct.product_code}
            </span>
          )}
          <span className="truncate">{ang.project_name || ang.parentProduct?.name}</span>
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-0.5 rounded text-slate-500 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="ดูรายละเอียดจริงเชิงลึก (Deep Dive)"
          >
            <Info className="w-3 h-3" />
          </button>
          {phaseId === 'scripted' && onUnpickScript && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onUnpickScript(ang.angle_id || ang.id); }}
              className="p-0.5 rounded text-slate-500 hover:text-rose-400 hover:bg-white/[0.08] transition-colors cursor-pointer"
              title="ปลดออกจากคิววันนี้ (ส่งกลับเข้าคลังสคริปต์)"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 2. Hook Title: Crisp 2-line with thin accent bar (Clickable to inspect) */}
      <div
        onClick={() => onInspectAngle(ang)}
        className="pl-2 border-l-2 border-[#25F4EE] text-xs font-bold text-cyan-200 line-clamp-2 leading-snug cursor-pointer hover:underline"
        title="คลิกเพื่อดูบทพูดและรายละเอียดเต็ม"
      >
        {ang.hook_title}
      </div>

      {/* Video Hover Thumbnail (if rendered) */}
      {ang.video_url && (
        <div className="w-full max-w-[100px] mx-auto pt-0.5">
          <HoverVideoThumb
            videoUrl={ang.video_url}
            onClick={() => onPreviewVideo(ang.video_url, ang)}
          />
        </div>
      )}

      {/* 3. Merged Bottom Action & Stepper Row (จัดเลย์เอาต์โปร่งตา ไม่เบียดแม้จอเล็ก) */}
      <div className="pt-1.5 border-t border-white/[0.06]">
        {phaseId === 'rendered' ? (
          <div className="space-y-1.5 w-full">
            {/* Row 1 (Publishing Channels): [ส่ง TikTok] + [ส่งมือถือ] */}
            <div className="grid grid-cols-2 gap-1.5 w-full">
              <button
                type="button"
                onClick={() => onOpenTiktokModal && onOpenTiktokModal(ang)}
                className="py-2 px-2 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#FE2C55]/20 cursor-pointer transition-all active:scale-95 whitespace-nowrap"
                title="ส่งคลิป แคปชัน และไอดีปักตะกร้าไปโพสต์บน TikTok Studio"
              >
                <Rocket className="w-3.5 h-3.5 flex-shrink-0" />
                <span>ส่ง TikTok</span>
              </button>

              <button
                type="button"
                onClick={() => onOpenQrModal(ang)}
                className="py-2 px-2 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all whitespace-nowrap active:scale-95"
                title="เปิด QR Code สแกนโหลดคลิปลงมือถือ"
              >
                <QrCode className="w-3.5 h-3.5 flex-shrink-0" />
                <span>ส่งมือถือ</span>
              </button>
            </div>

            {/* Row 2 (QC & Editing Tools): [ตรวจ QC] + [ตัดใหม่] */}
            <div className="grid grid-cols-2 gap-1.5 w-full">
              {ang.video_url ? (
                <button
                  type="button"
                  onClick={() => onPreviewVideo(ang.video_url, ang)}
                  className="py-1.5 px-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors whitespace-nowrap"
                  title="พรีวิวตรวจคลิปเต็มจอ"
                >
                  <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                  <span>ตรวจ QC</span>
                </button>
              ) : <div />}

              <button
                type="button"
                onClick={() => onQcFail(ang)}
                className="py-1.5 px-2 rounded-lg bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors whitespace-nowrap"
                title="QC ไม่ผ่าน — ส่งตัดใหม่"
              >
                <RotateCcw className="w-3 h-3" />
                <span>ตัดใหม่</span>
              </button>
            </div>

            {/* Row 3: Quick Mark As Posted button */}
            <button
              type="button"
              onClick={() => onStatusChange(ang.parentProduct?.id, ang.angle_id, 'posted', null, null, true)}
              className="w-full py-1 px-2 rounded-lg bg-white/[0.03] hover:bg-emerald-500/15 hover:border-emerald-500/30 border border-white/[0.06] text-slate-400 hover:text-emerald-300 text-[11px] font-medium flex items-center justify-center gap-1 cursor-pointer transition-colors"
              title="คลิกเมื่อโพสต์คลิปนี้บน TikTok สำเร็จแล้ว เพื่อย้ายไปช่องโพสต์แล้ว"
            >
              <Check className="w-3 h-3 text-emerald-400" />
              <span>มาร์กว่าโพสต์แล้ว</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-1.5">
            {/* Left: Direct Primary Action */}
            <div className="flex items-center gap-1 min-w-0 flex-1">
              {phaseId === 'scripted' && (
                <button
                  onClick={() => hasVideos && onSendToStudio(ang.parentProduct, ang)}
                  disabled={!hasVideos}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 shadow-sm flex-shrink-0 transition-all ${
                    hasVideos
                      ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 active:scale-95 text-white cursor-pointer'
                      : 'bg-white/[0.05] border border-white/[0.08] text-slate-500 cursor-not-allowed opacity-50'
                  }`}
                  title={hasVideos ? 'ส่งไปตัดต่อ' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
                >
                  <Clapperboard className="w-3.5 h-3.5" />
                  <span>ส่งตัดต่อ</span>
                </button>
              )}

              {phaseId === 'in_production' && (
                <button
                  onClick={() => onSendToStudio(ang.parentProduct, ang)}
                  className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 active:scale-95 text-white text-xs font-bold flex items-center gap-1 cursor-pointer shadow-sm flex-shrink-0"
                  title={ang.project_name ? `เปิดไทม์ไลน์ของมุมนี้ (${ang.project_name})` : "เปิดทำต่อในหน้าตัดต่อ"}
                >
                  <Clapperboard className="w-3.5 h-3.5" />
                  <span>{ang.project_name ? 'เปิดไทม์ไลน์' : 'ไปหน้าตัดต่อ'}</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}

              {phaseId === 'mobile_ready' && (
                <>
                  <button
                    type="button"
                    onClick={() => onOpenTiktokModal && onOpenTiktokModal(ang)}
                    className="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center gap-1 shadow-sm cursor-pointer transition-all active:scale-95"
                    title="ส่งคลิปไป TikTok Studio"
                  >
                    <Rocket className="w-3 h-3" />
                    <span>ส่ง TikTok</span>
                  </button>
                  <button
                    onClick={() => onOpenQrModal(ang)}
                    className="px-2 py-1.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 hover:bg-purple-500/25 text-xs font-bold flex items-center gap-1 cursor-pointer"
                    title="เปิด QR Code"
                  >
                    <QrCode className="w-3 h-3" />
                    <span>QR</span>
                  </button>
                  <button
                    onClick={() => onStatusChange(ang.parentProduct.id, ang.angle_id, 'posted', null, null, true)}
                    className="px-2 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 text-xs font-bold flex items-center gap-1 cursor-pointer"
                    title="มาร์กว่าโพสต์แล้ว"
                  >
                    <Check className="w-3 h-3" />
                    <span>โพสต์แล้ว</span>
                  </button>
                </>
              )}

          {phaseId === 'posted' && (
            <div
              onClick={() => onInspectAngle(ang)}
              className="px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-sm text-emerald-300 font-bold flex items-center gap-1 cursor-pointer hover:bg-emerald-500/20"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>ออนไลน์แล้ว</span>
            </div>
          )}
        </div>

        {/* Right: Caption Quick Copy Only (เฉพาะเมื่อคลิปพร้อมส่งเข้ามือถือ หรือ โพสต์แล้ว) */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {captionText && (phaseId === 'mobile_ready' || phaseId === 'posted') && (
            <button
              onClick={() => onCopyCaption(captionText, ang.angle_id)}
              className="p-1.5 rounded-lg bg-black/40 hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-white cursor-pointer transition-colors"
              title="คัดลอกแคปชัน & แฮชแท็ก"
            >
              {copiedAngleId === ang.angle_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-[#25F4EE]" />}
            </button>
          )}
        </div>
      </div>
    )}
  </div>
</div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📱 MOBILE CARD VIEW COMPONENT (Clean & Thumb-Friendly for iPhone 15 PM)
// ═══════════════════════════════════════════════════════════════════════
const MobileTableRowCard = memo(function MobileTableRowCard({
  ang,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onOpenTiktokModal,
  onInspectAngle,
  onCopyCaption,
  onQcPass,
  copiedAngleId
}) {
  const currentPhase = PIPELINE_PHASES.find(p => p.id === ang.status) || PIPELINE_PHASES[0];
  const chosenVideos = (ang.selected_videos && ang.selected_videos.length > 0)
    ? ang.selected_videos
    : (ang.selected_video ? [ang.selected_video] : []);
  const hasVideos = chosenVideos.length > 0;
  const captionText = `${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`.trim();

  return (
    <div className="glass-card p-3 rounded-2xl border border-white/[0.08] space-y-2.5 bg-[#080B11]/90 shadow-lg">
      {/* 1. Header Row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <span
            onClick={() => onInspectAngle(ang)}
            className="font-bold text-white text-xs sm:text-sm font-kanit truncate hover:text-[#25F4EE] cursor-pointer"
          >
            {ang.project_name || ang.parentProduct?.name}
          </span>
        </div>
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-lg border flex-shrink-0 whitespace-nowrap ${currentPhase.color}`}>
          {currentPhase.label}
        </span>
      </div>

      {/* 2. Hook Title */}
      <div
        onClick={() => onInspectAngle(ang)}
        className="text-xs font-bold text-cyan-200 line-clamp-2 pl-2 border-l-2 border-[#25F4EE] cursor-pointer hover:underline"
      >
        {ang.hook_title}
      </div>

      {/* 3. Media Preview & Caption Box */}
      <div className="flex items-center gap-2">
        {ang.video_url && (
          <button
            onClick={() => onPreviewVideo(ang.video_url)}
            className="w-10 h-14 rounded-xl overflow-hidden bg-black relative border border-white/[0.1] hover:border-[#25F4EE] flex-shrink-0 group cursor-pointer"
          >
            <video src={`/api/media/${ang.video_url}`} className="w-full h-full object-cover" muted />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/10">
              <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
            </div>
          </button>
        )}

        <div className="flex-1 min-w-0">
          {(ang.status === 'mobile_ready' || ang.status === 'posted') ? (
            <button
              onClick={() => onCopyCaption(captionText, ang.angle_id)}
              className="w-full text-left p-1.5 rounded-xl bg-black/40 hover:bg-black/60 border border-white/[0.06] text-slate-300 text-xs flex items-center justify-between gap-1.5 cursor-pointer transition-colors"
              title="คลิกเพื่อคัดลอกแคปชัน & แฮชแท็ก"
            >
              <span className="line-clamp-2 text-xs font-mono">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
              <span className="text-[#25F4EE] flex-shrink-0">
                {copiedAngleId === ang.angle_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </span>
            </button>
          ) : (
            <p className="line-clamp-2 text-xs font-mono text-slate-400 p-1">
              {ang.tiktok_caption || 'ยังไม่มีแคปชัน'}
            </p>
          )}
        </div>
      </div>

      {/* 4. Action Row */}
      <div className="flex items-center gap-1.5 pt-1.5 border-t border-white/[0.06] flex-wrap">
        <button
          onClick={() => onInspectAngle(ang)}
          className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 cursor-pointer active:scale-95 flex-shrink-0"
          title="ดูรายละเอียดจริงเชิงลึก"
        >
          <Info className="w-4 h-4" />
        </button>

        <button
          onClick={() => hasVideos && onSendToStudio(ang.parentProduct, ang)}
          disabled={!hasVideos}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-1.5 transition-all whitespace-nowrap active:scale-95 flex-shrink-0 ${
            hasVideos
              ? 'bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/40 text-[#25F4EE] cursor-pointer'
              : 'bg-white/[0.03] border border-white/[0.06] text-slate-600 cursor-not-allowed opacity-40'
          }`}
          title={hasVideos ? 'ส่งเข้าหน้าตัดต่อ' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
        >
          <Clapperboard className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="whitespace-nowrap">ส่งตัดต่อ</span>
        </button>

        {(ang.status === 'rendered' || ang.qc_note) && onQcPass && (
          <button
            onClick={() => onQcPass(ang)}
            className="py-2 px-3 rounded-xl bg-[#25F4EE]/20 hover:bg-[#25F4EE]/30 border border-[#25F4EE]/40 text-[#25F4EE] text-xs font-bold inline-flex items-center justify-center gap-1 cursor-pointer transition-all active:scale-95 whitespace-nowrap flex-shrink-0"
            title="รับรอง QC ผ่าน"
          >
            <Check className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0" />
            <span className="whitespace-nowrap">QC ผ่าน</span>
          </button>
        )}

        <button
          onClick={() => onOpenQrModal(ang)}
          className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 cursor-pointer active:scale-95 flex-shrink-0"
          title="สแกน QR Code เข้ามือถือ"
        >
          <QrCode className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 📋 TABLE VIEW COMPONENT (High-Density True Table Style)
// ═══════════════════════════════════════════════════════════════════════
const TableRow = memo(function TableRow({
  ang,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
  onOpenTiktokModal,
  onInspectAngle,
  onCopyCaption,
  onQcPass,
  copiedAngleId
}) {
  const currentPhase = PIPELINE_PHASES.find(p => p.id === ang.status) || PIPELINE_PHASES[0];

  const chosenVideos = (ang.selected_videos && ang.selected_videos.length > 0)
    ? ang.selected_videos
    : (ang.selected_video ? [ang.selected_video] : []);
  const hasVideos = chosenVideos.length > 0;

  return (
    <tr className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
      {/* 1. Media Preview */}
      <td className="py-2.5 px-3 w-16 text-center">
        {ang.video_url ? (
          <button
            onClick={() => onPreviewVideo(ang.video_url)}
            className="w-10 h-13 rounded-lg overflow-hidden bg-black relative border border-white/[0.1] hover:border-[#25F4EE] inline-flex items-center justify-center group cursor-pointer shadow-sm"
          >
            <video src={`/api/media/${ang.video_url}`} className="w-full h-full object-cover" muted />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/10">
              <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
            </div>
          </button>
        ) : (
          <div className="w-10 h-13 rounded-lg bg-black/40 border border-white/[0.06] inline-flex items-center justify-center text-xs text-slate-600 font-mono">
            -
          </div>
        )}
      </td>

      {/* 2. Product & Hook Title */}
      <td className="py-2.5 px-3 min-w-[200px] max-w-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              onClick={() => onInspectAngle(ang)}
              className="font-bold text-white text-xs font-kanit hover:text-[#25F4EE] cursor-pointer"
            >
              {ang.parentProduct?.name}
            </span>
            {ang.badge && (
              <span className="flex-shrink-0 whitespace-nowrap">
                <Badge variant="cyan" size="sm">{ang.badge}</Badge>
              </span>
            )}
          </div>
          <p
            onClick={() => onInspectAngle(ang)}
            className="text-xs text-cyan-200 font-bold line-clamp-1 cursor-pointer hover:underline"
          >
            {ang.hook_title}
          </p>
        </div>
      </td>

      {/* 3. Status Phase (Locked Real Status Badge) */}
      <td className="py-2.5 px-3 w-40 whitespace-nowrap">
        <span className={`inline-flex items-center gap-1.5 py-1 px-2.5 rounded-lg text-xs font-bold border select-none whitespace-nowrap ${currentPhase.color}`}>
          <currentPhase.icon className="w-3 h-3 flex-shrink-0" />
          <span className="whitespace-nowrap">{currentPhase.label}</span>
        </span>
      </td>

      {/* 4. Caption Preview & Copy (Natural Flex Column) */}
      <td className="py-2.5 px-3 min-w-[220px]">
        {(ang.status === 'mobile_ready' || ang.status === 'posted') ? (
          <button
            onClick={() => onCopyCaption(`${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`, ang.angle_id)}
            className="text-left py-1.5 px-2.5 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.06] text-slate-300 text-xs flex items-center justify-between gap-2 w-full max-w-md cursor-pointer transition-colors group"
            title="คลิกเพื่อคัดลอกแคปชัน & แฮชแท็ก"
          >
            <span className="line-clamp-2 text-xs font-mono group-hover:text-white leading-relaxed">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
            <span className="text-[#25F4EE] flex-shrink-0">
              {copiedAngleId === ang.angle_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </span>
          </button>
        ) : (
          <p className="line-clamp-2 text-xs font-mono text-slate-400 max-w-md leading-relaxed" title={ang.tiktok_caption || ''}>
            {ang.tiktok_caption || '-'}
          </p>
        )}
      </td>

      {/* 5. Direct Action Buttons - Whitespace nowrap, Never Break Text */}
      <td className="py-2.5 px-3 text-right w-52 min-w-[190px] whitespace-nowrap">
        <div className="flex items-center justify-end gap-1.5 flex-nowrap">
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-slate-400 hover:text-white cursor-pointer flex-shrink-0 transition-colors"
            title="ดูรายละเอียดจริงเชิงลึก"
          >
            <Info className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => hasVideos && onSendToStudio(ang.parentProduct, ang)}
            disabled={!hasVideos}
            className={`py-1.5 px-3 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-all whitespace-nowrap flex-shrink-0 ${
              hasVideos
                ? 'bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] cursor-pointer active:scale-95'
                : 'bg-white/[0.03] border border-white/[0.06] text-slate-600 cursor-not-allowed opacity-40'
            }`}
            title={hasVideos ? 'ส่งเข้าหน้าตัดต่อ' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
          >
            <Clapperboard className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="whitespace-nowrap">ส่งตัดต่อ</span>
          </button>

          {ang.video_url && onOpenTiktokModal && (
            <button
              onClick={() => onOpenTiktokModal(ang)}
              className="py-1.5 px-2.5 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold inline-flex items-center gap-1 cursor-pointer transition-all active:scale-95 whitespace-nowrap flex-shrink-0 shadow-sm"
              title="ส่งคลิปไป TikTok Studio พร้อมปักตะกร้า"
            >
              <Rocket className="w-3.5 h-3.5 flex-shrink-0" />
              <span>ส่ง TikTok</span>
            </button>
          )}

          {(ang.status === 'rendered' || ang.qc_note) && onQcPass && (
            <button
              onClick={() => onQcPass(ang)}
              className="py-1.5 px-2.5 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/35 text-[#25F4EE] text-xs font-bold inline-flex items-center gap-1 cursor-pointer transition-all active:scale-95 whitespace-nowrap flex-shrink-0"
              title="รับรอง QC ผ่าน (ล้างป้ายแดงออก)"
            >
              <Check className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0" />
              <span className="whitespace-nowrap">QC ผ่าน</span>
            </button>
          )}

          <button
            onClick={() => onOpenQrModal(ang)}
            className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white cursor-pointer flex-shrink-0 transition-colors"
            title="สแกน QR Code เข้ามือถือ"
          >
            <QrCode className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 🌟 MAIN CONTENT TRACKER HUB COMPONENT (True Deep-Dive Tracking)
// ═══════════════════════════════════════════════════════════════════════
export default function ContentTrackerHub({ status, onApplyToStudio, onRefresh, onGoToGallery, onGoToEditor, onGoToFlow }) {
  const mobileBaseUrl = status?.mobile_url || (typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  // Round P1.5: request-sequence guard so an older, slower fetchProductsData()
  // response can't resolve after a newer one and overwrite fresher state
  // (angle statuses, video urls, a just-saved cover_url reverting on screen).
  // Same pattern as hooks/useProjectLoader.js's requestSequence ref.
  const productsRequestSequence = useRef(0);
  useEffect(() => () => {
    productsRequestSequence.current += 1;
  }, []);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [activePhase, setActivePhase] = useState('all'); // 'all' | 'scripted' | 'in_production' | ...
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('capcut_tracker_view_mode') || 'kanban';
    } catch {
      return 'kanban';
    }
  });
  const [copiedAngleId, setCopiedAngleId] = useState(null);
  const [previewVideoUrl, setPreviewVideoUrl] = useState(null);
  const [previewVideoAngle, setPreviewVideoAngle] = useState(null);
  const [qrModalItem, setQrModalItem] = useState(null);
  const [tiktokModalItem, setTiktokModalItem] = useState(null);
  const [coverPreviewItem, setCoverPreviewItem] = useState(null);
  const [tiktokCaption, setTiktokCaption] = useState('');
  const [tiktokHashtags, setTiktokHashtags] = useState('');
  const [tiktokProductId, setTiktokProductId] = useState('');
  const [tiktokScheduleTime, setTiktokScheduleTime] = useState('');
  const [isSubmittingTiktok, setIsSubmittingTiktok] = useState(false);
  const [inspectAngle, setInspectAngle] = useState(null); // Deep-Dive Inspection state
  const colRefs = useRef({});
  const { toastMessage, showToast, hideToast } = useToast();

  const [groupByProduct, setGroupByProduct] = useState(true);
  const [collapsedGroups, setCollapsedGroups] = useState({});
  const [hideOldPosted, setHideOldPosted] = useState(true);

  // ── Round TRK-3: Decluttering Board States (Archive & Script Library) ──
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [archiveSearchQuery, setArchiveSearchQuery] = useState('');
  const [showScriptLibraryModal, setShowScriptLibraryModal] = useState(false);
  const [scriptLibrarySearch, setScriptLibrarySearch] = useState('');

  // Picked scripts for today's production (persists in localStorage)
  const [pickedScriptIds, setPickedScriptIds] = useState(() => {
    try {
      const saved = localStorage.getItem('omnicut_today_picked_scripts');
      if (saved) return JSON.parse(saved);
    } catch {}
    return null;
  });

  useEffect(() => {
    if (pickedScriptIds !== null) {
      try {
        localStorage.setItem('omnicut_today_picked_scripts', JSON.stringify(pickedScriptIds));
      } catch {}
    }
  }, [pickedScriptIds]);

  // Today Date string for filtering posted clips (Local time 'YYYY-MM-DD')
  // Round P1.5 (7d): recomputed on visibility/focus + a low-frequency interval
  // (not a one-shot useMemo) so a tab left open across midnight -- likely for
  // an overnight content-scheduling tool -- doesn't keep filtering "posted
  // today" against yesterday's date until the user manually reloads.
  const computeTodayDateStr = () => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  };
  const [todayDateStr, setTodayDateStr] = useState(computeTodayDateStr);

  useEffect(() => {
    const refreshTodayDateStr = () => {
      setTodayDateStr((prev) => {
        const next = computeTodayDateStr();
        return next === prev ? prev : next;
      });
    };
    document.addEventListener('visibilitychange', refreshTodayDateStr);
    window.addEventListener('focus', refreshTodayDateStr);
    // Fallback for tabs that stay foregrounded/visible across midnight without
    // ever blurring or hiding.
    const intervalId = setInterval(refreshTodayDateStr, 60 * 1000);
    return () => {
      document.removeEventListener('visibilitychange', refreshTodayDateStr);
      window.removeEventListener('focus', refreshTodayDateStr);
      clearInterval(intervalId);
    };
  }, []);

  const isAnglePostedToday = useCallback((ang) => {
    const dateVal = ang.posted_at || ang.updated_at;
    if (!dateVal) return false;
    return String(dateVal).startsWith(todayDateStr);
  }, [todayDateStr]);

  const handleTogglePickScript = useCallback((aid) => {
    setPickedScriptIds((prev) => {
      const current = prev || [];
      if (current.includes(aid)) {
        return current.filter((id) => id !== aid);
      }
      return [...current, aid];
    });
  }, []);

  const handlePickTopScripts = useCallback((angles, limit = 4) => {
    const ids = angles.slice(0, limit).map((a) => a.angle_id || a.id);
    setPickedScriptIds(ids);
  }, []);

  const handleClearPickedScripts = useCallback(() => {
    setPickedScriptIds([]);
  }, []);

  useEffect(() => {
    if (pickedScriptIds === null && products.length > 0) {
      const allScripted = [];
      products.forEach((p) => {
        (p.angles || []).forEach((a) => {
          if ((a.status || 'scripted') === 'scripted') {
            allScripted.push(a.angle_id || a.id);
          }
        });
      });
      if (allScripted.length > 0) {
        setPickedScriptIds(allScripted.slice(0, 4));
      } else {
        setPickedScriptIds([]);
      }
    }
  }, [products, pickedScriptIds]);

  const toggleGroupCollapse = (phaseId, groupKey) => {
    const key = `${phaseId}_${groupKey}`;
    setCollapsedGroups((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const [coverStudioItem, setCoverStudioItem] = useState(null);

  const handleOpenTiktokModal = useCallback((ang, scheduleTime = '') => {
    if (!ang) return;
    const targetPid = ang?.parentProduct?.tiktok_product_id || ang?.parentProduct?.name || '';
    const cover = getCoverVariant(ang);
    setTiktokModalItem({
      ...ang,
      cover_url: cover.url || ang.cover_url || '',
      cover_path: cover.path || ang.cover_path || '',
    });
    setTiktokCaption(ang.tiktok_caption || ang.hook_title || '');
    setTiktokHashtags(ang.tiktok_hashtags || '#รีวิว #ของดีบอกต่อ');
    setTiktokProductId(targetPid);
    setTiktokScheduleTime(scheduleTime || '');
  }, []);

  const handleConfirmTiktokAutopost = useCallback(async () => {
    if (!tiktokModalItem) return;
    if (!tiktokModalItem.video_url) {
      showToast('ยังไม่มีไฟล์วิดีโอที่ตัดเสร็จสำหรับคลิปนี้', 'error');
      return;
    }
    setIsSubmittingTiktok(true);
    try {
      await prepareTiktokAutopost(
        tiktokModalItem.video_url,
        tiktokModalItem.cover_path || tiktokModalItem.cover_url || null,
        tiktokCaption,
        tiktokHashtags,
        tiktokModalItem.parentProduct?.id,
        tiktokModalItem.angle_id,
        tiktokProductId.trim() || undefined,
        tiktokScheduleTime.trim() || undefined,
        tiktokModalItem.export_id || null,
      );
      showToast('ส่งข้อมูลให้ Extension แล้ว! กำลังเปิด TikTok Studio...');
      window.open('https://www.tiktok.com/tiktokstudio/upload', '_blank');
    } catch (err) {
      showToast('ส่งข้อมูลไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsSubmittingTiktok(false);
    }
  }, [tiktokModalItem, tiktokCaption, tiktokHashtags, tiktokProductId, tiktokScheduleTime, showToast]);

  const handlePreviewVideo = useCallback((url, ang = null) => {
    setPreviewVideoUrl(url);
    setPreviewVideoAngle(ang);
  }, []);

  const handleSwitchViewMode = (mode) => {
    setViewMode(mode);
    try {
      localStorage.setItem('capcut_tracker_view_mode', mode);
    } catch {
      // ignore
    }
  };

  const scrollToPhaseColumn = (phaseId) => {
    setActivePhase(phaseId);
    if (viewMode === 'kanban' && phaseId !== 'all' && colRefs.current[phaseId]) {
      colRefs.current[phaseId].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  };

  const fetchProductsData = useCallback(async () => {
    const sequence = ++productsRequestSequence.current;
    setLoading(true);
    try {
      const [res, exportsRes] = await Promise.all([
        getProducts(),
        getExports().catch(() => ({ exports: [] })),
      ]);
      if (sequence !== productsRequestSequence.current) return;
      if (res.products) {
        setProducts(mergeCoverMetadata(res.products, exportsRes));
      }
    } catch (err) {
      console.error(err);
    } finally {
      if (sequence === productsRequestSequence.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProductsData();
  }, [fetchProductsData]);

  const handleOpenCoverStudio = useCallback((ang) => {
    if (!ang) return;
    const cover = getCoverVariant(ang);
    const item = {
      path: ang.video_url || '',
      rel_path: ang.video_url || '',
      name: ang.parentProduct?.name || '',
      product_name: ang.parentProduct?.name || '',
      project_name: ang.project_name || '',
      hook_title: ang.hook_title || '',
      angle_name: ang.angle_name || '',
      thumbnail_url: ang.cover_url || ang.thumbnail_url || (ang.video_url ? `/api/media/${ang.video_url}` : ''),
      cover_url: cover.url || ang.cover_url || '',
      cover_path: cover.path || ang.cover_path || '',
      cover_3x4_url: ang.cover_3x4_url || ang.media_url_3x4 || '',
      cover_3x4_path: ang.cover_3x4_path || '',
      parentProduct: ang.parentProduct,
      angle_id: ang.angle_id,
      export_id: ang.export_id || null,
    };
    setCoverStudioItem(item);
  }, []);

  const handleCoverSaved = useCallback(async (res) => {
    showToast('สร้างภาพปก 3:4 สำเร็จแล้ว!');
    if (tiktokModalItem) {
      setTiktokModalItem((prev) => (prev ? applyCoverResult(prev, res) : null));
    }
    const productId = coverStudioItem?.parentProduct?.id;
    const angleId = coverStudioItem?.angle_id;
    if (productId && angleId && (res?.cover_path || res?.cover_3x4_path || res?.cover_9x16_path)) {
      try {
        await updateAngleCover(productId, angleId, {
          cover_path: res.cover_path || null,
          cover_3x4_path: res.cover_3x4_path || null,
          cover_9x16_path: res.cover_9x16_path || null,
        });
      } catch (err) {
        showToast('บันทึกภาพปกเข้ากับมุมสินค้าไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
        return;
      }
    }
    await fetchProductsData();
  }, [coverStudioItem, tiktokModalItem, showToast, fetchProductsData]);

  const handleAngleStatusChange = useCallback(async (productId, angleId, nextStatus, videoUrl = null, qcNote = null, clearQcNote = false, clearConflictNote = false, exportId = null) => {
    try {
      if (nextStatus === 'posted') {
        const sourceAngle = products
          .find((product) => product.id === productId)
          ?.angles?.find((angle) => angle.angle_id === angleId);
        const exactVideo = videoUrl || sourceAngle?.video_url;
        const exactExportId = exportId || sourceAngle?.export_id;
        if (!exactVideo || !exactExportId) {
          throw new Error('ไม่พบ export_id ของคลิปนี้ จึงหยุดการมาร์กโพสต์เพื่อป้องกันการเลือกคลิปผิดตัว');
        }
        await markPosted(exactVideo, productId, angleId, exactExportId);
        productsRequestSequence.current += 1;
        await fetchProductsData();
        showToast('มาร์กว่าโพสต์แล้วสำเร็จ');
        return;
      }
      await updateAngleStatus(productId, angleId, nextStatus, videoUrl, null, qcNote, clearQcNote, clearConflictNote, exportId);
      // Invalidate any in-flight fetchProductsData (even one started before this
      // patch) so its response can't resolve afterwards and overwrite this patch.
      productsRequestSequence.current += 1;
      setProducts(prev => prev.map(p => {
        if (p.id === productId) {
          const updatedAngles = p.angles?.map(a => {
            if (a.angle_id !== angleId) return a;
            return {
              ...a,
              status: nextStatus,
              ...(videoUrl ? { video_url: videoUrl } : {}),
              ...(qcNote !== null ? { qc_note: qcNote } : {}),
              ...(clearQcNote ? { qc_note: null } : {}),
              ...(clearConflictNote ? { data_conflict_note: null } : {}),
              ...(exportId ? { export_id: exportId } : {}),
            };
          }) || [];
          return { ...p, angles: updatedAngles };
        }
        return p;
      }));
      // Also update inspectAngle state if it's currently open
      if (inspectAngle && inspectAngle.angle_id === angleId) {
        setInspectAngle(prev => prev ? {
          ...prev,
          status: nextStatus,
          ...(videoUrl ? { video_url: videoUrl } : {}),
          ...(qcNote !== null ? { qc_note: qcNote } : {}),
          ...(clearQcNote ? { qc_note: null } : {}),
          ...(clearConflictNote ? { data_conflict_note: null } : {}),
          ...(exportId ? { export_id: exportId } : {}),
        } : null);
      }
      showToast('อัปเดตสถานะสำเร็จ');
    } catch (err) {
      showToast('ไม่สามารถอัปเดตสถานะได้: ' + err.message, 'error');
    }
  }, [products, inspectAngle, fetchProductsData, showToast]);

  // Round BUG-3: dismisses the "auto-unlinked from another angle's clip"
  // banner reconcile_existing_projects() leaves on the loser of a collision.
  const handleDismissConflict = useCallback(async (ang) => {
    if (!ang || !ang.parentProduct) return;
    await handleAngleStatusChange(
      ang.parentProduct.id,
      ang.angle_id,
      ang.status || 'scripted',
      null,
      null,
      false,
      true, // clearConflictNote
    );
  }, [handleAngleStatusChange]);

  // Round BUG-3.3: TikTok Shop product ID lives on the PRODUCT (one TikTok
  // Shop listing serves every angle of that product), not the angle --
  // there was previously no UI anywhere to set it (only ESSAGER has one,
  // set by hand-editing products.json).
  const handleSaveTiktokProductId = useCallback(async (productId, tiktokProductId) => {
    try {
      const trimmed = tiktokProductId.trim();
      await updateProduct(productId, { tiktok_product_id: trimmed || null });
      // Invalidate any in-flight fetchProductsData (even one started before this
      // patch) so its response can't resolve afterwards and overwrite this patch.
      productsRequestSequence.current += 1;
      setProducts(prev => prev.map(p => p.id === productId ? { ...p, tiktok_product_id: trimmed || null } : p));
      if (inspectAngle?.parentProduct?.id === productId) {
        setInspectAngle(prev => prev ? { ...prev, parentProduct: { ...prev.parentProduct, tiktok_product_id: trimmed || null } } : null);
      }
      showToast('บันทึก TikTok Product ID แล้ว');
    } catch (err) {
      showToast('บันทึกไม่สำเร็จ: ' + err.message, 'error');
    }
  }, [inspectAngle, showToast]);

  // Short scannable code (e.g. "ESG01") so a person can match a CapCut
  // project-picker entry back to its tracker row without reading the full
  // Thai product name -- auto-generated on the backend, editable here once
  // if the naive auto-abbreviation needs a human correction.
  const handleSaveProductCode = useCallback(async (productId, code) => {
    try {
      const trimmed = code.trim().toUpperCase();
      await updateProduct(productId, { product_code: trimmed || null });
      // Invalidate any in-flight fetchProductsData (even one started before this
      // patch) so its response can't resolve afterwards and overwrite this patch.
      productsRequestSequence.current += 1;
      setProducts(prev => prev.map(p => p.id === productId ? { ...p, product_code: trimmed || null } : p));
      if (inspectAngle?.parentProduct?.id === productId) {
        setInspectAngle(prev => prev ? { ...prev, parentProduct: { ...prev.parentProduct, product_code: trimmed || null } } : null);
      }
      showToast('บันทึกรหัสสินค้าแล้ว');
    } catch (err) {
      showToast('บันทึกไม่สำเร็จ: ' + err.message, 'error');
    }
  }, [inspectAngle, showToast]);

  // Same prepare -> extension flow as ExportGallery's Post Studio panel --
  // hands the clip off to tiktok_autopost_extension/, which the user
  // triggers from its own popup on a real, already-logged-in TikTok Studio
  // upload tab (see scripts/api_tiktok_autopost.py's docstring for why the
  // app can't message the extension directly).
  const handlePrepareAutopost = useCallback(async (ang) => {
    const targetPid = ang?.parentProduct?.tiktok_product_id || ang?.parentProduct?.name || '';
    if (!targetPid) {
      showToast('สินค้านี้ยังไม่มี TikTok Product ID หรือชื่อสินค้า -- ใส่ก่อนถึงจะปักตะกร้าได้', 'error');
      return;
    }
    if (!ang.video_url) {
      showToast('มุมนี้ยังไม่มีคลิปที่เรนเดอร์แล้ว', 'error');
      return;
    }
    try {
      await prepareTiktokAutopost(
        ang.video_url, null,
        ang.tiktok_caption || '', ang.tiktok_hashtags || '',
        ang.parentProduct.id, ang.angle_id,
        targetPid,
        null,
        ang.export_id || null,
      );
      showToast('เตรียมคลิปให้ extension แล้ว -- ไปคลิกไอคอน extension บนแท็บ TikTok Studio ที่เปิดไว้');
    } catch (err) {
      showToast('เตรียมคลิปไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    }
  }, [showToast]);

  // ── QC Fail Modal state ──────────────────────────────────────────────────
  const [qcFailTarget, setQcFailTarget] = useState(null); // angle object
  const [qcFailNote, setQcFailNote]     = useState('');

  const handleQcFail = useCallback((ang) => {
    setQcFailTarget(ang);
    setQcFailNote('');
  }, []);

  const handleQcFailConfirm = useCallback(async () => {
    if (!qcFailTarget) return;
    const note = qcFailNote.trim() || 'QC ไม่ผ่าน';
    await handleAngleStatusChange(
      qcFailTarget.parentProduct.id,
      qcFailTarget.angle_id,
      'in_production',
      null,     // videoUrl — keep existing
      note,     // qc_note
      false,
    );
    showToast('ส่งตัดใหม่แล้ว — สถานะกลับเป็น "กำลังตัดต่อ"');
    setQcFailTarget(null);
    setQcFailNote('');
    setInspectAngle(null); // close inspect modal if open
  }, [qcFailTarget, qcFailNote, handleAngleStatusChange, showToast]);

  const handleQcPass = useCallback(async (ang, moveToNext = false) => {
    if (!ang || !ang.parentProduct) return;
    const nextStatus = moveToNext ? 'mobile_ready' : (ang.status || 'rendered');
    await handleAngleStatusChange(
      ang.parentProduct.id,
      ang.angle_id,
      nextStatus,
      ang.video_url || null,
      null,     // clear qc_note
      true,     // clearQcNote
      false,
      ang.export_id || null,
    );
    showToast('🎉 QC ผ่านเรียบร้อยแล้ว! ล้างข้อความไม่ผ่านออก และการ์ดเป็นสีฟ้าพร้อมใช้งาน');
    setPreviewVideoUrl(null);
    setPreviewVideoAngle(null);
  }, [handleAngleStatusChange, showToast]);

  const handleSendToStudio = useCallback((product, angle, angleIdx = -1) => {
    if (!onApplyToStudio) return;

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');

    // Do NOT set in_production prematurely when merely opening studio!
    // Status only becomes 'in_production' when a timeline project actually exists in 03_Projects.

    let resolvedIdx = angleIdx;
    if (resolvedIdx < 0 && product?.angles) {
      if (angle?.angle_id) {
        resolvedIdx = product.angles.findIndex(a => a.angle_id === angle.angle_id);
      } else {
        // No angle_id on this angle at all -- a data problem, not something
        // to paper over with a hook_title string match (two angles can share
        // a title, which risks loading the WRONG angle's script/video into
        // the editor). Surface it and fall back to index 0 rather than guess.
        console.warn('[ContentTrackerHub] handleSendToStudio: angle has no angle_id -- cannot resolve its index reliably', angle);
        resolvedIdx = -1;
      }
      if (resolvedIdx < 0) resolvedIdx = 0;
    } else if (resolvedIdx < 0) {
      resolvedIdx = 0;
    }

    const chosenVideos = angle.selected_videos && angle.selected_videos.length > 0
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : []);

    if (chosenVideos.length === 0) {
      showToast('ยังไม่มีคลิปดิบในสคริปต์นี้ กรุณาแนบคลิปก่อนส่งตัดต่อ', 'error');
      return;
    }

    onApplyToStudio({
      productId: product.id,
      angleId: angle.angle_id,
      productName: angle.product_name || product.name || 'สินค้า',
      // The banner's three tiers come from the angle (the script AI splits
      // the product name) and fall back to a whitespace split. They used to
      // be left blank here on purpose, which meant the first render burned
      // the whole product name into the brand tier and nothing into the rest.
      hookBrand: angle.hook_brand || guessBrandModel(angle.product_name || '').brand,
      hookModel: angle.hook_model || guessBrandModel(angle.product_name || '').model,
      hookLabel: angle.hook_label || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || product.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || product.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: chosenVideos[0] || '',
      selectedVideos: chosenVideos,
      openProjectName: angle.project_name || '',
      openVideoUrl: angle.video_url || '',
      isRendered: angle.status === 'rendered' || !!angle.video_url,
      fullProduct: {
        id: product.id,
        title: product.name,
        description: product.description,
        price_note: product.price_note,
        product_code: product.product_code || '',
        images: product.images || [],
        angles: product.angles || [angle]
      },
      angleIndex: resolvedIdx
    });
  }, [onApplyToStudio, handleAngleStatusChange]);

  const handleCopyCaption = useCallback((text, angleId) => {
    navigator.clipboard.writeText(text);
    setCopiedAngleId(angleId);
    showToast('คัดลอกแคปชัน & แฮชแท็กแล้ว!');
    setTimeout(() => setCopiedAngleId(null), 2000);
  }, [showToast]);

  // Flatten all angles with useMemo
  const allAnglesList = useMemo(() => {
    const list = [];
    products.forEach(p => {
      (p.angles || []).forEach(a => {
        list.push({
          ...a,
          parentProduct: p,
          status: a.status || 'scripted'
        });
      });
    });
    return list;
  }, [products]);

  // Phase Stats with useMemo
  const phaseCounts = useMemo(() => ({
    scripted: allAnglesList.filter(a => a.status === 'scripted').length,
    in_production: allAnglesList.filter(a => a.status === 'in_production').length,
    rendered: allAnglesList.filter(a => a.status === 'rendered').length,
    mobile_ready: allAnglesList.filter(a => a.status === 'mobile_ready').length,
    posted: allAnglesList.filter(a => a.status === 'posted').length,
  }), [allAnglesList]);

  // Filtered angles with useMemo and Debounced Search
  const filteredAngles = useMemo(() => {
    const q = (debouncedSearch || '').toLowerCase().trim();
    return allAnglesList.filter(a => {
      const matchesSearch = !q ||
        a.parentProduct?.name?.toLowerCase().includes(q) ||
        a.hook_title?.toLowerCase().includes(q) ||
        a.angle_name?.toLowerCase().includes(q);

      const matchesProduct = selectedProductFilter === 'all' || a.parentProduct?.id === selectedProductFilter;
      const matchesPhase = activePhase === 'all' || a.status === activePhase;

      return matchesSearch && matchesProduct && matchesPhase;
    });
  }, [allAnglesList, debouncedSearch, selectedProductFilter, activePhase]);

  const mobileUrl = typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '';

  // Drag & Drop Handler (Desktop)
  const handleDropOnColumn = (targetPhaseId, e) => {
    e.preventDefault();
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      if (data && data.productId && data.angleId && data.fromPhase !== targetPhaseId) {
        if (data.fromPhase === 'posted') {
          showToast('ไม่อนุญาตให้ย้ายคลิปที่โพสต์แล้วออกจากคอลัมน์นี้ (ต้องเก็บไว้เป็นหลักฐาน)', 'error');
          return;
        }
        if (targetPhaseId === 'posted') {
          showToast('การบันทึกสถานะโพสต์ต้องผ่านการส่ง TikTok หรือปุ่มมาร์กว่าโพสต์แล้วเท่านั้น', 'error');
          return;
        }
        handleAngleStatusChange(data.productId, data.angleId, targetPhaseId);
      }
    } catch (err) {
      console.error('Drop parse error', err);
    }
  };

  return (
    <div className="space-y-3 animate-fadeIn pb-16">
      {/* Central Toast */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ══════════════════════════════════════════════════════════
          🎯 DEEP-DIVE JOB INSPECTOR MODAL (ติดตามงานจริงเชิงลึก)
         ══════════════════════════════════════════════════════════ */}
      <Modal
        isOpen={!!inspectAngle}
        onClose={() => setInspectAngle(null)}
        title="รายละเอียดงานจริงเชิงลึก (Deep-Dive Pipeline Inspector)"
        subtitle={inspectAngle?.parentProduct?.name}
        maxWidth="max-w-2xl"
      >
        {inspectAngle && (() => {
          const currentPhaseInfo = PIPELINE_PHASES.find(p => p.id === inspectAngle.status) || PIPELINE_PHASES[0];
          const scriptLines = Array.isArray(inspectAngle.script_lines)
            ? inspectAngle.script_lines
            : (inspectAngle.script_text ? inspectAngle.script_text.split('\n') : []);
          const captionText = `${inspectAngle.tiktok_caption || ''}\n\n${inspectAngle.tiktok_hashtags || ''}`.trim();

          const effectiveVideoUrl = inspectAngle.video_url ||
            inspectAngle.parentProduct?.images?.find(img => {
              const p = img.local_path || img.rel_path || '';
              return p.endsWith('.mp4') || p.endsWith('.mov') || p.endsWith('.webm');
            })?.rel_path ||
            inspectAngle.parentProduct?.images?.find(img => {
              const p = img.local_path || img.rel_path || '';
              return p.endsWith('.mp4') || p.endsWith('.mov') || p.endsWith('.webm');
            })?.local_path || null;

          const isRenderedOrBeyond = inspectAngle.status === 'rendered' || inspectAngle.status === 'mobile_ready' || inspectAngle.status === 'posted';

          const attachedVideos = (inspectAngle.selected_videos && inspectAngle.selected_videos.length > 0)
            ? inspectAngle.selected_videos
            : (inspectAngle.selected_video ? [inspectAngle.selected_video] : []);
          const hasAttachedVideos = attachedVideos.length > 0;

          return (
            <div className="space-y-3 max-h-[78vh] overflow-y-auto pr-1">
              {/* 1. Compact Single-Row Status Ribbon (ยุบบรรทัดเดียว ไม่ขึ้น 2 บรรทัด) */}
              <div className="p-2 sm:p-2.5 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className={`px-2 py-0.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 flex-shrink-0 ${currentPhaseInfo.color}`}>
                    <currentPhaseInfo.icon className="w-3.5 h-3.5" />
                    <span>{currentPhaseInfo.label}</span>
                  </span>
                  {inspectAngle.badge && (
                    <span className="text-sm px-1.5 py-0.5 font-mono font-bold rounded bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 truncate hidden sm:inline">
                      {inspectAngle.badge}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1 flex-shrink-0">
                  <span className="text-xs text-slate-400 font-medium mr-1">สถานะปัจจุบัน:</span>
                  <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${currentPhaseInfo.color}`}>
                    <currentPhaseInfo.icon className="w-3.5 h-3.5" />
                    <span>{currentPhaseInfo.label}</span>
                  </span>
                </div>
              </div>

              {/* Round BUG-3: Data Conflict Alert — this angle got auto-unlinked
                  because another angle already legitimately claimed the same clip */}
              {inspectAngle.data_conflict_note && (
                <div className="flex items-start justify-between gap-2 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30">
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
                    <div>
                      <div className="text-xs font-bold text-amber-300 mb-0.5">ปลดคลิปอัตโนมัติ — ชนกับ angle อื่น</div>
                      <div className="text-xs text-amber-200/90 font-mono leading-snug">{inspectAngle.data_conflict_note}</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDismissConflict(inspectAngle)}
                    className="px-2 py-0.5 rounded-md bg-white/[0.1] hover:bg-white/[0.18] text-amber-200 font-black text-[10px] cursor-pointer whitespace-nowrap active:scale-95 transition-all flex-shrink-0"
                  >
                    เข้าใจแล้ว
                  </button>
                </div>
              )}

              {/* QC Note Alert — shown when a previous QC fail note exists */}
              {inspectAngle.qc_note && (
                <div className="flex items-start gap-2 p-2.5 rounded-xl bg-red-500/10 border border-red-500/30">
                  <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
                  <div>
                    <div className="text-xs font-bold text-red-300 mb-0.5">QC ไม่ผ่าน — ต้องตัดต่อใหม่</div>
                    <div className="text-xs text-red-200 font-mono leading-snug">{inspectAngle.qc_note}</div>
                  </div>
                </div>
              )}

              {/* Short scannable product code (per-product, not per-angle) --
                  matches the prefix used in the CapCut project name so a
                  person can tell projects apart at a glance without reading
                  the full Thai product name. */}
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-300 flex-shrink-0">รหัสสินค้า:</span>
                  <input
                    key={`code-${inspectAngle.parentProduct?.id}`}
                    id={`product-code-${inspectAngle.parentProduct?.id}`}
                    type="text"
                    defaultValue={inspectAngle.parentProduct?.product_code || ''}
                    placeholder="เช่น ESG01 (auto-gen ให้แล้ว แก้เองได้)"
                    className="flex-1 min-w-0 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.1] text-xs text-white placeholder:text-slate-600 font-mono uppercase focus:outline-none focus:border-fuchsia-400/40"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById(`product-code-${inspectAngle.parentProduct?.id}`);
                      handleSaveProductCode(inspectAngle.parentProduct?.id, el?.value || '');
                    }}
                    className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 text-xs font-bold cursor-pointer active:scale-95 transition-all flex-shrink-0"
                  >
                    บันทึก
                  </button>
                </div>
              </div>

              {/* Round BUG-3.3: TikTok Shop product ID (per-product, not per-angle) + ปักตะกร้า */}
              <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-300 flex-shrink-0">TikTok Product ID:</span>
                  <input
                    key={inspectAngle.parentProduct?.id}
                    id={`tiktok-pid-${inspectAngle.parentProduct?.id}`}
                    type="text"
                    defaultValue={inspectAngle.parentProduct?.tiktok_product_id || ''}
                    placeholder="เช่น 1737088044189583209 (ว่าง = ใช้ชื่อสินค้าค้นหา)"
                    className="flex-1 min-w-0 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.1] text-xs text-white placeholder:text-slate-600 font-mono focus:outline-none focus:border-[#25F4EE]/40"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById(`tiktok-pid-${inspectAngle.parentProduct?.id}`);
                      handleSaveTiktokProductId(inspectAngle.parentProduct?.id, el?.value || '');
                    }}
                    className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 text-xs font-bold cursor-pointer active:scale-95 transition-all flex-shrink-0"
                  >
                    บันทึก
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => handlePrepareAutopost(inspectAngle)}
                  disabled={(!inspectAngle.parentProduct?.tiktok_product_id && !inspectAngle.parentProduct?.name) || !inspectAngle.video_url}
                  title={(!inspectAngle.parentProduct?.tiktok_product_id && !inspectAngle.parentProduct?.name) ? 'ใส่ TikTok Product ID หรือชื่อสินค้าก่อน' : (!inspectAngle.video_url ? 'ยังไม่มีคลิปที่เรนเดอร์แล้ว' : 'เตรียมคลิปให้ extension ปักตะกร้า')}
                  className="w-full py-2 px-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Flame className="w-3.5 h-3.5" />
                  <span>ส่ง TikTok ปักตะกร้า</span>
                </button>
              </div>

              {/* 2. Hook Title 3s (Compact) */}
              <div className="space-y-1">
                <div className="text-sm font-semibold text-slate-400">Hook 3 วินาทีแรก (จุดหยุดคนดู):</div>
                <div className="p-2.5 rounded-xl bg-[#080B11] border-l-4 border-[#25F4EE] text-xs sm:text-sm font-bold text-cyan-200 leading-snug">
                  {inspectAngle.hook_title || 'ไม่มี Hook'}
                </div>
              </div>

              {/* 2.1 Attached Raw Footage Section (คลิปดิบที่ใช้จริงสำหรับสคริปต์นี้) */}
              <div className="space-y-1.5 p-2.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span className="flex items-center gap-1.5 text-cyan-300">
                    <Film className="w-4 h-4 text-[#25F4EE]" />
                    <span>คลิปดิบที่ใช้สำหรับสคริปต์นี้ ({attachedVideos.length} คลิป)</span>
                  </span>
                  {hasAttachedVideos ? (
                    <span className="text-xs text-emerald-400 font-mono font-bold">● พร้อมตัดต่อ</span>
                  ) : (
                    <span className="text-xs text-amber-400 font-mono font-bold">● ยังไม่ได้เลือกคลิป</span>
                  )}
                </div>

                {hasAttachedVideos ? (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {attachedVideos.map((vPath, idx) => {
                      const fname = vPath.split(/[\\/]/).pop();
                      return (
                        <div
                          key={vPath + idx}
                          className="flex items-center gap-1.5 py-1 px-2 rounded-lg bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-xs font-bold text-[#25F4EE]"
                          title={vPath}
                        >
                          <Film className="w-3 h-3 flex-shrink-0" />
                          <span className="font-mono">{idx + 1}. {fname}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="py-2 px-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>ยังไม่มีคลิปดิบที่ผูกกับสคริปต์นี้ (ไม่สามารถส่งตัดต่อได้ กรุณาแนบคลิปก่อน)</span>
                  </div>
                )}
              </div>

              {/* 3. Video QC Player Section (แสดงผลเสมอเมื่อสถานะคือ ตัดต่อเสร็จ / ส่งมือถือ / โพสต์แล้ว หรือมีวิดีโอ) */}
              {(isRenderedOrBeyond || effectiveVideoUrl) && (
                <div className="space-y-1.5 p-2.5 rounded-xl bg-black/60 border border-white/[0.08]">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                    <span className="flex items-center gap-1.5 text-cyan-300">
                      <Video className="w-4 h-4 text-[#25F4EE]" />
                      <span>พรีวิววิดีโอที่ตัดต่อเสร็จ (QC Player)</span>
                    </span>
                    {effectiveVideoUrl && (
                      <span className="text-sm text-emerald-400 font-mono font-bold">● พร้อมเล่น</span>
                    )}
                  </div>

                  {effectiveVideoUrl ? (
                    <div className="relative rounded-xl overflow-hidden bg-black border border-white/[0.1] max-w-[220px] mx-auto shadow-xl">
                      <video
                        src={`/api/media/${effectiveVideoUrl}`}
                        controls
                        playsInline
                        className="w-full aspect-[9/16] max-h-56 object-contain mx-auto bg-black"
                      />
                    </div>
                  ) : (
                    <div className="py-4 px-3 text-center text-xs text-slate-400 space-y-2 border border-dashed border-white/[0.08] rounded-xl bg-black/30">
                      <div className="w-8 h-8 rounded-full bg-white/[0.05] border border-white/[0.1] flex items-center justify-center mx-auto text-slate-400">
                        <Video className="w-4 h-4" />
                      </div>
                      <p className="text-xs text-slate-300 font-bold">ยังไม่พบไฟล์วิดีโอที่เรนเดอร์สำหรับมุมนี้</p>
                      <button
                        onClick={() => {
                          if (!hasAttachedVideos) return;
                          setInspectAngle(null);
                          handleSendToStudio(inspectAngle.parentProduct, inspectAngle);
                        }}
                        disabled={!hasAttachedVideos}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 shadow-sm transition-all ${
                          hasAttachedVideos
                            ? 'bg-[#FE2C55] hover:bg-[#E0264B] text-white cursor-pointer active:scale-95'
                            : 'bg-white/[0.05] border border-white/[0.08] text-slate-500 cursor-not-allowed opacity-50'
                        }`}
                        title={hasAttachedVideos ? 'สร้าง & เรนเดอร์คลิปนี้ใน Studio' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
                      >
                        <Clapperboard className="w-3.5 h-3.5" />
                        <span>สร้าง & เรนเดอร์คลิปนี้ใน Studio</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* 4. Script Breakdown Section (Compact) */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span>บทพูดพากย์ ({scriptLines.length} ท่อน):</span>
                  {scriptLines.length > 0 && (
                    <button
                      onClick={() => handleCopyCaption(scriptLines.join('\n'), 'script_modal')}
                      className="text-[#25F4EE] hover:underline flex items-center gap-1 text-sm font-bold cursor-pointer"
                    >
                      {copiedAngleId === 'script_modal' ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอกสคริปต์</>}
                    </button>
                  )}
                </div>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-1 max-h-36 overflow-y-auto font-mono text-xs text-slate-200">
                  {scriptLines.length === 0 ? (
                    <div className="text-slate-500 text-center py-2">ไม่มีบทพูด</div>
                  ) : (
                    scriptLines.map((line, idx) => (
                      <div key={idx} className="flex items-start gap-1.5">
                        <span className="text-[#25F4EE] font-bold flex-shrink-0">{idx + 1}.</span>
                        <span>{line}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* 5. TikTok Caption & Hashtags */}
              {captionText && (
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06] space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                    <span>แคปชัน & แฮชแท็ก TikTok:</span>
                    <button
                      onClick={() => handleCopyCaption(captionText, 'cap_modal')}
                      className="text-[#25F4EE] hover:underline flex items-center gap-1 text-sm font-bold cursor-pointer"
                    >
                      {copiedAngleId === 'cap_modal' ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอกแคปชัน</>}
                    </button>
                  </div>
                  <p className="text-xs text-slate-300 font-mono line-clamp-2 select-all">
                    {inspectAngle.tiktok_caption} {inspectAngle.tiktok_hashtags}
                  </p>
                </div>
              )}

              {/* 6. True Deep-Dive Navigation Action Bar */}
              <div className="pt-2 border-t border-white/[0.08] flex items-center gap-2">
                {/* Button 1: Go to Script Lab */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    onGoToFlow?.(inspectAngle.parentProduct?.id);
                  }}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                  title="ดูและปรับแต่งสคริปต์ในหน้าสินค้า"
                >
                  <FileText className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Lab สคริปต์</span>
                </button>

                {/* Button 2: Go to Video Editor (Unified Primary Action) */}
                <button
                  onClick={() => {
                    if (!hasAttachedVideos) return;
                    setInspectAngle(null);
                    handleSendToStudio(inspectAngle.parentProduct, inspectAngle);
                  }}
                  disabled={!hasAttachedVideos}
                  className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all whitespace-nowrap ${
                    hasAttachedVideos
                      ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white cursor-pointer shadow-md shadow-[#FE2C55]/20 active:scale-95'
                      : 'bg-white/[0.05] border border-white/[0.08] text-slate-500 cursor-not-allowed opacity-50'
                  }`}
                  title={hasAttachedVideos ? 'ส่งมุมนี้เข้าสู่หน้าตัดต่อทันที' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
                >
                  <Clapperboard className="w-3.5 h-3.5" />
                  <span>ส่งไปตัดต่อ</span>
                </button>

                {/* Button 3: QC Fail (only when rendered or mobile_ready) */}
                {(inspectAngle.status === 'rendered' || inspectAngle.status === 'mobile_ready') && (
                  <button
                    onClick={() => handleQcFail(inspectAngle)}
                    className="py-2.5 px-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0 whitespace-nowrap"
                    title="QC ไม่ผ่าน — reset สถานะกลับไปตัดใหม่"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>QC ไม่ผ่าน</span>
                  </button>
                )}

                {/* Button 3.5: QC Pass (one-click approve/clear QC fail) */}
                {(inspectAngle.status === 'rendered' || inspectAngle.qc_note) && (
                  <button
                    onClick={() => handleQcPass(inspectAngle)}
                    className="py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:brightness-110 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5 cursor-pointer transition-all shadow-md shadow-[#25F4EE]/20 flex-shrink-0 active:scale-95 whitespace-nowrap"
                    title="กดเพื่อรับรอง QC ผ่านทันที (ล้างป้ายแดงออก)"
                  >
                    <Check className="w-3.5 h-3.5 text-slate-950 stroke-[3]" />
                    <span>QC ผ่าน</span>
                  </button>
                )}

                {/* Button 4: TikTok Studio Post */}
                {isRenderedOrBeyond && inspectAngle.video_url && (
                  <button
                    onClick={() => {
                      const ang = inspectAngle;
                      setInspectAngle(null);
                      handleOpenTiktokModal(ang);
                    }}
                    className="py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0 whitespace-nowrap shadow-md shadow-[#FE2C55]/20 active:scale-95"
                    title="ส่งคลิปไป TikTok Studio พร้อมปักตะกร้า"
                  >
                    <Rocket className="w-3.5 h-3.5" />
                    <span>ส่ง TikTok</span>
                  </button>
                )}

                {/* Button 4.5: Cover Studio 9:16 */}
                {isRenderedOrBeyond && inspectAngle.video_url && (
                  <button
                    type="button"
                    onClick={() => {
                      const ang = inspectAngle;
                      handleOpenCoverStudio(ang);
                    }}
                    className="py-2.5 px-3.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0 whitespace-nowrap active:scale-95"
                    title="สตูดิโอสร้างปกคลิป 9:16 (Auto Highlight Crop + AI Hook + 3D Badge)"
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    <span>สร้างปก 9:16</span>
                  </button>
                )}

                {/* Button 5: Mobile QR */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    setQrModalItem(inspectAngle);
                  }}
                  className="py-2.5 px-3.5 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0 whitespace-nowrap"
                  title="สแกน QR โหลดเข้ามือถือ"
                >
                  <QrCode className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>ส่งมือถือ (QR)</span>
                </button>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* ── QC Fail Confirmation Modal (Responsive on Desktop & iPhone 15 Pro Max) ── */}
      <Modal
        isOpen={!!qcFailTarget}
        onClose={() => { setQcFailTarget(null); setQcFailNote(''); }}
        title="QC ไม่ผ่าน — ส่งตัดใหม่"
        subtitle={qcFailTarget?.hook_title}
        maxWidth="max-w-md"
      >
        {qcFailTarget && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 sm:p-3.5 rounded-2xl bg-red-500/10 border border-red-500/30">
              <div className="w-10 h-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                <RotateCcw className="w-5 h-5 text-red-400" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm sm:text-base font-bold text-red-300">คลิปนี้จะถูกส่งกลับไปตัดใหม่</div>
                <div className="text-xs text-slate-400 mt-0.5 leading-snug">สถานะจะเปลี่ยนกลับเป็น "กำลังตัดต่อ" เพื่อเปิด Studio แก้ไขได้ทันที</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300 block">หมายเหตุ QC (เพื่อให้ตัดต่อเห็นว่าต้องแก้อะไร)</label>
              <textarea
                value={qcFailNote}
                onChange={e => setQcFailNote(e.target.value)}
                placeholder="เช่น เสียงพากย์เร็วเกินไป, ตัดจังหวะไม่เรียบร้อย, ข้อความตกขอบจอ"
                rows={3}
                className="w-full rounded-xl bg-black/40 border border-white/[0.1] text-slate-200 text-xs sm:text-sm p-3 placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]/50 resize-none font-mono leading-relaxed"
              />
              <div className="text-xs text-slate-500">ถ้าไม่ระบุจะใช้ "QC ไม่ผ่าน" เป็นค่าเริ่มต้น</div>
            </div>

            {/* Responsive Actions: Side-by-side on desktop, Stacked on narrow/mobile */}
            <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center gap-2 sm:gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => { setQcFailTarget(null); setQcFailNote(''); }}
                className="w-full sm:w-1/3 py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 text-xs sm:text-sm font-bold cursor-pointer transition-all flex items-center justify-center whitespace-nowrap active:scale-95"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                onClick={handleQcFailConfirm}
                className="w-full sm:flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 cursor-pointer transition-all shadow-lg shadow-red-900/30 active:scale-95 whitespace-nowrap"
              >
                <RotateCcw className="w-4 h-4 flex-shrink-0" />
                <span>ยืนยันส่งตัดใหม่</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Video Modal Preview with Direct Responsive QC Control Panel */}
      <Modal
        isOpen={!!previewVideoUrl}
        onClose={() => { setPreviewVideoUrl(null); setPreviewVideoAngle(null); }}
        title="พรีวิววิดีโอ (ตรวจ QC ก่อนโพสต์)"
        subtitle={previewVideoAngle?.hook_title}
        maxWidth="max-w-md"
      >
        {previewVideoUrl && (
          <div className="space-y-3.5">
            <video
              src={`/api/media/${previewVideoUrl}`}
              controls
              autoPlay
              className="w-full rounded-2xl bg-black aspect-[9/16] object-contain max-h-[60vh] shadow-2xl border border-white/[0.08]"
            />

            {/* Quick QC Decision Toolbar */}
            {previewVideoAngle && (
              <div className="p-3 rounded-2xl bg-[#080B11] border border-white/[0.1] space-y-2.5 shadow-xl">
                {previewVideoAngle.qc_note && (
                  <div className="flex items-center gap-2 py-1.5 px-2.5 rounded-xl bg-red-500/15 border border-red-500/30 text-xs font-bold text-red-300">
                    <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />
                    <span className="truncate">สถานะเดิม: QC ไม่ผ่าน ({previewVideoAngle.qc_note})</span>
                  </div>
                )}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleQcPass(previewVideoAngle)}
                    className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:brightness-110 text-slate-950 text-xs sm:text-sm font-black flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/25 cursor-pointer active:scale-95 transition-all whitespace-nowrap"
                  >
                    <Check className="w-4 h-4 text-slate-950 stroke-[3] flex-shrink-0" />
                    <span>QC ผ่าน (เป็นสีฟ้า)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const ang = previewVideoAngle;
                      setPreviewVideoUrl(null);
                      setPreviewVideoAngle(null);
                      handleQcFail(ang);
                    }}
                    className="py-2.5 px-3.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all whitespace-nowrap active:scale-95"
                  >
                    <RotateCcw className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>ตัดใหม่</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* QR Code Modal for Mobile Quick Post Transfer */}
      <Modal
        isOpen={!!qrModalItem}
        onClose={() => setQrModalItem(null)}
        title="สแกนเพื่อเปิดตัวช่วยโพสต์บนมือถือ"
        subtitle={qrModalItem?.hook_title}
        maxWidth="max-w-sm"
      >
        {qrModalItem && (() => {
          // caption/hashtags deliberately omitted from the QR-encoded URL --
          // MobileQuickPostPage fetches the live product/angle via pid+aid
          // and reads tiktok_caption/tiktok_hashtags straight off that, so
          // embedding the full text here too just risks a long AI-written
          // caption + hashtag list pushing the URL past a QR code's payload
          // ceiling ("RangeError: Data too long" from QRCodeSVG).
          const quickPostUrl = `${mobileBaseUrl}/?quick_post=1&pid=${encodeURIComponent(qrModalItem.parentProduct?.id || '')}&aid=${encodeURIComponent(qrModalItem.angle_id || '')}&eid=${encodeURIComponent(qrModalItem.export_id || '')}&video=${encodeURIComponent(qrModalItem.video_url || '')}&product=${encodeURIComponent(qrModalItem.parentProduct?.name || '')}&hook=${encodeURIComponent(qrModalItem.hook_title || '')}`;

          return (
            <div className="text-center space-y-3.5">
              <div className="p-3 rounded-2xl bg-gradient-to-tr from-[#FE2C55]/15 to-[#25F4EE]/15 border border-[#25F4EE]/30 text-center space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-[#25F4EE]">
                  <Sparkles className="w-4 h-4" />
                  <span>Quick Post Companion 4 สเต็ป</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  สแกนด้วย iPhone / Android เพื่อโหลดคลิป, ก็อปแคปชัน, ก็อปชื่อปักตะกร้า และเปิด TikTok ทันที
                </p>
              </div>

              <div className="bg-white p-3 rounded-2xl inline-block shadow-xl">
                <SafeQRCode value={quickPostUrl} size={180} level="M" />
              </div>

              {/* Caption Preview & Copy inside Modal */}
              <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-left space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                  <span>แคปชัน & แฮชแท็กพร้อมโพสต์:</span>
                  <button
                    type="button"
                    onClick={() => handleCopyCaption(`${qrModalItem.tiktok_caption || ''}\n\n${qrModalItem.tiktok_hashtags || ''}`, 'modal')}
                    className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    {copiedAngleId === 'modal' ? <><Check className="w-3.5 h-3.5 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3.5 h-3.5" /> คัดลอก</>}
                  </button>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2 font-mono leading-relaxed select-all">
                  {qrModalItem.tiktok_caption} {qrModalItem.tiktok_hashtags}
                </p>
              </div>

              <div className="space-y-2 pt-1">
                <Button
                  onClick={() => {
                    handleAngleStatusChange(qrModalItem.parentProduct.id, qrModalItem.angle_id, 'mobile_ready');
                    setQrModalItem(null);
                    showToast('อัปเดตสถานะเป็น "ส่งเข้ามือถือแล้ว"');
                  }}
                  variant="tiktok"
                  size="md"
                  icon={Check}
                  className="w-full"
                >
                  มาร์กว่า "ส่งเข้ามือถือแล้ว"
                </Button>

                <a
                  href={quickPostUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-[11px] text-slate-400 hover:text-[#25F4EE] hover:underline pt-1"
                >
                  ทดสอบเปิดหน้านี้บนเบราว์เซอร์นี้
                </a>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* ── TikTok Studio Post Modal (Preview, Edit Caption & Product ID) ── */}
      <Modal
        isOpen={!!tiktokModalItem}
        onClose={() => !isSubmittingTiktok && setTiktokModalItem(null)}
        title="เตรียมโพสต์ TikTok Studio (พร้อมปักตะกร้า)"
        subtitle={tiktokModalItem?.parentProduct?.name ? `${tiktokModalItem.parentProduct.name} — ${tiktokModalItem.hook_title || ''}` : tiktokModalItem?.hook_title}
        maxWidth="max-w-lg"
      >
        {tiktokModalItem && (
          <div className="space-y-4 pt-1">
            {/* Top Video Preview & Info Banner */}
            <div className="flex items-center gap-3 p-3 rounded-2xl bg-[#080B11] border border-white/[0.08]">
              {tiktokModalItem.video_url ? (
                <div className="w-16 aspect-[9/16] rounded-xl overflow-hidden bg-black border border-white/[0.1] flex-shrink-0 shadow-md">
                  <video
                    src={`/api/media/${tiktokModalItem.video_url}`}
                    className="w-full h-full object-cover"
                    controls={false}
                    muted
                  />
                </div>
              ) : null}
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs font-bold text-white truncate font-kanit">
                    {tiktokModalItem.parentProduct?.name}
                  </span>
                  {tiktokModalItem.badge && (
                    <Badge variant="cyan" size="sm">{tiktokModalItem.badge}</Badge>
                  )}
                </div>
                <p className="text-xs font-bold text-[#25F4EE] line-clamp-1">
                  {tiktokModalItem.hook_title}
                </p>
                <p className="text-[11px] text-slate-400">
                  ระบบจะส่งข้อมูลคลิป แคปชัน และรหัสสินค้าให้ TikTok Studio Auto-post Extension
                </p>
              </div>
            </div>

            {/* TikTok cover uses the dedicated 3:4 crop when available. */}
            <div className="flex items-center justify-between p-3 rounded-2xl bg-[#0B101B] border border-white/[0.08]">
              <div className="flex items-center gap-3 min-w-0">
                {tiktokModalItem.cover_url ? (
                  <button
                    type="button"
                    onClick={() => setCoverPreviewItem(tiktokModalItem)}
                    className="group relative w-12 aspect-[3/4] rounded-lg overflow-hidden border border-amber-500/40 flex-shrink-0 shadow-md cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-[#25F4EE]"
                    aria-label="เปิดพรีวิวภาพปก 3:4"
                    title="เปิดพรีวิวภาพปกขนาดใหญ่"
                  >
                    <img
                      src={tiktokModalItem.cover_url}
                      alt="Cover 3:4"
                      className="w-full h-full object-cover"
                    />
                    <span className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/35 transition-colors">
                      <Eye className="w-4 h-4 text-white opacity-0 group-hover:opacity-100 drop-shadow-md transition-opacity" />
                    </span>
                  </button>
                ) : (
                  <div className="w-12 aspect-[3/4] rounded-lg bg-slate-900 border border-slate-800 flex flex-col items-center justify-center text-slate-500 flex-shrink-0">
                    <ImageIcon className="w-4 h-4 opacity-40" />
                    <span className="text-[8px] mt-0.5">ยังไม่มีปก</span>
                  </div>
                )}
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-white">ภาพปกคลิป 3:4 (TikTok Cover)</span>
                    {tiktokModalItem.cover_url ? (
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 font-bold border border-emerald-500/30">
                        พร้อมส่ง
                      </span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-300 font-bold border border-amber-500/30">
                        แนะนำทำปก
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5">
                    {tiktokModalItem.cover_url ? 'มีภาพปกพร้อมแนบไปกับคลิปแล้ว' : 'เพิ่มยอดคลิกด้วยการเลือกช็อตเด่น + Hook AI'}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleOpenCoverStudio(tiktokModalItem)}
                className="py-1.5 px-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer whitespace-nowrap active:scale-95 transition-all flex-shrink-0"
              >
                <ImageIcon className="w-3.5 h-3.5" />
                <span>{tiktokModalItem.cover_url ? 'เปลี่ยนภาพปก' : 'สร้างปก 3:4'}</span>
              </button>
            </div>

            {/* Caption & Hashtag Inputs */}
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  คำอธิบายคลิป (Caption):
                </label>
                <Textarea
                  value={tiktokCaption}
                  onChange={(e) => setTiktokCaption(e.target.value)}
                  placeholder="เขียนแคปชั่นดึงดูดใจ..."
                  rows={3}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  แฮชแท็ก (Hashtags):
                </label>
                <Input
                  value={tiktokHashtags}
                  onChange={(e) => setTiktokHashtags(e.target.value)}
                  placeholder="#รีวิว #ของดีบอกต่อ..."
                />
              </div>

              <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>รหัสสินค้าปักตะกร้า (TikTok Product ID):</span>
                  <span className="text-[10px] text-slate-400">เว้นว่างไว้จะใช้ชื่อสินค้าค้นหาแทน</span>
                </label>
                <Input
                  value={tiktokProductId}
                  onChange={(e) => setTiktokProductId(e.target.value)}
                  placeholder="เช่น 1737088044189583209 หรือชื่อสินค้า"
                />
              </div>

              <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
                <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>เวลาตั้งเวลาโพสต์ล่วงหน้า (Schedule Time):</span>
                  </span>
                  <span className="text-[10px] text-slate-400">เว้นว่างไว้หากต้องการโพสต์ทันที</span>
                </label>
                <input
                  type="time"
                  value={tiktokScheduleTime}
                  onChange={(e) => setTiktokScheduleTime(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-black/50 border border-white/[0.1] text-xs font-mono text-white focus:outline-none focus:border-[#25F4EE]/50"
                />
              </div>
            </div>

            {/* Actions Bar */}
            <div className="flex items-center justify-between pt-3 border-t border-white/[0.08] gap-2">
              <button
                type="button"
                onClick={() => {
                  const pid = tiktokModalItem.parentProduct?.id;
                  const aid = tiktokModalItem.angle_id;
                  if (pid && aid) {
                    markPosted(
                      tiktokModalItem.video_url,
                      pid,
                      aid,
                      tiktokModalItem.export_id || null,
                    ).then(async () => {
                      setTiktokModalItem(null);
                      showToast('มาร์กว่าโพสต์แล้วสำเร็จ');
                      await fetchProductsData();
                    }).catch((err) => {
                      showToast('ไม่สามารถมาร์กว่าโพสต์แล้วได้: ' + (err.response?.data?.detail || err.message), 'error');
                    });
                    return;
                    showToast('มาร์กว่าโพสต์บน TikTok สำเร็จแล้ว');
                  }
                }}
                className="text-xs text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer flex items-center gap-1"
                title="คลิกหากโพสต์คลิปนี้บน TikTok เสร็จสิ้นแล้ว"
              >
                <Check className="w-3.5 h-3.5" />
                <span>มาร์กว่าโพสต์แล้ว</span>
              </button>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => setTiktokModalItem(null)}
                  disabled={isSubmittingTiktok}
                >
                  ยกเลิก
                </Button>
                <button
                  type="button"
                  onClick={handleConfirmTiktokAutopost}
                  disabled={isSubmittingTiktok}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                >
                  <Rocket className="w-3.5 h-3.5" />
                  <span>{isSubmittingTiktok ? 'กำลังส่งข้อมูล...' : 'ส่งไป TikTok Studio'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Large cover preview keeps inspection separate from editing. */}
      <Modal
        isOpen={!!coverPreviewItem}
        onClose={() => setCoverPreviewItem(null)}
        title="พรีวิวภาพปก 3:4"
        subtitle={coverPreviewItem?.project_name || coverPreviewItem?.parentProduct?.name || ''}
        maxWidth="max-w-2xl"
      >
        {coverPreviewItem?.cover_url && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-amber-500/25 bg-black/50 p-3 sm:p-5 flex items-center justify-center min-h-[18rem]">
              <img
                src={coverPreviewItem.cover_url}
                alt="พรีวิวภาพปก 3:4"
                className="max-h-[62dvh] w-auto max-w-full object-contain rounded-xl shadow-2xl"
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-slate-400">กดเปลี่ยนภาพปกเพื่อปรับภาพต่อใน Cover Studio</p>
              <Button
                variant="outline"
                size="sm"
                icon={ImageIcon}
                onClick={() => {
                  const item = coverPreviewItem;
                  setCoverPreviewItem(null);
                  handleOpenCoverStudio(item);
                }}
              >
                เปลี่ยนภาพปก
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Script Library Modal (Round TRK-3) ── */}
      <Modal
        isOpen={showScriptLibraryModal}
        onClose={() => setShowScriptLibraryModal(false)}
        title="คลังสคริปต์ทั้งหมด (Script Library)"
        subtitle="เลือกสคริปต์ 3-5 รายการเพื่อนำขึ้นมาตัดต่อบนบอร์ดประจำวันนี้"
        maxWidth="max-w-3xl"
      >
        <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {/* Top Toolbar: Search & Quick Pick Actions */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-white/[0.08]">
            <div className="relative flex-1 min-w-0">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={scriptLibrarySearch}
                onChange={(e) => setScriptLibrarySearch(e.target.value)}
                placeholder="ค้นหาสคริปต์ หรือชื่อสินค้า..."
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-black/50 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50"
              />
            </div>

            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className="text-xs font-mono text-cyan-300 px-2 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                เลือกแล้ว: {pickedScriptIds?.length || 0} รายการ
              </span>
              <button
                type="button"
                onClick={() => {
                  const allScripted = allAnglesList.filter(a => (a.status || 'scripted') === 'scripted');
                  handlePickTopScripts(allScripted, 4);
                  showToast('เลือก 4 สคริปต์แรกเข้าคิววันนี้เรียบร้อย');
                }}
                className="px-2.5 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] text-slate-200 text-xs font-bold cursor-pointer transition-colors whitespace-nowrap"
                title="เลือก 4 รายการแรกอัตโนมัติ"
              >
                เลือก 4 รายการแรก
              </button>
              <button
                type="button"
                onClick={() => {
                  handleClearPickedScripts();
                  showToast('ล้างคิวสคริปต์วันนี้ทั้งหมด');
                }}
                className="px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-rose-500/15 border border-white/[0.06] hover:border-rose-500/30 text-slate-400 hover:text-rose-300 text-xs font-bold cursor-pointer transition-colors whitespace-nowrap"
                title="ล้างการเลือกทั้งหมด"
              >
                ล้างคิว
              </button>
            </div>
          </div>

          {/* List of Available Scripts */}
          {(() => {
            const allScripted = allAnglesList.filter(a => (a.status || 'scripted') === 'scripted');
            const q = scriptLibrarySearch.toLowerCase().trim();
            const filtered = allScripted.filter(a =>
              !q ||
              (a.parentProduct?.name || '').toLowerCase().includes(q) ||
              (a.hook_title || '').toLowerCase().includes(q)
            );

            if (filtered.length === 0) {
              return (
                <div className="py-12 text-center text-slate-500 text-xs">
                  {allScripted.length === 0 ? 'ยังไม่มีสคริปต์ในระบบ' : 'ไม่พบสคริปต์ที่ตรงกับคำค้นหา'}
                </div>
              );
            }

            return (
              <div className="space-y-2.5">
                {filtered.map((ang, idx) => {
                  const aid = ang.angle_id || ang.id;
                  const isPicked = (pickedScriptIds || []).includes(aid);
                  const chosenVideos = (ang.selected_videos && ang.selected_videos.length > 0)
                    ? ang.selected_videos
                    : (ang.selected_video ? [ang.selected_video] : []);
                  const hasVideos = chosenVideos.length > 0;

                  return (
                    <div
                      key={`${ang.parentProduct?.id}_${aid || idx}`}
                      className={`p-3 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isPicked
                          ? 'bg-cyan-950/20 border-cyan-500/40 shadow-sm shadow-cyan-500/5'
                          : 'bg-black/30 border-white/[0.08] hover:border-white/[0.15]'
                      }`}
                    >
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-bold text-white font-kanit">
                            {ang.parentProduct?.name}
                          </span>
                          {ang.badge && (
                            <Badge variant="cyan" size="sm">{ang.badge}</Badge>
                          )}
                          {hasVideos ? (
                            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                              มีคลิปดิบพร้อม ({chosenVideos.length})
                            </span>
                          ) : (
                            <span className="text-[10px] text-amber-400/80">
                              ยังไม่ได้แนบคลิปดิบ
                            </span>
                          )}
                        </div>
                        <div className="pl-2 border-l-2 border-[#25F4EE] text-xs font-semibold text-cyan-200 line-clamp-1">
                          {ang.hook_title}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center flex-shrink-0">
                        <button
                          type="button"
                          onClick={() => handleTogglePickScript(aid)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer active:scale-95 whitespace-nowrap ${
                            isPicked
                              ? 'bg-cyan-500/20 hover:bg-rose-500/20 border border-cyan-500/40 hover:border-rose-500/40 text-cyan-300 hover:text-rose-300'
                              : 'bg-white/[0.06] hover:bg-cyan-500/20 border border-white/[0.1] hover:border-cyan-500/40 text-slate-200 hover:text-cyan-300'
                          }`}
                        >
                          {isPicked ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>อยู่ในคิววันนี้</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3.5 h-3.5" />
                              <span>หยิบมาทำวันนี้</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      </Modal>

      {/* ── Historical Posted Clips Archive Modal (Round TRK-3) ── */}
      <Modal
        isOpen={showArchiveModal}
        onClose={() => setShowArchiveModal(false)}
        title="คลังประวัติคลิปที่โพสต์แล้วทั้งหมด (Posted Archive)"
        subtitle="ประวัติคลิปที่โพสต์สำเร็จก่อนวันนี้ทั้งหมด เพื่อไม่ให้รกบอร์ดหลัก"
        maxWidth="max-w-3xl"
      >
        <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {/* Top Search Toolbar */}
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-white/[0.08]">
            <div className="relative flex-1 min-w-0">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={archiveSearchQuery}
                onChange={(e) => setArchiveSearchQuery(e.target.value)}
                placeholder="ค้นหาคลิปย้อนหลัง, สคริปต์, หรือชื่อสินค้า..."
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-black/50 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50"
              />
            </div>
            {archiveSearchQuery && (
              <button
                type="button"
                onClick={() => setArchiveSearchQuery('')}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* List of Archived Posted Clips */}
          {(() => {
            const allPosted = allAnglesList.filter(a => a.status === 'posted');
            const q = archiveSearchQuery.toLowerCase().trim();
            const filtered = allPosted.filter(a =>
              !q ||
              (a.parentProduct?.name || '').toLowerCase().includes(q) ||
              (a.hook_title || '').toLowerCase().includes(q)
            );

            if (filtered.length === 0) {
              return (
                <div className="py-12 text-center text-slate-500 text-xs">
                  {allPosted.length === 0 ? 'ยังไม่มีคลิปที่โพสต์ในระบบ' : 'ไม่พบคลิปที่ตรงกับคำค้นหา'}
                </div>
              );
            }

            return (
              <div className="space-y-2.5">
                {filtered.map((ang, idx) => {
                  const dateStr = ang.posted_at || ang.updated_at || '';
                  const displayDate = dateStr ? new Date(dateStr).toLocaleDateString('th-TH', {
                    day: 'numeric',
                    month: 'short',
                    year: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  }) : 'ไม่ระบุเวลา';
                  const captionText = `${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`.trim();

                  return (
                    <div
                      key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                      className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] hover:border-emerald-500/40 transition-all flex items-center gap-3 group"
                    >
                      {/* Left: Mini 9:16 Video Preview */}
                      {ang.video_url ? (
                        <div
                          onClick={() => handlePreviewVideo(ang.video_url, ang)}
                          className="w-12 aspect-[9/16] rounded-xl overflow-hidden bg-black border border-white/[0.1] hover:border-[#25F4EE] flex-shrink-0 relative cursor-pointer group/vid"
                          title="คลิกเพื่อเปิดดูวิดีโอ"
                        >
                          <video
                            src={`/api/media/${ang.video_url}#t=1.0`}
                            muted
                            playsInline
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover/vid:bg-black/10">
                            <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                          </div>
                        </div>
                      ) : (
                        <div className="w-12 aspect-[9/16] rounded-xl bg-slate-900 border border-white/[0.08] flex items-center justify-center flex-shrink-0 text-slate-600">
                          <Film className="w-4 h-4" />
                        </div>
                      )}

                      {/* Middle: Details */}
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-bold text-white font-kanit truncate">
                            {ang.parentProduct?.name}
                          </span>
                          {ang.badge && (
                            <Badge variant="cyan" size="sm">{ang.badge}</Badge>
                          )}
                          <span className="text-[10px] font-mono text-emerald-400/90 px-1.5 py-0.2 rounded bg-emerald-500/10 border border-emerald-500/20">
                            {displayDate}
                          </span>
                        </div>
                        <p className="text-xs text-[#25F4EE] font-bold line-clamp-1">
                          {ang.hook_title}
                        </p>
                        {captionText && (
                          <p className="text-[11px] text-slate-400 line-clamp-1">
                            {captionText}
                          </p>
                        )}
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {captionText && (
                          <button
                            type="button"
                            onClick={() => handleCopyCaption(captionText, ang.angle_id)}
                            className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white cursor-pointer transition-colors"
                            title="คัดลอกแคปชัน & แฮชแท็ก"
                          >
                            {copiedAngleId === ang.angle_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-[#25F4EE]" />}
                          </button>
                        )}
                        {ang.video_url && (
                          <button
                            type="button"
                            onClick={() => handlePreviewVideo(ang.video_url, ang)}
                            className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-[#25F4EE] cursor-pointer transition-colors"
                            title="เปิดดูวิดีโอเต็ม"
                          >
                            <Play className="w-3.5 h-3.5 fill-current" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleOpenTiktokModal && handleOpenTiktokModal(ang)}
                          className="px-2.5 py-1.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center gap-1 shadow-sm cursor-pointer active:scale-95 whitespace-nowrap"
                          title="ส่งคลิปไป TikTok Studio อีกครั้ง"
                        >
                          <Rocket className="w-3 h-3 flex-shrink-0" />
                          <span>ส่ง TikTok</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      </Modal>

      {/* ── 1. Top Header Banner ── */}
      <div className="w-full max-w-full min-w-0 bg-[#0B0F19] border border-white/[0.08] p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 sm:gap-4 overflow-hidden">
        <div className="flex items-start sm:items-center gap-3 sm:gap-3.5 w-full min-w-0 flex-1">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-lg shadow-[#FE2C55]/20 flex-shrink-0 mt-0.5 sm:mt-0">
            <Layers className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 min-w-0">
              <h2 className="text-base sm:text-lg lg:text-xl font-bold font-kanit text-white tracking-wide truncate">
                แทร็กเกอร์ 5 เฟส
              </h2>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 whitespace-nowrap flex-shrink-0">
                Content Tracker Hub
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 line-clamp-1 sm:line-clamp-2 leading-relaxed break-words">
              ระบบติดตามสถานะคลิปตลอด Pipeline 5 ขั้นตอน (สคริปต์พร้อม → กำลังตัดต่อ → ตัดต่อเสร็จ / ตรวจ QC → ส่งเข้ามือถือ → โพสต์แล้ว)
            </p>
          </div>
        </div>

        {/* Global Action Toolbar */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-start sm:justify-end flex-wrap pt-0.5 md:pt-0 min-w-0 flex-shrink-0">
          {/* View Mode Toggle Switcher */}
          <div className="flex items-center p-0.5 rounded-xl bg-black/40 border border-white/[0.08]">
            <button
              type="button"
              onClick={() => handleSwitchViewMode('kanban')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'kanban'
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองบอร์ด 5 เฟส (Kanban)"
            >
              <Kanban className="w-3.5 h-3.5" />
              <span>บอร์ด 5 เฟส</span>
            </button>
            <button
              type="button"
              onClick={() => handleSwitchViewMode('schedule')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'schedule'
                  ? 'bg-gradient-to-r from-[#FE2C55]/20 to-[#25F4EE]/20 text-white border border-[#25F4EE]/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet)"
            >
              <Calendar className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>คิวประจำวัน</span>
            </button>
            <button
              type="button"
              onClick={() => handleSwitchViewMode('table')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองตารางข้อมูล (Table)"
            >
              <Table className="w-3.5 h-3.5" />
              <span>ตารางข้อมูล</span>
            </button>
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={() => { fetchProductsData(); onRefresh?.(); }}
            className="p-2 min-w-[36px] min-h-[36px] rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white border border-white/[0.08] transition-colors cursor-pointer flex items-center justify-center active:scale-95 flex-shrink-0"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#25F4EE]' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── 2. Responsive 5-Phase Metric Cards (iPhone 15 PM Touch Snap + Tablet/Desktop Adaptive Grid) ── */}
      <div className="w-full max-w-full overflow-x-auto no-scrollbar snap-x flex gap-2 pb-1 sm:grid sm:grid-cols-3 xl:grid-cols-6 sm:overflow-visible">
        {/* All Card */}
        <button
          type="button"
          onClick={() => scrollToPhaseColumn('all')}
          className={`flex-shrink-0 snap-start min-w-[130px] sm:min-w-0 p-3 rounded-2xl border text-left transition-all relative cursor-pointer active:scale-95 ${
            activePhase === 'all'
              ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 shadow-lg ring-1 ring-[#25F4EE]/30'
              : 'bg-[#080B11]/80 border-white/[0.06] hover:border-white/[0.15] hover:bg-white/[0.02]'
          }`}
        >
          <div className="flex items-center justify-between gap-1.5">
            <div className="flex items-center gap-2 min-w-0">
              <Layers className={`w-4 h-4 flex-shrink-0 ${activePhase === 'all' ? 'text-[#25F4EE]' : 'text-slate-400'}`} />
              <span className={`text-xs font-bold truncate ${activePhase === 'all' ? 'text-white' : 'text-slate-300'}`}>
                ทั้งหมด
              </span>
            </div>
            <span className={`text-[11px] px-2 py-0.5 rounded-full font-mono font-bold flex-shrink-0 ${
              activePhase === 'all'
                ? 'bg-white text-slate-950 shadow-sm'
                : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
            }`}>
              {allAnglesList.length}
            </span>
          </div>
          <div className="text-[10px] text-slate-400 truncate mt-1">คลิปทุกสถานะ</div>
          <div className={`h-1 w-full mt-2 rounded-full transition-all ${
            activePhase === 'all' ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]' : 'bg-white/[0.04]'
          }`} />
        </button>

        {/* 5 Phase Cards */}
        {PIPELINE_PHASES.map((p) => {
          const count = phaseCounts[p.id] || 0;
          const isActive = activePhase === p.id;
          const Icon = p.icon;

          return (
            <button
              key={p.id}
              type="button"
              onClick={() => scrollToPhaseColumn(isActive && activePhase !== 'all' ? 'all' : p.id)}
              className={`flex-shrink-0 snap-start min-w-[140px] sm:min-w-0 p-3 rounded-2xl border text-left transition-all relative cursor-pointer active:scale-95 ${
                isActive
                  ? `${p.color} shadow-lg ring-1 ring-[#25F4EE]/30`
                  : 'bg-[#080B11]/80 border-white/[0.06] hover:border-white/[0.15] hover:bg-white/[0.02]'
              }`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {p.label}
                  </span>
                </div>
                <span className={`text-[11px] px-2 py-0.5 rounded-full font-mono font-bold flex-shrink-0 ${
                  isActive
                    ? 'bg-white text-slate-950 shadow-sm'
                    : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
                }`}>
                  {count}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 truncate mt-1">{p.short}</div>
              <div className={`h-1 w-full mt-2 rounded-full transition-all ${
                isActive ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]' : 'bg-white/[0.04]'
              }`} />
            </button>
          );
        })}
      </div>

      {/* ── 3. Streamlined Search & Filter Row ── */}
      <div className="bg-[#0B0F19] p-2.5 sm:p-3 rounded-2xl border border-white/[0.08] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-2.5">
        {/* Search Box */}
        <div className="relative flex-1 min-w-0">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ค้นหาชื่อสินค้า, สคริปต์, หรือ Hook..."
            className="w-full pl-9 pr-8 py-2 rounded-xl bg-[#080B11] border border-white/[0.1] text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50 shadow-inner"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Product Filter Dropdown & Match Stats */}
        <div className="flex items-center gap-2 justify-between md:justify-end flex-shrink-0">
          <select
            value={selectedProductFilter}
            onChange={(e) => setSelectedProductFilter(e.target.value)}
            className="py-2 px-3 rounded-xl bg-[#080B11] border border-white/[0.12] text-xs font-bold text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer max-w-[170px] sm:max-w-[220px] truncate"
          >
            <option value="all">สินค้าทั้งหมด ({products.length})</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} ({(p.angles || []).length})
              </option>
            ))}
          </select>

          <span className="text-[11px] font-mono px-2.5 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-slate-400 whitespace-nowrap">
            {filteredAngles.length} รายการ
          </span>
        </div>
      </div>

      {/* ── Quick Product Pills (Round TRK-2) ── */}
      {products.length > 0 && (
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 pt-0.5">
          <button
            type="button"
            onClick={() => setSelectedProductFilter('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer active:scale-95 flex items-center gap-1.5 ${
              selectedProductFilter === 'all'
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                : 'bg-white/[0.04] text-slate-400 hover:text-white hover:bg-white/[0.08] border border-white/[0.06]'
            }`}
          >
            <span>สินค้าทั้งหมด</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/40 text-slate-300">
              {allAnglesList.length}
            </span>
          </button>
          {products.map((p) => {
            const pCount = (p.angles || []).length;
            const isSelected = selectedProductFilter === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedProductFilter(isSelected ? 'all' : p.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer active:scale-95 flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                    : 'bg-white/[0.04] text-slate-400 hover:text-white hover:bg-white/[0.08] border border-white/[0.06]'
                }`}
              >
                <span className="truncate max-w-[160px]">{p.name}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/40 text-slate-300">
                  {pCount}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          3. REAL HORIZONTAL KANBAN BOARD (SWIPEABLE COLUMNS)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'kanban' && (
        <div className="space-y-1.5">
          {/* Mobile Swipe Hint */}
          <div className="flex xl:hidden items-center justify-between text-sm text-slate-400 px-1">
            <span className="flex items-center gap-1 text-slate-400">
              <ChevronLeft className="w-3 h-3 text-[#25F4EE]" />
              <span>เลื่อนซ้าย-ขวาเพื่อดูหัวข้อถัดไป</span>
              <ChevronRight className="w-3 h-3 text-[#25F4EE]" />
            </span>
            <span className="text-[#25F4EE] font-bold font-mono">5 คอลัมน์</span>
          </div>

          {/* Real Horizontal Kanban Board with Snap-Scroll */}
          <div className="flex overflow-x-auto snap-x snap-mandatory gap-2.5 pb-3 no-scrollbar scroll-smooth items-start xl:grid xl:grid-cols-5 xl:overflow-x-visible xl:snap-none">
            {PIPELINE_PHASES.map((phase) => {
              const rawPhaseAngles = filteredAngles.filter(a => a.status === phase.id);
              const isScripted = phase.id === 'scripted';
              const isPosted = phase.id === 'posted';

              // In scripted phase: only show angles picked for today's production!
              const activePickedIds = pickedScriptIds || [];
              const displayedScriptAngles = isScripted
                ? rawPhaseAngles.filter(a => activePickedIds.includes(a.angle_id || a.id))
                : rawPhaseAngles;

              // In posted phase: only show angles posted TODAY
              const todayPostedAngles = isPosted
                ? rawPhaseAngles.filter(isAnglePostedToday)
                : [];
              const archivedPostedAngles = isPosted
                ? rawPhaseAngles.filter(a => !isAnglePostedToday(a))
                : [];

              const phaseAngles = isScripted
                ? displayedScriptAngles
                : isPosted
                ? todayPostedAngles
                : rawPhaseAngles;

              // Group by product for 'scripted' phase if toggle active
              const productGroups = {};
              if (isScripted && groupByProduct) {
                phaseAngles.forEach(ang => {
                  const pid = ang.parentProduct?.id || 'other';
                  if (!productGroups[pid]) {
                    productGroups[pid] = {
                      product: ang.parentProduct,
                      angles: []
                    };
                  }
                  productGroups[pid].angles.push(ang);
                });
              }
              const groupKeys = Object.keys(productGroups);

              return (
                <div
                  key={phase.id}
                  ref={(el) => (colRefs.current[phase.id] = el)}
                  className="w-[82vw] max-w-[320px] xl:w-auto xl:max-w-none flex-shrink-0 snap-center p-2.5 border border-white/[0.08] space-y-2 rounded-2xl glass-card transition-colors hover:border-white/[0.15] bg-[#070A12] flex flex-col"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-1.5 border-b border-white/[0.08]">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-white font-kanit">
                      <phase.icon className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>{phase.label}</span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {isScripted ? (
                        <>
                          <button
                            type="button"
                            onClick={() => setShowScriptLibraryModal(true)}
                            className="px-2 py-0.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors active:scale-95"
                            title="เปิดคลังสคริปต์ทั้งหมดเพื่อเลือกเข้าบอร์ดประจำวัน"
                          >
                            <FolderDown className="w-3 h-3" />
                            <span>คลัง ({rawPhaseAngles.length})</span>
                          </button>
                          <span
                            className="text-xs font-mono font-bold px-1.5 py-0.2 rounded-full bg-black/60 border border-white/[0.08] text-[#25F4EE]"
                            title={`คิววันนี้ ${displayedScriptAngles.length} จากสคริปต์ทั้งหมด ${rawPhaseAngles.length}`}
                          >
                            {displayedScriptAngles.length}/{rawPhaseAngles.length}
                          </span>
                        </>
                      ) : isPosted ? (
                        <>
                          {archivedPostedAngles.length > 0 && (
                            <button
                              type="button"
                              onClick={() => setShowArchiveModal(true)}
                              className="px-2 py-0.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors active:scale-95"
                              title="เปิดดูคลังประวัติคลิปที่โพสต์ในอดีตทั้งหมด"
                            >
                              <Archive className="w-3 h-3" />
                              <span>คลัง ({archivedPostedAngles.length})</span>
                            </button>
                          )}
                          <span className="text-xs font-mono font-bold px-1.5 py-0.2 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">
                            {todayPostedAngles.length} วันนี้
                          </span>
                        </>
                      ) : (
                        <span className="text-sm font-mono font-bold px-1.5 py-0.2 rounded-full bg-black/60 border border-white/[0.08] text-slate-300">
                          {rawPhaseAngles.length}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Cards inside column (Vertical Scrollable within column) */}
                  <div className="space-y-2 max-h-[68vh] overflow-y-auto pr-0.5 min-h-[120px]">
                    {isScripted && rawPhaseAngles.length > 0 && displayedScriptAngles.length === 0 ? (
                      <div className="py-6 text-center space-y-2 border border-dashed border-white/[0.08] rounded-xl px-2">
                        <div className="text-xs text-slate-400">ยังไม่ได้หยิบสคริปต์เข้าคิววันนี้</div>
                        <button
                          type="button"
                          onClick={() => setShowScriptLibraryModal(true)}
                          className="py-1.5 px-3 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer"
                        >
                          <FolderDown className="w-3.5 h-3.5" />
                          <span>เลือกสคริปต์จากคลัง ({rawPhaseAngles.length} รายการ)</span>
                        </button>
                      </div>
                    ) : isPosted && rawPhaseAngles.length > 0 && todayPostedAngles.length === 0 ? (
                      <div className="py-6 text-center space-y-2 border border-dashed border-white/[0.08] rounded-xl px-2">
                        <div className="text-xs text-slate-400">วันนี้ยังไม่มีคลิปโพสต์ใหม่</div>
                        {archivedPostedAngles.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setShowArchiveModal(true)}
                            className="py-1.5 px-3 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer"
                          >
                            <Archive className="w-3.5 h-3.5 text-emerald-400" />
                            <span>ดูคลังประวัติ ({archivedPostedAngles.length} คลิป)</span>
                          </button>
                        )}
                      </div>
                    ) : phaseAngles.length === 0 ? (
                      <div className="py-8 text-center text-sm text-slate-500 border border-dashed border-white/[0.06] rounded-xl">
                        ไม่มีคลิปในขั้นตอนนี้
                      </div>
                    ) : isScripted && groupByProduct ? (
                      /* Accordion Group by Product View */
                      groupKeys.map((pid) => {
                        const grp = productGroups[pid];
                        const isCollapsed = collapsedGroups[`${phase.id}_${pid}`];
                        return (
                          <div key={pid} className="rounded-xl border border-white/[0.08] overflow-hidden bg-black/30">
                            <button
                              type="button"
                              onClick={() => toggleGroupCollapse(phase.id, pid)}
                              className="w-full flex items-center justify-between px-2.5 py-2 bg-white/[0.03] hover:bg-white/[0.06] text-left transition-colors cursor-pointer"
                            >
                              <div className="flex items-center gap-1.5 min-w-0">
                                {isCollapsed ? (
                                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                                ) : (
                                  <ChevronDown className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0" />
                                )}
                                <span className="text-xs font-bold text-slate-200 truncate font-kanit">
                                  {grp.product?.name || 'สินค้า'}
                                </span>
                              </div>
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/50 text-slate-400 border border-white/[0.06] flex-shrink-0">
                                {grp.angles.length}
                              </span>
                            </button>
                            {!isCollapsed && (
                              <div className="p-1.5 space-y-2 bg-black/20">
                                {grp.angles.map((ang, idx) => (
                                  <KanbanCard
                                    key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                                    ang={ang}
                                    phaseId={phase.id}
                                    onSendToStudio={handleSendToStudio}
                                    onStatusChange={handleAngleStatusChange}
                                    onPreviewVideo={handlePreviewVideo}
                                    onOpenQrModal={setQrModalItem}
                                    onOpenTiktokModal={handleOpenTiktokModal}
                                    onOpenCoverStudio={handleOpenCoverStudio}
                                    onInspectAngle={setInspectAngle}
                                    onCopyCaption={handleCopyCaption}
                                    onQcFail={handleQcFail}
                                    onQcPass={handleQcPass}
                                    onDismissConflict={handleDismissConflict}
                                    onUnpickScript={handleTogglePickScript}
                                    copiedAngleId={copiedAngleId}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      /* Flat Cards List */
                      phaseAngles.map((ang, idx) => (
                        <KanbanCard
                          key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                          ang={ang}
                          phaseId={phase.id}
                          onSendToStudio={handleSendToStudio}
                          onStatusChange={handleAngleStatusChange}
                          onPreviewVideo={handlePreviewVideo}
                          onOpenQrModal={setQrModalItem}
                          onOpenTiktokModal={handleOpenTiktokModal}
                          onOpenCoverStudio={handleOpenCoverStudio}
                          onInspectAngle={setInspectAngle}
                          onCopyCaption={handleCopyCaption}
                          onQcFail={handleQcFail}
                          onQcPass={handleQcPass}
                          onDismissConflict={handleDismissConflict}
                          onUnpickScript={handleTogglePickScript}
                          copiedAngleId={copiedAngleId}
                        />
                      ))
                    )}

                    {/* Bottom Quick Action for Scripted Column */}
                    {isScripted && rawPhaseAngles.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowScriptLibraryModal(true)}
                        className="w-full py-2 px-2.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-dashed border-cyan-500/30 text-cyan-300 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-95"
                        title="เปิดคลังสคริปต์เพื่อหยิบสคริปต์เพิ่มเติมมาตัดต่อวันนี้"
                      >
                        <FolderDown className="w-3.5 h-3.5 text-cyan-400" />
                        <span>หยิบสคริปต์จากคลัง ({Math.max(0, rawPhaseAngles.length - displayedScriptAngles.length)} เหลืออยู่)</span>
                      </button>
                    )}

                    {/* Bottom Quick Action for Posted Column */}
                    {isPosted && archivedPostedAngles.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowArchiveModal(true)}
                        className="w-full py-2 px-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-95"
                        title="เปิดดูคลิปที่โพสต์แล้วทั้งหมดในอดีต"
                      >
                        <Archive className="w-3.5 h-3.5 text-emerald-400" />
                        <span>คลังประวัติคลิปเก่า ({archivedPostedAngles.length} คลิป)</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          4. DAILY RUN SHEET (ตารางจัดคิวโพสต์ประจำวัน 3-5 คลิป)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'schedule' && (
        <ScheduleAgenda
          readyClips={allAnglesList.filter((a) => (a.status === 'rendered' || a.status === 'mobile_ready') && a.video_url)}
          onPreviewVideo={handlePreviewVideo}
          onOpenCoverStudio={handleOpenCoverStudio}
            showToast={showToast}
        />
      )}

      {/* ══════════════════════════════════════════════════════════
          4. ADAPTIVE RESPONSIVE TABLE VIEW (DESKTOP PRO TABLE + MOBILE FEED)
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'table' && (
        <div className="space-y-3">
          {/* 📱 Mobile Card Feed for iPhone 15 Pro Max and Narrow Screens */}
          <div className="block md:hidden space-y-2.5">
            {filteredAngles.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 rounded-2xl bg-[#070A12] border border-white/[0.08]">
                ไม่พบข้อมูลคลิปตามเงื่อนไขที่ค้นหา
              </div>
            ) : (
              filteredAngles.map((ang, idx) => (
                <MobileTableRowCard
                  key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                  ang={ang}
                  onSendToStudio={handleSendToStudio}
                  onStatusChange={handleAngleStatusChange}
                  onPreviewVideo={handlePreviewVideo}
                  onOpenQrModal={setQrModalItem}
                  onOpenTiktokModal={handleOpenTiktokModal}
                  onInspectAngle={setInspectAngle}
                  onCopyCaption={handleCopyCaption}
                  onQcPass={handleQcPass}
                  copiedAngleId={copiedAngleId}
                />
              ))
            )}
          </div>

          {/* 💻 Desktop High-Density Pro Table */}
          <div className="hidden md:block glass-card rounded-2xl border border-white/[0.08] overflow-hidden bg-[#070A12] shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.08] bg-black/70 text-slate-400 font-bold text-xs uppercase tracking-wider">
                    <th className="py-3 px-3 w-16 text-center whitespace-nowrap">วิดีโอ</th>
                    <th className="py-3 px-3 min-w-[200px] max-w-sm">สินค้า & มุมขาย (Hook Title)</th>
                    <th className="py-3 px-3 w-40 whitespace-nowrap">สถานะขั้นตอน</th>
                    <th className="py-3 px-3 min-w-[220px]">แคปชัน TikTok</th>
                    <th className="py-3 px-3 text-right w-52 min-w-[190px] whitespace-nowrap">ปุ่มลัด</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAngles.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-xs text-slate-500">
                        ไม่พบข้อมูลคลิปตามเงื่อนไขที่ค้นหา
                      </td>
                    </tr>
                  ) : (
                    filteredAngles.map((ang, idx) => (
                      <TableRow
                        key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                        ang={ang}
                        onSendToStudio={handleSendToStudio}
                        onStatusChange={handleAngleStatusChange}
                        onPreviewVideo={handlePreviewVideo}
                        onOpenQrModal={setQrModalItem}
                        onOpenTiktokModal={handleOpenTiktokModal}
                        onInspectAngle={setInspectAngle}
                        onCopyCaption={handleCopyCaption}
                        onQcPass={handleQcPass}
                        copiedAngleId={copiedAngleId}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── 9:16 Cover & Hook Studio Modal ── */}
      <CoverStudioModal
        isOpen={!!coverStudioItem}
        onClose={() => setCoverStudioItem(null)}
        videoItem={coverStudioItem}
        onCoverSaved={handleCoverSaved}
      />
    </div>
  );
}
