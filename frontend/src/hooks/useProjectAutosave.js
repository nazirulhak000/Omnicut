import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { createLatestSaveQueue } from '../lib/projectSaveQueue.js';

const LIFECYCLE_API_KEY = import.meta.env?.VITE_API_KEY;


export function lifecycleSaveHeaders(apiKey = LIFECYCLE_API_KEY) {
  return apiKey ? { 'Content-Type': 'application/json', 'X-API-Key': apiKey } : {
    'Content-Type': 'application/json',
  };
}


function payloadKey(payload) {
  return JSON.stringify(payload || {});
}

function callSave(saveRef, name, body) {
  return saveRef.current(name, body);
}

/**
 * Imperative autosave coordinator used by the React hook and by deterministic
 * tests. The editor passes immutable payload snapshots, so equivalent
 * snapshots can be compared once and duplicate queue entries can be avoided.
 */
export function createProjectAutosaveController({
  queue,
  schedule = setTimeout,
  cancel = clearTimeout,
  onStatusChange = () => {},
  maxSaveRetries = 2,
  saveRetryDelayMs = 4000,
}) {
  let timer = null;
  let retryTimer = null;
  let retryCount = 0;
  // Dedupes the retry bookkeeping when two flush() callers (e.g. the debounce
  // timer and a manual saveNow) race against the same in-flight queue.flush()
  // promise — both attach a handler, but only one should count as "the" failure.
  const retriedFlushes = new WeakSet();
  let baseline = { projectName: '', key: '' };
  let queued = null;
  let keyCache = { hasValue: false, payload: null, key: '' };
  const jobKeys = new WeakMap();

  const getKey = (payload) => {
    if (keyCache.hasValue && keyCache.payload === payload) return keyCache.key;
    const key = payloadKey(payload);
    keyCache = { hasValue: true, payload, key };
    return key;
  };

  const clearTimer = () => {
    if (timer !== null) {
      cancel(timer);
      timer = null;
    }
  };

  const clearRetryTimer = () => {
    if (retryTimer !== null) {
      cancel(retryTimer);
      retryTimer = null;
    }
  };

  // A failed save leaves its job in the queue's `pending` slot (see
  // projectSaveQueue's error handling), but nothing else would ever flush it
  // again until an unrelated edit happens to schedule a new debounce timer.
  // Give it a small, bounded number of automatic follow-up attempts instead
  // of leaving it stranded. Only once those are exhausted do we give up and
  // let the caller surface an 'error' status.
  const scheduleRetry = () => {
    clearRetryTimer();
    if (retryCount >= maxSaveRetries) {
      retryCount = 0;
      onStatusChange('error');
      return;
    }
    retryCount += 1;
    retryTimer = schedule(() => {
      retryTimer = null;
      runFlush().catch(() => {});
    }, saveRetryDelayMs);
  };

  const runFlush = () => {
    const attempt = queue.flush();
    return attempt.then(
      (result) => {
        retryCount = 0;
        clearRetryTimer();
        return result;
      },
      (error) => {
        if (!retriedFlushes.has(attempt)) {
          retriedFlushes.add(attempt);
          if (queue.hasPending()) scheduleRetry();
          else retryCount = 0;
        }
        throw error;
      },
    );
  };

  const matches = (job, projectName, key) => (
    !!job
    && job.projectName === projectName
    && (jobKeys.get(job) || getKey(job.payload)) === key
  );

  const enqueue = (projectName, payload, key) => {
    const active = queue.peekActive?.();
    const pending = queue.peekPending();
    if (matches(active, projectName, key) || matches(pending, projectName, key)) {
      queued = { projectName, key };
      return pending || active;
    }
    const job = queue.enqueue(projectName, payload);
    if (job) jobKeys.set(job, key);
    queued = { projectName, key };
    return job;
  };

  const observe = ({ projectName, payload, enabled, debounceMs = 500 }) => {
    const key = getKey(payload);

    if (!enabled || !projectName) {
      clearTimer();
      return;
    }

    const isBaseline = baseline.projectName === projectName && baseline.key === key;
    if (isBaseline) {
      clearTimer();
      const active = queue.peekActive?.();
      const pending = queue.peekPending();
      if (active) {
        // The in-flight request cannot be cancelled. Put the baseline behind
        // it so a revert cannot be overwritten by the older edit.
        if (!matches(active, projectName, key) || !matches(pending, projectName, key)) {
          enqueue(projectName, payload, key);
        }
      } else {
        queue.clearPending();
        queued = null;
        onStatusChange('saved');
      }
      return;
    }

    const active = queue.peekActive?.();
    const pending = queue.peekPending();
    if (!matches(active, projectName, key) || (pending && !matches(pending, projectName, key))) {
      enqueue(projectName, payload, key);
    } else if (!active && !pending && (!queued || queued.projectName !== projectName || queued.key !== key)) {
      enqueue(projectName, payload, key);
    }

    clearTimer();
    if (!queue.hasPending()) return;
    timer = schedule(() => {
      timer = null;
      runFlush().catch(() => {});
    }, debounceMs);
  };

  const flush = () => {
    clearTimer();
    return runFlush();
  };

  const setBaseline = (projectName, payload) => {
    clearTimer();
    clearRetryTimer();
    retryCount = 0;
    const active = queue.peekActive?.();
    queue.clearPending();
    const key = getKey(payload);
    baseline = { projectName, key };
    queued = null;
    onStatusChange('saved');
    if (active?.projectName === projectName) enqueue(projectName, payload, key);
  };

  const saveNow = ({ projectName, payload, enabled }) => {
    if (!projectName || !enabled) return null;
    const key = getKey(payload);
    enqueue(projectName, payload, key);
    return flush();
  };

  return {
    observe,
    flush,
    setBaseline,
    saveNow,
    clearTimer,
    peekPending() {
      return queue.peekPending();
    },
    peekActive() {
      return queue.peekActive?.() || null;
    },
  };
}

export function useProjectAutosave({
  projectName,
  payload,
  enabled,
  saveProject,
  debounceMs = 500,
}) {
  const [saveStatus, setSaveStatus] = useState('saved');
  const saveRef = useRef(saveProject);
  useEffect(() => {
    saveRef.current = saveProject;
  }, [saveProject]);
  const save = useCallback((name, body) => callSave(saveRef, name, body), []);
  const [queue] = useState(() => createLatestSaveQueue(
    save,
    {
      onQueued() {
        setSaveStatus('dirty');
      },
      onSaving() {
        setSaveStatus('saving');
      },
      onSaved(_job, isLatest) {
        if (isLatest) setSaveStatus('saved');
      },
      onError() {
        setSaveStatus('dirty');
      },
    },
  ));
  const controller = useMemo(() => createProjectAutosaveController({
    queue,
    onStatusChange: setSaveStatus,
  }), [queue]);

  const flush = useCallback(() => controller.flush(), [controller]);
  const setBaseline = useCallback((name, body) => {
    controller.setBaseline(name, body);
  }, [controller]);

  useEffect(() => {
    controller.observe({ projectName, payload, enabled, debounceMs });
    return controller.clearTimer;
  }, [controller, debounceMs, enabled, payload, projectName]);

  const saveNow = useCallback(async () => (
    controller.saveNow({ projectName, payload, enabled })
  ), [controller, enabled, payload, projectName]);

  useEffect(() => {
    let lifecycleSaveStarted = false;
    const saveBeforeUnload = () => {
      // pagehide and beforeunload can both fire for one navigation. Sending
      // twice creates a race and defeats latest-save-wins at the server.
      if (lifecycleSaveStarted) return;
      lifecycleSaveStarted = true;

      if (queue.isSaving()) {
        // Let the queue drain in its existing order. A second keepalive fetch
        // for a newer pending payload could overtake the active request.
        controller.flush().catch(() => {});
        return;
      }

      const job = controller.peekPending();
      if (!job || typeof fetch !== 'function') return;
      fetch(`/api/projects/${encodeURIComponent(job.projectName)}/state`, {
        method: 'PATCH',
        headers: lifecycleSaveHeaders(),
        body: JSON.stringify(job.payload),
        keepalive: true,
      }).catch(() => {});
    };
    const resetLifecycleGuard = () => {
      lifecycleSaveStarted = false;
    };
    window.addEventListener('pagehide', saveBeforeUnload);
    window.addEventListener('beforeunload', saveBeforeUnload);
    window.addEventListener('pageshow', resetLifecycleGuard);
    return () => {
      window.removeEventListener('pagehide', saveBeforeUnload);
      window.removeEventListener('beforeunload', saveBeforeUnload);
      window.removeEventListener('pageshow', resetLifecycleGuard);
      controller.clearTimer();
      // Route changes/unmounts do not always emit a browser lifecycle event.
      // Give a queued latest snapshot the same flush opportunity as a project
      // switch before the hook disappears.
      controller.flush().catch(() => {});
    };
  }, [controller, queue]);

  return { saveStatus, setSaveStatus, flush, saveNow, setBaseline };
}
