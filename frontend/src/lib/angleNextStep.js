// Where one selling angle stands, and the one action that moves it forward.
// The product page shows that action as the only filled button of the angle
// panel; every other action of the same state is listed as secondary.

/** Stage of an angle, from its stored status, its clips and its voice/shot plan. */
export function angleStage(angle = {}, { selectedCount = 0, shotListInfo = null } = {}) {
  const status = angle.status || 'scripted';
  const posted = status === 'posted' || Boolean(angle.posted_at);
  if (posted) return 'posted';
  if (status === 'rendered' && angle.video_url) return 'rendered';
  if (!posted && status === 'in_production') return 'drafted';
  if (selectedCount === 0) return 'needs_clips';
  if (!shotListInfo?.has_shot_list || shotListInfo?.is_edge_tts) return 'needs_voice';
  return 'ready_to_draft';
}

const ACTIONS = {
  posted: { primary: 'watch', secondary: ['gallery', 'clone'] },
  rendered: { primary: 'watch', secondary: ['gallery', 'timeline', 'recut'] },
  drafted: { primary: 'timeline', secondary: ['tracker', 'recut'] },
  needs_clips: { primary: 'pick_clips', secondary: ['tracker'] },
  needs_voice: { primary: 'voice', secondary: ['tracker', 'studio'] },
  ready_to_draft: { primary: 'draft', secondary: ['tracker', 'studio'] },
};

/** `{stage, primary, secondary}` for one angle. */
export function angleNextStep(angle = {}, context = {}) {
  const stage = angleStage(angle, context);
  if (stage === 'posted' && !angle.video_url) return { stage, primary: 'gallery', secondary: ['clone'] };
  return { stage, ...ACTIONS[stage] };
}

// Short state label of a list row, and the hint next to the panel's button.
export const STAGE_LABEL = {
  posted: 'โพสต์แล้ว',
  rendered: 'เรนเดอร์แล้ว',
  drafted: 'มีดราฟต์',
  needs_clips: 'ยังไม่มีคลิป',
  needs_voice: 'ยังไม่มีเสียง',
  ready_to_draft: 'พร้อมทำดราฟต์',
};

export const STAGE_HINT = {
  posted: 'โพสต์แล้ว ล็อกเนื้อหาไว้เป็นประวัติ',
  rendered: 'เรนเดอร์เสร็จ ตรวจคลิปแล้วไปโพสต์ที่ Gallery',
  drafted: 'มีดราฟต์ใน Editor แล้ว',
  needs_clips: 'ขั้นต่อไป: เลือกคลิปดิบให้มุมนี้',
  needs_voice: 'ขั้นต่อไป: เตรียมเสียงนำถ่ายและแผนถ่าย',
  ready_to_draft: 'ขั้นต่อไป: สร้างดราฟต์',
};

/** Button text of an action; a few read differently by stage. */
export function angleActionLabel(action, stage, { edgeTts = false } = {}) {
  switch (action) {
    case 'watch': return 'ดูคลิป';
    case 'gallery': return 'เปิดใน Gallery';
    case 'clone': return 'ทำซ้ำเพื่อตัดใหม่';
    case 'timeline': return stage === 'drafted' ? 'เปิดทำต่อใน Editor' : 'เปิดดูใน Editor';
    case 'recut': return 'ตัดใหม่';
    case 'tracker': return stage === 'drafted' ? 'ดูใน Tracker' : 'ส่งเข้า Tracker';
    case 'pick_clips': return 'เลือกคลิป';
    case 'voice': return edgeTts ? 'อัปเกรดเสียง' : 'เตรียมเสียงและแผนถ่าย';
    case 'draft': return 'สร้างดราฟต์';
    case 'studio': return 'ตั้งค่าเองใน Editor';
    default: return action;
  }
}
