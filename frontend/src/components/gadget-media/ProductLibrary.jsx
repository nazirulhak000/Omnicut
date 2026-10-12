import React, { useMemo, useState } from 'react';
import { ArrowRight, CircleAlert, Filter, Loader2, Plus, RefreshCw } from 'lucide-react';

import { formatDuration, projectDisplayName, STATUS_LABELS } from '../../lib/gadgetMediaProject.js';
import { useGadgetDraft } from './useGadgetDraft.js';


const EMPTY_FORM = {
  brand: '', model: '', category: 'Gadget', variant: '', audience: '',
  editorial_promise: 'ช่วยให้คนดูเข้าใจสินค้าและตัดสินใจก่อนซื้อใน 45–60 วินาที',
  presentation_mode: 'gemini_tts', voice: '',
};


export default function ProductLibrary({ projects, loading, onRefresh, onCreate, onOpen, seed }) {
  const [showCreate, setShowCreate] = useState(Boolean(seed));
  const [form, setForm] = useState(() => ({ ...EMPTY_FORM, audience: seed?.audience || '', editorial_promise: seed?.editorialPromise || EMPTY_FORM.editorial_promise }));
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const draftParticipant = useGadgetDraft(form, {
    reset: setForm,
    save: () => {
      if (!form.brand.trim() || !form.model.trim()) throw new Error('กรอก Brand และ Model ก่อนบันทึก หรือเลือกทิ้งการแก้ไข');
      return onCreate(form);
    },
  });

  const filtered = useMemo(() => projects.filter((project) => {
    const identity = project.product_identity || {};
    const haystack = `${identity.brand || ''} ${identity.model || ''} ${identity.category || ''}`.toLowerCase();
    const matchesQuery = !query || haystack.includes(query.toLowerCase());
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesQuery && matchesStatus;
  }), [projects, query, statusFilter]);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const created = await draftParticipant.save();
      setForm(EMPTY_FORM);
      draftParticipant.markSaved(EMPTY_FORM);
      setShowCreate(false);
      onOpen(created.project_id);
    } catch (createError) {
      setError(createError?.response?.data?.detail || createError?.message || 'สร้าง Product Video ไม่สำเร็จ');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-2xl bg-[#0B0F19] p-3 ring-1 ring-white/[0.08] sm:flex-row sm:items-center">
        <label className="min-w-0 flex-1">
          <span className="sr-only">ค้นหา Product Video</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ค้นหา Brand, Model หรือ Category"
            className="h-10 w-full rounded-xl bg-black/25 px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] placeholder:text-slate-500 focus:ring-cyan-300/70"
          />
        </label>
        <label className="flex items-center gap-2 rounded-xl bg-black/25 px-3 ring-1 ring-white/[0.1]">
          <Filter className="h-4 w-4 text-slate-500" />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="h-10 bg-transparent text-xs font-bold text-slate-200 outline-none">
            <option value="all">ทุกสถานะ</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <button type="button" onClick={onRefresh} disabled={loading} className="flex h-10 items-center justify-center gap-2 rounded-xl px-3 text-xs font-bold text-slate-200 ring-1 ring-white/[0.1] hover:bg-white/[0.06] disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> รีเฟรช
        </button>
        <button type="button" onClick={() => setShowCreate((value) => !value)} className="flex h-10 items-center justify-center gap-2 rounded-xl bg-cyan-300 px-4 text-xs font-black text-[#061116] hover:bg-cyan-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
          <Plus className="h-4 w-4" /> สร้าง Product Video
        </button>
      </div>

      {showCreate && (
        <form onSubmit={submit} className="rounded-2xl bg-[#0B0F19] p-5 ring-1 ring-cyan-300/30">
          <div className="flex flex-col gap-1">
            <h2 className="text-lg font-black text-white">เริ่มจากสินค้าหนึ่งรุ่น</h2>
            <p className="max-w-3xl text-sm leading-6 text-slate-400">ระบบจะสร้าง Project, Timeline และ Export namespace แยกจากงานรีวิวปักตะกร้าเดิมทั้งหมด</p>
          </div>
          {error && <p className="mt-3 flex items-center gap-2 text-sm text-rose-200"><CircleAlert className="h-4 w-4" />{error}</p>}
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Brand" value={form.brand} required onChange={(value) => setForm((current) => ({ ...current, brand: value }))} placeholder="Xiaomi" />
            <Field label="Model" value={form.model} required onChange={(value) => setForm((current) => ({ ...current, model: value }))} placeholder="14T Pro" />
            <Field label="Category" value={form.category} onChange={(value) => setForm((current) => ({ ...current, category: value }))} placeholder="Smartphone" />
            <Field label="Variant" value={form.variant} onChange={(value) => setForm((current) => ({ ...current, variant: value }))} placeholder="Titan Black" />
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <Field label="กลุ่มคนดู" value={form.audience} onChange={(value) => setForm((current) => ({ ...current, audience: value }))} placeholder="คนที่กำลังเลือกมือถือเน้นกล้อง" />
            <Field label="คำสัญญาของคลิป" value={form.editorial_promise} onChange={(value) => setForm((current) => ({ ...current, editorial_promise: value }))} />
          </div>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
            <label className="text-xs font-bold text-slate-300">
              รูปแบบเสียง
              <select value={form.presentation_mode} onChange={(event) => setForm((current) => ({ ...current, presentation_mode: event.target.value }))} className="mt-1.5 block h-10 rounded-xl bg-[#111827] px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] focus:ring-cyan-300/70">
                <option value="gemini_tts">Gemini TTS</option>
                <option value="creator_voice">เสียง Creator</option>
                <option value="product_only">Product-only</option>
              </select>
            </label>
            <button type="submit" disabled={submitting || !form.brand.trim() || !form.model.trim()} className="flex h-10 items-center gap-2 rounded-xl bg-cyan-300 px-5 text-sm font-black text-[#061116] disabled:cursor-not-allowed disabled:opacity-50">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} สร้าง Project
            </button>
          </div>
        </form>
      )}

      {loading && projects.length === 0 ? (
        <div className="grid min-h-64 place-items-center rounded-2xl bg-[#0B0F19] text-sm text-slate-400 ring-1 ring-white/[0.08]"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />กำลังโหลด Product Library</div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl bg-[#0B0F19] px-6 py-14 text-center ring-1 ring-white/[0.08]">
          <p className="text-base font-black text-white">ยังไม่มี Product Video ที่ตรงกับตัวกรอง</p>
          <p className="mt-2 text-sm text-slate-400">สร้าง Project แรก แล้วค่อยเติม Source, Evidence และ Timeline ใน Workspace เดียว</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl bg-[#0B0F19] ring-1 ring-white/[0.08]">
          <div className="hidden grid-cols-[minmax(240px,2fr)_1fr_150px_110px_96px] gap-4 border-b border-white/[0.07] px-4 py-3 text-[10px] font-bold text-slate-500 lg:grid">
            <span>สินค้า</span><span>สถานะ</span><span>Quality</span><span>ความยาว</span><span className="text-right">เปิดงาน</span>
          </div>
          <ul className="divide-y divide-white/[0.06]">
            {filtered.map((project) => (
              <li key={project.project_id}>
                <button type="button" onClick={() => onOpen(project.project_id)} className="grid w-full gap-3 px-4 py-4 text-left transition-colors hover:bg-white/[0.035] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-300 lg:grid-cols-[minmax(240px,2fr)_1fr_150px_110px_96px] lg:items-center lg:gap-4">
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-black text-white">{projectDisplayName(project)}</span>
                    <span className="mt-1 block truncate text-[11px] text-slate-500">{project.product_identity?.category || 'Gadget'} · {project.project_id}</span>
                  </span>
                  <span className="text-xs font-bold text-slate-300">{STATUS_LABELS[project.status] || project.status}</span>
                  <span className={`text-xs font-bold ${project.quality_passed ? 'text-emerald-300' : project.blocker_count ? 'text-amber-200' : 'text-slate-500'}`}>{project.quality_passed ? `ผ่าน · ${project.quality_score}/100` : project.blocker_count ? `${project.blocker_count} blocker` : 'ยังไม่ตรวจ'}</span>
                  <span className="text-xs text-slate-300">{formatDuration(project.duration)}</span>
                  <span className="flex items-center justify-end gap-1 text-xs font-black text-cyan-300">ทำต่อ <ArrowRight className="h-4 w-4" /></span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}


function Field({ label, value, onChange, placeholder = '', required = false }) {
  return (
    <label className="text-xs font-bold text-slate-300">
      {label}{required && <span className="text-rose-300"> *</span>}
      <input required={required} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-1.5 h-10 w-full rounded-xl bg-black/25 px-3 text-sm text-white outline-none ring-1 ring-white/[0.1] placeholder:text-slate-600 focus:ring-cyan-300/70" />
    </label>
  );
}

