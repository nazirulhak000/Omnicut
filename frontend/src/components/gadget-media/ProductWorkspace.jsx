import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, CheckCircle2, CircleAlert, Loader2, RefreshCw } from 'lucide-react';

import {
  approveGadgetMediaRender,
  buildGadgetMediaTimeline,
  generateGadgetMediaNarration,
  getGadgetMediaProject,
  getGadgetMediaTimeline,
  getRenderStatus,
  probeGadgetMediaSource,
  renderGadgetMediaProject,
  saveGadgetMediaTimeline,
  updateGadgetMediaProject,
  validateGadgetMediaProject,
} from '../../api.js';
import { projectDisplayName, STATUS_LABELS } from '../../lib/gadgetMediaProject.js';
import QualityInspector from './QualityInspector.jsx';
import StageRail from './StageRail.jsx';
import {
  BriefStage,
  CutStage,
  EvidenceStage,
  ReviewStage,
  SourcesStage,
  StoryStage,
} from './stages/StageForms.jsx';


const STATUS_STAGE = {
  brief: 'brief', sourcing: 'sources', source_ready: 'evidence', research_ready: 'story',
  script_ready: 'cut', in_production: 'cut', review_required: 'review', ready_to_render: 'review',
  rendered: 'review', approved: 'review', published: 'review',
};


export default function ProductWorkspace({ projectId, onBack, onProjectChanged }) {
  const [project, setProject] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [activeStage, setActiveStage] = useState('brief');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saveState, setSaveState] = useState('saved');
  const [renderState, setRenderState] = useState({ running: false, percent: 0, message: '', error: false });
  const [narrationState, setNarrationState] = useState({ running: false, percent: 0, message: '', error: false });
  const pollTimer = useRef(null);
  const narrationPollTimer = useRef(null);
  const pollRenderRef = useRef(null);
  const pollNarrationRef = useRef(null);

  const load = useCallback(async ({ keepStage = true } = {}) => {
    setLoading(true);
    setError('');
    try {
      const nextProject = await getGadgetMediaProject(projectId);
      setProject(nextProject);
      if (!keepStage) setActiveStage(STATUS_STAGE[nextProject.status] || 'brief');
      try {
        setTimeline(await getGadgetMediaTimeline(projectId));
      } catch (timelineError) {
        if (timelineError?.response?.status === 404) setTimeline(null);
        else throw timelineError;
      }
      onProjectChanged?.();
    } catch (loadError) {
      setError(loadError?.response?.data?.detail || loadError?.message || 'โหลด Product Workspace ไม่สำเร็จ');
    } finally {
      setLoading(false);
    }
  }, [onProjectChanged, projectId]);

  useEffect(() => {
    queueMicrotask(() => load({ keepStage: false }));
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
      if (narrationPollTimer.current) clearTimeout(narrationPollTimer.current);
    };
  }, [load]);

  const acceptProject = (nextProject) => {
    setProject(nextProject);
    onProjectChanged?.();
    return nextProject;
  };

  const saveProject = async (payload, successMessage = 'บันทึก Project แล้ว') => {
    setBusy(true);
    setSaveState('saving');
    setError('');
    setNotice('');
    try {
      const saved = await updateGadgetMediaProject(projectId, payload);
      acceptProject(saved);
      setSaveState('saved');
      setNotice(successMessage);
      setActiveStage(STATUS_STAGE[saved.status] || activeStage);
      return saved;
    } catch (saveError) {
      setSaveState('error');
      setError(saveError?.response?.data?.detail || saveError?.message || 'บันทึก Project ไม่สำเร็จ');
      throw saveError;
    } finally {
      setBusy(false);
    }
  };

  const probeSource = async (payload) => {
    const response = await probeGadgetMediaSource(projectId, payload);
    acceptProject(response.project);
    setNotice(`ตรวจ Source ${response.source.width}×${response.source.height} สำเร็จ`);
    return response;
  };

  const buildTimeline = async () => {
    setBusy(true);
    setError('');
    try {
      const response = await buildGadgetMediaTimeline(projectId);
      setTimeline(response.timeline);
      acceptProject(response.project);
      setNotice('สร้าง Assembly Timeline ใน namespace GadgetMedia แล้ว');
    } catch (buildError) {
      setError(buildError?.response?.data?.detail || buildError?.message || 'สร้าง Timeline ไม่สำเร็จ');
      throw buildError;
    } finally {
      setBusy(false);
    }
  };

  const saveTimeline = async (value) => {
    const response = await saveGadgetMediaTimeline(projectId, value);
    setTimeline(response.timeline);
    acceptProject(response.project);
    setNotice('บันทึก Timeline แล้ว');
  };

  const validateQuality = async () => {
    setBusy(true);
    setError('');
    try {
      const response = await validateGadgetMediaProject(projectId);
      acceptProject(response.project);
      setNotice(response.report.passed ? 'ผ่าน Hard Gate ทั้งหมด พร้อม Render' : `พบ ${response.report.blockers.length} blocker`);
    } catch (qualityError) {
      setError(qualityError?.response?.data?.detail || qualityError?.message || 'ตรวจ Quality ไม่สำเร็จ');
    } finally {
      setBusy(false);
    }
  };

  const pollRender = useCallback(async (jobId) => {
    try {
      const status = await getRenderStatus(jobId);
      const percent = Math.round((Number(status.progress) || 0) * 100);
      if (status.status === 'completed') {
        setRenderState({ running: false, percent: 100, message: 'Render Master เสร็จแล้ว กรุณาตรวจและอนุมัติ Version', error: false });
        await load();
        return;
      }
      if (['failed', 'cancelled'].includes(status.status)) {
        setRenderState({ running: false, percent, message: status.error || status.message || 'Render ไม่สำเร็จ', error: true });
        return;
      }
      setRenderState({ running: true, percent, message: status.message || 'กำลัง Render', error: false });
      pollTimer.current = setTimeout(() => pollRenderRef.current?.(jobId), 1000);
    } catch (pollError) {
      setRenderState({ running: false, percent: 0, message: pollError?.response?.data?.detail || 'ติดตามสถานะ Render ไม่สำเร็จ', error: true });
    }
  }, [load]);
  useEffect(() => {
    pollRenderRef.current = pollRender;
  }, [pollRender]);

  const pollNarration = useCallback(async (jobId) => {
    try {
      const status = await getRenderStatus(jobId);
      const percent = Math.round((Number(status.progress) || 0) * 100);
      if (status.status === 'completed') {
        setNarrationState({ running: false, percent: 100, message: 'สร้าง Gemini TTS และผูกไฟล์เสียงกับ Project แล้ว', error: false });
        await load();
        return;
      }
      if (['failed', 'cancelled'].includes(status.status)) {
        setNarrationState({ running: false, percent, message: status.error || status.message || 'สร้าง Gemini TTS ไม่สำเร็จ', error: true });
        return;
      }
      setNarrationState({ running: true, percent, message: status.message || 'กำลังสร้าง Gemini TTS', error: false });
      narrationPollTimer.current = setTimeout(() => pollNarrationRef.current?.(jobId), 1000);
    } catch (pollError) {
      setNarrationState({ running: false, percent: 0, message: pollError?.response?.data?.detail || 'ติดตามสถานะ Gemini TTS ไม่สำเร็จ', error: true });
    }
  }, [load]);
  useEffect(() => {
    pollNarrationRef.current = pollNarration;
  }, [pollNarration]);

  const startNarration = async (blocks) => {
    setNarrationState({ running: true, percent: 0, message: 'กำลังบันทึก Story และส่งเข้าคิว Gemini TTS', error: false });
    try {
      const saved = await saveProject({
        story: { ...(project.story || {}), blocks },
        ...(project.status === 'research_ready' ? { status: 'script_ready' } : {}),
      }, 'บันทึก Story แล้ว กำลังสร้าง Gemini TTS');
      const response = await generateGadgetMediaNarration(projectId, {
        script_text: blocks.map((block) => block.text || '').join(' '),
        voice_preset: saved.presentation?.voice || 'gemini_fenrir_male_strong',
        ad_tone: saved.presentation?.ad_tone || 'commercial_expert',
        speed: Number(saved.presentation?.speed) || 1.15,
      });
      pollNarration(response.job_id);
    } catch (narrationError) {
      setNarrationState({ running: false, percent: 0, message: narrationError?.response?.data?.detail || narrationError?.message || 'เริ่มสร้าง Gemini TTS ไม่สำเร็จ', error: true });
    }
  };

  const startRender = async () => {
    setRenderState({ running: true, percent: 0, message: 'กำลังส่งเข้าคิว Render', error: false });
    try {
      const response = await renderGadgetMediaProject(projectId, { export_preset: 'post' });
      pollRender(response.job_id);
    } catch (renderError) {
      setRenderState({ running: false, percent: 0, message: renderError?.response?.data?.detail || renderError?.message || 'เริ่ม Render ไม่สำเร็จ', error: true });
    }
  };

  const approve = async (artifactId) => {
    setBusy(true);
    setError('');
    try {
      acceptProject(await approveGadgetMediaRender(projectId, artifactId));
      setNotice('เลือก Approved Master แล้ว Version อื่นยังเก็บเป็นประวัติ');
    } catch (approveError) {
      setError(approveError?.response?.data?.detail || approveError?.message || 'อนุมัติ Master ไม่สำเร็จ');
    } finally {
      setBusy(false);
    }
  };

  let stageContent = null;
  if (project) {
    const stageKey = `${project.project_id}-${project.updated_at}`;
    if (activeStage === 'brief') stageContent = <BriefStage key={stageKey} project={project} busy={busy} onSave={saveProject} />;
    else if (activeStage === 'sources') stageContent = <SourcesStage key={stageKey} project={project} busy={busy} onProbe={probeSource} onAdvance={(status) => saveProject({ status })} />;
    else if (activeStage === 'evidence') stageContent = <EvidenceStage key={stageKey} project={project} busy={busy} onSave={saveProject} />;
    else if (activeStage === 'story') stageContent = <StoryStage key={stageKey} project={project} busy={busy} narrationState={narrationState} onSave={saveProject} onGenerateNarration={startNarration} />;
    else if (activeStage === 'cut') stageContent = <CutStage key={stageKey} project={project} timeline={timeline} busy={busy} onSaveProject={saveProject} onBuildTimeline={buildTimeline} onSaveTimeline={saveTimeline} onSendReview={() => saveProject({ status: 'review_required' }, 'ส่งเข้า Review แล้ว')} />;
    else stageContent = <ReviewStage key={stageKey} project={project} timeline={timeline} busy={busy} renderState={renderState} onValidate={validateQuality} onRender={startRender} onApprove={approve} onRefresh={load} />;
  }

  if (loading && !project) return <div className="grid min-h-[420px] place-items-center rounded-2xl bg-[#0B0F19] text-sm text-slate-400 ring-1 ring-white/[0.08]"><Loader2 className="h-5 w-5 animate-spin" />กำลังเปิด Product Workspace</div>;
  if (!project) return <div className="rounded-2xl bg-rose-500/10 p-5 text-sm text-rose-200 ring-1 ring-rose-400/25">{error || 'ไม่พบ Product Video Project'}</div>;

  return (
    <div className="space-y-4">
      <header className="rounded-2xl bg-[#0B0F19] p-4 ring-1 ring-white/[0.08] sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <button type="button" onClick={onBack} aria-label="กลับ Product Library" className="grid h-10 w-10 flex-none place-items-center rounded-xl text-slate-300 ring-1 ring-white/[0.1] hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"><ArrowLeft className="h-4 w-4" /></button>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-black text-white sm:text-2xl">{projectDisplayName(project)}</h1>
              <p className="mt-1 text-xs text-slate-500">{project.project_id} · {STATUS_LABELS[project.status] || project.status}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`flex h-9 items-center gap-1.5 rounded-xl px-3 text-xs font-bold ${saveState === 'error' ? 'bg-rose-500/10 text-rose-200' : saveState === 'saving' ? 'bg-amber-500/10 text-amber-200' : 'bg-emerald-500/10 text-emerald-300'}`}>{saveState === 'saving' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : saveState === 'error' ? <CircleAlert className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}{saveState === 'saving' ? 'กำลังบันทึก' : saveState === 'error' ? 'บันทึกไม่สำเร็จ' : 'บันทึกแล้ว'}</span>
            <button type="button" onClick={() => load()} disabled={loading} className="flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-bold text-slate-200 ring-1 ring-white/[0.1] hover:bg-white/[0.06] disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> โหลดล่าสุด</button>
          </div>
        </div>
        <p className="mt-4 max-w-4xl text-sm leading-6 text-slate-400">{project.editorial_promise || 'หนึ่งสินค้า หนึ่งเรื่องเล่า หนึ่ง Approved Master'}</p>
      </header>

      <StageRail activeStage={activeStage} status={project.status} onChange={setActiveStage} />

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl bg-rose-500/10 px-3 py-2 text-sm text-rose-200 ring-1 ring-rose-400/25"><CircleAlert className="mt-0.5 h-4 w-4 flex-none" />{error}</div>}
      {notice && <div className="flex items-center justify-between gap-3 rounded-xl bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200 ring-1 ring-emerald-400/25"><span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 flex-none" />{notice}</span><button type="button" onClick={() => setNotice('')} className="text-xs font-bold text-emerald-100/70 hover:text-white">ปิด</button></div>}
      {narrationState.message && <div className={`rounded-xl px-3 py-2 text-sm ${narrationState.error ? 'bg-rose-500/10 text-rose-200 ring-1 ring-rose-400/25' : 'bg-[#D97757]/10 text-[#F6C5B4] ring-1 ring-[#D97757]/25'}`}>{narrationState.message}</div>}

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">{stageContent}</div>
        <QualityInspector project={project} timeline={timeline} />
      </div>
    </div>
  );
}
