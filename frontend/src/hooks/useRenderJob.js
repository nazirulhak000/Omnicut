import { useCallback, useEffect, useRef, useState } from 'react';

import {
  calculateJobProgress,
  clearActiveJob,
  formatJobError,
  getActiveJob,
  normalizeJobResult,
  saveActiveJob,
} from '../lib/renderJobModel.js';

/**
 * Hook for managing render jobs, status polling, unmount cleanup,
 * and project-scoped race condition protection.
 */
export function useRenderJob({
  projectName,
  fetchStatus,
  onComplete,
  onError,
  pollIntervalMs = 1000,
}) {
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [isRendering, setIsRendering] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [applyError, setApplyError] = useState(null);

  const activeProjectRef = useRef(projectName);
  const timerRef = useRef(null);
  const isMountedRef = useRef(true);
  const callbacksRef = useRef({ onComplete, onError, fetchStatus });
  callbacksRef.current = { onComplete, onError, fetchStatus };

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopJob = useCallback(() => {
    clearTimer();
    setIsRendering(false);
  }, [clearTimer]);

  const clearResult = useCallback(() => setApplyResult(null), []);
  const clearError = useCallback(() => setApplyError(null), []);

  const pollJob = useCallback((id, targetProject) => {
    clearTimer();
    if (!id || !targetProject) return;

    timerRef.current = setInterval(async () => {
      // Guard: If component unmounted or project switched, abort immediately
      if (!isMountedRef.current || activeProjectRef.current !== targetProject) {
        clearTimer();
        return;
      }

      try {
        const fetcher = callbacksRef.current.fetchStatus;
        if (!fetcher) return;

        const st = await fetcher(id);

        // Re-check project guard after async network request
        if (!isMountedRef.current || activeProjectRef.current !== targetProject) {
          clearTimer();
          return;
        }

        setJobStatus(st);
        const { isDone, isFailed } = calculateJobProgress(st);

        if (isDone) {
          clearTimer();
          setIsRendering(false);
          clearActiveJob(targetProject);
          const rawResult = st.result || {};
          const normalized = normalizeJobResult(rawResult);
          setApplyResult(rawResult);
          callbacksRef.current.onComplete?.(rawResult, id, targetProject, normalized);
        } else if (isFailed) {
          clearTimer();
          setIsRendering(false);
          clearActiveJob(targetProject);
          const errorMsg = formatJobError(st.error || 'เกิดข้อผิดพลาดในการเรนเดอร์');
          setApplyError(errorMsg);
          callbacksRef.current.onError?.(errorMsg, id, targetProject);
        }
      } catch (err) {
        // Network errors or temporary timeouts: continue polling unless explicitly fatal
        if (!isMountedRef.current || activeProjectRef.current !== targetProject) {
          clearTimer();
        }
      }
    }, pollIntervalMs);
  }, [clearTimer, pollIntervalMs]);

  const startJob = useCallback((newJobId, initialStatus = null) => {
    if (!newJobId) return;
    const currentProject = activeProjectRef.current;
    setJobId(newJobId);
    setIsRendering(true);
    setApplyError(null);
    setApplyResult(null);

    if (initialStatus) {
      setJobStatus(initialStatus);
    } else {
      setJobStatus({ progress: 0.05, message: 'กำลังเตรียมข้อมูล...' });
    }

    if (currentProject) {
      saveActiveJob(currentProject, newJobId);
    }

    pollJob(newJobId, currentProject);
  }, [pollJob]);

  // Handle project switching and resume active jobs
  useEffect(() => {
    activeProjectRef.current = projectName;
    clearTimer();
    setIsRendering(false);
    setJobStatus(null);

    if (!projectName) {
      setJobId(null);
      return undefined;
    }

    // Check if there is an active background render job for this project
    const storedJobId = getActiveJob(projectName);
    if (storedJobId) {
      setJobId(storedJobId);
      setIsRendering(true);
      setJobStatus({ progress: 0.1, message: 'กำลังตรวจสอบสถานะการเรนเดอร์...' });
      pollJob(storedJobId, projectName);
    } else {
      setJobId(null);
    }

    return clearTimer;
  }, [clearTimer, pollJob, projectName]);

  // Component lifecycle: set isMounted and cleanup timers
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimer();
    };
  }, [clearTimer]);

  const progress = calculateJobProgress(jobStatus);

  return {
    jobId,
    jobStatus,
    isRendering,
    applyResult,
    setApplyResult,
    applyError,
    setApplyError,
    progressPercent: progress.percent,
    progressMessage: progress.message,
    startJob,
    stopJob,
    clearResult,
    clearError,
  };
}
