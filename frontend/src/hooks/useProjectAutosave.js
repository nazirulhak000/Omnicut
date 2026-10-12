import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { createLatestSaveQueue } from '../lib/projectSaveQueue.js';
import { withProjectRevision } from '../lib/projectRevision.js';
import { captureChannel, registerChannelSwitchParticipant } from '../lib/channelRuntime.js';
import { projectApiPath } from '../lib/channelTransport.js';

// The normal browser path uses the same-origin proxy, which injects auth on
// the server side. An explicit key remains supported for isolated callers and
// deterministic tests, but the app no longer sources one from import.meta.env.
export function lifecycleSaveHeaders(apiKey) {
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
  // Called when the server refuses a save because the project moved on
  // (HTTP 409). The failed job stays pending; only a reload resolves it.
  onConflict = () => {},
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
  let baselineGeneration = 0;
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
    const generation = baselineGeneration;
    const attempt = queue.flush();
    return attempt.then(
      (result) => {
        retryCount = 0;
        clearRetryTimer();
        if (result && generation === baselineGeneration) {
          baseline = { projectName: result.projectName, key: jobKeys.get(result) || getKey(result.payload) };
        }
        return result;
      },
      (error) => {
        if (!retriedFlushes.has(attempt)) {
          retriedFlushes.add(attempt);
          if (error?.response?.status === 409) {
            clearRetryTimer();
            onStatusChange('error');
            onConflict(error);
          } else if (queue.hasPending()) scheduleRetry();
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
    baselineGeneration += 1;
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
    async discard() {
      baselineGeneration += 1;
      clearTimer();
      clearRetryTimer();
      queue.clearPending();
      // An already dispatched request remains bound to its original channel.
      // Wait for it to settle before leaving; never dispatch pending edits.
      if (queue.isSaving()) await queue.flush().catch(() => {});
      queue.clearPending();
      clearRetryTimer();
      onStatusChange('saved');
    },
    // True while any edit is waiting, queued, retrying or in flight -- i.e.
    // the server may not hold what the editor shows.
    hasUnsavedWork() {
      return timer !== null || retryTimer !== null || queue.hasPending() || !!queue.isSaving?.();
    },
    hasUnsavedPayload({ projectName, payload, enabled }) {
      return !!enabled && !!projectName && (baseline.projectName !== projectName || baseline.key !== getKey(payload));
    },
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
  // The caller knows the server moved on (e.g. a render rewrote the project
  // while edits were pending). Closing the tab then would lose those edits.
  unsavedAtRisk = false,
}) {
  const [channelToken] = useState(captureChannel);
  const [saveStatus, setSaveStatus] = useState('saved');
  const [saveConflict, setSaveConflict] = useState(false);
  const conflictRef = useRef(false);
  const atRiskRef = useRef(unsavedAtRisk);
  atRiskRef.current = unsavedAtRisk;
  const saveRef = useRef(saveProject);
  useEffect(() => {
    saveRef.current = saveProject;
  }, [saveProject]);
  const save = useCallback((name, body) => saveRef.current(name, body, channelToken), [channelToken]);
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
        conflictRef.current = false;
        setSaveConflict(false);
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
    onConflict() {
      conflictRef.current = true;
      setSaveConflict(true);
    },
  }), [queue]);

  const flush = useCallback(() => controller.flush(), [controller]);
  const setBaseline = useCallback((name, body) => {
    conflictRef.current = false;
    setSaveConflict(false);
    controller.setBaseline(name, body);
  }, [controller]);
  const hasUnsavedWork = useCallback(() => controller.hasUnsavedWork(), [controller]);

  useEffect(() => {
    controller.observe({ projectName, payload, enabled, debounceMs });
    return controller.clearTimer;
  }, [controller, debounceMs, enabled, payload, projectName]);

  const saveNow = useCallback(async () => (
    controller.saveNow({ projectName, payload, enabled })
  ), [controller, enabled, payload, projectName]);

  const currentEdit = useRef(null);
  currentEdit.current = { projectName, payload, enabled };
  useEffect(() => registerChannelSwitchParticipant({
    isDirty: () => controller.hasUnsavedWork() || controller.hasUnsavedPayload(currentEdit.current),
    save: async () => {
      controller.observe({ ...currentEdit.current, debounceMs: 0 });
      await controller.flush();
    },
    discard: () => controller.discard(),
  }), [controller]);

  useEffect(() => {
    let lifecycleSaveStarted = false;
    const saveBeforeUnload = (event) => {
      // The server already refused these edits (409) or is known to have moved
      // on: a keepalive save would be refused the same way, silently. Ask the
      // browser to confirm leaving instead, so the edits are not lost unseen.
      if (
        event?.type === 'beforeunload'
        && (conflictRef.current || atRiskRef.current)
        && controller.hasUnsavedWork()
      ) {
        event.preventDefault();
        event.returnValue = '';
        return;
      }
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
      fetch(`/api${projectApiPath(job.projectName)}/state`, {
        method: 'PATCH',
        headers: { ...lifecycleSaveHeaders(), 'X-OmniCut-Channel': channelToken.channel_id },
        body: JSON.stringify(withProjectRevision(job.projectName, { ...job.payload, channel_id: channelToken.channel_id }, channelToken.channel_id)),
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

  return { saveStatus, setSaveStatus, flush, saveNow, setBaseline, saveConflict, hasUnsavedWork };
}
