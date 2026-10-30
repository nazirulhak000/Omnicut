import { activeChannel } from './channelRuntime.js';
import { assertChannelId } from './channelId.js';
export const MOBILE_WORKFLOW_KEY = 'omnicut.mobileWorkflow';

export function progressPercent(value) {
  const fraction = Number(value);
  return Number.isFinite(fraction) ? Math.round(Math.max(0, Math.min(1, fraction)) * 100) : 0;
}

export function filmingUrl(sessionId, productId, angleId, channelId = activeChannel()) {
  const params = new URLSearchParams({ film: '1', session: sessionId, return: 'mobile', product: productId, angle: angleId, channel: assertChannelId(channelId) });
  return `/?${params}`;
}

export function filmingReturnUrl(search) {
  const params = new URLSearchParams(search);
  if (params.get('return') !== 'mobile') return null;
  const channelId = assertChannelId(params.get('channel') || activeChannel());
  return `/?${new URLSearchParams({ mode: 'mobile', mobile_session: params.get('session') || '', product: params.get('product') || '', angle: params.get('angle') || '', channel: channelId })}`;
}

// Schedule only after the previous request settles. Stop invalidates in-flight replies.
export function pollMobileTask({ fetchTask, onTask, onError, interval = 2000, maxErrors = 3, schedule = setTimeout, cancel = clearTimeout }) {
  let stopped = false;
  let timer;
  let errors = 0;
  async function tick() {
    try {
      const response = await fetchTask();
      if (stopped) return;
      if (!response?.task) throw new Error('ไม่ได้รับสถานะงานจากเซิร์ฟเวอร์');
      errors = 0;
      if (onTask(response.task) === false) { stopped = true; return; }
    } catch (error) {
      if (stopped) return;
      errors += 1;
      if (error?.response?.status === 404 || errors >= maxErrors) {
        stopped = true;
        onError(error);
        return;
      }
    }
    if (!stopped) timer = schedule(tick, interval);
  }
  tick();
  return () => { stopped = true; if (timer !== undefined) cancel(timer); };
}

// ── P2-4: catalog pagination (mobile touch list) ──
export const MOBILE_CATALOG_PAGE_SIZE = 20;

/** Query params for one catalog page. */
export function catalogPageParams(page = 1) {
  return { page, page_size: MOBILE_CATALOG_PAGE_SIZE };
}

/** Append a fetched page to the loaded list without showing an id twice. */
export function mergeCatalogPage(existing, incoming) {
  const merged = existing.slice();
  const seen = new Set(merged.map(item => item?.id).filter(id => id !== undefined && id !== null));
  for (const item of incoming || []) {
    if (!item) continue;
    const key = item.id;
    if (key === undefined || key === null) {
      merged.push(item);
      continue;
    }
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(item);
  }
  return merged;
}

// ── Mobile E2E UX (2026-10-30) ──

/** The mobile catalog DTO names the finished clip `rendered_video_url`; older rows used `video_url`. */
export function angleVideoUrl(angle) {
  return angle?.rendered_video_url || angle?.video_url || null;
}

/** An angle counts as posted only when the backend says so (status or posted_at). */
export function isAnglePosted(angle) {
  return Boolean(angle && (angle.status === 'posted' || angle.posted_at));
}

/** Uploaded footage belongs to exactly one product+angle pair. */
export function footageKey(productId, angleId) {
  if (!productId) return null;
  return `${productId}:${angleId || 'quick_take'}`;
}

const MOBILE_RENDER_TASK_TYPE = 'mobile_auto_assemble_render';
const LIVE_TASK_STATUSES = new Set(['queued', 'processing']);

/**
 * Pick the still-running mobile render task to reattach to after the phone
 * reopened the page. Prefers the task for the remembered product/angle, then
 * the newest live mobile render. Returns null when nothing is running.
 */
export function findResumableMobileTask(tasks, { productId = null, angleId = null } = {}) {
  const live = (Array.isArray(tasks) ? tasks : []).filter(t =>
    t && t.type === MOBILE_RENDER_TASK_TYPE && LIVE_TASK_STATUSES.has(t.status));
  if (!live.length) return null;
  const sameAngle = live.find(t => {
    const p = t.payload || {};
    return (!productId || p.product_id === productId) && (!angleId || p.angle_id === angleId);
  });
  if (productId || angleId) return sameAngle || null;
  return live[0];
}

/**
 * Mark-posted is idempotent from the phone's point of view. Success when the
 * server says the clip is already posted, or when it answers 404 (file already
 * moved into Posted/) to a RETRY whose previous attempt got no response at all
 * (request reached the server, reply was lost). Any other 409/404 is a real
 * failure -- e.g. export_id mismatch -- and must stay an error.
 */
export function isAlreadyPostedError(error, { previousAttemptLost = false } = {}) {
  const status = error?.response?.status;
  const detail = String(error?.response?.data?.detail || '').toLowerCase();
  if (/already posted|โพสต์แล้ว/.test(detail) && !/ไม่สามารถนำกลับ/.test(detail)) return true;
  return status === 404 && previousAttemptLost;
}

/** True when the request never got an HTTP reply (offline, timeout, tunnel drop). */
export function isNoResponseError(error) {
  return Boolean(error) && !error.response;
}
