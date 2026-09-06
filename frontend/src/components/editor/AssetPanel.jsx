import React, { useMemo, useState, useRef } from 'react';
import {
  Check, Film, Music, Palette, Plus, Search, Sticker, Type, Volume2, Play, Square,
  FileText, Sparkles, Loader2, Download, Copy, RefreshCw, Layers, Eye, X, Upload, Clock
} from 'lucide-react';
import { transcribeMedia, uploadFile } from '../../api';

const TABS = [
  { id: 'clips', label: 'คลิป', icon: Film },
  { id: 'srt', label: 'AI ถอดซับ', icon: FileText },
  { id: 'audio', label: 'เสียง', icon: Music },
  { id: 'text', label: 'ข้อความ', icon: Type },
  { id: 'sticker', label: 'สติกเกอร์', icon: Sticker },
  { id: 'filter', label: 'ฟิลเตอร์', icon: Palette },
];

// Drag payload type shared with Timeline's drop target.
export const CLIP_DRAG_TYPE = 'application/x-capcut-clip';
export const TEXT_TEMPLATE_DRAG_TYPE = 'application/x-capcut-text-template';

import { toMediaUrl } from '../../lib/mediaUrl';
import TextLookPreview from './TextLookPreview';
import { HOOK_FS_RATIO, HOOK_SHADOW, overlayFromTextTemplate } from '../../lib/overlayModel';
import { TIER_KEYS } from '../../lib/hookStyles';

const LEGACY_SFX_ALIASES = {
  whoosh: 'sfx_whoosh_fast',
  pop: 'sfx_pop_bubble',
  ding: 'sfx_bell_ding',
  cash: 'sfx_cash_register',
  boom: 'sfx_vine_boom',
};

/**
 * A gallery card's look, resolved through the same conversion a saved project
 * goes through. The card and the canvas cannot disagree because neither one
 * carries its own description of the style.
 */
// What a banner card shows: three short stand-ins, so the size and colour
// ladder of a template reads at a glance without needing a real product.
const HOOK_CARD_SAMPLE = ['BRAND', 'รุ่นเด่น', 'หมวดสินค้า'];

/** One tier of a hook template, in TextLook spelling, for a gallery card. */
function hookCardLook(tpl, tierKey) {
  const tier = tpl.tiers[tierKey];
  return {
    font: tpl.font,
    size_pct: tier.size_pct,
    color: tier.color === null ? '#FFE600' : tier.color,
    outline_color: tier.outline_color,
    outline_px: tier.outline_px,
    upper: tier.upper,
    pill: tier.pill ? { fill: tier.pill, border: null, pad_x_em: 0.342, pad_y_em: 0.171 } : null,
    shadow: HOOK_SHADOW,
  };
}

function getMotionPreviewClass(motion) {
  const loop = motion?.loop;
  const animIn = motion?.in;
  if (loop === 'flicker') return 'group-hover:anim-preview-flicker';
  if (loop === 'shake' || animIn === 'pop') return 'group-hover:anim-preview-shake';
  if (loop === 'wave') return 'group-hover:anim-preview-wave';
  if (loop === 'pulse' || animIn === 'bounce') return 'group-hover:anim-preview-pulse';
  if (animIn === 'pop_zoom') return 'group-hover:anim-preview-pop_zoom';
  if (loop === 'lightsweep') return 'group-hover:anim-preview-lightsweep';
  return 'group-hover:scale-105';
}

export function templateLook(tpl) {
  return overlayFromTextTemplate(tpl, { id: '__card__', start: 0, end: 1 }).look;
}

export const TEXT_TEMPLATES = [
  // ─── 1. Hook พาดหัวเปิดคลิป (0 - 3.5s ตรึงสายตาทันที) ───
  {
    id: 'tpl_hook_warning_stop',
    category: 'hook',
    name: 'อย่าเพิ่งซื้อถ้ายังไม่รู้',
    text: 'อย่าเพิ่งซื้อ! ⚠️\nถ้ายังไม่รู้สิ่งนี้',
    fontName: 'Kanit',
    color: '#FFE600',
    scale: 1.35,
    anim: 'stamp',
    bgStyle: 'badge_red',
    badgeColor: '#FE2C55',
    sfx: 'boom',
    sfxLabel: 'Boom กระแทก',
    // A coloured edge, thick enough to hold its own against the banner's --
    // a text overlay had no outline fields at all before this, so every card
    // in this gallery burned the same black 5.0 and read flat beside one.
    look: { outline_color: '#5C0016', outline_px: 7.0 },
  },
  {
    id: 'tpl_hook_real_deal',
    category: 'hook',
    name: 'ตัวจบสายนี้จริงมั้ย?',
    text: 'ตัวจบสายนี้จริงมั้ย? ⚡',
    fontName: 'Prompt',
    color: '#25F4EE',
    scale: 1.3,
    anim: 'zoom',
    bgStyle: 'pill',
    sfx: 'sfx_whoosh_fast',
    sfxLabel: 'Whoosh พุ่งเร็ว',
    // A coloured edge, thick enough to hold its own against the banner's --
    // a text overlay had no outline fields at all before this, so every card
    // in this gallery burned the same black 5.0 and read flat beside one.
    look: { outline_color: '#04303A', outline_px: 6.0 },
  },
  {
    id: 'tpl_hook_honest_review',
    category: 'hook',
    name: 'รีวิวเรียลๆ 1 เดือน',
    text: 'รีวิวเรียลๆ ใช้จริง 1 เดือน 📦',
    fontName: 'Kanit',
    color: '#FFFFFF',
    scale: 1.25,
    anim: 'pop',
    bgStyle: 'pill',
    sfx: 'sfx_sub_drop',
    sfxLabel: 'Sub Drop ทุ้มลึก',
    // A coloured edge, thick enough to hold its own against the banner's --
    // a text overlay had no outline fields at all before this, so every card
    // in this gallery burned the same black 5.0 and read flat beside one.
    look: { outline_color: '#000000', outline_px: 6.0 },
  },
  {
    id: 'tpl_hook_shock_reveal',
    category: 'hook',
    name: 'ลองแล้วถึงรู้!',
    text: 'ลองแล้วถึงรู้! 😱',
    fontName: 'Kanit',
    color: '#FE2C55',
    scale: 1.35,
    anim: 'pop',
    bgStyle: 'badge_yellow',
    badgeColor: '#FFE600',
    sfx: 'sfx_gasp_shock',
    sfxLabel: 'Gasp ตกใจ',
    // A coloured edge, thick enough to hold its own against the banner's --
    // a text overlay had no outline fields at all before this, so every card
    // in this gallery burned the same black 5.0 and read flat beside one.
    look: { outline_color: '#FFFFFF', outline_px: 9.0 },
  },
  {
    id: 'tpl_hook_flash_sale',
    category: 'hook',
    name: 'โปรไฟลุก Flash Sale',
    text: 'โปรไฟลุก ด่วน! 🔥\nลดกระหน่ำวันนี้',
    fontName: 'Kanit',
    color: '#FFE04C',
    scale: 1.35,
    anim: 'pop',
    bgStyle: 'badge_red',
    badgeColor: '#FE2C55',
    sfx: 'boom',
    sfxLabel: 'Boom ไฟลุก',
    look: { outline_color: '#000000', outline_px: 8.0 },
  },
  {
    id: 'tpl_hook_neon_cyber',
    category: 'hook',
    name: 'นีออน ไซเบอร์ไฮป์',
    text: 'รุ่นใหม่มาแรง ⚡\nCYBER 2026',
    fontName: 'Chakra Petch',
    color: '#25F4EE',
    scale: 1.3,
    anim: 'zoom',
    bgStyle: 'pill',
    sfx: 'whoosh',
    sfxLabel: 'Whoosh นีออน',
    look: { outline_color: '#000000', outline_px: 8.0 },
  },
  {
    id: 'tpl_hook_minimal_luxury',
    category: 'hook',
    name: 'ลักชัวรี ลุคหรูพรีเมียม',
    text: 'LUXURY EDITION ✨\nตัวท็อปพรีเมียม',
    fontName: 'Prompt',
    color: '#E6C24A',
    scale: 1.25,
    anim: 'rise',
    bgStyle: 'pill',
    sfx: 'ding',
    sfxLabel: 'Ding กระดิ่งทอง',
    look: { outline_color: '#1A1A1A', outline_px: 4.0 },
  },

  // ─── 2. รีวิว & ฟีเจอร์เด่น (Review & Feature Highlight) ───
  {
    id: 'tpl_review_score_10',
    category: 'review',
    name: 'คะแนน 10/10 ไม่หัก',
    text: '10/10 ไม่หัก 🌟',
    fontName: 'Kanit',
    color: '#FFD700',
    scale: 1.2,
    anim: 'pop',
    bgStyle: 'none',
    sfx: 'ding',
    sfxLabel: 'Ding กระดิ่ง',
  },
  {
    id: 'tpl_review_must_have',
    category: 'review',
    name: 'ของมันต้องมี',
    text: 'ของมันต้องมี ✔️',
    fontName: 'Kanit',
    color: '#00F59B',
    scale: 1.15,
    anim: 'pop',
    bgStyle: 'pill',
    sfx: 'pop',
    sfxLabel: 'Pop บับเบิล',
  },
  {
    id: 'tpl_review_pros_cons',
    category: 'review',
    name: 'ข้อดี vs ข้อควรระวัง',
    text: 'ข้อดี vs ข้อควรระวัง ⚖️',
    fontName: 'Prompt',
    color: '#FFFFFF',
    scale: 1.1,
    anim: 'slide',
    bgStyle: 'pill',
    sfx: 'sfx_whoosh_fast',
    sfxLabel: 'Whoosh ตัดฉาก',
  },
  {
    id: 'tpl_review_pro_tip',
    category: 'review',
    name: 'Pro Tip แนะนำ',
    text: '💡 PRO TIP: แนะนำเลย',
    fontName: 'Prompt',
    color: '#25F4EE',
    scale: 1.1,
    anim: 'slide',
    bgStyle: 'pill',
    sfx: 'sfx_bell_ding',
    sfxLabel: 'Bell Ding แจ้งเตือน',
  },
  {
    id: 'tpl_review_verdict',
    category: 'review',
    name: 'สรุปคุ้มค่าน่าจัด',
    text: 'สรุปคุ้มค่าน่าจัด 💯',
    fontName: 'Kanit',
    color: '#C084FC',
    scale: 1.2,
    anim: 'pop',
    bgStyle: 'none',
    sfx: 'ding',
    sfxLabel: 'Ding สำเร็จ',
  },

  // ─── 3. ดีล & โปรโมชั่น (Sales & Deals) ───
  {
    id: 'tpl_sale_flash_50',
    category: 'sale',
    name: 'Flash Sale Tag',
    text: 'FLASH SALE 50% 🔥',
    fontName: 'Kanit',
    color: '#FFFFFF',
    scale: 1.25,
    anim: 'stamp',
    bgStyle: 'badge_red',
    badgeColor: '#FE2C55',
    sfx: 'cash',
    sfxLabel: 'Cash เปิดกล่องเงิน',
  },
  {
    id: 'tpl_sale_special_price',
    category: 'sale',
    name: 'ราคาพิเศษวันนี้',
    text: 'ราคาพิเศษวันนี้ 💰',
    fontName: 'Prompt',
    color: '#000000',
    scale: 1.15,
    anim: 'pop',
    bgStyle: 'badge_yellow',
    badgeColor: '#FFE600',
    sfx: 'sfx_coin_drop',
    sfxLabel: 'Coin เหรียญทอง',
  },
  {
    id: 'tpl_sale_bogo',
    category: 'sale',
    name: 'โปรเด็ด 1 แถม 1',
    text: 'โปรเด็ด 1 แถม 1 🎁',
    fontName: 'Kanit',
    color: '#FF6B00',
    scale: 1.2,
    anim: 'pop',
    bgStyle: 'none',
    sfx: 'pop',
    sfxLabel: 'Pop บับเบิล',
  },
  {
    id: 'tpl_sale_drop_price',
    category: 'sale',
    name: 'ลดเหลือเพียง...',
    text: 'ลดเหลือเพียง ฿99.- 🏷️',
    fontName: 'Kanit',
    color: '#FFE600',
    scale: 1.25,
    anim: 'zoom',
    bgStyle: 'pill',
    sfx: 'sfx_cash_register',
    sfxLabel: 'Cash Register เก็บเงิน',
  },
  {
    id: 'tpl_sale_limited_stock',
    category: 'sale',
    name: 'ด่วนจำกัด 100 ชิ้น',
    text: 'ด่วน! จำกัด 100 ชิ้นแรก ⏳',
    fontName: 'Prompt',
    color: '#FFFFFF',
    scale: 1.15,
    anim: 'slide',
    bgStyle: 'badge_red',
    badgeColor: '#E11D48',
    sfx: 'sfx_camera_shutter',
    sfxLabel: 'Shutter ถ่ายรูป',
  },

  // ─── 4. ป้ายพิกัด & Call to Action (CTA) ───
  {
    id: 'tpl_cta_basket',
    category: 'cta',
    name: 'พิกัดจิ้มตะกร้าเหลือง',
    text: 'พิกัดจิ้มตะกร้าซ้ายล่าง 👇',
    fontName: 'Kanit',
    color: '#000000',
    scale: 1.2,
    anim: 'slide',
    bgStyle: 'badge_yellow',
    badgeColor: '#FFE600',
    sfx: 'ding',
    sfxLabel: 'Ding กระดิ่ง',
  },
  {
    id: 'tpl_cta_pin',
    category: 'cta',
    name: 'พิกัดในคลิป',
    text: 'พิกัดในคลิป 📍',
    fontName: 'Kanit',
    color: '#25F4EE',
    scale: 1.05,
    anim: 'slide',
    bgStyle: 'pill',
    sfx: 'pop',
    sfxLabel: 'Pop บับเบิล',
  },
  {
    id: 'tpl_cta_hurry_coupon',
    category: 'cta',
    name: 'เก็บคูปองลดเพิ่ม',
    text: 'กดเก็บคูปองลดเพิ่ม 🎟️',
    fontName: 'Prompt',
    color: '#00F59B',
    scale: 1.1,
    anim: 'pop',
    bgStyle: 'pill',
    sfx: 'sfx_bell_ding',
    sfxLabel: 'Bell Ding แจ้งเตือน',
  },
  {
    id: 'tpl_cta_save_favorite',
    category: 'cta',
    name: 'เซฟไว้ดูก่อนหมดโปร',
    text: 'เซฟไว้เลย เดี๋ยวหาไม่เจอ 📌',
    fontName: 'Prompt',
    color: '#FFFFFF',
    scale: 1.05,
    anim: 'fade',
    bgStyle: 'pill',
    sfx: 'sfx_mouse_click',
    sfxLabel: 'Click คลิกเบา',
  },

  // ─── 5. มินิมอล & คลีน (Minimal & Clean) ───
  {
    id: 'tpl_minimal_tech_spec',
    category: 'minimal',
    name: 'Tech Specs Tag',
    text: 'TECH SPECS',
    fontName: 'Prompt',
    color: '#E2E8F0',
    scale: 0.95,
    anim: 'fade',
    bgStyle: 'none',
    sfx: 'sfx_mouse_click',
    sfxLabel: 'Click คลิกเบา',
  },
  {
    id: 'tpl_minimal_lower_third',
    category: 'minimal',
    name: 'Clean Lower-Third',
    text: 'PRODUCT REVIEW',
    fontName: 'IBMPlex',
    color: '#FFFFFF',
    scale: 0.95,
    anim: 'fade',
    bgStyle: 'pill',
    sfx: 'sfx_mouse_click',
    sfxLabel: 'Click คลิกเบา',
  },
  {
    id: 'tpl_minimal_feature_bullet',
    category: 'minimal',
    name: 'Key Highlight',
    text: 'KEY HIGHLIGHT ✨',
    fontName: 'Kanit',
    color: '#25F4EE',
    scale: 1.0,
    anim: 'slide',
    bgStyle: 'pill',
    sfx: 'pop',
    sfxLabel: 'Pop บับเบิล',
  },
];

const FONTS = [
  { id: 'IBMPlex', name: 'IBM Plex Sans Thai' },
  { id: 'Kanit', name: 'Kanit' },
  { id: 'Prompt', name: 'Prompt' },
  { id: 'NotoSansThai', name: 'Noto Sans Thai' },
];

function parseSrtToCues(srtText) {
  if (!srtText) return [];
  const blocks = srtText.trim().split(/\n\s*\n/);
  const cues = [];

  const timeToSec = (timeStr) => {
    if (!timeStr) return 0;
    const [hms, ms] = timeStr.trim().replace('.', ',').split(',');
    const [h, m, s] = hms.split(':').map(Number);
    return (h || 0) * 3600 + (m || 0) * 60 + (s || 0) + (parseInt(ms || 0, 10) / 1000);
  };

  blocks.forEach((block) => {
    const lines = block.trim().split('\n');
    if (lines.length >= 2) {
      let timeLine = lines[0].includes('-->') ? lines[0] : lines[1];
      let textLines = lines[0].includes('-->') ? lines.slice(1) : lines.slice(2);

      if (timeLine && timeLine.includes('-->')) {
        const [startStr, endStr] = timeLine.split('-->');
        const start = timeToSec(startStr);
        const end = timeToSec(endStr);
        const text = textLines[0] || '';
        const translation = textLines.slice(1).join(' ') || '';

        cues.push({
          start: Number(start.toFixed(2)),
          end: Number(end.toFixed(2)),
          text: text.trim(),
          translation: translation.trim(),
          sfx: null
        });
      }
    }
  });

  return cues;
}

function Row({ active, onClick, children, title, draggable, onDragStart, onDragEnd }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={`group flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE] ${
        active
          ? 'border-[#25F4EE] bg-[#25F4EE]/10 text-white'
          : 'border-white/[0.08] bg-black/40 hover:border-white/[0.2] hover:bg-white/[0.05]'
      }`}
    >
      {children}
    </button>
  );
}

export default function AssetPanel({
  videos = [],
  clipList = [],
  durations = {},
  assets,             // { sfx, music, fonts, stickers, luts }
  style,              // { fontName, bgmName, lutName, stickerBadge }
  selectedCaption,    // cue object or null
  onAddClip,
  onAddTextAtPlayhead,
  onAddTextTemplate,
  onSelectTextTemplate,
  previewTextTemplate = null,
  activeTextTemplateId = null,
  hookTemplates = null,
  activeHookTemplate = null,
  onApplyHookTemplate = null,
  onStyleChange,
  onAssignSfx,
  onImportCues,       // (cues: Array<{ start, end, text, translation, sfx }>) => void
  onVideoUploaded,
  projectName = '',
}) {
  const [tab, setTab] = useState('clips');
  const [query, setQuery] = useState('');
  const [textCategory, setTextCategory] = useState('all');
  const [textSearch, setTextSearch] = useState('');

  // Live Preview SFX when clicking a text template
  const playSfxPreview = (sfxKey) => {
    if (!sfxKey || !assets?.sfx) return;
    const sfxList = assets.sfx || [];
    const canonical = LEGACY_SFX_ALIASES[sfxKey] || sfxKey;
    const item = sfxList.find(s => s.id === canonical || s.name === canonical || s.id === sfxKey || s.name === sfxKey)
      || sfxList.find(s => s.name?.toLowerCase().includes(sfxKey.toLowerCase()));
    if (!item?.path) return;
    try {
      const audio = new Audio(toMediaUrl(item.path));
      audio.volume = 0.28;
      audio.play().catch(() => {});
    } catch (_) {}
  };

  // Quick video preview modal state
  const [previewVideo, setPreviewVideo] = useState(null);

  // Direct video upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // Helper to calculate how many times a video is mapped / used on the timeline
  const getClipUsage = (video) => {
    if (!clipList || clipList.length === 0) return 0;
    const vPath = (video.path || '').replace(/\\/g, '/').toLowerCase();
    const vName = (video.name || '').toLowerCase();
    return clipList.filter((c) => {
      const cPath = (c.source_path || '').replace(/\\/g, '/').toLowerCase();
      return cPath === vPath || (vName && cPath.endsWith('/' + vName)) || (vName && cPath.endsWith(vName));
    }).length;
  };

  // Helper to format seconds into M:SS
  const formatDuration = (sec) => {
    if (!sec || isNaN(sec)) return null;
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleDirectUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('target_dir', 'raw');
      if (projectName) fd.append('product_id', projectName);
      const res = await uploadFile(fd, (pct) => setUploadProgress(pct));
      if (res?.file && onVideoUploaded) {
        onVideoUploaded(res.file);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadError('อัปโหลดไฟล์ล้มเหลว กรุณาลองใหม่อีกครั้ง');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Auto-SRT Generator state inside Editor
  const [selectedMediaForSrt, setSelectedMediaForSrt] = useState(videos[0]?.path || '');
  const [srtMode, setSrtMode] = useState('bilingual'); // 'bilingual' | 'mono' | 'dual'
  const [srtLang, setSrtLang] = useState('th');
  const [srtDensity, setSrtDensity] = useState(5);
  const [transcribing, setTranscribing] = useState(false);
  const [transcribeResult, setTranscribeResult] = useState(null);
  const [transcribeError, setTranscribeError] = useState(null);
  const [copiedSrt, setCopiedSrt] = useState(false);
  const [importedSuccess, setImportedSuccess] = useState(false);

  const handleTranscribe = async () => {
    if (!selectedMediaForSrt) {
      setTranscribeError('กรุณาเลือกคลิปวิดีโอหรือเสียงที่ต้องการถอดซับก่อนครับ');
      return;
    }

    setTranscribing(true);
    setTranscribeError(null);
    setTranscribeResult(null);
    setImportedSuccess(false);

    try {
      const res = await transcribeMedia({
        media_path: selectedMediaForSrt,
        mode: srtMode,
        lang: srtLang || null,
        words_per_line: srtDensity,
        fast: true
      });
      setTranscribeResult(res);
    } catch (err) {
      setTranscribeError(err.friendlyMessage || err.response?.data?.detail || err.message || 'ถอดเสียงล้มเหลว');
    } finally {
      setTranscribing(false);
    }
  };

  const handleImportToTimeline = () => {
    if (!transcribeResult?.content) return;
    const parsedCues = parseSrtToCues(transcribeResult.content);
    if (parsedCues.length === 0) {
      setTranscribeError('ไม่พบข้อความซับไตเติลที่แยกเวลาได้');
      return;
    }
    onImportCues?.(parsedCues);
    setImportedSuccess(true);
    setTimeout(() => setImportedSuccess(false), 3000);
  };

  const handleCopySrt = () => {
    if (!transcribeResult?.content) return;
    navigator.clipboard.writeText(transcribeResult.content);
    setCopiedSrt(true);
    setTimeout(() => setCopiedSrt(false), 2000);
  };

  const [previewingAudio, setPreviewingAudio] = useState(null);
  const audioPlayerRef = useRef(null);

  const toggleAudioPreview = (e, relPath) => {
    e.stopPropagation();
    const url = `/api/media/${relPath}`;
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      if (previewingAudio === url) {
        setPreviewingAudio(null);
        return;
      }
    }
    const a = new Audio(url);
    audioPlayerRef.current = a;
    setPreviewingAudio(url);
    a.play().catch(() => {});
    a.onended = () => setPreviewingAudio(null);
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (item) => !q || `${item.label_th || ''} ${item.name || ''}`.toLowerCase().includes(q);
    return {
      videos: (videos || []).filter((v) => !q || v.name.toLowerCase().includes(q)),
      sfx: (assets?.sfx || []).filter(match),
      music: (assets?.music || []).filter(match),
      stickers: (assets?.stickers || []).filter(match),
      luts: (assets?.luts || []).filter(match),
      fonts: FONTS
        .map((f) => {
          // Match the render engine's font id to a real file on disk so the
          // row can be previewed in its own typeface instead of the UI font.
          const key = f.id.toLowerCase();
          const file = (assets?.fonts || []).find((a) => {
            const norm = (a.id || '').replace(/[^a-zA-Z]/g, '').toLowerCase();
            return norm.startsWith(key);
          });
          return { ...f, file };
        })
        .filter((f) => !q || `${f.name} ${f.id}`.toLowerCase().includes(q)),
    };
  }, [videos, assets, query]);

  return (
    <div className="flex h-full min-h-0 flex-col border-r border-white/[0.08] bg-[#0C1019]">
      {/* tab rail - responsive 6 tabs fitting all screen widths without overflow */}
      <div className="grid grid-cols-6 border-b border-white/[0.08] bg-black/30 p-1 gap-1 flex-shrink-0">
        {TABS.map(({ id, label, icon: Icon }) => {
          const isActive = tab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              title={label}
              aria-pressed={isActive}
              className={`flex flex-col items-center justify-center py-2 px-0.5 rounded-lg transition-all focus:outline-none cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-b from-[#25F4EE]/15 to-blue-500/10 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <Icon className="h-3.5 w-3.5 flex-shrink-0 mb-0.5" strokeWidth={isActive ? 2.2 : 1.7} />
              <span className="text-[10px] font-medium tracking-tight truncate w-full text-center leading-tight">
                {label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search & Direct Upload bar (hide in SRT tab) */}
      {tab !== 'srt' && (
        <div className="flex-shrink-0 p-2 space-y-1.5 border-b border-white/[0.04]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ค้นหา..."
              className="w-full py-1.5 pl-8 pr-2.5 rounded-xl bg-black/50 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-[#25F4EE]"
            />
          </div>

          {tab === 'clips' && (
            <div>
              <input
                type="file"
                ref={fileInputRef}
                accept="video/*"
                className="hidden"
                onChange={handleDirectUpload}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full py-1.5 px-2.5 rounded-xl border border-dashed border-white/[0.12] hover:border-[#25F4EE]/50 hover:bg-[#25F4EE]/5 text-slate-300 hover:text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#25F4EE]" />
                    <span>กำลังอัปโหลด ({uploadProgress}%)...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>แนบคลิปเพิ่มเข้าโปรเจกต์</span>
                  </>
                )}
              </button>
              {uploadError && (
                <p className="text-[11px] text-rose-400 mt-1 text-center">{uploadError}</p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
        {/* TAB 1: CLIPS */}
        {tab === 'clips' && (
          <div className="space-y-1.5">
            {filtered.videos.map((v) => {
              const usageCount = getClipUsage(v);
              const isUsed = usageCount > 0;
              const dur = v.duration || durations?.[v.path] || durations?.[v.rel_path];
              const durStr = formatDuration(dur);

              return (
                <div
                  key={v.path}
                  className={`group flex items-center justify-between gap-1.5 rounded-xl border p-2 text-left transition-all ${
                    isUsed
                      ? 'border-[#25F4EE]/40 bg-[#25F4EE]/[0.05] hover:border-[#25F4EE]'
                      : 'border-white/[0.08] bg-black/40 hover:border-white/[0.2] hover:bg-white/[0.05]'
                  }`}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.effectAllowed = 'copy';
                    e.dataTransfer.setData(
                      CLIP_DRAG_TYPE,
                      JSON.stringify({ path: v.path, name: v.name, duration: dur || v.duration })
                    );
                  }}
                >
                  {/* Left: Preview trigger & Metadata */}
                  <div
                    className="flex items-center gap-2 min-w-0 flex-1 cursor-pointer"
                    onClick={() => onAddClip(v)}
                    title="คลิกเพื่อต่อท้ายไทม์ไลน์ หรือลากไปวางตรงจุดที่ต้องการ"
                  >
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewVideo(v);
                      }}
                      title="เปิดดูพรีวิวคลิป"
                      className="h-7 w-7 rounded-lg bg-white/[0.06] hover:bg-[#25F4EE]/20 hover:text-[#25F4EE] text-slate-400 flex items-center justify-center transition-colors cursor-pointer flex-shrink-0"
                    >
                      <Eye className="h-3.5 w-3.5" />
                    </button>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-xs font-semibold text-slate-200 group-hover:text-white" title={v.name}>
                          {v.name}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 mt-0.5">
                        {durStr && (
                          <span className="text-[10px] font-mono text-slate-400 flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5 text-slate-500" />
                            {durStr}
                          </span>
                        )}
                        {v.size_mb ? (
                          <span className="text-[10px] text-slate-500">{v.size_mb} MB</span>
                        ) : null}
                        {isUsed ? (
                          <span className="px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[9.5px] font-bold">
                            ในไทม์ไลน์ {usageCount > 1 ? `(${usageCount})` : ''}
                          </span>
                        ) : (
                          <span className="text-[9.5px] text-slate-500">
                            ยังไม่ใช้
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right: Quick Add Button */}
                  <button
                    type="button"
                    onClick={() => onAddClip(v)}
                    title="เพิ่มลงในไทม์ไลน์"
                    className="h-7 w-7 rounded-lg bg-white/[0.06] hover:bg-[#25F4EE] hover:text-slate-950 text-slate-400 flex items-center justify-center transition-all cursor-pointer flex-shrink-0"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
            {filtered.videos.length === 0 && (
              <p className="px-1 py-4 text-center text-xs text-slate-500">
                ไม่มีคลิปที่ตรงกับคำค้น — สามารถกดปุ่มแนบคลิปเพิ่มด้านบนได้เลยครับ
              </p>
            )}
          </div>
        )}

        {/* TAB 2: AI AUTO-SRT SUBTITLES (Consolidated) */}
        {tab === 'srt' && (
          <div className="space-y-3 text-left">
            <div className="p-2.5 rounded-xl bg-gradient-to-r from-[#25F4EE]/10 to-blue-500/10 border border-[#25F4EE]/20 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#25F4EE] font-kanit">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Auto-SRT (ถอดซับแม่นยำ)</span>
              </div>
              <p className="text-sm text-slate-300 leading-tight">
                ถอดเสียงอัตโนมัติด้วย Whisper + PyThaiNLP แล้วนำเข้าเป็นท่อนคำบรรยายบนไทม์ไลน์ทันที
              </p>
            </div>

            {/* Select Media */}
            <div className="space-y-1">
              <label className="text-sm font-bold text-slate-300">เลือกคลิปหรือเสียง:</label>
              <select
                value={selectedMediaForSrt}
                onChange={(e) => setSelectedMediaForSrt(e.target.value)}
                className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#25F4EE]"
              >
                {videos.map((v) => (
                  <option key={v.path} value={v.path} className="bg-[#080B11]">
                    {v.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Subtitle Mode */}
            <div className="space-y-1">
              <label className="text-sm font-bold text-slate-300">รูปแบบภาษา:</label>
              <select
                value={srtMode}
                onChange={(e) => setSrtMode(e.target.value)}
                className="w-full py-1.5 px-2 rounded-xl bg-black/60 border border-white/[0.1] text-white text-sm focus:outline-none focus:border-[#25F4EE]"
              >
                <option value="bilingual" className="bg-[#080B11]">2 ภาษา (ไทย + แปลอังกฤษ)</option>
                <option value="mono" className="bg-[#080B11]">ภาษาไทยล้วน</option>
                <option value="dual" className="bg-[#080B11]">Dual Original</option>
              </select>
            </div>

            {/* Subtitle Density */}
            <div className="space-y-1">
              <label className="text-sm font-bold text-slate-300">ความยาวประโยค:</label>
              <div className="grid grid-cols-3 gap-1">
                {[
                  { count: 4, label: '4 คำ' },
                  { count: 5, label: '5-6 คำ' },
                  { count: 7, label: '7-8 คำ' },
                ].map((d) => (
                  <button
                    key={d.count}
                    type="button"
                    onClick={() => setSrtDensity(d.count)}
                    className={`py-1 rounded-lg text-sm font-bold border transition-colors ${
                      srtDensity === d.count
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Transcribe Action Button */}
            <button
              type="button"
              onClick={handleTranscribe}
              disabled={transcribing}
              className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer transition-all disabled:opacity-50"
            >
              {transcribing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>กำลังถอดเสียง AI...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>เริ่มถอดซับอัตโนมัติ</span>
                </>
              )}
            </button>

            {transcribeError && (
              <p className="text-sm text-rose-400 bg-rose-500/10 p-2 rounded-xl border border-rose-500/20">
                {transcribeError}
              </p>
            )}

            {/* Transcribe Results & Import Button */}
            {transcribeResult && (
              <div className="p-2.5 rounded-xl bg-black/60 border border-[#25F4EE]/30 space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between text-sm font-bold text-[#25F4EE]">
                  <span>ถอดเสียงสำเร็จ</span>
                  <button
                    type="button"
                    onClick={handleCopySrt}
                    className="text-sm text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer"
                  >
                    {copiedSrt ? <><Check className="w-3 h-3 text-emerald-400" /> คัดลอกแล้ว</> : <><Copy className="w-3 h-3" /> คัดลอก .SRT</>}
                  </button>
                </div>

                <div className="max-h-28 overflow-y-auto p-1.5 rounded-lg bg-black/40 border border-white/[0.04] text-sm font-mono text-slate-300 space-y-1 select-all">
                  {transcribeResult.content || 'ไม่มีข้อความ'}
                </div>

                {/* Import to Timeline Button */}
                <button
                  type="button"
                  onClick={handleImportToTimeline}
                  className="w-full py-1.5 px-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-sm font-bold flex items-center justify-center gap-1.5 shadow-md cursor-pointer transition-all"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>นำเข้าสู่ไทม์ไลน์ (Import to Timeline)</span>
                </button>

                {importedSuccess && (
                  <p className="text-sm text-emerald-400 text-center font-bold">
                    ✓ นำเข้าคำบรรยายลงไทม์ไลน์เรียบร้อยแล้ว
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AUDIO */}
        {tab === 'audio' && (
          <>
            <p className="px-1 pt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
              เพลงประกอบ (ทั้งคลิป)
            </p>

            <div className="mb-2 space-y-2 rounded-xl border border-white/[0.08] bg-black/40 p-2.5">
              <label className="block">
                <span className="mb-1 flex justify-between text-xs text-slate-300">
                  <span>ระดับเสียงเพลง (BGM)</span>
                  <span className="font-mono text-[#25F4EE] font-bold">{Math.round((style.bgmVolume ?? 0.12) * 100)}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={style.bgmVolume ?? 0.12}
                  onChange={(e) => onStyleChange({ bgmVolume: parseFloat(e.target.value) })}
                  className="w-full accent-[#25F4EE]"
                />
              </label>

              <div className="grid grid-cols-4 gap-1">
                {[0.08, 0.15, 0.25, 0.40].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => onStyleChange({ bgmVolume: v })}
                    className={`py-1 rounded-lg text-[10px] font-mono font-bold border transition-all cursor-pointer ${
                      Math.abs((style.bgmVolume ?? 0.12) - v) < 0.03
                        ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                        : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white'
                    }`}
                  >
                    {Math.round(v * 100)}%
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => onStyleChange({ bgmDucking: !style.bgmDucking })}
                aria-pressed={!!style.bgmDucking}
                className={`w-full rounded-lg border py-1.5 text-xs font-bold transition-all cursor-pointer ${
                  style.bgmDucking
                    ? 'border-[#25F4EE] bg-[#25F4EE]/20 text-[#25F4EE]'
                    : 'border-white/[0.08] bg-black/40 text-slate-300 hover:text-white'
                }`}
              >
                {style.bgmDucking ? '✓ ลดเสียงเพลงอัตโนมัติขณะพูด (Auto-Duck)' : 'ลดเสียงเพลงอัตโนมัติขณะพูด (Auto-Duck)'}
              </button>
              <p className="text-[11px] leading-relaxed text-slate-500">
                เปิดแล้วเพลงจะเบาลง ~12 dB ระหว่างมีเสียงพูด และค่อยๆ ดังกลับตอนเว้นวรรค
              </p>
            </div>

            <Row active={!style.bgmName} onClick={() => onStyleChange({ bgmName: null })}>
              <Music className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-sm text-slate-200">เสียงหลักของช่อง</span>
              {!style.bgmName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.music.map((m) => {
              const isPlayingThis = previewingAudio === `/api/media/${m.file?.rel_path}`;
              return (
                <Row
                  key={m.id}
                  active={style.bgmName === m.id}
                  onClick={() => onStyleChange({ bgmName: m.id })}
                  title={m.name}
                >
                  {m.file ? (
                    <button
                      type="button"
                      onClick={(e) => toggleAudioPreview(e, m.file.rel_path)}
                      className={`p-1 rounded-md transition-colors cursor-pointer mr-1 ${
                        isPlayingThis ? 'bg-[#25F4EE] text-black animate-pulse' : 'bg-white/[0.08] text-slate-300 hover:text-white hover:bg-white/[0.15]'
                      }`}
                      title={isPlayingThis ? 'หยุดฟัง' : 'ลองฟังเสียง'}
                    >
                      {isPlayingThis ? <Square className="h-3 w-3 fill-current" /> : <Play className="h-3 w-3 fill-current" />}
                    </button>
                  ) : (
                    <Music className="h-3.5 w-3.5 flex-shrink-0 text-slate-400 mr-1" />
                  )}
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-200">{m.label_th || m.name}</span>
                  {style.bgmName === m.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
                </Row>
              );
            })}

            <p className="px-1 pt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              เสียงเอฟเฟกต์ {selectedCaption ? '(ใส่ให้ท่อนที่เลือก)' : '(เลือกท่อนคำบรรยายก่อน)'}
            </p>
            {filtered.sfx.map((s) => {
              const isPlayingThis = previewingAudio === `/api/media/${s.file?.rel_path}`;
              return (
                <Row
                  key={s.id}
                  active={selectedCaption?.sfx === s.id}
                  onClick={() => selectedCaption && onAssignSfx(s.id)}
                  title={selectedCaption ? `ใส่ ${s.name}` : 'เลือกท่อนคำบรรยายบนไทม์ไลน์ก่อน'}
                >
                  {s.file ? (
                    <button
                      type="button"
                      onClick={(e) => toggleAudioPreview(e, s.file.rel_path)}
                      className={`p-1 rounded-md transition-colors cursor-pointer mr-1 ${
                        isPlayingThis ? 'bg-[#25F4EE] text-black animate-pulse' : 'bg-white/[0.08] text-slate-300 hover:text-white hover:bg-white/[0.15]'
                      }`}
                      title={isPlayingThis ? 'หยุดฟัง' : 'ลองฟังเสียง'}
                    >
                      {isPlayingThis ? <Square className="h-3 w-3 fill-current" /> : <Play className="h-3 w-3 fill-current" />}
                    </button>
                  ) : (
                    <Volume2 className={`h-3.5 w-3.5 flex-shrink-0 mr-1 ${selectedCaption ? 'text-slate-400' : 'text-slate-600'}`} />
                  )}
                  <span className={`min-w-0 flex-1 truncate text-sm ${selectedCaption ? 'text-slate-200' : 'text-slate-500'}`}>
                    {s.label_th || s.name}
                  </span>
                  {selectedCaption?.sfx === s.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
                </Row>
              );
            })}
          </>
        )}

        {/* TAB 4: TEXT / TEMPLATES & FONTS */}
        {tab === 'text' && (
          <div className="space-y-3">
            {/* Quick Add Default Text Button */}
            <button
              type="button"
              onClick={onAddTextAtPlayhead}
              className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-[#00D4FF] hover:brightness-110 text-black text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-[#25F4EE]/20 cursor-pointer transition-all active:scale-95"
            >
              <Plus className="w-4 h-4 text-black" />
              <span>เพิ่มข้อความที่หัวอ่าน (Default Text)</span>
            </button>

            {/* Search Input for Templates */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                value={textSearch}
                onChange={(e) => setTextSearch(e.target.value)}
                placeholder="ค้นหาเทมเพลตข้อความ..."
                className="w-full pl-8 pr-7 py-1.5 rounded-lg bg-black/40 border border-white/[0.1] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#25F4EE]"
              />
              {textSearch && (
                <button
                  type="button"
                  onClick={() => setTextSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>

            {/* Category Filter Pills */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1 no-scrollbar text-xs">
              {[
                { id: 'all', label: 'ทั้งหมด' },
                // Two different things were both called "hook": a punchy line
                // that keeps someone watching, and the product badge in the
                // first three seconds. They are separate rows now because
                // they are separate jobs -- and separate lanes on the timeline.
                { id: 'banner', label: '🏷️ ป้ายฮุก (แบรนด์)' },
                { id: 'hook', label: '🔥 ฮุคคำพูด' },
                { id: 'review', label: '⭐ รีวิว & ฟีเจอร์' },
                { id: 'sale', label: '🏷️ ดีล & โปรโมชั่น' },
                { id: 'cta', label: '🎯 พิกัด & CTA' },
                { id: 'minimal', label: '💎 มินิมอล & คลีน' },
              ].map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setTextCategory(cat.id)}
                  className={`px-2.5 py-1 rounded-full whitespace-nowrap text-[11px] font-semibold transition-all cursor-pointer ${
                    textCategory === cat.id
                      ? 'bg-[#25F4EE] text-black shadow-sm font-bold'
                      : 'bg-white/[0.06] text-slate-300 hover:bg-white/[0.12] hover:text-white'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* The banner's own looks. Picking one dresses the clip's hook
                overlay -- the left panel browses, the right panel edits, the
                same way it works for every other kind of overlay. */}
            {(textCategory === 'all' || textCategory === 'banner') && (
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(hookTemplates || {}).map(([key, tpl]) => (
                  <button
                    key={key}
                    type="button"
                    data-text-template-card="true"
                    onClick={() => onApplyHookTemplate?.(key)}
                    title={tpl.label_th}
                    className={`group flex flex-col gap-1.5 rounded-xl border p-2 text-left transition-all hover:-translate-y-0.5 cursor-pointer ${
                      activeHookTemplate === key
                        ? 'border-[#E6C24A] bg-[#E6C24A]/10 shadow-lg shadow-[#E6C24A]/20 ring-1 ring-[#E6C24A]/50'
                        : 'border-white/[0.08] bg-gradient-to-b from-[#18181B] to-[#0E0E10] hover:border-[#E6C24A]/60'
                    }`}
                  >
                    <div className="relative flex h-20 w-full flex-col items-center justify-center gap-0.5 overflow-hidden rounded-lg border border-white/[0.04] bg-black/60 p-1.5">
                      <div className="absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-black/70 to-transparent pointer-events-none" />
                      <div className={`w-full flex flex-col items-center justify-center gap-0.5 relative z-10 transition-transform duration-200 ${getMotionPreviewClass(tpl.motion)}`}>
                        {TIER_KEYS.map((tierKey, i) => (
                          <TextLookPreview
                            key={tierKey}
                            look={hookCardLook(tpl, tierKey)}
                            text={HOOK_CARD_SAMPLE[i]}
                            baseFsRatio={HOOK_FS_RATIO}
                            scale={0.19}
                          />
                        ))}
                      </div>
                      <span className="absolute top-1 right-1 px-1 py-0.2 text-[8px] font-mono font-bold rounded bg-black/70 text-[#E6C24A] border border-[#E6C24A]/30">
                        {(tpl.motion?.loop || tpl.motion?.in || '').toUpperCase()}
                      </span>
                    </div>
                    <span className="truncate text-[10px] font-semibold text-slate-300">
                      {tpl.label_th}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Visual Template Grid (2 columns like CapCut Text Effects) */}
            <div className="grid grid-cols-2 gap-2">
              {(textCategory === 'banner' ? [] : TEXT_TEMPLATES).filter((tpl) => {
                const matchesCat = textCategory === 'all' || tpl.category === textCategory;
                const matchesSearch = !textSearch.trim() || 
                  tpl.name.toLowerCase().includes(textSearch.toLowerCase()) || 
                  tpl.text.toLowerCase().includes(textSearch.toLowerCase());
                return matchesCat && matchesSearch;
              }).map((tpl) => {
                const isPreviewing = previewTextTemplate?.template_id === tpl.id;
                const isSelectedApplied = activeTextTemplateId === tpl.id;
                return (
                  <div
                    key={tpl.id}
                    data-text-template-card="true"
                    draggable={true}
                    onDragStart={(e) => {
                      e.dataTransfer.setData(TEXT_TEMPLATE_DRAG_TYPE, JSON.stringify(tpl));
                      e.dataTransfer.setData('text/plain', tpl.text);
                    }}
                    onClick={() => {
                      if (tpl.sfx) {
                        playSfxPreview(tpl.sfx);
                      }
                      if (onSelectTextTemplate) {
                        onSelectTextTemplate(tpl);
                      } else if (onAddTextTemplate) {
                        onAddTextTemplate(tpl);
                      } else if (onAddTextAtPlayhead) {
                        onAddTextAtPlayhead();
                      }
                    }}
                    className={`group relative flex flex-col items-center justify-between rounded-xl border p-2 cursor-pointer transition-all hover:-translate-y-0.5 ${
                      isSelectedApplied
                        ? 'border-[#25F4EE] bg-[#25F4EE]/10 shadow-lg shadow-[#25F4EE]/20 ring-1 ring-[#25F4EE]/50'
                        : isPreviewing
                        ? 'border-[#25F4EE] bg-gradient-to-b from-[#1c2e38] to-[#0E0E10] shadow-lg shadow-[#25F4EE]/20'
                        : 'border-white/[0.08] bg-gradient-to-b from-[#18181B] to-[#0E0E10] hover:border-[#25F4EE]/60 hover:shadow-lg hover:shadow-[#25F4EE]/10'
                    }`}
                    title={
                      isSelectedApplied
                        ? `สไตล์ปัจจุบันของข้อความที่เลือก: ${tpl.name}`
                        : `คลิกเพื่อดูตัวอย่างภาพและฟังเสียง: ${tpl.name} (${tpl.sfxLabel || tpl.sfx})`
                    }
                  >
                    {/* Visual Style Preview Card (CSS typography preview) */}
                    <div className="w-full h-20 rounded-lg bg-black/60 border border-white/[0.04] flex flex-col items-center justify-center p-1.5 overflow-hidden text-center select-none relative group-hover:bg-black/40 transition-colors">
                      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:8px_8px]" />
                      <TextLookPreview
                        look={templateLook(tpl)}
                        text={tpl.text}
                        scale={0.34}
                        className="relative z-10 max-w-full px-1 transition-transform duration-200 group-hover:scale-105"
                      />
                      {isPreviewing && (
                        <div className="absolute top-1 right-1 px-1.5 py-0.5 rounded bg-[#25F4EE] text-[9px] font-bold text-black shadow animate-pulse">
                          พรีวิว
                        </div>
                      )}
                      {/* Transition & SFX Micro-Badge */}
                      <div className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded bg-black/85 backdrop-blur text-[8.5px] font-medium text-slate-300 flex items-center gap-1 border border-white/[0.1] shadow-sm">
                        <span className="text-[#25F4EE] font-bold">{(tpl.anim || 'pop').toUpperCase()}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-amber-300 font-semibold truncate max-w-[68px]">🔊 {tpl.sfxLabel || tpl.sfx}</span>
                      </div>
                    </div>

                    {/* Template Meta / Add Icon */}
                    <div className="w-full mt-2 flex items-center justify-between gap-1">
                      <span className={`text-[11px] font-medium truncate ${isSelectedApplied || isPreviewing ? 'text-[#25F4EE] font-bold' : 'text-slate-300 group-hover:text-white'}`}>
                        {tpl.name}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (tpl.sfx) {
                            playSfxPreview(tpl.sfx);
                          }
                          if (onAddTextTemplate) {
                            onAddTextTemplate(tpl);
                          } else if (onAddTextAtPlayhead) {
                            onAddTextAtPlayhead();
                          }
                        }}
                        className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/[0.08] text-slate-300 hover:bg-[#25F4EE] hover:text-black hover:scale-110 active:scale-95 transition-all cursor-pointer"
                        title="ใส่ข้อความนี้ลงไทม์ไลน์"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Fonts Explorer Section */}
            <div className="pt-3 border-t border-white/[0.08]">
              <div className="flex items-center justify-between px-1 mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  ฟอนต์มาตรฐาน ({filtered.fonts.length})
                </span>
              </div>
              <div className="space-y-1">
                {filtered.fonts.map((f) => (
                  <Row key={f.id} active={style.fontName === f.id} onClick={() => onStyleChange({ fontName: f.id })}>
                    <Type className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />
                    <span
                      className="min-w-0 flex-1 truncate text-xs text-slate-200"
                      style={f.file ? { fontFamily: `'ed-${f.id}', sans-serif` } : undefined}
                    >
                      {f.name} · ก ข ค ABC
                    </span>
                    {style.fontName === f.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
                  </Row>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: STICKERS */}
        {tab === 'sticker' && (
          <>
            {style.stickerBadge ? (
              <div className="mb-2 space-y-2.5 rounded-xl border border-white/[0.08] bg-black/40 p-2.5">
                <div>
                  <span className="mb-1.5 block text-xs font-semibold text-slate-300">ตำแหน่งการวางป้าย</span>
                  <div className="grid grid-cols-3 gap-1">
                    {[
                      ['top_left', 'บนซ้าย'], ['top_center', 'กึ่งกลางบน'], ['top_right', 'บนขวา'],
                      ['bottom_left', 'ล่างซ้าย'], ['bottom_center', 'กึ่งกลางล่าง'], ['bottom_right', 'ล่างขวา'],
                    ].map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => onStyleChange({ stickerPosition: id })}
                        className={`rounded-lg border py-1.5 text-xs font-bold transition-all cursor-pointer ${
                          (style.stickerPosition || 'top_right') === id
                            ? 'border-[#25F4EE] bg-[#25F4EE]/20 text-[#25F4EE]'
                            : 'border-white/[0.08] bg-black/40 text-slate-400 hover:text-white'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="block">
                  <span className="mb-1 flex justify-between text-xs text-slate-300">
                    <span>ขนาดป้าย / สติกเกอร์</span>
                    <span className="font-mono text-[#25F4EE] font-bold">{Math.round((style.stickerScale ?? 1) * 100)}%</span>
                  </span>
                  <input
                    type="range" min={0.4} max={2} step={0.05}
                    value={style.stickerScale ?? 1}
                    onChange={(e) => onStyleChange({ stickerScale: parseFloat(e.target.value) })}
                    className="w-full accent-[#25F4EE]"
                  />
                </label>
              </div>
            ) : null}

            <Row active={!style.stickerBadge} onClick={() => onStyleChange({ stickerBadge: '' })}>
              <Sticker className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-sm text-slate-200">ไม่ใส่ป้าย / สติกเกอร์</span>
              {!style.stickerBadge && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.stickers.map((s) => (
              <Row
                key={s.id}
                active={style.stickerBadge === s.name || style.stickerBadge === s.id}
                onClick={() => onStyleChange({ stickerBadge: s.name })}
                title={s.name}
              >
                <img src={s.img_url} alt="" className="h-7 w-7 flex-shrink-0 rounded-md object-contain bg-black/40 p-0.5 border border-white/[0.06]" />
                <span className="min-w-0 flex-1 truncate text-sm text-slate-200">{s.name.replace(/\.(png|webp|jpg)$/i, '')}</span>
                {(style.stickerBadge === s.name || style.stickerBadge === s.id) && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}
            <p className="px-1 pt-2 text-xs leading-relaxed text-slate-500">
              พรีวิวสดจะแสดงป้ายบนจอวิดีโอทันที และเรนเดอร์เข้าไฟล์จริงด้วย FFmpeg Overlay
            </p>
          </>
        )}

        {/* TAB 6: LUTS / FILTERS */}
        {tab === 'filter' && (
          <>
            <Row active={!style.lutName} onClick={() => onStyleChange({ lutName: null })}>
              <Palette className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate text-sm text-slate-200">ไม่ใช้ (เร็วกว่า)</span>
              {!style.lutName && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
            </Row>
            {filtered.luts.map((l) => (
              <Row
                key={l.id}
                active={style.lutName === l.id}
                onClick={() => onStyleChange({ lutName: l.id })}
                title={l.name}
              >
                <Palette className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-sm text-slate-200">
                  {l.name.replace(/\.cube$/i, '')}
                </span>
                {style.lutName === l.id && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#25F4EE]" />}
              </Row>
            ))}
            {style.lutName && (
              <label className="block px-1 pt-2">
                <span className="mb-1 flex justify-between text-sm text-slate-400">
                  <span>ความเข้มฟิลเตอร์</span>
                  <span className="font-mono text-slate-300">{Math.round((style.lutIntensity ?? 1) * 100)}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={style.lutIntensity ?? 1}
                  onChange={(e) => onStyleChange({ lutIntensity: parseFloat(e.target.value) })}
                  className="w-full accent-[#D97757]"
                />
                <span className="block pt-1 text-xs leading-relaxed text-slate-500">
                  พรีวิวไม่แสดงฟิลเตอร์ — เห็นผลจริงหลังกด Apply
                </span>
              </label>
            )}
          </>
        )}
      </div>

      {/* Quick Video Preview Modal */}
      {previewVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#0D111A] p-4 shadow-2xl space-y-3">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2.5">
              <div className="flex items-center gap-2 min-w-0">
                <Film className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
                <span className="text-sm font-bold text-white truncate">{previewVideo.name}</span>
              </div>
              <button
                type="button"
                onClick={() => setPreviewVideo(null)}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.1] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="rounded-xl overflow-hidden bg-black flex items-center justify-center max-h-[55vh]">
              <video
                src={`/api/media/${previewVideo.rel_path || previewVideo.path}`}
                controls
                autoPlay
                className="max-h-[50vh] w-auto max-w-full rounded-lg"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-slate-400">
                ความยาว: {formatDuration(previewVideo.duration || durations?.[previewVideo.path] || durations?.[previewVideo.rel_path]) || 'ไม่ระบุ'}
                {previewVideo.size_mb ? ` · ${previewVideo.size_mb} MB` : ''}
              </span>
              <button
                type="button"
                onClick={() => {
                  onAddClip(previewVideo);
                  setPreviewVideo(null);
                }}
                className="py-1.5 px-3 rounded-xl bg-gradient-to-r from-[#25F4EE] to-blue-500 text-slate-950 text-xs font-bold flex items-center gap-1.5 hover:brightness-110 transition-all cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>เพิ่มลงในไทม์ไลน์</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
