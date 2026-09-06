import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { createLatestSaveQueue } from '../lib/projectSaveQueue.js';


function payloadKey(payload) {
  return JSON.stringify(payload || {});
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
  const latestRef = useRef({ projectName: '', payload: null, key: '' });
  const baselineRef = useRef({ projectName: '', key: '' });
  const latestSequenceRef = useRef(0);
  const timerRef = useRef(null);

  saveRef.current = saveProject;
  const queue = useMemo(() => createLatestSaveQueue(
    (name, body) => saveRef.current(name, body),
    {
      onQueued(job) {
        latestSequenceRef.current = job.sequence;
        setSaveStatus('dirty');
      },
      onSaving() {
        setSaveStatus('saving');
      },
      onSaved(job) {
        if (job.sequence === latestSequenceRef.current) setSaveStatus('saved');
      },
      onError() {
        setSaveStatus('dirty');
      },
    },
  ), []);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const flush = useCallback(async () => {
    clearTimer();
    return queue.flush();
  }, [clearTimer, queue]);

  const setBaseline = useCallback((name, body) => {
    clearTimer();
    queue.clearPending();
    const key = payloadKey(body);
    baselineRef.current = { projectName: name, key };
    latestRef.current = { projectName: name, payload: body, key };
    setSaveStatus('saved');
  }, [clearTimer, queue]);

  useEffect(() => {
    if (!enabled || !projectName) return undefined;
    const key = payloadKey(payload);
    latestRef.current = { projectName, payload, key };
    if (baselineRef.current.projectName === projectName && baselineRef.current.key === key) {
      return undefined;
    }

    queue.enqueue(projectName, payload);
    clearTimer();
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      queue.flush().catch(() => {});
    }, debounceMs);
    return clearTimer;
  }, [clearTimer, debounceMs, enabled, payload, projectName, queue]);

  const saveNow = useCallback(async () => {
    if (!projectName || !enabled) return null;
    const latest = latestRef.current;
    if (!queue.hasPending()) queue.enqueue(projectName, latest.payload || payload);
    return flush();
  }, [enabled, flush, payload, projectName, queue]);

  useEffect(() => {
    const saveBeforeUnload = () => {
      const job = queue.peekPending() || (queue.isSaving() ? latestRef.current : null);
      if (!job || typeof fetch !== 'function') return;
      fetch(`/api/projects/${encodeURIComponent(job.projectName)}/state`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(job.payload),
        keepalive: true,
      }).catch(() => {});
    };
    window.addEventListener('pagehide', saveBeforeUnload);
    window.addEventListener('beforeunload', saveBeforeUnload);
    return () => {
      window.removeEventListener('pagehide', saveBeforeUnload);
      window.removeEventListener('beforeunload', saveBeforeUnload);
      clearTimer();
    };
  }, [clearTimer, queue]);

  return { saveStatus, setSaveStatus, flush, saveNow, setBaseline };
}
