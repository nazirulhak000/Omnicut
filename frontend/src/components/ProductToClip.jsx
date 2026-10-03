import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  Link2, Sparkles, Clapperboard, Loader2, Check, Copy, CopyPlus,
  AlertCircle, ArrowRight, Upload, Trash2, RefreshCw, Plus, Film, Video,
  ChevronDown, ChevronUp, ChevronRight, Package, Rocket, FolderOpen, X,
  Search, LayoutGrid, Filter, Play, Lock, Edit3, Replace, Columns, List,
  ShoppingBag, ShieldCheck, Database, Zap, Layers, Eye, EyeOff, CheckCircle2, Tag,
  Volume2, Mic, AlertTriangle, VolumeX, Scissors, MoreHorizontal
} from 'lucide-react';
import {
  scrapeAndPlanProduct, scrapeAndPlanProductAsync, getProducts, updateProduct,
  previewProductSource, previewProductImageMetadataAsync, refreshProductSource, updateAngleStatus, updateAngleVideos, setDefaultVideosForProduct,
  getSceneCatalogs, indexSceneCatalogs, deleteProduct, deleteProductAngle,
  uploadFile, resolveTiktokProductId, rerollAngleScript,
  generateShotList, getShotList, getShotListStatus, getTaskStatus,
  generateProductBatch, batchGenerateAudio, startBatchDraft, getBatchRenderStatus
} from '../api';
import { Modal, Toast, Button, Badge, Input, Textarea, ConfirmModal, PageHeader } from './ui';
import MediaPickerModal from './MediaPickerModal';
import FindReplaceModal from './FindReplaceModal';
import ProductMetadataModal from './ProductMetadataModal';
import ShotListModal from './ShotListModal';
import HookVariationModal from './HookVariationModal';
import BatchRenderModal from './BatchRenderModal';
import HookHeaderModal from './HookHeaderModal';
import SceneCatalogModal from './SceneCatalogModal';
import ManualStoryboardModal from './ManualStoryboardModal';
import UniversalFilmingRecipeModal from './UniversalFilmingRecipeModal';
import { toMediaUrl } from '../lib/mediaUrl';
import { useToast } from '../hooks';
import { useTaskManager } from '../context/TaskContext';
import { guessBrandModel } from '../lib/overlayModel';
import { getRecommendedStyleForAngle } from '../lib/stylePresetCatalog';
import { resolveHistoryTargetId, resolveSelectedProduct } from '../lib/productSelection';
import { buildProjectName } from '../lib/projectName';

const GEMINI_VOICE_OPTIONS = [
  { id: 'gemini_puck_male_hype', label: 'Puck — ชายพลังสูง TikTok' },
  { id: 'gemini_charon_male_pro', label: 'Charon — ชายทุ้มลึก น่าเชื่อถือ' },
  { id: 'gemini_kore_female_bright', label: 'Kore — หญิงสดใส ป้ายยาเก่ง' },
  { id: 'gemini_aoede_female_pro', label: 'Aoede — หญิงพรีเมียม นุ่มนวล' },
  { id: 'gemini_fenrir_male_strong', label: 'Fenrir — ชายสตรอง คมเข้ม (ค่าเริ่มต้น)' },
];

function getVoicePresetShortName(presetId) {
  if (!presetId) return 'Fenrir';
  if (presetId.includes('puck')) return 'Puck';
  if (presetId.includes('charon')) return 'Charon';
  if (presetId.includes('kore')) return 'Kore';
  if (presetId.includes('aoede')) return 'Aoede';
  if (presetId.includes('fenrir')) return 'Fenrir';
  return 'Gemini';
}

function getVoicePresetFullLabel(presetId) {
  const opt = GEMINI_VOICE_OPTIONS.find(v => v.id === presetId);
  return opt ? opt.label.split('—')[0].trim() : (getVoicePresetShortName(presetId) + ' (Gemini)');
}

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
function ProductCard({ product, isSelected, onSelect, onToggleHide }) {
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
      className={`flex-shrink-0 w-[130px] sm:w-[150px] rounded-xl border transition-all cursor-pointer group snap-center p-2.5 space-y-2 text-left relative ${
        isSelected
          ? 'bg-[#25F4EE]/[0.08] border-[#25F4EE]/60 shadow-lg shadow-[#25F4EE]/10 ring-1 ring-[#25F4EE]/40'
          : 'bg-[#0B0F19] border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.03]'
      }`}
    >
      {/* Thumbnail or Placeholder */}
      <div className="w-full aspect-square rounded-lg overflow-hidden bg-black/60 border border-white/[0.06] flex items-center justify-center relative">
        {thumbSrc ? (
          <img src={thumbSrc} alt="" className="w-full h-full object-cover" />
        ) : (
          <Package className={`w-7 h-7 ${isSelected ? 'text-[#25F4EE]' : 'text-slate-600'}`} />
        )}

        {onToggleHide && (
          <button
            type="button"
            onClick={(e) => onToggleHide(product, e)}
            className={`absolute top-1.5 right-1.5 p-1 rounded-lg backdrop-blur-md border transition-all cursor-pointer z-10 ${
              product.is_hidden
                ? 'bg-amber-500/80 border-amber-400 text-slate-950 opacity-100'
                : 'bg-black/60 hover:bg-rose-500/80 border-white/20 hover:border-rose-400 text-slate-300 hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100'
            }`}
            title={product.is_hidden ? 'ยกเลิกการซ่อนสินค้านี้' : 'ซ่อนสินค้านี้'}
            aria-label={product.is_hidden ? 'ยกเลิกการซ่อนสินค้านี้' : 'ซ่อนสินค้านี้'}
          >
            {product.is_hidden ? (
              <Eye className="w-3.5 h-3.5" />
            ) : (
              <EyeOff className="w-3.5 h-3.5" />
            )}
          </button>
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
// 4-phase pipeline definition for sidebar dot indicators
// 4-phase pipeline definition for sidebar dot indicators
const PIPELINE_PHASES = [
  { key: 'scripted', label: 'สคริปต์พร้อม', short: 'สคริปต์' },
  { key: 'in_production', label: 'กำลังตัดต่อ', short: 'ตัดต่อ' },
  { key: 'rendered', label: 'ตัดต่อเสร็จ', short: 'เสร็จ' },
  { key: 'posted', label: 'โพสต์แล้ว', short: 'โพสต์' },
];

function resolvePhaseIndex(angle) {
  const curStatus = angle.status || 'scripted';
  const isRendered = (curStatus === 'rendered' || curStatus === 'posted') && !!angle.video_url;
  const isInProduction = curStatus === 'in_production';
  if (curStatus === 'posted') return 3;
  if (isRendered) return 2;
  if (isInProduction) return 1;
  return 0;
}

function PhaseDots({ angle, compact = false }) {
  const activeIdx = resolvePhaseIndex(angle);
  const currentPhase = PIPELINE_PHASES[activeIdx];

  return (
    <div
      className="inline-flex items-center gap-1.5 py-0.5 px-1.5 rounded-full bg-black/40 border border-white/[0.06]"
      title={`สถานะกระบวนการ: ${currentPhase.label} (สเต็ป ${activeIdx + 1}/4)`}
    >
      <div className="flex items-center gap-1">
        {PIPELINE_PHASES.map((phase, i) => {
          const isCurrent = i === activeIdx;
          const isPassed = i < activeIdx;

          return (
            <div key={phase.key} className="flex items-center">
              {/* Connector line between dots */}
              {i > 0 && (
                <div
                  className={`h-0.5 w-1.5 sm:w-2 transition-colors duration-300 ${
                    isPassed || isCurrent ? 'bg-emerald-500/70' : 'bg-white/[0.08]'
                  }`}
                />
              )}
              {/* Dot */}
              <div className="relative flex items-center justify-center">
                {isCurrent && (
                  <span className="absolute w-3.5 h-3.5 rounded-full bg-emerald-400/30 animate-ping opacity-75" />
                )}
                <span
                  className={`rounded-full transition-all duration-300 ${
                    isCurrent
                      ? 'w-2 h-2 bg-emerald-400 ring-2 ring-emerald-400/40 shadow-sm shadow-emerald-400/60 scale-110 z-10'
                      : isPassed
                      ? 'w-1.5 h-1.5 bg-emerald-500/80'
                      : 'w-1.5 h-1.5 bg-white/[0.12]'
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
      {!compact && (
        <span className={`text-[9px] font-bold ml-0.5 ${
          activeIdx === 3 ? 'text-emerald-300'
          : activeIdx === 2 ? 'text-cyan-300'
          : activeIdx === 1 ? 'text-amber-300'
          : 'text-slate-400'
        }`}>
          {currentPhase.short}
        </span>
      )}
    </div>
  );
}

function AngleSidebarItem({
  angle,
  index,
  isSelected,
  onSelect,
  onPreviewExportVideo,
  shotListInfo,
  onGenerateShotList,
  onOpenShotList,
  isGeneratingShotList = false,
  onDeleteAngle,
  projectName,
}) {
  const curStatus = angle.status || 'scripted';
  const isRendered = (curStatus === 'rendered' || curStatus === 'posted') && !!angle.video_url;
  const isInProduction = curStatus === 'in_production';
  const isLocked = curStatus === 'posted' || isInProduction || isRendered;

  const phaseIdx = resolvePhaseIndex(angle);

  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);
  const hasShotList = shotListInfo?.has_shot_list;
  const isStaleShotList = shotListInfo?.is_stale;
  const isEdgeTtsShotList = shotListInfo?.is_edge_tts;

  return (
    <div
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
      aria-current={isSelected ? 'true' : undefined}
      className={`p-2.5 rounded-xl border transition-all cursor-pointer text-left group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 ${
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

        {/* Title + Phase Dots + Badges */}
        <div className="min-w-0 flex-1 space-y-1.5">
          {/* Row 1: Name + 4-Phase Stepper */}
          <div className="flex items-center justify-between gap-2">
            <span className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-200'}`}>
              {angle.angle_name}
            </span>
            <div className="flex-shrink-0">
              <PhaseDots angle={angle} />
            </div>
          </div>

          {/* Row 2: Content Type Badges + Shot List Badge */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <ContentTypeBadges angle={angle} compact />

            {/* Shot List Status Badge */}
            {hasShotList ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenShotList ? onOpenShotList(index) : (onGenerateShotList && onGenerateShotList(index));
                }}
                className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md border transition-all cursor-pointer ${
                  isEdgeTtsShotList
                    ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-400/40 ring-1 ring-amber-400/30 shadow-xs'
                    : isStaleShotList
                      ? 'bg-orange-500/15 hover:bg-orange-500/25 text-orange-300 border-orange-400/40 ring-1 ring-orange-400/20'
                      : 'bg-indigo-500/15 hover:bg-indigo-500/25 text-cyan-300 border-indigo-400/40 ring-1 ring-indigo-400/20 shadow-xs'
                }`}
                title={isEdgeTtsShotList
                  ? '⚠️ แผนถ่ายนี้สร้างด้วย Edge-TTS เดิม — คลิกเพื่อเปิดดูและอัปเกรดเป็น Gemini TTS'
                  : isStaleShotList
                    ? 'บทเปลี่ยนหลังจากสร้างแผนถ่าย — คลิกเพื่อตรวจหรืออัปเดต'
                    : `มีแผนถ่ายพร้อมแล้ว (${getVoicePresetFullLabel(shotListInfo?.voice_preset)}) — คลิกเพื่อเปิดดูแผนถ่าย`}
              >
                {isEdgeTtsShotList ? (
                  <>
                    <AlertTriangle className="w-2.5 h-2.5 text-amber-300 flex-shrink-0" />
                    <span>⚠️ Edge-TTS (เสียงเดิม)</span>
                  </>
                ) : isStaleShotList ? (
                  <>
                    <Clapperboard className="w-2.5 h-2.5 flex-shrink-0" />
                    <span>แผนถ่ายเก่า (บทเปลี่ยน)</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-2.5 h-2.5 text-cyan-300 flex-shrink-0" />
                    <span>🎙️ Gemini ({getVoicePresetShortName(shotListInfo?.voice_preset)})</span>
                  </>
                )}
              </button>
            ) : (
              !isLocked && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onGenerateShotList && onGenerateShotList(index);
                  }}
                  disabled={isGeneratingShotList}
                  className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/[0.04] hover:bg-amber-500/15 text-slate-400 hover:text-amber-200 border border-white/[0.08] hover:border-amber-500/30 transition-all cursor-pointer disabled:opacity-50"
                  title="ยังไม่มีแผนถ่าย — คลิกเพื่อสร้างแผนถ่ายสำหรับมุมนี้"
                >
                  {isGeneratingShotList ? (
                    <Loader2 className="w-2.5 h-2.5 animate-spin text-amber-400" />
                  ) : (
                    <Clapperboard className="w-2.5 h-2.5 text-amber-400/70" />
                  )}
                  <span>+ แผนถ่าย</span>
                </button>
              )
            )}
          </div>

          {/* Row 3: Hook preview */}
          {angle.hook_title && (
            <p className="text-[11px] text-slate-400 truncate">
              "{angle.hook_title}"
            </p>
          )}

          {/* Row 3b: angle_id + projected project name */}
          <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
            {/* angle_id chip — ยืนยันว่า ID ไม่ซ้ำ */}
            {angle.angle_id && (
              <span
                className="inline-flex items-center gap-1 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE]/80 border border-[#25F4EE]/20"
                title={`angle_id = ${angle.angle_id} (batch ${angle.batch || 1})`}
              >
                <Tag className="w-2 h-2 flex-shrink-0" />
                {angle.angle_id}{angle.batch && angle.batch > 1 ? `_b${angle.batch}` : ''}
              </span>
            )}
            {/* timeline project name — แสดงเฉพาะเมื่อสคริปต์เข้าไทม์ไลน์แล้วจริง */}
            {angle.project_name && (
              <span
                className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 truncate max-w-[140px]"
                title={`โปรเจกต์ในไทม์ไลน์: ${angle.project_name}`}
              >
                <FolderOpen className="w-2 h-2 flex-shrink-0" />
                {angle.project_name}
              </span>
            )}
          </div>

          {/* Row 4: Footer — footage tag + delete button + preview button */}
          <div className="flex items-center justify-between pt-0.5 text-[10px]">
            <div className="flex items-center gap-2.5">
              {selectedVideos.length > 0 ? (
                <span className="inline-flex items-center gap-1 text-[#25F4EE] font-medium">
                  <Film className="w-2.5 h-2.5" />
                  <span>{selectedVideos.length} คลิป</span>
                </span>
              ) : (
                <span className="text-slate-500 italic">ยังไม่ได้เลือกคลิป</span>
              )}

              {onDeleteAngle && angle.status !== 'posted' && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteAngle(angle, index);
                  }}
                  className="hidden opacity-0 group-hover:opacity-100 hover:!opacity-100 px-1.5 py-0.5 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/15 transition-all cursor-pointer items-center gap-1"
                  title="ลบสคริปต์มุมนี้"
                >
                  <Trash2 className="w-3 h-3" />
                  <span className="text-[10px] font-medium">ลบสคริปต์</span>
                </button>
              )}
            </div>

            {isRendered && angle.video_url && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onPreviewExportVideo && onPreviewExportVideo(angle);
                }}
                className="hidden p-1 px-1.5 rounded bg-cyan-500/15 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/30 items-center gap-1 transition-colors"
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
function AngleMobilePill({ angle, index, isSelected, onSelect, shotListInfo }) {
  const selectedVideos = angle.selected_videos || (angle.selected_video ? [angle.selected_video] : []);
  const hasShotList = shotListInfo?.has_shot_list;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full px-3 py-2 rounded-xl border text-left transition-all cursor-pointer flex items-center gap-2 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 ${
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
          <PhaseDots angle={angle} compact={true} />
          <span className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
            {angle.angle_name}
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <ContentTypeBadges angle={angle} compact />
          {hasShotList && (
            <span className={`inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded border ${
              shotListInfo?.is_edge_tts
                ? 'text-amber-300 bg-amber-500/15 border-amber-500/30'
                : 'text-cyan-300 bg-indigo-500/15 border-indigo-500/30'
            }`}>
              {shotListInfo?.is_edge_tts ? (
                <span>⚠️ Edge</span>
              ) : (
                <span>🎙️ {getVoicePresetShortName(shotListInfo?.voice_preset)}</span>
              )}
            </span>
          )}
        </div>
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
  angle, index, onCopy, onSendToStudio, onOpenInTimeline, onPreviewExportVideo, onCloneAngle, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false,
  onOpenMediaPicker, onSaveScript, onOpenFindReplace, onRerollScript, onGenerateShotList,
  isGeneratingShotList = false, onOpenHookVariants,
  productData, onOpenEditHookHeader, shotListInfo, onDeleteAngle,
  onQuickDraft, draftingAngleId,
  sceneCatalogsMap = {}, onIndexSceneCatalog, isScanningScenes = false, onOpenSceneCatalog,
  onOpenStoryboard,
  projectName,
}) {
  const effectiveBrand = angle.hook_brand ?? productData?.hook_brand ?? guessBrandModel(angle.product_name || productData?.name || productData?.title || '').brand;
  const effectiveModel = angle.hook_model ?? productData?.hook_model ?? guessBrandModel(angle.product_name || productData?.name || productData?.title || '').model;
  const effectiveLabel = angle.hook_label ?? productData?.hook_label ?? '';
  const lines = Array.isArray(angle.script_lines)
    ? angle.script_lines
    : (angle.script_text ? angle.script_text.split('\n') : []);

  const [isEditing, setIsEditing] = useState(false);
  const [showMoreTools, setShowMoreTools] = useState(false);
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
      if (angleChanged) setShowMoreTools(false);
      prevAngleIdRef.current = curAngleId;
      prevScriptTextRef.current = scriptText;
      prevHookRef.current = angle.hook_title || '';
    }
  }, [angle.angle_id, index, scriptText, angle.hook_title]);

  const curStatus = angle.status || 'scripted';
  const isPosted = curStatus === 'posted' || !!angle.posted_at;
  const isRendered = (curStatus === 'rendered' || isPosted) && !!angle.video_url;
  const isInProduction = !isPosted && curStatus === 'in_production';
  const isLocked = isPosted || isInProduction || isRendered;

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

  const handleAddLine = () => {
    setEditText((current) => current ? `${current}\n` : '\n');
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
          <h2 className={`text-xs sm:text-sm md:text-base font-bold truncate ${
            isLocked ? 'text-slate-300' : 'text-white'
          }`}>
            {angle.angle_name}
          </h2>
          <span className={`text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${statusColor}`}>
            {statusLabel}
          </span>
          {/* angle_id chip — ยืนยันว่า ID ไม่ซ้ำ */}
          {angle.angle_id && (
            <span
              className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE]/70 border border-[#25F4EE]/20 flex-shrink-0"
              title={`angle_id ที่ไม่ซ้ำกัน: ${angle.angle_id} (batch ${angle.batch || 1})`}
            >
              <Tag className="w-2.5 h-2.5" />
              {angle.angle_id}{angle.batch && angle.batch > 1 ? `_b${angle.batch}` : ''}
            </span>
          )}
        </div>

        {/* Project name in timeline — แสดงเฉพาะเมื่อมีโปรเจกต์ในไทม์ไลน์แล้วจริง */}
        {angle.project_name && (
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            <span className="text-[10px] text-slate-500">โปรเจกต์ในไทม์ไลน์:</span>
            <span
              className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 font-mono"
              title={`โปรเจกต์ CapCut: ${angle.project_name}`}
            >
              <FolderOpen className="w-3 h-3" />
              {angle.project_name}
            </span>
          </div>
        )}

        {/* Action icons */}
        <div className="flex items-center gap-1.5 self-end xs:self-auto flex-shrink-0">
          {!isEditing && !isLocked && (
            <button
              type="button"
              onClick={handleStartEdit}
              className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-amber-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>แก้ Hook + บทพูด</span>
            </button>
          )}
          {!isEditing && (
            <button
              type="button"
              onClick={() => setShowMoreTools((open) => !open)}
              aria-expanded={showMoreTools}
              className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
              <span>เพิ่มเติม</span>
            </button>
          )}
          {showMoreTools && !isEditing && (
            <>
              {!isLocked ? (
                <>
                  <button
                    type="button"
                    onClick={handleStartEdit}
                    className="hidden px-2 sm:px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-amber-300 text-xs font-bold items-center gap-1 cursor-pointer transition-all"
                    title="แก้ไข Hook และบทพูดในกล่องนี้โดยตรง"
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
                    className={`px-2 sm:px-2.5 py-1 rounded-lg border text-xs font-bold flex items-center gap-1 cursor-pointer transition-all disabled:opacity-50 disabled:cursor-wait ${
                      shotListInfo?.is_edge_tts
                        ? 'bg-amber-500/20 hover:bg-amber-500/30 border-amber-500/40 text-amber-300 ring-1 ring-amber-400/20 shadow-xs'
                        : shotListInfo?.has_shot_list
                          ? 'bg-indigo-500/20 hover:bg-indigo-500/30 border-indigo-400/40 text-cyan-300 ring-1 ring-indigo-400/20 shadow-xs'
                          : 'bg-white/[0.05] hover:bg-white/[0.1] border-white/[0.08] text-amber-300'
                    }`}
                    title={shotListInfo?.is_edge_tts
                      ? '⚠️ แผนถ่ายนี้สร้างด้วย Edge-TTS เดิม — คลิกเพื่อเปิดดูและอัปเกรดเป็น Gemini TTS'
                      : shotListInfo?.has_shot_list
                        ? `เปิดดูแผนถ่าย (${getVoicePresetFullLabel(shotListInfo?.voice_preset)})`
                        : 'สร้างแผนถ่าย (Shot List) จากจังหวะเสียงพากย์จริง'}
                  >
                    {isGeneratingShotList ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : shotListInfo?.is_edge_tts ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
                    ) : shotListInfo?.has_shot_list ? (
                      <Mic className="w-3.5 h-3.5 text-cyan-300" />
                    ) : (
                      <Clapperboard className="w-3.5 h-3.5" />
                    )}
                    <span className="hidden xs:inline sm:inline">
                      {shotListInfo?.is_edge_tts
                        ? '⚠️ แผนถ่าย (Edge-TTS เดิม)'
                        : shotListInfo?.has_shot_list
                          ? `🎙️ แผนถ่าย (${getVoicePresetShortName(shotListInfo?.voice_preset)})`
                          : '+ แผนถ่าย'}
                    </span>
                  </button>
                </>
              )}
              {!isPosted && onDeleteAngle && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onDeleteAngle(angle, index); }}
                  className="px-2 sm:px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold flex items-center gap-1 cursor-pointer transition-all"
                  title="ลบสคริปต์มุมนี้"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span className="hidden xs:inline sm:inline">ลบสคริปต์</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Consolidated script context: one surface instead of nested status cards. */}
      <section className="border-y border-white/[0.08] divide-y divide-white/[0.06]" aria-label="ข้อมูล Hook และเสียงนำถ่าย">
          <div className="py-3 flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div className="min-w-0 space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap text-[11px] text-slate-400">
                <span className="inline-flex items-center gap-1.5 font-bold text-slate-300">
                  <Tag className="w-3.5 h-3.5 text-[#25F4EE]" />
                  Hook Header · 3 ป้าย
                </span>
                <span>{effectiveBrand || 'ยังไม่มีแบรนด์'}</span>
                <span className="text-slate-700">/</span>
                <span>{effectiveModel || 'ยังไม่มีรุ่น'}</span>
                {effectiveLabel && (
                  <>
                    <span className="text-slate-700">/</span>
                    <span>{effectiveLabel}</span>
                  </>
                )}
                {isLocked && (
                  <span className="inline-flex items-center gap-1 text-amber-300/80">
                    <Lock className="w-3 h-3" /> ล็อกตามไทม์ไลน์
                  </span>
                )}
              </div>
              {isEditing ? (
                <input
                  type="text"
                  value={editHook}
                  onChange={(event) => setEditHook(event.target.value)}
                  placeholder="พิมพ์ Hook พาดหัวเปิดคลิป"
                  aria-label="แก้ไข Hook พาดหัวเปิดคลิป"
                  className="w-full max-w-[72ch] bg-transparent border-b border-[#25F4EE]/40 focus:border-[#25F4EE] px-0 py-1 text-sm font-bold text-white focus:outline-none"
                />
              ) : (
                <p className="text-sm font-bold text-white leading-relaxed max-w-[72ch]">
                  {angle.hook_title ? `“${angle.hook_title}”` : 'ยังไม่มี Hook พาดหัวเปิดคลิป'}
                </p>
              )}
            </div>

            {!isLocked && !isEditing && (
              <div className="flex items-center gap-1 flex-shrink-0">
                {onOpenEditHookHeader && (
                  <button
                    type="button"
                    onClick={() => onOpenEditHookHeader(index)}
                    className="px-2 py-1 text-xs font-semibold text-slate-400 hover:text-white rounded-md hover:bg-white/[0.05] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60"
                    title="แก้ไข 3 ป้าย: แบรนด์ · รุ่น · หมวด"
                  >
                    แก้ 3 ป้าย
                  </button>
                )}
                {onOpenHookVariants && (
                  <button
                    type="button"
                    onClick={() => onOpenHookVariants(angle, index)}
                    className="px-2 py-1 text-xs font-semibold text-[#25F4EE] rounded-md hover:bg-[#25F4EE]/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60"
                  >
                    สร้าง Hook ใหม่
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0 text-xs">
              {isGeneratingShotList ? (
                <Loader2 className="w-4 h-4 text-[#25F4EE] animate-spin flex-shrink-0" />
              ) : shotListInfo?.is_edge_tts ? (
                <AlertTriangle className="w-4 h-4 text-amber-300 flex-shrink-0" />
              ) : shotListInfo?.has_shot_list ? (
                <Mic className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
              ) : (
                <VolumeX className="w-4 h-4 text-slate-500 flex-shrink-0" />
              )}
              <span className="font-bold text-slate-200 whitespace-nowrap">เสียงนำถ่าย</span>
              <span className={`truncate ${
                shotListInfo?.is_edge_tts
                  ? 'text-amber-300'
                  : shotListInfo?.has_shot_list
                    ? 'text-slate-400'
                    : 'text-slate-500'
              }`}>
                {isGeneratingShotList
                  ? 'กำลังเตรียมเสียงและแผนถ่าย'
                  : shotListInfo?.is_edge_tts
                    ? 'Edge-TTS เดิม ควรอัปเกรดก่อนสร้างดราฟต์'
                    : shotListInfo?.has_shot_list
                      ? `${getVoicePresetFullLabel(shotListInfo?.voice_preset)}${shotListInfo?.is_stale ? ' · บทเปลี่ยน ควรสร้างเสียงใหม่' : ' · พร้อมใช้งาน'}`
                      : 'ยังไม่ได้สร้าง'}
              </span>
            </div>

            {(!isLocked || shotListInfo?.has_shot_list) && (
              <button
                type="button"
                onClick={() => onGenerateShotList && onGenerateShotList(index)}
                disabled={isGeneratingShotList}
                className="self-end sm:self-auto px-2.5 py-1 rounded-md text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/[0.06] disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60"
              >
                {shotListInfo?.is_edge_tts
                  ? 'อัปเกรดเสียง'
                  : shotListInfo?.has_shot_list
                    ? 'เปิดเสียงและแผน'
                    : 'สร้างเสียงและแผน'}
              </button>
            )}
          </div>
      </section>

      {/* Locked Notice Banner */}
      {isLocked && (
        <div className="hidden p-3 rounded-xl bg-white/[0.02] border border-white/[0.08] items-center gap-2 text-xs text-slate-400">
          <Lock className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <span>
            {isPosted
              ? 'สคริปต์นี้โพสต์ลง TikTok แล้ว ระบบล็อกเนื้อหาและคลิปทั้งหมดเพื่อเก็บเป็นประวัติ'
              : isRendered
                ? 'ตัดต่อเสร็จแล้ว ระบบล็อกเนื้อหาและคลิปเพื่อคงความตรงกันกับวิดีโอที่สร้างไว้'
                : 'สคริปต์นี้กำลังตัดต่อในไทม์ไลน์ ล็อกเนื้อหาและคลิปเพื่อความสอดคล้องกับไทม์ไลน์'}
          </span>
        </div>
      )}

      {/* 2. Hook Header (3-tier Banner) */}
      <div className="hidden p-3 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
            <Tag className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span>Hook Header · 3 ป้ายบนวิดีโอ:</span>
          </div>
          {!isLocked && onOpenEditHookHeader && (
            <button
              type="button"
              onClick={() => onOpenEditHookHeader(index)}
              className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer transition-colors"
              title="แก้ไขแบรนด์, รุ่น และหมวดสินค้าสำหรับป้าย Hook"
            >
              <Edit3 className="w-3 h-3" />
                    <span>แก้ 3 ป้าย</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2.5 py-1 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
            <span className="text-slate-500 font-semibold">แบรนด์:</span>
            <strong className="text-cyan-300">{effectiveBrand || '—'}</strong>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
            <span className="text-slate-500 font-semibold">รุ่น:</span>
            <strong className="text-amber-300">{effectiveModel || '—'}</strong>
          </span>
          {effectiveLabel && (
            <span className="px-2.5 py-1 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
              <span className="text-slate-500 font-semibold">หมวด:</span>
              <strong className="text-emerald-300">{effectiveLabel}</strong>
            </span>
          )}
        </div>
      </div>

      {/* 3. Hook Callout */}
      {angle.hook_title && !isEditing && (
        <div className="hidden p-3 rounded-xl bg-gradient-to-r from-[#FE2C55]/15 via-black/40 to-[#25F4EE]/10 border border-[#FE2C55]/30 items-center justify-between gap-2.5 text-xs sm:text-sm font-bold text-white shadow-sm">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <span className="text-lg">🎯</span>
            <div className="min-w-0 flex-1 leading-snug">
              <span className="text-xs text-rose-400 font-semibold block">Hook พาดหัวเปิดคลิป:</span>
              <span className="block whitespace-normal break-words">"{angle.hook_title}"</span>
            </div>
          </div>
          {!isLocked && onOpenHookVariants && (
            <button
              type="button"
              onClick={() => onOpenHookVariants(angle, index)}
              className="px-2.5 py-1 rounded-lg bg-cyan-400/[0.1] hover:bg-cyan-400/[0.2] border border-cyan-400/30 text-cyan-300 text-xs font-bold flex items-center gap-1.5 flex-shrink-0 transition-colors"
              title="สร้าง Hook ทางเลือก 5 สไตล์ด้วย AI"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>สร้าง Hook</span>
            </button>
          )}
        </div>
      )}

      {/* 4. Voice Track & Shot List Status Banner (Main Screen Visibility) */}
      <div className="hidden rounded-xl overflow-hidden transition-all">
        {shotListInfo?.is_edge_tts ? (
          <div className="p-3 bg-gradient-to-r from-amber-950/40 via-amber-900/25 to-amber-950/40 border border-amber-500/35 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shadow-sm">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-300 font-extrabold text-xs flex items-center gap-1.5 border border-amber-400/40 shadow-xs flex-shrink-0">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
                ⚠️ เสียงนำถ่าย: Edge-TTS (เสียงเดิม)
              </span>
              <span className="text-xs text-amber-200/80 leading-tight">
                แผนถ่ายนี้ใช้เสียง Edge-TTS เดิม จังหวะอาจยังไม่สมจริง แนะนำให้อัปเกรดเป็น Gemini TTS
              </span>
            </div>
            <button
              type="button"
              onClick={() => onGenerateShotList && onGenerateShotList(index)}
              className="self-end sm:self-auto px-3 py-1 rounded-lg bg-amber-500/25 hover:bg-amber-500/40 border border-amber-400/50 text-amber-200 hover:text-white text-xs font-bold transition-all cursor-pointer flex-shrink-0 shadow-xs"
            >
              เปิดอัปเกรดเสียง ➔
            </button>
          </div>
        ) : shotListInfo?.has_shot_list ? (
          <div className="p-2.5 sm:p-3 bg-gradient-to-r from-indigo-950/40 via-slate-900/40 to-indigo-950/40 border border-indigo-500/25 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-2 py-0.5 rounded-md bg-indigo-500/20 text-cyan-300 font-bold text-xs flex items-center gap-1.5 border border-indigo-400/30 flex-shrink-0">
                <Mic className="w-3.5 h-3.5 text-cyan-300" />
                🎙️ เสียงนำถ่าย: Gemini TTS ({getVoicePresetFullLabel(shotListInfo?.voice_preset)})
              </span>
              <span className="text-xs text-slate-400 leading-tight">
                {shotListInfo?.is_stale
                  ? '⚠️ บทพูดมีการแก้ไขหลังจากสร้างเสียง แนะนำให้กดสร้างใหม่เพื่อจังหวะที่ตรงกัน'
                  : 'เสียงนำถ่ายพร้อมแล้ว ช็อตตรงตามจังหวะพูดจริง'}
              </span>
            </div>
            <div className="flex items-center gap-2 self-end sm:self-auto flex-shrink-0">
              <button
                type="button"
                onClick={() => onGenerateShotList && onGenerateShotList(index)}
                className="px-3 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 hover:text-white text-xs font-bold transition-all cursor-pointer flex-shrink-0"
              >
                เปิดฟังเสียง / ดูแผนถ่าย
              </button>
            </div>
          </div>
        ) : (
          <div className="p-2.5 bg-white/[0.02] border border-white/[0.06] rounded-xl flex items-center justify-between gap-2 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <VolumeX className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
              <span>เสียงนำถ่าย: ยังไม่ได้สร้าง (ยังไม่มีไฟล์เสียงและแผนถ่ายของมุมนี้)</span>
            </div>
            {!isLocked && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onGenerateShotList && onGenerateShotList(index)}
                  disabled={isGeneratingShotList}
                  className="px-2.5 py-1 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-400/30 text-cyan-300 text-xs font-bold transition-all cursor-pointer flex-shrink-0 disabled:opacity-50"
                >
                  + สร้างเสียงพากย์ & แผนถ่าย
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. Script Lines or Editor */}
      {isEditing ? (
        <div className="space-y-1.5 animate-fadeIn">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold">
            <span className="text-[#25F4EE]">แก้บทพูดบนรายการ · 1 ช่องต่อ 1 ท่อน</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleAddLine}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[#25F4EE] hover:text-white hover:bg-[#25F4EE]/10"
                title="เพิ่มช่องบทพูดอีก 1 ท่อน"
              >
                <Plus className="w-3 h-3" /> เพิ่มบรรทัด
              </button>
              <button
                type="button"
                onClick={() => {
                  const newLines = editText.split('\n').map((line) => line.trim()).filter(Boolean);
                  if (newLines.length > 0) onSaveScript && onSaveScript(index, newLines, editHook.trim());
                  onOpenFindReplace && onOpenFindReplace(index);
                }}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-slate-400 hover:text-white hover:bg-white/[0.05]"
              >
                <Replace className="w-3 h-3" /> แทนที่คำ
              </button>
            </div>
          </div>

          <div className="divide-y divide-white/[0.05]">
            {editText.split('\n').map((line, lineIndex, currentLines) => (
              <div key={lineIndex} className="flex items-start gap-3 py-2 px-1 focus-within:bg-white/[0.02]">
                <span className="w-5 text-xs font-bold text-[#25F4EE] text-center flex-shrink-0 mt-1.5">{lineIndex + 1}</span>
                <textarea
                  value={line}
                  onChange={(event) => {
                    const nextLines = [...currentLines];
                    nextLines[lineIndex] = event.target.value.replace(/\r?\n/g, ' ');
                    setEditText(nextLines.join('\n'));
                  }}
                  rows={1}
                  aria-label={`แก้ไขบทพูดท่อนที่ ${lineIndex + 1}`}
                  className="min-h-8 w-full resize-y bg-transparent border-0 border-b border-transparent focus:border-[#25F4EE]/40 px-0 py-1 text-xs sm:text-sm text-white leading-relaxed focus:outline-none"
                />
              </div>
            ))}
          </div>

           <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
            <span className="text-[11px] text-slate-500">แก้ Hook ได้ที่บรรทัดด้านบน · เพิ่มท่อนได้ด้วยปุ่มเพิ่มบรรทัด</span>
            <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCancelEdit}
              className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 text-xs font-semibold cursor-pointer flex items-center gap-1 transition-all"
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
        </div>
      ) : (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>บทพูดพากย์ · {lines.length} ท่อน</span>
            {!isLocked && <span className="text-[11px] text-slate-500 italic">คลิกที่กล่องเพื่อแก้ไข</span>}
          </div>

          <div
            onClick={handleStartEdit}
            className={`max-h-64 overflow-y-auto text-xs sm:text-sm leading-relaxed divide-y divide-white/[0.05] transition-colors group/box ${
              isLocked
                ? 'text-slate-300 cursor-default'
                : 'text-slate-200 cursor-pointer hover:bg-white/[0.01]'
            }`}
            title={isLocked ? 'ล็อกเนื้อหาแล้ว' : 'คลิกเพื่อแก้ไขสคริปต์'}
          >
            {lines.map((line, lIdx) => (
              <div key={lIdx} className="flex items-start gap-3 py-2.5 px-1 hover:bg-white/[0.02] transition-colors">
                <span className={`w-5 font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  isLocked ? 'text-slate-500' : 'text-[#25F4EE]'
                }`}>
                  {lIdx + 1}
                </span>
                <span className="flex-1 text-slate-200 leading-relaxed">{line}</span>
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
          <div className="flex items-center gap-2">
            <span className="text-xs">
              {selectedVideos.length > 0
                ? <span className="text-emerald-400 font-bold">เลือกแล้ว {selectedVideos.length} คลิป</span>
                : <span className="text-amber-400 font-bold">ยังไม่ได้เลือกคลิป</span>}
            </span>
            {!isLocked && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onOpenStoryboard && onOpenStoryboard(angle, index);
                }}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 ${
                  angle.manual_shot_map?.length > 0
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
                    : 'bg-[#25F4EE]/10 border-[#25F4EE]/30 text-[#25F4EE] hover:bg-[#25F4EE]/20'
                }`}
                title="เลือกคลิปหรือช่วงช็อตให้แต่ละท่อนของสคริปต์"
              >
                <Scissors className="w-3.5 h-3.5" />
                <span>{angle.manual_shot_map?.length > 0 ? `แก้ช็อต (${angle.manual_shot_map.length} ท่อน)` : 'เลือกช็อตของสคริปต์'}</span>
              </button>
            )}
          </div>
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
            const cat = sceneCatalogsMap[path];
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
                {cat?.is_indexed ? (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenSceneCatalog && onOpenSceneCatalog(path, fileName, cat);
                    }}
                    className="ml-0.5 text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/35 text-emerald-300 font-bold border border-emerald-500/40 whitespace-nowrap cursor-pointer flex items-center gap-1 transition-all active:scale-95 shadow-xs"
                    title={`คลิกเพื่อดูสารบัญฉาก ${cat.scenes_count} ฉาก (ตรวจดูมุมมองและจังหวะตัด)`}
                  >
                    <span>⚡ {cat.scenes_count} ฉาก</span>
                    <Eye className="w-3 h-3 text-emerald-400" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onIndexSceneCatalog && onIndexSceneCatalog(path);
                    }}
                    disabled={isScanningScenes}
                    className="ml-0.5 text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 cursor-pointer whitespace-nowrap disabled:opacity-50"
                    title="สแกนสารบัญฉากด้วย Vision AI ทันที"
                  >
                    ⚡ สแกนฉาก
                  </button>
                )}
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
        {isPosted ? (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            {angle.video_url && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onPreviewExportVideo && onPreviewExportVideo(angle);
                }}
                className="flex-1 sm:flex-initial py-3 sm:py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer active:scale-95 transition-all"
                title="เปิดดูวิดีโอที่โพสต์แล้วบน TikTok"
              >
                <Film className="w-4 h-4 text-cyan-400" />
                <span>ดูคลิปที่โพสต์แล้ว</span>
              </button>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onCloneAngle && onCloneAngle(angle, index);
              }}
              className="flex-1 sm:flex-initial py-3 sm:py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.12] text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all"
              title="คัดลอกสคริปต์นี้เป็นฉบับใหม่เพื่อตัดต่อใหม่โดยไม่กระทบคลิปเดิม"
            >
              <CopyPlus className="w-4 h-4 text-[#25F4EE]" />
              <span>ทำซ้ำเพื่อตัดคลิปใหม่</span>
            </button>
          </div>
        ) : isRendered ? (
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
          <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts) onSendToStudio(angle, index);
                else onGenerateShotList && onGenerateShotList(index);
              }}
              className={`order-2 w-full sm:w-auto py-3 sm:py-2.5 px-5 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 cursor-pointer active:scale-95 transition-all ${
                shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts
                  ? 'bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/[0.12]'
                  : 'bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 shadow-lg shadow-[#25F4EE]/15'
              }`}
            >
              {shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts
                ? <Clapperboard className="w-4 h-4" />
                : <Mic className="w-4 h-4" />}
              <span>{shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts ? 'ตั้งค่าก่อนส่ง' : 'เตรียมเสียงและแผนถ่าย'}</span>
            </button>

            {Boolean(shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts) && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onQuickDraft ? onQuickDraft(angle, index) : onSendToStudio(angle, index);
                }}
                disabled={draftingAngleId === angle.angle_id}
                className="order-1 w-full sm:w-auto py-3 sm:py-2.5 px-5 rounded-xl bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 border border-[#25F4EE]/50 text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#25F4EE]/15 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                title="1-Click Quick Draft: สร้างดราฟต์ไทม์ไลน์อัตโนมัติตามสไตล์ของมุมนี้และเปิดเข้าสู่ไทม์ไลน์ทันที"
              >
                {draftingAngleId === angle.angle_id ? (
                  <>
                    <Loader2 className="w-4 h-4 text-white animate-spin" />
                    <span>กำลังสร้างดราฟต์...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>สร้างดราฟต์ 1-Click</span>
                  </>
                )}
              </button>
            )}

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenStoryboard && onOpenStoryboard(angle, index);
              }}
              className={`hidden w-full sm:w-auto py-3 sm:py-2.5 px-4 rounded-xl border text-xs sm:text-sm font-bold items-center justify-center gap-2 shadow-sm cursor-pointer active:scale-95 transition-all ${
                angle.manual_shot_map?.length > 0
                  ? 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border-emerald-500/40 shadow-xs'
                  : 'bg-cyan-500/15 hover:bg-cyan-500/25 border-cyan-500/35 text-cyan-300'
              }`}
              title="กำหนดช็อตวิดีโอด้วยตนเองรายวรรคบทพูด (Manual Storyboard Mapper)"
            >
              <Scissors className="w-4 h-4" />
              <span>{angle.manual_shot_map?.length > 0 ? `ล็อกช็อต (${angle.manual_shot_map.length} วรรค)` : 'วางแผนช็อตรายวรรค'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// 📝 ACCORDION SCRIPT ITEM (with Angle-Specific Footage Selector)
// ═══════════════════════════════════════════════════════════════════════
function ScriptAccordionItem({
  angle, index, isOpen, onToggle, onCopy, onSendToStudio, onOpenInTimeline, onPreviewExportVideo, onCloneAngle, copiedIndex,
  videos = [], onToggleVideoForAngle, onUploadVideo, uploadingImg = false,
  onOpenMediaPicker,
  onSaveScript, onOpenFindReplace, onRerollScript, onGenerateShotList,
  isGeneratingShotList = false, onOpenHookVariants,
  productData, onOpenEditHookHeader,
  shotListInfo, onQuickDraft, draftingAngleId,
  sceneCatalogsMap = {}, onIndexSceneCatalog, isScanningScenes = false, onOpenSceneCatalog,
  onOpenStoryboard,
}) {
  const effectiveBrand = angle.hook_brand ?? productData?.hook_brand ?? guessBrandModel(angle.product_name || productData?.name || productData?.title || '').brand;
  const effectiveModel = angle.hook_model ?? productData?.hook_model ?? guessBrandModel(angle.product_name || productData?.name || productData?.title || '').model;
  const effectiveLabel = angle.hook_label ?? productData?.hook_label ?? '';
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
  const isInProduction = !isPosted && curStatus === 'in_production';
  const isLocked = isPosted || isInProduction || isRendered;

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

  const handleAddLine = () => {
    setEditText((current) => current ? `${current}\n` : '\n');
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
            <p className="text-sm text-slate-500 truncate mt-0.5">
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
                  : isRendered
                    ? 'ตัดต่อเสร็จแล้ว ระบบล็อกเนื้อหาและคลิปเพื่อคงความตรงกันกับวิดีโอที่สร้างไว้'
                    : 'สคริปต์นี้กำลังตัดต่อในไทม์ไลน์ ล็อกเนื้อหาและคลิปเพื่อความสอดคล้องกับไทม์ไลน์'}
              </span>
            </div>
          )}

          {/* Hook Header (3-tier Banner) */}
          <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
                <Tag className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>Hook Header · 3 ป้ายบนวิดีโอ:</span>
              </div>
              {!isLocked && onOpenEditHookHeader && (
                <button
                  type="button"
                  onClick={() => onOpenEditHookHeader(index)}
                  className="text-xs font-bold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer transition-colors"
                  title="แก้ไขแบรนด์, รุ่น และหมวดสินค้าสำหรับป้าย Hook"
                >
                  <Edit3 className="w-3 h-3" />
                  <span>แก้ 3 ป้าย</span>
                </button>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
                <span className="text-slate-500 font-semibold">แบรนด์:</span>
                <strong className="text-cyan-300">{effectiveBrand || '—'}</strong>
              </span>
              <span className="px-2 py-0.5 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
                <span className="text-slate-500 font-semibold">รุ่น:</span>
                <strong className="text-amber-300">{effectiveModel || '—'}</strong>
              </span>
              {effectiveLabel && (
                <span className="px-2 py-0.5 rounded-lg bg-black/50 border border-white/[0.1] text-xs text-white flex items-center gap-1">
                  <span className="text-slate-500 font-semibold">หมวด:</span>
                  <strong className="text-emerald-300">{effectiveLabel}</strong>
                </span>
              )}
            </div>
          </div>

          {/* Hook Highlight / Editor */}
          {angle.hook_title && !isEditing && (
            <div className={`p-2.5 rounded-lg border-l-[3px] text-xs sm:text-sm font-bold leading-snug flex items-center justify-between gap-2 ${
              isLocked
                ? 'bg-black/30 border-slate-600 text-slate-300'
                : 'bg-black/50 border-[#25F4EE] text-cyan-200'
            }`}>
              <span className="flex-1 min-w-0 whitespace-normal break-words leading-relaxed">{angle.hook_title}</span>
              {!isLocked && onOpenHookVariants && (
                <button
                  type="button"
                  onClick={() => onOpenHookVariants(angle, index)}
                  className="px-2 py-0.5 rounded-md bg-cyan-400/[0.1] hover:bg-cyan-400/[0.2] border border-cyan-400/30 text-cyan-300 text-[11px] font-bold flex items-center gap-1 flex-shrink-0 transition-colors"
                  title="สร้าง Hook ทางเลือก 5 สไตล์ด้วย AI"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>สร้าง Hook</span>
                </button>
              )}
            </div>
          )}

          {/* Script Editing Box OR Read-Only Display */}
          {isEditing ? (
            <div className="space-y-2.5 p-3 rounded-xl bg-black/60 border border-[#25F4EE]/40 animate-fadeIn">
               <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#25F4EE] font-bold">
                <span className="flex items-center gap-1.5">
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>แก้ไขบทพูด (1 บรรทัด = 1 ท่อน):</span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleAddLine}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[#25F4EE] hover:text-white hover:bg-[#25F4EE]/10"
                    title="เพิ่มบรรทัดบทพูดอีก 1 ท่อน"
                  >
                    <Plus className="w-3 h-3" /> เพิ่มบรรทัด
                  </button>
                  <span className="text-slate-400 text-[11px] font-mono">
                    {editText.split('\n').filter(l => l.trim()).length} ท่อน
                  </span>
                </div>
              </div>

              {/* Hook Input */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-slate-400">Hook พาดหัวคลิป:</label>
                  {onOpenHookVariants && (
                    <button
                      type="button"
                      onClick={() => onOpenHookVariants(angle, index)}
                      className="text-cyan-300 hover:text-cyan-200 text-[10px] font-bold flex items-center gap-1 cursor-pointer"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>AI เจน Hook 5 สไตล์</span>
                    </button>
                  )}
                </div>
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
                  💡 แต่ละบรรทัดจะกลายเป็นซับไตเติล 1 ท่อน · กด Enter เพื่อเพิ่มบรรทัดใหม่ได้
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
                        title="แก้ไข Hook และบทพูดในกล่องนี้โดยตรง"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>แก้ Hook + บทพูด</span>
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
                const cat = sceneCatalogsMap[path];
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
                    {cat?.is_indexed ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenSceneCatalog && onOpenSceneCatalog(path, fileName, cat);
                        }}
                        className="ml-0.5 text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/35 text-emerald-300 font-bold border border-emerald-500/40 whitespace-nowrap cursor-pointer flex items-center gap-1 transition-all active:scale-95 shadow-xs"
                        title={`คลิกเพื่อดูสารบัญฉาก ${cat.scenes_count} ฉาก (ตรวจดูมุมมองและจังหวะตัด)`}
                      >
                        <span>⚡ {cat.scenes_count} ฉาก</span>
                        <Eye className="w-3 h-3 text-emerald-400" />
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onIndexSceneCatalog && onIndexSceneCatalog(path);
                        }}
                        disabled={isScanningScenes}
                        className="ml-0.5 text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 cursor-pointer whitespace-nowrap disabled:opacity-50"
                        title="สแกนสารบัญฉากด้วย Vision AI ทันที"
                      >
                        ⚡ สแกนฉาก
                      </button>
                    )}
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
            {isPosted ? (
              <>
                {angle.video_url && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onPreviewExportVideo && onPreviewExportVideo(angle);
                    }}
                    className="py-2 px-3.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-cyan-500/10 cursor-pointer active:scale-95 transition-all"
                    title="เปิดดูวิดีโอที่โพสต์แล้วบน TikTok (หลักฐาน)"
                  >
                    <Film className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ดูคลิปที่โพสต์แล้ว</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloneAngle && onCloneAngle(angle, index);
                  }}
                  className="py-2 px-3.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.12] text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
                  title="คัดลอกสคริปต์นี้เป็นฉบับใหม่เพื่อตัดต่อใหม่โดยไม่กระทบคลิปเดิม"
                >
                  <CopyPlus className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>ทำซ้ำเพื่อตัดคลิปใหม่</span>
                </button>
              </>
            ) : isRendered ? (
              <>
                {angle.video_url && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onPreviewExportVideo && onPreviewExportVideo(angle);
                    }}
                    className="py-2 px-3.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-400/40 text-cyan-300 hover:text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-cyan-500/10 cursor-pointer active:scale-95 transition-all"
                    title="เปิดดูวิดีโอที่ตัดต่อและ Export เสร็จแล้ว (ตรวจ QC)"
                  >
                    <Film className="w-3.5 h-3.5 text-cyan-400" />
                    <span>ดูคลิปที่ Export แล้ว</span>
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
                  title="เปิดดูวิดีโอที่ตัดเสร็จแล้วในไทม์ไลน์ทันที"
                >
                  <Play className="w-3.5 h-3.5 fill-white text-white" />
                  <span>เปิดดูในไทม์ไลน์</span>
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
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts) onSendToStudio(angle, index);
                    else onGenerateShotList && onGenerateShotList(index);
                  }}
                  className={`order-2 py-2 px-4 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all ${
                    shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts
                      ? 'bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/[0.12]'
                      : 'bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 shadow-lg shadow-[#25F4EE]/15'
                  }`}
                >
                  {shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts
                    ? <Clapperboard className="w-3.5 h-3.5" />
                    : <Mic className="w-3.5 h-3.5" />}
                  <span>{shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts ? 'ตั้งค่าก่อนส่ง' : 'เตรียมเสียงและแผนถ่าย'}</span>
                </button>

                {Boolean(shotListInfo?.has_shot_list && !shotListInfo?.is_edge_tts) && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onQuickDraft ? onQuickDraft(angle, index) : onSendToStudio(angle, index);
                    }}
                    disabled={draftingAngleId === angle.angle_id}
                    className="order-1 py-2 px-3.5 rounded-xl bg-[#25F4EE] hover:bg-[#4ff8f2] border border-[#25F4EE]/50 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-[#25F4EE]/15 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
                    title="1-Click Quick Draft: สร้างดราฟต์ไทม์ไลน์อัตโนมัติตามสไตล์ของมุมนี้และเปิดเข้าสู่ไทม์ไลน์ทันที"
                  >
                    {draftingAngleId === angle.angle_id ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                        <span>กำลังสร้างดราฟต์...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-3.5 h-3.5" />
                        <span>สร้างดราฟต์ 1-Click</span>
                      </>
                    )}
                  </button>
                )}

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenStoryboard && onOpenStoryboard(angle, index);
                  }}
                  className={`hidden w-full sm:w-auto py-3 sm:py-2.5 px-4 rounded-xl border text-xs sm:text-sm font-bold items-center justify-center gap-2 shadow-sm cursor-pointer active:scale-95 transition-all ${
                    angle.manual_shot_map?.length > 0
                      ? 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border-emerald-500/40 shadow-xs'
                      : 'bg-cyan-500/15 hover:bg-cyan-500/25 border-cyan-500/35 text-cyan-300'
                  }`}
                  title="กำหนดช็อตวิดีโอด้วยตนเองรายวรรคบทพูด (Manual Storyboard Mapper)"
                >
                  <Scissors className="w-4 h-4" />
                  <span>{angle.manual_shot_map?.length > 0 ? `ล็อกช็อต (${angle.manual_shot_map.length} วรรค)` : 'วางแผนช็อตรายวรรค'}</span>
                </button>
              </div>
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
export default function ProductToClip({ status, videos = [], onRefresh, onApplyToStudio, onGoToGallery, selectedProductId, pendingFlowTaskVersion, consumePendingAngleId, consumePendingImageMetadataPreview, workspaceData }) {
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
  const { toastMessage, toastType, toastDuration, showToast, hideToast } = useToast();
  const { refreshTrigger, toggleActivityDrawer, activeTasks, pollTasks } = useTaskManager();

  // Collect all known project names across this product to avoid collisions across batches
  const knownProjects = useMemo(() => {
    const list = [];
    (productData?.projects || []).forEach((p) => {
      if (p) list.push(typeof p === 'string' ? p : p.project_name);
    });
    (productData?.angles || []).forEach((a) => {
      if (a?.project_name) list.push(a.project_name);
    });
    return list;
  }, [productData]);
  const readProducts = (options = {}) => workspaceData?.loadProducts
    ? workspaceData.loadProducts(options)
    : getProducts();

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
  const [deleteTargetAngle, setDeleteTargetAngle] = useState(null);
  const [isDeletingAngle, setIsDeletingAngle] = useState(false);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'accordion'
  const [productToolsOpen, setProductToolsOpen] = useState(false);

  const hiddenProductsCount = useMemo(() => {
    return (historyList || []).filter(p => !!p.is_hidden).length;
  }, [historyList]);

  const activeProductsCount = useMemo(() => {
    return (historyList || []).filter(p => !p.is_hidden).length;
  }, [historyList]);

  const unstartedVisibleProducts = useMemo(() => {
    return (historyList || []).filter(p => {
      if (p.is_hidden) return false;
      const done = (p.angles || []).filter(a => a.status === 'posted' || a.status === 'rendered').length;
      return done === 0;
    });
  }, [historyList]);

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
    if (productFilter === 'hidden') {
      list = list.filter(p => !!p.is_hidden);
    } else {
      list = list.filter(p => !p.is_hidden);
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
  const [shotListError, setShotListError] = useState(null);
  const [shotListStatusMap, setShotListStatusMap] = useState({}); // {angle_id: {has_shot_list, is_stale, voice_engine_type, voice_preset, is_edge_tts}}
  const [storyboardAngle, setStoryboardAngle] = useState(null); // angle opened in ManualStoryboardModal
  const [filmingRecipeModalOpen, setFilmingRecipeModalOpen] = useState(false);

  // Automatically keep shotListStatusMap updated whenever current productData changes
  useEffect(() => {
    if (productData?.id) {
      getShotListStatus(productData.id)
        .then(res => setShotListStatusMap(res.status || {}))
        .catch(() => setShotListStatusMap({}));
    }
  }, [productData?.id]);

  const getShotListInfoForAngle = useCallback((ang) => {
    if (!ang) return null;
    const angId = ang.angle_id || ang.id;
    if (!angId) return null;
    const bKey = `${angId}_b${ang.batch || 1}`;
    if (shotListStatusMap[bKey]) return shotListStatusMap[bKey];
    if (!ang.batch || ang.batch === 1) return shotListStatusMap[angId] || null;
    return null;
  }, [shotListStatusMap]);

  const [hookModalAngle, setHookModalAngle] = useState(null);

  // Batch Render Modal State
  const [batchRenderOpen, setBatchRenderOpen] = useState(false);

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
      workspaceData?.invalidateTrackerData?.();

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

  // Hook Header Modal State
  const [hookHeaderModalOpen, setHookHeaderModalOpen] = useState(false);
  const [hookHeaderAngleIdx, setHookHeaderAngleIdx] = useState(0);

  // Uploading Screenshot/Image
  const [uploadingImg, setUploadingImg] = useState(false);
  const fileInputRef = useRef(null);

  // Load History on Mount or when background task finishes
  const loadHistory = async (targetId = null, isStale = () => false) => {
    const requestId = ++historyRequestRef.current;
    setLoadingHistory(true);
    try {
      const res = await readProducts();
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
      angles: item.angles || [],
    });
    const nextAngles = item.angles || [];
    setAngles(nextAngles);
    // Fetch shot-list status for sidebar badges (fire-and-forget)
    getShotListStatus(item.id).then(res => setShotListStatusMap(res.status || {})).catch(() => setShotListStatusMap({}));
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
    let restoredIdx = -1;
    if (pendingId) {
      if (typeof pendingId === 'object' && pendingId.angle_id) {
        restoredIdx = nextAngles.findIndex(
          a => a.angle_id === pendingId.angle_id && (a.batch || 1) === (pendingId.batch || 1)
        );
      } else {
        restoredIdx = nextAngles.findIndex(a => a.angle_id === pendingId);
      }
    }
    setOpenAngleIdx(restoredIdx >= 0 ? restoredIdx : 0);
    setSelectedImages([]);
  };

  const [batchHiding, setBatchHiding] = useState(false);

  const handleToggleHideProduct = async (prod, e) => {
    e?.stopPropagation?.();
    if (!prod?.id) return;
    const newHidden = !prod.is_hidden;
    try {
      const res = await updateProduct(prod.id, { is_hidden: newHidden });
      if (res.product) {
        setHistoryList(prev => prev.map(p => p.id === res.product.id ? { ...p, ...res.product } : p));
        // If the currently selected product was hidden and we're not in the hidden filter,
        // switch selection to the first available non-hidden product
        if (newHidden && selectedHistoryId === prod.id && productFilter !== 'hidden') {
          const remaining = (historyList || []).filter(p => p.id !== prod.id && !p.is_hidden);
          if (remaining.length > 0) {
            selectProduct(remaining[0]);
          }
        }
        workspaceData?.invalidateTrackerData?.();
        showToast(
          newHidden
            ? `ซ่อน "${prod.name || prod.title || 'สินค้า'}" เรียบร้อยแล้ว`
            : `ยกเลิกการซ่อน "${prod.name || prod.title || 'สินค้า'}" เรียบร้อยแล้ว`,
          'info'
        );
      }
    } catch (err) {
      console.error('Failed to toggle product hidden status:', err);
      showToast('ไม่สามารถเปลี่ยนสถานะซ่อนสินค้าได้: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleBatchHideUnstarted = async () => {
    if (unstartedVisibleProducts.length === 0) {
      showToast('ไม่มีสินค้าที่ยังไม่เริ่มทำที่ต้องซ่อนครับ', 'info');
      return;
    }
    setBatchHiding(true);
    try {
      await Promise.all(
        unstartedVisibleProducts.map(p => updateProduct(p.id, { is_hidden: true }))
      );
      const updatedIds = new Set(unstartedVisibleProducts.map(p => p.id));
      setHistoryList(prev => prev.map(p => updatedIds.has(p.id) ? { ...p, is_hidden: true } : p));
      // If current product was hidden, select a remaining visible product
      if (selectedHistoryId && updatedIds.has(selectedHistoryId)) {
        const remaining = (historyList || []).filter(p => !updatedIds.has(p.id) && !p.is_hidden);
        if (remaining.length > 0) {
          selectProduct(remaining[0]);
        }
      }
      workspaceData?.invalidateTrackerData?.();
      showToast(`ซ่อนสินค้าที่ยังไม่ทำ ${unstartedVisibleProducts.length} รายการเรียบร้อยแล้ว`, 'success');
    } catch (err) {
      console.error('Failed to batch hide unstarted products:', err);
      showToast('เกิดข้อผิดพลาดในการซ่อนสินค้า: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setBatchHiding(false);
    }
  };

  const handleBatchUnhideAll = async () => {
    const hiddenItems = (historyList || []).filter(p => !!p.is_hidden);
    if (hiddenItems.length === 0) return;
    try {
      await Promise.all(hiddenItems.map(p => updateProduct(p.id, { is_hidden: false })));
      setHistoryList(prev => prev.map(p => ({ ...p, is_hidden: false })));
      setProductFilter('all');
      workspaceData?.invalidateTrackerData?.();
      showToast(`ยกเลิกการซ่อนสินค้าทั้งหมด ${hiddenItems.length} รายการแล้ว`, 'success');
    } catch (err) {
      console.error('Failed to unhide all products:', err);
      showToast('ไม่สามารถยกเลิกการซ่อนทั้งหมดได้: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleAngleStatusChange = async (angleId, nextStatus, batch = null) => {
    if (!productData?.id) return;
    try {
      await updateAngleStatus(productData.id, angleId, nextStatus, null, null, null, false, false, null, false, batch);
      setAngles(prev => prev.map(a => (a.angle_id === angleId && (batch === null || (a.batch || 1) === batch)) ? { ...a, status: nextStatus } : a));
      workspaceData?.invalidateTrackerData?.();
      const res = await readProducts({ force: true });
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
      workspaceData?.invalidateTrackerData?.();
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
      workspaceData?.invalidateTrackerData?.();
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

  const handleSaveHookHeader = async ({ hookBrand, hookModel, hookLabel, scope, syncScriptText, angleIndex }) => {
    if (!productData?.id) return;

    let updatedAngles = [...angles];
    const targetAngle = angles[angleIndex] || {};
    const oldBrand = targetAngle.hook_brand || productData.hook_brand || '';
    const oldModel = targetAngle.hook_model || productData.hook_model || '';

    if (scope === 'all') {
      updatedAngles = angles.map((ang) => {
        const nextAng = {
          ...ang,
          hook_brand: hookBrand,
          hook_model: hookModel,
          hook_label: hookLabel,
        };
        if (syncScriptText && (oldBrand || oldModel)) {
          let lines = ang.script_lines || [];
          if (oldBrand && hookBrand && oldBrand !== hookBrand) {
            lines = lines.map(l => l.replaceAll(oldBrand, hookBrand));
          }
          if (oldModel && hookModel && oldModel !== hookModel) {
            lines = lines.map(l => l.replaceAll(oldModel, hookModel));
          }
          nextAng.script_lines = lines;
          nextAng.script_text = lines.join('\n');
        }
        return nextAng;
      });
      setAngles(updatedAngles);

      try {
        const res = await updateProduct(productData.id, {
          hook_brand: hookBrand,
          hook_model: hookModel,
          hook_label: hookLabel,
          angles: updatedAngles,
          apply_to_angles: true,
        });
        workspaceData?.invalidateTrackerData?.();
        if (res.product) {
          setProductData(prev => ({ ...prev, ...res.product, angles: res.product.angles || updatedAngles }));
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
        showToast(`อัปเดตป้าย Hook ไปยังทั้ง ${angles.length} สคริปต์ เรียบร้อยแล้ว!`);
      } catch (err) {
        console.error('Failed to update hook header:', err);
        showToast('ไม่สามารถอัปเดตป้าย Hook ได้: ' + err.message, 'error');
      }
    } else {
      updatedAngles = angles.map((ang, idx) => {
        if (idx !== angleIndex) return ang;
        const nextAng = {
          ...ang,
          hook_brand: hookBrand,
          hook_model: hookModel,
          hook_label: hookLabel,
        };
        if (syncScriptText && (oldBrand || oldModel)) {
          let lines = ang.script_lines || [];
          if (oldBrand && hookBrand && oldBrand !== hookBrand) {
            lines = lines.map(l => l.replaceAll(oldBrand, hookBrand));
          }
          if (oldModel && hookModel && oldModel !== hookModel) {
            lines = lines.map(l => l.replaceAll(oldModel, hookModel));
          }
          nextAng.script_lines = lines;
          nextAng.script_text = lines.join('\n');
        }
        return nextAng;
      });
      setAngles(updatedAngles);

      try {
        const res = await updateProduct(productData.id, { angles: updatedAngles });
        workspaceData?.invalidateTrackerData?.();
        if (res.product) {
          setProductData(prev => ({ ...prev, ...res.product, angles: res.product.angles || updatedAngles }));
          setHistoryList(prev => prev.map(p => p.id === res.product.id ? res.product : p));
        }
        showToast(`อัปเดตป้าย Hook เฉพาะมุมที่ ${angleIndex + 1} เรียบร้อยแล้ว!`);
      } catch (err) {
        console.error('Failed to update hook header:', err);
        showToast('ไม่สามารถอัปเดตป้าย Hook ได้: ' + err.message, 'error');
      }
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

    const targetBatch = targetAngle.batch || 1;
    setRerollingScript(true);
    try {
      const res = await rerollAngleScript(productData.id, targetAngle.angle_id, {
        duration: rerollDuration,
        extra_beats: rerollExtraBeats,
        batch: targetBatch,
      });
      if (res.success && res.task_id) {
        pendingRerollAngleIdRef.current = { angle_id: targetAngle.angle_id, batch: targetBatch };
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

  const handleHookApplied = (updatedAngle) => {
    if (!updatedAngle) return;
    const isTarget = (a) =>
      ((a.angle_id && a.angle_id === updatedAngle.angle_id) || (a.id && a.id === updatedAngle.id)) &&
      (a.batch || 1) === (updatedAngle.batch || 1);
    setAngles(prev => prev.map(a => isTarget(a) ? { ...a, ...updatedAngle } : a));
    if (productData?.id) {
      setProductData(prev => prev ? {
        ...prev,
        angles: (prev.angles || []).map(a => isTarget(a) ? { ...a, ...updatedAngle } : a)
      } : prev);
      setHistoryList(prev => prev.map(p => p.id === productData.id ? {
        ...p,
        angles: (p.angles || []).map(a => isTarget(a) ? { ...a, ...updatedAngle } : a)
      } : p));
    }
  };

  const handleBatchCompleted = async () => {
    if (productData?.id) {
      try {
        workspaceData?.invalidateTrackerData?.();
        const res = await readProducts({ force: true });
        const updated = res.products || [];
        setHistoryList(updated);
        const current = updated.find(p => p.id === productData.id);
        if (current) {
          setProductData(current);
          setAngles(current.angles || []);
        }
      } catch (err) {
        console.error('Failed to reload products after batch render:', err);
      }
    }
  };

  // ── Shot-list generation (per-beat filming plan from real TTS timing) ──
  // Runs the actual generate-task + poll cycle. Only called when there's no
  // existing shot list yet, or the user explicitly asks to regenerate one
  // (via the modal's "สร้างใหม่" action) -- never as the default click
  const resolveAdTone = (tone) => (tone && tone !== 'commercial_premium' && ['commercial_hype', 'commercial_aesthetic', 'commercial_expert'].includes(tone)) ? tone : 'commercial_hype';

  // behavior, since re-running this re-synthesizes the voiceover from
  // scratch every time.
  const runShotListGeneration = async (angleIdx, targetAngle, voiceOverrides = {}) => {
    setGeneratingShotListIdx(angleIdx);
    setShotListError(null);
    try {
      const overrides = {
        voice_engine_type: 'gemini_tts',
        voice_preset: targetAngle.voice_preset || 'gemini_fenrir_male_strong',
        voice_rate: '+15%',
        ad_tone: resolveAdTone(targetAngle.ad_tone),
        batch: targetAngle.batch || 1,
        ...voiceOverrides,
      };
      const res = await generateShotList(productData.id, targetAngle.angle_id, overrides);
      if (!res.success || !res.task_id) {
        const errText = 'ไม่สามารถเริ่มสร้างแผนถ่ายได้';
        setShotListError(errText);
        showToast(errText, 'error');
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
          const errMsg = task.error || 'สร้างแผนถ่ายไม่สำเร็จ';
          setShotListError(errMsg);
          showToast('สร้างแผนถ่ายไม่สำเร็จ: ' + errMsg, 'error');
          return;
        }
      }
      if (!result) {
        const timeoutMsg = 'สร้างแผนถ่ายใช้เวลานานเกินไป กรุณาลองใหม่';
        setShotListError(timeoutMsg);
        showToast(timeoutMsg, 'error');
        return;
      }
      const updatedAngle = { ...targetAngle, voice_preset: overrides.voice_preset };
      setShotListResult({ angle: updatedAngle, ...result });
      setShotListAngleIdx(angleIdx);
      setShotListError(null);
      // Refresh sidebar shot-list badges after generation
      if (productData?.id) getShotListStatus(productData.id).then(res => setShotListStatusMap(res.status || {})).catch(() => {});
    } catch (err) {
      const failMsg = err.friendlyMessage || err.message || 'ไม่สามารถสร้างแผนถ่ายได้';
      setShotListError(failMsg);
      console.error('Failed to generate shot list:', err);
      showToast('ไม่สามารถสร้างแผนถ่ายได้: ' + failMsg, 'error');
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
      const existing = await getShotList(productData.id, targetAngle.angle_id, targetAngle.batch || 1);
      setShotListResult({ angle: targetAngle, ...existing });
      setShotListAngleIdx(angleIdx);
      setGeneratingShotListIdx(null);
    } catch {
      // 404 (or any other lookup failure) -- no shot list yet, generate one.
      await runShotListGeneration(angleIdx, targetAngle);
    }
  };

  const handleRegenerateShotList = (overrides = {}) => {
    if (shotListAngleIdx === null) return;
    const targetAngle = angles[shotListAngleIdx];
    if (!targetAngle?.angle_id) return;
    runShotListGeneration(shotListAngleIdx, targetAngle, overrides);
  };

  const handleOpenStoryboard = (targetAngle, targetIdx = 0) => {
    if (!targetAngle) return;
    setStoryboardAngle(targetAngle);
  };

  const handleStoryboardSaveSuccess = (pinArray) => {
    if (!storyboardAngle) return;
    const targetAngleId = storyboardAngle.angle_id || storyboardAngle.id;
    const targetBatch = storyboardAngle.batch || 1;
    setAngles((prev) =>
      prev.map((a) => {
        if ((a.angle_id || a.id) === targetAngleId && (a.batch || 1) === targetBatch) {
          return { ...a, manual_shot_map: pinArray };
        }
        return a;
      })
    );
    if (productData?.angles) {
      productData.angles = productData.angles.map((a) => {
        if ((a.angle_id || a.id) === targetAngleId && (a.batch || 1) === targetBatch) {
          return { ...a, manual_shot_map: pinArray };
        }
        return a;
      });
    }
  };

  const handleDeleteHistory = (target) => {
    if (!target) return;
    setDeleteTargetProduct(target);
  };

  const confirmDeleteProduct = async () => {
    if (!deleteTargetProduct?.id) return;
    setIsDeletingProduct(true);
    try {
      await deleteProduct(deleteTargetProduct.id, true);
      showToast('ลบสินค้าและสคริปต์ทั้งหมดเรียบร้อยแล้ว');
      workspaceData?.invalidateTrackerData?.();
      const res = await readProducts({ force: true });
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
      const msg = err.response?.data?.detail || err.friendlyMessage || err.message;
      showToast('ลบไม่สำเร็จ: ' + msg, 'error');
    } finally {
      setIsDeletingProduct(false);
    }
  };

  const handleDeleteAngleClick = (angle, index) => {
    if (!angle) return;
    if (angle.status === 'posted') {
      showToast('ไม่อนุญาตให้ลบมุมที่โพสต์แล้ว', 'error');
      return;
    }
    setDeleteTargetAngle({ angle, index });
  };

  const confirmDeleteAngle = async () => {
    if (!deleteTargetAngle || !productData?.id) return;
    const { angle, index } = deleteTargetAngle;
    const angleId = angle.angle_id || angle.id;
    if (!angleId) {
      showToast('ไม่พบรหัสประจำมุม (angle_id)', 'error');
      setDeleteTargetAngle(null);
      return;
    }

    setIsDeletingAngle(true);
    try {
      await deleteProductAngle(productData.id, angleId, angle.batch || 1);
      showToast(`ลบสคริปต์ "${angle.angle_name || 'มุมนี้'}" เรียบร้อยแล้ว`);
      workspaceData?.invalidateTrackerData?.();
      const res = await readProducts({ force: true });
      const updated = res.products || [];
      setHistoryList(updated);
      const current = updated.find((p) => p.id === productData.id);
      if (current) {
        selectProduct(current);
      }
      setDeleteTargetAngle(null);
      if (activeAngleIdx >= index) {
        setActiveAngleIdx((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Failed to delete angle:', err);
      showToast(err?.response?.data?.detail || err?.message || 'เกิดข้อผิดพลาดในการลบสคริปต์', 'error');
    } finally {
      setIsDeletingAngle(false);
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
        workspaceData?.invalidateTrackerData?.();
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
      workspaceData?.invalidateTrackerData?.();
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
      workspaceData?.invalidateTrackerData?.();
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
      workspaceData?.invalidateTrackerData?.();
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
        const isAngleInProd = curStatus === 'in_production';
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
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, selectedPaths, targetAngle.batch || 1);
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
    const isInProduction = curStatus === 'in_production';
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
        const res = await updateAngleVideos(productData.id, targetAngle.angle_id, newVideos, targetAngle.batch || 1);
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

    const targetBatch = angle.batch || 1;
    const resolvedIndex = typeof angleIdx === 'number' && angleIdx >= 0
      ? angleIdx
      : angles.findIndex(a => 
          ((a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title) &&
          (a.batch || 1) === targetBatch
        );

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
      batch: targetBatch,
      productName: angle.product_name || productData?.title || customKeyword || 'สินค้า',
      // The banner's three tiers come from the angle (the script AI splits
      // the product name) and fall back to a whitespace split. They used to
      // be left blank here on purpose, which meant the first render burned
      // the whole product name into the brand tier and nothing into the rest.
      hookBrand: angle.hook_brand || productData?.hook_brand || guessBrandModel(angle.product_name || productData?.title || '').brand,
      hookModel: angle.hook_model || productData?.hook_model || guessBrandModel(angle.product_name || productData?.title || '').model,
      hookLabel: angle.hook_label || productData?.hook_label || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: resolveAdTone(angle.ad_tone),
      voicePreset: angle.voice_preset || 'gemini_fenrir_male_strong',
      voiceGender: 'male',
      voiceMode: 'gemini_tts',
      voiceSpeed: '+15%',
      shotListId: `${productData?.id}:${angle.angle_id}`,
      selectedVideo: primaryVideo,
      selectedVideos: chosenVideos,
      manualShotMap: angle.manual_shot_map || [],
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
    const targetBatch = angle.batch || 1;
    const resolvedIndex = typeof index === 'number'
      ? index
      : angles.findIndex(a => 
          ((a.angle_id && a.angle_id === angle.angle_id) || a.hook_title === angle.hook_title) &&
          (a.batch || 1) === targetBatch
        );

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
      hookBrand: angle.hook_brand || productData?.hook_brand || guessBrandModel(angle.product_name || productData?.title || '').brand,
      hookModel: angle.hook_model || productData?.hook_model || guessBrandModel(angle.product_name || productData?.title || '').model,
      hookLabel: angle.hook_label || productData?.hook_label || '',
      customScript: scriptText,
      keyFeatures: angle.key_features || productData?.description || '',
      painPoint: angle.pain_point || '',
      priceDeal: angle.price_deal || productData?.price_note || '',
      adTone: resolveAdTone(angle.ad_tone),
      voicePreset: angle.voice_preset || 'gemini_fenrir_male_strong',
      voiceGender: 'male',
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

  const handleCloneAngle = async (angle, index) => {
    if (!productData?.id) return;
    const baseAngle = angle || (typeof index === 'number' ? angles[index] : null);
    if (!baseAngle) return;

    const clonedAngleId = `angle_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const clonedAngle = {
      ...baseAngle,
      angle_id: clonedAngleId,
      hook_title: baseAngle.hook_title ? `${baseAngle.hook_title} (ฉบับใหม่)` : 'สคริปต์ฉบับใหม่',
      status: 'scripted',
      project_name: null,
      video_url: null,
      posted_at: null,
      is_posted: false,
    };

    const nextAngles = [...angles, clonedAngle];
    setAngles(nextAngles);
    setOpenAngleIdx(nextAngles.length - 1);

    try {
      const res = await updateProduct(productData.id, { angles: nextAngles });
      workspaceData?.invalidateTrackerData?.();
      if (res?.product) {
        setProductData(prev => ({ ...prev, ...res.product, angles: res.product.angles }));
      }
      showToast('คัดลอกเป็นสคริปต์ฉบับใหม่เรียบร้อย พร้อมสำหรับตัดต่อใหม่!');
    } catch (e) {
      console.error('Clone angle failed:', e);
      showToast('เกิดข้อผิดพลาดในการคัดลอกสคริปต์');
    }
  };

  const [selectedBatch, setSelectedBatch] = useState('all');
  const [hidePosted, setHidePosted] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [batchToolsOpen, setBatchToolsOpen] = useState(false);
  const [batchAngleCount, setBatchAngleCount] = useState(10);
  const [batchDuration, setBatchDuration] = useState('60s');
  const [isGeneratingBatch, setIsGeneratingBatch] = useState(false);

  const totalAngles = angles.length;
  const postedAngles = angles.filter(a => a.status === 'posted' || !!a.posted_at).length;
  const progressPercent = totalAngles > 0 ? Math.round((postedAngles / totalAngles) * 100) : 0;
  const activeAngleIdx = openAngleIdx >= 0 && openAngleIdx < angles.length ? openAngleIdx : 0;
  const rerollTargetAngle = rerollModalAngleIdx !== null ? angles[rerollModalAngleIdx] : null;

  const batches = useMemo(() => {
    const set = new Set();
    angles.forEach(a => {
      set.add(a.batch || 1);
    });
    return Array.from(set).sort((a, b) => a - b);
  }, [angles]);

  const displayedAngles = useMemo(() => {
    return angles
      .map((ang, originalIndex) => ({ ...ang, originalIndex }))
      .filter(ang => {
        if (selectedBatch !== 'all' && (ang.batch || 1) !== selectedBatch) return false;
        if (hidePosted && (ang.status === 'posted' || !!ang.posted_at)) return false;
        return true;
      });
  }, [angles, selectedBatch, hidePosted]);

  const handleGenerateBatch = async () => {
    if (!productData?.id) return;
    setIsGeneratingBatch(true);
    try {
      const res = await generateProductBatch(productData.id, {
        angle_count: batchAngleCount,
        duration: batchDuration,
      });
      if (res.success && res.task_id) {
        setShowBatchModal(false);
        showToast(`🚀 เริ่มสร้างสคริปต์ล็อตใหม่ ${batchAngleCount} มุมในเบื้องหลังแล้ว`);
      }
    } catch (err) {
      console.error('Generate batch failed:', err);
      showToast('ไม่สามารถเริ่มเจนสคริปต์ล็อตใหม่ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsGeneratingBatch(false);
    }
  };

  const [selectedVoicePreset, setSelectedVoicePreset] = useState('gemini_fenrir_male_strong');
  const [isStartingBatchAudio, setIsStartingBatchAudio] = useState(false);

  // Active batch audio background task for this product
  const batchAudioTask = useMemo(() => {
    return (activeTasks || []).find(t =>
      t.task_type === 'batch_generate_audio' &&
      t.metadata?.product_id === productData?.id &&
      t.status === 'running'
    );
  }, [activeTasks, productData?.id]);

  // Target angles in current scope (either selected batch or all batches)
  const targetBatchAngles = useMemo(() => {
    return angles.filter(ang => {
      if (selectedBatch !== 'all' && (ang.batch || 1) !== selectedBatch) return false;
      return true;
    });
  }, [angles, selectedBatch]);

  // Exclude completed clips (rendered or posted) from audio pre-generation requirements
  const isAngleCompleted = (ang) => {
    return ang.status === 'rendered' || ang.status === 'posted' || Boolean(ang.posted_at);
  };

  const activeBatchAngles = useMemo(() => {
    return targetBatchAngles.filter(ang => !isAngleCompleted(ang));
  }, [targetBatchAngles]);

  const missingAudioCount = useMemo(() => {
    return activeBatchAngles.filter(ang => {
      const status = getShotListInfoForAngle(ang);
      return !status?.has_shot_list || Boolean(status?.is_edge_tts);
    }).length;
  }, [activeBatchAngles, getShotListInfoForAngle]);

  const readyAudioCount = activeBatchAngles.length - missingAudioCount;

  // Refresh shot list status when batch audio task finishes
  const prevBatchAudioTaskStatusRef = useRef(null);
  useEffect(() => {
    if (prevBatchAudioTaskStatusRef.current === 'running' && !batchAudioTask && productData?.id) {
      getShotListStatus(productData.id).then(res => setShotListStatusMap(res.status || {})).catch(() => {});
    }
    prevBatchAudioTaskStatusRef.current = batchAudioTask ? 'running' : null;
  }, [batchAudioTask, productData?.id]);

  // ── Scene Catalog (Vision AI) State & Handlers ──
  const [sceneCatalogsMap, setSceneCatalogsMap] = useState({});
  const [isScanningScenes, setIsScanningScenes] = useState(false);

  const refreshSceneCatalogs = useCallback(async () => {
    if (!productData?.id) return;
    try {
      const res = await getSceneCatalogs(productData.id);
      if (res?.catalogs) {
        setSceneCatalogsMap(res.catalogs);
      }
    } catch (err) {
      console.warn('Failed to load scene catalogs:', err);
    }
  }, [productData?.id]);

  useEffect(() => {
    refreshSceneCatalogs();
  }, [refreshSceneCatalogs, productData?.id, angles, refreshTrigger]);

  const allAttachedVideos = useMemo(() => {
    const list = [];
    (productData?.default_videos || []).forEach(v => {
      if (v && !list.includes(v)) list.push(v);
    });
    angles.forEach(ang => {
      (ang.selected_videos || []).forEach(v => {
        if (v && !list.includes(v)) list.push(v);
      });
      if (ang.selected_video && !list.includes(ang.selected_video)) {
        list.push(ang.selected_video);
      }
    });
    return list;
  }, [productData?.default_videos, angles]);

  const totalIndexedScenesCount = useMemo(() => {
    let total = 0;
    Object.values(sceneCatalogsMap).forEach(cat => {
      if (cat?.is_indexed) {
        total += cat.scenes_count || 0;
      }
    });
    return total;
  }, [sceneCatalogsMap]);

  const unindexedVideosCount = useMemo(() => {
    return allAttachedVideos.filter(v => !sceneCatalogsMap[v]?.is_indexed).length;
  }, [allAttachedVideos, sceneCatalogsMap]);
  const canRegenerateBatchAudio = activeBatchAngles.length > 0;

  const [inspectingCatalog, setInspectingCatalog] = useState(null);

  const handleOpenSceneCatalog = (videoPath, videoName, catalog) => {
    const fileName = videoName || (videoPath ? videoPath.split(/[/\\]/).pop() : 'วิดีโอ');
    const cat = catalog || (videoPath ? sceneCatalogsMap[videoPath] : null);
    setInspectingCatalog({
      videoPath,
      videoName: fileName,
      catalog: cat
    });
  };

  const handleIndexSceneCatalog = async (videoPath = null, force = false) => {
    if (!productData?.id) return;
    setIsScanningScenes(true);
    try {
      showToast('👁️ สั่งวิเคราะห์แบ่งสารบัญฉากในเบื้องหลังแล้ว ติดตามที่เมนูกิจกรรมได้สดๆ', 'info');
      const res = await indexSceneCatalogs(productData.id, { video_path: videoPath, force });
      if (res?.task_id) {
        pollTasks();
      }
    } catch (err) {
      console.error('Scan scene catalog failed:', err);
      showToast('ไม่สามารถสแกนฉากได้: ' + (err.response?.data?.detail || err.message), 'error');
      setIsScanningScenes(false);
    }
  };

  const handleBatchGenerateAudio = async ({ forceRegenerate = false } = {}) => {
    if (!productData?.id) return;
    setIsStartingBatchAudio(true);
    try {
      const payload = {
        voice_preset: selectedVoicePreset,
        batch_index: selectedBatch !== 'all' ? selectedBatch : null,
        force_regenerate: forceRegenerate,
      };
      const res = await batchGenerateAudio(productData.id, payload);
      if (res.task_id) {
        showToast(`เริ่มเตรียมเสียงพากย์อัตโนมัติ ${res.angle_count ?? activeBatchAngles.length} มุมในเบื้องหลังแล้ว (ข้ามคลิปที่เสร็จ/โพสต์แล้ว)`, 'info');
      }
    } catch (err) {
      console.error('Batch audio generation failed:', err);
      showToast('ไม่สามารถเริ่มเตรียมเสียงพากย์ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsStartingBatchAudio(false);
    }
  };

  // Angles in current batch that already have a project/draft
  const readyDraftCount = useMemo(() => {
    return activeBatchAngles.filter(ang => (ang.status === 'in_production' || ang.status === 'rendered' || ang.status === 'posted') && ang.project_name).length;
  }, [activeBatchAngles]);

  // Angles that have audio ready and are waiting for draft creation
  const readyForDraftAngles = useMemo(() => {
    return activeBatchAngles.filter(ang => {
      if ((ang.status === 'in_production' || ang.status === 'rendered' || ang.status === 'posted') && ang.project_name) return false;
      const status = getShotListInfoForAngle(ang);
      return Boolean(status?.has_shot_list && !status?.is_edge_tts);
    });
  }, [activeBatchAngles, getShotListInfoForAngle]);

  const attachedAngleCount = useMemo(() => angles.filter((ang) => {
    const selected = ang.selected_videos || (ang.selected_video ? [ang.selected_video] : []);
    return selected.length > 0;
  }).length, [angles]);

  const audioReadyAngleCount = useMemo(() => angles.filter((ang) => {
    if (isAngleCompleted(ang)) return true;
    const audioStatus = getShotListInfoForAngle(ang);
    return Boolean(audioStatus?.has_shot_list && !audioStatus?.is_edge_tts);
  }).length, [angles, getShotListInfoForAngle]);

  const sceneReadyAngleCount = useMemo(() => angles.filter((ang) => {
    const selected = ang.selected_videos || (ang.selected_video ? [ang.selected_video] : []);
    return selected.length > 0 && selected.every((videoPath) => sceneCatalogsMap[videoPath]?.is_indexed);
  }).length, [angles, sceneCatalogsMap]);

  const draftAngleCount = useMemo(() => angles.filter((ang) => (
    ['in_production', 'rendered', 'posted'].includes(ang.status) && Boolean(ang.project_name)
  )).length, [angles]);

  const [isStartingBatchDraft, setIsStartingBatchDraft] = useState(false);
  const [draftingAngleId, setDraftingAngleId] = useState(null);

  // Active batch draft background task for this product
  const batchDraftTask = useMemo(() => {
    return (activeTasks || []).find(t =>
      (t.task_type === 'batch_draft' || (t.task_type === 'batch_render' && (t.payload?.is_draft || t.metadata?.is_draft))) &&
      (t.metadata?.product_id === productData?.id || t.payload?.product_id === productData?.id) &&
      t.status === 'running'
    );
  }, [activeTasks, productData?.id]);

  useEffect(() => {
    const batchIsReady = angles.length > 0
      && missingAudioCount === 0
      && unindexedVideosCount === 0
      && !batchAudioTask
      && !batchDraftTask;
    if (batchIsReady) setBatchToolsOpen(false);
  }, [angles.length, missingAudioCount, unindexedVideosCount, batchAudioTask, batchDraftTask]);

  // Auto-refresh product and tracker when batch draft completes
  const prevBatchDraftTaskStatusRef = useRef(null);
  useEffect(() => {
    if (prevBatchDraftTaskStatusRef.current === 'running' && !batchDraftTask && productData?.id) {
      readProducts({ force: true }).then(res => {
        const updated = res.products || [];
        const current = updated.find(p => p.id === productData.id);
        if (current) selectProduct(current);
      }).catch(() => {});
      workspaceData?.invalidateTrackerData?.();
      showToast('🎉 สร้างดราฟต์ไทม์ไลน์เสร็จสมบูรณ์ ทุกมุมพร้อมเปิดทำต่อในไทม์ไลน์แล้ว!', 'success');
    }
    prevBatchDraftTaskStatusRef.current = batchDraftTask ? 'running' : null;
  }, [batchDraftTask, productData?.id]);

  const handleBatchCreateDraft = async () => {
    if (!productData?.id) return;
    if (readyForDraftAngles.length === 0) {
      showToast('ไม่มีมุมมองที่พร้อมสร้างดราฟต์ (ต้องเตรียมเสียงพากย์ก่อน)', 'warning');
      return;
    }
    setIsStartingBatchDraft(true);
    try {
      const angleProjectNames = {};
      readyForDraftAngles.forEach((a, idx) => {
        const aBatch = a.batch || (selectedBatch !== 'all' ? selectedBatch : 1);
        const pName = buildProjectName({
          productName: productData.name,
          angle: a,
          angleIndex: idx,
          existingProjects: [...knownProjects, ...Object.values(angleProjectNames)],
          productCode: productData.product_code || '',
          batch: aBatch,
        });
        angleProjectNames[a.angle_id] = pName;
      });
      const effectiveBatch = selectedBatch !== 'all' ? selectedBatch : null;
      const payload = {
        product_id: productData.id,
        angle_ids: readyForDraftAngles.map(a => a.angle_id),
        voice_preset: selectedVoicePreset,
        angle_project_names: angleProjectNames,
        export_mp4: false,
        batch_index: effectiveBatch,
      };
      const res = await startBatchDraft(payload);
      if (res.batch_id) {
        showToast(`🚀 เริ่มสร้างดราฟต์ไทม์ไลน์ ${res.total_items ?? readyForDraftAngles.length} มุมมองในเบื้องหลังแล้ว (พร้อมเปิดตรวจในไม่กี่วินาที)`, 'info');
      }
    } catch (err) {
      console.error('Batch draft creation failed:', err);
      showToast('ไม่สามารถเริ่มสร้างดราฟต์ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setIsStartingBatchDraft(false);
    }
  };

  const handleSingleAngleQuickDraft = async (angle, index) => {
    if (!productData?.id || !angle?.angle_id) return;
    setDraftingAngleId(angle.angle_id);
    try {
      const angleId = angle.angle_id || angle.id;
      const angleBatch = angle.batch || (selectedBatch !== 'all' ? selectedBatch : 1);
      const recommendedStyle = angleId ? getRecommendedStyleForAngle(angleId) : undefined;
      const angleProjectName = buildProjectName({
        productName: productData.name,
        angle,
        angleIndex: index,
        existingProjects: knownProjects,
        productCode: productData.product_code || '',
        batch: angleBatch,
      });
      const payload = {
        product_id: productData.id,
        angle_ids: [angle.angle_id],
        voice_preset: angle.voice_preset || selectedVoicePreset,
        style_preset: angle.style_preset || recommendedStyle,
        project_name: angleProjectName,
        angle_project_names: { [angle.angle_id]: angleProjectName },
        export_mp4: false,
        batch_index: angleBatch,
      };
      const res = await startBatchDraft(payload);
      let draftProjectName = null;
      if (res.batch_id) {
        let attempts = 0;
        let done = false;
        // Poll for up to 60 seconds (60 * 1000ms)
        while (attempts < 60 && !done) {
          await new Promise(r => setTimeout(r, 1000));
          const statusRes = await getBatchRenderStatus(res.batch_id);
          if (statusRes.status === 'completed' || statusRes.status === 'failed') {
            done = true;
            const completedItem = statusRes.items?.[0];
            if (completedItem?.project_name) {
              draftProjectName = completedItem.project_name;
            }
          }
          attempts++;
        }
      }
      const prodRes = await readProducts({ force: true });
      const updatedList = prodRes.products || [];
      const updatedProd = updatedList.find(p => p.id === productData.id);
      let targetAngle = angle;
      if (updatedProd) {
        selectProduct(updatedProd);
        targetAngle = (updatedProd.angles || []).find(a => a.angle_id === angle.angle_id && (a.batch || 1) === angleBatch) || angle;
        workspaceData?.invalidateTrackerData?.();
      }
      if (draftProjectName) {
        targetAngle = { ...targetAngle, project_name: draftProjectName };
        handleOpenInTimeline(targetAngle, index);
        showToast('🎉 สร้างดราฟต์ไทม์ไลน์เรียบร้อย เปิดเข้าสู่ไทม์ไลน์แล้ว!', 'success');
      } else {
        showToast('⏳ กำลังประกอบดราฟต์ในพื้นหลัง สามารถกดเปิดไทม์ไลน์จากศูนย์กิจกรรมด้านบนเมื่อเสร็จสิ้นได้ครับ', 'info');
      }
    } catch (err) {
      console.error('Quick draft failed:', err);
      showToast('ไม่สามารถสร้างดราฟต์ได้: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setDraftingAngleId(null);
    }
  };

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="space-y-4 relative animate-fadeIn pb-16">
      {/* Central Toast Notification */}
      <Toast message={toastMessage} type={toastType} duration={toastDuration} onClose={hideToast} />

      <PageHeader
        icon={Package}
        eyebrow={productData ? 'สินค้าปัจจุบัน' : 'Step 1 — เลือกสินค้า'}
        titlePrefix={
          productData?.product_code && (
            <span className="px-2 py-0.5 rounded-lg bg-fuchsia-500/20 border border-fuchsia-500/35 text-fuchsia-300 font-bold text-xs sm:text-sm flex-shrink-0">
              {productData.product_code}
            </span>
          )
        }
        title={productData?.title || productData?.name || (historyList.length > 0 ? 'เลือกสินค้าจากการ์ดสินค้า' : 'ยังไม่มีสินค้า — เริ่มวิเคราะห์สินค้าใหม่')}
        titleClassName="text-lg sm:text-xl md:text-2xl font-black text-white tracking-tight"
        secondRow={
          <>
            {/* Product cards: primary product switcher in the header. */}
            {historyList.length > 1 && (
              <div className="pt-2 border-t border-white/[0.06] animate-fadeIn">
                <div className="flex items-stretch gap-2.5 overflow-x-auto pb-1 no-scrollbar snap-x snap-mandatory scroll-smooth pr-4" aria-label="เลือกสินค้า">
                  {filteredHistory.map((p) => (
                    <ProductCard
                      key={p.id}
                      product={p}
                      isSelected={selectedHistoryId === p.id}
                      onSelect={selectProduct}
                      onToggleHide={handleToggleHideProduct}
                    />
                  ))}
                  {filteredHistory.length === 0 && productSearch && (
                    <div className="flex items-center justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-400 gap-2 flex-shrink-0">
                      <Search className="w-4 h-4 text-slate-500" />
                      <span>ไม่พบสินค้าที่ตรงกับ "{productSearch}"</span>
                    </div>
                  )}
                  {filteredHistory.length === 0 && !productSearch && productFilter === 'hidden' && (
                    <div className="flex items-center justify-center p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-400 gap-2 flex-shrink-0">
                      <EyeOff className="w-4 h-4 text-slate-500" />
                      <span>ไม่มีสินค้าที่ถูกซ่อนอยู่</span>
                    </div>
                  )}
                </div>

                {productFilter === 'hidden' && (
                  <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-xs text-amber-200 mt-2">
                    <div className="flex items-center gap-2">
                      <EyeOff className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <span>กำลังแสดงเฉพาะสินค้าที่ซ่อนอยู่ ({filteredHistory.length} รายการ)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleBatchUnhideAll}
                        className="px-2.5 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-[11px] cursor-pointer"
                      >
                        ยกเลิกการซ่อนทั้งหมด
                      </button>
                      <button
                        type="button"
                        onClick={() => setProductFilter('all')}
                        className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/15 text-white font-bold text-[11px] cursor-pointer"
                      >
                        กลับไปดูสินค้าปกติ
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Row 2: daily product controls. Less-used tools stay behind disclosure. */}
            <div className="flex items-center gap-2 flex-wrap justify-between pt-2 border-t border-white/[0.06]">
              {totalAngles > 0 && (
                <div className="flex items-center gap-1.5 sm:gap-2 bg-black/40 px-2.5 py-1.5 rounded-xl border border-white/[0.08] flex-shrink-0">
                  <span className="text-[11px] sm:text-xs text-slate-400 font-medium">คืบหน้า</span>
                  <span className="text-[11px] sm:text-xs text-white font-bold font-mono">{postedAngles}/{totalAngles}</span>
                  <div className="w-12 sm:w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] rounded-full transition-all duration-500" style={{ width: `${progressPercent}%` }} />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 ml-auto">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 text-xs font-bold cursor-pointer shadow-md active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]"
                  title="วิเคราะห์สินค้าใหม่"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>สินค้าใหม่</span>
                </button>
                <button
                  type="button"
                  onClick={() => setProductToolsOpen((open) => !open)}
                  aria-expanded={productToolsOpen}
                  aria-controls="product-secondary-tools"
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/60 ${
                    productToolsOpen
                      ? 'bg-white/[0.1] text-white border-white/[0.18]'
                      : 'bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border-white/[0.08]'
                  }`}
                >
                  <MoreHorizontal className="w-4 h-4" />
                  <span>เครื่องมือสินค้า</span>
                  {hiddenProductsCount > 0 && !productToolsOpen && (
                    <span className="w-2 h-2 rounded-full bg-amber-400" title={`มีสินค้าที่ซ่อนอยู่ ${hiddenProductsCount} รายการ`} />
                  )}
                </button>
              </div>
            </div>

            {productToolsOpen && (
              <div id="product-secondary-tools" className="mt-2 p-2.5 rounded-xl bg-black/30 border border-white/[0.08] flex flex-wrap items-center gap-2 animate-fadeIn">
                <div className="relative flex items-center flex-1 min-w-[190px] max-w-sm">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
                  <input
                    type="text"
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    placeholder="ค้นหาสินค้า..."
                    className="w-full bg-black/40 border border-white/[0.1] focus:border-[#25F4EE] text-slate-200 text-xs pl-8 pr-7 py-1.5 rounded-xl focus:outline-none placeholder-slate-500"
                  />
                  {productSearch && (
                    <button
                      type="button"
                      onClick={() => setProductSearch('')}
                      className="absolute right-2 text-slate-400 hover:text-white cursor-pointer"
                      title="ล้างคำค้นหา"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {productData && (
                  <>
                    <button type="button" onClick={() => setShowMetadataModal(true)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold transition-colors">
                      <Database className="w-3.5 h-3.5 text-[#25F4EE]" /><span>ข้อมูล AI</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setHookHeaderAngleIdx(openAngleIdx >= 0 ? openAngleIdx : 0);
                        setHookHeaderModalOpen(true);
                      }}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold transition-colors"
                    >
                      <Tag className="w-3.5 h-3.5 text-amber-300" /><span>ตั้งค่าป้าย Hook</span>
                    </button>
                  </>
                )}
                {unstartedVisibleProducts.length > 0 && (
                  <button
                    type="button"
                    onClick={handleBatchHideUnstarted}
                    disabled={batchHiding}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/25 text-xs font-bold transition-colors cursor-pointer disabled:opacity-50"
                    title="ซ่อนสินค้าที่ความคืบหน้า 0/10 มุม ออกจากแถบหลัก"
                  >
                    <EyeOff className="w-3.5 h-3.5 text-rose-400" />
                    <span>ซ่อนสินค้าที่ยังไม่ทำ ({unstartedVisibleProducts.length})</span>
                  </button>
                )}
                <button type="button" onClick={() => setShowCatalogModal(true)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold transition-colors">
                  <LayoutGrid className="w-3.5 h-3.5 text-[#25F4EE]" /><span>คลังสินค้า</span>
                </button>
                <button type="button" onClick={loadHistory} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold transition-colors">
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} /><span>รีเฟรชข้อมูล</span>
                </button>
                {(hiddenProductsCount > 0 || productFilter === 'hidden') && (
                  <button
                    type="button"
                    onClick={() => setProductFilter((f) => (f === 'hidden' ? 'all' : 'hidden'))}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-bold transition-colors cursor-pointer ${
                      productFilter === 'hidden'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-slate-200 border-white/[0.08]'
                    }`}
                    title={productFilter === 'hidden' ? 'กลับไปแสดงสินค้าหลัก' : `ดูสินค้าที่ซ่อนไว้ (${hiddenProductsCount})`}
                  >
                    {productFilter === 'hidden' ? <Eye className="w-3.5 h-3.5 text-amber-400" /> : <EyeOff className="w-3.5 h-3.5 text-slate-400" />}
                    <span>{productFilter === 'hidden' ? 'ดูสินค้าหลัก' : `ซ่อนอยู่ (${hiddenProductsCount})`}</span>
                  </button>
                )}
                {productData && (
                  <button type="button" onClick={() => handleDeleteHistory(productData)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/25 text-xs font-bold transition-colors ml-auto">
                    <Trash2 className="w-3.5 h-3.5" /><span>ลบสินค้า</span>
                  </button>
                )}
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
            <section aria-label="สถานะเวิร์กโฟลว์" className="rounded-2xl border border-white/[0.08] bg-[#090D15] overflow-hidden">
              <div className="px-3.5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06]">
                <div>
                  <h2 className="text-sm font-bold text-white">พื้นที่ทำงานสคริปต์</h2>
                  <p className="text-[11px] text-slate-500 mt-0.5">เลือกสคริปต์ทางซ้าย แล้วทำขั้นตอนถัดไปทางขวา</p>
                </div>
                <span className="text-xs text-slate-400">
                  โพสต์แล้ว <strong className="text-emerald-300 font-mono">{postedAngles}/{totalAngles}</strong> คลิป
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 divide-x divide-y xl:divide-y-0 divide-white/[0.06]">
                {[
                  { label: 'บทพร้อม', value: totalAngles, icon: Sparkles },
                  { label: 'คลิปพร้อม', value: attachedAngleCount, icon: Film },
                  { label: 'เสียงพร้อม', value: audioReadyAngleCount, icon: Mic },
                  { label: 'ฉากพร้อม', value: sceneReadyAngleCount, icon: Eye },
                  { label: 'ดราฟต์', value: draftAngleCount, icon: Clapperboard },
                  { label: 'โพสต์แล้ว', value: postedAngles, icon: CheckCircle2 },
                ].map((step) => {
                  const StepIcon = step.icon;
                  const complete = totalAngles > 0 && step.value >= totalAngles;
                  return (
                    <div key={step.label} className="px-3 py-2.5 flex items-center gap-2 min-w-0">
                      <span className={`w-7 h-7 rounded-lg flex items-center justify-center border ${
                        complete
                          ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300'
                          : 'bg-white/[0.03] border-white/[0.08] text-slate-500'
                      }`}>
                        <StepIcon className="w-3.5 h-3.5" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-[10px] text-slate-500 truncate">{step.label}</p>
                        <p className={`text-xs font-bold font-mono ${complete ? 'text-emerald-300' : 'text-slate-200'}`}>
                          {step.value}/{totalAngles}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-2xl border border-white/[0.08] bg-[#080B11] p-2.5 sm:p-3 space-y-2.5">
              <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-2.5">
                <div className="flex items-center gap-1 overflow-x-auto no-scrollbar pb-0.5">
                  <button
                    type="button"
                    onClick={() => setSelectedBatch('all')}
                    className={`px-2.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap border ${selectedBatch === 'all' ? 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30' : 'text-slate-400 border-transparent hover:text-white'}`}
                  >
                    ทุกล็อต ({angles.length})
                  </button>
                  {batches.map((batch) => {
                    const batchCount = angles.filter((angle) => (angle.batch || 1) === batch).length;
                    return (
                      <button
                        key={batch}
                        type="button"
                        onClick={() => setSelectedBatch(batch)}
                        className={`px-2.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap border ${selectedBatch === batch ? 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30' : 'text-slate-400 border-transparent hover:text-white'}`}
                      >
                        ล็อต {batch} ({batchCount})
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-2 flex-wrap">

                  {batchAudioTask || batchDraftTask ? (
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-200 border border-cyan-500/25 text-xs font-bold">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{batchAudioTask?.step || batchDraftTask?.step || 'กำลังประมวลผล...'}</span>
                    </div>
                  ) : missingAudioCount > 0 ? (
                    <button type="button" onClick={handleBatchGenerateAudio} disabled={isStartingBatchAudio} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 text-xs font-bold disabled:opacity-50">
                      {isStartingBatchAudio ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Volume2 className="w-3.5 h-3.5" />}
                      <span>เตรียมเสียง ({missingAudioCount})</span>
                    </button>
                  ) : unindexedVideosCount > 0 ? (
                    <button type="button" onClick={() => handleIndexSceneCatalog()} disabled={isScanningScenes} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 text-xs font-bold disabled:opacity-50">
                      {isScanningScenes ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                      <span>สแกนฉาก ({unindexedVideosCount})</span>
                    </button>
                  ) : readyForDraftAngles.length > 0 ? (
                    <button type="button" onClick={handleBatchCreateDraft} disabled={isStartingBatchDraft} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#25F4EE] hover:bg-[#4ff8f2] text-slate-950 text-xs font-bold disabled:opacity-50">
                      {isStartingBatchDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                      <span>สร้างดราฟต์ทุกมุม ({readyForDraftAngles.length})</span>
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 text-xs font-bold">
                      <Check className="w-3.5 h-3.5" /> พร้อมครบ
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={() => setBatchToolsOpen((open) => !open)}
                    aria-expanded={batchToolsOpen}
                    aria-controls="batch-secondary-tools"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"
                  >
                    <MoreHorizontal className="w-4 h-4" />
                    <span>จัดการล็อต</span>
                    {batchToolsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {batchToolsOpen && (
                <div id="batch-secondary-tools" className="pt-2.5 border-t border-white/[0.06] grid gap-3 xl:grid-cols-[auto_1fr] animate-fadeIn">
                  <div className="flex items-center gap-1 bg-black/30 p-1 rounded-lg border border-white/[0.06] w-fit h-fit">
                    <button type="button" onClick={() => setViewMode('split')} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold ${viewMode === 'split' ? 'bg-white/[0.1] text-white' : 'text-slate-400'}`}>
                      <Columns className="w-3.5 h-3.5" /> สตูดิโอ
                    </button>
                    <button type="button" onClick={() => setViewMode('accordion')} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold ${viewMode === 'accordion' ? 'bg-white/[0.1] text-white' : 'text-slate-400'}`}>
                      <List className="w-3.5 h-3.5" /> แถวยาว
                    </button>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {!batchAudioTask && !batchDraftTask && activeBatchAngles.length > 0 && (
                      <label className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-cyan-500/[0.06] border border-cyan-500/20">
                        <Mic className="w-3.5 h-3.5 shrink-0 text-[#25F4EE]" aria-hidden="true" />
                        <span className="text-[10px] font-semibold text-slate-400 whitespace-nowrap">เสียง</span>
                        <select
                          value={selectedVoicePreset}
                          onChange={(event) => setSelectedVoicePreset(event.target.value)}
                          disabled={isStartingBatchAudio}
                          aria-label="เสียงที่จะใช้ก่อนเตรียมเสียง"
                          title="เลือกเสียงสำหรับเตรียมเสียงหรือเจนเสียงใหม่ทั้งสคริปต์"
                          className="w-[190px] max-w-full bg-black/40 border border-white/[0.1] rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-[#25F4EE] disabled:opacity-50"
                        >
                          {GEMINI_VOICE_OPTIONS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
                        </select>
                      </label>
                    )}
                    {!batchAudioTask && !batchDraftTask && missingAudioCount === 0 && canRegenerateBatchAudio && (
                      <button
                        type="button"
                        onClick={() => handleBatchGenerateAudio({ forceRegenerate: true })}
                        disabled={isStartingBatchAudio}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-200 border border-indigo-400/25 text-xs font-bold disabled:opacity-50"
                        title="สร้างเสียงพากย์ใหม่ให้ทุกสคริปต์ที่ยังไม่ตัดต่อเสร็จ โดยใช้เสียงที่เลือกไว้"
                      >
                        {isStartingBatchAudio ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                        <span>เจนเสียงใหม่ทั้งสคริปต์ ({activeBatchAngles.length})</span>
                      </button>
                    )}
                    <button type="button" onClick={() => { setFindReplaceAngleIdx(activeAngleIdx); setFindReplaceOpen(true); }} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"><Replace className="w-3.5 h-3.5" /> แทนที่คำ</button>
                    <button type="button" onClick={() => handleOpenMediaPicker(-1)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"><FolderOpen className="w-3.5 h-3.5" /> คลิปให้ทุกมุม</button>
                    <button type="button" onClick={() => setBatchRenderOpen(true)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"><Zap className="w-3.5 h-3.5" /> เรนเดอร์หลายมุม</button>
                    <button type="button" onClick={() => setFilmingRecipeModalOpen(true)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"><Clapperboard className="w-3.5 h-3.5" /> สูตรถ่ายทำ</button>
                    <button type="button" onClick={() => setShowBatchModal(true)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold"><Plus className="w-3.5 h-3.5" /> เจนล็อตใหม่</button>
                    {postedAngles > 0 && (
                      <button type="button" onClick={() => setHidePosted(!hidePosted)} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.08] text-xs font-bold">
                        {hidePosted ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />} {hidePosted ? 'แสดงที่โพสต์แล้ว' : `ซ่อนที่โพสต์แล้ว (${postedAngles})`}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </section>

            <div className="hidden flex-col sm:flex-row sm:items-center justify-between gap-2.5 px-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#FE2C55]" />
                  <span>Step 2 — เลือกมุมขาย & คลิปประกอบ ({totalAngles} สคริปต์{batches.length > 1 ? ` • ${batches.length} ล็อต` : ''})</span>
                </h2>
                <span className="text-xs text-slate-600 hidden sm:inline">•</span>
                <span className="text-xs font-semibold text-slate-400">
                  โพสต์แล้ว <strong className="text-emerald-400 font-mono">{postedAngles}</strong>/{totalAngles} คลิป
                </span>
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

                <button
                  type="button"
                  onClick={() => setBatchRenderOpen(true)}
                  className="px-2.5 py-1 rounded-xl bg-gradient-to-r from-cyan-500/20 to-emerald-500/20 hover:from-cyan-500/30 hover:to-emerald-500/30 border border-cyan-500/40 text-xs font-bold text-cyan-200 cursor-pointer flex items-center gap-1.5 transition-all shadow-sm"
                  title="เปิดหน้าต่างเรนเดอร์หลายมุมมองพร้อมกันในคิวเบื้องหลัง"
                >
                  <Zap className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="hidden xs:inline sm:inline">เรนเดอร์หลายมุม</span>
                </button>
              </div>
            </div>

            {/* ── Sub-bar: Batch Selector & Filters & Actions ── */}
            <div className="hidden flex-wrap items-center justify-between gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <div className="flex items-center gap-1.5 flex-wrap">
                {/* Batch Selector Pills */}
                <div className="flex items-center gap-1 bg-black/30 p-1 rounded-xl border border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => setSelectedBatch('all')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      selectedBatch === 'all'
                        ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30'
                        : 'text-slate-400 hover:text-white border border-transparent'
                    }`}
                  >
                    ทุกล็อต ({angles.length})
                  </button>
                  {batches.map((b) => {
                    const bCount = angles.filter(a => (a.batch || 1) === b).length;
                    return (
                      <button
                        key={b}
                        type="button"
                        onClick={() => setSelectedBatch(b)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                          selectedBatch === b
                            ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30'
                            : 'text-slate-400 hover:text-white border border-transparent'
                        }`}
                      >
                        ล็อต {b} ({bCount})
                      </button>
                    );
                  })}
                </div>

                {/* Quick Filter: Hide Posted */}
                {postedAngles > 0 && (
                  <button
                    type="button"
                    onClick={() => setHidePosted(!hidePosted)}
                    className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                      hidePosted
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        : 'bg-white/[0.04] text-slate-400 border-white/[0.08] hover:text-white'
                    }`}
                    title={hidePosted ? 'กำลังซ่อนคลิปที่โพสต์แล้ว แตะเพื่อแสดงทั้งหมด' : 'แตะเพื่อซ่อนคลิปที่โพสต์แล้ว'}
                  >
                    {hidePosted ? <EyeOff className="w-3 h-3 text-amber-400" /> : <Eye className="w-3 h-3" />}
                    <span>ซ่อนที่โพสต์แล้ว ({postedAngles})</span>
                  </button>
                )}
              </div>

              {/* Action Button: Generate New Batch with AI */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowBatchModal(true)}
                  className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#FE2C55]/20 to-[#25F4EE]/20 hover:from-[#FE2C55]/30 hover:to-[#25F4EE]/30 border border-[#25F4EE]/40 text-xs font-bold text-[#25F4EE] cursor-pointer flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
                  title="ให้ AI ศึกษาประวัติมุมเดิม แล้วคิดมุมขายใหม่เพิ่มอีก 4-10 มุมโดยไม่ซ้ำเดิม"
                >
                  <Sparkles className="w-3.5 h-3.5 text-[#FE2C55]" />
                  <span>เจนล็อตใหม่</span>
                </button>
              </div>
            </div>

            {/* ── Batch Audio Preparation Bar (Batch Gemini TTS Pre-generation) ── */}
            {angles.length > 0 && (
              <div className="hidden p-2.5 sm:p-3 rounded-xl bg-gradient-to-r from-[#0f172a]/95 via-[#1e1b4b]/60 to-[#0f172a]/95 border border-indigo-500/25 shadow-lg backdrop-blur-md flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-200">
                    <Mic className="w-4 h-4 text-indigo-400" />
                    <span>เสียงพากย์อัตโนมัติ:</span>
                  </div>

                  {/* Voice Preset Dropdown */}
                  <div className="relative">
                    <select
                      value={selectedVoicePreset}
                      onChange={(e) => setSelectedVoicePreset(e.target.value)}
                      disabled={!!batchAudioTask || isStartingBatchAudio}
                      className="bg-slate-900/90 hover:bg-slate-900 border border-indigo-400/30 hover:border-indigo-400/60 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-400 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                      title="เลือกเสียง Gemini TTS สำหรับเตรียมเสียงทุกมุม"
                    >
                      {GEMINI_VOICE_OPTIONS.map((opt) => (
                        <option key={opt.id} value={opt.id} className="bg-slate-900 text-slate-200">
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Status indicator pill */}
                  <div className="flex items-center gap-1.5 text-[11px] flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full font-semibold border ${
                      activeBatchAngles.length === 0
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        : missingAudioCount === 0
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    }`}>
                      {activeBatchAngles.length === 0
                        ? 'ตัดเสร็จ/โพสต์ครบทุกมุมแล้ว'
                        : missingAudioCount === 0
                          ? `เสียงพร้อมครบ ${readyAudioCount}/${activeBatchAngles.length} มุม`
                          : `เสียงพร้อมแล้ว ${readyAudioCount}/${activeBatchAngles.length} มุม (ขาด ${missingAudioCount})`
                      }
                    </span>
                    {readyDraftCount > 0 && (
                      <span className={`px-2 py-0.5 rounded-full font-semibold border ${
                        readyDraftCount === activeBatchAngles.length
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                          : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                      }`}>
                        ดราฟต์ไทม์ไลน์ {readyDraftCount}/${activeBatchAngles.length} มุม
                      </span>
                    )}
                    {allAttachedVideos.length > 0 && (
                      totalIndexedScenesCount > 0 ? (
                        <button
                          type="button"
                          onClick={() => {
                            const firstIndexed = allAttachedVideos.find(v => sceneCatalogsMap[v]?.is_indexed);
                            if (firstIndexed) {
                              handleOpenSceneCatalog(firstIndexed, firstIndexed.split(/[/\\]/).pop(), sceneCatalogsMap[firstIndexed]);
                            }
                          }}
                          className="px-2 py-0.5 rounded-full font-semibold border bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border-emerald-500/30 flex items-center gap-1 cursor-pointer transition-all active:scale-95 shadow-xs"
                          title={`สแกนสารบัญฉาก Vision AI แล้ว ${totalIndexedScenesCount} ฉาก (คลิกเพื่อดูสารบัญฉาก)`}
                        >
                          <Sparkles className="w-3 h-3 text-emerald-400" />
                          <span>สารบัญฉากพร้อม ({totalIndexedScenesCount} ฉาก)</span>
                          <Eye className="w-3 h-3 text-emerald-400 ml-0.5" />
                        </button>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full font-semibold border bg-amber-500/15 text-amber-300 border-amber-500/30 flex items-center gap-1" title="ยังไม่ได้สแกนสารบัญฉากด้วย Vision AI">
                          <span>⚠️ ยังไม่ได้สแกนฉาก</span>
                        </span>
                      )
                    )}
                  </div>
                </div>

                {/* Action / Progress Area */}
                <div className="flex items-center gap-2 flex-wrap">
                  {batchAudioTask ? (
                    <div className="flex items-center gap-2.5 bg-indigo-950/60 px-3 py-1.5 rounded-lg border border-indigo-500/30">
                      <Loader2 className="w-4 h-4 text-indigo-400 animate-spin flex-shrink-0" />
                      <div className="flex flex-col">
                        <span className="text-xs text-indigo-200 font-medium leading-tight max-w-[240px] sm:max-w-xs truncate" title={batchAudioTask.step}>
                          {batchAudioTask.step || 'กำลังเตรียมเสียงพากย์...'}
                        </span>
                        {typeof batchAudioTask.progress === 'number' && (
                          <div className="w-full bg-slate-800 rounded-full h-1 mt-1 overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-1 transition-all duration-300"
                              style={{ width: `${Math.max(5, batchAudioTask.progress)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleBatchGenerateAudio}
                      disabled={isStartingBatchAudio || isStartingBatchDraft || Boolean(batchDraftTask) || activeBatchAngles.length === 0}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95 ${
                        activeBatchAngles.length === 0
                          ? 'bg-white/[0.04] text-slate-500 border border-white/[0.06]'
                          : missingAudioCount > 0
                            ? 'bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white border border-indigo-400/40 hover:shadow-indigo-500/20'
                            : 'bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 border border-white/[0.1]'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                      title={activeBatchAngles.length === 0
                        ? 'ทุกมุมในล็อตนี้ตัดเสร็จหรือโพสต์แล้ว ไม่จำเป็นต้องสร้างเสียงใหม่'
                        : missingAudioCount > 0
                          ? `สร้างเสียงพากย์อัตโนมัติสำหรับ ${missingAudioCount} มุมที่ยังไม่มี (ข้ามคลิปที่เสร็จ/โพสต์แล้ว & พักรอ Rate Limit 429 ให้อัตโนมัติ)`
                          : 'ทุกมุมที่รอดำเนินการมีเสียงพากย์แล้ว แตะหากต้องการสร้างเสียงใหม่'}
                    >
                      {isStartingBatchAudio ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                          <span>กำลังเริ่มเตรียมเสียง...</span>
                        </>
                      ) : (
                        <>
                          <Volume2 className="w-3.5 h-3.5 text-cyan-300" />
                          <span>
                            {activeBatchAngles.length === 0
                              ? 'ตัดเสร็จครบแล้ว'
                              : missingAudioCount > 0
                                ? `เตรียมเสียงพากย์ (${missingAudioCount} มุม)`
                                : `เตรียมเสียงใหม่ (${activeBatchAngles.length} มุม)`
                            }
                          </span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Batch Draft Task Progress or Trigger Button */}
                  {batchDraftTask ? (
                    <div className="flex items-center gap-2.5 bg-emerald-950/60 px-3 py-1.5 rounded-lg border border-emerald-500/30">
                      <Loader2 className="w-4 h-4 text-emerald-400 animate-spin flex-shrink-0" />
                      <div className="flex flex-col">
                        <span className="text-xs text-emerald-200 font-medium leading-tight max-w-[240px] sm:max-w-xs truncate" title={batchDraftTask.step}>
                          {batchDraftTask.step || 'กำลังสร้างดราฟต์ไทม์ไลน์...'}
                        </span>
                        {typeof batchDraftTask.progress === 'number' && (
                          <div className="w-full bg-slate-800 rounded-full h-1 mt-1 overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-emerald-500 to-teal-400 h-1 transition-all duration-300"
                              style={{ width: `${Math.max(5, batchDraftTask.progress)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ) : readyForDraftAngles.length > 0 ? (
                    <button
                      type="button"
                      onClick={handleBatchCreateDraft}
                      disabled={isStartingBatchDraft || isStartingBatchAudio || Boolean(batchAudioTask)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border border-emerald-400/40 hover:shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                      title={`สร้างโปรเจกต์ดราฟต์ไทม์ไลน์สำหรับ ${readyForDraftAngles.length} มุมมองที่เตรียมเสียงแล้ว (ไม่เรนเดอร์ MP4 เสร็จในไม่กี่วินาที พร้อมเปิดตรวจปกและคัตติ้ง)`}
                    >
                      {isStartingBatchDraft ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                          <span>กำลังเริ่มสร้างดราฟต์...</span>
                        </>
                      ) : (
                        <>
                          <Film className="w-3.5 h-3.5 text-emerald-200" />
                          <span>สร้างดราฟต์ทุกมุม ({readyForDraftAngles.length} มุม)</span>
                        </>
                      )}
                    </button>
                  ) : readyDraftCount > 0 && readyDraftCount === activeBatchAngles.length ? (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span>ดราฟต์ไทม์ไลน์พร้อมครบทุกมุม</span>
                    </span>
                  ) : null}

                  {/* Scan Scene Catalog Button */}
                  {allAttachedVideos.length > 0 && (
                    <button
                      type="button"
                      onClick={() => handleIndexSceneCatalog()}
                      disabled={isScanningScenes}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95 ${
                        unindexedVideosCount > 0
                          ? 'bg-gradient-to-r from-amber-500/25 to-emerald-500/25 hover:from-amber-500/35 hover:to-emerald-500/35 text-emerald-300 border border-emerald-500/50'
                          : 'bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 border border-white/[0.1]'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                      title={unindexedVideosCount > 0
                        ? `ให้ Vision AI ดูคลิปดิบ 1 ครั้งเพื่อทำสารบัญฉาก (${unindexedVideosCount} คลิป) แล้วนำไปจับคู่กับทุกสคริปต์โดยไม่ต้องดูซ้ำ`
                        : `สแกนซ้ำเพื่ออัปเดตสารบัญฉากใหม่`}
                    >
                      {isScanningScenes ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                          <span>กำลังสแกนสารบัญฉาก...</span>
                        </>
                      ) : (
                        <>
                          <Eye className="w-3.5 h-3.5 text-emerald-400" />
                          <span>
                            {unindexedVideosCount > 0
                              ? `สแกนสารบัญฉาก Vision AI (${unindexedVideosCount} คลิป)`
                              : `สแกนสารบัญฉากซ้ำ`}
                          </span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Universal Filming Recipe Button */}
                  <button
                    type="button"
                    onClick={() => setFilmingRecipeModalOpen(true)}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95 bg-gradient-to-r from-rose-500/20 to-purple-500/20 hover:from-rose-500/30 hover:to-purple-500/30 text-rose-300 border border-rose-500/40 hover:border-rose-400"
                    title="เปิดดูสูตรถ่ายทำ 5 ช็อตมาตรฐานสำหรับสินค้านี้ (Hook, 360°, Macro, Action, CTA) พร้อม QR สแกนขึ้นมือถือ"
                  >
                    <Clapperboard className="w-3.5 h-3.5 text-rose-400" />
                    <span>สูตรถ่ายทำ 5 ช็อต</span>
                  </button>
                </div>
              </div>
            )}

            {/* Master-Detail Split View (Default Studio Mode) */}
            {viewMode === 'split' ? (
              <div className="space-y-3 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-4 items-start">
                {/* MOBILE (< lg): compact script list; selected item opens one detail panel below */}
                <div className="lg:hidden space-y-1.5">
                  <div className="flex items-center justify-between px-1">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      เลือกสคริปต์ ({displayedAngles.length}/{angles.length} มุม)
                    </span>
                    <span className="text-[11px] font-mono text-[#25F4EE] font-bold">
                      มุมที่ {activeAngleIdx + 1}/{angles.length}
                    </span>
                  </div>
                  {displayedAngles.length === 0 ? (
                    <div className="p-4 text-center rounded-xl bg-white/[0.02] border border-white/[0.06] text-slate-400 text-xs space-y-1">
                      <p>ไม่มีสคริปต์ที่ตรงกับตัวกรองปัจจุบัน</p>
                      {hidePosted && (
                        <button
                          type="button"
                          onClick={() => setHidePosted(false)}
                          className="text-[#25F4EE] underline text-xs cursor-pointer"
                        >
                          แสดงคลิปที่โพสต์แล้ว
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="grid gap-1.5 max-h-56 overflow-y-auto pr-1 no-scrollbar">
                      {displayedAngles.map((ang) => (
                        <AngleMobilePill
                          key={`${ang.angle_id || ang.id || 'ang'}_b${ang.batch || 1}_${ang.originalIndex}`}
                          angle={ang}
                          index={ang.originalIndex}
                          isSelected={activeAngleIdx === ang.originalIndex}
                          onSelect={() => setOpenAngleIdx(ang.originalIndex)}
                          shotListInfo={getShotListInfoForAngle(ang)}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* DESKTOP (lg+): compact navigation list (4 cols) */}
                <div className="hidden lg:block lg:col-span-4 space-y-2 lg:max-h-[calc(100vh-210px)] lg:overflow-y-auto pr-1 no-scrollbar">
                  {displayedAngles.length === 0 ? (
                    <div className="p-6 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] text-slate-400 text-xs space-y-2">
                      <p>ไม่มีสคริปต์ที่ตรงกับตัวกรองปัจจุบัน</p>
                      {hidePosted && (
                        <button
                          type="button"
                          onClick={() => setHidePosted(false)}
                          className="text-[#25F4EE] underline cursor-pointer"
                        >
                          แสดงคลิปที่โพสต์แล้ว
                        </button>
                      )}
                    </div>
                  ) : (
                    displayedAngles.map((ang) => (
                      <AngleSidebarItem
                        key={`${ang.angle_id || ang.id || 'ang'}_b${ang.batch || 1}_${ang.originalIndex}`}
                        angle={ang}
                        index={ang.originalIndex}
                        isSelected={activeAngleIdx === ang.originalIndex}
                        onSelect={() => setOpenAngleIdx(ang.originalIndex)}
                        onPreviewExportVideo={(a) => setPreviewExportAngle(a)}
                        shotListInfo={getShotListInfoForAngle(ang)}
                        onGenerateShotList={handleGenerateShotList}
                        onOpenShotList={handleGenerateShotList}
                        isGeneratingShotList={generatingShotListIdx === ang.originalIndex}
                        onDeleteAngle={handleDeleteAngleClick}
                        projectName={buildProjectName({
                          productName: productData?.name || '',
                          angle: ang,
                          angleIndex: ang.originalIndex,
                          existingProjects: knownProjects,
                          productCode: productData?.product_code || '',
                          batch: ang.batch,
                        })}
                      />
                    ))
                  )}
                </div>

                {/* Right Column (Active Workbench / 7 cols sticky) */}
                <div className="lg:col-span-8 lg:sticky lg:top-4">
                  {angles[activeAngleIdx] ? (
                    <AngleActiveWorkbench
                      angle={angles[activeAngleIdx]}
                      index={activeAngleIdx}
                      onCopy={copyScriptText}
                      onSendToStudio={handleSendToStudio}
                      onOpenInTimeline={handleOpenInTimeline}
                      onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                      onCloneAngle={handleCloneAngle}
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
                      onOpenHookVariants={(ang) => setHookModalAngle(ang)}
                      onRerollScript={handleOpenRerollScriptModal}
                      onGenerateShotList={handleGenerateShotList}
                      isGeneratingShotList={generatingShotListIdx === activeAngleIdx}
                      productData={productData}
                      onOpenEditHookHeader={(idx) => {
                        setHookHeaderAngleIdx(idx);
                        setHookHeaderModalOpen(true);
                      }}
                      shotListInfo={getShotListInfoForAngle(angles[activeAngleIdx])}
                      onDeleteAngle={handleDeleteAngleClick}
                      onQuickDraft={handleSingleAngleQuickDraft}
                      draftingAngleId={draftingAngleId}
                      sceneCatalogsMap={sceneCatalogsMap}
                      onIndexSceneCatalog={handleIndexSceneCatalog}
                      isScanningScenes={isScanningScenes}
                      onOpenSceneCatalog={handleOpenSceneCatalog}
                      onOpenStoryboard={handleOpenStoryboard}
                      projectName={buildProjectName({
                        productName: productData?.name || '',
                        angle: angles[activeAngleIdx],
                        angleIndex: activeAngleIdx,
                        existingProjects: knownProjects,
                        productCode: productData?.product_code || '',
                        batch: angles[activeAngleIdx]?.batch,
                      })}
                    />
                  ) : displayedAngles[0] ? (
                    <AngleActiveWorkbench
                      angle={angles[displayedAngles[0].originalIndex]}
                      index={displayedAngles[0].originalIndex}
                      onCopy={copyScriptText}
                      onSendToStudio={handleSendToStudio}
                      onOpenInTimeline={handleOpenInTimeline}
                      onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                      onCloneAngle={handleCloneAngle}
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
                      onOpenHookVariants={(ang) => setHookModalAngle(ang)}
                      onRerollScript={handleOpenRerollScriptModal}
                      onGenerateShotList={handleGenerateShotList}
                      isGeneratingShotList={generatingShotListIdx === displayedAngles[0].originalIndex}
                      productData={productData}
                      onOpenEditHookHeader={(idx) => {
                        setHookHeaderAngleIdx(idx);
                        setHookHeaderModalOpen(true);
                      }}
                      shotListInfo={getShotListInfoForAngle(angles[displayedAngles[0]?.originalIndex])}
                      onDeleteAngle={handleDeleteAngleClick}
                      onQuickDraft={handleSingleAngleQuickDraft}
                      draftingAngleId={draftingAngleId}
                      sceneCatalogsMap={sceneCatalogsMap}
                      onIndexSceneCatalog={handleIndexSceneCatalog}
                      isScanningScenes={isScanningScenes}
                      onOpenSceneCatalog={handleOpenSceneCatalog}
                      onOpenStoryboard={handleOpenStoryboard}
                      projectName={buildProjectName({
                        productName: productData?.name || '',
                        angle: angles[displayedAngles[0]?.originalIndex],
                        angleIndex: displayedAngles[0]?.originalIndex ?? 0,
                        existingProjects: knownProjects,
                        productCode: productData?.product_code || '',
                        batch: angles[displayedAngles[0]?.originalIndex]?.batch,
                      })}
                    />
                  ) : null}
                </div>
              </div>
            ) : (
              /* Classic Accordion View */
              <div className="space-y-1.5">
                {displayedAngles.length === 0 ? (
                  <div className="p-6 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] text-slate-400 text-xs space-y-2">
                    <p>ไม่มีสคริปต์ที่ตรงกับตัวกรองปัจจุบัน</p>
                    {hidePosted && (
                      <button
                        type="button"
                        onClick={() => setHidePosted(false)}
                        className="text-[#25F4EE] underline cursor-pointer"
                      >
                        แสดงคลิปที่โพสต์แล้ว
                      </button>
                    )}
                  </div>
                ) : (
                  displayedAngles.map((ang) => (
                    <ScriptAccordionItem
                      key={`${ang.angle_id || ang.id || 'ang'}_b${ang.batch || 1}_${ang.originalIndex}`}
                      angle={ang}
                      index={ang.originalIndex}
                      isOpen={openAngleIdx === ang.originalIndex}
                      onToggle={() => setOpenAngleIdx(openAngleIdx === ang.originalIndex ? -1 : ang.originalIndex)}
                      onCopy={copyScriptText}
                      onSendToStudio={handleSendToStudio}
                      onOpenInTimeline={handleOpenInTimeline}
                      onPreviewExportVideo={(ang) => setPreviewExportAngle(ang)}
                      onCloneAngle={handleCloneAngle}
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
                      onOpenHookVariants={(ang) => setHookModalAngle(ang)}
                      onRerollScript={handleOpenRerollScriptModal}
                      onGenerateShotList={handleGenerateShotList}
                      isGeneratingShotList={generatingShotListIdx === ang.originalIndex}
                      productData={productData}
                      onOpenEditHookHeader={(idx) => {
                        setHookHeaderAngleIdx(idx);
                        setHookHeaderModalOpen(true);
                      }}
                      shotListInfo={getShotListInfoForAngle(ang)}
                      onQuickDraft={handleSingleAngleQuickDraft}
                      draftingAngleId={draftingAngleId}
                      sceneCatalogsMap={sceneCatalogsMap}
                      onIndexSceneCatalog={handleIndexSceneCatalog}
                      isScanningScenes={isScanningScenes}
                      onOpenSceneCatalog={handleOpenSceneCatalog}
                      onOpenStoryboard={handleOpenStoryboard}
                    />
                  ))
                )}
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
            <h3 className="text-lg font-bold text-white">เริ่มต้นสร้างคลิปขายจากสินค้าได้เลย!</h3>
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

      {/* ── Hook Header Modal ── */}
      <HookHeaderModal
        isOpen={hookHeaderModalOpen}
        onClose={() => setHookHeaderModalOpen(false)}
        product={productData}
        angles={angles}
        currentAngleIndex={hookHeaderAngleIdx}
        onSaveHookHeader={handleSaveHookHeader}
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
        onClose={() => { setShotListAngleIdx(null); setShotListResult(null); setShotListError(null); }}
        productId={productData?.id}
        mobileBaseUrl={mobileBaseUrl}
        result={shotListResult}
        onRegenerate={handleRegenerateShotList}
        regenerating={shotListAngleIdx !== null && generatingShotListIdx === shotListAngleIdx}
        error={shotListError}
        onOpenStoryboard={handleOpenStoryboard}
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
                { id: 'all', label: `ทั้งหมด (${activeProductsCount})` },
                { id: 'in_progress', label: `กำลังทำ` },
                { id: 'completed', label: `เสร็จแล้ว` },
                ...(hiddenProductsCount > 0 ? [{ id: 'hidden', label: `ซ่อนอยู่ (${hiddenProductsCount})` }] : []),
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
                        <button
                          type="button"
                          onClick={(e) => handleToggleHideProduct(p, e)}
                          className={`absolute top-1.5 left-1.5 p-1 rounded-lg backdrop-blur-md border transition-all cursor-pointer z-10 ${
                            p.is_hidden
                              ? 'bg-amber-500/80 border-amber-400 text-slate-950 opacity-100'
                              : 'bg-black/60 hover:bg-rose-500/80 border-white/20 hover:border-rose-400 text-slate-300 hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100'
                          }`}
                          title={p.is_hidden ? 'ยกเลิกการซ่อนสินค้านี้' : 'ซ่อนสินค้านี้'}
                          aria-label={p.is_hidden ? 'ยกเลิกการซ่อนสินค้านี้' : 'ซ่อนสินค้านี้'}
                        >
                          {p.is_hidden ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                        </button>
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
              {Boolean(previewExportAngle?.status === 'posted' || previewExportAngle?.posted_at) ? (
                <button
                  type="button"
                  onClick={() => {
                    const ang = previewExportAngle;
                    setPreviewExportAngle(null);
                    handleCloneAngle(ang, openAngleIdx >= 0 ? openAngleIdx : 0);
                  }}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.08] hover:bg-white/[0.14] border border-white/[0.12] text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer shadow-md active:scale-95 transition-all"
                  title="คัดลอกสคริปต์นี้เพื่อตัดต่อใหม่"
                >
                  <CopyPlus className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>ทำซ้ำเพื่อตัดคลิปใหม่</span>
                </button>
              ) : (
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
              )}
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
        description={
          deleteTargetProduct?.angles?.some((a) => a.status === 'posted' || a.posted_at)
            ? "⚠️ สินค้านี้มีมุมหรือสคริปต์ที่บันทึกว่าโพสต์แล้ว การลบถาวรจะบังคับล้างข้อมูลสินค้า สเปก และประวัติทั้งหมดออกจากระบบ"
            : "ข้อมูลสินค้า สเปก และสคริปต์มุมมองขายทั้งหมดจะถูกลบออกจากระบบ"
        }
        itemName={deleteTargetProduct?.title || deleteTargetProduct?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบข้อมูลถาวร"
        loading={isDeletingProduct}
        variant="danger"
      />

      {/* ── Delete Angle Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!deleteTargetAngle}
        onClose={() => setDeleteTargetAngle(null)}
        onConfirm={confirmDeleteAngle}
        title="ลบสคริปต์มุมนี้ถาวร?"
        description="สคริปต์ บทพูด แผนถ่ายทำ และการตั้งค่าของมุมนี้จะถูกลบออกจากระบบ"
        itemName={deleteTargetAngle?.angle?.angle_name || deleteTargetAngle?.angle?.hook_title}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ลบสคริปต์นี้"
        loading={isDeletingAngle}
        variant="danger"
      />

      {/* ── Shot List Modal (แผนถ่ายทำตามสคริปต์) ── */}
      <ShotListModal
        isOpen={shotListAngleIdx !== null && !!shotListResult}
        onClose={() => {
          setShotListAngleIdx(null);
          setShotListResult(null);
          setShotListError(null);
        }}
        productId={productData?.id}
        mobileBaseUrl={mobileBaseUrl}
        result={shotListResult}
        onRegenerate={handleRegenerateShotList}
        regenerating={generatingShotListIdx !== null}
        error={shotListError}
        onOpenStoryboard={handleOpenStoryboard}
      />

      {/* ── Manual Storyboard Mapper Modal (กำหนดช็อตด้วยตนเองรายวรรค) ── */}
      <ManualStoryboardModal
        isOpen={Boolean(storyboardAngle)}
        onClose={() => setStoryboardAngle(null)}
        productId={productData?.id}
        product={productData}
        angle={storyboardAngle}
        onSaveSuccess={handleStoryboardSaveSuccess}
        onOpenVoiceGen={() => {
          if (!storyboardAngle) return;
          const aid = storyboardAngle.angle_id || storyboardAngle.id;
          const aBatch = storyboardAngle.batch || 1;
          const aIdx = angles.findIndex((a) => (a.angle_id || a.id) === aid && (a.batch || 1) === aBatch);
          if (aIdx >= 0) {
            handleGenerateShotList(aIdx);
          }
        }}
      />

      {/* ── Universal Filming Recipe Modal (สูตรถ่ายทำ 5 ช็อตมาตรฐาน) ── */}
      <UniversalFilmingRecipeModal
        isOpen={filmingRecipeModalOpen}
        onClose={() => setFilmingRecipeModalOpen(false)}
        productData={productData}
        showToast={showToast}
      />


      {/* ── AI Hook Variation & A/B Modal ── */}
      <HookVariationModal
        isOpen={!!hookModalAngle}
        onClose={() => setHookModalAngle(null)}
        product={productData}
        angle={hookModalAngle}
        onHookApplied={handleHookApplied}
        showToast={showToast}
      />

      {/* ── Batch Angle Render Queue Modal ── */}
      <BatchRenderModal
        isOpen={batchRenderOpen}
        onClose={() => setBatchRenderOpen(false)}
        product={productData ? { ...productData, angles } : null}
        angles={angles}
        voicePreset={selectedVoicePreset}
        onBatchCompleted={handleBatchCompleted}
        showToast={showToast}
      />

      {/* ── Generate New Batch Modal ── */}
      <Modal
        isOpen={showBatchModal}
        onClose={() => !isGeneratingBatch && setShowBatchModal(false)}
        title="เจนสคริปต์ล็อตใหม่ด้วย AI (ไม่ซ้ำมุมเดิม)"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400 leading-relaxed">
            AI จะนำชื่อมุมมองเดิมทั้งหมด <strong className="text-white">({angles.length} มุม)</strong> มาเป็นบริบทเพื่อหลีกเลี่ยงการสร้างมุมซ้ำ และคิดค้นแกนการขายใหม่ๆ พร้อมฮุกที่สดใหม่สำหรับสินค้านี้
          </p>

          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5 text-xs">
            <span className="text-slate-400 font-semibold block">มุมเดิมที่จะหลีกเลี่ยง ({angles.length} มุม):</span>
            <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-1">
              {angles.map((a, i) => (
                <span key={i} className="px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-300 text-[11px] truncate max-w-[200px]">
                  {a.angle_name}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-slate-300 font-semibold block">จำนวนมุมที่จะสร้างเพิ่มในล็อตนี้:</label>
            <div className="flex items-center gap-2">
              {[
                { val: 4, label: '4 มุม' },
                { val: 7, label: '7 มุม' },
                { val: 10, label: '10 มุม (แนะนำ)' },
              ].map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setBatchAngleCount(opt.val)}
                  className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    batchAngleCount === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.04] text-slate-400 border border-white/[0.08] hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-slate-300 font-semibold block">ความยาวคลิป:</label>
            <div className="flex items-center gap-2">
              {DURATION_OPTIONS.map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setBatchDuration(opt.val)}
                  className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    batchDuration === opt.val
                      ? 'bg-[#25F4EE]/20 text-[#25F4EE] border border-[#25F4EE]/40 ring-1 ring-[#25F4EE]/20'
                      : 'bg-white/[0.04] text-slate-400 border border-white/[0.08] hover:text-white'
                  }`}
                >
                  {opt.val}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
            <Button
              variant="ghost"
              onClick={() => setShowBatchModal(false)}
              disabled={isGeneratingBatch}
            >
              ยกเลิก
            </Button>
            <Button
              variant="primary"
              onClick={handleGenerateBatch}
              disabled={isGeneratingBatch}
              className="bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white font-bold"
            >
              {isGeneratingBatch ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  กำลังสั่งการ AI...
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  เริ่มสร้างล็อต {batches.length + 1} ({batchAngleCount} มุม)
                </span>
              )}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Scene Catalog Viewer Modal ── */}
      <SceneCatalogModal
        isOpen={Boolean(inspectingCatalog)}
        onClose={() => setInspectingCatalog(null)}
        catalog={inspectingCatalog?.catalog || (inspectingCatalog?.videoPath ? sceneCatalogsMap[inspectingCatalog.videoPath] : null)}
        videoName={inspectingCatalog?.videoName}
        videoPath={inspectingCatalog?.videoPath}
        onRescan={() => {
          if (inspectingCatalog?.videoPath) {
            handleIndexSceneCatalog(inspectingCatalog.videoPath, true);
          }
        }}
        isRescanning={isScanningScenes}
      />
    </div>
  );
}
