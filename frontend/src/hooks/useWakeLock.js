import { useEffect, useState } from 'react';

/**
 * Keeps the screen awake while a mobile task is running (filming / rendering).
 *
 * P2-3: phones drop to sleep during long renders and guided takes, which kills
 * MediaRecorder mid-take and freezes the progress polling. The Screen Wake Lock
 * API is Chromium-only (iOS Safari has no support yet), so everything degrades
 * to a no-op there — `supported` is reported for callers that want to know.
 *
 * The lock is re-requested when the page becomes visible again because iOS and
 * Android release it automatically whenever the tab is backgrounded.
 *
 * @param {boolean} active request while true, release when it flips false
 * @returns {boolean} true when the browser exposes navigator.wakeLock
 */
export default function useWakeLock(active) {
  const [supported] = useState(
    () => typeof navigator !== 'undefined' && 'wakeLock' in navigator,
  );

  useEffect(() => {
    if (!active || !supported) return undefined;
    let cancelled = false;
    let sentinel = null;

    const request = async () => {
      try {
        const lock = await navigator.wakeLock.request('screen');
        if (cancelled) {
          await lock.release();
          return;
        }
        sentinel = lock;
      } catch {
        // Not allowed right now (battery saver, hidden tab, denied) — keep
        // going without a lock instead of surfacing an error to the user.
        sentinel = null;
      }
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') request();
    };

    request();
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', handleVisibility);
      const lock = sentinel;
      sentinel = null;
      if (lock) lock.release().catch(() => {});
    };
  }, [active, supported]);

  return supported;
}
