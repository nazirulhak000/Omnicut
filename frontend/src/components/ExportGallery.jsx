import React, { useState, useMemo, useEffect, useCallback, useRef, memo } from 'react';
import {
  Film, Download, Folder, RefreshCw, Trash2,
  AlertTriangle, Check, Play, Search, Filter, ArrowUpDown,
  Smartphone, CheckSquare, Square, Share2, Copy, FileText, QrCode, Sparkles, HardDrive,
  ShieldAlert, XCircle, CheckCircle2, History, FileQuestion, Link2,
  Columns, List, LayoutGrid, Clock, Calendar, Tag, DollarSign, Layers, ChevronDown, ChevronUp, Zap, ShieldCheck,
  Image as ImageIcon, FolderOpen, ExternalLink
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import {
  openFolder, deleteFile, getProducts, linkExportToAngle,
  revealFile, generateCover, markPosted, prepareTiktokAutopost, getExportMediaInfo,
} from '../api';
import { Modal, Toast, Button, Badge, ConfirmModal } from './ui';
import { useDebounce, useToast } from '../hooks';
import RawVaultPanel from './RawVaultPanel';
import CoverStudioModal from './CoverStudioModal';

// The gallery's own QR used to be a degraded copy of ContentTrackerHub's --
// missing pid/aid/hook/hashtags and reading `video.caption`, a key
// /api/exports never returns (it returns `tiktok_caption`). A scanned QR
// landed on a mobile page that could not call updateAngleStatus
// (MobileQuickPostPage.jsx requires both ids) and showed an empty caption.
// One builder now, matching ContentTrackerHub.jsx's URL shape exactly.
function buildQuickPostUrl(mobileBaseUrl, video) {
  const params = new URLSearchParams({
    quick_post: '1',
    pid: video.product_id || '',
    aid: video.angle_id || '',
    video: video.rel_path || video.path || '',
    product: video.product_name || video.name || '',
    hook: video.hook_title || '',
    caption: video.tiktok_caption || '',
    hashtags: video.tiktok_hashtags || '',
  });
  return `${mobileBaseUrl}/?${params.toString()}`;
}

// The 2 spec tiles below used to hardcode "30 FPS - H.264 MP4" and
// "1080x1920 (9:16 FHD)" for every clip -- silently wrong for a `_draft`
// 720p export. Derive both from a real ffprobe result instead
// (GET /api/exports/media-info); the other 2 tiles (Safe Zone, Voice/SFX/BGM
// mix ratio) are legitimate app-wide constants, not per-file data, and stay
// hardcoded on purpose.
function formatCodecSpec(mediaInfo) {
  if (!mediaInfo) return 'กำลังตรวจสอบ...';
  const codec = (mediaInfo.codec_name || '').toLowerCase();
  const codecLabel = codec === 'h264' ? 'H.264' : codec === 'hevc' ? 'H.265/HEVC' : (codec ? codec.toUpperCase() : 'MP4');
  return `${mediaInfo.fps || '-'} FPS • ${codecLabel} MP4`;
}

function formatResolutionSpec(mediaInfo) {
  if (!mediaInfo) return 'กำลังตรวจสอบ...';
  const w = mediaInfo.width;
  const h = mediaInfo.height;
  const longSide = Math.max(w || 0, h || 0);
  const label = longSide >= 1920 ? '9:16 FHD' : longSide >= 1280 ? '9:16 HD' : '9:16';
  return `${w}x${h} (${label})`;
}

// Helper: Format full date & time (e.g. "4 ก.ย. 2026, 18:45:20 น.")
function formatDateTimeFull(str) {
  if (!str) return 'เพิ่งตัดต่อเสร็จ';
  try {
    const d = new Date(str.includes('T') ? str : str.replace(' ', 'T'));
    if (isNaN(d.getTime())) return str;
    return d.toLocaleString('th-TH', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }) + ' น.';
  } catch {
    return str;
  }
}

// Helper: Relative time description (e.g. "5 นาทีที่แล้ว", "เมื่อสักครู่")
function getRelativeTimeDesc(timestamp, dateStr) {
  let ts = timestamp;
  if (!ts && dateStr) {
    try {
      ts = new Date(dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T')).getTime() / 1000;
    } catch {
      ts = null;
    }
  }
  if (!ts) return 'เพิ่งเสร็จ';
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return 'เมื่อสักครู่';
  if (diff < 3600) return `${Math.floor(diff / 60)} นาทีที่แล้ว`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ชม. ที่แล้ว`;
  return `${Math.floor(diff / 86400)} วันที่แล้ว`;
}

// Helper: Format duration in minutes:seconds
function formatDuration(sec) {
  if (!sec || isNaN(sec)) return '--:--';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// Memoized Export Video Item Card
const ExportCard = memo(function ExportCard({
  item,
  isSelected,
  onToggleSelect,
  onOpenDetail,
  onOpenDelete
}) {
  const nameLow = (item.name || '').toLowerCase();
  const isEsseger = nameLow.includes('esseger') || nameLow.includes('สายชาร์จ');
  const isLogitech = nameLow.includes('logitech') || nameLow.includes('wave');

  return (
    <div
      className={`overflow-hidden transition-all duration-200 flex flex-col justify-between group relative rounded-2xl sm:rounded-3xl border glass-card shadow-lg ${
        isSelected
          ? 'border-[#25F4EE] ring-1 ring-[#25F4EE] bg-[#25F4EE]/5'
          : item.is_qc_rejected
          ? 'border-red-500/50 hover:border-red-400 bg-red-950/10 hover:shadow-red-950/40 ring-1 ring-red-500/20'
          : item.is_previous_version
          ? 'opacity-80 hover:opacity-100 border-amber-500/30 hover:border-amber-400/60 bg-amber-950/10 hover:shadow-amber-950/30 ring-1 ring-amber-500/20'
          : item.is_unlinked
          ? 'border-slate-700/60 hover:border-slate-500/60 bg-slate-900/40'
          : 'border-emerald-500/30 hover:border-emerald-400/70 bg-emerald-950/5 hover:shadow-2xl ring-1 ring-emerald-500/20'
      }`}
    >
      {/* Card Top / Video Thumbnail Area */}
      <div>
        {/* Select Checkbox (Top Left) */}
        <button
          onClick={() => onToggleSelect(item.path)}
          className="absolute top-2.5 left-2.5 sm:top-3 sm:left-3 z-20 w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-black/75 backdrop-blur-md flex items-center justify-center border border-white/20 text-white cursor-pointer hover:border-[#25F4EE] shadow-sm transition-transform active:scale-95"
        >
          {isSelected ? <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#25F4EE]" /> : <Square className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-400" />}
        </button>

        {/* Product Tag Badge + Status Badge (Top Right) */}
        <div className="absolute top-2.5 right-2.5 sm:top-3 sm:right-3 z-20 flex items-center gap-1 sm:gap-1.5 flex-wrap justify-end">
          {item.is_qc_rejected ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-red-600/90 text-white font-black text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-red-400/50">
              <ShieldAlert className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>QC ปัดตก</span>
            </span>
          ) : item.is_previous_version ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-amber-600/90 text-white font-bold text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-amber-400/50">
              <History className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>เวอร์ชันเก่า</span>
            </span>
          ) : item.is_unlinked ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-slate-700/90 text-slate-200 font-bold text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-slate-600/50">
              <FileQuestion className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-slate-300" />
              <span>ภายนอก</span>
            </span>
          ) : item.is_latest ? (
            <span className="px-1.5 sm:px-2 py-0.5 rounded-md bg-emerald-600/90 text-white font-black text-[9px] sm:text-[10px] shadow-sm tracking-wider flex items-center gap-1 border border-emerald-400/50">
              <CheckCircle2 className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
              <span>ล่าสุด</span>
            </span>
          ) : null}

          {isLogitech ? (
            <Badge variant="slate" size="xs">Logitech</Badge>
          ) : isEsseger ? (
            <Badge variant="cyan" size="xs">Esseger</Badge>
          ) : null}
        </div>

        {/* Video / Poster Preview (9:16 Vertical) */}
        <div
          onClick={() => onOpenDetail(item)}
          className="bg-black aspect-[9/16] w-full flex items-center justify-center relative overflow-hidden cursor-pointer"
        >
          {item.thumbnail_url ? (
            <img
              src={item.thumbnail_url}
              alt={item.name}
              loading="lazy"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <video
              src={`/api/media/${item.rel_path || item.path}#t=1.0`}
              preload="metadata"
              className="w-full h-full object-cover"
              playsInline
              muted
              loop
              onLoadedMetadata={e => {
                try { e.target.currentTime = 1.0; } catch {}
              }}
              onMouseOver={e => e.target.play().catch(() => {})}
              onMouseOut={e => { e.target.pause(); try { e.target.currentTime = 1.0; } catch {} }}
            />
          )}

          {/* Centered Play Button Overlay */}
          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-all flex flex-col items-center justify-center gap-1.5 sm:gap-2 pointer-events-none">
            {item.is_qc_rejected ? (
              <>
                <div className="w-10 h-10 sm:w-13 sm:h-13 rounded-full bg-gradient-to-tr from-red-600 to-rose-600 text-white flex items-center justify-center shadow-xl shadow-red-600/50 ring-2 ring-red-400 ring-offset-2 ring-offset-black/50 transform group-hover:scale-110 transition-all">
                  <Play className="w-4 h-4 sm:w-5 sm:h-5 fill-current ml-0.5 text-white" />
                </div>
                <div className="px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-red-600/90 backdrop-blur-md text-white font-black text-[9px] sm:text-[11px] shadow-lg border border-red-400/60 tracking-wide flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-white" />
                  <span>QC ไม่ผ่าน</span>
                </div>
                {item.qc_note && (
                  <div className="max-w-[85%] text-center text-[9px] sm:text-[10px] text-red-100 font-mono leading-snug px-1.5 sm:px-2 py-0.5 rounded-md bg-black/70 border border-red-500/40 truncate">
                    {item.qc_note}
                  </div>
                )}
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  ดูรายละเอียด (ตรวจ QC)
                </span>
              </>
            ) : item.is_previous_version ? (
              <>
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-tr from-amber-600 to-orange-500 text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
                  <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4 fill-current ml-0.5 text-white" />
                </div>
                <div className="px-2 py-0.5 rounded-full bg-amber-600/80 backdrop-blur-md text-white font-bold text-[9px] sm:text-[10px] shadow-md border border-amber-400/40 tracking-wide flex items-center gap-1">
                  <History className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" />
                  <span>เวอร์ชันเก่า</span>
                </div>
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด
                </span>
              </>
            ) : (
              <>
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-all">
                  <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4 fill-current ml-0.5 text-white" />
                </div>
                <span className="text-[10px] sm:text-xs font-bold text-white bg-black/80 px-2.5 py-0.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                  คลิกดูรายละเอียด
                </span>
              </>
            )}
          </div>
        </div>

        {/* Video Metadata */}
        <div className="p-2.5 sm:p-4 space-y-1 sm:space-y-1.5 text-left">
          <h4
            onClick={() => onOpenDetail(item)}
            className="text-xs sm:text-sm font-bold text-white truncate cursor-pointer hover:text-[#25F4EE] transition-colors"
            title={item.hook_title || item.name}
          >
            {item.hook_title || item.name}
          </h4>

          {item.product_name && (
            <p className="text-[10px] sm:text-[11px] text-slate-400 truncate" title={item.product_name}>
              {item.product_name}
            </p>
          )}

          <div className="flex items-center justify-between text-[10px] sm:text-xs text-slate-400 font-mono pt-0.5">
            <span className="flex items-center gap-1 text-[#25F4EE] font-bold">
              {item.size_mb} MB
            </span>
            <span className="text-[10px] sm:text-xs text-slate-400">
              {item.modified?.split(' ')?.[0] || item.modified}
            </span>
          </div>
        </div>
      </div>

      {/* Card Action Buttons */}
      <div className="p-2 sm:p-3 pt-0 flex items-center gap-1 sm:gap-1.5 border-t border-white/[0.08] mt-1 sm:mt-2">
        <button
          onClick={() => onOpenDetail(item)}
          className="flex-1 py-1.5 sm:py-2 px-1.5 sm:px-2.5 rounded-lg sm:rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-[11px] sm:text-xs font-bold flex items-center justify-center cursor-pointer transition-colors"
        >
          ดูรายละเอียด
        </button>

        <a
          href={`/api/media/${item.path}`}
          download={item.name}
          className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold transition-colors cursor-pointer flex-shrink-0"
          title="ดาวน์โหลด .MP4"
        >
          <Download className="w-3.5 h-3.5" />
        </a>

        <button
          onClick={() => onOpenDelete(item)}
          className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-bold transition-colors cursor-pointer flex-shrink-0"
          title="ลบวิดีโอ"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════
// 🎬 EXPORT SIDEBAR ITEM (Left Column Playlist in Split View)
// ═══════════════════════════════════════════════════════════════════════
function ExportSidebarItem({ item, isSelected, isActive, onSelect, onToggleCheck }) {
  return (
    <div
      onClick={onSelect}
      className={`p-2.5 rounded-xl border transition-all cursor-pointer text-left group relative active:scale-98 ${
        isActive
          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-md shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/30'
          : 'bg-[#080B11] border-white/[0.06] hover:border-white/[0.18] hover:bg-white/[0.02]'
      }`}
    >
      {isActive && (
        <div className="absolute left-0 top-2 bottom-2 w-1 bg-[#25F4EE] rounded-r-full shadow-sm shadow-[#25F4EE]" />
      )}

      <div className="flex items-start gap-2.5">
        {/* Checkbox */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleCheck(item.path);
          }}
          className="mt-1 w-5 h-5 rounded flex items-center justify-center border border-white/20 hover:border-[#25F4EE] transition-colors flex-shrink-0 cursor-pointer"
        >
          {isSelected ? <Check className="w-3.5 h-3.5 text-[#25F4EE]" /> : <Square className="w-3 h-3 text-slate-500" />}
        </button>

        {/* Mini 9:16 Thumbnail */}
        <div className="w-10 h-16 rounded-lg overflow-hidden bg-black flex-shrink-0 relative border border-white/[0.08]">
          {item.thumbnail_url ? (
            <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <video
              src={`/api/media/${item.rel_path || item.path}#t=1.0`}
              className="w-full h-full object-cover"
              muted
            />
          )}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center justify-between gap-1.5">
            <span className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-200'}`}>
              {item.hook_title || item.name}
            </span>
            {item.is_latest ? (
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex-shrink-0">
                ล่าสุด
              </span>
            ) : item.is_previous_version ? (
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 flex-shrink-0">
                เก่า
              </span>
            ) : item.is_qc_rejected ? (
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-red-500/15 text-red-300 border border-red-500/30 flex-shrink-0">
                QC
              </span>
            ) : null}
          </div>

          <p className="text-[11px] text-slate-400 truncate font-mono">
            {item.name}
          </p>

          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span className="font-mono text-cyan-300">{item.size_mb} MB</span>
            <span>•</span>
            <span>{item.modified?.split(' ')?.[0] || 'เพิ่งสร้าง'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 📱 EXPORT MOBILE PILL (Horizontal Swipeable Tab for iPhone 15 PM)
// ═══════════════════════════════════════════════════════════════════════
function ExportMobilePill({ item, isActive, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex-shrink-0 snap-center px-2.5 py-2 rounded-xl border text-left transition-all cursor-pointer flex items-center gap-2 max-w-[200px] active:scale-95 ${
        isActive
          ? 'bg-[#25F4EE]/15 border-[#25F4EE] shadow-md shadow-[#25F4EE]/20 ring-1 ring-[#25F4EE]/40'
          : 'bg-[#080B11] border-white/[0.08] hover:border-white/[0.2] text-slate-300'
      }`}
    >
      <div className="w-8 h-12 rounded-md overflow-hidden bg-black flex-shrink-0 border border-white/[0.1]">
        {item.thumbnail_url ? (
          <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
        ) : (
          <video src={`/api/media/${item.rel_path || item.path}#t=1.0`} className="w-full h-full object-cover" muted />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
            item.is_latest ? 'bg-emerald-400' : item.is_previous_version ? 'bg-amber-400' : 'bg-slate-400'
          }`} />
          <span className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-300'}`}>
            {item.hook_title || item.name}
          </span>
        </div>
        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
          {item.size_mb} MB
        </div>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 🎬 EXPORT ACTIVE WORKBENCH (Right Column Studio QC Panel in Split View)
// ═══════════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════════
// 🎬 EXPORT ACTIVE WORKBENCH (Studio QC & Deep Insights Panel)
// ═══════════════════════════════════════════════════════════════════════
function ExportActiveWorkbench({
  video,
  onSwapToLatest,
  onOpenLinkModal,
  onCopyCaption,
  copiedCaption,
  mobileBaseUrl,
  onDelete,
  onGenerateCover,
  onRevealFile,
  onMarkPosted,
  onPrepareAutopost
}) {
  const videoRef = useRef(null);
  const [videoDuration, setVideoDuration] = useState(null);
  const [showFullScript, setShowFullScript] = useState(false);
  const [copiedPath, setCopiedPath] = useState(false);
  const [mediaInfo, setMediaInfo] = useState(null);
  const [atSeconds, setAtSeconds] = useState(1.0);
  const [coverResult, setCoverResult] = useState(null);
  const [coverBusy, setCoverBusy] = useState(false);
  const [showCoverStudio, setShowCoverStudio] = useState(false);
  const [revealBusy, setRevealBusy] = useState(false);
  const [postBusy, setPostBusy] = useState(false);
  const [autopostBusy, setAutopostBusy] = useState(false);
  const [showTierInputs, setShowTierInputs] = useState(false);
  const [tierBrand, setTierBrand] = useState('');
  const [tierModel, setTierModel] = useState('');
  const [tierLabel, setTierLabel] = useState('');
  const [autopostEnabled] = useState(() => {
    try {
      return localStorage.getItem('omnicut_tiktok_autopost_enabled') === 'true';
    } catch {
      return false;
    }
  });

  // Reset per-video Post Studio state whenever the selected clip changes --
  // otherwise a cover grabbed for the previous video would linger on screen.
  useEffect(() => {
    setAtSeconds(1.0);
    setCoverResult(null);
    setShowTierInputs(false);
    setTierBrand('');
    setTierModel('');
    setTierLabel('');
  }, [video?.rel_path || video?.path]);

  useEffect(() => {
    if (!video) return;
    let cancelled = false;
    setMediaInfo(null);
    getExportMediaInfo(video.rel_path || video.path)
      .then((info) => { if (!cancelled) setMediaInfo(info); })
      .catch(() => { if (!cancelled) setMediaInfo(null); });
    return () => { cancelled = true; };
  }, [video?.rel_path || video?.path]);

  if (!video) {
    return (
      <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-8 text-center text-slate-400">
        <Film className="w-10 h-10 mx-auto text-slate-600 mb-2" />
        <p className="text-xs">เลือกคลิปจากรายการฝั่งซ้ายเพื่อตรวจ QC และดูรายละเอียด</p>
      </div>
    );
  }

  const handleCopyPath = () => {
    const p = video.rel_path || video.path;
    navigator.clipboard.writeText(p);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleScrub = (e) => {
    const v = parseFloat(e.target.value);
    setAtSeconds(v);
    if (videoRef.current) videoRef.current.currentTime = v;
  };

  const handleGenerateCoverClick = async () => {
    setCoverBusy(true);
    const res = await onGenerateCover(video, atSeconds, { brand: tierBrand, model: tierModel, label: tierLabel });
    if (res) setCoverResult(res);
    setCoverBusy(false);
  };

  const handleRevealClick = async () => {
    setRevealBusy(true);
    await onRevealFile(video);
    setRevealBusy(false);
  };

  const handleMarkPostedClick = async () => {
    setPostBusy(true);
    await onMarkPosted(video);
    setPostBusy(false);
  };

  const handlePrepareAutopostClick = async () => {
    setAutopostBusy(true);
    await onPrepareAutopost(video, coverResult?.cover_path || null);
    setAutopostBusy(false);
  };

  const scriptLines = Array.isArray(video.script_lines) ? video.script_lines : [];
  const renderedTime = video.modified_time || video.modified;
  const relativeTime = getRelativeTimeDesc(video.timestamp, renderedTime);

  return (
    <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-3.5 sm:p-5 shadow-xl space-y-4 animate-fadeIn">
      {/* 1. Header with title & badges */}
      <div className="flex flex-col xs:flex-row xs:items-center justify-between gap-2 pb-3 border-b border-white/[0.08]">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-[#25F4EE]" />
              <span>พรีวิว & ตรวจ QC วิดีโอ</span>
            </span>
            {video.is_latest && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                เวอร์ชันล่าสุด (พร้อมโพสต์)
              </span>
            )}
            {video.is_previous_version && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                เวอร์ชันก่อนหน้า
              </span>
            )}
            {video.is_qc_rejected && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/15 text-red-300 border border-red-500/30">
                QC ปัดตก
              </span>
            )}
          </div>
          <h2 className="text-sm sm:text-base font-bold text-white font-kanit truncate mt-1">
            {video.hook_title || video.name}
          </h2>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono mt-0.5 truncate">
            {video.product_name && (
              <span className="text-[#25F4EE] font-bold">{video.product_name}</span>
            )}
            {video.angle_name && (
              <>
                <span>•</span>
                <span className="text-slate-300">{video.angle_name}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 2. Side-by-side layout: Video Player + Info */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
        {/* Left: 9:16 Video Player Preview (No autoPlay to prevent echo) */}
        <div className="md:col-span-5 w-full max-w-[260px] sm:max-w-[290px] aspect-[9/16] mx-auto rounded-2xl overflow-hidden bg-black border border-white/[0.12] shadow-2xl relative flex items-center justify-center ring-1 ring-white/[0.05]">
          <video
            ref={videoRef}
            key={video.rel_path || video.path}
            src={`/api/media/${video.rel_path || video.path}`}
            controls
            playsInline
            preload="metadata"
            onLoadedMetadata={(e) => setVideoDuration(e.target.duration)}
            className="w-full h-full object-contain"
          />
        </div>

        {/* Right: Metadata, Specs, Marketing, Captions, QR */}
        <div className="md:col-span-7 space-y-3">
          {/* Version/QC Warning Banners */}
          {video.is_previous_version && (
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-start gap-2.5">
                <History className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-[11px] text-amber-300 font-kanit">
                  <span className="font-bold block">เวอร์ชันก่อนหน้า (มีเวอร์ชันใหม่กว่าแทนที่แล้ว)</span>
                  {video.latest_video_name && (
                    <span className="text-amber-200/80 font-mono text-[10px] block truncate">
                      ล่าสุด: {video.latest_video_name}
                    </span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSwapToLatest(video)}
                className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-bold transition-all cursor-pointer flex-shrink-0 active:scale-95"
              >
                ดูตัวล่าสุด
              </button>
            </div>
          )}

          {video.is_unlinked && (
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <div className="flex items-start gap-2.5">
                <FileQuestion className="w-4 h-4 text-slate-300 flex-shrink-0 mt-0.5" />
                <div className="text-[11px] text-slate-300 font-kanit">
                  <span className="font-bold block">คลิปภายนอก (ยังไม่ได้ผูกกับสคริปต์สินค้า)</span>
                  <span className="text-slate-400 text-[10px] block">สามารถผูกเพื่อดึงแคปชันและข้อมูลสินค้าได้</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onOpenLinkModal(video)}
                className="px-2.5 py-1 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 text-[#25F4EE] text-xs font-bold transition-all cursor-pointer flex-shrink-0 active:scale-95"
              >
                ผูกกับสคริปต์
              </button>
            </div>
          )}

          {/* 4 Deep Technical & Generation Spec Cards (2x2 Grid) */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* Box 1: เวลาที่เจนเสร็จ */}
            <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
              <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                <Clock className="w-3 h-3 text-[#25F4EE]" />
                <span>เวลาที่ตัดต่อเสร็จ</span>
              </div>
              <div className="font-mono text-white text-[11px] font-bold truncate">
                {formatDateTimeFull(renderedTime)}
              </div>
              <div className="text-[10px] text-[#25F4EE] font-kanit">
                {relativeTime}
              </div>
            </div>

            {/* Box 2: ความยาวคลิป & FPS */}
            <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
              <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                <Film className="w-3 h-3 text-emerald-400" />
                <span>ความยาว & เฟรมเรต</span>
              </div>
              <div className="font-mono text-emerald-300 text-[11px] font-bold">
                {formatDuration(videoDuration)} นาที
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                {formatCodecSpec(mediaInfo)}
              </div>
            </div>

            {/* Box 3: ขนาด & สเปกหน้าจอ */}
            <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
              <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                <HardDrive className="w-3 h-3 text-cyan-400" />
                <span>ขนาดไฟล์ & สัดส่วน</span>
              </div>
              <div className="font-mono text-cyan-300 text-[11px] font-bold">
                {video.size_mb} MB
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                {formatResolutionSpec(mediaInfo)}
              </div>
            </div>

            {/* Box 4: Safe Zone & ระดับเสียง */}
            <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
              <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                <ShieldCheck className="w-3 h-3 text-purple-400" />
                <span>Safe Zone & อัตราเสียง</span>
              </div>
              <div className="font-mono text-purple-300 text-[11px] font-bold">
                Safe Zone ล่าง 420px
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                Voice 100% / SFX 28% / BGM 12%
              </div>
            </div>
          </div>

          {/* Product & Marketing Context Card */}
          {(video.product_name || video.angle_name || video.price_deal || video.key_features) && (
            <div className="p-3 rounded-xl bg-gradient-to-br from-white/[0.04] to-black/40 border border-white/[0.08] space-y-2">
              <div className="text-[11px] font-bold text-slate-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5 font-kanit">
                  <Tag className="w-3.5 h-3.5 text-[#FE2C55]" />
                  <span>ข้อมูลสินค้าและแคมเปญ</span>
                </span>
                {video.price_deal && (
                  <span className="px-2 py-0.5 rounded-full bg-[#FE2C55]/15 text-[#FE2C55] font-bold text-[10px] border border-[#FE2C55]/30">
                    {video.price_deal}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-kanit">
                <div>
                  <span className="text-slate-500 block text-[10px]">สินค้า:</span>
                  <span className="text-white font-medium truncate block">{video.product_name || '-'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">มุมมองรีวิว (Angle):</span>
                  <span className="text-slate-200 font-medium truncate block">{video.angle_name || '-'}</span>
                </div>
                {video.ad_tone && (
                  <div className="col-span-2">
                    <span className="text-slate-500 block text-[10px]">โทนเสียงพากย์:</span>
                    <span className="text-slate-300 text-[11px]">{video.ad_tone}</span>
                  </div>
                )}
                {video.key_features && (
                  <div className="col-span-2">
                    <span className="text-slate-500 block text-[10px]">จุดขายสินค้า:</span>
                    <span className="text-slate-300 text-[11px] line-clamp-2">{video.key_features}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Script Breakdown Accordion */}
          {scriptLines.length > 0 && (
            <div className="rounded-xl border border-white/[0.08] bg-black/40 overflow-hidden">
              <button
                type="button"
                onClick={() => setShowFullScript(!showFullScript)}
                className="w-full p-2.5 flex items-center justify-between text-xs font-bold text-slate-300 hover:text-white transition-colors cursor-pointer"
              >
                <span className="flex items-center gap-1.5 font-kanit">
                  <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>บทพูดสคริปต์ในคลิป ({scriptLines.length} ท่อน • J-Cut)</span>
                </span>
                {showFullScript ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>

              {showFullScript && (
                <div className="p-3 border-t border-white/[0.06] space-y-2 bg-black/60 max-h-48 overflow-y-auto no-scrollbar font-mono text-xs">
                  {scriptLines.map((line, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <span className="w-5 h-5 rounded bg-[#25F4EE]/10 text-[#25F4EE] flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <p className="text-slate-300 leading-relaxed text-[11px]">
                        {typeof line === 'string' ? line : line.text || line.dialogue || JSON.stringify(line)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Caption & Hashtag Box */}
          <div className="p-3 rounded-xl bg-black/50 border border-white/[0.08] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 font-kanit">
                <FileText className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>แคปชัน & แฮชแท็กสำหรับโพสต์</span>
              </span>
              {video.tiktok_caption ? (
                <button
                  type="button"
                  onClick={() => onCopyCaption(`${video.tiktok_caption}\n\n${video.tiktok_hashtags || ''}`)}
                  className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[#25F4EE] hover:text-white text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer active:scale-95"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copiedCaption ? 'คัดลอกแล้ว!' : 'คัดลอก'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpenLinkModal?.(video)}
                  className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <AlertTriangle className="w-3 h-3" />
                  <span>ผูกกับสินค้าก่อน</span>
                </button>
              )}
            </div>
            {video.tiktok_caption ? (
              <p className="text-xs text-slate-300 bg-black/40 p-2.5 rounded-lg border border-white/[0.04] select-all leading-relaxed font-mono line-clamp-3">
                {video.tiktok_caption}&nbsp;
                {video.tiktok_hashtags || ''}
              </p>
            ) : (
              <p className="text-xs text-amber-400/90 bg-amber-950/20 p-2.5 rounded-lg border border-amber-500/20">
                ⚠ คลิปนี้ยังไม่ได้ผูกกับ Angle สินค้า — ยังไม่มีแคปชันจริงให้คัดลอก
                (เดิมจะเผลอคัดลอกข้อความตัวอย่างไปโพสต์แทน)
              </p>
            )}
          </div>

          {/* Post Studio: pick a cover frame (fixes the .webp TikTok rejects) */}
          {!video.is_posted && (
            <div className="p-3 rounded-xl bg-black/50 border border-white/[0.08] space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 font-kanit">
                  <ImageIcon className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>ปกโพสต์ (Cover)</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowTierInputs(!showTierInputs)}
                  className="text-[10px] text-slate-500 hover:text-slate-300 font-kanit cursor-pointer"
                >
                  {showTierInputs ? 'ซ่อนช่องแต่งข้อความ' : 'ใส่ข้อความบนปก (ไม่บังคับ)'}
                </button>
              </div>

              {showTierInputs && (
                <div className="grid grid-cols-3 gap-1.5">
                  <input
                    value={tierBrand}
                    onChange={(e) => setTierBrand(e.target.value)}
                    placeholder="แบรนด์"
                    className="min-w-0 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.08] text-[11px] text-white placeholder:text-slate-600 focus:outline-none focus:border-[#25F4EE]/40"
                  />
                  <input
                    value={tierModel}
                    onChange={(e) => setTierModel(e.target.value)}
                    placeholder="รุ่น/หัวข้อ"
                    className="min-w-0 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.08] text-[11px] text-white placeholder:text-slate-600 focus:outline-none focus:border-[#25F4EE]/40"
                  />
                  <input
                    value={tierLabel}
                    onChange={(e) => setTierLabel(e.target.value)}
                    placeholder="ป้ายท้าย"
                    className="min-w-0 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.08] text-[11px] text-white placeholder:text-slate-600 focus:outline-none focus:border-[#25F4EE]/40"
                  />
                </div>
              )}

              <div className="flex gap-3 items-center">
                <div className="w-14 aspect-[9/16] rounded-lg overflow-hidden bg-black border border-white/[0.1] flex-shrink-0">
                  {coverResult ? (
                    <img src={coverResult.media_url} className="w-full h-full object-cover" alt="ตัวอย่างปก" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-600">
                      <ImageIcon className="w-4 h-4" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0 space-y-1">
                  <input
                    type="range"
                    min={0}
                    max={Math.max(videoDuration || 1, 0.1)}
                    step={0.1}
                    value={Math.min(atSeconds, videoDuration || atSeconds)}
                    onChange={handleScrub}
                    className="w-full accent-[#25F4EE] cursor-pointer"
                  />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] text-slate-400 font-mono">วินาทีที่ {atSeconds.toFixed(1)}s</span>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => setShowCoverStudio(true)}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-[11px] font-bold cursor-pointer active:scale-95 transition-all flex items-center gap-1"
                        title="เปิดสตูดิโอสร้างปกคลิป 9:16 แบบมืออาชีพ (Auto Highlight Crop + AI Hook + 3D Badge)"
                      >
                        <ImageIcon className="w-3.5 h-3.5" />
                        <span>สตูดิโอทำปก 9:16</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleGenerateCoverClick}
                        disabled={coverBusy}
                        className="px-2.5 py-1 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 text-[#25F4EE] text-[11px] font-bold cursor-pointer active:scale-95 disabled:opacity-50 disabled:cursor-wait transition-all"
                      >
                        {coverBusy ? 'กำลังสร้าง...' : coverResult ? 'สร้างใหม่' : 'สร้างปก'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {coverResult && (
                <p className="text-[10px] text-emerald-300/90 bg-emerald-950/20 px-2.5 py-1.5 rounded-lg border border-emerald-500/20">
                  บันทึกแล้วที่ {coverResult.cover_path} — ลากไฟล์นี้วางเป็นปกตอนอัพโหลด (ไฟล์ .jpg, TikTok รับ)
                </p>
              )}
            </div>
          )}

          {/* File Path and QR Transfer */}
          <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] flex items-center justify-between gap-3">
            <div className="space-y-1 min-w-0 flex-1">
              <div className="text-xs font-bold text-white flex items-center gap-1.5 font-kanit">
                <Smartphone className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>สแกน QR โหลดคลิปเข้ามือถือ</span>
              </div>
              <p className="text-[10px] text-slate-400">เปิดกล้องสแกนเพื่อโหลด MP4 ลงเครื่องทันที</p>
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleCopyPath}
                  className="px-2 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white text-[10px] font-mono flex items-center gap-1 transition-all cursor-pointer"
                  title="คัดลอก Path ไฟล์"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copiedPath ? 'คัดลอก Path แล้ว' : 'คัดลอกที่อยู่ไฟล์'}</span>
                </button>
              </div>
            </div>
            <div className="p-1.5 bg-white rounded-xl shadow-lg flex-shrink-0" title="สแกนเพื่อเปิดตัวช่วยโพสต์ Quick Post บนมือถือ">
              <QRCodeSVG
                value={buildQuickPostUrl(mobileBaseUrl, video)}
                size={68}
                level="M"
              />
            </div>
          </div>

          {/* Bottom Action Buttons */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-2 border-t border-white/[0.08]">
            <a
              href={`/api/media/${video.rel_path || video.path}`}
              download={video.name}
              className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg cursor-pointer active:scale-95 transition-all text-center"
            >
              <Download className="w-4 h-4" />
              <span>ดาวน์โหลด MP4</span>
            </a>
            <button
              type="button"
              onClick={() => onDelete(video)}
              className="py-2.5 px-3.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all"
            >
              <Trash2 className="w-4 h-4" />
              <span>ลบ</span>
            </button>
          </div>

          {/* Post Studio: reveal-in-Explorer -> drag into TikTok Studio -> mark posted */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <button
              type="button"
              onClick={handleRevealClick}
              disabled={revealBusy}
              className="flex-1 py-2 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
            >
              <Folder className="w-3.5 h-3.5" />
              <span>เปิดไฟล์ใน Explorer</span>
            </button>
            <a
              href="https://www.tiktok.com/tiktokstudio/upload"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 py-2 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all text-center"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>เปิด TikTok Studio</span>
            </a>
            {video.is_posted ? (
              <span className="flex-1 py-2 px-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-bold flex items-center justify-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>โพสต์แล้ว</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={handleMarkPostedClick}
                disabled={postBusy}
                className="flex-1 py-2 px-3 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 text-emerald-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{postBusy ? 'กำลังมาร์ค...' : 'มาร์คว่าโพสต์แล้ว'}</span>
              </button>
            )}
          </div>

          {/* Round POST-2: experimental auto-post, off unless enabled in Settings */}
          {autopostEnabled && !video.is_posted && (
            <button
              type="button"
              onClick={handlePrepareAutopostClick}
              disabled={autopostBusy}
              className="w-full py-2 px-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
              title="ต้องติดตั้ง tiktok_autopost_extension/ และเปิดแท็บ TikTok Studio ที่ล็อกอินไว้ก่อน"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{autopostBusy ? 'กำลังเตรียม...' : 'โพสต์ TikTok อัตโนมัติ (ทดลอง)'}</span>
            </button>
          )}
        </div>
      </div>

      {/* 9:16 Cover Studio Modal */}
      <CoverStudioModal
        isOpen={showCoverStudio}
        onClose={() => setShowCoverStudio(false)}
        videoItem={video}
        onCoverSaved={(res) => {
          setCoverResult(res);
        }}
      />
    </div>
  );
}

export default function ExportGallery({ exportsList, onRefresh, initialHighlightVideo, onClearHighlightVideo, status }) {
  const [activeMediaTab, setActiveMediaTab] = useState('exports');
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('omnicut_export_gallery_view_mode') || 'grid';
    } catch {
      return 'grid';
    }
  }); // 'grid' (default) | 'split'

  useEffect(() => {
    try {
      localStorage.setItem('omnicut_export_gallery_view_mode', viewMode);
    } catch {}
  }, [viewMode]);
  const [activeVideoPath, setActiveVideoPath] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [selectedProductFilter, setSelectedProductFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'latest' | 'previous' | 'unlinked' | 'qc_rejected'
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'oldest' | 'size_desc' | 'name'
  const [selectedDetailVideo, setSelectedDetailVideo] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [showBatchDeleteModal, setShowBatchDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { toastMessage, toastType, showToast, hideToast } = useToast();
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [copiedCaption, setCopiedCaption] = useState(false);

  // Link to script/product modal state
  const [linkingVideo, setLinkingVideo] = useState(null);
  const [availableProducts, setAvailableProducts] = useState([]);
  const [selectedLinkProductId, setSelectedLinkProductId] = useState('');
  const [selectedLinkAngleId, setSelectedLinkAngleId] = useState('');
  const [isLinking, setIsLinking] = useState(false);
  const [modalDuration, setModalDuration] = useState(null);
  const [modalShowScript, setModalShowScript] = useState(false);
  const [modalCopiedPath, setModalCopiedPath] = useState(false);
  const [modalMediaInfo, setModalMediaInfo] = useState(null);

  useEffect(() => {
    setModalDuration(null);
    setModalShowScript(false);
    setModalCopiedPath(false);
    setModalMediaInfo(null);
    if (!selectedDetailVideo) return;
    let cancelled = false;
    getExportMediaInfo(selectedDetailVideo.rel_path || selectedDetailVideo.path)
      .then((info) => { if (!cancelled) setModalMediaInfo(info); })
      .catch(() => { if (!cancelled) setModalMediaInfo(null); });
    return () => { cancelled = true; };
  }, [selectedDetailVideo]);

  const handleSwapToLatest = useCallback((currentVideo) => {
    if (!currentVideo || !exportsList) return;
    const latest = exportsList.find(v => {
      if (currentVideo.latest_video_name && v.name === currentVideo.latest_video_name) return true;
      if (currentVideo.latest_video_path && (v.path === currentVideo.latest_video_path || v.rel_path === currentVideo.latest_video_rel)) return true;
      if (currentVideo.product_id && currentVideo.angle_id && v.product_id === currentVideo.product_id && v.angle_id === currentVideo.angle_id && v.is_latest) return true;
      if (currentVideo.project_name && v.project_name === currentVideo.project_name && v.is_latest) return true;
      return false;
    });
    if (latest) {
      setSelectedDetailVideo(latest);
      showToast(`สลับไปยังเวอร์ชันล่าสุด: ${latest.hook_title || latest.name}`);
    } else {
      showToast('ไม่พบไฟล์เวอร์ชันล่าสุดในรายการ หรืออาจถูกลบไปแล้ว', 'warning');
    }
  }, [exportsList, showToast]);

  const handleOpenLinkModal = useCallback(async (video) => {
    setLinkingVideo(video);
    try {
      const res = await getProducts();
      const prods = Array.isArray(res) ? res : (res?.products || []);
      setAvailableProducts(prods);
      if (prods.length > 0) {
        setSelectedLinkProductId(prods[0].id);
        if (prods[0].angles?.length > 0) {
          setSelectedLinkAngleId(prods[0].angles[0].angle_id);
        } else {
          setSelectedLinkAngleId('');
        }
      }
    } catch (err) {
      showToast('ไม่สามารถโหลดรายชื่อสินค้าได้: ' + err.message, 'error');
    }
  }, [showToast]);

  const handleLinkProductChange = useCallback((e) => {
    const pid = e.target.value;
    setSelectedLinkProductId(pid);
    const prod = availableProducts.find(p => p.id === pid);
    if (prod?.angles?.length > 0) {
      setSelectedLinkAngleId(prod.angles[0].angle_id);
    } else {
      setSelectedLinkAngleId('');
    }
  }, [availableProducts]);

  const selectedProductAngles = useMemo(() => {
    if (!selectedLinkProductId || !availableProducts) return [];
    const prod = availableProducts.find(p => p.id === selectedLinkProductId);
    return prod?.angles || [];
  }, [selectedLinkProductId, availableProducts]);

  const handleConfirmLink = useCallback(async () => {
    if (!linkingVideo || !selectedLinkProductId || !selectedLinkAngleId) {
      showToast('กรุณาเลือกสินค้าและมุมสคริปต์ที่ต้องการผูก', 'error');
      return;
    }
    setIsLinking(true);
    try {
      await linkExportToAngle(linkingVideo.path, selectedLinkProductId, selectedLinkAngleId);
      showToast('ผูกคลิปกับสคริปต์เรียบร้อยแล้ว');
      setLinkingVideo(null);
      if (selectedDetailVideo?.path === linkingVideo.path) {
        setSelectedDetailVideo(null);
      }
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('ผูกคลิปไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsLinking(false);
    }
  }, [linkingVideo, selectedLinkProductId, selectedLinkAngleId, selectedDetailVideo, onRefresh, showToast]);

  // Auto-open video detail modal if user navigated from a completed render task
  useEffect(() => {
    if (!initialHighlightVideo || !exportsList || exportsList.length === 0) return;
    const targetStr = String(initialHighlightVideo).toLowerCase().trim();
    const matched = exportsList.find((item) => {
      const name = (item.name || '').toLowerCase();
      const path = (item.path || '').toLowerCase();
      const relPath = (item.rel_path || '').toLowerCase();
      const prodId = (item.product_id || '').toLowerCase();
      return name.includes(targetStr) || targetStr.includes(name) ||
             path.includes(targetStr) || relPath.includes(targetStr) ||
             (prodId && targetStr.includes(prodId));
    });

    if (matched) {
      setActiveVideoPath(matched.path);
      setSelectedDetailVideo(matched);
      onClearHighlightVideo?.();
    } else if (exportsList.length > 0) {
      // Fallback: pick the latest rendered video if name slightly varied
      setActiveVideoPath(exportsList[0].path);
      setSelectedDetailVideo(exportsList[0]);
      onClearHighlightVideo?.();
    }
  }, [initialHighlightVideo, exportsList, onClearHighlightVideo]);

  const handleOpenExportsFolder = useCallback(() => {
    openFolder('exports');
  }, []);

  const handleCopyCaption = useCallback((text) => {
    navigator.clipboard.writeText(text);
    setCopiedCaption(true);
    showToast('คัดลอกแคปชันเรียบร้อยแล้ว');
    setTimeout(() => setCopiedCaption(false), 2000);
  }, [showToast]);

  // Round POST-1.3: Post Studio actions -- cover grab, reveal-in-Explorer,
  // and closing the Ready_to_post -> Posted lifecycle from inside the panel.
  const handleGenerateCover = useCallback(async (video, atSeconds, tiers) => {
    try {
      const res = await generateCover(
        video.rel_path || video.path, atSeconds,
        tiers?.brand || '', tiers?.model || '', tiers?.label || '',
      );
      showToast('สร้างปกเรียบร้อยแล้ว — ลากไฟล์นี้ (05_Covers_Thumbnails) ไปวางตอนอัพโหลด');
      return res;
    } catch (err) {
      showToast('สร้างปกไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
      return null;
    }
  }, [showToast]);

  const handleRevealFile = useCallback(async (video) => {
    try {
      await revealFile(video.rel_path || video.path);
    } catch (err) {
      showToast('เปิด Explorer ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    }
  }, [showToast]);

  const handleMarkPosted = useCallback(async (video) => {
    try {
      await markPosted(video.rel_path || video.path, video.product_id || null, video.angle_id || null);
      showToast(`มาร์ค "${video.hook_title || video.name}" ว่าโพสต์แล้ว — ย้ายไฟล์ไป Posted/ แล้ว`);
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('มาร์คว่าโพสต์แล้วไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    }
  }, [showToast, onRefresh]);

  const handlePrepareAutopost = useCallback(async (video, coverPath) => {
    try {
      const caption = video.tiktok_caption || video.caption || video.hook_title || '';
      const hashtags = video.tiktok_hashtags || (video.product_name ? `#${video.product_name.replace(/\s+/g, '')} #รีวิวของดี #พิกัดในตะกร้า` : '#รีวิวของดี #พิกัดในตะกร้า');
      await prepareTiktokAutopost(
        video.rel_path || video.path,
        coverPath || null,
        caption,
        hashtags,
        video.product_id || null,
        video.angle_id || null,
        video.tiktok_product_id || null,
      );
      showToast('เตรียมข้อมูลคลิปเข้า Extension สำเร็จ! ให้เปิด Extension บนแท็บ TikTok เพื่อเริ่มเติมข้อมูล');
      window.open('https://www.tiktok.com/tiktokstudio/upload', '_blank');
    } catch (err) {
      showToast('เตรียมคลิปไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    }
  }, [showToast]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteFile(deleteTarget.path);
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อยแล้ว`);
      setDeleteTarget(null);
      if (selectedDetailVideo?.path === deleteTarget.path) setSelectedDetailVideo(null);
      if (activeVideoPath === deleteTarget.path) setActiveVideoPath(null);
      setSelectedVideos(prev => prev.filter(p => p !== deleteTarget.path));
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, selectedDetailVideo, activeVideoPath, onRefresh, showToast]);

  const confirmBatchDelete = useCallback(async () => {
    if (selectedVideos.length === 0) return;

    setDeleting(true);
    try {
      for (const p of selectedVideos) {
        try {
          await deleteFile(p);
        } catch (e) {
          console.error(e);
        }
      }
      showToast(`ลบวิดีโอ ${selectedVideos.length} คลิปเรียบร้อยแล้ว`);
      setSelectedVideos([]);
      setShowBatchDeleteModal(false);
      setActiveVideoPath(null);
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast('เกิดข้อผิดพลาดในการลบไฟล์: ' + err.message, 'error');
    } finally {
      setDeleting(false);
    }
  }, [selectedVideos, onRefresh, showToast]);

  const handleBatchDelete = useCallback(() => {
    if (selectedVideos.length === 0) return;
    setShowBatchDeleteModal(true);
  }, [selectedVideos]);

  const toggleSelectVideo = useCallback((path) => {
    setSelectedVideos(prev =>
      prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
    );
  }, []);

  // Compute Total Storage with useMemo
  const totalMB = useMemo(() => {
    if (!exportsList || exportsList.length === 0) return '0.0';
    const sum = exportsList.reduce((acc, curr) => acc + (parseFloat(curr.size_mb) || 0), 0);
    return sum.toFixed(1);
  }, [exportsList]);

  // Extract unique product tags from filenames with useMemo
  const productTags = useMemo(() => {
    if (!exportsList) return [];
    const tags = new Set();
    exportsList.forEach(v => {
      if (v.product_name) tags.add(v.product_name);
      else {
        const nameLow = v.name.toLowerCase();
        if (nameLow.includes('logitech') || nameLow.includes('wave')) tags.add('Logitech Wave Keys');
        else if (nameLow.includes('esseger') || nameLow.includes('สายชาร์จ')) tags.add('Esseger สายชาร์จ 66W');
        else tags.add('คลิปอื่นๆ');
      }
    });
    return Array.from(tags);
  }, [exportsList]);

  // Filter & Sort with useMemo and Debounced Search
  const filteredExports = useMemo(() => {
    if (!exportsList) return [];
    const q = (debouncedSearch || '').toLowerCase().trim();

    let list = exportsList.filter(item => {
      const matchesSearch = !q ||
        item.name.toLowerCase().includes(q) ||
        item.hook_title?.toLowerCase().includes(q) ||
        item.product_name?.toLowerCase().includes(q);

      let matchesProduct = true;
      if (selectedProductFilter !== 'all') {
        matchesProduct = item.product_name === selectedProductFilter ||
          (selectedProductFilter.includes('Logitech') && item.name.toLowerCase().includes('logitech')) ||
          (selectedProductFilter.includes('Esseger') && item.name.toLowerCase().includes('esseger'));
      }

      let matchesStatus = true;
      if (statusFilter === 'latest')      matchesStatus = !!item.is_latest;
      if (statusFilter === 'previous')    matchesStatus = !!item.is_previous_version;
      if (statusFilter === 'unlinked')    matchesStatus = !!item.is_unlinked;
      if (statusFilter === 'qc_rejected') matchesStatus = !!item.is_qc_rejected;

      return matchesSearch && matchesProduct && matchesStatus;
    });

    // Sorting
    list = [...list].sort((a, b) => {
      if (sortBy === 'newest') return (b.modified_raw || 0) - (a.modified_raw || 0);
      if (sortBy === 'oldest') return (a.modified_raw || 0) - (b.modified_raw || 0);
      if (sortBy === 'size_desc') return (parseFloat(b.size_mb) || 0) - (parseFloat(a.size_mb) || 0);
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      return 0;
    });

    return list;
  }, [exportsList, debouncedSearch, selectedProductFilter, statusFilter, sortBy]);

  // Active Video computed for Split Studio view
  const activeVideo = useMemo(() => {
    if (activeVideoPath) {
      const found = filteredExports.find(v => v.path === activeVideoPath);
      if (found) return found;
    }
    return filteredExports[0] || null;
  }, [activeVideoPath, filteredExports]);

  // Quick counts for filter chips
  const counts = useMemo(() => {
    if (!exportsList) return { all: 0, latest: 0, previous: 0, unlinked: 0, qc_rejected: 0 };
    return {
      all:         exportsList.length,
      latest:      exportsList.filter(v => !!v.is_latest).length,
      previous:    exportsList.filter(v => !!v.is_previous_version).length,
      unlinked:    exportsList.filter(v => !!v.is_unlinked).length,
      qc_rejected: exportsList.filter(v => !!v.is_qc_rejected).length,
    };
  }, [exportsList]);

  const toggleSelectAll = useCallback(() => {
    if (selectedVideos.length === filteredExports.length) {
      setSelectedVideos([]);
    } else {
      setSelectedVideos(filteredExports.map(v => v.path));
    }
  }, [selectedVideos.length, filteredExports]);

  // status.mobile_url (from /api/status) survives a production build served
  // from a different port than the Vite dev server's 5173; ContentTrackerHub
  // already does the same fallback chain.
  const mobileBaseUrl = status?.mobile_url || (typeof window !== 'undefined' ? `http://${window.location.hostname}:5173` : '');

  return (
    <div className="space-y-4 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} onClose={hideToast} />

      {/* ── Unified Media Center & Command Bar ── */}
      <div className="rounded-2xl sm:rounded-3xl border border-white/[0.08] bg-[#0B0F19]/90 backdrop-blur-xl p-3 sm:p-5 shadow-2xl relative overflow-hidden space-y-3 sm:space-y-4">
        {/* Ambient Glow Aura */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#FE2C55]/10 via-[#25F4EE]/5 to-transparent rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Row 1: Tab Switcher + Stats Badge + View Mode & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 relative z-10">
          {/* Media Switcher Tabs */}
          <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-black/40 border border-white/[0.06] w-full md:w-auto">
            <button
              type="button"
              onClick={() => setActiveMediaTab('exports')}
              className={`flex-1 md:flex-initial px-3.5 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                activeMediaTab === 'exports'
                  ? 'bg-[#FE2C55]/20 text-[#FE2C55] border border-[#FE2C55]/40 shadow-md shadow-[#FE2C55]/10'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>คลิปตัดเสร็จ ({exportsList?.length || 0})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveMediaTab('raw_vault')}
              className={`flex-1 md:flex-initial px-3.5 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                activeMediaTab === 'raw_vault'
                  ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-md shadow-[#25F4EE]/10'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Film className="w-4 h-4" />
              <span>คลิปดิบ (Raw Vault)</span>
            </button>
          </div>

          {/* Quick Metrics & Studio Controls (Exports Tab Only) */}
          {activeMediaTab === 'exports' && (
            <div className="flex flex-wrap items-center justify-between md:justify-end gap-2 w-full md:w-auto">
              {/* Metrics Pill */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs font-mono text-slate-300">
                <span className="text-white font-bold">{filteredExports.length}</span> คลิป
                <span className="text-slate-600">•</span>
                <span className="text-[#25F4EE] font-bold">{totalMB}</span> MB
                <span className="text-slate-600">•</span>
                <span className="text-emerald-400 font-bold">9:16 FHD</span>
              </div>

              {/* View Mode Toggle: Studio vs Grid */}
              <div className="flex items-center p-0.5 rounded-xl bg-black/40 border border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setViewMode('split')}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                    viewMode === 'split'
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="โหมดสตูดิโอ 2 ฝั่ง (เลือกคลิปซ้าย ดู QC ขวา)"
                >
                  <Columns className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">สตูดิโอ 2 ฝั่ง</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('grid')}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                    viewMode === 'grid'
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="โหมดตารางการ์ด 9:16 ทั้งหมด"
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">ตารางการ์ด</span>
                </button>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1.5">
                <Button
                  onClick={onRefresh}
                  variant="secondary"
                  size="sm"
                  icon={RefreshCw}
                  className="px-2.5 sm:px-3"
                  title="รีเฟรชคลังคลิป"
                >
                  <span className="hidden sm:inline">รีเฟรช</span>
                </Button>
                <Button
                  onClick={handleOpenExportsFolder}
                  variant="secondary"
                  size="sm"
                  icon={Folder}
                  className="px-2.5 sm:px-3"
                  title="เปิดโฟลเดอร์ Exports บนเครื่อง"
                >
                  <span className="hidden sm:inline">เปิดโฟลเดอร์</span>
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Row 2: Search, Filters & Status Bar (Only in exports tab) */}
        {activeMediaTab === 'exports' && (
          <div className="pt-3 border-t border-white/[0.06] space-y-3 relative z-10">
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-2.5">
              {/* Search input with clear */}
              <div className="relative flex-1 md:max-w-md lg:max-w-lg">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="ค้นหาชื่อคลิป, แคปชัน, หรือสินค้า..."
                  className="w-full bg-black/50 border border-white/[0.1] focus:border-[#FE2C55] focus:ring-1 focus:ring-[#FE2C55] rounded-xl pl-10 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:outline-none transition-all"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white flex items-center justify-center text-xs transition-colors cursor-pointer"
                    title="ล้างคำค้นหา"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Product and Sort dropdowns */}
              <div className="grid grid-cols-2 sm:flex sm:items-center gap-2">
                <div className="relative flex-1 sm:w-44">
                  <select
                    value={selectedProductFilter}
                    onChange={(e) => setSelectedProductFilter(e.target.value)}
                    className="w-full py-2 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer truncate"
                  >
                    <option value="all" className="bg-[#080B11]">สินค้าทั้งหมด ({exportsList?.length || 0})</option>
                    {productTags.map(t => (
                      <option key={t} value={t} className="bg-[#080B11]">{t}</option>
                    ))}
                  </select>
                </div>

                <div className="relative flex-1 sm:w-32">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="w-full py-2 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-white text-xs font-bold focus:outline-none focus:border-[#FE2C55] transition-colors cursor-pointer"
                  >
                    <option value="newest" className="bg-[#080B11]">ใหม่ล่าสุด</option>
                    <option value="oldest" className="bg-[#080B11]">เก่าที่สุด</option>
                    <option value="size_desc" className="bg-[#080B11]">ขนาดใหญ่สุด</option>
                    <option value="name" className="bg-[#080B11]">เรียงตามชื่อ</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Status Filter Chips & Batch Selection */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 no-scrollbar touch-pan-x flex-nowrap">
                {[
                  { id: 'all',         label: 'ทั้งหมด',              count: counts.all,          color: 'text-slate-300 border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.08]',   active: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/40 shadow-sm shadow-[#25F4EE]/10' },
                  { id: 'latest',      label: 'เวอร์ชันล่าสุด',        count: counts.latest,       color: 'text-emerald-300 border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10', active: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10' },
                  { id: 'previous',    label: 'เวอร์ชันก่อนหน้า',       count: counts.previous,     color: 'text-amber-300 border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10',   active: 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm shadow-amber-500/10' },
                  { id: 'unlinked',    label: 'คลิปภายนอก',          count: counts.unlinked,     color: 'text-slate-400 border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06]',  active: 'bg-slate-500/20 text-slate-200 border-slate-500/40' },
                  { id: 'qc_rejected', label: 'QC ปัดตก',            count: counts.qc_rejected,  color: 'text-red-300 border-red-500/20 bg-red-500/5 hover:bg-red-500/10',         active: 'bg-red-500/20 text-red-300 border-red-500/40 shadow-sm shadow-red-500/10' },
                ].map(chip => (
                  <button
                    key={chip.id}
                    type="button"
                    onClick={() => setStatusFilter(chip.id)}
                    className={`py-1 px-2.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 ${
                      statusFilter === chip.id ? chip.active : chip.color
                    }`}
                  >
                    {chip.id === 'latest' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {chip.id === 'previous' && <History className="w-3.5 h-3.5 text-amber-400" />}
                    {chip.id === 'unlinked' && <FileQuestion className="w-3.5 h-3.5 text-slate-400" />}
                    {chip.id === 'qc_rejected' && <ShieldAlert className="w-3.5 h-3.5 text-red-400" />}
                    <span>{chip.label}</span>
                    <span className="font-mono text-[11px] opacity-75">({chip.count})</span>
                  </button>
                ))}
              </div>

              {/* Batch Actions & Select All */}
              <div className="flex items-center gap-2 justify-between sm:justify-end flex-shrink-0">
                <button
                  type="button"
                  onClick={toggleSelectAll}
                  className="py-1 sm:py-1.5 px-2.5 sm:px-3 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-bold text-slate-300 flex items-center gap-1.5 cursor-pointer transition-colors active:scale-95"
                >
                  {selectedVideos.length === filteredExports.length && filteredExports.length > 0 ? (
                    <CheckSquare className="w-3.5 h-3.5 text-[#FE2C55]" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span>เลือกทั้งหมด ({filteredExports.length})</span>
                </button>

                {selectedVideos.length > 0 && (
                  <Button
                    onClick={handleBatchDelete}
                    loading={deleting}
                    variant="danger"
                    size="sm"
                    icon={Trash2}
                    className="py-1 px-2.5 text-xs active:scale-95"
                  >
                    ลบที่เลือก ({selectedVideos.length})
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Content View Area ── */}
      {activeMediaTab === 'raw_vault' ? (
        <RawVaultPanel />
      ) : (
        <>
          {filteredExports.length === 0 ? (
            /* Empty State */
            <div className="p-16 text-center space-y-4 rounded-3xl border border-white/[0.08] glass-panel shadow-xl">
              <div>
                <h3 className="text-lg font-bold text-white">
                  {searchQuery ? 'ไม่พบคลิปวิดีโอที่ค้นหา' : 'ยังไม่มีคลิปวิดีโอที่ตัดเสร็จในคลัง'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-md mx-auto">
                  {searchQuery
                    ? 'ลองพิมพ์คำค้นหาอื่น หรือเปลี่ยนตัวกรองสินค้า'
                    : 'ไปที่เมนู 1-Click Studio แล้วกดเริ่มตัดต่อวิดีโอ คลิปที่ตัดเสร็จจะมาปรากฏในคลังนี้โดยอัตโนมัติ'}
                </p>
              </div>
            </div>
          ) : viewMode === 'split' ? (
            /* Master-Detail Studio Layout - Single Workbench in entire DOM (Prevents Audio Echo) */
            <div className="space-y-4">
              {/* Mobile (< lg): iPhone 15 Pro Max Touch-friendly Horizontal Snap Carousel */}
              <div className="lg:hidden space-y-2">
                <div className="flex items-center justify-between px-1">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 font-kanit">
                    <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>เลือกคลิปตรวจ QC ({filteredExports.length})</span>
                  </span>
                  <span className="text-[11px] text-slate-500">ปัดซ้าย-ขวาเพื่อเลือก</span>
                </div>
                <div className="flex items-center gap-2 overflow-x-auto pb-2 pt-1 px-1 snap-x snap-mandatory no-scrollbar -mx-2 px-2">
                  {filteredExports.map(item => (
                    <ExportMobilePill
                      key={item.path}
                      item={item}
                      isActive={activeVideo?.path === item.path}
                      onSelect={() => setActiveVideoPath(item.path)}
                    />
                  ))}
                </div>
              </div>

              {/* Main Responsive Grid: 1 Workbench in DOM */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                {/* Left Column (5 Cols): Playlist (Desktop only) */}
                <div className="hidden lg:block lg:col-span-5 space-y-2.5">
                  <div className="flex items-center justify-between px-2 py-1">
                    <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 font-kanit">
                      <List className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>รายการคลิป ({filteredExports.length})</span>
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      คลิกเพื่อเลือกตรวจ QC
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[calc(100vh-230px)] overflow-y-auto pr-1 no-scrollbar">
                    {filteredExports.map(item => (
                      <ExportSidebarItem
                        key={item.path}
                        item={item}
                        isSelected={selectedVideos.includes(item.path)}
                        isActive={activeVideo?.path === item.path}
                        onSelect={() => setActiveVideoPath(item.path)}
                        onToggleCheck={toggleSelectVideo}
                      />
                    ))}
                  </div>
                </div>

                {/* Right Column (7 Cols on desktop, 100% on mobile): Single Workbench in DOM */}
                <div className="w-full lg:col-span-7 lg:sticky lg:top-4">
                  <ExportActiveWorkbench
                    video={activeVideo}
                    onSwapToLatest={handleSwapToLatest}
                    onOpenLinkModal={handleOpenLinkModal}
                    onCopyCaption={handleCopyCaption}
                    copiedCaption={copiedCaption}
                    mobileBaseUrl={mobileBaseUrl}
                    onDelete={(v) => setDeleteTarget(v)}
                    onGenerateCover={handleGenerateCover}
                    onRevealFile={handleRevealFile}
                    onMarkPosted={handleMarkPosted}
                    onPrepareAutopost={handlePrepareAutopost}
                  />
                </div>
              </div>
            </div>
          ) : (
            /* Grid View: 9:16 Card Showcase */
            <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3 sm:gap-4 lg:gap-5">
              {filteredExports.map((item, idx) => (
                <ExportCard
                  key={item.rel_path || item.path || idx}
                  item={item}
                  isSelected={selectedVideos.includes(item.path)}
                  onToggleSelect={toggleSelectVideo}
                  onOpenDetail={setSelectedDetailVideo}
                  onOpenDelete={setDeleteTarget}
                />
              ))}
            </div>
          )}

          {/* ── Floating Batch Action Bar (Mobile & Desktop) ── */}
          {selectedVideos.length > 0 && (
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-md w-[calc(100%-2rem)] p-3 rounded-2xl bg-[#0B0F19]/95 border border-[#25F4EE]/40 backdrop-blur-2xl shadow-2xl flex items-center justify-between gap-3 animate-fadeIn">
              <div className="flex items-center gap-2.5 text-xs font-bold text-white">
                <span className="w-6 h-6 rounded-lg bg-[#25F4EE]/20 text-[#25F4EE] flex items-center justify-center font-mono text-xs">
                  {selectedVideos.length}
                </span>
                <span>เลือกไว้ {selectedVideos.length} คลิป</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedVideos([])}
                  className="py-1.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-xs font-bold text-slate-300 transition-colors cursor-pointer"
                >
                  ยกเลิก
                </button>
                <button
                  type="button"
                  onClick={handleBatchDelete}
                  className="py-1.5 px-3.5 rounded-xl bg-rose-500 hover:bg-rose-600 text-xs font-bold text-white flex items-center gap-1.5 shadow-lg shadow-rose-500/20 transition-all active:scale-95 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>ลบที่เลือก</span>
                </button>
              </div>
            </div>
          )}

          {/* ── DETAILED VIDEO QC, FULL PREVIEW & METADATA MODAL (For Grid Card clicks) ── */}
          <Modal
            isOpen={!!selectedDetailVideo}
            onClose={() => setSelectedDetailVideo(null)}
            title={selectedDetailVideo?.hook_title || selectedDetailVideo?.name || 'พรีวิววิดีโอ'}
            subtitle={selectedDetailVideo?.hook_title ? `${selectedDetailVideo.product_name ? `${selectedDetailVideo.product_name} • ` : ''}${selectedDetailVideo.name}` : 'พรีวิวคลิปขนาดเต็ม สแกน QR โหลดเข้ามือถือ'}
            maxWidth="max-w-2xl"
          >
            {selectedDetailVideo && (
              <div className="space-y-4 max-h-[80vh] overflow-y-auto pr-1 no-scrollbar">
                {/* 1. Large 9:16 Video Player Preview (No autoPlay to prevent audio echo) */}
                <div className="w-full max-w-[320px] sm:max-w-[360px] aspect-[9/16] max-h-[60vh] mx-auto rounded-2xl overflow-hidden bg-black border border-white/[0.12] shadow-2xl relative flex items-center justify-center ring-1 ring-white/[0.05]">
                  <video
                    key={selectedDetailVideo.rel_path || selectedDetailVideo.path}
                    src={`/api/media/${selectedDetailVideo.rel_path || selectedDetailVideo.path}`}
                    controls
                    playsInline
                    preload="metadata"
                    onLoadedMetadata={(e) => setModalDuration(e.target.duration)}
                    className="w-full h-full object-contain"
                  />
                </div>

                {/* Version / QC Status Banners */}
                {selectedDetailVideo.is_previous_version && (
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30">
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
                        <History className="w-4 h-4 text-amber-400" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-amber-300 mb-0.5">คลิปนี้เป็นเวอร์ชันก่อนหน้า (มีเวอร์ชันใหม่กว่าแทนที่แล้ว)</div>
                        {selectedDetailVideo.latest_video_name && (
                          <div className="text-[11px] text-amber-200/80">
                            เวอร์ชันล่าสุด: <span className="font-mono text-white">{selectedDetailVideo.latest_video_name}</span>
                          </div>
                        )}
                        <div className="text-[10px] text-slate-400 mt-0.5">สามารถสลับไปดูตัวล่าสุด หรือลบไฟล์นี้เพื่อประหยัดพื้นที่ดิสก์</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSwapToLatest(selectedDetailVideo)}
                      className="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer flex-shrink-0 shadow-sm"
                      title="เปิดดูคลิปเวอร์ชันล่าสุด"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>สลับไปดูตัวล่าสุด</span>
                    </button>
                  </div>
                )}

                {selectedDetailVideo.is_unlinked && (
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/60">
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-700/40 border border-slate-600/40 flex items-center justify-center flex-shrink-0">
                        <FileQuestion className="w-4 h-4 text-slate-300" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-200 mb-0.5">คลิปภายนอก (ยังไม่ได้ผูกกับสคริปต์สินค้า)</div>
                        <div className="text-[11px] text-slate-400">
                          ไฟล์นี้ยังไม่มีข้อมูลสคริปต์ในระบบ สามารถเลือกผูกกับสินค้าเพื่อดึงสคริปต์และแคปชันมาใช้ได้
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleOpenLinkModal(selectedDetailVideo)}
                      className="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/40 text-[#25F4EE] hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer flex-shrink-0 shadow-sm"
                    >
                      <Link2 className="w-3.5 h-3.5" />
                      <span>ผูกกับสคริปต์</span>
                    </button>
                  </div>
                )}

                {selectedDetailVideo.is_latest && !selectedDetailVideo.is_qc_rejected && (
                  <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span>คลิปเวอร์ชันล่าสุด (พร้อมใช้งานและโพสต์ลง TikTok ทันที)</span>
                  </div>
                )}

                {/* QC Rejected Banner */}
                {selectedDetailVideo.is_qc_rejected && (
                  <div className="flex items-start gap-3 p-3 rounded-2xl bg-red-500/10 border border-red-500/30">
                    <div className="w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                      <ShieldAlert className="w-4 h-4 text-red-400" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-red-300 mb-0.5">คลิปนี้ถูกปัดตก QC — ถูกแทนที่แล้ว</div>
                      {selectedDetailVideo.qc_note && (
                        <div className="text-xs text-red-200/80 font-mono">{selectedDetailVideo.qc_note}</div>
                      )}
                      <div className="text-[10px] text-slate-400 mt-1">สามารถลบไฟล์นี้ได้อย่างปลอดภัย เวอร์ชันใหม่ถูก render แล้ว</div>
                    </div>
                  </div>
                )}

                {/* 4 Detailed Spec & Generation Time Cards (2x2 Grid) */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {/* Box 1: เวลาที่เจนเสร็จ */}
                  <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                      <Clock className="w-3 h-3 text-[#25F4EE]" />
                      <span>เวลาที่ตัดต่อเสร็จ</span>
                    </div>
                    <div className="font-mono text-white text-[11px] font-bold truncate">
                      {formatDateTimeFull(selectedDetailVideo.modified_time || selectedDetailVideo.modified)}
                    </div>
                    <div className="text-[10px] text-[#25F4EE] font-kanit">
                      {getRelativeTimeDesc(selectedDetailVideo.timestamp, selectedDetailVideo.modified_time || selectedDetailVideo.modified)}
                    </div>
                  </div>

                  {/* Box 2: ความยาวคลิป & FPS */}
                  <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                      <Film className="w-3 h-3 text-emerald-400" />
                      <span>ความยาว & เฟรมเรต</span>
                    </div>
                    <div className="font-mono text-emerald-300 text-[11px] font-bold">
                      {formatDuration(modalDuration)} นาที
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {formatCodecSpec(modalMediaInfo)}
                    </div>
                  </div>

                  {/* Box 3: ขนาด & สเปกหน้าจอ */}
                  <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                      <HardDrive className="w-3 h-3 text-cyan-400" />
                      <span>ขนาดไฟล์ & สัดส่วน</span>
                    </div>
                    <div className="font-mono text-cyan-300 text-[11px] font-bold">
                      {selectedDetailVideo.size_mb} MB
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {formatResolutionSpec(modalMediaInfo)}
                    </div>
                  </div>

                  {/* Box 4: Safe Zone & ระดับเสียง */}
                  <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-1">
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 font-kanit">
                      <ShieldCheck className="w-3 h-3 text-purple-400" />
                      <span>Safe Zone & อัตราเสียง</span>
                    </div>
                    <div className="font-mono text-purple-300 text-[11px] font-bold">
                      Safe Zone ล่าง 420px
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      Voice 100% / SFX 28% / BGM 12%
                    </div>
                  </div>
                </div>

                {/* Product & Marketing Context Card */}
                {(selectedDetailVideo.product_name || selectedDetailVideo.angle_name || selectedDetailVideo.price_deal || selectedDetailVideo.key_features) && (
                  <div className="p-3 rounded-xl bg-gradient-to-br from-white/[0.04] to-black/40 border border-white/[0.08] space-y-2">
                    <div className="text-[11px] font-bold text-slate-300 flex items-center justify-between">
                      <span className="flex items-center gap-1.5 font-kanit">
                        <Tag className="w-3.5 h-3.5 text-[#FE2C55]" />
                        <span>ข้อมูลสินค้าและแคมเปญ</span>
                      </span>
                      {selectedDetailVideo.price_deal && (
                        <span className="px-2 py-0.5 rounded-full bg-[#FE2C55]/15 text-[#FE2C55] font-bold text-[10px] border border-[#FE2C55]/30">
                          {selectedDetailVideo.price_deal}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-kanit">
                      <div>
                        <span className="text-slate-500 block text-[10px]">สินค้า:</span>
                        <span className="text-white font-medium truncate block">{selectedDetailVideo.product_name || '-'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px]">มุมมองรีวิว (Angle):</span>
                        <span className="text-slate-200 font-medium truncate block">{selectedDetailVideo.angle_name || '-'}</span>
                      </div>
                      {selectedDetailVideo.ad_tone && (
                        <div className="col-span-2">
                          <span className="text-slate-500 block text-[10px]">โทนเสียงพากย์:</span>
                          <span className="text-slate-300 text-[11px]">{selectedDetailVideo.ad_tone}</span>
                        </div>
                      )}
                      {selectedDetailVideo.key_features && (
                        <div className="col-span-2">
                          <span className="text-slate-500 block text-[10px]">จุดขายสินค้า:</span>
                          <span className="text-slate-300 text-[11px] line-clamp-2">{selectedDetailVideo.key_features}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Script Breakdown Accordion */}
                {Array.isArray(selectedDetailVideo.script_lines) && selectedDetailVideo.script_lines.length > 0 && (
                  <div className="rounded-xl border border-white/[0.08] bg-black/40 overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setModalShowScript(!modalShowScript)}
                      className="w-full p-2.5 flex items-center justify-between text-xs font-bold text-slate-300 hover:text-white transition-colors cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5 font-kanit">
                        <Layers className="w-3.5 h-3.5 text-[#25F4EE]" />
                        <span>บทพูดสคริปต์ในคลิป ({selectedDetailVideo.script_lines.length} ท่อน • J-Cut)</span>
                      </span>
                      {modalShowScript ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>

                    {modalShowScript && (
                      <div className="p-3 border-t border-white/[0.06] space-y-2 bg-black/60 max-h-48 overflow-y-auto no-scrollbar font-mono text-xs">
                        {selectedDetailVideo.script_lines.map((line, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                            <span className="w-5 h-5 rounded bg-[#25F4EE]/10 text-[#25F4EE] flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                              {idx + 1}
                            </span>
                            <p className="text-slate-300 leading-relaxed text-[11px]">
                              {typeof line === 'string' ? line : line.text || line.dialogue || JSON.stringify(line)}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Caption & Hashtag Box */}
                <div className="p-3.5 rounded-2xl bg-black/50 border border-white/[0.08] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 font-kanit">
                      <FileText className="w-3.5 h-3.5 text-[#25F4EE]" />
                      <span>แคปชัน & แฮชแท็กสำหรับโพสต์</span>
                    </span>
                    {selectedDetailVideo.tiktok_caption ? (
                      <button
                        onClick={() => handleCopyCaption(`${selectedDetailVideo.tiktok_caption}\n\n${selectedDetailVideo.tiktok_hashtags || ''}`)}
                        className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[#25F4EE] hover:text-white text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <Copy className="w-3 h-3" />
                        <span>{copiedCaption ? 'คัดลอกแล้ว!' : 'คัดลอก'}</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenLinkModal(selectedDetailVideo)}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <AlertTriangle className="w-3 h-3" />
                        <span>ผูกกับสินค้าก่อน</span>
                      </button>
                    )}
                  </div>
                  {selectedDetailVideo.tiktok_caption ? (
                    <p className="text-xs text-slate-300 bg-black/40 p-2.5 rounded-xl border border-white/[0.04] select-all leading-relaxed font-mono">
                      {selectedDetailVideo.tiktok_caption}&nbsp;
                      {selectedDetailVideo.tiktok_hashtags || ''}
                    </p>
                  ) : (
                    <p className="text-xs text-amber-400/90 bg-amber-950/20 p-2.5 rounded-xl border border-amber-500/20">
                      ⚠ คลิปนี้ยังไม่ได้ผูกกับ Angle สินค้า — ยังไม่มีแคปชันจริงให้คัดลอก
                      (เดิมจะเผลอคัดลอกข้อความตัวอย่างไปโพสต์แทน)
                    </p>
                  )}
                </div>

                {/* 3. File Path with copy button */}
                <div className="p-3 rounded-2xl bg-black/40 border border-white/[0.08] flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] text-slate-400 block font-kanit">ที่อยู่ไฟล์บนเครื่อง</span>
                    <span className="text-xs font-mono text-slate-300 truncate block">
                      {selectedDetailVideo.rel_path || selectedDetailVideo.name}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(selectedDetailVideo.rel_path || selectedDetailVideo.path);
                      setModalCopiedPath(true);
                      setTimeout(() => setModalCopiedPath(false), 2000);
                    }}
                    className="px-2.5 py-1.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-slate-200 text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer flex-shrink-0"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{modalCopiedPath ? 'คัดลอกแล้ว' : 'คัดลอกที่อยู่'}</span>
                  </button>
                </div>

                {/* 3.5 Post Studio Quick Actions (Desktop & TikTok Helper) */}
                <div className="p-3.5 rounded-2xl bg-[#0B0F19] border border-amber-500/20 space-y-2.5">
                  <div className="text-xs font-bold text-amber-300 flex items-center justify-between font-kanit">
                    <span className="flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      <span>โพสต์คลิปผ่านคอม (Post Studio)</span>
                    </span>
                    {selectedDetailVideo.is_posted ? (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>โพสต์แล้ว</span>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleMarkPosted(selectedDetailVideo)}
                        className="px-2 py-0.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-[10px] font-bold border border-emerald-500/20 cursor-pointer"
                      >
                        มาร์คว่าโพสต์แล้ว
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleRevealFile(selectedDetailVideo)}
                      className="flex-1 py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      <span>เปิดใน Explorer</span>
                    </button>
                    <a
                      href="https://www.tiktok.com/tiktokstudio/upload"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>เปิด TikTok Studio</span>
                    </a>
                  </div>
                  {!selectedDetailVideo.is_posted && (
                    <button
                      type="button"
                      onClick={() => handlePrepareAutopost(selectedDetailVideo, null)}
                      className="w-full py-2.5 px-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all shadow-md"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>โพสต์ TikTok อัตโนมัติ (ทดลอง)</span>
                    </button>
                  )}
                </div>

                {/* 4. QR Mobile Download Section */}
                <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] text-center space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/30 flex items-center justify-center text-[#25F4EE] mx-auto">
                    <Smartphone className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white font-kanit">สแกน QR เปิดตัวช่วยโพสต์บนมือถือ</h4>
                    <p className="text-xs text-slate-400 mt-0.5">เปิดกล้องมือถือสแกนเพื่อโหลดคลิป, ก็อปแคปชัน, ก็อปชื่อปักตะกร้า และเปิด TikTok ทันที</p>
                  </div>
                  <div className="p-3 bg-white rounded-2xl inline-block shadow-xl">
                    <QRCodeSVG
                      value={buildQuickPostUrl(mobileBaseUrl, selectedDetailVideo)}
                      size={150}
                      level="M"
                    />
                  </div>
                </div>

                {/* 5. Modal Footer Action Buttons */}
                <div className="flex items-center gap-2 pt-2 border-t border-white/[0.08]">
                  <a
                    href={`/api/media/${selectedDetailVideo.rel_path || selectedDetailVideo.path}`}
                    download={selectedDetailVideo.name}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg cursor-pointer active:scale-95 transition-all text-center"
                  >
                    <Download className="w-4 h-4" />
                    <span>ดาวน์โหลด MP4</span>
                  </a>
                  <Button
                    onClick={() => {
                      setDeleteTarget(selectedDetailVideo);
                      setSelectedDetailVideo(null);
                    }}
                    variant="danger"
                    size="md"
                    icon={Trash2}
                  >
                    {selectedDetailVideo.is_previous_version ? 'ลบไฟล์เวอร์ชันนี้' : 'ลบไฟล์'}
                  </Button>
                </div>
              </div>
            )}
          </Modal>

          {/* ── LINK EXTERNAL VIDEO TO PRODUCT/ANGLE MODAL ── */}
          <Modal
            isOpen={!!linkingVideo}
            onClose={() => setLinkingVideo(null)}
            title="ผูกวิดีโอนี้กับสินค้าและสคริปต์"
            subtitle={linkingVideo?.name}
            maxWidth="max-w-md"
          >
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-xs text-slate-300">
                เลือกสินค้าและมุมมองสคริปต์ (Angle) ที่ต้องการเชื่อมโยงเข้ากับคลิปนี้ เมื่อเชื่อมแล้วคลิปจะถูกนำไปแสดงข้อมูลสคริปต์ แคปชัน และแท็กสินค้า
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">เลือกสินค้า</label>
                <select
                  value={selectedLinkProductId}
                  onChange={handleLinkProductChange}
                  className="w-full py-2.5 px-3 rounded-xl bg-black/60 border border-white/[0.12] text-white text-xs font-bold focus:outline-none focus:border-[#25F4EE]"
                >
                  {availableProducts.map(p => (
                    <option key={p.id} value={p.id} className="bg-[#080B11]">
                      {p.name || p.title || p.id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">เลือกมุมสคริปต์ (Angle)</label>
                {selectedProductAngles.length > 0 ? (
                  <select
                    value={selectedLinkAngleId}
                    onChange={(e) => setSelectedLinkAngleId(e.target.value)}
                    className="w-full py-2.5 px-3 rounded-xl bg-black/60 border border-white/[0.12] text-white text-xs font-bold focus:outline-none focus:border-[#25F4EE]"
                  >
                    {selectedProductAngles.map(a => (
                      <option key={a.angle_id} value={a.angle_id} className="bg-[#080B11]">
                        {a.angle_name || a.angle_id} {a.hook_title ? `— "${a.hook_title.slice(0, 30)}..."` : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                    สินค้านี้ยังไม่มีมุมสคริปต์ที่สร้างไว้
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-white/[0.08]">
                <Button
                  variant="secondary"
                  onClick={() => setLinkingVideo(null)}
                  disabled={isLinking}
                  className="flex-1"
                >
                  ยกเลิก
                </Button>
                <Button
                  variant="primary"
                  onClick={handleConfirmLink}
                  loading={isLinking}
                  disabled={!selectedLinkProductId || !selectedLinkAngleId}
                  icon={Check}
                  className="flex-1"
                >
                  {isLinking ? 'กำลังผูกคลิป...' : 'ยืนยันการผูกคลิป'}
                </Button>
              </div>
            </div>
          </Modal>

          {/* ── Single Video Delete Confirm Modal ── */}
          <ConfirmModal
            isOpen={!!deleteTarget}
            onClose={() => setDeleteTarget(null)}
            onConfirm={confirmDelete}
            title="ลบคลิปวิดีโอนี้ถาวร?"
            description="ไฟล์วิดีโอ MP4 ในโฟลเดอร์ Exports จะถูกลบออกจากเครื่อง"
            itemName={deleteTarget?.name}
            dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
            confirmText="ลบไฟล์ถาวร"
            loading={deleting}
            variant="danger"
          />

          {/* ── Batch Delete Confirm Modal ── */}
          <ConfirmModal
            isOpen={showBatchDeleteModal}
            onClose={() => setShowBatchDeleteModal(false)}
            onConfirm={confirmBatchDelete}
            title={`ลบคลิปวิดีโอที่เลือกทั้งหมด (${selectedVideos.length} รายการ)?`}
            description={`ไฟล์วิดีโอทั้งหมด ${selectedVideos.length} ไฟล์จะถูกลบออกจากเครื่องอย่างถาวร`}
            dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
            confirmText={`ลบทั้งหมด ${selectedVideos.length} ไฟล์`}
            loading={deleting}
            variant="danger"
          />
        </>
      )}
    </div>
  );
}

