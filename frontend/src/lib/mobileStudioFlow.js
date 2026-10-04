export const MOBILE_WORKFLOW_KEY = 'omnicut.mobileWorkflow';

export function progressPercent(value) {
  const fraction = Number(value);
  return Number.isFinite(fraction) ? Math.round(Math.max(0, Math.min(1, fraction)) * 100) : 0;
}

export function filmingUrl(sessionId, productId, angleId) {
  const params = new URLSearchParams({ film: '1', session: sessionId, return: 'mobile', product: productId, angle: angleId });
  return `/?${params}`;
}

export function filmingReturnUrl(search) {
  const params = new URLSearchParams(search);
  if (params.get('return') !== 'mobile') return null;
  return `/?${new URLSearchParams({ mode: 'mobile', mobile_session: params.get('session') || '', product: params.get('product') || '', angle: params.get('angle') || '' })}`;
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
