// Service Worker registration + backend health monitor for OmniCut Mobile PWA.
//
// Pure / dependency-injected helpers allow deterministic unit testing in both
// node:test and Vitest without requiring a live browser or server.

export const SW_SCRIPT_URL = '/sw.js';
export const HEALTH_ENDPOINT = '/api/health';
export const DEFAULT_HEALTH_TIMEOUT_MS = 5000;
export const DEFAULT_MONITOR_INTERVAL_MS = 15000;

/**
 * Safely registers `/sw.js` when `serviceWorker` is available on navigator.
 * Never throws; returns `{ registered: boolean, registration: object|null, error?: Error }`.
 */
export async function registerServiceWorker({
  nav = typeof navigator !== 'undefined' ? navigator : null,
  swUrl = SW_SCRIPT_URL,
  scope = '/',
} = {}) {
  if (!nav || !('serviceWorker' in nav) || !nav.serviceWorker?.register) {
    return { registered: false, registration: null };
  }

  try {
    const registration = await nav.serviceWorker.register(swUrl, { scope });
    return { registered: true, registration };
  } catch (error) {
    return { registered: false, registration: null, error };
  }
}

/**
 * Calls `GET /api/health` with a 5s timeout (default) and returns
 * `{ online: boolean, status: number, timestamp: number }`.
 */
export async function checkServerHealth(
  fetchImpl = typeof fetch === 'function' ? fetch : null,
  { timeoutMs = DEFAULT_HEALTH_TIMEOUT_MS, endpoint = HEALTH_ENDPOINT, now = Date.now } = {}
) {
  const timestamp = typeof now === 'function' ? now() : Date.now();
  if (typeof fetchImpl !== 'function') {
    return { online: false, status: 0, timestamp };
  }

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  let timerId = null;

  const timeoutPromise = new Promise((_, reject) => {
    timerId = setTimeout(() => {
      if (controller) {
        try {
          controller.abort();
        } catch {
          // ignore
        }
      }
      reject(new Error('Health check timed out'));
    }, timeoutMs);
  });

  try {
    const response = await Promise.race([
      fetchImpl(endpoint, {
        method: 'GET',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        ...(controller ? { signal: controller.signal } : {}),
      }),
      timeoutPromise,
    ]);

    const status = typeof response?.status === 'number' ? response.status : 0;
    const online = Boolean(response && (response.ok || (status >= 200 && status < 500)));
    return {
      online,
      status,
      timestamp: typeof now === 'function' ? now() : Date.now(),
    };
  } catch {
    return {
      online: false,
      status: 0,
      timestamp: typeof now === 'function' ? now() : Date.now(),
    };
  } finally {
    if (timerId !== null) clearTimeout(timerId);
  }
}

/**
 * Periodic health monitor that pauses polling while `document.hidden === true`
 * and immediately re-checks on `visibilitychange` (when visible) or `online`.
 */
export function createHealthMonitor({
  intervalMs = DEFAULT_MONITOR_INTERVAL_MS,
  onChange,
  fetchImpl = typeof fetch === 'function' ? fetch : null,
  doc = typeof document !== 'undefined' ? document : null,
  win = typeof window !== 'undefined' ? window : null,
  timeoutMs = DEFAULT_HEALTH_TIMEOUT_MS,
} = {}) {
  let timerId = null;
  let stopped = false;
  let lastResult = null;
  let inFlight = null;

  const isHidden = () => Boolean(doc && doc.hidden === true);

  const notify = (result) => {
    lastResult = result;
    if (typeof onChange === 'function') {
      onChange(result);
    }
  };

  const runCheck = async () => {
    if (stopped) return lastResult;
    if (inFlight) return inFlight;

    inFlight = checkServerHealth(fetchImpl, { timeoutMs })
      .then((result) => {
        inFlight = null;
        if (!stopped) notify(result);
        return result;
      })
      .catch(() => {
        inFlight = null;
        const fallback = { online: false, status: 0, timestamp: Date.now() };
        if (!stopped) notify(fallback);
        return fallback;
      });

    return inFlight;
  };

  const clearScheduledTimer = () => {
    if (timerId !== null) {
      clearInterval(timerId);
      timerId = null;
    }
  };

  const ensureTimer = () => {
    if (stopped || isHidden() || timerId !== null) return;
    if (intervalMs > 0) {
      timerId = setInterval(() => {
        if (isHidden()) {
          clearScheduledTimer();
          return;
        }
        runCheck();
      }, intervalMs);
    }
  };

  const handleVisibilityChange = () => {
    if (stopped) return;
    if (isHidden()) {
      clearScheduledTimer();
    } else {
      ensureTimer();
      runCheck();
    }
  };

  const handleOnline = () => {
    if (stopped) return;
    if (!isHidden()) {
      ensureTimer();
    }
    runCheck();
  };

  const start = () => {
    stopped = false;
    if (doc && typeof doc.addEventListener === 'function') {
      doc.addEventListener('visibilitychange', handleVisibilityChange);
    }
    if (win && typeof win.addEventListener === 'function') {
      win.addEventListener('online', handleOnline);
    }
    if (!isHidden()) {
      ensureTimer();
      runCheck();
    }
  };

  const stop = () => {
    stopped = true;
    clearScheduledTimer();
    if (doc && typeof doc.removeEventListener === 'function') {
      doc.removeEventListener('visibilitychange', handleVisibilityChange);
    }
    if (win && typeof win.removeEventListener === 'function') {
      win.removeEventListener('removeEventListener' in win ? 'online' : 'online', handleOnline);
    }
  };

  // Start immediately on creation unless document is hidden
  start();

  return {
    checkNow: runCheck,
    stop,
    start,
    getLastResult: () => lastResult,
    isRunning: () => !stopped && timerId !== null,
  };
}
