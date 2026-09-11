import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Link2, Sparkles, Clapperboard, Loader2, Check, Copy,
  AlertCircle, ArrowRight, Upload, Trash2, RefreshCw, Plus, Film, Video,
  ChevronDown, ChevronUp, ChevronRight, Package, Rocket, FolderOpen, X,
  Search, LayoutGrid, Filter, Play, Lock, Edit3, Replace, Columns, List,
  ShoppingBag, ShieldCheck, Database
} from 'lucide-react';
import {
  scrapeAndPlanProduct, scrapeAndPlanProductAsync, getProducts, updateProduct,
  previewProductSource, previewProductImageMetadataAsync, refreshProductSource, updateAngleStatus, updateAngleVideos, setDefaultVideosForProduct, deleteProduct,
  uploadFile, resolveTiktokProductId, rerollAngleScript,
  generateShotList, getShotList, getTaskStatus
} from '../api';
import { Modal, Toast, Button, Badge, Input, Textarea, ConfirmModal, PageHeader } from './ui';
import MediaPickerModal from './MediaPickerModal';
import FindReplaceModal from './FindReplaceModal';
import ProductMetadataModal from './ProductMetadataModal';
import ShotListModal from './ShotListModal';
import { toMediaUrl } from '../lib/mediaUrl';
import { useToast } from '../hooks';
import { useTaskManager } from '../context/TaskContext';
import { guessBrandModel } from '../lib/overlayModel';
import { resolveHistoryTargetId, resolveSelectedProduct } from '../lib/productSelection';

// One Gemini vision call reads all of these together (product photo, spec
// sheet, review screenshots) -- capped so a single analyze request stays a
// handful of images, not an unbounded upload.
const MAX_ANALYZE_IMAGES = 5;
const MAX_PRODUCT_REFERENCE_IMAGES = 20;

// Mirrors scripts/product_scraper.py's DURATION_SPECS -- keep these Thai
// labels byte-for-byte identical to the backend constants so the UI never
// promises a duration tier the backend doesn't recognize.
const DURATION_OPTIONS = [
  { val: '30s', label: '30 วินาที (สั้นกระชับ)' },
  { val: '60s', label: '60 วินาที (มาตรฐาน)' },
  { val: '90s', label: '90 วินาที (แอดวานซ์ ละเอียด)' },
];

// Mirrors scripts/product_scraper.py's EXTRA_BEAT_BLOCKS.
const EXTRA_BEAT_OPTIONS = [
  { val: 'spec_detail', label: 'สเปก/สรรพคุณละเอียด' },
  { val: 'comparison', label: 'เปรียบเทียบของเดิม vs ของใหม่' },
  { val: 'use_cases', label: 'การใช้งานจริง/เคสตัวอย่างหลายสถานการณ์' },
  { val: 'faq', label: 'ตอบคำถามที่มักเจอ (FAQ) / ข้อกังวล' },
];

// Stable keys returned by the backend. A topic can have more than one badge
// when extra content beats were selected for the same angle.
const CONTENT_TYPE_CATALOG = {
  problem_solution: { label: 'ปัญหา → ทางออก', className: 'text-rose-200 bg-rose-500/10 border-rose-400/25' },
  specs: { label: 'สเปก/สรรพคุณ', className: 'text-cyan-200 bg-cyan-500/10 border-cyan-400/25' },
  unboxing: { label: 'แกะกล่อง / First Impression', className: 'text-violet-200 bg-violet-500/10 border-violet-400/25' },
  promotion: { label: 'โปรโมชัน / ความคุ้มค่า', className: 'text-amber-200 bg-amber-500/10 border-amber-400/25' },
  comparison: { label: 'เปรียบเทียบ', className: 'text-blue-200 bg-blue-500/10 border-blue-400/25' },
  tips: { label: 'ทริก / How-to', className: 'text-lime-200 bg-lime-500/10 border-lime-400/25' },
  warning: { label: 'ข้อควรระวัง', className: 'text-orange-200 bg-orange-500/10 border-orange-400/25' },
  target_audience: { label: 'เจาะกลุ่มผู้ใช้', className: 'text-fuchsia-200 bg-fuchsia-500/10 border-fuchsia-400/25' },
  experience: { label: 'ประสบการณ์ใช้งานจริง', className: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/25' },
  use_cases: { label: 'การใช้งานจริง', className: 'text-teal-200 bg-teal-500/10 border-teal-400/25' },
  faq: { label: 'FAQ / ข้อกังวล', className: 'text-sky-200 bg-sky-500/10 border-sky-400/25' },
  value: { label: 'คำนวณความคุ้มค่า', className: 'text-yellow-200 bg-yellow-500/10 border-yellow-400/25' },
};

const ANGLE_CONTENT_TYPES = {
  pain_point: ['problem_solution'],
  spec_review: ['specs'],
  unboxing: ['unboxing'],
  fomo_deal: ['promotion'],
  comparison: ['comparison'],
  life_hack: ['tips'],
  stop_scroll: ['warning'],
  niche_target: ['target_audience'],
  longterm_review: ['experience'],
  math_value: ['value'],
};

const EXTRA_BEAT_CONTENT_TYPES = {
  spec_detail: 'specs',
  comparison: 'comparison',
  use_cases: 'use_cases',
  faq: 'faq',
};

function contentTypesForAngle(angle) {
  if (Array.isArray(angle?.content_types) && angle.content_types.length > 0) {
    return angle.content_types;
  }
  const types = [...(ANGLE_CONTENT_TYPES[angle?.angle_id] || [])];
  (angle?.extra_beats || []).forEach(beat => {
    const type = EXTRA_BEAT_CONTENT_TYPES[beat];
    if (type && !types.includes(type)) types.push(type);
  });
  return types;
}

function ContentTypeBadges({ angle, compact = false }) {
  const types = contentTypesForAngle(angle);
  if (types.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {types.map(type => {
        const meta = CONTENT_TYPE_CATALOG[type] || {
          label: type,
          className: 'text-slate-300 bg-white/[0.05] border-white/[0.12]',
        };
        return (
          <span
            key={type}
            title={meta.label}
            className={`${compact ? 'text-[9px] px-1.5 py-0.5' : 'text-[10px] px-2 py-0.5'} inline-flex items-center rounded-full border font-semibold leading-tight ${meta.className}`}
          >
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}

// Sensible default checkbox pre-check per duration tier, matching the
// backend's own default extra-beat mix (30s -> none, 60s -> first 2, 90s -> all).
function defaultExtraBeatsForDuration(duration) {
  if (duration === '90s') return EXTRA_BEAT_OPTIONS.map(o => o.val);
  if (duration === '60s') return EXTRA_BEAT_OPTIONS.slice(0, 2).map(o => o.val);
  return [];
}

// ═══════════════════════════════════════════════════════════════════════
// 📦 PRODUCT CARD (Horizontal Gallery Item)
// ═══════════════════════════════════════════════════════════════════════
function ProductCard({ product, isSelected, onSelect }) {
  const pAngles = product.angles || [];
  const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
  const total = pAngles.length || 4;
  const pct = Math.round((pDone / total) * 100);
  const thumb = product.images?.[0];
  // A scraped product-page image only ever has .url (external CDN link);
  // a user-uploaded one only has .rel_path/.local_path -- toMediaUrl handles
  // both, including the http(s) passthrough a bare CDN link needs.
  const thumbSrc = thumb ? toMediaUrl(thumb.rel_path || thumb.local_path || thumb.url) : null;

  return (
    <button
      onClick={() => onSelect(product)}
      className={`flex-shrink-0 w-[130px] sm:w-[150px] rounded-xl border transition-all cursor-pointer group snap-center p-2.5 space-y-2 text-left ${
        isSelected
          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
          : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
      }`}
    >
      {/* Thumbnail or Placeholder */}
      <div className="w-full aspect-square rounded-lg overflow-hidden bg-black/60 border border-white/[0.06] flex items-center justify-center">
        {thumbSrc ? (
          <img src={thumbSrc} alt="" className="w-full h-full object-cover" />
        ) : (
          <Package className={`w-7 h-7 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-600'}`} />
        )}
      </div>

      {/* Name */}
      <div className={`text-xs font-bold truncate leading-tight ${isSelected ? 'text-white' : 'text-slate-300'}`}>
        {product.name}
      </div>

      {/* Progress Mini Bar */}
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={`text-sm font-mono font-bold flex-shrink-0 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-500'}`}>
          {pDone}/{total}
        </span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 📑 ANGLE SIDEBAR ITEM (Left Column in Split Studio View)
// ═══════════════════════════════════════════════════════════════════════
function AngleSidebarItem({ angle, index, isSelected, onSelect, onPreviewExportVideo }) {
  const curStatus = angle.status || 'scripted';
  const isRendered = (curStatus === 'rendered' || curStatus === 'posted') && !!angle.video_url;
  const isInProduction = curStatus === 'in_production' || (!!angle.project_name && !isRendered);

  const statusLabel = curStatus === 'posted' ? 'โพสต์แล้ว'
    : isRendered ? 'ตัดเสร็จแล้ว'
    : isInProduction ? 'กำลังตัดต่อ'
    : 'สคริปต์พร้อม';

  const statusColor = curStatus === 'posted' ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isRendered ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isInProduction ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : 'bg-white/[0.05] text-slate-400 border-white/[0.08]';

  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);

  return (
    <div
      onClick={onSelect}
      className={`p-2.5 rounded-xl border transition-all cursor-pointer text-left group relative ${
        isSelected
          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-md shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/30'
          : 'bg-[#080B11] border-white/[0.06] hover:border-white/[0.18] hover:bg-white/[0.02]'
      }`}
    >
      {/* Active Indicator Bar on left edge */}
      {isSelected && (
        <div className="absolute left-0 top-2 bottom-2 w-1 bg-[#25F4EE] rounded-r-full shadow-sm shadow-[#25F4EE]" />
      )}

      <div className="flex items-start gap-2.5">
        {/* Number Badge */}
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${
          isSelected
            ? 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950 shadow-sm'
            : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
        }`}>
          {index + 1}
        </span>

        {/* Title + Hook Preview */}
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center justify-between gap-1.5">
            <span className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-200'}`}>
              {angle.angle_name}
            </span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border flex-shrink-0 ${statusColor}`}>
              {statusLabel}
            </span>
          </div>

          <ContentTypeBadges angle={angle} compact />

          {angle.hook_title && (
            <p className="text-[11px] text-slate-400 truncate font-kanit">
              "{angle.hook_title}"
            </p>
          )}

          {/* Footer of item: footage tag + preview button */}
          <div className="flex items-center justify-between pt-0.5 text-[10px]">
            {selectedVideos.length > 0 ? (
              <span className="inline-flex items-center gap-1 text-[#25F4EE] font-medium">
                <Film className="w-2.5 h-2.5" />
                <span>{selectedVideos.length} คลิป</span>
              </span>
            ) : (
              <span className="text-slate-500 italic">ยังไม่ได้เลือกคลิป</span>
            )}

            {isRendered && angle.video_url && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onPreviewExportVideo && onPreviewExportVideo(angle);
                }}
                className="p-1 rounded bg-cyan-500/15 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/30 flex items-center gap-1 transition-colors"
                title="ดูคลิปที่ Export แล้ว"
              >
                <Play className="w-2.5 h-2.5 fill-cyan-300" />
                <span className="text-[10px] font-bold">ดูคลิป</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 📱 ANGLE MOBILE PILL (Horizontal Swipeable Tab for iPhone 15 PM)
// ═══════════════════════════════════════════════════════════════════════
function AngleMobilePill({ angle, index, isSelected, onSelect }) {
  const curStatus = angle.status || 'scripted';
  const isRendered = (curStatus === 'rendered' || curStatus === 'posted') && !!angle.video_url;
  const isInProduction = curStatus === 'in_production' || (!!angle.project_name && !isRendered);
  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);

  const statusDot = curStatus === 'posted' || isRendered
    ? 'bg-emerald-400'
    : isInProduction
    ? 'bg-amber-400 animate-pulse'
    : 'bg-slate-500';

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex-shrink-0 snap-center px-3 py-2 rounded-xl border text-left transition-all cursor-pointer flex items-center gap-2 max-w-[210px] active:scale-95 ${
        isSelected
          ? 'bg-[#25F4EE]/15 border-[#25F4EE] shadow-md shadow-[#25F4EE]/20 ring-1 ring-[#25F4EE]/40'
          : 'bg-[#080B11] border-white/[0.08] hover:border-white/[0.2] text-slate-300'
      }`}
    >
      <span className={`w-5 h-5 rounded-lg flex items-center justify-center text-[11px] font-bold flex-shrink-0 ${
        isSelected
          ? 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950 shadow-sm'
          : 'bg-white/[0.08] text-slate-400'
      }`}>
        {index + 1}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusDot}`} />
          <span className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
            {angle.angle_name}
          </span>
        </div>
        <ContentTypeBadges angle={angle} compact />
        <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
          {selectedVideos.length > 0 ? (
            <span className="text-[#25F4EE] font-medium">{selectedVideos.length} คลิป</span>
          ) : (
            <span className="text-slate-500">ไม่มีคลิป</span>
          )}
        </div>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 🎬 ANGLE ACTIVE WORKBENCH (Right Column Studio in Split View)
// ═══════════════════════════════════════════════════════════════════════
function AngleActiveWorkbench({
  angle, index, onCopy, onSendToStudio, onOpenInTimeline, onPreviewExportVideo, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false,
  onOpenMediaPicker, onSaveScript, onOpenFindReplace, onRerollScript, onGenerateShotList,
  isGeneratingShotList = false
}) {
  const lines = Array.isArray(angle.script_lines)
    ? angle.script_lines
    : (angle.script_text ? angle.script_text.split('\n') : []);

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [editHook, setEditHook] = useState(angle.hook_title || '');

  const scriptText = lines.join('\n');
  const prevAngleIdRef = useRef(angle.angle_id || index);
  const prevScriptTextRef = useRef(scriptText);
  const prevHookRef = useRef(angle.hook_title || '');

  // Keep editText and editHook in sync whenever angle is replaced externally (e.g. Find & Replace) or switched
  useEffect(() => {
    const curAngleId = angle.angle_id || index;
    const angleChanged = curAngleId !== prevAngleIdRef.current;
    const scriptChanged = scriptText !== prevScriptTextRef.current;
    const hookChanged = (angle.hook_title || '') !== prevHookRef.current;

    if (angleChanged || scriptChanged || hookChanged) {
      setEditText(scriptText);
      setEditHook(angle.hook_title || '');
      prevAngleIdRef.current = curAngleId;
      prevScriptTextRef.current = scriptText;
      prevHookRef.current = angle.hook_title || '';
    }
  }, [angle.angle_id, index, scriptText, angle.hook_title]);

  const curStatus = angle.status || 'scripted';
  const isPosted = curStatus === 'posted' || !!angle.posted_at;
  const isRendered = (curStatus === 'rendered' || isPosted) && !!angle.video_url;
  const isInProduction = !isPosted && (curStatus === 'in_production' || (!!angle.project_name && !isRendered));
  const isLocked = isPosted || isInProduction;

  const handleStartEdit = (e) => {
    if (isLocked) return;
    e && e.stopPropagation();
    setEditText(lines.join('\n'));
    setEditHook(angle.hook_title || '');
    setIsEditing(true);
  };

  const handleCancelEdit = (e) => {
    e && e.stopPropagation();
    setIsEditing(false);
    setEditText(lines.join('\n'));
    setEditHook(angle.hook_title || '');
  };

  const handleSave = (e) => {
    if (isLocked) return;
    e && e.stopPropagation();
    const newLines = editText
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean);

    if (newLines.length === 0) return;

    onSaveScript && onSaveScript(index, newLines, editHook.trim());
    setIsEditing(false);
  };

  const statusLabel = isPosted ? 'โพสต์แล้ว'
    : isRendered ? 'ตัดเสร็จแล้ว'
    : isInProduction ? 'กำลังตัดต่อ'
    : 'สคริปต์พร้อม';

  const statusColor = isPosted ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isRendered ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isInProduction ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : 'bg-white/[0.05] text-slate-400 border-white/[0.08]';

  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);

  return (
    <div className={`border rounded-2xl p-3.5 sm:p-5 shadow-xl space-y-3.5 sm:space-y-4 animate-fadeIn transition-colors ${
      isLocked
        ? 'bg-[#090C14]/90 border-white/[0.06]'
        : 'bg-[#0B0F19] border-white/[0.1]'
    }`}>
      {/* 1. Header Bar */}
      <div className="flex flex-col xs:flex-row xs:items-center justify-between gap-2.5 pb-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-6 h-6 sm:w-7 sm:h-7 rounded-xl font-bold text-xs flex items-center justify-center shadow-sm flex-shrink-0 ${
            isLocked
              ? 'bg-slate-800 text-slate-400 border border-white/[0.08]'
              : 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950'
          }`}>
            {index + 1}
          </span>
          <h2 className={`text-xs sm:text-sm md:text-base font-bold truncate font-kanit ${
            isLocked ? 'text-slate-300' : 'text-white'
          }`}>
            {angle.angle_name}
          </h2>
          <span className={`text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${statusColor}`}>
            {statusLabel}
          </span>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1.5 self-end xs:self-auto flex-shrink-0">
          {!isEditing && (
            <>
              {!isLocked ? (
                <>
                  <button
                    type="button"
                    onClick={handleStartEdit}
                    className="px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-amber-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
                    title="แก้ไขบทพูดในกล่องนี้โดยตรง"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>แก้ไข</span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenFindReplace && onOpenFindReplace(index);
                    }}
                    className="px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-cyan-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
                    title="ค้นหาและแทนที่คำในสคริปต์"
                  >
                    <Replace className="w-3.5 h-3.5" />
                    <span className="hidden xs:inline sm:inline">แทนที่คำ</span>
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-400 text-xs font-bold select-none">
                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                  <span>ล็อกเนื้อหาแล้ว</span>
                </div>
              )}
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onCopy(lines.join('\n'), index); }}
                className="px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-[#25F4EE] text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
              >
                {copiedIndex === index
                  ? <><Check className="w-3.5 h-3.5 text-emerald-400" /> <span className="hidden xs:inline sm:inline">คัดลอกแล้ว</span></>
                  : <><Copy className="w-3.5 h-3.5" /> <span>คัดลอก</span></>}
              </button>
              {!isLocked && (
                <>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onRerollScript && onRerollScript(index); }}
                    className="px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-fuchsia-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
                    title="ให้ AI เขียนสคริปต์ใหม่สำหรับมุมนี้"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span className="hidden xs:inline sm:inline">รีสคริปต์ด้วย AI</span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onGenerateShotList && onGenerateShotList(index); }}
                    disabled={isGeneratingShotList}
                    className="px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-amber-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all disabled:opacity-50 disabled:cursor-wait"
                    title="สร้างแผนถ่าย (Shot List) จากจังหวะเสียงพากย์จริง"
                  >
                    {isGeneratingShotList
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <Clapperboard className="w-3.5 h-3.5" />}
                    <span className="hidden xs:inline sm:inline">แผนถ่าย</span>
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Locked Notice Banner */}
      {isLocked && (
        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center gap-2 text-xs text-slate-400">
          <Lock className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <span>
            {isPosted
              ? 'สคริปต์นี้โพสต์ลง TikTok แล้ว ระบบล็อกเนื้อหาและคลิปทั้งหมดเพื่อเก็บเป็นประวัติ'
              : 'สคริปต์นี้กำลังตัดต่อในไทม์ไลน์ ล็อกเนื้อหาและคลิปเพื่อความสอดคล้องกับไทม์ไลน์'}
          </span>
        </div>
      )}

      {/* 2. Hook Callout */}
      {angle.hook_title && !isEditing && (
        <div className="p-3 rounded-xl bg-gradient-to-r from-[#FE2C55]/15 via-black/40 to-[#25F4EE]/10 border border-[#FE2C55]/30 flex items-center gap-2.5 text-xs sm:text-sm font-bold text-white shadow-sm">
          <span className="text-lg">🎯</span>
          <div className="min-w-0 flex-1 font-kanit leading-snug">
            <span className="text-xs text-rose-400 font-semibold block">Hook พาดหัวเปิดคลิป:</span>
            <span>"{angle.hook_title}"</span>
          </div>
        </div>
      )}

      {/* 3. Script Lines or Editor */}
      {isEditing ? (
        <div className="space-y-3 p-3.5 rounded-xl bg-black/60 border border-[#25F4EE]/40 animate-fadeIn">
          <div className="flex items-center justify-between text-xs text-[#25F4EE] font-bold">
            <span className="flex items-center gap-1.5">
              <Edit3 className="w-3.5 h-3.5" />
              <span>แก้ไขบทพูดพากย์ (1 บรรทัด = 1 ท่อนซับไตเติล):</span>
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  const newLines = editText.split('\n').map(l => l.trim()).filter(Boolean);
                  if (newLines.length > 0) {
                    onSaveScript && onSaveScript(index, newLines, editHook.trim());
                  }
                  onOpenFindReplace && onOpenFindReplace(index);
                }}
                className="px-2 py-0.5 rounded-md bg-white/[0.08] hover:bg-white/[0.15] text-cyan-300 text-[11px] font-bold flex items-center gap-1 transition-all cursor-pointer"
                title="ค้นหาและแทนที่คำในสคริปต์นี้"
              >
                <Replace className="w-3 h-3" />
                <span>แทนที่คำ</span>
              </button>
              <span className="text-slate-400 text-xs font-mono">
                {editText.split('\n').filter(l => l.trim()).length} ท่อน
              </span>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300">Hook พาดหัวคลิป:</label>
            <input
              type="text"
              value={editHook}
              onChange={(e) => setEditHook(e.target.value)}
              placeholder="Hook พาดหัวคลิป..."
              className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg px-3 py-2 text-xs text-cyan-200 font-bold focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300">บทพูดพากย์แต่ละท่อน:</label>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={Math.max(6, editText.split('\n').length + 1)}
              className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg p-3 text-xs text-white font-mono leading-relaxed focus:outline-none resize-y"
              placeholder="พิมพ์บทพูดแต่ละท่อน เว้น 1 บรรทัดต่อ 1 ท่อน..."
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={handleCancelEdit}
              className="px-3.5 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-semibold cursor-pointer flex items-center gap-1 transition-all"
            >
              <X className="w-3.5 h-3.5" />
              <span>ยกเลิก</span>
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold shadow-md cursor-pointer flex items-center gap-1.5 active:scale-95 transition-all"
            >
              <Check className="w-3.5 h-3.5" />
              <span>บันทึกสคริปต์</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>บทพูดพากย์ ({lines.length} ท่อน):</span>
            {!isLocked && <span className="text-[11px] text-slate-500 italic">คลิกที่กล่องเพื่อแก้ไข</span>}
          </div>

          <div
            onClick={handleStartEdit}
            className={`p-3.5 rounded-xl border space-y-2.5 max-h-64 overflow-y-auto text-xs sm:text-sm leading-relaxed transition-all group/box ${
              isLocked
                ? 'bg-black/20 border-white/[0.06] text-slate-300 cursor-default'
                : 'bg-black/40 hover:bg-black/60 border-white/[0.06] hover:border-[#25F4EE]/30 text-slate-200 cursor-pointer'
            }`}
            title={isLocked ? 'ล็อกเนื้อหาแล้ว' : 'คลิกเพื่อแก้ไขสคริปต์'}
          >
            {lines.map((line, lIdx) => (
              <div key={lIdx} className="flex items-start gap-2.5 p-1.5 rounded-lg hover:bg-white/[0.03] transition-colors">
                <span className={`w-5 h-5 rounded-md font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  isLocked ? 'bg-white/[0.03] text-slate-400' : 'bg-white/[0.05] text-[#25F4EE]'
                }`}>
                  {lIdx + 1}
                </span>
                <span className="flex-1 text-slate-200 leading-relaxed font-kanit">{line}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Footage Attachment Section */}
      <div className="space-y-2 pt-2 border-t border-white/[0.08]">
        <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
          <span className="flex items-center gap-1.5 text-slate-300">
            <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>คลิปดิบที่แนบกับมุมนี้:</span>
          </span>
          <span className="text-xs font-mono">
            {selectedVideos.length > 0
              ? <span className="text-emerald-400 font-bold">เลือกแล้ว {selectedVideos.length} คลิป</span>
              : <span className="text-amber-400 font-bold">⚠️ ยังไม่ได้เลือกคลิป</span>}
          </span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
          {isPosted ? (
            <div
              className="flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold bg-emerald-500/10 border-emerald-500/30 text-emerald-300 select-none cursor-not-allowed"
              title="คลิปนี้โพสต์ลง TikTok แล้ว ล็อกรายการคลิปเก็บเป็นหลักฐาน"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>คลิปที่โพสต์แล้ว ({selectedVideos.length})</span>
            </div>
          ) : isInProduction ? (
            <div
              className="flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold bg-amber-500/10 border-amber-500/30 text-amber-300 select-none cursor-not-allowed"
              title="สคริปต์นี้กำลังตัดต่อจริงในไทม์ไลน์"
            >
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              <span>คลิปในไทม์ไลน์ ({selectedVideos.length})</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenMediaPicker && onOpenMediaPicker(index);
              }}
              className={`flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3.5 rounded-lg border text-xs font-bold transition-all cursor-pointer shadow-sm active:scale-95 ${
                selectedVideos.length > 0
                  ? 'bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border-[#25F4EE]/40 text-[#25F4EE]'
                  : 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-500/50 text-amber-300 animate-pulse'
              }`}
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>{selectedVideos.length > 0 ? `เปลี่ยน/เลือกคลิป (${videos.length})` : `เลือกคลิป (${videos.length})`}</span>
            </button>
          )}

          {selectedVideos.map(path => {
            const fileName = path.split(/[/\\]/).pop();
            return (
              <div
                key={path}
                className={`flex-shrink-0 flex items-center gap-1.5 py-1 px-2.5 rounded-lg border text-xs font-bold shadow-sm animate-fadeIn ${
                  isPosted
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : isInProduction
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-[#25F4EE]/15 border-[#25F4EE]/40 text-[#25F4EE]'
                }`}
              >
                <Film className={`w-3.5 h-3.5 ${isPosted ? 'text-emerald-400' : isInProduction ? 'text-amber-400' : 'text-[#25F4EE]'}`} />
                <span className="truncate max-w-[160px]">{fileName}</span>
                {isLocked ? (
                  <span className="p-0.5 text-slate-400/70 ml-0.5">
                    <Lock className="w-3 h-3" />
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleVideoForAngle && onToggleVideoForAngle(index, path);
                    }}
                    className="p-0.5 hover:bg-[#25F4EE]/30 rounded text-[#25F4EE] hover:text-white cursor-pointer ml-0.5 transition-colors"
                    title="ยกเลิกการผูกคลิปนี้"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Production Action Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
        {isRendered ? (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            {angle.video_url && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onPreviewExportVideo && onPreviewExportVideo(angle);
                }}
                className="py-3 sm:py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer active:scale-95 transition-all"
              >
                <Film className="w-4 h-4 text-cyan-400" />
                <span>ดูคลิปที่ Export แล้ว</span>
              </button>
            )}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (onOpenInTimeline) {
                    onOpenInTimeline(angle, index);
                  } else {
                    onSendToStudio(angle, index);
                  }
                }}
                className="flex-1 sm:flex-initial py-3 sm:py-2.5 px-5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/25 cursor-pointer active:scale-95 transition-all"
              >
                <Play className="w-4 h-4 fill-white text-white" />
                <span>เปิดดูในไทม์ไลน์</span>
                <ArrowRight className="w-3.5 h-3.5 text-white/80" />
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                className="py-3 sm:py-2.5 px-3.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 border border-white/[0.1] cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>ตัดใหม่</span>
              </button>
            </div>
          </div>
        ) : isInProduction ? (
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (onOpenInTimeline) {
                  onOpenInTimeline(angle, index);
                } else {
                  onSendToStudio(angle, index);
                }
              }}
              className="flex-1 sm:flex-initial py-3 sm:py-2.5 px-5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-amber-500/25 cursor-pointer active:scale-95 transition-all"
            >
              <Play className="w-4 h-4 fill-white text-white" />
              <span>เปิดทำต่อในไทม์ไลน์</span>
              <ArrowRight className="w-3.5 h-3.5 text-white/80" />
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
              className="py-3 sm:py-2.5 px-3.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 border border-white/[0.1] cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>ตัดใหม่</span>
            </button>
          </div>
        ) : selectedVideos.length === 0 ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenMediaPicker && onOpenMediaPicker(index);
            }}
            className="w-full sm:w-auto py-3 sm:py-2.5 px-5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-md cursor-pointer active:scale-95 transition-all"
          >
            <FolderOpen className="w-4 h-4 text-amber-400" />
            <span>เลือกคลิปก่อนส่งตัดต่อ</span>
            <ArrowRight className="w-3.5 h-3.5 text-amber-400/80" />
          </button>
        ) : (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
            className="w-full sm:w-auto py-3 sm:py-2.5 px-6 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
          >
            <Clapperboard className="w-4 h-4 text-white" />
            <span>เลือกมุมนี้ & ส่งตัดต่อ</span>
            <ArrowRight className="w-3.5 h-3.5 text-white/80" />
          </button>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 📝 ACCORDION SCRIPT ITEM (with Angle-Specific Footage Selector)
// ═══════════════════════════════════════════════════════════════════════
function ScriptAccordionItem({
  angle, index, isOpen, onToggle, onCopy, onSendToStudio, onOpenInTimeline, onPreviewExportVideo, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false,
  onOpenMediaPicker,
  onSaveScript, onOpenFindReplace, onRerollScript, onGenerateShotList,
  isGeneratingShotList = false
}) {
  const lines = Array.isArray(angle.script_lines)
    ? angle.script_lines
    : (angle.script_text ? angle.script_text.split('\n') : []);

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [editHook, setEditHook] = useState(angle.hook_title || '');

  // Keep editor state in sync if external lines change while not actively editing
  useEffect(() => {
    if (!isEditing) {
      setEditText(lines.join('\n'));
      setEditHook(angle.hook_title || '');
    }
  }, [lines, angle.hook_title, isEditing]);

  const curStatus = angle.status || 'scripted';
  const isPosted = curStatus === 'posted' || !!angle.posted_at;
  // ONLY rendered if an actual video export URL exists or status is posted!
  const isRendered = (curStatus === 'rendered' || isPosted) && (!!angle.video_url);
  const isInProduction = !isPosted && (curStatus === 'in_production' || (!!angle.project_name && !isRendered));
  const isLocked = isPosted || isInProduction;

  const handleStartEdit = (e) => {
    if (isLocked) return;
    e?.stopPropagation?.();
    setEditText(lines.join('\n'));
    setEditHook(angle.hook_title || '');
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setEditText(lines.join('\n'));
    setEditHook(angle.hook_title || '');
    setIsEditing(false);
  };

  const handleSave = () => {
    if (isLocked) return;
    const newLines = editText
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean);

    if (newLines.length === 0) return;

    onSaveScript && onSaveScript(index, newLines, editHook.trim());
    setIsEditing(false);
  };

  const statusLabel = isPosted ? 'โพสต์แล้ว'
    : isRendered ? 'ตัดเสร็จแล้ว'
    : isInProduction ? 'กำลังตัดต่อ'
    : 'สคริปต์พร้อม';

  const statusColor = isPosted ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isRendered ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    : isInProduction ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : 'bg-white/[0.05] text-slate-400 border-white/[0.08]';

  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);

  return (
    <div className={`rounded-xl border transition-all ${
      isOpen
        ? isLocked ? 'bg-[#090C14] border-white/[0.12] shadow-md' : 'bg-[#0B0F19] border-[#25F4EE]/30 shadow-md'
        : 'bg-[#080B11] border-white/[0.06] hover:border-white/[0.15]'
    }`}>
      {/* Collapsed Header Row */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left cursor-pointer group"
      >
        {/* Number Badge */}
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 ${
          isOpen
            ? isLocked ? 'bg-slate-800 text-slate-400 border border-white/[0.08]' : 'bg-gradient-to-tr from-[#25F4EE] to-blue-500 text-slate-950 shadow-sm'
            : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
        }`}>
          {index + 1}
        </span>

        {/* Name + Hook Preview */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-bold truncate ${isOpen ? 'text-white' : 'text-slate-200'}`}>
              {angle.angle_name}
            </span>
          </div>
          {!isOpen && angle.hook_title && (
            <p className="text-sm text-slate-500 truncate mt-0.5 font-kanit">
              "{angle.hook_title}"
            </p>
          )}
        </div>

        {/* Attached Video Count Badge (if any) */}
        {selectedVideos.length > 0 && !isOpen && (
          <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/20 flex-shrink-0">
            <Film className="w-3 h-3" />
            <span>{selectedVideos.length} คลิป</span>
          </span>
        )}

        {/* Status Badge */}
        <span className={`text-sm font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${statusColor}`}>
          {statusLabel}
        </span>

        {/* Quick Preview Button on Header when Exported */}
        {isRendered && angle.video_url && !isOpen && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onPreviewExportVideo && onPreviewExportVideo(angle);
            }}
            className="p-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/30 flex items-center justify-center flex-shrink-0 cursor-pointer transition-all"
            title="กดเพื่อดูคลิปวิดีโอที่ Export แล้ว"
          >
            <Play className="w-3 h-3 fill-cyan-300 text-cyan-300" />
          </button>
        )}

        {/* Chevron */}
        {isOpen
          ? <ChevronDown className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
          : <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white flex-shrink-0" />
        }
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="px-3 pb-3 space-y-3 border-t border-white/[0.06] pt-3 animate-fadeIn">
          {/* Locked Notice Banner */}
          {isLocked && (
            <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.08] flex items-center gap-2 text-xs text-slate-400">
              <Lock className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
              <span>
                {isPosted
                  ? 'สคริปต์นี้โพสต์ลง TikTok แล้ว ระบบล็อกเนื้อหาและคลิปทั้งหมดเพื่อเก็บเป็นประวัติ'
                  : 'สคริปต์นี้กำลังตัดต่อในไทม์ไลน์ ล็อกเนื้อหาและคลิปเพื่อความสอดคล้องกับไทม์ไลน์'}
              </span>
            </div>
          )}

          {/* Hook Highlight / Editor */}
          {angle.hook_title && !isEditing && (
            <div className={`p-2.5 rounded-lg border-l-[3px] text-xs sm:text-sm font-bold leading-snug ${
              isLocked
                ? 'bg-black/30 border-slate-600 text-slate-300'
                : 'bg-black/50 border-[#25F4EE] text-cyan-200'
            }`}>
              {angle.hook_title}
            </div>
          )}

          {/* Script Editing Box OR Read-Only Display */}
          {isEditing ? (
            <div className="space-y-2.5 p-3 rounded-xl bg-black/60 border border-[#25F4EE]/40 animate-fadeIn">
              <div className="flex items-center justify-between text-xs text-[#25F4EE] font-bold">
                <span className="flex items-center gap-1.5">
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>แก้ไขบทพูด (1 บรรทัด = 1 ท่อน):</span>
                </span>
                <span className="text-slate-400 text-[11px] font-mono">
                  {editText.split('\n').filter(l => l.trim()).length} ท่อน
                </span>
              </div>

              {/* Hook Input */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">Hook พาดหัวคลิป:</label>
                <input
                  type="text"
                  value={editHook}
                  onChange={(e) => setEditHook(e.target.value)}
                  placeholder="Hook พาดหัวคลิป..."
                  className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg px-2.5 py-1.5 text-xs text-cyan-200 font-bold focus:outline-none"
                />
              </div>

              {/* Script Textarea */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400">บทพูดพากย์แต่ละท่อน:</label>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={Math.max(5, editText.split('\n').length)}
                  className="w-full bg-[#080B11] border border-white/[0.12] focus:border-[#25F4EE] rounded-lg p-2.5 text-xs text-white font-mono leading-relaxed focus:outline-none resize-y"
                  placeholder="พิมพ์บทพูดแต่ละท่อน เว้น 1 บรรทัดต่อ 1 ท่อน..."
                />
                <p className="text-[10px] text-slate-500">
                  💡 แต่ละบรรทัดจะกลายเป็นซับไตเติล 1 ท่อนตามจังหวะเสียงพากย์อัตโนมัติ
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-semibold cursor-pointer flex items-center gap-1 transition-all"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>ยกเลิก</span>
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold shadow-md cursor-pointer flex items-center gap-1.5 active:scale-95 transition-all"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>บันทึกสคริปต์</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm text-slate-400 font-semibold">
                <span>บทพูดพากย์ ({lines.length} ท่อน):</span>
                <div className="flex items-center gap-2">
                  {isLocked ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-slate-400 text-[11px] font-bold">
                      <Lock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{isPosted ? 'โพสต์แล้ว (ล็อกเนื้อหา)' : 'กำลังตัดต่อ (ล็อกเนื้อหา)'}</span>
                    </span>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={handleStartEdit}
                        className="text-amber-300 hover:text-amber-200 hover:underline flex items-center gap-1 cursor-pointer font-bold text-xs"
                        title="แก้ไขบทพูดในกล่องนี้โดยตรง"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>แก้ไข</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenFindReplace && onOpenFindReplace(index);
                        }}
                        className="text-cyan-300 hover:text-cyan-200 hover:underline flex items-center gap-1 cursor-pointer font-bold text-xs"
                        title="ค้นหาและแทนที่คำในสคริปต์ทั้งหมด"
                      >
                        <Replace className="w-3.5 h-3.5" />
                        <span>แทนที่คำ</span>
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onCopy(lines.join('\n'), index); }}
                    className="text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer font-bold text-xs"
                  >
                    {copiedIndex === index
                      ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</>
                      : <><Copy className="w-3 h-3" /> คัดลอก</>}
                  </button>
                  {!isLocked && (
                    <>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onRerollScript && onRerollScript(index); }}
                        className="text-fuchsia-300 hover:text-fuchsia-200 hover:underline flex items-center gap-1 cursor-pointer font-bold text-xs"
                        title="ให้ AI เขียนสคริปต์ใหม่สำหรับมุมนี้"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>รีสคริปต์ด้วย AI</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onGenerateShotList && onGenerateShotList(index); }}
                        disabled={isGeneratingShotList}
                        className="text-amber-300 hover:text-amber-200 hover:underline flex items-center gap-1 cursor-pointer font-bold text-xs disabled:opacity-50 disabled:cursor-wait"
                        title="สร้างแผนถ่าย (Shot List) จากจังหวะเสียงพากย์จริง"
                      >
                        {isGeneratingShotList
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Clapperboard className="w-3.5 h-3.5" />}
                        <span>แผนถ่าย</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div
                onClick={handleStartEdit}
                className={`p-2.5 rounded-lg border space-y-1 max-h-44 overflow-y-auto font-mono text-xs leading-relaxed transition-colors group/box relative ${
                  isLocked
                    ? 'bg-black/20 border-white/[0.06] text-slate-300 cursor-default'
                    : 'bg-black/40 hover:bg-black/60 border border-white/[0.06] hover:border-white/[0.18] text-slate-200 cursor-pointer'
                }`}
                title={isLocked ? 'สคริปต์นี้ถูกล็อกเนื้อหาแล้ว' : 'คลิกที่กล่องนี้เพื่อแก้ไขสคริปต์ได้ทันที'}
              >
                {lines.map((line, lIdx) => (
                  <div key={lIdx} className="flex items-start gap-1.5">
                    <span className={`font-bold flex-shrink-0 ${isLocked ? 'text-slate-500' : 'text-[#25F4EE]'}`}>{lIdx + 1}.</span>
                    <span>{line}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 🎬 Angle-Specific Footage Selector */}
          <div className="space-y-1.5 pt-1 border-t border-white/[0.06]">
            <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
              <span className="flex items-center gap-1.5 text-slate-300">
                <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>คลิปดิบที่แนบกับมุมนี้:</span>
              </span>
              <span className="text-[11px] font-mono">
                {selectedVideos.length > 0
                  ? <span className="text-emerald-400 font-bold">เลือกแล้ว {selectedVideos.length} คลิป</span>
                  : <span className="text-amber-400/90 font-bold flex items-center gap-1">⚠️ ยังไม่ได้เลือกคลิป</span>}
              </span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
              {/* Media Picker Modal Trigger Button */}
              {isPosted ? (
                <div
                  className="flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold bg-emerald-500/10 border-emerald-500/30 text-emerald-300 select-none cursor-not-allowed"
                  title="คลิปนี้โพสต์ลง TikTok แล้ว ล็อกรายการคลิปเก็บเป็นหลักฐาน"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>คลิปที่โพสต์แล้ว ({selectedVideos.length})</span>
                </div>
              ) : isInProduction ? (
                <div
                  className="flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold bg-amber-500/10 border-amber-500/30 text-amber-300 select-none cursor-not-allowed"
                  title="สคริปต์นี้กำลังตัดต่อจริงในไทม์ไลน์ ล็อครายการคลิปตามไทม์ไลน์จริง"
                >
                  <Lock className="w-3.5 h-3.5 text-amber-400" />
                  <span>คลิปในไทม์ไลน์ ({selectedVideos.length})</span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenMediaPicker && onOpenMediaPicker(index);
                  }}
                  className={`flex-shrink-0 flex items-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-bold transition-all cursor-pointer shadow-sm active:scale-95 ${
                    selectedVideos.length > 0
                      ? 'bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border-[#25F4EE]/40 text-[#25F4EE]'
                      : 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-500/50 text-amber-300 animate-pulse'
                  }`}
                  title="เปิดคลังเลือกคลิปแบบ Grid พร้อมดูภาพพรีวิวและค้นหา"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>{selectedVideos.length > 0 ? `เปลี่ยน/เลือกคลิป (${videos.length})` : `เลือกคลิป (${videos.length})`}</span>
                </button>
              )}

              {/* Show Selected Footage Tags */}
              {selectedVideos.map(path => {
                const fileName = path.split(/[/\\]/).pop();
                return (
                  <div
                    key={path}
                    className={`flex-shrink-0 flex items-center gap-1.5 py-1 px-2.5 rounded-lg border text-xs font-bold shadow-sm animate-fadeIn ${
                      isPosted
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : isInProduction
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                        : 'bg-[#25F4EE]/15 border-[#25F4EE]/40 text-[#25F4EE]'
                    }`}
                  >
                    <Film className={`w-3.5 h-3.5 ${isPosted ? 'text-emerald-400' : isInProduction ? 'text-amber-400' : 'text-[#25F4EE]'}`} />
                    <span className="truncate max-w-[130px]">{fileName}</span>
                    {isLocked ? (
                      <span
                        className="p-0.5 text-slate-400/70 ml-0.5"
                        title={isPosted ? "คลิปนี้ถูกโพสต์แล้ว (ล็อก)" : "คลิปนี้กำลังใช้งานจริงในไทม์ไลน์ (ล็อก)"}
                      >
                        <Lock className="w-3 h-3" />
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleVideoForAngle && onToggleVideoForAngle(index, path);
                        }}
                        className="p-0.5 hover:bg-[#25F4EE]/30 rounded text-[#25F4EE] hover:text-white cursor-pointer ml-0.5 transition-colors"
                        title="ยกเลิกการผูกคลิปนี้"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                );
              })}

              {/* If no video explicitly chosen */}
              {selectedVideos.length === 0 && (
                <span className="text-[11px] text-amber-400/80 italic py-1">
                  (ต้องเลือกคลิปก่อนส่งตัดต่อ)
                </span>
              )}
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.06]">
            {isRendered ? (
              <>
                {angle.video_url && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onPreviewExportVideo && onPreviewExportVideo(angle);
                    }}
                    className="py-2 px-3.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-cyan-500/10 cursor-pointer active:scale-95 transition-all"
                    title={isPosted ? "เปิดดูวิดีโอที่โพสต์แล้วบน TikTok (หลักฐาน)" : "เปิดดูวิดีโอที่ตัดต่อและ Export เสร็จแล้ว (ตรวจ QC)"}
                  >
                    <Film className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{isPosted ? "ดูคลิปที่โพสต์แล้ว" : "ดูคลิปที่ Export แล้ว"}</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onOpenInTimeline) {
                      onOpenInTimeline(angle, index);
                    } else {
                      onSendToStudio(angle, index);
                    }
                  }}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-500/25 cursor-pointer active:scale-95 transition-all"
                  title={isPosted ? "เปิดดูวิดีโอในไทม์ไลน์หน้าตัดต่อ (โหมดล็อกสำหรับคลิปที่โพสต์แล้ว)" : "เปิดดูวิดีโอที่ตัดเสร็จแล้วในไทม์ไลน์ทันที"}
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>เปิดดูในไทม์ไลน์</span>
                  <ArrowRight className="w-3 h-3 text-white/80" />
                </button>
                {!isPosted && (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                    className="py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center gap-1 border border-white/[0.1] cursor-pointer"
                    title="ส่งไปปรับแต่งสคริปต์หรือตัดมุมนี้ใหม่"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>ตัดใหม่</span>
                  </button>
                )}
              </>
            ) : isInProduction ? (
              <>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onOpenInTimeline) {
                      onOpenInTimeline(angle, index);
                    } else {
                      onSendToStudio(angle, index);
                    }
                  }}
                  className="py-2 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-amber-500/25 cursor-pointer active:scale-95 transition-all"
                  title="เปิดตัดต่อในไทม์ไลน์"
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>เปิดทำต่อในไทม์ไลน์</span>
                  <ArrowRight className="w-3 h-3 text-white/80" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                  className="py-2 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-slate-300 text-xs font-medium flex items-center gap-1 border border-white/[0.1] cursor-pointer"
                  title="ส่งไปปรับแต่งสคริปต์หรือตัดมุมนี้ใหม่"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>ตัดใหม่</span>
                </button>
              </>
            ) : selectedVideos.length === 0 ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenMediaPicker && onOpenMediaPicker(index);
                }}
                className="py-2 px-4 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1.5 shadow-md cursor-pointer active:scale-95 transition-all"
                title="คลิกเพื่อเลือกคลิปสำหรับมุมนี้ก่อน"
              >
                <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                <span>เลือกคลิปก่อนส่งตัดต่อ</span>
                <ArrowRight className="w-3 h-3 text-amber-400/80" />
              </button>
            ) : (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onSendToStudio(angle, index); }}
                className="py-2 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
              >
                <Clapperboard className="w-3.5 h-3.5 text-white" />
                <span>เลือกมุมนี้ & ส่งตัดต่อ</span>
                <ArrowRight className="w-3 h-3 text-white/80" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 🌟 MAIN: ProductToClip Component (Redesigned Guided Workflow)
// ═══════════════════════════════════════════════════════════════════════
export default function ProductToClip({ status, videos = [], onRefresh, onApplyToStudio, onGoToGallery, selectedProductId, pendingFlowTaskVersion, consumePendingAngleId, consumePendingImageMetadataPreview }) {
  // Mirrors ExportGallery.jsx's mobileBaseUrl computation -- the LAN IP of
  // the Vite dev server a phone scanning a QR code needs to reach.
  const mobileBaseUrl = status?.mobile_url || (typeof window !== 'undefined' ? `https://${window.location.hostname}:5173` : '');

  // Input Mode & Active View
  const [showAddModal, setShowAddModal] = useState(false);
  const [inputMode, setInputMode] = useState('link');
  const [url, setUrl] = useState('');
  const [customKeyword, setCustomKeyword] = useState('');
  const [rawText, setRawText] = useState('');
  const [tiktokProductId, setTiktokProductId] = useState('');
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  // Active Product & Angles State
  const [productData, setProductData] = useState(null);
  // Up to MAX_ANALYZE_IMAGES reference screenshots (product page, spec sheet,
  // reviews) the AI reads directly via vision when generating angles -- not
  // just a single cover thumbnail. Each entry: { path, previewUrl, name }.
  const [selectedImages, setSelectedImages] = useState([]);
  const [angles, setAngles] = useState([]);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [openAngleIdx, setOpenAngleIdx] = useState(0); // Accordion: which angle is expanded
  const [previewExportAngle, setPreviewExportAngle] = useState(null); // Dialog: preview exported MP4 video
  const { toastMessage, showToast, hideToast } = useToast();
  const { refreshTrigger, toggleActivityDrawer } = useTaskManager();

  // History / All Products & Scalable Catalog
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState(selectedProductId || null);
  const selectedHistoryIdRef = useRef(selectedProductId || null);
  const previousExternalProductIdRef = useRef(null);
  const historyRequestRef = useRef(0);
  const [productSearch, setProductSearch] = useState('');
  const [productFilter, setProductFilter] = useState('all'); // 'all' | 'in_progress' | 'completed'
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [showMetadataModal, setShowMetadataModal] = useState(false);
  const [savingProductImages, setSavingProductImages] = useState(false);
  const [refreshingProductSource, setRefreshingProductSource] = useState(false);
  const [productSourcePreview, setProductSourcePreview] = useState(null);
  const [savingProductMetadata, setSavingProductMetadata] = useState(false);
  const [removingProductImageIndex, setRemovingProductImageIndex] = useState(null);
  const productImageInputRef = useRef(null);
  const pendingImageMetadataPreviewRef = useRef(null);
  const [isStep1Collapsed, setIsStep1Collapsed] = useState(false);
  const [deleteTargetProduct, setDeleteTargetProduct] = useState(null);
  const [isDeletingProduct, setIsDeletingProduct] = useState(false);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'accordion'
  const [showProductStrip, setShowProductStrip] = useState(false);

  // Filtered Products for 100+ items
  const filteredHistory = useMemo(() => {
    let list = historyList || [];
    const q = (productSearch || '').trim().toLowerCase();
    if (q) {
      list = list.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) ||
        (p.price || '').toLowerCase().includes(q)
      );
    }
    if (productFilter === 'in_progress') {
      list = list.filter(p => {
        const done = (p.angles || []).filter(a => a.status === 'posted' || a.status === 'rendered').length;
        return done < (p.angles?.length || 4);
      });
    } else if (productFilter === 'completed') {
      list = list.filter(p => {
        const done = (p.angles || []).filter(a => a.status === 'posted' || a.status === 'rendered').length;
        return done >= (p.angles?.length || 4) && ((p.angles?.length || 0) > 0);
      });
    }
    return list;
  }, [historyList, productSearch, productFilter]);

  // Angle Count Selection
  const [angleCount, setAngleCount] = useState(7); // Default: 7 (Sweet Spot)
  // Duration Selection (independent of angleCount -- both apply together)
  const [duration, setDuration] = useState('30s'); // Default matches backend default

  // Reroll-Script Modal State (per-angle AI script reroll, separate from video reroll)
  const [rerollModalAngleIdx, setRerollModalAngleIdx] = useState(null); // null = closed
  const [rerollDuration, setRerollDuration] = useState('30s');
  const [rerollExtraBeats, setRerollExtraBeats] = useState([]);
  const [rerollingScript, setRerollingScript] = useState(false);
  // Tracks the angle_id of an in-flight reroll so the completion refresh
  // (driven by refreshTrigger, same as the scrape-and-plan flow) can restore
  // focus to that angle instead of resetting to angle 0 like a fresh product load.
  const pendingRerollAngleIdRef = useRef(null);

  // Shot-list generation: self-contained (polls its own task_id directly via
  // getTaskStatus) rather than piggybacking on the reroll-script /
  // refreshTrigger flow above, since it doesn't rewrite the angle's script --
  // it only produces a new, separate record for the modal below to display.
  const [shotListAngleIdx, setShotListAngleIdx] = useState(null); // angle this modal is open for
  const [generatingShotListIdx, setGeneratingShotListIdx] = useState(null); // angle currently generating
  const [shotListResult, setShotListResult] = useState(null);

  // Edit TikTok Product ID Modal State (Backlog & Post-creation support)
  const [showEditTiktokIdModal, setShowEditTiktokIdModal] = useState(false);
  const [editTiktokIdInput, setEditTiktokIdInput] = useState('');
  const [resolvingTiktokId, setResolvingTiktokId] = useState(false);
  const [savingTiktokId, setSavingTiktokId] = useState(false);

  const handleOpenEditTiktokIdModal = () => {
    if (!productData) return;
    setEditTiktokIdInput(productData.tiktok_product_id || '');
    setShowEditTiktokIdModal(true);
  };

  const handleResolveAndSetId = async (inputVal) => {
    const trimmed = (inputVal || '').trim();
    if (!trimmed) return;
    if (/^\d{10,}$/.test(trimmed)) {
      setEditTiktokIdInput(trimmed);
      return;
    }
    setResolvingTiktokId(true);
    try {
      const res = await resolveTiktokProductId(trimmed);
      if (res?.success && res?.product_id) {
        setEditTiktokIdInput(res.product_id);
        showToast(`ดึงรหัสสินค้าสำเร็จ: ${res.product_id}`);
      } else {
        showToast('ไม่พบรหัสสินค้า TikTok ในลิงก์นี้ — กรุณาใส่รหัสตัวเลขโดยตรง', 'warning');
      }
    } catch (e) {
      showToast('ไม่สามารถดึงรหัสจากลิงก์ได้: ' + (e.message || ''), 'error');
    } finally {
      setResolvingTiktokId(false);
    }
  };

  const handleSaveTiktokId = async () => {
    if (!productData) return;
    setSavingTiktokId(true);
    try {
      let finalId = editTiktokIdInput.trim();
      if (finalId && !/^\d{10,}$/.test(finalId) && (finalId.startsWith('http://') || finalId.startsWith('https://') || finalId.includes('tiktok.com'))) {
        try {
          const res = await resolveTiktokProductId(finalId);
          if (res?.success && res?.product_id) {
            finalId = res.product_id;
          }
        } catch (_) {}
      }

      const patchVal = finalId || null;
      await updateProduct(productData.id, { tiktok_product_id: patchVal });

      setProductData(prev => prev ? { ...prev, tiktok_product_id: patchVal } : prev);
      setHistoryList(prev => prev.map(p => p.id === productData.id ? { ...p, tiktok_product_id: patchVal } : p));

      setShowEditTiktokIdModal(false);
      showToast(patchVal
        ? `บันทึกรหัส TikTok ID (${patchVal}) ให้ทั้ง ${productData.angles?.length || 0} สคริปต์แล้ว`
        : 'ปรับเป็นใช้ชื่อสินค้าค้นหาปักตะกร้าแทนแล้ว');
    } catch (err) {
      showToast('บันทึกไม่สำเร็จ: ' + (err.message || ''), 'error');
    } finally {
      setSavingTiktokId(false);
    }
  };

  // Media Picker Modal State
  const [pickerModalOpen, setPickerModalOpen] = useState(false);
  const [pickerAngleIndex, setPickerAngleIndex] = useState(0);

  // Batch Find & Replace Modal State
  const [findReplaceOpen, setFindReplaceOpen] = useState(false);
  const [findReplaceAngleIdx, setFindReplaceAngleIdx] = useState(0);

  // Uploading Screenshot/Image
  const [uploadingImg, setUploadingImg] = useState(false);
  const fileInputRef = useRef(null);

  // Load History on Mount or when background task finishes
  const loadHistory = async (targetId = null, isStale = () => false) => {
    const requestId = ++historyRequestRef.current;
    setLoadingHistory(true);
    try {
      const res = await getProducts();
      // React StrictMode's dev-only double-invoke of mount effects fires
      // this effect (and its loadHistory call) twice in a row for the same
      // mount; both calls' selectProduct() would otherwise race to consume
      // pendingRerollAngleIdRef, with whichever resolves second always
      // winning and resetting the just-restored angle back to index 0. The
      // isStale() check lets the effect's own cleanup mark its first
      // in-flight call obsolete once StrictMode's second invoke starts.
      if (isStale() || requestId !== historyRequestRef.current) return;
      if (res.products) {
        setHistoryList(res.products);
        if (res.products.length > 0) {
          const effectiveId = targetId || selectedHistoryIdRef.current;
          const current = resolveSelectedProduct(res.products, effectiveId);
          if (current) selectProduct(current);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      if (requestId === historyRequestRef.current) setLoadingHistory(false);
    }
  };

  useEffect(() => {
    // A reroll jump from the Activity Center's task list carries its angle
    // id through App-level ref state (consumePendingAngleId), read-and-cleared
    // once here. Because useRef persists across React StrictMode's dev-only
    // double-invoke of this effect (same fiber, only effects/cleanups
    // re-run), pendingRerollAngleIdRef.current -- set on the first invoke --
    // is still there for the second invoke to see even though
    // consumePendingAngleId() itself only returns non-null once.
    const pendingId = consumePendingAngleId?.();
    if (pendingId) {
      pendingRerollAngleIdRef.current = pendingId;
    }
    const pendingImagePreview = consumePendingImageMetadataPreview?.();
    if (pendingImagePreview) {
      pendingImageMetadataPreviewRef.current = pendingImagePreview;
    }
    // Both StrictMode invokes call loadHistory(), each racing to resolve and
    // call selectProduct() (which reads-and-clears the ref above) -- without
    // this guard, whichever resolves *second* always wins, and if that's the
    // stale first invoke's call, it sees an already-cleared ref and stomps
    // the just-restored angle back to index 0. Marking each invoke's own
    // call stale from its own cleanup ensures only the surviving invoke's
    // call is allowed to apply its result.
    let stale = false;
    const targetId = resolveHistoryTargetId(
      selectedProductId,
      previousExternalProductIdRef.current,
      selectedHistoryIdRef.current,
    );
    if (selectedProductId && selectedProductId !== previousExternalProductIdRef.current) {
      selectedHistoryIdRef.current = selectedProductId;
    }
    previousExternalProductIdRef.current = selectedProductId || null;
    loadHistory(targetId, () => stale);
    const onFocus = () => loadHistory();
    window.addEventListener('focus', onFocus);
    return () => {
      stale = true;
      window.removeEventListener('focus', onFocus);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProductId, refreshTrigger, pendingFlowTaskVersion]);

  const selectProduct = (item) => {
    if (!item) return;
    selectedHistoryIdRef.current = item.id;
    setSelectedHistoryId(item.id);
    setProductData({
      id: item.id,
      name: item.name,
      title: item.name,
      url: item.url,
      platform: item.platform || '',
      category: item.category || '',
      specs: item.specs || [],
      pain_points: item.pain_points || [],
      selling_points: item.selling_points || [],
      target_buyer: item.target_buyer || '',
      description: item.description || '',
      raw_text: item.raw_text || '',
      price_note: item.price_note || '',
      status: item.status || 'scripted',
      images: item.images || (item.thumbnail ? [{ rel_path: item.thumbnail, name: 'thumb' }] : []),
      thumbnail: item.thumbnail || '',
      tiktok_product_id: item.tiktok_product_id || '',
      product_code: item.product_code || '',
      metadata_source: item.metadata_source || '',
      source_warning: item.source_warning || '',
      created_at: item.created_at || '',
      updated_at: item.updated_at || '',
    });
    const nextAngles = item.angles || [];
    setAngles(nextAngles);
    const pendingImagePreview = pendingImageMetadataPreviewRef.current;
    if (pendingImagePreview?.product_id === item.id) {
      setProductSourcePreview(pendingImagePreview.preview || pendingImagePreview);
      setShowMetadataModal(true);
      pendingImageMetadataPreviewRef.current = null;
    }
    // Normally reset to the first angle on a fresh product load -- but if a
    // script reroll just completed (pendingRerollAngleIdRef set right before
    // this reload was triggered), restore focus to that same angle instead
    // of yanking the user back to angle 0 right after they asked to reroll
    // a specific one. Checked here (not a separate effect keyed on
    // refreshTrigger) so there's no race with this same reload's own
    // async completion -- by the time selectProduct runs, nextAngles is the
    // authoritative freshly-loaded list.
    const pendingId = pendingRerollAngleIdRef.current;
    pendingRerollAngleIdRef.current = null;
    const restoredIdx = pendingId ? nextAngles.findIndex(a => a.angle_id === pendingId) : -1;
    setOpenAngleIdx(restoredIdx >= 0 ? restoredIdx : 0);
    setSelectedImages([]);
  };

  const handleAngleStatusChange = async (angleId, nextStatus) => {
    if (!productData?.id) return;
    try {
      await updateAngleStatus(productData.id, angleId, nextStatus);
      setAngles(prev => prev.map(a => a.angle_id === angleId ? { ...a, status: nextStatus } : a));
      const res = await getProducts();
      if (res.products) setHistoryList(res.products);
      showToast(`อัปเดตสถานะสคริปต์เรียบร้อยแล้ว`);
    } catch (err) {
      showToast('ไม่สามารถอัปเดตสถานะได้: ' + err.message, 'error');
    }
  };

  const handleSaveScript = async (angleIdx, newLines, newHookTitle) => {
    if (!productData?.id) return;
    const targetAngle = angles[angleIdx];
    if (!targetAngle) return;

    const nextAngles = angles.map((ang, idx) => {
      if (idx !== angleIdx) return ang;
      const updated = {
        ...ang,
        script_lines: newLines,
        script_text: newLines.join('\n'),
        tts_lines: newLines,
      };
      if (typeof newHookTitle === 'string' && newHookTitle) {
        updated.hook_title = newHookTitle;
        updated.tts_hook_title = newHookTitle.replace(/^[^\w\s\u0E00-\u0E7F]+/, '').trim();
      }
      return updated;
    });

    setAngles(nextAngles);

    try {
      const res = await updateProduct(productData.id, { angles: nextAngles });
      if (res.product) {
        setProductData(prev => ({ ...prev, ...res.product, angles: res.product.angles }));
        setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
      }
      showToast(`บันทึกสคริปต์มุมที่ ${angleIdx + 1} (${targetAngle.angle_name || 'สคริปต์'}) เรียบร้อยแล้ว`);
    } catch (err) {
      console.error('Failed to save script:', err);
      showToast('ไม่สามารถบันทึกสคริปต์ได้: ' + err.message, 'error');
    }
  };

  const handleApplyFindReplace = async ({ findText, replaceText, scope, updatedAngles, matchCount, affectedAnglesCount }) => {
    if (!productData?.id) return;
    setAngles(updatedAngles);

    try {
      const res = await updateProduct(productData.id, { angles: updatedAngles });
      if (res.product) {
        setProductData(prev => ({ ...prev, ...res.product, angles: res.product.angles }));
        setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
      }
      showToast(`แทนที่คำว่า "${findText}" เป็น "${replaceText}" สำเร็จทั้งหมด ${matchCount} จุด ใน ${affectedAnglesCount} สคริปต์!`);
    } catch (err) {
      console.error('Failed to replace words in scripts:', err);
      showToast('ไม่สามารถแทนที่คำในสคริปต์ได้: ' + err.message, 'error');
    }
  };

  // ── Per-Angle AI Script Reroll (separate from the video-render reroll system) ──
  const handleOpenRerollScriptModal = (angleIdx) => {
    const target = angles[angleIdx];
    if (!target) return;
    const existingDuration = target.duration || '30s';
    setRerollDuration(existingDuration);
    setRerollExtraBeats(
      Array.isArray(target.extra_beats) ? target.extra_beats : defaultExtraBeatsForDuration(existingDuration)
    );
    setRerollModalAngleIdx(angleIdx);
  };

  const handleCloseRerollScriptModal = () => {
    if (rerollingScript) return; // don't let a stray click drop an in-flight request's modal state
    setRerollModalAngleIdx(null);
  };

  const handleToggleRerollExtraBeat = (val) => {
    setRerollExtraBeats(prev => prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val]);
  };

  const handleSubmitRerollScript = async () => {
    if (!productData?.id || rerollModalAngleIdx === null) return;
    const targetAngle = angles[rerollModalAngleIdx];
    if (!targetAngle?.angle_id) return;

    setRerollingScript(true);
    try {
      const res = await rerollAngleScript(productData.id, targetAngle.angle_id, {
        duration: rerollDuration,
        extra_beats: rerollExtraBeats,
      });
      if (res.success && res.task_id) {
        pendingRerollAngleIdRef.current = targetAngle.angle_id;
        setRerollModalAngleIdx(null);
        showToast(`🚀 กำลังรีสคริปต์มุม "${targetAngle.angle_name || ''}" ด้วย AI ในเบื้องหลัง...`);
      } else {
        showToast('ไม่สามารถเริ่มรีสคริปต์ได้', 'error');
      }
    } catch (err) {
      console.error('Failed to reroll script:', err);
      showToast('ไม่สามารถรีสคริปต์ได้: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setRerollingScript(false);
    }
  };

  // ── Shot-list generation (per-beat filming plan from real TTS timing) ──
  // Runs the actual generate-task + poll cycle. Only called when there's no
  // existing shot list yet, or the user explicitly asks to regenerate one
  // (via the modal's "สร้างใหม่" action) -- never as the default click
  // behavior, since re-running this re-synthesizes the voiceover from
  // scratch every time.
  const runShotListGeneration = async (angleIdx, targetAngle) => {
    setGeneratingShotListIdx(angleIdx);
    try {
      const res = await generateShotList(productData.id, targetAngle.angle_id);
      if (!res.success || !res.task_id) {
        showToast('ไม่สามารถเริ่มสร้างแผนถ่ายได้', 'error');
        return;
      }
      // Self-poll rather than waiting on TaskContext's global refreshTrigger
      // -- this task never changes the angle/product record, so nothing
      // outside this modal needs to know about it.
      let result = null;
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const task = await getTaskStatus(res.task_id);
        if (task.status === 'completed') {
          result = task.result;
          break;
        }
        if (task.status === 'failed') {
          showToast('สร้างแผนถ่ายไม่สำเร็จ: ' + (task.error || ''), 'error');
          return;
        }
      }
      if (!result) {
        showToast('สร้างแผนถ่ายใช้เวลานานเกินไป กรุณาลองใหม่', 'error');
        return;
      }
      setShotListResult({ angle: targetAngle, ...result });
      setShotListAngleIdx(angleIdx);
    } catch (err) {
      console.error('Failed to generate shot list:', err);
      showToast('ไม่สามารถสร้างแผนถ่ายได้: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setGeneratingShotListIdx(null);
    }
  };

  // Default click: reopen the already-generated shot list instantly if one
  // exists (no re-run) -- only falls through to a fresh generation the
  // first time, when none exists yet.
  const handleGenerateShotList = async (angleIdx) => {
    if (!productData?.id) return;
    const targetAngle = angles[angleIdx];
    if (!targetAngle?.angle_id) return;

    setGeneratingShotListIdx(angleIdx);
    try {
      const existing = await getShotList(productData.id, targetAngle.angle_id);
      setShotListResult({ angle: targetAngle, ...existing });
      setShotListAngleIdx(angleIdx);
      setGeneratingShotListIdx(null);
    } catch {
      // 404 (or any other lookup failure) -- no shot list yet, generate one.
      await runShotListGeneration(angleIdx, targetAngle);
    }
  };

  const handleRegenerateShotList = () => {
    if (shotListAngleIdx === null) return;
    const targetAngle = angles[shotListAngleIdx];
    if (!targetAngle?.angle_id) return;
    runShotListGeneration(shotListAngleIdx, targetAngle);
  };

  const handleDeleteHistory = (target) => {
    if (!target) return;
    setDeleteTargetProduct(target);
  };

  const confirmDeleteProduct = async () => {
    if (!deleteTargetProduct?.id) return;
    setIsDeletingProduct(true);
    try {
      await deleteProduct(deleteTargetProduct.id);
      showToast('ลบสินค้าและสคริปต์ทั้งหมดเรียบร้อยแล้ว');
      const res = await getProducts();
      const updated = res.products || [];
      setHistoryList(updated);
      if (updated.length > 0) {
        selectProduct(updated[0]);
      } else {
        setProductData(null);
        setAngles([]);
      }
      setDeleteTargetProduct(null);
    } catch (err) {
      showToast('ลบไม่สำเร็จ: ' + err.message, 'error');
    } finally {
      setIsDeletingProduct(false);
    }
  };

  const handleScrapeAndPlan = async () => {
    if (inputMode === 'link' && !url.trim()) {
      showToast('กรุณากรอกลิงก์สินค้าก่อนครับ', 'warning');
      return;
    }
    if (inputMode === 'text' && !customKeyword.trim() && !rawText.trim()) {
      showToast('กรุณาระบุชื่อสินค้าหรือสเปกก่อนครับ', 'warning');
      return;
    }
    if (inputMode === 'image' && selectedImages.length === 0 && !customKeyword.trim()) {
      showToast('กรุณาอัปโหลดรูปภาพหรือระบุชื่อสินค้าก่อนครับ', 'warning');
      return;
    }

    setFetching(true);
    setFetchError(null);

    try {
      const payload = {
        url: inputMode === 'link' ? url : undefined,
        raw_text: inputMode === 'text' ? `${customKeyword}\n${rawText}` : undefined,
        custom_keyword: customKeyword || undefined,
        image_paths: inputMode === 'image' ? selectedImages.map((img) => img.path) : undefined,
        angle_count: angleCount,
        duration,
        tiktok_product_id: tiktokProductId.trim() || undefined,
      };

      // Non-blocking async background task execution
      const res = await scrapeAndPlanProductAsync(payload);
      if (res.success && res.task_id) {
        setShowAddModal(false);
        setUrl('');
        setCustomKeyword('');
        setRawText('');
        setTiktokProductId('');
        setSelectedImages([]);
        showToast(`🚀 เริ่มวิเคราะห์สินค้า & สร้าง ${angleCount} สคริปต์ในเบื้องหลังแล้ว — สามารถเปลี่ยนหน้าหรือทำงานต่อได้ทันที`);
      } else {
        // Fallback to sync if async did not return task_id
        const syncRes = await scrapeAndPlanProduct(payload);
        if (syncRes.success && syncRes.product) {
          selectProduct(syncRes.product);
          setShowAddModal(false);
          setUrl('');
          setCustomKeyword('');
          setRawText('');
          setTiktokProductId('');
          setSelectedImages([]);
          await loadHistory();
          showToast(`AI วิเคราะห์และสร้าง ${angleCount} สคริปต์สำเร็จแล้ว`);
        }
      }
    } catch (err) {
      console.error('Scrape and plan error:', err);
      setFetchError(err.friendlyMessage || err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการวิเคราะห์สินค้า');
    } finally {
      setFetching(false);
    }
  };

  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    // The video branch below (drop a clip here to set it as this product's
    // default footage) only ever meant one file at a time -- keep that
    // exactly as it was. Multi-select only applies to the image/reference
    // path this function otherwise serves.
    const isVideoFile = (f) => f.type.startsWith('video/') || /\.(mp4|mov|webm|mkv|avi)$/i.test(f.name);
    if (files.length === 1 && isVideoFile(files[0])) {
      const file = files[0];
      setUploadingImg(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('target_dir', 'raw');
      try {
        const res = await uploadFile(formData);
        if (res.file && productData?.id) {
          const filePath = res.file.rel_path || res.file.path;
          const updateRes = await setDefaultVideosForProduct(productData.id, [filePath]);
          if (updateRes.product) {
            setProductData(updateRes.product);
            setAngles(updateRes.product.angles || []);
            setHistoryList(prev => prev.map(p => p.id === updateRes.product.id ? updateRes.product : p));
          }
          onRefresh && onRefresh();
          showToast(`แนบคลิป "${file.name}" เป็นคลิปหลักเริ่มต้นให้ทุกสคริปต์เรียบร้อยแล้ว`);
        }
      } catch (err) {
        showToast('อัปโหลดไม่สำเร็จ: ' + (err.friendlyMessage || err.message), 'error');
      } finally {
        setUploadingImg(false);
        if (e.target) e.target.value = '';
      }
      return;
    }

    const room = MAX_ANALYZE_IMAGES - selectedImages.length;
    if (room <= 0) {
      showToast(`แนบได้สูงสุด ${MAX_ANALYZE_IMAGES} รูปต่อครั้งครับ`, 'warning');
      if (e.target) e.target.value = '';
      return;
    }
    const toUpload = files.filter((f) => !isVideoFile(f)).slice(0, room);
    if (files.length > toUpload.length) {
      showToast(`แนบได้สูงสุด ${MAX_ANALYZE_IMAGES} รูปต่อครั้ง — เก็บแค่ ${toUpload.length} รูปแรก`, 'warning');
    }

    setUploadingImg(true);
    try {
      const uploaded = [];
      for (const file of toUpload) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_dir', 'inbox');
        const res = await uploadFile(formData);
        if (res.file) {
          uploaded.push({
            path: res.file.rel_path || res.file.path,
            previewUrl: toMediaUrl(res.file.rel_path || res.file.path),
            name: file.name,
          });
        }
      }
      if (uploaded.length) {
        setSelectedImages((prev) => [...prev, ...uploaded]);
        showToast(uploaded.length > 1 ? `อัปโหลดรูปภาพ ${uploaded.length} รูปเรียบร้อยแล้ว` : 'อัปโหลดรูปภาพเรียบร้อยแล้ว');
      }
    } catch (err) {
      showToast('อัปโหลดไม่สำเร็จ: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setUploadingImg(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleProductReferenceUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length || !productData?.id) return;

    const isImageFile = (file) => file.type.startsWith('image/') || /\.(heic|heif|jpe?g|png|webp|gif|avif)$/i.test(file.name);
    const existingImages = Array.isArray(productData.images) ? productData.images : [];
    const room = MAX_PRODUCT_REFERENCE_IMAGES - existingImages.length;
    if (room <= 0) {
      showToast(`เก็บรูปอ้างอิงได้สูงสุด ${MAX_PRODUCT_REFERENCE_IMAGES} รูปต่อสินค้า`, 'warning');
      if (e.target) e.target.value = '';
      return;
    }

    const toUpload = files.filter(isImageFile).slice(0, room);
    if (!toUpload.length) {
      showToast('กรุณาเลือกไฟล์รูปภาพเท่านั้น', 'warning');
      if (e.target) e.target.value = '';
      return;
    }
    if (files.length > toUpload.length) {
      showToast(`แนบได้สูงสุด ${MAX_PRODUCT_REFERENCE_IMAGES} รูปต่อสินค้า — เก็บเฉพาะไฟล์รูปที่ยังมีพื้นที่`, 'warning');
    }

    setSavingProductImages(true);
    try {
      const uploaded = [];
      for (const file of toUpload) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_dir', 'inbox');
        const res = await uploadFile(formData);
        if (res.file) {
          const path = res.file.rel_path || res.file.path;
          uploaded.push({
            path,
            rel_path: res.file.rel_path || path,
            previewUrl: toMediaUrl(path),
            name: file.name,
            source: 'user_upload',
          });
        }
      }

      if (uploaded.length) {
        const nextImages = [...existingImages, ...uploaded];
        const updateRes = await updateProduct(productData.id, { images: nextImages });
        const savedProduct = updateRes.product || { ...productData, images: nextImages };
        setProductData(prev => ({ ...prev, ...savedProduct, images: savedProduct.images || nextImages }));
        setHistoryList(prev => prev.map(p => p.id === productData.id ? { ...p, ...savedProduct, images: savedProduct.images || nextImages } : p));
        showToast(uploaded.length > 1 ? `บันทึกรูปอ้างอิง ${uploaded.length} รูปให้สินค้าแล้ว` : 'บันทึกรูปอ้างอิงให้สินค้าแล้ว');
      }
    } catch (err) {
      showToast('บันทึกรูปอ้างอิงไม่สำเร็จ: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setSavingProductImages(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleRemoveProductImage = async (imageIndex) => {
    if (!productData?.id) return;
    const existingImages = Array.isArray(productData.images) ? productData.images : [];
    if (!existingImages[imageIndex]) return;

    setRemovingProductImageIndex(imageIndex);
    try {
      const nextImages = existingImages.filter((_, index) => index !== imageIndex);
      const updateRes = await updateProduct(productData.id, { images: nextImages });
      const savedProduct = updateRes.product || { ...productData, images: nextImages };
      setProductData(prev => ({ ...prev, ...savedProduct, images: savedProduct.images || nextImages }));
      setHistoryList(prev => prev.map(p => p.id === productData.id ? { ...p, ...savedProduct, images: savedProduct.images || nextImages } : p));
      showToast('เอารูปออกจากข้อมูลสินค้าแล้ว (ไฟล์ต้นฉบับยังอยู่ในคลังไฟล์)');
    } catch (err) {
      showToast('เอารูปออกไม่สำเร็จ: ' + (err.friendlyMessage || err.message), 'error');
    } finally {
      setRemovingProductImageIndex(null);
    }
  };

  const handlePreviewProductSource = async ({ url } = {}) => {
    if (!productData?.id || !url?.trim()) return;

    setRefreshingProductSource(true);
    setProductSourcePreview(null);
    try {
      const response = await previewProductSource(productData.id, { url: url.trim() });
      setProductSourcePreview(response);
      showToast('ตรวจข้อมูลใหม่เรียบร้อยแล้ว เลือกฟิลด์ที่ต้องการบันทึกได้เลย');
    } catch (err) {
      showToast('อ่านรายละเอียดจาก URL ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setRefreshingProductSource(false);
    }
  };

  const handlePreviewProductImages = async () => {
    if (!productData?.id) return;

    setRefreshingProductSource(true);
    setProductSourcePreview(null);
    try {
      const response = await previewProductImageMetadataAsync(productData.id);
      if (!response?.task_id) {
        throw new Error('ระบบไม่คืนรหัสงานเบื้องหลัง');
      }
      setShowMetadataModal(false);
      showToast('เริ่มอ่านข้อมูลจากรูปในเบื้องหลังแล้ว — ปิดหน้านี้ได้ และดูผลจาก Activity Center เมื่อเสร็จ');
    } catch (err) {
      showToast('อ่าน metadata จากรูปไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setRefreshingProductSource(false);
    }
  };

  const handleApplyProductSource = async ({ url, fields, overrides }) => {
    if (!productData?.id || !url || !fields?.length) return;

    setRefreshingProductSource(true);
    try {
      let response;
      if (productSourcePreview?.source_type === 'vision_image') {
        const incoming = productSourcePreview.incoming || {};
        const imagePatch = Object.fromEntries(
          fields
            .filter((field) => !['url', 'images'].includes(field))
            .map((field) => [field, overrides?.[field] ?? incoming[field]])
        );
        response = await updateProduct(productData.id, {
          ...imagePatch,
          metadata_source: 'vision_image',
          source_warning: productSourcePreview.source_warning || '',
        });
      } else {
        response = await refreshProductSource(productData.id, { url, fields, overrides });
      }
      if (response.product) {
        const refreshed = response.product;
        setProductData(prev => ({ ...prev, ...refreshed }));
        setAngles(refreshed.angles || angles);
        setHistoryList(prev => prev.map(item => item.id === refreshed.id ? refreshed : item));
      }
      setProductSourcePreview(null);
    } catch (err) {
      showToast('บันทึกข้อมูลใหม่ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setRefreshingProductSource(false);
    }
  };

  const handleSaveProductMetadata = async (changes) => {
    if (!productData?.id) return;

    setSavingProductMetadata(true);
    try {
      const response = await updateProduct(productData.id, changes);
      const saved = response.product || { ...productData, ...changes };
      setProductData(prev => ({ ...prev, ...saved }));
      setHistoryList(prev => prev.map(item => item.id === saved.id ? { ...item, ...saved } : item));
    } catch (err) {
      showToast('บันทึก metadata ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
      throw err;
    } finally {
      setSavingProductMetadata(false);
    }
  };

  const handleOpenMediaPicker = (idx) => {
    setPickerAngleIndex(idx);
    setPickerModalOpen(true);
  };

  const handleConfirmMediaPicker = async (selectedPaths) => {
    // Case 1: Product-level default for ALL angles (idx === -1)
    if (pickerAngleIndex === -1) {
      setAngles(prev => prev.map(ang => {
        const curStatus = ang.status || 'scripted';
        const isAngleInProd = curStatus === 'in_production' || (!!ang.project_name && curStatus !== 'rendered' && curStatus !== 'posted');
        if (isAngleInProd) {
          // Keep existing timeline clips locked for angles in production
          return ang;
        }
        return {
          ...ang,
          selected_videos: selectedPaths,
          selected_video: selectedPaths[0] || null
        };
      }));
      if (productData?.id) {
        try {
          const res = await setDefaultVideosForProduct(productData.id, selectedPaths);
          if (res.product) {
            setProductData(res.product);
            setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
          }
          onRefresh && onRefresh();
        } catch (err) {
          console.error('Failed to set default videos for all angles:', err);
        }
      }
      showToast(`ตั้งคลิปเริ่มต้น ${selectedPaths.length} คลิปให้ทุกสคริปต์เรียบร้อยแล้ว`);
      return;
    }

    // Case 2: Specific angle customization
    const targetAngle = angles[pickerAngleIndex];
    if (!targetAngle) return;

    // Immediate UI update
    setAngles(prev => {
      const next = [...prev];
      if (next[pickerAngleIndex]) {
        const ang = { ...next[pickerAngleIndex] };
        ang.selected_videos = selectedPaths;
        ang.selected_video = selectedPaths[0] || null;
        next[pickerAngleIndex] = ang;
      }
      return next;
    });
    showToast(`เลือกคลิปดิบ ${selectedPaths.length} คลิปสำหรับมุมมองนี้เรียบร้อยแล้ว`);

    // Backend Persistence
    if (productData?.id && targetAngle.angle_id) {
      try {
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, selectedPaths);
        if (res.product) {
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
      } catch (err) {
        console.error('Failed to persist angle videos:', err);
      }
    }
  };

  const handleToggleVideoForAngle = async (angleIdx, videoPath) => {
    const targetAngle = angles[angleIdx];
    if (!targetAngle) return;

    const curStatus = targetAngle.status || 'scripted';
    const isInProduction = curStatus === 'in_production' || (!!targetAngle.project_name && curStatus !== 'rendered' && curStatus !== 'posted');
    if (isInProduction) {
      showToast('คลิปนี้กำลังถูกใช้งานจริงในไทม์ไลน์ ไม่สามารถตัดออกได้จนกว่าจะตัดออกจากไทม์ไลน์จริง', 'warning');
      return;
    }

    const currentVideos = targetAngle.selected_videos || (targetAngle.selected_video ? [targetAngle.selected_video] : []);
    const newVideos = currentVideos.includes(videoPath)
      ? currentVideos.filter(p => p !== videoPath)
      : [...currentVideos, videoPath];

    // Immediate UI update
    setAngles(prev => {
      const next = [...prev];
      const ang = { ...next[angleIdx] };
      ang.selected_videos = newVideos;
      ang.selected_video = newVideos[0] || null;
      next[angleIdx] = ang;
      return next;
    });
    showToast('อัปเดตการเลือกคลิปสำหรับมุมนี้เรียบร้อยแล้ว');

    // Backend Persistence
    if (productData?.id && targetAngle.angle_id) {
      try {
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, newVideos);
        if (res.product) {
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
      } catch (err) {
        console.error('Failed to persist angle videos:', err);
      }
    }
  };

  const copyScriptText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    showToast('คัดลอกสคริปต์เรียบร้อยแล้ว');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSendToStudio = async (angle, angleIdx = 0) => {
    if (!onApplyToStudio) return;

    const chosenVideos = angle.selected_videos && angle.selected_videos.length > 0
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : []);

    const resolvedIndex = typeof angleIdx === 'number' && angleIdx >= 0
      ? angleIdx
      : angles.findIndex(a => (a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title);

    if (chosenVideos.length === 0) {
      showToast('⚠️ กรุณาเลือกคลิปวิดีโอสำหรับมุมนี้ก่อนส่งตัดต่อ', 'warning');
      handleOpenMediaPicker(resolvedIndex >= 0 ? resolvedIndex : 0);
      return;
    }

    // Do NOT set in_production prematurely when merely sending to studio!
    // Status stays 'scripted' until user actually presses render in timeline.

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');

    const primaryVideo = chosenVideos[0] || '';

    onApplyToStudio({
      productId: productData?.id,
      angleId: angle.angle_id,
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      // The banner's three tiers come from the angle (the script AI splits
      // the product name) and fall back to a whitespace split. They used to
      // be left blank here on purpose, which meant the first render burned
      // the whole product name into the brand tier and nothing into the rest.
      hookBrand: angle.hook_brand || guessBrandModel(angle.product_name || '').brand,
      hookModel: angle.hook_model || guessBrandModel(angle.product_name || '').model,
      hookLabel: angle.hook_label || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
      // No openProjectName here on purpose -- this handler backs both
      // "เลือกมุมนี้ & ส่งตัดต่อ" (first-time send) and "ตัดใหม่" (explicitly
      // re-cut from scratch), so it must always open a fresh project.
      // handleOpenInTimeline below is the one that intentionally reopens
      // angle.project_name for "เปิดทำต่อในไทม์ไลน์" (continue an existing,
      // already-rendered project) -- this function used to copy that same
      // line, so any angle carrying a stale project_name from an earlier,
      // since-discarded project silently reopened it instead of starting new.
      openVideoUrl: angle.video_url || '',
      fullProduct: {
        id: productData?.id,
        title: productData?.title || customKeyword || 'สินค้า',
        description: productData?.description,
        price_note: productData?.price_note,
        product_code: productData?.product_code || '',
        selectedVideo: primaryVideo,
        selectedVideos: chosenVideos,
        images: productData?.images || [],
        angles: angles && angles.length > 0 ? angles : [angle]
      },
      angleIndex: resolvedIndex >= 0 ? resolvedIndex : 0
    });
  };

  const handleOpenInTimeline = (angle, index) => {
    const resolvedIndex = typeof index === 'number'
      ? index
      : angles.findIndex(a => (a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title);

    const chosenVideos = (angle.selected_videos && angle.selected_videos.length > 0)
      ? angle.selected_videos
      : (angle.selected_video ? [angle.selected_video] : (productData?.videos ? productData.videos.map(v => v.path || v.rel_path) : []));

    const scriptLines = Array.isArray(angle.script_lines)
      ? angle.script_lines
      : (angle.script_text ? angle.script_text.split('\n') : []);
    const scriptText = scriptLines.join('\n');
    const primaryVideo = chosenVideos[0] || '';

    onApplyToStudio({
      productId: productData?.id,
      angleId: angle.angle_id,
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      // The banner's three tiers come from the angle (the script AI splits
      // the product name) and fall back to a whitespace split. They used to
      // be left blank here on purpose, which meant the first render burned
      // the whole product name into the brand tier and nothing into the rest.
      hookBrand: angle.hook_brand || guessBrandModel(angle.product_name || '').brand,
      hookModel: angle.hook_model || guessBrandModel(angle.product_name || '').model,
      hookLabel: angle.hook_label || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: angle.ad_tone || 'commercial_premium',
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
      openProjectName: angle.project_name || '',
      openVideoUrl: angle.video_url || '',
      isRendered: true,
      fullProduct: {
        id: productData?.id,
        title: productData?.title || customKeyword || 'สินค้า',
        description: productData?.description,
        price_note: productData?.price_note,
        product_code: productData?.product_code || '',
        selectedVideo: primaryVideo,
        selectedVideos: chosenVideos,
        images: productData?.images || [],
        angles: angles && angles.length > 0 ? angles : [angle]
      },
      angleIndex: resolvedIndex >= 0 ? resolvedIndex : 0
    });
  };

  const totalAngles = angles.length;
  const postedAngles = angles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
  const progressPercent = totalAngles > 0 ? Math.round((postedAngles / totalAngles) * 100) : 0;
  const activeAngleIdx = openAngleIdx >= 0 && openAngleIdx < angles.length ? openAngleIdx : 0;
  const rerollTargetAngle = rerollModalAngleIdx !== null ? angles[rerollModalAngleIdx] : null;

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="space-y-4 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} onClose={hideToast} />

      <PageHeader
        icon={Package}
        eyebrow={productData ? 'สินค้าปัจจุบัน' : 'Step 1 — เลือกสินค้า'}
        badges={
          <>
            {productData?.price_note && (
              <span className="text-[10px] sm:text-xs font-bold font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                {productData.price_note}
              </span>
            )}
            {productData && (
              productData.tiktok_product_id ? (
                <button
                  type="button"
                  onClick={handleOpenEditTiktokIdModal}
                  className="inline-flex items-center gap-1.5 text-[10px] sm:text-xs font-bold font-mono text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 px-2.5 py-0.5 rounded-full border border-cyan-500/20 hover:border-cyan-500/40 transition-colors cursor-pointer group"
                  title="คลิกเพื่อแก้ไขหรือล้างไอดีสินค้า (มีผลกับทุกสคริปต์ในชุดนี้)"
                >
                  <ShoppingBag className="w-3 h-3 text-cyan-400" />
                  <span>ID: {productData.tiktok_product_id}</span>
                  <Edit3 className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100 transition-opacity" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleOpenEditTiktokIdModal}
                  className="inline-flex items-center gap-1.5 text-[10px] sm:text-xs text-slate-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] px-2.5 py-0.5 rounded-full border border-white/[0.08] hover:border-white/[0.2] transition-colors cursor-pointer group"
                  title="ไม่มี ID ระบบจะค้นหาด้วยชื่อสินค้า — คลิกเพื่อใส่ไอดีหรือลิงก์แชร์ย้อนหลัง"
                >
                  <ShoppingBag className="w-3 h-3 text-slate-400 group-hover:text-cyan-400 transition-colors" />
                  <span>ปักตะกร้าด้วยชื่อ</span>
                  <span className="text-[10px] text-cyan-400 font-medium group-hover:underline">ใส่ไอดี</span>
                </button>
              )
            )}
          </>
        }
        titlePrefix={
          productData?.product_code && (
            <span className="px-1.5 py-0.2 rounded bg-fuchsia-500/15 border border-fuchsia-500/30 text-fuchsia-300 font-mono text-[10px] flex-shrink-0">
              {productData.product_code}
            </span>
          )
        }
        title={productData?.title || productData?.name || (historyList.length > 0 ? 'เลือกสินค้าจากรายการด้านล่าง' : 'ยังไม่มีสินค้า — เริ่มวิเคราะห์สินค้าใหม่')}
        quickSwitcher={
          historyList.length > 1 && (
            <div className="relative flex-shrink-0">
              <select
                value={selectedHistoryId || ''}
                onChange={(e) => {
                  const found = historyList.find(p => p.id === e.target.value);
                  if (found) selectProduct(found);
                }}
                className="bg-black/50 border border-white/[0.1] hover:border-[#25F4EE]/40 text-slate-200 text-xs font-bold py-1.5 px-2 sm:px-3 rounded-xl focus:outline-none focus:border-[#25F4EE] cursor-pointer max-w-[130px] sm:max-w-[200px] truncate"
                title="สลับสินค้าด่วน"
              >
                {historyList.map(p => (
                  <option key={p.id} value={p.id} className="bg-[#080B11] text-white">
                    {p.product_code ? `${p.product_code} · ${p.name}` : p.name} ({p.angles?.length || 0} สคริปต์)
                  </option>
                ))}
              </select>
            </div>
          )
        }
        secondRow={
          <>
            {/* Row 2: Progress & Action Tools (Responsive on iPhone 15 PM) */}
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap justify-between pt-2 border-t border-white/[0.06]">
              {/* Progress Pill */}
              {totalAngles > 0 && (
                <div className="flex items-center gap-1.5 sm:gap-2 bg-black/40 px-2.5 py-1.5 rounded-xl border border-white/[0.08] flex-shrink-0">
                  <span className="text-[11px] sm:text-xs text-slate-400 font-medium">คืบหน้า</span>
                  <span className="text-[11px] sm:text-xs text-white font-bold font-mono">{postedAngles}/{totalAngles}</span>
                  <div className="w-12 sm:w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full transition-all duration-500" style={{ width: `${progressPercent}%` }} />
                  </div>
                </div>
              )}

              {/* Action Tools Group */}
              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap sm:flex-nowrap flex-1 justify-end">
                {/* Instant Search Bar */}
                <div className="relative flex items-center">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
                  <input
                    type="text"
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    placeholder="ค้นหาสินค้า..."
                    className="bg-black/40 border border-white/[0.1] focus:border-[#25F4EE] text-slate-200 text-xs pl-8 pr-6 py-1.5 rounded-xl w-[95px] xs:w-[115px] sm:w-[140px] focus:w-[135px] sm:focus:w-[170px] transition-all focus:outline-none placeholder-slate-500"
                  />
                  {productSearch && (
                    <button
                      onClick={() => setProductSearch('')}
                      className="absolute right-1.5 text-slate-400 hover:text-white cursor-pointer"
                      title="ล้างคำค้นหา"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {productData && (
                  <button
                    type="button"
                    onClick={() => setShowMetadataModal(true)}
                    className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/25 text-xs font-bold cursor-pointer transition-colors"
                    title="ดู metadata และรูปที่ AI ใช้"
                  >
                    <Database className="w-3.5 h-3.5" />
                    <span className="hidden xs:inline sm:inline">ข้อมูล AI</span>
                  </button>
                )}

                {/* Catalog Modal Button */}
                <button
                  onClick={() => setShowCatalogModal(true)}
                  className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white border border-white/[0.08] text-xs font-bold cursor-pointer transition-colors"
                  title="เปิดดูคลังสินค้าทั้งหมดแบบตาราง"
                >
                  <LayoutGrid className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span className="hidden xs:inline sm:inline">คลัง</span>
                </button>

                {/* Toggle Horizontal Card Strip */}
                <button
                  onClick={() => setShowProductStrip(!showProductStrip)}
                  className={`flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-xl border text-xs font-bold cursor-pointer transition-colors ${
                    showProductStrip
                      ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 text-[#25F4EE]'
                      : 'bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border-white/[0.08]'
                  }`}
                  title={showProductStrip ? "ซ่อนแถบการ์ดสินค้า" : "แสดงแถบการ์ดสินค้าทั้งหมด"}
                >
                  {showProductStrip ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  <span className="hidden xs:inline sm:inline">การ์ด</span>
                </button>

                {/* + Add New Product */}
                <button
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-slate-950 text-xs font-bold cursor-pointer shadow-md hover:opacity-95 active:scale-95 transition-all"
                  title="วิเคราะห์สินค้าใหม่"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline sm:inline">สินค้าใหม่</span>
                </button>

                {/* Refresh */}
                <button
                  onClick={loadHistory}
                  className="p-1.5 sm:p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/[0.06] cursor-pointer transition-colors"
                  title="รีเฟรชข้อมูล"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
                </button>

                {/* Delete current product */}
                {productData && (
                  <button
                    onClick={() => handleDeleteHistory(productData)}
                    className="p-1.5 sm:p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 cursor-pointer transition-colors"
                    title="ลบสินค้านี้"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Optional Horizontal Card Strip (Shown when user expands it or no product selected) */}
            {(showProductStrip || !productData) && (
              <div className="pt-2 border-t border-white/[0.06] animate-fadeIn">
                <div className="flex items-stretch gap-2.5 overflow-x-auto pb-1 no-scrollbar snap-x snap-mandatory scroll-smooth pr-4">
                  {filteredHistory.map(p => (
                    <ProductCard
                      key={p.id}
                      product={p}
                  isSelected={selectedHistoryId === p.id}
                  onSelect={(prod) => {
                    selectProduct(prod);
                  }}
                />
              ))}

              {filteredHistory.length === 0 && productSearch && (
                <div className="flex items-center justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-400 gap-2 flex-shrink-0">
                  <Search className="w-4 h-4 text-slate-500" />
                  <span>ไม่พบสินค้าที่ตรงกับ "{productSearch}"</span>
                </div>
              )}
            </div>
          </div>
        )}
          </>
        }
      />

      {/* ── Product Metadata Inspector ── */}
      <ProductMetadataModal
        product={productData}
        isOpen={showMetadataModal}
        onClose={() => { setShowMetadataModal(false); setProductSourcePreview(null); }}
        onAddImages={handleProductReferenceUpload}
        onRemoveImage={handleRemoveProductImage}
        onPreviewSource={handlePreviewProductSource}
        onPreviewImages={handlePreviewProductImages}
        onApplySource={handleApplyProductSource}
        onSaveMetadata={handleSaveProductMetadata}
        sourcePreview={productSourcePreview}
        onCancelPreview={() => setProductSourcePreview(null)}
        imageInputRef={productImageInputRef}
        uploading={savingProductImages}
        refreshingSource={refreshingProductSource}
        savingMetadata={savingProductMetadata}
        removingIndex={removingProductImageIndex}
        maxImages={MAX_PRODUCT_REFERENCE_IMAGES}
      />

      {/* ══════════════════════════════════════════════════════════
          ADD PRODUCT MODAL
         ══════════════════════════════════════════════════════════ */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title={`เพิ่มสินค้าใหม่ ➔ ให้ AI สร้าง ${angleCount} สคริปต์`}
        subtitle="รองรับทุกลิงก์ Shopee / TikTok Shop หรือพิมพ์สเปกตรงๆ"
        maxWidth="max-w-xl"
      >
        <div className="space-y-4">
          {/* Input Mode Selector */}
          <div className="flex items-center gap-1 p-1 bg-black/40 rounded-xl border border-white/[0.08]">
            {[
              { id: 'link', label: 'ลิงก์สินค้า' },
              { id: 'text', label: 'ข้อความสเปก' },
              { id: 'image', label: 'รูปภาพสินค้า' },
            ].map(m => (
              <button
                key={m.id}
                onClick={() => setInputMode(m.id)}
                className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  inputMode === m.id ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Mode 1: URL */}
          {inputMode === 'link' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ลิงก์สินค้า:"
                type="url"
                value={url}
                onChange={(e) => {
                  const val = e.target.value;
                  setUrl(val);
                  if (!tiktokProductId) {
                    const m = val.match(/\/(?:product|item)\/(\d{10,})/) || val.match(/[?&](?:item_id|itemId|product_id)=(\d{10,})/);
                    if (m) {
                      setTiktokProductId(m[1]);
                    } else if (val.includes('tiktok.com')) {
                      resolveTiktokProductId(val.trim()).then(res => {
                        if (res?.success && res?.product_id) {
                          setTiktokProductId(res.product_id);
                        }
                      }).catch(() => {});
                    }
                  }
                }}
                placeholder="https://shopee.co.th/product/... หรือ https://vt.tiktok.com/..."
              />
              <p className="text-sm text-slate-500">
                หากแพลตฟอร์มป้องกันการดึงข้อมูล ระบบจะแนะนำให้วางข้อความสเปกแทน
              </p>
            </div>
          )}

          {/* Mode 2: Raw Text */}
          {inputMode === 'text' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ชื่อสินค้า:"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น สายชาร์จแม่เหล็ก 3-in-1 หรือ เซรั่มหน้าใส"
              />
              <Textarea
                label="รายละเอียดสินค้าและสเปก:"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={5}
                placeholder="ก๊อปปี้รายละเอียดสินค้ามาวางที่นี่ได้เลย..."
              />
            </div>
          )}

          {/* Mode 3: Image / Screenshot */}
          {inputMode === 'image' && (
            <div className="space-y-3 pt-1">
              <Input
                label="ชื่อสินค้า:"
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                placeholder="เช่น Esseger สายชาร์จแม่เหล็ก"
              />
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  รูปสินค้าหรือภาพหน้าจอ (แนบได้สูงสุด {MAX_ANALYZE_IMAGES} รูป — AI จะอ่านสรรพคุณ/สเปคจากทุกรูปที่แนบ):
                </label>

                {selectedImages.length > 0 && (
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mb-2">
                    {selectedImages.map((img, i) => (
                      <div key={img.path} className="relative group aspect-square rounded-xl overflow-hidden border border-white/[0.12] bg-black/40">
                        <img src={img.previewUrl} alt={img.name} className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => setSelectedImages((prev) => prev.filter((_, idx) => idx !== i))}
                          title="ลบรูปนี้"
                          className="absolute top-1 right-1 flex items-center justify-center w-5 h-5 rounded-full bg-black/70 text-rose-300 hover:bg-rose-500/80 hover:text-white cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div
                  className="relative block border-2 border-dashed border-white/[0.15] hover:border-[#25F4EE]/50 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-black/30"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/*,image/heic,image/heif,image/jpeg,image/png,image/webp,.heic,.HEIC,.heif,.HEIF,.jpg,.jpeg,.png,.webp"
                    onChange={handleImageUpload}
                    disabled={uploadingImg || selectedImages.length >= MAX_ANALYZE_IMAGES}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20 disabled:cursor-not-allowed"
                  />
                  {uploadingImg ? (
                    <div className="flex flex-col items-center gap-2 text-[#25F4EE] pointer-events-none">
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span className="text-xs font-bold">กำลังอัปโหลดรูปภาพ...</span>
                    </div>
                  ) : selectedImages.length >= MAX_ANALYZE_IMAGES ? (
                    <div className="space-y-1.5 text-slate-400 pointer-events-none">
                      <Check className="w-7 h-7 mx-auto text-emerald-400" />
                      <div className="text-xs font-bold text-emerald-400">แนบครบ {MAX_ANALYZE_IMAGES} รูปแล้ว</div>
                      <div className="text-sm text-slate-500">ลบรูปด้านบนก่อนถึงจะแนบเพิ่มได้</div>
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-slate-400 pointer-events-none">
                      <Upload className="w-7 h-7 mx-auto text-slate-500" />
                      <div className="text-xs font-bold text-slate-200">
                        {selectedImages.length > 0 ? `แตะเพื่อเลือกเพิ่ม (${selectedImages.length}/${MAX_ANALYZE_IMAGES})` : 'แตะเพื่อเลือกรูปสินค้า'}
                      </div>
                      <div className="text-sm text-slate-500">รองรับ HEIC, JPG, PNG, WebP · เลือกได้หลายรูปพร้อมกัน</div>
                    </div>
                  )}
                </div>

                {/* Native Fallback for 100% iOS Safari support */}
                <div className="mt-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-1 text-left">
                  <span className="text-[11px] font-bold text-slate-400 block">หรือเลือกไฟล์รูปภาพ:</span>
                  <input
                    type="file"
                    multiple
                    accept="image/*,image/heic,image/heif,image/jpeg,image/png,image/webp,.heic,.HEIC,.heif,.HEIF,.jpg,.jpeg,.png,.webp"
                    onChange={handleImageUpload}
                    disabled={uploadingImg || selectedImages.length >= MAX_ANALYZE_IMAGES}
                    className="block w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-[#25F4EE]/20 file:text-[#25F4EE] hover:file:bg-[#25F4EE]/30 file:cursor-pointer cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}

          {fetchError && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{fetchError}</span>
              </div>
              {inputMode === 'link' && (
                <button
                  type="button"
                  onClick={() => { setInputMode('text'); setFetchError(null); }}
                  className="px-3 py-1.5 rounded-lg bg-white/[0.1] hover:bg-white/[0.15] text-white text-sm font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span>สลับไปใช้วิธีวางข้อความสเปกแทน</span>
                </button>
              )}
            </div>
          )}

          {/* TikTok Product ID Input (Optional - falls back to product name) */}
          <div className="pt-2 border-t border-white/[0.06] space-y-1.5">
            <Input
              label="ไอดีสินค้าสำหรับปักตะกร้า (TikTok Product ID):"
              type="text"
              value={tiktokProductId}
              onChange={(e) => {
                const val = e.target.value;
                setTiktokProductId(val);
                const m = val.match(/\/(?:product|item)\/(\d{10,})/) || val.match(/[?&](?:item_id|itemId|product_id)=(\d{10,})/);
                if (m) {
                  setTiktokProductId(m[1]);
                }
              }}
              onPaste={(e) => {
                const pasted = e.clipboardData.getData('text');
                if (pasted && (pasted.startsWith('http://') || pasted.startsWith('https://') || pasted.includes('tiktok.com'))) {
                  const m = pasted.match(/\/(?:product|item)\/(\d{10,})/) || pasted.match(/[?&](?:item_id|itemId|product_id)=(\d{10,})/);
                  if (m) {
                    setTimeout(() => setTiktokProductId(m[1]), 20);
                  } else {
                    resolveTiktokProductId(pasted.trim()).then(res => {
                      if (res?.success && res?.product_id) {
                        setTiktokProductId(res.product_id);
                      }
                    }).catch(() => {});
                  }
                }
              }}
              placeholder="เช่น 1737088044189583209 หรือวางลิงก์แชร์ vt.tiktok.com..."
            />
            <p className="text-[11px] text-slate-400">
              💡 ใส่ไอดีเป็นหลักสำหรับปักตะกร้าอัตโนมัติ (หรือวางลิงก์แชร์เพื่อดึงไอดี) หากไม่มีระบบจะค้นหาด้วยชื่อสินค้าแทนให้ตรงที่สุด
            </p>
          </div>

          {/* ── Angle Count Selector ── */}
          <div className="flex items-center gap-3 py-2.5">
            <span className="text-xs text-slate-400 font-semibold">จำนวนมุมขาย:</span>
            <div className="flex items-center gap-1.5">
              {[
                { val: 4, label: '4', desc: 'Quick' },
                { val: 7, label: '7', desc: 'แนะนำ' },
                { val: 10, label: '10', desc: 'ครบ' },
              ].map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setAngleCount(opt.val)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                    angleCount === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.05] text-slate-400 border border-white/[0.08] hover:border-white/[0.2] hover:text-white'
                  }`}
                >
                  {opt.label}
                  {opt.desc && <span className="ml-1 text-[10px] opacity-60">({opt.desc})</span>}
                </button>
              ))}
            </div>
          </div>

          {/* ── Duration Selector (independent of angle count -- both apply together) ── */}
          <div className="flex items-center gap-3 py-2.5 -mt-1">
            <span className="text-xs text-slate-400 font-semibold">ความยาวคลิป:</span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {DURATION_OPTIONS.map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setDuration(opt.val)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                    duration === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.05] text-slate-400 border border-white/[0.08] hover:border-white/[0.2] hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Angle breakdown preview hint */}
          <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-300">
              <Sparkles className="w-3 h-3 text-[#25F4EE]" />
              <span>แนวทางสคริปต์ที่ AI จะสร้างให้ ({angleCount} สคริปต์):</span>
            </div>
            {angleCount === 4 && (
              <p className="text-slate-400 leading-relaxed">
                1. 😫 ปัญหาก่อนใช้ • 2. ⚙️ <strong className="text-cyan-300">รีวิวสเปกเจาะลึก</strong> • 3. 🛍️ แกะกล่องว้าว • 4. 🔥 FOMO ดีลโปร
              </p>
            )}
            {angleCount === 7 && (
              <p className="text-slate-400 leading-relaxed">
                4 มุมหลัก (รวม ⚙️ <strong className="text-cyan-300">รีวิวสเปกเจาะลึก</strong>) + 🆚 เทียบของเดิม + 🤫 ทริกลึก + ⚠️ เตือนภัยก่อนซื้อ
              </p>
            )}
            {angleCount === 10 && (
              <p className="text-slate-400 leading-relaxed">
                ครบ 10 รูปแบบ (รวม ⚙️ <strong className="text-cyan-300">รีวิวสเปกเจาะลึก</strong>, สายเฉพาะทาง, รีวิว 3 เดือน, และคำนวณความคุ้มค่า)
              </p>
            )}
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
            <Button variant="secondary" onClick={() => setShowAddModal(false)}>
              ยกเลิก
            </Button>
            <Button variant="primary" onClick={handleScrapeAndPlan} loading={fetching} icon={Sparkles}>
              วิเคราะห์ & สร้าง {angleCount} สคริปต์ x {DURATION_OPTIONS.find(o => o.val === duration)?.label || duration}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ══════════════════════════════════════════════════════════
          STEP 2 + 3: PRODUCT DETAIL + SCRIPT ACCORDION + MEDIA
         ══════════════════════════════════════════════════════════ */}
      {productData ? (
        <div className="space-y-4">
          {/* ──── STEP 2: Script Lab & Footage Selection ──── */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 px-1">
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#FE2C55]" />
                  <span>Step 2 — เลือกมุมขาย & คลิปประกอบ ({totalAngles} สคริปต์)</span>
                </h2>
              </div>

              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                {/* View Mode Toggle: Split (Studio) vs Accordion (List) */}
                <div className="flex items-center bg-black/40 p-0.5 rounded-xl border border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => setViewMode('split')}
                    className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      viewMode === 'split'
                        ? 'bg-[#25F4EE]/15 text-[#25F4EE] shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="มุมมองแบบสตูดิโอ: บนมือถือเลือกมุมแบบ Carousel บนคอมแบ่ง 2 ฝั่ง"
                  >
                    <Columns className="w-3.5 h-3.5" />
                    <span>สตูดิโอ</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('accordion')}
                    className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      viewMode === 'accordion'
                        ? 'bg-[#25F4EE]/15 text-[#25F4EE] shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="มุมมองแบบแถวยาวคลาสสิก"
                  >
                    <List className="w-3.5 h-3.5" />
                    <span>แถวเดียว</span>
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setFindReplaceAngleIdx(activeAngleIdx);
                    setFindReplaceOpen(true);
                  }}
                  className="px-2.5 py-1 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-amber-300 cursor-pointer flex items-center gap-1.5 transition-all"
                  title="ค้นหาและแทนที่คำในสคริปต์ทั้งหมด หรือเฉพาะมุมที่เลือก"
                >
                  <Replace className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline sm:inline">แทนที่คำ</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleOpenMediaPicker(-1)}
                  className="px-2.5 py-1 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-xs font-bold text-[#25F4EE] cursor-pointer flex items-center gap-1.5 transition-all"
                  title="เลือกคลิปจากคลังหรืออัปโหลดใหม่ ให้เป็นคลิปเริ่มต้นของทุกสคริปต์"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline sm:inline">คลิปให้ทุกมุม</span>
                </button>
              </div>
            </div>

            {/* Master-Detail Split View (Default Studio Mode) */}
            {viewMode === 'split' ? (
              <div className="space-y-3 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-4 items-start">
                {/* MOBILE (< lg): Horizontal Swipeable Angle Carousel for iPhone 15 Pro Max */}
                <div className="lg:hidden space-y-1.5">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      แตะสลับมุมขาย ({angles.length} มุม):
                    </span>
                    <span className="text-[11px] font-mono text-[#25F4EE] font-bold">
                      มุมที่ {activeAngleIdx + 1}/{angles.length}
                    </span>
                  </div>
                  <div className="flex items-stretch gap-2 overflow-x-auto pb-2 pt-0.5 no-scrollbar snap-x snap-mandatory pr-2 scroll-smooth">
                    {angles.map((ang, idx) => (
                      <AngleMobilePill
                        key={ang.angle_id || idx}
                        angle={ang}
                        index={idx}
                        isSelected={activeAngleIdx === idx}
                        onSelect={() => setOpenAngleIdx(idx)}
                      />
                    ))}
                  </div>
                </div>

                {/* DESKTOP (lg+): Left Column Vertical Playlist (5 cols) */}
                <div className="hidden lg:block lg:col-span-5 space-y-2 lg:max-h-[calc(100vh-210px)] lg:overflow-y-auto pr-1 no-scrollbar">
                  {angles.map((ang, idx) => (
                    <AngleSidebarItem
                      key={ang.angle_id || idx}
                      angle={ang}
                      index={idx}
                      isSelected={activeAngleIdx === idx}
                      onSelect={() => setOpenAngleIdx(idx)}
                      onPreviewExportVideo={(a) => setPreviewExportAngle(a)}
                    />
                  ))}
                </div>

                {/* Right Column (Active Workbench / 7 cols sticky) */}
                <div className="lg:col-span-7 lg:sticky lg:top-4">
                  {angles[activeAngleIdx] && (
                    <AngleActiveWorkbench
                      angle={angles[activeAngleIdx]}
                      index={activeAngleIdx}
                      onCopy={copyScriptText}
                      onSendToStudio={handleSendToStudio}
                      onOpenInTimeline={handleOpenInTimeline}
                      onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                      copiedIndex={copiedIndex}
                      videos={videos}
                      onToggleVideoForAngle={handleToggleVideoForAngle}
                      onUploadVideo={handleImageUpload}
                      uploadingImg={uploadingImg}
                      onOpenMediaPicker={handleOpenMediaPicker}
                      onSaveScript={handleSaveScript}
                      onOpenFindReplace={(i) => {
                        setFindReplaceAngleIdx(i);
                        setFindReplaceOpen(true);
                      }}
                      onRerollScript={handleOpenRerollScriptModal}
                      onGenerateShotList={handleGenerateShotList}
                      isGeneratingShotList={generatingShotListIdx === activeAngleIdx}
                    />
                  )}
                </div>
              </div>
            ) : (
              /* Classic Accordion View */
              <div className="space-y-1.5">
                {angles.map((ang, idx) => (
                  <ScriptAccordionItem
                    key={ang.angle_id || idx}
                    angle={ang}
                    index={idx}
                    isOpen={openAngleIdx === idx}
                    onToggle={() => setOpenAngleIdx(openAngleIdx === idx ? -1 : idx)}
                    onCopy={copyScriptText}
                    onSendToStudio={handleSendToStudio}
                    onOpenInTimeline={handleOpenInTimeline}
                    onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                    copiedIndex={copiedIndex}
                    videos={videos}
                    onToggleVideoForAngle={handleToggleVideoForAngle}
                    onUploadVideo={handleImageUpload}
                    uploadingImg={uploadingImg}
                    onOpenMediaPicker={handleOpenMediaPicker}
                    onSaveScript={handleSaveScript}
                    onOpenFindReplace={(i) => {
                      setFindReplaceAngleIdx(i);
                      setFindReplaceOpen(true);
                    }}
                    onRerollScript={handleOpenRerollScriptModal}
                    onGenerateShotList={handleGenerateShotList}
                    isGeneratingShotList={generatingShotListIdx === idx}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ══════════════════════════════════════════════════════════
           🌟 EMPTY STATE / ONBOARDING (First-Run Experience)
          ══════════════════════════════════════════════════════════ */
        <div className="p-8 sm:p-12 text-center space-y-5 rounded-2xl glass-card shadow-2xl border border-white/[0.08]">
          {/* Hero Icon */}
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#FE2C55]/20 to-[#25F4EE]/20 border border-white/[0.1] flex items-center justify-center mx-auto shadow-lg">
            <Rocket className="w-8 h-8 text-[#25F4EE]" />
          </div>

          <div>
            <h3 className="text-lg font-bold text-white font-kanit">เริ่มต้นสร้างคลิปขายจากสินค้าได้เลย!</h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
              วางลิงก์สินค้าจาก Shopee หรือ TikTok Shop → AI จะวิเคราะห์สเปกและสร้าง <strong className="text-white">4 สคริปต์ป้ายยา</strong> จาก 4 มุมขายให้ทันที → เลือกมุมที่ชอบแล้วกด "ส่งตัดต่อ"
            </p>
          </div>

          {/* 3-Step Visual Guide */}
          <div className="flex items-center justify-center gap-3 text-xs text-slate-400 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-[#25F4EE]/20 text-[#25F4EE] font-bold text-sm flex items-center justify-center">1</span>
              <span>วางลิงก์/สเปก</span>
            </div>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-[#FE2C55]/20 text-[#FE2C55] font-bold text-sm flex items-center justify-center">2</span>
              <span>AI สร้าง 4 สคริปต์</span>
            </div>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <div className="flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-sm flex items-center justify-center">3</span>
              <span>ส่งตัดต่อใน Studio</span>
            </div>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="mx-auto py-3 px-6 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-sm font-bold flex items-center gap-2 shadow-lg shadow-[#FE2C55]/25 cursor-pointer active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4 text-white" />
            <span>วิเคราะห์สินค้าแรกของคุณ</span>
          </button>
        </div>
      )}

      {/* ── Universal Media Picker Modal ── */}
      <MediaPickerModal
        isOpen={pickerModalOpen}
        onClose={() => setPickerModalOpen(false)}
        title={`เลือกคลิปสำหรับมุม: ${angles[pickerAngleIndex]?.angle_name || 'มุมมองขาย'}`}
        productId={productData?.id}
        productName={productData?.title}
        selectedVideos={angles[pickerAngleIndex]?.selected_videos || (angles[pickerAngleIndex]?.selected_video ? [angles[pickerAngleIndex]?.selected_video] : [])}
        onConfirm={handleConfirmMediaPicker}
        isMultiSelect={true}
      />

      {/* ── Batch Find & Replace Modal ── */}
      <FindReplaceModal
        isOpen={findReplaceOpen}
        onClose={() => setFindReplaceOpen(false)}
        angles={angles}
        currentAngleIndex={findReplaceAngleIdx}
        onApplyReplace={handleApplyFindReplace}
      />

      {/* ── Reroll Script with AI Modal (per-angle, overwrites script in place) ── */}
      <Modal
        isOpen={rerollModalAngleIdx !== null}
        onClose={handleCloseRerollScriptModal}
        title="รีสคริปต์ด้วย AI"
        subtitle={rerollTargetAngle ? `หัวข้อเดิม: ${rerollTargetAngle.angle_name || ''}` : ''}
        maxWidth="max-w-lg"
      >
        <div className="space-y-4">
          {rerollTargetAngle && (
            <div className="space-y-1.5 rounded-xl border border-[#25F4EE]/20 bg-[#25F4EE]/[0.04] p-3">
              <div className="text-[11px] font-semibold text-slate-400">
                ประเภทเนื้อหาของหัวข้อนี้
              </div>
              <ContentTypeBadges angle={rerollTargetAngle} />
              <p className="text-[11px] leading-relaxed text-slate-400">
                เจนใหม่จะเปลี่ยนเฉพาะบทพูดในหัวข้อนี้ ส่วนท่อนเสริมที่เลือกจะถูกแทรกอยู่ในหัวข้อเดิม
              </p>
            </div>
          )}

          {/* Duration Selector */}
          <div className="space-y-1.5">
            <span className="text-xs text-slate-400 font-semibold">ความยาวคลิป:</span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {DURATION_OPTIONS.map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => {
                    setRerollDuration(opt.val);
                    // Re-sync the extra-beat checkboxes to this tier's default
                    // mix -- without this, switching duration inside the modal
                    // left whatever checkboxes were showing from the PREVIOUS
                    // tier (e.g. still 0 checked after switching 30s -> 60s),
                    // silently mismatched from what the length selector implies.
                    setRerollExtraBeats(defaultExtraBeatsForDuration(opt.val));
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all ${
                    rerollDuration === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.05] text-slate-400 border border-white/[0.08] hover:border-white/[0.2] hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Extra Beats Checkboxes */}
          <div className="space-y-1.5">
            <span className="text-xs text-slate-400 font-semibold">เนื้อหาเสริมที่ต้องการ (เลือกได้หลายข้อ):</span>
            <div className="space-y-1.5">
              {EXTRA_BEAT_OPTIONS.map(opt => (
                <label
                  key={opt.val}
                  className="flex items-center gap-2 p-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-xs text-slate-300 hover:text-white hover:border-white/[0.15] cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={rerollExtraBeats.includes(opt.val)}
                    onChange={() => handleToggleRerollExtraBeat(opt.val)}
                    className="accent-[#25F4EE] w-3.5 h-3.5 cursor-pointer flex-shrink-0"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Overwrite Warning (only when the angle already has production progress) */}
          {rerollTargetAngle && (rerollTargetAngle.project_name || rerollTargetAngle.video_url) && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                มุมนี้มีการตัดต่อ/วิดีโอผูกอยู่แล้ว — การรีสคริปต์จะเขียนบทพูดใหม่ทับของเดิมทันที (กู้คืนสคริปต์เก่าไม่ได้)
                แต่โปรเจกต์/วิดีโอที่ตัดไว้จะยังอยู่เหมือนเดิม ไม่ถูกลบหรือรีเซ็ต
              </span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
            <Button variant="secondary" onClick={handleCloseRerollScriptModal} disabled={rerollingScript}>
              ยกเลิก
            </Button>
            <Button variant="primary" onClick={handleSubmitRerollScript} loading={rerollingScript} icon={Sparkles}>
              รีสคริปต์
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Shot List Modal (per-beat filming plan from real TTS timing) ── */}
      <ShotListModal
        isOpen={shotListAngleIdx !== null}
        onClose={() => { setShotListAngleIdx(null); setShotListResult(null); }}
        productId={productData?.id}
        mobileBaseUrl={mobileBaseUrl}
        result={shotListResult}
        onRegenerate={handleRegenerateShotList}
        regenerating={shotListAngleIdx !== null && generatingShotListIdx === shotListAngleIdx}
      />

      {/* ── Product Catalog Modal (Searchable Grid for 100+ items) ── */}
      <Modal
        isOpen={showCatalogModal}
        onClose={() => setShowCatalogModal(false)}
        title={`คลังสินค้าทั้งหมด (${historyList.length} รายการ)`}
        subtitle="ค้นหา กรอง และเลือกสินค้าเพื่อเข้าสู่หน้ามุมมองขายและสคริปต์"
        maxWidth="max-w-4xl"
      >
        <div className="space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-white/[0.08]">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                placeholder="ค้นหาชื่อสินค้า, ราคา, หรือคีย์เวิร์ด..."
                className="w-full bg-[#080B11] border border-white/[0.1] focus:border-[#25F4EE] text-white text-xs pl-9 pr-8 py-2 rounded-xl focus:outline-none placeholder-slate-500"
                autoFocus
              />
              {productSearch && (
                <button
                  onClick={() => setProductSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                  title="ล้างคำค้นหา"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 p-1 bg-black/40 rounded-xl border border-white/[0.08] flex-shrink-0">
              {[
                { id: 'all', label: `ทั้งหมด (${historyList.length})` },
                { id: 'in_progress', label: `กำลังทำ` },
                { id: 'completed', label: `เสร็จแล้ว` },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setProductFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    productFilter === tab.id
                      ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Grid Cards Container */}
          <div className="max-h-[60vh] overflow-y-auto pr-1 no-scrollbar">
            {filteredHistory.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {filteredHistory.map(p => {
                  const pAngles = p.angles || [];
                  const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
                  const total = pAngles.length || 4;
                  const pct = Math.round((pDone / total) * 100);
                  const thumb = p.images?.[0];
                  const thumbSrc = thumb ? toMediaUrl(thumb.rel_path || thumb.local_path || thumb.url) : null;
                  const isSelected = selectedHistoryId === p.id;

                  return (
                    <div
                      key={p.id}
                      onClick={() => {
                        selectProduct(p);
                        setShowCatalogModal(false);
                      }}
                      className={`p-3 rounded-xl border transition-all cursor-pointer group relative flex flex-col justify-between space-y-2.5 ${
                        isSelected
                          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE] shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
                          : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
                      }`}
                    >
                      {/* Image Preview */}
                      <div className="w-full aspect-square rounded-lg overflow-hidden bg-black/60 border border-white/[0.06] flex items-center justify-center relative">
                        {thumbSrc ? (
                          <img src={thumbSrc} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                        ) : (
                          <Package className={`w-10 h-10 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-600'}`} />
                        )}
                        {isSelected && (
                          <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-[#25F4EE] text-black flex items-center justify-center shadow-md">
                            <Check className="w-3 h-3 stroke-[3]" />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="space-y-1">
                        <div className={`text-xs font-bold truncate leading-tight ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                          {p.name}
                        </div>
                        {p.price && (
                          <div className="text-xs font-mono font-bold text-amber-400">
                            {p.price}
                          </div>
                        )}
                      </div>

                      {/* Progress Bar & Angle Count */}
                      <div className="space-y-1 pt-1 border-t border-white/[0.06]">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">สคริปต์</span>
                          <span className="font-mono font-bold text-[#25F4EE]">
                            {pDone}/{total} มุม
                          </span>
                        </div>
                        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-12 text-center space-y-3">
                <Package className="w-12 h-12 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400">
                  {productSearch ? `ไม่พบสินค้าที่ตรงกับคำค้นหา "${productSearch}"` : 'ยังไม่มีสินค้าในระบบ'}
                </p>
                {productSearch && (
                  <button
                    onClick={() => setProductSearch('')}
                    className="text-xs text-[#25F4EE] hover:underline font-bold cursor-pointer"
                  >
                    ล้างการค้นหา
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-white/[0.08]">
            <Button
              variant="primary"
              onClick={() => {
                setShowCatalogModal(false);
                setShowAddModal(true);
              }}
              className="flex items-center gap-1.5 text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>วิเคราะห์สินค้าใหม่</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => setShowCatalogModal(false)}
              className="text-xs"
            >
              ปิดหน้าต่าง
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Video Export Preview Modal (Dialog ดูคลิป ณ จุดนั้นทันที) ── */}
      <Modal
        isOpen={!!previewExportAngle}
        onClose={() => setPreviewExportAngle(null)}
        title="🎬 พรีวิววิดีโอที่ตัดต่อเสร็จแล้ว (QC & Export Preview)"
        subtitle={previewExportAngle?.hook_title || productData?.name}
        maxWidth="max-w-md"
      >
        {previewExportAngle && (
          <div className="space-y-3.5">
            <div className="relative rounded-2xl overflow-hidden bg-black aspect-[9/16] max-h-[66vh] mx-auto border border-white/[0.1] shadow-2xl flex items-center justify-center">
              <video
                src={toMediaUrl(previewExportAngle.video_url)}
                controls
                autoPlay
                playsInline
                className="w-full h-full object-contain"
              />
            </div>

            {/* Meta & Quick Details */}
            <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <Check className="w-3.5 h-3.5" />
                  <span>เรนเดอร์เสร็จสมบูรณ์พร้อมโพสต์ (9:16)</span>
                </span>
                {previewExportAngle.badge && (
                  <Badge variant="cyan" size="sm">{previewExportAngle.badge}</Badge>
                )}
              </div>
              {previewExportAngle.tiktok_caption && (
                <p className="text-xs text-slate-300 line-clamp-2 font-mono leading-relaxed select-all">
                  {previewExportAngle.tiktok_caption} {previewExportAngle.tiktok_hashtags}
                </p>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center gap-2 pt-1">
              {onGoToGallery && (
                <button
                  type="button"
                  onClick={() => {
                    setPreviewExportAngle(null);
                    onGoToGallery();
                  }}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                  title="ไปที่หน้าคลัง Export ทั้งหมด"
                >
                  <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
                  <span>เปิดใน Gallery</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  const ang = previewExportAngle;
                  setPreviewExportAngle(null);
                  handleOpenInTimeline(ang, openAngleIdx >= 0 ? openAngleIdx : 0);
                }}
                className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
                title="เปิดดูในไทม์ไลน์"
              >
                <Play className="w-3.5 h-3.5 fill-white text-white" />
                <span>เปิดดูในไทม์ไลน์</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Edit TikTok Product ID Modal (Post-creation / Backlog support) ── */}
      <Modal
        isOpen={showEditTiktokIdModal}
        onClose={() => !savingTiktokId && setShowEditTiktokIdModal(false)}
        title="ไอดีสินค้าสำหรับปักตะกร้า (TikTok Product ID)"
        subtitle={`สินค้านี้: ${productData?.title || productData?.name || ''}`}
        maxWidth="max-w-lg"
      >
        <div className="space-y-4 pt-1">
          <div className="p-3 bg-cyan-500/[0.06] border border-cyan-500/20 rounded-xl space-y-1">
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold">
              <ShoppingBag className="w-4 h-4 flex-shrink-0" />
              <span>แนบกับทุกสคริปต์ในชุดนี้ ({productData?.angles?.length || 0} สคริปต์)</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              ไอดีนี้จะถูกบันทึกไว้ที่ระดับตัวสินค้า ทำให้ทุกมุมขายและทุกคลิปที่เรนเดอร์ในชุดนี้ ใช้ไอดีเดียวกันนี้ในการค้นหาและปักตะกร้าอัตโนมัติบน TikTok Shop ทันที
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>ระบุรหัสตัวเลข หรือ วางลิงก์สินค้า / ลิงก์แชร์:</span>
              {resolvingTiktokId && (
                <span className="text-[11px] text-cyan-400 flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  กำลังดึงไอดีจากลิงก์...
                </span>
              )}
            </label>
            <div className="relative">
              <input
                type="text"
                value={editTiktokIdInput}
                onChange={(e) => {
                  const val = e.target.value;
                  setEditTiktokIdInput(val);
                  const m = val.match(/\/(?:product|item)\/(\d{10,})/) || val.match(/[?&](?:item_id|itemId|product_id)=(\d{10,})/);
                  if (m) {
                    setEditTiktokIdInput(m[1]);
                    showToast(`ดึงรหัสสินค้าสำเร็จ: ${m[1]}`);
                  }
                }}
                onPaste={(e) => {
                  const pasted = e.clipboardData.getData('text');
                  if (pasted && (pasted.startsWith('http://') || pasted.startsWith('https://') || pasted.includes('tiktok.com'))) {
                    setTimeout(() => handleResolveAndSetId(pasted), 50);
                  }
                }}
                placeholder="เช่น 1737088044189583209 หรือวาง https://vt.tiktok.com/..."
                className="w-full bg-[#080B11] border border-white/[0.1] focus:border-[#25F4EE] text-white text-xs px-3 py-2.5 rounded-xl focus:outline-none placeholder-slate-500 font-mono"
                autoFocus
              />
              {editTiktokIdInput && (
                <button
                  type="button"
                  onClick={() => setEditTiktokIdInput('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white cursor-pointer p-1"
                  title="ล้างค่า"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {editTiktokIdInput && (editTiktokIdInput.startsWith('http://') || editTiktokIdInput.startsWith('https://') || editTiktokIdInput.includes('tiktok.com')) && !/^\d{10,}$/.test(editTiktokIdInput) && (
              <button
                type="button"
                onClick={() => handleResolveAndSetId(editTiktokIdInput)}
                disabled={resolvingTiktokId}
                className="w-full py-1.5 px-3 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer border border-cyan-500/30"
              >
                {resolvingTiktokId ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>กำลังตามลิงก์เพื่อแกะไอดี...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>ดึงรหัสตัวเลขจากลิงก์นี้</span>
                  </>
                )}
              </button>
            )}

            <p className="text-[11px] text-slate-500">
              💡 รองรับทั้งรหัสตัวเลข 15–19 หลัก, ลิงก์สินค้า TikTok Shop หรือลิงก์แชร์สั้น (vt.tiktok.com)
              <br />
              หากเว้นว่างไว้ ระบบจะใช้ชื่อสินค้าในการค้นหาเพื่อปักตะกร้าแทน
            </p>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-white/[0.08]">
            {productData?.tiktok_product_id ? (
              <button
                type="button"
                onClick={() => setEditTiktokIdInput('')}
                className="text-xs text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
              >
                ล้างไอดี (ใช้ชื่อค้นหา)
              </button>
            ) : <div />}

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                onClick={() => setShowEditTiktokIdModal(false)}
                disabled={savingTiktokId}
              >
                ยกเลิก
              </Button>
              <Button
                variant="primary"
                onClick={handleSaveTiktokId}
                disabled={savingTiktokId || resolvingTiktokId}
                className="bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white font-bold"
              >
                {savingTiktokId ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    บันทึก...
                  </span>
                ) : 'บันทึก'}
              </Button>
            </div>
          </div>
        </div>
      </Modal>

      {/* ── Delete Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!deleteTargetProduct}
        onClose={() => setDeleteTargetProduct(null)}
        onConfirm={confirmDeleteProduct}
        title="ลบสินค้าและสคริปต์ทั้งหมดถาวร?"
        description="ข้อมูลสินค้า สเปก และสคริปต์มุมมองขายทั้งหมดจะถูกลบออกจากระบบ"
        itemName={deleteTargetProduct?.title || deleteTargetProduct?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบข้อมูลถาวร"
        loading={isDeletingProduct}
        variant="danger"
      />
    </div>
  );
}
