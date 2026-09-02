import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, Check, ChevronDown, ChevronRight, Film, Loader2, Package,
  Rocket, Sparkles, Upload, Volume2, Wand2,
} from 'lucide-react';
import { generateAiScripts, previewVoice, startRender, uploadFile } from '../../api';
import { DEFAULT_STUDIO_FORM, STUDIO_FORM_KEY, getSavedStudioForm } from '../../lib/studioDefaults';
import { angleToForm, angleLabel } from '../../lib/angleToForm';
import { useRenderJob } from '../../hooks/useRenderJob';

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
const RENDER_STEPS = ['เขียนบท', 'พากย์เสียง', 'ทำซับ', 'มิกซ์เสียง', 'ตัดต่อ + เรนเดอร์'];

function Section({ step, title, hint, children, done }) {
  return (
    <section className="rounded-2xl border border-white/[0.08] bg-black/40 p-3">
      <header className="mb-2 flex items-center gap-2">
        <span className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg text-[11px] font-bold ${
          done ? 'bg-[#D97757] text-white' : 'bg-white/[0.06] text-slate-400'
        }`}>
          {done ? <Check className="h-3.5 w-3.5" /> : step}
        </span>
        <h3 className="text-xs font-bold text-white">{title}</h3>
        {hint && <span className="ml-auto text-[10px] text-slate-500">{hint}</span>}
      </header>
      {children}
    </section>
  );
}

function Field({ label, value, onChange, placeholder, multiline }) {
  const Tag = multiline ? 'textarea' : 'input';
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] text-slate-400">{label}</span>
      <Tag
        value={value || ''}
        rows={multiline ? 3 : undefined}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full resize-none rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] text-white placeholder-slate-600 focus:border-[#D97757] focus:outline-none"
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
  // Start from whatever was used last -- voice, font, tone and badge are
  // channel-level choices, and retyping them every clip was the old form's
  // job to avoid.
  const [form, setForm] = useState(() => getSavedStudioForm());
  const [showFields, setShowFields] = useState(!productContext);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiScripts, setAiScripts] = useState(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [uploadPct, setUploadPct] = useState(null);
  const [nameConflict, setNameConflict] = useState(null);
  const fileRef = useRef(null);

  const patch = (next) => setForm((prev) => ({ ...prev, ...next }));

  useEffect(() => {
    try {
      localStorage.setItem(STUDIO_FORM_KEY, JSON.stringify(form));
    } catch (err) { /* private mode: the form just will not be remembered */ }
  }, [form]);

  const {
    rendering, jobStatus, progressPercent, renderError, executeRender,
  } = useRenderJob({
    onComplete: (result) => {
      const name = result?.project_name || result?.projectName;
      if (name) onCreated?.(name);
    },
  });

  // Fill the form from the angle the product flow produced. Re-runs when the
  // user switches angle, so the panel always reflects the current pick.
  const angles = productContext?.angles || [];
  useEffect(() => {
    const next = angleToForm(angles[angleIndex], productContext || {});
    if (next) setForm((prev) => ({ ...prev, ...next }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productContext?.id, productContext?.title, angleIndex, angles.length]);

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

  const handleAiScript = async () => {
    setAiBusy(true);
    setAiError(null);
    try {
      const res = await generateAiScripts({
        product_name: form.productName,
        key_features: form.keyFeatures,
        pain_point: form.painPoint,
        price_deal: form.priceDeal,
      });
      setAiScripts(res?.angles || []);
    } catch (err) {
      setAiError(err.friendlyMessage || 'ขอบทจาก AI ไม่สำเร็จ');
    } finally {
      setAiBusy(false);
    }
  };

  const useAiAngle = (angle) => {
    const lines = Array.isArray(angle.script_lines) ? angle.script_lines.join('\n') : (angle.script_text || '');
    patch({
      customScript: lines,
      useCustomScript: true,
      hookTitle: angle.hook_title || form.hookTitle,
      ...(angle.ad_tone ? { adTone: angle.ad_tone } : null),
    });
    setAiScripts(null);
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
      export_mp4: true,
      export_capcut: false,
    });
  };

  // ── rendering takes minutes; the form is replaced by where it is up to ──
  if (rendering) {
    const stepIndex = Math.min(RENDER_STEPS.length - 1, Math.floor((progressPercent / 100) * RENDER_STEPS.length));
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="w-full max-w-md space-y-4 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-[#D97757]" />
          <div>
            <p className="text-sm font-bold text-white">กำลังสร้าง {projectName}</p>
            <p className="pt-1 text-[11px] text-slate-400">{jobStatus?.message || 'กำลังเตรียมข้อมูล...'}</p>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.08]">
            <div className="h-full bg-[#D97757] transition-all duration-500" style={{ width: `${Math.max(4, progressPercent)}%` }} />
          </div>
          <ol className="flex justify-between text-[9px]">
            {RENDER_STEPS.map((label, i) => (
              <li key={label} className={i <= stepIndex ? 'text-[#E89274]' : 'text-slate-600'}>{label}</li>
            ))}
          </ol>
          <p className="text-[10px] leading-relaxed text-slate-500">
            พากย์เสียงกับเรนเดอร์ใช้เวลา 2-4 นาทีบนเครื่องนี้ · ยกเลิกกลางคันไม่ได้ ปิดหน้านี้แล้วงานยังวิ่งต่อ
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="mx-auto max-w-2xl space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#D97757]" />
          <h2 className="text-sm font-bold text-white">สร้างคลิปใหม่</h2>
          <span className="ml-auto font-mono text-[10px] text-slate-500">{projectName}</span>
        </div>

        {/* ── 1. product + angle ── */}
        <Section step="1" title="สินค้า & มุมที่จะเล่า" done={!!form.productName} hint={productContext ? productContext.title : 'ยังไม่ได้เลือกสินค้า'}>
          {angles.length > 0 ? (
            <div className="space-y-2">
              <label className="block">
                <span className="mb-1 block text-[10px] text-slate-400">มุมที่จะเล่า ({angles.length} มุมจากเมนูสินค้า)</span>
                <select
                  value={angleIndex}
                  onChange={(e) => onAngleChange?.(parseInt(e.target.value, 10))}
                  className="w-full rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] text-white focus:border-[#D97757] focus:outline-none"
                >
                  {angles.map((a, i) => (
                    <option key={i} value={i}>{angleLabel(a, i)}</option>
                  ))}
                </select>
              </label>
              <div className="rounded-lg bg-white/[0.03] px-2 py-1.5 text-[10px] leading-relaxed text-slate-400">
                <div className="truncate"><span className="text-slate-500">สินค้า:</span> {form.productName}</div>
                <div className="truncate"><span className="text-slate-500">Hook:</span> {form.hookTitle || '—'}</div>
                <div className="truncate"><span className="text-slate-500">ปัญหา:</span> {form.painPoint || '—'}</div>
              </div>
              <button
                type="button"
                onClick={() => setShowFields((v) => !v)}
                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white cursor-pointer"
              >
                {showFields ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                แก้ข้อความเอง
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-start gap-2 rounded-lg border border-[#5C4326] bg-[#2E2418] p-2">
                <Package className="h-3.5 w-3.5 flex-shrink-0 text-[#C08A5E]" />
                <p className="text-[10px] leading-relaxed text-[#D9BFA0]">
                  ยังไม่ได้เลือกสินค้าจากเมนู “สินค้า → คลิป” — เลือกจากที่นั่นแล้วค่าทุกช่องจะเติมให้เอง หรือกรอกเองด้านล่างก็ได้
                </p>
              </div>
              <button
                type="button"
                onClick={onGoToProductFlow}
                className="w-full rounded-lg border border-white/[0.08] bg-black/40 py-1.5 text-[11px] font-bold text-slate-200 hover:text-white cursor-pointer"
              >
                ไปเลือกสินค้า
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
        <Section step="2" title="คลิปดิบ" done={!!form.selectedVideo} hint={`${videos.length} ไฟล์`}>
          <div className="max-h-40 space-y-1 overflow-y-auto">
            {videos.map((v) => (
              <button
                key={v.path}
                type="button"
                onClick={() => patch({ selectedVideo: v.path })}
                className={`flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors duration-150 cursor-pointer ${
                  form.selectedVideo === v.path
                    ? 'border-[#D97757] bg-[#D97757]/10 text-white'
                    : 'border-white/[0.08] bg-black/40 text-slate-300 hover:border-white/[0.2]'
                }`}
              >
                <Film className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate text-[11px]">{v.name}</span>
                {form.selectedVideo === v.path && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[#E89274]" />}
              </button>
            ))}
            {videos.length === 0 && (
              <p className="px-1 py-2 text-[10px] text-slate-500">ยังไม่มีคลิปดิบ — อัปโหลดด้านล่าง</p>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="video/*,image/*"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files?.[0])}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploadPct !== null}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/[0.08] bg-black/40 py-1.5 text-[11px] font-bold text-slate-200 hover:text-white disabled:opacity-50 cursor-pointer"
          >
            <Upload className="h-3.5 w-3.5" />
            {uploadPct !== null ? `กำลังอัปโหลด ${uploadPct}%` : 'อัปโหลดคลิปใหม่'}
          </button>
        </Section>

        {/* ── 3. script ── */}
        <Section step="3" title="บทพูด" done={!!form.customScript} hint={form.useCustomScript ? 'ใช้บทนี้' : 'ให้ระบบเขียนเอง'}>
          <div className="space-y-2">
            <button
              type="button"
              onClick={handleAiScript}
              disabled={aiBusy || !form.productName}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[#D97757]/40 bg-[#D97757]/10 py-1.5 text-[11px] font-bold text-[#E89274] hover:bg-[#D97757]/20 disabled:opacity-40 cursor-pointer"
            >
              {aiBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
              {aiBusy ? 'กำลังเขียน...' : 'ให้ AI เขียนบทให้'}
            </button>

            {aiScripts && (
              <div className="space-y-1">
                <p className="text-[10px] text-slate-400">เลือก 1 มุม:</p>
                {aiScripts.map((a, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => useAiAngle(a)}
                    className="w-full rounded-lg border border-white/[0.08] bg-black/40 p-2 text-left hover:border-[#D97757] cursor-pointer"
                  >
                    <div className="text-[11px] font-bold text-white">{a.angle_name || `มุมที่ ${i + 1}`}</div>
                    <div className="truncate pt-0.5 text-[10px] text-slate-400">
                      {(Array.isArray(a.script_lines) ? a.script_lines[0] : a.script_text) || ''}
                    </div>
                  </button>
                ))}
              </div>
            )}

            <textarea
              rows={6}
              value={form.customScript || ''}
              onChange={(e) => patch({ customScript: e.target.value, useCustomScript: true })}
              placeholder="บทจะเติมให้เองเมื่อเลือกมุมจากเมนูสินค้า หรือกดปุ่ม AI ด้านบน"
              className="w-full resize-none rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] leading-relaxed text-white placeholder-slate-600 focus:border-[#D97757] focus:outline-none"
            />
            <label className="flex items-center gap-2 text-[10px] text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={!!form.useCustomScript}
                onChange={(e) => patch({ useCustomScript: e.target.checked })}
                className="accent-[#D97757]"
              />
              พูดตามบทนี้ (ปิด = ให้ระบบเขียนบทจากจุดเด่นเอง)
            </label>
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
            <span className="text-xs font-bold text-white">ตั้งค่าเสียง & สไตล์</span>
            <span className="ml-auto text-[10px] text-slate-500">ค่าเริ่มต้นใช้ได้เลย</span>
          </button>

          {showAdvanced && (
            <div className="space-y-2 border-t border-white/[0.08] p-3">
              <label className="block">
                <span className="mb-1 block text-[10px] text-slate-400">เสียงพากย์</span>
                <div className="flex gap-1">
                  <select
                    value={form.voicePreset}
                    onChange={(e) => patch({ voicePreset: e.target.value })}
                    className="min-w-0 flex-1 rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] text-white focus:outline-none"
                  >
                    {VOICE_PRESETS.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
                  </select>
                  <button
                    type="button"
                    onClick={handlePreviewVoice}
                    disabled={voiceBusy}
                    title="ลองฟังเสียง"
                    className="flex h-[30px] w-9 flex-shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-black/40 text-slate-300 hover:text-white disabled:opacity-40 cursor-pointer"
                  >
                    {voiceBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Volume2 className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </label>

              <label className="block">
                <span className="mb-1 block text-[10px] text-slate-400">ฟอนต์ซับ</span>
                <select
                  value={form.fontName}
                  onChange={(e) => patch({ fontName: e.target.value })}
                  className="w-full rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] text-white focus:outline-none"
                >
                  {FONTS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
                </select>
              </label>

              <label className="block">
                <span className="mb-1 block text-[10px] text-slate-400">โทนโฆษณา</span>
                <select
                  value={form.adTone || 'commercial_premium'}
                  onChange={(e) => patch({ adTone: e.target.value })}
                  className="w-full rounded-lg border border-white/[0.08] bg-black/40 px-2 py-1.5 text-[11px] text-white focus:outline-none"
                >
                  {AD_TONES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </label>

              <label className="flex items-center gap-2 text-[10px] text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.useAiVision !== false}
                  onChange={(e) => patch({ useAiVision: e.target.checked })}
                  className="accent-[#D97757]"
                />
                ให้ AI ดูภาพเลือกช็อตให้ (ช้าลงเล็กน้อย แต่ตรงเนื้อหากว่า)
              </label>

              <label className="flex items-center gap-2 text-[10px] text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.bilingualSubtitles !== false}
                  onChange={(e) => patch({ bilingualSubtitles: e.target.checked })}
                  className="accent-[#D97757]"
                />
                ซับสองภาษา (ไทย + อังกฤษ)
              </label>

              <p className="text-[9px] leading-relaxed text-slate-500">
                เพลง ฟิลเตอร์ ป้าย และหน้าตาซับ ปรับได้ละเอียดกว่านี้ในไทม์ไลน์หลังคลิปเสร็จ
              </p>
            </div>
          )}
        </section>

        {/* ── 5. create ── */}
        {willCreateVariant && (
          <p className="flex items-center gap-1.5 text-[10px] text-[#C08A5E]">
            <AlertCircle className="h-3 w-3 flex-shrink-0" />
            มีโปรเจกต์ชื่อ {baseName} อยู่แล้ว — อันนี้จะถูกสร้างเป็น {projectName} ไม่ทับของเดิม
          </p>
        )}
        {(renderError || aiError) && (
          <p className="flex items-start gap-1.5 text-[10px] text-[#E0A9A2]">
            <AlertCircle className="h-3 w-3 flex-shrink-0" />{renderError || aiError}
          </p>
        )}

        <button
          type="button"
          onClick={handleCreate}
          disabled={!!missing}
          title={missing || 'เริ่มสร้างคลิป'}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#D97757] py-2.5 text-sm font-bold text-white transition-colors duration-150 hover:bg-[#C2683D] disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
        >
          <Rocket className="h-4 w-4" />
          สร้างคลิป
        </button>
        {missing && <p className="text-center text-[10px] text-slate-500">{missing}</p>}
      </div>
    </div>
  );
}
