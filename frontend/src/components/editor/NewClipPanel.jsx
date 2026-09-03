import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, Check, ChevronDown, ChevronRight, Film, Loader2, Package,
  Rocket, Sparkles, Upload, Volume2, FolderOpen, ArrowRight, Clock, Hourglass, CheckCircle2
} from 'lucide-react';
import { previewVoice, startRender, uploadFile, updateAngleVideos } from '../../api';
import { DEFAULT_STUDIO_FORM, STUDIO_FORM_KEY, getSavedStudioForm } from '../../lib/studioDefaults';
import { angleToForm, angleLabel } from '../../lib/angleToForm';
import { useRenderJob } from '../../hooks/useRenderJob';
import MediaPickerModal from '../MediaPickerModal';

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

// == GEMINI_VOICE_PRESETS in scripts/gemini_tts_engine.py. An id that is not
// in that map falls through to a default voice without complaining, so the
// picker would quietly play something else than it names.
const VOICE_PRESETS = [
  { id: 'gemini_puck_male_hype', label: '⚡ Puck — ชายพลังสูง สไตล์ TikTok' },
  { id: 'gemini_charon_male_pro', label: '🎙️ Charon — ชายทุ้มลึก น่าเชื่อถือ' },
  { id: 'gemini_kore_female_bright', label: '✨ Kore — หญิงสดใส ป้ายยาเก่ง' },
  { id: 'gemini_aoede_female_pro', label: '👑 Aoede — หญิงพรีเมียม นุ่มนวล' },
  { id: 'gemini_fenrir_male_strong', label: '🔥 Fenrir — ชายสตรอง คมเข้ม' },
];

// == AD_TONE_PRESETS in the same file.
const AD_TONES = [
  { id: 'commercial_premium', label: '📢 โฆษณาพรีเมียม' },
  { id: 'commercial_hype', label: '🔥 ป้ายยาไวรัล' },
  { id: 'commercial_aesthetic', label: '✨ มินิมอล ดูแพง' },
  { id: 'commercial_expert', label: '🎙️ ผู้เชี่ยวชาญ' },
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

function Section({ step, title, hint, children, done }) {
  return (
    <section className="rounded-2xl border border-white/[0.08] bg-black/40 p-3">
      <header className="mb-2 flex items-center gap-2">
        <span className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-base font-bold ${
          done ? 'bg-[#D97757] text-white' : 'bg-white/[0.06] text-slate-400'
        }`}>
          {done ? <Check className="h-4 w-4" /> : step}
        </span>
        <h3 className="text-lg font-bold text-white">{title}</h3>
        {hint && <span className="ml-auto text-sm text-[#9C968F]">{hint}</span>}
      </header>
      {children}
    </section>
  );
}

function Field({ label, value, onChange, placeholder, multiline }) {
  const Tag = multiline ? 'textarea' : 'input';
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-slate-400">{label}</span>
      <Tag
        value={value || ''}
        rows={multiline ? 4 : undefined}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="min-h-9 w-full resize-none rounded-lg border border-white/[0.08] bg-black/40 px-3 py-2 text-base text-white placeholder-slate-600 focus:border-[#D97757] focus:outline-none"
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
  const [showFields, setShowFields] = useState(!productContext);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [uploadPct, setUploadPct] = useState(null);
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
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
      setForm((prev) => ({
        ...prev,
        ...next,
        selectedVideo: next.selectedVideo || (next.selectedVideos && next.selectedVideos[0]) || '',
        selectedVideos: next.selectedVideos || (next.selectedVideo ? [next.selectedVideo] : [])
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productContext?.id, productContext?.title, angleIndex, angles.length, angles[angleIndex]?.selected_videos]);

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
        const found = videos.find(v => v.path === path || v.rel_path === path);
        if (found) return found;
        const name = path.split(/[/\\]/).pop();
        return { path, name };
      });
    }
    return videos;
  }, [angleAttachedVideos, videos]);

  // Project names come from the product name (pipeline.py), so two angles of
  // the same product would land in the same folder and overwrite each other.
  const projectName = useMemo(() => {
    const clean = (form.productName || 'สินค้า')
      .split('').filter((c) => /[\p{L}\p{N} _-]/u.test(c)).join('')
      .trim().replace(/\s+/g, '_');
    const base = `TikTok_${clean}`;
    if (!existingProjects.includes(base)) return base;
    // same product, another angle -> _a2, _a3 ...
    for (let n = 2; n < 30; n++) {
      const candidate = `${base}_a${n}`;
      if (!existingProjects.includes(candidate)) return candidate;
    }
    return `${base}_${Date.now().toString(36)}`;
  }, [form.productName, existingProjects]);

  const baseName = `TikTok_${(form.productName || '').trim().replace(/\s+/g, '_')}`;
  const willCreateVariant = projectName !== baseName && existingProjects.length > 0;

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
        text: form.hookTitle || form.productName,
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
    executeRender({
      project_name: projectName,
      product_name: form.productName,
      raw_video_path: form.selectedVideo,
      key_features: form.keyFeatures,
      pain_point: form.painPoint,
      price_deal: form.priceDeal,
      hook_title: form.hookTitle,
      custom_script: form.useCustomScript ? form.customScript : null,
      voice_mode: form.voiceMode,
      voice_gender: form.voiceGender,
      voice_preset: form.voicePreset,
      voice_rate: form.voiceSpeed,
      ad_tone: form.adTone || 'commercial_premium',
      human_voice_audio: null,
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
    <div className="h-full overflow-y-auto p-4 xl:p-6">
      <div className="mx-auto max-w-3xl space-y-3 xl:max-w-5xl xl:space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-[#D97757]" />
          <h2 className="text-2xl font-bold text-white">สร้างคลิปใหม่</h2>
          <span className="ml-auto font-mono text-sm text-[#9C968F]">{projectName}</span>
        </div>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2 xl:gap-4 xl:items-start">
        {/* ── 1. product + angle ── */}
        <Section step="1" title="สินค้า & มุมที่จะเล่า" done={!!form.productName} hint={productContext ? productContext.title : 'ยังไม่ได้เลือกสินค้า'}>
          {angles.length > 0 ? (
            <div className="space-y-2">
              {/* Locked/Assigned Angle from Product flow (No arbitrary dropdown) */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-slate-400">มุมที่ส่งมาตัดต่อ:</span>
                  <button
                    type="button"
                    onClick={onGoToProductFlow}
                    className="text-xs text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer font-bold transition-colors"
                    title="กลับไปเลือกมุมและคลิปที่หน้าสินค้า"
                  >
                    <span>เปลี่ยนมุมที่หน้าสินค้า</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex items-center gap-2 p-2.5 rounded-lg bg-black/50 border border-[#25F4EE]/30 shadow-inner">
                  <div className="w-2 h-2 rounded-full bg-[#25F4EE] animate-pulse flex-shrink-0" />
                  <span className="text-sm font-bold text-cyan-200 truncate">
                    {angleLabel(currentAngle || angles[angleIndex], angleIndex)}
                  </span>
                </div>
              </div>

              <div className="rounded-lg bg-white/[0.03] px-3 py-2.5 text-sm leading-relaxed text-slate-400 border border-white/[0.04]">
                <div className="truncate"><span className="text-[#9C968F] font-semibold">สินค้า:</span> {form.productName}</div>
                <div className="truncate"><span className="text-[#9C968F] font-semibold">Hook:</span> {form.hookTitle || '—'}</div>
                <div className="truncate"><span className="text-[#9C968F] font-semibold">ปัญหา:</span> {form.painPoint || '—'}</div>
              </div>
              <button
                type="button"
                onClick={() => setShowFields((v) => !v)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                {showFields ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                แก้ข้อความสคริปต์/Hook เอง
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-start gap-2 rounded-lg border border-[#5C4326] bg-[#2E2418] p-2">
                <Package className="h-3.5 w-3.5 flex-shrink-0 text-[#C08A5E]" />
                <p className="text-sm leading-relaxed text-[#D9BFA0]">
                  ยังไม่ได้เลือกมุมจากเมนู “สินค้า → คลิป” — กรุณาไปเลือกมุมและผูกคลิปที่หน้าสินค้าก่อนเพื่อความถูกต้อง
                </p>
              </div>
              <button
                type="button"
                onClick={onGoToProductFlow}
                className="h-9 w-full rounded-lg border border-[#25F4EE]/40 bg-[#25F4EE]/10 text-sm font-bold text-[#25F4EE] hover:bg-[#25F4EE]/20 cursor-pointer flex items-center justify-center gap-1.5 transition-all"
              >
                <Package className="w-3.5 h-3.5" />
                <span>ไปเลือกสินค้า & มุมที่หน้าสินค้า</span>
              </button>
            </div>
          )}

          {(showFields || angles.length === 0) && (
            <div className="mt-2 space-y-2">
              <Field label="ชื่อสินค้า" value={form.productName} onChange={(v) => patch({ productName: v })} placeholder="เช่น Esseger สายชาร์จแม่เหล็ก" />
              <Field label="Hook 3 วินาทีแรก" value={form.hookTitle} onChange={(v) => patch({ hookTitle: v })} placeholder="เช่น อย่าเพิ่งเลื่อนผ่าน!" />
              <Field label="ปัญหาที่ลูกค้าเจอ" value={form.painPoint} onChange={(v) => patch({ painPoint: v })} />
              <Field label="จุดเด่น" value={form.keyFeatures} onChange={(v) => patch({ keyFeatures: v })} multiline />
              <Field label="โปรโมชั่น / CTA" value={form.priceDeal} onChange={(v) => patch({ priceDeal: v })} />
            </div>
          )}
        </Section>

        {/* ── 2. footage ── */}
        <Section
          step="2"
          title="คลิปดิบ"
          done={!!form.selectedVideo || angleAttachedVideos.length > 0 || (videos.length > 0)}
          hint={
            form.selectedVideo
              ? `เลือก 1 คลิป (${(form.selectedVideo.split(/[/\\]/).pop())})`
              : (angleAttachedVideos.length > 0
                  ? `${displayVideos.length} ไฟล์ที่ผูกกับมุมนี้`
                  : (videos.length > 0 ? `ใช้คลิปทั้งหมดในคลัง (${videos.length} คลิป)` : 'ยังไม่มีคลิป'))
          }
        >
          <div className="max-h-40 space-y-1 overflow-y-auto">
            {displayVideos.map((v) => (
              <button
                key={v.path}
                type="button"
                onClick={() => patch({ selectedVideo: v.path })}
                className={`flex min-h-9 w-full items-center gap-2 rounded-lg border px-3 py-2 text-left transition-colors duration-150 cursor-pointer ${
                  form.selectedVideo === v.path
                    ? 'border-[#D97757] bg-[#D97757]/10 text-white'
                    : 'border-white/[0.08] bg-black/40 text-slate-300 hover:border-white/[0.2]'
                }`}
              >
                <Film className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-sm">{v.name}</span>
                {form.selectedVideo === v.path && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </button>
            ))}
            {displayVideos.length === 0 && (
              <p className="px-1 py-2 text-sm text-[#9C968F]">ยังไม่มีคลิปดิบ — เลือกจากคลังหรืออัปโหลดด้านล่าง</p>
            )}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <button
              type="button"
              onClick={() => setMediaPickerOpen(true)}
              className="flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg border border-[#25F4EE]/30 bg-[#25F4EE]/10 text-sm font-bold text-[#25F4EE] hover:bg-[#25F4EE]/20 transition-all cursor-pointer"
            >
              <FolderOpen className="h-3.5 w-3.5" />
              <span>เปิดคลังคลิป (Grid)</span>
            </button>
            <label
              className={`flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/[0.08] bg-black/40 text-sm font-bold text-slate-200 hover:text-white transition-all cursor-pointer ${
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
        </Section>
        </div>

        {/* ── 3. script ── */}
        <Section
          step="3"
          title="บทพูดพากย์"
          done={!!form.customScript}
          hint={
            form.customScript
              ? `${(form.customScript.split('\n').filter(Boolean).length)} ท่อน (${form.customScript.length} ตัวอักษร)`
              : 'ส่งบทมาจากหน้าสินค้า'
          }
        >
          <div className="space-y-2">
            <textarea
              rows={10}
              value={form.customScript || ''}
              onChange={(e) => patch({ customScript: e.target.value, useCustomScript: true })}
              placeholder="บทพูดจะถูกส่งมาจากมุมที่คุณเลือกในหน้าสินค้า..."
              className="w-full resize-none rounded-lg border border-white/[0.08] bg-black/40 px-3 py-2.5 text-base leading-relaxed text-white placeholder-slate-600 focus:border-[#25F4EE] focus:outline-none font-mono text-xs sm:text-sm"
            />
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="text-[#25F4EE] font-medium flex items-center gap-1">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>ใช้บทพูดจากมุมที่ส่งมา (สามารถปรับแก้ข้อความในกล่องได้)</span>
              </span>
              <span>{form.customScript ? `${form.customScript.length} ตัวอักษร` : ''}</span>
            </div>
          </div>
        </Section>

        {/* ── 4. advanced ── */}
        <section className="rounded-2xl border border-white/[0.08] bg-black/40">
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="flex w-full items-center gap-2 p-3 text-left cursor-pointer"
          >
            {showAdvanced ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
            <span className="text-lg font-bold text-white">ตั้งค่าเสียง & สไตล์</span>
            <span className="ml-auto text-sm text-[#9C968F]">ค่าเริ่มต้นใช้ได้เลย</span>
          </button>

          {showAdvanced && (
            <div className="space-y-2 border-t border-white/[0.08] p-3">
              <label className="block">
                <span className="mb-1 block text-sm text-slate-400">เสียงพากย์</span>
                <div className="flex gap-1">
                  <select
                    value={form.voicePreset}
                    onChange={(e) => patch({ voicePreset: e.target.value })}
                    className="h-9 min-w-0 flex-1 rounded-lg border border-white/[0.08] bg-black/40 px-3 text-base text-white focus:outline-none"
                  >
                    {VOICE_PRESETS.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
                  </select>
                  <button
                    type="button"
                    onClick={handlePreviewVoice}
                    disabled={voiceBusy}
                    title="ลองฟังเสียง"
                    className="flex h-9 w-10 flex-shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-black/40 text-slate-300 hover:text-white disabled:opacity-40 cursor-pointer"
                  >
                    {voiceBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Volume2 className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </label>

              <label className="block">
                <span className="mb-1 block text-sm text-slate-400">ฟอนต์ซับ</span>
                <select
                  value={form.fontName}
                  onChange={(e) => patch({ fontName: e.target.value })}
                  className="h-9 w-full rounded-lg border border-white/[0.08] bg-black/40 px-3 text-base text-white focus:outline-none"
                >
                  {FONTS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
                </select>
              </label>

              <label className="block">
                <span className="mb-1 block text-sm text-slate-400">โทนโฆษณา</span>
                <select
                  value={form.adTone || 'commercial_premium'}
                  onChange={(e) => patch({ adTone: e.target.value })}
                  className="h-9 w-full rounded-lg border border-white/[0.08] bg-black/40 px-3 text-base text-white focus:outline-none"
                >
                  {AD_TONES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.useAiVision !== false}
                  onChange={(e) => patch({ useAiVision: e.target.checked })}
                  className="h-[18px] w-[18px] flex-shrink-0 accent-[#D97757]"
                />
                ให้ AI ดูภาพเลือกช็อตให้ (ช้าลงเล็กน้อย แต่ตรงเนื้อหากว่า)
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.bilingualSubtitles !== false}
                  onChange={(e) => patch({ bilingualSubtitles: e.target.checked })}
                  className="h-[18px] w-[18px] flex-shrink-0 accent-[#D97757]"
                />
                ซับสองภาษา (ไทย + อังกฤษ)
              </label>

              <p className="text-xs leading-relaxed text-[#9C968F]">
                เพลง ฟิลเตอร์ ป้าย และหน้าตาซับ ปรับได้ละเอียดกว่านี้ในไทม์ไลน์หลังคลิปเสร็จ
              </p>
            </div>
          )}
        </section>

        {/* ── 5. create ── */}
        {willCreateVariant && (
          <p className="flex items-center gap-1.5 text-sm text-[#C08A5E]">
            <AlertCircle className="h-3 w-3 flex-shrink-0" />
            มีโปรเจกต์ชื่อ {baseName} อยู่แล้ว — อันนี้จะถูกสร้างเป็น {projectName} ไม่ทับของเดิม
          </p>
        )}
        {(renderError || aiError) && (
          <p className="flex items-start gap-1.5 text-sm text-[#E0A9A2]">
            <AlertCircle className="h-3 w-3 flex-shrink-0" />{renderError || aiError}
          </p>
        )}

        <button
          type="button"
          onClick={handleCreate}
          disabled={!!missing}
          title={missing || 'เริ่มสร้างคลิป'}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#D97757] text-base font-bold text-white transition-colors duration-150 hover:bg-[#C2683D] disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
        >
          <Rocket className="h-4 w-4" />
          สร้างคลิป
        </button>
        {missing && <p className="text-center text-sm text-[#9C968F]">{missing}</p>}
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
    </div>
  );
}
