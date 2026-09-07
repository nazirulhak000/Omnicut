import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getRenderStatus, startRender } from '../api.js';

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
 * Supports both manual startJob (EditorShell) and full payload executeRender (NewClipPanel).
 */
export function useRenderJob({
  projectName,
  fetchStatus = getRenderStatus,
  onComplete,
  onError,
  pollIntervalMs = 1000,
} = {}) {
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobProjectName, setJobProjectName] = useState(projectName || '');
  const [isRendering, setIsRendering] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [applyError, setApplyError] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [displayPercent, setDisplayPercent] = useState(0);

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
    setStartTime(null);
  }, [clearTimer]);

  const resetJob = useCallback(() => {
    clearTimer();
    setIsRendering(false);
    setJobId(null);
    setJobStatus(null);
    setApplyResult(null);
    setApplyError(null);
    setStartTime(null);
    setElapsedSeconds(0);
    setDisplayPercent(0);
  }, [clearTimer]);

  const clearResult = useCallback(() => setApplyResult(null), []);
  const clearError = useCallback(() => setApplyError(null), []);

  const pollJob = useCallback((id, targetProject) => {
    clearTimer();
    if (!id || !targetProject) return;

    const checkOnce = async () => {
      // Guard: If component unmounted or project switched, abort immediately
      if (!isMountedRef.current || activeProjectRef.current !== targetProject) {
        clearTimer();
        return;
      }

      try {
        const fetcher = callbacksRef.current.fetchStatus || getRenderStatus;
        if (!fetcher) return;

        const st = await fetcher(id);

        // Re-check project guard after async network request
        if (!isMountedRef.current || activeProjectRef.current !== targetProject) {
          clearTimer();
          return;
        }

        setJobStatus(st);
        const { isDone, isFailed, isCancelled } = calculateJobProgress(st);

        if (isDone) {
          clearTimer();
          setIsRendering(false);
          setStartTime(null);
          setDisplayPercent(100);
          clearActiveJob(targetProject);
          const rawResult = st.result || {};
          const normalized = normalizeJobResult(rawResult);
          setApplyResult(rawResult);
          callbacksRef.current.onComplete?.(rawResult, id, targetProject, normalized);
        } else if (isCancelled) {
          // Terminal, but not an error -- stop polling and clear the
          // "rendering" flag the same way isFailed does, without routing it
          // through onError/applyError (which the UI renders as a failure).
          clearTimer();
          setIsRendering(false);
          setStartTime(null);
          clearActiveJob(targetProject);
        } else if (isFailed) {
          clearTimer();
          setIsRendering(false);
          setStartTime(null);
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
    };

    // Run an immediate check rather than waiting for the first interval
    // tick. This matters most when resuming a job entry loaded from
    // storage (see the project-switch effect below): the stored entry is
    // never trusted blindly -- its status is confirmed against the server
    // right away instead of only after pollIntervalMs has elapsed (during
    // which an unmount/project-switch could occur and the check would
    // never happen at all).
    checkOnce();
    timerRef.current = setInterval(checkOnce, pollIntervalMs);
  }, [clearTimer, pollIntervalMs]);

  const startJob = useCallback((newJobId, initialStatus = null) => {
    if (!newJobId) return;
    const currentProject = activeProjectRef.current;
    setJobId(newJobId);
    setIsRendering(true);
    setStartTime((prev) => prev || Date.now());
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

  const executeRender = useCallback(async (payload) => {
    resetJob();
    const projName = payload?.project_name || payload?.product_name || 'วิดีโอ';
    setJobProjectName(projName);
    activeProjectRef.current = projName;
    const now = Date.now();
    setStartTime(now);
    setElapsedSeconds(0);
    setDisplayPercent(5);
    setIsRendering(true);
    setApplyError(null);
    setApplyResult(null);
    const initialStatus = { progress: 0.05, message: 'กำลังเตรียมข้อมูลและจัดโครงสร้างสคริปต์...' };
    setJobStatus(initialStatus);

    try {
      const res = await startRender(payload);
      if (res?.job_id) {
        startJob(res.job_id, initialStatus);
        return res.job_id;
      } else {
        throw new Error('ไม่พบ Job ID จากเซิร์ฟเวอร์');
      }
    } catch (err) {
      stopJob();
      const errMsg = err?.friendlyMessage || err?.response?.data?.detail || err?.message || 'เกิดข้อผิดพลาดในการสั่งเรนเดอร์';
      setApplyError(errMsg);
      callbacksRef.current.onError?.(errMsg);
      throw err;
    }
  }, [resetJob, startJob, stopJob]);

  // Handle project switching and resume active jobs
  useEffect(() => {
    activeProjectRef.current = projectName;
    clearTimer();
    setIsRendering(false);
    setJobStatus(null);
    setStartTime(null);
    setElapsedSeconds(0);
    setDisplayPercent(0);
    if (projectName) {
      setJobProjectName(projectName);
    }

    if (!projectName) {
      setJobId(null);
      return undefined;
    }

    // Check if there is an active background render job for this tab. The
    // job is tracked by its stable job_id, not by project label (see
    // renderJobModel.js) -- so this resumes correctly even if the label the
    // job was started under differs from the current `projectName` (e.g. a
    // project shown under its canonical on-disk name here after having been
    // started from NewClipPanel's own product-name-based label).
    const storedJobId = getActiveJob(projectName);
    if (storedJobId) {
      setJobId(storedJobId);
      setIsRendering(true);
      setStartTime(Date.now());
      setJobStatus({ progress: 0.1, message: 'กำลังตรวจสอบสถานะการเรนเดอร์...' });
      pollJob(storedJobId, projectName);
    } else {
      setJobId(null);
    }

    return clearTimer;
  }, [clearTimer, pollJob, projectName]);

  // Real-time 1-second elapsed timer
  useEffect(() => {
    if (!isRendering || !startTime) {
      setElapsedSeconds(0);
      return;
    }
    const updateElapsed = () => {
      const elapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
      setElapsedSeconds(elapsed);
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [isRendering, startTime]);

  // Smooth micro-progress ticker ensuring line and percentage always visibly advance
  useEffect(() => {
    if (!isRendering) {
      if (!applyResult) setDisplayPercent(0);
      return;
    }

    const targetPct = Math.round((jobStatus?.progress || 0.05) * 100);

    const ticker = setInterval(() => {
      setDisplayPercent((curr) => {
        if (curr < targetPct) {
          const step = Math.max(1, Math.ceil((targetPct - curr) / 3));
          return Math.min(targetPct, curr + step);
        }
        // Micro-trickle while waiting for long stages:
        const cap = targetPct < 70 ? targetPct + 4 : (targetPct < 85 ? targetPct + 3 : Math.min(98, targetPct + 2));
        if (curr < cap && Math.random() < 0.35) {
          return curr + 1;
        }
        return curr;
      });
    }, 350);

    return () => clearInterval(ticker);
  }, [isRendering, jobStatus?.progress, applyResult]);

  // Smart ETA estimation based on progress & elapsed time
  const estimatedRemainingSeconds = useMemo(() => {
    if (!isRendering || elapsedSeconds < 3 || displayPercent < 8) {
      return 110; // Baseline ~1.5 - 2 minutes
    }
    if (displayPercent >= 98) return 5;
    const progressFraction = Math.max(0.08, displayPercent / 100);
    const totalEst = elapsedSeconds / progressFraction;
    const remaining = Math.max(5, Math.round(totalEst - elapsedSeconds));
    return Math.min(240, remaining);
  }, [isRendering, elapsedSeconds, displayPercent]);

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
    rendering: isRendering,
    jobProjectName,
    setJobProjectName,
    applyResult,
    renderResult: applyResult,
    setApplyResult,
    applyError,
    renderError: applyError,
    setApplyError,
    progressPercent: progress.percent,
    progressMessage: progress.message,
    displayPercent,
    elapsedSeconds,
    estimatedRemainingSeconds,
    startJob,
    stopJob,
    executeRender,
    resetJob,
    clearResult,
    clearError,
  };
}

export default useRenderJob;
