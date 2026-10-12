import { cloneElement, useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { hyperframesWorkflowApi } from '../../api.js';
import { projectDisplayName } from '../../lib/gadgetMediaProject.js';
import { registerChannelSwitchParticipant } from '../../lib/channelRuntime.js';
import { HF_STYLE_PROFILES, HF_STATUS_LABELS, draftFromProject, handoffText, makeFinalizePayload, makeProjectPayload, productAngles, projectWorkflowJobs, renderActions, renderPhaseLabel, shouldPollRender, workflowStep } from '../../lib/hyperframesWorkflow.js';

const initialLayer = () => ({ path: '', x: '48', y: '48', width: '300', height: '180', start: '0', duration: '3' });
const initialDraft = () => ({ sourceType: 'product_angle', overlay: false, layers: [initialLayer()], title: '', description: '', gadgetProjectId: '', brief: '', script: '', duration: '30', audioMode: 'narration', styleId: 'tech_explainer', voicePath: '', musicPath: '', productId: '', mediaPaths: '' });
const fieldClass = 'w-full rounded-lg border border-white/15 bg-[#080B11] px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#25F4EE]/70 disabled:opacity-50';
const buttonClass = 'rounded-lg border border-white/15 px-4 py-2 text-slate-200 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE] disabled:cursor-not-allowed disabled:opacity-40';
const primaryClass = 'rounded-lg bg-[#25F4EE] px-4 py-2 font-semibold text-slate-950 hover:bg-[#57F7F1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:cursor-not-allowed disabled:opacity-40';
const idOf = value => value?.project_id || value?.id;
const savedKey = channel => `omnicut.hf.workflow.${channel}`;

function Field({ label, children, hint }) {
  const id = useId();
  return <div className="block space-y-2"><label htmlFor={id} className="text-slate-300">{label}</label>{cloneElement(children, { id, ...(hint ? { 'aria-describedby': `${id}-hint` } : {}) })}{hint && <span id={`${id}-hint`} className="block text-slate-400">{hint}</span>}</div>;
}

export default function HyperFramesWorkflow({ products = [], channelId, onOpenGallery, onOpenGadgetReview, service = hyperframesWorkflowApi }) {
  const headingId = useId();
  const [projects, setProjects] = useState([]);
  const [gadgetProjects, setGadgetProjects] = useState([]);
  const [aiCapabilities, setAiCapabilities] = useState(null);
  const [overlayMaster, setOverlayMaster] = useState(null);
  const [overlayApproved, setOverlayApproved] = useState(false);
  const [project, setProject] = useState(null);
  const [creative, setCreative] = useState(null);
  const [render, setRender] = useState(null);
  const [packet, setPacket] = useState(null);
  const [draft, setDraft] = useState(initialDraft);
  const [productId, setProductId] = useState('');
  const [angleId, setAngleId] = useState('');
  const [dirty, setDirty] = useState(false);
  const [editing, setEditing] = useState(false);
  const [publishDirty, setPublishDirty] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [revisionReviewed, setRevisionReviewed] = useState(false);
  const [publish, setPublish] = useState({ caption: '', hashtags: '', coverPath: '', reviewed: false });
  const epoch = useRef(0);
  const dirtyRef = useRef(false);
  const saveRef = useRef(null);
  const scope = useRef(channelId);
  scope.current = channelId;
  dirtyRef.current = dirty || publishDirty;
  const product = useMemo(() => products.find(item => (item.id || item.product_id) === productId), [products, productId]);
  const angles = productAngles(product);
  const actions = renderActions(render);
  const step = workflowStep(project, creative, render);
  const creativeActive = ['queued', 'authoring'].includes(creative?.status);
  const acceptedIsCurrent = !!project?.accepted_revision && (!creative || creative.submitted_revision?.id === project.accepted_revision.id);

  const resetDraft = useCallback(() => { setDraft(initialDraft()); setProductId(''); setAngleId(''); setDirty(false); setEditing(false); }, []);
  const loadProject = useCallback(async (id, token = epoch.current) => {
    const requestedChannel = scope.current;
    const response = await service.getProject(id);
    if (token !== epoch.current || requestedChannel !== scope.current) return;
    setProject(response.project);
    setProjects(previous => previous.some(item => idOf(item) === id) ? previous.map(item => idOf(item) === id ? response.project : item) : [...previous, response.project]);
    const jobs = projectWorkflowJobs(response.project, response.authoring_jobs, response.render_jobs);
    setCreative(jobs.creative); setRender(jobs.render);
    try { sessionStorage.setItem(savedKey(scope.current), id); } catch { /* Optional reload convenience. */ }
    return response;
  }, [service]);

  useEffect(() => {
    const token = ++epoch.current;
    setProjects([]); setGadgetProjects([]); setAiCapabilities(null); setOverlayMaster(null); setOverlayApproved(false); setProject(null); setCreative(null); setRender(null); setPacket(null);
    setError(''); setNotice(''); setBusy(''); setRevisionReviewed(false);
    setPublish({ caption: '', hashtags: '', coverPath: '', reviewed: false }); setPublishDirty(false); resetDraft();
    if (!channelId || !service) return;
    service.listGadgetProjects?.().then(response => { if (token === epoch.current) setGadgetProjects(response.projects || []); }).catch(() => { /* Creation still validates source availability server-side. */ });
    service.aiCapabilities?.().then(response => { if (token === epoch.current) setAiCapabilities(response); }).catch(() => { if (token === epoch.current) setAiCapabilities({ available: false, status: 'unavailable' }); });
    service.listProjects().then(async response => {
      if (token !== epoch.current) return;
      const rows = response.projects || [];
      setProjects(rows);
      let remembered = null;
      try { remembered = sessionStorage.getItem(savedKey(channelId)); } catch { /* Optional. */ }
      if (rows.some(item => idOf(item) === remembered)) await loadProject(remembered, token);
    }).catch(issue => { if (token === epoch.current) setError(issue.friendlyMessage || issue.message); });
    return () => { ++epoch.current; };
  }, [channelId, service, loadProject, resetDraft]);

  useEffect(() => {
    const open = event => {
      const { channelId: owner, projectId } = event.detail || {};
      if (owner !== scope.current || !projectId) return;
      if (dirtyRef.current) { setError('บันทึกหรือทิ้งการแก้ไขก่อนเปิดงานจาก Activity Center'); return; }
      const token = ++epoch.current;
      setPacket(null); setProject(null); setCreative(null); setRender(null); setBusy('open'); setError('');
      loadProject(projectId, token).catch(issue => {
        if (token === epoch.current) setError(issue.friendlyMessage || issue.message);
      }).finally(() => { if (token === epoch.current) setBusy(''); });
    };
    window.addEventListener('omnicut:open-hyperframes', open);
    return () => window.removeEventListener('omnicut:open-hyperframes', open);
  }, [loadProject]);

  useEffect(() => registerChannelSwitchParticipant({
    id: 'hyperframes-workflow', isDirty: () => dirtyRef.current,
    save: () => saveRef.current?.(), discard: () => { resetDraft(); setPublish({ caption: '', hashtags: '', coverPath: '', reviewed: false }); setPublishDirty(false); dirtyRef.current = false; },
  }), [resetDraft]);
  useEffect(() => {
    if (!dirty && !publishDirty) return;
    const warn = event => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, publishDirty]);
  useEffect(() => { setRevisionReviewed(false); }, [project?.project_id, creative?.id, creative?.submitted_revision?.id]);
  useEffect(() => { setPublish(previous => ({ ...previous, reviewed: false })); }, [render?.id, render?.artifact?.sha256]);

  const run = async (name, task) => {
    const token = epoch.current;
    const channel = channelId;
    setBusy(name); setError(''); setNotice('');
    try { await task(token); }
    catch (issue) { if (token === epoch.current && channel === scope.current) setError(issue.friendlyMessage || issue.message); }
    finally { if (token === epoch.current && channel === scope.current) setBusy(''); }
  };
  const create = async () => {
    const token = epoch.current;
    const payload = makeProjectPayload({ product, angleId, draft: draft.overlay ? { ...draft, audioMode: 'silent' } : draft });
    let response;
    if (draft.overlay) {
      if (!overlayMaster || !overlayApproved) throw new Error('ตรวจและยืนยัน approved master รุ่นนี้ก่อนสร้าง overlay');
      const layers = draft.layers.map(layer => ({ path: layer.path.trim(), ...Object.fromEntries(['x', 'y', 'width', 'height', 'start', 'duration'].map(key => [key, Number(layer[key])])) }));
      response = await service.createOverlay({ ...payload, approval: { approved: true, master_digest: overlayMaster.master_digest }, layers });
    } else response = await service.createProject(payload);
    if (token !== epoch.current) return;
    setProjects(previous => [...previous, response.project]);
    setProject(response.project); setCreative(response.job || null); setRender(null); setPacket(null); setDirty(false);
    dirtyRef.current = false;
    try { sessionStorage.setItem(savedKey(channelId), idOf(response.project)); } catch { /* Optional. */ }
    setNotice('บันทึก brief แล้ว เตรียมส่งงานให้ AI ได้');
  };
  const inspectMaster = () => run('overlay-inspect', async token => {
    if (!draft.gadgetProjectId) throw new Error('เลือกโปรเจกต์ Gadget ก่อน');
    setOverlayMaster(null); setOverlayApproved(false);
    const response = await service.inspectOverlay({ source_binding: { type: 'gadget_project', project_id: draft.gadgetProjectId } });
    if (token === epoch.current) { setOverlayMaster(response.master); setOverlayApproved(false); setDraft(previous => ({ ...previous, duration: String(response.master.specs.duration) })); }
  });
  useEffect(() => { setOverlayMaster(null); setOverlayApproved(false); }, [draft.gadgetProjectId, draft.sourceType, draft.overlay]);
  const saveInputs = async () => {
    if (!project) return create();
    const token = epoch.current;
    const parent = products.find(item => (item.id || item.product_id) === project.source_binding.product_id);
    const payload = makeProjectPayload({ product: parent, angleId: project.source_binding.angle_id, draft });
    const response = await service.updateProject(idOf(project), { expected_revision: project.revision, inputs: payload.inputs });
    if (token !== epoch.current) return;
    setProject(response.project); setCreative(null); setRender(null); setPacket(null); setDirty(false); setEditing(false);
    dirtyRef.current = false;
    setProjects(previous => previous.map(item => idOf(item) === idOf(response.project) ? response.project : item));
    setNotice('บันทึก brief รุ่นใหม่แล้ว ผลงานและคิวเก่ายังคงไฟล์เดิม เตรียมงาน AI รุ่นใหม่ได้');
  };
  const editInputs = () => {
    setDraft(draftFromProject(project)); setProductId(project.source_binding.product_id || ''); setAngleId(project.source_binding.angle_id || ''); setEditing(true); setDirty(false);
  };
  saveRef.current = () => {
    if (publishDirty) throw new Error('Caption หรือปกยังไม่ส่งออก กลับไปตรวจและส่งออก หรือเลือกทิ้งการแก้ไขก่อนเปลี่ยนช่อง');
    return editing ? saveInputs() : create();
  };

  useEffect(() => {
    if (!project || (!shouldPollRender(render) && !['queued', 'authoring'].includes(creative?.status))) return;
    const token = epoch.current;
    let stopped = false;
    let timer;
    const poll = async () => {
      try {
        const response = await service.getProject(idOf(project));
        if (stopped || token !== epoch.current) return;
        setProject(response.project);
        const jobs = projectWorkflowJobs(response.project, response.authoring_jobs, response.render_jobs);
        setCreative(jobs.creative); setRender(jobs.render);
      } catch (issue) { if (!stopped && token === epoch.current) setError(issue.friendlyMessage || issue.message); }
      if (!stopped && token === epoch.current) timer = setTimeout(poll, 2500);
    };
    timer = setTimeout(poll, 2500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [project?.project_id, creative?.status, render?.status, service]);

  const editDraft = changes => { setDraft(previous => ({ ...previous, ...changes })); setDirty(true); };
  const editPublish = changes => { setPublish(previous => ({ ...previous, ...changes })); setPublishDirty(true); };
  const refresh = () => run('refresh', token => loadProject(idOf(project), token));
  const prepareAI = () => run('handoff', async token => {
    const response = await service.createAuthoringJob(idOf(project), { expected_revision: project.revision });
    if (token !== epoch.current) return;
    const job = response.job;
    setCreative(job);
    const handoff = await service.getHandoff(job.id);
    if (token === epoch.current) setPacket(handoff.handoff);
    await loadProject(idOf(project), token);
  });
  const showHandoff = () => run('handoff', async token => {
    const response = await service.getHandoff(creative.id);
    if (token === epoch.current) setPacket(response.handoff);
  });
  const generateAI = () => run('ai-generate', async token => {
    let job = creative;
    if (!job || job.status !== 'queued') {
      const created = await service.createAuthoringJob(idOf(project), { expected_revision: project.revision });
      if (token !== epoch.current) return;
      job = created.job; setCreative(job);
    }
    const response = await service.generateAI(job.id, { expected_generation: job.generation, model: aiCapabilities.default_model, timeout_seconds: 120, max_output_tokens: 8192 });
    if (token !== epoch.current) return;
    setCreative(response.job); setPacket(null); setNotice('AI กำลังสร้าง composition งานยังต้องยอมรับ revision และตรวจคลิปก่อนส่งออก');
  });
  const cancelAI = () => run('ai-cancel', async token => {
    const response = await service.cancelAI(creative.id);
    if (token === epoch.current) setCreative(response.job);
  });
  const copyHandoff = () => run('copy', async token => {
    await navigator.clipboard.writeText(handoffText(packet));
    if (token === epoch.current) setNotice('คัดลอกคำสั่งพร้อมแพ็กเกจงานแล้ว นำไปให้ AI session ที่จะรับงาน');
  });
  const accept = () => run('accept', async token => {
    await service.acceptRevision(idOf(project), { expected_revision: project.revision, authoring_job_id: creative.id });
    await loadProject(idOf(project), token);
  });
  const startRender = (fresh = false) => run('render', async token => {
    const key = `${idOf(project)}:${project.accepted_revision.id}${fresh === true ? `:${crypto.randomUUID()}` : ''}`;
    const response = await service.createRenderJob(idOf(project), { expected_revision: project.revision, idempotency_key: key });
    if (token === epoch.current) setRender(response.job);
    await loadProject(idOf(project), token);
  });
  const changeRender = method => run(method, async token => {
    const response = await service[method](render.id);
    if (token === epoch.current) setRender(response.job);
  });
  const finalize = () => run('finalize', async token => {
    const response = await service.finalizeRender(render.id, makeFinalizePayload(project, render, publish));
    if (token === epoch.current) { setRender(response.job); setPublishDirty(false); }
    await loadProject(idOf(project), token);
  });

  return <section aria-labelledby={headingId} className="space-y-6 rounded-xl border border-white/10 bg-[#0D111A] p-4 sm:p-6">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-2"><h2 id={headingId} className="font-semibold text-white">ผลิตคลิปด้วย AI และส่งออกเข้าคิวเดิม</h2><p className="text-slate-400">บันทึกงาน เลือก AI ในแอปหรือ session ภายนอก แล้วตรวจคลิปจริงก่อนส่งออก</p></div>
      <span className="rounded-md bg-white/5 px-3 py-2 text-slate-300">ช่อง {channelId || 'ยังไม่ได้เลือก'}</span>
    </header>
    <ol className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="ขั้นตอนผลิตคลิป">{['บันทึก brief', 'ทำงานกับ AI', 'รับ revision', 'ตรวจคลิปจริง', 'เปิด Gallery / ตั้งเวลา'].map((label, index) => <li key={label} aria-current={step === index ? 'step' : undefined} className={`border-b-2 pb-2 ${step === index ? 'border-[#25F4EE] text-[#25F4EE]' : 'border-white/10 text-slate-400'}`}>{index + 1}. {label}</li>)}</ol>
    <p className="text-slate-400">รองรับคลิปสินค้า / Angle คลิปอิสระ และโปรเจกต์ Gadget เลือก AI ในแอปหรือ session ภายนอกได้ ผู้ใช้ตรวจฉากและคลิปก่อนส่งออก ส่วนงาน Gadget ต้องอนุมัติใน Review ก่อนเข้าคิวโพสต์</p>
    {error && <p role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-red-200">{error}</p>}
    {notice && <p role="status" className="text-[#25F4EE]">{notice}</p>}
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-1"><Field label="เปิดงานที่บันทึกแล้ว"><select className={fieldClass} value={idOf(project) || ''} disabled={!!busy || dirty || publishDirty} onChange={event => { const id = event.target.value; ++epoch.current; setPacket(null); setProject(null); setCreative(null); setRender(null); setRevisionReviewed(false); setPublish({ caption: '', hashtags: '', coverPath: '', reviewed: false }); if (id) run('open', token => loadProject(id, token)); }}><option value="">สร้างงานใหม่</option>{projects.map(item => <option key={idOf(item)} value={idOf(item)}>{item.inputs?.brief?.slice(0, 60) || item.project_name} · r{item.revision}</option>)}</select></Field></div>
      {project && <button className={buttonClass} disabled={!!busy} onClick={refresh}>ตรวจสถานะล่าสุด</button>}
      {project && !editing && <button className={buttonClass} disabled={!!busy || !!project.overlay_contract || creativeActive || shouldPollRender(render) || publishDirty} onClick={editInputs}>แก้ brief เพื่อสร้าง revision ใหม่</button>}
      {editing && <button className={buttonClass} disabled={!!busy} onClick={resetDraft}>ยกเลิกการแก้ brief</button>}
      {dirty && <button className={buttonClass} disabled={!!busy} onClick={resetDraft}>ยกเลิก brief ที่ยังไม่บันทึก</button>}
      {publishDirty && <button className={buttonClass} disabled={!!busy} onClick={() => { setPublish({ caption: '', hashtags: '', coverPath: '', reviewed: false }); setPublishDirty(false); dirtyRef.current = dirty; }}>ทิ้งข้อความและปกที่ยังไม่ส่งออก</button>}
    </div>
    {(!project || editing) && <form onSubmit={event => { event.preventDefault(); run('save', editing ? saveInputs : create); }} className="space-y-4">
      {editing && <p className="text-slate-400">แก้ brief ของงานเดิม สินค้าและ Angle คงเดิม เมื่อบันทึกต้องรับ composition ใหม่ก่อนเรนเดอร์ ผลงานที่ส่งออกและคิวเดิมไม่เปลี่ยนไฟล์</p>}
      <Field label="ประเภทงาน"><select className={fieldClass} value={draft.sourceType} disabled={editing} onChange={event => editDraft({ sourceType: event.target.value })}><option value="product_angle">คลิปสินค้า / Angle</option><option value="standalone">คลิปอิสระ (Standalone)</option><option value="gadget_project">คลิปจากโปรเจกต์ Gadget</option></select></Field>
      {draft.sourceType === 'product_angle' && <div className="grid gap-4 md:grid-cols-2"><Field label="สินค้า"><select required className={fieldClass} value={productId} disabled={editing} onChange={event => { setProductId(event.target.value); setAngleId(''); setDirty(true); }}><option value="">เลือกสินค้าในช่องนี้</option>{products.map(item => <option key={item.id || item.product_id} value={item.id || item.product_id}>{item.name || item.product_name || item.product_code || item.id}</option>)}</select></Field><Field label="Angle"><select required className={fieldClass} value={angleId} disabled={!product || editing} onChange={event => { setAngleId(event.target.value); setDirty(true); }}><option value="">เลือก Angle ของสินค้า</option>{angles.map(angle => <option key={angle.angle_id || angle.id} value={angle.angle_id || angle.id}>{angle.title || angle.name || angle.hook || angle.id}</option>)}</select></Field></div>}
      {draft.sourceType === 'standalone' && <><Field label="ชื่อคลิป"><input required maxLength={200} className={fieldClass} value={draft.title} onChange={event => editDraft({ title: event.target.value })} /></Field><Field label="ข้อมูลประกอบคลิป"><textarea rows={2} maxLength={8000} className={fieldClass} value={draft.description} onChange={event => editDraft({ description: event.target.value })} /></Field></>}
      {draft.sourceType === 'gadget_project' && <Field label="โปรเจกต์ Gadget" hint="ผลงานใหม่ต้องผ่าน Review ใน Gadget ก่อนส่งเข้าคิวโพสต์"><select required disabled={editing} className={fieldClass} value={draft.gadgetProjectId} onChange={event => editDraft({ gadgetProjectId: event.target.value })}><option value="">เลือกโปรเจกต์ในช่องนี้</option>{gadgetProjects.map(item => <option key={item.id || item.project_id} value={item.id || item.project_id}>{item.title || item.name || (item.product_identity ? projectDisplayName(item) : item.id || item.project_id)}</option>)}</select></Field>}
      {draft.sourceType === 'gadget_project' && !editing && <div className="space-y-4">
        <label className="flex items-start gap-3 text-slate-300"><input type="checkbox" className="mt-1 accent-[#25F4EE]" checked={draft.overlay} onChange={event => editDraft({ overlay: event.target.checked, audioMode: 'silent' })} />เพิ่มกราฟิกบน approved master โดยรักษาภาพ เสียง และความยาวเดิม</label>
        {draft.overlay && <section className="space-y-4 border-t border-white/10 pt-4" aria-label="กราฟิกบน master">
          <button type="button" className={buttonClass} disabled={!!busy || !draft.gadgetProjectId} onClick={inspectMaster}>ตรวจ approved master</button>
          {overlayMaster && <div className="space-y-2"><p className="break-all text-slate-300">{overlayMaster.artifact_id} · {overlayMaster.specs.duration} วินาที · 1080×1920 / 30 FPS</p><label className="flex items-start gap-3 text-slate-300"><input type="checkbox" className="mt-1 accent-[#25F4EE]" checked={overlayApproved} onChange={event => setOverlayApproved(event.target.checked)} />ยืนยันใช้ master รุ่นนี้เพื่อสร้างคลิปใหม่ ต้นฉบับยังคงเดิม</label></div>}
          {(draft.layers || []).map((layer, index) => <fieldset key={index} className="space-y-3"><legend className="mb-2 text-slate-200">กราฟิกชิ้นที่ {index + 1}</legend><Field label="ไฟล์ภาพ PNG/JPG/WebP" hint="ใช้ไฟล์ใน Assets กลางหรือโปรเจกต์ของช่องนี้"><input required className={fieldClass} value={layer.path} onChange={event => editDraft({ layers: draft.layers.map((value, i) => i === index ? { ...value, path: event.target.value } : value) })} /></Field><div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{[['x', 'ตำแหน่ง X'], ['y', 'ตำแหน่ง Y'], ['width', 'ความกว้าง'], ['height', 'ความสูง'], ['start', 'เริ่มที่ (วินาที)'], ['duration', 'แสดงนาน (วินาที)']].map(([key, label]) => <Field key={key} label={label}><input required type="number" step="0.1" min="0" className={fieldClass} value={layer[key]} onChange={event => editDraft({ layers: draft.layers.map((value, i) => i === index ? { ...value, [key]: event.target.value } : value) })} /></Field>)}</div>{draft.layers.length > 1 && <button type="button" className={buttonClass} onClick={() => editDraft({ layers: draft.layers.filter((_, i) => i !== index) })}>นำกราฟิกชิ้นนี้ออก</button>}</fieldset>)}
          <button type="button" className={buttonClass} disabled={draft.layers.length >= 24} onClick={() => editDraft({ layers: [...draft.layers, initialLayer()] })}>เพิ่มกราฟิกอีกชิ้น</button>
          <p className="text-slate-400">กราฟิกต้องอยู่ในช่วง X 48–900 และ Y 48–1500 รวมขนาดแล้ว และอยู่ในความยาวเดิมของคลิป ใช้ภาพนิ่งโดยไม่แก้ฟอนต์หรือเสียงของ master</p>
        </section>}
      </div>}
      <Field label="Brief ที่ต้องการให้ AI ทำ"><textarea required rows={3} className={fieldClass} value={draft.brief} onChange={event => editDraft({ brief: event.target.value })} /></Field>
      <div className="grid gap-4 sm:grid-cols-3"><Field label="สไตล์"><select className={fieldClass} value={draft.styleId} onChange={event => editDraft({ styleId: event.target.value })}>{HF_STYLE_PROFILES.map(style => <option key={style.id} value={style.id}>{style.label} · v{style.version}</option>)}</select></Field><Field label="ความยาว (วินาที)"><input required type="number" min="1" max="3599" step="0.1" className={fieldClass} value={draft.duration} disabled={draft.overlay} onChange={event => editDraft({ duration: event.target.value })} /></Field><Field label="เสียง"><select className={fieldClass} value={draft.audioMode} disabled={draft.overlay} onChange={event => editDraft({ audioMode: event.target.value })}><option value="narration">เสียงพากย์</option><option value="music_only">ดนตรี ไม่มีเสียงพากย์</option><option value="silent">ไม่มีเสียง</option></select></Field></div>
      <Field label={draft.audioMode === 'narration' ? 'บทที่ยอมรับแล้ว' : 'บทหรือข้อความในฉาก'}><textarea required={draft.audioMode === 'narration'} rows={3} className={fieldClass} value={draft.script} onChange={event => editDraft({ script: event.target.value })} /></Field>
      <Field label="วัตถุดิบที่ AI ใช้ (ถ้ามี)" hint="ระบุไฟล์ภายในโปรเจกต์ หนึ่งไฟล์ต่อบรรทัด เช่น 01_Raw/สินค้า/ภาพสินค้า.png ใช้ข้อมูลจริงของสินค้านี้เท่านั้น"><textarea rows={2} className={fieldClass} value={draft.mediaPaths} onChange={event => editDraft({ mediaPaths: event.target.value })} /></Field>
      {draft.audioMode === 'narration' && <Field label="ไฟล์เสียงพากย์ที่มีอยู่จริง" hint="ใช้ path ภายในโปรเจกต์ แอปตรวจไฟล์และ hash ก่อนสร้างงาน AI"><input required className={fieldClass} value={draft.voicePath} onChange={event => editDraft({ voicePath: event.target.value })} /></Field>}
      {draft.audioMode !== 'silent' && <Field label="ไฟล์ดนตรี" hint="ระบุ path ภายในโปรเจกต์ โหมดดนตรีต้องมีไฟล์จริง"><input required={draft.audioMode === 'music_only'} className={fieldClass} value={draft.musicPath} onChange={event => editDraft({ musicPath: event.target.value })} /></Field>}
      <Field label="TikTok product ID สำหรับตะกร้า (ถ้ามี)"><input className={fieldClass} value={draft.productId} onChange={event => editDraft({ productId: event.target.value })} /></Field>
      <p className="text-slate-400">สไตล์เป็นข้อกำหนดที่ส่งให้ AI ภาพจริงต้องตรวจ revision อีกครั้ง ไม่สร้างเสียงพากย์จำลอง</p>
      <button className={primaryClass} disabled={!!busy || !channelId || !service} type="submit">{busy === 'save' ? 'กำลังบันทึก' : editing ? 'บันทึก brief รุ่นใหม่' : 'บันทึก brief และเจ้าของงาน'}</button>
    </form>}
    {project && !editing && <div className="space-y-5">
      {project.source_binding.type === 'gadget_project' && onOpenGadgetReview && <button className={buttonClass} disabled={!!busy || publishDirty} onClick={() => onOpenGadgetReview(project.source_binding.project_id)}>เปิดโปรเจกต์ Gadget เพื่อตรวจและอนุมัติคลิป</button>}
      <div className="border-l-2 border-[#25F4EE] pl-4"><p className="text-white">{project.inputs?.brief || project.project_name}</p><p className="mt-2 text-slate-400">revision {project.revision} · {project.inputs?.duration_seconds} วินาที · {project.inputs?.audio_mode}</p></div>
      {creative && !creativeActive && !shouldPollRender(render) && <button className={buttonClass} disabled={!!busy || publishDirty} onClick={prepareAI}>ขอ revision ใหม่จาก brief ที่บันทึกไว้</button>}
      <section className="space-y-3 border-t border-white/10 pt-5" aria-label="AI ในแอป">
        <h3 className="font-semibold text-white">สร้าง composition ด้วย AI ในแอป</h3>
        <p className="text-slate-400">เรียก Gemini ด้วย API ที่ตั้งค่าไว้ ใช้โควต้าหรือเครดิตของบัญชี รุ่น {aiCapabilities?.default_model || 'ตามการตั้งค่า'} จำกัดคำตอบ 8,192 tokens และรอไม่เกิน 120 วินาที ผลงานยังต้องผ่านการยอมรับ revision และตรวจคลิป</p>
        {!aiCapabilities?.available && <p className="text-amber-200">{aiCapabilities?.status === 'missing_key' ? 'ตั้งค่า Gemini API key ในการตั้งค่าเดิมก่อน หรือใช้ AI session ภายนอก' : 'AI ในแอปยังไม่พร้อม ตรวจการตั้งค่า API/SDK หรือใช้ AI session ภายนอก'}</p>}
        {project.overlay_contract && <p className="text-slate-300">Overlay รุ่นนี้ล็อก master และกราฟิกแล้ว หากต้องการแก้ให้สร้างงาน overlay ใหม่</p>}
        <div className="flex flex-wrap gap-3"><button className={primaryClass} disabled={!!busy || !!project.overlay_contract || !aiCapabilities?.available || creative?.status === 'authoring' || shouldPollRender(render)} onClick={generateAI}>เริ่มสร้างด้วย AI ในแอป</button>{creative?.checkpoint?.provider && creative.status === 'authoring' && <button className={buttonClass} disabled={!!busy} onClick={cancelAI}>ยกเลิกการสร้างด้วย AI</button>}</div>
        {creative?.error && <p role="alert" className="text-red-200">{typeof creative.error === 'string' ? creative.error : JSON.stringify(creative.error)}</p>}
      </section>
      <section className="space-y-3" aria-label="งาน AI"><h3 className="font-semibold text-white">ทำงานกับ AI session</h3><p className="text-slate-300">{creative ? HF_STATUS_LABELS[creative.status] || creative.status : 'ยังไม่ได้เตรียมงานให้ AI'}</p>{creativeActive && creative?.checkpoint?.next_action && <p className="text-slate-400">ทำต่อ: {creative.checkpoint.next_action}</p>}<div className="flex flex-wrap gap-3">{!creative && <button className={primaryClass} disabled={!!busy} onClick={prepareAI}>เตรียมแพ็กเกจงาน AI</button>}{creative && <button className={buttonClass} disabled={!!busy} onClick={showHandoff}>เปิดคำสั่งรับงาน / ทำต่อ</button>}{packet && <button className={buttonClass} disabled={!!busy} onClick={copyHandoff}>คัดลอกคำสั่งให้ AI</button>}</div>{packet && <details className="rounded-lg border border-white/10 p-3"><summary className="cursor-pointer text-slate-300">ดูแพ็กเกจงานที่บันทึกแล้ว</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-all text-slate-400">{JSON.stringify(packet, null, 2)}</pre></details>}</section>
      {creative?.status === 'submitted' && creative.submitted_revision?.id !== project.accepted_revision?.id && <section className="space-y-3 border-t border-white/10 pt-5"><h3 className="font-semibold text-white">ตรวจ revision ที่ AI ส่งกลับ</h3><p className="text-slate-400">{creative.submitted_revision?.id} · {creative.submitted_revision?.files?.length || 0} dependencies ที่ตรึงแล้ว</p><p className="text-slate-400">เปิดดู composition ที่ AI ส่งให้ก่อน ยังไม่มี preview runtime ในหน้านี้</p><label className="flex items-start gap-3 text-slate-300"><input type="checkbox" checked={revisionReviewed} onChange={event => setRevisionReviewed(event.target.checked)} className="mt-1 accent-[#25F4EE]" />ตรวจ composition รุ่นนี้แล้ว และยอมรับให้เรนเดอร์รุ่นนี้</label><button className={primaryClass} disabled={!!busy || !revisionReviewed} onClick={accept}>รับ revision นี้</button></section>}
      {acceptedIsCurrent && !render && <section className="space-y-3 border-t border-white/10 pt-5"><h3 className="font-semibold text-white">เรนเดอร์จาก revision ที่ยอมรับแล้ว</h3><p className="break-all text-slate-400">{project.accepted_revision.id}</p><button className={primaryClass} disabled={!!busy} onClick={startRender}>เริ่มเรนเดอร์</button></section>}
      {acceptedIsCurrent && render?.status === 'cancelled' && <button className={buttonClass} disabled={!!busy} onClick={() => startRender(true)}>สร้างงานเรนเดอร์ใหม่จาก revision เดิม</button>}
      {render && <section className="space-y-4 border-t border-white/10 pt-5" aria-label="งานเรนเดอร์"><div className="flex flex-wrap justify-between gap-3"><h3 className="font-semibold text-white">{HF_STATUS_LABELS[render.status] || render.status}</h3><span className="text-slate-400">{renderPhaseLabel(render.phase)}</span></div>{render.error && <p role="alert" className="text-red-200">{typeof render.error === 'string' ? render.error : JSON.stringify(render.error)}</p>}<div className="flex flex-wrap gap-3">{actions.cancel && <button className={buttonClass} disabled={!!busy} onClick={() => changeRender('cancelRender')}>ยกเลิกงานเรนเดอร์</button>}{actions.retry && <button className={buttonClass} disabled={!!busy} onClick={() => changeRender('retryRender')}>ลองเรนเดอร์ revision เดิมอีกครั้ง</button>}</div>
        {render.artifact?.path && service.artifactUrl && <video controls preload="metadata" className="mx-auto max-h-[520px] w-full max-w-sm rounded-lg bg-black" src={service.artifactUrl(render.id, 'video')} />}
        {actions.finalize && <form className="space-y-4" onSubmit={event => { event.preventDefault(); finalize(); }}><p className="text-slate-400">ตรวจภาพ เสียง และข้อความในคลิปจริงก่อนลงทะเบียน การส่งออกยังไม่โพสต์ไป TikTok</p><Field label="Caption"><textarea rows={2} maxLength={4000} className={fieldClass} value={publish.caption} onChange={event => editPublish({ caption: event.target.value })} /></Field><Field label="Hashtags (คั่นด้วยช่องว่าง)"><input className={fieldClass} value={publish.hashtags} onChange={event => editPublish({ hashtags: event.target.value })} /></Field><Field label="ไฟล์ปก 9:16 (ถ้ามี)" hint="ต้องอยู่ในช่องนี้หรือคลัง Assets กลาง"><input className={fieldClass} value={publish.coverPath} onChange={event => editPublish({ coverPath: event.target.value })} /></Field>{project.inputs?.tiktok_product_id && <p className="text-slate-400">ตะกร้าที่บันทึกไว้: {project.inputs.tiktok_product_id}</p>}<label className="flex items-start gap-3 text-slate-300"><input type="checkbox" checked={publish.reviewed} onChange={event => editPublish({ reviewed: event.target.checked })} className="mt-1 accent-[#25F4EE]" />ดูคลิปจริงรุ่นนี้และยืนยันพร้อมส่งออกแล้ว</label><button type="submit" className={primaryClass} disabled={!!busy || !publish.reviewed}>ส่งออกและลงทะเบียนใน Gallery</button></form>}
        {render.status === 'recovery_required' && <div className="space-y-3"><p className="text-amber-200">การส่งออกมีผลบางส่วน ต้องตรวจ finalize intent ก่อนทำต่อ ห้ามสร้างคลิปใหม่หรือโพสต์ซ้ำเพื่อแก้ปัญหา</p>{service.repairRender && <button className={buttonClass} disabled={!!busy} onClick={() => changeRender('repairRender')}>ตรวจและกู้คืนการส่งออกเดิม</button>}</div>}
        {(render.export_id || render.status === 'finalized') && <div className="space-y-3"><p className="text-[#25F4EE]">ลงทะเบียนผลงานแล้ว {render.export_id}</p><p className="text-slate-400">เปิด Gallery เพื่อเลือกผลงานนี้และตั้งเวลาผ่านคิวเดิม ผู้ใช้ยังเป็นผู้กด extension</p>{onOpenGallery && <button className={primaryClass} onClick={() => onOpenGallery(render.export_id)}>เปิดผลงานใน Gallery</button>}</div>}
      </section>}
    </div>}
  </section>;
}
