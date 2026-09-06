import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import {
  AlertCircle, Check, ChevronDown, ChevronRight, Film, Loader2, Package,
  Rocket, Sparkles, Upload, Volume2, FolderOpen, ArrowRight, Clock, Hourglass, CheckCircle2, Play,
  FileText, Sliders, Mic2
} from 'lucide-react';
import { previewVoice, startRender, uploadFile, updateAngleVideos, updateAngleStatus } from '../../api';
import { DEFAULT_STUDIO_FORM, STUDIO_FORM_KEY, getSavedStudioForm } from '../../lib/studioDefaults';
import { angleToForm, angleLabel } from '../../lib/angleToForm';
import { isSameVideo, getMediaName } from '../../lib/mediaUrl';
import { buildProjectName, extractShortProductName, cleanAngleSlug } from '../../lib/projectName';
import { useRenderJob } from '../../hooks/useRenderJob';
import MediaPickerModal from '../MediaPickerModal';
import VoicePickerModal from '../VoicePickerModal';
import { guessBrandModel, newHookOverlay, templateForAdTone } from '../../lib/overlayModel';

function formatTime(seconds) {
  if (seconds == null || isNaN(seconds)) return '00:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatRemaining(seconds) {
  if (!seconds || seconds <= 5) return 'ใกล้เสร็จแล้ว...';
  if (seconds < 60) return `~${seconds} วินาที`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 15 ? `~${m} นาที ${s} วิ` : `~${m} นาที`;
}

// == GEMINI_VOICE_PRESETS in scripts/gemini_tts_engine.py.
const VOICE_PRESETS = [
  { id: 'gemini_puck_male_hype', label: 'Puck — ชายพลังสูง สไตล์ TikTok' },
  { id: 'gemini_charon_male_pro', label: 'Charon — ชายทุ้มลึก น่าเชื่อถือ' },
  { id: 'gemini_kore_female_bright', label: 'Kore — หญิงสดใส ป้ายยาเก่ง' },
  { id: 'gemini_aoede_female_pro', label: 'Aoede — หญิงพรีเมียม นุ่มนวล' },
  { id: 'gemini_fenrir_male_strong', label: 'Fenrir — ชายสตรอง คมเข้ม' },
];

// == AD_TONE_PRESETS in the same file.
const AD_TONES = [
  { id: 'commercial_premium', label: 'โฆษณาพรีเมียม' },
  { id: 'commercial_hype', label: 'ป้ายยาไวรัล' },
  { id: 'commercial_aesthetic', label: 'มินิมอล ดูแพง' },
  { id: 'commercial_expert', label: 'ผู้เชี่ยวชาญ' },
];

/** "+15%" -> 1.15 for the preview endpoint, which wants a float. */
function rateToSpeed(rate) {
  const m = String(rate || '').match(/(-?\d+)/);
  return m ? 1 + Number(m[1]) / 100 : 1.15;
}

const FONTS = [
  { id: 'IBMPlex', label: 'IBM Plex Sans Thai' },
  { id: 'Kanit', label: 'Kanit' },
  { id: 'Prompt', label: 'Prompt' },
  { id: 'NotoSansThai', label: 'Noto Sans Thai' },
];

/** Steps the backend reports, so the wait shows where it is rather than a bar. */
const RENDER_STEPS = ['เขียนบท', 'พากย์เสียง', 'ทำซับ', 'มิกซ์เสียง', 'เปิด Editor'];

function Section({ icon: Icon, title, hint, badgeText, children, done, className = '' }) {
  return (
    <section className={`rounded-2xl border border-white/[0.08] bg-[#0B0F19]/90 shadow-xl backdrop-blur-md p-4 sm:p-5 transition-all ${className}`}>
      <header className="mb-3.5 flex items-center justify-between gap-2 pb-2.5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5 min-w-0">
          {Icon && (
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 border ${
              done
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                : 'bg-white/[0.05] border-white/[0.08] text-[#E89274]'
            }`}>
              {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
            </div>
          )}
          <h3 className="text-base sm:text-lg font-bold text-white tracking-wide truncate font-kanit">{title}</h3>
        </div>
        {badgeText ? (
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-white/[0.06] text-slate-300 border border-white/[0.08] truncate max-w-[200px]">
            {badgeText}
          </span>
        ) : hint ? (
          <span className="text-xs text-slate-400 font-mono truncate max-w-[200px]">{hint}</span>
        ) : null}
      </header>
      {children}
    </section>
  );
}

function Field({ label, value, onChange, onBlur, placeholder, multiline }) {
  const Tag = multiline ? 'textarea' : 'input';
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-slate-400">{label}</span>
      <Tag
        value={value || ''}
        rows={multiline ? 3 : undefined}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        className="min-h-9 w-full resize-none rounded-xl border border-white/[0.08] bg-black/40 px-3 py-2 text-xs sm:text-sm text-slate-100 placeholder-slate-600 focus:border-[#25F4EE]/60 focus:ring-1 focus:ring-[#25F4EE]/30 focus:outline-none transition-all"
      />
    </label>
  );
}


export default function NewClipPanel({
  videos = [],
  productContext = null,
  angleIndex = 0,
  onAngleChange,
  existingProjects = [],
  onGoToProductFlow,
  onVideoUploaded,
  onCreated,
}) {
  const [form, setForm] = useState(() => getSavedStudioForm());
  // The product flow used to arrive with these collapsed, which is why the
  // banner was blank on nearly every first render: nobody opened them. They
  // stay open until the banner has something in it.
  const [showFields, setShowFields] = useState(
    () => !productContext || !(getSavedStudioForm().hookBrand || '').trim(),
  );
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [uploadPct, setUploadPct] = useState(null);
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [voicePickerOpen, setVoicePickerOpen] = useState(false);
  const [nameConflict, setNameConflict] = useState(null);
  const fileRef = useRef(null);

  const patch = (next) => setForm((prev) => ({ ...prev, ...next }));

  useEffect(() => {
    try {
      localStorage.setItem(STUDIO_FORM_KEY, JSON.stringify(form));
    } catch (err) { /* private mode: the form just will not be remembered */ }
  }, [form]);

  const {
    rendering, jobProjectName, jobStatus, progressPercent, displayPercent, elapsedSeconds, estimatedRemainingSeconds, renderError, executeRender,
  } = useRenderJob({
    onComplete: (result) => {
      const name = result?.project_name || result?.projectName;
      const targetAngle = currentAngle || angles[angleIndex];
      if (productContext?.id && targetAngle?.angle_id && name) {
        updateAngleStatus(productContext.id, targetAngle.angle_id, 'in_production', null, name).catch(() => {});
      }
      if (name) onCreated?.(name);
    },
  });

  // Fill the form from the angle the product flow produced. Re-runs when the
  // user switches angle, so the panel always reflects the current pick.
  const angles = productContext?.angles || [];
  const currentAngle = angles[angleIndex];

  useEffect(() => {
    const next = angleToForm(angles[angleIndex], productContext || {});
    if (next) {
      let resolvedVideo = next.selectedVideo || (next.selectedVideos && next.selectedVideos[0]) || '';
      let resolvedVideos = next.selectedVideos && next.selectedVideos.length > 0 ? next.selectedVideos : (resolvedVideo ? [resolvedVideo] : []);

      // If angle has selected_videos or selected_video directly
      const curAngle = angles[angleIndex];
      const angleVids = (curAngle?.selected_videos && curAngle.selected_videos.length > 0)
        ? curAngle.selected_videos
        : (curAngle?.selected_video ? [curAngle.selected_video] : []);

      if (!resolvedVideo && angleVids.length > 0) {
        resolvedVideo = angleVids[0];
        resolvedVideos = angleVids;
      }

      // Canonical match against available videos list if available
      if (resolvedVideo && videos.length > 0) {
        const found = videos.find(v => isSameVideo(v, resolvedVideo));
        if (found) {
          resolvedVideo = found.path || found.rel_path;
        }
      }

      setForm((prev) => ({
        ...prev,
        ...next,
        selectedVideo: resolvedVideo || prev.selectedVideo || '',
        selectedVideos: resolvedVideos.length > 0 ? resolvedVideos : (resolvedVideo ? [resolvedVideo] : prev.selectedVideos)
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productContext?.id, productContext?.title, angleIndex, angles.length, angles[angleIndex]?.selected_videos, angles[angleIndex]?.selected_video, videos]);

  const angleAttachedVideos = useMemo(() => {
    if (currentAngle?.selected_videos && currentAngle.selected_videos.length > 0) {
      return currentAngle.selected_videos;
    }
    if (currentAngle?.selected_video) {
      return [currentAngle.selected_video];
    }
    if (form.selectedVideos && form.selectedVideos.length > 0) {
      return form.selectedVideos;
    }
    return [];
  }, [currentAngle, form.selectedVideos]);

  const displayVideos = useMemo(() => {
    if (angleAttachedVideos.length > 0) {
      return angleAttachedVideos.map(path => {
        const found = videos.find(v => isSameVideo(v, path));
        if (found) return found;
        const name = getMediaName(path);
        return { path, name };
      });
    }
    return videos;
  }, [angleAttachedVideos, videos]);

  const isVideoSelected = useCallback((v) => {
    if (!v) return false;
    if (form.selectedVideo && isSameVideo(form.selectedVideo, v)) return true;
    if (Array.isArray(form.selectedVideos) && form.selectedVideos.some((sv) => isSameVideo(sv, v))) return true;
    if (!form.selectedVideo && displayVideos.length === 1 && angleAttachedVideos.length > 0) return true;
    return false;
  }, [form.selectedVideo, form.selectedVideos, displayVideos.length, angleAttachedVideos.length]);

  // Standard project name: [short_product]_[angle]_[1, 2, 3...]
  // Resolves the angle context and prevents cryptic duplicates or overwriting.
  const projectName = useMemo(() => {
    return buildProjectName({
      productName: form.productName,
      angle: currentAngle || (angles && angles[angleIndex]),
      angleIndex,
      existingProjects,
      productCode: productContext?.product_code || '',
    });
  }, [form.productName, currentAngle, angles, angleIndex, existingProjects, productContext?.product_code]);

  // The panel's footer reads both of these, but neither was ever declared --
  // rendering the panel threw "angleSpecificProject is not defined" and the
  // whole editor route fell through to the error boundary.
  //
  // The angle carries its own project once one has been created for it (the
  // same `project_name` ContentTrackerHub and EditorShell read).
  const angleSpecificProject = (currentAngle || angles[angleIndex])?.project_name || '';
  // Whether creating now would spawn a new variant (_2, _3, ...) rather than
  // the first-ever project for this product+angle: checked directly against
  // existingProjects (does the "_1" entry already exist?) instead of
  // pattern-matching projectName's own suffix, which broke the moment a
  // legitimately-named project happened to end in something other than "_1"
  // (or masked it when it did).
  const willCreateVariant = useMemo(() => {
    if (!projectName) return false;
    const angleForSlug = currentAngle || (angles && angles[angleIndex]);
    const codePart = (productContext?.product_code || '').trim().toUpperCase();
    const base = codePart
      ? `${codePart}-${cleanAngleSlug(angleForSlug, angleIndex)}`
      : `${extractShortProductName(form.productName)}_${cleanAngleSlug(angleForSlug, angleIndex)}`;
    const firstVariantName = `${base}_1`;
    return (existingProjects || []).some((p) => {
      const name = typeof p === 'string' ? p : (p && p.project_name) || '';
      return name === firstVariantName;
    });
  }, [projectName, currentAngle, angles, angleIndex, productContext?.product_code, form.productName, existingProjects]);

  const handleUpload = async (file) => {
    if (!file) return;
    const data = new FormData();
    data.append('file', file);
    setUploadPct(0);
    try {
      // /api/upload answers { message, file: get_file_info(...) }
      const res = await uploadFile(data, (pct) => setUploadPct(pct));
      const info = res?.file || res;
      if (info?.path) {
        patch({ selectedVideo: info.path });
        onVideoUploaded?.({ ...info, name: info.name || file.name });
      }
    } catch (err) {
      setAiError(err.friendlyMessage || 'อัปโหลดไม่สำเร็จ');
    } finally {
      setUploadPct(null);
    }
  };

  const handlePreviewVoice = async () => {
    setVoiceBusy(true);
    try {
      const res = await previewVoice({
        text: [form.hookBrand, form.hookModel, form.hookLabel].filter(Boolean).join(' ') || form.productName,
        // /api/voice/preview resolves the Gemini preset out of voice_gender;
        // sending "male" here auditions an Edge-TTS voice instead of the one
        // that is actually selected.
        voice_gender: form.voicePreset,
        speed: rateToSpeed(form.voiceSpeed),
        ad_tone: form.adTone,
      });
      const url = res?.audio_url || res?.url;
      if (url) new Audio(url).play().catch(() => {});
    } catch (err) {
      setAiError(err.friendlyMessage || 'ลองเสียงไม่สำเร็จ');
    } finally {
      setVoiceBusy(false);
    }
  };

  const missing = !form.selectedVideo
    ? 'เลือกคลิปดิบก่อน'
    : (!form.productName?.trim() ? 'ใส่ชื่อสินค้าก่อน' : null);

  const handleCreate = () => {
    if (missing || rendering) return;
    const selectedSources = Array.from(new Set([
      ...(Array.isArray(form.selectedVideos) ? form.selectedVideos : []),
      form.selectedVideo,
    ].filter(Boolean)));
    executeRender({
      project_name: projectName,
      product_name: form.productName,
      raw_video_path: form.selectedVideo,
      // Preserve every selected source for the AI draft. The first source is
      // retained as raw_video_path for backwards compatibility; the pipeline
      // uses clip_list when more than one source is supplied.
      clip_list: selectedSources.length > 1
        ? selectedSources.map((source_path) => ({ source_path, trim_start: 0, trim_end: null }))
        : null,
      key_features: form.keyFeatures,
      pain_point: form.painPoint,
      price_deal: form.priceDeal,
      hook_brand: form.hookBrand,
      hook_model: form.hookModel,
      hook_label: form.hookLabel,
      // The banner goes out as an overlay, already dressed. Its look follows
      // the narration tone the angle chose, so a first render stops landing
      // on 'tech' whatever the clip actually sounds like -- and whatever the
      // user picks in the editor afterwards still wins.
      overlays: [
        newHookOverlay({
          brand: form.hookBrand || guessBrandModel(form.productName).brand,
          model: form.hookModel || guessBrandModel(form.productName).model,
          label: form.hookLabel,
          template: templateForAdTone(form.adTone),
        }),
      ].filter(Boolean),
      custom_script: form.useCustomScript ? form.customScript : null,
      voice_mode: form.voiceMode,
      voice_gender: form.voiceGender,
      voice_preset: form.voicePreset,
      voice_rate: form.voiceSpeed,
      ad_tone: form.adTone || 'commercial_premium',
      human_voice_audio: null,
      product_id: productContext?.id || null,
      angle_id: (currentAngle?.angle_id || angles[angleIndex]?.angle_id) || null,
      font_name: form.fontName || 'IBMPlex',
      bilingual_subtitles: form.bilingualSubtitles !== false,
      use_ai_vision: form.useAiVision !== false,
      sticker_badge: form.stickerBadge || null,
      bgm_name: form.bgmName || null,
      lut_name: form.lutName || null,
      export_mp4: false,
      export_capcut: false,
    });
  };

  // ── rendering takes minutes; display live dynamic progress dashboard ──
  if (rendering) {
    const effectivePercent = Math.max(displayPercent || 0, progressPercent || 0);
    const stepIndex = Math.min(
      RENDER_STEPS.length - 1,
      Math.max(0, Math.floor((effectivePercent / 100) * RENDER_STEPS.length))
    );

    return (
      <div className="flex h-full items-center justify-center p-4 sm:p-6 overflow-y-auto">
        <div className="w-full max-w-lg space-y-5 rounded-3xl border border-white/[0.08] bg-[#0E1118]/90 p-6 sm:p-8 shadow-2xl backdrop-blur-xl text-center animate-fadeIn">
          {/* Circular Glowing Pulse with Big Number */}
          <div className="relative mx-auto w-28 h-28 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#D97757]/30 to-[#25F4EE]/30 blur-xl animate-pulse" />
            <div className="absolute inset-0 rounded-full border-2 border-dashed border-[#D97757]/40 animate-[spin_4s_linear_infinite]" />
            <div className="relative z-10 w-22 h-22 rounded-full bg-[#141824] border border-white/[0.1] shadow-2xl flex flex-col items-center justify-center">
              <span className="text-3xl font-black font-mono text-white tracking-tight">
                {effectivePercent}%
              </span>
              <span className="text-[10px] font-bold text-[#25F4EE] uppercase tracking-wider">กำลังรัน</span>
            </div>
          </div>

          {/* Project Title & Live Sub-Step Message */}
          <div className="space-y-2">
            <h3 className="text-base sm:text-lg font-extrabold text-white tracking-wide truncate">
              กำลังสร้าง {jobProjectName || projectName}
            </h3>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] shadow-inner text-xs font-semibold text-[#E89274] max-w-full">
              <span className="w-2 h-2 rounded-full bg-[#D97757] animate-ping flex-shrink-0" />
              <span className="truncate">{jobStatus?.message || jobStatus?.step_label || 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...'}</span>
            </div>
          </div>

          {/* Thick Glowing Progress Bar with Shimmer */}
          <div className="space-y-2 pt-1">
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-black/60 border border-white/[0.08] shadow-inner">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#D97757] via-[#FF8A65] to-[#25F4EE] transition-all duration-300 relative overflow-hidden"
                style={{ width: `${Math.max(4, effectivePercent)}%` }}
              >
                {/* Moving Sheen Light Wave */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent -translate-x-full animate-shimmer" />
              </div>
            </div>

            {/* Live Elapsed & Remaining Timers */}
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1 pt-0.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>เวลาที่ใช้: <strong className="text-white">{formatTime(elapsedSeconds)}</strong></span>
              </span>
              <span className="flex items-center gap-1.5">
                <Hourglass className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>คาดว่าเสร็จใน: <strong className="text-[#25F4EE]">{formatRemaining(estimatedRemainingSeconds)}</strong></span>
              </span>
            </div>
          </div>

          {/* Milestone Stepper with Badges */}
          <div className="grid grid-cols-5 gap-1.5 pt-2">
            {RENDER_STEPS.map((label, i) => {
              const isDone = i < stepIndex;
              const isCurrent = i === stepIndex;
              return (
                <div
                  key={label}
                  className={`flex flex-col items-center gap-0.5 p-2 rounded-xl border text-center transition-all ${
                    isDone
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : isCurrent
                      ? 'border-[#D97757]/80 bg-[#D97757]/20 text-[#E89274] ring-1 ring-[#D97757]/50 shadow-md scale-[1.02]'
                      : 'border-white/[0.04] bg-white/[0.02] text-slate-500'
                  }`}
                >
                  <div className="text-[10px] font-bold">
                    {isDone ? '✓ เสร็จ' : isCurrent ? '⚡ รันอยู่' : `${i + 1}`}
                  </div>
                  <span className="text-[11px] font-bold leading-tight truncate w-full">{label}</span>
                </div>
              );
            })}
          </div>

          {/* Safety & Background Note */}
          <p className="text-xs leading-relaxed text-slate-400 border-t border-white/[0.06] pt-3">
            💡 <span className="text-slate-300">สร้างเสียง ซับไตเติล และจัดช็อตตัดต่ออัตโนมัติ</span> · เมื่อเสร็จจะเปิดเข้าหน้า Editor เพื่อพรีวิวและปรับแต่งก่อนกดเรนเดอร์จริง
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 lg:p-8 bg-[#07090E]">
      <div className="mx-auto max-w-[1440px] space-y-5 animate-fadeIn">
        {/* ── Top Header Bar ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#D97757]/20 to-[#FF8A65]/10 border border-[#D97757]/30 flex items-center justify-center text-[#E89274] shadow-md shadow-[#D97757]/10">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-black text-white font-kanit tracking-tight">สร้างคลิปใหม่</h2>
              <p className="text-xs text-slate-400">ตรวจสอบบทพากย์ จัดการวัตถุดิบ และเริ่มตัดต่อเข้าสู่ไทม์ไลน์</p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className="text-xs text-slate-500 font-semibold">ชื่อโปรเจกต์:</span>
            <span className="px-2.5 py-1 rounded-lg bg-cyan-950/50 border border-cyan-800/40 text-cyan-300 font-mono text-xs font-bold shadow-inner truncate max-w-[320px]">
              {projectName}
            </span>
          </div>
        </div>

        {/* ── 2-Column Responsive Studio Layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-6 items-start">

          {/* ════════ LEFT COLUMN (Creative Core: Script & Audio Settings) ════════ */}
          <div className="lg:col-span-7 space-y-5">

            {/* 1. Voiceover Script Card */}
            <Section
              icon={FileText}
              title="บทพูดพากย์"
              done={!!form.customScript}
              badgeText={
                form.customScript
                  ? `${form.customScript.split('\n').filter(Boolean).length} ท่อน · ${form.customScript.length} ตัวอักษร`
                  : 'ยังไม่มีบทพูด'
              }
            >
              <div className="space-y-3">
                <div className="relative">
                  <textarea
                    rows={12}
                    value={form.customScript || ''}
                    onChange={(e) => patch({ customScript: e.target.value, useCustomScript: true })}
                    placeholder="บทพูดจะถูกส่งมาจากมุมที่คุณเลือกในหน้าสินค้า..."
                    className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/50 px-3.5 py-3 text-sm sm:text-base leading-relaxed text-slate-100 placeholder-slate-600 focus:border-[#25F4EE]/60 focus:ring-1 focus:ring-[#25F4EE]/30 focus:outline-none font-sans shadow-inner transition-all"
                  />
                  {form.customScript && (
                    <div className="absolute top-2.5 right-3 pointer-events-none">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-black/70 border border-white/[0.08] text-slate-300">
                        ~{Math.max(5, Math.round(form.customScript.length / 14))} วิ
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                  <span className="text-cyan-300 font-medium flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>ใช้บทพูดจากมุมที่ส่งมา (สามารถปรับแก้ไขข้อความได้อิสระ)</span>
                  </span>
                  <span className="font-mono text-slate-400">{form.customScript ? `${form.customScript.length} ตัวอักษร` : ''}</span>
                </div>
              </div>
            </Section>

            {/* 2. Audio & Style Card */}
            <Section
              icon={Sliders}
              title="ตั้งค่าเสียง & สไตล์"
              done={true}
              badgeText="ค่าเริ่มต้นพร้อมใช้"
            >
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {/* Voice Preset — opens VoicePickerModal */}
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold text-slate-300">เสียงพากย์ AI</span>
                    <button
                      type="button"
                      onClick={() => setVoicePickerOpen(true)}
                      className="h-10 w-full flex items-center gap-2.5 px-3 rounded-xl border border-white/[0.08] bg-black/40 text-xs sm:text-sm text-white hover:border-[#E89274]/50 hover:bg-[#E89274]/[0.05] cursor-pointer transition-all text-left"
                    >
                      <Mic2 className="h-4 w-4 flex-shrink-0 text-[#E89274]" />
                      <span className="flex-1 truncate">
                        {VOICE_PRESETS.find(v => v.id === form.voicePreset)?.label || 'เลือกเสียงพากย์'}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/[0.06] border border-white/[0.08] text-slate-400 flex-shrink-0">เลือก</span>
                    </button>
                    <p className="mt-1 text-[10px] text-slate-500">โทน: {AD_TONES.find(t => t.id === (form.adTone || 'commercial_premium'))?.label || '—'}</p>
                  </label>

                  {/* Subtitle Font */}
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold text-slate-300">ฟอนต์ซับไตเติล</span>
                    <select
                      value={form.fontName}
                      onChange={(e) => patch({ fontName: e.target.value })}
                      className="h-10 w-full rounded-xl border border-white/[0.08] bg-black/40 px-3 text-xs sm:text-sm text-white focus:border-[#25F4EE]/60 focus:outline-none cursor-pointer"
                    >
                      {FONTS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
                    </select>
                  </label>

                </div>


                {/* Toggles */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 border-t border-white/[0.06]">
                  <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-white/[0.06] bg-black/30 text-xs text-slate-300 hover:text-white cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={form.useAiVision !== false}
                      onChange={(e) => patch({ useAiVision: e.target.checked })}
                      className="h-4 w-4 rounded accent-[#D97757] cursor-pointer"
                    />
                    <span>ให้ AI ดูภาพเพื่อเลือกช็อตตัดต่อ</span>
                  </label>

                  <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-white/[0.06] bg-black/30 text-xs text-slate-300 hover:text-white cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={form.bilingualSubtitles !== false}
                      onChange={(e) => patch({ bilingualSubtitles: e.target.checked })}
                      className="h-4 w-4 rounded accent-[#D97757] cursor-pointer"
                    />
                    <span>ซับสองภาษา (ไทย + อังกฤษ)</span>
                  </label>
                </div>

                <p className="text-[11px] leading-relaxed text-slate-500 pt-1">
                  สามารถปรับแต่ง BGM, เสียงเอฟเฟกต์ (SFX), ป้ายสติกเกอร์ และฟิลเตอร์สีได้ละเอียดทุกช็อตในไทม์ไลน์
                </p>
              </div>
            </Section>
          </div>

          {/* ════════ RIGHT COLUMN (Context, Media & Action Dock) ════════ */}
          <div className="lg:col-span-5 space-y-5">

            {/* 3. Product & Angle Card */}
            <Section
              icon={Package}
              title="สินค้า & มุมที่จะเล่า"
              done={!!form.productName}
              badgeText={productContext ? productContext.title : 'ยังไม่ได้เลือกสินค้า'}
            >
              {angles.length > 0 ? (
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-slate-400">มุมที่ส่งมาตัดต่อ:</span>
                      <button
                        type="button"
                        onClick={onGoToProductFlow}
                        className="text-xs text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer font-bold transition-colors"
                        title="กลับไปเลือกมุมและคลิปที่หน้าสินค้า"
                      >
                        <span>เปลี่ยนมุม</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 rounded-xl bg-black/50 border border-[#25F4EE]/30 shadow-inner">
                      <div className="w-2 h-2 rounded-full bg-[#25F4EE] animate-pulse flex-shrink-0" />
                      <span className="text-xs sm:text-sm font-bold text-cyan-200 truncate">
                        {angleLabel(currentAngle || angles[angleIndex], angleIndex)}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl bg-white/[0.03] p-3 text-xs leading-relaxed text-slate-300 border border-white/[0.04] space-y-1.5">
                    <div className="truncate"><span className="text-slate-500 font-semibold">สินค้า:</span> <strong className="text-white">{form.productName}</strong></div>
                    <div className="truncate"><span className="text-slate-500 font-semibold">Hook:</span> {[form.hookBrand, form.hookModel, form.hookLabel].filter(Boolean).join(' · ') || '—'}</div>
                    <div className="truncate"><span className="text-slate-500 font-semibold">ปัญหา:</span> {form.painPoint || '—'}</div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowFields((v) => !v)}
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white cursor-pointer transition-colors"
                  >
                    {showFields ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    <span>{showFields ? 'ซ่อนการแก้ไขข้อมูลสินค้า' : 'แก้ไขข้อมูลสินค้า & Hook เพิ่มเติม'}</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3">
                    <Package className="h-4 w-4 flex-shrink-0 text-amber-400 mt-0.5" />
                    <p className="text-xs leading-relaxed text-amber-200">
                      ยังไม่ได้เลือกมุมจากเมนู “สินค้า → คลิป” — กรุณาไปเลือกมุมและผูกคลิปที่หน้าสินค้าก่อนเพื่อความแม่นยำ
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onGoToProductFlow}
                    className="h-10 w-full rounded-xl border border-[#25F4EE]/40 bg-[#25F4EE]/10 text-xs sm:text-sm font-bold text-[#25F4EE] hover:bg-[#25F4EE]/20 cursor-pointer flex items-center justify-center gap-1.5 transition-all"
                  >
                    <Package className="w-4 h-4" />
                    <span>ไปเลือกสินค้า & มุมที่หน้าสินค้า</span>
                  </button>
                </div>
              )}

              {(showFields || angles.length === 0) && (
                <div className="mt-3 space-y-2 pt-3 border-t border-white/[0.06]">
                  <Field
                    label="ชื่อสินค้า"
                    value={form.productName}
                    onChange={(v) => patch({ productName: v })}
                    onBlur={() => {
                      if (!form.hookBrand && !form.hookModel) {
                        const { brand, model } = guessBrandModel(form.productName);
                        if (brand || model) patch({ hookBrand: brand, hookModel: model });
                      }
                    }}
                    placeholder="เช่น Esseger สายชาร์จแม่เหล็ก"
                  />
                  <Field label="Header: แบรนด์" value={form.hookBrand} onChange={(v) => patch({ hookBrand: v })} placeholder="เช่น Logitech" />
                  <Field label="Header: รุ่น/โมเดล" value={form.hookModel} onChange={(v) => patch({ hookModel: v })} placeholder="เช่น Wave Keys" />
                  <Field label="Header: หมวดสินค้า" value={form.hookLabel} onChange={(v) => patch({ hookLabel: v })} placeholder="เช่น คีย์บอร์ดไร้สาย" />
                  <Field label="ปัญหาที่ลูกค้าเจอ" value={form.painPoint} onChange={(v) => patch({ painPoint: v })} />
                  <Field label="จุดเด่น" value={form.keyFeatures} onChange={(v) => patch({ keyFeatures: v })} multiline />
                  <Field label="โปรโมชั่น / CTA" value={form.priceDeal} onChange={(v) => patch({ priceDeal: v })} />
                </div>
              )}
            </Section>

            {/* 4. Raw Footage Card */}
            <Section
              icon={Film}
              title="คลิปดิบ (Footage)"
              done={!!form.selectedVideo || angleAttachedVideos.length > 0 || (videos.length > 0)}
              badgeText={
                form.selectedVideo
                  ? `เลือก 1 คลิป`
                  : (angleAttachedVideos.length > 0
                      ? `${displayVideos.length} ไฟล์ที่ผูกไว้`
                      : (videos.length > 0 ? `${videos.length} คลิปในคลัง` : 'ยังไม่มีคลิป'))
              }
            >
              <div className="space-y-3">
                <div className="max-h-44 space-y-1.5 overflow-y-auto pr-1">
                  {displayVideos.map((v) => {
                    const selected = isVideoSelected(v);
                    return (
                      <button
                        key={v.path || v.rel_path || v.name}
                        type="button"
                        onClick={() => {
                          const chosen = v.path || v.rel_path;
                          patch({ selectedVideo: chosen, selectedVideos: [chosen] });
                        }}
                        className={`flex min-h-10 w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left transition-all cursor-pointer ${
                          selected
                            ? 'border-[#D97757] bg-[#D97757]/15 text-white shadow-sm ring-1 ring-[#D97757]/30'
                            : 'border-white/[0.08] bg-black/40 text-slate-300 hover:border-white/[0.2] hover:bg-white/[0.02]'
                        }`}
                      >
                        <Film className={`h-4 w-4 flex-shrink-0 ${selected ? 'text-[#E89274]' : 'text-slate-500'}`} />
                        <span className="min-w-0 flex-1 truncate text-xs sm:text-sm font-medium">{v.name || getMediaName(v)}</span>
                        {selected && (
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            <span className="text-[10px] font-bold text-[#E89274] bg-[#D97757]/25 px-2 py-0.5 rounded-md">เลือกแล้ว</span>
                            <Check className="h-3.5 w-3.5 text-[#E89274]" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                  {displayVideos.length === 0 && (
                    <p className="px-1 py-3 text-xs text-slate-400 text-center bg-black/20 rounded-xl border border-dashed border-white/[0.08]">
                      ยังไม่มีคลิปดิบ — เลือกจากคลังหรืออัปโหลดคลิปใหม่
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setMediaPickerOpen(true)}
                    className="flex h-10 items-center justify-center gap-1.5 rounded-xl border border-[#25F4EE]/30 bg-[#25F4EE]/10 text-xs font-bold text-[#25F4EE] hover:bg-[#25F4EE]/20 transition-all cursor-pointer shadow-sm"
                  >
                    <FolderOpen className="h-3.5 w-3.5" />
                    <span>เปิดคลังคลิป</span>
                  </button>
                  <label
                    className={`flex h-10 items-center justify-center gap-1.5 rounded-xl border border-white/[0.1] bg-white/[0.04] text-xs font-bold text-slate-200 hover:text-white hover:bg-white/[0.08] transition-all cursor-pointer shadow-sm ${
                      uploadPct !== null ? 'opacity-50 pointer-events-none' : ''
                    }`}
                  >
                    <Upload className="h-3.5 w-3.5 text-[#25F4EE]" />
                    <span>{uploadPct !== null ? `อัปโหลด ${uploadPct}%` : 'อัปโหลดคลิปใหม่'}</span>
                    <input
                      ref={fileRef}
                      type="file"
                      accept="video/*,video/mp4,video/quicktime,video/webm,.mov,.mp4"
                      className="sr-only"
                      disabled={uploadPct !== null}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleUpload(file);
                        e.target.value = '';
                      }}
                    />
                  </label>
                </div>
              </div>
            </Section>

            {/* 5. Summary & Action Dock */}
            <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-[#0F1420]/95 to-[#090C12]/95 p-4 sm:p-5 shadow-2xl backdrop-blur-xl space-y-3.5 ring-1 ring-white/[0.04]">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-kanit">ความพร้อมก่อนสร้าง</span>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                  !missing ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                }`}>
                  {!missing ? 'พร้อมสร้างคลิป' : 'ข้อมูลยังไม่ครบ'}
                </span>
              </div>

              {/* Checklist Badges */}
              <div className="space-y-1.5 text-xs text-slate-300">
                <div className="flex items-center justify-between p-2 rounded-lg bg-black/40 border border-white/[0.04]">
                  <span className="text-slate-400">1. สินค้า & มุม:</span>
                  <span className={form.productName ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                    {form.productName ? 'ระบุแล้ว' : 'ยังไม่ระบุ'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-black/40 border border-white/[0.04]">
                  <span className="text-slate-400">2. คลิปดิบ:</span>
                  <span className={form.selectedVideo ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                    {form.selectedVideo ? 'เลือกแล้ว' : 'ยังไม่ได้เลือก'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-black/40 border border-white/[0.04]">
                  <span className="text-slate-400">3. สคริปต์บทพากย์:</span>
                  <span className={form.customScript ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                    {form.customScript ? `${form.customScript.length} ตัวอักษร` : 'ยังไม่มีบท'}
                  </span>
                </div>
              </div>

              {angleSpecificProject ? (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-xs text-[#C08A5E]">
                    <AlertCircle className="h-4 w-4 flex-shrink-0 text-amber-400" />
                    <span>มุมนี้มีโปรเจกต์ <strong>{angleSpecificProject}</strong> ในไทม์ไลน์อยู่แล้ว</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onCreated && onCreated(angleSpecificProject)}
                    className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/25 cursor-pointer transition-all"
                  >
                    <Play className="w-3.5 h-3.5 fill-white" />
                    <span>เปิดดูไทม์ไลน์ของมุมนี้</span>
                  </button>
                </div>
              ) : willCreateVariant ? (
                <p className="flex items-center gap-1.5 text-xs text-[#C08A5E]">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                  <span>จะถูกสร้างเป็นโปรเจกต์ใหม่: <strong>{projectName}</strong></span>
                </p>
              ) : null}

              {(renderError || aiError) && (
                <p className="flex items-start gap-1.5 text-xs text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                  <span>{renderError || aiError}</span>
                </p>
              )}

              {/* Main Submit Button */}
              <button
                type="button"
                onClick={handleCreate}
                disabled={!!missing}
                title={missing || 'เริ่มสร้างคลิป'}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#D97757] to-[#FF8A65] text-sm sm:text-base font-bold text-white transition-all shadow-lg shadow-[#D97757]/20 hover:brightness-110 hover:shadow-[#D97757]/30 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer active:scale-[0.98]"
              >
                <Rocket className="h-4 w-4" />
                <span>สร้างคลิป & เข้าสู่ไทม์ไลน์</span>
              </button>
              {missing && <p className="text-center text-xs text-amber-400/90">{missing}</p>}
            </div>

          </div>
        </div>
      </div>

      {/* ── Universal Media Picker Modal ── */}
      <MediaPickerModal
        isOpen={mediaPickerOpen}
        onClose={() => setMediaPickerOpen(false)}
        title={`เลือกคลิปสำหรับโปรเจกต์: ${form.productName || 'วิดีโอ'}`}
        productId={productContext?.id}
        productName={productContext?.title || form.productName}
        selectedVideos={form.selectedVideos && form.selectedVideos.length > 0 ? form.selectedVideos : (form.selectedVideo ? [form.selectedVideo] : [])}
        onConfirm={(paths) => {
          if (paths && paths.length > 0) {
            patch({ selectedVideo: paths[0], selectedVideos: paths });
            if (productContext?.id && angles[angleIndex]?.angle_id) {
              updateAngleVideos(productContext.id, angles[angleIndex].angle_id, paths).catch(() => {});
            }
          }
        }}
        isMultiSelect={true}
      />

      {/* ── Voice Picker Modal ── */}
      <VoicePickerModal
        isOpen={voicePickerOpen}
        onClose={() => setVoicePickerOpen(false)}
        selectedVoice={form.voicePreset}
        selectedTone={form.adTone || 'commercial_premium'}
        onSelect={({ voiceId, toneId }) => patch({ voicePreset: voiceId, adTone: toneId })}
      />
    </div>
  );
}
