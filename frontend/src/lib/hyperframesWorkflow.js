/** Values are versioned creative inputs, not promises of generated visuals. */
export const HF_STYLE_PROFILES = Object.freeze([
  { id: 'tech_explainer', version: 1, label: 'อธิบายเทคโนโลยี', tokens: { background: '#0B1220', foreground: '#FFFFFF', accent: '#25F4EE', scene_strategy: 'question-detail-proof-summary', motion: 'measured' } },
  { id: 'pov_chat', version: 1, label: 'เล่าเรื่องผ่านแชท', tokens: { background: '#101815', foreground: '#FFFFFF', accent: '#66FF00', scene_strategy: 'conversation-reveal-detail', motion: 'message-reveal' } },
  { id: 'vs_battle', version: 1, label: 'เปรียบเทียบสินค้า', tokens: { background: '#14121B', foreground: '#FFFFFF', accent: '#FF6622', scene_strategy: 'paired-facts-verdict', motion: 'paired-comparison' } },
]);

export function productAngles(product) {
  return (Array.isArray(product?.angles) ? product.angles : []).filter(angle => angle.angle_id || angle.id);
}

export function latestWorkflowJob(rows) {
  if (!Array.isArray(rows) || !rows.length) return null;
  const time = value => typeof value === 'number' ? value * 1000 : Date.parse(value || '') || 0;
  return rows.reduce((latest, row) => !latest || time(row.created_at) >= time(latest.created_at) ? row : latest, null);
}

export function parseMediaRefs(text) {
  const paths = [...new Set(String(text || '').split(/\r?\n/).map(path => path.trim()).filter(Boolean))];
  if (paths.some(path => /^(?:[a-z][a-z0-9+.-]*:|[\\/])|(?:^|[\\/])\.\.(?:[\\/]|$)/i.test(path))) throw new Error('วัตถุดิบต้องเป็นไฟล์ภายในโปรเจกต์ ห้ามใช้ URL หรือ path นอกโปรเจกต์');
  return paths.map(path => ({ path: path.replaceAll('\\', '/') }));
}

export function draftFromProject(project) {
  const inputs = project?.inputs || {};
  return { sourceType: project?.source_binding?.type || 'product_angle', gadgetProjectId: project?.source_binding?.project_id || '', title: inputs.title || '', description: inputs.description || '', brief: inputs.brief || '', script: inputs.script || '', duration: String(inputs.duration_seconds || 30), audioMode: inputs.audio_mode || 'silent', styleId: inputs.style_profile?.id || 'tech_explainer', voicePath: inputs.voiceover_path || '', musicPath: inputs.music_path || '', productId: inputs.tiktok_product_id || '', mediaPaths: (inputs.media_refs || []).map(ref => typeof ref === 'string' ? ref : ref.path).filter(Boolean).join('\n') };
}

export function projectWorkflowJobs(project, authoringJobs, renderJobs) {
  const acceptedId = project?.accepted_revision?.id;
  const creative = latestWorkflowJob((authoringJobs || []).filter(job => job.base_revision === project?.revision || (acceptedId && job.submitted_revision?.id === acceptedId)));
  const pendingComposition = creative && creative.submitted_revision?.id !== acceptedId;
  const render = acceptedId && !pendingComposition ? latestWorkflowJob((renderJobs || []).filter(job => (job.snapshot?.id || job.artifact?.composition_revision) === acceptedId)) : null;
  return { creative, render };
}

export function makeProjectPayload({ product, angleId, draft }) {
  const productId = product?.id || product?.product_id;
  const sourceType = draft.sourceType || 'product_angle';
  if (!['product_angle', 'standalone', 'gadget_project'].includes(sourceType)) throw new Error('เลือกประเภทงานที่รองรับก่อน');
  if (sourceType === 'product_angle' && (!productId || !productAngles(product).some(angle => (angle.angle_id || angle.id) === angleId))) throw new Error('เลือกสินค้าและ Angle ที่มีอยู่จริงก่อน');
  if (sourceType === 'standalone' && !draft.title?.trim()) throw new Error('ตั้งชื่อคลิป standalone ก่อน');
  if (sourceType === 'gadget_project' && !draft.gadgetProjectId?.trim()) throw new Error('เลือกโปรเจกต์ Gadget ในช่องนี้ก่อน');
  const profile = HF_STYLE_PROFILES.find(item => item.id === draft.styleId);
  if (!profile) throw new Error('เลือกสไตล์ที่มี version ก่อน');
  const duration = Number(draft.duration);
  if (!Number.isFinite(duration) || duration <= 0 || duration >= 3600) throw new Error('ระบุความยาวมากกว่า 0 และน้อยกว่า 3600 วินาที');
  if (!draft.brief?.trim()) throw new Error('เขียนสิ่งที่ต้องการให้คลิปสื่อก่อน');
  if (!['narration', 'music_only', 'silent'].includes(draft.audioMode)) throw new Error('เลือกโหมดเสียงก่อน');
  if (draft.audioMode === 'narration' && (!draft.script?.trim() || !draft.voicePath?.trim())) throw new Error('โหมดพากย์ต้องมีบทที่ยอมรับแล้วและไฟล์เสียงจริง');
  if (draft.audioMode === 'music_only' && !draft.musicPath?.trim()) throw new Error('โหมดดนตรีต้องเลือกไฟล์เพลงจริง');
  const { label: _label, ...style } = profile;
  return {
    source_binding: sourceType === 'product_angle' ? { type: sourceType, product_id: productId, angle_id: angleId } : sourceType === 'gadget_project' ? { type: sourceType, project_id: draft.gadgetProjectId.trim() } : { type: sourceType },
    inputs: {
      brief: draft.brief.trim(), duration_seconds: duration, audio_mode: draft.audioMode,
      ...(sourceType === 'standalone' ? { title: draft.title.trim(), description: draft.description?.trim() || '' } : {}),
      style_profile: structuredClone(style), script: draft.script?.trim() || '',
      ...(draft.audioMode === 'narration' ? { voiceover_path: draft.voicePath.trim() } : {}),
      ...(draft.audioMode !== 'silent' && draft.musicPath?.trim() ? { music_path: draft.musicPath.trim() } : {}),
      media_refs: draft.mediaPaths !== undefined ? parseMediaRefs(draft.mediaPaths) : Array.isArray(draft.mediaRefs) ? structuredClone(draft.mediaRefs) : [],
      ...(draft.productId?.trim() ? { tiktok_product_id: draft.productId.trim() } : {}),
    },
  };
}

const RUNNING = new Set(['queued', 'render_queued', 'claimed', 'running', 'rendering', 'validating', 'finalizing', 'cancel_requested']);
export function shouldPollRender(job) { return !!job && RUNNING.has(job.status || job.phase); }
export function renderActions(job) {
  const status = job?.status || job?.phase;
  return {
    cancel: !!job && RUNNING.has(status) && !['finalizing', 'cancel_requested'].includes(status),
    retry: ['failed', 'interrupted'].includes(status),
    finalize: status === 'qc_ready' && !!job?.artifact?.path && !!job.artifact.sha256,
  };
}

export function makeFinalizePayload(project, job, form) {
  if (!project?.id && !project?.project_id) throw new Error('ไม่พบโปรเจกต์ที่บันทึกแล้ว');
  if (!renderActions(job).finalize) throw new Error('รอคลิปที่ผ่านการเรนเดอร์และตรวจไฟล์ก่อน');
  if (!form.reviewed) throw new Error('ดูคลิปจริงและยืนยันการตรวจคลิปก่อนส่งออก');
  if (!Number.isInteger(job.revision) || job.revision < 1) throw new Error('ไม่พบ revision ของงานเรนเดอร์ กรุณาตรวจสถานะล่าสุด');
  return { expected_revision: job.revision, artifact_hash: job.artifact.sha256, publish_package: { caption: form.caption?.trim() || '', hashtags: String(form.hashtags || '').split(/\s+/).filter(Boolean), ...(project.inputs?.tiktok_product_id ? { tiktok_product_id: project.inputs.tiktok_product_id } : {}), ...(form.coverPath?.trim() ? { cover_path: form.coverPath.trim(), cover_format: '9x16' } : {}) } };
}

export function handoffText(packet) {
  if (!packet?.work_id || !packet?.work_path || !packet?.input_hash) throw new Error('แพ็กเกจงาน AI ยังไม่ครบ');
  if (/^(?:[a-z]:|\/)|(?:^|[\\/])\.\.(?:[\\/]|$)/i.test(packet.work_path)) throw new Error('ขอบเขตงาน AI ไม่ถูกต้อง');
  return `ทำงาน HyperFrames ตามแพ็กเกจที่แอปบันทึกไว้ ใช้ API claim / heartbeat / checkpoint / submit และเขียนเฉพาะ work_path ห้ามแก้ฐานข้อมูลหรือโพสต์\n\n${JSON.stringify(packet, null, 2)}`;
}

export function workflowStep(project, creative, render) {
  if (!project) return 0;
  if (creative && creative.submitted_revision?.id !== project.accepted_revision?.id) return creative.status === 'submitted' ? 2 : 1;
  if (render?.export_id || render?.status === 'finalized') return 4;
  if (render) return 3;
  if (project.accepted_revision) return 2;
  return creative?.status === 'submitted' ? 2 : 1;
}

export const HF_STATUS_LABELS = { queued: 'รอเริ่มงาน', authoring: 'AI รับงานแล้ว', submitted: 'ส่ง revision แล้ว รอตรวจ', rendering: 'กำลังเรนเดอร์', running: 'กำลังทำงาน', validating: 'กำลังตรวจไฟล์', finalizing: 'กำลังลงทะเบียนผลงาน', qc_ready: 'พร้อมดูคลิปจริง', review_ready: 'พร้อมดูคลิปจริง', rendered: 'เรนเดอร์เสร็จ', completed: 'งานเสร็จ', finalized: 'ส่งออกและลงทะเบียนแล้ว', recovery_required: 'ต้องตรวจและกู้คืนการส่งออก', failed: 'งานล้มเหลว', interrupted: 'งานถูกขัดจังหวะ', cancelled: 'ยกเลิกแล้ว', cancel_requested: 'กำลังหยุดงาน' };

export function renderPhaseLabel(phase) {
  return ({ queued: 'รอประมวลผล', validating_snapshot: 'ตรวจ revision และวัตถุดิบ', awaiting_final_review: 'ยืนยันคลิปก่อนส่งออก', finalizing: 'ลงทะเบียนผลงาน', finalized: 'ผลงานพร้อมใน Gallery', recovery_required: 'ตรวจผลการส่งออกเดิม', interrupted: 'ทำต่อจาก revision เดิมได้', cancelled: 'หยุดงานแล้ว' })[phase] || '';
}
