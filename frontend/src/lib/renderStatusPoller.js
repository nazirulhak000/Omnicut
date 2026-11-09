/**
 * Self-scheduling poll of one render job's status (S4-15).
 *
 * The live render widget used a 1s setInterval: a slow response let requests
 * pile up, one failed request stopped polling for good, and the 4s "linger"
 * timeout after completion was never cleared on unmount. Here the next tick is
 * scheduled only after the previous request settles (at most one in flight),
 * a failure backs off and retries, polling gives up only after several
 * failures in a row, and stop() cancels every pending timer.
 *
 * Timers are injectable so the behaviour is unit tested without real time.
 */

export const RENDER_TERMINAL_STATUSES = Object.freeze(['completed', 'done', 'failed', 'error', 'cancelled']);

export function isTerminalRenderStatus(status) {
  return RENDER_TERMINAL_STATUSES.includes(String(status || '').toLowerCase());
}

/**
 * @param {{
 *   jobId: string,
 *   fetchStatus: (jobId: string) => Promise<any>,
 *   onStatus: (data: any) => void,
 *   onFinished?: () => void,      // after the linger once a terminal status is seen
 *   onGiveUp?: () => void,        // after maxFailures consecutive errors
 *   isHidden?: () => boolean,     // skip the request while the page is hidden
 *   intervalMs?: number,
 *   lingerMs?: number,
 *   maxFailures?: number,
 *   maxBackoffMs?: number,
 *   schedule?: (fn: () => void, ms: number) => any,
 *   cancel?: (handle: any) => void,
 * }} opts
 * @returns {{ stop: () => void, isStopped: () => boolean }}
 */
export function startRenderStatusPoller({
  jobId,
  fetchStatus,
  onStatus,
  onFinished,
  onGiveUp,
  isHidden = () => false,
  intervalMs = 1000,
  lingerMs = 4000,
  maxFailures = 5,
  maxBackoffMs = 15000,
  schedule = (fn, ms) => setTimeout(fn, ms),
  cancel = (handle) => clearTimeout(handle),
}) {
  let stopped = false;
  let timer = null;
  let failures = 0;

  const later = (fn, ms) => {
    if (stopped) return;
    timer = schedule(() => {
      timer = null;
      if (!stopped) fn();
    }, ms);
  };

  const tick = async () => {
    if (isHidden()) {
      later(tick, intervalMs);
      return;
    }
    let data;
    try {
      data = await fetchStatus(jobId);
    } catch {
      if (stopped) return;
      failures += 1;
      if (failures >= maxFailures) {
        stopped = true;
        onGiveUp?.();
        return;
      }
      later(tick, Math.min(maxBackoffMs, intervalMs * 2 ** failures));
      return;
    }
    if (stopped) return;
    failures = 0;
    onStatus(data);
    if (isTerminalRenderStatus(data?.status)) {
      later(() => {
        stopped = true;
        onFinished?.();
      }, lingerMs);
      return;
    }
    later(tick, intervalMs);
  };

  later(tick, intervalMs);

  return {
    stop() {
      stopped = true;
      if (timer !== null) cancel(timer);
      timer = null;
    },
    isStopped: () => stopped,
  };
}
