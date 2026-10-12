import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  CheckCircle2,
  CircleAlert,
  Cpu,
  ExternalLink,
  FileText,
  Play,
  Plus,
  RefreshCw,
  Save,
  Scissors,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { PageHeader } from './ui';
import GadgetMediaStudio from './gadget-media/GadgetMediaStudio.jsx';
import { useGadgetDraft } from './gadget-media/useGadgetDraft.js';
import {
  createGadgetMediaCampaign,
  getGadgetMediaCampaignReadiness,
  getGadgetMediaPresetSources,
  listGadgetMediaCampaigns,
  updateGadgetMediaSlot,
} from '../api';
import {
  GADGET_MEDIA_STATUSES,
  SOURCE_RIGHTS_OPTIONS,
  calculateCampaignAnalytics,
  campaignProgress,
  generateScriptTemplate,
  readinessCounts,
  seriesLabel,
  statusLabel,
} from '../lib/gadgetMedia';

const EMPTY_SOURCE = {
  source_url: '',
  rights_basis: 'self_recorded',
  creator_or_brand: '',
  usage_note: '',
  rights_reviewed: false,
};

function errorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function statusClasses(status) {
  if (status === 'published') return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
  if (status === 'edited') return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
  if (status === 'recorded') return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
  if (status === 'scripted') return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
  return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
}

function CampaignPlanner({ onCreateProductProject }) {
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [readiness, setReadiness] = useState(null);
  const [presetSources, setPresetSources] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState('');

  const [draft, setDraft] = useState({
    hook: '',
    script: '',
    status: 'planned',
    metrics: { views: 0, completion_rate: 0.0, comments: 0, follows: 0 },
  });
  const [sourceDraft, setSourceDraft] = useState(EMPTY_SOURCE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [activeViewMode, setActiveViewMode] = useState('slots'); // 'slots' | 'analytics'

  const campaign = useMemo(
    () => campaigns.find((item) => item.campaign_id === selectedCampaignId) || null,
    [campaigns, selectedCampaignId],
  );
  const slot = useMemo(
    () => campaign?.slots?.find((item) => item.slot_id === selectedSlotId) || null,
    [campaign, selectedSlotId],
  );
  const progress = campaignProgress(campaign);
  const counts = readinessCounts(readiness);
  const slotBlockers = readiness?.blockers?.[slot?.slot_id] || [];
  const analytics = useMemo(() => calculateCampaignAnalytics(campaign), [campaign]);
  const draftParticipant = useGadgetDraft(draft, { reset: setDraft, save: () => saveSlot(draft) });
  const sourceParticipant = useGadgetDraft(sourceDraft, { reset: setSourceDraft, save: () => saveSourceDraft() });
  const campaignCreation = useGadgetDraft(null, { reset() {}, save: () => createCampaign() });

  const loadCampaigns = async (preferredId = selectedCampaignId) => {
    setLoading(true);
    setError('');
    try {
      const response = await listGadgetMediaCampaigns();
      const nextCampaigns = response.campaigns || [];
      setCampaigns(nextCampaigns);
      const nextId = nextCampaigns.some((item) => item.campaign_id === preferredId)
        ? preferredId
        : nextCampaigns[0]?.campaign_id || '';
      setSelectedCampaignId(nextId);
    } catch (loadError) {
      setError(errorMessage(loadError, 'โหลด Gadget Media campaign ไม่สำเร็จ'));
    } finally {
      setLoading(false);
    }
  };

  const loadPresetSources = async () => {
    try {
      const res = await getGadgetMediaPresetSources();
      setPresetSources(res.sources || []);
    } catch (err) {
      console.warn('โหลด preset sources ไม่สำเร็จ:', err);
    }
  };

  useEffect(() => {
    loadCampaigns('');
    loadPresetSources();
  }, []);

  useEffect(() => {
    if (!campaign) {
      setSelectedSlotId('');
      return;
    }
    setSelectedSlotId((current) =>
      campaign.slots.some((item) => item.slot_id === current)
        ? current
        : campaign.slots[0]?.slot_id || '',
    );
  }, [campaign]);

  useEffect(() => {
    if (!slot) {
      const empty = {
        hook: '',
        script: '',
        status: 'planned',
        metrics: { views: 0, completion_rate: 0.0, comments: 0, follows: 0 },
      };
      setDraft(empty);
      draftParticipant.markSaved(empty);
      setSourceDraft(EMPTY_SOURCE);
      sourceParticipant.markSaved(EMPTY_SOURCE);
      return;
    }
    const nextDraft = {
      hook: slot.hook || '',
      script: slot.script || '',
      status: slot.status || 'planned',
      metrics: {
        views: slot.metrics?.views || 0,
        completion_rate: slot.metrics?.completion_rate || 0.0,
        comments: slot.metrics?.comments || 0,
        follows: slot.metrics?.follows || 0,
      },
    };
    setDraft(nextDraft);
    draftParticipant.markSaved(nextDraft);
    setSourceDraft(EMPTY_SOURCE);
    sourceParticipant.markSaved(EMPTY_SOURCE);
  }, [selectedCampaignId, selectedSlotId]);

  useEffect(() => {
    if (!selectedCampaignId) {
      setReadiness(null);
      return;
    }
    let cancelled = false;
    getGadgetMediaCampaignReadiness(selectedCampaignId)
      .then((response) => {
        if (!cancelled) setReadiness(response);
      })
      .catch((readinessError) => {
        if (!cancelled) setError(errorMessage(readinessError, 'โหลด readiness ไม่สำเร็จ'));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCampaignId]);

  const createCampaign = async () => {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const created = await createGadgetMediaCampaign({});
      setCampaigns((current) => [...current, created]);
      setSelectedCampaignId(created.campaign_id);
      setNotice('สร้าง Campaign 21 ช่องเรียบร้อยแล้ว');
    } catch (createError) {
      setError(errorMessage(createError, 'สร้าง campaign ไม่สำเร็จ'));
      throw createError;
    } finally {
      setSaving(false);
    }
  };

  const saveSlot = async (payload = draft) => {
    if (!campaign || !slot) throw new Error('เลือก Campaign และ slot ก่อนบันทึก');
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await updateGadgetMediaSlot(campaign.campaign_id, slot.slot_id, payload);
      setCampaigns(current => current.map(item => item.campaign_id === campaign.campaign_id
        ? { ...item, slots: item.slots.map(value => value.slot_id === slot.slot_id ? saved : value) } : item));
      setReadiness(null);
      try { setReadiness(await getGadgetMediaCampaignReadiness(campaign.campaign_id)); }
      catch (refreshError) { console.warn('โหลด readiness หลังบันทึกไม่สำเร็จ:', refreshError); }
      setNotice('บันทึก slot เรียบร้อยแล้ว');
      return saved;
    } catch (saveError) {
      setError(errorMessage(saveError, 'บันทึก slot ไม่สำเร็จ'));
      throw saveError;
    } finally {
      setSaving(false);
    }
  };

  const handleApplyPresetSource = (preset) => {
    if (!preset) return;
    setSourceDraft({
      source_url: preset.source_url || '',
      rights_basis: preset.rights_basis || 'commentary_excerpt',
      creator_or_brand: preset.brand || preset.channel || '',
      usage_note: preset.usage_note || 'วิเคราะห์สเปกและข้อดีข้อเสีย',
      rights_reviewed: false,
    });
    setNotice(`ดึงข้อมูลต้นทาง ${preset.brand || preset.topic} แล้ว`);
  };

  const handleGenerateScript = () => {
    if (!slot) return;
    const matchedPreset = presetSources.find((p) => p.id === selectedPresetId);
    const topic = matchedPreset?.topic || slot.hook.replace(/^(คลิปนี้|สเปก|ของจริง).*?/, '').trim() || 'Gadget รุ่นนี้';
    const brand = matchedPreset?.brand || '';
    const generated = generateScriptTemplate(slot.series, { topic, brand });
    setDraft((current) => ({
      ...current,
      hook: generated.hook,
      script: generated.script,
      status: current.status === 'planned' ? 'scripted' : current.status,
    }));
    setNotice('สร้างโครงสร้างสคริปต์ 5 ท่อนสำเร็จแล้ว');
  };

  const handleSendToEditor = () => {
    if (!slot || !draft.script.trim()) {
      setError('กรุณาเตรียมสคริปต์ก่อนส่งเข้าหน้าตัดต่อ');
      return;
    }
    onCreateProductProject?.({
      campaignId: campaign.campaign_id,
      slotId: slot.slot_id,
      audience: slot.target_audience,
      editorialPromise: draft.hook || slot.hook,
      sourceRefs: slot.source_refs || [],
      sourceScript: draft.script,
    });
  };

  const saveSourceDraft = async () => {
    if (!sourceDraft.source_url.trim()) {
      throw new Error('กรุณาใส่ source URL ก่อนบันทึกแหล่งที่มา หรือเลือกทิ้งการแก้ไข');
    }
    return saveSlot({
      source_refs: [...(slot?.source_refs || []), { ...sourceDraft }],
    });
  };

  const addSource = async () => {
    try { await sourceParticipant.save(); }
    catch (sourceError) { setError(errorMessage(sourceError, 'บันทึกแหล่งที่มาไม่สำเร็จ')); return; }
    setSourceDraft(EMPTY_SOURCE);
    sourceParticipant.markSaved(EMPTY_SOURCE);
  };

  const removeSource = async (sourceId) => {
    await saveSlot({
      source_refs: (slot?.source_refs || []).filter((source) => source.source_id !== sourceId),
    });
  };

  const toggleSourceReviewed = async (sourceId, currentStatus) => {
    const updatedSources = (slot?.source_refs || []).map((source) =>
      source.source_id === sourceId ? { ...source, rights_reviewed: !currentStatus } : source,
    );
    await saveSlot({ source_refs: updatedSources });
  };

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Gadget Media · 30 วัน"
        title="แคมเปญสร้างผู้ติดตามแบบ Organic"
        icon={Cpu}
        iconGradient="from-cyan-500/25 to-blue-500/20"
        actions={(
          <>
            <div className="flex items-center rounded-xl bg-white/[0.04] p-0.5 border border-white/[0.08]">
              <button
                type="button"
                onClick={() => setActiveViewMode('slots')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  activeViewMode === 'slots'
                    ? 'bg-cyan-400 text-black shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                21 ช่องคอนเทนต์
              </button>
              <button
                type="button"
                onClick={() => setActiveViewMode('analytics')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeViewMode === 'analytics'
                    ? 'bg-cyan-400 text-black shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                สถิติและผลลัพธ์
              </button>
            </div>
            <button
              type="button"
              onClick={() => loadCampaigns()}
              disabled={loading || saving}
              className="min-h-9 px-3 rounded-xl border border-white/[0.1] bg-white/[0.04] text-xs font-bold text-slate-200 hover:bg-white/[0.08] disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              รีเฟรช
            </button>
            <button
              type="button"
              onClick={() => campaignCreation.save().catch(() => {})}
              disabled={saving}
              className="min-h-9 px-3 rounded-xl bg-[#25F4EE] text-[#061116] text-xs font-black hover:bg-cyan-300 disabled:opacity-50 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              สร้าง Campaign 21 คลิป
            </button>
          </>
        )}
        secondRow={(
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>คำสัญญา: เล่าเรื่อง Gadget ให้เข้าใจง่าย ก่อนคุณเสียเงินซื้อ</span>
            <span className="text-slate-600">|</span>
            <span>ช่องทางแยกอิสระ ไม่ผูกกับตะกร้า Affiliate</span>
            <span className="text-slate-600">|</span>
            <span className="text-cyan-300 font-semibold">9:16 (1080x1920, 30 FPS) Micro-Burst</span>
          </div>
        )}
      />

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200 flex items-start gap-2">
          <CircleAlert className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {loading && !campaigns.length ? (
        <div className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] p-10 text-center text-sm text-slate-400">
          กำลังโหลด Gadget Media campaign
        </div>
      ) : !campaign ? (
        <div className="rounded-2xl border border-dashed border-cyan-500/30 bg-cyan-500/[0.05] p-10 text-center">
          <Cpu className="mx-auto w-10 h-10 text-cyan-300 mb-3" />
          <h2 className="text-lg font-black text-white">เริ่มแผน 30 วันของ Gadget Media</h2>
          <p className="mt-2 text-sm text-slate-400">สร้าง Campaign เพื่อได้ 21 ช่องงาน แบ่งเป็น 3 ซีรีส์ พร้อมสิทธิบัตรและความถูกต้องของคลิป</p>
          <button
            type="button"
            onClick={() => campaignCreation.save().catch(() => {})}
            disabled={saving}
            className="mt-5 min-h-10 px-4 rounded-xl bg-[#25F4EE] text-[#061116] text-sm font-black disabled:opacity-50"
          >
            สร้าง Campaign แรก
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-2.5">
            <StatCard label="ช่องทั้งหมด" value={progress.total} hint="เป้าหมาย 21 คลิป" />
            <StatCard label="เผยแพร่แล้ว" value={progress.published} hint={`${progress.percent}% ของแผน`} tone="emerald" />
            <StatCard label="กำลังทำ" value={progress.inProgress} hint="มีสคริปต์หรือตัดต่อ" tone="violet" />
            <StatCard label="พร้อมเผยแพร่" value={counts.ready} hint="ผ่านสิทธิ์และตรวจครบ" tone="cyan" />
            <StatCard label="Private Cut / ติด blocker" value={counts.blocked} hint="ดูภายในได้ ล็อกโพสต์จริง" tone="rose" />
          </div>

          {activeViewMode === 'analytics' ? (
            /* ── Analytics & Results Dashboard ── */
            <div className="space-y-4">
              <section className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-base font-black text-white flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-cyan-300" />
                      ผลลัพธ์ภาพรวม 30 วัน (21 คลิป)
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">วัดผลการเติบโตแบบ Organic เพื่อสร้างผู้ติดตามที่แท้จริง</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                    <p className="text-[11px] text-slate-400">ยอดวิวรวม (Views)</p>
                    <p className="mt-1 text-2xl font-black text-white">{analytics.totalViews.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                    <p className="text-[11px] text-slate-400">ผู้ติดตามเพิ่ม (Follows)</p>
                    <p className="mt-1 text-2xl font-black text-emerald-300">+{analytics.totalFollows.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                    <p className="text-[11px] text-slate-400">คอมเมนต์รวม</p>
                    <p className="mt-1 text-2xl font-black text-cyan-300">{analytics.totalComments.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                    <p className="text-[11px] text-slate-400">ดูจบเฉลี่ย (Completion)</p>
                    <p className="mt-1 text-2xl font-black text-[#F2B39D]">{analytics.avgCompletionRate}%</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                    <p className="text-[11px] text-slate-400">Follows ต่อ 1K วิว</p>
                    <p className="mt-1 text-2xl font-black text-amber-300">{analytics.followsPer1000Views}</p>
                  </div>
                </div>

                {/* Breakdown by Series */}
                <h3 className="mt-6 mb-3 text-xs font-bold text-slate-300 uppercase tracking-wider">ประสิทธิภาพแยกตาม 3 ซีรีส์</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {Object.entries(analytics.series).map(([key, item]) => (
                    <div key={key} className="rounded-xl border border-white/[0.08] bg-black/20 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-black text-cyan-300">{seriesLabel(key)}</span>
                        <span className="text-[10px] text-slate-400">{item.count} คลิป</span>
                      </div>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between text-slate-300">
                          <span>ยอดวิว:</span>
                          <span className="font-bold">{item.views.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>ผู้ติดตาม:</span>
                          <span className="font-bold text-emerald-300">+{item.follows}</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>ดูจบเฉลี่ย:</span>
                          <span className="font-bold">{item.avgCompletionRate}%</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Follows/1K วิว:</span>
                          <span className="font-bold text-amber-300">{item.followsPer1000Views}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : (
            /* ── Content Slots & Studio Management ── */
            <div className="grid xl:grid-cols-[minmax(0,1.2fr)_minmax(380px,0.8fr)] gap-4 items-start">
              <section className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] p-3 sm:p-4">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500">Campaign</p>
                    <h2 className="text-base font-black text-white">{campaign.name}</h2>
                  </div>
                  <select
                    value={selectedCampaignId}
                    onChange={(event) => setSelectedCampaignId(event.target.value)}
                    className="min-h-9 max-w-full rounded-xl border border-white/[0.1] bg-[#111827] px-3 text-xs text-slate-200 outline-none"
                  >
                    {campaigns.map((item) => (
                      <option key={item.campaign_id} value={item.campaign_id}>{item.name}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
                  {campaign.slots.map((item, index) => {
                    const selected = item.slot_id === selectedSlotId;
                    const ready = item.ready_to_publish;
                    return (
                      <button
                        type="button"
                        key={item.slot_id}
                        onClick={() => setSelectedSlotId(item.slot_id)}
                        className={`text-left rounded-xl border p-3 transition-colors ${
                          selected
                            ? 'border-cyan-400/70 bg-cyan-400/[0.09]'
                            : 'border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.05]'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-bold text-slate-500">#{String(index + 1).padStart(2, '0')}</span>
                          <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-bold ${statusClasses(item.status)}`}>
                            {statusLabel(item.status)}
                          </span>
                        </div>
                        <p className="mt-2 text-[10px] font-bold text-cyan-300">{seriesLabel(item.series)}</p>
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-200">{item.hook}</p>
                        <div className={`mt-2 flex items-center gap-1 text-[10px] ${ready ? 'text-emerald-300' : 'text-amber-300'}`}>
                          {ready ? <CheckCircle2 className="w-3 h-3" /> : <CircleAlert className="w-3 h-3" />}
                          <span>{ready ? 'พร้อมเผยแพร่' : 'Private Cut'}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* Slot Editor Panel */}
              <section className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] p-3 sm:p-4 space-y-4 xl:sticky xl:top-20">
                {slot ? (
                  <>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">{slot.slot_id}</p>
                        <h2 className="mt-1 text-base font-black text-white">{seriesLabel(slot.series)}</h2>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${statusClasses(slot.status)}`}>
                        {statusLabel(slot.status)}
                      </span>
                    </div>

                    {/* Preset Sources Picker */}
                    {presetSources.length > 0 && (
                      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/[0.04] p-2.5">
                        <label className="block text-[11px] font-bold text-cyan-300 mb-1">
                          ดึงข้อมูลจากแหล่งข่าว/สินค้าที่มีอยู่
                        </label>
                        <div className="flex gap-2">
                          <select
                            value={selectedPresetId}
                            onChange={(e) => {
                              setSelectedPresetId(e.target.value);
                              const p = presetSources.find((item) => item.id === e.target.value);
                              if (p) handleApplyPresetSource(p);
                            }}
                            className="min-h-8 flex-1 rounded-lg border border-white/[0.1] bg-[#111827] px-2 text-xs text-white outline-none"
                          >
                            <option value="">เลือกสินค้าหรือข่าวต้นทาง...</option>
                            {presetSources.map((ps) => (
                              <option key={ps.id} value={ps.id}>
                                {ps.brand}: {ps.topic}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}

                    {/* Hook & Script Editor */}
                    <label className="block text-xs font-bold text-slate-300">
                      Hook (0-2 วินาที)
                      <input
                        value={draft.hook}
                        onChange={(event) => setDraft((current) => ({ ...current, hook: event.target.value }))}
                        className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/60"
                      />
                    </label>

                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="text-xs font-bold text-slate-300">Script (30–40 วินาที)</label>
                        <button
                          type="button"
                          onClick={handleGenerateScript}
                          className="px-2.5 py-1 rounded-lg bg-cyan-400/15 border border-cyan-400/30 text-cyan-300 text-xs font-bold hover:bg-cyan-400/25 flex items-center gap-1.5 transition-colors"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
                          สร้างสคริปต์ 5 ท่อน
                        </button>
                      </div>
                      <textarea
                        value={draft.script}
                        onChange={(event) => setDraft((current) => ({ ...current, script: event.target.value }))}
                        rows={7}
                        placeholder="[Hook 0-2s] ...&#10;[Evidence 3-8s] ...&#10;[Explain 9-28s] ...&#10;[Verdict 29-36s] ...&#10;[CTA 37-40s] ..."
                        className="w-full resize-y rounded-xl border border-white/[0.1] bg-black/20 px-3 py-2.5 text-xs leading-6 text-white outline-none focus:border-cyan-400/60 font-mono"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <label className="block text-xs font-bold text-slate-300">
                        สถานะงาน
                        <select
                          value={draft.status}
                          onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value }))}
                          className="mt-1.5 w-full rounded-xl border border-white/[0.1] bg-[#111827] px-3 py-2 text-xs text-white outline-none"
                        >
                          {Object.entries(GADGET_MEDIA_STATUSES).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </label>
                      <div className="flex items-end">
                        <button
                          type="button"
                          onClick={() => draftParticipant.save().catch(() => {})}
                          disabled={saving}
                          className="min-h-9 w-full rounded-xl bg-cyan-300 text-[#061116] text-xs font-black disabled:opacity-50 flex items-center justify-center gap-2 hover:bg-cyan-200"
                        >
                          บันทึก slot
                        </button>
                      </div>
                    </div>

                    {/* Primary Action Buttons: Send to Editor / Quick Render */}
                    <div className="grid grid-cols-2 gap-2 pt-2">
                      <button
                        type="button"
                        onClick={handleSendToEditor}
                        className="min-h-10 rounded-xl bg-[#D97757] hover:bg-[#C2683D] text-white text-xs font-bold flex items-center justify-center gap-1.5"
                      >
                        <Scissors className="w-4 h-4" />
                        สร้าง Product Project
                      </button>
                      <button
                        type="button"
                        onClick={handleSendToEditor}
                        className="min-h-10 rounded-xl border border-white/[0.1] bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5"
                      >
                        <Play className="w-4 h-4 text-cyan-300" />
                        เปิด Product Studio
                      </button>
                    </div>

                    {/* Source Provenance & Rights Gate */}
                    <div className="border-t border-white/[0.08] pt-4">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-black text-white flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-cyan-300" />
                          Source provenance
                        </h3>
                        <span className="text-[10px] text-slate-500">{slot.source_refs?.length || 0} แหล่ง</span>
                      </div>
                      <div className="mt-2 space-y-2">
                        {(slot.source_refs || []).map((source) => (
                          <div key={source.source_id} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-2.5">
                            <div className="flex items-start justify-between gap-2">
                              <a
                                href={source.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="min-w-0 text-xs text-cyan-300 hover:underline flex items-center gap-1"
                              >
                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{source.source_url}</span>
                              </a>
                              <button
                                type="button"
                                onClick={() => removeSource(source.source_id).catch(() => {})}
                                className="text-[10px] text-rose-300 hover:text-rose-200"
                              >
                                ลบ
                              </button>
                            </div>
                            <p className="mt-1 text-[10px] text-slate-400">
                              {SOURCE_RIGHTS_OPTIONS.find((item) => item.value === source.rights_basis)?.label || source.rights_basis}
                              {source.creator_or_brand ? ` • ${source.creator_or_brand}` : ''}
                            </p>
                            <div className="mt-2 flex items-center justify-between">
                              <label className="flex items-center gap-1.5 text-[11px] text-slate-300 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={source.rights_reviewed}
                                  onChange={() => toggleSourceReviewed(source.source_id, source.rights_reviewed).catch(() => {})}
                                  className="rounded border-white/20 bg-black/40 text-cyan-400 focus:ring-0"
                                />
                                <span>ยืนยันการตรวจสิทธิ์แล้ว</span>
                              </label>
                              <span className={`text-[10px] font-semibold ${source.rights_reviewed ? 'text-emerald-300' : 'text-amber-300'}`}>
                                {source.rights_reviewed ? 'สิทธิ์ผ่าน' : 'Private Cut only'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="mt-3 grid gap-2">
                        <input
                          value={sourceDraft.source_url}
                          onChange={(event) => setSourceDraft((current) => ({ ...current, source_url: event.target.value }))}
                          placeholder="Source URL"
                          className="rounded-xl border border-white/[0.1] bg-black/20 px-3 py-2 text-xs text-white outline-none"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <select
                            value={sourceDraft.rights_basis}
                            onChange={(event) => setSourceDraft((current) => ({ ...current, rights_basis: event.target.value }))}
                            className="rounded-xl border border-white/[0.1] bg-[#111827] px-3 py-2 text-xs text-white outline-none"
                          >
                            {SOURCE_RIGHTS_OPTIONS.map((item) => (
                              <option key={item.value} value={item.value}>{item.label}</option>
                            ))}
                          </select>
                          <input
                            value={sourceDraft.creator_or_brand}
                            onChange={(event) => setSourceDraft((current) => ({ ...current, creator_or_brand: event.target.value }))}
                            placeholder="แบรนด์ / ช่องต้นทาง"
                            className="rounded-xl border border-white/[0.1] bg-black/20 px-3 py-2 text-xs text-white outline-none"
                          />
                        </div>
                        {sourceDraft.rights_basis === 'commentary_excerpt' && (
                          <input
                            value={sourceDraft.usage_note}
                            onChange={(event) => setSourceDraft((current) => ({ ...current, usage_note: event.target.value }))}
                            placeholder="อธิบายว่าใช้ช่วงนี้เพื่อวิจารณ์อะไร"
                            className="rounded-xl border border-white/[0.1] bg-black/20 px-3 py-2 text-xs text-white outline-none"
                          />
                        )}
                        <label className="flex items-center gap-2 text-[11px] text-slate-300">
                          <input
                            type="checkbox"
                            checked={sourceDraft.rights_reviewed}
                            onChange={(event) => setSourceDraft((current) => ({ ...current, rights_reviewed: event.target.checked }))}
                            className="rounded border-white/20 bg-black/40 text-cyan-400 focus:ring-0"
                          />
                          สิทธิ์และนโยบายผ่านการตรวจสอบแล้ว
                        </label>
                        <button
                          type="button"
                          onClick={addSource}
                          disabled={saving}
                          className="min-h-9 rounded-xl border border-cyan-400/30 bg-cyan-400/[0.08] text-xs font-bold text-cyan-200 hover:bg-cyan-400/[0.15] disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          <Plus className="w-3.5 h-3.5" /> เพิ่มแหล่งที่มา
                        </button>
                      </div>
                    </div>

                    {/* Slot Analytics Entry */}
                    <div className="border-t border-white/[0.08] pt-4">
                      <h4 className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                        <BarChart3 className="w-3.5 h-3.5 text-cyan-300" />
                        บันทึกผลสถิติหลังโพสต์ (Analytics)
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-slate-400">ยอดวิว (Views)</label>
                          <input
                            type="number"
                            value={draft.metrics.views || ''}
                            onChange={(e) => setDraft((curr) => ({
                              ...curr,
                              metrics: { ...curr.metrics, views: Math.max(0, parseInt(e.target.value, 10) || 0) },
                            }))}
                            placeholder="0"
                            className="mt-1 w-full rounded-lg border border-white/[0.1] bg-black/20 px-2.5 py-1.5 text-xs text-white outline-none"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-400">ดูจบ % (Completion)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={draft.metrics.completion_rate || ''}
                            onChange={(e) => setDraft((curr) => ({
                              ...curr,
                              metrics: { ...curr.metrics, completion_rate: Math.max(0, parseFloat(e.target.value) || 0) },
                            }))}
                            placeholder="0.0"
                            className="mt-1 w-full rounded-lg border border-white/[0.1] bg-black/20 px-2.5 py-1.5 text-xs text-white outline-none"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-400">คอมเมนต์</label>
                          <input
                            type="number"
                            value={draft.metrics.comments || ''}
                            onChange={(e) => setDraft((curr) => ({
                              ...curr,
                              metrics: { ...curr.metrics, comments: Math.max(0, parseInt(e.target.value, 10) || 0) },
                            }))}
                            placeholder="0"
                            className="mt-1 w-full rounded-lg border border-white/[0.1] bg-black/20 px-2.5 py-1.5 text-xs text-white outline-none"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-400">ผู้ติดตามเพิ่ม (Follows)</label>
                          <input
                            type="number"
                            value={draft.metrics.follows || ''}
                            onChange={(e) => setDraft((curr) => ({
                              ...curr,
                              metrics: { ...curr.metrics, follows: Math.max(0, parseInt(e.target.value, 10) || 0) },
                            }))}
                            placeholder="0"
                            className="mt-1 w-full rounded-lg border border-white/[0.1] bg-black/20 px-2.5 py-1.5 text-xs text-white outline-none"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Publish readiness badge and blockers */}
                    <div className={`rounded-xl border p-3 ${slotBlockers.length ? 'border-amber-500/30 bg-amber-500/[0.06]' : 'border-emerald-500/30 bg-emerald-500/[0.06]'}`}>
                      <div className="flex items-center justify-between text-xs font-black text-white">
                        <span className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-cyan-300" />
                          สถานะ Rights Gate & Readiness
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${slot.ready_to_publish ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                          {slot.ready_to_publish ? 'พร้อมเผยแพร่' : 'Private Rough Cut'}
                        </span>
                      </div>
                      {slotBlockers.length ? (
                        <ul className="mt-2 space-y-1 text-[11px] leading-5 text-amber-200">
                          {slotBlockers.map((blocker) => (
                            <li key={blocker}>• {blocker}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-2 text-[11px] text-emerald-200">
                          ตรวจสิทธิ์และข้อมูลครบถ้วน พร้อมสำหรับการเผยแพร่สู่ TikTok
                        </p>
                      )}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-slate-400">เลือก slot เพื่อเริ่มเขียน Hook และ Script</p>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, hint, tone = 'slate' }) {
  const toneClass = {
    slate: 'text-white',
    emerald: 'text-emerald-300',
    violet: 'text-[#F2B39D]',
    cyan: 'text-cyan-300',
    rose: 'text-rose-300',
  }[tone];
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] p-3">
      <p className="text-[10px] text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-black ${toneClass}`}>{value}</p>
      <p className="mt-1 text-[10px] text-slate-500">{hint}</p>
    </div>
  );
}


export default function GadgetMediaHub(props) {
  const [surface, setSurface] = useState('studio');
  const [studioSeed, setStudioSeed] = useState(null);

  const startProjectFromCampaign = (seed) => {
    setStudioSeed(seed);
    setSurface('studio');
  };

  return (
    <div className="space-y-4">
      <div className="inline-flex rounded-xl bg-[#0B0F19] p-1 ring-1 ring-white/[0.08]" role="tablist" aria-label="มุมมอง Gadget Media">
        <button
          type="button"
          role="tab"
          aria-selected={surface === 'studio'}
          onClick={() => setSurface('studio')}
          className={surfaceTabClasses(surface === 'studio')}
        >
          Product Studio
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={surface === 'campaign'}
          onClick={() => setSurface('campaign')}
          className={surfaceTabClasses(surface === 'campaign')}
        >
          Campaign และ Analytics
        </button>
      </div>

      {surface === 'studio' ? (
        <GadgetMediaStudio key={props.initialProjectId || 'library'} initialProjectId={props.initialProjectId || ''} seed={studioSeed} onSeedConsumed={() => setStudioSeed(null)} />
      ) : (
        <CampaignPlanner {...props} onCreateProductProject={startProjectFromCampaign} />
      )}
    </div>
  );
}


function surfaceTabClasses(active) {
  const base = 'h-9 rounded-lg px-4 text-xs font-black transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300';
  if (active) return `${base} bg-cyan-300 text-[#061116]`;
  return `${base} text-slate-300 hover:bg-white/[0.06]`;
}
