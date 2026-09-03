import React, { useState, useEffect, useMemo, useCallback, useRef, memo } from 'react';
import {
  Layers, Clapperboard, Check, Trash2, ArrowRight, Play,
  Smartphone, RefreshCw, Search, QrCode, ArrowLeft, Copy,
  Kanban, Table, Sparkles, CheckCircle2, Clock,
  ExternalLink, ChevronRight, ChevronLeft, Filter, AlertCircle,
  Video, Eye, Flame, TrendingUp, Plus, X, FileText, Scissors,
  FolderDown, Info, Film, RotateCcw, ShieldAlert
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import {
  getProducts, updateAngleStatus, deleteProduct, updateProduct
} from '../api';
import { Modal, Toast, Button, Badge, Input } from './ui';
import { useDebounce, useToast } from '../hooks';

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
        src={`/api/media/${videoUrl}`}
        muted
        playsInline
        loop
        className="w-full h-full object-cover"
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
  onInspectAngle,
  onCopyCaption,
  onQcFail,
  onQcPass,
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
      
      {/* 1. Header: Product Name + Badge + Detail Inspect Icon */}
      <div className="flex items-center justify-between gap-1.5 text-xs">
        <span
          onClick={() => onInspectAngle(ang)}
          className="font-bold text-white truncate flex-1 min-w-0 font-kanit text-sm hover:text-[#25F4EE] cursor-pointer"
          title={`คลิกเพื่อดูรายละเอียดเชิงลึกของ: ${ang.parentProduct?.name}`}
        >
          {ang.parentProduct?.name}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {ang.badge && (
            <span className="text-xs px-1.5 py-0.2 font-mono font-bold rounded bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 whitespace-nowrap">
              {ang.badge}
            </span>
          )}
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-0.5 rounded text-slate-500 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="ดูรายละเอียดจริงเชิงลึก (Deep Dive)"
          >
            <Info className="w-3 h-3" />
          </button>
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
            {/* Primary Action Button: Full-width Cyan QC Pass */}
            {onQcPass && (
              <button
                type="button"
                onClick={() => onQcPass(ang)}
                className="w-full py-1.5 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:brightness-110 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer transition-all active:scale-95 whitespace-nowrap"
                title={ang.qc_note ? "คลิกเพื่อแก้ให้ QC ผ่าน (ล้างป้ายแดงออก)" : "คลิกเพื่อยืนยัน QC ผ่าน (พร้อมส่งมือถือ)"}
              >
                <Check className="w-3.5 h-3.5 text-slate-950 stroke-[3]" />
                <span>{ang.qc_note ? "แก้เป็น QC ผ่าน" : "ยืนยัน QC ผ่าน"}</span>
              </button>
            )}

            {/* Secondary Actions Row: 3 Balanced Equal Columns */}
            <div className="grid grid-cols-3 gap-1.5 w-full">
              {ang.video_url ? (
                <button
                  type="button"
                  onClick={() => onPreviewVideo(ang.video_url, ang)}
                  className="py-1.5 px-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1 cursor-pointer transition-colors whitespace-nowrap"
                  title="พรีวิวตรวจ QC"
                >
                  <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
                  <span>QC</span>
                </button>
              ) : <div />}

              <button
                type="button"
                onClick={() => onQcFail(ang)}
                className="py-1.5 px-1 rounded-lg bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-bold flex items-center justify-center gap-1 cursor-pointer transition-colors whitespace-nowrap"
                title="QC ไม่ผ่าน — ส่งตัดใหม่"
              >
                <RotateCcw className="w-3 h-3" />
                <span>ตัดใหม่</span>
              </button>

              <button
                type="button"
                onClick={() => onOpenQrModal(ang)}
                className="py-1.5 px-1 rounded-lg bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 text-xs font-bold flex items-center justify-center gap-1 cursor-pointer transition-colors whitespace-nowrap"
                title="ส่งเข้ามือถือ"
              >
                <QrCode className="w-3 h-3" />
                <span>มือถือ</span>
              </button>
            </div>
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
// 📋 TABLE VIEW COMPONENT (High-Density True Table Style)
// ═══════════════════════════════════════════════════════════════════════
const TableRow = memo(function TableRow({
  ang,
  onSendToStudio,
  onStatusChange,
  onPreviewVideo,
  onOpenQrModal,
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
      <td className="py-2 px-3 w-14">
        {ang.video_url ? (
          <button
            onClick={() => onPreviewVideo(ang.video_url)}
            className="w-9 h-12 rounded-lg overflow-hidden bg-black relative border border-white/[0.1] hover:border-[#25F4EE] flex-shrink-0 group cursor-pointer"
          >
            <video src={`/api/media/${ang.video_url}`} className="w-full h-full object-cover" muted />
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/10">
              <Play className="w-3 h-3 fill-current text-[#25F4EE]" />
            </div>
          </button>
        ) : (
          <div className="w-9 h-12 rounded-lg bg-black/40 border border-white/[0.06] flex items-center justify-center text-sm text-slate-600 font-mono">
            -
          </div>
        )}
      </td>

      {/* 2. Product & Hook Title */}
      <td className="py-2 px-3">
        <div className="space-y-0.5 max-w-xs sm:max-w-md">
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
      <td className="py-2 px-3">
        <span className={`inline-flex items-center gap-1.5 py-1 px-2.5 rounded-lg text-xs font-bold border select-none ${currentPhase.color}`}>
          <currentPhase.icon className="w-3 h-3" />
          <span>{currentPhase.label}</span>
        </span>
      </td>

      {/* 4. Caption Preview & Copy (คัดลอกได้เมื่อส่งเข้ามือถือหรือโพสต์แล้ว) */}
      <td className="py-2 px-3">
        {(ang.status === 'mobile_ready' || ang.status === 'posted') ? (
          <button
            onClick={() => onCopyCaption(`${ang.tiktok_caption || ''}\n\n${ang.tiktok_hashtags || ''}`, ang.angle_id)}
            className="text-left py-1 px-2 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.06] text-slate-300 text-xs flex items-center justify-between gap-2 max-w-[180px] cursor-pointer transition-colors"
            title="คลิกเพื่อคัดลอกแคปชัน & แฮชแท็ก"
          >
            <span className="truncate text-sm font-mono">{ang.tiktok_caption || 'คัดลอกแคปชัน'}</span>
            <span className="text-[#25F4EE] flex-shrink-0">
              {copiedAngleId === ang.angle_id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            </span>
          </button>
        ) : (
          <span className="truncate text-sm font-mono text-slate-500 max-w-[180px] block" title={ang.tiktok_caption || ''}>
            {ang.tiktok_caption || '-'}
          </span>
        )}
      </td>

      {/* 5. Direct Action Buttons */}
      <td className="py-2 px-3 text-right">
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => onInspectAngle(ang)}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-slate-400 hover:text-white cursor-pointer"
            title="ดูรายละเอียดจริงเชิงลึก"
          >
            <Info className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => hasVideos && onSendToStudio(ang.parentProduct, ang)}
            disabled={!hasVideos}
            className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-all ${
              hasVideos
                ? 'bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] cursor-pointer'
                : 'bg-white/[0.03] border border-white/[0.06] text-slate-600 cursor-not-allowed opacity-40'
            }`}
            title={hasVideos ? 'ส่งเข้า 1-Click Studio' : 'ยังไม่มีคลิปดิบ (กรุณาแนบคลิปก่อนส่งตัดต่อ)'}
          >
            <Clapperboard className="w-3 h-3" />
            <span>Studio</span>
          </button>

          {(ang.status === 'rendered' || ang.qc_note) && onQcPass && (
            <button
              onClick={() => onQcPass(ang)}
              className="py-1 px-2 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/35 text-[#25F4EE] text-xs font-bold flex items-center gap-1 cursor-pointer transition-all active:scale-95"
              title="รับรอง QC ผ่าน (ล้างป้ายแดงออก)"
            >
              <Check className="w-3 h-3 text-[#25F4EE]" />
              <span>QC ผ่าน</span>
            </button>
          )}

          <button
            onClick={() => onOpenQrModal(ang)}
            className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 cursor-pointer"
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
export default function ContentTrackerHub({ onApplyToStudio, onRefresh, onGoToGallery, onGoToEditor, onGoToFlow }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
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
  const [inspectAngle, setInspectAngle] = useState(null); // Deep-Dive Inspection state
  const colRefs = useRef({});
  const { toastMessage, showToast, hideToast } = useToast();

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
    setLoading(true);
    try {
      const res = await getProducts();
      if (res.products) {
        setProducts(res.products);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProductsData();
  }, [fetchProductsData]);

  const handleAngleStatusChange = useCallback(async (productId, angleId, nextStatus, videoUrl = null, qcNote = null, clearQcNote = false) => {
    try {
      await updateAngleStatus(productId, angleId, nextStatus, videoUrl, null, qcNote, clearQcNote);
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
        } : null);
      }
      showToast('อัปเดตสถานะสำเร็จ');
    } catch (err) {
      showToast('ไม่สามารถอัปเดตสถานะได้: ' + err.message, 'error');
    }
  }, [inspectAngle, showToast]);

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
      resolvedIdx = product.angles.findIndex(a => (a.angle_id && a.angle_id === angle?.angle_id) || a.hook_title === angle?.hook_title);
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
      // Not auto-filling hookBrand/hookModel/hookLabel -- the 3-tier hook
      // banner is manual-only (see EditorShell.jsx).
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
                  className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
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
                    className="py-2.5 px-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0"
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
                    className="py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-[#25F4EE] to-cyan-400 hover:brightness-110 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5 cursor-pointer transition-all shadow-md shadow-[#25F4EE]/20 flex-shrink-0 active:scale-95"
                    title="กดเพื่อรับรอง QC ผ่านทันที (ล้างป้ายแดงออก)"
                  >
                    <Check className="w-3.5 h-3.5 text-slate-950 stroke-[3]" />
                    <span>QC ผ่าน</span>
                  </button>
                )}

                {/* Button 4: Mobile QR */}
                <button
                  onClick={() => {
                    setInspectAngle(null);
                    setQrModalItem(inspectAngle);
                  }}
                  className="py-2.5 px-3.5 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all flex-shrink-0"
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

      {/* ── QC Fail Confirmation Modal ─────────────────────────────────────── */}
      <Modal
        isOpen={!!qcFailTarget}
        onClose={() => { setQcFailTarget(null); setQcFailNote(''); }}
        title="QC ไม่ผ่าน — ส่งตัดใหม่"
        subtitle={qcFailTarget?.hook_title}
        maxWidth="max-w-sm"
      >
        {qcFailTarget && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30">
              <div className="w-10 h-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                <RotateCcw className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <div className="text-sm font-bold text-red-300">คลิปนี้จะถูกส่งกลับไปตัดใหม่</div>
                <div className="text-xs text-slate-400 mt-0.5">สถานะจะเปลี่ยนกลับเป็น "กำลังตัดต่อ" — เปิด Studio ได้ทันที</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300 block">หมายเหตุ QC (เพื่อให้ตัดต่อเห็นว่าต้องแก้อะไร)</label>
              <textarea
                value={qcFailNote}
                onChange={e => setQcFailNote(e.target.value)}
                placeholder="เช่น: เสียงหนักเกิน, ตัดไม่เรียบร้อย, ร้องเรียนไม่ดี…"
                rows={3}
                className="w-full rounded-xl bg-black/40 border border-white/[0.1] text-slate-200 text-xs p-2.5 placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]/50 resize-none font-mono leading-relaxed"
              />
              <div className="text-xs text-slate-500">ถ้าไม่ระบุจะใช้ "QC ไม่ผ่าน" เป็นค่าเริ่มต้น</div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => { setQcFailTarget(null); setQcFailNote(''); }}
                className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-sm font-bold cursor-pointer transition-all"
              >
                ยกเลิก
              </button>
              <button
                onClick={handleQcFailConfirm}
                className="flex-1 py-2.5 px-3 rounded-xl bg-red-500/80 hover:bg-red-500 text-white text-sm font-bold flex items-center justify-center gap-2 cursor-pointer transition-all shadow-lg shadow-red-900/30 active:scale-95"
              >
                <RotateCcw className="w-4 h-4" />
                ยืนยัน — ส่งตัดใหม่
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Video Modal Preview with Direct QC Control Panel */}
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
              className="w-full rounded-2xl bg-black aspect-[9/16] object-contain max-h-[62vh] shadow-2xl border border-white/[0.08]"
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
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleQcPass(previewVideoAngle)}
                    className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 hover:brightness-110 text-slate-950 text-xs font-black flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/25 cursor-pointer active:scale-95 transition-all"
                  >
                    <Check className="w-4 h-4 text-slate-950 stroke-[3]" />
                    <span>ยืนยัน QC ผ่าน (เปลี่ยนเป็นการ์ดสีฟ้า)</span>
                  </button>
                  <button
                    onClick={() => {
                      const ang = previewVideoAngle;
                      setPreviewVideoUrl(null);
                      setPreviewVideoAngle(null);
                      handleQcFail(ang);
                    }}
                    className="py-2.5 px-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-bold flex items-center justify-center gap-1 cursor-pointer transition-all flex-shrink-0"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>ไม่ผ่าน</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* QR Code Modal for Mobile Transfer */}
      <Modal
        isOpen={!!qrModalItem}
        onClose={() => setQrModalItem(null)}
        title="สแกน QR เพื่อส่งคลิปเข้ามือถือ"
        subtitle={qrModalItem?.hook_title}
        maxWidth="max-w-sm"
      >
        {qrModalItem && (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 text-[#25F4EE] flex items-center justify-center mx-auto shadow-md">
              <Smartphone className="w-6 h-6" />
            </div>

            <div className="bg-white p-3 rounded-2xl inline-block shadow-xl">
              <QRCodeSVG value={mobileUrl} size={180} />
            </div>

            {/* Caption Preview & Copy inside Modal */}
            <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-left space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                <span>แคปชัน & แฮชแท็กพร้อมโพสต์:</span>
                <button
                  onClick={() => handleCopyCaption(`${qrModalItem.tiktok_caption || ''}\n\n${qrModalItem.tiktok_hashtags || ''}`, 'modal')}
                  className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  {copiedAngleId === 'modal' ? <><Check className="w-3.5 h-3.5 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3.5 h-3.5" /> คัดลอก</>}
                </button>
              </div>
              <p className="text-xs text-slate-300 line-clamp-3 font-mono leading-relaxed select-all">
                {qrModalItem.tiktok_caption} {qrModalItem.tiktok_hashtags}
              </p>
            </div>

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
          </div>
        )}
      </Modal>

      {/* ══════════════════════════════════════════════════════════
          1. COMPACT METRIC CHIPS RIBBON (TAP TO SWITCH/FILTER)
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-panel p-2 rounded-xl border border-white/[0.08] bg-[#0B0E17]">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 no-scrollbar pr-4">
          {/* Card 0: All */}
          <button
            type="button"
            onClick={() => scrollToPhaseColumn('all')}
            className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 border ${
              activePhase === 'all'
                ? 'bg-[#25F4EE]/20 text-[#25F4EE] border-[#25F4EE]/50 shadow-sm'
                : 'bg-black/40 text-slate-400 border-white/[0.08] hover:text-white hover:border-white/[0.15]'
            }`}
          >
            <span>ทั้งหมด</span>
            <span className="font-mono text-sm px-1.5 py-0.2 rounded-full bg-black/60">{allAnglesList.length}</span>
          </button>

          {/* Cards 1..5 */}
          {PIPELINE_PHASES.map((p) => {
            const count = phaseCounts[p.id] || 0;
            const isActive = activePhase === p.id;
            const Icon = p.icon;

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => scrollToPhaseColumn(isActive && activePhase !== 'all' ? 'all' : p.id)}
                className={`py-1 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 border ${
                  isActive
                    ? `${p.color} ring-1 ring-[#25F4EE]/40 shadow-sm font-bold`
                    : 'bg-black/40 text-slate-400 border-white/[0.08] hover:text-white hover:border-white/[0.15]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{p.short}</span>
                <span className="font-mono text-sm px-1.5 py-0.2 rounded-full bg-black/60 font-bold">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          2. STREAMLINED SEARCH & VIEW CONTROLS (MERGED ROW)
         ══════════════════════════════════════════════════════════ */}
      <div className="glass-card p-2 rounded-xl border border-white/[0.08] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-2">
        {/* Search Box */}
        <div className="relative flex-1 min-w-0">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ค้นหาชื่อสินค้า, สคริปต์, หรือ Hook..."
            className="w-full pl-8 pr-7 py-1.5 rounded-lg bg-[#080B11] border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]/50"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Product Filter Dropdown & View Mode Switcher (Merged Row) */}
        <div className="flex items-center gap-1.5 justify-between md:justify-end flex-shrink-0">
          <select
            value={selectedProductFilter}
            onChange={(e) => setSelectedProductFilter(e.target.value)}
            className="py-1.5 px-2 rounded-lg bg-[#080B11] border border-white/[0.1] text-xs font-bold text-slate-200 focus:outline-none focus:border-[#25F4EE]/50 cursor-pointer max-w-[150px] sm:max-w-[200px] truncate"
          >
            <option value="all">สินค้าทั้งหมด ({products.length})</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} ({(p.angles || []).length})
              </option>
            ))}
          </select>

          {/* Multi-View Switcher */}
          <div className="flex items-center p-0.5 rounded-lg bg-black/60 border border-white/[0.1] flex-shrink-0">
            <button
              type="button"
              onClick={() => handleSwitchViewMode('kanban')}
              className={`py-1 px-2 rounded-md text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                viewMode === 'kanban'
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองบอร์ด (Kanban)"
            >
              <Kanban className="w-3 h-3" />
              <span>บอร์ด</span>
            </button>

            <button
              type="button"
              onClick={() => handleSwitchViewMode('table')}
              className={`py-1 px-2 rounded-md text-xs font-bold flex items-center gap-1 transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="มุมมองตาราง (Table)"
            >
              <Table className="w-3 h-3" />
              <span>ตาราง</span>
            </button>
          </div>
        </div>
      </div>

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
              const phaseAngles = filteredAngles.filter(a => a.status === phase.id);

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
                    <span className="text-sm font-mono font-bold px-1.5 py-0.2 rounded-full bg-black/60 border border-white/[0.08] text-slate-300">
                      {phaseAngles.length}
                    </span>
                  </div>

                  {/* Cards inside column (Vertical Scrollable within column) */}
                  <div className="space-y-2 max-h-[68vh] overflow-y-auto pr-0.5 min-h-[120px]">
                    {phaseAngles.length === 0 ? (
                      <div className="py-8 text-center text-sm text-slate-500 border border-dashed border-white/[0.06] rounded-xl">
                        ไม่มีคลิปในขั้นตอนนี้
                      </div>
                    ) : (
                      phaseAngles.map((ang, idx) => (
                        <KanbanCard
                          key={`${ang.parentProduct?.id}_${ang.angle_id || idx}`}
                          ang={ang}
                          phaseId={phase.id}
                          onSendToStudio={handleSendToStudio}
                          onStatusChange={handleAngleStatusChange}
                          onPreviewVideo={handlePreviewVideo}
                          onOpenQrModal={setQrModalItem}
                          onInspectAngle={setInspectAngle}
                          onCopyCaption={handleCopyCaption}
                          onQcFail={handleQcFail}
                          onQcPass={handleQcPass}
                          copiedAngleId={copiedAngleId}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════
          4. CLEAN HIGH-DENSITY REAL TABLE VIEW
         ══════════════════════════════════════════════════════════ */}
      {viewMode === 'table' && (
        <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden bg-[#070A12] shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[620px]">
              <thead>
                <tr className="border-b border-white/[0.08] bg-black/70 text-slate-400 font-bold text-sm">
                  <th className="py-2.5 px-3 w-14 text-center">วิดีโอ</th>
                  <th className="py-2.5 px-3 min-w-[180px]">สินค้า & มุมขาย (Hook Title)</th>
                  <th className="py-2.5 px-3 w-32">สถานะขั้นตอน</th>
                  <th className="py-2.5 px-3 w-44">แคปชัน TikTok</th>
                  <th className="py-2.5 px-3 text-right w-24">ปุ่มลัด</th>
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
      )}
    </div>
  );
}
