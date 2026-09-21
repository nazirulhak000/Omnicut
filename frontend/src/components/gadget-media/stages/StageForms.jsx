import React, { useState } from 'react';
import {
  AlertTriangle, CheckCircle2, ExternalLink, FileCheck2, Loader2, Plus,
  Mic2, RefreshCw, Save, Scissors, ShieldCheck, Sparkles, Trash2, Video,
} from 'lucide-react';

import { toMediaUrl } from '../../../lib/mediaUrl.js';
import {
  canRenderProject,
  FACT_TYPE_OPTIONS,
  formatDuration,
  newEdlShot,
  newFact,
  newStoryBlock,
  STORY_ROLE_OPTIONS,
} from '../../../lib/gadgetMediaProject.js';
import GadgetMediaTimelineHost from '../timeline/GadgetMediaTimelineHost.jsx';


const REQUIRED_ROLES = new Set(['hook', 'hero_benefit', 'proof', 'caveat', 'verdict']);


export function BriefStage({ project, busy, onSave }) {
  const [draft, setDraft] = useState({
    product_identity: project.product_identity,
    audience: project.audience || '',
    editorial_promise: project.editorial_promise || '',
    presentation: {
      mode: 'gemini_tts', voice: 'gemini_puck_male_hype', ad_tone: 'commercial_expert', speed: 1.15,
      ...(project.presentation || {}),
    },
  });
  const save = () => onSave({ ...draft, ...(project.status === 'brief' ? { status: 'sourcing' } : {}) });
  return (
    <StageSection title="Brief ของคลิป" description="ล็อกสินค้าเพียงหนึ่งรุ่น คนดู และประโยชน์หลักก่อนเริ่มหา Source">
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Brand" value={draft.product_identity.brand || ''} onChange={(value) => setDraft((current) => ({ ...current, product_identity: { ...current.product_identity, brand: value } }))} />
        <TextField label="Model" value={draft.product_identity.model || ''} onChange={(value) => setDraft((current) => ({ ...current, product_identity: { ...current.product_identity, model: value } }))} />
        <TextField label="Category" value={draft.product_identity.category || ''} onChange={(value) => setDraft((current) => ({ ...current, product_identity: { ...current.product_identity, category: value } }))} />
        <TextField label="Variant" value={draft.product_identity.variant || ''} onChange={(value) => setDraft((current) => ({ ...current, product_identity: { ...current.product_identity, variant: value } }))} />
      </div>
      <TextArea label="คนดูหลัก" value={draft.audience} onChange={(value) => setDraft((current) => ({ ...current, audience: value }))} placeholder="เขากำลังเลือกอะไร และกังวลเรื่องไหน" />
      <TextArea label="คำสัญญาของคลิป" value={draft.editorial_promise} onChange={(value) => setDraft((current) => ({ ...current, editorial_promise: value }))} placeholder="ดูจบแล้วคนดูจะเข้าใจหรือตัดสินใจอะไรได้" />
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs font-bold text-slate-300">รูปแบบการนำเสนอ
          <select value={draft.presentation.mode || 'gemini_tts'} onChange={(event) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, mode: event.target.value } }))} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70">
            <option value="gemini_tts">เปิดหน้า + Gemini TTS</option>
            <option value="creator_voice">หน้าและเสียง Creator</option>
            <option value="product_only">Product-only</option>
          </select>
        </label>
        {draft.presentation.mode === 'gemini_tts' ? (
          <label className="text-xs font-bold text-slate-300">Gemini Voice
            <select value={draft.presentation.voice || 'gemini_puck_male_hype'} onChange={(event) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, voice: event.target.value } }))} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70">
              <option value="gemini_puck_male_hype">Puck · ชายพลังสูง</option>
              <option value="gemini_charon_male_pro">Charon · ชายทุ้มน่าเชื่อถือ</option>
              <option value="gemini_kore_female_bright">Kore · หญิงสดใส</option>
              <option value="gemini_aoede_female_pro">Aoede · หญิงพรีเมียม</option>
              <option value="gemini_fenrir_male_strong">Fenrir · ชายคมเข้ม</option>
            </select>
          </label>
        ) : <TextField label="หมายเหตุเสียง Creator" value={draft.presentation.voice || ''} onChange={(value) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, voice: value } }))} />}
      </div>
      {draft.presentation.mode === 'gemini_tts' && (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-xs font-bold text-slate-300">น้ำเสียงโฆษณา
            <select value={draft.presentation.ad_tone || 'commercial_expert'} onChange={(event) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, ad_tone: event.target.value } }))} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70">
              <option value="commercial_expert">Tech Expert</option>
              <option value="commercial_premium">Premium</option>
              <option value="commercial_hype">Viral Hype</option>
              <option value="commercial_aesthetic">Aesthetic</option>
            </select>
          </label>
          <label className="text-xs font-bold text-slate-300">ความเร็วเสียง
            <input type="number" min="0.75" max="1.5" step="0.05" value={draft.presentation.speed || 1.15} onChange={(event) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, speed: Number(event.target.value) } }))} className="mt-1.5 h-10 w-full rounded-xl bg-black/25 px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70" />
          </label>
        </div>
      )}
      {draft.presentation.mode !== 'product_only' && <TextField label="ไฟล์เสียงใน Product Project" value={draft.presentation.audio_path || ''} onChange={(value) => setDraft((current) => ({ ...current, presentation: { ...current.presentation, audio_path: value } }))} placeholder={draft.presentation.mode === 'gemini_tts' ? 'ระบบจะเติมให้อัตโนมัติหลังสร้าง Gemini TTS' : 'เช่น audio/voice/creator.wav'} />}
      <ActionBar busy={busy} onClick={save} label={project.status === 'brief' ? 'บันทึกและไป Sources' : 'บันทึก Brief'} />
    </StageSection>
  );
}


export function SourcesStage({ project, busy, onProbe, onAdvance }) {
  const productKey = `${project.product_identity.brand || ''} ${project.product_identity.model || ''}`.trim().toLowerCase();
  const [form, setForm] = useState({
    local_path: '', source_url: '', creator_or_brand: project.product_identity.brand || '',
    rights_basis: 'licensed_press_kit', rights_reviewed: false, usage_note: '', product_key: productKey,
  });
  const [probing, setProbing] = useState(false);
  const [error, setError] = useState('');
  const sources = project.source_assets || [];
  const ready = sources.length > 0 && sources.every((source) => (
    Math.max(Number(source.width || 0), Number(source.height || 0)) >= 1920
    && Math.min(Number(source.width || 0), Number(source.height || 0)) >= 1080
    && source.rights_reviewed
  ));

  const probe = async () => {
    setProbing(true);
    setError('');
    try {
      await onProbe(form);
      setForm((current) => ({ ...current, local_path: '', source_url: '', usage_note: '', rights_reviewed: false }));
    } catch (probeError) {
      setError(probeError?.response?.data?.detail || probeError?.message || 'ตรวจ Source ไม่สำเร็จ');
    } finally {
      setProbing(false);
    }
  };

  return (
    <StageSection title="Source Vault" description="ลงทะเบียนไฟล์จริงแล้วให้ ffprobe ตรวจ Resolution, FPS, Duration, Codec และ Audio ก่อนเข้า Timeline">
      <div className="overflow-hidden rounded-2xl bg-black/20 ring-1 ring-white/[0.07]">
        {sources.length === 0 ? <p className="px-4 py-8 text-center text-sm text-slate-500">ยังไม่มี Source ใน Project นี้</p> : (
          <ul className="divide-y divide-white/[0.06]">
            {sources.map((source) => {
              const native = Math.max(source.width || 0, source.height || 0) >= 1920 && Math.min(source.width || 0, source.height || 0) >= 1080 && !source.upscaled;
              return (
                <li key={source.source_id} className="grid gap-2 px-4 py-3 md:grid-cols-[minmax(0,1fr)_130px_120px] md:items-center">
                  <span className="min-w-0"><span className="block truncate text-xs font-bold text-white">{source.local_path || source.source_url}</span><span className="mt-1 block text-[10px] text-slate-500">{source.creator_or_brand || 'ไม่ระบุผู้สร้าง'} · {source.codec || 'ยังไม่ระบุ Codec'}</span></span>
                  <span className={`text-xs font-bold ${native ? 'text-emerald-300' : 'text-rose-300'}`}>{source.width || 0}×{source.height || 0} · {source.fps || 0} FPS</span>
                  <span className={`flex items-center gap-1.5 text-xs font-bold ${source.rights_reviewed ? 'text-emerald-300' : 'text-amber-200'}`}>{source.rights_reviewed ? <ShieldCheck className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}{source.rights_reviewed ? 'สิทธิ์ผ่าน' : 'รอตรวจสิทธิ์'}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="rounded-2xl bg-white/[0.025] p-4 ring-1 ring-white/[0.07]">
        <h3 className="text-sm font-black text-white">เพิ่ม Source จากไฟล์ใน Workspace</h3>
        {error && <p className="mt-2 text-xs text-rose-200">{error}</p>}
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <TextField label="Path ของไฟล์" value={form.local_path} onChange={(value) => setForm((current) => ({ ...current, local_path: value }))} placeholder="01_Raw/GadgetMedia/สินค้า/original/video.mp4" />
          <TextField label="Source URL" value={form.source_url} onChange={(value) => setForm((current) => ({ ...current, source_url: value }))} placeholder="หน้า Official หรือ Press kit" />
          <TextField label="Brand / Creator" value={form.creator_or_brand} onChange={(value) => setForm((current) => ({ ...current, creator_or_brand: value }))} />
          <label className="text-xs font-bold text-slate-300">สิทธิ์การใช้
            <select value={form.rights_basis} onChange={(event) => setForm((current) => ({ ...current, rights_basis: event.target.value }))} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1]">
              <option value="licensed_press_kit">Licensed Press Kit</option><option value="self_recorded">ถ่ายเอง</option><option value="commentary_excerpt">Commentary Excerpt</option><option value="original_ai_visual">Original AI Visual</option>
            </select>
          </label>
          <TextField label="หมายเหตุการใช้" value={form.usage_note} onChange={(value) => setForm((current) => ({ ...current, usage_note: value }))} placeholder="ใช้เป็นภาพ Proof พร้อม Voiceover ของช่อง" />
        </div>
        <label className="mt-3 flex cursor-pointer items-start gap-2 text-xs leading-5 text-slate-300">
          <input type="checkbox" checked={form.rights_reviewed} onChange={(event) => setForm((current) => ({ ...current, rights_reviewed: event.target.checked }))} className="mt-1" />
          <span>ตรวจสิทธิ์และเงื่อนไขการใช้งานแล้ว พร้อมบันทึกหลักฐานไว้กับ Project</span>
        </label>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[11px] text-slate-500">ไฟล์ต่ำกว่า Native 1080p ยังเก็บเป็น Reference ได้ แต่ Quality Gate จะไม่ให้เป็น Approved Master</p>
          <button type="button" onClick={probe} disabled={probing || !form.local_path.trim()} className="flex h-10 items-center gap-2 rounded-xl bg-cyan-300 px-4 text-xs font-black text-[#061116] disabled:opacity-50">{probing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Video className="h-4 w-4" />} ตรวจและเพิ่ม Source</button>
        </div>
      </div>

      {project.status === 'sourcing' && <ActionBar busy={busy} onClick={() => onAdvance('source_ready')} disabled={!ready} label="ยืนยัน Sources พร้อม" hint={!ready ? 'ต้องมี Native 1080p และสิทธิ์ผ่านทุกไฟล์ที่จะใช้' : ''} />}
    </StageSection>
  );
}


export function EvidenceStage({ project, busy, onSave }) {
  const [facts, setFacts] = useState(project.facts || []);
  const ready = facts.length > 0 && facts.every((fact) => fact.type === 'opinion' || (fact.evidence_refs || []).length > 0) && facts.every((fact) => fact.text?.trim());
  const patch = (id, changes) => setFacts((current) => current.map((fact) => fact.fact_id === id ? { ...fact, ...changes } : fact));
  const save = () => onSave({ facts, ...(project.status === 'source_ready' ? { status: 'research_ready' } : {}) });
  return (
    <StageSection title="Evidence Board" description="แยก Brand claim, Verified fact, Opinion และ Caveat ให้ย้อนกลับไปหา Source ได้ทุกข้อ">
      <div className="space-y-3">
        {facts.map((fact, index) => (
          <div key={fact.fact_id} className="grid gap-3 rounded-2xl bg-white/[0.025] p-4 ring-1 ring-white/[0.07] lg:grid-cols-[160px_minmax(0,1fr)_minmax(180px,0.8fr)_40px] lg:items-end">
            <label className="text-xs font-bold text-slate-300">ประเภท
              <select value={fact.type} onChange={(event) => patch(fact.fact_id, { type: event.target.value })} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1]">{FACT_TYPE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            </label>
            <TextField label={`Fact ${index + 1}`} value={fact.text || ''} onChange={(value) => patch(fact.fact_id, { text: value })} placeholder="เขียนข้อมูลแบบตรวจสอบได้หนึ่งข้อ" />
            <TextField label="Evidence source_id" value={(fact.evidence_refs || []).join(', ')} onChange={(value) => patch(fact.fact_id, { evidence_refs: splitIds(value) })} placeholder="source-001" />
            <button type="button" onClick={() => setFacts((current) => current.filter((item) => item.fact_id !== fact.fact_id))} aria-label={`ลบ Fact ${index + 1}`} className="grid h-10 w-10 place-items-center rounded-xl text-rose-200/70 ring-1 ring-white/[0.1] hover:bg-rose-500/10 hover:text-rose-100"><Trash2 className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
      <button type="button" onClick={() => setFacts((current) => [...current, newFact()])} className="flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-bold text-cyan-300 ring-1 ring-cyan-300/30 hover:bg-cyan-300/[0.07]"><Plus className="h-4 w-4" /> เพิ่ม Fact</button>
      <ActionBar busy={busy} onClick={save} disabled={!ready} label={project.status === 'source_ready' ? 'บันทึกและไป Story' : 'บันทึก Evidence'} hint={!ready ? 'Fact ทุกข้อที่ไม่ใช่ Opinion ต้องมี Evidence source_id' : ''} />
    </StageSection>
  );
}


export function StoryStage({ project, busy, narrationState, onSave, onGenerateNarration }) {
  const [blocks, setBlocks] = useState(project.story?.blocks || []);
  const roles = new Set(blocks.map((block) => block.role));
  const ready = REQUIRED_ROLES.size === [...REQUIRED_ROLES].filter((role) => roles.has(role)).length && blocks.every((block) => block.text?.trim());
  const patch = (id, changes) => setBlocks((current) => current.map((block) => block.block_id === id ? { ...block, ...changes } : block));
  const createBlueprint = () => setBlocks(STORY_ROLE_OPTIONS.map(([_role], index) => newStoryBlock(index)));
  const save = () => onSave({ story: { ...(project.story || {}), blocks }, ...(project.status === 'research_ready' ? { status: 'script_ready' } : {}) });
  return (
    <StageSection title="Story 45–60 วินาที" description="เรียง Problem → Product Reveal → Benefit → Proof → Use Case → Honest Caveat → Verdict">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={createBlueprint} className="flex h-9 items-center gap-2 rounded-xl bg-[#D97757]/15 px-3 text-xs font-bold text-[#F2B39D] ring-1 ring-[#D97757]/35 hover:bg-[#D97757]/25"><Sparkles className="h-4 w-4" /> สร้างโครง 8 ช่วง</button>
        <button type="button" onClick={() => setBlocks((current) => [...current, newStoryBlock(current.length)])} className="flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-bold text-cyan-300 ring-1 ring-cyan-300/30 hover:bg-cyan-300/[0.07]"><Plus className="h-4 w-4" /> เพิ่ม Story block</button>
      </div>
      <div className="space-y-3">
        {blocks.map((block, index) => (
          <div key={block.block_id} className="rounded-2xl bg-white/[0.025] p-4 ring-1 ring-white/[0.07]">
            <div className="grid gap-3 lg:grid-cols-[170px_minmax(0,1fr)_40px] lg:items-end">
              <label className="text-xs font-bold text-slate-300">หน้าที่ของช่วง
                <select value={block.role} onChange={(event) => patch(block.block_id, { role: event.target.value })} className="mt-1.5 h-10 w-full rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1]">{STORY_ROLE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
              </label>
              <TextArea label={`บทพูดช่วง ${index + 1}`} value={block.text || ''} onChange={(value) => patch(block.block_id, { text: value })} placeholder="หนึ่งช่วง หนึ่งใจความ อ่านแล้วเห็นภาพที่จะใช้" rows={2} />
              <button type="button" onClick={() => setBlocks((current) => current.filter((item) => item.block_id !== block.block_id))} aria-label={`ลบ Story block ${index + 1}`} className="mb-0.5 grid h-10 w-10 place-items-center rounded-xl text-rose-200/70 ring-1 ring-white/[0.1] hover:bg-rose-500/10 hover:text-rose-100"><Trash2 className="h-4 w-4" /></button>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <TextField label="Visual intent" value={block.visual_intent || ''} onChange={(value) => patch(block.block_id, { visual_intent: value })} placeholder="Hero shot, Detail, UI หรือ Context" />
              <TextField label="claim_ids" value={(block.claim_ids || []).join(', ')} onChange={(value) => patch(block.block_id, { claim_ids: splitIds(value) })} />
              <TextField label="evidence_ids" value={(block.evidence_ids || []).join(', ')} onChange={(value) => patch(block.block_id, { evidence_ids: splitIds(value) })} />
            </div>
          </div>
        ))}
      </div>
      {project.presentation?.mode === 'gemini_tts' && (
        <div className="rounded-2xl bg-[#D97757]/10 p-4 ring-1 ring-[#D97757]/30">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div><p className="text-sm font-black text-[#F6C5B4]">Gemini TTS จาก Story นี้</p><p className="mt-1 text-xs leading-5 text-slate-400">ระบบรวมบทพูดทุกช่วง สร้างไฟล์ WAV แบบ Versioned และผูกกลับเข้า Product Project อัตโนมัติ</p></div>
            <button type="button" onClick={() => onGenerateNarration(blocks)} disabled={busy || narrationState?.running || !ready} className="flex h-10 flex-none items-center gap-2 rounded-xl bg-[#D97757] px-4 text-xs font-black text-white hover:bg-[#C2683D] disabled:cursor-not-allowed disabled:opacity-45">{narrationState?.running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic2 className="h-4 w-4" />}{narrationState?.running ? `กำลังสร้าง ${narrationState.percent}%` : 'บันทึกและสร้าง Gemini TTS'}</button>
          </div>
        </div>
      )}
      <ActionBar busy={busy} onClick={save} disabled={!ready} label={project.status === 'research_ready' ? 'บันทึกและไป Cut' : 'บันทึก Story'} hint={!ready ? 'ต้องมี Hook, Hero Benefit, Proof, Caveat, Verdict และทุกช่วงต้องมีข้อความ' : ''} />
    </StageSection>
  );
}


export function CutStage({ project, timeline, busy, onSaveProject, onBuildTimeline, onSaveTimeline, onSendReview }) {
  const sources = project.source_assets || [];
  const blocks = project.story?.blocks || [];
  const [shots, setShots] = useState(project.edit?.edl?.shots || []);
  const [savingTimeline, setSavingTimeline] = useState(false);
  const patch = (id, changes) => setShots((current) => current.map((shot) => shot.shot_id === id ? { ...shot, ...changes } : shot));
  const addShot = () => setShots((current) => [...current, newEdlShot(sources[0]?.source_id, blocks[0]?.block_id, current.length)]);
  const build = async () => {
    await onSaveProject({ edit: { ...project.edit, edl: { shots } } });
    await onBuildTimeline();
  };
  const saveTimeline = async (value) => {
    setSavingTimeline(true);
    try { await onSaveTimeline(value); } finally { setSavingTimeline(false); }
  };
  return (
    <StageSection title="Assembly Cut" description="เลือกช่วง Source ให้ตรงกับ Story block ก่อนเปิด Timeline จากนั้นปรับ Trim, Speed และลำดับช็อตในพื้นที่นี้">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-400">EDL {shots.length} ช็อต · Timeline {timeline ? formatDuration(timeline.duration) : 'ยังไม่สร้าง'}</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={addShot} disabled={!sources.length || !blocks.length} className="flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-bold text-cyan-300 ring-1 ring-cyan-300/30 disabled:opacity-40"><Plus className="h-4 w-4" /> เพิ่มช็อต</button>
          <button type="button" onClick={build} disabled={busy || !shots.length} className="flex h-9 items-center gap-2 rounded-xl bg-[#D97757]/20 px-3 text-xs font-black text-[#F6C5B4] ring-1 ring-[#D97757]/35 disabled:opacity-40">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scissors className="h-4 w-4" />} {timeline ? 'สร้าง Assembly ใหม่' : 'สร้าง Timeline'}</button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl bg-black/20 ring-1 ring-white/[0.07]">
        <table className="w-full min-w-[920px] text-left text-xs">
          <thead className="text-[10px] text-slate-500"><tr><th className="px-3 py-2.5">Source</th><th>Story</th><th>In</th><th>Out</th><th>เหตุผลที่เลือก</th><th className="pr-3 text-right">ลบ</th></tr></thead>
          <tbody className="divide-y divide-white/[0.06]">
            {shots.map((shot, index) => (
              <tr key={shot.shot_id}>
                <td className="px-3 py-2"><select value={shot.source_id} onChange={(event) => patch(shot.shot_id, { source_id: event.target.value })} className="h-9 max-w-[220px] rounded-lg bg-[#111827] px-2 text-xs text-white outline-none ring-1 ring-white/[0.1]">{sources.map((source) => <option key={source.source_id} value={source.source_id}>{source.source_id}</option>)}</select></td>
                <td><select value={shot.story_block_id} onChange={(event) => patch(shot.shot_id, { story_block_id: event.target.value })} className="h-9 max-w-[180px] rounded-lg bg-[#111827] px-2 text-xs text-white outline-none ring-1 ring-white/[0.1]">{blocks.map((block) => <option key={block.block_id} value={block.block_id}>{block.role}</option>)}</select></td>
                <td><MiniNumber value={shot.source_start} onChange={(value) => patch(shot.shot_id, { source_start: value })} /></td>
                <td><MiniNumber value={shot.source_end} onChange={(value) => patch(shot.shot_id, { source_end: value })} /></td>
                <td><input value={shot.reason || ''} onChange={(event) => patch(shot.shot_id, { reason: event.target.value })} placeholder="ภาพนี้พิสูจน์อะไร" className="h-9 w-full min-w-[220px] rounded-lg bg-black/25 px-2 text-xs text-white outline-none ring-1 ring-white/[0.1]" /></td>
                <td className="pr-3 text-right"><button type="button" onClick={() => setShots((current) => current.filter((item) => item.shot_id !== shot.shot_id))} aria-label={`ลบช็อต ${index + 1}`} className="rounded-lg p-2 text-rose-200/70 hover:bg-rose-500/10 hover:text-rose-100"><Trash2 className="h-4 w-4" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {timeline && <GadgetMediaTimelineHost key={timeline.updated_at || timeline.duration} timeline={timeline} onSave={saveTimeline} saving={savingTimeline} />}

      {timeline && (
        <div className="rounded-2xl bg-white/[0.025] p-4 ring-1 ring-white/[0.07]">
          <label className="flex cursor-pointer items-start gap-2 text-xs leading-5 text-slate-300"><input type="checkbox" checked={Boolean(project.edit?.parity_verified)} onChange={(event) => onSaveProject({ edit: { ...project.edit, parity_verified: event.target.checked } })} className="mt-1" /><span>ตรวจ Preview เทียบกับ Render contract แล้ว: ลำดับช็อต, Crop, Duration, Audio และ Safe Zone ตรงกัน</span></label>
          {project.status === 'in_production' && <div className="mt-4"><ActionBar busy={busy} onClick={onSendReview} label="ส่งเข้าขั้น Review" /></div>}
        </div>
      )}
    </StageSection>
  );
}


export function ReviewStage({ project, timeline, busy, renderState, onValidate, onRender, onApprove, onRefresh }) {
  const artifacts = (project.artifacts || []).filter((item) => item.kind === 'render');
  return (
    <StageSection title="Review และ Approved Master" description="Hard Gate ต้องผ่านทั้งหมดก่อน Render และต้องมีคนเลือกหนึ่ง Version เป็น Approved Master">
      <div className="grid gap-3 md:grid-cols-3">
        <ReviewMetric label="Duration" value={formatDuration(timeline?.duration || project.edit?.duration || 0)} ok={(timeline?.duration || 0) >= 45 && (timeline?.duration || 0) <= 60} />
        <ReviewMetric label="Hard Gate" value={project.quality_report?.passed ? 'ผ่านทั้งหมด' : `${project.quality_report?.blockers?.length || 0} blocker`} ok={project.quality_report?.passed} />
        <ReviewMetric label="Approved Master" value={project.approved_master_id ? 'เลือกแล้ว' : 'ยังไม่เลือก'} ok={Boolean(project.approved_master_id)} />
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={onValidate} disabled={busy} className="flex h-10 items-center gap-2 rounded-xl px-4 text-xs font-black text-cyan-200 ring-1 ring-cyan-300/30 hover:bg-cyan-300/[0.07] disabled:opacity-50">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />} ตรวจ Quality</button>
        <button type="button" onClick={onRender} disabled={busy || renderState.running || !canRenderProject(project)} className="flex h-10 items-center gap-2 rounded-xl bg-[#D97757] px-4 text-xs font-black text-white hover:bg-[#C2683D] disabled:cursor-not-allowed disabled:opacity-45">{renderState.running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Video className="h-4 w-4" />}{renderState.running ? `กำลัง Render ${renderState.percent}%` : 'Render Master 1080p'}</button>
        <button type="button" onClick={onRefresh} disabled={busy} className="flex h-10 items-center gap-2 rounded-xl px-4 text-xs font-bold text-slate-200 ring-1 ring-white/[0.1] hover:bg-white/[0.06]"><RefreshCw className="h-4 w-4" /> โหลดสถานะล่าสุด</button>
      </div>
      {renderState.message && <p className={`rounded-xl px-3 py-2 text-xs ${renderState.error ? 'bg-rose-500/10 text-rose-200 ring-1 ring-rose-400/25' : 'bg-cyan-500/[0.07] text-cyan-100 ring-1 ring-cyan-300/20'}`}>{renderState.message}</p>}

      <div className="overflow-hidden rounded-2xl bg-black/20 ring-1 ring-white/[0.07]">
        <div className="border-b border-white/[0.06] px-4 py-3"><h3 className="text-sm font-black text-white">Render versions</h3></div>
        {artifacts.length === 0 ? <p className="px-4 py-8 text-center text-sm text-slate-500">ยังไม่มี Render version</p> : (
          <ul className="divide-y divide-white/[0.06]">
            {artifacts.map((artifact) => (
              <li key={artifact.artifact_id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0"><p className="truncate text-xs font-bold text-white">v{String(artifact.version || 1).padStart(2, '0')} · {artifact.path}</p><p className="mt-1 text-[10px] text-slate-500">{formatDuration(artifact.duration)} · 1080×1920 · 30 FPS</p></div>
                <div className="flex items-center gap-2">
                  <a href={toMediaUrl(artifact.path)} target="_blank" rel="noreferrer" className="flex h-9 items-center gap-1.5 rounded-xl px-3 text-xs font-bold text-slate-200 ring-1 ring-white/[0.1] hover:bg-white/[0.06]">เปิดดู <ExternalLink className="h-3.5 w-3.5" /></a>
                  <button type="button" onClick={() => onApprove(artifact.artifact_id)} disabled={busy || artifact.approved} className={`flex h-9 items-center gap-1.5 rounded-xl px-3 text-xs font-black ${artifact.approved ? 'bg-emerald-500/15 text-emerald-300' : 'bg-cyan-300 text-[#061116]'} disabled:opacity-70`}>{artifact.approved ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}{artifact.approved ? 'Approved Master' : 'อนุมัติเป็น Master'}</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </StageSection>
  );
}


function StageSection({ title, description, children }) {
  return <section className="space-y-4 rounded-2xl bg-[#0B0F19] p-4 ring-1 ring-white/[0.08] sm:p-5"><header><h2 className="text-lg font-black text-white">{title}</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-slate-400">{description}</p></header>{children}</section>;
}

function TextField({ label, value, onChange, placeholder = '' }) {
  return <label className="text-xs font-bold text-slate-300">{label}<input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-1.5 h-10 w-full rounded-xl bg-black/25 px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] placeholder:text-slate-600 focus:ring-cyan-300/70" /></label>;
}

function TextArea({ label, value, onChange, placeholder = '', rows = 3 }) {
  return <label className="block text-xs font-bold text-slate-300">{label}<textarea rows={rows} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-1.5 w-full resize-y rounded-xl bg-black/25 px-3 py-2 text-sm leading-6 text-white outline-none ring-1 ring-white/[0.1] placeholder:text-slate-600 focus:ring-cyan-300/70" /></label>;
}

function ActionBar({ busy, onClick, label, disabled = false, hint = '' }) {
  return <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] pt-4"><p className="text-[11px] text-amber-200">{hint}</p><button type="button" onClick={onClick} disabled={busy || disabled} className="flex h-10 items-center gap-2 rounded-xl bg-cyan-300 px-4 text-xs font-black text-[#061116] disabled:cursor-not-allowed disabled:opacity-45">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{label}</button></div>;
}

function MiniNumber({ value, onChange }) {
  return <input type="number" min="0" step="0.1" value={value ?? 0} onChange={(event) => onChange(Number(event.target.value))} className="h-9 w-20 rounded-lg bg-black/25 px-2 text-xs text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70" />;
}

function ReviewMetric({ label, value, ok }) {
  return <div className="rounded-2xl bg-white/[0.025] p-4 ring-1 ring-white/[0.07]"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className={`mt-1 text-lg font-black ${ok ? 'text-emerald-300' : 'text-amber-200'}`}>{value}</p></div>;
}

function splitIds(value) {
  return String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
}
