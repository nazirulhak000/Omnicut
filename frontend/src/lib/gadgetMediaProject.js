export const PRODUCT_VIDEO_STAGES = Object.freeze([
  { id: 'brief', label: 'Brief', hint: 'สินค้าและคนดู' },
  { id: 'sources', label: 'Sources', hint: 'ไฟล์และสิทธิ์' },
  { id: 'evidence', label: 'Evidence', hint: 'Claim และหลักฐาน' },
  { id: 'story', label: 'Story', hint: 'เรื่องเล่า 45–60 วิ' },
  { id: 'cut', label: 'Cut', hint: 'EDL และ Timeline' },
  { id: 'review', label: 'Review', hint: 'ตรวจ Render อนุมัติ' },
]);

export const STORY_ROLE_OPTIONS = Object.freeze([
  ['hook', 'Hook'],
  ['product_reveal', 'Product Reveal'],
  ['hero_benefit', 'Hero Benefit'],
  ['proof', 'Proof'],
  ['use_case', 'Use Case'],
  ['caveat', 'Caveat'],
  ['verdict', 'Verdict'],
  ['cta', 'CTA'],
]);

export const FACT_TYPE_OPTIONS = Object.freeze([
  ['brand_claim', 'ข้อมูลจาก Brand'],
  ['verified_fact', 'ข้อมูลที่ตรวจสอบแล้ว'],
  ['opinion', 'ความคิดเห็นของช่อง'],
  ['caveat', 'ข้อจำกัด'],
]);

export const STATUS_LABELS = Object.freeze({
  brief: 'Brief',
  sourcing: 'กำลังเตรียม Source',
  source_ready: 'Source พร้อม',
  research_ready: 'Evidence พร้อม',
  script_ready: 'Story พร้อม',
  in_production: 'กำลังตัดต่อ',
  review_required: 'รอตรวจ',
  ready_to_render: 'พร้อม Render',
  rendered: 'Render แล้ว',
  approved: 'Approved Master',
  published: 'เผยแพร่แล้ว',
});

export function projectDisplayName(project) {
  const identity = project?.product_identity || {};
  return [identity.brand, identity.model, identity.variant].filter(Boolean).join(' ') || 'Product Video';
}

export function projectBlockers(project) {
  return project?.quality_report?.blockers || [];
}

export function projectDuration(project, timeline = null) {
  return Number(timeline?.duration ?? project?.edit?.duration ?? 0);
}

export function formatDuration(seconds) {
  const value = Number(seconds) || 0;
  return `${value.toFixed(value % 1 ? 1 : 0)} วิ`;
}

export function newStoryBlock(index = 0) {
  const role = STORY_ROLE_OPTIONS[Math.min(index, STORY_ROLE_OPTIONS.length - 1)]?.[0] || 'use_case';
  return {
    block_id: `block-${Date.now().toString(36)}-${index}`,
    role,
    text: '',
    visual_intent: '',
    claim_ids: [],
    evidence_ids: [],
  };
}

export function newFact() {
  return {
    fact_id: `fact-${Date.now().toString(36)}`,
    type: 'brand_claim',
    text: '',
    evidence_refs: [],
    usage_note: '',
  };
}

export function newEdlShot(sourceId = '', blockId = '', order = 0) {
  return {
    shot_id: `shot-${Date.now().toString(36)}-${order}`,
    source_id: sourceId,
    story_block_id: blockId,
    source_start: 0,
    source_end: 3,
    speed: 1,
    transition_in: 'cut',
    reason: '',
  };
}

export function timelineWithClips(timeline, clips) {
  const duration = clips.reduce((sum, clip) => {
    const span = Math.max(0, Number(clip.trim_end || 0) - Number(clip.trim_start || 0));
    return sum + span / Math.max(0.25, Number(clip.speed || 1)) + Math.max(0, Number(clip.freeze_tail || 0));
  }, 0);
  return {
    ...timeline,
    clips,
    clip_list: clips,
    duration: Math.round(duration * 1000) / 1000,
  };
}

export function canRenderProject(project) {
  return project?.status === 'ready_to_render' && project?.quality_report?.passed === true;
}

