// Product page helpers for background work: which task belongs to the open
// product, and what the two production-chain buttons would act on.
//
// The backend's task record is { type, status: queued|processing|completed|
// failed|cancelled, progress: 0..1, step_label, payload, result, error }.

export const CHAIN_TASK_TYPE = 'production_chain';
export const CHAIN_LABEL = { draft: 'ผลิตถึงดราฟต์', render: 'เรนเดอร์และเข้าคิว' };
export const OPEN_AUTOFILL_KEY = 'omnicut.schedule.open_autofill';

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
  return {
    draft: open.filter((angle) => !hasDraft(angle) && hasScript(angle)).length,
    render: open.filter(hasDraft).length,
  };
}

export function chainConfirmText(kind, count) {
  if (kind === 'render') {
    return `เรนเดอร์ดราฟต์ที่ตรวจแล้ว ${count} มุม ตามค่าที่บันทึกไว้ใน Editor\n`
      + 'เสร็จแล้วระบบเปิดหน้าจัดคิวโพสต์ให้ตรวจก่อนบันทึก\n\nเริ่มเรนเดอร์เลยไหม?';
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
 * What the product page does once a chain task has ended.
 * `openSchedule` is true only for a render chain that produced clips.
 */
export function chainFollowUp(task) {
  if (!task || task.type !== CHAIN_TASK_TYPE || isActiveTask(task)) {
    return { refresh: false, openSchedule: false, rendered: 0 };
  }
  const rendered = task.status === 'completed' && task.result?.kind === 'render'
    ? (task.result.rendered || []).length
    : 0;
  return { refresh: true, openSchedule: rendered > 0, rendered };
}

/** Ask the schedule page to open its auto-fill preview on its next mount. */
export function requestScheduleAutofill(storage) {
  try { storage?.setItem(OPEN_AUTOFILL_KEY, '1'); } catch { /* storage unavailable: the owner opens it by hand */ }
}

/** True once per request; clears it so a reload does not reopen the preview. */
export function consumeScheduleAutofill(storage) {
  try {
    if (storage?.getItem(OPEN_AUTOFILL_KEY) !== '1') return false;
    storage.removeItem(OPEN_AUTOFILL_KEY);
    return true;
  } catch {
    return false;
  }
}
