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

