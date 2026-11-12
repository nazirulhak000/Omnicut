// Product page helpers for background work: which task belongs to the open
// product, and what the production-chain buttons would act on.
//
// The backend's task record is { type, status: queued|processing|completed|
// failed|cancelled, progress: 0..1, step_label, payload, result, error }.

export const CHAIN_TASK_TYPE = 'production_chain';
export const CHAIN_LABEL = {
  draft: 'ผลิตถึงดราฟต์',
  render: 'เรนเดอร์ดราฟต์',
  full: 'ผลิตจนเรนเดอร์เสร็จ',
};

const ACTIVE_STATUSES = new Set(['queued', 'processing']);
const DRAFT_STATUSES = new Set(['in_production', 'rendered', 'posted']);

export const isActiveTask = (task) => ACTIVE_STATUSES.has(task?.status);

/** The running (or queued) task of one of `types` that works on this product. */
export function findProductTask(tasks, productId, types, accept = null) {
  if (!productId) return null;
  const wanted = new Set(types);
  return (tasks || []).find((task) => (
    wanted.has(task?.type)
    && task?.payload?.product_id === productId
    && isActiveTask(task)
    && (!accept || accept(task))
  )) || null;
}

/** Task progress (0..1 from the backend) as a whole percentage, or null. */
export function taskPercent(task) {
  const value = Number(task?.progress);
  if (!Number.isFinite(value)) return null;
  return Math.round(Math.min(1, Math.max(0, value)) * 100);
}

const isFinished = (angle) => (
  angle?.status === 'rendered' || angle?.status === 'posted' || Boolean(angle?.posted_at)
);
const hasDraft = (angle) => DRAFT_STATUSES.has(angle?.status) && Boolean(angle?.project_name);
const hasScript = (angle) => (angle?.script_lines || angle?.tts_lines || [])
  .some((line) => String(line ?? '').trim());

/**
 * How many angles each chain would work on -- the same rules the backend
 * applies (scripts/production_chain.py), so the button count is what runs.
 * `batch` is a lot number, or 'all' / null for every lot.
 */
export function chainTargets(angles, batch = null) {
  const lot = batch === 'all' || batch == null ? null : Number(batch);
  const scoped = (angles || []).filter((angle) => (
    angle?.angle_id && (lot === null || (angle.batch || 1) === lot)
  ));
  const open = scoped.filter((angle) => !isFinished(angle));
  const draft = open.filter((angle) => !hasDraft(angle) && hasScript(angle)).length;
  // full renders only the drafts it builds itself, so it acts on the same angles as draft
  return { draft, render: open.filter(hasDraft).length, full: draft };
}

export function chainConfirmText(kind, count) {
  if (kind === 'full') {
    return `เตรียมเสียงพากย์ สแกนฉาก สร้างดราฟต์ และเรนเดอร์ ${count} มุมต่อเนื่องกัน\n`
      + 'ไม่หยุดให้ตรวจดราฟต์ก่อนเรนเดอร์ และไม่จัดคิวโพสต์\n\nเริ่มผลิตเลยไหม?';
  }
  if (kind === 'render') {
    return `เรนเดอร์ดราฟต์ที่ตรวจแล้ว ${count} มุม ตามค่าที่บันทึกไว้ใน Editor\n`
      + 'ไม่จัดคิวโพสต์ — จัดคิวเองทีหลังที่หน้าตารางโพสต์\n\nเริ่มเรนเดอร์เลยไหม?';
  }
  return `เตรียมเสียงพากย์ สแกนฉาก และสร้างดราฟต์ ${count} มุมต่อเนื่องกัน\n`
    + 'ระบบหยุดที่ดราฟต์ให้เปิดตรวจใน Editor ก่อนเรนเดอร์\n\nเริ่มผลิตเลยไหม?';
}

/** Message for a chain that could not start (409 carries { message, task_id }). */
export function chainStartError(error) {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === 'object') return detail.message || 'เริ่มงานไม่สำเร็จ';
  return detail || error?.message || 'เริ่มงานไม่สำเร็จ';
}

/**
 * What the product page does once a chain task has ended: reload the product.
 * No chain opens the posting schedule -- the owner queues finished clips
 * later -- and the app-wide task toast already says how the chain ended.
 */
export function chainFollowUp(task) {
  return { refresh: Boolean(task && task.type === CHAIN_TASK_TYPE && !isActiveTask(task)) };
}
